"""Switch entities for MAIKA speakers."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MaikaConfigEntry
from .entity import MaikaCommandEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MaikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MAIKA switches."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        MaikaMicrophoneMuteSwitch(coordinator, serial_number)
        for serial_number in coordinator.data["devices"]
    )


class MaikaMicrophoneMuteSwitch(MaikaCommandEntity, SwitchEntity):
    """Mute or unmute a MAIKA speaker's physical microphone."""

    _attr_translation_key = "microphone_mute"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:microphone-off"

    def __init__(self, coordinator, serial_number) -> None:
        super().__init__(coordinator, serial_number, "microphone_mute")
        self._optimistic_state = False

    @property
    def is_on(self) -> bool:
        """Return true when the microphone is muted."""
        value = self.device.get("mute")
        return bool(value) if value is not None else self._optimistic_state

    @property
    def assumed_state(self) -> bool:
        """Flag state as assumed until live DeviceInfo has been received."""
        return self.device.get("mute") is None

    async def async_turn_on(self, **kwargs) -> None:
        """Mute the microphone."""
        await self._async_set_muted(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Unmute the microphone."""
        await self._async_set_muted(False)

    async def _async_set_muted(self, muted: bool) -> None:
        await self.coordinator.client.async_set_microphone_mute(
            self.serial_number, muted
        )
        self._optimistic_state = muted
        self.coordinator.async_update_device_data(self.serial_number, {"mute": muted})
        await self.coordinator.async_refresh_live(self.serial_number)
