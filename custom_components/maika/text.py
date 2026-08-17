"""Text settings for MAIKA speakers."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.text import TextEntity, TextEntityDescription, TextMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MaikaConfigEntry
from .entity import MaikaEntity


@dataclass(frozen=True, kw_only=True)
class MaikaTextDescription(TextEntityDescription):
    """Describe a writable MAIKA text setting."""

    api_field: str


TEXT_DESCRIPTIONS = (
    MaikaTextDescription(
        key="speaker_name",
        translation_key="speaker_name",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:rename-box",
        mode=TextMode.TEXT,
        api_field="name",
    ),
    MaikaTextDescription(
        key="calling_name",
        translation_key="calling_name",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:account-voice",
        mode=TextMode.TEXT,
        api_field="calling_name",
    ),
    MaikaTextDescription(
        key="address",
        translation_key="address",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:map-marker",
        mode=TextMode.TEXT,
        api_field="address",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MaikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MAIKA text settings."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        MaikaText(coordinator, serial_number, description)
        for serial_number in coordinator.data["devices"]
        for description in TEXT_DESCRIPTIONS
    )


class MaikaText(MaikaEntity, TextEntity):
    """A writable MAIKA text setting."""

    entity_description: MaikaTextDescription
    _attr_native_min = 0
    _attr_native_max = 255

    def __init__(self, coordinator, serial_number, description) -> None:
        super().__init__(coordinator, serial_number, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | None:
        """Return the current text value."""
        value = self.device.get(self.entity_description.api_field)
        return str(value) if value is not None else None

    async def async_set_value(self, value: str) -> None:
        """Write a text setting through the MAIKA REST API."""
        await self.coordinator.client.async_update_device(
            int(self.device["id"]),
            self.serial_number,
            **{self.entity_description.api_field: value},
        )
        await self.coordinator.async_request_refresh()
