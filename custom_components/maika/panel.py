"""MAIKA Speaker management panel for the Home Assistant sidebar."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .api import MaikaApiError
from .audio_library import (
    AUDIO_LIBRARY_PANEL_PATH,
    AUDIO_LIBRARY_URL_PATH,
    async_ensure_audio_library_paths,
    list_audio_files,
    normalize_audio_path,
    resolve_audio_file,
)
from .const import (
    CONF_CLOUD_CAST_BASE_URL,
    CONF_ENABLE_CLOUD_CAST,
    CONF_ENABLE_VOICE_COMMAND_SENSOR,
    CONF_SCAN_INTERVAL,
    CONF_VOICE_COMMAND_RULES,
    CONF_VOICE_RESPONSE_TTS_ENTITY_ID,
    CONF_VOICE_SUCCESS_AUDIO_PATH,
    CONF_VOICE_SUCCESS_AUDIO_SOURCE,
    CONF_VOICE_SUCCESS_AUDIO_TIMING,
    CONF_VOICE_SUCCESS_AUDIO_URL,
    CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VOICE_COMMAND_RULES,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    VOICE_SUCCESS_AUDIO_SOURCE_CUSTOM,
    VOICE_SUCCESS_AUDIO_SOURCE_LIBRARY,
    VOICE_SUCCESS_AUDIO_SOURCE_OPTIONS,
    VOICE_SUCCESS_AUDIO_TIMING_OPTIONS,
)
from .license import (
    MaikaLicenseClient,
    MaikaLicenseConnectionError,
    MaikaLicenseResponseError,
    MaikaLicenseTokenError,
    async_get_installation_identity,
    normalize_license_key,
    normalize_license_server_url,
)
from .license_config import DEFAULT_LICENSE_SERVER_URL, LICENSE_PORTAL_URL
from .license_store import MaikaLicenseStore, MaikaStoredLicense
from .media_relay import MaikaMediaRelayView
from .media_url import is_valid_http_media_url
from .reminders import (
    REMINDER_STATUS_DISABLED,
    REMINDER_STATUS_ENABLED,
    ReminderValidationError,
    build_reminder_payload,
    build_reminder_update_payload,
    flatten_reminders,
)
from .voice_rules import (
    MAX_PHRASE_LENGTH,
    MAX_VOICE_COMMAND_RULES,
    VoiceCommandRulesError,
    parse_voice_command_rules,
    voice_action_catalog,
)
from .voice_success_audio import (
    resolve_voice_success_audio_path,
    resolve_voice_success_audio_source,
    resolve_voice_success_audio_timing,
)

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "maika-panel"
PANEL_MODULE_URL = "/maika_panel/maika-panel.js"
PANEL_TITLE = "MAIKA"
PANEL_ICON = "mdi:speaker-wireless"
STATIC_URL_PATH = "/maika_panel"
_REGISTERED_KEY = f"{DOMAIN}_panel_registered"
_FRONTEND_DIR = Path(__file__).parent / "frontend"

_OPTION_KEYS = (
    CONF_SCAN_INTERVAL,
    CONF_ENABLE_CLOUD_CAST,
    CONF_CLOUD_CAST_BASE_URL,
    CONF_ENABLE_VOICE_COMMAND_SENSOR,
    CONF_VOICE_COMMAND_RULES,
    CONF_VOICE_RESPONSE_TTS_ENTITY_ID,
    CONF_VOICE_SUCCESS_AUDIO_SOURCE,
    CONF_VOICE_SUCCESS_AUDIO_TIMING,
    CONF_VOICE_SUCCESS_AUDIO_URL,
    CONF_VOICE_SUCCESS_AUDIO_PATH,
    CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID,
)

_DEVICE_FIELDS = (
    "id",
    "device_id",
    "name",
    "calling_name",
    "address",
    "manufacturer",
    "model",
    "status",
    "firmware_version",
    "online",
    "available_to_call",
    "is_favorite",
    "wakeword_response_type",
    "wakeword_sensitivity_level",
    "tts_voice",
    "volume",
    "mute",
    "current_playback",
    "latest_playlist",
    "wifi",
)


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the sidebar panel, static assets and API views once."""
    if hass.data.get(_REGISTERED_KEY):
        return
    try:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    STATIC_URL_PATH,
                    str(_FRONTEND_DIR),
                    False,
                )
            ]
        )
    except Exception as err:  # pragma: no cover - defensive only
        _LOGGER.warning("Không đăng ký được tài nguyên panel MAIKA: %s", err)

    await async_ensure_audio_library_paths(hass)

    for view in (
        MaikaPanelStateView(hass),
        MaikaPanelFavoritesView(hass),
        MaikaPanelLicenseView(hass),
        MaikaPanelOptionsView(hass),
        MaikaPanelActionView(hass),
        MaikaPanelChatView(hass),
        MaikaPanelRemindersView(hass),
        MaikaPanelAudioLibraryView(hass),
        MaikaMediaRelayView(hass),
    ):
        hass.http.register_view(view)

    try:
        from homeassistant.components import panel_custom

        await panel_custom.async_register_panel(
            hass,
            webcomponent_name="maika-panel",
            frontend_url_path=PANEL_URL_PATH,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            module_url=f"{PANEL_MODULE_URL}?v={_module_version()}",
            config={"domain": DOMAIN},
            require_admin=False,
            embed_iframe=False,
        )
    except Exception as err:  # pragma: no cover - defensive only
        _LOGGER.warning("Không đăng ký được sidebar panel MAIKA: %s", err)
    hass.data[_REGISTERED_KEY] = True


