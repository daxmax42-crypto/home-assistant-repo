"""Select platform for ISEEVY Video Decoder - Stream selection."""

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
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
    """Set up ISEEVY select entities."""
    coordinator: ISEEVYDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        ISEEVYStreamSelect(coordinator, entry),
    ])


class ISEEVYStreamSelect(CoordinatorEntity, SelectEntity):
    """Select entity for choosing the active stream."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_stream_select"
        self._attr_name = "Active Stream"
        self._attr_icon = "mdi:video-switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ISEEVY Decoder ({entry.data['host']})",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=SW_VERSION,
            configuration_url=f"http://{entry.data['host']}",
        )

    @property
    def options(self) -> list[str]:
        """Return available stream options."""
        if not self.coordinator.data:
            return []
        streams = self.coordinator.data.get("streams", [])
        return [f"{s['index']}: {s['title']}" for s in streams if s['title']]

    @property
    def current_option(self) -> str | None:
        """Return the currently selected stream."""
        if not self.coordinator.data:
            return None
        streams = self.coordinator.data.get("streams", [])
        current_idx = self.coordinator.data.get("current_stream_index")
        if current_idx and 1 <= current_idx <= len(streams):
            stream = streams[current_idx - 1]
            return f"{stream['index']}: {stream['title']}"
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected stream."""
        try:
            # Extract index from option string (format: "1: Stream Name")
            stream_index = int(option.split(":")[0].strip())
            success = await self.coordinator.async_set_stream(stream_index)
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to switch to stream %d", stream_index)
        except (ValueError, IndexError) as err:
            _LOGGER.error("Invalid stream option: %s", option)