"""Shared validation for MAIKA cloud-cast URLs."""

from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit

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