async def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar panel when the last MAIKA account is deleted."""
    if not hass.data.pop(_REGISTERED_KEY, False):
        return
    try:
        from homeassistant.components import frontend

        frontend.async_remove_panel(hass, PANEL_URL_PATH)
    except Exception as err:  # pragma: no cover - defensive only
        _LOGGER.debug("Không gỡ được sidebar panel MAIKA: %s", err)


def _module_version() -> str:
    from .const import INTEGRATION_VERSION

    return INTEGRATION_VERSION


def _maika_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    return list(hass.config_entries.async_entries(DOMAIN))


def _entry_by_id(hass: HomeAssistant, entry_id: Any) -> ConfigEntry | None:
    if not isinstance(entry_id, str) or not entry_id:
        return None
    return hass.config_entries.async_get_entry(entry_id)


def _json_safe(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str))
    except (TypeError, ValueError):
        return str(value)


def _public_options(options: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_SCAN_INTERVAL: options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        CONF_ENABLE_CLOUD_CAST: bool(options.get(CONF_ENABLE_CLOUD_CAST, False)),
        CONF_CLOUD_CAST_BASE_URL: str(options.get(CONF_CLOUD_CAST_BASE_URL, "") or ""),
        CONF_ENABLE_VOICE_COMMAND_SENSOR: bool(
            options.get(CONF_ENABLE_VOICE_COMMAND_SENSOR, False)
        ),
        CONF_VOICE_COMMAND_RULES: options.get(
            CONF_VOICE_COMMAND_RULES, DEFAULT_VOICE_COMMAND_RULES
        ),
        CONF_VOICE_SUCCESS_AUDIO_SOURCE: resolve_voice_success_audio_source(options),
        CONF_VOICE_SUCCESS_AUDIO_TIMING: resolve_voice_success_audio_timing(options),
        CONF_VOICE_SUCCESS_AUDIO_URL: str(
            options.get(CONF_VOICE_SUCCESS_AUDIO_URL, "") or ""
        ),
        CONF_VOICE_SUCCESS_AUDIO_PATH: resolve_voice_success_audio_path(options),
        CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID: str(
            options.get(CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID, "") or ""
        ),
        CONF_VOICE_RESPONSE_TTS_ENTITY_ID: str(
            options.get(CONF_VOICE_RESPONSE_TTS_ENTITY_ID, "") or ""
        ),
    }


def _serialize_license(manager: Any) -> dict[str, Any]:
    if manager is None:
        return {"status": "unavailable", "key_hint": "", "activation_code": ""}
    record = getattr(manager, "record", None)
    entitlement = getattr(manager, "entitlement", None)
    return {
        "status": getattr(manager, "state", "unavailable"),
        "plan": getattr(entitlement, "plan", None),
        "features": list(getattr(entitlement, "features", ()) or ()),
        "expires_at": getattr(entitlement, "expires_at", None),
        "license_expires_at": getattr(entitlement, "license_expires_at", None),
        "grace_until": getattr(entitlement, "grace_until", None),
        "key_hint": getattr(entitlement, "key_hint", "") or "",
        "license_id": getattr(record, "license_id", None),
        "activation_code": getattr(record, "activation_code", ""),
        "server_url": getattr(record, "server_url", ""),
        "updated_at": getattr(record, "updated_at", 0),
    }


def _serial_for_device(
    device_registry: dr.DeviceRegistry, device_id: str | None
) -> str:
    """Return the MAIKA serial owned by a device registry entry."""
    if not device_id:
        return ""
    device = device_registry.async_get(device_id)
    if device is None:
        return ""
    for domain, identifier in device.identifiers:
        if domain == DOMAIN and isinstance(identifier, str) and identifier:
            return identifier
    return ""


def _serialize_entry(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    runtime = getattr(entry, "runtime_data", None)
    coordinator = getattr(runtime, "coordinator", None)
    manager = getattr(runtime, "license_manager", None)

    devices: dict[str, Any] = {}
    if coordinator is not None and getattr(coordinator, "data", None):
        for serial, device in (coordinator.data.get("devices") or {}).items():
            if not isinstance(device, dict):
                continue
            payload = {"serial_number": serial}
            for field in _DEVICE_FIELDS:
                if field in device:
                    payload[field] = _json_safe(device[field])
            devices[serial] = payload

    entities: dict[str, list[str]] = {}
    device_entities: dict[str, dict[str, list[str]]] = {}
    entity_keys: dict[str, str] = {}
    registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.disabled_by:
            continue
        entities.setdefault(registry_entry.domain, []).append(registry_entry.entity_id)
        serial = _serial_for_device(device_registry, registry_entry.device_id)
        unique_id = registry_entry.unique_id or ""
        if serial and unique_id.startswith(f"{serial}_"):
            entity_keys[registry_entry.entity_id] = unique_id[len(serial) + 1 :]
        if not serial:
            continue
        grouped = device_entities.setdefault(serial, {})
        grouped.setdefault(registry_entry.domain, []).append(registry_entry.entity_id)
        if serial not in devices:
            device = device_registry.async_get(registry_entry.device_id)
            devices[serial] = {
                "serial_number": serial,
                "name": (device.name_by_user or device.name) if device else "",
            }

    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "options": _public_options(dict(entry.options)),
        "license": _serialize_license(manager),
        "command_history": _json_safe(
            list(getattr(coordinator, "voice_command_history", ()) or ())
        ),
        "chat": _json_safe(list(getattr(coordinator, "chat_log", ()) or ())),
        "devices": devices,
        "entities": {domain: sorted(ids) for domain, ids in entities.items()},
        "device_entities": {
            serial: {domain: sorted(ids) for domain, ids in grouped.items()}
            for serial, grouped in device_entities.items()
        },
        "entity_keys": entity_keys,
    }


def _validate_options(
    hass: HomeAssistant,
    entry: ConfigEntry,
    incoming: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    errors: dict[str, str] = {}
    values = dict(entry.options)

    if CONF_SCAN_INTERVAL in incoming:
        try:
            scan_interval = int(incoming[CONF_SCAN_INTERVAL])
        except (TypeError, ValueError):
            errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
        else:
            if MIN_SCAN_INTERVAL <= scan_interval <= MAX_SCAN_INTERVAL:
                values[CONF_SCAN_INTERVAL] = scan_interval
            else:
                errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"

    for key in (CONF_ENABLE_CLOUD_CAST, CONF_ENABLE_VOICE_COMMAND_SENSOR):
        if key in incoming:
            values[key] = bool(incoming[key])

    if CONF_CLOUD_CAST_BASE_URL in incoming:
        base_url = str(incoming[CONF_CLOUD_CAST_BASE_URL] or "").strip()
        if base_url and not is_valid_http_media_url(base_url):
            errors[CONF_CLOUD_CAST_BASE_URL] = "invalid_cloud_cast_base_url"
        else:
            values[CONF_CLOUD_CAST_BASE_URL] = base_url

    if CONF_VOICE_COMMAND_RULES in incoming:
        rules_text = str(incoming[CONF_VOICE_COMMAND_RULES] or "")
        try:
            parse_voice_command_rules(rules_text)
        except VoiceCommandRulesError:
            errors[CONF_VOICE_COMMAND_RULES] = "invalid_voice_command_rules"
        else:
            values[CONF_VOICE_COMMAND_RULES] = rules_text

    if CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID in incoming:
        entity_id = str(
            incoming[CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID] or ""
        ).strip()
        if entity_id and entity_id not in hass.states.async_entity_ids("media_player"):
            errors[CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID] = (
                "voice_success_audio_media_player_invalid"
            )
        else:
            values[CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID] = entity_id

    if CONF_VOICE_RESPONSE_TTS_ENTITY_ID in incoming:
        entity_id = str(incoming[CONF_VOICE_RESPONSE_TTS_ENTITY_ID] or "").strip()
        if entity_id and entity_id not in hass.states.async_entity_ids("tts"):
            errors[CONF_VOICE_RESPONSE_TTS_ENTITY_ID] = "voice_response_tts_invalid"
        else:
            values[CONF_VOICE_RESPONSE_TTS_ENTITY_ID] = entity_id

    audio_keys = (
        CONF_VOICE_SUCCESS_AUDIO_SOURCE,
        CONF_VOICE_SUCCESS_AUDIO_TIMING,
        CONF_VOICE_SUCCESS_AUDIO_URL,
        CONF_VOICE_SUCCESS_AUDIO_PATH,
    )
    if any(key in incoming for key in audio_keys):
        merged = dict(values)
        for key in audio_keys:
            if key in incoming:
                merged[key] = incoming[key]
        audio_source = resolve_voice_success_audio_source(merged)
        values[CONF_VOICE_SUCCESS_AUDIO_SOURCE] = audio_source
        values[CONF_VOICE_SUCCESS_AUDIO_TIMING] = resolve_voice_success_audio_timing(
            merged
        )
        audio_url = str(merged.get(CONF_VOICE_SUCCESS_AUDIO_URL, "") or "").strip()
        if (
            audio_source == VOICE_SUCCESS_AUDIO_SOURCE_CUSTOM
            and audio_url
            and not is_valid_http_media_url(audio_url)
        ):
            errors[CONF_VOICE_SUCCESS_AUDIO_URL] = "invalid_voice_success_audio_url"
        values[CONF_VOICE_SUCCESS_AUDIO_URL] = audio_url
        audio_path = str(merged.get(CONF_VOICE_SUCCESS_AUDIO_PATH, "") or "").strip()
        normalized_path = normalize_audio_path(audio_path) if audio_path else ""
        if audio_source == VOICE_SUCCESS_AUDIO_SOURCE_LIBRARY and (
            not normalized_path or resolve_audio_file(hass, normalized_path) is None
        ):
            errors[CONF_VOICE_SUCCESS_AUDIO_PATH] = "invalid_voice_success_audio_path"
        values[CONF_VOICE_SUCCESS_AUDIO_PATH] = normalized_path

    return values, errors


class MaikaPanelMixin:
    """Shared helpers for panel views."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    def entry_or_error(
        self, body: dict[str, Any]
    ) -> tuple[ConfigEntry | None, web.Response | None]:
        entry = _entry_by_id(self.hass, body.get("entry_id"))
        if entry is None:
            return None, self.json_message("entry_not_found", 404)
        return entry, None


