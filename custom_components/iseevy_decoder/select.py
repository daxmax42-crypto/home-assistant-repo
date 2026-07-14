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
        ISEEVYOutputResolutionSelect(coordinator, entry),
        ISEEVYAspectRatioSelect(coordinator, entry),
        ISEEVYLanguageSelect(coordinator, entry),
        ISEEVYRTSPOverSelect(coordinator, entry),
        ISEEVYTimezoneEWSelect(coordinator, entry),
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
        # Use cached last selected stream since device can't report current stream
        current_idx = self.coordinator.data.get("last_selected_stream")
        if current_idx and 1 <= current_idx <= len(streams):
            stream = streams[current_idx - 1]
            return f"{stream['index']}: {stream['title']}"
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected stream."""
        try:
            # Extract index from option string (format: "1: Stream Name")
            stream_index = int(option.split(":")[0].strip())
            success = await self.coordinator.async_select_stream(stream_index)
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to switch to stream %d", stream_index)
        except (ValueError, IndexError) as err:
            _LOGGER.error("Invalid stream option: %s", option)


# Resolution option list (format_type 0-16, must match const.FORMAT_TYPE_MAP order)
_RES_OPTIONS = [
    "1080P60", "1080P50", "1080P25", "1080I60", "1080I50",
    "720P60", "720P50", "576P", "480P", "576I", "480I",
    "720P5994", "1080P2997", "1080P5994", "1080I5994",
    "3840X2160_2997", "3840X2160_30",
]
_RES_LABEL_TO_CFG = {v: str(i) for i, v in enumerate(_RES_OPTIONS)}


class _ISEEVYSettingSelect(CoordinatorEntity, SelectEntity):
    """Base for settings selects: read a get.cgi field, write via telnet cfg.ini (never /set.cgi)."""

    def __init__(self, c, e, key, name, data_key, cfg_field, options, value_map, label_to_cfg, icon):
        super().__init__(c)
        self._entry = e
        self._attr_unique_id = f"{e.entry_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._data_key = data_key
        self._cfg_field = cfg_field
        self._options = options
        self._value_map = value_map
        self._label_to_cfg = label_to_cfg
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, e.entry_id)},
            name=f"ISEEVY Decoder ({e.data['host']})",
            manufacturer=MANUFACTURER, model=MODEL, sw_version=SW_VERSION,
            configuration_url=f"http://{e.data['host']}")

    @property
    def options(self):
        return self._options

    @property
    def current_option(self):
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self._data_key)
        if raw is None:
            return None
        return self._value_map.get(str(raw))

    async def async_select_option(self, option: str) -> None:
        if option in self._label_to_cfg:
            await self.coordinator.async_set_setting(self._cfg_field, self._label_to_cfg[option])
            await self.coordinator.async_request_refresh()


class ISEEVYOutputResolutionSelect(_ISEEVYSettingSelect):
    def __init__(self, c, e):
        super().__init__(c, e, "output_resolution", "Output Resolution", "video_format",
                         "format_type", _RES_OPTIONS, {v: v for v in _RES_OPTIONS},
                         _RES_LABEL_TO_CFG, "mdi:monitor")


class ISEEVYAspectRatioSelect(_ISEEVYSettingSelect):
    def __init__(self, c, e):
        super().__init__(c, e, "aspect_ratio", "Aspect Ratio", "aspect_ratio", "aspect",
                         ["4:3", "16:9", "Auto"], {"4:3": "4:3", "16:9": "16:9", "Auto": "Auto"},
                         {"4:3": "0", "16:9": "1", "Auto": "2"}, "mdi:crop")


class ISEEVYLanguageSelect(_ISEEVYSettingSelect):
    def __init__(self, c, e):
        super().__init__(c, e, "language", "Language", "language", "language",
                         ["Simplified Chinese", "English"],
                         {"Simplified Chinese": "Simplified Chinese", "English": "English"},
                         {"Simplified Chinese": "0", "English": "1"}, "mdi:translate")


class ISEEVYRTSPOverSelect(_ISEEVYSettingSelect):
    def __init__(self, c, e):
        super().__init__(c, e, "rtsp_over_type", "RTSP Over Type", "rtsp_transport", "rtspover",
                         ["TCP", "UDP"], {"TCP": "TCP", "UDP": "UDP"},
                         {"TCP": "0", "UDP": "1"}, "mdi:network")


class ISEEVYTimezoneEWSelect(_ISEEVYSettingSelect):
    def __init__(self, c, e):
        super().__init__(c, e, "timezone_ew", "Time Zone E/W", "timezone_ew", "timezone_ew",
                         ["EAST", "WEST"], {"0": "EAST", "1": "WEST"},
                         {"EAST": "0", "WEST": "1"}, "mdi:earth")