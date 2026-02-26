from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
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
        VideohubOutputMediaPlayer(
            coordinator=coordinator,
            entry=entry,
            output_index=output_index,
        )
        for output_index in state.output_indexes
    ]
    async_add_entities(entities)


@dataclass(slots=True)
class VideohubInputSource:
    index: int
    label: str

    @property
    def source_value(self) -> str:
        return f"{self.index}: {self.label}"


class VideohubOutputMediaPlayer(
    CoordinatorEntity[BlackmagicVideohubCoordinator],
    MediaPlayerEntity,
):
    """Media player entity representing one Videohub output route."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:video-switch"
    _attr_supported_features = MediaPlayerEntityFeature.SELECT_SOURCE

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
        self._attr_unique_id = f"{entry.entry_id}_media_output_route_{output_index}"
        self._source_to_index: dict[str, int] = {}

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
    def state(self) -> MediaPlayerState:
        return MediaPlayerState.ON

    @property
    def source_list(self) -> list[str]:
        state = self.coordinator.data
        if state is None:
            return []

        sources: list[str] = []
        source_to_index: dict[str, int] = {}
        for idx in state.input_indexes:
            label = state.input_labels.get(idx, f"Input {idx}")
            source = VideohubInputSource(index=idx, label=label).source_value
            sources.append(source)
            source_to_index[source] = idx

        self._source_to_index = source_to_index
        return sources

    @property
    def source(self) -> str | None:
        state = self.coordinator.data
        if state is None:
            return None
        input_index = state.video_output_routing.get(self._output_index)
        if input_index is None:
            return None
        label = state.input_labels.get(input_index, f"Input {input_index}")
        return VideohubInputSource(index=input_index, label=label).source_value

    async def async_select_source(self, source: str) -> None:
        if source not in self._source_to_index:
            _ = self.source_list
        input_index = self._source_to_index[source]
        await self.coordinator.async_set_route(self._output_index, input_index)