class MaikaPanelStateView(MaikaPanelMixin, HomeAssistantView):
    """Return the whole MAIKA panel snapshot."""

    url = "/api/maika/panel"
    name = "api:maika:panel"

    async def get(self, request: web.Request) -> web.Response:
        return self.json(
            {
                "entries": [
                    _serialize_entry(self.hass, entry)
                    for entry in _maika_entries(self.hass)
                ],
                "portal_url": LICENSE_PORTAL_URL,
                "default_server_url": DEFAULT_LICENSE_SERVER_URL,
                "scan_interval_bounds": [MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL],
                "audio_source_options": list(VOICE_SUCCESS_AUDIO_SOURCE_OPTIONS),
                "audio_library_path": AUDIO_LIBRARY_PANEL_PATH,
                "audio_library_url_path": AUDIO_LIBRARY_URL_PATH,
                "audio_timing_options": list(VOICE_SUCCESS_AUDIO_TIMING_OPTIONS),
                "voice_actions": voice_action_catalog(),
                "voice_limits": {
                    "rules": MAX_VOICE_COMMAND_RULES,
                    "phrase": MAX_PHRASE_LENGTH,
                },
            }
        )


class MaikaPanelFavoritesView(MaikaPanelMixin, HomeAssistantView):
    """Return the current account's favorite song identifiers."""

    url = "/api/maika/panel/favorites"
    name = "api:maika:panel:favorites"

    async def get(self, request: web.Request) -> web.Response:
        entry = _entry_by_id(self.hass, request.query.get("entry_id"))
        if entry is None:
            return self.json_message("entry_not_found", 404)
        runtime = getattr(entry, "runtime_data", None)
        coordinator = getattr(runtime, "coordinator", None)
        client = getattr(coordinator, "client", None)
        if client is None:
            return self.json_message("entry_not_ready", 503)
        try:
            playlist_id = await client.async_resolve_favorite_playlist_id(force=True)
            songs = (
                await client.async_list_all_playlist_songs(
                    playlist_id, limit=1000, order_by="oldest", max_pages=10
                )
                if playlist_id is not None
                else []
            )
        except MaikaApiError:
            return self.json_message("favorites_unavailable", 502)
        song_ids: list[str] = []
        seen: set[str] = set()
        for song in songs:
            if not isinstance(song, dict):
                continue
            for field in ("songKey", "key", "id", "mediaId", "media_id"):
                value = song.get(field)
                if isinstance(value, bool) or value is None:
                    continue
                text = str(value).strip()
                if text and text not in seen:
                    seen.add(text)
                    song_ids.append(text)
        return self.json({"song_ids": song_ids})


