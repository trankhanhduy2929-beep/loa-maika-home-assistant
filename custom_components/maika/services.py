"""Home Assistant services for MAIKA reminders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import MaikaApiClient, MaikaApiError
from .const import DOMAIN
from .reminders import (
    REMINDER_FREQUENCIES,
    REMINDER_STATUS_DISABLED,
    REMINDER_STATUS_ENABLED,
    ReminderValidationError,
    build_reminder_payload,
    build_reminder_update_payload,
    flatten_reminders,
)

ATTR_ENTRY_ID = "entry_id"
ATTR_SERIAL_NUMBER = "serial_number"
ATTR_REMINDER_ID = "reminder_id"
ATTR_REMINDER_IDS = "reminder_ids"
ATTR_ENABLED = "enabled"
ATTR_EVENT = "event"
ATTR_START_AT = "start_at"
ATTR_FREQUENCY = "frequency"
ATTR_ALERT_PRIOR = "alert_prior"
ATTR_CUSTOM_TTS = "custom_tts"
ATTR_STATUS = "status"
ATTR_MUTE_DAYS = "mute_days"

SERVICE_CREATE_REMINDER = "create_reminder"
SERVICE_UPDATE_REMINDER = "update_reminder"
SERVICE_SET_REMINDER_ENABLED = "set_reminder_enabled"
SERVICE_DELETE_REMINDERS = "delete_reminders"
SERVICE_MUTE_REMINDERS = "mute_reminders"
SERVICE_ADD_CURRENT_TO_FAVORITES = "add_current_to_favorites"

_TARGET_FIELDS = {
    vol.Optional(ATTR_ENTRY_ID): cv.string,
    vol.Optional(ATTR_SERIAL_NUMBER): cv.string,
    vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
}

CREATE_REMINDER_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELDS,
        vol.Required(ATTR_EVENT): cv.string,
        vol.Required(ATTR_START_AT): cv.string,
        vol.Optional(ATTR_FREQUENCY, default="once"): vol.In(REMINDER_FREQUENCIES),
        vol.Optional(ATTR_ALERT_PRIOR, default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=1440)
        ),
        vol.Optional(ATTR_CUSTOM_TTS): cv.string,
    }
)

UPDATE_REMINDER_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELDS,
        vol.Required(ATTR_REMINDER_ID): cv.positive_int,
        vol.Optional(ATTR_EVENT): cv.string,
        vol.Optional(ATTR_START_AT): cv.string,
        vol.Optional(ATTR_FREQUENCY): vol.In(REMINDER_FREQUENCIES),
        vol.Optional(ATTR_ALERT_PRIOR): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=1440)
        ),
        vol.Optional(ATTR_CUSTOM_TTS): cv.string,
        vol.Optional(ATTR_STATUS): vol.All(
            vol.Coerce(int),
            vol.In([REMINDER_STATUS_ENABLED, REMINDER_STATUS_DISABLED]),
        ),
    }
)

SET_REMINDER_ENABLED_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELDS,
        vol.Required(ATTR_REMINDER_ID): cv.positive_int,
        vol.Required(ATTR_ENABLED): cv.boolean,
    }
)

DELETE_REMINDERS_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELDS,
        vol.Required(ATTR_REMINDER_IDS): vol.All(
            cv.ensure_list, [cv.positive_int], vol.Length(min=1)
        ),
    }
)

MUTE_REMINDERS_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELDS,
        vol.Required(ATTR_REMINDER_IDS): vol.All(
            cv.ensure_list, [cv.positive_int], vol.Length(min=1)
        ),
        vol.Required(ATTR_MUTE_DAYS): vol.All(
            cv.ensure_list, [cv.string], vol.Length(min=1)
        ),
    }
)

ADD_CURRENT_TO_FAVORITES_SCHEMA = vol.Schema({**_TARGET_FIELDS})


@dataclass(frozen=True, slots=True)
class _Speaker:
    """The loaded account and cloud client for one speaker."""

    entry: ConfigEntry
    client: MaikaApiClient
    serial_number: str


def _loaded_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    return [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if getattr(getattr(entry, "runtime_data", None), "client", None) is not None
    ]


def _entry_serial(entry: ConfigEntry, serial_number: str) -> bool:
    coordinator = getattr(entry.runtime_data, "coordinator", None)
    devices = (getattr(coordinator, "data", None) or {}).get("devices") or {}
    return serial_number in devices


def _loaded_entry(hass: HomeAssistant, entry_id: str) -> ConfigEntry:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="maika_service_entry_not_found",
        )
    if getattr(getattr(entry, "runtime_data", None), "client", None) is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="maika_service_entry_not_found",
        )
    return entry


def _device_serial(device: dr.DeviceEntry) -> str:
    for domain, identifier in device.identifiers:
        if domain == DOMAIN and isinstance(identifier, str) and identifier:
            return identifier
    return ""


def _first_string(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
    return ""


def _playback_attributes(entry: ConfigEntry, serial_number: str) -> dict[str, Any]:
    coordinator = getattr(entry.runtime_data, "coordinator", None)
    devices = (getattr(coordinator, "data", None) or {}).get("devices") or {}
    device = devices.get(serial_number)
    if not isinstance(device, dict):
        return {}
    current = device.get("current_playback")
    if not isinstance(current, dict):
        return {}
    payload = current.get("payload")
    if not isinstance(payload, dict):
        return {}
    attributes = payload.get("playbackAttributes")
    return attributes if isinstance(attributes, dict) else {}


def _favorite_song_payload(attributes: dict[str, Any]) -> dict[str, Any]:
    image = attributes.get("image")
    image_url = _first_string(
        attributes.get("imageURL"),
        attributes.get("image_url"),
        image.get("url") if isinstance(image, dict) else None,
    )
    song_id = _first_string(
        attributes.get("key"),
        attributes.get("songKey"),
        attributes.get("id"),
        attributes.get("mediaId"),
        attributes.get("media_id"),
    )
    return {
        "singer": _first_string(attributes.get("artist"), attributes.get("narrator")),
        "song_id": song_id,
        "song_name": _first_string(
            attributes.get("name"), attributes.get("song"), attributes.get("title")
        )
        or song_id,
        "song_url": _first_string(attributes.get("url")),
        "lyric": _first_string(attributes.get("lyric")),
        "image_url": image_url,
    }


def _resolve_speaker(hass: HomeAssistant, data: dict[str, Any]) -> _Speaker:
    device_ids = data.get(ATTR_DEVICE_ID) or []
    if len(device_ids) > 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="maika_service_device_multiple",
        )

    requested_serial = str(data.get(ATTR_SERIAL_NUMBER) or "").strip()
    requested_entry = str(data.get(ATTR_ENTRY_ID) or "").strip()
    entry: ConfigEntry | None = None

    if device_ids:
        device = dr.async_get(hass).async_get(device_ids[0])
        if device is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_service_device_unknown",
            )
        device_serial = _device_serial(device)
        if requested_serial and requested_serial != device_serial:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_service_device_unknown",
            )
        requested_serial = device_serial
        if not requested_serial:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_service_device_unknown",
            )
        candidates = [
            _loaded_entry(hass, entry_id)
            for entry_id in device.config_entries
            if entry_id in {item.entry_id for item in _loaded_entries(hass)}
        ]
        if requested_entry:
            candidates = [
                candidate
                for candidate in candidates
                if candidate.entry_id == requested_entry
            ]
        if len(candidates) != 1:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_service_device_unknown",
            )
        entry = candidates[0]

    if entry is None and requested_entry:
        entry = _loaded_entry(hass, requested_entry)

    if entry is None:
        candidates = [
            candidate
            for candidate in _loaded_entries(hass)
            if not requested_serial or _entry_serial(candidate, requested_serial)
        ]
        serials = {
            serial
            for candidate in candidates
            for serial in (
                (getattr(candidate.runtime_data.coordinator, "data", None) or {})
                .get("devices", {})
                .keys()
            )
            if not requested_serial or serial == requested_serial
        }
        if len(candidates) == 1 and len(serials) == 1:
            entry = candidates[0]
            requested_serial = next(iter(serials))
        elif len(candidates) > 1 or len(serials) > 1:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_service_device_multiple",
            )

    if entry is not None and not requested_serial:
        serials = list(
            (getattr(entry.runtime_data.coordinator, "data", None) or {})
            .get("devices", {})
            .keys()
        )
        if len(serials) == 1:
            requested_serial = serials[0]
    if entry is None or not requested_serial:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="maika_service_device_required",
        )
    if not _entry_serial(entry, requested_serial):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="maika_service_device_unknown",
        )
    runtime = entry.runtime_data
    return _Speaker(entry, runtime.client, requested_serial)


async def _scoped_reminder_ids(speaker: _Speaker, reminder_ids: list[int]) -> list[int]:
    try:
        groups = await speaker.client.async_list_reminders()
    except MaikaApiError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="maika_service_reminder_failed",
        ) from err
    available = {
        reminder["id"]: reminder
        for reminder in flatten_reminders(groups)
        if speaker.serial_number in (reminder.get("devices") or [])
    }
    if any(reminder_id not in available for reminder_id in reminder_ids):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="maika_service_reminder_not_found",
        )
    return list(dict.fromkeys(reminder_ids))


def _parse_mute_days(values: list[str]) -> list[str]:
    days: list[str] = []
    for value in values:
        try:
            parsed = date.fromisoformat(value.strip())
        except ValueError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_service_invalid_mute_days",
            ) from err
        days.append(parsed.isoformat())
    return list(dict.fromkeys(days))


async def _async_create_reminder(hass: HomeAssistant, call: ServiceCall) -> None:
    speaker = _resolve_speaker(hass, call.data)
    try:
        payload = build_reminder_payload(
            event=call.data[ATTR_EVENT],
            start_at=call.data[ATTR_START_AT],
            serial_number=speaker.serial_number,
            frequency=call.data[ATTR_FREQUENCY],
            alert_prior=call.data[ATTR_ALERT_PRIOR],
            custom_tts=call.data.get(ATTR_CUSTOM_TTS),
        )
    except ReminderValidationError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="maika_service_invalid_reminder",
            translation_placeholders={"reason": err.code},
        ) from err
    try:
        await speaker.client.async_create_reminder(payload)
    except MaikaApiError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="maika_service_reminder_failed",
        ) from err


async def _async_update_reminder(hass: HomeAssistant, call: ServiceCall) -> None:
    speaker = _resolve_speaker(hass, call.data)
    reminder_id = int(call.data[ATTR_REMINDER_ID])
    await _scoped_reminder_ids(speaker, [reminder_id])
    fields = {
        name: call.data[name]
        for name in (
            ATTR_EVENT,
            ATTR_START_AT,
            ATTR_FREQUENCY,
            ATTR_ALERT_PRIOR,
            ATTR_CUSTOM_TTS,
            ATTR_STATUS,
        )
        if name in call.data
    }
    try:
        payload = build_reminder_update_payload(**fields)
    except ReminderValidationError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="maika_service_invalid_reminder",
            translation_placeholders={"reason": err.code},
        ) from err
    try:
        await speaker.client.async_update_reminder(reminder_id, payload)
    except MaikaApiError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="maika_service_reminder_failed",
        ) from err


async def _async_set_reminder_enabled(hass: HomeAssistant, call: ServiceCall) -> None:
    speaker = _resolve_speaker(hass, call.data)
    reminder_id = int(call.data[ATTR_REMINDER_ID])
    await _scoped_reminder_ids(speaker, [reminder_id])
    payload = build_reminder_update_payload(
        status=(
            REMINDER_STATUS_ENABLED
            if call.data[ATTR_ENABLED]
            else REMINDER_STATUS_DISABLED
        )
    )
    try:
        await speaker.client.async_update_reminder(reminder_id, payload)
    except MaikaApiError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="maika_service_reminder_failed",
        ) from err


async def _async_delete_reminders(hass: HomeAssistant, call: ServiceCall) -> None:
    speaker = _resolve_speaker(hass, call.data)
    reminder_ids = await _scoped_reminder_ids(
        speaker, [int(value) for value in call.data[ATTR_REMINDER_IDS]]
    )
    try:
        await speaker.client.async_delete_reminders(reminder_ids)
    except MaikaApiError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="maika_service_reminder_failed",
        ) from err


async def _async_mute_reminders(hass: HomeAssistant, call: ServiceCall) -> None:
    speaker = _resolve_speaker(hass, call.data)
    reminder_ids = await _scoped_reminder_ids(
        speaker, [int(value) for value in call.data[ATTR_REMINDER_IDS]]
    )
    mute_days = _parse_mute_days(call.data[ATTR_MUTE_DAYS])
    try:
        await speaker.client.async_mute_reminders(reminder_ids, mute_days)
    except MaikaApiError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="maika_service_reminder_failed",
        ) from err


async def _async_add_current_to_favorites(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    speaker = _resolve_speaker(hass, call.data)
    payload = _favorite_song_payload(
        _playback_attributes(speaker.entry, speaker.serial_number)
    )
    if not payload["song_id"] or not payload["song_url"]:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="maika_favorite_no_track",
        )
    try:
        favorite_playlist_id = await speaker.client.async_resolve_favorite_playlist_id()
        if not favorite_playlist_id:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_favorites_unavailable",
            )
        await speaker.client.async_add_song_to_playlist(favorite_playlist_id, **payload)
    except ServiceValidationError:
        raise
    except MaikaApiError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="maika_favorite_failed",
        ) from err


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register MAIKA services once per Home Assistant instance."""
    services = (
        (
            SERVICE_CREATE_REMINDER,
            CREATE_REMINDER_SCHEMA,
            _async_create_reminder,
        ),
        (
            SERVICE_UPDATE_REMINDER,
            UPDATE_REMINDER_SCHEMA,
            _async_update_reminder,
        ),
        (
            SERVICE_SET_REMINDER_ENABLED,
            SET_REMINDER_ENABLED_SCHEMA,
            _async_set_reminder_enabled,
        ),
        (
            SERVICE_DELETE_REMINDERS,
            DELETE_REMINDERS_SCHEMA,
            _async_delete_reminders,
        ),
        (
            SERVICE_MUTE_REMINDERS,
            MUTE_REMINDERS_SCHEMA,
            _async_mute_reminders,
        ),
        (
            SERVICE_ADD_CURRENT_TO_FAVORITES,
            ADD_CURRENT_TO_FAVORITES_SCHEMA,
            _async_add_current_to_favorites,
        ),
    )
    for service, schema, handler in services:
        if not hass.services.has_service(DOMAIN, service):
            hass.services.async_register(DOMAIN, service, handler, schema=schema)
