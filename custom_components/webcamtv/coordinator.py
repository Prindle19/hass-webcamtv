"""Polling coordinator: one status + camera-list fetch per interval."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WebcamtvApi, WebcamtvError
from .const import DOMAIN, SCAN_INTERVAL_SECS

_LOGGER = logging.getLogger(__name__)


class WebcamtvCoordinator(DataUpdateCoordinator[dict]):
    """Holds {"status": {...}, "cameras": [...]} refreshed from the appliance."""

    def __init__(self, hass: HomeAssistant, api: WebcamtvApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECS),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            status = await self.api.status()
            cameras = await self.api.cameras()
        except WebcamtvError as err:
            raise UpdateFailed(str(err)) from err
        return {"status": status, "cameras": cameras}
