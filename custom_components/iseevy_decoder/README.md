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
- **Number entities** for volume + settings control (sliders/inputs)
- **Select entities** for stream + output settings (resolution, aspect, language, RTSP transport, TZ E/W)
- **Switch entities** for boolean settings (DHCP, low-latency, clock, auto-reboot, channel schedule)
- **Button entities**: Refresh Stream, Refresh Channel List, **Verify Real Channel** (netstat ground truth)
- **Services**: `iseevy_decoder.select_stream`, `iseevy_decoder.set_volume`, `iseevy_decoder.verify_channel`
- **Config flow** for easy setup via UI, with re-authentication support
- **Local polling** - no cloud dependency
- **Safe on-device writes**: volume/settings go through a telnet `/mnt/cfg.ini` edit (live-applied, no reboot). **Never** `/set.cgi` (it corrupts the device config). Channel switching uses `/setpro.cgi?playindex=N-1&end` (0-based).

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
   - **Username**: `admin`
   - **Password**: `0p3nd00r` (the live FalconAdmin web-UI password — NOT the dormant `admin`/`admin` .htpasswd)
   - **Port**: `80` (default)
4. Submit - the integration will test the connection

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.iseevy_decoder_firmware_version` | sensor | Firmware version (diagnostic) |
| `sensor.iseevy_decoder_play_status` | sensor | Play status (No Playing / No Signal / Playing) |
| `sensor.iseevy_decoder_video_format` | sensor | Output video format |
| `sensor.iseevy_decoder_aspect_ratio` | sensor | Aspect ratio |
| `sensor.iseevy_decoder_language` | sensor | Language (diagnostic) |
| `sensor.iseevy_decoder_rtsp_transport` | sensor | RTSP transport TCP/UDP (diagnostic) |
| `sensor.iseevy_decoder_ip_address` | sensor | IP (diagnostic) |
| `sensor.iseevy_decoder_mac_address` | sensor | MAC (diagnostic) |
| `sensor.iseevy_decoder_netmask` | sensor | Netmask (diagnostic) |
| `sensor.iseevy_decoder_gateway` | sensor | Gateway (diagnostic) |
| `sensor.iseevy_decoder_dns` | sensor | DNS (diagnostic) |
| `sensor.iseevy_decoder_volume` | sensor | Volume level (0-100%) |
| `sensor.iseevy_decoder_stream_count` | sensor | Total configured streams (diagnostic) |
| `sensor.iseevy_decoder_dhcp_enabled` | sensor | DHCP on/off (diagnostic) |
| `sensor.iseevy_decoder_autoreboot_enabled` | sensor | Auto-reboot on/off (diagnostic) |
| `sensor.iseevy_decoder_low_delay_mode` | sensor | Low-delay mode on/off (diagnostic) |
| `sensor.iseevy_decoder_last_verified_channel` | sensor | Last netstat/pro.ini-verified channel (ground truth) |
| `number.iseevy_decoder_volume` | number | Volume slider (telnet cfg.ini write) |
| `number.iseevy_decoder_timezone` | number | Time zone 0-12 |
| `number.iseevy_decoder_autoreboot_time` | number | Auto-reboot hour 0-23 |
| `number.iseevy_decoder_channel_schedule_time` | number | Channel schedule sec 0-59 |
| `number.iseevy_decoder_udp_video_buffer` | number | UDP video buffer 1-40M |
| `select.iseevy_decoder_active_stream` | select | Active stream (cached last selection — device can't report it) |
| `select.iseevy_decoder_output_resolution` | select | Output resolution (telnet cfg.ini write) |
| `select.iseevy_decoder_aspect_ratio` | select | Aspect ratio (telnet cfg.ini write) |
| `select.iseevy_decoder_language` | select | Language (telnet cfg.ini write) |
| `select.iseevy_decoder_rtsp_over_type` | select | RTSP transport (telnet cfg.ini write) |
| `select.iseevy_decoder_time_zone_ew` | select | Time zone E/W (telnet cfg.ini write) |
| `switch.iseevy_decoder_dhcp` | switch | DHCP (telnet cfg.ini write + **reboot**) |
| `switch.iseevy_decoder_multicast_low_latency` | switch | Multicast low latency (telnet cfg.ini write) |
| `switch.iseevy_decoder_clock` | switch | Clock / showtime (telnet cfg.ini write) |
| `switch.iseevy_decoder_schedule_to_reboot` | switch | Auto-reboot (telnet cfg.ini write) |
| `switch.iseevy_decoder_channel_schedule` | switch | Channel schedule (telnet cfg.ini write) |
| `button.iseevy_decoder_refresh_stream` | button | Force data refresh |
| `button.iseevy_decoder_refresh_channel_list` | button | Refresh channel-title list from /getpro.cgi |
| `button.iseevy_decoder_verify_real_channel` | button | Poll real channel via netstat + pro.ini |

## Stream Selection

The decoder supports up to 29 pre-configured RTSP streams. The **Active Stream** select shows
the last channel you requested (the device cannot report its real channel — `curplay_title` is a
constant). To learn the REAL current channel off-site, press **Verify Real Channel**; it reads
the live RTSP peer via `netstat` and disambiguates shared-host channels (e.g. `10.0.100.53` backs
ch2-4/17/28) using the decoder's own `/mnt/pro.ini`. Result lands in
`sensor.iseevy_decoder_last_verified_channel`.

Channels switch via the safe `GET /setpro.cgi?playindex=N-1&end` surface (0-based: channel N =
playindex N-1). Volume and settings write via a safe telnet `/mnt/cfg.ini` edit (live-applied, no
reboot) — **never `/set.cgi`** (it corrupts `cfg.ini` + `cfgbak.ini` and breaks video).

## Supported Devices

- ISEEVY H.265/H.264 4K/1080P Video Decoder
- Compatible rebrands using the same FalconAdmin web UI
- HiSilicon-based decoders with `/get.cgi` and `/getpro.cgi` endpoints

## API Endpoints Used

- `GET /get.cgi` - System information (XML)
- `GET /getpro.cgi` - Stream configuration (XML, reliable titles)
- `GET /setpro.cgi?playindex=N&end` - Switch to stream N (0-based; channel N = playindex N-1)
- Volume / settings writes: **telnet `root`/`unisheen` → edit `/mnt/cfg.ini`** (live-applied)
- **NOT used**: `/set.cgi` (corrupts cfg.ini), `/setvol.cgi` (404, does not exist)

## Security Notes

- Credentials are stored encrypted in Home Assistant's config entry system
- No cloud connectivity - purely local LAN communication
- Uses HTTP Basic Auth (same as web UI)
- Recommend: Place decoder on isolated IoT VLAN

## Troubleshooting

**"Authentication failed"**
- Verify username/password match web UI login (`admin` / `0p3nd00r`)
- Telnet writes use `root` / `unisheen`

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