"""Config flow for MAIKA."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    MaikaApiClient,
    MaikaApiError,
    MaikaAuthenticationError,
)
from .const import (
    CONF_CLIENT_ID,
    CONF_ENABLE_CLOUD_CAST,
    CONF_ENABLE_VOICE_COMMAND_SENSOR,
    CONF_LICENSE_KEY,
    CONF_LICENSE_SERVER_URL,
    CONF_PASSWORD,
    CONF_PHONE_NUMBER,
    CONF_SCAN_INTERVAL,
    CONF_SESSION_ID,
    CONF_VOICE_COMMAND_RULES,
    CONF_VOICE_SUCCESS_AUDIO_SOURCE,
    CONF_VOICE_SUCCESS_AUDIO_TIMING,
    CONF_VOICE_SUCCESS_AUDIO_URL,
    CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VOICE_COMMAND_RULES,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    VOICE_SUCCESS_AUDIO_SOURCE_BUNDLED,
    VOICE_SUCCESS_AUDIO_SOURCE_CUSTOM,
    VOICE_SUCCESS_AUDIO_SOURCE_DISABLED,
    VOICE_SUCCESS_AUDIO_SOURCE_OPTIONS,
    VOICE_SUCCESS_AUDIO_TIMING_OPTIONS,
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
    BUNDLED_VOICE_SUCCESS_AUDIO_URL,
    DEFAULT_LICENSE_SERVER_URL,
    LICENSE_PORTAL_URL,
)
from .license_store import MaikaLicenseStore, MaikaStoredLicense
from .media_url import is_valid_http_media_url
from .phone import normalize_login_identifier
from .voice_rules import VoiceCommandRulesError, parse_voice_command_rules
from .voice_success_audio import (
    resolve_voice_success_audio_source,
    resolve_voice_success_audio_timing,
)

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


def _maika_media_player_entity_ids(
    registry: er.EntityRegistry, entry_id: str
) -> tuple[str, ...]:
    return tuple(
        sorted(
            entry.entity_id
            for entry in er.async_entries_for_config_entry(registry, entry_id)
            if entry.domain == Platform.MEDIA_PLAYER
            and entry.platform == DOMAIN
            and entry.disabled_by is None
        )
    )


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
    await client.async_list_devices()
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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the MAIKA options flow."""
        return MaikaOptionsFlow()


