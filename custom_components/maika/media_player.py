"""Media player entities for MAIKA speakers."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote, unquote, urlsplit

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    BrowseError,
    BrowseMedia,
    MediaClass,
    MediaPlayerDeviceClass,
    MediaPlayerEnqueue,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    async_process_play_media_url,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import MaikaConfigEntry
from .api import MaikaApiError
from .cast_target import cast_ready_url
from .const import CONF_CLOUD_CAST_BASE_URL, CONF_ENABLE_CLOUD_CAST, DOMAIN
from .content_store import MaikaContentStore
from .entity import MaikaCommandEntity
from .media_url import is_valid_http_media_url

_BASE_SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.BROWSE_MEDIA
)
_CLOUD_CAST_SUPPORTED_FEATURES = MediaPlayerEntityFeature.SEEK
_CLOUD_CAST_STREAM_FORMATS = {
    "application/ogg": "AUDIO_MPEG",
    "application/octet-stream": "AUDIO_MPEG",
    "audio": "AUDIO_MPEG",
    "audio/aac": "AUDIO_MPEG",
    "audio/aacp": "AUDIO_MPEG",
    "audio/flac": "AUDIO_MPEG",
    "audio/m4a": "AUDIO_MPEG",
    "audio/mp3": "AUDIO_MPEG",
    "audio/mp4": "AUDIO_MPEG",
    "audio/mp4a-latm": "AUDIO_MPEG",
    "audio/mpeg": "AUDIO_MPEG",
    "audio/mpegurl": "AUDIO_MPEG",
    "audio/ogg": "AUDIO_MPEG",
    "audio/opus": "AUDIO_MPEG",
    "audio/vnd.wave": "AUDIO_MPEG",
    "audio/wav": "AUDIO_MPEG",
    "audio/wave": "AUDIO_MPEG",
    "audio/webm": "AUDIO_MPEG",
    "audio/x-aac": "AUDIO_MPEG",
    "audio/x-flac": "AUDIO_MPEG",
    "audio/x-m4a": "AUDIO_MPEG",
    "audio/x-mpeg": "AUDIO_MPEG",
    "audio/x-mpegurl": "AUDIO_MPEG",
    "audio/x-wav": "AUDIO_MPEG",
    "music": "AUDIO_MPEG",
    "url": "AUDIO_MPEG",
}
_DEFAULT_UNMUTE_VOLUME = 0.3
_MEDIA_ROOT = "maika_root"
_MEDIA_PLAYLIST = "maika_playlist"
_MEDIA_SONG = "maika_song"
_MEDIA_CS_ROOT = "maika_cs_root"
_MEDIA_CS_CHANNELS = "maika_cs_channels"
_MEDIA_CS_CATEGORIES = "maika_cs_categories"
_MEDIA_CS_HIGHLIGHTS = "maika_cs_highlights"
_MEDIA_CS_CHANNEL_PREFIX = "maika_cs_channel:"
_MEDIA_CS_CATEGORY_PREFIX = "maika_cs_category:"
_MEDIA_CS_MEDIA_PREFIX = "maika_cs_media:"
_MEDIA_CS_TRACK = "maika_cs_track"
_CS_ROOT_TITLE = "Thư viện giải trí MAIKA"
_CS_CHANNELS_TITLE = "Kênh"
_CS_CATEGORIES_TITLE = "Thể loại"
_CS_HIGHLIGHTS_TITLE = "Nổi bật"
_QUEUE_TITLE = "Danh sách trên loa MAIKA"
_MAX_SONG_KEY_BYTES = 512
_MAX_QUEUE_ITEM_ID_LENGTH = 71 + _MAX_SONG_KEY_BYTES * 3
_QUEUE_ITEM_ID_PATTERN = re.compile(r"maika:([0-9a-f]{64}):([A-Za-z0-9_.~%\-]+)")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MaikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MAIKA media players."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        MaikaMediaPlayer(coordinator, serial_number)
        for serial_number in coordinator.data["devices"]
    )


class MaikaMediaPlayer(MaikaCommandEntity, MediaPlayerEntity):
    """Control playback and volume on a MAIKA speaker."""

    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_media_image_remotely_accessible = True
    _attr_volume_step = 0.05

    def __init__(self, coordinator, serial_number) -> None:
        super().__init__(coordinator, serial_number, "media_player")
        self._position_updated_at: datetime | None = None
        self._reported_playback: tuple[Any, ...] | None = None
        self._volume_before_mute: float | None = None
        self._last_cast_media: dict[str, Any] | None = None
        self._content_store = MaikaContentStore(coordinator.client)
        self._cloud_cast_enabled = bool(
            coordinator.entry.options.get(CONF_ENABLE_CLOUD_CAST, False)
        )
        self._attr_supported_features = _BASE_SUPPORTED_FEATURES
        if self._cloud_cast_enabled:
            self._attr_supported_features |= _CLOUD_CAST_SUPPORTED_FEATURES
        self._update_position_timestamp()

    @property
    def _cast_base_url(self) -> str:
        """Return the user pinned base URL for speaker media downloads."""
        return str(
            self.coordinator.entry.options.get(CONF_CLOUD_CAST_BASE_URL, "") or ""
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Keep the timestamp tied to the reported playback, not volume updates."""
        self._update_position_timestamp()
        super()._handle_coordinator_update()

    @callback
    def _update_position_timestamp(self) -> None:
        """Refresh the time anchor when position, state or track changes."""
        playback = (
            self.state,
            self.media_position,
            self.media_content_id,
            self.media_title,
        )
        if playback != self._reported_playback:
            self._reported_playback = playback
            self._position_updated_at = (
                datetime.now(dt_util.UTC) if self.media_position is not None else None
            )

    @property
    def state(self) -> MediaPlayerState:
        """Return current playback state."""
        status = str(self._current_playback.get("status") or "").lower()
        if status in {"start", "started", "resume", "resumed", "playing"}:
            return MediaPlayerState.PLAYING
        if status in {"pause", "paused"}:
            return MediaPlayerState.PAUSED
        return MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        """Return volume normalized to Home Assistant's 0..1 range."""
        volume = self.device.get("volume")
        if volume is None:
            return None
        try:
            return max(0.0, min(1.0, float(volume) / 100.0))
        except (TypeError, ValueError):
            return None

    @property
    def is_volume_muted(self) -> bool | None:
        """Return whether speaker output volume is muted."""
        volume = self.volume_level
        return volume == 0 if volume is not None else None

    @property
    def media_content_id(self) -> str | None:
        """Return the current MAIKA media identifier or URL."""
        attributes = self._playback_attributes
        return self._first_string(
            attributes.get("url"),
            attributes.get("mediaId"),
            attributes.get("media_id"),
            attributes.get("key"),
            attributes.get("songKey"),
            attributes.get("id"),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes = self._playback_attributes
        key = next(
            (
                key
                for field in ("key", "songKey", "id")
                if (key := self._valid_song_key(attributes.get(field))) is not None
            ),
            None,
        )
        if key is None:
            return {}
        result = {"maika_song_key": key}
        playlist, songs = self._native_playlist()
        if any(song.get("songKey") == key for song in songs):
            result["maika_queue_item_id"] = self._queue_item_id(
                self._queue_revision(playlist), key
            )
        return result

    @property
    def media_title(self) -> str | None:
        """Return current media title."""
        attributes = self._playback_attributes
        return self._first_string(
            attributes.get("song"),
            attributes.get("title"),
            attributes.get("name"),
        )

    @property
    def media_artist(self) -> str | None:
        """Return current media artist or narrator."""
        attributes = self._playback_attributes
        return self._first_string(attributes.get("artist"), attributes.get("narrator"))

    @property
    def media_album_name(self) -> str | None:
        """Return current media album."""
        return self._first_string(self._playback_attributes.get("album"))

    @property
    def media_image_url(self) -> str | None:
        """Return current media artwork URL."""
        attributes = self._playback_attributes
        direct_url = self._first_string(
            attributes.get("imageURL"), attributes.get("image_url")
        )
        if direct_url:
            return direct_url
        image = attributes.get("image")
        if isinstance(image, dict):
            return self._first_string(
                image.get("url"), image.get("src"), image.get("imageURL")
            )
        return None

    @property
    def media_content_type(self) -> str | None:
        """Return the MAIKA media type when available."""
        attributes = self._playback_attributes
        return self._first_string(
            attributes.get("mediaType"),
            attributes.get("media_type"),
            attributes.get("type"),
        )

    @property
    def media_playlist(self) -> str | None:
        """Return the latest MAIKA playlist title or identifier."""
        playlist = self.device.get("latest_playlist")
        if not isinstance(playlist, dict):
            return None
        return self._first_string(
            playlist.get("title"), playlist.get("listKey"), playlist.get("item")
        )

    @property
    def media_position(self) -> float | None:
        """Return playback position in seconds."""
        payload = self._current_playback.get("payload")
        if not isinstance(payload, dict):
            return None
        value = payload.get("offsetInMilliseconds")
        try:
            seconds = float(value) / 1000.0
        except (TypeError, ValueError):
            return None
        return max(0.0, seconds) if math.isfinite(seconds) else None

    @property
    def media_position_updated_at(self) -> datetime | None:
        """Return the timestamp associated with playback position."""
        if self.media_position is None:
            return None
        return self._position_updated_at

    @property
    def media_duration(self) -> float | None:
        """Return total track length in seconds when the speaker reports it."""
        payload = self._current_playback.get("payload")
        if not isinstance(payload, dict):
            return None
        value = payload.get("durationInMilliseconds")
        if value is None:
            value = payload.get("durationInMillis")
        try:
            seconds = float(value) / 1000.0
        except (TypeError, ValueError):
            return None
        return seconds if math.isfinite(seconds) and seconds > 0 else None

    async def async_set_volume_level(self, volume: float) -> None:
        """Set speaker playback volume."""
        normalized_volume = max(0.0, min(1.0, volume))
        target = round(normalized_volume * 100)
        if target > 0:
            self._volume_before_mute = target / 100
        await self.coordinator.client.async_set_volume(self.serial_number, target)
        self.coordinator.async_update_device_data(
            self.serial_number, {"volume": target}
        )
        self._schedule_live_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or restore speaker output using its volume control."""
        current_volume = self.volume_level
        if mute:
            if current_volume is not None and current_volume > 0:
                self._volume_before_mute = current_volume
            await self.async_set_volume_level(0)
            return

        if current_volume is not None and current_volume > 0:
            return
        restore_volume = self._volume_before_mute or _DEFAULT_UNMUTE_VOLUME
        await self.async_set_volume_level(restore_volume)

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        if (
            media_content_type == _MEDIA_PLAYLIST
            and media_content_id == _MEDIA_PLAYLIST
        ):
            return await self._async_browse_playlist()
        if media_content_id and media_content_id.startswith("maika_cs_"):
            return await self._async_browse_content_store(media_content_id)
        if media_content_id and media_source.is_media_source_id(media_content_id):
            return await self._async_browse_sources(media_content_id)
        if (not media_content_type and not media_content_id) or (
            media_content_type == _MEDIA_ROOT and media_content_id == _MEDIA_ROOT
        ):
            children = [await self._async_browse_playlist()]
            if self._cloud_cast_enabled:
                children.append(await self._async_browse_sources(None))
            children.append(self._content_store_root())
            return BrowseMedia(
                media_class=MediaClass.DIRECTORY,
                media_content_type=_MEDIA_ROOT,
                media_content_id=_MEDIA_ROOT,
                title="MAIKA",
                can_play=False,
                can_expand=True,
                children=children,
            )
        raise BrowseError(
            translation_domain=DOMAIN,
            translation_key="maika_queue_invalid_selection",
        )

    def _content_store_root(self) -> BrowseMedia:
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_type=_MEDIA_CS_ROOT,
            media_content_id=_MEDIA_CS_ROOT,
            title=_CS_ROOT_TITLE,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
            children=[
                self._cs_directory(_MEDIA_CS_CHANNELS, _CS_CHANNELS_TITLE),
                self._cs_directory(_MEDIA_CS_CATEGORIES, _CS_CATEGORIES_TITLE),
                self._cs_directory(_MEDIA_CS_HIGHLIGHTS, _CS_HIGHLIGHTS_TITLE),
            ],
        )

    @staticmethod
    def _cs_directory(media_id: str, title: str) -> BrowseMedia:
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_type=media_id,
            media_content_id=media_id,
            title=title,
            can_play=False,
            can_expand=True,
        )

    async def _async_browse_content_store(self, media_content_id: str) -> BrowseMedia:
        if not self.available:
            raise BrowseError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_unavailable",
            )
        try:
            if media_content_id == _MEDIA_CS_ROOT:
                return self._content_store_root()
            if media_content_id == _MEDIA_CS_CHANNELS:
                return await self._async_browse_cs_channels()
            if media_content_id == _MEDIA_CS_CATEGORIES:
                return await self._async_browse_cs_categories()
            if media_content_id == _MEDIA_CS_HIGHLIGHTS:
                return await self._async_browse_cs_highlights(
                    None, _CS_HIGHLIGHTS_TITLE
                )
            if media_content_id.startswith(_MEDIA_CS_CHANNEL_PREFIX):
                channel_id = self._cs_int(media_content_id, _MEDIA_CS_CHANNEL_PREFIX)
                return await self._async_browse_cs_channel_medias(
                    channel_id, _CS_CHANNELS_TITLE
                )
            if media_content_id.startswith(_MEDIA_CS_CATEGORY_PREFIX):
                value = media_content_id[len(_MEDIA_CS_CATEGORY_PREFIX) :]
                return await self._async_browse_cs_highlights(value, value)
            if media_content_id.startswith(_MEDIA_CS_MEDIA_PREFIX):
                media_id = self._cs_int(media_content_id, _MEDIA_CS_MEDIA_PREFIX)
                return await self._async_browse_cs_episodes(media_id)
        except MaikaApiError as err:
            raise BrowseError(
                translation_domain=DOMAIN,
                translation_key="maika_content_store_failed",
            ) from err
        raise BrowseError(
            translation_domain=DOMAIN,
            translation_key="maika_content_store_invalid_selection",
        )

    @staticmethod
    def _cs_int(media_id: str, prefix: str) -> int:
        raw = media_id[len(prefix) :]
        if not raw.lstrip("-").isdigit():
            raise BrowseError(
                translation_domain=DOMAIN,
                translation_key="maika_content_store_invalid_selection",
            )
        return int(raw)

    @staticmethod
    def _cs_cover(cover: str | None) -> str | None:
        return cover if cover and is_valid_http_media_url(cover) else None

    async def _async_browse_cs_channels(self) -> BrowseMedia:
        channels = await self._content_store.async_channels()
        children = [
            BrowseMedia(
                media_class=MediaClass.CHANNEL,
                media_content_type=f"{_MEDIA_CS_CHANNEL_PREFIX}{channel['id']}",
                media_content_id=f"{_MEDIA_CS_CHANNEL_PREFIX}{channel['id']}",
                title=channel["name"],
                can_play=False,
                can_expand=True,
                thumbnail=self._cs_cover(channel.get("cover")),
            )
            for channel in channels
        ]
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_type=_MEDIA_CS_CHANNELS,
            media_content_id=_MEDIA_CS_CHANNELS,
            title=_CS_CHANNELS_TITLE,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.CHANNEL,
            children=children,
        )

    async def _async_browse_cs_categories(self) -> BrowseMedia:
        categories = await self._content_store.async_categories()
        children = [
            BrowseMedia(
                media_class=MediaClass.GENRE,
                media_content_type=f"{_MEDIA_CS_CATEGORY_PREFIX}{category['value']}",
                media_content_id=f"{_MEDIA_CS_CATEGORY_PREFIX}{category['value']}",
                title=category["title"],
                can_play=False,
                can_expand=True,
            )
            for category in categories
        ]
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_type=_MEDIA_CS_CATEGORIES,
            media_content_id=_MEDIA_CS_CATEGORIES,
            title=_CS_CATEGORIES_TITLE,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.GENRE,
            children=children,
        )

    async def _async_browse_cs_highlights(
        self, category: str | None, title: str
    ) -> BrowseMedia:
        medias = await self._content_store.async_highlights(category)
        media_content_type = (
            f"{_MEDIA_CS_CATEGORY_PREFIX}{category}"
            if category
            else _MEDIA_CS_HIGHLIGHTS
        )
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_type=media_content_type,
            media_content_id=media_content_type,
            title=title,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.ALBUM,
            children=[self._cs_media_node(media) for media in medias],
        )

    async def _async_browse_cs_channel_medias(
        self, channel_id: int, title: str
    ) -> BrowseMedia:
        medias = await self._content_store.async_channel_medias(channel_id)
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_type=f"{_MEDIA_CS_CHANNEL_PREFIX}{channel_id}",
            media_content_id=f"{_MEDIA_CS_CHANNEL_PREFIX}{channel_id}",
            title=title,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.ALBUM,
            children=[self._cs_media_node(media) for media in medias],
        )

    def _cs_media_node(self, media: dict[str, Any]) -> BrowseMedia:
        audio = media.get("audio")
        if audio and not media.get("is_list") and is_valid_http_media_url(audio):
            return self._cs_track(audio, media.get("title"), media.get("cover"))
        return BrowseMedia(
            media_class=MediaClass.ALBUM,
            media_content_type=f"{_MEDIA_CS_MEDIA_PREFIX}{media['id']}",
            media_content_id=f"{_MEDIA_CS_MEDIA_PREFIX}{media['id']}",
            title=media.get("title") or f"MAIKA {media['id']}",
            can_play=False,
            can_expand=True,
            thumbnail=self._cs_cover(media.get("cover")),
        )

    async def _async_browse_cs_episodes(self, media_id: int) -> BrowseMedia:
        episodes = await self._content_store.async_episodes(media_id)
        children = [
            self._cs_track(episode["audio"], episode.get("title"), episode.get("cover"))
            for episode in episodes
        ]
        return BrowseMedia(
            media_class=MediaClass.ALBUM,
            media_content_type=f"{_MEDIA_CS_MEDIA_PREFIX}{media_id}",
            media_content_id=f"{_MEDIA_CS_MEDIA_PREFIX}{media_id}",
            title=f"MAIKA {media_id}",
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.MUSIC,
            children=children,
        )

    @staticmethod
    def _cs_track(audio: str, title: str | None, cover: str | None) -> BrowseMedia:
        return BrowseMedia(
            media_class=MediaClass.MUSIC,
            media_content_type=_MEDIA_CS_TRACK,
            media_content_id=audio,
            title=title or "MAIKA",
            can_play=True,
            can_expand=False,
            thumbnail=cover if cover and is_valid_http_media_url(cover) else None,
        )

    async def _async_browse_sources(self, media_content_id: str | None) -> BrowseMedia:
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )

    async def _async_browse_playlist(self) -> BrowseMedia:
        if not self.available:
            raise BrowseError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_unavailable",
            )
        try:
            refreshed = await self.coordinator.async_refresh_live(
                self.serial_number, required_fields=("latest_playlist",)
            )
        except (MaikaApiError, ConfigEntryAuthFailed) as err:
            raise BrowseError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_refresh_failed",
            ) from err
        if refreshed is False:
            raise BrowseError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_refresh_failed",
            )
        if not self.available:
            raise BrowseError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_unavailable",
            )
        playlist, songs = self._native_playlist()
        revision = self._queue_revision(playlist)
        children = []
        for song in songs:
            key = self._valid_song_key(song.get("songKey"))
            title = self._first_string(song.get("song")) or "Bài hát MAIKA"
            artist = self._first_string(song.get("artist"))
            children.append(
                BrowseMedia(
                    media_class=MediaClass.TRACK,
                    media_content_type=_MEDIA_SONG,
                    media_content_id=self._queue_item_id(revision, key) if key else "",
                    title=f"{title} — {artist}" if artist else title,
                    can_play=key is not None,
                    can_expand=False,
                )
            )
        return BrowseMedia(
            media_class=MediaClass.PLAYLIST,
            media_content_type=_MEDIA_PLAYLIST,
            media_content_id=_MEDIA_PLAYLIST,
            title=self._first_string(playlist.get("title")) or _QUEUE_TITLE,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.TRACK,
            children=children,
        )

    def _native_playlist(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        playlist = self.device.get("latest_playlist")
        if not isinstance(playlist, dict):
            return {}, []
        songs = playlist.get("songs")
        return playlist, (
            [song for song in songs if isinstance(song, dict)]
            if isinstance(songs, list)
            else []
        )

    def _queue_revision(self, playlist: dict[str, Any]) -> str:
        songs = playlist.get("songs")
        keys = (
            [
                song.get("songKey")
                if isinstance(song, dict) and isinstance(song.get("songKey"), str)
                else None
                for song in songs
            ]
            if isinstance(songs, list)
            else []
        )
        identity = [
            self.serial_number,
            playlist.get("listKey"),
            playlist.get("source"),
            keys,
        ]
        return hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _valid_song_key(value: Any) -> str | None:
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > _MAX_SONG_KEY_BYTES
            or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value)
        ):
            return None
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError:
            return None
        return value if len(encoded) <= _MAX_SONG_KEY_BYTES else None

    @staticmethod
    def _queue_item_id(revision: str, key: str) -> str:
        return f"maika:{revision}:{quote(key, safe='')}"

    async def async_media_play(self) -> None:
        """Resume playback."""
        await self._async_playback_command("ResumeCommandIssued", "resume")

    async def async_media_pause(self) -> None:
        """Pause playback."""
        await self._async_playback_command("PauseCommandIssued", "paused")

    async def async_media_stop(self) -> None:
        """Stop sound via pause without pretending the firmware reset playback."""
        await self.async_media_pause()

    async def async_media_next_track(self) -> None:
        """Skip to the next item."""
        await self._async_playback_command("NextCommandIssued", None)

    async def async_media_previous_track(self) -> None:
        """Return to the previous item."""
        await self._async_playback_command("PreviousCommandIssued", None)

    async def async_media_seek(self, position: float) -> None:
        """Restart the current cloud cast at a new offset to seek."""
        if not self._cloud_cast_enabled:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_disabled",
            )

        try:
            target = float(position)
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_invalid_seek_position",
            ) from err
        if not math.isfinite(target):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_invalid_seek_position",
            )
        target = max(0.0, target)
        duration = self.media_duration
        if duration is not None:
            target = min(target, duration)

        source = self._current_cast_source()
        if source is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_seek_unavailable",
            )

        offset = round(target * 1000)
        try:
            await self.coordinator.client.async_cast_media(
                self.serial_number,
                source["url"],
                title=source.get("title"),
                stream_format=source.get("stream_format", "AUDIO_MPEG"),
                offset_milliseconds=offset,
            )
        except MaikaApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_failed",
            ) from err

        current_payload = self._current_playback.get("payload")
        payload = dict(current_payload) if isinstance(current_payload, dict) else {}
        payload.update(
            {
                "offsetInMilliseconds": offset,
                "playbackAttributes": dict(source["attributes"]),
            }
        )
        self._position_updated_at = datetime.now(dt_util.UTC)
        self.coordinator.async_update_device_data(
            self.serial_number,
            {
                "current_playback": {
                    "status": "start",
                    "payload": payload,
                }
            },
        )
        self._schedule_live_refresh()

    async def async_play_media(
        self,
        media_type: MediaType | str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        if media_type == _MEDIA_SONG:
            await self._async_jump_to_song(media_id, kwargs.get("enqueue"))
            return
        if media_type == _MEDIA_CS_TRACK:
            await self._async_cast_content_store(media_id, kwargs.get("extra"))
            return
        if not self._cloud_cast_enabled:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_disabled",
            )

        enqueue = kwargs.get("enqueue")
        if enqueue not in (
            None,
            MediaPlayerEnqueue.PLAY,
            MediaPlayerEnqueue.REPLACE,
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_unsupported_mode",
            )

        if not media_id:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_invalid_url",
            )

        original_media_id = media_id
        if media_source.is_media_source_id(media_id):
            resolved = await media_source.async_resolve_media(
                self.hass,
                media_id,
                target_media_player=self.entity_id,
            )
            media_id = resolved.url
            media_type = resolved.mime_type

        normalized_media_type = str(media_type).lower().split(";", 1)[0].strip()
        stream_format = _CLOUD_CAST_STREAM_FORMATS.get(normalized_media_type)
        if stream_format is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_unsupported_media",
                translation_placeholders={"media_type": normalized_media_type},
            )

        media_url = async_process_play_media_url(self.hass, media_id)
        media_url = cast_ready_url(self.hass, media_url, self._cast_base_url)
        self._validate_media_url(media_url)
        title = self._media_title(kwargs.get("extra"), original_media_id, media_url)

        try:
            await self.coordinator.client.async_cast_media(
                self.serial_number,
                media_url,
                title=title,
                stream_format=stream_format,
            )
        except MaikaApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_failed",
            ) from err

        cast_attributes = {
            "mediaType": normalized_media_type,
            "media_type": normalized_media_type,
            "title": title,
            "url": media_url,
        }
        self._last_cast_media = {
            "url": media_url,
            "title": title,
            "media_type": normalized_media_type,
            "stream_format": stream_format,
            "attributes": cast_attributes,
        }
        self._position_updated_at = datetime.now(dt_util.UTC)
        self.coordinator.async_update_device_data(
            self.serial_number,
            {
                "current_playback": {
                    "status": "start",
                    "payload": {
                        "offsetInMilliseconds": 0,
                        "playbackAttributes": cast_attributes,
                    },
                }
            },
        )
        self._schedule_live_refresh()

    async def _async_cast_content_store(self, media_url: str, extra: Any) -> None:
        if not self._cloud_cast_enabled:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_disabled",
            )
        if not isinstance(media_url, str) or not is_valid_http_media_url(media_url):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_invalid_url",
            )
        title = self._media_title(extra, media_url, media_url)
        try:
            await self.coordinator.client.async_cast_media(
                self.serial_number,
                media_url,
                title=title,
                stream_format="AUDIO_MPEG",
            )
        except MaikaApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_failed",
            ) from err
        self._schedule_live_refresh()

    async def _async_jump_to_song(self, media_id: str, enqueue: Any) -> None:
        if not self.available:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_unavailable",
            )
        if enqueue not in (None, MediaPlayerEnqueue.PLAY, MediaPlayerEnqueue.REPLACE):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_unsupported_mode",
            )
        if (
            not isinstance(media_id, str)
            or len(media_id) > _MAX_QUEUE_ITEM_ID_LENGTH
            or (match := _QUEUE_ITEM_ID_PATTERN.fullmatch(media_id)) is None
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_invalid_selection",
            )
        revision, encoded_key = match.groups()
        try:
            key = self._valid_song_key(unquote(encoded_key, errors="strict"))
        except UnicodeDecodeError:
            key = None
        if key is None or self._queue_item_id(revision, key) != media_id:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_invalid_selection",
            )
        try:
            refreshed = await self.coordinator.async_refresh_live(
                self.serial_number, required_fields=("latest_playlist",)
            )
        except (MaikaApiError, ConfigEntryAuthFailed) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_refresh_failed",
            ) from err
        if refreshed is False:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_refresh_failed",
            )
        if not self.available:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_unavailable",
            )
        playlist, songs = self._native_playlist()
        if revision != self._queue_revision(playlist):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_changed",
            )
        if not any(song.get("songKey") == key for song in songs):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_invalid_selection",
            )
        try:
            await self.coordinator.client.async_playback_command(
                self.serial_number, "JumpCommandIssued", song_key=key
            )
        except MaikaApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="maika_queue_jump_failed",
            ) from err
        self._schedule_live_refresh()

    async def _async_playback_command(
        self, command: str, optimistic_status: str | None
    ) -> None:
        await self.coordinator.client.async_playback_command(
            self.serial_number, command
        )
        if optimistic_status is not None:
            current = dict(self._current_playback)
            position = self.media_position
            now = datetime.now(dt_util.UTC)
            if position is not None:
                if self.state == MediaPlayerState.PLAYING and self._position_updated_at:
                    position += max(
                        0.0, (now - self._position_updated_at).total_seconds()
                    )
                duration = self.media_duration
                if duration is not None:
                    position = min(position, duration)
                payload = dict(current["payload"])
                payload["offsetInMilliseconds"] = round(position * 1000)
                current["payload"] = payload
                self._position_updated_at = now
            current["status"] = optimistic_status
            self.coordinator.async_update_device_data(
                self.serial_number, {"current_playback": current}
            )
        self._schedule_live_refresh()

    def _current_cast_source(self) -> dict[str, Any] | None:
        """Return the media currently handed to the speaker, if any."""
        attributes = self._playback_attributes
        url = self._first_string(attributes.get("url"), attributes.get("mediaId"))
        if url and is_valid_http_media_url(url):
            return {
                "url": url,
                "title": self.media_title,
                "media_type": self._first_string(
                    attributes.get("mediaType"), attributes.get("media_type")
                )
                or "audio",
                "stream_format": "AUDIO_MPEG",
                "attributes": dict(attributes),
            }
        if (
            self._last_cast_media
            and self.state != MediaPlayerState.IDLE
            and self.media_content_id is None
            and self.media_title
            and self.media_title == self._last_cast_media.get("title")
        ):
            return self._last_cast_media
        return None

    @callback
    def _schedule_live_refresh(self) -> None:
        """Refresh live data in the background so commands return fast."""
        self.coordinator.async_schedule_playback_refresh(self.serial_number)

    @property
    def _current_playback(self) -> dict[str, Any]:
        current = self.device.get("current_playback")
        return current if isinstance(current, dict) else {}

    @property
    def _playback_attributes(self) -> dict[str, Any]:
        payload = self._current_playback.get("payload")
        if not isinstance(payload, dict):
            return {}
        attributes = payload.get("playbackAttributes")
        return attributes if isinstance(attributes, dict) else {}

    @staticmethod
    def _first_string(*values: Any) -> str | None:
        return next(
            (str(value) for value in values if isinstance(value, str) and value),
            None,
        )

    @staticmethod
    def _validate_media_url(media_url: str) -> None:
        if not is_valid_http_media_url(media_url):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cast_invalid_url",
            )

    @staticmethod
    def _media_title(extra: Any, *media_ids: str) -> str:
        if isinstance(extra, dict):
            metadata = extra.get("metadata")
            if isinstance(metadata, dict):
                title = metadata.get("title") or metadata.get("name")
                if isinstance(title, str) and title.strip():
                    return title.strip()[:255]
            title = extra.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()[:255]

        for media_id in media_ids:
            filename = unquote(PurePosixPath(urlsplit(media_id).path).name)
            if not filename:
                continue
            title = filename.rsplit(".", 1)[0].strip()
            if title:
                return title[:255]
        return "Home Assistant"
