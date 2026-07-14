"""Switch entities for ISEEVY decoder settings.

All writes go through the safe telnet cfg.ini path (coordinator.async_set_setting),
NEVER /set.cgi (which corrupts the device config).
"""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ISEEVYDataUpdateCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL, SW_VERSION

# (data_key in coordinator, entity name, cfg.ini field to write)
_SWITCHES = [
    ("dhcp_enabled", "DHCP", "dhcp"),
    ("lowdelay_mode", "Multicast Low Latency", "lowdelay_mode"),
    ("showtime_enabled", "Clock", "showtime"),
    ("autoreboot_enabled", "Schedule to Reboot", "autoreboot_status"),
    ("lunbo_enabled", "Channel Schedule", "lunbo_status"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ISEEVY switch entities."""
    coordinator: ISEEVYDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            _SettingSwitch(coordinator, entry, data_key, name, cfg_field)
            for data_key, name, cfg_field in _SWITCHES
        ]
    )


class _SettingSwitch(CoordinatorEntity, SwitchEntity):
    """Switch mirrored from a decoder boolean setting (telnet cfg.ini write)."""

    def __init__(self, coordinator, entry, data_key, name, cfg_field) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._data_key = data_key
        self._cfg_field = cfg_field
        self._attr_unique_id = f"{entry.entry_id}_{data_key}"
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
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.get(self._data_key, False))

    async def async_turn_on(self, **_kwargs: object) -> None:
        # DHCP is a network setting the app reads at boot -> reboot required.
        await self.coordinator.async_set_setting(self._cfg_field, "1", reboot=(self._cfg_field == "dhcp"))
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **_kwargs: object) -> None:
        await self.coordinator.async_set_setting(self._cfg_field, "0", reboot=(self._cfg_field == "dhcp"))
        await self.coordinator.async_request_refresh()
