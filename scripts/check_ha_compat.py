#!/usr/bin/env python3
"""Check the integration against the installed Home Assistant version."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components/maika"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_translations(
    services: dict[str, Any], translations: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    translated = translations.get("services", {})
    if set(services) != set(translated):
        errors.append(
            "service translation keys differ: "
            f"yaml={sorted(services)} translations={sorted(translated)}"
        )
        return errors

    for name, service in services.items():
        if not translated[name].get("name") or not translated[name].get("description"):
            errors.append(f"{name}: missing translated name or description")
        fields = set(service.get("fields", {}))
        translated_fields = set(translated[name].get("fields", {}))
        if fields != translated_fields:
            errors.append(
                f"{name}: field translation keys differ: "
                f"yaml={sorted(fields)} translations={sorted(translated_fields)}"
            )
        for field in fields & translated_fields:
            if not translated[name]["fields"][field].get("name"):
                errors.append(f"{name}.{field}: missing translated field name")
    return errors


def main() -> int:
    sys.dont_write_bytecode = True
    import yaml
    from homeassistant.helpers.selector import validate_selector

    sys.path.insert(0, str(ROOT))
    importlib.import_module("custom_components.maika")

    services = yaml.safe_load(
        (INTEGRATION / "services.yaml").read_text(encoding="utf-8")
    )
    errors: list[str] = []
    field_count = 0
    for name, service in services.items():
        if "target" in service:
            errors.append(f"{name}: device targets are not supported by hassfest")
        for field_name, field in service.get("fields", {}).items():
            if selector := field.get("selector"):
                field_count += 1
                try:
                    validate_selector(selector)
                except Exception as err:
                    errors.append(f"{name}.{field_name}: {err}")

    errors.extend(
        _check_translations(
            services,
            _load_json(INTEGRATION / "translations/en.json"),
        )
    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "Home Assistant compatibility checks passed: "
        f"{len(services)} services, {field_count} selectors"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
