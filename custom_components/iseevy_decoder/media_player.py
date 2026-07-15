"""Media player platform for ISEEVY Video Decoder — Alexa/Google/Assist voice control.

WHY THIS EXISTS
---------------
Amazon Alexa does NOT support Home Assistant `select` entities (the entity page shows
"Unsupported"). It DOES support `media_player` with a channel/input source list. So
this entity is the Alexa-compatible voice surface for changing the decoder channel:

  * "Alexa, change the channel to 3camWest2"  -> select_source(title)      (by TITLE)
  * "Alexa, change the input to 3camWest2"    -> select_source(title)
  * "Alexa, play channel 3"                   -> play_media(channel=3)     (by NUMBER)

Google Assistant and Assist can use this media_player OR the existing `select` entity.
The decoder has no real play/pause/volume-over-HDMI semantics, so we only implement the
channel/input surface (source_list, select_source, play_media). Volume stays on the
number entity.

Title-list awareness: `source_list` is derived from the coordinator's live streams, and
the Refresh Channel List button now pushes immediately (coordinator.async_refresh_channel_list),
so renamed/added titles become voice-addressable as soon as HA re-syncs the entity.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_CHANNEL,
    MediaPlayerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ISEEVYDataUpdateCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL, SW_VERSION

_LOGGER = logging.getLogger(__name__)

# Features we expose: change channel by source (title) and by media (number).
_SUPPORT = (
    MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.PLAY_MEDIA
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ISEEVY media player entity."""
    coordinator: ISEEVYDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ISEEVYMediaPlayer(coordinator, entry)])


class ISEEVYMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    """Media player entity exposing decoder channels as Alexa-compatible sources."""

    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = _SUPPORT

    def __init__(self, coordinator: ISEEVYDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_media_player"
        self._attr_name = "Decoder"
        self._attr_icon = "mdi:television"
        # The device is always "on" (it's a decoder); Alexa needs powered-on state.
        self._attr_state = "on"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ISEEVY Decoder ({entry.data['host']})",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=SW_VERSION,
            configuration_url=f"http://{entry.data['host']}",
        )

    @property
    def source_list(self) -> list[str] | None:
        """All configured stream titles — the voice channel/input list."""
        if not self.coordinator.data:
            return None
        streams = self.coordinator.data.get("streams", [])
        return [s["title"] for s in streams if s.get("title")]

    @property
    def source(self) -> str | None:
        """Currently selected stream title (mirrors the Active Stream select)."""
        if not self.coordinator.data:
            return None
        streams = self.coordinator.data.get("streams", [])
        idx = self.coordinator.data.get("last_selected_stream")
        if idx and 1 <= idx <= len(streams):
            return streams[idx - 1].get("title")
        return None

    async def async_select_source(self, source: str) -> None:
        """Change channel by TITLE (voice: "change the channel to <title>")."""
        success = await self.coordinator.async_select_stream_by_name(source)
        if not success:
            _LOGGER.error("Failed to select source %r", source)

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        """Change channel by NUMBER (voice: "play channel <n>").

        Accepts media_type "channel" with media_id being the 1-based channel number,
        or a bare number string. Also accepts a title as a fallback.
        """
        media_id = str(media_id).strip()
        if media_type == MEDIA_TYPE_CHANNEL or media_type in (None, ""):
            # Try to parse as a channel number first.
            try:
                idx = int(media_id)
                success = await self.coordinator.async_select_stream(idx)
                if success:
                    return
                # If the number didn't map (out of range), fall through to name match.
            except ValueError:
                pass
        # Fallback: treat media_id as a title.
        success = await self.coordinator.async_select_stream_by_name(media_id)
        if not success:
            _LOGGER.error("Failed to play media %r (type=%r)", media_id, media_type)
