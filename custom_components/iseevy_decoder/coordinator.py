"""Coordinator for ISEEVY Video Decoder integration."""

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ISEEVYClient, ISEEVYAPIError
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ISEEVYDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the ISEEVY decoder."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.entry = entry
        self.client = ISEEVYClient(
            host=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            data = await self.client.get_all_data()
            return data
        except ISEEVYAPIError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_set_volume(self, volume: int) -> bool:
        """Set volume on the decoder."""
        try:
            await self.client.set_volume(volume)
            return True
        except ISEEVYAPIError as err:
            _LOGGER.error("Failed to set volume: %s", err)
            return False

    async def async_select_stream(self, stream_index: int) -> bool:
        """Select a stream on the decoder."""
        try:
            await self.client.select_stream(stream_index)
            return True
        except ISEEVYAPIError as err:
            _LOGGER.error("Failed to select stream: %s", err)
            return False

    async def async_select_stream_by_name(self, stream_name: str) -> bool:
        """Select a stream on the decoder by name."""
        try:
            # Get current streams to find index by name
            data = await self.client.get_all_data()
            streams = data.get("streams", [])
            
            # Find stream by name (case-insensitive exact match)
            for stream in streams:
                if stream.get("title", "").lower() == stream_name.lower():
                    return await self.async_select_stream(stream["index"])
            
            _LOGGER.error("Stream with name '%s' not found", stream_name)
            return False
        except ISEEVYAPIError as err:
            _LOGGER.error("Failed to select stream by name: %s", err)
            return False

    async def async_shutdown(self) -> None:
        """Shutdown the client."""
        await self.client.close()
        await super().async_shutdown()