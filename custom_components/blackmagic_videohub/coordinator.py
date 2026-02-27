from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .videohub import BlackmagicVideohubClient, VideohubState

_LOGGER = logging.getLogger(__name__)


class BlackmagicVideohubCoordinator(DataUpdateCoordinator[VideohubState]):
    """Coordinator for polling Videohub state."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        client: BlackmagicVideohubClient,
        name: str,
        update_interval: timedelta | None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=update_interval,
        )
        self.client = client

    async def _async_update_data(self) -> VideohubState:
        try:
            return await self.client.async_fetch_state()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Failed to fetch Videohub state: {err}") from err

    async def async_set_route(self, output_index: int, input_index: int) -> None:
        await self.client.async_route_output(output_index, input_index)
        if self.data is None:
            return

        # Avoid immediate post-route polling; update locally and let normal poll
        # cadence verify state to reduce connection churn on fragile devices.
        updated = VideohubState(
            model_name=self.data.model_name,
            unique_id=self.data.unique_id,
            input_labels=dict(self.data.input_labels),
            output_labels=dict(self.data.output_labels),
            video_output_routing=dict(self.data.video_output_routing),
            device_fields=dict(self.data.device_fields),
        )
        updated.video_output_routing[output_index] = input_index
        self.async_set_updated_data(updated)