class MaikaOptionsFlow(config_entries.OptionsFlow):
    """Configure licensing, polling and experimental cloud features."""

    def __init__(self) -> None:
        self._pending_license: MaikaStoredLicense | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["license", "features"],
        )

    async def async_step_license(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Activate, replace or refresh this HA installation license."""
        identity = await async_get_installation_identity(self.hass)
        store = MaikaLicenseStore(self.hass)
        record = await store.async_load()
        status = await _async_cached_license_state(self.hass, identity, record)
        errors: dict[str, str] = {}

        if user_input is not None:
            license_key = str(user_input.get(CONF_LICENSE_KEY, "")).strip()
            try:
                server_url = _resolve_server_url(user_input, record)
                client = MaikaLicenseClient(self.hass, server_url, identity)
                if license_key:
                    response = await client.async_activate(license_key)
                elif record is not None and (
                    record.installation_hash == identity.installation_hash
                ):
                    response = await client.async_refresh(record.refresh_token)
                else:
                    errors[CONF_LICENSE_KEY] = "license_key_required"
                    response = None

                if response is not None:
                    record = await _async_store_license_response(
                        self.hass,
                        server_url=server_url,
                        identity=identity,
                        previous=None if license_key else record,
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
                _LOGGER.exception("Unexpected exception while updating MAIKA license")
                errors["base"] = "unknown"
            else:
                if response is not None and response.status in {
                    LICENSE_STATUS_ACTIVE,
                    LICENSE_STATUS_GRACE,
                }:
                    self.config_entry.async_create_task(
                        self.hass,
                        self.hass.config_entries.async_reload(
                            self.config_entry.entry_id
                        ),
                        "Reload MAIKA after license activation",
                    )
                    return self.async_create_entry(
                        title="", data=dict(self.config_entry.options)
                    )
                if response is not None and response.status == LICENSE_STATUS_PENDING:
                    self._pending_license = record
                    return await self.async_step_license_pending()
                if response is not None:
                    errors["base"] = _license_error_key(response.status)

        server_default = record.server_url if record else DEFAULT_LICENSE_SERVER_URL
        schema = _server_url_schema(server_default)
        schema[vol.Optional(CONF_LICENSE_KEY, default="")] = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        )
        return self.async_show_form(
            step_id="license",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={
                "activation_code": identity.activation_code,
                "license_status": status,
                "portal_url": LICENSE_PORTAL_URL or "—",
            },
        )

    async def async_step_license_pending(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Recheck a manually approved activation."""
        record = (
            self._pending_license or await MaikaLicenseStore(self.hass).async_load()
        )
        identity = await async_get_installation_identity(self.hass)
        if record is None or record.installation_hash != identity.installation_hash:
            return await self.async_step_license()

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
                    self.config_entry.async_create_task(
                        self.hass,
                        self.hass.config_entries.async_reload(
                            self.config_entry.entry_id
                        ),
                        "Reload MAIKA after license approval",
                    )
                    return self.async_create_entry(
                        title="", data=dict(self.config_entry.options)
                    )
                if response.status != LICENSE_STATUS_PENDING:
                    return await self.async_step_license()
                errors["base"] = "license_pending"
            self._pending_license = record

        return self.async_show_form(
            step_id="license_pending",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"activation_code": record.activation_code},
        )

    async def async_step_features(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage integration polling and experimental feature options."""
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}
        values = dict(self.config_entry.options)
        registry = er.async_get(self.hass)
        media_player_entity_ids = _maika_media_player_entity_ids(
            registry, self.config_entry.entry_id
        )

        if user_input is not None:
            normalized = dict(user_input)
            selected_media_player = str(
                normalized.get(CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID, "")
            ).strip()
            if selected_media_player and (
                registry_entry := registry.async_get(selected_media_player)
            ):
                selected_media_player = registry_entry.entity_id
            if not selected_media_player and len(media_player_entity_ids) == 1:
                selected_media_player = media_player_entity_ids[0]
            normalized[CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID] = (
                selected_media_player
            )
            audio_source = resolve_voice_success_audio_source(normalized)
            normalized[CONF_VOICE_SUCCESS_AUDIO_SOURCE] = audio_source
            normalized[CONF_VOICE_SUCCESS_AUDIO_TIMING] = (
                resolve_voice_success_audio_timing(normalized)
            )
            audio_url = str(normalized.get(CONF_VOICE_SUCCESS_AUDIO_URL, "")).strip()
            normalized[CONF_VOICE_SUCCESS_AUDIO_URL] = audio_url

            try:
                parse_voice_command_rules(
                    str(normalized.get(CONF_VOICE_COMMAND_RULES, ""))
                )
            except VoiceCommandRulesError as err:
                errors[CONF_VOICE_COMMAND_RULES] = "invalid_voice_command_rules"
                description_placeholders["rule_error"] = str(err)

            if audio_source != VOICE_SUCCESS_AUDIO_SOURCE_DISABLED:
                if not normalized.get(CONF_ENABLE_VOICE_COMMAND_SENSOR, False):
                    errors[CONF_VOICE_SUCCESS_AUDIO_SOURCE] = (
                        "voice_success_audio_requires_voice_sensor"
                    )
                elif not normalized.get(CONF_ENABLE_CLOUD_CAST, False):
                    errors[CONF_VOICE_SUCCESS_AUDIO_SOURCE] = (
                        "voice_success_audio_requires_cloud_cast"
                    )

                if (
                    audio_source == VOICE_SUCCESS_AUDIO_SOURCE_BUNDLED
                    and not BUNDLED_VOICE_SUCCESS_AUDIO_URL
                ):
                    errors[CONF_VOICE_SUCCESS_AUDIO_SOURCE] = (
                        "voice_success_audio_bundled_unavailable"
                    )
                elif audio_source == VOICE_SUCCESS_AUDIO_SOURCE_CUSTOM and not (
                    audio_url and is_valid_http_media_url(audio_url)
                ):
                    errors[CONF_VOICE_SUCCESS_AUDIO_URL] = (
                        "voice_success_audio_url_invalid"
                    )

                media_player_entity_id = normalized[
                    CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID
                ]
                if not media_player_entity_id:
                    errors[CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID] = (
                        "voice_success_audio_media_player_required"
                    )
                else:
                    media_player_registry_entry = registry.async_get(
                        media_player_entity_id
                    )
                    if (
                        media_player_registry_entry is None
                        or media_player_registry_entry.domain != Platform.MEDIA_PLAYER
                        or media_player_registry_entry.platform != DOMAIN
                        or media_player_registry_entry.config_entry_id
                        != self.config_entry.entry_id
                    ):
                        errors[CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID] = (
                            "voice_success_audio_media_player_invalid"
                        )

            if not errors:
                return self.async_create_entry(title="", data=normalized)
            values = normalized

        if len(media_player_entity_ids) == 1:
            values[CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID] = media_player_entity_ids[
                0
            ]
        media_player_entity_marker = vol.Optional(
            CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID
        )
        if values.get(CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID):
            media_player_entity_marker = vol.Optional(
                CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID,
                default=values[CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID],
            )

        schema: dict[vol.Marker, Any] = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=values.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                ),
            ),
            vol.Optional(
                CONF_ENABLE_CLOUD_CAST,
                default=values.get(CONF_ENABLE_CLOUD_CAST, False),
            ): bool,
            vol.Optional(
                CONF_ENABLE_VOICE_COMMAND_SENSOR,
                default=values.get(CONF_ENABLE_VOICE_COMMAND_SENSOR, False),
            ): bool,
            vol.Optional(
                CONF_VOICE_COMMAND_RULES,
                default=values.get(
                    CONF_VOICE_COMMAND_RULES, DEFAULT_VOICE_COMMAND_RULES
                ),
            ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            vol.Optional(
                CONF_VOICE_SUCCESS_AUDIO_SOURCE,
                default=resolve_voice_success_audio_source(values),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(VOICE_SUCCESS_AUDIO_SOURCE_OPTIONS),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="voice_success_audio_source",
                )
            ),
            vol.Optional(
                CONF_VOICE_SUCCESS_AUDIO_TIMING,
                default=resolve_voice_success_audio_timing(values),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(VOICE_SUCCESS_AUDIO_TIMING_OPTIONS),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="voice_success_audio_timing",
                )
            ),
            vol.Optional(
                CONF_VOICE_SUCCESS_AUDIO_URL,
                default=values.get(CONF_VOICE_SUCCESS_AUDIO_URL, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
        }
        if len(media_player_entity_ids) != 1:
            schema[media_player_entity_marker] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=Platform.MEDIA_PLAYER,
                    integration=DOMAIN,
                )
            )

        return self.async_show_form(
            step_id="features",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={
                **description_placeholders,
                "portal_url": LICENSE_PORTAL_URL or "—",
            },
        )
