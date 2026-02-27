from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)
from .videohub import BlackmagicVideohubClient, VideohubState


class CannotConnect(HomeAssistantError):
    """Error to indicate connection failure."""


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> VideohubState:
    """Validate the user input allows us to connect."""
    del hass
    client = BlackmagicVideohubClient(
        host=data[CONF_HOST],
        port=data.get(CONF_PORT, DEFAULT_PORT),
    )
    try:
        return await client.async_fetch_state()
    except Exception as err:  # noqa: BLE001
        raise CannotConnect from err


class BlackmagicVideohubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Blackmagic Videohub."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                state = await _validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                unique_id = state.unique_id or f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                configured_name = (user_input.get(CONF_NAME) or "").strip()
                title = (
                    configured_name
                    or state.model_name
                    or f"{DEFAULT_NAME} ({user_input[CONF_HOST]})"
                )
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                    vol.Optional(CONF_NAME, default=""): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=DEFAULT_SCAN_INTERVAL_SECONDS,
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return BlackmagicVideohubOptionsFlow(config_entry)


class BlackmagicVideohubOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=3600)
                    )
                }
            ),
        )
