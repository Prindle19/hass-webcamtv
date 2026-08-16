"""The webcamtv appliance as a media_player entity.

Sources are the appliance's playlists (listed first — they're the primary way
to drive it) plus every individual camera. Transport controls map to the
player's real modes: pause freezes the current camera, play rejoins the live
edge, stop blanks the screen, selecting a camera pins it, selecting a playlist
resumes cycling.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CAMERA_SOURCE_PREFIX, DEFAULT_NAME, DOMAIN
from .coordinator import WebcamtvCoordinator

PLAYLIST_ID = "playlist:"
CAMERA_ID = "camera:"
CAMERA_GROUP_ID = "cameras:"

# Same grouping as the appliance's admin UI: beach cams by state (this order),
# anything unknown under Other, and Camelback Resort as its own group.
STATE_GROUPS = [
    ("NJ", "New Jersey"),
    ("NC", "North Carolina"),
    ("VA", "Virginia"),
    ("SC", "South Carolina"),
    ("MD", "Maryland"),
    ("OR", "Oregon"),
    ("FL", "Florida"),
    ("NY", "New York"),
]


def _camera_groups(cameras: list[dict]) -> list[tuple[str, str, list[dict]]]:
    """Ordered [(content_id, label, cameras)], alphabetical within each group."""

    def is_camelback(cam: dict) -> bool:
        provider = cam.get("provider")
        if provider is not None:
            return provider == "wetmet"
        return cam.get("state") == "PA"  # pre-1.1.1 appliances omit provider

    by_name = lambda cam: cam.get("name", "")
    beach = [c for c in cameras if not is_camelback(c)]
    known = {abbr for abbr, _ in STATE_GROUPS}
    groups = []
    for abbr, label in STATE_GROUPS:
        cams = sorted((c for c in beach if c.get("state") == abbr), key=by_name)
        if cams:
            groups.append((CAMERA_GROUP_ID + abbr, label, cams))
    other = sorted((c for c in beach if c.get("state") not in known), key=by_name)
    if other:
        groups.append((CAMERA_GROUP_ID + "other", "Other", other))
    camelback = sorted((c for c in cameras if is_camelback(c)), key=by_name)
    if camelback:
        groups.append((CAMERA_GROUP_ID + "camelback", "Camelback Resort", camelback))
    return groups


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WebcamtvCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WebcamtvMediaPlayer(coordinator, entry)])


class WebcamtvMediaPlayer(CoordinatorEntity[WebcamtvCoordinator], MediaPlayerEntity):
    """One entity per appliance; it carries the device's name."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.BROWSE_MEDIA
        | MediaPlayerEntityFeature.PLAY_MEDIA
    )

    def __init__(self, coordinator: WebcamtvCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        status = coordinator.data["status"]
        self._attr_unique_id = entry.unique_id or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=entry.title or DEFAULT_NAME,
            manufacturer="webcamtv",
            model="Raspberry Pi webcam appliance",
            sw_version=status.get("version") or None,
            configuration_url=f"{coordinator.api.base_url}/admin",
        )

    # ---- state ----

    @property
    def _status(self) -> dict:
        return self.coordinator.data["status"]

    @property
    def _cameras(self) -> list[dict]:
        return self.coordinator.data["cameras"]

    @property
    def state(self) -> MediaPlayerState:
        return {
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
        }.get(self._status.get("state"), MediaPlayerState.IDLE)

    @property
    def media_content_type(self) -> MediaType | None:
        return MediaType.VIDEO if self._status.get("camera") else None

    @property
    def media_title(self) -> str | None:
        cam = self._status.get("camera")
        return cam.get("name") if cam else None

    @property
    def source(self) -> str | None:
        cam = self._status.get("camera")
        if self._status.get("mode") == "pinned" and cam:
            return CAMERA_SOURCE_PREFIX + cam.get("name", "")
        return self._status.get("active_playlist")

    @property
    def source_list(self) -> list[str]:
        playlists = list(self._status.get("playlists") or [])
        cameras = [CAMERA_SOURCE_PREFIX + c["name"] for c in self._cameras]
        return playlists + cameras

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cam = self._status.get("camera") or {}
        return {
            "mode": self._status.get("mode"),
            "active_playlist": self._status.get("active_playlist"),
            "camera_id": cam.get("id"),
        }

    # ---- commands ----

    async def async_media_play(self) -> None:
        await self.coordinator.api.command("play")
        await self.coordinator.async_request_refresh()

    async def async_media_pause(self) -> None:
        await self.coordinator.api.command("pause")
        await self.coordinator.async_request_refresh()

    async def async_media_stop(self) -> None:
        await self.coordinator.api.command("stop")
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        if source.startswith(CAMERA_SOURCE_PREFIX):
            name = source[len(CAMERA_SOURCE_PREFIX):]
            cam = next((c for c in self._cameras if c["name"] == name), None)
            if cam:
                await self.coordinator.api.play_camera(cam["id"])
        elif source in (self._status.get("playlists") or []):
            await self.coordinator.api.set_playlist(source)
        await self.coordinator.async_request_refresh()

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        if media_id.startswith(PLAYLIST_ID):
            await self.coordinator.api.set_playlist(media_id[len(PLAYLIST_ID):])
        elif media_id.startswith(CAMERA_ID):
            await self.coordinator.api.play_camera(media_id[len(CAMERA_ID):])
        elif media_id in (self._status.get("playlists") or []):
            await self.coordinator.api.set_playlist(media_id)
        else:
            await self.coordinator.api.play_camera(media_id)
        await self.coordinator.async_request_refresh()

    # ---- media browser ----

    async def async_browse_media(
        self, media_content_type: str | None = None, media_content_id: str | None = None
    ) -> BrowseMedia:
        if media_content_id == "playlists":
            return _folder(
                "playlists",
                "Playlists",
                [
                    _leaf(PLAYLIST_ID + name, name, MediaClass.PLAYLIST)
                    for name in (self._status.get("playlists") or [])
                ],
            )
        if media_content_id == "cameras":
            return _folder(
                "cameras",
                "Cameras",
                [
                    _folder(group_id, label, None)
                    for group_id, label, _ in _camera_groups(self._cameras)
                ],
            )
        if media_content_id and media_content_id.startswith(CAMERA_GROUP_ID):
            for group_id, label, cams in _camera_groups(self._cameras):
                if group_id == media_content_id:
                    return _folder(
                        group_id,
                        label,
                        [
                            _leaf(CAMERA_ID + c["id"], c["name"], MediaClass.VIDEO)
                            for c in cams
                        ],
                    )
        return _folder(
            "root",
            self._status.get("name") or DEFAULT_NAME,
            [
                _folder("playlists", "Playlists", None),
                _folder("cameras", "Cameras", None),
            ],
        )


def _folder(content_id: str, title: str, children: list[BrowseMedia] | None) -> BrowseMedia:
    return BrowseMedia(
        title=title,
        media_class=MediaClass.DIRECTORY,
        media_content_id=content_id,
        media_content_type="",
        can_play=False,
        can_expand=True,
        children=children,
    )


def _leaf(content_id: str, title: str, media_class: MediaClass) -> BrowseMedia:
    return BrowseMedia(
        title=title,
        media_class=media_class,
        media_content_id=content_id,
        media_content_type=MediaType.VIDEO,
        can_play=True,
        can_expand=False,
    )