class MaikaPanelLicenseView(MaikaPanelMixin, HomeAssistantView):
    """Activate or replace the license key from the panel."""

    url = "/api/maika/panel/license"
    name = "api:maika:panel:license"

    async def post(self, request: web.Request) -> web.Response:
        body = await _read_json(request)
        entry, error = self.entry_or_error(body)
        if error is not None:
            return error
        try:
            license_key = normalize_license_key(str(body.get("license_key") or ""))
        except ValueError:
            return self.json_message("invalid_license", 400)

        identity = await async_get_installation_identity(self.hass)
        store = MaikaLicenseStore(self.hass)
        record = await store.async_load()
        candidate = (
            str(body.get("server_url") or "").strip()
            or (record.server_url if record else "")
            or DEFAULT_LICENSE_SERVER_URL
        )
        try:
            server_url = normalize_license_server_url(candidate)
        except ValueError:
            return self.json_message("invalid_server_url", 400)

        client = MaikaLicenseClient(self.hass, server_url, identity)
        try:
            response = await client.async_activate(license_key)
        except MaikaLicenseConnectionError:
            return self.json_message("license_server_unavailable", 502)
        except MaikaLicenseResponseError as err:
            return self.json_message(err.code, 400)
        except (MaikaLicenseTokenError, ValueError):
            return self.json_message("invalid_license_response", 400)

        refreshed = MaikaStoredLicense.from_response(
            server_url=server_url,
            installation_hash=identity.installation_hash,
            previous=None,
            response=response,
        )
        await store.async_save(refreshed)
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(entry.entry_id)
        )
        return self.json(
            {
                "status": response.status,
                "activation_code": response.activation_code,
            }
        )


