"""Data coordinator for MAIKA devices and voice-command rules."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, Platform
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    MaikaApiClient,
    MaikaApiError,
    MaikaAuthenticationError,
)
from .const import (
    CONF_ENABLE_CLOUD_CAST,
    CONF_ENABLE_VOICE_COMMAND_SENSOR,
    CONF_SCAN_INTERVAL,
    CONF_VOICE_COMMAND_RULES,
    CONF_VOICE_SUCCESS_AUDIO_URL,
    CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VOICE_COMMAND_RULES,
    DOMAIN,
)
from .media_url import is_valid_http_media_url
from .voice_rules import (
    VoiceCommandRule,
    VoiceCommandRulesError,
    normalize_voice_phrase,
    parse_voice_command_rules,
)

_LOGGER = logging.getLogger(__name__)

type CoordinatorData = dict[str, Any]


class MaikaDataUpdateCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Coordinate REST polling and live speaker state."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: MaikaApiClient,
    ) -> None:
        self.entry = entry
        self.client = client
        self._processed_speech: dict[str, float] = {}
        self._last_voice_command: dict[str, Any] | None = None
        self._voice_command_sequence = 0
        self._stream_frame_count = 0
        self._stream_directive_count = 0
        self._last_stream_frame_kind: str | None = None
        self._last_stream_frame_type: str | None = None
        self._last_stream_frame_name: str | None = None
        self._last_stream_frame_namespace: str | None = None
        self._last_stream_frame_at: str | None = None
        self._last_stream_frame_has_raw_speech = False
        self._voice_subscription_lock = asyncio.Lock()
        self._voice_subscribed_generation: dict[str, int] = {}
        self._voice_subscription_target_count = 0
        self._voice_subscription_status = (
            "waiting_for_stream" if self._voice_stream_enabled() else "disabled"
        )
        self._voice_subscription_last_at: str | None = None
        self._voice_subscription_last_error: str | None = None
        try:
            voice_rules = parse_voice_command_rules(
                str(
                    entry.options.get(
                        CONF_VOICE_COMMAND_RULES, DEFAULT_VOICE_COMMAND_RULES
                    )
                )
            )
        except VoiceCommandRulesError as err:
            _LOGGER.error("Ignoring invalid MAIKA voice command rules: %s", err)
            voice_rules = ()
        self._voice_command_rules = {
            rule.normalized_phrase: rule for rule in voice_rules
        }
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
            config_entry=entry,
        )

    async def _async_update_data(self) -> CoordinatorData:
        try:
            listed_devices = await self.client.async_list_devices()
            details = await asyncio.gather(
                *(self._async_get_detail(device) for device in listed_devices)
            )
        except MaikaAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except MaikaApiError as err:
            raise UpdateFailed(str(err)) from err

        try:
            voices = await self.client.async_get_tts_voices()
        except MaikaAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except MaikaApiError as err:
            _LOGGER.debug("Unable to refresh MAIKA TTS voices: %s", err)
            voices = []

        devices: dict[str, dict[str, Any]] = {}
        for listed, detail in zip(listed_devices, details, strict=True):
            merged = {**listed, **detail}
            serial_number = merged.get("device_id")
            if isinstance(serial_number, str) and serial_number:
                devices[serial_number] = merged

        live_results = await asyncio.gather(
            *(
                self.client.async_request_device_info(serial_number)
                for serial_number in devices
            ),
            return_exceptions=True,
        )
        for serial_number, live_result in zip(devices, live_results, strict=True):
            if isinstance(live_result, dict):
                devices[serial_number] = self._merge_live_data(
                    devices[serial_number], live_result
                )

        await self._async_ensure_voice_subscriptions(devices)

        voice_options = {
            str(voice["code"]): str(voice.get("name") or voice["code"])
            for voice in voices
            if voice.get("code")
        }
        if not voice_options and self.data:
            voice_options = dict(self.data.get("voices", {}))

        return {
            "devices": devices,
            "voices": voice_options,
            "voice_command_rule_count": len(self._voice_command_rules),
            "last_voice_command": self._last_voice_command,
            **self._stream_diagnostics_data(),
        }

    async def _async_get_detail(self, listed_device: dict[str, Any]) -> dict[str, Any]:
        try:
            internal_id = int(listed_device["id"])
            return await self.client.async_get_device(internal_id)
        except MaikaAuthenticationError:
            raise
        except (KeyError, TypeError, ValueError, MaikaApiError):
            return listed_device

    async def async_refresh_live(self, serial_number: str) -> None:
        """Refresh live volume, mute and playback data for one speaker."""
        try:
            live = await self.client.async_request_device_info(serial_number)
        except MaikaAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except MaikaApiError:
            return
        if live:
            self.async_update_device_data(serial_number, live)

    @callback
    def async_update_device_data(
        self, serial_number: str, changes: dict[str, Any]
    ) -> None:
        """Apply optimistic or stream-driven changes to coordinator data."""
        if not self.data:
            return
        devices = self.data.get("devices")
        if not isinstance(devices, dict) or serial_number not in devices:
            return
        updated_devices = dict(devices)
        updated_devices[serial_number] = self._merge_live_data(
            devices[serial_number], changes
        )
        self.async_set_updated_data(
            {
                **self.data,
                "devices": updated_devices,
                **self._stream_diagnostics_data(),
            }
        )

    @callback
    def async_handle_stream_frame(self, frame: dict[str, Any]) -> None:
        """Handle decoded frames emitted by the MAIKA /connect stream."""
        frame = self._normalize_stream_frame(frame)
        self._record_stream_frame(frame)
        self._publish_stream_diagnostics()

        if self._is_connect_frame(frame):
            self._schedule_voice_subscriptions()
            return

        header = frame.get("header")
        payload = frame.get("payload")
        if not isinstance(header, dict):
            return

        if (
            header.get("name") == "DeviceInfo"
            and header.get("namespace") == "ClientInformation"
            and isinstance(payload, dict)
        ):
            serial_number = payload.get("deviceId") or payload.get("device_id")
            if isinstance(serial_number, str) and serial_number:
                self.async_update_device_data(serial_number, payload)
            return

        if header.get("type") != "speakerConversationResponse":
            return
        if not self.entry.options.get(CONF_ENABLE_VOICE_COMMAND_SENSOR, False):
            return

        raw_speech = header.get("rawSpeech") or header.get("raw_speech")
        if not isinstance(raw_speech, str) or not raw_speech.strip():
            return
        raw_speech = raw_speech.strip()

        source_session_value = header.get("sessionId") or header.get("session_id")
        source_session = (
            str(source_session_value) if source_session_value is not None else None
        )
        message_id_value = (
            header.get("messageId")
            or header.get("message_id")
            or header.get("dialogRequestId")
            or header.get("dialog_request_id")
        )
        message_id = str(
            message_id_value
            or f"{source_session or 'unknown'}:{normalize_voice_phrase(raw_speech)}"
        )
        now = time.monotonic()
        self._processed_speech = {
            key: timestamp
            for key, timestamp in self._processed_speech.items()
            if now - timestamp < 300
        }
        dedupe_key = f"{message_id}:{normalize_voice_phrase(raw_speech)}"
        if dedupe_key in self._processed_speech:
            return
        self._processed_speech[dedupe_key] = now

        self._record_voice_command(
            raw_speech,
            source_session=source_session,
            message_id=message_id,
        )

    async def _async_ensure_voice_subscriptions(
        self, devices: dict[str, dict[str, Any]]
    ) -> None:
        """Subscribe the current cloud connection to every MAIKA speaker."""
        if not self._voice_stream_enabled():
            self._voice_subscription_target_count = 0
            self._voice_subscription_status = "disabled"
            self._voice_subscription_last_error = None
            return

        self._voice_subscription_target_count = len(devices)
        if not devices:
            self._voice_subscription_status = "no_devices"
            self._voice_subscription_last_error = None
            return
        if not self.client.listener_connected:
            self._voice_subscription_status = "waiting_for_stream"
            return

        async with self._voice_subscription_lock:
            generation = self.client.listener_generation
            if not self.client.listener_connected or generation <= 0:
                self._voice_subscription_status = "waiting_for_stream"
                return

            self._voice_subscribed_generation = {
                serial_number: subscribed_generation
                for serial_number, subscribed_generation in (
                    self._voice_subscribed_generation.items()
                )
                if serial_number in devices
            }
            attempted = False
            failed = False
            for serial_number in devices:
                if self._voice_subscribed_generation.get(serial_number) == generation:
                    continue
                attempted = True
                try:
                    await self.client.async_start_conversation_listening(serial_number)
                except MaikaAuthenticationError:
                    failed = True
                    self._voice_subscription_last_error = "authentication_failed"
                    _LOGGER.debug("Unable to authenticate one MAIKA voice subscription")
                except MaikaApiError:
                    failed = True
                    self._voice_subscription_last_error = "cloud_request_failed"
                    _LOGGER.debug("Unable to register one MAIKA voice subscription")
                else:
                    self._voice_subscribed_generation[serial_number] = generation

            if attempted:
                self._voice_subscription_last_at = datetime.now(UTC).isoformat()

            subscribed_count = self._current_voice_subscription_count()
            if subscribed_count == len(devices):
                self._voice_subscription_status = "subscribed"
                self._voice_subscription_last_error = None
            elif subscribed_count:
                self._voice_subscription_status = "partial"
            elif failed:
                self._voice_subscription_status = "failed"
            else:
                self._voice_subscription_status = "pending"

        self._publish_stream_diagnostics()

    async def async_stop_voice_subscriptions(self) -> None:
        """Best-effort StopListening for subscriptions created by this entry."""
        serial_numbers = tuple(self._voice_subscribed_generation)
        if not serial_numbers:
            return
        try:
            async with asyncio.timeout(10):
                for serial_number in serial_numbers:
                    try:
                        await self.client.async_stop_conversation_listening(
                            serial_number
                        )
                    except MaikaApiError:
                        _LOGGER.debug("Unable to stop one MAIKA voice subscription")
        except TimeoutError:
            _LOGGER.debug("Timed out stopping MAIKA voice subscriptions")
        self._voice_subscribed_generation.clear()

    @callback
    def _schedule_voice_subscriptions(self) -> None:
        """Re-register voice subscriptions after a stream reconnect."""
        if not self._voice_stream_enabled() or not self.data:
            return
        devices = self.data.get("devices")
        if not isinstance(devices, dict):
            return
        self.entry.async_create_background_task(
            self.hass,
            self._async_ensure_voice_subscriptions(devices),
            "MAIKA speaker conversation subscriptions",
        )

    @callback
    def _record_voice_command(
        self,
        raw_speech: str,
        *,
        source_session: str | None,
        message_id: str,
    ) -> None:
        """Store the latest phrase and start its matching safe rule."""
        normalized = normalize_voice_phrase(raw_speech)
        rule = self._voice_command_rules.get(normalized)
        entity_state = self.hass.states.get(rule.entity_id) if rule else None
        service = f"{rule.entity_id.partition('.')[0]}.{rule.action}" if rule else None
        self._voice_command_sequence += 1
        sequence = self._voice_command_sequence
        self._last_voice_command = {
            "text": raw_speech,
            "normalized": normalized,
            "received_at": datetime.now(UTC).isoformat(),
            "message_id": message_id,
            "source_session": source_session,
            "matched_phrase": rule.phrase if rule else None,
            "target_entity_id": rule.entity_id if rule else None,
            "action": rule.action if rule else None,
            "service": service,
            "entity_state_before": entity_state.state if entity_state else None,
            "entity_state_after": None,
            "executed": False,
            "error": None,
            "success_audio_status": None,
            "success_audio_error": None,
        }
        self._publish_last_voice_command()

        if rule is not None:
            self.entry.async_create_background_task(
                self.hass,
                self._async_execute_voice_rule(rule, sequence=sequence),
                "MAIKA voice command action",
            )

    async def _async_execute_voice_rule(
        self, rule: VoiceCommandRule, *, sequence: int
    ) -> None:
        """Execute one allow-listed generic Home Assistant entity action."""
        executed = False
        error: str | None = None
        service_domain = rule.entity_id.partition(".")[0]
        entity_state = self.hass.states.get(rule.entity_id)

        if entity_state is None:
            error = "entity_not_found"
            _LOGGER.warning(
                "MAIKA voice rule target %s does not exist",
                rule.entity_id,
            )
        elif entity_state.state == STATE_UNAVAILABLE:
            error = "entity_unavailable"
            _LOGGER.warning(
                "MAIKA voice rule target %s is unavailable",
                rule.entity_id,
            )
        elif not self.hass.services.has_service(service_domain, rule.action):
            error = "service_not_supported"
            _LOGGER.warning(
                "MAIKA voice rule target %s does not support %s",
                rule.entity_id,
                rule.action,
            )
        else:
            try:
                await self.hass.services.async_call(
                    service_domain,
                    rule.action,
                    {ATTR_ENTITY_ID: rule.entity_id},
                    blocking=True,
                    context=Context(),
                )
                executed = True
            except Exception as err:
                error = type(err).__name__
                _LOGGER.warning(
                    "MAIKA voice action %s for %s failed: %s",
                    rule.action,
                    rule.entity_id,
                    err,
                )

        if sequence != self._voice_command_sequence or self._last_voice_command is None:
            return
        entity_state_after = self.hass.states.get(rule.entity_id)
        self._last_voice_command = {
            **self._last_voice_command,
            "entity_state_after": (
                entity_state_after.state if entity_state_after else None
            ),
            "executed": executed,
            "error": error,
            "success_audio_status": (
                "pending" if executed and self._voice_success_audio_enabled() else None
            ),
            "success_audio_error": None,
        }
        self._publish_last_voice_command()

        if not executed or not self._voice_success_audio_enabled():
            return

        (
            success_audio_status,
            success_audio_error,
        ) = await self._async_play_voice_success_audio()
        if sequence != self._voice_command_sequence or self._last_voice_command is None:
            return
        self._last_voice_command = {
            **self._last_voice_command,
            "success_audio_status": success_audio_status,
            "success_audio_error": success_audio_error,
        }
        self._publish_last_voice_command()

    def _voice_success_audio_enabled(self) -> bool:
        return bool(
            str(self.entry.options.get(CONF_VOICE_SUCCESS_AUDIO_URL, "")).strip()
        )

    async def _async_play_voice_success_audio(self) -> tuple[str, str | None]:
        """Cast a configured MP3 only after a HASS voice action succeeds."""
        if not self.entry.options.get(CONF_ENABLE_CLOUD_CAST, False):
            return "failed", "cloud_cast_disabled"

        audio_url = str(
            self.entry.options.get(CONF_VOICE_SUCCESS_AUDIO_URL, "")
        ).strip()
        if not audio_url:
            return "failed", "audio_url_not_configured"
        if not is_valid_http_media_url(audio_url):
            return "failed", "audio_url_invalid"

        media_player_entity_id, target_error = (
            self._voice_success_media_player_entity_id()
        )
        if media_player_entity_id is None:
            return "failed", target_error

        registry = er.async_get(self.hass)
        media_player_registry_entry = registry.async_get(media_player_entity_id)
        if media_player_registry_entry is None:
            return "failed", "media_player_not_found"
        if (
            media_player_registry_entry.domain != Platform.MEDIA_PLAYER
            or media_player_registry_entry.platform != DOMAIN
            or media_player_registry_entry.config_entry_id != self.entry.entry_id
        ):
            return "failed", "media_player_not_maika_entry"

        media_player_state = self.hass.states.get(media_player_entity_id)
        if media_player_state is None:
            return "failed", "media_player_not_found"
        if media_player_state.state == STATE_UNAVAILABLE:
            return "failed", "media_player_unavailable"

        unique_id = media_player_registry_entry.unique_id
        unique_id_suffix = "_media_player"
        if not unique_id.endswith(unique_id_suffix):
            return "failed", "media_player_unique_id_invalid"
        serial_number = unique_id[: -len(unique_id_suffix)]
        devices = self.data.get("devices", {}) if self.data else {}
        if not isinstance(devices, dict) or serial_number not in devices:
            return "failed", "media_player_device_not_found"

        try:
            await self.client.async_cast_media(
                serial_number,
                audio_url,
                title="Home Assistant",
                stream_format="AUDIO_MPEG",
            )
        except MaikaApiError as err:
            error_type = type(err).__name__
            _LOGGER.warning("MAIKA voice success audio failed (%s)", error_type)
            return "failed", error_type

        self.async_update_device_data(
            serial_number,
            {
                "current_playback": {
                    "status": "start",
                    "payload": {
                        "offsetInMilliseconds": 0,
                        "playbackAttributes": {
                            "mediaType": "audio/mpeg",
                            "media_type": "audio/mpeg",
                            "title": "Home Assistant",
                            "url": audio_url,
                        },
                    },
                }
            },
        )
        return "played", None

    def _voice_success_media_player_entity_id(
        self,
    ) -> tuple[str | None, str | None]:
        """Resolve the configured speaker or the only speaker in this entry."""
        registry = er.async_get(self.hass)
        configured_entity_id = str(
            self.entry.options.get(CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID, "")
        ).strip()
        if configured_entity_id:
            return configured_entity_id, None

        entity_ids = tuple(
            registry_entry.entity_id
            for registry_entry in er.async_entries_for_config_entry(
                registry, self.entry.entry_id
            )
            if registry_entry.domain == Platform.MEDIA_PLAYER
            and registry_entry.platform == DOMAIN
            and registry_entry.disabled_by is None
        )
        if len(entity_ids) == 1:
            return entity_ids[0], None
        if not entity_ids:
            return None, "media_player_not_found"
        return None, "media_player_not_configured"

    @callback
    def _publish_last_voice_command(self) -> None:
        """Notify coordinator entities about the latest voice command."""
        if not self.data:
            return
        self.async_set_updated_data(
            {
                **self.data,
                "last_voice_command": self._last_voice_command,
                **self._stream_diagnostics_data(),
            }
        )

    @callback
    def _publish_stream_diagnostics(self) -> None:
        """Publish safe stream metadata without raw cloud payloads."""
        if not self.data:
            return
        self.async_set_updated_data(
            {
                **self.data,
                **self._stream_diagnostics_data(),
            }
        )

    @staticmethod
    def _merge_live_data(
        device: dict[str, Any], live: dict[str, Any]
    ) -> dict[str, Any]:
        merged = dict(device)
        for key in ("volume", "mute", "current_playback", "latest_playlist"):
            if key in live:
                merged[key] = live[key]
        return merged

    def _voice_stream_enabled(self) -> bool:
        return bool(self.entry.options.get(CONF_ENABLE_VOICE_COMMAND_SENSOR, False))

    def _current_voice_subscription_count(self) -> int:
        generation = self.client.listener_generation
        return sum(
            subscribed_generation == generation
            for subscribed_generation in self._voice_subscribed_generation.values()
        )

    def _stream_diagnostics_data(self) -> dict[str, Any]:
        return {
            "stream_connected": self.client.listener_connected,
            "stream_generation": self.client.listener_generation,
            "stream_frame_count": self._stream_frame_count,
            "stream_directive_count": self._stream_directive_count,
            "last_stream_frame_kind": self._last_stream_frame_kind,
            "last_stream_frame_type": self._last_stream_frame_type,
            "last_stream_frame_name": self._last_stream_frame_name,
            "last_stream_frame_namespace": self._last_stream_frame_namespace,
            "last_stream_frame_at": self._last_stream_frame_at,
            "last_stream_frame_has_raw_speech": (
                self._last_stream_frame_has_raw_speech
            ),
            "voice_subscription_status": self._voice_subscription_status,
            "voice_subscription_target_count": (self._voice_subscription_target_count),
            "voice_subscription_count": self._current_voice_subscription_count(),
            "voice_subscription_last_at": self._voice_subscription_last_at,
            "voice_subscription_last_error": (self._voice_subscription_last_error),
        }

    def _record_stream_frame(self, frame: dict[str, Any]) -> None:
        self._stream_frame_count += 1
        header = frame.get("header")
        if self._is_connect_frame(frame):
            frame_kind = "connect"
        elif "apiKeys" in frame:
            frame_kind = "api_keys"
        elif isinstance(header, dict):
            frame_kind = "directive"
            self._stream_directive_count += 1
        else:
            frame_kind = "unknown"

        self._last_stream_frame_kind = frame_kind
        self._last_stream_frame_type = self._safe_stream_value(
            header.get("type") if isinstance(header, dict) else None
        )
        self._last_stream_frame_name = self._safe_stream_value(
            header.get("name") if isinstance(header, dict) else None
        )
        self._last_stream_frame_namespace = self._safe_stream_value(
            header.get("namespace") if isinstance(header, dict) else None
        )
        self._last_stream_frame_has_raw_speech = bool(
            isinstance(header, dict)
            and (header.get("rawSpeech") or header.get("raw_speech"))
        )
        self._last_stream_frame_at = datetime.now(UTC).isoformat()

    @staticmethod
    def _safe_stream_value(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text[:128] or None

    @staticmethod
    def _is_connect_frame(frame: dict[str, Any]) -> bool:
        if frame.get("session_id"):
            return True
        if "connected" not in frame:
            return False
        header = frame.get("header")
        return isinstance(header, dict) and bool(
            header.get("sessionId") or header.get("session_id")
        )

    @staticmethod
    def _normalize_stream_frame(frame: dict[str, Any]) -> dict[str, Any]:
        if isinstance(frame.get("header"), dict):
            return frame
        for key in ("directive", "event", "message", "response", "data"):
            nested = frame.get(key)
            if isinstance(nested, dict):
                normalized = MaikaDataUpdateCoordinator._normalize_stream_frame(nested)
                if isinstance(normalized.get("header"), dict):
                    return normalized
        return frame
