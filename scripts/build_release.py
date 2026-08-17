#!/usr/bin/env python3
"""Build deterministic HACS and manual-install release archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components/maika"
FIXED_TIMESTAMP = (2026, 8, 17, 0, 0, 0)


def _integration_files() -> list[Path]:
    files = []
    for path in INTEGRATION.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".pyc" or "__pycache__" in path.parts:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.as_posix())


def _write_zip(path: Path, *, manual: bool) -> None:
    with zipfile.ZipFile(
        path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for source in _integration_files():
            relative = source.relative_to(INTEGRATION).as_posix()
            arcname = f"custom_components/maika/{relative}" if manual else relative
            info = zipfile.ZipInfo(arcname, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes(), compresslevel=9)


def _sha256(path: Path) -> str:
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
        "--allow-template",
        action="store_true",
        help="Allow packaged GitHub metadata placeholders.",
    )
    args = parser.parse_args()

    validate_command = [sys.executable, str(ROOT / "scripts/validate_repository.py")]
    if args.allow_template:
        validate_command.append("--allow-template")
    if args.tag:
        validate_command.extend(("--tag", args.tag))
    subprocess.run(validate_command, cwd=ROOT, check=True)

    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    version = str(manifest["version"])
    tag = args.tag or f"v{version}"
    if tag.removeprefix("v") != version:
        raise SystemExit(f"Tag {tag} does not match manifest version {version}")

    output = ROOT / args.output
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    hacs_zip = output / "maika.zip"
    manual_zip = output / "maika-manual.zip"
    _write_zip(hacs_zip, manual=False)
    _write_zip(manual_zip, manual=True)

    checksums = output / "SHA256SUMS.txt"
    checksums.write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in (hacs_zip, manual_zip)),
        encoding="utf-8",
    )
    print(f"Built MAIKA Speaker {version}")
    for path in (hacs_zip, manual_zip, checksums):
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