class MaikaPanelOptionsView(MaikaPanelMixin, HomeAssistantView):
    """Update validated integration options from the panel."""

    url = "/api/maika/panel/options"
    name = "api:maika:panel:options"

    async def post(self, request: web.Request) -> web.Response:
        body = await _read_json(request)
        entry, error = self.entry_or_error(body)
        if error is not None:
            return error
        incoming = body.get("options")
        if not isinstance(incoming, dict):
            return self.json_message("invalid_options", 400)
        if "expected_voice_options" in body:
            expected = body["expected_voice_options"]
            if not isinstance(expected, dict) or any(
                key not in _OPTION_KEYS for key in expected
            ):
                return self.json_message("invalid_options", 400)
            current = _public_options(dict(entry.options))
            if any(current.get(key) != value for key, value in expected.items()):
                return self.json_message("voice_rules_changed", 409)
        if "expected_voice_rules" in body and body["expected_voice_rules"] != str(
            entry.options.get(CONF_VOICE_COMMAND_RULES, DEFAULT_VOICE_COMMAND_RULES)
            or ""
        ):
            return self.json_message("voice_rules_changed", 409)
        filtered = {key: incoming[key] for key in _OPTION_KEYS if key in incoming}
        merged, errors = _validate_options(self.hass, entry, filtered)
        if errors:
            return self.json({"errors": errors}, status_code=400)
        self.hass.config_entries.async_update_entry(entry, options=merged)
        return self.json({"updated": True})


