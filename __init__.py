"""Home Assistant integration for MAIKA smart speakers."""

from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MaikaApiClient
from .const import (
    CONF_CLIENT_ID,
    CONF_PASSWORD,
    CONF_PHONE_NUMBER,
    CONF_SESSION_ID,
    DOMAIN,
)
from .coordinator import MaikaDataUpdateCoordinator
from .license_config import LICENSE_PORTAL_URL
from .license_manager import MaikaLicenseManager, MaikaLicenseUnavailableError
from .phone import normalize_login_identifier
from .runtime import MaikaRuntimeData

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]

type MaikaConfigEntry = ConfigEntry[MaikaRuntimeData]

_LICENSE_NOTIFICATION_ID = "maika_license_activation"


async def async_setup_entry(hass: HomeAssistant, entry: MaikaConfigEntry) -> bool:
    """Set up MAIKA from a config entry."""
    try:
        license_manager = await MaikaLicenseManager.async_create(hass)
    except MaikaLicenseUnavailableError as err:
        _show_license_notification(hass, err)
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="license_unavailable",
            translation_placeholders={
                "activation_code": err.activation_code,
                "license_error": err.code,
                "portal_url": LICENSE_PORTAL_URL or "—",
            },
        ) from err

    persistent_notification.async_dismiss(hass, _LICENSE_NOTIFICATION_ID)
    client = MaikaApiClient(
        async_get_clientsession(hass),
        str(entry.data[CONF_PHONE_NUMBER]),
        str(entry.data[CONF_PASSWORD]),
        str(entry.data[CONF_CLIENT_ID]),
        str(entry.data[CONF_SESSION_ID]),
    )
    coordinator = MaikaDataUpdateCoordinator(hass, entry, client)
    client.set_event_callback(coordinator.async_handle_stream_frame)
    listener_task = entry.async_create_background_task(
        hass,
        client.async_listen_forever(),
        "MAIKA cloud event stream",
    )
    client.set_listener_task(listener_task)

    try:
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = MaikaRuntimeData(client, coordinator, license_manager)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await client.async_stop()
        raise

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    license_manager.async_start(
        entry,
        lambda err: _async_handle_invalid_license(hass, entry, err),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MaikaConfigEntry) -> bool:
    """Unload a MAIKA config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.license_manager.async_stop()
        await entry.runtime_data.coordinator.async_stop_voice_subscriptions()
        await entry.runtime_data.client.async_stop()
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: MaikaConfigEntry) -> bool:
    """Migrate config entries created before activation support."""
    if entry.version < 3:
        data = dict(entry.data)
        phone_number = data.get(CONF_PHONE_NUMBER)
        if phone_number is not None:
            data[CONF_PHONE_NUMBER] = normalize_login_identifier(str(phone_number))
        hass.config_entries.async_update_entry(entry, data=data, version=3)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: MaikaConfigEntry) -> None:
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_handle_invalid_license(
    hass: HomeAssistant,
    entry: MaikaConfigEntry,
    err: MaikaLicenseUnavailableError,
) -> None:
    """Unload a running entry after its signed lease becomes unusable."""
    _show_license_notification(hass, err)
    await hass.config_entries.async_reload(entry.entry_id)


def _show_license_notification(
    hass: HomeAssistant, err: MaikaLicenseUnavailableError
) -> None:
    """Show safe activation instructions without exposing license secrets."""
    portal_message = (
        f" Chọn gói hoặc xem key tại {LICENSE_PORTAL_URL}."
        if LICENSE_PORTAL_URL
        else ""
    )
    persistent_notification.async_create(
        hass,
        (
            "MAIKA chưa kích hoạt. Mở Cài đặt > Thiết bị & dịch vụ > MAIKA > "
            f"Cấu hình. Mã máy: {err.activation_code}. Trạng thái: {err.code}."
            f"{portal_message}"
        ),
        title="Kích hoạt MAIKA",
        notification_id=_LICENSE_NOTIFICATION_ID,
    )
