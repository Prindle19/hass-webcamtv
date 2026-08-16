"""Thin async client for the webcamtv appliance's REST API."""
from __future__ import annotations

from typing import Any

import aiohttp


class WebcamtvError(Exception):
    """The appliance is unreachable or returned an error."""


class WebcamtvApi:
    """Talks to the appliance (http://webcamtv.local by default)."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        host = host.strip().rstrip("/")
        self._base = host if host.startswith("http") else f"http://{host}"
        self._session = session

    @property
    def base_url(self) -> str:
        return self._base

    async def _request(self, method: str, path: str, payload: dict | None = None) -> Any:
        try:
            async with self._session.request(
                method,
                f"{self._base}{path}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                if resp.status >= 400:
                    raise WebcamtvError(f"{path} -> HTTP {resp.status}")
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise WebcamtvError(f"{path} -> {err}") from err

    async def status(self) -> dict:
        """State + playlists: {device_id, name, state, mode, camera, ...}."""
        return await self._request("GET", "/api/status")

    async def cameras(self) -> list[dict]:
        """All known cameras: [{id, name, state}, ...]."""
        return await self._request("GET", "/api/cameras")

    async def set_playlist(self, name: str) -> None:
        """Switch the active playlist (starts cycling it)."""
        await self._request("POST", "/api/playlist", {"name": name})

    async def play_camera(self, camera_id: str) -> None:
        """Pin one camera (pauses cycling until a playlist is applied)."""
        await self._request("POST", "/api/play", {"id": camera_id})

    async def command(self, command: str) -> None:
        """Transport control: play | pause | stop."""
        await self._request("POST", "/api/command", {"command": command})
