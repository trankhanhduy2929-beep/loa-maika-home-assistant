from __future__ import annotations

import ast
import asyncio
import io
import runpy
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, Mock, call

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "custom_components/maika"


class CoordinatorStub:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, *args, **kwargs):
        self.hass = hass
        self.data = None

    def async_set_updated_data(self, data):
        self.data = data


class HistoryStoreStub:
    """In-memory stand-in for the HA Store backed command history."""

    instances: ClassVar[list] = []

    def __init__(self, hass, entry_id):
        self.hass = hass
        self.entry_id = entry_id
        self.saved = None
        self.to_load = []
        HistoryStoreStub.instances.append(self)

    async def async_load(self):
        return list(self.to_load)

    async def async_save(self, history):
        self.saved = list(history)


class OfflineSession:
    def __getattr__(self, name):
        raise AssertionError(f"Unexpected network operation: {name}")


def load_code(filename, namespace):
    path = DIRECTORY / filename
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        node
        for node in tree.body
        if not (
            (
                isinstance(node, ast.ImportFrom)
                and (node.level > 0 or (node.module or "").startswith("homeassistant"))
            )
            or (
                isinstance(node, ast.Import)
                and any(alias.name == "aiohttp" for alias in node.names)
            )
        )
    ]
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


def load_modules():
    constants = runpy.run_path(str(DIRECTORY / "const.py"))
    phone = runpy.run_path(str(DIRECTORY / "phone.py"))
    api = load_code(
        "api.py",
        {
            **constants,
            **phone,
            "__name__": "maika_live_api_test",
            "aiohttp": SimpleNamespace(
                ClientTimeout=lambda **kwargs: SimpleNamespace(**kwargs),
                ClientError=type("ClientError", (Exception,), {}),
            ),
        },
    )
    rules = runpy.run_path(str(DIRECTORY / "voice_rules.py"))
    voice_state = runpy.run_path(str(DIRECTORY / "voice_state.py"))
    coordinator = load_code(
        "coordinator.py",
        {
            **constants,
            **rules,
            **voice_state,
            **{
                name: api[name]
                for name in (
                    "MaikaApiClient",
                    "MaikaApiError",
                    "MaikaAuthenticationError",
                    "merge_current_playback",
                )
            },
            "__name__": "maika_live_coordinator_test",
            "DataUpdateCoordinator": CoordinatorStub,
            "MaikaVoiceCommandHistoryStore": HistoryStoreStub,
            "callback": lambda function: function,
            "ConfigEntryAuthFailed": type("ConfigEntryAuthFailed", (Exception,), {}),
            "UpdateFailed": type("UpdateFailed", (Exception,), {}),
            "LICENSE_PORTAL_URL": "",
            "persistent_notification": SimpleNamespace(
                async_create=Mock(), async_dismiss=Mock()
            ),
        },
    )
    return api, coordinator


def playback(key="track-a", offset=12000):
    return {
        "status": "playing",
        "payload": {
            "offsetInMilliseconds": offset,
            "durationInMilliseconds": 180000,
            "playbackAttributes": {
                "key": key,
                "title": key,
                "artist": "Artist",
                "imageURL": "https://example.org/cover.jpg",
            },
        },
    }


class LivePlaybackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.api, self.module = load_modules()
        self.tasks = []
        self.entry = SimpleNamespace(
            entry_id="offline-test",
            options={},
            async_create_background_task=self.create_task,
        )
        self.hass = SimpleNamespace()
        self.client = self.api["MaikaApiClient"](
            OfflineSession(), "test@example.org", "dummy", "client", "session"
        )
        self.client.async_send_command = AsyncMock()
        self.client._handle_stream_frame({"session_id": "test-session"})
        self.coordinator = self.module["MaikaDataUpdateCoordinator"](
            self.hass, self.entry, self.client
        )
        self.coordinator.data = {
            "devices": {
                "one": {
                    "device_id": "one",
                    "id": 1,
                    "name": "One",
                    "volume": 30,
                    "mute": False,
                    "current_playback": playback(),
                    "latest_playlist": {"listKey": "old-list"},
                },
                "two": {"device_id": "two", "id": 2, "volume": 60},
            },
            "voices": {"voice": "Voice"},
        }
        self.client.set_event_callback(self.coordinator.async_handle_stream_frame)
        self.poll_devices = deepcopy(list(self.coordinator.data["devices"].values()))
        self.client.async_list_devices = AsyncMock(
            side_effect=lambda: deepcopy(self.poll_devices)
        )
        self.client.async_get_device = AsyncMock(return_value={})
        self.client.async_get_tts_voices = AsyncMock(return_value=[])

    async def asyncTearDown(self):
        self.client.async_send_command.side_effect = None
        await self.coordinator.async_stop()
        await self.client.async_stop()
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    def create_task(self, hass, coroutine, name):
        self.assertIs(hass, self.hass)
        task = asyncio.create_task(coroutine, name=name)
        self.tasks.append(task)
        return task

    def spawn(self, coroutine):
        return self.create_task(self.hass, coroutine, "test")

    def report(self, serial="one", **changes):
        self.client._handle_stream_frame(
            {
                "directive": {
                    "header": {"name": "DeviceInfo", "namespace": "ClientInformation"},
                    "payload": {"deviceId": serial, **deepcopy(changes)},
                }
            }
        )

    def device(self, serial="one"):
        return self.coordinator.data["devices"][serial]

    async def poll(self):
        data = await self.coordinator._async_update_data()
        self.coordinator.async_set_updated_data(data)
        return data

    def player(self):
        module = runpy.run_path(str(ROOT / "scripts/test_media_player.py"))
        self.coordinator.last_update_success = True
        self.device()["online"] = True
        self.device()["latest_playlist"] = {
            "listKey": "list",
            "songs": [{"songKey": "track-a", "song": "Track A"}],
        }
        self.client.async_playback_command = AsyncMock(
            wraps=self.client.async_playback_command
        )
        return module["load_player"]()(self.coordinator, "one")

    def subscription_calls(self, name="StartListening", kind="media_control"):
        return [
            args
            for args in self.client.async_send_command.call_args_list
            if args.args[0] == name and args.args[2].get("type") == kind
        ]

    async def test_timeouts_return_none_not_cache_and_clean_waiters(self):
        self.report(current_playback=playback())
        for connected in (False, True):
            with self.subTest(connected=connected):
                if connected:
                    self.client._connected.set()
                else:
                    self.client._connected.clear()
                result = await self.client.async_request_device_info("one", 0.001)
                self.assertIsNone(result)
                self.assertFalse(self.client._device_info_waiters)
        self.assertEqual(
            self.client.live_device_info["one"]["current_playback"], playback()
        )
        self.assertEqual(self.client.async_send_command.await_count, 1)

    async def test_volume_only_response_is_not_a_fresh_playback_snapshot(self):
        self.report(current_playback=playback(), latest_playlist={"listKey": "list"})
        self.client.async_send_command.side_effect = lambda *args: self.report(
            volume=71
        )
        response = await self.client.async_request_device_info("one", 0.1)
        self.assertEqual(response, {"device_id": "one", "volume": 71})
        self.assertEqual(
            self.client.live_device_info["one"]["current_playback"], playback()
        )
        self.assertNotIn("online", response)
        self.assertEqual(self.device()["current_playback"], playback())
        self.assertEqual(
            self.client.async_send_command.call_args.args[2],
            {"deviceId": "one", "fields": self.api["DEVICE_INFO_FIELDS"]},
        )
        self.assertIn("current_playback", self.api["DEVICE_INFO_FIELDS"].split(","))
        self.assertIn("latest_playlist", self.api["DEVICE_INFO_FIELDS"].split(","))

    async def test_queue_browse_rejects_volume_only_refresh(self):
        player = self.player()
        self.client.async_send_command.side_effect = lambda *args: self.report(
            volume=71
        )
        with self.assertRaisesRegex(
            player.async_browse_media.__globals__["BrowseError"],
            "maika_queue_refresh_failed",
        ):
            await player.async_browse_media("maika_playlist", "maika_playlist")
        self.client.async_playback_command.assert_not_awaited()
        self.assertEqual(self.device()["volume"], 71)
        self.assertEqual(self.device()["latest_playlist"]["listKey"], "list")

    async def test_queue_jump_rejects_volume_only_refresh(self):
        player = self.player()
        playlist = self.device()["latest_playlist"]
        item_id = player._queue_item_id(player._queue_revision(playlist), "track-a")
        self.client.async_send_command.side_effect = lambda *args: self.report(
            volume=71
        )
        with self.assertRaisesRegex(
            player.async_play_media.__globals__["HomeAssistantError"],
            "maika_queue_refresh_failed",
        ):
            await player.async_play_media("maika_song", item_id)
        self.client.async_playback_command.assert_not_awaited()
        self.assertFalse(self.coordinator._playback_refresh_tasks)

    async def test_queue_refresh_uses_newer_playlist_event_after_volume_response(self):
        player = self.player()
        playlist = deepcopy(self.device()["latest_playlist"])

        def command(name, namespace, payload):
            if name == "GetDeviceInfo":
                self.report(volume=71)
                self.report(latest_playlist=playlist)

        self.client.async_send_command.side_effect = command
        result = await player.async_browse_media("maika_playlist", "maika_playlist")
        self.assertEqual(len(result.children), 1)
        await player.async_play_media("maika_song", result.children[0].media_content_id)
        self.assertEqual(
            self.client.async_playback_command.await_args_list,
            [
                call("one", "JumpCommandIssued", song_key="track-a"),
                call("one", "ResumeCommandIssued"),
            ],
        )
        self.assertEqual(
            self.client.async_send_command.await_args_list[-2:],
            [
                call(
                    "JumpCommandIssued",
                    "PlaybackController",
                    {"deviceId": "one", "songKey": "track-a"},
                ),
                call(
                    "ResumeCommandIssued",
                    "PlaybackController",
                    {"deviceId": "one"},
                ),
            ],
        )
        self.assertEqual(self.client.async_send_command.await_count, 4)

    async def test_queue_refresh_counts_only_new_reports_for_the_same_speaker(self):
        player = self.player()
        playlist = deepcopy(self.device()["latest_playlist"])
        self.report(latest_playlist=playlist)

        def command(*args):
            self.report("two", latest_playlist=playlist)
            self.report(current_playback={"status": "paused"})

        self.client.async_send_command.side_effect = command
        self.assertFalse(
            await self.coordinator.async_refresh_live(
                "one", required_fields=("latest_playlist",)
            )
        )
        self.assertEqual(player.state, "paused")
        self.client.async_playback_command.assert_not_awaited()

    async def test_queue_clear_during_refresh_invalidates_selection(self):
        player = self.player()
        playlist = self.device()["latest_playlist"]
        item_id = player._queue_item_id(player._queue_revision(playlist), "track-a")

        def command(*args):
            self.report(volume=71)
            self.report(latest_playlist=None)

        self.client.async_send_command.side_effect = command
        with self.assertRaisesRegex(
            player.async_play_media.__globals__["ServiceValidationError"],
            "maika_queue_changed",
        ):
            await player.async_play_media("maika_song", item_id)
        self.client.async_playback_command.assert_not_awaited()
        self.assertIsNone(self.device()["latest_playlist"])

    async def test_required_queue_refresh_can_merge_a_direct_response(self):
        playlist = {"listKey": "new-list", "songs": []}
        self.client.async_request_device_info = AsyncMock(
            return_value={"device_id": "one", "latest_playlist": playlist}
        )
        self.assertTrue(
            await self.coordinator.async_refresh_live(
                "one", required_fields=("latest_playlist",)
            )
        )
        self.assertEqual(self.device()["latest_playlist"], playlist)

    async def test_waiter_payload_is_independent_of_merged_cache(self):
        self.report(current_playback=playback())
        patch = {"status": "paused", "payload": {"offsetInMilliseconds": 50000}}
        self.client.async_send_command.side_effect = lambda *args: self.report(
            currentPlayback=patch
        )
        response = await self.client.async_request_device_info("one", 0.1)
        self.assertEqual(response["current_playback"], patch)
        response["current_playback"]["payload"]["offsetInMilliseconds"] = -1
        for device in (self.device(), self.client.live_device_info["one"]):
            self.assertEqual(
                device["current_playback"]["payload"]["offsetInMilliseconds"], 50000
            )
            self.assertEqual(
                device["current_playback"]["payload"]["playbackAttributes"]["key"],
                "track-a",
            )

    async def test_cancelled_request_does_not_cancel_other_waiters(self):
        started = asyncio.Event()
        count = 0

        async def command(*args):
            nonlocal count
            count += 1
            if count == 2:
                started.set()

        self.client.async_send_command.side_effect = command
        first = self.spawn(self.client.async_request_device_info("one", 1))
        second = self.spawn(self.client.async_request_device_info("one", 1))
        await asyncio.wait_for(started.wait(), 1)
        first.cancel()
        await asyncio.gather(first, return_exceptions=True)
        self.report(volume=45)
        self.assertEqual(await second, {"device_id": "one", "volume": 45})
        self.assertFalse(self.client._device_info_waiters)

    async def test_request_send_error_and_stop_release_waiters(self):
        self.client.async_send_command.side_effect = self.api["MaikaConnectionError"](
            "offline"
        )
        with self.assertRaises(self.api["MaikaConnectionError"]):
            await self.client.async_request_device_info("one", 0.1)
        self.assertFalse(self.client._device_info_waiters)
        started = asyncio.Event()
        self.client.async_send_command.side_effect = lambda *args: started.set()
        task = self.spawn(self.client.async_request_device_info("one", 1))
        await asyncio.wait_for(started.wait(), 1)
        await self.client.async_stop()
        self.assertIsInstance(
            (await asyncio.gather(task, return_exceptions=True))[0],
            asyncio.CancelledError,
        )
        self.assertFalse(self.client._device_info_waiters)
        self.assertIsNone(await self.client.async_request_device_info("one", 0.1))

    async def test_partial_playback_preserves_track_and_explicit_null_clears(self):
        self.report(current_playback=playback())
        self.report(current_playback={"status": "paused"})
        self.report(current_playback={"payload": {"offsetInMilliseconds": 16000}})
        expected = playback(offset=16000)
        expected["status"] = "paused"
        self.assertEqual(self.device()["current_playback"], expected)
        self.assertEqual(
            self.client.live_device_info["one"]["current_playback"], expected
        )
        self.report(
            current_playback={
                "payload": {"playbackAttributes": {"key": "track-a", "artist": None}}
            }
        )
        self.assertIsNone(
            self.device()["current_playback"]["payload"]["playbackAttributes"]["artist"]
        )
        self.assertEqual(
            self.device()["current_playback"]["payload"]["durationInMilliseconds"],
            180000,
        )
        self.report(current_playback={"payload": {"playbackAttributes": None}})
        self.assertIsNone(
            self.device()["current_playback"]["payload"]["playbackAttributes"]
        )
        self.report(current_playback={"payload": None})
        self.assertIsNone(self.device()["current_playback"]["payload"])
        self.report(current_playback=None, latest_playlist=None)
        for device in (
            self.device(),
            self.client.live_device_info["one"],
            self.client._discovered_devices["one"],
        ):
            self.assertIsNone(device["current_playback"])
            self.assertIsNone(device["latest_playlist"])

    async def test_new_track_replaces_attributes_and_drops_old_timing(self):
        merge = self.api["merge_current_playback"]
        for identity in (
            "key",
            "songKey",
            "url",
            "id",
            "mediaId",
            "media_id",
            "title",
            "song",
            "name",
        ):
            with self.subTest(identity=identity):
                old = playback()
                old["payload"]["durationInMillis"] = 180000
                old["payload"]["playbackAttributes"][identity] = "before"
                patch = {"payload": {"playbackAttributes": {identity: "after"}}}
                result = merge(old, patch)
                self.assertEqual(result["payload"], patch["payload"])
                self.assertEqual(old["payload"]["offsetInMilliseconds"], 12000)
        self.report(current_playback=playback())
        self.report(
            current_playback={"payload": {"playbackAttributes": {"key": "track-b"}}}
        )
        expected = {"playbackAttributes": {"key": "track-b"}}
        self.assertEqual(self.device()["current_playback"]["payload"], expected)
        self.assertEqual(
            self.client.live_device_info["one"]["current_playback"]["payload"], expected
        )
        self.assertEqual(
            self.client._discovered_devices["one"]["current_playback"]["payload"],
            expected,
        )

    async def test_refresh_does_not_reapply_old_waiter_after_new_event(self):
        def command(*args):
            self.report(current_playback=playback("track-b", 0), volume=40)
            self.report(current_playback=playback("track-c", 3000))
            self.report(volume=80, latest_playlist={"listKey": "new-list"})

        self.client.async_send_command.side_effect = command
        self.assertTrue(await self.coordinator.async_refresh_live("one"))
        self.assertEqual(self.device()["current_playback"], playback("track-c", 3000))
        self.assertEqual(self.device()["volume"], 80)
        self.assertEqual(self.device()["latest_playlist"], {"listKey": "new-list"})
        self.assertEqual(self.coordinator._live_revision, 3)

    async def test_refresh_does_not_reapply_status_patch_to_new_track(self):
        def command(*args):
            self.report(current_playback={"status": "paused"})
            self.report(current_playback=playback("track-b", 0))

        self.client.async_send_command.side_effect = command
        await self.coordinator.async_refresh_live("one")
        self.assertEqual(self.device()["current_playback"], playback("track-b", 0))

    async def test_overlapping_refreshes_cannot_replay_older_response(self):
        first_started = asyncio.Event()
        release_first = asyncio.Event()
        requests = 0

        async def command(*args):
            nonlocal requests
            requests += 1
            if requests == 1:
                self.report(current_playback=playback("track-b", 0))
                first_started.set()
                await release_first.wait()
            else:
                self.report(current_playback=playback("track-c", 2000))
                self.report(volume=91)

        self.client.async_send_command.side_effect = command
        first = self.spawn(self.coordinator.async_refresh_live("one"))
        await asyncio.wait_for(first_started.wait(), 1)
        self.assertTrue(await self.coordinator.async_refresh_live("one"))
        release_first.set()
        self.assertTrue(await first)
        self.assertEqual(self.device()["current_playback"], playback("track-c", 2000))
        self.assertEqual(self.device()["volume"], 91)
        self.assertFalse(self.client._device_info_waiters)

    async def test_poll_keeps_events_while_other_speaker_is_still_awaiting(self):
        one_reported = asyncio.Event()

        async def command(name, namespace, payload):
            if name != "GetDeviceInfo":
                return
            if payload["deviceId"] == "one":
                self.report(current_playback=playback("track-b", 0))
                one_reported.set()
            else:
                await one_reported.wait()
                self.report(
                    current_playback={"payload": {"offsetInMilliseconds": 7000}}
                )
                self.report(volume=92, latest_playlist={"listKey": "last"})
                self.report("two", volume=76)

        self.client.async_send_command.side_effect = command
        await self.poll()
        self.assertEqual(self.device()["current_playback"], playback("track-b", 7000))
        self.assertEqual(self.device()["volume"], 92)
        self.assertEqual(self.device()["latest_playlist"], {"listKey": "last"})
        self.assertEqual(self.device("two")["volume"], 76)

    async def test_refresh_fallback_merges_only_fields_without_newer_events(self):
        async def request(serial):
            self.report(volume=90)
            return {"device_id": serial, "volume": 10, "mute": True}

        self.client.async_request_device_info = AsyncMock(side_effect=request)
        self.assertTrue(await self.coordinator.async_refresh_live("one"))
        self.assertEqual(self.device()["volume"], 90)
        self.assertTrue(self.device()["mute"])
        self.assertEqual(self.device()["current_playback"], playback())

    async def test_refresh_timeout_and_identifier_only_do_not_publish(self):
        before = deepcopy(self.coordinator.data)
        self.client.async_request_device_info = AsyncMock(
            side_effect=[None, {"device_id": "one"}]
        )
        for _ in range(2):
            self.assertFalse(await self.coordinator.async_refresh_live("one"))
            self.assertEqual(self.coordinator.data, before)
            self.assertEqual(self.coordinator._live_revision, 0)

    async def test_poll_retains_all_fields_across_every_await(self):
        async def listed():
            self.report(current_playback=playback("track-b", 1000))
            return deepcopy(self.poll_devices)

        async def detail(internal_id):
            if internal_id == 1:
                self.report(volume=81)
            return {}

        async def voices():
            self.report(mute=True)
            return []

        def command(name, namespace, payload):
            if name == "GetDeviceInfo":
                self.report(payload["deviceId"], volume=82)
                if payload["deviceId"] == "one":
                    self.report(
                        current_playback={"payload": {"offsetInMilliseconds": 2000}}
                    )
            elif payload["type"] == "conversation":
                self.report(latest_playlist={"listKey": "last-await"})

        self.entry.options["enable_voice_command_sensor"] = True
        self.client.async_list_devices.side_effect = listed
        self.client.async_get_device.side_effect = detail
        self.client.async_get_tts_voices.side_effect = voices
        self.client.async_send_command.side_effect = command
        await self.poll()
        self.assertEqual(self.device()["current_playback"], playback("track-b", 2000))
        self.assertEqual(self.device()["volume"], 82)
        self.assertTrue(self.device()["mute"])
        self.assertEqual(self.device()["latest_playlist"], {"listKey": "last-await"})
        self.assertEqual(self.coordinator.data["voices"], {"voice": "Voice"})
        self.assertEqual(self.device()["name"], "One")

    async def test_poll_first_refresh_preserves_events_before_devices_exist(self):
        self.coordinator.data = None

        async def listed():
            self.report(current_playback=playback("track-b", 0))
            self.report(volume=81)
            return deepcopy(self.poll_devices)

        self.client.async_list_devices.side_effect = listed
        self.client.async_request_device_info = AsyncMock(return_value=None)
        await self.poll()
        self.assertEqual(self.device()["current_playback"], playback("track-b", 0))
        self.assertEqual(self.device()["volume"], 81)

    async def test_poll_null_and_new_track_cannot_resurrect_rest_duration(self):
        async def request(serial):
            if serial == "one":
                self.report(current_playback=None, latest_playlist=None)
                self.report(
                    current_playback={
                        "status": "start",
                        "payload": {"playbackAttributes": {"key": "track-b"}},
                    }
                )
            return None

        self.client.async_request_device_info = AsyncMock(side_effect=request)
        await self.poll()
        self.assertEqual(
            self.device()["current_playback"],
            {"status": "start", "payload": {"playbackAttributes": {"key": "track-b"}}},
        )
        self.assertIsNone(self.device()["latest_playlist"])

    async def test_poll_timeout_and_volume_only_do_not_rollback_previous_stream(self):
        self.report(current_playback=playback("track-b", 5000))
        self.report(latest_playlist=None)
        self.client.async_request_device_info = AsyncMock(return_value=None)
        await self.poll()
        self.assertEqual(self.device()["current_playback"], playback("track-b", 5000))
        self.assertIsNone(self.device()["latest_playlist"])

        async def request(serial):
            return {"device_id": serial, "volume": 85}

        self.client.async_request_device_info.side_effect = request
        await self.poll()
        self.assertEqual(self.device()["current_playback"], playback("track-b", 5000))
        self.assertEqual(self.device()["volume"], 85)
        self.assertIsNone(self.device()["latest_playlist"])

    async def test_first_poll_partial_response_keeps_rest_track_attributes(self):
        self.coordinator.data = None

        async def request(serial):
            if serial == "one":
                self.report(current_playback={"status": "paused"})
            return None

        self.client.async_request_device_info = AsyncMock(side_effect=request)
        await self.poll()
        expected = playback()
        expected["status"] = "paused"
        self.assertEqual(self.device()["current_playback"], expected)

    async def test_subscription_works_without_voice_and_removes_missing_speaker(self):
        self.client.async_request_device_info = AsyncMock(return_value=None)
        await self.poll()
        await self.poll()
        self.assertCountEqual(
            self.subscription_calls(),
            [
                call(
                    "StartListening",
                    "Conversation",
                    {"deviceId": serial, "type": "media_control"},
                )
                for serial in ("one", "two")
            ],
        )
        self.assertFalse(self.subscription_calls(kind="conversation"))
        self.assertEqual(self.coordinator.data["voice_subscription_status"], "disabled")
        self.poll_devices = self.poll_devices[:1]
        await self.poll()
        self.assertEqual(
            self.subscription_calls("StopListening"),
            [
                call(
                    "StopListening",
                    "Conversation",
                    {"deviceId": "two", "type": "media_control"},
                )
            ],
        )
        self.assertNotIn("two", self.coordinator._media_subscribed_generation)
        await self.coordinator.async_stop()
        self.assertEqual(len(self.subscription_calls("StopListening")), 2)

    async def test_media_reconnect_is_generation_scoped_and_coalesced(self):
        self.client.async_request_device_info = AsyncMock(return_value=None)
        await self.poll()
        self.client._connected.clear()
        await self.coordinator._async_ensure_media_subscriptions()
        self.client._handle_stream_frame({"session_id": "next"})
        task = self.coordinator._media_subscription_task
        self.client._handle_stream_frame({"session_id": "next"})
        self.assertIs(self.coordinator._media_subscription_task, task)
        await task
        self.assertEqual(self.client.listener_generation, 2)
        self.assertEqual(len(self.subscription_calls()), 4)
        self.assertEqual(
            self.coordinator._media_subscribed_generation, {"one": 2, "two": 2}
        )

    async def test_reconnect_during_subscription_does_not_mark_new_generation(self):
        self.coordinator._media_subscription_targets = {"one"}
        started = asyncio.Event()
        blocked = asyncio.Event()

        async def command(*args):
            if self.client.async_send_command.await_count == 1:
                started.set()
                await blocked.wait()

        self.client.async_send_command.side_effect = command
        self.coordinator._schedule_media_subscriptions()
        old_task = self.coordinator._media_subscription_task
        await asyncio.wait_for(started.wait(), 1)
        self.client._connected.clear()
        self.client._handle_stream_frame({"session_id": "next"})
        await self.coordinator._media_subscription_task
        await asyncio.gather(old_task, return_exceptions=True)
        self.assertTrue(old_task.cancelled())
        self.assertEqual(self.coordinator._media_subscribed_generation, {"one": 2})
        self.assertEqual(len(self.subscription_calls()), 2)

    async def test_failed_subscription_retries_and_stop_continues_after_error(self):
        self.coordinator._media_subscription_targets = {"one", "two"}
        self.client.async_send_command.side_effect = [
            self.api["MaikaConnectionError"]("offline"),
            None,
        ]
        await self.coordinator._async_ensure_media_subscriptions()
        self.assertEqual(len(self.coordinator._media_subscribed_generation), 1)
        self.client.async_send_command.side_effect = None
        await self.coordinator._async_ensure_media_subscriptions()
        self.assertEqual(len(self.subscription_calls()), 3)
        self.client.async_send_command.side_effect = self.api["MaikaConnectionError"](
            "offline"
        )
        await self.coordinator.async_stop()
        self.assertEqual(len(self.subscription_calls("StopListening")), 2)
        self.assertFalse(self.coordinator._media_subscribed_generation)

    async def test_stop_cancels_inflight_subscription_and_prevents_recreation(self):
        self.coordinator._media_subscription_targets = {"one"}
        started = asyncio.Event()

        async def command(name, *args):
            if name == "StartListening":
                started.set()
                await asyncio.Event().wait()

        self.client.async_send_command.side_effect = command
        self.coordinator._schedule_media_subscriptions()
        task = self.coordinator._media_subscription_task
        await asyncio.wait_for(started.wait(), 1)
        await self.coordinator.async_stop()
        self.assertTrue(task.cancelled())
        self.assertEqual(len(self.subscription_calls("StopListening")), 1)
        before = len(self.tasks)
        self.coordinator.async_handle_stream_frame({"session_id": "after-stop"})
        self.coordinator.async_schedule_playback_refresh("one")
        await self.coordinator._async_ensure_media_subscriptions()
        self.assertEqual(len(self.tasks), before)

    async def test_media_target_change_cancels_inflight_and_cleans_removed_target(self):
        self.coordinator._media_subscription_targets = {"one"}
        started = asyncio.Event()

        async def command(name, namespace, payload):
            if name == "StartListening" and payload["deviceId"] == "one":
                started.set()
                await asyncio.Event().wait()

        self.client.async_send_command.side_effect = command
        self.coordinator._schedule_media_subscriptions()
        old_task = self.coordinator._media_subscription_task
        await asyncio.wait_for(started.wait(), 1)
        self.coordinator._media_subscription_targets = {"two"}
        self.coordinator._schedule_media_subscriptions()
        await self.coordinator._media_subscription_task
        await asyncio.gather(old_task, return_exceptions=True)
        self.assertTrue(old_task.cancelled())
        self.assertEqual(self.coordinator._media_subscribed_generation, {"two": 1})
        self.assertFalse(self.coordinator._media_subscription_pending)
        self.assertEqual(
            self.subscription_calls("StopListening"),
            [
                call(
                    "StopListening",
                    "Conversation",
                    {"deviceId": "one", "type": "media_control"},
                )
            ],
        )

    async def test_poll_subscription_can_be_cancelled_during_unload(self):
        started = asyncio.Event()

        async def command(name, *args):
            if name == "StartListening":
                started.set()
                await asyncio.Event().wait()

        self.client.async_send_command.side_effect = command
        poll = self.spawn(self.poll())
        await asyncio.wait_for(started.wait(), 1)
        await self.coordinator.async_stop()
        await poll
        self.assertTrue(self.coordinator._media_subscription_task.cancelled())
        self.assertFalse(self.coordinator._media_subscribed_generation)
        self.assertFalse(self.coordinator._media_subscription_pending)
        self.assertEqual(len(self.subscription_calls("StopListening")), 1)
        self.assertEqual(self.client.async_send_command.await_count, 2)

    async def test_stop_cancels_voice_subscription_without_affecting_media(self):
        self.entry.options["enable_voice_command_sensor"] = True
        self.client.async_request_device_info = AsyncMock(return_value=None)
        started = asyncio.Event()

        async def command(name, namespace, payload):
            if name == "StartListening" and payload["type"] == "conversation":
                started.set()
                await asyncio.Event().wait()

        self.client.async_send_command.side_effect = command
        poll = self.spawn(self.poll())
        await asyncio.wait_for(started.wait(), 1)
        await self.coordinator.async_stop()
        await poll
        self.assertTrue(self.coordinator._voice_subscription_task.cancelled())
        self.assertFalse(self.coordinator._voice_subscription_pending)
        self.assertEqual(
            len(self.subscription_calls("StopListening", "conversation")), 1
        )
        self.assertEqual(len(self.subscription_calls("StopListening")), 2)

    async def test_follow_up_stops_on_auth_error_and_bounds_connection_failures(self):
        self.module["_PLAYBACK_REFRESH_DELAYS"] = (0, 0, 0)
        self.client.async_request_device_info = AsyncMock(
            side_effect=self.api["MaikaAuthenticationError"]("offline")
        )
        self.coordinator.async_schedule_playback_refresh("one")
        await self.coordinator._playback_refresh_tasks["one"]
        self.assertEqual(self.client.async_request_device_info.await_count, 1)
        self.assertFalse(self.coordinator._playback_refresh_tasks)
        self.client.async_request_device_info = AsyncMock(
            side_effect=self.api["MaikaConnectionError"]("offline")
        )
        self.coordinator.async_schedule_playback_refresh("one")
        await self.coordinator._playback_refresh_tasks["one"]
        self.assertEqual(self.client.async_request_device_info.await_count, 3)
        self.assertFalse(self.coordinator._playback_refresh_tasks)

    async def test_follow_up_is_bounded_coalesced_and_independent_per_speaker(self):
        self.assertEqual(self.module["_PLAYBACK_REFRESH_DELAYS"], (0, 1, 2))
        self.module["_PLAYBACK_REFRESH_DELAYS"] = (0, 0.001, 0.002)
        self.client.async_request_device_info = AsyncMock(return_value=None)
        self.coordinator.async_schedule_playback_refresh("one")
        first = self.coordinator._playback_refresh_tasks["one"]
        self.coordinator.async_schedule_playback_refresh("one")
        replacement = self.coordinator._playback_refresh_tasks["one"]
        self.coordinator.async_schedule_playback_refresh("two")
        second = self.coordinator._playback_refresh_tasks["two"]
        await asyncio.gather(first, replacement, second, return_exceptions=True)
        self.assertTrue(first.cancelled())
        self.assertCountEqual(
            self.client.async_request_device_info.call_args_list,
            [call("one")] * 3 + [call("two")] * 3,
        )
        self.assertFalse(self.coordinator._playback_refresh_tasks)
        self.assertEqual(len(self.tasks), 3)
        self.coordinator.async_schedule_playback_refresh("unknown")
        self.assertEqual(len(self.tasks), 3)

    async def test_follow_up_replacement_cancels_waiter_not_new_task(self):
        self.module["_PLAYBACK_REFRESH_DELAYS"] = (0,)
        started = asyncio.Event()
        self.client.async_send_command.side_effect = lambda *args: started.set()
        self.coordinator.async_schedule_playback_refresh("one")
        old = self.coordinator._playback_refresh_tasks["one"]
        await asyncio.wait_for(started.wait(), 1)
        self.coordinator.async_schedule_playback_refresh("one")
        replacement = self.coordinator._playback_refresh_tasks["one"]
        await asyncio.gather(old, return_exceptions=True)
        self.assertIs(self.coordinator._playback_refresh_tasks["one"], replacement)
        self.report(volume=65)
        await replacement
        self.assertTrue(old.cancelled())
        self.assertFalse(self.client._device_info_waiters)
        self.assertEqual(self.device()["volume"], 65)

    async def test_stop_cancels_all_follow_ups_and_pending_requests(self):
        started = asyncio.Event()
        count = 0

        def command(*args):
            nonlocal count
            count += 1
            if count == 2:
                started.set()

        self.client.async_send_command.side_effect = command
        self.coordinator.async_schedule_playback_refresh("one")
        self.coordinator.async_schedule_playback_refresh("two")
        tasks = list(self.coordinator._playback_refresh_tasks.values())
        await asyncio.wait_for(started.wait(), 1)
        await self.coordinator.async_stop()
        self.assertTrue(all(task.cancelled() for task in tasks))
        self.assertFalse(self.client._device_info_waiters)
        self.assertFalse(self.coordinator._playback_refresh_tasks)
        self.assertFalse(await self.coordinator.async_refresh_live("one"))

    async def test_removed_speaker_cancels_follow_up(self):
        started = asyncio.Event()
        self.client.async_send_command.side_effect = lambda *args: started.set()
        self.coordinator.async_schedule_playback_refresh("two")
        task = self.coordinator._playback_refresh_tasks["two"]
        await asyncio.wait_for(started.wait(), 1)
        self.poll_devices = self.poll_devices[:1]
        self.client.async_request_device_info = AsyncMock(return_value=None)
        await self.poll()
        await asyncio.gather(task, return_exceptions=True)
        self.assertTrue(task.cancelled())
        self.assertNotIn("two", self.coordinator.data["devices"])
        self.assertFalse(self.client._device_info_waiters)

    async def test_voice_diagnostics_rules_and_media_are_independent(self):
        self.client.async_request_device_info = AsyncMock(return_value=None)
        self.entry.options["enable_voice_command_sensor"] = True
        await self.poll()
        self.assertEqual(len(self.subscription_calls(kind="conversation")), 2)
        self.assertEqual(len(self.subscription_calls()), 2)
        self.assertEqual(
            self.coordinator.data["voice_subscription_status"], "subscribed"
        )
        frame = {
            "header": {
                "type": "speakerConversationResponse",
                "rawSpeech": "next song",
                "messageId": "phrase",
            }
        }
        self.client._handle_stream_frame(frame)
        self.client._handle_stream_frame(frame)
        self.assertEqual(self.coordinator._voice_command_sequence, 1)
        self.assertEqual(len(self.coordinator.voice_command_history), 1)
        self.assertEqual(
            self.coordinator.data["last_voice_command"]["text"], "next song"
        )
        self.assertFalse(self.coordinator._playback_refresh_tasks)
        self.assertEqual(self.device()["current_playback"], playback())
        await self.coordinator.async_stop()
        self.assertEqual(
            len(self.subscription_calls("StopListening", "conversation")), 2
        )
        self.assertEqual(len(self.subscription_calls("StopListening")), 2)

    async def test_command_history_is_persisted_after_recognition(self):
        self.entry.options["enable_voice_command_sensor"] = True
        self.client.async_request_device_info = AsyncMock(return_value=None)
        await self.poll()
        frame = {
            "header": {
                "type": "speakerConversationResponse",
                "rawSpeech": "next song",
                "messageId": "phrase",
            }
        }
        self.client._handle_stream_frame(frame)
        task = self.coordinator._history_save_task
        self.assertIsNotNone(task)
        await task
        self.assertEqual(self.coordinator._history_store.saved[0]["text"], "next song")

    async def test_command_history_restores_from_storage(self):
        self.coordinator._history_store.to_load = [
            {
                "text": "bật đèn",
                "normalized": "bat den",
                "received_at": "2024-01-01T00:00:00+00:00",
                "executed": True,
            }
        ]
        await self.coordinator._async_setup()
        self.assertEqual(self.coordinator.voice_command_history[0]["text"], "bật đèn")

    async def test_chat_send_records_turn_and_captures_assistant_reply(self):
        self.client.async_send_voice_text = AsyncMock()
        self.client.async_request_device_info = AsyncMock(return_value=None)
        await self.poll()
        result = await self.coordinator.async_send_chat("one", "bật đèn")
        self.assertTrue(result["ok"])
        self.client.async_send_voice_text.assert_awaited_once_with("one", "bật đèn")
        self.assertEqual(self.coordinator.chat_log[0]["role"], "user")
        frame = {
            "header": {"namespace": "TextToSpeech", "name": "Speak"},
            "response": {"items": [{"simpleResponse": {"displayText": "Đã bật đèn"}}]},
        }
        self.client._handle_stream_frame(frame)
        log = self.coordinator.chat_log
        self.assertEqual(log[-1]["role"], "assistant")
        self.assertEqual(log[-1]["text"], "Đã bật đèn")

    async def test_chat_send_rejects_unknown_speaker_and_empty_message(self):
        self.client.async_send_voice_text = AsyncMock()
        unknown = await self.coordinator.async_send_chat("ghost", "hi")
        self.assertEqual(unknown["error"], "unknown_speaker")
        empty = await self.coordinator.async_send_chat("one", "   ")
        self.assertEqual(empty["error"], "empty_message")
        self.client.async_send_voice_text.assert_not_awaited()

    async def test_voice_rule_execution_and_license_reminder_are_preserved(self):
        options = {
            "enable_voice_command_sensor": True,
            "voice_command_rules": "bật đèn | light.demo | turn_on",
        }
        entry = SimpleNamespace(
            entry_id="rules",
            options=options,
            async_create_background_task=self.create_task,
            runtime_data=SimpleNamespace(
                license_manager=SimpleNamespace(
                    entitlement=SimpleNamespace(license_expires_at=1)
                )
            ),
        )
        self.hass.states = SimpleNamespace(
            get=lambda entity_id: SimpleNamespace(state="off")
        )
        self.hass.services = SimpleNamespace(
            has_service=lambda *args: True, async_call=AsyncMock()
        )
        self.module["ATTR_ENTITY_ID"] = "entity_id"
        self.module["STATE_UNAVAILABLE"] = "unavailable"
        self.module["Context"] = SimpleNamespace
        self.module["has_voice_success_audio"] = lambda options: False
        self.module["resolve_voice_success_audio_timing"] = lambda options: (
            "after_success"
        )
        coordinator = self.module["MaikaDataUpdateCoordinator"](
            self.hass, entry, self.client
        )
        coordinator.data = deepcopy(self.coordinator.data)
        coordinator.async_handle_stream_frame(
            {
                "header": {
                    "type": "speakerConversationResponse",
                    "rawSpeech": "bật đèn",
                    "messageId": "rule-test",
                }
            }
        )
        await self.tasks[-1]
        self.hass.services.async_call.assert_awaited_once()
        self.assertEqual(
            self.hass.services.async_call.call_args.args[:3],
            ("light", "turn_on", {"entity_id": "light.demo"}),
        )
        self.assertTrue(coordinator.data["last_voice_command"]["executed"])
        coordinator._async_check_license_expiry()
        coordinator._async_check_license_expiry()
        self.module["persistent_notification"].async_create.assert_called_once()
        await coordinator.async_stop()

    async def test_unload_and_failed_setup_use_coordinator_stop_before_client(self):
        path = DIRECTORY / "__init__.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        tree.body = [
            node
            for node in tree.body
            if getattr(node, "name", "") in {"async_setup_entry", "async_unload_entry"}
            or (isinstance(node, ast.ImportFrom) and node.module == "__future__")
        ]
        events = []

        namespace = {
            "PLATFORMS": [],
            "async_register_panel": AsyncMock(),
            "MaikaLicenseManager": SimpleNamespace(
                async_create=AsyncMock(return_value=SimpleNamespace())
            ),
            "MaikaLicenseUnavailableError": type("LicenseError", (Exception,), {}),
            "persistent_notification": SimpleNamespace(async_dismiss=Mock()),
            "_LICENSE_NOTIFICATION_ID": "test",
            "async_get_clientsession": lambda hass: OfflineSession(),
            "MaikaApiClient": lambda *args: self.client,
            "MaikaDataUpdateCoordinator": lambda *args: self.coordinator,
            **{
                f"CONF_{name}": name.lower()
                for name in ("PHONE_NUMBER", "PASSWORD", "CLIENT_ID", "SESSION_ID")
            },
        }
        exec(compile(tree, str(path), "exec"), namespace)
        self.hass.config_entries = SimpleNamespace(
            async_unload_platforms=AsyncMock(return_value=False)
        )
        self.entry.runtime_data = SimpleNamespace(
            license_manager=SimpleNamespace(async_stop=AsyncMock()),
            coordinator=SimpleNamespace(async_stop=AsyncMock()),
            client=SimpleNamespace(async_stop=AsyncMock()),
        )
        self.assertFalse(await namespace["async_unload_entry"](self.hass, self.entry))
        self.entry.runtime_data.coordinator.async_stop.assert_not_awaited()
        self.hass.config_entries.async_unload_platforms.return_value = True

        async def stop_license():
            events.append("license")

        async def stop_coordinator():
            events.append("coordinator")

        async def stop_client():
            events.append("client")

        self.entry.runtime_data.license_manager.async_stop.side_effect = stop_license
        self.entry.runtime_data.coordinator.async_stop.side_effect = stop_coordinator
        self.entry.runtime_data.client.async_stop.side_effect = stop_client
        self.assertTrue(await namespace["async_unload_entry"](self.hass, self.entry))
        self.assertEqual(events, ["license", "coordinator", "client"])
        self.entry.data = dict.fromkeys(
            ("phone_number", "password", "client_id", "session_id"), "offline"
        )
        self.client.async_listen_forever = AsyncMock()
        self.coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=RuntimeError("setup failed")
        )
        self.coordinator.async_stop = AsyncMock(side_effect=stop_coordinator)
        self.client.async_stop = AsyncMock(side_effect=stop_client)
        events.clear()
        with self.assertRaisesRegex(RuntimeError, "setup failed"):
            await namespace["async_setup_entry"](self.hass, self.entry)
        self.assertEqual(events, ["coordinator", "client"])

    async def test_voice_read_state_speaks_tts_without_service_call(self):
        options = {
            "enable_voice_command_sensor": True,
            "enable_experimental_cloud_cast": True,
            "voice_response_tts_entity_id": "tts.piper",
            "voice_success_media_player_entity_id": "media_player.one",
            "voice_command_rules": (
                "nhiệt độ phòng khách | sensor.nhiet_do | read\n"
                "bật máy lạnh | climate.phong_khach | set_temperature | "
                '{"temperature":26,"hvac_mode":"cool"}'
            ),
        }
        entry = SimpleNamespace(
            entry_id="rules",
            options=options,
            async_create_background_task=self.create_task,
        )
        sensor_state = SimpleNamespace(
            entity_id="sensor.nhiet_do",
            state="28.5",
            attributes={
                "friendly_name": "Nhiệt độ phòng khách",
                "unit_of_measurement": "°C",
            },
        )
        tts_state = SimpleNamespace(
            entity_id="tts.piper",
            state="idle",
            attributes={"friendly_name": "Piper"},
        )
        known_states = {
            "sensor.nhiet_do": sensor_state,
            "tts.piper": tts_state,
        }
        self.hass.states = SimpleNamespace(
            get=lambda entity_id: known_states.get(entity_id),
            async_entity_ids=lambda domain: ["tts.piper"] if domain == "tts" else [],
        )
        self.hass.services = SimpleNamespace(
            has_service=lambda *args: True,
            async_call=AsyncMock(),
        )
        self.module["Context"] = SimpleNamespace
        self.module["STATE_UNAVAILABLE"] = "unavailable"
        coordinator = self.module["MaikaDataUpdateCoordinator"](
            self.hass, entry, self.client
        )
        coordinator._voice_media_player_for_response = lambda: (
            "media_player.one",
            None,
        )
        rule = coordinator._voice_command_rules["nhiet do phong khach"]
        self.assertTrue(rule.is_read)
        self.assertIsNone(rule.service)
        climate_rule = coordinator._voice_command_rules["bat may lanh"]
        self.assertFalse(climate_rule.is_read)
        self.assertEqual(climate_rule.service, "climate.set_temperature")

        coordinator._record_voice_command(
            "nhiệt độ phòng khách",
            source_session=None,
            message_id="read-test",
            dialog_request_id=None,
            conversation_message_id=None,
            server_message_id=None,
        )
        await self.tasks[-1]

        self.hass.services.async_call.assert_awaited_once()
        domain, service, data = self.hass.services.async_call.call_args.args[:3]
        self.assertEqual((domain, service), ("tts", "speak"))
        self.assertEqual(data["entity_id"], "tts.piper")
        self.assertEqual(data["media_player_entity_id"], "media_player.one")
        self.assertEqual(data["message"], "Nhiệt độ phòng khách là 28,5 độ C.")
        command = coordinator._last_voice_command
        self.assertTrue(command["executed"])
        self.assertIsNone(command["error"])
        self.assertEqual(command["response_text"], data["message"])
        await coordinator.async_stop()

    def test_voice_rules_split_comma_separated_phrases(self):
        rules = self.module["parse_voice_command_rules"](
            "bật điện, bật quạt | switch.den | turn_on"
        )
        self.assertEqual([rule.phrase for rule in rules], ["bật điện", "bật quạt"])
        self.assertTrue(all(rule.entity_id == "switch.den" for rule in rules))
        self.assertTrue(all(rule.action == "turn_on" for rule in rules))

    def test_voice_rules_reject_duplicate_comma_phrase(self):
        with self.assertRaises(self.module["VoiceCommandRulesError"]):
            self.module["parse_voice_command_rules"](
                "bật điện, bật quạt | switch.den | turn_on\n"
                "bật quạt | switch.den | turn_off"
            )

    def test_voice_rules_count_comma_phrases_toward_limit(self):
        limit = self.module["MAX_VOICE_COMMAND_RULES"]
        lines = [f"câu {index} | switch.den | turn_on" for index in range(limit - 1)]
        lines.append("câu cuối, câu vượt | switch.den | turn_on")
        with self.assertRaises(self.module["VoiceCommandRulesError"]):
            self.module["parse_voice_command_rules"]("\n".join(lines))

    def test_voice_rules_rewrite_renamed_entity_without_touching_layout(self):
        text = (
            "# giữ nguyên ghi chú\n"
            "bật đèn | light.old | turn_on\r\n"
            "bật quạt, mở cửa | switch.old | turn_on\n"
        )
        updated = self.module["replace_voice_command_rule_entity_id"](
            text, "light.old", "light.new"
        )
        self.assertEqual(
            updated,
            "# giữ nguyên ghi chú\n"
            "bật đèn | light.new | turn_on\r\n"
            "bật quạt, mở cửa | switch.old | turn_on\n",
        )
        self.assertEqual(
            self.module["replace_voice_command_rule_entity_id"](
                text, "light.missing", "light.new"
            ),
            text,
        )
        self.assertEqual(
            self.module["replace_voice_command_rule_entity_id"](
                text, "light.old", "invalid entity"
            ),
            text,
        )

    def test_entity_registry_rename_updates_voice_rule_options(self):
        options = {
            "voice_command_rules": (
                "bật đèn | light.old | turn_on\nbật quạt | switch.old | turn_on"
            )
        }
        self.entry.options = options
        updates = []
        self.hass.config_entries = SimpleNamespace(
            async_update_entry=lambda entry, **kwargs: updates.append(kwargs)
        )
        self.coordinator.async_handle_entity_registry_updated(
            SimpleNamespace(
                data={
                    "action": "update",
                    "old_entity_id": "light.old",
                    "new_entity_id": "light.new",
                }
            )
        )
        self.assertEqual(len(updates), 1)
        self.assertEqual(
            updates[0]["options"]["voice_command_rules"],
            "bật đèn | light.new | turn_on\nbật quạt | switch.old | turn_on",
        )
        self.coordinator.async_handle_entity_registry_updated(
            SimpleNamespace(
                data={
                    "action": "update",
                    "old_entity_id": "light.missing",
                    "new_entity_id": "light.other",
                }
            )
        )
        self.assertEqual(len(updates), 1)

    def test_voice_state_formats_climate_values(self):
        state = SimpleNamespace(
            entity_id="climate.phong_khach",
            state="cool",
            attributes={
                "friendly_name": "Điều hòa phòng khách",
                "current_temperature": 28.5,
                "current_humidity": 60,
                "temperature": 26,
                "temperature_unit": "°C",
            },
        )
        self.assertEqual(
            self.module["format_voice_state"](state),
            "Điều hòa phòng khách đang làm lạnh. "
            "Nhiệt độ hiện tại 28,5 độ C. "
            "Độ ẩm 60 phần trăm. "
            "Nhiệt độ đặt 26 độ C.",
        )


def validate_live_playback() -> list[str]:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LivePlaybackTests)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(suite)
    return [] if result.wasSuccessful() else [output.getvalue()]


if __name__ == "__main__":
    unittest.main()
