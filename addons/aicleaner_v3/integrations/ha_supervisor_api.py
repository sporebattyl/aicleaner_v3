"""
HA Supervisor API Integration
Proper implementation of Supervisor API calls and integration
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from homeassistant.core import HomeAssistant
from homeassistant.components import hassio
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

class HASupervisorAPI:
    """Home Assistant Supervisor API integration."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the Supervisor API client."""
        self.hass = hass
        self.session = async_get_clientsession(hass)
        self._supervisor_token = None
        self._supervisor_url = "http://supervisor"
        
    async def async_setup(self) -> bool:
        """Set up the Supervisor API client."""
        try:
            if not hassio.is_hassio(self.hass):
                _LOGGER.warning("Not running under Supervisor")
                return False
                
            # Get Supervisor token
            self._supervisor_token = hassio.get_supervisor_token(self.hass)
            if not self._supervisor_token:
                _LOGGER.error("Failed to get Supervisor token")
                return False
                
            # Test API connection
            info = await self.async_get_supervisor_info()
            if info:
                _LOGGER.info(f"Connected to Supervisor v{info.get('version', 'unknown')}")
                return True
                
        except Exception as e:
            _LOGGER.error(f"Supervisor API setup failed: {e}")
            
        return False
    
    async def async_get_supervisor_info(self) -> Optional[Dict[str, Any]]:
        """Get Supervisor information."""
        try:
            headers = {"Authorization": f"Bearer {self._supervisor_token}"}
            async with self.session.get(
                f"{self._supervisor_url}/supervisor/info",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                else:
                    _LOGGER.error(f"Supervisor API error: {response.status}")
                    
        except Exception as e:
            _LOGGER.error(f"Failed to get Supervisor info: {e}")
            
        return None
    
    async def async_get_addon_info(self, addon_slug: str) -> Optional[Dict[str, Any]]:
        """Get addon information."""
        try:
            headers = {"Authorization": f"Bearer {self._supervisor_token}"}
            async with self.session.get(
                f"{self._supervisor_url}/addons/{addon_slug}/info",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                else:
                    _LOGGER.error(f"Addon info API error: {response.status}")
                    
        except Exception as e:
            _LOGGER.error(f"Failed to get addon info: {e}")
            
        return None
    
    async def async_update_addon_options(
        self, 
        addon_slug: str, 
        options: Dict[str, Any]
    ) -> bool:
        """Update addon options."""
        try:
            headers = {
                "Authorization": f"Bearer {self._supervisor_token}",
                "Content-Type": "application/json"
            }
            async with self.session.post(
                f"{self._supervisor_url}/addons/{addon_slug}/options",
                json={"options": options},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    _LOGGER.info(f"Updated addon {addon_slug} options")
                    return True
                else:
                    _LOGGER.error(f"Failed to update addon options: {response.status}")
                    
        except Exception as e:
            _LOGGER.error(f"Failed to update addon options: {e}")
            
        return False
    
    async def async_restart_addon(self, addon_slug: str) -> bool:
        """Restart an addon."""
        try:
            headers = {"Authorization": f"Bearer {self._supervisor_token}"}
            async with self.session.post(
                f"{self._supervisor_url}/addons/{addon_slug}/restart",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    _LOGGER.info(f"Restarted addon {addon_slug}")
                    return True
                else:
                    _LOGGER.error(f"Failed to restart addon: {response.status}")
                    
        except Exception as e:
            _LOGGER.error(f"Failed to restart addon: {e}")
            
        return False
    
    async def async_get_system_info(self) -> Optional[Dict[str, Any]]:
        """Get system information."""
        try:
            headers = {"Authorization": f"Bearer {self._supervisor_token}"}
            async with self.session.get(
                f"{self._supervisor_url}/host/info",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                else:
                    _LOGGER.error(f"System info API error: {response.status}")
                    
        except Exception as e:
            _LOGGER.error(f"Failed to get system info: {e}")
            
        return None
