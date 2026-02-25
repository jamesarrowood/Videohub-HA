from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BlackmagicVideohubRuntimeData
from .const import DOMAIN
from .coordinator import BlackmagicVideohubCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: BlackmagicVideohubRuntimeData = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime.coordinator
    state = coordinator.data
    if state is None:
        return

    entities = [
        VideohubOutputRouteSelect(
            coordinator=coordinator,
            entry=entry,
            output_index=output_index,
        )
        for output_index in state.output_indexes
    ]
    async_add_entities(entities)


@dataclass(slots=True)
class VideohubInputOption:
    index: int
    label: str

    @property
    def option_value(self) -> str:
        return f"{self.index}: {self.label}"


class VideohubOutputRouteSelect(CoordinatorEntity[BlackmagicVideohubCoordinator], SelectEntity):
    """Select entity representing one Videohub output route."""

    _attr_has_entity_name = True

    def __init__(
        self,
        *,
        coordinator: BlackmagicVideohubCoordinator,
        entry: ConfigEntry,
        output_index: int,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._output_index = output_index
        self._attr_unique_id = f"{entry.entry_id}_output_route_{output_index}"
        self._option_to_index: dict[str, int] = {}

    @property
    def device_info(self) -> DeviceInfo:
        state = self.coordinator.data
        model = state.model_name if state else None
        unique = (
            state.unique_id
            if state and state.unique_id
            else f"{self._entry.data.get(CONF_HOST)}:{self._entry.data.get(CONF_PORT, 9990)}"
        )
        return DeviceInfo(
            identifiers={(DOMAIN, unique)},
            manufacturer="Blackmagic Design",
            name=self._entry.title,
            model=model,
        )

    @property
    def name(self) -> str:
        state = self.coordinator.data
        if state is None:
            return f"Output {self._output_index}"
        label = state.output_labels.get(self._output_index, f"Output {self._output_index}")
        return f"Output {self._output_index} ({label})"

    @property
    def options(self) -> list[str]:
        state = self.coordinator.data
        if state is None:
            return []
        options: list[str] = []
        option_to_index: dict[str, int] = {}
        for idx in state.input_indexes:
            label = state.input_labels.get(idx, f"Input {idx}")
            option = VideohubInputOption(index=idx, label=label).option_value
            options.append(option)
            option_to_index[option] = idx
        self._option_to_index = option_to_index
        return options

    @property
    def current_option(self) -> str | None:
        state = self.coordinator.data
        if state is None:
            return None
        input_index = state.video_output_routing.get(self._output_index)
        if input_index is None:
            return None
        label = state.input_labels.get(input_index, f"Input {input_index}")
        return VideohubInputOption(index=input_index, label=label).option_value

    async def async_select_option(self, option: str) -> None:
        if option not in self._option_to_index:
            # Refresh mapping from latest coordinator state if needed.
            _ = self.options
        input_index = self._option_to_index[option]
        await self.coordinator.async_set_route(self._output_index, input_index)
