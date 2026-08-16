"""Constants for the webcamtv integration."""

DOMAIN = "webcamtv"
DEFAULT_NAME = "webcamtv"
DEFAULT_HOST = "webcamtv.local"

# How often to poll the appliance's /api/status (local LAN, cheap).
SCAN_INTERVAL_SECS = 5

# Sources are playlists first (the primary way to drive the device), then
# individual cameras, prefixed so a camera can't collide with a playlist name.
CAMERA_SOURCE_PREFIX = "\U0001F3A5 "  # 🎥
