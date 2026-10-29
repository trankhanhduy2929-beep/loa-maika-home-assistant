"""Helpers for MAIKA reminder requests and responses."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .const import APP_EXECUTOR, APP_TIMEZONE

REMINDER_FREQUENCIES = ("once", "daily", "weekly", "monthly", "yearly")
REMINDER_STATUS_ENABLED = 1
REMINDER_STATUS_DISABLED = 2
MAX_REMINDER_EVENT = 200
MAX_REMINDER_SPEECH = 500
MAX_ALERT_PRIOR_MINUTES = 1440


class ReminderValidationError(ValueError):
    """Raised when panel reminder input cannot be sent to MAIKA."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _timezone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or APP_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(APP_TIMEZONE)


def parse_reminder_start(value: str) -> datetime:
    """Parse a browser datetime-local value in the MAIKA app timezone."""
    text = value.strip()
    if not text:
        raise ReminderValidationError("reminder_start_required")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as err:
        raise ReminderValidationError("invalid_reminder_start") from err
    timezone = _timezone(APP_TIMEZONE)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


def _event_title(event: str) -> str:
    title = event.strip()
    if not title:
        raise ReminderValidationError("reminder_event_required")
    if len(title) > MAX_REMINDER_EVENT:
        raise ReminderValidationError("reminder_event_too_long")
    return title


def _frequency(value: str) -> str:
    if value not in REMINDER_FREQUENCIES:
        raise ReminderValidationError("invalid_reminder_frequency")
    return value


def _alert_prior(value: Any) -> int:
    try:
        prior = int(value)
    except (TypeError, ValueError) as err:
        raise ReminderValidationError("invalid_reminder_alert_prior") from err
    if not 0 <= prior <= MAX_ALERT_PRIOR_MINUTES:
        raise ReminderValidationError("invalid_reminder_alert_prior")
    return prior


def _future_start(value: str) -> datetime:
    start = parse_reminder_start(value)
    if start <= datetime.now(start.tzinfo) - timedelta(seconds=60):
        raise ReminderValidationError("reminder_start_in_past")
    return start


def _speech(value: str | None, title: str) -> str:
    speech = (value or "").strip() or title
    if len(speech) > MAX_REMINDER_SPEECH:
        raise ReminderValidationError("reminder_speech_too_long")
    return speech


def build_reminder_payload(
    *,
    event: str,
    start_at: str,
    serial_number: str,
    frequency: str = "once",
    alert_prior: int = 0,
    custom_tts: str | None = None,
    executor: str = APP_EXECUTOR,
) -> dict[str, Any]:
    """Build the snake_case body expected by POST /v1/reminder."""
    title = _event_title(event)
    frequency = _frequency(frequency)
    if not serial_number.strip():
        raise ReminderValidationError("reminder_device_required")
    prior = _alert_prior(alert_prior)
    start = _future_start(start_at)
    speech = _speech(custom_tts, title)

    return {
        "alert_prior": prior * 60,
        "event": title,
        "executor": executor or APP_EXECUTOR,
        "frequency": frequency,
        "num_alert": 1,
        "period_time": 1,
        "reminder_type": 1,
        "start_date": start.strftime("%Y-%m-%d"),
        "start_time": start.strftime("%H:%M:%S"),
        "timezone": APP_TIMEZONE,
        "repeat_per_alert": 1,
        "devices": [serial_number.strip()],
        "alarm_type": 1,
        "custom_tts": speech,
    }


def build_reminder_update_payload(
    *,
    event: str | None = None,
    start_at: str | None = None,
    frequency: str | None = None,
    alert_prior: Any | None = None,
    custom_tts: str | None = None,
    status: Any | None = None,
    executor: str = APP_EXECUTOR,
) -> dict[str, Any]:
    """Build a partial snake_case body expected by PUT /v1/reminder/{id}."""
    payload: dict[str, Any] = {"executor": executor or APP_EXECUTOR}
    title = _event_title(event) if event is not None else None
    if title is not None:
        payload["event"] = title
    if frequency is not None:
        payload["frequency"] = _frequency(str(frequency))
    if alert_prior is not None:
        payload["alert_prior"] = _alert_prior(alert_prior) * 60
    if start_at is not None:
        start = _future_start(start_at)
        payload["start_date"] = start.strftime("%Y-%m-%d")
        payload["start_time"] = start.strftime("%H:%M:%S")
        payload["timezone"] = APP_TIMEZONE
    if custom_tts is not None:
        payload["custom_tts"] = _speech(custom_tts, title or "")
    if status is not None:
        try:
            reminder_status = int(status)
        except (TypeError, ValueError) as err:
            raise ReminderValidationError("invalid_reminder_status") from err
        if reminder_status not in (
            REMINDER_STATUS_ENABLED,
            REMINDER_STATUS_DISABLED,
        ):
            raise ReminderValidationError("invalid_reminder_status")
        payload["status"] = reminder_status
    if len(payload) == 1:
        raise ReminderValidationError("invalid_reminder_update")
    return payload


def _integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _reminder_start(item: dict[str, Any]) -> str | None:
    date_text = item.get("start_date")
    time_text = item.get("start_time")
    if not isinstance(date_text, str) or not date_text:
        return None
    if not isinstance(time_text, str) or not time_text:
        return None
    raw_timezone = item.get("timezone")
    timezone = _timezone(raw_timezone if isinstance(raw_timezone, str) else None)
    try:
        parsed = datetime.strptime(
            f"{date_text} {time_text}", "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone)
    except ValueError:
        return None
    return parsed.isoformat()


def flatten_reminders(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten grouped cloud reminders into panel-friendly records."""
    reminders: list[dict[str, Any]] = []
    for group in groups:
        items = group.get("listReminders")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            reminder_id = _integer(item.get("id"))
            if reminder_id is None:
                continue
            event = str(item.get("event") or item.get("reminder") or "Nhắc hẹn")
            alert_prior = _integer(item.get("alert_prior")) or 0
            reminders.append(
                {
                    "id": reminder_id,
                    "event": event,
                    "start_at": _reminder_start(item),
                    "start_date": item.get("start_date"),
                    "start_time": item.get("start_time"),
                    "frequency": item.get("frequency") or "once",
                    "completed": _integer(item.get("completed")) or 0,
                    "status": _integer(item.get("status")) or 0,
                    "reminder_type": _integer(item.get("reminder_type")) or 1,
                    "alarm_type": _integer(item.get("alarm_type")) or 1,
                    "alert_prior_minutes": max(0, alert_prior // 60),
                    "custom_tts": item.get("custom_tts") or "",
                    "devices": [
                        device
                        for device in item.get("devices") or []
                        if isinstance(device, str)
                    ],
                }
            )
    reminders.sort(
        key=lambda item: (item["start_at"] or "9999", item["id"]),
    )
    return reminders
