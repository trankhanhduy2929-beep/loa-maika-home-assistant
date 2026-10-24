#!/usr/bin/env python3
"""Validate MAIKA HTTPS media relay helpers without Home Assistant installed."""

from __future__ import annotations

import ast
import runpy
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ADDON_URL = "http://192.168.5.187:2032/api/media-mp3/token/audio.mp3"


def _load_media_relay():
    path = ROOT / "custom_components/maika/media_relay.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.Import)
            and any(alias.name == "aiohttp" for alias in node.names)
        )
        and not (
            isinstance(node, ast.ImportFrom)
            and (
                node.level > 0
                or (node.module or "").startswith(("aiohttp", "homeassistant"))
            )
        )
    ]
    namespace = {
        "__name__": "maika_media_relay_test",
        "aiohttp": SimpleNamespace(
            ClientError=Exception,
            ClientPayloadError=Exception,
            ClientTimeout=lambda **kwargs: kwargs,
        ),
        "web": SimpleNamespace(
            Request=object,
            Response=lambda **kwargs: SimpleNamespace(**kwargs),
            StreamResponse=lambda **kwargs: SimpleNamespace(**kwargs),
        ),
        "HomeAssistantView": type("HomeAssistantView", (), {}),
        "HomeAssistant": object,
        "NoURLAvailableError": type("NoURLAvailableError", (Exception,), {}),
        "get_url": lambda hass, **kwargs: hass.external_url,
        "async_get_clientsession": lambda hass: None,
        "DOMAIN": "maika",
    }
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


def _load_cast_target(relay):
    path = ROOT / "custom_components/maika/cast_target.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.ImportFrom)
            and (node.level > 0 or (node.module or "").startswith("homeassistant"))
        )
    ]
    media_url = runpy.run_path(str(ROOT / "custom_components/maika/media_url.py"))
    namespace = {
        "__name__": "maika_cast_target_test",
        "public_relay_url": relay["public_relay_url"],
        "is_reachable_media_host": media_url["is_reachable_media_host"],
        "rewrite_media_origin": media_url["rewrite_media_origin"],
        "HomeAssistant": object,
        "NoURLAvailableError": relay["NoURLAvailableError"],
        "get_url": relay["get_url"],
        "is_hass_url": lambda hass, value: False,
    }
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


def _hass(external_url="https://ha.example:8123"):
    return SimpleNamespace(
        data={},
        external_url=external_url,
        config=SimpleNamespace(
            api=SimpleNamespace(
                use_ssl=True,
                port=8123,
                local_ip="192.168.5.187",
            ),
            internal_url="http://192.168.5.187:8123",
            external_url=external_url,
        ),
    )


def validate_media_relay() -> list[str]:
    """Return validation errors for the relay helpers."""
    errors: list[str] = []
    relay = _load_media_relay()

    if not relay["is_addon_media_url"](ADDON_URL):
        errors.append("add-on media URL was not recognized")
    for value in (
        "http://192.168.5.187:2032/other/token",
        "http://192.168.5.187:9999/api/media-mp3/token/audio.mp3",
        "https://example.com/api/media-mp3/token/audio.mp3",
        "http://127.0.0.1:2032/api/media-mp3/token/audio.mp3",
    ):
        if relay["is_addon_media_url"](value):
            errors.append(f"unsafe media URL was accepted: {value}")

    hass = _hass()
    public_url = relay["public_relay_url"](hass, ADDON_URL)
    if not public_url or not public_url.startswith(
        "https://ha.example:8123/api/maika/relay/"
    ):
        errors.append(f"unexpected public relay URL: {public_url}")
    else:
        token = urlsplit(public_url).path.rsplit("/", 1)[-1]
        registry = relay["media_relay_registry"](hass)
        if registry.resolve(token) != ADDON_URL:
            errors.append("relay token did not resolve to the add-on URL")
        if registry.resolve("missing") is not None:
            errors.append("missing relay token was accepted")

    if relay["public_relay_url"](_hass("http://ha.example:8123"), ADDON_URL):
        errors.append("HTTP Home Assistant URL was used for the relay")
    if relay["public_relay_url"](hass, "https://example.com/song.mp3"):
        errors.append("non-add-on media was proxied")

    cast_target = _load_cast_target(relay)
    proxied = cast_target["cast_ready_url"](hass, ADDON_URL, "")
    if not proxied.startswith("https://ha.example:8123/api/maika/relay/"):
        errors.append(f"cast_ready_url did not proxy add-on media: {proxied}")
    else:
        token = urlsplit(proxied).path.rsplit("/", 1)[-1]
        if relay["media_relay_registry"](hass).resolve(token) != ADDON_URL:
            errors.append("cast_ready_url relay token did not resolve")
    if cast_target["cast_ready_url"](hass, "https://example.com/song.mp3", "") != (
        "https://example.com/song.mp3"
    ):
        errors.append("cast_ready_url changed a public media URL")

    return errors


if __name__ == "__main__":
    failures = validate_media_relay()
    if failures:
        raise SystemExit("\n".join(failures))
    print("media relay validation passed")
