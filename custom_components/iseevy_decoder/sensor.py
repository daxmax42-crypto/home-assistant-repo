"""Sensor platform for ISEEVY Video Decoder."""

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    """Set up ISEEVY sensor entities."""
    coordinator: ISEEVYDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        ISEEVYFirmwareSensor(coordinator, entry),
        ISEEVYPlayStatusSensor(coordinator, entry),
        ISEEVYVideoFormatSensor(coordinator, entry),
        ISEEVYAspectRatioSensor(coordinator, entry),
        ISEEVYLanguageSensor(coordinator, entry),
        ISEEVYRTSPTransportSensor(coordinator, entry),
        ISEEVYIPAddressSensor(coordinator, entry),
        ISEEVYMACAddressSensor(coordinator, entry),
        ISEEVYVolumeSensor(coordinator, entry),
        ISEEVYCurrentStreamSensor(coordinator, entry),
        ISEEVYStreamCountSensor(coordinator, entry),
        ISEEVDHCPEnabledSensor(coordinator, entry),
        ISEEVAutoRebootSensor(coordinator, entry),
        ISEEVYLowDelaySensor(coordinator, entry),
    ]

    async_add_entities(entities)


class ISEEVYBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for ISEEVY decoder."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry, key: str, name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
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


class ISEEVYFirmwareSensor(ISEEVYBaseSensor):
    """Firmware version sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "firmware_version", "Firmware Version")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:chip"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("firmware_version") if self.coordinator.data else None


class ISEEVYPlayStatusSensor(ISEEVYBaseSensor):
    """Play status sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "play_status", "Play Status")
        self._attr_icon = "mdi:play-circle-outline"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("play_status") if self.coordinator.data else None


class ISEEVYVideoFormatSensor(ISEEVYBaseSensor):
    """Video format sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "video_format", "Video Format")
        self._attr_icon = "mdi:monitor-screenshot"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("video_format") if self.coordinator.data else None


class ISEEVYAspectRatioSensor(ISEEVYBaseSensor):
    """Aspect ratio sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "aspect", "Aspect Ratio")
        self._attr_icon = "mdi:crop"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("aspect") if self.coordinator.data else None


class ISEEVYLanguageSensor(ISEEVYBaseSensor):
    """Language sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "language", "Language")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:translate"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("language") if self.coordinator.data else None


class ISEEVYRTSPTransportSensor(ISEEVYBaseSensor):
    """RTSP transport sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "rtsp_transport", "RTSP Transport")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("rtsp_transport") if self.coordinator.data else None


class ISEEVYIPAddressSensor(ISEEVYBaseSensor):
    """IP address sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "ip_address", "IP Address")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:ip-network"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("ip_address") if self.coordinator.data else None


class ISEEVYMACAddressSensor(ISEEVYBaseSensor):
    """MAC address sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "mac_address", "MAC Address")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:network-outline"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("mac_address") if self.coordinator.data else None


class ISEEVYVolumeSensor(ISEEVYBaseSensor):
    """Volume sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "volume", "Volume")
        self._attr_icon = "mdi:volume-high"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("volume") if self.coordinator.data else None


class ISEEVYCurrentStreamSensor(ISEEVYBaseSensor):
    """Current stream sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "current_stream", "Current Stream")
        self._attr_icon = "mdi:video-input-hdmi"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        streams = self.coordinator.data.get("streams", [])
        current_idx = self.coordinator.data.get("current_stream_index")
        if current_idx and 1 <= current_idx <= len(streams):
            return streams[current_idx - 1]["title"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        streams = self.coordinator.data.get("streams", [])
        current_idx = self.coordinator.data.get("current_stream_index")
        if current_idx and 1 <= current_idx <= len(streams):
            stream = streams[current_idx - 1]
            return {
                "stream_index": current_idx,
                "stream_url": stream["url"],
            }
        return None


class ISEEVYStreamCountSensor(ISEEVYBaseSensor):
    """Stream count sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "stream_count", "Stream Count")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:counter"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data:
            return None
        return len(self.coordinator.data.get("streams", []))


class ISEEVDHCPEnabledSensor(ISEEVYBaseSensor):
    """DHCP enabled sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "dhcp_enabled", "DHCP Enabled")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["Enabled", "Disabled"]

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return "Enabled" if self.coordinator.data.get("dhcp_enabled") else "Disabled"


class ISEEVAutoRebootSensor(ISEEVYBaseSensor):
    """Auto reboot sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "autoreboot_enabled", "Auto Reboot")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["Enabled", "Disabled"]

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return "Enabled" if self.coordinator.data.get("autoreboot_enabled") else "Disabled"


class ISEEVYLowDelaySensor(ISEEVYBaseSensor):
    """Low delay mode sensor."""

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "lowdelay_mode", "Low Delay Mode")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["Enabled", "Disabled"]

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return "Enabled" if self.coordinator.data.get("lowdelay_mode") else "Disabled"