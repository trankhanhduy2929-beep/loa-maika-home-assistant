"""Persistent storage for recognized MAIKA voice-command history.

The recognized-command list used to live only in memory, so it disappeared on
every Home Assistant reload or restart. Persisting it through the Home
Assistant storage helper keeps the panel history across restarts without
touching config entries.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_STORAGE_VERSION = 1


def _storage_key(entry_id: str) -> str:
    return f"maika.command_history.{entry_id}"


class MaikaVoiceCommandHistoryStore:
    """Load and save the recent recognized-command list for one entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, _STORAGE_VERSION, _storage_key(entry_id))

    async def async_load(self) -> list[dict[str, Any]]:
        """Return the stored history, newest first, or an empty list."""
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return []
        history = data.get("history")
        if not isinstance(history, list):
            return []
        return [item for item in history if isinstance(item, dict)]

    async def async_save(self, history: list[dict[str, Any]]) -> None:
        """Persist the current history list."""
        await self._store.async_save({"history": list(history)})
