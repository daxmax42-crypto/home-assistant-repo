"""Number platform for ISEEVY Video Decoder - Volume control."""

import logging
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
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
    """Set up ISEEVY number entities."""
    coordinator: ISEEVYDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        ISEEVYVolumeNumber(coordinator, entry),
    ])


class ISEEVYVolumeNumber(CoordinatorEntity, NumberEntity):
    """Number entity for volume control."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_volume"
        self._attr_name = "Volume"
        self._attr_icon = "mdi:volume-high"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ISEEVY Decoder ({entry.data['host']})",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=SW_VERSION,
            configuration_url=f"http://{entry.data['host']}",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.coordinator.data is not None

    @property
    def native_value(self) -> float | None:
        """Return the current volume."""
        if self.coordinator.data:
            return float(self.coordinator.data.get("volume", 0))
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the volume."""
        volume_int = int(value)
        success = await self.coordinator.async_set_volume(volume_int)
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set volume to %d", volume_int)