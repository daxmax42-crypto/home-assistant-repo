"""Button platform for ISEEVY Video Decoder - Refresh button."""

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ISEEVYDataUpdateCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL, SW_VERSION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ISEEVY button entities."""
    coordinator: ISEEVYDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        ISEEVYRefreshButton(coordinator, entry),
        ISEEVYRefreshChannelListButton(coordinator, entry),
    ])


class ISEEVYRefreshButton(CoordinatorEntity, ButtonEntity):
    """Button entity to manually refresh the decoder data."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self._attr_name = "Refresh Stream"
        self._attr_icon = "mdi:refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ISEEVY Decoder ({entry.data['host']})",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=SW_VERSION,
            configuration_url=f"http://{entry.data['host']}",
        )

    async def async_press(self) -> None:
        """Press the button - refresh the coordinator."""
        await self.coordinator.async_request_refresh()


class ISEEVYRefreshChannelListButton(CoordinatorEntity, ButtonEntity):
    """Button entity to manually refresh the channel list from the decoder."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_refresh_channel_list"
        self._attr_name = "Refresh Channel List"
        self._attr_icon = "mdi:playlist-edit"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ISEEVY Decoder ({entry.data['host']})",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=SW_VERSION,
            configuration_url=f"http://{entry.data['host']}",
        )

    async def async_press(self) -> None:
        """Press the button - force refresh of channel list."""
        # Force a full data fetch which will re-query /getpro.cgi
        await self.coordinator.async_request_refresh()