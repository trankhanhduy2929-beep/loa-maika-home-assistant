#!/usr/bin/env python3
"""Exercise MAIKA reminder services without Home Assistant installed."""

from __future__ import annotations

import ast
import io
import sys
import types
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "custom_components/maika"


class ServiceValidationError(Exception):
    """Stub for Home Assistant service validation errors."""

    def __init__(
        self,
        *,
        translation_domain: str | None = None,
        translation_key: str | None = None,
        translation_placeholders: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(translation_key or translation_domain or "validation")
        self.translation_domain = translation_domain
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders


class HomeAssistantError(Exception):
    """Stub for Home Assistant integration errors."""

    def __init__(
        self,
        *,
        translation_domain: str | None = None,
        translation_key: str | None = None,
    ) -> None:
        super().__init__(translation_key or translation_domain or "error")
        self.translation_domain = translation_domain
        self.translation_key = translation_key


class MaikaApiError(Exception):
    """Stub for MAIKA cloud errors."""


class VolMarker:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs


def load_reminders() -> dict[str, Any]:
    path = DIRECTORY / "reminders.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        node
        for node in tree.body
        if not (isinstance(node, ast.ImportFrom) and node.level > 0)
    ]
    namespace: dict[str, Any] = {
        "__name__": "maika_service_reminders",
        "APP_EXECUTOR": "vn_south",
        "APP_TIMEZONE": "Asia/Ho_Chi_Minh",
    }
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


def load_services(reminders: dict[str, Any], registry: Any) -> dict[str, Any]:
    path = DIRECTORY / "services.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        node
        for node in tree.body
        if not (
            (
                isinstance(node, ast.ImportFrom)
                and (
                    node.level > 0
                    or (node.module or "").startswith("homeassistant")
                    or node.module == "voluptuous"
                )
            )
            or (
                isinstance(node, ast.Import)
                and any(alias.name == "voluptuous" for alias in node.names)
            )
        )
    ]
    cv = types.SimpleNamespace(
        string=str,
        ensure_list=lambda value: value if isinstance(value, list) else [value],
        positive_int=int,
        boolean=bool,
    )
    device_registry = types.SimpleNamespace(async_get=lambda hass: registry)
    namespace: dict[str, Any] = {
        "__name__": "maika_services_test",
        "vol": types.SimpleNamespace(
            Optional=VolMarker,
            Required=VolMarker,
            All=VolMarker,
            Coerce=VolMarker,
            Range=VolMarker,
            In=VolMarker,
            Length=VolMarker,
            Schema=lambda schema: schema,
            Invalid=ValueError,
        ),
        "ConfigEntry": object,
        "ATTR_DEVICE_ID": "device_id",
        "ServiceCall": object,
        "ServiceValidationError": ServiceValidationError,
        "HomeAssistantError": HomeAssistantError,
        "cv": cv,
        "dr": device_registry,
        "DOMAIN": "maika",
        "MaikaApiClient": type,
        "MaikaApiError": MaikaApiError,
    }
    for name in (
        "REMINDER_FREQUENCIES",
        "REMINDER_STATUS_DISABLED",
        "REMINDER_STATUS_ENABLED",
        "ReminderValidationError",
        "build_reminder_payload",
        "build_reminder_update_payload",
        "flatten_reminders",
    ):
        namespace[name] = reminders[name]
    module = types.ModuleType("maika_services_test")
    module.__dict__.update(namespace)
    sys.modules[module.__name__] = module
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module.__dict__


class FakeConfigEntries:
    def __init__(self, entries: list[Any]) -> None:
        self.entries = entries

    def async_entries(self, domain: str) -> list[Any]:
        return [entry for entry in self.entries if entry.domain == domain]

    def async_get_entry(self, entry_id: str) -> Any:
        return next(
            (entry for entry in self.entries if entry.entry_id == entry_id), None
        )


class FakeHass:
    def __init__(self, entries: list[Any]) -> None:
        self.config_entries = FakeConfigEntries(entries)
        self.services = types.SimpleNamespace(has_service=lambda *args: False)


class FakeDeviceRegistry:
    def __init__(self, devices: dict[str, Any]) -> None:
        self.devices = devices

    def async_get(self, device_id: str) -> Any:
        return self.devices.get(device_id)


def make_entry(
    entry_id: str = "entry-1",
    serials: tuple[str, ...] = ("SN1",),
    client: Any | None = None,
) -> Any:
    client = client or types.SimpleNamespace()
    devices = {serial: {"serial_number": serial} for serial in serials}
    return types.SimpleNamespace(
        entry_id=entry_id,
        domain="maika",
        runtime_data=types.SimpleNamespace(
            client=client,
            coordinator=types.SimpleNamespace(data={"devices": devices}),
        ),
    )