class MaikaPanelActionView(MaikaPanelMixin, HomeAssistantView):
    """Run small maintenance actions from the panel."""

    url = "/api/maika/panel/action"
    name = "api:maika:panel:action"

    async def post(self, request: web.Request) -> web.Response:
        body = await _read_json(request)
        entry, error = self.entry_or_error(body)
        if error is not None:
            return error
        action = str(body.get("action") or "")
        if action == "reload":
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(entry.entry_id)
            )
            return self.json({"reloaded": True})
        return self.json_message("invalid_action", 400)


class MaikaPanelChatView(MaikaPanelMixin, HomeAssistantView):
    """Send a typed utterance to one MAIKA speaker from the panel."""

    url = "/api/maika/panel/chat"
    name = "api:maika:panel:chat"

    async def post(self, request: web.Request) -> web.Response:
        body = await _read_json(request)
        entry, error = self.entry_or_error(body)
        if error is not None:
            return error
        runtime = getattr(entry, "runtime_data", None)
        coordinator = getattr(runtime, "coordinator", None)
        if coordinator is None:
            return self.json_message("coordinator_unavailable", 503)
        serial_number = str(body.get("serial_number") or "").strip()
        if not serial_number:
            return self.json_message("unknown_speaker", 400)
        text = str(body.get("text") or "")
        result = await coordinator.async_send_chat(serial_number, text)
        if not result.get("ok"):
            return self.json({"ok": False, "error": result.get("error")}, status=400)
        return self.json(result)


