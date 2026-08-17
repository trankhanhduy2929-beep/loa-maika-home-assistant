#!/usr/bin/env python3
"""Validate the standalone MAIKA Home Assistant repository."""

from __future__ import annotations

import argparse
import ast
import base64
import binascii
import ipaddress
import json
import re
import struct
import sys
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "maika"
OWNER_PLACEHOLDER = "GITHUB_USERNAME"
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

REQUIRED_FILES = (
    ".github/CODEOWNERS",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/dependabot.yml",
    ".github/pull_request_template.md",
    ".github/workflows/release.yml",
    ".github/workflows/validate.yml",
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "docs/API_RESEARCH.md",
    "docs/CLOUD_CAST.md",
    "docs/ENTITIES.md",
    "docs/LICENSING.md",
    "docs/SECURITY_NOTES.md",
    "LICENSE",
    "NOTICE.md",
    "README.md",
    "REPOSITORY_SETUP.md",
    "SECURITY.md",
    "hacs.json",
    "pyproject.toml",
    "custom_components/maika/__init__.py",
    "custom_components/maika/config_flow.py",
    "custom_components/maika/license.py",
    "custom_components/maika/license_config.py",
    "custom_components/maika/license_manager.py",
    "custom_components/maika/license_store.py",
    "custom_components/maika/brand/icon.png",
    "custom_components/maika/manifest.json",
    "custom_components/maika/strings.json",
    "custom_components/maika/translations/en.json",
    "custom_components/maika/translations/vi.json",
    "scripts/configure_licensing.py",
)

TEMPLATE_FILES = (
    ".github/CODEOWNERS",
    ".github/ISSUE_TEMPLATE/config.yml",
    "README.md",
    "SECURITY.md",
    "custom_components/maika/manifest.json",
)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ValueError(f"Invalid JSON {path.relative_to(ROOT)}: {err}") from err


def _validate_zip(path: Path, *, hacs_format: bool, errors: list[str]) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if not names:
                errors.append(f"{path.relative_to(ROOT)} is empty")
                return
            for name in names:
                candidate = Path(name)
                if candidate.is_absolute() or ".." in candidate.parts:
                    errors.append(f"Unsafe ZIP entry in {path.name}: {name}")
                if "__pycache__" in candidate.parts or name.endswith(".pyc"):
                    errors.append(f"Cache file in {path.name}: {name}")
            if hacs_format:
                if any(name.startswith("custom_components/") for name in names):
                    errors.append(
                        "maika.zip must contain integration files at archive root"
                    )
                if "manifest.json" not in names:
                    errors.append("maika.zip does not contain root manifest.json")
            elif "custom_components/maika/manifest.json" not in names:
                errors.append(
                    "maika-manual.zip does not contain custom_components/maika/manifest.json"
                )
    except (OSError, zipfile.BadZipFile) as err:
        errors.append(f"Invalid ZIP {path.relative_to(ROOT)}: {err}")


def _validate_brand_icon(path: Path, errors: list[str]) -> None:
    try:
        data = path.read_bytes()
    except OSError as err:
        errors.append(f"Unable to read brand icon: {err}")
        return
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        errors.append("brand/icon.png must be a valid PNG file")
        return
    width, height = struct.unpack(">II", data[16:24])
    if width != height or width < 128:
        errors.append("brand/icon.png must be square and at least 128x128")


def _string_constants(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, str] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            values[node.targets[0].id] = node.value.value
    return values


