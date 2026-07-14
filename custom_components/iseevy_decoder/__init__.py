"""ISEEVY Video Decoder integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import ISEEVYAuthError, ISEEVYConnectionError
from .coordinator import ISEEVYDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ISEEVY Video Decoder from a config entry."""
    coordinator = ISEEVYDataUpdateCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ISEEVYAuthError as err:
        _LOGGER.error("Authentication failed for %s", entry.data["host"])
        # Trigger reauth flow
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "reauth", "entry_id": entry.entry_id},
                data=entry.data,
            )
        )
        return False
    except ISEEVYConnectionError as err:
        raise ConfigEntryNotReady(f"Cannot connect to {entry.data['host']}: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def async_select_stream(call):
        """Handle select_stream service call."""
        stream_index = call.data.get("stream_index")
        stream_name = call.data.get("stream_name")
        
        if stream_index is not None:
            success = await coordinator.async_select_stream(stream_index)
        elif stream_name is not None:
            success = await coordinator.async_select_stream_by_name(stream_name)
        else:
            _LOGGER.error("Either stream_index or stream_name must be provided")
            return
        
        if success:
            await coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to select stream")

    hass.services.async_register(
        DOMAIN,
        "select_stream",
        async_select_stream,
        schema=None,  # Schema defined in services.yaml
    )

    async def async_set_volume(call):
        """Set decoder volume (safe telnet cfg.ini write — never /set.cgi)."""
        volume = call.data.get("volume")
        if volume is None:
            _LOGGER.error("volume is required for set_volume")
            return
        success = await coordinator.async_set_volume(int(volume))
        if success:
            await coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set volume to %d", volume)

    hass.services.async_register(DOMAIN, "set_volume", async_set_volume, schema=None)

    async def async_verify_channel(call):
        """Poll the decoder for the real current channel via netstat (ground truth)."""
        result = await coordinator.async_verify_channel()
        _LOGGER.info("Verified channel: %s", result)

    hass.services.async_register(
        DOMAIN,
        "verify_channel",
        async_verify_channel,
        schema=None,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()
    hass.services.async_remove(DOMAIN, "select_stream")
    hass.services.async_remove(DOMAIN, "set_volume")
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)