"""Browse and resolve public NhacCuaTui music."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote, urlsplit

_NCT_KEY = re.compile(r"^[A-Za-z0-9]{6,32}$")
_NCT_SONG_PATH = re.compile(r"/song/([A-Za-z0-9]{6,32})")
_NCT_LEGACY_SONG_PATH = re.compile(r"[.-]([A-Za-z0-9]{6,32})\.html$")
_STREAM_TYPE_ORDER = {"320": 0, "128": 1, "lossless": 2}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def _stream_url(media: dict[str, Any]) -> str | None:
    options = []
    for raw in _as_list(media.get("streamURL")):
        option = _as_dict(raw)
        stream = _text(option.get("stream"))
        if option.get("status") != 1 or not stream:
            continue
        if not stream.startswith(("http://", "https://")):
            continue
        options.append((option, stream))
    options.sort(
        key=lambda item: (
            1 if item[0].get("onlyVIP") else 0,
            _STREAM_TYPE_ORDER.get(str(item[0].get("type")), 3),
        )
    )
    return options[0][1] if options else None


def _track(value: Any) -> dict[str, Any] | None:
    media = _as_dict(value)
    key = _text(media.get("key"))
    if key is None:
        return None
    return {
        "key": key,
        "title": _text(media.get("name")) or _text(media.get("title")) or key,
        "artist": _text(media.get("artistName")),
        "cover": _text(media.get("image")) or _text(media.get("imageShare")),
        "duration": _int(media.get("duration")),
        "stream_url": _stream_url(media),
    }


def _tracks(value: Any) -> list[dict[str, Any]]:
    tracks = []
    for item in _as_list(value):
        track = _track(item)
        if track is not None:
            tracks.append(track)
    return tracks


def parse_nct_song_key(value: Any) -> str | None:
    """Return a NhacCuaTui song key from a key, nct: key, or song URL."""
    text = str(value or "").strip()
    if not text:
        return None
    if text.lower().startswith("nct:"):
        key = text[4:].strip()
        return key if _NCT_KEY.fullmatch(key) else None
    split = urlsplit(text)
    host = (split.hostname or "").lower()
    if host != "nhaccuatui.com" and not host.endswith(".nhaccuatui.com"):
        return None
    path = unquote(split.path)
    match = _NCT_SONG_PATH.search(path) or _NCT_LEGACY_SONG_PATH.search(path)
    return match.group(1) if match else None


class MaikaNhacCuaTui:
    """Small client for the public NhacCuaTui JSON API."""

    def __init__(self, client) -> None:
        self._client = client

    async def async_feed(self, limit: int = 50) -> list[dict[str, Any]]:
        payload = await self._client.async_nct_json(
            "/api/v1/song/feed",
            {"pageindex": 1, "pagesize": limit},
        )
        return _tracks(_as_dict(payload.get("data")).get("list"))

    async def async_charts(self) -> list[dict[str, Any]]:
        payload = await self._client.async_nct_json(
            "/api/v1/playlist/charts",
            {"pageindex": 1, "pagesize": 20},
        )
        charts = []
        for item in _as_list(payload.get("data")):
            chart = _as_dict(item)
            key = _text(chart.get("key"))
            title = (
                _text(chart.get("title"))
                or _text(chart.get("titleDetail"))
                or _text(chart.get("name"))
            )
            if key is None or title is None:
                continue
            charts.append(
                {
                    "key": key,
                    "title": title,
                    "cover": _text(chart.get("image")) or _text(chart.get("cover")),
                    "tracks": _tracks(chart.get("items")),
                }
            )
        return charts

    async def async_chart_tracks(self, chart_key: str) -> list[dict[str, Any]]:
        payload = await self._client.async_nct_json(
            "/api/v1/app/charts/more",
            {"chartKey": chart_key, "pageindex": 1, "pagesize": 50},
        )
        return _tracks(payload.get("data"))

    async def async_search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        keyword = str(query or "").strip()
        if not keyword:
            return []
        payload = await self._client.async_nct_json(
            "/api/v1/search/song",
            {
                "keyword": keyword,
                "pageindex": 1,
                "pagesize": limit,
                "correct": "false",
            },
        )
        return _tracks(_as_dict(payload.get("data")).get("songs"))

    async def async_song(self, key: str) -> dict[str, Any] | None:
        payload = await self._client.async_nct_json(f"/api/v1/song/detail/{key}")
        return _track(payload.get("data"))
