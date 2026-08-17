"""Binary sensor entities for MAIKA speakers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import MaikaConfigEntry
from .entity import MaikaEntity


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return None


def _wifi_connected(device: dict[str, Any]) -> bool | None:
    wifi_list = device.get("wifi")
    if not isinstance(wifi_list, list):
        return None
    values = [
        _as_bool(wifi.get("connected")) for wifi in wifi_list if isinstance(wifi, dict)
    ]
    if any(value is True for value in values):
        return True
    if any(value is False for value in values):
        return False
    return None


def _device_active(device: dict[str, Any]) -> bool | None:
    try:
        return int(device["status"]) == 1
    except (KeyError, TypeError, ValueError):
        return None


def _warranty_active(device: dict[str, Any]) -> bool | None:
    value = device.get("warranty_expire_date")
    if not isinstance(value, str) or not value:
        return None
    expires = dt_util.parse_datetime(value)
    if expires is None:
        return None
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=dt_util.UTC)
    now = datetime.now(dt_util.UTC)
    return expires > now


@dataclass(frozen=True, kw_only=True)
class MaikaBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a MAIKA binary sensor."""

    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSOR_DESCRIPTIONS = (
    MaikaBinarySensorDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: _as_bool(device.get("online")),
    ),
    MaikaBinarySensorDescription(
        key="wifi_connected",
        translation_key="wifi_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=_wifi_connected,
    ),
    MaikaBinarySensorDescription(
        key="available_to_call",
        translation_key="available_to_call",
        icon="mdi:phone",
        value_fn=lambda device: _as_bool(device.get("available_to_call")),
    ),
    MaikaBinarySensorDescription(
        key="favorite",
        translation_key="favorite",
        icon="mdi:star",
        value_fn=lambda device: _as_bool(device.get("is_favorite")),
    ),
    MaikaBinarySensorDescription(
        key="device_active",
        translation_key="device_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:check-decagram",
        value_fn=_device_active,
    ),
    MaikaBinarySensorDescription(
        key="warranty_active",
        translation_key="warranty_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shield-check",
        value_fn=_warranty_active,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MaikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MAIKA binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        MaikaBinarySensor(coordinator, serial_number, description)
        for serial_number in coordinator.data["devices"]
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class MaikaBinarySensor(MaikaEntity, BinarySensorEntity):
    """A MAIKA speaker binary state."""

    entity_description: MaikaBinarySensorDescription

    def __init__(self, coordinator, serial_number, description) -> None:
        super().__init__(coordinator, serial_number, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the binary state."""
        return self.entity_description.value_fn(self.device)
