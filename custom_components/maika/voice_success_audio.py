"""Resolve the audio source used after a successful Home Assistant rule."""

from __future__ import annotations

from collections.abc import Mapping

from .const import (
    CONF_VOICE_SUCCESS_AUDIO_SOURCE,
    CONF_VOICE_SUCCESS_AUDIO_URL,
    DEFAULT_VOICE_SUCCESS_AUDIO_SOURCE,
    VOICE_SUCCESS_AUDIO_SOURCE_BUNDLED,
    VOICE_SUCCESS_AUDIO_SOURCE_CUSTOM,
    VOICE_SUCCESS_AUDIO_SOURCE_OPTIONS,
)
from .license_config import BUNDLED_VOICE_SUCCESS_AUDIO_URL


def resolve_voice_success_audio_source(options: Mapping[str, object]) -> str:
    """Resolve the source while retaining pre-1.7 custom URL entries."""
    source = str(options.get(CONF_VOICE_SUCCESS_AUDIO_SOURCE, "")).strip().lower()
    if source in VOICE_SUCCESS_AUDIO_SOURCE_OPTIONS:
        return source
    if str(options.get(CONF_VOICE_SUCCESS_AUDIO_URL, "")).strip():
        return VOICE_SUCCESS_AUDIO_SOURCE_CUSTOM
    return DEFAULT_VOICE_SUCCESS_AUDIO_SOURCE


def resolve_voice_success_audio_url(options: Mapping[str, object]) -> str:
    """Return the configured URL, preserving the pre-1.7 URL behavior."""
    source = resolve_voice_success_audio_source(options)
    custom_url = str(options.get(CONF_VOICE_SUCCESS_AUDIO_URL, "")).strip()

    if source == VOICE_SUCCESS_AUDIO_SOURCE_BUNDLED:
        return BUNDLED_VOICE_SUCCESS_AUDIO_URL.strip()
    if source == VOICE_SUCCESS_AUDIO_SOURCE_CUSTOM:
        return custom_url
    return ""


def has_voice_success_audio(options: Mapping[str, object]) -> bool:
    """Return whether a source has been selected and resolved to a URL."""
    return bool(resolve_voice_success_audio_url(options))
