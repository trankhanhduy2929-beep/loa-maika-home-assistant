#!/usr/bin/env python3
"""Validate the standalone MAIKA Home Assistant repository."""

from __future__ import annotations

import argparse
import ast
import asyncio
import base64
import binascii
import ipaddress
import json
import re
import runpy
import struct
import sys
import types
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
    "docs/VOICE_COMMANDS.md",
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
    "custom_components/maika/voice_success_audio.py",
    "custom_components/maika/voice_rules.py",
    "custom_components/maika/content_store.py",
    "custom_components/maika/brand/icon.png",
    "custom_components/maika/manifest.json",
    "custom_components/maika/services.py",
    "custom_components/maika/services.yaml",
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

    portal_url = config_values.get("PORTAL_PUBLIC_URL", "")
    if portal_url:
        parsed = urlsplit(portal_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            errors.append("PORTAL_PUBLIC_URL must be a clean HTTPS origin")
        else:
            try:
                ipaddress.ip_address(parsed.hostname)
            except ValueError:
                pass
            else:
                errors.append("PORTAL_PUBLIC_URL must use a hostname")

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


def _validate_voice_success_audio(errors: list[str]) -> None:
    """Validate success audio source/timing wiring in the panel and runtime."""
    const_values = _string_constants(ROOT / f"custom_components/{DOMAIN}/const.py")
    expected_sources = {
        const_values.get("VOICE_SUCCESS_AUDIO_SOURCE_DISABLED"),
        const_values.get("VOICE_SUCCESS_AUDIO_SOURCE_BUNDLED"),
        const_values.get("VOICE_SUCCESS_AUDIO_SOURCE_LIBRARY"),
        const_values.get("VOICE_SUCCESS_AUDIO_SOURCE_CUSTOM"),
    }
    if expected_sources != {"disabled", "bundled", "library", "custom"}:
        errors.append("Voice success audio source constants are invalid")
    const_source = (ROOT / f"custom_components/{DOMAIN}/const.py").read_text(
        encoding="utf-8"
    )
    if 'VOICE_SUCCESS_AUDIO_LIBRARY_DIRS = ("www", "mp3", "media")' not in const_source:
        errors.append("Voice success audio library folders are invalid")
    expected_timings = {
        const_values.get("VOICE_SUCCESS_AUDIO_TIMING_AFTER_SUCCESS"),
        const_values.get("VOICE_SUCCESS_AUDIO_TIMING_PRIORITY"),
    }
    if expected_timings != {"after_success", "priority"}:
        errors.append("Voice success audio timing constants are invalid")

    resolver = (ROOT / f"custom_components/{DOMAIN}/voice_success_audio.py").read_text(
        encoding="utf-8"
    )
    for marker in (
        "BUNDLED_VOICE_SUCCESS_AUDIO_URL",
        "CONF_VOICE_SUCCESS_AUDIO_URL",
        "CONF_VOICE_SUCCESS_AUDIO_TIMING",
        "resolve_voice_success_audio_timing",
        "pre-1.7",
    ):
        if marker not in resolver:
            errors.append(f"Voice success audio resolver is missing {marker}")

    panel = (ROOT / f"custom_components/{DOMAIN}/panel.py").read_text(encoding="utf-8")
    for marker in (
        "MaikaPanelRemindersView",
        "/api/maika/panel/reminders",
        "async_list_reminders",
        "build_reminder_payload",
    ):
        if marker not in panel:
            errors.append(f"Panel is missing reminder integration {marker}")
    editor = (
        ROOT / f"custom_components/{DOMAIN}/frontend/maika-voice-editor.js"
    ).read_text(encoding="utf-8")
    coordinator = (ROOT / f"custom_components/{DOMAIN}/coordinator.py").read_text(
        encoding="utf-8"
    )
    for marker in (
        "CONF_VOICE_SUCCESS_AUDIO_SOURCE",
        "CONF_VOICE_SUCCESS_AUDIO_TIMING",
        "resolve_voice_success_audio_source",
        "resolve_voice_success_audio_timing",
    ):
        if marker not in panel:
            errors.append(f"Panel is missing voice audio marker {marker}")
    for marker in (
        "voice_success_audio_source",
        "voice_success_audio_timing",
        "voice_success_audio_url",
        "voice_success_audio_path",
        "voice_success_media_player_entity_id",
    ):
        if marker not in editor:
            errors.append(f"Voice editor is missing audio option {marker}")
    for field, expected in (
        ("audio-source", expected_sources),
        ("audio-timing", expected_timings),
    ):
        select = re.search(rf'<select id="{field}">(.*?)</select>', editor, re.DOTALL)
        choices = set(
            re.findall(r'<option value="([^"]+)"', select[1] if select else "")
        )
        if choices != expected:
            errors.append(f"Voice editor has invalid {field} choices")
    if "resolve_voice_success_audio_url" not in coordinator:
        errors.append("Coordinator must resolve bundled/custom success audio")
    for marker in (
        "resolve_voice_success_audio_timing",
        "dialog_request_id=dialog_request_id",
        "MAIKA priority voice success audio",
    ):
        if marker not in coordinator:
            errors.append(f"Coordinator is missing priority audio marker {marker}")

    api = (ROOT / f"custom_components/{DOMAIN}/api.py").read_text(encoding="utf-8")
    for marker in ("server_message_id", 'event_header["serverMessageId"]'):
        if marker not in api:
            errors.append(f"MAIKA cast API is missing conversation marker {marker}")


def _validate_voice_rules(errors: list[str]) -> None:
    """Smoke-test the standalone safe voice-rule parser."""
    path = ROOT / f"custom_components/{DOMAIN}/voice_rules.py"
    coordinator_path = ROOT / f"custom_components/{DOMAIN}/coordinator.py"
    parser_source = path.read_text(encoding="utf-8")
    coordinator_source = coordinator_path.read_text(encoding="utf-8")
    for marker in (
        "_VOICE_SERVICE_SPECS",
        "_RESERVED_SERVICE_DATA_KEYS",
        "MAX_SERVICE_DATA_LENGTH",
        "MappingProxyType",
    ):
        if marker not in parser_source:
            errors.append(f"Voice rule parser is missing safeguard {marker}")
    for marker in (
        "service_data = dict(rule.service_data)",
        "service_data[ATTR_ENTITY_ID] = rule.entity_id",
    ):
        if marker not in coordinator_source:
            errors.append(f"Voice rule coordinator is missing safeguard {marker}")

    module_name = "_maika_voice_rules_validation"
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    previous_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        exec(compile(parser_source, str(path), "exec"), module.__dict__)
        rules = module.parse_voice_command_rules(
            "\n".join(
                (
                    "bật đèn | light.den | turn_on",
                    'đèn 70 | light.den | turn_on | {"brightness_pct":70}',
                    'mở rèm nửa | cover.rem | set_cover_position | {"position":50}',
                    'điều hòa 26 | climate.may_lanh | set_temperature | {"temperature":26}',
                    'quạt 60 | fan.quat | set_percentage | {"percentage":60}',
                    "chạy cảnh ngủ | scene.di_ngu | turn_on",
                    "bấm chuông | button.chuong | press",
                )
            )
        )
        if len(rules) != 7:
            errors.append("Voice rule parser did not preserve valid rules")
        elif (
            rules[0].service != "light.turn_on"
            or dict(rules[1].service_data) != {"brightness_pct": 70}
            or dict(rules[2].service_data) != {"position": 50}
        ):
            errors.append("Voice rule parser returned unexpected service data")
        read_rules = module.parse_voice_command_rules(
            "nhiệt độ phòng khách | sensor.nhiet_do | read"
        )
        catalog = module.voice_action_catalog()
        if (
            len(read_rules) != 1
            or not read_rules[0].is_read
            or read_rules[0].service is not None
            or "read" not in catalog.get("sensor", {})
            or catalog["sensor"]["read"]["fields"]
        ):
            errors.append("Voice rule parser did not preserve the read action")

        rejected_rules = (
            'x | light.a | turn_on | {"entity_id":"light.b"}',
            'x | fan.a | set_percentage | {"percentage":101}',
            "x | homeassistant.a | restart",
            "x | climate.a | set_temperature",
            'x | light.a | turn_on | {"brightness_pct":{"nested":1}}',
            "x | lock.a | unlock",
            'x | light.a | turn_on | {"brightness_pct":1,"brightness_pct":2}',
            'x | automation.a | trigger | {"skip_condition":"false"}',
        )
        for rule_text in rejected_rules:
            try:
                module.parse_voice_command_rules(rule_text)
            except module.VoiceCommandRulesError:
                continue
            errors.append(f"Unsafe voice rule was accepted: {rule_text}")
        catalog = module.voice_action_catalog()
        json.dumps(catalog)
        if set(catalog) != set(module._VOICE_SERVICE_SPECS):
            errors.append("Voice editor catalog must match the rule allow-list")
        if catalog["fan"]["set_percentage"]["fields"]["percentage"] != {
            "type": "integer",
            "min": 0,
            "max": 100,
        }:
            errors.append("Voice editor percentage bounds are incorrect")
        if catalog["climate"]["set_temperature"]["required"] != ["temperature"]:
            errors.append("Voice editor is missing required temperature")
        if "unlock" in catalog["lock"]:
            errors.append("Voice editor must not allow unlocking doors")
        automation = module.parse_voice_command_rules(
            'chạy cảnh | automation.demo | trigger | {"skip_condition":false}'
        )[0]
        if dict(automation.service_data) != {"skip_condition": False}:
            errors.append("Automation condition choice was not preserved")
        _validate_panel_options(errors, module)
    except Exception as err:
        errors.append(f"Voice rule validation failed: {err}")
    finally:
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module


def _validate_panel_options(errors: list[str], voice_module: types.ModuleType) -> None:
    """Exercise panel option handling without a running Home Assistant."""
    directory = ROOT / f"custom_components/{DOMAIN}"
    namespace = {
        "parse_voice_command_rules": voice_module.parse_voice_command_rules,
        "VoiceCommandRulesError": voice_module.VoiceCommandRulesError,
    }
    for filename in ("const.py", "media_url.py"):
        path = directory / filename
        exec(compile(path.read_text(), str(path), "exec"), namespace)

    class View:
        @staticmethod
        def json(data: Any, status_code: int = 200) -> tuple[int, Any]:
            return status_code, data

        @staticmethod
        def json_message(message: str, status_code: int) -> tuple[int, Any]:
            return status_code, {"message": message}

    namespace["HomeAssistantView"] = View
    selected = {
        "resolve_voice_success_audio_source",
        "resolve_voice_success_audio_url",
        "resolve_voice_success_audio_timing",
        "resolve_voice_success_audio_path",
        "normalize_audio_path",
        "resolve_audio_file",
        "has_voice_success_audio",
        "_serialize_entry",
        "_serialize_license",
        "_serial_for_device",
        "_public_options",
        "_validate_options",
        "_entry_by_id",
        "_read_json",
        "_json_safe",
        "MaikaPanelMixin",
        "MaikaPanelOptionsView",
        "MaikaPanelLicenseView",
    }
    namespace["Path"] = Path
    namespace["json"] = json
    namespace["HomeAssistant"] = object
    namespace["StaticPathConfig"] = object
    namespace["get_url"] = lambda home_assistant, prefer_external=False: (
        "https://ha.test"
    )

    class NoURLAvailableError(Exception):
        """Stub for the Home Assistant network helper."""

    namespace["NoURLAvailableError"] = NoURLAvailableError
    for filename in ("audio_library.py", "voice_success_audio.py", "panel.py"):
        path = directory / filename
        tree = ast.parse(path.read_text(), filename=str(path))
        tree.body = [
            node
            for node in tree.body
            if getattr(node, "name", "") in selected
            or (isinstance(node, ast.ImportFrom) and node.module == "__future__")
            or (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "_OPTION_KEYS"
                    for target in node.targets
                )
            )
        ]
        exec(compile(tree, str(path), "exec"), namespace)

    rules_key = namespace["CONF_VOICE_COMMAND_RULES"]
    audio_key = namespace["CONF_VOICE_SUCCESS_AUDIO_SOURCE"]
    scan_key = namespace["CONF_SCAN_INTERVAL"]
    entry = types.SimpleNamespace(
        entry_id="maika-test",
        title="MAIKA test",
        options={
            rules_key: "# legacy\nbật đèn | light.demo | turn_on",
            audio_key: "bundled",
            scan_key: 60,
        },
    )

    def update_entry(target: Any, *, options: dict[str, Any]) -> None:
        target.options = options

    hass = types.SimpleNamespace(
        config_entries=types.SimpleNamespace(
            async_get_entry=lambda entry_id: (
                entry if entry_id == entry.entry_id else None
            ),
            async_update_entry=update_entry,
        ),
        states=types.SimpleNamespace(
            async_entity_ids=lambda domain: ["media_player.test"]
        ),
    )
    view = namespace["MaikaPanelOptionsView"](hass)
    server_urls = []

    class LicenseStore:
        record = types.SimpleNamespace(server_url="https://old.example.test")

        def __init__(self, home_assistant: Any) -> None:
            pass

        async def async_load(self) -> Any:
            return self.record

        async def async_save(self, record: Any) -> None:
            type(self).record = record

    class LicenseClient:
        def __init__(self, home_assistant: Any, server_url: str, identity: Any) -> None:
            server_urls.append(server_url)

        async def async_activate(self, key: str) -> Any:
            assert key == "MAIKA-TEST-ONLY"
            return types.SimpleNamespace(status="active", activation_code="TEST")

    async def identity(home_assistant: Any) -> Any:
        return types.SimpleNamespace(installation_hash="test-installation")

    async def reload_entry(entry_id: str) -> None:
        assert entry_id == entry.entry_id

    namespace.update(
        MaikaLicenseStore=LicenseStore,
        MaikaLicenseClient=LicenseClient,
        MaikaStoredLicense=types.SimpleNamespace(
            from_response=lambda **values: types.SimpleNamespace(**values)
        ),
        normalize_license_key=lambda key: key,
        normalize_license_server_url=lambda url: url,
        async_get_installation_identity=identity,
        DEFAULT_LICENSE_SERVER_URL="https://default.example.test",
    )
    hass.config_entries.async_reload = reload_entry
    hass.async_create_task = lambda task: task.close()

    async def request(payload: Any) -> tuple[int, Any]:
        async def read_json() -> Any:
            return payload

        return await view.post(types.SimpleNamespace(json=read_json))

    async def check() -> None:
        original = dict(entry.options)
        namespace.update(
            er=types.SimpleNamespace(
                async_get=lambda home_assistant: None,
                async_entries_for_config_entry=lambda registry, entry_id: [],
            ),
            dr=types.SimpleNamespace(async_get=lambda home_assistant: None),
            config=types.SimpleNamespace(
                path=lambda *parts: str(Path("/config").joinpath(*parts))
            ),
            BUNDLED_VOICE_SUCCESS_AUDIO_URL="https://example.test/maika.mp3",
        )
        snapshot = namespace["_serialize_entry"](hass, entry)
        assert snapshot["entry_id"] == entry.entry_id
        assert snapshot["license"]["status"] == "unavailable"
        assert snapshot["options"][rules_key] == original[rules_key]
        assert snapshot["devices"] == {}
        resolve_audio = namespace["resolve_voice_success_audio_url"]
        timing_key = namespace["CONF_VOICE_SUCCESS_AUDIO_TIMING"]
        url_key = namespace["CONF_VOICE_SUCCESS_AUDIO_URL"]
        legacy_audio = {url_key: "https://example.test/legacy.mp3"}
        assert resolve_audio(legacy_audio) == legacy_audio[url_key]
        assert (
            resolve_audio({audio_key: "bundled"})
            == namespace["BUNDLED_VOICE_SUCCESS_AUDIO_URL"]
        )
        assert resolve_audio({**legacy_audio, audio_key: "disabled"}) == ""
        assert (
            resolve_audio({**legacy_audio, audio_key: "custom"})
            == legacy_audio[url_key]
        )
        assert not namespace["has_voice_success_audio"]({audio_key: "disabled"})
        for timing in ("priority", "after_success"):
            assert (
                namespace["resolve_voice_success_audio_timing"]({timing_key: timing})
                == timing
            )
        assert (
            namespace["resolve_voice_success_audio_timing"]({timing_key: "invalid"})
            == namespace["DEFAULT_VOICE_SUCCESS_AUDIO_TIMING"]
        )
        status, _ = await request(
            {"entry_id": entry.entry_id, "options": {scan_key: 90}}
        )
        assert status == 200
        assert entry.options == {**original, scan_key: 90}
        expected = namespace["_public_options"](entry.options)
        newer = (
            '# legacy\nngủ ngon | automation.demo | trigger | {"skip_condition":false}'
        )
        payload = {
            "entry_id": entry.entry_id,
            "options": {rules_key: newer},
            "expected_voice_rules": original[rules_key],
            "expected_voice_options": {audio_key: expected[audio_key]},
        }
        status, _ = await request(payload)
        assert status == 200 and entry.options[rules_key] == newer
        license_view = namespace["MaikaPanelLicenseView"](hass)

        async def activation_body() -> Any:
            return {"entry_id": entry.entry_id, "license_key": "MAIKA-TEST-ONLY"}

        for record in (
            types.SimpleNamespace(server_url="https://old.example.test"),
            None,
        ):
            LicenseStore.record = record
            status, data = await license_view.post(
                types.SimpleNamespace(json=activation_body)
            )
            assert status == 200 and data["status"] == "active"
            assert LicenseStore.record.installation_hash == "test-installation"
        assert server_urls == [
            "https://old.example.test",
            "https://default.example.test",
        ]
        before_conflict = dict(entry.options)
        status, data = await request(payload)
        assert status == 409 and data["message"] == "voice_rules_changed"
        assert entry.options == before_conflict
        payload["expected_voice_rules"] = newer
        entry.options[audio_key] = "disabled"
        status, _ = await request(payload)
        assert status == 409 and entry.options[audio_key] == "disabled"
        status, _ = await request(
            {
                "entry_id": entry.entry_id,
                "options": {rules_key: "x | lock.door | unlock"},
            }
        )
        assert status == 400 and entry.options[rules_key] == newer
        status, _ = await request({"entry_id": "missing", "options": {scan_key: 60}})
        assert status == 404
        status, _ = await request(
            {"entry_id": entry.entry_id, "options": [], "expected_voice_options": []}
        )
        assert status == 400
        status, _ = await request(
            {"entry_id": entry.entry_id, "options": {}, "expected_voice_options": []}
        )
        assert status == 400
        status, _ = await request(
            {"entry_id": entry.entry_id, "options": {scan_key: 60}}
        )
        assert status == 200 and entry.options[rules_key] == newer
        base_key = namespace["CONF_CLOUD_CAST_BASE_URL"]
        status, data = await request(
            {"entry_id": entry.entry_id, "options": {base_key: "not a url"}}
        )
        assert status == 400
        assert data["errors"].get(base_key) == "invalid_cloud_cast_base_url"
        status, _ = await request(
            {
                "entry_id": entry.entry_id,
                "options": {base_key: "http://192.168.1.42:8123"},
            }
        )
        assert status == 200 and entry.options[base_key] == "http://192.168.1.42:8123"
        status, _ = await request(
            {"entry_id": entry.entry_id, "options": {base_key: ""}}
        )
        assert status == 200 and entry.options[base_key] == ""

    try:
        asyncio.run(check())
    except Exception as err:
        errors.append(
            f"Panel options compatibility/conflict validation failed: {err!r}"
        )


