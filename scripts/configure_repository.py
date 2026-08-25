#!/usr/bin/env python3
"""Configure or reconfigure GitHub repository metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER_PLACEHOLDER = "GITHUB_USERNAME"
LEGACY_REPOSITORY_PLACEHOLDER = "ha-maika"
TEMPLATE_NOTICE = re.compile(
    r"\n?<!-- TEMPLATE_NOTICE_START -->.*?<!-- TEMPLATE_NOTICE_END -->\n?",
    re.DOTALL,
)
FILES = (
    ".github/CODEOWNERS",
    ".github/ISSUE_TEMPLATE/config.yml",
    "README.md",
    "REPOSITORY_SETUP.md",
    "SECURITY.md",
    "custom_components/maika/manifest.json",
)


def _validate_owner(value: str) -> str:
    owner = value.removeprefix("@").strip()
    if (
        not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", owner)
        or "--" in owner
    ):
        raise argparse.ArgumentTypeError("Invalid GitHub username or organization")
    return owner


def _validate_repository(value: str) -> str:
    repository = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", repository):
        raise argparse.ArgumentTypeError("Invalid GitHub repository name")
    return repository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", required=True, type=_validate_owner)
    parser.add_argument(
        "--repo",
        required=True,
        type=_validate_repository,
    )
    args = parser.parse_args()

    manifest_path = ROOT / "custom_components/maika/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    documentation = str(manifest.get("documentation", ""))
    current_repository = re.fullmatch(
        r"https://github\.com/([^/]+)/([^/]+)", documentation
    )
    current_owner = current_repository.group(1) if current_repository else None
    current_name = current_repository.group(2) if current_repository else None

    changed = 0
    for relative in FILES:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        updated = text.replace(OWNER_PLACEHOLDER, args.owner).replace(
            LEGACY_REPOSITORY_PLACEHOLDER, args.repo
        )
        if current_owner:
            updated = updated.replace(current_owner, args.owner)
        if current_name:
            updated = updated.replace(current_name, args.repo)
        if relative == "README.md":
            updated = TEMPLATE_NOTICE.sub("\n", updated)
        if updated != text:
            path.write_bytes(updated.encode("utf-8"))
            changed += 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_url = f"https://github.com/{args.owner}/{args.repo}"
    if manifest.get("documentation") != expected_url:
        raise RuntimeError("Unable to update manifest documentation URL")
    if manifest.get("issue_tracker") != f"{expected_url}/issues":
        raise RuntimeError("Unable to update manifest issue tracker URL")
    if manifest.get("codeowners") != [f"@{args.owner}"]:
        raise RuntimeError("Unable to update manifest codeowner")

    if changed == 0:
        print("No template metadata changed; repository may already be configured")
    else:
        print(f"Configured {args.owner}/{args.repo} in {changed} files")
    print("Next: run scripts/validate_repository.py, then push to GitHub")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
