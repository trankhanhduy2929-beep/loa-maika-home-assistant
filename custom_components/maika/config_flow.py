"""Config flow for MAIKA."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    MaikaApiClient,
    MaikaApiError,
    MaikaAuthenticationError,
)
from .const import (
    CONF_CLIENT_ID,
    CONF_LICENSE_KEY,
    CONF_LICENSE_SERVER_URL,
    CONF_PASSWORD,
    CONF_PHONE_NUMBER,
    CONF_SESSION_ID,
    DOMAIN,
)
from .license import (
    LICENSE_STATUS_ACTIVE,
    LICENSE_STATUS_GRACE,
    LICENSE_STATUS_PENDING,
    MaikaInstallationIdentity,
    MaikaLicenseClient,
    MaikaLicenseConnectionError,
    MaikaLicenseResponse,
    MaikaLicenseResponseError,
    MaikaLicenseTokenError,
    async_get_installation_identity,
    normalize_license_server_url,
)
from .license_config import (
    DEFAULT_LICENSE_SERVER_URL,
    LICENSE_PORTAL_URL,
)
from .license_store import MaikaLicenseStore, MaikaStoredLicense
from .phone import normalize_login_identifier

_LOGGER = logging.getLogger(__name__)

_LICENSE_ERROR_MAP = {
    "activation_limit": "license_activation_limit",
    "installation_deactivated": "license_deactivated",
    "installation_rejected": "license_rejected",
    "installation_revoked": "license_revoked",
    "invalid_license": "invalid_license",
    "license_expired": "license_expired",
    "license_inactive": "license_inactive",
    "license_request_rejected": "license_rejected",
}


async def _async_validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, str]:
    client = MaikaApiClient(
        async_get_clientsession(hass),
        str(data[CONF_PHONE_NUMBER]),
        str(data[CONF_PASSWORD]),
        str(data.get(CONF_CLIENT_ID) or uuid4()),
        str(data.get(CONF_SESSION_ID) or uuid4()),
    )
    account = await client.async_login()
    title = str(account.get("full_name") or account.get("calling_name") or "MAIKA")
    return {"title": title, "unique_id": str(account["id"])}


async def _async_store_license_response(
    hass: HomeAssistant,
    *,
    server_url: str,
    identity: MaikaInstallationIdentity,
    previous: MaikaStoredLicense | None,
    response: MaikaLicenseResponse,
) -> MaikaStoredLicense:
    record = MaikaStoredLicense.from_response(
        server_url=server_url,
        installation_hash=identity.installation_hash,
        previous=previous,
        response=response,
    )
    await MaikaLicenseStore(hass).async_save(record)
    return record


def _license_error_key(code: str) -> str:
    return _LICENSE_ERROR_MAP.get(code, "license_rejected")


def _server_url_schema(default: str) -> dict[vol.Marker, Any]:
    if DEFAULT_LICENSE_SERVER_URL:
        return {}
    return {
        vol.Required(CONF_LICENSE_SERVER_URL, default=default): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
        )
    }


def _resolve_server_url(
    user_input: dict[str, Any], record: MaikaStoredLicense | None
) -> str:
    candidate = str(
        user_input.get(CONF_LICENSE_SERVER_URL)
        or (record.server_url if record else "")
        or DEFAULT_LICENSE_SERVER_URL
    )
    return normalize_license_server_url(candidate)


async def _async_cached_license_state(
    hass: HomeAssistant,
    identity: MaikaInstallationIdentity,
    record: MaikaStoredLicense | None,
) -> str:
    if record is None:
        return "not_configured"
    if record.installation_hash != identity.installation_hash:
        return "installation_mismatch"
    if record.status == LICENSE_STATUS_PENDING:
        return LICENSE_STATUS_PENDING
    if not record.lease_token:
        return record.status
    try:
        client = MaikaLicenseClient(hass, record.server_url, identity)
        return client.verify_lease(record.lease_token).state_at()
    except (MaikaLicenseTokenError, ValueError):
        return "invalid_lease"


class MaikaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a MAIKA config flow."""

    VERSION = 3

    def __init__(self) -> None:
        self._pending_license: MaikaStoredLicense | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Activate this Home Assistant installation."""
        identity = await async_get_installation_identity(self.hass)
        store = MaikaLicenseStore(self.hass)
        record = await store.async_load()
        cached_state = await _async_cached_license_state(self.hass, identity, record)
        if user_input is None:
            if cached_state in {LICENSE_STATUS_ACTIVE, LICENSE_STATUS_GRACE}:
                return await self.async_step_account()
            if cached_state == LICENSE_STATUS_PENDING and record is not None:
                self._pending_license = record
                return await self.async_step_activation_pending()

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                server_url = _resolve_server_url(user_input, record)
                client = MaikaLicenseClient(self.hass, server_url, identity)
                response = await client.async_activate(
                    str(user_input[CONF_LICENSE_KEY])
                )
                record = await _async_store_license_response(
                    self.hass,
                    server_url=server_url,
                    identity=identity,
                    previous=None,
                    response=response,
                )
            except ValueError as err:
                key = str(err)
                errors[
                    CONF_LICENSE_SERVER_URL
                    if key == "invalid_server_url"
                    else CONF_LICENSE_KEY
                ] = key
            except MaikaLicenseConnectionError:
                errors["base"] = "cannot_connect_license"
            except MaikaLicenseResponseError as err:
                errors["base"] = _license_error_key(err.code)
            except MaikaLicenseTokenError:
                errors["base"] = "invalid_license_response"
            except Exception:
                _LOGGER.exception("Unexpected exception during MAIKA activation")
                errors["base"] = "unknown"
            else:
                if response.status in {LICENSE_STATUS_ACTIVE, LICENSE_STATUS_GRACE}:
                    return await self.async_step_account()
                if response.status == LICENSE_STATUS_PENDING:
                    self._pending_license = record
                    return await self.async_step_activation_pending()
                errors["base"] = _license_error_key(response.status)

        server_default = record.server_url if record else DEFAULT_LICENSE_SERVER_URL
        schema = _server_url_schema(server_default)
        schema[vol.Required(CONF_LICENSE_KEY)] = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={
                "activation_code": identity.activation_code,
                "portal_url": LICENSE_PORTAL_URL or "—",
            },
        )

    async def async_step_activation_pending(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Wait for the seller to approve this installation."""
        record = (
            self._pending_license or await MaikaLicenseStore(self.hass).async_load()
        )
        identity = await async_get_installation_identity(self.hass)
        if record is None or record.installation_hash != identity.installation_hash:
            return await self.async_step_user()

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                response = await MaikaLicenseClient(
                    self.hass, record.server_url, identity
                ).async_refresh(record.refresh_token)
                record = await _async_store_license_response(
                    self.hass,
                    server_url=record.server_url,
                    identity=identity,
                    previous=record,
                    response=response,
                )
            except MaikaLicenseConnectionError:
                errors["base"] = "cannot_connect_license"
            except MaikaLicenseResponseError as err:
                errors["base"] = _license_error_key(err.code)
            except MaikaLicenseTokenError:
                errors["base"] = "invalid_license_response"
            else:
                if response.status in {LICENSE_STATUS_ACTIVE, LICENSE_STATUS_GRACE}:
                    return await self.async_step_account()
                if response.status != LICENSE_STATUS_PENDING:
                    return await self.async_step_user()
                errors["base"] = "license_pending"
            self._pending_license = record

        return self.async_show_form(
            step_id="activation_pending",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"activation_code": record.activation_code},
        )

    async def async_step_account(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create an entry from MAIKA account credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            normalized = {
                CONF_PHONE_NUMBER: normalize_login_identifier(
                    str(user_input[CONF_PHONE_NUMBER])
                ),
                CONF_PASSWORD: str(user_input[CONF_PASSWORD]),
                CONF_CLIENT_ID: str(uuid4()),
                CONF_SESSION_ID: str(uuid4()),
            }
            try:
                info = await _async_validate_input(self.hass, normalized)
            except MaikaAuthenticationError:
                errors["base"] = "invalid_auth"
            except MaikaApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during MAIKA setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=normalized)

        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PHONE_NUMBER): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update expired or changed MAIKA credentials."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="reauth_failed")

        errors: dict[str, str] = {}
        if user_input is not None:
            updated_data = {
                **entry.data,
                CONF_PHONE_NUMBER: normalize_login_identifier(
                    str(user_input[CONF_PHONE_NUMBER])
                ),
                CONF_PASSWORD: str(user_input[CONF_PASSWORD]),
            }
            try:
                info = await _async_validate_input(self.hass, updated_data)
            except MaikaAuthenticationError:
                errors["base"] = "invalid_auth"
            except MaikaApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during MAIKA reauthentication")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=updated_data,
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PHONE_NUMBER,
                        default=entry.data.get(CONF_PHONE_NUMBER, ""),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
            errors=errors,
        )
