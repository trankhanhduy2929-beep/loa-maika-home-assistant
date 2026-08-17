"""Diagnostics support for MAIKA."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from . import MaikaConfigEntry
from .const import (
    CONF_CLIENT_ID,
    CONF_PASSWORD,
    CONF_PHONE_NUMBER,
    CONF_SESSION_ID,
    CONF_VOICE_COMMAND_RULES,
    CONF_VOICE_SUCCESS_AUDIO_URL,
)

_LEGACY_CONF_VOICE_SUCCESS_MESSAGE = "voice_success_message"

TO_REDACT = {
    "Authorization",
    CONF_CLIENT_ID,
    CONF_PASSWORD,
    CONF_PHONE_NUMBER,
    CONF_SESSION_ID,
    CONF_VOICE_SUCCESS_AUDIO_URL,
    CONF_VOICE_COMMAND_RULES,
    _LEGACY_CONF_VOICE_SUCCESS_MESSAGE,
    "access_token",
    "activationCode",
    "activation_code",
    "address",
    "authorization",
    "avatarURL",
    "calling_name",
    "city",
    "country",
    "current_playback",
    "deviceId",
    "device_id",
    "email",
    "first_name",
    "full_name",
    "last_name",
    "last_voice_command",
    "lease_token",
    "license_id",
    "license_key",
    "license_token",
    "installation_hash",
    "latest_playlist",
    "local_media_info",
    "meta_data",
    "name",
    "occupation",
    "organization_code",
    "persona",
    "phone_number",
    "rawSpeech",
    "refresh_token",
    "room",
    "sample_text",
    "settings",
    "sip_auth_user",
    "sip_id",
    "sip_password",
    "ssid",
    "tssv_config",
    "user_id",
    "user_profile",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MaikaConfigEntry
) -> dict[str, Any]:
    """Return redacted integration diagnostics."""
    return async_redact_data(
        {
            "entry_data": dict(entry.data),
            "entry_options": dict(entry.options),
            "coordinator_data": entry.runtime_data.coordinator.data,
            "stream_connected": entry.runtime_data.client.listener_connected,
            "license_status": entry.runtime_data.license_manager.state,
        },
        TO_REDACT,
    )
