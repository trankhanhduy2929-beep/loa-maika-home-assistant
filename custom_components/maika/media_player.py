"""Media player entities for MAIKA speakers."""

from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    BrowseMedia,
    MediaPlayerDeviceClass,
    MediaPlayerEnqueue,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    async_process_play_media_url,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import MaikaConfigEntry
from .api import MaikaApiError
from .const import CONF_ENABLE_CLOUD_CAST, DOMAIN
from .entity import MaikaCommandEntity
from .media_url import is_valid_http_media_url

_BASE_SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
)
_CLOUD_CAST_SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.BROWSE_MEDIA
)
_CLOUD_CAST_STREAM_FORMATS = {
    "audio": "AUDIO_MPEG",
    "audio/aac": "AUDIO_MPEG",
    "audio/m4a": "AUDIO_MPEG",
    "audio/mp3": "AUDIO_MPEG",
    "audio/mp4": "AUDIO_MPEG",
    "audio/mp4a-latm": "AUDIO_MPEG",
    "audio/mpeg": "AUDIO_MPEG",
    "audio/x-aac": "AUDIO_MPEG",
    "audio/x-m4a": "AUDIO_MPEG",
    "audio/x-mpeg": "AUDIO_MPEG",
    "music": "AUDIO_MPEG",
    "url": "AUDIO_MPEG",
}
_DEFAULT_UNMUTE_VOLUME = 0.3


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
        self._volume_before_mute: float | None = None
        self._cloud_cast_enabled = bool(
            coordinator.entry.options.get(CONF_ENABLE_CLOUD_CAST, False)
        )
        self._attr_supported_features = _BASE_SUPPORTED_FEATURES
        if self._cloud_cast_enabled:
            self._attr_supported_features |= _CLOUD_CAST_SUPPORTED_FEATURES

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
            attributes.get("songKey"),
            attributes.get("key"),
        )

    @property
    def media_title(self) -> str | None:
        """Return current media title."""
        attributes = self._playback_attributes
        return self._first_string(
            attributes.get("title"),
            attributes.get("song"),
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
            return float(value) / 1000.0 if value is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def media_position_updated_at(self) -> datetime | None:
        """Return the timestamp associated with playback position."""
        if self.media_position is None:
            return None
        if self._position_updated_at is None:
            self._position_updated_at = datetime.now(dt_util.UTC)
        return self._position_updated_at

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
        await self.coordinator.async_refresh_live(self.serial_number)

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
        """Browse audio exposed by Home Assistant media sources."""
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )

    async def async_media_play(self) -> None:
        """Resume playback."""
        await self._async_playback_command("ResumeCommandIssued", "resume")

    async def async_media_pause(self) -> None:
        """Pause playback."""
        await self._async_playback_command("PauseCommandIssued", "paused")

    async def async_media_next_track(self) -> None:
        """Skip to the next item."""
        await self._async_playback_command("NextCommandIssued", None)

    async def async_media_previous_track(self) -> None:
        """Return to the previous item."""
        await self._async_playback_command("PreviousCommandIssued", None)

    async def async_play_media(
        self,
        media_type: MediaType | str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        """Cast one supported audio URL to the physical MAIKA speaker."""
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

        self._position_updated_at = datetime.now(dt_util.UTC)
        self.coordinator.async_update_device_data(
            self.serial_number,
            {
                "current_playback": {
                    "status": "start",
                    "payload": {
                        "offsetInMilliseconds": 0,
                        "playbackAttributes": {
                            "mediaType": normalized_media_type,
                            "media_type": normalized_media_type,
                            "title": title,
                            "url": media_url,
                        },
                    },
                }
            },
        )
        await self.coordinator.async_refresh_live(self.serial_number)

    async def _async_playback_command(
        self, command: str, optimistic_status: str | None
    ) -> None:
        await self.coordinator.client.async_playback_command(
            self.serial_number, command
        )
        if optimistic_status is not None:
            current = dict(self._current_playback)
            current["status"] = optimistic_status
            self.coordinator.async_update_device_data(
                self.serial_number, {"current_playback": current}
            )
        await self.coordinator.async_refresh_live(self.serial_number)

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
