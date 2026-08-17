#!/usr/bin/env python3
"""Configure the activation endpoint embedded in MAIKA release builds."""

from __future__ import annotations

import argparse
import base64
import binascii
import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "custom_components/maika/license_config.py"


def normalize_server_url(value: str) -> str:
    """Return a release-safe HTTPS activation endpoint."""
    parsed = urlsplit(value.strip().rstrip("/"))
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("server URL must be HTTPS and must not contain credentials")
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        raise ValueError("server URL must use a hostname, not an IP literal")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def normalize_public_key(value: str) -> str:
    """Validate a Base64 DER public key without requiring cryptography."""
    normalized = "".join(value.split())
    try:
        decoded = base64.b64decode(normalized, validate=True)
    except binascii.Error as err:
        raise ValueError("public key must be valid Base64") from err
    if len(decoded) < 40 or len(decoded) > 256:
        raise ValueError("public key DER length is invalid")
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-url", required=True)
    parser.add_argument(
        "--public-key-b64-file",
        type=Path,
        help="Optional Base64 DER Ed25519 public key file for a planned key rotation.",
    )
    args = parser.parse_args()

    server_url = normalize_server_url(args.server_url)
    current = CONFIG_PATH.read_text(encoding="utf-8")
    match = re.search(r'^LICENSE_PUBLIC_KEY_B64 = "([^"]+)"$', current, re.MULTILINE)
    if match is None:
        raise ValueError("unable to read the current public key")
    public_key = match.group(1)
    if args.public_key_b64_file:
        public_key = normalize_public_key(
            args.public_key_b64_file.read_text(encoding="utf-8")
        )

    content = (
        '"""Build-time licensing configuration for MAIKA."""\n\n'
        "from __future__ import annotations\n\n"
        f"DEFAULT_LICENSE_SERVER_URL = {json.dumps(server_url)}\n"
        f"LICENSE_PUBLIC_KEY_B64 = {json.dumps(public_key)}\n"
    )
    CONFIG_PATH.write_bytes(content.encode("utf-8"))
    print(f"Configured activation server: {server_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
