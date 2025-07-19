"""Provides an interface to the Home Assistant Supervisor API."""
import logging
import os

import aiohttp

_LOGGER = logging.getLogger(__name__)

class SupervisorAPI:
    """A class to interact with the HA Supervisor API."""

    def __init__(self, loop):
        self.loop = loop
        self.session = aiohttp.ClientSession(loop=loop)
        self.supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
        if not self.supervisor_token:
            _LOGGER.warning("SUPERVISOR_TOKEN not set. Supervisor API is unavailable.")

    async def _request(self, method, endpoint, data=None):
        """Make a request to the Supervisor API."""
        if not self.supervisor_token:
            raise ConnectionRefusedError("Supervisor API token is not available.")

        url = f"http://supervisor/{endpoint}"
        headers = {"Authorization": f"Bearer {self.supervisor_token}"}

        try:
            async with self.session.request(method, url, headers=headers, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Supervisor API request failed: {err}")
            raise

    async def get_self_info(self):
        """Get information about this addon."""
        return await self._request("GET", "addons/self/info")

    async def restart_addon(self):
        """Restart this addon."""
        _LOGGER.info("Requesting addon restart via Supervisor API.")
        return await self._request("POST", "addons/self/restart")

    async def close(self):
        """Close the aiohttp session."""
        await self.session.close()