def _validate_media_cast_config(errors: list[str]) -> None:
    """Exercise the cloud-cast URL rewrite helpers without Home Assistant."""
    directory = ROOT / f"custom_components/{DOMAIN}"

    media_namespace: dict[str, Any] = {}
    media_path = directory / "media_url.py"
    exec(compile(media_path.read_text(), str(media_path), "exec"), media_namespace)
    is_reachable = media_namespace["is_reachable_media_host"]
    rewrite = media_namespace["rewrite_media_origin"]

    for host, expected in (
        ("homeassistant.local", False),
        ("hassio", False),
        ("localhost", False),
        ("127.0.0.1", False),
        ("192.168.1.42", True),
        ("10.0.0.5", True),
        ("media.example.org", True),
    ):
        if is_reachable(host) is not expected:
            errors.append(f"is_reachable_media_host({host!r}) must be {expected}")

    signed = "http://homeassistant.local:8123/media/local/nhac.mp3?authSig=abc.def"
    if rewrite(signed, "http://192.168.1.42:8123") != (
        "http://192.168.1.42:8123/media/local/nhac.mp3?authSig=abc.def"
    ):
        errors.append("rewrite_media_origin must keep the path and signature")
    if rewrite("https://cdn.example.org/a.mp3", "") != "https://cdn.example.org/a.mp3":
        errors.append("rewrite_media_origin must be a no-op without a base URL")
    if rewrite("not-a-url", "http://192.168.1.42:8123") != "not-a-url":
        errors.append("rewrite_media_origin must ignore non-HTTP values")

    class NoURLAvailableError(Exception):
        """Stub for the Home Assistant network helper."""

    def is_hass_url(home_assistant: Any, url: str) -> bool:
        host = (urlsplit(url).hostname or "").lower()
        return host in {"homeassistant.local", "192.168.1.42", "ha.example.org"}

    def get_url(home_assistant: Any, **kwargs: Any) -> str:
        if kwargs.get("prefer_external"):
            return str(home_assistant.config.external_url)
        return str(home_assistant.config.internal_url)

    namespace: dict[str, Any] = {
        "HomeAssistant": object,
        "NoURLAvailableError": NoURLAvailableError,
        "get_url": get_url,
        "is_hass_url": is_hass_url,
        "is_reachable_media_host": is_reachable,
        "rewrite_media_origin": rewrite,
        "public_relay_url": lambda home_assistant, media_url: None,
    }
    cast_path = directory / "cast_target.py"
    cast_namespace: dict[str, Any] = dict(namespace)
    cast_tree = ast.parse(cast_path.read_text(), filename=str(cast_path))
    cast_tree.body = [
        node
        for node in cast_tree.body
        if not (
            isinstance(node, ast.ImportFrom)
            and (node.level > 0 or (node.module or "").startswith("homeassistant"))
        )
    ]
    exec(compile(cast_tree, str(cast_path), "exec"), cast_namespace)

    def make_hass(*, use_ssl: bool, local_ip: str | None) -> Any:
        return types.SimpleNamespace(
            config=types.SimpleNamespace(
                api=types.SimpleNamespace(
                    local_ip=local_ip, port=8123, use_ssl=use_ssl
                ),
                internal_url="http://homeassistant.local:8123",
                external_url="https://ha.example.org",
            )
        )

    plain_hass = make_hass(use_ssl=False, local_ip="192.168.1.42")
    if (
        cast_namespace["resolve_cast_base_url"](plain_hass)
        != "http://192.168.1.42:8123"
    ):
        errors.append("resolve_cast_base_url must prefer the LAN IP")
    if (
        cast_namespace["resolve_cast_base_url"](plain_hass, "http://10.0.0.9:8123")
        != "http://10.0.0.9:8123"
    ):
        errors.append("resolve_cast_base_url must honour the explicit override")
    ssl_hass = make_hass(use_ssl=True, local_ip="192.168.1.42")
    if cast_namespace["resolve_cast_base_url"](ssl_hass) != "https://ha.example.org":
        errors.append("resolve_cast_base_url must not pin an HTTP IP behind TLS")

    ready = cast_namespace["cast_ready_url"]
    if ready(plain_hass, signed) != (
        "http://192.168.1.42:8123/media/local/nhac.mp3?authSig=abc.def"
    ):
        errors.append("cast_ready_url must rewrite an mDNS Home Assistant host")
    addon_media = "http://homeassistant.local:2032/api/media/token/audio.m4a"
    if ready(plain_hass, addon_media) != (
        "http://192.168.1.42:2032/api/media/token/audio.m4a"
    ):
        errors.append("cast_ready_url must keep the add-on media port")
    googlevideo = "https://rr3---sn-x.googlevideo.com/videoplayback?x=1"
    if ready(plain_hass, googlevideo) != googlevideo:
        errors.append("cast_ready_url must keep an already reachable host")
    override = ready(plain_hass, signed, "http://10.0.0.9:8123")
    if override != "http://10.0.0.9:8123/media/local/nhac.mp3?authSig=abc.def":
        errors.append("cast_ready_url must apply the explicit override")


