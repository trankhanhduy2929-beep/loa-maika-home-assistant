#!/usr/bin/env python3
"""Exercise playback against HA stubs without a cloud account or real speaker."""

from __future__ import annotations

import ast
import asyncio
import hashlib
import io
import json
import runpy
import unittest
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from enum import IntFlag, StrEnum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call
from urllib.parse import quote, unquote

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
    SEARCH_MEDIA = 4194304


class State(StrEnum):
    PLAYING = "playing"
    PAUSED = "paused"
    IDLE = "idle"


class HomeError(Exception):
    def __init__(self, **kwargs):
        super().__init__(kwargs.get("translation_key"))
        self.translation_key = kwargs.get("translation_key")
        self.translation_domain = kwargs.get("translation_domain")


class ValidationError(HomeError):
    pass


class BrowseError(HomeError):
    pass


class SearchError(Exception):
    pass


class SearchMedia:
    def __init__(self, *, result):
        self.result = result


class BrowseMedia:
    def __init__(
        self,
        *,
        media_class,
        media_content_id,
        media_content_type,
        title,
        can_play,
        can_expand,
        children=None,
        children_media_class=None,
        thumbnail=None,
    ):
        self.media_class = media_class
        self.media_content_id = media_content_id
        self.media_content_type = media_content_type
        self.title = title
        self.can_play = can_play
        self.can_expand = can_expand
        self.children = children
        self.children_media_class = children_media_class
        self.thumbnail = thumbnail


class ApiError(Exception):
    pass


class ContentStoreStub:
    def __init__(self, client):
        self.client = client
        self.async_channels = AsyncMock(return_value=[])
        self.async_categories = AsyncMock(return_value=[])
        self.async_highlights = AsyncMock(return_value=[])
        self.async_channel_categories = AsyncMock(return_value=[])
        self.async_channel_medias = AsyncMock(return_value=[])
        self.async_episodes = AsyncMock(return_value=[])


