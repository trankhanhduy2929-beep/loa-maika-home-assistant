from __future__ import annotations

import io
import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "custom_components/maika/nhaccuatui.py"))
MaikaNhacCuaTui = MODULE["MaikaNhacCuaTui"]
parse_nct_song_key = MODULE["parse_nct_song_key"]


class FakeClient:
    def __init__(self, responses):
        self._responses = responses
        self.calls: list[tuple[str, dict]] = []

    async def async_nct_json(self, path, params=None):
        self.calls.append((path, params or {}))
        response = self._responses.get(path)
        if isinstance(response, Exception):
            raise response
        if response is None:
            raise AssertionError(f"unexpected path: {path}")
        return response


def stream(url, kind, *, vip=False, status=1):
    return {
        "stream": url,
        "type": kind,
        "onlyVIP": vip,
        "status": status,
    }


FEED_RESPONSE = {
    "code": 0,
    "data": {
        "list": [
            {
                "key": "Track0001",
                "name": "Bài mới",
                "artistName": "Ca sĩ",
                "image": "https://cdn/cover.jpg",
                "duration": "180",
                "streamURL": [
                    stream("https://stream/128.mp3", "128"),
                    stream("https://stream/320.mp3", "320"),
                    stream("https://stream/lossless.flac", "lossless", vip=True),
                    stream("https://stream/broken.mp3", "128", status=0),
                ],
            },
            {"key": "", "name": "Broken"},
            {"key": "Track0002", "name": "VIP only", "streamURL": []},
        ]
    },
}

CHARTS_RESPONSE = {
    "code": 0,
    "data": [
        {
            "key": "chart-1",
            "title": "Top 50",
            "image": "https://cdn/chart.jpg",
            "items": [
                {"key": "Track0003", "name": "Chart song", "artistName": "A"},
            ],
        },
        {"key": "", "title": "Broken"},
    ],
}

CHART_TRACKS_RESPONSE = {
    "code": 0,
    "data": [
        {"key": "Track0004", "name": "Full chart", "artistName": "B"},
    ],
}

SEARCH_RESPONSE = {
    "code": 0,
    "data": {
        "songs": [
            {
                "key": "Track0006",
                "name": "Tìm thấy",
                "artistName": "Sơn Tùng",
                "image": "https://cdn/search.jpg",
                "duration": "210",
                "streamURL": [stream("https://stream/search-320.mp3", "320")],
            },
            {"key": "", "name": "Broken"},
        ]
    },
}

SONG_RESPONSE = {
    "code": 0,
    "data": {
        "key": "Track0005",
        "name": "Chi tiết",
        "artistName": "C",
        "image": "https://cdn/song.jpg",
        "duration": 200,
        "streamURL": [
            stream("https://stream/song-128.mp3", "128"),
            stream("https://stream/song-320.mp3", "320"),
        ],
    },
}


class NhacCuaTuiTests(unittest.IsolatedAsyncioTestCase):
    def store(self, responses):
        self.client = FakeClient(responses)
        return MaikaNhacCuaTui(self.client)

    async def test_feed_normalizes_and_prefers_320(self):
        store = self.store({"/api/v1/song/feed": FEED_RESPONSE})
        tracks = await store.async_feed()
        self.assertEqual([track["key"] for track in tracks], ["Track0001", "Track0002"])
        self.assertEqual(tracks[0]["title"], "Bài mới")
        self.assertEqual(tracks[0]["artist"], "Ca sĩ")
        self.assertEqual(tracks[0]["duration"], 180)
        self.assertEqual(tracks[0]["stream_url"], "https://stream/320.mp3")
        self.assertIsNone(tracks[1]["stream_url"])
        self.assertEqual(
            self.client.calls[0],
            ("/api/v1/song/feed", {"pageindex": 1, "pagesize": 50}),
        )

    async def test_charts_list_and_full_chart(self):
        store = self.store(
            {
                "/api/v1/playlist/charts": CHARTS_RESPONSE,
                "/api/v1/app/charts/more": CHART_TRACKS_RESPONSE,
            }
        )
        charts = await store.async_charts()
        self.assertEqual(len(charts), 1)
        self.assertEqual(charts[0]["key"], "chart-1")
        self.assertEqual(charts[0]["tracks"][0]["title"], "Chart song")
        tracks = await store.async_chart_tracks("chart-1")
        self.assertEqual(tracks[0]["key"], "Track0004")
        self.assertEqual(
            self.client.calls[1],
            (
                "/api/v1/app/charts/more",
                {"chartKey": "chart-1", "pageindex": 1, "pagesize": 50},
            ),
        )

    async def test_search_normalizes_and_skips_blank(self):
        store = self.store({"/api/v1/search/song": SEARCH_RESPONSE})
        tracks = await store.async_search("  Sơn Tùng  ")
        self.assertEqual([track["key"] for track in tracks], ["Track0006"])
        self.assertEqual(tracks[0]["title"], "Tìm thấy")
        self.assertEqual(tracks[0]["artist"], "Sơn Tùng")
        self.assertEqual(tracks[0]["stream_url"], "https://stream/search-320.mp3")
        self.assertEqual(
            self.client.calls[0],
            (
                "/api/v1/search/song",
                {
                    "keyword": "Sơn Tùng",
                    "pageindex": 1,
                    "pagesize": 50,
                    "correct": "false",
                },
            ),
        )

    async def test_blank_search_skips_request(self):
        store = self.store({})
        self.assertEqual(await store.async_search("   "), [])
        self.assertEqual(self.client.calls, [])

    async def test_song_detail_and_missing_key(self):
        store = self.store({"/api/v1/song/detail/Track0005": SONG_RESPONSE})
        track = await store.async_song("Track0005")
        self.assertEqual(track["title"], "Chi tiết")
        self.assertEqual(track["stream_url"], "https://stream/song-320.mp3")

    def test_parse_song_key_from_urls_and_prefix(self):
        self.assertEqual(
            parse_nct_song_key("https://www.nhaccuatui.com/song/Track0001"),
            "Track0001",
        )
        self.assertEqual(
            parse_nct_song_key(
                "https://www.nhaccuatui.com/bai-hat/ten-bai-hat.abcdef123456.html"
            ),
            "abcdef123456",
        )
        self.assertEqual(parse_nct_song_key("nct:Track0001"), "Track0001")
        self.assertIsNone(parse_nct_song_key("https://example.com/song/Track0001"))
        self.assertIsNone(parse_nct_song_key("Track0001"))
        self.assertIsNone(parse_nct_song_key("nct:../bad"))


def validate_nhaccuatui() -> list[str]:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(NhacCuaTuiTests)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(suite)
    return [] if result.wasSuccessful() else [output.getvalue()]


if __name__ == "__main__":
    unittest.main()
