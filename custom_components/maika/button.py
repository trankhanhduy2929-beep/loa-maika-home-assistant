"""Button entities for MAIKA speakers."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MaikaConfigEntry
from .entity import MaikaCommandEntity, MaikaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MaikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MAIKA buttons."""
    coordinator = entry.runtime_data.coordinator
    entities: list[ButtonEntity] = []
    for serial_number in coordinator.data["devices"]:
        entities.extend(
            (
                MaikaRestartButton(coordinator, serial_number),
                MaikaRefreshButton(coordinator, serial_number),
            )
        )
    async_add_entities(entities)


class MaikaRestartButton(MaikaCommandEntity, ButtonEntity):
    """Safely restart a MAIKA speaker."""

    _attr_translation_key = "restart"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(self, coordinator, serial_number) -> None:
        super().__init__(coordinator, serial_number, "restart")

    async def async_press(self) -> None:
        """Restart the speaker."""
        await self.coordinator.client.async_restart_device(self.serial_number)


class MaikaRefreshButton(MaikaEntity, ButtonEntity):
    """Request current playback, volume and microphone state."""

    _attr_translation_key = "refresh_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator, serial_number) -> None:
        super().__init__(coordinator, serial_number, "refresh_status")

    async def async_press(self) -> None:
        """Refresh REST and live speaker data."""
        await self.coordinator.async_refresh_live(self.serial_number)
        await self.coordinator.async_request_refresh()
