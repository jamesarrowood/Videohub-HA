from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_ENTRY_ID,
    ATTR_INPUT,
    ATTR_OUTPUT,
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    PLATFORMS,
    SERVICE_ROUTE_OUTPUT,
)
from .coordinator import BlackmagicVideohubCoordinator
from .videohub import BlackmagicVideohubClient

_LOGGER = logging.getLogger(__name__)

ROUTE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required(ATTR_OUTPUT): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Required(ATTR_INPUT): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)


@dataclass(slots=True)
class BlackmagicVideohubRuntimeData:
    coordinator: BlackmagicVideohubCoordinator


BlackmagicVideohubConfigEntry = ConfigEntry


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})

    if not hass.services.has_service(DOMAIN, SERVICE_ROUTE_OUTPUT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ROUTE_OUTPUT,
            _make_route_output_service_handler(hass),
            schema=ROUTE_SERVICE_SCHEMA,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: BlackmagicVideohubConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    name = entry.title or entry.data.get(CONF_NAME, DEFAULT_NAME)
    scan_seconds = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
    )

    client = BlackmagicVideohubClient(host=host, port=port)
    coordinator = BlackmagicVideohubCoordinator(
        hass,
        client=client,
        name=name,
        update_interval=timedelta(seconds=scan_seconds),
    )

    await coordinator.async_config_entry_first_refresh()
    if coordinator.data is None:
        raise ConfigEntryNotReady("No Videohub data received")

    hass.data[DOMAIN][entry.entry_id] = BlackmagicVideohubRuntimeData(coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BlackmagicVideohubConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


def _make_route_output_service_handler(hass: HomeAssistant):
    async def _handle_route_output(call: ServiceCall) -> None:
        entry_id = call.data[ATTR_ENTRY_ID]
        output_index = call.data[ATTR_OUTPUT]
        input_index = call.data[ATTR_INPUT]

        runtime: BlackmagicVideohubRuntimeData | None = hass.data.get(DOMAIN, {}).get(entry_id)
        if runtime is None:
            raise HomeAssistantError(
                f"No Blackmagic Videohub config entry loaded for entry_id={entry_id}"
            )

        try:
            await runtime.coordinator.async_set_route(output_index, input_index)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(
                f"Failed to route output {output_index} to input {input_index}: {err}"
            ) from err

    return _handle_route_output
