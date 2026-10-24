"""Shared validation for MAIKA cloud-cast URLs."""

from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit, urlunsplit

MAX_MEDIA_URL_LENGTH = 8192


def is_valid_http_media_url(value: str) -> bool:
    """Return whether a URL is safe for MAIKA cloud cast."""
    if (
        not value
        or len(value) > MAX_MEDIA_URL_LENGTH
        or any(character.isspace() for character in value)
    ):
        return False

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not hostname
        or port == 0
        or parsed.username is not None
        or parsed.password is not None
        or hostname == "localhost"
        or hostname.endswith(".localhost")
    ):
        return False

    try:
        address = ip_address(hostname)
    except ValueError:
        return True
    return not (
        address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
    )


_MDNS_SUFFIXES = (".local", ".internal")
_UNRESOLVABLE_HOSTS = frozenset(
    {"localhost", "homeassistant", "hassio", "supervisor", "homeassistant.local"}
)


def is_reachable_media_host(host: str | None) -> bool:
    """Return whether a speaker on the same LAN can likely resolve a host name."""
    if not host:
        return False
    normalized = host.strip().lower().rstrip(".")
    if not normalized or normalized in _UNRESOLVABLE_HOSTS:
        return False
    if normalized.endswith(_MDNS_SUFFIXES):
        return False
    try:
        address = ip_address(normalized)
    except ValueError:
        return True
    return not (
        address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
    )


def rewrite_media_origin(
    media_url: str, base_url: str, *, keep_port: bool = False
) -> str:
    """Return ``media_url`` with the scheme, host and (optionally) port of ``base_url``."""
    if not media_url or not base_url:
        return media_url

    parsed = urlsplit(media_url)
    base = urlsplit(base_url)
    if parsed.scheme.lower() not in {"http", "https"} or not base.netloc:
        return media_url
    if base.scheme.lower() not in {"http", "https"}:
        return media_url

    netloc = base.netloc
    if keep_port and parsed.port is not None:
        host = base.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        netloc = f"{host}:{parsed.port}"

    return urlunsplit((base.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
