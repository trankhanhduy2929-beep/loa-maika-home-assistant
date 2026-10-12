"""Locate and serve local audio files for MAIKA voice feedback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import (
    MAX_VOICE_SUCCESS_AUDIO_LIBRARY_DEPTH,
    MAX_VOICE_SUCCESS_AUDIO_LIBRARY_FILES,
    VOICE_SUCCESS_AUDIO_LIBRARY_DIRS,
    VOICE_SUCCESS_AUDIO_LIBRARY_EXTENSIONS,
)

AUDIO_LIBRARY_URL_PATH = "/maika_media"
AUDIO_LIBRARY_PANEL_PATH = "maika/panel/audio"
_REGISTERED_KEY = "maika_audio_library_paths"


def normalize_audio_path(value: Any) -> str:
    """Return a safe relative path inside the allowed audio directories."""
    text = str(value or "").strip().replace("\\", "/").lstrip("/")
    if not text:
        return ""
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return ""
    if parts[0] not in VOICE_SUCCESS_AUDIO_LIBRARY_DIRS:
        return ""
    if Path(parts[-1]).suffix.lower() not in VOICE_SUCCESS_AUDIO_LIBRARY_EXTENSIONS:
        return ""
    if len(parts) - 1 > MAX_VOICE_SUCCESS_AUDIO_LIBRARY_DEPTH:
        return ""
    return "/".join(parts)


def resolve_audio_file(hass: HomeAssistant, value: Any) -> Path | None:
    """Return the existing file for a stored library path, if any."""
    relative = normalize_audio_path(value)
    if not relative:
        return None
    root, *rest = relative.split("/")
    candidate = Path(hass.config.path(root)).joinpath(*rest)
    try:
        return candidate if candidate.is_file() else None
    except OSError:
        return None


def list_audio_files(hass: HomeAssistant) -> list[dict[str, str]]:
    """List selectable audio files inside the allowed directories."""
    files: list[dict[str, str]] = []
    for root in VOICE_SUCCESS_AUDIO_LIBRARY_DIRS:
        base = Path(hass.config.path(root))
        try:
            if not base.is_dir():
                continue
            entries = base.rglob("*")
            for path in entries:
                if len(files) >= MAX_VOICE_SUCCESS_AUDIO_LIBRARY_FILES:
                    break
                try:
                    if not path.is_file():
                        continue
                except OSError:
                    continue
                if path.suffix.lower() not in VOICE_SUCCESS_AUDIO_LIBRARY_EXTENSIONS:
                    continue
                relative = path.relative_to(base)
                if len(relative.parts) > MAX_VOICE_SUCCESS_AUDIO_LIBRARY_DEPTH:
                    continue
                files.append(
                    {
                        "path": f"{root}/{relative.as_posix()}",
                        "name": relative.as_posix(),
                        "root": root,
                    }
                )
        except OSError:
            continue
    files.sort(key=lambda item: (item["root"], item["name"].lower()))
    return files


def audio_static_paths(hass: HomeAssistant) -> dict[str, str]:
    """Return the static URL prefixes for the directories that exist."""
    return {
        f"{AUDIO_LIBRARY_URL_PATH}/{root}": str(Path(hass.config.path(root)))
        for root in VOICE_SUCCESS_AUDIO_LIBRARY_DIRS
        if Path(hass.config.path(root)).is_dir()
    }


async def async_ensure_audio_library_paths(hass: HomeAssistant) -> None:
    """Register static paths for the audio folders that exist on disk."""
    http = getattr(hass, "http", None)
    if http is None:
        return
    registered = hass.data.setdefault(_REGISTERED_KEY, set())
    pending = {
        url_path: directory
        for url_path, directory in audio_static_paths(hass).items()
        if url_path not in registered
    }
    if not pending:
        return
    try:
        await http.async_register_static_paths(
            [
                StaticPathConfig(url_path, directory, False)
                for url_path, directory in pending.items()
            ]
        )
    except Exception:  # pragma: no cover - defensive only
        return
    registered.update(pending)


def library_audio_url(hass: HomeAssistant, value: Any) -> str:
    """Return the absolute URL the MAIKA cloud can fetch for a library file."""
    relative = normalize_audio_path(value)
    if not relative or resolve_audio_file(hass, relative) is None:
        return ""
    try:
        base = get_url(hass, prefer_external=True)
    except NoURLAvailableError:
        return ""
    return f"{str(base).rstrip('/')}{AUDIO_LIBRARY_URL_PATH}/{relative}"
