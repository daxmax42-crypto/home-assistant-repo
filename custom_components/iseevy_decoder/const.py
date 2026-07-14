"""Constants for the ISEEVY Video Decoder integration."""

DOMAIN = "iseevy_decoder"

# Configuration keys
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PORT = "port"

# Defaults
DEFAULT_PORT = 80
DEFAULT_USERNAME = "admin"
# The device's TELNET console uses a DIFFERENT credential than its web UI.
# The web login (admin/0p3nd00r) logs into telnet but lands in a shell context
# where the CTRL-C app-console break does NOT detach — so pro.ini reads fail and
# verify_channel returns all-None. Telnet MUST use root/unisheen.
DEFAULT_TELNET_USERNAME = "root"
DEFAULT_TELNET_PASSWORD = "unisheen"
DEFAULT_SCAN_INTERVAL = 30  # seconds

# API Endpoints
ENDPOINT_GET = "/get.cgi"
ENDPOINT_GETPRO = "/getpro.cgi"

# XML Element Names (from get.cgi)
XML_SYSVERSION = "sysversion"
XML_BOX_IP = "box_ip"
XML_BOX_NETMASK = "box_netmask"
XML_BOX_GATEWAY = "box_gateway"
XML_BOX_DNS0 = "box_dns0"
XML_BOX_MAC = "box_mac"
XML_FORMAT_TYPE = "format_type"
XML_ASPECT = "aspect"
XML_LANGUAGE = "language"
XML_VOLUME = "volume"
XML_UDP_BUF = "udp_buf"
XML_NORMAL_BUF = "normal_buf"
XML_PLAYSTATUS = "playstatus"
XML_RTSP_OVER = "rtspover"
XML_DHCP = "dhcp"
XML_TIMEZONE = "timezone"
XML_TIMEZONE_EW = "timezone_ew"
XML_SHOWTIME = "showtime"
XML_AUTOREBOOT_STATUS = "autoreboot_status"
XML_AUTOREBOOT_TIME = "autoreboot_time"
XML_LUNBO_STATUS = "lunbo_status"
XML_LUNBO_TIME = "lunbo_time"
XML_LOWDELAY_MODE = "lowdelay_mode"

# XML Element Names (from getpro.cgi)
XML_CURPLAY_TITLE = "curplay_title"
XML_CURPLAY_URL = "curplay_url"
XML_TITLE_PREFIX = "title"
XML_URL_PREFIX = "url"

# Play Status Mapping
PLAY_STATUS_MAP = {
    "2": "Playing",
    "5": "No Signal",
    "6": "No Playing",
}

# Format Type Mapping
FORMAT_TYPE_MAP = {
    "0": "1080P60",
    "1": "1080P50",
    "2": "1080P25",
    "3": "1080I60",
    "4": "1080I50",
    "5": "720P60",
    "6": "720P50",
    "7": "576P",
    "8": "480P",
    "9": "576I",
    "10": "480I",
    "11": "720P5994",
    "12": "1080P2997",
    "13": "1080P5994",
    "14": "1080I5994",
    "15": "3840X2160_2997",
    "16": "3840X2160_30",
}

# Aspect Ratio Mapping
ASPECT_MAP = {
    "0": "4:3",
    "1": "16:9",
    "2": "Auto",
}

# Language Mapping
LANGUAGE_MAP = {
    "0": "Simplified Chinese",
    "1": "English",
}

# RTSP Over Mapping
RTSP_OVER_MAP = {
    "0": "TCP",
    "1": "UDP",
}

# Attributes
ATTR_STREAMS = "streams"
ATTR_CURRENT_STREAM = "current_stream"
ATTR_FIRMWARE_VERSION = "firmware_version"
ATTR_MAC_ADDRESS = "mac_address"
ATTR_IP_ADDRESS = "ip_address"
ATTR_NETMASK = "netmask"
ATTR_GATEWAY = "gateway"
ATTR_DNS = "dns"
ATTR_FORMAT = "video_format"
ATTR_ASPECT = "aspect_ratio"
ATTR_LANGUAGE = "language"
ATTR_VOLUME = "volume"
ATTR_PLAY_STATUS = "play_status"
ATTR_RTSP_TRANSPORT = "rtsp_transport"
ATTR_DHCP = "dhcp_enabled"
ATTR_TIMEZONE = "timezone"
ATTR_AUTOREBOOT = "autoreboot_enabled"
ATTR_LUNBO = "lunbo_enabled"

# Device Info
MANUFACTURER = "ISEEVY"
MODEL = "4K Video Decoder"
SW_VERSION = "2021050601"