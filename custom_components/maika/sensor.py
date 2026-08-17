"""Sensor entities for MAIKA speakers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import MaikaConfigEntry
from .const import CONF_ENABLE_VOICE_COMMAND_SENSOR
from .coordinator import MaikaDataUpdateCoordinator
from .entity import MaikaEntity


def _wifi_ssid(device: dict[str, Any]) -> str | None:
    wifi_list = device.get("wifi")
    if not isinstance(wifi_list, list):
        return None
    connected = next(
        (
            wifi
            for wifi in wifi_list
            if isinstance(wifi, dict) and wifi.get("connected")
        ),
        None,
    )
    selected = connected or next(
        (wifi for wifi in wifi_list if isinstance(wifi, dict)), None
    )
    return selected.get("ssid") if selected else None


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.UTC)
    return parsed


def _playback_status(device: dict[str, Any]) -> str | None:
    current = device.get("current_playback")
    if not isinstance(current, dict):
        return None
    status = current.get("status")
    return str(status) if status else None


@dataclass(frozen=True, kw_only=True)
class MaikaSensorDescription(SensorEntityDescription):
    """Describe a MAIKA sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS = (
    MaikaSensorDescription(
        key="volume",
        translation_key="volume",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:volume-high",
        value_fn=lambda device: device.get("volume"),
    ),
    MaikaSensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
        value_fn=lambda device: device.get("firmware_version"),
    ),
    MaikaSensorDescription(
        key="firmware_update_status",
        translation_key="firmware_update_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:update",
        value_fn=lambda device: device.get("firmware_update_status"),
    ),
    MaikaSensorDescription(
        key="model",
        translation_key="model",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:speaker",
        value_fn=lambda device: device.get("model"),
    ),
    MaikaSensorDescription(
        key="serial_number",
        translation_key="serial_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
        value_fn=lambda device: device.get("device_id"),
    ),
    MaikaSensorDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi",
        value_fn=_wifi_ssid,
    ),
    MaikaSensorDescription(
        key="activated_at",
        translation_key="activated_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-check",
        value_fn=lambda device: _parse_timestamp(device.get("activated_at")),
    ),
    MaikaSensorDescription(
        key="warranty_expire_date",
        translation_key="warranty_expire_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shield-clock",
        value_fn=lambda device: _parse_timestamp(device.get("warranty_expire_date")),
    ),
    MaikaSensorDescription(
        key="room",
        translation_key="room",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:floor-plan",
        value_fn=lambda device: device.get("room") or None,
    ),
    MaikaSensorDescription(
        key="default_language",
        translation_key="default_language",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:translate",
        value_fn=lambda device: device.get("default_language"),
    ),
    MaikaSensorDescription(
        key="playback_status",
        translation_key="playback_status",
        icon="mdi:play-circle-outline",
        value_fn=_playback_status,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MaikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MAIKA sensors."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = [
        MaikaSensor(coordinator, serial_number, description)
        for serial_number in coordinator.data["devices"]
        for description in SENSOR_DESCRIPTIONS
    ]
    if entry.options.get(CONF_ENABLE_VOICE_COMMAND_SENSOR, False):
        entities.append(MaikaLastVoiceCommandSensor(coordinator, entry.entry_id))
    async_add_entities(entities)


class MaikaSensor(MaikaEntity, SensorEntity):
    """A read-only MAIKA speaker value."""

    entity_description: MaikaSensorDescription

    def __init__(self, coordinator, serial_number, description) -> None:
        super().__init__(coordinator, serial_number, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.device)


class MaikaLastVoiceCommandSensor(
    CoordinatorEntity[MaikaDataUpdateCoordinator], SensorEntity
):
    """Expose the latest phrase recognized by the MAIKA cloud stream."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:message-processing-outline"
    _attr_translation_key = "last_voice_command"

    def __init__(self, coordinator: MaikaDataUpdateCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_last_voice_command"

    @property
    def native_value(self) -> str | None:
        """Return the latest recognized phrase, limited to a valid HA state."""
        command = self.coordinator.data.get("last_voice_command")
        if not isinstance(command, dict):
            return None
        text = command.get("text")
        return str(text)[:255] if text else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return matching and execution details without stream identifiers."""
        command = self.coordinator.data.get("last_voice_command")
        base_attributes = {
            "stream_connected": bool(
                self.coordinator.data.get("stream_connected", False)
            ),
            "stream_generation": int(self.coordinator.data.get("stream_generation", 0)),
            "stream_frame_count": int(
                self.coordinator.data.get("stream_frame_count", 0)
            ),
            "stream_directive_count": int(
                self.coordinator.data.get("stream_directive_count", 0)
            ),
            "configured_rule_count": int(
                self.coordinator.data.get("voice_command_rule_count", 0)
            ),
            "voice_subscription_status": self.coordinator.data.get(
                "voice_subscription_status"
            ),
            "voice_subscription_target_count": int(
                self.coordinator.data.get("voice_subscription_target_count", 0)
            ),
            "voice_subscription_count": int(
                self.coordinator.data.get("voice_subscription_count", 0)
            ),
        }
        for key in (
            "last_stream_frame_kind",
            "last_stream_frame_type",
            "last_stream_frame_name",
            "last_stream_frame_namespace",
            "last_stream_frame_at",
            "last_stream_frame_has_raw_speech",
            "voice_subscription_last_at",
            "voice_subscription_last_error",
        ):
            value = self.coordinator.data.get(key)
            if value is not None:
                base_attributes[key] = value
        if not isinstance(command, dict):
            return base_attributes

        matched = command.get("matched_phrase") is not None
        if command.get("error"):
            result = "failed"
        elif command.get("executed"):
            result = "executed"
        elif matched:
            result = "pending"
        else:
            result = "not_matched"

        attributes = {
            **base_attributes,
            "received_at": command.get("received_at"),
            "normalized": command.get("normalized"),
            "matched": matched,
            "matched_phrase": command.get("matched_phrase"),
            "target_entity_id": command.get("target_entity_id"),
            "action": command.get("action"),
            "service": command.get("service"),
            "entity_state_before": command.get("entity_state_before"),
            "entity_state_after": command.get("entity_state_after"),
            "executed": bool(command.get("executed")),
            "result": result,
            "error": command.get("error"),
            "success_audio_status": command.get("success_audio_status"),
            "success_audio_error": command.get("success_audio_error"),
        }
        return {key: value for key, value in attributes.items() if value is not None}