def reminder_group(reminder_id: int, serial: str = "SN1") -> dict[str, Any]:
    return {
        "listReminders": [
            {
                "id": reminder_id,
                "event": "Họp",
                "devices": [serial],
                "start_date": "2030-01-02",
                "start_time": "08:00:00",
                "frequency": "once",
                "status": 1,
            }
        ]
    }


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.reminders = load_reminders()
        self.registry = FakeDeviceRegistry({})
        self.module = load_services(self.reminders, self.registry)

    def future(self, minutes: int = 30) -> str:
        return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()

    async def test_create_reminder_resolves_speaker_and_builds_payload(self):
        client = types.SimpleNamespace(async_create_reminder=AsyncMock(return_value={}))
        hass = FakeHass([make_entry(client=client)])
        call = types.SimpleNamespace(
            data={
                "serial_number": "SN1",
                "event": "Họp",
                "start_at": self.future(),
                "frequency": "daily",
                "alert_prior": 15,
            }
        )
        await self.module["_async_create_reminder"](hass, call)
        payload = client.async_create_reminder.await_args.args[0]
        self.assertEqual(payload["event"], "Họp")
        self.assertEqual(payload["alert_prior"], 900)
        self.assertEqual(payload["devices"], ["SN1"])

    async def test_update_scopes_reminder_to_speaker(self):
        client = types.SimpleNamespace(
            async_list_reminders=AsyncMock(return_value=[reminder_group(7)]),
            async_update_reminder=AsyncMock(return_value={}),
        )
        hass = FakeHass([make_entry(client=client)])
        call = types.SimpleNamespace(
            data={"serial_number": "SN1", "reminder_id": 7, "event": "Họp mới"}
        )
        await self.module["_async_update_reminder"](hass, call)
        client.async_update_reminder.assert_awaited_once_with(
            7, {"executor": "vn_south", "event": "Họp mới"}
        )

    async def test_update_rejects_reminder_from_another_speaker(self):
        client = types.SimpleNamespace(
            async_list_reminders=AsyncMock(return_value=[reminder_group(7, "OTHER")]),
            async_update_reminder=AsyncMock(return_value={}),
        )
        hass = FakeHass([make_entry(client=client)])
        call = types.SimpleNamespace(
            data={"serial_number": "SN1", "reminder_id": 7, "event": "Họp mới"}
        )
        with self.assertRaises(ServiceValidationError) as error:
            await self.module["_async_update_reminder"](hass, call)
        self.assertEqual(
            error.exception.translation_key, "maika_service_reminder_not_found"
        )
        client.async_update_reminder.assert_not_awaited()

    async def test_toggle_delete_and_mute_use_scoped_ids(self):
        client = types.SimpleNamespace(
            async_list_reminders=AsyncMock(
                return_value=[reminder_group(7), reminder_group(8)]
            ),
            async_update_reminder=AsyncMock(return_value={}),
            async_delete_reminders=AsyncMock(return_value={}),
            async_mute_reminders=AsyncMock(return_value={}),
        )
        hass = FakeHass([make_entry(client=client)])
        await self.module["_async_set_reminder_enabled"](
            hass,
            types.SimpleNamespace(
                data={"serial_number": "SN1", "reminder_id": 7, "enabled": False}
            ),
        )
        client.async_update_reminder.assert_awaited_once_with(
            7, {"executor": "vn_south", "status": 2}
        )
        await self.module["_async_delete_reminders"](
            hass,
            types.SimpleNamespace(
                data={"serial_number": "SN1", "reminder_ids": [7, 8]}
            ),
        )
        client.async_delete_reminders.assert_awaited_once_with([7, 8])
        await self.module["_async_mute_reminders"](
            hass,
            types.SimpleNamespace(
                data={
                    "serial_number": "SN1",
                    "reminder_ids": [7],
                    "mute_days": ["2030-01-04"],
                }
            ),
        )
        client.async_mute_reminders.assert_awaited_once_with([7], ["2030-01-04"])

    async def test_device_target_resolves_serial_and_entry(self):
        entry = make_entry()
        hass = FakeHass([entry])
        self.registry.devices["device-1"] = types.SimpleNamespace(
            identifiers={("maika", "SN1")},
            config_entries={"entry-1"},
        )
        speaker = self.module["_resolve_speaker"](hass, {"device_id": ["device-1"]})
        self.assertEqual(speaker.serial_number, "SN1")
        self.assertIs(speaker.entry, entry)

    async def test_ambiguous_speaker_requires_entry_or_serial(self):
        hass = FakeHass([make_entry("entry-1"), make_entry("entry-2")])
        with self.assertRaises(ServiceValidationError) as error:
            self.module["_resolve_speaker"](hass, {})
        self.assertEqual(
            error.exception.translation_key, "maika_service_device_multiple"
        )

    async def test_invalid_mute_date_is_rejected(self):
        client = types.SimpleNamespace(
            async_list_reminders=AsyncMock(return_value=[reminder_group(7)]),
            async_mute_reminders=AsyncMock(return_value={}),
        )
        hass = FakeHass([make_entry(client=client)])
        with self.assertRaises(ServiceValidationError) as error:
            await self.module["_async_mute_reminders"](
                hass,
                types.SimpleNamespace(
                    data={
                        "serial_number": "SN1",
                        "reminder_ids": [7],
                        "mute_days": ["next monday"],
                    }
                ),
            )
        self.assertEqual(
            error.exception.translation_key, "maika_service_invalid_mute_days"
        )
        client.async_mute_reminders.assert_not_awaited()

    async def test_add_current_song_uses_queue_when_playback_lacks_key(self):
        client = types.SimpleNamespace(
            favorite_playlist_id=42,
            async_resolve_favorite_playlist_id=AsyncMock(return_value=42),
            async_add_song_to_playlist=AsyncMock(return_value={}),
        )
        entry = make_entry(client=client)
        device = entry.runtime_data.coordinator.data["devices"]["SN1"]
        device["current_playback"] = {
            "payload": {
                "playbackAttributes": {
                    "title": "Bài từ queue",
                    "artist": "Ca sĩ queue",
                }
            }
        }
        device["latest_playlist"] = {
            "songs": [
                {
                    "songKey": "queue-key",
                    "song": "Bài từ queue",
                    "artist": "Ca sĩ queue",
                    "url": "https://cdn/queue.mp3",
                },
                {
                    "songKey": "other-key",
                    "song": "Bài khác",
                    "artist": "Ca sĩ khác",
                    "url": "https://cdn/other.mp3",
                },
            ]
        }
        await self.module["_async_add_current_to_favorites"](
            FakeHass([entry]), types.SimpleNamespace(data={"serial_number": "SN1"})
        )
        client.async_add_song_to_playlist.assert_awaited_once_with(
            42,
            singer="Ca sĩ queue",
            song_id="queue-key",
            song_name="Bài từ queue",
            song_url="https://cdn/queue.mp3",
            lyric="",
            image_url="",
        )

    async def test_add_current_song_uses_favorite_playlist(self):
        client = types.SimpleNamespace(
            favorite_playlist_id=42,
            async_resolve_favorite_playlist_id=AsyncMock(return_value=42),
            async_add_song_to_playlist=AsyncMock(return_value={}),
        )
        entry = make_entry(client=client)
        entry.runtime_data.coordinator.data["devices"]["SN1"]["current_playback"] = {
            "payload": {
                "playbackAttributes": {
                    "key": "song-key",
                    "name": "Bài hát",
                    "artist": "Ca sĩ",
                    "url": "https://cdn/song.mp3",
                    "lyric": "https://cdn/lyric.lrc",
                    "image": {"url": "https://cdn/cover.jpg"},
                }
            }
        }
        await self.module["_async_add_current_to_favorites"](
            FakeHass([entry]), types.SimpleNamespace(data={"serial_number": "SN1"})
        )
        client.async_resolve_favorite_playlist_id.assert_awaited_once_with(force=True)
        client.async_add_song_to_playlist.assert_awaited_once_with(
            42,
            singer="Ca sĩ",
            song_id="song-key",
            song_name="Bài hát",
            song_url="https://cdn/song.mp3",
            lyric="https://cdn/lyric.lrc",
            image_url="https://cdn/cover.jpg",
        )

    async def test_add_current_song_rejects_missing_track(self):
        client = types.SimpleNamespace(
            favorite_playlist_id=42,
            async_resolve_favorite_playlist_id=AsyncMock(return_value=42),
            async_add_song_to_playlist=AsyncMock(return_value={}),
        )
        with self.assertRaises(ServiceValidationError) as error:
            await self.module["_async_add_current_to_favorites"](
                FakeHass([make_entry(client=client)]),
                types.SimpleNamespace(data={"serial_number": "SN1"}),
            )
        self.assertEqual(error.exception.translation_key, "maika_favorite_no_track")
        client.async_add_song_to_playlist.assert_not_awaited()

    async def test_services_register_once(self):
        registered: list[str] = []
        hass = types.SimpleNamespace(
            services=types.SimpleNamespace(
                has_service=lambda domain, name: name in registered,
                async_register=lambda domain, name, handler, schema=None: (
                    registered.append(name)
                ),
            )
        )
        await self.module["async_setup_services"](hass)
        await self.module["async_setup_services"](hass)
        self.assertEqual(
            registered,
            [
                "create_reminder",
                "update_reminder",
                "set_reminder_enabled",
                "delete_reminders",
                "mute_reminders",
                "add_current_to_favorites",
            ],
        )


def validate_services() -> list[str]:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ServiceTests)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(suite)
    return [] if result.wasSuccessful() else [output.getvalue()]


if __name__ == "__main__":
    unittest.main()
