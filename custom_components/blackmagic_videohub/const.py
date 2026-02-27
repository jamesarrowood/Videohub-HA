from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "blackmagic_videohub"

DEFAULT_NAME = "Blackmagic Videohub"
DEFAULT_PORT = 9990
DEFAULT_SCAN_INTERVAL_SECONDS = 30
DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS)

CONF_SCAN_INTERVAL = "scan_interval"

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.MEDIA_PLAYER]

SERVICE_ROUTE_OUTPUT = "route_output"

ATTR_ENTRY_ID = "entry_id"
ATTR_OUTPUT = "output"
ATTR_INPUT = "input"