class NhacCuaTuiStub:
    def __init__(self, client):
        self.client = client
        self.async_feed = AsyncMock(return_value=[])
        self.async_charts = AsyncMock(return_value=[])
        self.async_chart_tracks = AsyncMock(return_value=[])
        self.async_search = AsyncMock(return_value=[])
        self.async_song = AsyncMock(return_value={})


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
        return self.coordinator.data["devices"].get(self.serial_number, {})

    @property
    def available(self):
        return (
            self.coordinator.last_update_success
            and self.serial_number in self.coordinator.data["devices"]
            and bool(self.device.get("online"))
        )

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
        "BrowseMedia": BrowseMedia,
        "BrowseError": BrowseError,
        "SearchError": SearchError,
        "SearchMedia": SearchMedia,
        "MediaClass": SimpleNamespace(
            DIRECTORY="directory",
            PLAYLIST="playlist",
            TRACK="track",
            CHANNEL="channel",
            GENRE="genre",
            ALBUM="album",
            MUSIC="music",
        ),
        "MaikaContentStore": ContentStoreStub,
        "MaikaNhacCuaTui": NhacCuaTuiStub,
        "parse_nct_song_key": runpy.run_path(
            str(ROOT / "custom_components/maika/nhaccuatui.py")
        )["parse_nct_song_key"],
        "media_source": SimpleNamespace(
            is_media_source_id=lambda value: (
                isinstance(value, str) and value.startswith("media-source://")
            ),
            async_browse_media=AsyncMock(),
            async_resolve_media=AsyncMock(),
        ),
        "async_process_play_media_url": Mock(side_effect=lambda hass, url: url),
        "cast_ready_url": Mock(side_effect=lambda hass, url, base: url),
        "ServiceValidationError": ValidationError,
        "HomeAssistantError": HomeError,
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
            async_set_volume=AsyncMock(),
            favorite_playlist_id=None,
            async_resolve_favorite_playlist_id=AsyncMock(return_value=None),
            async_list_all_playlist_songs=AsyncMock(return_value=[]),
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
            last_update_success=True,
            async_refresh_live=AsyncMock(return_value=True),
            async_schedule_playback_refresh=Mock(),
            async_update_device_data=self.update_device,
            hass=SimpleNamespace(async_create_task=self.create_task),
        )
        self.player = load_player()(self.coordinator, "speaker-one")
        self.player.entity_id = "media_player.maika_one"
        self.media_source = self.player.async_play_media.__globals__["media_source"]

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

    def assert_jump_and_resume(self, serial, key):
        self.assertEqual(
            self.client.async_playback_command.await_args_list,
            [
                call(serial, "JumpCommandIssued", song_key=key),
                call(serial, "ResumeCommandIssued"),
            ],
        )

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
        self.coordinator.async_schedule_playback_refresh.assert_called_once_with(
            "speaker-one"
        )
        self.assertFalse(self.tasks)

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
        with self.assertRaises(HomeError) as error:
            await self.player.async_media_seek(80)
        self.assertNotIsInstance(error.exception, ValidationError)
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

    def native_playlist(self, songs=None):
        playlist = {
            "title": "Nhạc trên loa",
            "listKey": "playlist-one",
            "source": "native",
            "songs": songs
            if songs is not None
            else [
                {"songKey": "key-one", "song": "Cùng tên", "artist": "Ca sĩ A"},
                {"songKey": "key-two", "song": "Cùng tên", "artist": "Ca sĩ A"},
            ],
        }
        self.player.device["latest_playlist"] = playlist
        return playlist

    async def browse_playlist(self, player=None):
        return await (player or self.player).async_browse_media(
            "maika_playlist", "maika_playlist"
        )

    def assert_no_playback(self):
        self.client.async_playback_command.assert_not_awaited()
        self.client.async_cast_media.assert_not_awaited()
        self.coordinator.async_schedule_playback_refresh.assert_not_called()
        self.assertFalse(self.tasks)

    async def assert_invalid_selection(
        self,
        media_id,
        translation_key,
        expected_exception: type[HomeError] = ValidationError,
    ):
        with self.assertRaises(expected_exception) as error:
            await self.player.async_play_media("maika_song", media_id)
        self.assertIs(type(error.exception), expected_exception)
        self.assertEqual(error.exception.translation_key, translation_key)
        self.assertEqual(error.exception.translation_domain, "maika")
        self.assert_no_playback()

    async def test_native_features_and_root_do_not_require_cloud_cast(self):
        self.coordinator.entry.options = {}
        player = type(self.player)(self.coordinator, "speaker-one")
        self.native_playlist()
        self.assertTrue(player._attr_supported_features & Features.BROWSE_MEDIA)
        self.assertTrue(player._attr_supported_features & Features.PLAY_MEDIA)
        self.assertTrue(player._attr_supported_features & Features.SEARCH_MEDIA)
        self.assertFalse(player._attr_supported_features & Features.SEEK)
        result = await player.async_browse_media()
        self.assertEqual(result.media_content_type, "maika_root")
        self.assertEqual(result.media_content_id, "maika_root")
        playlist = result.children[0]
        self.assertEqual(playlist.media_content_type, "maika_playlist")
        self.assertEqual(playlist.media_content_id, "maika_playlist")
        self.assertEqual(len(playlist.children), 2)
        self.assertEqual(
            [child.media_content_id for child in result.children],
            ["maika_playlist", "maika_nct_root", "maika_cs_root"],
        )
        self.media_source.async_browse_media.assert_not_awaited()
        self.coordinator.async_refresh_live.assert_awaited_once_with(
            "speaker-one", required_fields=("latest_playlist",)
        )
        await player.async_play_media(
            "maika_song", playlist.children[1].media_content_id
        )
        self.assert_jump_and_resume("speaker-one", "key-two")
        self.coordinator.async_schedule_playback_refresh.assert_called_once_with(
            "speaker-one"
        )
        self.client.async_cast_media.assert_not_awaited()

    async def test_search_media_returns_nct_tracks(self):
        self.player._nct.async_search.return_value = [
            {
                "key": "Track0009",
                "title": "Tìm thấy",
                "artist": "Sơn Tùng",
                "cover": "https://cdn.example.test/search.jpg",
            }
        ]
        result = await self.player.async_search_media(
            SimpleNamespace(search_query="  Sơn Tùng  ")
        )
        self.player._nct.async_search.assert_awaited_once_with("Sơn Tùng")
        self.assertEqual(len(result.result), 1)
        node = result.result[0]
        self.assertEqual(node.media_content_type, "maika_nct_track")
        self.assertEqual(node.media_content_id, "Track0009")
        self.assertEqual(node.title, "Tìm thấy — Sơn Tùng")
        self.assertTrue(node.can_play)

    async def test_blank_search_returns_empty_without_request(self):
        result = await self.player.async_search_media(
            SimpleNamespace(search_query="   ")
        )
        self.assertEqual(result.result, [])
        self.player._nct.async_search.assert_not_awaited()

    async def test_root_combines_native_playlist_with_existing_ha_sources(self):
        self.native_playlist()
        sources = BrowseMedia(
            media_class="directory",
            media_content_type="music",
            media_content_id="media-source://media_source",
            title="My media",
            can_play=False,
            can_expand=True,
            children=[],
        )
        self.media_source.async_browse_media.return_value = sources
        result = await self.player.async_browse_media()
        self.assertEqual(result.media_content_type, "maika_root")
        self.assertEqual(result.media_content_id, "maika_root")
        self.assertFalse(result.can_play)
        self.assertTrue(result.can_expand)
        self.assertEqual(result.children[0].media_content_id, "maika_playlist")
        self.assertIs(result.children[1], sources)
        self.media_source.async_browse_media.assert_awaited_once()
        args, kwargs = self.media_source.async_browse_media.call_args
        self.assertEqual(args, (self.player.hass, None))
        content_filter = kwargs["content_filter"]
        self.assertTrue(
            content_filter(SimpleNamespace(media_content_type="audio/mpeg"))
        )
        self.assertFalse(
            content_filter(SimpleNamespace(media_content_type="video/mp4"))
        )
        explicit_root = await self.player.async_browse_media("maika_root", "maika_root")
        self.assertEqual(explicit_root.children[0].media_content_id, "maika_playlist")
        self.assert_no_playback()

    async def test_existing_media_source_browse_requests_are_preserved(self):
        for cloud_cast_enabled in (False, True):
            with self.subTest(cloud_cast_enabled=cloud_cast_enabled):
                self.player._cloud_cast_enabled = cloud_cast_enabled
                expected = object()
                self.media_source.async_browse_media.return_value = expected
                result = await self.player.async_browse_media(
                    "music", "media-source://media_source/local"
                )
                self.assertIs(result, expected)
                self.assertEqual(
                    self.media_source.async_browse_media.call_args.args,
                    (self.player.hass, "media-source://media_source/local"),
                )
        self.coordinator.async_refresh_live.assert_not_awaited()
        self.assert_no_playback()

    async def test_queue_browse_waits_for_latest_native_songs_without_leaking_urls(
        self,
    ):
        self.native_playlist([])

        async def refresh(serial, *, required_fields):
            self.assertEqual(serial, "speaker-one")
            self.native_playlist(
                [
                    {
                        "songKey": "native-key",
                        "song": "Tên bài thật",
                        "title": "Wrong title",
                        "artist": "Ca sĩ",
                        "url": "https://example.org/music?signature=private",
                        "imageURL": "https://example.org/art?signature=private",
                    }
                ]
            )

        self.coordinator.async_refresh_live.side_effect = refresh
        result = await self.browse_playlist()
        self.coordinator.async_refresh_live.assert_awaited_once_with(
            "speaker-one", required_fields=("latest_playlist",)
        )
        self.assertEqual(result.title, "Nhạc trên loa")
        self.assertEqual(result.media_class, "playlist")
        self.assertEqual(result.children_media_class, "track")
        self.assertFalse(result.can_play)
        self.assertTrue(result.can_expand)
        child = result.children[0]
        self.assertEqual(child.title, "Tên bài thật — Ca sĩ")
        self.assertEqual(child.media_content_type, "maika_song")
        self.assertEqual(child.media_class, "track")
        self.assertTrue(child.can_play)
        self.assertFalse(child.can_expand)
        self.assertIsNone(child.thumbnail)
        self.assertNotIn("private", repr(vars(child)))
        self.assertNotIn("https", repr(vars(child)))
        self.assertNotIn("Wrong title", repr(vars(child)))
        self.assert_no_playback()

    async def test_absent_empty_and_malformed_playlists_never_synthesize_queue(self):
        self.player.device["history"] = [{"songKey": "history", "song": "Old song"}]
        for playlist in (
            None,
            [],
            "bad",
            {},
            {"songs": []},
            {"songs": None},
            {"songs": "bad"},
            {"songs": [None, 0, "bad"]},
            {"items": [{"songKey": "not-a-song"}]},
            {"url": "https://example.org/not-a-queue.mp3"},
        ):
            with self.subTest(playlist=playlist):
                self.player.device["latest_playlist"] = playlist
                result = await self.browse_playlist()
                self.assertEqual(result.title, "Danh sách trên loa MAIKA")
                self.assertEqual(result.children, [])
        self.player.device["latest_playlist"] = {"title": "Danh sách rỗng", "songs": []}
        result = await self.browse_playlist()
        self.assertEqual(result.title, "Danh sách rỗng")
        self.assertEqual(result.children, [])
        self.assert_no_playback()

    async def test_invalid_song_keys_remain_visible_but_not_playable(self):
        invalid_keys = (
            None,
            "",
            "   ",
            3,
            True,
            {},
            [],
            "a\nkey",
            "\x7f",
            "\ud800",
            "x" * 513,
            "á" * 257,
        )
        self.native_playlist(
            [{"songKey": key, "song": "Unselectable"} for key in invalid_keys]
            + [{"key": "wrong-field", "id": "wrong-id", "song": "Missing songKey"}]
        )
        result = await self.browse_playlist()
        self.assertEqual(len(result.children), len(invalid_keys) + 1)
        for child in result.children:
            self.assertFalse(child.can_play)
            self.assertFalse(child.can_expand)
            self.assertEqual(child.media_content_type, "maika_song")
            self.assertEqual(child.media_content_id, "")
        self.assert_no_playback()

    async def test_duplicate_titles_use_distinct_keys_and_duplicate_keys_share_id(self):
        self.native_playlist(
            [
                {"songKey": "key-one", "song": "Same", "artist": "Artist"},
                {"songKey": "key-two", "song": "Same", "artist": "Artist"},
                {"songKey": "key-one", "song": "Same", "artist": "Artist"},
            ]
        )
        result = await self.browse_playlist()
        one, two, repeated_one = result.children
        self.assertEqual(one.title, two.title)
        self.assertNotEqual(one.media_content_id, two.media_content_id)
        self.assertEqual(one.media_content_id, repeated_one.media_content_id)
        self.assertTrue(all(child.can_play for child in result.children))
        await self.player.async_play_media("maika_song", repeated_one.media_content_id)
        self.assert_jump_and_resume("speaker-one", "key-one")

    async def test_revision_tracks_speaker_list_source_and_order_not_metadata(self):
        playlist = self.native_playlist()
        original = (await self.browse_playlist()).children[0].media_content_id
        playlist["title"] = "New label"
        playlist["songs"][0].update(
            {
                "song": "New title",
                "artist": "New artist",
                "url": "https://example.org/new",
            }
        )
        self.assertEqual(
            (await self.browse_playlist()).children[0].media_content_id, original
        )
        same_queue = deepcopy(playlist)
        for field, value in (("listKey", "other-list"), ("source", "other-source")):
            with self.subTest(field=field):
                self.player.device["latest_playlist"] = {**same_queue, field: value}
                self.assertNotEqual(
                    (await self.browse_playlist()).children[0].media_content_id,
                    original,
                )
        self.player.device["latest_playlist"] = {
            **same_queue,
            "songs": list(reversed(same_queue["songs"])),
        }
        self.assertNotEqual(
            (await self.browse_playlist()).children[1].media_content_id, original
        )
        self.coordinator.data["devices"]["speaker-two"].update(
            {"online": True, "latest_playlist": same_queue}
        )
        other = type(self.player)(self.coordinator, "speaker-two")
        self.assertNotEqual(
            (await self.browse_playlist(other)).children[0].media_content_id, original
        )
        self.assert_no_playback()

    async def test_ids_are_deterministic_canonical_bounded_and_preserve_exact_key(self):
        key = "  Bài/%:x?&=+#  "
        self.native_playlist([{"songKey": key, "song": "Unicode"}])
        child = (await self.browse_playlist()).children[0]
        self.assertEqual(
            (await self.browse_playlist()).children[0].media_content_id,
            child.media_content_id,
        )
        prefix, revision, encoded = child.media_content_id.split(":")
        self.assertEqual(prefix, "maika")
        self.assertRegex(revision, r"^[0-9a-f]{64}$")
        expected_revision = hashlib.sha256(
            json.dumps(
                ["speaker-one", "playlist-one", "native", [key]],
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(revision, expected_revision)
        self.assertEqual(encoded, quote(key, safe=""))
        self.assertEqual(unquote(encoded), key)
        self.assertLessEqual(len(child.media_content_id), 1607)
        await self.player.async_play_media("maika_song", child.media_content_id)
        self.assert_jump_and_resume("speaker-one", key)
        self.native_playlist([{"songKey": "á" * 256, "song": "Bound"}])
        longest = (await self.browse_playlist()).children[0]
        self.assertTrue(longest.can_play)
        self.assertEqual(len(longest.media_content_id), 1607)

    async def test_jump_sends_once_and_waits_for_reported_metadata_and_state(self):
        self.native_playlist()
        child = (await self.browse_playlist()).children[1]
        self.report(status="paused")
        self.coordinator.async_refresh_live.reset_mock()
        before = deepcopy(self.coordinator.data)
        timestamp = self.player.media_position_updated_at
        self.advance(5)
        await self.player.async_play_media(
            "maika_song",
            child.media_content_id,
            extra={"metadata": {"title": "Injected"}, "song_key": "arbitrary"},
            command="Reset",
        )
        self.assert_jump_and_resume("speaker-one", "key-two")
        self.coordinator.async_refresh_live.assert_awaited_once_with(
            "speaker-one", required_fields=("latest_playlist",)
        )
        self.coordinator.async_schedule_playback_refresh.assert_called_once_with(
            "speaker-one"
        )
        self.assertNotEqual(self.coordinator.data, before)
        self.assertEqual(self.player.media_title, "Cùng tên")
        self.assertEqual(self.player.media_artist, "Ca sĩ A")
        self.assertEqual(self.player.state, State.PLAYING)
        self.assertEqual(self.player.media_position, 0)
        self.assertNotEqual(self.player.media_position_updated_at, timestamp)
        self.client.async_cast_media.assert_not_awaited()
        self.assertFalse(self.tasks)
        current = deepcopy(self.player._current_playback)
        current["payload"]["playbackAttributes"] = {
            "key": "key-two",
            "song": "New song",
        }
        self.update_device("speaker-one", {"current_playback": current})
        self.assertEqual(self.player.media_title, "New song")
        self.assertEqual(
            self.player.extra_state_attributes["maika_queue_item_id"],
            child.media_content_id,
        )

    async def test_jump_failure_keeps_metadata_state_and_position_untouched(self):
        self.native_playlist()
        child = (await self.browse_playlist()).children[0]
        before = deepcopy(self.coordinator.data)
        timestamp = self.player.media_position_updated_at
        self.client.async_playback_command.side_effect = ApiError("cloud failure")
        with self.assertRaises(HomeError) as error:
            await self.player.async_play_media("maika_song", child.media_content_id)
        self.assertNotIsInstance(error.exception, ValidationError)
        self.assertEqual(error.exception.translation_key, "maika_queue_jump_failed")
        self.client.async_playback_command.assert_awaited_once_with(
            "speaker-one", "JumpCommandIssued", song_key="key-one"
        )
        self.assertEqual(self.coordinator.data, before)
        self.assertEqual(self.player.media_position_updated_at, timestamp)
        self.coordinator.async_schedule_playback_refresh.assert_not_called()
        self.client.async_cast_media.assert_not_awaited()

    async def test_malformed_ids_raw_urls_and_commands_never_reach_api(self):
        self.native_playlist()
        valid_id = (await self.browse_playlist()).children[0].media_content_id
        prefix = valid_id.rsplit(":", 1)[0] + ":"
        invalid_ids = (
            None,
            3,
            {},
            "",
            "key-one",
            "0",
            "JumpCommandIssued",
            "Reset",
            "https://example.org/song.mp3",
            "media-source://media_source/local/song.mp3",
            "maika:key-one",
            "maika:" + "g" * 64 + ":key-one",
            valid_id + ":extra",
            valid_id + "\n",
            prefix + "%",
            prefix + "%GG",
            prefix + "%FF",
            prefix + "%00",
            prefix + "%ED%A0%80",
            prefix + "a/b",
            prefix + "key%2Done",
            prefix + "%20",
            prefix + "x" * 513,
            prefix + "%61" * 513,
            valid_id.replace("maika:", "MAIKA:"),
        )
        self.coordinator.async_refresh_live.reset_mock()
        for media_id in invalid_ids:
            with self.subTest(media_id=media_id):
                await self.assert_invalid_selection(
                    media_id, "maika_queue_invalid_selection"
                )
        self.coordinator.async_refresh_live.assert_not_awaited()

    async def test_unknown_key_and_lookalike_keys_require_exact_membership(self):
        self.native_playlist()
        item_id = (await self.browse_playlist()).children[0].media_content_id
        prefix = item_id.rsplit(":", 1)[0] + ":"
        for key in (
            "missing",
            "key-one ",
            "KEY-ONE",
            "0",
            "Reset",
            "https://example.org/song.mp3?signature=mock",
        ):
            with self.subTest(key=key):
                await self.assert_invalid_selection(
                    prefix + quote(key, safe=""), "maika_queue_invalid_selection"
                )
        self.player.device["latest_playlist"] = {"songs": []}
        empty_revision = self.player._queue_revision(
            self.player.device["latest_playlist"]
        )
        await self.assert_invalid_selection(
            f"maika:{empty_revision}:key-one", "maika_queue_invalid_selection"
        )

    async def test_stale_queue_ids_are_rejected_after_refresh(self):
        for change in ("list", "source", "order", "removed", "empty", "missing"):
            with self.subTest(change=change):
                self.coordinator.async_refresh_live.side_effect = None
                playlist = self.native_playlist()
                item_id = (await self.browse_playlist()).children[0].media_content_id

                async def refresh(
                    serial, change=change, playlist=playlist, *, required_fields
                ):
                    if change == "list":
                        playlist["listKey"] = "new-list"
                    elif change == "source":
                        playlist["source"] = "new-source"
                    elif change == "order":
                        playlist["songs"].reverse()
                    elif change == "removed":
                        playlist["songs"].pop(0)
                    elif change == "empty":
                        playlist["songs"] = []
                    else:
                        self.player.device.pop("latest_playlist")

                self.coordinator.async_refresh_live.side_effect = refresh
                await self.assert_invalid_selection(item_id, "maika_queue_changed")

    async def test_other_speaker_ids_cannot_select_even_identical_queue_keys(self):
        playlist = self.native_playlist()
        own_id = (await self.browse_playlist()).children[0].media_content_id
        self.coordinator.data["devices"]["speaker-two"].update(
            {"online": True, "latest_playlist": deepcopy(playlist)}
        )
        other = type(self.player)(self.coordinator, "speaker-two")
        other_id = (await self.browse_playlist(other)).children[0].media_content_id
        self.assertNotEqual(other_id, own_id)
        await self.assert_invalid_selection(other_id, "maika_queue_changed")
        prefix = own_id.rsplit(":", 1)[0] + ":"
        self.coordinator.data["devices"]["speaker-two"]["latest_playlist"][
            "songs"
        ].append({"songKey": "only-other-speaker", "song": "Other"})
        await self.assert_invalid_selection(
            prefix + "only-other-speaker", "maika_queue_invalid_selection"
        )

    async def test_offline_missing_or_failed_entry_blocks_browse_and_jump(self):
        self.native_playlist()
        item_id = (await self.browse_playlist()).children[0].media_content_id
        original = deepcopy(self.player.device)
        self.coordinator.async_refresh_live.reset_mock()
        for condition in ("offline", "missing", "failed"):
            with self.subTest(condition=condition):
                self.coordinator.data["devices"]["speaker-one"] = deepcopy(original)
                self.coordinator.last_update_success = True
                if condition == "offline":
                    self.player.device["online"] = False
                elif condition == "missing":
                    self.coordinator.data["devices"].pop("speaker-one")
                else:
                    self.coordinator.last_update_success = False
                await self.assert_invalid_selection(item_id, "maika_queue_unavailable")
                with self.assertRaises(BrowseError) as error:
                    await self.browse_playlist()
                self.assertEqual(
                    error.exception.translation_key, "maika_queue_unavailable"
                )
        self.coordinator.async_refresh_live.assert_not_awaited()

    async def test_offline_or_removed_during_refresh_never_sends_jump(self):
        for remove in (False, True):
            with self.subTest(remove=remove):
                self.coordinator.async_refresh_live.side_effect = None
                self.coordinator.data["devices"]["speaker-one"] = {"online": True}
                self.native_playlist()
                item_id = (await self.browse_playlist()).children[0].media_content_id

                async def refresh(serial, remove=remove, *, required_fields):
                    if remove:
                        self.coordinator.data["devices"].pop(serial)
                    else:
                        self.player.device["online"] = False

                self.coordinator.async_refresh_live.side_effect = refresh
                await self.assert_invalid_selection(item_id, "maika_queue_unavailable")

    async def test_queue_refresh_failure_does_not_use_cached_selection(self):
        self.native_playlist()
        item_id = (await self.browse_playlist()).children[0].media_content_id
        auth_error = self.player.async_play_media.__globals__["ConfigEntryAuthFailed"]
        for exception in (ApiError("failed"), auth_error()):
            with self.subTest(exception=type(exception).__name__):
                self.coordinator.async_refresh_live.side_effect = exception
                with self.assertRaises(BrowseError) as error:
                    await self.browse_playlist()
                self.assertEqual(
                    error.exception.translation_key, "maika_queue_refresh_failed"
                )
                await self.assert_invalid_selection(
                    item_id, "maika_queue_refresh_failed", HomeError
                )

    async def test_failed_refresh_result_blocks_cached_queue_and_jump(self):
        self.native_playlist()
        item_id = (await self.browse_playlist()).children[0].media_content_id
        before = deepcopy(self.coordinator.data)
        self.coordinator.async_refresh_live.return_value = False
        with self.assertRaises(BrowseError) as error:
            await self.browse_playlist()
        self.assertEqual(error.exception.translation_key, "maika_queue_refresh_failed")
        await self.assert_invalid_selection(
            item_id, "maika_queue_refresh_failed", HomeError
        )
        self.assertEqual(self.coordinator.data, before)

    async def test_unknown_browse_tokens_never_become_media_sources(self):
        for media_type, media_id in (
            ("maika_playlist", "wrong"),
            ("music", "maika_playlist"),
            ("maika_song", "key-one"),
            ("url", "https://example.org/song.mp3"),
        ):
            with self.subTest(media_type=media_type, media_id=media_id):
                with self.assertRaises(BrowseError):
                    await self.player.async_browse_media(media_type, media_id)
        self.media_source.async_browse_media.assert_not_awaited()
        self.coordinator.async_refresh_live.assert_not_awaited()
        self.assert_no_playback()

    async def test_native_jump_does_not_support_enqueue_add_or_next(self):
        self.native_playlist()
        item_id = (await self.browse_playlist()).children[0].media_content_id
        for enqueue in ("add", "next", "invalid"):
            with self.subTest(enqueue=enqueue):
                with self.assertRaises(ValidationError) as error:
                    await self.player.async_play_media(
                        "maika_song", item_id, enqueue=enqueue
                    )
                self.assertEqual(
                    error.exception.translation_key, "maika_queue_unsupported_mode"
                )
        self.assert_no_playback()

    async def test_cast_and_seek_remain_gated_when_native_play_media_is_enabled(self):
        self.player._cloud_cast_enabled = False
        for media_type, media_id in (
            ("audio/mpeg", "https://example.org/song.mp3"),
            ("music", "media-source://media_source/local/song.mp3"),
        ):
            with self.assertRaises(ValidationError) as error:
                await self.player.async_play_media(media_type, media_id)
            self.assertEqual(error.exception.translation_key, "cloud_cast_disabled")
        with self.assertRaises(ValidationError) as error:
            await self.player.async_media_seek(30)
        self.assertEqual(error.exception.translation_key, "cloud_cast_disabled")
        self.media_source.async_resolve_media.assert_not_awaited()
        self.assert_no_playback()

    async def test_unsupported_cloud_cast_media_and_modes_stay_rejected(self):
        for media_type, kwargs, expected in (
            ("video/mp4", {}, "cloud_cast_unsupported_media"),
            ("JumpCommandIssued", {}, "cloud_cast_unsupported_media"),
            ("audio/mpeg", {"enqueue": "add"}, "cloud_cast_unsupported_mode"),
            ("audio/mpeg", {"enqueue": "next"}, "cloud_cast_unsupported_mode"),
        ):
            with self.subTest(media_type=media_type, kwargs=kwargs):
                with self.assertRaises(ValidationError) as error:
                    await self.player.async_play_media(
                        media_type, "https://example.org/song.mp3", **kwargs
                    )
                self.assertEqual(error.exception.translation_key, expected)
        self.assert_no_playback()

    async def test_existing_cast_url_and_media_source_resolution_are_preserved(self):
        signed_url = "https://example.org/song.mp3?authSig=mock"
        await self.player.async_play_media(
            "audio/mpeg", signed_url, extra={"metadata": {"title": "Cast title"}}
        )
        self.client.async_cast_media.assert_awaited_once_with(
            "speaker-one", signed_url, title="Cast title", stream_format="AUDIO_MPEG"
        )
        self.assertEqual(self.player.media_content_id, signed_url)
        self.assertEqual(self.player.media_title, "Cast title")
        self.assertEqual(self.player.extra_state_attributes, {})
        self.coordinator.async_schedule_playback_refresh.assert_called_once_with(
            "speaker-one"
        )
        self.client.async_cast_media.reset_mock()
        self.media_source.async_resolve_media.return_value = SimpleNamespace(
            url=signed_url, mime_type="audio/mpeg"
        )
        await self.player.async_play_media(
            "music", "media-source://media_source/local/song.mp3"
        )
        self.media_source.async_resolve_media.assert_awaited_once_with(
            self.player.hass,
            "media-source://media_source/local/song.mp3",
            target_media_player="media_player.maika_one",
        )
        self.client.async_cast_media.assert_awaited_once()
        self.assertEqual(self.player.media_content_id, signed_url)
        self.client.async_playback_command.assert_not_awaited()

    async def test_next_previous_seek_and_volume_use_coordinator_refresh_scheduler(
        self,
    ):
        for action, args, command in (
            (self.player.async_media_next_track, (), "NextCommandIssued"),
            (self.player.async_media_previous_track, (), "PreviousCommandIssued"),
            (self.player.async_media_seek, (20,), None),
            (self.player.async_set_volume_level, (0.4,), None),
        ):
            with self.subTest(action=action.__name__):
                self.coordinator.async_schedule_playback_refresh.reset_mock()
                self.client.async_playback_command.reset_mock()
                before = deepcopy(self.player._current_playback)
                await action(*args)
                if command:
                    self.client.async_playback_command.assert_awaited_once_with(
                        "speaker-one", command
                    )
                    self.assertEqual(self.player._current_playback, before)
                self.coordinator.async_schedule_playback_refresh.assert_called_once_with(
                    "speaker-one"
                )
        self.coordinator.async_refresh_live.assert_not_awaited()
        self.assertFalse(self.tasks)

    async def test_native_metadata_matches_app_and_current_queue_item(self):
        self.native_playlist()
        child = (await self.browse_playlist()).children[0]
        payload = self.player.device["current_playback"]["payload"]
        for field in ("key", "songKey", "id"):
            with self.subTest(field=field):
                payload["playbackAttributes"] = {
                    field: "key-one",
                    "song": "App song",
                    "title": "Wrong title",
                    "name": "Wrong name",
                    "artist": "Singer",
                }
                self.assertEqual(self.player.media_title, "App song")
                self.assertEqual(self.player.media_artist, "Singer")
                self.assertEqual(self.player.media_content_id, "key-one")
                self.assertEqual(
                    self.player.extra_state_attributes,
                    {
                        "maika_song_key": "key-one",
                        "maika_queue_item_id": child.media_content_id,
                    },
                )
        payload["playbackAttributes"] = {
            "key": "key-one",
            "songKey": "key-two",
            "id": "other",
        }
        self.assertEqual(
            self.player.extra_state_attributes["maika_song_key"], "key-one"
        )
        payload["playbackAttributes"] = {
            "title": "Fallback title",
            "name": "Fallback name",
        }
        self.assertEqual(self.player.media_title, "Fallback title")
        payload["playbackAttributes"] = {"name": "Fallback name"}
        self.assertEqual(self.player.media_title, "Fallback name")
        self.assertEqual(self.player.extra_state_attributes, {})
        payload["playbackAttributes"] = {"key": "not-in-queue"}
        self.assertEqual(
            self.player.extra_state_attributes, {"maika_song_key": "not-in-queue"}
        )
        payload["playbackAttributes"] = {"key": "key-one"}
        self.player.device["latest_playlist"] = None
        self.assertEqual(
            self.player.extra_state_attributes, {"maika_song_key": "key-one"}
        )
        self.assert_no_playback()

    async def test_favorite_identifier_falls_back_to_media_id_and_numeric_id(self):
        payload = self.player.device["current_playback"]["payload"]
        payload["playbackAttributes"] = {"mediaId": "media-one", "song": "Song"}
        self.assertEqual(
            self.player.extra_state_attributes, {"maika_favorite_song_id": "media-one"}
        )
        payload["playbackAttributes"] = {"id": 321, "song": "Song"}
        self.assertEqual(
            self.player.extra_state_attributes, {"maika_favorite_song_id": "321"}
        )

    async def test_favorite_and_duration_fall_back_to_current_queue_song(self):
        self.native_playlist(
            [
                {"songKey": "key-one", "song": "Bài duy nhất", "time": "3:35"},
                {"songKey": "key-two", "song": "Bài khác", "time": "4:00"},
            ]
        )
        current = deepcopy(self.player.device["current_playback"])
        current["payload"].pop("durationInMilliseconds")
        current["payload"]["playbackAttributes"] = {
            "title": "Bài duy nhất",
            "artist": "Ca sĩ A",
        }
        self.update_device("speaker-one", {"current_playback": current})
        self.assertEqual(
            self.player.extra_state_attributes,
            {"maika_favorite_song_id": "key-one"},
        )
        self.assertEqual(self.player.media_duration, 215)

    async def test_duration_falls_back_to_current_queue_song_time(self):
        current = deepcopy(self.player.device["current_playback"])
        current["payload"].pop("durationInMilliseconds")
        current["payload"]["playbackAttributes"] = {"key": "key-one"}
        self.update_device("speaker-one", {"current_playback": current})
        self.native_playlist([{"songKey": "key-one", "time": "3:35"}])
        self.assertEqual(self.player.media_duration, 215)
        self.native_playlist([{"songKey": "key-one", "time": "215000"}])
        self.assertEqual(self.player.media_duration, 215)

    async def test_queue_attributes_follow_revision_without_exposing_playlist(self):
        playlist = self.native_playlist()
        self.player.device["current_playback"]["payload"]["playbackAttributes"] = {
            "key": "key-one"
        }
        first_id = self.player.extra_state_attributes["maika_queue_item_id"]
        playlist["songs"].reverse()
        second_id = self.player.extra_state_attributes["maika_queue_item_id"]
        self.assertNotEqual(first_id, second_id)
        result = await self.browse_playlist()
        self.assertEqual(second_id, result.children[1].media_content_id)
        self.assertEqual(
            set(self.player.extra_state_attributes),
            {"maika_song_key", "maika_queue_item_id"},
        )
        self.assert_no_playback()

    async def test_browse_rechecks_availability_after_live_refresh(self):
        self.native_playlist()

        async def refresh(serial, *, required_fields):
            self.coordinator.data["devices"].pop(serial)

        self.coordinator.async_refresh_live.side_effect = refresh
        with self.assertRaises(BrowseError) as error:
            await self.browse_playlist()
        self.assertEqual(error.exception.translation_key, "maika_queue_unavailable")
        self.assert_no_playback()

    async def test_native_selection_uses_only_ha_entity_entry_points(self):
        path = ROOT / "custom_components/maika/media_player.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        self.assertTrue(issubclass(type(self.player), CommandEntity))
        self.assertEqual(type(self.player).__bases__[1].__name__, "MediaPlayerEntity")
        functions = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
        }
        self.assertTrue({"async_browse_media", "async_play_media"} <= functions)
        forbidden = {
            "register_view",
            "async_register_command",
            "async_register",
            "async_call",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, forbidden)
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(
                    node.module,
                    {
                        "homeassistant.components.http",
                        "homeassistant.components.websocket_api",
                    },
                )
        self.assert_no_playback()

    async def test_queue_errors_have_matching_english_and_vietnamese_translations(self):
        path = ROOT / "custom_components/maika"
        strings = json.loads((path / "strings.json").read_text(encoding="utf-8"))
        english = json.loads(
            (path / "translations/en.json").read_text(encoding="utf-8")
        )
        vietnamese = json.loads(
            (path / "translations/vi.json").read_text(encoding="utf-8")
        )
        for key in (
            "maika_queue_unavailable",
            "maika_queue_refresh_failed",
            "maika_queue_invalid_selection",
            "maika_queue_changed",
            "maika_queue_unsupported_mode",
            "maika_queue_jump_failed",
            "maika_content_store_failed",
            "maika_content_store_invalid_selection",
            "maika_favorites_unavailable",
            "maika_favorites_failed",
        ):
            with self.subTest(key=key):
                self.assertEqual(strings["exceptions"][key], english["exceptions"][key])
                self.assertTrue(vietnamese["exceptions"][key]["message"])
        self.assert_no_playback()

    def content_store(self):
        return self.player._content_store

    def nct(self):
        return self.player._nct

    async def test_content_store_browse_tree_and_play(self):
        self.content_store().async_channels.return_value = [
            {"id": 7, "name": "VOV Giao thông", "cover": None}
        ]
        self.content_store().async_channel_categories.return_value = [
            {
                "id": 1,
                "title": "Tin tức",
                "cover": "https://cdn/category.png",
                "medias": [
                    {
                        "id": 100,
                        "title": "Bản tin sáng",
                        "cover": None,
                        "audio": "https://cdn/100.mp3",
                        "is_list": False,
                    }
                ],
            }
        ]
        root = await self.player.async_browse_media("maika_cs_root", "maika_cs_root")
        self.assertEqual(
            [child.media_content_id for child in root.children],
            [
                "maika_cs_channels",
                "maika_cs_categories",
                "maika_cs_highlights",
                "maika_nct_root",
            ],
        )
        channels = await self.player.async_browse_media(
            "maika_cs_channels", "maika_cs_channels"
        )
        self.assertEqual(channels.children[0].media_content_id, "maika_cs_channel:7")
        categories = await self.player.async_browse_media(
            "maika_cs_channel:7", "maika_cs_channel:7"
        )
        category = categories.children[0]
        self.assertEqual(category.media_content_id, "maika_cs_channel_category:7:1")
        self.assertEqual(category.title, "Tin tức")
        self.assertEqual(category.thumbnail, "https://cdn/category.png")
        medias = await self.player.async_browse_media(
            category.media_content_id, category.media_content_id
        )
        self.content_store().async_channel_categories.assert_awaited_with(7)
        track = medias.children[0]
        self.assertEqual(track.media_content_type, "maika_cs_track")
        self.assertEqual(track.media_content_id, "https://cdn/100.mp3")
        self.assertTrue(track.can_play)
        await self.player.async_play_media("maika_cs_track", track.media_content_id)
        self.client.async_cast_media.assert_awaited_once()
        args, kwargs = self.client.async_cast_media.call_args
        self.assertEqual(args[0], "speaker-one")
        self.assertEqual(args[1], "https://cdn/100.mp3")
        self.assertEqual(kwargs["stream_format"], "AUDIO_MPEG")

    async def test_content_store_play_updates_playback_before_live_event(self):
        self.content_store().async_channel_categories.return_value = []
        await self.player.async_play_media(
            "maika_cs_track",
            "https://cdn/new.mp3",
            extra={"title": "Bài mới"},
        )
        current = self.player._current_playback
        self.assertEqual(current["status"], "start")
        self.assertEqual(current["payload"]["offsetInMilliseconds"], 0)
        self.assertEqual(current["payload"]["playbackAttributes"]["title"], "Bài mới")
        self.assertEqual(
            current["payload"]["playbackAttributes"]["url"], "https://cdn/new.mp3"
        )
        self.assertEqual(self.player.media_title, "Bài mới")
        self.assertEqual(self.player.media_position, 0)
        self.assertEqual(self.player._last_cast_media["url"], "https://cdn/new.mp3")
        self.coordinator.async_schedule_playback_refresh.assert_called_once_with(
            "speaker-one"
        )

    async def test_next_and_previous_update_known_native_queue_track(self):
        self.native_playlist(
            [
                {"songKey": "key-one", "song": "Bài một", "artist": "Ca sĩ A"},
                {"songKey": "key-two", "song": "Bài hai", "artist": "Ca sĩ B"},
            ]
        )
        self.player.device["current_playback"]["payload"]["playbackAttributes"] = {
            "key": "key-one",
            "title": "Bài một",
        }
        await self.player.async_media_next_track()
        self.client.async_playback_command.assert_awaited_once_with(
            "speaker-one", "NextCommandIssued"
        )
        self.assertEqual(self.player.media_title, "Bài hai")
        self.assertEqual(self.player.media_artist, "Ca sĩ B")
        self.assertEqual(self.player.media_position, 0)
        self.assertEqual(self.player.state, State.PLAYING)

        self.client.async_playback_command.reset_mock()
        await self.player.async_media_previous_track()
        self.client.async_playback_command.assert_awaited_once_with(
            "speaker-one", "PreviousCommandIssued"
        )
        self.assertEqual(self.player.media_title, "Bài một")
        self.assertEqual(self.player.media_artist, "Ca sĩ A")
        self.assertEqual(self.player.media_position, 0)

    async def test_content_store_media_without_audio_expands_to_episodes(self):
        self.content_store().async_channels.return_value = []
        self.content_store().async_channel_categories.return_value = [
            {
                "id": 4,
                "title": "Phim",
                "cover": None,
                "medias": [
                    {
                        "id": 200,
                        "title": "Series",
                        "cover": None,
                        "audio": None,
                        "is_list": True,
                    }
                ],
            }
        ]
        categories = await self.player.async_browse_media(
            "maika_cs_channel:9", "maika_cs_channel:9"
        )
        category = categories.children[0]
        medias = await self.player.async_browse_media(
            category.media_content_id, category.media_content_id
        )
        album = medias.children[0]
        self.assertEqual(album.media_content_id, "maika_cs_media:200")
        self.assertTrue(album.can_expand)
        self.content_store().async_episodes.return_value = [
            {
                "id": 300,
                "title": "Tập 1",
                "cover": None,
                "audio": "https://cdn/300.mp3",
                "duration": 1800,
            }
        ]
        episodes = await self.player.async_browse_media(
            "maika_cs_media:200", "maika_cs_media:200"
        )
        self.assertEqual(episodes.children[0].media_content_id, "https://cdn/300.mp3")
        self.content_store().async_episodes.assert_awaited_once_with(200)

    async def test_content_store_play_requires_cloud_cast(self):
        self.player._cloud_cast_enabled = False
        with self.assertRaises(ValidationError) as error:
            await self.player.async_play_media("maika_cs_track", "https://cdn/x.mp3")
        self.assertEqual(error.exception.translation_key, "cloud_cast_disabled")
        self.client.async_cast_media.assert_not_awaited()

    async def test_content_store_play_rejects_non_http_url(self):
        with self.assertRaises(ValidationError) as error:
            await self.player.async_play_media("maika_cs_track", "not-a-url")
        self.assertEqual(error.exception.translation_key, "cloud_cast_invalid_url")

    async def test_content_store_failure_raises_browse_error(self):
        self.content_store().async_channels.side_effect = ApiError("boom")
        with self.assertRaises(BrowseError) as error:
            await self.player.async_browse_media(
                "maika_cs_channels", "maika_cs_channels"
            )
        self.assertEqual(error.exception.translation_key, "maika_content_store_failed")

    async def test_content_store_invalid_selection_raises_browse_error(self):
        with self.assertRaises(BrowseError) as error:
            await self.player.async_browse_media(
                "maika_cs_channel:abc", "maika_cs_channel:abc"
            )
        self.assertEqual(
            error.exception.translation_key, "maika_content_store_invalid_selection"
        )

    async def test_favorites_resolve_missing_playlist_id_by_title(self):
        self.client.async_resolve_favorite_playlist_id.return_value = "favorite-list"
        self.client.async_list_all_playlist_songs.return_value = [
            {
                "songKey": "Track0001",
                "song": "Bài yêu thích",
                "url": "https://cdn/fav.mp3",
            }
        ]
        content_root = await self.player.async_browse_media(
            "maika_cs_root", "maika_cs_root"
        )
        self.assertEqual(content_root.children[0].media_content_id, "maika_favorite")
        favorites = await self.player.async_browse_media(
            "maika_favorite", "maika_favorite"
        )
        self.client.async_resolve_favorite_playlist_id.assert_awaited()
        self.client.async_list_all_playlist_songs.assert_awaited_once_with(
            "favorite-list"
        )
        self.assertEqual(favorites.children[0].media_content_id, "https://cdn/fav.mp3")

    async def test_favorites_retry_empty_cached_playlist_by_title(self):
        self.client.favorite_playlist_id = 42
        self.client.async_resolve_favorite_playlist_id.return_value = "favorite-list"
        self.client.async_list_all_playlist_songs.side_effect = [
            [],
            [
                {
                    "songKey": "Track0001",
                    "song": "Bài yêu thích",
                    "url": "https://cdn/fav.mp3",
                }
            ],
        ]
        favorites = await self.player.async_browse_media(
            "maika_favorite", "maika_favorite"
        )
        self.client.async_resolve_favorite_playlist_id.assert_awaited_once_with(
            force=True
        )
        self.assertEqual(
            [
                call.args[0]
                for call in self.client.async_list_all_playlist_songs.await_args_list
            ],
            [42, "favorite-list"],
        )
        self.assertEqual(favorites.children[0].media_content_id, "https://cdn/fav.mp3")

    async def test_favorites_require_playlist_and_surface_failures(self):
        with self.assertRaises(BrowseError) as error:
            await self.player.async_browse_media("maika_favorite", "maika_favorite")
        self.assertEqual(error.exception.translation_key, "maika_favorites_unavailable")
        self.client.favorite_playlist_id = 42
        self.client.async_list_all_playlist_songs.side_effect = ApiError("boom")
        with self.assertRaises(BrowseError) as error:
            await self.player.async_browse_media("maika_favorite", "maika_favorite")
        self.assertEqual(error.exception.translation_key, "maika_favorites_failed")

    async def test_favorites_are_first_content_store_directory_and_playable(self):
        self.client.favorite_playlist_id = 42
        self.client.async_list_all_playlist_songs.return_value = [
            {
                "songKey": "Track0001",
                "song": "Bài yêu thích",
                "artist": "Ca sĩ",
                "url": "https://cdn/favorite.mp3",
                "imageURL": "https://cdn/favorite.jpg",
            },
            {
                "songKey": "Track0002",
                "song": "Thiếu stream",
                "url": "not-a-url",
            },
        ]
        content_root = await self.player.async_browse_media(
            "maika_cs_root", "maika_cs_root"
        )
        favorite = content_root.children[0]
        self.assertEqual(favorite.media_content_type, "maika_favorite")
        self.assertEqual(favorite.media_content_id, "maika_favorite")
        self.assertEqual(favorite.title, "Bài hát yêu thích")

        favorites = await self.player.async_browse_media(
            "maika_favorite", "maika_favorite"
        )
        self.client.async_list_all_playlist_songs.assert_awaited_once_with(42)
        self.assertEqual(len(favorites.children), 1)
        track = favorites.children[0]
        self.assertEqual(track.media_content_type, "maika_favorite_track")
        self.assertEqual(track.media_content_id, "https://cdn/favorite.mp3")
        self.assertEqual(track.title, "Bài yêu thích — Ca sĩ")
        self.assertEqual(track.thumbnail, "https://cdn/favorite.jpg")
        self.assertTrue(track.can_play)

        await self.player.async_play_media(
            "maika_favorite_track", track.media_content_id
        )
        self.client.async_cast_media.assert_awaited_once()
        self.assertEqual(
            self.client.async_cast_media.call_args.args[:2],
            ("speaker-one", "https://cdn/favorite.mp3"),
        )

    async def test_nhaccuatui_browse_and_play(self):
        self.nct().async_feed.return_value = [
            {
                "key": "Track0001",
                "title": "Bài mới",
                "artist": "Ca sĩ",
                "cover": "https://cdn/cover.jpg",
                "duration": 180,
                "stream_url": "https://stream/320.mp3",
            }
        ]
        self.nct().async_charts.return_value = [
            {
                "key": "chart-1",
                "title": "Top 50",
                "cover": None,
                "tracks": [],
            }
        ]
        self.nct().async_chart_tracks.return_value = [
            {"key": "Track0002", "title": "Chart song", "artist": None}
        ]
        root = await self.player.async_browse_media("maika_nct_root", "maika_nct_root")
        self.assertEqual(
            [child.media_content_id for child in root.children],
            ["maika_nct_feed", "maika_nct_charts"],
        )
        feed = await self.player.async_browse_media("maika_nct_feed", "maika_nct_feed")
        track = feed.children[0]
        self.assertEqual(track.media_content_type, "maika_nct_track")
        self.assertEqual(track.media_content_id, "Track0001")
        self.assertEqual(track.title, "Bài mới — Ca sĩ")
        charts = await self.player.async_browse_media(
            "maika_nct_charts", "maika_nct_charts"
        )
        chart = charts.children[0]
        self.assertEqual(chart.media_content_id, "maika_nct_chart:chart-1")
        chart_tracks = await self.player.async_browse_media(
            chart.media_content_id, chart.media_content_id
        )
        self.assertEqual(chart_tracks.children[0].media_content_id, "Track0002")
        self.nct().async_chart_tracks.assert_awaited_once_with("chart-1")

        self.nct().async_song.return_value = {
            "key": "Track0001",
            "title": "Bài mới",
            "artist": "Ca sĩ",
            "stream_url": "https://stream/320.mp3",
        }
        await self.player.async_play_media("maika_nct_track", "Track0001")
        self.nct().async_song.assert_awaited_once_with("Track0001")
        self.client.async_cast_media.assert_awaited_once()
        args, kwargs = self.client.async_cast_media.call_args
        self.assertEqual(args[0], "speaker-one")
        self.assertEqual(args[1], "https://stream/320.mp3")
        self.assertEqual(kwargs["stream_format"], "AUDIO_MPEG")
        self.assertEqual(kwargs["title"], "Bài mới — Ca sĩ")

    async def test_nhaccuatui_direct_url_resolves_song(self):
        self.nct().async_song.return_value = {
            "key": "Track0001",
            "title": "Bài mới",
            "artist": None,
            "stream_url": "https://stream/320.mp3",
        }
        await self.player.async_play_media(
            "music", "https://www.nhaccuatui.com/song/Track0001"
        )
        self.nct().async_song.assert_awaited_once_with("Track0001")
        self.client.async_cast_media.assert_awaited_once()

    async def test_nhaccuatui_rejects_invalid_key_and_missing_stream(self):
        with self.assertRaises(ValidationError) as error:
            await self.player.async_play_media("maika_nct_track", "../bad")
        self.assertEqual(error.exception.translation_key, "nhaccuatui_invalid_track")
        self.nct().async_song.return_value = {"title": "No stream"}
        with self.assertRaises(HomeError) as error:
            await self.player.async_play_media("maika_nct_track", "Track0001")
        self.assertEqual(
            error.exception.translation_key, "nhaccuatui_track_unavailable"
        )
        self.client.async_cast_media.assert_not_awaited()


def validate_media_player():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PlaybackTests)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(suite)
    return [] if result.wasSuccessful() else [output.getvalue()]


if __name__ == "__main__":
    unittest.main()
