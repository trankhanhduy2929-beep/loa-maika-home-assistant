"""Data coordinator for MAIKA devices and voice-command rules."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.components import persistent_notification
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
    merge_current_playback,
)
from .audio_library import async_ensure_audio_library_paths, library_audio_url
from .command_history import MaikaVoiceCommandHistoryStore
from .const import (
    CONF_ENABLE_CLOUD_CAST,
    CONF_ENABLE_VOICE_COMMAND_SENSOR,
    CONF_SCAN_INTERVAL,
    CONF_VOICE_COMMAND_RULES,
    CONF_VOICE_RESPONSE_TTS_ENTITY_ID,
    CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VOICE_COMMAND_RULES,
    DOMAIN,
    LICENSE_EXPIRY_REMINDER_DAYS,
    MAX_CHAT_HISTORY,
    MAX_CHAT_MESSAGE_LENGTH,
    MAX_VOICE_COMMAND_HISTORY,
    VOICE_SUCCESS_AUDIO_TIMING_PRIORITY,
)
from .license_config import LICENSE_PORTAL_URL
from .media_url import is_valid_http_media_url
from .voice_rules import (
    VoiceCommandRule,
    VoiceCommandRulesError,
    normalize_voice_phrase,
    parse_voice_command_rules,
)
from .voice_state import format_voice_state
from .voice_success_audio import (
    has_voice_success_audio,
    resolve_voice_success_audio_path,
    resolve_voice_success_audio_timing,
    resolve_voice_success_audio_url,
)

_LOGGER = logging.getLogger(__name__)
_LIVE_FIELDS = ("volume", "mute", "current_playback", "latest_playlist")
_PLAYBACK_REFRESH_DELAYS = (0, 1, 2)

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
        self._stopping = False
        self._live_device_data: dict[str, dict[str, Any]] = {}
        self._live_revision = 0
        self._live_field_revisions: dict[str, dict[str, int]] = {}
        self._playback_refresh_tasks: dict[str, asyncio.Task[Any]] = {}
        self._media_subscription_lock = asyncio.Lock()
        self._media_subscription_targets: set[str] = set()
        self._media_subscribed_generation: dict[str, int] = {}
        self._media_subscription_pending: dict[str, int] = {}
        self._media_subscription_task: asyncio.Task[Any] | None = None
        self._media_subscription_generation = 0
        self._media_subscription_task_targets: frozenset[str] = frozenset()
        self._voice_subscription_task: asyncio.Task[Any] | None = None
        self._voice_subscription_generation = 0
        self._voice_subscription_pending: set[str] = set()
        self._processed_speech: dict[str, float] = {}
        self._last_voice_command: dict[str, Any] | None = None
        self._voice_command_history: list[dict[str, Any]] = []
        self._history_store = MaikaVoiceCommandHistoryStore(hass, entry.entry_id)
        self._history_save_task: asyncio.Task[Any] | None = None
        self._chat_log: list[dict[str, Any]] = []
        self._chat_pending_serial: str | None = None
        self._license_reminder_date: str | None = None
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

    async def _async_setup(self) -> None:
        """Restore the persisted voice-command history before first refresh."""
        try:
            history = await self._history_store.async_load()
        except Exception:  # history storage must never block setup
            _LOGGER.debug("Unable to load MAIKA command history", exc_info=True)
            return
        if history:
            self._voice_command_history = history[:MAX_VOICE_COMMAND_HISTORY]

    async def _async_update_data(self) -> CoordinatorData:
        if self._stopping:
            return self.data or {"devices": {}}
        previous_devices = self.data.get("devices", {}) if self.data else {}
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
                devices[serial_number] = {
                    **{
                        key: value
                        for key, value in previous_devices.get(
                            serial_number, {}
                        ).items()
                        if key in _LIVE_FIELDS
                    },
                    **merged,
                }

        if self._stopping:
            return self.data or {"devices": {}}
        self._media_subscription_targets = set(devices)
        for serial_number, device in devices.items():
            latest = self._live_device_data.setdefault(serial_number, {})
            for key in _LIVE_FIELDS:
                if key in device and key not in latest:
                    latest[key] = deepcopy(device[key])
        for serial_number in tuple(self._playback_refresh_tasks):
            if serial_number not in devices:
                self._playback_refresh_tasks.pop(serial_number).cancel()
        self._schedule_media_subscriptions()
        if self._media_subscription_task is not None:
            await asyncio.gather(self._media_subscription_task, return_exceptions=True)
        await asyncio.gather(
            *(self.async_refresh_live(serial_number) for serial_number in devices),
            return_exceptions=True,
        )
        self._schedule_voice_subscriptions(devices)
        if self._voice_subscription_task is not None:
            await asyncio.gather(self._voice_subscription_task, return_exceptions=True)
        if self._stopping:
            return self.data or {"devices": {}}
        for serial_number, live in self._live_device_data.items():
            if serial_number in devices:
                revisions = self._live_field_revisions.get(serial_number, {})
                devices[serial_number] = {
                    **devices[serial_number],
                    **{
                        key: deepcopy(value)
                        for key, value in live.items()
                        if key in revisions
                    },
                }
        self._live_device_data = {
            serial: live
            for serial, live in self._live_device_data.items()
            if serial in devices
        }
        self._live_field_revisions = {
            serial: revisions
            for serial, revisions in self._live_field_revisions.items()
            if serial in devices
        }

        voice_options = {
            str(voice["code"]): str(voice.get("name") or voice["code"])
            for voice in voices
            if voice.get("code")
        }
        if not voice_options and self.data:
            voice_options = dict(self.data.get("voices", {}))

        self._async_check_license_expiry()
        return {
            "devices": devices,
            "voices": voice_options,
            "voice_command_rule_count": len(self._voice_command_rules),
            "last_voice_command": self._last_voice_command,
            "voice_command_history": list(self._voice_command_history),
            **self._stream_diagnostics_data(),
        }

    @property
    def voice_command_history(self) -> list[dict[str, Any]]:
        """Return recent recognized commands, newest first."""
        return list(self._voice_command_history)

    @callback
    def _remember_voice_command(self) -> None:
        """Keep the latest finalized command in the recent-history list."""
        command = self._last_voice_command
        if not isinstance(command, dict) or command.get("executed") is None:
            return
        stored = {
            key: value
            for key, value in command.items()
            if key not in {"message_id", "source_session", "service_data"}
        }
        identity = f"{command.get('received_at')}|{command.get('normalized')}"
        for index, existing in enumerate(self._voice_command_history):
            existing_identity = (
                f"{existing.get('received_at')}|{existing.get('normalized')}"
            )
            if existing_identity == identity:
                self._voice_command_history[index] = stored
                break
        else:
            self._voice_command_history.insert(0, stored)
        del self._voice_command_history[MAX_VOICE_COMMAND_HISTORY:]
        self._schedule_history_save()

    @callback
    def _schedule_history_save(self) -> None:
        """Persist the command history without blocking the event loop."""
        task = self._history_save_task
        if task is not None and not task.done():
            task.cancel()
        self._history_save_task = self.entry.async_create_background_task(
            self.hass,
            self._history_store.async_save(list(self._voice_command_history)),
            "MAIKA command history save",
        )

    @property
    def chat_log(self) -> list[dict[str, Any]]:
        """Return the recent speaker chat turns, oldest first."""
        return [dict(turn) for turn in self._chat_log]

    async def async_send_chat(self, serial_number: str, text: str) -> dict[str, Any]:
        """Send a typed utterance to one speaker and record the user turn."""
        message = (text or "").strip()
        if not message:
            return {"ok": False, "error": "empty_message"}
        if len(message) > MAX_CHAT_MESSAGE_LENGTH:
            return {"ok": False, "error": "message_too_long"}
        if serial_number not in (self.data or {}).get("devices", {}):
            return {"ok": False, "error": "unknown_speaker"}
        try:
            await self.client.async_send_voice_text(serial_number, message)
        except MaikaApiError:
            _LOGGER.debug("Unable to send MAIKA chat message", exc_info=True)
            return {"ok": False, "error": "send_failed"}
        self._append_chat("user", message, serial_number)
        self._chat_pending_serial = serial_number
        return {"ok": True, "chat": self.chat_log}

    @callback
    def _append_chat(self, role: str, text: str, serial_number: str) -> None:
        self._chat_log.append(
            {
                "role": role,
                "text": text,
                "serial_number": serial_number,
                "at": datetime.now(UTC).isoformat(),
            }
        )
        del self._chat_log[:-MAX_CHAT_HISTORY]

    @callback
    def _maybe_capture_assistant_reply(
        self, header: dict[str, Any], frame: dict[str, Any]
    ) -> None:
        """Attach a spoken assistant reply to the pending chat turn."""
        if not self._chat_pending_serial:
            return
        namespace = str(header.get("namespace", "")).casefold()
        if namespace not in ("texttospeech", "speechsynthesizer"):
            return
        text = self._extract_speech_text(frame)
        if not text:
            return
        serial_number = self._chat_pending_serial
        self._chat_pending_serial = None
        self._append_chat("assistant", text, serial_number)
        self._publish_last_voice_command()

    @classmethod
    def _extract_speech_text(cls, frame: dict[str, Any]) -> str | None:
        """Best-effort extraction of display text from a TTS directive frame."""
        response = frame.get("response")
        if isinstance(response, dict):
            items = response.get("items")
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    simple = item.get("simpleResponse")
                    if not isinstance(simple, dict):
                        continue
                    for key in ("displayText", "textToSpeech", "ssml"):
                        value = simple.get(key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()
        return None

    @callback
    def _async_check_license_expiry(self) -> None:
        """Raise one daily reminder while a paid key is close to expiring."""
        runtime = getattr(self.entry, "runtime_data", None)
        entitlement = getattr(
            getattr(runtime, "license_manager", None), "entitlement", None
        )
        expires_at = getattr(entitlement, "license_expires_at", None)
        notification_id = f"maika_license_expiry_{self.entry.entry_id}"
        if not isinstance(expires_at, int):
            return
        remaining_seconds = expires_at - int(time.time())
        if remaining_seconds > LICENSE_EXPIRY_REMINDER_DAYS * 86_400:
            if self._license_reminder_date is not None:
                self._license_reminder_date = None
                persistent_notification.async_dismiss(self.hass, notification_id)
            return
        today = datetime.now(UTC).date().isoformat()
        if self._license_reminder_date == today:
            return
        self._license_reminder_date = today
        if remaining_seconds < 0:
            summary = "Key MAIKA đã hết hạn."
        else:
            days_left = max(1, math.ceil(remaining_seconds / 86_400))
            summary = f"Key MAIKA còn khoảng {days_left} ngày."
        persistent_notification.async_create(
            self.hass,
            f"{summary} Mở panel MAIKA → Bản quyền để gia hạn: {LICENSE_PORTAL_URL}",
            title="MAIKA: key sắp hết hạn",
            notification_id=notification_id,
        )

    async def _async_get_detail(self, listed_device: dict[str, Any]) -> dict[str, Any]:
        try:
            internal_id = int(listed_device["id"])
            return await self.client.async_get_device(internal_id)
        except MaikaAuthenticationError:
            raise
        except (KeyError, TypeError, ValueError, MaikaApiError):
            return listed_device

    async def async_refresh_live(
        self, serial_number: str, *, required_fields: tuple[str, ...] = ()
    ) -> bool:
        """Refresh live volume, mute and playback data for one speaker."""
        if self._stopping:
            return False
        revision = self._live_revision
        try:
            live = await self.client.async_request_device_info(serial_number)
        except MaikaAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except MaikaApiError:
            return False
        if self._stopping or not isinstance(live, dict):
            return False
        revisions = self._live_field_revisions.get(serial_number, {})
        changes = {
            key: live[key]
            for key in _LIVE_FIELDS
            if key in live and revisions.get(key, 0) <= revision
        }
        if changes:
            self.async_update_device_data(serial_number, changes)
        if required_fields:
            return all(
                key in live or revisions.get(key, 0) > revision
                for key in required_fields
            )
        return any(key in live for key in _LIVE_FIELDS)

    @callback
    def async_schedule_playback_refresh(self, serial_number: str) -> None:
        if self._stopping or not self.data:
            return
        if serial_number not in self.data.get("devices", {}):
            return
        previous = self._playback_refresh_tasks.pop(serial_number, None)
        if previous is not None:
            previous.cancel()
        self._playback_refresh_tasks[serial_number] = (
            self.entry.async_create_background_task(
                self.hass,
                self._async_playback_refresh(serial_number),
                "MAIKA playback follow-up refresh",
            )
        )

    async def _async_playback_refresh(self, serial_number: str) -> None:
        try:
            for delay in _PLAYBACK_REFRESH_DELAYS:
                if delay:
                    await asyncio.sleep(delay)
                if self._stopping or not self.data:
                    return
                if serial_number not in self.data.get("devices", {}):
                    return
                try:
                    await self.async_refresh_live(serial_number)
                except ConfigEntryAuthFailed:
                    return
        finally:
            if (
                self._playback_refresh_tasks.get(serial_number)
                is asyncio.current_task()
            ):
                self._playback_refresh_tasks.pop(serial_number, None)

    @callback
    def async_update_device_data(
        self, serial_number: str, changes: dict[str, Any]
    ) -> None:
        """Apply optimistic or stream-driven changes to coordinator data."""
        if self._stopping:
            return
        changes = {key: changes[key] for key in _LIVE_FIELDS if key in changes}
        if not changes:
            return
        devices = self.data.get("devices", {}) if self.data else {}
        current = {
            **self._live_device_data.get(serial_number, {}),
            **devices.get(serial_number, {}),
        }
        merged = self._merge_live_data(current, changes)
        self._live_revision += 1
        revisions = self._live_field_revisions.setdefault(serial_number, {})
        latest = self._live_device_data.setdefault(serial_number, {})
        for key in changes:
            latest[key] = deepcopy(merged[key])
            revisions[key] = self._live_revision
        if serial_number not in devices:
            return
        updated_devices = dict(devices)
        updated_devices[serial_number] = merged
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
        if self._stopping:
            return
        frame = self._normalize_stream_frame(frame)
        self._record_stream_frame(frame)
        self._publish_stream_diagnostics()

        if self._is_connect_frame(frame):
            self._schedule_media_subscriptions()
            self._schedule_voice_subscriptions()
            return

        header = frame.get("header")
        payload = frame.get("payload")
        if not isinstance(header, dict):
            return

        self._maybe_capture_assistant_reply(header, frame)

        if (
            str(header.get("name", "")).casefold() == "deviceinfo"
            and str(header.get("namespace", "")).casefold() == "clientinformation"
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
        dialog_request_id = self._safe_stream_value(
            header.get("dialogRequestId") or header.get("dialog_request_id")
        )
        conversation_message_id = self._safe_stream_value(
            header.get("messageId") or header.get("message_id")
        )
        server_message_id = self._safe_stream_value(
            header.get("serverMessageId") or header.get("server_message_id")
        )
        message_id = str(
            conversation_message_id
            or dialog_request_id
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
            dialog_request_id=dialog_request_id,
            conversation_message_id=conversation_message_id,
            server_message_id=server_message_id,
        )

    async def _async_ensure_media_subscriptions(self) -> None:
        if self._stopping or not self.client.listener_connected:
            return
        async with self._media_subscription_lock:
            generation = self.client.listener_generation
            if self._stopping or not self.client.listener_connected or generation <= 0:
                return
            subscriptions = {
                **self._media_subscribed_generation,
                **self._media_subscription_pending,
            }
            for serial_number, subscribed in subscriptions.items():
                if serial_number in self._media_subscription_targets:
                    continue
                if subscribed == generation:
                    try:
                        await self.client.async_stop_media_listening(serial_number)
                    except MaikaApiError:
                        _LOGGER.debug("Unable to stop one MAIKA media subscription")
                        continue
                self._media_subscribed_generation.pop(serial_number, None)
                self._media_subscription_pending.pop(serial_number, None)
            for serial_number in tuple(self._media_subscription_targets):
                if serial_number not in self._media_subscription_targets:
                    continue
                if (
                    self._stopping
                    or not self.client.listener_connected
                    or self.client.listener_generation != generation
                ):
                    return
                if self._media_subscribed_generation.get(serial_number) == generation:
                    continue
                self._media_subscription_pending[serial_number] = generation
                try:
                    await self.client.async_start_media_listening(serial_number)
                except MaikaApiError:
                    _LOGGER.debug("Unable to register one MAIKA media subscription")
                else:
                    self._media_subscribed_generation[serial_number] = generation
                self._media_subscription_pending.pop(serial_number, None)

    @callback
    def _schedule_media_subscriptions(self) -> None:
        if self._stopping:
            return
        generation = self.client.listener_generation
        targets = frozenset(self._media_subscription_targets)
        task = self._media_subscription_task
        if task is not None and not task.done():
            if (
                self._media_subscription_generation == generation
                and self._media_subscription_task_targets == targets
            ):
                return
            task.cancel()
        self._media_subscription_generation = generation
        self._media_subscription_task_targets = targets
        self._media_subscription_task = self.entry.async_create_background_task(
            self.hass,
            self._async_ensure_media_subscriptions(),
            "MAIKA speaker media subscriptions",
        )

    async def async_stop(self) -> None:
        self._stopping = True
        tasks = [
            *self._playback_refresh_tasks.values(),
            self._media_subscription_task,
            self._voice_subscription_task,
        ]
        pending = [task for task in tasks if task is not None and not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self._playback_refresh_tasks.clear()
        try:
            async with asyncio.timeout(10), self._media_subscription_lock:
                for serial_number in (
                    self._media_subscribed_generation.keys()
                    | self._media_subscription_pending.keys()
                ):
                    try:
                        await self.client.async_stop_media_listening(serial_number)
                    except MaikaApiError:
                        _LOGGER.debug("Unable to stop one MAIKA media subscription")
        except TimeoutError:
            _LOGGER.debug("Timed out stopping MAIKA media subscriptions")
        self._media_subscribed_generation.clear()
        self._media_subscription_pending.clear()
        self._media_subscription_targets.clear()
        self._live_device_data.clear()
        self._live_field_revisions.clear()
        await self.async_stop_voice_subscriptions()
        await self._async_flush_history()

    async def _async_flush_history(self) -> None:
        """Write the pending command history to storage on shutdown."""
        task = self._history_save_task
        if task is not None and not task.done():
            task.cancel()
        self._history_save_task = None
        try:
            async with asyncio.timeout(5):
                await self._history_store.async_save(list(self._voice_command_history))
        except TimeoutError:
            _LOGGER.debug("Timed out saving MAIKA command history")
        except Exception:  # never fail shutdown on storage
            _LOGGER.debug("Unable to save MAIKA command history", exc_info=True)

    async def _async_ensure_voice_subscriptions(
        self, devices: dict[str, dict[str, Any]]
    ) -> None:
        """Subscribe the current cloud connection to every MAIKA speaker."""
        if self._stopping:
            return
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
            if self._stopping:
                return
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
                if (
                    self._stopping
                    or not self.client.listener_connected
                    or self.client.listener_generation != generation
                ):
                    return
                if self._voice_subscribed_generation.get(serial_number) == generation:
                    continue
                attempted = True
                self._voice_subscription_pending.add(serial_number)
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
                self._voice_subscription_pending.discard(serial_number)

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
        try:
            async with asyncio.timeout(10), self._voice_subscription_lock:
                serial_numbers = (
                    self._voice_subscribed_generation.keys()
                    | self._voice_subscription_pending
                )
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
        self._voice_subscription_pending.clear()

    @callback
    def _schedule_voice_subscriptions(
        self, devices: dict[str, dict[str, Any]] | None = None
    ) -> None:
        """Re-register voice subscriptions after a stream reconnect."""
        if self._stopping or not self._voice_stream_enabled():
            return
        if devices is None:
            devices = self.data.get("devices") if self.data else None
        if not isinstance(devices, dict):
            return
        generation = self.client.listener_generation
        task = self._voice_subscription_task
        if task is not None and not task.done():
            if self._voice_subscription_generation == generation:
                return
            task.cancel()
        self._voice_subscription_generation = generation
        self._voice_subscription_task = self.entry.async_create_background_task(
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
        dialog_request_id: str | None,
        conversation_message_id: str | None,
        server_message_id: str | None,
    ) -> None:
        """Store the latest phrase and start its matching safe rule."""
        normalized = normalize_voice_phrase(raw_speech)
        rule = self._voice_command_rules.get(normalized)
        entity_state = self.hass.states.get(rule.entity_id) if rule else None
        service = rule.service if rule else None
        success_audio_enabled = (
            rule is not None
            and not rule.is_read
            and self._voice_success_audio_enabled()
        )
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
            "service_data": dict(rule.service_data) if rule else None,
            "entity_state_before": entity_state.state if entity_state else None,
            "entity_state_after": None,
            "executed": False,
            "error": None,
            "response_text": None,
            "success_audio_timing": (
                self._voice_success_audio_timing() if success_audio_enabled else None
            ),
            "success_audio_status": "pending" if success_audio_enabled else None,
            "success_audio_error": None,
        }
        self._publish_last_voice_command()

        if rule is not None:
            action = (
                self._async_execute_voice_read(rule, sequence=sequence)
                if rule.is_read
                else self._async_execute_voice_rule(
                    rule,
                    sequence=sequence,
                    dialog_request_id=dialog_request_id,
                    message_id=conversation_message_id,
                    server_message_id=server_message_id,
                )
            )
            self.entry.async_create_background_task(
                self.hass,
                action,
                "MAIKA voice command action",
            )

    async def _async_execute_voice_read(
        self,
        rule: VoiceCommandRule,
        *,
        sequence: int,
    ) -> None:
        """Speak the current state of a read-only voice rule target."""
        response_text: str | None = None
        executed = False
        error: str | None = None
        entity_state = self.hass.states.get(rule.entity_id)

        if entity_state is None:
            error = "entity_not_found"
            _LOGGER.warning(
                "MAIKA voice read target %s does not exist",
                rule.entity_id,
            )
        else:
            response_text = format_voice_state(entity_state)
            status, error = await self._async_speak_voice_response(response_text)
            executed = status == "played"

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
            "response_text": response_text,
        }
        self._publish_last_voice_command()

    async def _async_speak_voice_response(
        self, response_text: str
    ) -> tuple[str, str | None]:
        """Render a spoken answer on the configured MAIKA speaker via TTS."""
        if not self.entry.options.get(CONF_ENABLE_CLOUD_CAST, False):
            return "failed", "cloud_cast_disabled"
        if not self.hass.services.has_service("tts", "speak"):
            return "failed", "tts_not_supported"

        tts_entity_id, tts_error = self._voice_response_tts_entity_id()
        if tts_entity_id is None:
            return "failed", tts_error
        media_player_entity_id, player_error = self._voice_media_player_for_response()
        if media_player_entity_id is None:
            return "failed", player_error

        try:
            await self.hass.services.async_call(
                "tts",
                "speak",
                {
                    "entity_id": tts_entity_id,
                    "media_player_entity_id": media_player_entity_id,
                    "message": response_text,
                    "cache": True,
                },
                blocking=True,
                context=Context(),
            )
        except Exception as err:
            error_type = type(err).__name__
            _LOGGER.warning("MAIKA voice response TTS failed (%s)", error_type)
            return "failed", error_type
        return "played", None

    def _voice_response_tts_entity_id(self) -> tuple[str | None, str | None]:
        """Resolve the configured TTS entity or the only TTS entity."""
        configured_entity_id = str(
            self.entry.options.get(CONF_VOICE_RESPONSE_TTS_ENTITY_ID, "")
        ).strip()
        if configured_entity_id:
            if self.hass.states.get(configured_entity_id) is None:
                return None, "tts_not_found"
            return configured_entity_id, None

        entity_ids = tuple(self.hass.states.async_entity_ids("tts"))
        if len(entity_ids) == 1:
            return entity_ids[0], None
        if not entity_ids:
            return None, "tts_not_configured"
        return None, "tts_not_selected"

    def _voice_media_player_for_response(self) -> tuple[str | None, str | None]:
        """Validate that the answer will play on a speaker from this entry."""
        media_player_entity_id, error = self._voice_success_media_player_entity_id()
        if media_player_entity_id is None:
            return None, error

        registry_entry = er.async_get(self.hass).async_get(media_player_entity_id)
        if registry_entry is None:
            return None, "media_player_not_found"
        if (
            registry_entry.domain != Platform.MEDIA_PLAYER
            or registry_entry.platform != DOMAIN
            or registry_entry.config_entry_id != self.entry.entry_id
        ):
            return None, "media_player_not_maika_entry"
        state = self.hass.states.get(media_player_entity_id)
        if state is None:
            return None, "media_player_not_found"
        if state.state == STATE_UNAVAILABLE:
            return None, "media_player_unavailable"
        return media_player_entity_id, None

    async def _async_execute_voice_rule(
        self,
        rule: VoiceCommandRule,
        *,
        sequence: int,
        dialog_request_id: str | None,
        message_id: str | None,
        server_message_id: str | None,
    ) -> None:
        """Execute one allow-listed Home Assistant entity action."""
        executed = False
        error: str | None = None
        success_audio_enabled = self._voice_success_audio_enabled()
        success_audio_timing = self._voice_success_audio_timing()
        priority_audio_task: asyncio.Task[tuple[str, str | None]] | None = None
        priority_audio_cancelled = False
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
            if (
                success_audio_enabled
                and success_audio_timing == VOICE_SUCCESS_AUDIO_TIMING_PRIORITY
            ):
                priority_audio_task = self.entry.async_create_background_task(
                    self.hass,
                    self._async_play_voice_success_audio(
                        dialog_request_id=dialog_request_id,
                        message_id=message_id,
                        server_message_id=server_message_id,
                    ),
                    "MAIKA priority voice success audio",
                )
                await asyncio.sleep(0)
            try:
                service_data = dict(rule.service_data)
                service_data[ATTR_ENTITY_ID] = rule.entity_id
                await self.hass.services.async_call(
                    service_domain,
                    rule.action,
                    service_data,
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

        if (
            not executed
            and priority_audio_task is not None
            and not priority_audio_task.done()
        ):
            priority_audio_task.cancel()
            priority_audio_cancelled = True

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
                "pending"
                if priority_audio_task is not None
                or (executed and success_audio_enabled)
                else None
            ),
            "success_audio_error": None,
        }
        self._publish_last_voice_command()

        if priority_audio_task is not None:
            try:
                success_audio_status, success_audio_error = await priority_audio_task
            except asyncio.CancelledError:
                if not priority_audio_cancelled:
                    raise
                success_audio_status = "cancelled"
                success_audio_error = "home_assistant_action_failed"
            if not executed and success_audio_status == "played":
                success_audio_status = "played_before_failure"
        elif executed and success_audio_enabled:
            (
                success_audio_status,
                success_audio_error,
            ) = await self._async_play_voice_success_audio(
                dialog_request_id=dialog_request_id,
                message_id=message_id,
                server_message_id=server_message_id,
            )
        else:
            return

        if sequence != self._voice_command_sequence or self._last_voice_command is None:
            return
        self._last_voice_command = {
            **self._last_voice_command,
            "success_audio_status": success_audio_status,
            "success_audio_error": success_audio_error,
        }
        self._publish_last_voice_command()

    def _voice_success_audio_enabled(self) -> bool:
        return has_voice_success_audio(self.entry.options)

    def _voice_success_audio_timing(self) -> str:
        return resolve_voice_success_audio_timing(self.entry.options)

    async def _async_play_voice_success_audio(
        self,
        *,
        dialog_request_id: str | None,
        message_id: str | None,
        server_message_id: str | None,
    ) -> tuple[str, str | None]:
        """Cast the configured MP3 with the originating conversation context."""
        if not self.entry.options.get(CONF_ENABLE_CLOUD_CAST, False):
            return "failed", "cloud_cast_disabled"

        audio_url = resolve_voice_success_audio_url(self.entry.options)
        if not audio_url:
            library_path = resolve_voice_success_audio_path(self.entry.options)
            if not library_path:
                return "failed", "audio_url_not_configured"
            await async_ensure_audio_library_paths(self.hass)
            audio_url = library_audio_url(self.hass, library_path)
            if not audio_url:
                return "failed", "audio_library_unavailable"
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
                dialog_request_id=dialog_request_id,
                message_id=message_id,
                server_message_id=server_message_id,
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
        self._remember_voice_command()
        self.async_set_updated_data(
            {
                **self.data,
                "last_voice_command": self._last_voice_command,
                "voice_command_history": list(self._voice_command_history),
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
        for key in _LIVE_FIELDS:
            if key in live:
                merged[key] = (
                    merge_current_playback(device.get(key), live[key])
                    if key == "current_playback"
                    else deepcopy(live[key])
                )
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
