"""
AICleaner Package - Intelligent Multi-Zone Cleanliness Management
Component-based design following TDD principles
"""

import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .ha_integration.entity_manager import AICleanerEntityManager
from .ha_integration.service_manager import AICleanerServiceManager
from .ha_integration.supervisor_api import SupervisorAPI
from .ha_integration.performance_monitor import PerformanceMonitor
from .mqtt_discovery.discovery_manager import MQTTDiscoveryManager

_LOGGER = logging.getLogger(__name__)

# Import core components
from .core.analyzer import ZoneAnalyzer
from .core.analysis_queue import AnalysisPriority
from .core.state_manager import AnalysisState
from .core.scheduler import ZoneScheduler
from .core.state_manager import StateManager
from .core.performance_monitor import PerformanceMonitor as CorePerformanceMonitor

# Import integration components
from .integrations.ha_client import HAClient
from .integrations.mqtt_manager import MQTTManager
from .integrations.gemini_client import GeminiClient

# Import existing components for backward compatibility
try:
    from .aicleaner import AICleaner, Zone
    from .configuration_manager import ConfigurationManager
    from .notification_engine import NotificationEngine
    from .ignore_rules_manager import IgnoreRulesManager
except ImportError:
    # These may not be available during testing
    pass

# Import external dependencies for test patching
try:
    from google.generativeai.generative_models import GenerativeModel
    from pathlib import Path
except ImportError:
    # Fallback for environments without these dependencies
    GenerativeModel = None
    Path = None

__version__ = "2.1.0"
__all__ = [
    # Core components
    'ZoneAnalyzer',
    'AnalysisPriority',
    'AnalysisState',
    'ZoneScheduler',
    'StateManager',
    'PerformanceMonitor',
    
    # Integration components
    'HAClient',
    'MQTTManager',
    'GeminiClient',
    
    # Legacy components
    'AICleaner',
    'Zone',
    'ConfigurationManager',
    'NotificationEngine',
    'IgnoreRulesManager',
    
    # External dependencies
    'GenerativeModel',
    'Path'
]

# Home Assistant Integration Functions
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AICleaner v3 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Setup integration components
    supervisor_api = SupervisorAPI(hass.loop)
    performance_monitor = PerformanceMonitor(hass, DOMAIN)
    entity_manager = AICleanerEntityManager(hass, None)  # Coordinator needs to be set
    service_manager = AICleanerServiceManager(hass, DOMAIN)
    
    # Initialize unified configuration manager
    from .utils.configuration_manager import ConfigurationManager
    config_manager = ConfigurationManager()
    
    # Setup MQTT discovery integration with unified config
    mqtt_discovery_manager = MQTTDiscoveryManager(entity_manager, performance_monitor, config_manager)

    hass.data[DOMAIN][entry.entry_id] = {
        "supervisor_api": supervisor_api,
        "performance_monitor": performance_monitor,
        "entity_manager": entity_manager,
        "service_manager": service_manager,
        "mqtt_discovery_manager": mqtt_discovery_manager,
    }
    
    # Start MQTT discovery
    try:
        await mqtt_discovery_manager.start()
        _LOGGER.info("MQTT Discovery started successfully")
    except Exception as e:
        _LOGGER.warning(f"MQTT Discovery failed to start: {e}")
        # Continue without MQTT discovery

    # Forward the setup to the sensor platform.
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    
    if unload_ok:
        # Stop MQTT discovery gracefully
        try:
            mqtt_discovery_manager = hass.data[DOMAIN][entry.entry_id]["mqtt_discovery_manager"]
            await mqtt_discovery_manager.stop()
            _LOGGER.info("MQTT Discovery stopped successfully")
        except Exception as e:
            _LOGGER.warning(f"Error stopping MQTT Discovery: {e}")
        
        await hass.data[DOMAIN][entry.entry_id]["supervisor_api"].close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok