"""MAIKA Content Store (thư viện giải trí) GraphQL client.

Reverse engineered from the MAIKA Android 3.2.3 app
(``com.maika.data.repositoryimpl.APIGraphQLRepositoryImpl`` and the Apollo
operation documents in the ``pi`` package). The app talks to
``https://core.ocs.iviet.com/v1/graphql`` using the same MAIKA user access
token as the REST API, so this client reuses the authentication already
performed by :class:`~.api.MaikaApiClient`.

Only the read operations needed to browse channels, categories and episodes
and to resolve a playable ``audio`` URL are implemented.
"""

from __future__ import annotations

from typing import Any

from .api import MaikaApiClient, MaikaConnectionError

_QUERY_CHANNELS = """
query ContentChannels {
  media_channel(limit: 100, offset: 0, where: { is_enabled: { _eq: true } }) {
    cover id name slug
  }
}
"""

_QUERY_CHANNEL_MEDIAS = """
query ContentChannelMedias($id: Int!, $offset: Int!, $limit: Int!) {
  media_channel_by_pk(id: $id) {
    categories(
      where: { category: { is_published: { _eq: true } } }
      limit: $limit
      offset: $offset
    ) {
      category { description id title }
      medias(limit: 50, offset: 0) {
        media { audio cover description duration id large_cover title type }
      }
    }
  }
}
"""

_QUERY_CATEGORIES = """
query ContentCategories {
  media_type { bg_color description icon value }
}
"""

_QUERY_HIGHLIGHTS = """
query ContentHighlights($offset: Int!, $limit: Int!, $category: String) {
  highlights(limit: $limit, offset: $offset, media_type: $category) {
    cover created_at id is_list slug title type
    content_type { description value }
  }
}
"""

_QUERY_EPISODES = """
query ContentEpisodes($id: Int!, $offset: Int, $limit: Int) {
  media_episode_details(id: $id, limit: $limit, offset: $offset) {
    audio duration id title cover order_no
  }
}
"""

_MAX_ITEMS = 50


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


def normalize_media(item: Any) -> dict[str, Any] | None:
    """Normalize a media/highlight node into a stable shape."""
    media = _as_dict(item)
    media_id = _int(media.get("id"))
    if media_id is None:
        return None
    content_type = _as_dict(media.get("content_type"))
    type_info = _as_dict(media.get("_type"))
    title = (
        _text(media.get("title"))
        or _text(content_type.get("description"))
        or _text(type_info.get("description"))
    )
    return {
        "id": media_id,
        "title": title or f"MAIKA {media_id}",
        "cover": _text(media.get("cover")) or _text(media.get("large_cover")),
        "audio": _text(media.get("audio")),
        "is_list": bool(media.get("is_list")),
        "type": _text(media.get("type")),
    }


def normalize_episode(item: Any) -> dict[str, Any] | None:
    """Normalize an episode node into a playable shape."""
    episode = _as_dict(item)
    episode_id = _int(episode.get("id"))
    audio = _text(episode.get("audio"))
    if episode_id is None or audio is None:
        return None
    return {
        "id": episode_id,
        "title": _text(episode.get("title")) or f"MAIKA {episode_id}",
        "cover": _text(episode.get("cover")),
        "audio": audio,
        "duration": _int(episode.get("duration")),
    }


class MaikaContentStore:
    """Read-only view over the MAIKA Content Store GraphQL API."""

    def __init__(self, client: MaikaApiClient) -> None:
        self._client = client

    async def async_channels(self) -> list[dict[str, Any]]:
        data = await self._client.async_graphql(_QUERY_CHANNELS)
        channels = []
        for entry in _as_list(data.get("media_channel")):
            channel = _as_dict(entry)
            channel_id = _int(channel.get("id"))
            name = _text(channel.get("name"))
            if channel_id is None or name is None:
                continue
            channels.append(
                {
                    "id": channel_id,
                    "name": name,
                    "cover": _text(channel.get("cover")),
                }
            )
        return channels

    async def async_channel_medias(self, channel_id: int) -> list[dict[str, Any]]:
        data = await self._client.async_graphql(
            _QUERY_CHANNEL_MEDIAS,
            {"id": channel_id, "offset": 0, "limit": _MAX_ITEMS},
        )
        channel = _as_dict(data.get("media_channel_by_pk"))
        medias: list[dict[str, Any]] = []
        seen: set[int] = set()
        for group in _as_list(channel.get("categories")):
            for entry in _as_list(_as_dict(group).get("medias")):
                media = normalize_media(_as_dict(entry).get("media"))
                if media is None or media["id"] in seen:
                    continue
                seen.add(media["id"])
                medias.append(media)
        return medias

    async def async_categories(self) -> list[dict[str, Any]]:
        data = await self._client.async_graphql(_QUERY_CATEGORIES)
        categories = []
        for entry in _as_list(data.get("media_type")):
            category = _as_dict(entry)
            value = _text(category.get("value"))
            if value is None:
                continue
            categories.append(
                {
                    "value": value,
                    "title": _text(category.get("description")) or value,
                    "icon": _text(category.get("icon")),
                }
            )
        return categories

    async def async_highlights(
        self, category: str | None = None
    ) -> list[dict[str, Any]]:
        data = await self._client.async_graphql(
            _QUERY_HIGHLIGHTS,
            {"offset": 0, "limit": _MAX_ITEMS, "category": category},
        )
        medias: list[dict[str, Any]] = []
        for entry in _as_list(data.get("highlights")):
            media = normalize_media(entry)
            if media is not None:
                medias.append(media)
        return medias

    async def async_episodes(self, media_id: int) -> list[dict[str, Any]]:
        data = await self._client.async_graphql(
            _QUERY_EPISODES,
            {"id": media_id, "offset": 0, "limit": _MAX_ITEMS},
        )
        episodes: list[dict[str, Any]] = []
        for entry in _as_list(data.get("media_episode_details")):
            episode = normalize_episode(entry)
            if episode is not None:
                episodes.append(episode)
        return episodes


async def async_validate(client: MaikaApiClient) -> bool:
    """Smoke-check that the Content Store responds to a minimal query."""
    try:
        data = await client.async_graphql(_QUERY_CATEGORIES)
    except MaikaConnectionError:
        return False
    return isinstance(data.get("media_type"), list)
