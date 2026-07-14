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
from .telnet_client import ISEEVYTelnetClient

_LOGGER = logging.getLogger(__name__)


async def _raw_http_get(host: str, port: int, path: str, username: str, password: str, timeout: int = 10) -> tuple[int, dict[str, str], bytes]:
    """Perform raw HTTP GET request, handling malformed headers from ISEEVY decoder.

    The ISEEVY decoder returns invalid headers like 'Content- type: text/xml'
    (space after Content-) which aiohttp's strict parser rejects.
    This function reads raw HTTP response and parses headers leniently.
    """
    import base64

    # Create connection
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port),
        timeout=timeout
    )

    try:
        # Build request. NOTE: the device calls this header "Authorization: Basic ***"
        # ONLY in logged/echoed form — the real wire header must carry the credentials,
        # otherwise FalconAdmin returns 401 and every read fails.
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Authorization: Basic {auth}\r\n"
            f"Connection: close\r\n"
            f"User-Agent: HomeAssistant-ISEEVY/1.0.14\r\n"
            f"\r\n"
        )

        writer.write(request.encode())
        await writer.drain()

        # Read status line
        status_line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not status_line:
            raise aiohttp.ClientConnectorError("Empty response", None)

        status_line = status_line.decode('latin-1', errors='replace').strip()
        parts = status_line.split(' ', 2)
        if len(parts) < 2:
            raise aiohttp.ClientResponseError("Invalid status line", None)
        status_code = int(parts[1])

        # Read headers leniently
        headers = {}
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if not line or line == b'\r\n':
                break
            line = line.decode('latin-1', errors='replace').rstrip('\r\n')
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                # Fix malformed "Content- type" -> "Content-Type"
                if key == 'Content-':
                    key = 'Content-Type'
                headers[key.lower()] = value

        # Read body - handle both Content-Length and Transfer-Encoding: chunked
        body = b''
        transfer_encoding = headers.get('transfer-encoding', '').lower()

        if 'chunked' in transfer_encoding:
            # Handle chunked transfer encoding
            body = b''
            while True:
                # Read chunk size line
                chunk_line = await asyncio.wait_for(reader.readline(), timeout=timeout)
                if not chunk_line:
                    break
                chunk_line = chunk_line.decode('latin-1', errors='replace').strip()
                if not chunk_line:
                    continue
                try:
                    chunk_size = int(chunk_line, 16)
                except ValueError:
                    break
                if chunk_size == 0:
                    # Last chunk - read trailing CRLF
                    await reader.readline()
                    break
                # Read chunk data
                chunk_data = await asyncio.wait_for(reader.readexactly(chunk_size), timeout=timeout)
                body += chunk_data
                # Read trailing CRLF after chunk
                await reader.readline()
        else:
            # Handle Content-Length or read until EOF
            content_length = headers.get('content-length')
            if content_length:
                try:
                    length = int(content_length)
                    body = await asyncio.wait_for(reader.readexactly(length), timeout=timeout)
                except (ValueError, asyncio.IncompleteReadError):
                    body = await reader.read()
            else:
                # No content-length, read until EOF
                body = await reader.read()

        return status_code, headers, body

    finally:
        writer.close()
        await writer.wait_closed()


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
        # Safe telnet client for config writes (volume/settings) — never /set.cgi
        self.telnet = ISEEVYTelnetClient(host, username, password)

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session (kept for compatibility)."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, endpoint: str, params: dict[str, str] | None = None) -> str:
        """Make HTTP request using raw socket to handle malformed headers."""
        url = f"{self._base_url}{endpoint}"
        if params:
            query = '&'.join(f"{k}={v}" for k, v in params.items())
            path = f"{endpoint}?{query}"
        else:
            path = endpoint

        try:
            status_code, headers, body = await _raw_http_get(
                self.host, self.port, path, self.username, self.password
            )

            if status_code == 401:
                raise ISEEVYAuthError("Authentication failed")
            if status_code == 404:
                raise ISEEVYAPIError(f"Endpoint not found: {endpoint}")
            if status_code >= 400:
                raise ISEEVYAPIError(f"HTTP {status_code}: {body.decode('utf-8', errors='replace')}")

            # Decode body
            text = body.decode('utf-8', errors='replace')
            return text

        except asyncio.TimeoutError as err:
            raise ISEEVYConnectionError(f"Timeout: {err}") from err
        except (ConnectionError, OSError) as err:
            raise ISEEVYConnectionError(f"Connection failed: {err}") from err

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
                    # Note: curplay_title is UNRELIABLE (always returns "1")
                    # Mark as current only if we have external confirmation
                    "is_current": False,
                })
            i += 1

        return {
            "streams": streams,
            # curplay_title is UNRELIABLE - always returns "1" (Sunba Main)
            # Do not trust it for current stream detection
            "current_stream_index": None,
            "current_stream_url": current_url,
        }

    async def set_stream(self, stream_index: int) -> bool:
        """Switch to a specific stream by index (1-based)."""
        if not 1 <= stream_index <= 30:
            raise ValueError("Stream index must be 1-30")

        # Device API uses 0-indexed playindex internally, but XML titles are 1-indexed
        # Subtract 1 for the API call
        api_index = stream_index - 1

        # Correct endpoint format: /setpro.cgi?playindex=N&end (0-based)
        # NOT /setpro.cgi?pro=N (doesn't work), and NEVER /set.cgi (corrupts cfg.ini).
        await self._request("/setpro.cgi", params={"playindex": str(api_index), "end": ""})
        return True

    async def select_stream(self, stream_index: int) -> bool:
        """Switch to a specific stream by index (1-based). Alias for set_stream."""
        return await self.set_stream(stream_index)

    async def set_volume(self, volume: int) -> bool:
        """Set volume SAFELY via telnet cfg.ini edit (NOT /set.cgi — it corrupts device)."""
        if not 0 <= volume <= 100:
            raise ValueError("Volume must be 0-100")
        try:
            await self.telnet.connect()
            await self.telnet.set_cfg_field("volume", str(volume))
            return True
        except OSError as err:
            raise ISEEVYAPIError(f"Telnet volume set failed: {err}") from err
        finally:
            await self.telnet.close()

    async def verify_channel(self) -> dict[str, object]:
        """Determine the REAL current channel via ground truth (not the unreliable curplay_title).

        Method (per embedded-device-truth-verification skill):
          1. Read the ESTABLISHED RTSP peer IP from netstat (which stream is wired).
          2. Read /mnt/pro.ini (app OUTPUT file) — its curplay_url/curplay_title are the
             decoder's own record of the live stream and disambiguate hosts that back multiple
             channels (10.0.100.53 -> ch2/3/4/17/28; 10.0.100.54 -> ch14/15/25/26).
          3. Match the pro.ini curplay_url against the configured stream URLs.

        Returns {"peer_ip", "index", "title", "verified_via"}. If the peer is on a shared host
        and pro.ini match succeeds, verified_via="pro.ini"; otherwise "netstat" (ambiguous on
        shared hosts) or None.
        """
        try:
            await self.telnet.connect()
            peer = await self.telnet.get_rtsp_peer()
            if not peer:
                return {
                    "peer_ip": None,
                    "index": None,
                    "title": None,
                    "verified_via": None,
                }
            streams_data = await self.get_streams()
            streams = streams_data.get("streams", [])
            # Primary: pro.ini curplay_url is the device's own ground truth for the live stream.
            pro = await self.telnet.read_pro_ini()
            cur_url = None
            cur_title = None
            for ln in pro.splitlines():
                if ln.startswith("curplay_url="):
                    cur_url = ln.split("=", 1)[1].strip()
                elif ln.startswith("curplay_title="):
                    cur_title = ln.split("=", 1)[1].strip()
            if cur_url:
                for s in streams:
                    if s.get("url", "") and s["url"].strip() == cur_url:
                        return {
                            "peer_ip": peer,
                            "index": s["index"],
                            "title": s["title"],
                            "verified_via": "pro.ini",
                        }
            # Fallback: netstat peer IP -> first stream whose URL host matches.
            for s in streams:
                url = s.get("url", "")
                host = re.search(r"rtsp://[^@]*@?([\d.]+):", url) or re.search(
                    r"//([\d.]+):", url
                )
                if host and host.group(1) == peer:
                    return {
                        "peer_ip": peer,
                        "index": s["index"],
                        "title": s["title"],
                        "verified_via": "netstat",
                    }
            # Peer known but no stream matched (e.g. transient / unknown host).
            return {
                "peer_ip": peer,
                "index": None,
                "title": cur_title,
                "verified_via": "netstat",
            }
        except OSError as err:
            raise ISEEVYAPIError(f"Telnet verify failed: {err}") from err
        finally:
            await self.telnet.close()

    async def set_setting(self, field: str, value: str, reboot: bool = False) -> bool:
        """Safe config write: edit one cfg.ini field (live-applied, no reboot needed).

        NEVER /set.cgi (it corrupts the device). cfg.ini changes apply live — verified:
        get.cgi reflects the new value immediately and the UI updates without reboot.
        Pass reboot=True ONLY for settings the app reads solely at boot (e.g. dhcp /
        box_ip / box_netmask / box_gateway / box_dns0 network changes).

        field examples: 'format_type', 'aspect', 'language', 'rtspover',
        'lowdelay_mode', 'showtime', 'timezone', 'timezone_ew',
        'autoreboot_status', 'autoreboot_time', 'lunbo_status', 'lunbo_time', 'udp_buf'.
        """
        try:
            await self.telnet.connect()
            await self.telnet.set_cfg_field(field, value, reboot=reboot)
            return True
        except OSError as err:
            raise ISEEVYAPIError(f"Telnet setting set failed: {err}") from err
        finally:
            await self.telnet.close()

    async def get_all_data(self) -> dict[str, Any]:
        """Get all data in one call."""
        system_info = await self.get_system_info()
        streams_data = await self.get_streams()
        return {**system_info, **streams_data}