"""Login-identifier helpers for MAIKA authentication."""

from __future__ import annotations

_PHONE_NUMBER_SEPARATORS = str.maketrans("", "", " \t\r\n-.()")


def is_email_login_identifier(login_identifier: str) -> bool:
    """Return whether a MAIKA login identifier is an email address."""
    return "@" in login_identifier


def normalize_login_identifier(login_identifier: str) -> str:
    """Normalize a phone number while preserving an email address."""
    normalized = login_identifier.strip()
    if is_email_login_identifier(normalized):
        return normalized
    return normalize_phone_number(normalized)


def normalize_phone_number(phone_number: str) -> str:
    """Return a MAIKA-compatible Vietnamese phone number."""
    normalized = phone_number.strip().translate(_PHONE_NUMBER_SEPARATORS)
    if normalized.startswith("00"):
        normalized = f"+{normalized[2:]}"
    if normalized.startswith("+840"):
        return f"+84{normalized[4:]}"
    if normalized.startswith("+84"):
        return normalized
    if normalized.startswith("840"):
        return f"+84{normalized[3:]}"
    if normalized.startswith("84"):
        return f"+{normalized}"
    if normalized.startswith("0"):
        return f"+84{normalized[1:]}"
    return normalized
