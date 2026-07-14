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
        ISEEVYTimezoneNumber(coordinator, entry),
        ISEEVYAutoRebootTimeNumber(coordinator, entry),
        ISEEVYLunboTimeNumber(coordinator, entry),
        ISEEVYUdpBufferNumber(coordinator, entry),
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


class _SettingNumber(CoordinatorEntity, NumberEntity):
    """Number mirrored from a decoder numeric setting (telnet cfg.ini write)."""

    def __init__(self, c, e, key, name, data_key, cfg_field, mn, mx, icon):
        super().__init__(c)
        self._entry = e
        self._data_key = data_key
        self._cfg_field = cfg_field
        self._attr_unique_id = f"{e.entry_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = mn
        self._attr_native_max_value = mx
        self._attr_native_step = 1
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, e.entry_id)},
            name=f"ISEEVY Decoder ({e.data['host']})",
            manufacturer=MANUFACTURER, model=MODEL, sw_version=SW_VERSION,
            configuration_url=f"http://{e.data['host']}")

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        try:
            return float(self.coordinator.data.get(self._data_key, 0))
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_setting(self._cfg_field, str(int(value)))
        await self.coordinator.async_request_refresh()


class ISEEVYTimezoneNumber(_SettingNumber):
    def __init__(self, c, e):
        super().__init__(c, e, "timezone", "Time Zone", "timezone", "timezone", 0, 12, "mdi:earth")


class ISEEVYAutoRebootTimeNumber(_SettingNumber):
    def __init__(self, c, e):
        super().__init__(c, e, "autoreboot_time", "Auto Reboot Time", "autoreboot_time",
                         "autoreboot_time", 0, 23, "mdi:clock")


class ISEEVYLunboTimeNumber(_SettingNumber):
    def __init__(self, c, e):
        super().__init__(c, e, "lunbo_time", "Channel Schedule Time", "lunbo_time",
                         "lunbo_time", 0, 59, "mdi:timer")


class ISEEVYUdpBufferNumber(_SettingNumber):
    def __init__(self, c, e):
        super().__init__(c, e, "udp_buffer", "UDP Video Buffer", "udp_buffer",
                         "udp_buf", 1, 40, "mdi:buffer")