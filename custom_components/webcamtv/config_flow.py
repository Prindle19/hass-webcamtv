"""Config flow: the appliance announces _webcamtv._tcp via mDNS, so Home
Assistant discovers it automatically; a manual host entry is the fallback."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

try:  # HA 2025+ location
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
except ImportError:  # older HA
    from homeassistant.components.zeroconf import ZeroconfServiceInfo

from .api import WebcamtvApi, WebcamtvError
from .const import DEFAULT_HOST, DEFAULT_NAME, DOMAIN


class WebcamtvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle discovery and manual setup of a webcamtv appliance."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._name: str = DEFAULT_NAME

    async def _fetch_status(self, host: str) -> dict:
        api = WebcamtvApi(host, async_get_clientsession(self.hass))
        return await api.status()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip().rstrip("/")
            try:
                status = await self._fetch_status(host)
            except WebcamtvError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(status.get("device_id") or host)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=status.get("name") or DEFAULT_NAME,
                    data={CONF_HOST: host},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=DEFAULT_HOST): str}),
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo):
        host = str(discovery_info.host)
        port = discovery_info.port or 80
        self._host = host if port == 80 else f"{host}:{port}"
        try:
            status = await self._fetch_status(self._host)
        except WebcamtvError:
            return self.async_abort(reason="cannot_connect")
        await self.async_set_unique_id(status.get("device_id") or self._host)
        # Already configured -> just track the (possibly new) IP, no new entry.
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})
        self._name = status.get("name") or DEFAULT_NAME
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title=self._name, data={CONF_HOST: self._host})
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": self._name, "host": self._host or ""},
        )
