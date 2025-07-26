"""API client for AICleaner core service."""
import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


class AiCleanerApiClient:
    """Client for communicating with AICleaner core service."""

    def __init__(self, host: str, port: int, api_key: str, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self.host = host
        self.port = port
        self.api_key = api_key
        self.session = session
        self.base_url = f"http://{host}:{port}"
        
    async def get_status(self) -> Dict[str, Any]:
        """Get status from core service."""
        try:
            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            async with self.session.get(
                f"{self.base_url}/v1/status",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    _LOGGER.error("Failed to get status: %s", response.status)
                    return {"status": "error", "error": f"HTTP {response.status}"}
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout getting status from core service")
            return {"status": "unavailable", "error": "Timeout"}
        except Exception as e:
            _LOGGER.error("Error getting status: %s", e)
            return {"status": "error", "error": str(e)}
    
    async def analyze_camera(self, camera_entity_id: str, prompt: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
        """Analyze camera image using core service."""
        try:
            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            
            payload = {
                "prompt": prompt or "Analyze this camera image and describe what you see.",
                "camera_entity_id": camera_entity_id
            }
            
            if provider:
                payload["provider"] = provider
            
            async with self.session.post(
                f"{self.base_url}/v1/generate",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    _LOGGER.error("Failed to analyze camera: %s - %s", response.status, error_text)
                    return {"error": f"HTTP {response.status}: {error_text}"}
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout analyzing camera")
            return {"error": "Analysis timeout"}
        except Exception as e:
            _LOGGER.error("Error analyzing camera: %s", e)
            return {"error": str(e)}
    
    async def generate_text(self, prompt: str, provider: Optional[str] = None, 
                           temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Generate text using core service."""
        try:
            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            
            payload = {"prompt": prompt}
            
            if provider:
                payload["provider"] = provider
            if temperature is not None:
                payload["temperature"] = temperature
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            
            async with self.session.post(
                f"{self.base_url}/v1/generate",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    _LOGGER.error("Failed to generate text: %s - %s", response.status, error_text)
                    return {"error": f"HTTP {response.status}: {error_text}"}
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout generating text")
            return {"error": "Generation timeout"}
        except Exception as e:
            _LOGGER.error("Error generating text: %s", e)
            return {"error": str(e)}
    
    async def check_provider_status(self, provider: str) -> Dict[str, Any]:
        """Check specific provider status."""
        try:
            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            
            async with self.session.get(
                f"{self.base_url}/v1/providers/status",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    providers = data.get("providers", {})
                    return providers.get(provider, {"available": False, "error": "Provider not found"})
                else:
                    error_text = await response.text()
                    _LOGGER.error("Failed to check provider status: %s - %s", response.status, error_text)
                    return {"error": f"HTTP {response.status}: {error_text}"}
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout checking provider status")
            return {"error": "Status check timeout"}
        except Exception as e:
            _LOGGER.error("Error checking provider status: %s", e)
            return {"error": str(e)}
    
    async def switch_provider(self, provider: str) -> Dict[str, Any]:
        """Switch active provider."""
        try:
            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            
            payload = {"provider": provider}
            
            async with self.session.post(
                f"{self.base_url}/v1/providers/switch",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    _LOGGER.error("Failed to switch provider: %s - %s", response.status, error_text)
                    return {"error": f"HTTP {response.status}: {error_text}"}
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout switching provider")
            return {"error": "Switch timeout"}
        except Exception as e:
            _LOGGER.error("Error switching provider: %s", e)
            return {"error": str(e)}
    
    async def test_connection(self) -> bool:
        """Test connection to core service."""
        try:
            result = await self.get_status()
            return "error" not in result and "unavailable" not in result.get("status", "")
        except Exception:
            return False