class MaikaPanelRemindersView(MaikaPanelMixin, HomeAssistantView):
    """List, create and delete MAIKA reminders from the panel."""

    url = "/api/maika/panel/reminders"
    name = "api:maika:panel:reminders"

    async def get(self, request: web.Request) -> web.Response:
        entry = _entry_by_id(self.hass, request.query.get("entry_id"))
        if entry is None:
            return self.json_message("entry_not_found", 404)
        serial_number = str(request.query.get("serial_number") or "").strip()
        if serial_number and not _entry_serial(entry, serial_number):
            return self.json_message("unknown_speaker", 400)
        client = _entry_client(entry)
        if client is None:
            return self.json_message("coordinator_unavailable", 503)
        try:
            groups = await client.async_list_reminders()
        except MaikaApiError:
            return self.json_message("reminders_unavailable", 502)
        reminders = _filter_reminders(flatten_reminders(groups), serial_number)
        return self.json({"reminders": reminders})

    async def post(self, request: web.Request) -> web.Response:
        body = await _read_json(request)
        entry, error = self.entry_or_error(body)
        if error is not None:
            return error
        client = _entry_client(entry)
        if client is None:
            return self.json_message("coordinator_unavailable", 503)

        action = str(body.get("action") or "")
        serial_number = str(body.get("serial_number") or "").strip()
        if serial_number and not _entry_serial(entry, serial_number):
            return self.json_message("unknown_speaker", 400)

        if action == "create":
            if not _entry_serial(entry, serial_number):
                return self.json_message("unknown_speaker", 400)
            try:
                payload = build_reminder_payload(
                    event=str(body.get("event") or ""),
                    start_at=str(body.get("start_at") or ""),
                    serial_number=serial_number,
                    frequency=str(body.get("frequency") or "once"),
                    alert_prior=body.get("alert_prior", 0),
                    custom_tts=str(body.get("custom_tts") or ""),
                )
            except ReminderValidationError as err:
                return self.json_message(err.code, 400)
            try:
                await client.async_create_reminder(payload)
            except MaikaApiError:
                return self.json_message("reminders_unavailable", 502)
            return await self._json_after_change(client, serial_number)

        if action in ("update", "toggle"):
            try:
                reminder_id = _parse_reminder_id(body.get("reminder_id"))
                if action == "toggle":
                    enabled = body.get("enabled")
                    if not isinstance(enabled, bool):
                        return self.json_message("invalid_reminder_status", 400)
                    payload = build_reminder_update_payload(
                        status=(
                            REMINDER_STATUS_ENABLED
                            if enabled
                            else REMINDER_STATUS_DISABLED
                        )
                    )
                else:
                    fields = {
                        name: body[name]
                        for name in (
                            "event",
                            "start_at",
                            "frequency",
                            "alert_prior",
                            "custom_tts",
                            "status",
                        )
                        if name in body
                    }
                    payload = build_reminder_update_payload(**fields)
            except ReminderValidationError as err:
                return self.json_message(err.code, 400)
            try:
                await client.async_update_reminder(reminder_id, payload)
            except MaikaApiError:
                return self.json_message("reminders_unavailable", 502)
            return await self._json_after_change(client, serial_number)

        if action == "delete":
            try:
                reminder_ids = _parse_reminder_ids(
                    body.get("reminder_ids")
                    if "reminder_ids" in body
                    else [body.get("reminder_id")]
                )
            except ReminderValidationError as err:
                return self.json_message(err.code, 400)
            try:
                reminder_ids = await _scoped_reminder_ids(
                    client, serial_number, reminder_ids
                )
            except MaikaApiError:
                return self.json_message("reminders_unavailable", 502)
            if not reminder_ids:
                return self.json_message("invalid_reminder_id", 400)
            try:
                await client.async_delete_reminders(reminder_ids)
            except MaikaApiError:
                return self.json_message("reminders_unavailable", 502)
            return await self._json_after_change(client, serial_number)

        if action == "mute":
            try:
                reminder_ids = _parse_reminder_ids(body.get("reminder_ids"))
                mute_days = body.get("mute_days")
                if (
                    not isinstance(mute_days, list)
                    or not mute_days
                    or not all(
                        isinstance(day, str) and day.strip() for day in mute_days
                    )
                ):
                    return self.json_message("invalid_mute_days", 400)
            except ReminderValidationError as err:
                return self.json_message(err.code, 400)
            try:
                reminder_ids = await _scoped_reminder_ids(
                    client, serial_number, reminder_ids
                )
            except MaikaApiError:
                return self.json_message("reminders_unavailable", 502)
            if not reminder_ids:
                return self.json_message("invalid_reminder_id", 400)
            try:
                await client.async_mute_reminders(reminder_ids, mute_days)
            except MaikaApiError:
                return self.json_message("reminders_unavailable", 502)
            return await self._json_after_change(client, serial_number)

        return self.json_message("invalid_action", 400)

    async def _json_after_change(
        self, client: Any, serial_number: str = ""
    ) -> web.Response:
        try:
            groups = await client.async_list_reminders()
        except MaikaApiError:
            return self.json({"ok": True, "reminders": None})
        reminders = _filter_reminders(flatten_reminders(groups), serial_number)
        return self.json({"ok": True, "reminders": reminders})


