"""Config flow for ISEEVY Video Decoder."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)

from .const import DEFAULT_PORT, DEFAULT_USERNAME
from .api import ISEEVYClient, ISEEVYAuthError, ISEEVYConnectionError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
})


class ISEEVYConfigFlow(config_entries.ConfigFlow, domain="iseevy_decoder"):
    """Handle a config flow for ISEEVY Video Decoder."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            client = ISEEVYClient(
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                port=user_input[CONF_PORT],
            )

            try:
                if await client.test_connection():
                    await client.close()
                    return self.async_create_entry(
                        title=f"ISEEVY Decoder ({user_input[CONF_HOST]})",
                        data=user_input,
                    )
                errors["base"] = "auth_failed"
            except ISEEVYConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle re-authentication."""
        errors = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            client = ISEEVYClient(
                host=entry.data[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                port=entry.data[CONF_PORT],
            )

            try:
                if await client.test_connection():
                    await client.close()
                    # Update the existing entry with new credentials
                    self.hass.config_entries.async_update_entry(
                        entry, data={**entry.data, **user_input}
                    )
                    return self.async_abort(reason="reauth_successful")
                errors["base"] = "auth_failed"
            except ISEEVYConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"
            finally:
                await client.close()

        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME, default=entry.data[CONF_USERNAME]): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )