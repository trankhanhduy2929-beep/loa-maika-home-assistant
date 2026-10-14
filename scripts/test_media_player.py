#!/usr/bin/env python3
"""Exercise playback against HA stubs without a cloud account or real speaker."""

from __future__ import annotations

import ast
import asyncio
import io
import runpy
import unittest
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from enum import IntFlag, StrEnum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]


class Features(IntFlag):
    PAUSE = 1
    SEEK = 2
    VOLUME_SET = 4
    VOLUME_MUTE = 8
    PREVIOUS_TRACK = 16
    NEXT_TRACK = 32
    PLAY_MEDIA = 512
    STOP = 4096
    PLAY = 16384
    BROWSE_MEDIA = 131072


class State(StrEnum):
    PLAYING = "playing"
    PAUSED = "paused"
    IDLE = "idle"


class ValidationError(Exception):
    def __init__(self, **kwargs):
        super().__init__(kwargs.get("translation_key"))
        self.translation_key = kwargs.get("translation_key")


class ApiError(Exception):
    pass


class Clock:
    current = datetime(2026, 10, 14, tzinfo=UTC)

    @classmethod
    def now(cls, timezone):
        return cls.current.astimezone(timezone)


class CommandEntity:
    def __init__(self, coordinator, serial_number, entity_key):
        self.coordinator = coordinator
        self.serial_number = serial_number
        self.hass = coordinator.hass
        self.updates = 0

    @property
    def device(self):
        return self.coordinator.data["devices"][self.serial_number]

    def _handle_coordinator_update(self):
        self.updates += 1


def load_player():
    """Run the actual entity code using the repository validator's AST pattern."""
    path = ROOT / "custom_components/maika/media_player.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.ImportFrom)
            and (node.level > 0 or (node.module or "").startswith("homeassistant"))
        )
    ]
    namespace = {
        "__name__": "maika_media_player_test",
        "MaikaCommandEntity": CommandEntity,
        "MediaPlayerEntity": type("MediaPlayerEntity", (), {}),
        "MediaPlayerEntityFeature": Features,
        "MediaPlayerState": State,
        "MediaPlayerDeviceClass": SimpleNamespace(SPEAKER="speaker"),
        "MediaPlayerEnqueue": SimpleNamespace(PLAY="play", REPLACE="replace"),
        "ServiceValidationError": ValidationError,
        "HomeAssistantError": ValidationError,
        "ConfigEntryAuthFailed": type("ConfigEntryAuthFailed", (Exception,), {}),
        "MaikaApiError": ApiError,
        "CONF_ENABLE_CLOUD_CAST": "enable_experimental_cloud_cast",
        "CONF_CLOUD_CAST_BASE_URL": "cloud_cast_base_url",
        "DOMAIN": "maika",
        "callback": lambda function: function,
        "dt_util": SimpleNamespace(UTC=UTC),
        "is_valid_http_media_url": runpy.run_path(
            str(ROOT / "custom_components/maika/media_url.py")
        )["is_valid_http_media_url"],
    }
    exec(compile(tree, str(path), "exec"), namespace)
    namespace["datetime"] = Clock
    return namespace["MaikaMediaPlayer"]


class PlaybackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Clock.current = datetime(2026, 10, 14, tzinfo=UTC)
        self.tasks = []
        self.client = SimpleNamespace(
            async_playback_command=AsyncMock(),
            async_cast_media=AsyncMock(),
        )
        self.coordinator = SimpleNamespace(
            entry=SimpleNamespace(options={"enable_experimental_cloud_cast": True}),
            data={
                "devices": {
                    "speaker-one": {
                        "volume": 50,
                        "online": True,
                        "current_playback": {
                            "status": "playing",
                            "payload": {
                                "offsetInMilliseconds": 42000,
                                "durationInMilliseconds": 215000,
                                "playbackAttributes": {
                                    "url": "https://example.org/song.mp3",
                                    "title": "Song",
                                },
                            },
                        },
                    },
                    "speaker-two": {"volume": 70},
                }
            },
            client=self.client,
            async_refresh_live=AsyncMock(),
            async_update_device_data=self.update_device,
            hass=SimpleNamespace(async_create_task=self.create_task),
        )
        self.player = load_player()(self.coordinator, "speaker-one")

    async def asyncTearDown(self):
        await asyncio.gather(*self.tasks)

    def create_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        return task

    def update_device(self, serial, changes):
        device = self.coordinator.data["devices"][serial]
        self.coordinator.data["devices"][serial] = {**device, **changes}
        self.player._handle_coordinator_update()

    def advance(self, seconds):
        Clock.current += timedelta(seconds=seconds)

    def report(self, *, offset=42000, status="playing", title="Song"):
        current = deepcopy(self.player._current_playback)
        current["status"] = status
        current["payload"]["offsetInMilliseconds"] = offset
        current["payload"]["playbackAttributes"]["title"] = title
        self.update_device("speaker-one", {"current_playback": current})

    async def test_stop_pauses_without_fake_idle_reset_or_volume_change(self):
        before = deepcopy(self.coordinator.data)
        self.advance(8)
        await self.player.async_media_stop()
        self.client.async_playback_command.assert_awaited_once_with(
            "speaker-one", "PauseCommandIssued"
        )
        self.assertEqual(self.player.state, State.PAUSED)
        self.assertEqual(self.player.media_position, 50)
        self.assertEqual(self.player.media_duration, 215)
        self.assertEqual(self.player.volume_level, 0.5)
        self.assertEqual(self.player.media_title, "Song")
        self.assertEqual(
            self.coordinator.data["devices"]["speaker-two"],
            before["devices"]["speaker-two"],
        )
        self.assertEqual(len(self.tasks), 1)

    async def test_stop_failure_leaves_state_and_position_untouched(self):
        before = deepcopy(self.coordinator.data)
        timestamp = self.player.media_position_updated_at
        self.client.async_playback_command.side_effect = ApiError("offline")
        with self.assertRaises(ApiError):
            await self.player.async_media_stop()
        self.assertEqual(self.coordinator.data, before)
        self.assertEqual(self.player.media_position_updated_at, timestamp)
        self.assertFalse(self.tasks)

    async def test_stop_available_without_cloud_cast(self):
        self.coordinator.entry.options = {}
        player = load_player()(self.coordinator, "speaker-one")
        self.assertTrue(player._attr_supported_features & Features.STOP)
        self.assertFalse(player._attr_supported_features & Features.SEEK)

    async def test_pause_resume_does_not_count_time_spent_paused(self):
        self.advance(8)
        await self.player.async_media_pause()
        self.advance(600)
        await self.player.async_media_play()
        self.assertEqual(self.player.media_position, 50)
        self.assertEqual(self.player.media_position_updated_at, Clock.current)
        self.advance(2)
        await self.player.async_media_pause()
        self.assertEqual(self.player.media_position, 52)

    async def test_live_offset_refreshes_timestamp_not_volume_updates(self):
        self.advance(10)
        self.report(offset=52000)
        timestamp = Clock.current
        self.assertEqual(self.player.media_position_updated_at, timestamp)
        self.advance(20)
        self.update_device("speaker-one", {"volume": 80})
        self.assertEqual(self.player.media_position_updated_at, timestamp)
        self.assertEqual(self.player.updates, 2)

    async def test_same_offset_new_state_or_track_refreshes_timestamp(self):
        for update in ({"status": "paused"}, {"status": "resume"}, {"title": "New"}):
            self.advance(60)
            self.report(**update)
            self.assertEqual(self.player.media_position_updated_at, Clock.current)

    async def test_seek_keeps_duration_and_clamps_both_ends(self):
        for position, expected in ((-5, 0), (1000, 215000), (90.5, 90500)):
            self.advance(10)
            await self.player.async_media_seek(position)
            self.assertEqual(
                self.client.async_cast_media.call_args.kwargs["offset_milliseconds"],
                expected,
            )
            self.assertEqual(self.player.media_position, expected / 1000)
            self.assertEqual(self.player.media_duration, 215)
            self.assertEqual(self.player.media_position_updated_at, Clock.current)

    async def test_invalid_seek_does_not_send_a_command(self):
        before = deepcopy(self.coordinator.data)
        for position in (float("nan"), float("inf"), -float("inf"), "bad", None):
            with self.subTest(position=position):
                with self.assertRaises(ValidationError) as error:
                    await self.player.async_media_seek(position)
                self.assertEqual(
                    error.exception.translation_key, "cloud_cast_invalid_seek_position"
                )
        self.client.async_cast_media.assert_not_awaited()
        self.assertEqual(self.coordinator.data, before)

    async def test_seek_uses_audio_card_type_not_a_mime_type(self):
        self.player.device["current_playback"]["payload"]["playbackAttributes"][
            "mediaType"
        ] = "audio/mpeg"
        await self.player.async_media_seek(30)
        self.assertEqual(
            self.client.async_cast_media.call_args.kwargs.get("media_type", "audio"),
            "audio",
        )

    async def test_seek_failure_does_not_change_playback(self):
        before = deepcopy(self.coordinator.data)
        self.client.async_cast_media.side_effect = ApiError("failed")
        with self.assertRaises(ValidationError):
            await self.player.async_media_seek(80)
        self.assertEqual(self.coordinator.data, before)

    async def test_seek_never_restarts_an_old_cast_after_track_changes(self):
        self.player._last_cast_media = {
            "url": "https://example.org/old.mp3",
            "title": "Old cast",
            "attributes": {"title": "Old cast"},
        }
        for attributes in (
            {"songKey": "native-track", "title": "Old cast"},
            {"title": "Another track"},
            {},
        ):
            self.player.device["current_playback"]["payload"]["playbackAttributes"] = (
                attributes
            )
            with self.assertRaises(ValidationError) as error:
                await self.player.async_media_seek(30)
            self.assertEqual(
                error.exception.translation_key, "cloud_cast_seek_unavailable"
            )
        self.client.async_cast_media.assert_not_awaited()

    async def test_seek_can_reuse_matching_cast_metadata(self):
        self.player._last_cast_media = {
            "url": "https://example.org/song.mp3",
            "title": "Song",
            "attributes": {"title": "Song"},
        }
        self.player.device["current_playback"]["payload"]["playbackAttributes"] = {
            "title": "Song"
        }
        await self.player.async_media_seek(30)
        self.assertEqual(
            self.client.async_cast_media.call_args.args,
            ("speaker-one", "https://example.org/song.mp3"),
        )

    async def test_invalid_reported_timing_is_not_exposed(self):
        for value in (float("nan"), float("inf"), "bad", None):
            self.report(offset=value)
            self.assertIsNone(self.player.media_position)
            self.assertIsNone(self.player.media_position_updated_at)
            self.player.device["current_playback"]["payload"][
                "durationInMilliseconds"
            ] = value
            self.assertIsNone(self.player.media_duration)


def validate_media_player():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PlaybackTests)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(suite)
    return [] if result.wasSuccessful() else [output.getvalue()]


if __name__ == "__main__":
    unittest.main()
