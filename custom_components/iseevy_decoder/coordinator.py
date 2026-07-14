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
        # Cache last selected stream since device can't report it reliably
        self._last_selected_stream: int | None = None
        self._last_verified: dict[str, object] = {
            "peer_ip": None,
            "index": None,
            "title": None,
        }
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    @property
    def last_selected_stream(self) -> int | None:
        """Return the last selected stream index (1-based)."""
        return self._last_selected_stream

    def set_last_selected_stream(self, stream_index: int) -> None:
        """Cache the last selected stream index."""
        self._last_selected_stream = stream_index

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            data = await self.client.get_all_data()
            # Add cached last selected stream to data for select entity
            data["last_selected_stream"] = self._last_selected_stream
            # Add last netstat-verified channel (off-site ground truth)
            data["last_verified_channel"] = self._last_verified
            return data
        except ISEEVYAPIError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_set_volume(self, volume: int) -> bool:
        """Set volume on the decoder (safe telnet cfg.ini write). Push update immediately."""
        try:
            await self.client.set_volume(volume)
        except ISEEVYAPIError as err:
            _LOGGER.error("Failed to set volume: %s", err)
            return False
        # Push immediately so number/volume sensor update on HA 2026.x
        # (async_request_refresh is coalesced with the scheduled poll and the write
        #  never propagates; async_set_updated_data forces an immediate push).
        if self.data:
            current = dict(self.data)
            current["volume"] = volume
            self.async_set_updated_data(current)
        return True

    async def async_verify_channel(self) -> dict[str, object]:
        """Poll real channel via netstat (ground truth).

        Updates `last_verified_channel` AND the dropdown's cached selection (so the
        Active Stream dropdown reflects the verified channel) WITHOUT triggering a
        channel change (no setpro.cgi call).
        """
        try:
            result = await self.client.verify_channel()
        except ISEEVYAPIError as err:
            _LOGGER.error("Verify channel failed: %s", err)
            return {"peer_ip": None, "index": None, "title": None}
        self._last_verified = result
        idx = result.get("index")
        if isinstance(idx, int):
            # Reflect verified channel in the dropdown without a setpro.cgi call
            self._last_selected_stream = idx
        # Push immediately so the Last Verified Channel sensor + dropdown update NOW.
        # On HA 2026.x async_request_refresh() is coalesced with the scheduled poll and
        # the verify result never propagates; async_set_updated_data forces a push.
        if self.data:
            current = dict(self.data)
            current["last_verified_channel"] = self._last_verified
            current["last_selected_stream"] = self._last_selected_stream
            self.async_set_updated_data(current)
        else:
            # First refresh hasn't completed; cached values surface on next poll.
            await self.async_request_refresh()
        return result

    async def async_set_setting(self, field: str, value: str, reboot: bool = False) -> bool:
        """Set a decoder config field safely (telnet cfg.ini edit, live-applied, no reboot).
        Pass reboot=True only for network/DHCP settings the app reads at boot."""
        try:
            return await self.client.set_setting(field, value)
        except ISEEVYAPIError as err:
            _LOGGER.error("Set setting %s=%s failed: %s", field, value, err)
            return False

    @property
    def last_verified_channel(self) -> dict[str, object]:
        """Last netstat-verified channel (off-site ground truth)."""
        return self._last_verified


    async def async_select_stream(self, stream_index: int) -> bool:
        """Select a stream on the decoder. Push updated selection immediately."""
        try:
            await self.client.select_stream(stream_index)
        except ISEEVYAPIError as err:
            _LOGGER.error("Failed to select stream: %s", err)
            return False
        # Cache the selection since device can't report current stream
        self._last_selected_stream = stream_index
        # Push immediately so the Active Stream dropdown updates on HA 2026.x
        if self.data:
            current = dict(self.data)
            current["last_selected_stream"] = self._last_selected_stream
            self.async_set_updated_data(current)
        else:
            await self.async_request_refresh()
        return True

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