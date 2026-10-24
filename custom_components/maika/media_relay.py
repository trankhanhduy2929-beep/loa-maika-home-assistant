"""Proxy add-on media through Home Assistant's external HTTPS URL.

The MAIKA speaker fetches media from its own network. Some firmware rejects
plain HTTP URLs, while the YouTube Pro add-on normally exposes its relay on a
LAN HTTP port. When Home Assistant has an external HTTPS URL, register a
short-lived opaque URL on Home Assistant and stream the add-on response through
that URL. The speaker then only needs to reach Home Assistant over HTTPS.
"""

from __future__ import annotations

import logging
import secrets
import time
from ipaddress import ip_address
from urllib.parse import urlsplit, urlunsplit

import aiohttp
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

RELAY_REGISTRY_KEY = f"{DOMAIN}_media_relay"
ADDON_MEDIA_PORT = 2032
RELAY_TTL = 24 * 60 * 60
RELAY_MAX_ENTRIES = 512
_ADDON_MEDIA_PREFIXES = (
    "/api/media-mp3/",
    "/api/media/",
    "/api/media-remux/",
)
_STREAM_HEADERS = (
    "Content-Type",
    "Content-Length",
    "Content-Range",
    "Accept-Ranges",
    "Cache-Control",
    "Last-Modified",
    "ETag",
)


class MediaRelayRegistry:
    """Map opaque relay tokens to validated add-on media URLs."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[str, float]] = {}

    def register(self, media_url: str) -> str:
        """Register a media URL and return its opaque token."""
        self._prune()
        token = secrets.token_urlsafe(24)
        self._entries[token] = (media_url, time.monotonic() + RELAY_TTL)
        while len(self._entries) > RELAY_MAX_ENTRIES:
            self._entries.pop(next(iter(self._entries)))
        return token

    def resolve(self, token: str) -> str | None:
        """Return a registered URL, or ``None`` when missing or expired."""
        entry = self._entries.get(token)
        if entry is None:
            return None
        media_url, expires_at = entry
        if expires_at <= time.monotonic():
            self._entries.pop(token, None)
            return None
        return media_url

    def _prune(self) -> None:
        now = time.monotonic()
        expired = [token for token, (_, end) in self._entries.items() if end <= now]
        for token in expired:
            self._entries.pop(token, None)


def media_relay_registry(hass: HomeAssistant) -> MediaRelayRegistry:
    """Return the registry stored on the Home Assistant instance."""
    registry = hass.data.get(RELAY_REGISTRY_KEY)
    if not isinstance(registry, MediaRelayRegistry):
        registry = MediaRelayRegistry()
        hass.data[RELAY_REGISTRY_KEY] = registry
    return registry


def is_addon_media_url(value: str) -> bool:
    """Return whether a URL looks like the YouTube Pro add-on relay."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or port != ADDON_MEDIA_PORT
        or parsed.username is not None
        or parsed.password is not None
    ):
        return False
    if not any(parsed.path.startswith(prefix) for prefix in _ADDON_MEDIA_PREFIXES):
        return False
    try:
        address = ip_address(parsed.hostname)
    except ValueError:
        return False
    return address.is_private and not address.is_loopback


def public_relay_url(hass: HomeAssistant, media_url: str) -> str | None:
    """Return an HTTPS Home Assistant proxy URL for add-on media, if possible."""
    if not is_addon_media_url(media_url):
        return None
    try:
        external = get_url(
            hass,
            allow_internal=False,
            allow_ip=True,
            prefer_external=True,
        )
    except (NoURLAvailableError, TypeError, ValueError):
        return None
    try:
        parsed = urlsplit(external)
    except ValueError:
        return None
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return None
    base = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    token = media_relay_registry(hass).register(media_url)
    return f"{base}/api/maika/relay/{token}"


class MaikaMediaRelayView(HomeAssistantView):
    """Stream add-on media through Home Assistant over HTTPS."""

    name = "api:maika:media_relay"
    url = "/api/maika/relay/{token}"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request, token: str) -> web.StreamResponse:
        """Proxy a GET request to the registered add-on URL."""
        return await self._proxy(request, token, head=False)

    async def head(self, request: web.Request, token: str) -> web.StreamResponse:
        """Return upstream headers for a HEAD request."""
        return await self._proxy(request, token, head=True)

    async def _proxy(
        self, request: web.Request, token: str, *, head: bool
    ) -> web.StreamResponse:
        target = media_relay_registry(self.hass).resolve(token)
        if target is None:
            return web.Response(status=404, text="Media relay URL đã hết hạn")

        headers = {"Accept-Encoding": "identity"}
        for name in ("Range", "If-Range"):
            value = request.headers.get(name)
            if value:
                headers[name] = value

        session = async_get_clientsession(self.hass)
        timeout = aiohttp.ClientTimeout(
            total=None,
            sock_connect=10,
            sock_read=120,
        )
        method = session.head if head else session.get
        try:
            upstream = await method(target, headers=headers, timeout=timeout)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            _LOGGER.debug("MAIKA media relay upstream failed: %s", err)
            return web.Response(status=502, text="Không tải được media từ add-on")

        async with upstream:
            if upstream.status not in (200, 206):
                _LOGGER.debug(
                    "MAIKA media relay upstream returned HTTP %s", upstream.status
                )
                return web.Response(status=502, text="Add-on không trả media")

            response: web.StreamResponse
            if head:
                response = web.Response(status=upstream.status)
            else:
                response = web.StreamResponse(status=upstream.status)
            for name in _STREAM_HEADERS:
                value = upstream.headers.get(name)
                if value is not None:
                    response.headers[name] = value
            response.headers.setdefault("Accept-Ranges", "none")
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers["Access-Control-Allow-Origin"] = "*"
            if head:
                return response

            await response.prepare(request)
            try:
                async for chunk in upstream.content.iter_chunked(64 * 1024):
                    await response.write(chunk)
                await response.write_eof()
            except (ConnectionResetError, aiohttp.ClientPayloadError) as err:
                _LOGGER.debug("MAIKA media relay stream ended: %s", err)
            return response
