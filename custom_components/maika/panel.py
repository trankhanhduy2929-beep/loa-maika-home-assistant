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

from .const import (
    CONF_ENABLE_CLOUD_CAST,
    CONF_ENABLE_VOICE_COMMAND_SENSOR,
    CONF_SCAN_INTERVAL,
    CONF_VOICE_COMMAND_RULES,
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
from .media_url import is_valid_http_media_url
from .voice_rules import VoiceCommandRulesError, parse_voice_command_rules
from .voice_success_audio import (
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
    CONF_ENABLE_VOICE_COMMAND_SENSOR,
    CONF_VOICE_COMMAND_RULES,
    CONF_VOICE_SUCCESS_AUDIO_SOURCE,
    CONF_VOICE_SUCCESS_AUDIO_TIMING,
    CONF_VOICE_SUCCESS_AUDIO_URL,
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

    for view in (
        MaikaPanelStateView(hass),
        MaikaPanelLicenseView(hass),
        MaikaPanelOptionsView(hass),
        MaikaPanelActionView(hass),
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
    """Remove the sidebar panel when the last MAIKA entry unloads."""
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
        CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID: str(
            options.get(CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID, "") or ""
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
    registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.disabled_by:
            continue
        entities.setdefault(registry_entry.domain, []).append(registry_entry.entity_id)
        serial = _serial_for_device(device_registry, registry_entry.device_id)
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
        "devices": devices,
        "entities": {domain: sorted(ids) for domain, ids in entities.items()},
        "device_entities": {
            serial: {domain: sorted(ids) for domain, ids in grouped.items()}
            for serial, grouped in device_entities.items()
        },
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

    audio_keys = (
        CONF_VOICE_SUCCESS_AUDIO_SOURCE,
        CONF_VOICE_SUCCESS_AUDIO_TIMING,
        CONF_VOICE_SUCCESS_AUDIO_URL,
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
                "audio_timing_options": list(VOICE_SUCCESS_AUDIO_TIMING_OPTIONS),
            }
        )


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


async def _read_json(request: web.Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        # Malformed or missing JSON body: treat as an empty request.
        return {}
    return payload if isinstance(payload, dict) else {}
