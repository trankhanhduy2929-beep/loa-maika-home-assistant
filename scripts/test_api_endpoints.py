#!/usr/bin/env python3
"""Check the MAIKA REST endpoints used by favorites and reminders."""

from __future__ import annotations

import ast
import io
import runpy
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "custom_components/maika"


def load_api() -> dict:
    path = DIRECTORY / "api.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        node
        for node in tree.body
        if not (
            (isinstance(node, ast.ImportFrom) and node.level > 0)
            or (
                isinstance(node, ast.Import)
                and any(alias.name == "aiohttp" for alias in node.names)
            )
        )
    ]
    const = runpy.run_path(str(DIRECTORY / "const.py"))
    phone = runpy.run_path(str(DIRECTORY / "phone.py"))
    namespace = {
        "__name__": "maika_api_endpoint_test",
        "aiohttp": types.SimpleNamespace(
            ClientError=Exception,
            ClientSession=object,
            ClientTimeout=lambda **kwargs: kwargs,
            ClientResponse=object,
        ),
    }
    namespace.update(
        {
            name: value
            for name, value in const.items()
            if name.isupper() and isinstance(value, (str, int, float, tuple, dict))
        }
    )
    namespace.update(
        {
            "is_email_login_identifier": phone["is_email_login_identifier"],
            "normalize_login_identifier": phone["normalize_login_identifier"],
        }
    )
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


class ApiEndpointTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.module = load_api()
        self.client = self.module["MaikaApiClient"].__new__(
            self.module["MaikaApiClient"]
        )
        self.client._async_request_json = AsyncMock(return_value={})
        self.users = self.module["USERS_BASE_URL"]

    async def test_list_playlist_songs_passes_paging_and_filters_shapes(self):
        self.client._async_request_json.return_value = {
            "data": {"songs": [{"url": "https://cdn/x.mp3"}, None, "bad"]}
        }
        songs = await self.client.async_list_playlist_songs(
            42, page=2, limit=25, order_by="oldest"
        )
        self.assertEqual(songs, [{"url": "https://cdn/x.mp3"}])
        self.client._async_request_json.assert_awaited_once_with(
            "GET",
            f"{self.users}/v1/playlists/42/songs",
            params={"page": 2, "limit": 25, "order_by": "oldest"},
        )

    async def test_list_all_playlist_songs_follows_total_page_and_filters(self):
        self.client._async_request_json.side_effect = [
            {
                "data": {"songs": [{"url": "https://cdn/1.mp3"}, None]},
                "meta_data": {"total_page": 3},
            },
            {
                "data": {"songs": [{"url": "https://cdn/2.mp3"}]},
                "meta_data": {"total_page": 3},
            },
            {
                "data": {"songs": [{"url": "https://cdn/3.mp3"}, "bad"]},
                "meta_data": {"total_page": 3},
            },
        ]
        songs = await self.client.async_list_all_playlist_songs(42, limit=25)
        self.assertEqual(
            songs,
            [
                {"url": "https://cdn/1.mp3"},
                {"url": "https://cdn/2.mp3"},
                {"url": "https://cdn/3.mp3"},
            ],
        )
        self.assertEqual(
            [
                call.kwargs["params"]
                for call in self.client._async_request_json.await_args_list
            ],
            [
                {"page": 1, "limit": 25, "order_by": "latest"},
                {"page": 2, "limit": 25, "order_by": "latest"},
                {"page": 3, "limit": 25, "order_by": "latest"},
            ],
        )

    async def test_list_all_playlist_songs_caps_pages_and_defaults_to_one(self):
        self.client._async_request_json.return_value = {
            "data": {"songs": [{"url": "https://cdn/1.mp3"}]}
        }
        await self.client.async_list_all_playlist_songs(42)
        self.client._async_request_json.assert_awaited_once()

        self.client._async_request_json.reset_mock()
        self.client._async_request_json.side_effect = None
        self.client._async_request_json.return_value = {
            "data": {"songs": []},
            "meta_data": {"total_page": "99"},
        }
        await self.client.async_list_all_playlist_songs(42, max_pages=2)
        self.assertEqual(self.client._async_request_json.await_count, 2)

    async def test_add_song_to_playlist_posts_app_request_shape(self):
        await self.client.async_add_song_to_playlist(
            42,
            singer="Ca sĩ",
            song_id="song-key",
            song_name="Bài hát",
            song_url="https://cdn/song.mp3",
            lyric="https://cdn/lyric.lrc",
            image_url="https://cdn/cover.jpg",
        )
        self.client._async_request_json.assert_awaited_once_with(
            "POST",
            f"{self.users}/v1/playlists/42/songs",
            json_body={
                "singer": "Ca sĩ",
                "song_id": "song-key",
                "song_name": "Bài hát",
                "song_url": "https://cdn/song.mp3",
                "lyric": "https://cdn/lyric.lrc",
                "source": "nct",
                "status": 1,
                "imageURL": "https://cdn/cover.jpg",
            },
        )

    async def test_list_reminders_uses_get_and_returns_groups(self):
        self.client._async_request_json.return_value = {
            "data": [{"listReminders": []}, None, "bad"]
        }
        groups = await self.client.async_list_reminders()
        self.assertEqual(groups, [{"listReminders": []}])
        self.client._async_request_json.assert_awaited_once_with(
            "GET",
            f"{self.users}/v1/reminder",
            params={"page": 0, "limit": 1000},
        )

    async def test_create_and_delete_reminder_wire_format(self):
        await self.client.async_create_reminder({"event": "Họp"})
        self.client._async_request_json.assert_awaited_once_with(
            "POST", f"{self.users}/v1/reminder", json_body={"event": "Họp"}
        )
        self.client._async_request_json.reset_mock()
        await self.client.async_delete_reminder("17")
        self.client._async_request_json.assert_awaited_once_with(
            "DELETE",
            f"{self.users}/v1/reminder/17",
            json_body={
                "executor": "vn_south",
                "all": False,
                "reminder_ids": [17],
            },
        )

    async def test_update_toggle_mute_and_multi_delete_wire_format(self):
        await self.client.async_update_reminder("17", {"status": 2}, not_sync=True)
        self.client._async_request_json.assert_awaited_once_with(
            "PUT",
            f"{self.users}/v1/reminder/17",
            params={"not_sync": "true"},
            json_body={"status": 2},
        )
        self.client._async_request_json.reset_mock()
        await self.client.async_mute_reminders([3, "4"], ["2026-11-01"])
        self.client._async_request_json.assert_awaited_once_with(
            "POST",
            f"{self.users}/v1/reminder/mute",
            json_body={
                "executor": "vn_south",
                "mute_days": ["2026-11-01"],
                "reminder_ids": [3, 4],
            },
        )
        self.client._async_request_json.reset_mock()
        await self.client.async_delete_reminders(["3", 4])
        self.client._async_request_json.assert_awaited_once_with(
            "DELETE",
            f"{self.users}/v1/reminder",
            json_body={
                "executor": "vn_south",
                "all": False,
                "reminder_ids": [3, 4],
            },
        )

    async def test_missing_shapes_return_empty_lists(self):
        self.client._async_request_json.return_value = {"data": None}
        self.assertEqual(await self.client.async_list_playlist_songs(1), [])
        self.assertEqual(await self.client.async_list_reminders(), [])


def validate_api_endpoints() -> list[str]:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ApiEndpointTests)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(suite)
    return [] if result.wasSuccessful() else [output.getvalue()]


if __name__ == "__main__":
    unittest.main()
