"""Safe exact-match rules for MAIKA voice commands."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

MAX_VOICE_COMMAND_RULES = 200
MAX_RULE_TEXT_LENGTH = 100_000
MAX_RULE_LINE_LENGTH = 2_048
MAX_PHRASE_LENGTH = 200
MAX_SERVICE_DATA_LENGTH = 2_048
MAX_SERVICE_DATA_KEYS = 12
MAX_SERVICE_STRING_LENGTH = 255

_ENTITY_ID_PATTERN = re.compile(r"[a-z_][a-z0-9_]*\.[a-z0-9_]+")
_DURATION_PATTERN = re.compile(r"(?:\d{1,3}:)?\d{1,3}:\d{2}")
_RESERVED_SERVICE_DATA_KEYS = frozenset(
    {
        "entity_id",
        "target",
        "device_id",
        "area_id",
        "floor_id",
        "domain",
        "service",
        "context",
        "variables",
        "code",
        "credential",
        "password",
        "token",
        "access_token",
    }
)

type ServiceDataValidator = Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class _VoiceActionSpec:
    """Allowed service data for one Home Assistant action."""

    fields: Mapping[str, ServiceDataValidator] = field(
        default_factory=lambda: MappingProxyType({})
    )
    required: frozenset[str] = frozenset()
    mutually_exclusive: tuple[frozenset[str], ...] = ()


def _spec(
    fields: Mapping[str, ServiceDataValidator] | None = None,
    *,
    required: tuple[str, ...] = (),
    mutually_exclusive: tuple[tuple[str, ...], ...] = (),
) -> _VoiceActionSpec:
    """Build an immutable action specification."""
    return _VoiceActionSpec(
        fields=MappingProxyType(dict(fields or {})),
        required=frozenset(required),
        mutually_exclusive=tuple(frozenset(group) for group in mutually_exclusive),
    )


def _simple_actions(*actions: str) -> dict[str, _VoiceActionSpec]:
    return {action: _spec() for action in actions}


def _string(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("must be a string")
    value = value.strip()
    if not value:
        raise ValueError("cannot be empty")
    if len(value) > MAX_SERVICE_STRING_LENGTH:
        raise ValueError(f"must be at most {MAX_SERVICE_STRING_LENGTH} characters")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError("cannot contain control characters")
    return value


def _enum(*values: str) -> ServiceDataValidator:
    allowed = frozenset(values)

    def validate(value: Any) -> str:
        normalized = _string(value).casefold()
        if normalized not in allowed:
            choices = ", ".join(sorted(allowed))
            raise ValueError(f"must be one of: {choices}")
        return normalized

    return validate


def _boolean(value: Any) -> bool:
    if type(value) is not bool:
        raise ValueError("must be true or false")
    return value


def _number(minimum: float, maximum: float) -> ServiceDataValidator:
    def validate(value: Any) -> int | float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("must be a number")
        if not math.isfinite(float(value)):
            raise ValueError("must be a finite number")
        if value < minimum or value > maximum:
            raise ValueError(f"must be between {minimum:g} and {maximum:g}")
        return value

    return validate


def _integer(minimum: int, maximum: int) -> ServiceDataValidator:
    def validate(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("must be an integer")
        if isinstance(value, float):
            if not math.isfinite(value) or not value.is_integer():
                raise ValueError("must be an integer")
            value = int(value)
        if value < minimum or value > maximum:
            raise ValueError(f"must be between {minimum} and {maximum}")
        return int(value)

    return validate


def _sequence(*validators: ServiceDataValidator) -> ServiceDataValidator:
    def validate(value: Any) -> tuple[int | float, ...]:
        if not isinstance(value, (list, tuple)) or len(value) != len(validators):
            raise ValueError(f"must contain exactly {len(validators)} values")
        return tuple(
            validator(item) for validator, item in zip(validators, value, strict=True)
        )

    return validate


def _tone(value: Any) -> int | str:
    if isinstance(value, str):
        return _string(value)
    return _integer(0, 1_000_000)(value)


def _duration(value: Any) -> str:
    value = _string(value)
    if not _DURATION_PATTERN.fullmatch(value):
        raise ValueError("must use HH:MM:SS or MM:SS format")
    parts = [int(part) for part in value.split(":")]
    minutes, seconds = parts[-2:]
    if minutes > 59 or seconds > 59:
        raise ValueError("minutes and seconds must be between 00 and 59")
    return value


_LIGHT_TURN_ON_FIELDS: dict[str, ServiceDataValidator] = {
    "brightness": _integer(0, 255),
    "brightness_pct": _number(0, 100),
    "brightness_step": _integer(-255, 255),
    "brightness_step_pct": _number(-100, 100),
    "color_temp_kelvin": _integer(1, 100_000),
    "rgb_color": _sequence(*(_integer(0, 255) for _ in range(3))),
    "rgbw_color": _sequence(*(_integer(0, 255) for _ in range(4))),
    "rgbww_color": _sequence(*(_integer(0, 255) for _ in range(5))),
    "hs_color": _sequence(_number(0, 360), _number(0, 100)),
    "xy_color": _sequence(_number(0, 1), _number(0, 1)),
    "color_name": _string,
    "profile": _string,
    "flash": _enum("short", "long"),
    "effect": _string,
    "transition": _number(0, 6_553),
}

_LIGHT_TURN_OFF_FIELDS: dict[str, ServiceDataValidator] = {
    "flash": _enum("short", "long"),
    "transition": _number(0, 6_553),
}

_LIGHT_BRIGHTNESS_FIELDS = (
    "brightness",
    "brightness_pct",
    "brightness_step",
    "brightness_step_pct",
)
_LIGHT_COLOR_FIELDS = (
    "profile",
    "color_temp_kelvin",
    "rgb_color",
    "rgbw_color",
    "rgbww_color",
    "hs_color",
    "xy_color",
    "color_name",
)

_VOICE_SERVICE_SPECS: dict[str, dict[str, _VoiceActionSpec]] = {
    "light": {
        "turn_on": _spec(
            _LIGHT_TURN_ON_FIELDS,
            mutually_exclusive=(_LIGHT_BRIGHTNESS_FIELDS, _LIGHT_COLOR_FIELDS),
        ),
        "turn_off": _spec(_LIGHT_TURN_OFF_FIELDS),
        "toggle": _spec(
            _LIGHT_TURN_ON_FIELDS,
            mutually_exclusive=(_LIGHT_BRIGHTNESS_FIELDS, _LIGHT_COLOR_FIELDS),
        ),
    },
    "switch": _simple_actions("turn_on", "turn_off", "toggle"),
    "input_boolean": _simple_actions("turn_on", "turn_off", "toggle"),
    "camera": _simple_actions(
        "turn_on", "turn_off", "enable_motion_detection", "disable_motion_detection"
    ),
    "remote": {
        "turn_on": _spec({"activity": _string}),
        "turn_off": _spec({"activity": _string}),
        "toggle": _spec({"activity": _string}),
    },
    "fan": {
        "turn_on": _spec(
            {
                "percentage": _integer(0, 100),
                "preset_mode": _string,
            }
        ),
        "turn_off": _spec(),
        "toggle": _spec(),
        "increase_speed": _spec({"percentage_step": _integer(0, 100)}),
        "decrease_speed": _spec({"percentage_step": _integer(0, 100)}),
        "oscillate": _spec(
            {"oscillating": _boolean},
            required=("oscillating",),
        ),
        "set_direction": _spec(
            {"direction": _enum("forward", "reverse")},
            required=("direction",),
        ),
        "set_percentage": _spec(
            {"percentage": _integer(0, 100)},
            required=("percentage",),
        ),
        "set_preset_mode": _spec(
            {"preset_mode": _string},
            required=("preset_mode",),
        ),
    },
    "cover": {
        **_simple_actions(
            "open_cover",
            "close_cover",
            "stop_cover",
            "toggle",
            "open_cover_tilt",
            "close_cover_tilt",
            "stop_cover_tilt",
            "toggle_cover_tilt",
        ),
        "set_cover_position": _spec(
            {"position": _integer(0, 100)}, required=("position",)
        ),
        "set_cover_tilt_position": _spec(
            {"tilt_position": _integer(0, 100)},
            required=("tilt_position",),
        ),
    },
    "climate": {
        **_simple_actions("turn_on", "turn_off", "toggle"),
        "set_hvac_mode": _spec(
            {
                "hvac_mode": _enum(
                    "off", "heat", "cool", "heat_cool", "auto", "dry", "fan_only"
                )
            },
            required=("hvac_mode",),
        ),
        "set_preset_mode": _spec({"preset_mode": _string}, required=("preset_mode",)),
        "set_temperature": _spec(
            {
                "temperature": _number(-100, 200),
                "hvac_mode": _enum(
                    "off", "heat", "cool", "heat_cool", "auto", "dry", "fan_only"
                ),
            },
            required=("temperature",),
        ),
        "set_humidity": _spec({"humidity": _integer(0, 100)}, required=("humidity",)),
        "set_fan_mode": _spec({"fan_mode": _string}, required=("fan_mode",)),
        "set_swing_mode": _spec({"swing_mode": _string}, required=("swing_mode",)),
        "set_swing_horizontal_mode": _spec(
            {"swing_horizontal_mode": _string},
            required=("swing_horizontal_mode",),
        ),
    },
    "media_player": {
        **_simple_actions(
            "turn_on",
            "turn_off",
            "toggle",
            "volume_up",
            "volume_down",
            "media_play_pause",
            "media_play",
            "media_pause",
            "media_stop",
            "media_next_track",
            "media_previous_track",
            "clear_playlist",
        ),
        "volume_set": _spec(
            {"volume_level": _number(0, 1)}, required=("volume_level",)
        ),
        "volume_mute": _spec(
            {"is_volume_muted": _boolean}, required=("is_volume_muted",)
        ),
        "media_seek": _spec(
            {"seek_position": _number(0, 86_400_000)},
            required=("seek_position",),
        ),
        "select_source": _spec({"source": _string}, required=("source",)),
        "select_sound_mode": _spec({"sound_mode": _string}, required=("sound_mode",)),
        "shuffle_set": _spec({"shuffle": _boolean}, required=("shuffle",)),
        "repeat_set": _spec(
            {"repeat": _enum("off", "all", "one")}, required=("repeat",)
        ),
    },
    "scene": {
        "turn_on": _spec({"transition": _number(0, 6_553)}),
    },
    "script": _simple_actions("turn_on", "turn_off", "toggle"),
    "automation": {
        **_simple_actions("trigger", "turn_on", "turn_off", "toggle"),
    },
    "button": {"press": _spec()},
    "input_button": {"press": _spec()},
    "vacuum": {
        **_simple_actions(
            "start",
            "pause",
            "stop",
            "return_to_base",
            "clean_spot",
            "locate",
        ),
        "set_fan_speed": _spec({"fan_speed": _string}, required=("fan_speed",)),
    },
    "humidifier": {
        **_simple_actions("turn_on", "turn_off", "toggle"),
        "set_mode": _spec({"mode": _string}, required=("mode",)),
        "set_humidity": _spec({"humidity": _integer(0, 100)}, required=("humidity",)),
    },
    "water_heater": {
        **_simple_actions("turn_on", "turn_off"),
        "set_away_mode": _spec({"away_mode": _boolean}, required=("away_mode",)),
        "set_temperature": _spec(
            {"temperature": _number(-100, 200), "operation_mode": _string},
            required=("temperature",),
        ),
        "set_operation_mode": _spec(
            {"operation_mode": _string}, required=("operation_mode",)
        ),
    },
    "number": {
        "set_value": _spec(
            {"value": _number(-1_000_000, 1_000_000)}, required=("value",)
        ),
    },
    "input_number": {
        "set_value": _spec(
            {"value": _number(-1_000_000, 1_000_000)}, required=("value",)
        ),
        "increment": _spec(),
        "decrement": _spec(),
    },
    "select": {
        "select_first": _spec(),
        "select_last": _spec(),
        "select_next": _spec({"cycle": _boolean}),
        "select_previous": _spec({"cycle": _boolean}),
        "select_option": _spec({"option": _string}, required=("option",)),
    },
    "input_select": {
        "select_first": _spec(),
        "select_last": _spec(),
        "select_next": _spec({"cycle": _boolean}),
        "select_previous": _spec({"cycle": _boolean}),
        "select_option": _spec({"option": _string}, required=("option",)),
    },
    "counter": {
        "increment": _spec(),
        "decrement": _spec(),
        "reset": _spec(),
        "set_value": _spec({"value": _integer(0, 1_000_000)}, required=("value",)),
    },
    "timer": {
        "start": _spec({"duration": _duration}),
        "pause": _spec(),
        "cancel": _spec(),
        "finish": _spec(),
        "change": _spec({"duration": _duration}, required=("duration",)),
    },
    "text": {
        "set_value": _spec({"value": _string}, required=("value",)),
    },
    "input_text": {
        "set_value": _spec({"value": _string}, required=("value",)),
    },
    "siren": {
        "turn_on": _spec(
            {
                "tone": _tone,
                "duration": _integer(1, 86_400),
                "volume_level": _number(0, 1),
            }
        ),
        "turn_off": _spec(),
        "toggle": _spec(),
    },
    "valve": {
        **_simple_actions("open_valve", "close_valve", "stop_valve", "toggle"),
        "set_valve_position": _spec(
            {"position": _integer(0, 100)}, required=("position",)
        ),
    },
    "lawn_mower": _simple_actions("start_mowing", "pause", "dock"),
    "lock": {"lock": _spec()},
}

ALLOWED_VOICE_ACTIONS = frozenset(
    action
    for domain_actions in _VOICE_SERVICE_SPECS.values()
    for action in domain_actions
)


@dataclass(frozen=True, slots=True)
class VoiceCommandRule:
    """One exact-match MAIKA voice command rule."""

    phrase: str
    normalized_phrase: str
    entity_id: str
    action: str
    service_data: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @property
    def service(self) -> str:
        """Return the fully qualified Home Assistant service name."""
        return f"{self.entity_id.partition('.')[0]}.{self.action}"


class VoiceCommandRulesError(ValueError):
    """Raised when a voice command rule is invalid."""

    def __init__(self, line_number: int, reason: str) -> None:
        super().__init__(f"line {line_number}: {reason}")


def fold_text(value: str) -> str:
    """Case-fold text and remove Vietnamese diacritics."""
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(
        character for character in normalized if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")


def fold_token(value: str) -> str:
    """Fold one token and trim surrounding punctuation/symbols."""
    folded = fold_text(value)
    start = 0
    end = len(folded)
    while start < end and unicodedata.category(folded[start])[0] in {"P", "S"}:
        start += 1
    while end > start and unicodedata.category(folded[end - 1])[0] in {"P", "S"}:
        end -= 1
    return folded[start:end]


def normalize_voice_phrase(value: str) -> str:
    """Normalize a phrase for accent-insensitive exact matching."""
    folded = fold_text(value)
    without_punctuation = "".join(
        " " if unicodedata.category(character)[0] in {"P", "S"} else character
        for character in folded
    )
    return " ".join(without_punctuation.split())


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"JSON constant {value} is not allowed")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key '{key}'")
        result[key] = value
    return result


def _validate_json_shape(value: Any) -> Any:
    """Reject nested objects and oversized values before service validation."""
    if isinstance(value, dict):
        raise ValueError("nested JSON objects are not supported")
    if isinstance(value, list):
        if len(value) > 8:
            raise ValueError("arrays may contain at most 8 values")
        return tuple(_validate_json_shape(item) for item in value)
    if isinstance(value, str):
        if len(value) > MAX_SERVICE_STRING_LENGTH:
            raise ValueError(
                f"strings must be at most {MAX_SERVICE_STRING_LENGTH} characters"
            )
        return value
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("numbers must be finite")
    if value is None:
        raise ValueError("null values are not supported")
    if isinstance(value, (bool, int, float)):
        return value
    raise ValueError("contains an unsupported JSON value")


def _parse_service_data(domain: str, action: str, raw_value: str) -> Mapping[str, Any]:
    if not raw_value:
        raw_value = "{}"
    if len(raw_value) > MAX_SERVICE_DATA_LENGTH:
        raise ValueError(
            f"service data must be at most {MAX_SERVICE_DATA_LENGTH} characters"
        )
    try:
        decoded = json.loads(
            raw_value,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as err:
        raise ValueError(f"service data JSON is invalid: {err}") from err
    if not isinstance(decoded, dict):
        raise ValueError("service data must be a JSON object")
    if len(decoded) > MAX_SERVICE_DATA_KEYS:
        raise ValueError(
            f"service data may contain at most {MAX_SERVICE_DATA_KEYS} fields"
        )

    normalized_data: dict[str, Any] = {}
    for key, value in decoded.items():
        if not isinstance(key, str):
            raise ValueError("service data keys must be strings")
        normalized_key = key.strip().casefold()
        if not normalized_key:
            raise ValueError("service data keys cannot be empty")
        if normalized_key in normalized_data:
            raise ValueError(f"duplicate service data key '{normalized_key}'")
        if normalized_key in _RESERVED_SERVICE_DATA_KEYS:
            raise ValueError(f"service data key '{normalized_key}' is not allowed")
        normalized_data[normalized_key] = _validate_json_shape(value)

    action_spec = _VOICE_SERVICE_SPECS.get(domain, {}).get(action)
    if action_spec is None:
        raise ValueError(f"action '{action}' is not allowed for domain '{domain}'")
    allowed_fields = set(action_spec.fields)
    unknown_fields = sorted(set(normalized_data) - allowed_fields)
    if unknown_fields:
        raise ValueError(
            f"field(s) not allowed for {domain}.{action}: {', '.join(unknown_fields)}"
        )

    missing = sorted(action_spec.required - set(normalized_data))
    if missing:
        raise ValueError(
            f"missing required field(s) for {domain}.{action}: {', '.join(missing)}"
        )
    for group in action_spec.mutually_exclusive:
        present = sorted(group.intersection(normalized_data))
        if len(present) > 1:
            raise ValueError(f"fields cannot be used together: {', '.join(present)}")

    validated: dict[str, Any] = {}
    for key, value in normalized_data.items():
        try:
            validated[key] = action_spec.fields[key](value)
        except (TypeError, ValueError) as err:
            raise ValueError(f"field '{key}' {err}") from err
    return MappingProxyType(validated)


def parse_voice_command_rules(value: str) -> tuple[VoiceCommandRule, ...]:
    """Parse safe rules using three or four columns.

    The fourth column is an optional JSON object containing only the allow-listed
    service data for the entity domain and action.
    """
    if not isinstance(value, str):
        raise VoiceCommandRulesError(1, "rules must be text")
    if len(value) > MAX_RULE_TEXT_LENGTH:
        raise VoiceCommandRulesError(
            1, f"rules text must be at most {MAX_RULE_TEXT_LENGTH} characters"
        )

    rules: list[VoiceCommandRule] = []
    seen_phrases: set[str] = set()

    for line_number, raw_line in enumerate(value.splitlines(), start=1):
        if len(raw_line) > MAX_RULE_LINE_LENGTH:
            raise VoiceCommandRulesError(
                line_number,
                f"line must be at most {MAX_RULE_LINE_LENGTH} characters",
            )
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if len(rules) >= MAX_VOICE_COMMAND_RULES:
            raise VoiceCommandRulesError(
                line_number, f"at most {MAX_VOICE_COMMAND_RULES} rules are allowed"
            )

        parts = [part.strip() for part in line.split("|", 3)]
        if len(parts) not in {3, 4}:
            raise VoiceCommandRulesError(
                line_number,
                "expected 'phrase | entity_id | action [| JSON service data]'",
            )

        phrase, entity_id, action = parts[:3]
        normalized_phrase = normalize_voice_phrase(phrase)
        if not normalized_phrase:
            raise VoiceCommandRulesError(line_number, "phrase cannot be empty")
        if len(normalized_phrase) > MAX_PHRASE_LENGTH:
            raise VoiceCommandRulesError(
                line_number, f"phrase must be at most {MAX_PHRASE_LENGTH} characters"
            )

        entity_id = entity_id.casefold()
        if not _ENTITY_ID_PATTERN.fullmatch(entity_id):
            raise VoiceCommandRulesError(line_number, "entity_id is invalid")
        domain = entity_id.partition(".")[0]

        action = action.casefold()
        if "." in action:
            action_domain, action = action.split(".", 1)
            if action_domain != domain:
                raise VoiceCommandRulesError(
                    line_number,
                    f"service domain '{action_domain}' does not match entity domain '{domain}'",
                )
        if action not in _VOICE_SERVICE_SPECS.get(domain, {}):
            allowed_actions = ", ".join(sorted(_VOICE_SERVICE_SPECS.get(domain, {})))
            if allowed_actions:
                reason = f"action for {domain} must be one of: {allowed_actions}"
            else:
                reason = f"domain '{domain}' is not supported by voice rules"
            raise VoiceCommandRulesError(line_number, reason)

        try:
            service_data = _parse_service_data(
                domain, action, parts[3] if len(parts) == 4 else "{}"
            )
        except ValueError as err:
            raise VoiceCommandRulesError(line_number, str(err)) from err

        if normalized_phrase in seen_phrases:
            raise VoiceCommandRulesError(
                line_number,
                "normalized phrase duplicates an earlier rule",
            )

        seen_phrases.add(normalized_phrase)
        rules.append(
            VoiceCommandRule(
                phrase=" ".join(phrase.split()),
                normalized_phrase=normalized_phrase,
                entity_id=entity_id,
                action=action,
                service_data=service_data,
            )
        )

    return tuple(rules)
