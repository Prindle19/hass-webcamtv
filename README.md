# webcamtv for Home Assistant

Home Assistant integration for the **webcamtv appliance** — a Raspberry Pi
that boots straight into a rotating wall of live webcam streams (Jersey Shore
surf cams, ski slopes, boardwalks, …) on a TV or monitor.

The appliance announces itself on your LAN over mDNS (`_webcamtv._tcp`), so
once this integration is installed, Home Assistant discovers it automatically
and creates a **media player device**:

- **State** — `playing` / `paused` / `idle`, with the camera currently on
  screen as the media title.
- **Sources** — the appliance's playlists (listed first), then every
  individual camera (prefixed 🎥). Picking a playlist starts cycling it;
  picking a camera pins it on screen.
- **Transport** — play / pause / stop. Pause freezes the picture and the
  rotation timer; play rejoins the live edge; stop blanks the screen.
- **Media browser** — *Playlists* and *Cameras* folders, built live from the
  device, so new playlists and cameras appear on their own.

## Install

**HACS:** HACS → Integrations → ⋮ → *Custom repositories* → add this repo's
URL with category *Integration* → install **webcamtv** → restart Home
Assistant.

**Manual:** copy `custom_components/webcamtv/` into your Home Assistant
`config/custom_components/` directory and restart.

After the restart, Settings → Devices & Services shows **webcamtv
discovered** — click *Configure* and confirm. If no card appears, use *Add
Integration → webcamtv* and enter the device's **IP address** (from your
router, or `ping webcamtv.local` on a laptop). Many Home Assistant installs
run in a container that can't resolve `.local` mDNS names, so entering
`webcamtv.local` there may fail with "Could not reach the appliance" even
though the device is online.

## Automations

Everything goes through standard `media_player` services:

```yaml
action:
  - service: media_player.select_source
    target: { entity_id: media_player.webcamtv }
    data: { source: "Boardwalks" }
```

The entity exposes `mode` (`cycling` / `pinned` / `stopped`),
`active_playlist`, and `camera_id` attributes for conditions.

## Requirements

A webcamtv appliance on the same LAN, running appliance software **v1.1.0 or
newer** (older builds lack the transport API and mDNS announcement).