def _validate_panel_configuration(errors: list[str]) -> None:
    """Keep panel-only configuration reachable without bypassing activation."""
    directory = ROOT / f"custom_components/{DOMAIN}"
    tree = ast.parse((directory / "config_flow.py").read_text())
    flow = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MaikaConfigFlow"
    )
    methods = {
        node.name
        for node in flow.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    required = {
        "async_step_user",
        "async_step_activation_pending",
        "async_step_account",
        "async_step_reauth",
        "async_step_reauth_confirm",
    }
    if not required <= methods:
        errors.append(
            "Initial activation, account setup and reauthentication must remain available"
        )
    if methods & {"async_get_options_flow", "async_supports_options_flow"} or any(
        isinstance(node, ast.ClassDef) and node.name == "MaikaOptionsFlow"
        for node in tree.body
    ):
        errors.append(
            "Integration Configure must be removed; ongoing settings belong in the panel"
        )
    for relative in ("strings.json", "translations/en.json", "translations/vi.json"):
        data = _load_json(directory / relative)
        if "options" in data or "selector" in data:
            errors.append(f"Obsolete options UI translations in {relative}")
        if not {"user", "activation_pending", "account", "reauth_confirm"} <= set(
            data.get("config", {}).get("step", {})
        ):
            errors.append(
                f"Missing installation/reauthentication translations in {relative}"
            )
        message = (
            data.get("exceptions", {}).get("license_unavailable", {}).get("message", "")
        )
        if set(re.findall(r"\{([a-z_]+)\}", message)) != {
            "license_error",
            "activation_code",
            "portal_url",
        }:
            errors.append(f"License recovery message lost placeholders in {relative}")

    namespace: dict[str, Any] = {
        "DOMAIN": DOMAIN,
        "PLATFORMS": [],
        "LICENSE_PORTAL_URL": "",
        "_LICENSE_NOTIFICATION_ID": "maika-test",
    }
    path = directory / "__init__.py"
    tree = ast.parse(path.read_text(), filename=str(path))
    selected = {
        "async_setup_entry",
        "async_unload_entry",
        "async_remove_entry",
        "_show_license_notification",
        "_async_handle_invalid_license",
    }
    tree.body = [
        node
        for node in tree.body
        if getattr(node, "name", "") in selected
        or (isinstance(node, ast.ImportFrom) and node.module == "__future__")
    ]
    exec(compile(tree, str(path), "exec"), namespace)
    events: list[str] = []
    notifications: list[str] = []
    entry = types.SimpleNamespace(
        entry_id="existing",
        data={"account": "unchanged"},
        options={
            "scan_interval": 90,
            "voice_command_rules": "bật đèn | light.demo | turn_on",
        },
    )
    entries = [entry]
    hass = types.SimpleNamespace(
        data={},
        config_entries=types.SimpleNamespace(async_entries=lambda domain: entries),
        unload_ok=True,
    )

    class LicenseUnavailableError(Exception):
        code = "license_expired"
        activation_code = "MAIKA-TEST"

    class EntryNotReady(Exception):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(kwargs)
            self.placeholders = kwargs["translation_placeholders"]

    async def register_panel(home_assistant: Any) -> None:
        events.append("panel")
        home_assistant.data["panel"] = True

    async def remove_panel(home_assistant: Any) -> None:
        events.append("remove_panel")
        home_assistant.data.pop("panel", None)

    async def create_license(home_assistant: Any) -> None:
        events.append("license")
        raise LicenseUnavailableError

    async def unload_platforms(target: Any, platforms: Any) -> bool:
        events.append("unload")
        return hass.unload_ok

    async def record_stop(component: str) -> None:
        events.append(component)

    async def reload_entry(entry_id: str) -> None:
        assert entry_id == entry.entry_id
        events.append("reload")

    hass.config_entries.async_unload_platforms = unload_platforms
    hass.config_entries.async_reload = reload_entry
    namespace.update(
        async_register_panel=register_panel,
        async_remove_panel=remove_panel,
        MaikaLicenseManager=types.SimpleNamespace(async_create=create_license),
        MaikaLicenseUnavailableError=LicenseUnavailableError,
        ConfigEntryNotReady=EntryNotReady,
        persistent_notification=types.SimpleNamespace(
            async_create=lambda home_assistant, message, **kwargs: notifications.append(
                message
            )
        ),
    )

    async def check() -> None:
        original_data, original_options = dict(entry.data), dict(entry.options)
        try:
            await namespace["async_setup_entry"](hass, entry)
        except EntryNotReady as err:
            assert err.placeholders["license_error"] == "license_expired"
        else:
            raise AssertionError("Expired license must not start the speaker")
        assert events == ["panel", "license"]
        assert hass.data["panel"]
        assert "/maika-panel" in notifications[-1]
        assert not hasattr(entry, "runtime_data")
        await namespace["_async_handle_invalid_license"](
            hass, entry, LicenseUnavailableError()
        )
        assert events[-1] == "reload" and hass.data["panel"]
        entry.runtime_data = types.SimpleNamespace(
            license_manager=types.SimpleNamespace(
                async_stop=lambda: record_stop("license_stop")
            ),
            coordinator=types.SimpleNamespace(
                async_stop=lambda: record_stop("coordinator_stop")
            ),
            client=types.SimpleNamespace(async_stop=lambda: record_stop("client_stop")),
        )
        events.clear()
        hass.unload_ok = False
        assert not await namespace["async_unload_entry"](hass, entry)
        assert events == ["unload"] and hass.data["panel"]
        events.clear()
        hass.unload_ok = True
        assert await namespace["async_unload_entry"](hass, entry)
        assert events == ["unload", "license_stop", "coordinator_stop", "client_stop"]
        assert hass.data["panel"]
        del entry.runtime_data
        other = types.SimpleNamespace(entry_id="other")
        for remaining in ([entry, other], [other]):
            entries[:] = remaining
            await namespace["async_remove_entry"](hass, entry)
            assert hass.data["panel"]
        for remaining in ([entry], []):
            entries[:] = remaining
            hass.data["panel"] = True
            await namespace["async_remove_entry"](hass, entry)
            assert "panel" not in hass.data
        assert entry.data == original_data and entry.options == original_options

    try:
        asyncio.run(check())
    except Exception as err:
        errors.append(f"Panel-only configuration lifecycle validation failed: {err!r}")


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
    version = ""
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
            _validate_voice_success_audio(errors)
            _validate_voice_rules(errors)
            _validate_media_cast_config(errors)
            playback_tests = runpy.run_path(str(ROOT / "scripts/test_media_player.py"))
            errors.extend(playback_tests["validate_media_player"]())
            live_playback_tests = runpy.run_path(
                str(ROOT / "scripts/test_live_playback.py")
            )
            errors.extend(live_playback_tests["validate_live_playback"]())
            content_store_tests = runpy.run_path(
                str(ROOT / "scripts/test_content_store.py")
            )
            errors.extend(content_store_tests["validate_content_store"]())
            nhaccuatui_tests = runpy.run_path(str(ROOT / "scripts/test_nhaccuatui.py"))
            errors.extend(nhaccuatui_tests["validate_nhaccuatui"]())
            media_relay_tests = runpy.run_path(
                str(ROOT / "scripts/test_media_relay.py")
            )
            errors.extend(media_relay_tests["validate_media_relay"]())
            reminder_tests = runpy.run_path(str(ROOT / "scripts/test_reminders.py"))
            errors.extend(reminder_tests["validate_reminders"]())
            api_tests = runpy.run_path(str(ROOT / "scripts/test_api_endpoints.py"))
            errors.extend(api_tests["validate_api_endpoints"]())
            service_tests = runpy.run_path(str(ROOT / "scripts/test_services.py"))
            errors.extend(service_tests["validate_services"]())
            _validate_panel_configuration(errors)

    if hacs_path.is_file():
        try:
            hacs = _load_json(hacs_path)
        except ValueError:
            hacs = {}
        if not isinstance(hacs.get("zip_release"), bool):
            errors.append("hacs.json zip_release must be a boolean")
        if hacs.get("zip_release") is True and hacs.get("filename") != "maika.zip":
            errors.append(
                "hacs.json filename must be maika.zip when zip_release is true"
            )
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
    if version:
        versioned_hacs_zip = dist / f"maika-v{version}-hacs.zip"
        versioned_manual_zip = dist / f"maika-v{version}-manual.zip"
        if versioned_hacs_zip.exists():
            _validate_zip(versioned_hacs_zip, hacs_format=True, errors=errors)
        if versioned_manual_zip.exists():
            _validate_zip(versioned_manual_zip, hacs_format=False, errors=errors)

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
