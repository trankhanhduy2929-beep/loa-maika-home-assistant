"""Choose a Home Assistant URL that the MAIKA speaker can actually reach.

The MAIKA cloud hands the media URL to the speaker, which then fetches it from
its own network. Home Assistant may build that URL from ``internal_url`` (for
example the mDNS name ``homeassistant.local``) which a LAN device cannot always
resolve, so the cast silently fails. This module rewrites such URLs to a host
the speaker can reach, preferring the Home Assistant LAN address.
"""

from __future__ import annotations

import logging
from urllib.parse import urlsplit, urlunsplit

from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import NoURLAvailableError, get_url, is_hass_url

from .media_url import is_reachable_media_host, rewrite_media_origin

_LOGGER = logging.getLogger(__name__)

DEFAULT_HA_HTTP_PORT = 8123
_HTTP_SCHEMES = frozenset({"http", "https"})


def _clean_origin(value: str) -> str:
    """Return ``scheme://host[:port]`` for a configured base URL, else an empty string."""
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return ""
    if parsed.scheme.lower() not in _HTTP_SCHEMES or not parsed.netloc:
        return ""
    if parsed.username is not None or parsed.password is not None:
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _origin_host(origin: str) -> str | None:
    try:
        return urlsplit(origin).hostname
    except ValueError:
        return None


def _api_port(hass: HomeAssistant) -> int:
    port = getattr(getattr(hass.config, "api", None), "port", None)
    if isinstance(port, int) and 0 < port < 65536:
        return port
    return DEFAULT_HA_HTTP_PORT


def resolve_cast_base_url(hass: HomeAssistant, override: str = "") -> str:
    """Return the base Home Assistant URL the speaker should stream from."""
    explicit = _clean_origin(override)
    if explicit:
        return explicit

    api = getattr(hass.config, "api", None)
    if api is not None and not getattr(api, "use_ssl", False):
        local_ip = getattr(api, "local_ip", None)
        if isinstance(local_ip, str) and is_reachable_media_host(local_ip):
            return f"http://{local_ip}:{_api_port(hass)}"

    internal = _clean_origin(str(getattr(hass.config, "internal_url", "") or ""))
    if internal and is_reachable_media_host(_origin_host(internal)):
        return internal

    candidates: list[str] = []
    for prefer_external in (False, True):
        try:
            candidate = _clean_origin(
                get_url(hass, allow_ip=True, prefer_external=prefer_external)
            )
        except (NoURLAvailableError, TypeError, ValueError):
            continue
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        if is_reachable_media_host(_origin_host(candidate)):
            return candidate
    return candidates[0] if candidates else ""


def cast_ready_url(hass: HomeAssistant, media_url: str, override: str = "") -> str:
    """Rewrite a Home Assistant media URL to a host the speaker can reach."""
    try:
        parsed = urlsplit(media_url)
    except ValueError:
        return media_url
    host = parsed.hostname or ""
    if parsed.scheme.lower() not in _HTTP_SCHEMES or not host:
        return media_url

    explicit = _clean_origin(override)
    if explicit:
        if is_hass_url(hass, media_url) or not is_reachable_media_host(host):
            return rewrite_media_origin(media_url, explicit, keep_port=True)
        return media_url

    if is_reachable_media_host(host):
        return media_url

    base = resolve_cast_base_url(hass, override)
    if not base:
        return media_url
    _LOGGER.debug(
        "MAIKA cloud cast rewrote unreachable host %s to %s",
        host,
        _origin_host(base),
    )
    # Add-on media servers can live on another port of the same host, so keep
    # an explicit media port instead of forcing the Home Assistant port.
    return rewrite_media_origin(media_url, base, keep_port=True)
