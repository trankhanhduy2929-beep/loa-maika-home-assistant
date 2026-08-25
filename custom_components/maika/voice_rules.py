"""Safe exact-match rules for MAIKA voice commands."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

ALLOWED_VOICE_ACTIONS = frozenset({"toggle", "turn_off", "turn_on"})
_ENTITY_ID_PATTERN = re.compile(r"[a-z_][a-z0-9_]*\.[a-z0-9_]+")


@dataclass(frozen=True, slots=True)
class VoiceCommandRule:
    """One exact-match MAIKA voice command rule."""

    phrase: str
    normalized_phrase: str
    entity_id: str
    action: str


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


def parse_voice_command_rules(value: str) -> tuple[VoiceCommandRule, ...]:
    """Parse safe rules using `phrase | entity_id | action` lines."""
    rules: list[VoiceCommandRule] = []
    seen_phrases: set[str] = set()

    for line_number, raw_line in enumerate(value.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 3:
            raise VoiceCommandRulesError(
                line_number,
                "expected 'phrase | entity_id | turn_on/turn_off/toggle'",
            )

        phrase, entity_id, action = parts
        normalized_phrase = normalize_voice_phrase(phrase)
        if not normalized_phrase:
            raise VoiceCommandRulesError(line_number, "phrase cannot be empty")

        entity_id = entity_id.casefold()
        if not _ENTITY_ID_PATTERN.fullmatch(entity_id):
            raise VoiceCommandRulesError(line_number, "entity_id is invalid")

        action = action.casefold()
        if action not in ALLOWED_VOICE_ACTIONS:
            raise VoiceCommandRulesError(
                line_number,
                "action must be turn_on, turn_off or toggle",
            )

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
            )
        )

    return tuple(rules)
