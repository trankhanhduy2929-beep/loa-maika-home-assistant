#!/usr/bin/env python3
"""Build a deterministic clean source archive for GitHub handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = ROOT.name
FIXED_TIMESTAMP = (2026, 8, 17, 0, 0, 0)
EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".storage",
    ".venv",
    ".vscode",
    "__pycache__",
    "dist",
    "htmlcov",
    "node_modules",
    "venv",
}
EXCLUDED_NAMES = {
    ".dev.vars",
    ".env",
    ".env.local",
    ".env.production",
    ".env.production.local",
    "secrets.yaml",
}


def source_files() -> list[Path]:
    """Return repository files while excluding generated and private state."""
    return sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
            and path.name not in EXCLUDED_NAMES
            and path.suffix not in {".pyc", ".zip"}
        ),
        key=lambda path: path.as_posix(),
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Release tag, for example v1.6.0")
    parser.add_argument("--output", default="dist")
    parser.add_argument(
        "--public-key-b64-file",
        type=Path,
        help="Require the embedded license key to match this public key file.",
    )
    args = parser.parse_args()

    manifest = json.loads(
        (ROOT / "custom_components/maika/manifest.json").read_text(encoding="utf-8")
    )
    version = str(manifest["version"])
    tag = args.tag or f"v{version}"
    if tag.removeprefix("v") != version:
        raise SystemExit(f"Tag {tag} does not match manifest version {version}")

    validate_command = [
        sys.executable,
        str(ROOT / "scripts/validate_repository.py"),
        "--tag",
        tag,
    ]
    if args.public_key_b64_file:
        validate_command.extend(
            ("--public-key-b64-file", str(args.public_key_b64_file.resolve()))
        )
    subprocess.run(validate_command, cwd=ROOT, check=True)

    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{ARCHIVE_ROOT}-v{version}-github-source.zip"
    with zipfile.ZipFile(
        archive,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zip_file:
        for source in source_files():
            relative = source.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(
                f"{ARCHIVE_ROOT}/{relative}",
                date_time=FIXED_TIMESTAMP,
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zip_file.writestr(info, source.read_bytes(), compresslevel=9)

    checksum = output / f"{archive.name}.sha256"
    checksum.write_text(
        f"{sha256(archive)}  {archive.name}\n",
        encoding="utf-8",
    )
    print(archive.relative_to(ROOT))
    print(checksum.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
