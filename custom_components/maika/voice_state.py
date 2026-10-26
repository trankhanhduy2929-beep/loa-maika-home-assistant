"""Turn Home Assistant entity states into short Vietnamese speech."""

from __future__ import annotations

import math
import unicodedata
from typing import Any

STATE_UNAVAILABLE = "unavailable"
STATE_UNKNOWN = "unknown"
MAX_VOICE_RESPONSE_LENGTH = 400

_UNIT_SPEECH = {
    "%": "phần trăm",
    "°c": "độ C",
    "°f": "độ F",
    "c": "độ C",
    "f": "độ F",
    "k": "kelvin",
    "w": "oát",
    "kw": "kilowatt",
    "wh": "watt giờ",
    "kwh": "kilowatt giờ",
    "v": "vôn",
    "a": "ampe",
    "ma": "miliampe",
    "lx": "lux",
    "ppm": "phần triệu",
    "µg/m³": "microgram trên mét khối",
    "mg/m³": "miligam trên mét khối",
    "hpa": "héc-tô-pa",
    "pa": "paxcan",
    "m/s": "mét trên giây",
    "km/h": "kilômét trên giờ",
    "mm": "milimét",
    "cm": "xentimét",
    "m": "mét",
    "l": "lít",
    "ml": "mililít",
    "s": "giây",
    "min": "phút",
    "h": "giờ",
    "d": "ngày",
}

_BINARY_TEXT = {
    "battery": ("pin yếu", "pin bình thường"),
    "carbon_monoxide": ("phát hiện khí CO", "không phát hiện khí CO"),
    "cold": ("đang lạnh", "bình thường"),
    "connectivity": ("đang kết nối", "mất kết nối"),
    "door": ("đang mở", "đang đóng"),
    "garage_door": ("đang mở", "đang đóng"),
    "gas": ("phát hiện khí gas", "không phát hiện khí gas"),
    "heat": ("đang nóng", "bình thường"),
    "light": ("có ánh sáng", "không có ánh sáng"),
    "lock": ("đã khóa", "chưa khóa"),
    "moisture": ("phát hiện nước", "không phát hiện nước"),
    "motion": ("phát hiện chuyển động", "không phát hiện chuyển động"),
    "occupancy": ("có người", "không có người"),
    "opening": ("đang mở", "đang đóng"),
    "plug": ("đang cắm điện", "đã rút điện"),
    "power": ("có điện", "mất điện"),
    "presence": ("có người", "không có người"),
    "problem": ("có sự cố", "không có sự cố"),
    "safety": ("không an toàn", "an toàn"),
    "smoke": ("phát hiện khói", "không phát hiện khói"),
    "sound": ("phát hiện âm thanh", "không phát hiện âm thanh"),
    "tamper": ("bị can thiệp", "bình thường"),
    "vibration": ("phát hiện rung", "không phát hiện rung"),
    "window": ("đang mở", "đang đóng"),
}

_COVER_TEXT = {
    "open": "đang mở",
    "opening": "đang mở",
    "closed": "đang đóng",
    "closing": "đang đóng",
    "stopped": "đang dừng",
}

_HVAC_TEXT = {
    "off": "đang tắt",
    "heat": "đang sưởi",
    "cool": "đang làm lạnh",
    "heat_cool": "đang chạy tự động",
    "auto": "đang chạy tự động",
    "dry": "đang hút ẩm",
    "fan_only": "đang chạy quạt",
    "idle": "đang chờ",
}

_LOCK_TEXT = {
    "locked": "đã khóa",
    "locking": "đang khóa",
    "unlocked": "chưa khóa",
    "unlocking": "đang mở khóa",
    "jammed": "bị kẹt",
    "open": "đang mở",
    "opening": "đang mở",
}

_MEDIA_TEXT = {
    "playing": "đang phát",
    "paused": "đang tạm dừng",
    "idle": "đang chờ",
    "off": "đang tắt",
    "on": "đang bật",
    "standby": "đang chờ",
}

_NUMBER_DOMAINS = frozenset({"number", "input_number", "counter"})
_SELECT_DOMAINS = frozenset({"select", "input_select"})


def _speakable(value: Any, limit: int = MAX_VOICE_RESPONSE_LENGTH) -> str:
    text = "".join(
        " " if character.isspace() else character
        for character in str(value)
        if not character.isspace() or character == " "
    )
    text = "".join(character for character in text if not _is_control(character))
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    shortened = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.-")
    return shortened or text[:limit]


def _is_control(character: str) -> bool:
    return unicodedata.category(character) == "Cc"


def _number_text(value: Any) -> str | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _value_text(value: Any, unit: Any = None) -> str:
    number = _number_text(value)
    if number is None:
        text = _speakable(value, 200)
    else:
        text = number
    unit_text = _unit_text(unit)
    return f"{text} {unit_text}" if unit_text else text


