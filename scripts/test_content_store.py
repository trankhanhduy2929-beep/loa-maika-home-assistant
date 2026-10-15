from __future__ import annotations

import ast
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "custom_components/maika"


class MaikaConnectionError(Exception):
    pass


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


def load_content_store():
    return load_code(
        "content_store.py",
        {
            "MaikaApiClient": object,
            "MaikaConnectionError": MaikaConnectionError,
            "__name__": "maika_content_store_test",
        },
    )


class FakeClient:
    def __init__(self, responses):
        self._responses = responses
        self.calls: list[tuple[str, dict]] = []

    async def async_graphql(self, query, variables=None):
        self.calls.append((query, variables or {}))
        for marker, response in self._responses.items():
            if marker in query:
                if isinstance(response, Exception):
                    raise response
                return response
        raise AssertionError(f"unexpected query: {query}")


CHANNELS_RESPONSE = {
    "media_channel": [
        {
            "id": 7,
            "name": "VOV Giao thông",
            "cover": "https://cdn/7.png",
            "slug": "vov",
        },
        {"id": "9", "name": "Radio Hà Nội", "cover": None},
        {"id": None, "name": "Broken"},
        {"id": 11, "name": "   "},
    ]
}

CHANNEL_MEDIAS_RESPONSE = {
    "media_channel_by_pk": {
        "categories": [
            {
                "category": {"id": 1, "title": "Tin tức"},
                "medias": [
                    {
                        "media": {
                            "id": 100,
                            "title": "Bản tin sáng",
                            "audio": "https://cdn/100.mp3",
                        }
                    },
                    {"media": {"id": 101, "title": "Bản tin tối", "audio": None}},
                ],
            },
            {
                "category": {"id": 2, "title": "Khác"},
                "medias": [
                    {
                        "media": {
                            "id": 100,
                            "title": "Bản tin sáng",
                            "audio": "https://cdn/100.mp3",
                        }
                    },
                ],
            },
        ]
    }
}

CATEGORIES_RESPONSE = {
    "media_type": [
        {"value": "Podcast", "description": "Podcast", "icon": "mic"},
        {"value": "Radio", "description": "Radio"},
        {"value": None, "description": "Ignore"},
    ]
}

HIGHLIGHTS_RESPONSE = {
    "highlights": [
        {
            "id": 200,
            "title": "Series A",
            "is_list": True,
            "cover": "https://cdn/200.png",
        },
        {"id": 201, "title": None, "type": "audio"},
        {"id": "bad"},
    ]
}

EPISODES_RESPONSE = {
    "media_episode_details": [
        {
            "id": 300,
            "title": "Tập 1",
            "audio": "https://cdn/300.mp3",
            "duration": "1800",
        },
        {"id": 301, "title": "Tập 2", "audio": None},
        {"id": None, "audio": "https://cdn/x.mp3"},
    ]
}


class ContentStoreTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.module = load_content_store()

    def store(self, responses):
        self.client = FakeClient(responses)
        return self.module["MaikaContentStore"](self.client)

    async def test_channels_parse_and_skip_invalid(self):
        store = self.store({"media_channel(": CHANNELS_RESPONSE})
        channels = await store.async_channels()
        self.assertEqual(
            channels,
            [
                {"id": 7, "name": "VOV Giao thông", "cover": "https://cdn/7.png"},
                {"id": 9, "name": "Radio Hà Nội", "cover": None},
            ],
        )

    async def test_channel_medias_flatten_and_dedupe(self):
        store = self.store({"media_channel_by_pk": CHANNEL_MEDIAS_RESPONSE})
        medias = await store.async_channel_medias(7)
        self.assertEqual([media["id"] for media in medias], [100, 101])
        self.assertEqual(medias[0]["audio"], "https://cdn/100.mp3")
        self.assertIsNone(medias[1]["audio"])
        _query, variables = self.client.calls[0]
        self.assertEqual(variables, {"id": 7, "offset": 0, "limit": 50})

    async def test_categories_parse_and_skip_missing_value(self):
        store = self.store({"media_type {": CATEGORIES_RESPONSE})
        categories = await store.async_categories()
        self.assertEqual(
            categories,
            [
                {"value": "Podcast", "title": "Podcast", "icon": "mic"},
                {"value": "Radio", "title": "Radio", "icon": None},
            ],
        )

    async def test_highlights_normalize_and_pass_category(self):
        store = self.store({"highlights(": HIGHLIGHTS_RESPONSE})
        medias = await store.async_highlights("Podcast")
        self.assertEqual([media["id"] for media in medias], [200, 201])
        self.assertTrue(medias[0]["is_list"])
        self.assertEqual(medias[0]["title"], "Series A")
        self.assertEqual(medias[1]["title"], "MAIKA 201")
        self.assertEqual(self.client.calls[0][1]["category"], "Podcast")

    async def test_episodes_require_audio(self):
        store = self.store({"media_episode_details": EPISODES_RESPONSE})
        episodes = await store.async_episodes(200)
        self.assertEqual([episode["id"] for episode in episodes], [300])
        self.assertEqual(episodes[0]["duration"], 1800)
        self.assertEqual(self.client.calls[0][1], {"id": 200, "offset": 0, "limit": 50})

    async def test_validate_true_and_false(self):
        store = self.store({"media_type {": CATEGORIES_RESPONSE})
        self.assertTrue(await self.module["async_validate"](store._client))
        failing = self.store({"media_type {": MaikaConnectionError("boom")})
        self.assertFalse(await self.module["async_validate"](failing._client))


def validate_content_store() -> list[str]:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContentStoreTests)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(suite)
    return [] if result.wasSuccessful() else [output.getvalue()]


if __name__ == "__main__":
    unittest.main()
