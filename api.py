"""API Client for ISEEVY Video Decoder."""

import asyncio
import logging
import re
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp

from .const import (
    ENDPOINT_GET,
    ENDPOINT_GETPRO,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    PLAY_STATUS_MAP,
    FORMAT_TYPE_MAP,
    ASPECT_MAP,
    LANGUAGE_MAP,
    RTSP_OVER_MAP,
)

_LOGGER = logging.getLogger(__name__)


class ISEEVYAPIError(Exception):
    """Base exception for ISEEVY API errors."""
    pass


class ISEEVYAuthError(ISEEVYAPIError):
    """Authentication failed."""
    pass


class ISEEVYConnectionError(ISEEVYAPIError):
    """Connection failed."""
    pass


class ISEEVYClient:
    """Client for communicating with ISEEVY Video Decoder."""

    def __init__(
        self,
        host: str,
        username: str = DEFAULT_USERNAME,
        password: str = "",
        port: int = DEFAULT_PORT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self._session = session
        self._base_url = f"http://{host}:{port}"

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, endpoint: str, params: dict[str, str] | None = None) -> str:
        """Make HTTP request with basic auth."""
        url = f"{self._base_url}{endpoint}"
        auth = aiohttp.BasicAuth(self.username, self.password)

        try:
            async with self.session.get(url, auth=auth, params=params) as response:
                if response.status == 401:
                    raise ISEEVYAuthError("Authentication failed")
                if response.status == 404:
                    raise ISEEVYAPIError(f"Endpoint not found: {endpoint}")
                if response.status >= 400:
                    raise ISEEVYAPIError(f"HTTP {response.status}: {await response.text()}")
                
                text = await response.text()
                return text
        except aiohttp.ClientConnectorError as err:
            raise ISEEVYConnectionError(f"Connection failed: {err}") from err
        except asyncio.TimeoutError as err:
            raise ISEEVYConnectionError(f"Timeout: {err}") from err

    def _parse_xml(self, xml_text: str) -> dict[str, Any]:
        """Parse XML response into dict."""
        # Strip chunked encoding artifacts if present
        xml_text = xml_text.strip()
        # Remove leading chunk size if present (e.g., "2d0\r\n")
        xml_text = re.sub(r'^[0-9a-fA-F]+\r\n', '', xml_text)
        # Remove trailing chunk terminator if present (e.g., "\r\n0\r\n")
        xml_text = re.sub(r'\r\n0\r\n$', '', xml_text)

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            _LOGGER.debug("XML parse error: %s, text: %s", err, xml_text[:500])
            raise ISEEVYAPIError(f"Invalid XML response: {err}") from err

        result = {}
        for child in root:
            result[child.tag] = child.text
        return result

    async def test_connection(self) -> bool:
        """Test if we can connect and authenticate."""
        try:
            await self.get_system_info()
            return True
        except ISEEVYAuthError:
            return False
        except ISEEVYAPIError:
            return False

    async def get_system_info(self) -> dict[str, Any]:
        """Get system information from /get.cgi."""
        xml_text = await self._request(ENDPOINT_GET)
        data = self._parse_xml(xml_text)

        # Transform and map values
        return {
            "firmware_version": data.get("sysversion", "Unknown"),
            "ip_address": data.get("box_ip", "Unknown"),
            "netmask": data.get("box_netmask", "Unknown"),
            "gateway": data.get("box_gateway", "Unknown"),
            "dns": data.get("box_dns0", "Unknown"),
            "mac_address": data.get("box_mac", "Unknown"),
            "video_format": FORMAT_TYPE_MAP.get(data.get("format_type", ""), data.get("format_type", "Unknown")),
            "aspect_ratio": ASPECT_MAP.get(data.get("aspect", ""), data.get("aspect", "Unknown")),
            "language": LANGUAGE_MAP.get(data.get("language", ""), data.get("language", "Unknown")),
            "volume": int(data.get("volume", 0)),
            "play_status": PLAY_STATUS_MAP.get(data.get("playstatus", ""), data.get("playstatus", "Unknown")),
            "rtsp_transport": RTSP_OVER_MAP.get(data.get("rtspover", ""), data.get("rtspover", "Unknown")),
            "dhcp_enabled": data.get("dhcp") == "1",
            "timezone": data.get("timezone", "Unknown"),
            "timezone_ew": data.get("timezone_ew", "Unknown"),
            "showtime_enabled": data.get("showtime") == "1",
            "autoreboot_enabled": data.get("autoreboot_status") == "1",
            "autoreboot_time": data.get("autoreboot_time", "Unknown"),
            "lunbo_enabled": data.get("lunbo_status") == "1",
            "lunbo_time": data.get("lunbo_time", "Unknown"),
            "lowdelay_mode": data.get("lowdelay_mode") == "1",
            "udp_buffer": data.get("udp_buf", "Unknown"),
            "normal_buffer": data.get("normal_buf", "Unknown"),
        }

    async def get_streams(self) -> dict[str, Any]:
        """Get configured streams from /getpro.cgi."""
        xml_text = await self._request(ENDPOINT_GETPRO)
        data = self._parse_xml(xml_text)

        streams = []
        current_title = data.get("curplay_title", "")
        current_url = data.get("curplay_url", "")

        # Find all title/url pairs (title1/url1, title2/url2, ...)
        i = 1
        while True:
            title_key = f"title{i}"
            url_key = f"url{i}"

            if title_key not in data and url_key not in data:
                break

            title = data.get(title_key, "")
            url = data.get(url_key, "")

            if title or url:
                streams.append({
                    "index": i,
                    "title": title,
                    "url": url,
                    "is_current": str(i) == current_title,
                })
            i += 1

        return {
            "streams": streams,
            "current_stream_index": int(current_title) if current_title.isdigit() else None,
            "current_stream_url": current_url,
        }

    async def set_stream(self, stream_index: int) -> bool:
        """Switch to a specific stream by index (1-based)."""
        if not 1 <= stream_index <= 30:
            raise ValueError("Stream index must be 1-30")

        # Try common set stream endpoints
        for endpoint in ["/setpro.cgi", "/set.cgi"]:
            try:
                await self._request(endpoint, params={"pro": str(stream_index)})
                return True
            except ISEEVYAPIError:
                continue
        
        raise ISEEVYAPIError(f"Failed to set stream to {stream_index}")

    async def set_volume(self, volume: int) -> bool:
        """Set volume (0-100)."""
        if not 0 <= volume <= 100:
            raise ValueError("Volume must be 0-100")

        # Try common set volume endpoints
        for endpoint in ["/setvol.cgi", "/set.cgi"]:
            try:
                await self._request(endpoint, params={"vol": str(volume)})
                return True
            except ISEEVYAPIError:
                continue
        
        raise ISEEVYAPIError(f"Failed to set volume to {volume}")

    async def get_all_data(self) -> dict[str, Any]:
        """Get all data in one call."""
        system_info = await self.get_system_info()
        streams_data = await self.get_streams()
        return {**system_info, **streams_data}