def _filter_reminders(
    reminders: list[dict[str, Any]], serial_number: str
) -> list[dict[str, Any]]:
    if not serial_number:
        return reminders
    return [
        reminder
        for reminder in reminders
        if serial_number in (reminder.get("devices") or [])
    ]


def _parse_reminder_id(value: Any) -> int:
    if isinstance(value, bool):
        raise ReminderValidationError("invalid_reminder_id")
    try:
        reminder_id = int(value)
    except (TypeError, ValueError) as err:
        raise ReminderValidationError("invalid_reminder_id") from err
    if reminder_id <= 0:
        raise ReminderValidationError("invalid_reminder_id")
    return reminder_id


def _parse_reminder_ids(value: Any) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ReminderValidationError("invalid_reminder_id")
    return list(dict.fromkeys(_parse_reminder_id(item) for item in value))


async def _scoped_reminder_ids(
    client: Any, serial_number: str, reminder_ids: list[int]
) -> list[int]:
    if not serial_number:
        return reminder_ids
    groups = await client.async_list_reminders()
    allowed = {
        reminder["id"]
        for reminder in _filter_reminders(flatten_reminders(groups), serial_number)
    }
    return [reminder_id for reminder_id in reminder_ids if reminder_id in allowed]


def _entry_client(entry: ConfigEntry) -> Any:
    runtime = getattr(entry, "runtime_data", None)
    return getattr(runtime, "client", None)


def _entry_serial(entry: ConfigEntry, serial_number: str) -> bool:
    runtime = getattr(entry, "runtime_data", None)
    coordinator = getattr(runtime, "coordinator", None)
    data = getattr(coordinator, "data", None)
    devices = data.get("devices") if isinstance(data, dict) else None
    if not serial_number or not isinstance(devices, dict):
        return False
    return serial_number in devices


class MaikaPanelAudioLibraryView(MaikaPanelMixin, HomeAssistantView):
    """List the local audio files selectable for voice feedback."""

    url = "/api/maika/panel/audio"
    name = "api:maika:panel:audio"

    async def get(self, request: web.Request) -> web.Response:
        await async_ensure_audio_library_paths(self.hass)
        return self.json(
            {
                "url_path": AUDIO_LIBRARY_URL_PATH,
                "files": list_audio_files(self.hass),
            }
        )


async def _read_json(request: web.Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        # Malformed or missing JSON body: treat as an empty request.
        return {}
    return payload if isinstance(payload, dict) else {}
