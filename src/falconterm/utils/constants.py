"""Project-wide constants."""

from __future__ import annotations

APP_NAME = "FalconTerm"
APP_ID = "FalconTerm"  # Used for platformdirs and keyring service name
CONFIG_VERSION = 1

DEFAULT_FONT_FAMILY = "Menlo"
DEFAULT_FONT_SIZE = 13
DEFAULT_ROWS = 24
DEFAULT_COLS = 80
DEFAULT_SCROLLBACK = 5000
DEFAULT_ENCODING = "utf-8"
DEFAULT_PROTOCOL = "ssh"
DEFAULT_SSH_PORT = 22
DEFAULT_TELNET_PORT = 23

# Terminal widget render budget
PAINT_FRAME_MS = 16  # ~60 FPS batch window
GLYPH_CACHE_CAP = 8192

# Sidebar defaults
SIDEBAR_MIN_WIDTH = 180
SIDEBAR_DEFAULT_WIDTH = 240

# Window defaults
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 560

# File extensions / filters
BUNDLE_EXTENSION = ".ftsessions"

# Logging
LOG_FLUSH_INTERVAL_SEC = 2.0
LOG_BUFFER_BYTES = 8192