def _unit_text(unit: Any) -> str:
    if not isinstance(unit, str) or not unit.strip():
        return ""
    cleaned = unit.strip()
    return _UNIT_SPEECH.get(cleaned.casefold(), cleaned)


def _name(state: Any) -> str:
    attributes = getattr(state, "attributes", {}) or {}
    name = attributes.get("friendly_name") or getattr(state, "entity_id", "")
    return _speakable(name, 120)


def _on_off(state: Any, attributes: dict[str, Any]) -> str:
    is_on = state.state == "on"
    device_class = str(attributes.get("device_class") or "").casefold()
    if device_class in _BINARY_TEXT:
        on_text, off_text = _BINARY_TEXT[device_class]
        return on_text if is_on else off_text
    return "đang bật" if is_on else "đang tắt"


def _brightness(attributes: dict[str, Any]) -> str | None:
    percentage = _number_text(attributes.get("brightness_pct"))
    if percentage is not None:
        return f"độ sáng {percentage} phần trăm"
    brightness = _number_text(attributes.get("brightness"))
    if brightness is None:
        return None
    try:
        percentage = round(float(brightness) / 255 * 100)
    except (TypeError, ValueError):
        return None
    return f"độ sáng {percentage} phần trăm"


def _climate(state: Any, attributes: dict[str, Any]) -> str:
    name = _name(state)
    parts = [f"{name} {_HVAC_TEXT.get(state.state, state.state)}."]
    current = _number_text(attributes.get("current_temperature"))
    if current is not None:
        unit = _unit_text(attributes.get("temperature_unit")) or "độ C"
        parts.append(f"Nhiệt độ hiện tại {current} {unit}.")
    humidity = _number_text(attributes.get("current_humidity"))
    if humidity is not None:
        parts.append(f"Độ ẩm {humidity} phần trăm.")
    target = _number_text(attributes.get("temperature"))
    if target is not None:
        unit = _unit_text(attributes.get("temperature_unit")) or "độ C"
        parts.append(f"Nhiệt độ đặt {target} {unit}.")
    return _speakable(" ".join(parts))


def format_voice_state(state: Any) -> str:
    """Describe one HA state as a short Vietnamese spoken response."""
    name = _name(state)
    value = str(getattr(state, "state", "") or "")
    attributes = getattr(state, "attributes", {}) or {}
    domain = str(getattr(state, "entity_id", "")).partition(".")[0]
    lowered = value.casefold()

    if lowered == STATE_UNAVAILABLE:
        return f"{name} hiện không khả dụng."
    if lowered in {STATE_UNKNOWN, ""}:
        return f"{name} hiện chưa có dữ liệu."

    if domain == "climate":
        return _climate(state, attributes)

    if domain == "binary_sensor" or (
        domain == "sensor" and value in {"on", "off"} and attributes.get("device_class")
    ):
        return f"{name} {_on_off(state, attributes)}."

    if domain in {"sensor", "number", "input_number"}:
        unit = attributes.get("unit_of_measurement")
        return f"{name} là {_value_text(value, unit)}."

    if domain in _NUMBER_DOMAINS:
        return f"{name} là {_value_text(value)}."

    if domain in {"switch", "input_boolean", "light", "fan", "siren"}:
        parts = [f"{name} {_on_off(state, attributes)}."]
        if domain == "light" and value == "on":
            brightness = _brightness(attributes)
            if brightness:
                parts.append(f"{brightness}.")
        if domain == "fan" and value == "on":
            percentage = _number_text(attributes.get("percentage"))
            if percentage is not None:
                parts.append(f"Tốc độ {percentage} phần trăm.")
        return _speakable(" ".join(parts))

    if domain == "cover":
        parts = [f"{name} {_COVER_TEXT.get(value, value)}."]
        position = _number_text(attributes.get("current_position"))
        if position is not None:
            parts.append(f"Độ mở {position} phần trăm.")
        return _speakable(" ".join(parts))

    if domain == "lock":
        return f"{name} {_LOCK_TEXT.get(value, value)}."

    if domain == "media_player":
        parts = [f"{name} {_MEDIA_TEXT.get(value, value)}."]
        title = attributes.get("media_title")
        artist = attributes.get("media_artist")
        if title:
            parts.append(f"Đang phát {_speakable(title, 160)}.")
        if artist:
            parts.append(f"Ca sĩ {_speakable(artist, 120)}.")
        return _speakable(" ".join(parts))

    if domain in _SELECT_DOMAINS:
        return f"{name} đang chọn {_value_text(value)}."

    if domain in {"automation", "script"}:
        return f"{name} {_on_off(state, attributes)}."

    return f"{name} đang ở trạng thái {_value_text(value)}."
