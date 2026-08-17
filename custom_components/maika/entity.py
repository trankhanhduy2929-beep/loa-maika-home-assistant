"""Shared MAIKA entity classes."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MaikaDataUpdateCoordinator


class MaikaEntity(CoordinatorEntity[MaikaDataUpdateCoordinator]):
    """Base entity attached to one MAIKA speaker."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MaikaDataUpdateCoordinator,
        serial_number: str,
        entity_key: str,
    ) -> None:
        super().__init__(coordinator)
        self.serial_number = serial_number
        self._attr_unique_id = f"{serial_number}_{entity_key}"

    @property
    def device(self) -> dict[str, Any]:
        """Return the latest speaker data."""
        return self.coordinator.data["devices"].get(self.serial_number, {})

    @property
    def available(self) -> bool:
        """Return whether cloud data for this speaker is available."""
        return (
            self.coordinator.last_update_success
            and self.serial_number in self.coordinator.data.get("devices", {})
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device registry information."""
        device = self.device
        display_name = (
            device.get("calling_name")
            or device.get("name")
            or f"MAIKA {self.serial_number[-4:]}"
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self.serial_number)},
            manufacturer=str(device.get("manufacturer") or "OLLI"),
            model=device.get("model"),
            name=str(display_name),
            serial_number=self.serial_number,
            sw_version=device.get("firmware_version"),
        )


class MaikaCommandEntity(MaikaEntity):
    """Base class for entities that send commands to an online speaker."""

    @property
    def available(self) -> bool:
        """Commands are available only while the speaker reports online."""
        return super().available and bool(self.device.get("online"))
