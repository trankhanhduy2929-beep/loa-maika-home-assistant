"""Select entities for writable MAIKA settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MaikaConfigEntry
from .const import WAKEWORD_RESPONSE_OPTIONS, WAKEWORD_SENSITIVITY_OPTIONS
from .entity import MaikaEntity


@dataclass(frozen=True, kw_only=True)
class MaikaSelectDescription(SelectEntityDescription):
    """Describe a writable MAIKA select."""

    api_field: str
    value_fn: Callable[[dict[str, Any]], str | None]


SELECT_DESCRIPTIONS = (
    MaikaSelectDescription(
        key="wakeword_sensitivity",
        translation_key="wakeword_sensitivity",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:ear-hearing",
        options=WAKEWORD_SENSITIVITY_OPTIONS,
        api_field="wakeword_sensitivity_level",
        value_fn=lambda device: device.get("wakeword_sensitivity_level"),
    ),
    MaikaSelectDescription(
        key="wakeword_response",
        translation_key="wakeword_response",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:bell-ring",
        options=WAKEWORD_RESPONSE_OPTIONS,
        api_field="wakeword_response_type",
        value_fn=lambda device: device.get("wakeword_response_type"),
    ),
    MaikaSelectDescription(
        key="tts_voice",
        translation_key="tts_voice",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:account-voice",
        options=None,
        api_field="tts_voice",
        value_fn=lambda device: (
            device.get("tts_voice", {}).get("code")
            if isinstance(device.get("tts_voice"), dict)
            else device.get("tts_voice")
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MaikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MAIKA selects."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        MaikaSelect(coordinator, serial_number, description)
        for serial_number in coordinator.data["devices"]
        for description in SELECT_DESCRIPTIONS
    )


class MaikaSelect(MaikaEntity, SelectEntity):
    """A writable MAIKA select setting."""

    entity_description: MaikaSelectDescription

    def __init__(self, coordinator, serial_number, description) -> None:
        super().__init__(coordinator, serial_number, description.key)
        self.entity_description = description

    @property
    def options(self) -> list[str]:
        """Return supported options."""
        if self.entity_description.key == "tts_voice":
            options = list(self.coordinator.data.get("voices", {}))
        else:
            options = list(self.entity_description.options or [])
        current = self.current_option
        if current and current not in options:
            options.append(current)
        return options

    @property
    def current_option(self) -> str | None:
        """Return the current setting."""
        return self.entity_description.value_fn(self.device)

    async def async_select_option(self, option: str) -> None:
        """Write a speaker setting through the MAIKA REST API."""
        if option not in self.options:
            raise ValueError(f"Unsupported MAIKA option: {option}")
        await self.coordinator.client.async_update_device(
            int(self.device["id"]),
            self.serial_number,
            **{self.entity_description.api_field: option},
        )
        await self.coordinator.async_request_refresh()
