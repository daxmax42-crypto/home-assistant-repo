# ISEEVY Video Decoder - Home Assistant Custom Component

Custom integration for **ISEEVY H.265/H.264 4K Video Decoder** (and compatible rebranded units) in Home Assistant.

## Features

- **Sensor entities** for:
  - Firmware version, MAC/IP addresses
  - Play status (Playing/No Signal/No Playing)
  - Current stream title and URL
  - Total configured streams (up to 30)
  - Video format, aspect ratio, language
  - Volume level
  - RTSP transport (TCP/UDP)
  - DHCP, Auto-reboot, Low-delay mode status
- **Number entity** for volume control (slider 0-100%)
- **Config flow** for easy setup via UI
- **Re-authentication** support when password changes
- **Local polling** - no cloud dependency

## Installation

### Option 1: HACS (Recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add this repository URL, category: **Integration**
3. Search for "ISEEVY Video Decoder" and install
4. Restart Home Assistant

### Option 2: Manual

1. Copy the `iseevy_decoder` folder to your `config/custom_components/` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration → Search "ISEEVY Video Decoder"

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for "ISEEVY Video Decoder"
3. Enter:
   - **Host**: IP address of your decoder (e.g., `10.0.100.245`)
   - **Username**: `admin` (default)
   - **Password**: Your web interface password
   - **Port**: `80` (default)
4. Submit - the integration will test the connection

## Entities Created

| Entity | Description |
|--------|-------------|
| `sensor.iseevy_decoder_firmware_version` | Firmware version + network info (diagnostic) |
| `sensor.iseevy_decoder_play_status` | Current play state |
| `sensor.iseevy_decoder_current_stream` | Currently selected stream title |
| `sensor.iseevy_decoder_stream_count` | Total configured streams |
| `sensor.iseevy_decoder_volume` | Volume level (0-100%) |
| `sensor.iseevy_decoder_video_format` | Output video format |
| `sensor.iseevy_decoder_rtsp_transport` | RTSP transport protocol |
| `sensor.iseevy_decoder_dhcp_enabled` | DHCP status |
| `sensor.iseevy_decoder_autoreboot_enabled` | Auto-reboot status |
| `sensor.iseevy_decoder_low_delay_mode` | Low delay mode status |
| `number.iseevy_decoder_volume` | Volume slider control (0-100%) |

## Stream Selection

The decoder supports up to 30 pre-configured RTSP streams. The current stream is exposed as a sensor with attributes:
- `stream_index`: 1-based index of current stream
- `stream_url`: RTSP URL of current stream

To change streams, use the **Developer Tools → Services** → `iseevy_decoder.select_stream` service (if implemented) or create a script/automation.

## Supported Devices

- ISEEVY H.265/H.264 4K/1080P Video Decoder
- Compatible rebrands using the same FalconAdmin web UI
- HiSilicon-based decoders with `/get.cgi` and `/getpro.cgi` endpoints

## API Endpoints Used

- `GET /get.cgi` - System information (XML)
- `GET /getpro.cgi` - Stream configuration (XML)
- `GET /setpro.cgi?pro=N` - Switch to stream N
- `GET /setvol.cgi?vol=N` - Set volume (0-100)

## Security Notes

- Credentials are stored encrypted in Home Assistant's config entry system
- No cloud connectivity - purely local LAN communication
- Uses HTTP Basic Auth (same as web UI)
- Recommend: Place decoder on isolated IoT VLAN

## Troubleshooting

**"Authentication failed"**
- Verify username/password match web UI login
- Default is `admin` / `admin` but you likely changed it

**"Cannot connect"**
- Verify IP address and port (default 80)
- Check firewall/VLAN rules
- Confirm device is powered and on network

**No entities showing**
- Check logs for `iseevy_decoder` errors
- Verify firmware version >= 2021050601 (tested)

## Development

```bash
# Install dev dependencies
pip install -e .[dev]

# Run tests
pytest tests/

# Lint
ruff check .
```

## License

MIT License - see LICENSE file

## Credits

- Based on reverse-engineering of FalconAdmin UI (netcoders.net)
- Compatible with HiSilicon-based video decoders
- Inspired by public research on ISEEVY/HiSilicon devices (2020 CVEs)

## Changelog

### 1.0.0
- Initial release
- Sensors for all system parameters
- Volume control via number entity
- Config flow with auth validation
- Re-authentication support