def _validate_licensing_config(
    version: str,
    errors: list[str],
    expected_public_key_file: Path | None,
) -> None:
    const_path = ROOT / f"custom_components/{DOMAIN}/const.py"
    config_path = ROOT / f"custom_components/{DOMAIN}/license_config.py"
    try:
        const_values = _string_constants(const_path)
        config_values = _string_constants(config_path)
    except (OSError, UnicodeDecodeError, SyntaxError) as err:
        errors.append(f"Unable to validate licensing constants: {err}")
        return

    if const_values.get("INTEGRATION_VERSION") != version:
        errors.append("INTEGRATION_VERSION must match manifest version")

    server_url = config_values.get("DEFAULT_LICENSE_SERVER_URL", "")
    if server_url:
        parsed = urlsplit(server_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            errors.append("DEFAULT_LICENSE_SERVER_URL must be a clean HTTPS URL")
        else:
            try:
                ipaddress.ip_address(parsed.hostname)
            except ValueError:
                pass
            else:
                errors.append("DEFAULT_LICENSE_SERVER_URL must use a hostname")

    public_key = config_values.get("LICENSE_PUBLIC_KEY_B64", "")
    try:
        public_der = base64.b64decode(public_key, validate=True)
    except binascii.Error:
        errors.append("LICENSE_PUBLIC_KEY_B64 must be valid Base64 DER")
    else:
        ed25519_spki_prefix = bytes.fromhex("302a300506032b6570032100")
        if len(public_der) != 44 or not public_der.startswith(ed25519_spki_prefix):
            errors.append("LICENSE_PUBLIC_KEY_B64 must contain an Ed25519 public key")
        if expected_public_key_file is not None:
            try:
                expected_public_key = "".join(
                    expected_public_key_file.read_text(encoding="utf-8").split()
                )
                expected_der = base64.b64decode(expected_public_key, validate=True)
            except (OSError, UnicodeDecodeError, binascii.Error) as err:
                errors.append(f"Unable to read expected license public key: {err}")
            else:
                if public_der != expected_der:
                    errors.append(
                        "LICENSE_PUBLIC_KEY_B64 does not match --public-key-b64-file"
                    )


def validate(
    *,
    allow_template: bool,
    tag: str | None,
    expected_public_key_file: Path | None = None,
) -> list[str]:
    """Return validation errors."""
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    brand_icon = ROOT / f"custom_components/{DOMAIN}/brand/icon.png"
    if brand_icon.is_file():
        _validate_brand_icon(brand_icon, errors)

    for path in ROOT.rglob("*.py"):
        if "dist" in path.parts:
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as err:
            errors.append(f"Invalid Python {path.relative_to(ROOT)}: {err}")

    for path in ROOT.rglob("*.json"):
        if "dist" in path.parts:
            continue
        try:
            _load_json(path)
        except ValueError as err:
            errors.append(str(err))

    manifest_path = ROOT / f"custom_components/{DOMAIN}/manifest.json"
    hacs_path = ROOT / "hacs.json"
    if manifest_path.is_file():
        try:
            manifest = _load_json(manifest_path)
        except ValueError:
            manifest = {}
        if manifest.get("domain") != DOMAIN:
            errors.append("manifest domain must be maika")
        if manifest.get("config_flow") is not True:
            errors.append("manifest config_flow must be true")
        version = str(manifest.get("version", ""))
        if not SEMVER_PATTERN.fullmatch(version):
            errors.append("manifest version must use semantic versioning")
        codeowners = manifest.get("codeowners")
        if not isinstance(codeowners, list) or not codeowners:
            errors.append("manifest codeowners must contain a GitHub username")
        elif not all(
            isinstance(owner, str) and owner.startswith("@") for owner in codeowners
        ):
            errors.append("every manifest codeowner must start with @")
        for key in ("documentation", "issue_tracker"):
            value = manifest.get(key)
            if not isinstance(value, str) or not value.startswith("https://"):
                errors.append(f"manifest {key} must be an HTTPS URL")
        if tag:
            normalized_tag = tag.removeprefix("v")
            if normalized_tag != version:
                errors.append(
                    f"tag {tag} does not match manifest version {version or '<missing>'}"
                )
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        if version and f"[{version}]" not in changelog:
            errors.append(f"CHANGELOG.md does not contain [{version}]")
        if version:
            _validate_licensing_config(version, errors, expected_public_key_file)

    if hacs_path.is_file():
        try:
            hacs = _load_json(hacs_path)
        except ValueError:
            hacs = {}
        if hacs.get("zip_release") is not True:
            errors.append("hacs.json zip_release must be true")
        if hacs.get("filename") != "maika.zip":
            errors.append("hacs.json filename must be maika.zip")
        minimum_ha = str(hacs.get("homeassistant", ""))
        if not SEMVER_PATTERN.fullmatch(minimum_ha):
            errors.append("hacs.json homeassistant must be a semantic version")

    if not allow_template:
        for relative in TEMPLATE_FILES:
            path = ROOT / relative
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if OWNER_PLACEHOLDER in text:
                errors.append(
                    f"Template owner remains in {relative}; run configure_repository.py"
                )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        if "TEMPLATE_NOTICE_START" in readme:
            errors.append("README template notice has not been removed")

    forbidden = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("*")
        if path.is_file()
        and (
            path.suffix == ".pyc"
            or "__pycache__" in path.parts
            or path.name
            in {
                ".dev.vars",
                ".env",
                "ADMIN_TOKEN.txt",
                "home-assistant_v2.db",
                "LICENSE_PEPPER.txt",
                "secrets.yaml",
                "SIGNING_PRIVATE_KEY_B64.txt",
                "signing-private.pem",
            }
        )
    ]
    if forbidden:
        errors.append(f"Forbidden generated/sensitive files: {forbidden}")

    crlf_python = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("*.py")
        if path.is_file() and b"\r\n" in path.read_bytes()
    ]
    if crlf_python:
        errors.append(f"Python source must use LF line endings: {crlf_python}")

    private_key_markers = (
        "-----BEGIN " + "PRIVATE KEY-----",
        "-----BEGIN OPENSSH " + "PRIVATE KEY-----",
        "-----BEGIN RSA " + "PRIVATE KEY-----",
    )
    for path in ROOT.rglob("*"):
        if not path.is_file() or "dist" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if any(marker in text for marker in private_key_markers):
            errors.append(f"Private key material found in {path.relative_to(ROOT)}")

    dist = ROOT / "dist"
    hacs_zip = dist / "maika.zip"
    manual_zip = dist / "maika-manual.zip"
    if hacs_zip.exists():
        _validate_zip(hacs_zip, hacs_format=True, errors=errors)
    if manual_zip.exists():
        _validate_zip(manual_zip, hacs_format=False, errors=errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-template",
        action="store_true",
        help="Allow the packaged GITHUB_USERNAME placeholder.",
    )
    parser.add_argument(
        "--tag", help="Validate a release tag against manifest version."
    )
    parser.add_argument(
        "--public-key-b64-file",
        type=Path,
        help="Require the embedded license key to match this public key file.",
    )
    args = parser.parse_args()

    errors = validate(
        allow_template=args.allow_template,
        tag=args.tag,
        expected_public_key_file=args.public_key_b64_file,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
