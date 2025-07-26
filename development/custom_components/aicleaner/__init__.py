"""AICleaner v3 Custom Component"""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import AiCleanerCoordinator
from .api_client import AiCleanerApiClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AICleaner from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Create API client
    session = hass.helpers.aiohttp_client.async_get_clientsession()
    api_client = AiCleanerApiClient(
        host=entry.data["host"],
        port=entry.data["port"],
        api_key=entry.data.get("api_key"),
        session=session
    )
    
    # Test connection
    try:
        await api_client.test_connection()
    except Exception as e:
        _LOGGER.error(f"Failed to connect to AICleaner core service: {e}")
        return False
    
    # Create coordinator
    coordinator = AiCleanerCoordinator(hass, api_client)
    
    # Store coordinator in hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client
    }
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _register_services(hass, api_client)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def _register_services(hass: HomeAssistant, api_client: AiCleanerApiClient):
    """Register AICleaner services."""
    
    async def analyze_camera_service(call):
        """Handle analyze_camera service call."""
        camera_entity_id = call.data.get("entity_id")
        prompt = call.data.get("prompt", "Analyze this camera image")
        provider = call.data.get("provider")
        save_result = call.data.get("save_result", True)
        
        try:
            result = await api_client.analyze_camera(camera_entity_id, prompt, provider)
            _LOGGER.info(f"Camera analysis result: {result}")
            
            # Save result to sensor if requested
            if save_result:
                # Update last analysis result sensor
                hass.states.async_set(
                    f"sensor.aicleaner_last_analysis",
                    result.get("text", "No result"),
                    {
                        "camera": camera_entity_id,
                        "prompt": prompt,
                        "provider": result.get("provider", "unknown"),
                        "timestamp": dt_util.utcnow().isoformat()
                    }
                )
            
            # Fire event with the result
            hass.bus.async_fire("aicleaner_analysis_complete", {
                "camera": camera_entity_id,
                "result": result,
                "service": "analyze_camera"
            })
        except Exception as e:
            _LOGGER.error(f"Camera analysis failed: {e}")
    
    async def generate_text_service(call):
        """Handle generate_text service call."""
        prompt = call.data.get("prompt")
        provider = call.data.get("provider")
        temperature = call.data.get("temperature", 0.7)
        max_tokens = call.data.get("max_tokens", 1000)
        
        try:
            result = await api_client.generate_text(
                prompt=prompt,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens
            )
            _LOGGER.info(f"Text generation result: {result.get('text', '')[:100]}...")
            
            # Save result to sensor
            hass.states.async_set(
                f"sensor.aicleaner_last_generation",
                result.get("text", "No result"),
                {
                    "prompt": prompt,
                    "provider": result.get("provider", "unknown"),
                    "usage": result.get("usage", {}),
                    "timestamp": dt_util.utcnow().isoformat()
                }
            )
            
            # Fire event with the result
            hass.bus.async_fire("aicleaner_generation_complete", {
                "result": result,
                "service": "generate_text"
            })
        except Exception as e:
            _LOGGER.error(f"Text generation failed: {e}")
    
    async def check_provider_status_service(call):
        """Handle check_provider_status service call."""
        provider = call.data.get("provider")
        
        try:
            status = await api_client.check_provider_status(provider)
            _LOGGER.info(f"Provider {provider} status: {status}")
            
            # Fire event with the result
            hass.bus.async_fire("aicleaner_provider_status", {
                "provider": provider,
                "status": status,
                "service": "check_provider_status"
            })
        except Exception as e:
            _LOGGER.error(f"Provider status check failed: {e}")
    
    async def switch_provider_service(call):
        """Handle switch_provider service call."""
        provider = call.data.get("provider")
        
        try:
            result = await api_client.switch_provider(provider)
            _LOGGER.info(f"Switched to provider: {provider}")
            
            # Fire event with the result
            hass.bus.async_fire("aicleaner_provider_switched", {
                "provider": provider,
                "result": result,
                "service": "switch_provider"
            })
        except Exception as e:
            _LOGGER.error(f"Provider switch failed: {e}")
    
    # Register all services
    hass.services.async_register(
        DOMAIN,
        "analyze_camera",
        analyze_camera_service
    )
    
    hass.services.async_register(
        DOMAIN,
        "generate_text",
        generate_text_service
    )
    
    hass.services.async_register(
        DOMAIN,
        "check_provider_status",
        check_provider_status_service
    )
    
    hass.services.async_register(
        DOMAIN,
        "switch_provider",
        switch_provider_service
    )
