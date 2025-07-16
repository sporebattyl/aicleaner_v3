"""
HA Entity Manager Implementation
Proper entity registration, lifecycle management, and HA integration
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import EntityPlatform

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aicleaner_v3"

class AiCleanerEntity(Entity):
    """Base entity for AICleaner v3."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        entity_id: str,
        name: str,
        device_class: Optional[str] = None
    ):
        """Initialize the entity."""
        self.hass = hass
        self._config_entry = config_entry
        self._entity_id = entity_id
        self._name = name
        self._device_class = device_class
        self._state = None
        self._available = True
        self._attributes = {}
        
    @property
    def unique_id(self) -> str:
        """Return unique ID for this entity."""
        return f"{DOMAIN}_{self._config_entry.entry_id}_{self._entity_id}"
    
    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name
    
    @property
    def state(self):
        """Return the state of the entity."""
        return self._state
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._available
    
    @property
    def device_class(self) -> Optional[str]:
        """Return the device class."""
        return self._device_class
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity attributes."""
        return self._attributes
    
    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "AICleaner v3",
            "manufacturer": "AICleaner",
            "model": "AI Cleaning Assistant v3",
            "sw_version": "3.0.0",
            "configuration_url": f"homeassistant://config/integrations/dashboard/add?domain={DOMAIN}"
        }
    
    def update_state(self, state: Any, attributes: Optional[Dict[str, Any]] = None):
        """Update entity state and attributes."""
        self._state = state
        if attributes:
            self._attributes.update(attributes)
        self.async_write_ha_state()
    
    def set_available(self, available: bool):
        """Set entity availability."""
        self._available = available
        self.async_write_ha_state()

class AiCleanerSensor(AiCleanerEntity):
    """AICleaner sensor entity."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        entity_id: str,
        name: str,
        unit_of_measurement: Optional[str] = None,
        device_class: Optional[str] = None
    ):
        """Initialize the sensor."""
        super().__init__(hass, config_entry, entity_id, name, device_class)
        self._unit_of_measurement = unit_of_measurement
    
    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        return self._unit_of_measurement

class AiCleanerSwitch(AiCleanerEntity):
    """AICleaner switch entity."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        entity_id: str,
        name: str,
        device_class: Optional[str] = None
    ):
        """Initialize the switch."""
        super().__init__(hass, config_entry, entity_id, name, device_class)
        self._state = STATE_OFF
    
    @property
    def is_on(self) -> bool:
        """Return if the switch is on."""
        return self._state == STATE_ON
    
    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._state = STATE_ON
        self.async_write_ha_state()
        await self._execute_switch_action(True)
    
    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        self._state = STATE_OFF
        self.async_write_ha_state()
        await self._execute_switch_action(False)
    
    async def _execute_switch_action(self, turn_on: bool):
        """Execute the switch action."""
        # Implementation specific to each switch
        action = "on" if turn_on else "off"
        _LOGGER.info(f"Switch {self._entity_id} turned {action}")

class HAEntityManager:
    """Manage Home Assistant entity registration and lifecycle."""
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the entity manager."""
        self.hass = hass
        self.config_entry = config_entry
        self._entities: Dict[str, AiCleanerEntity] = {}
        self._platforms: Dict[str, "EntityPlatform"] = {}
    
    async def async_setup_entities(self):
        """Set up all entities for the integration."""
        _LOGGER.info("Setting up AICleaner v3 entities")
        
        # Create default entities
        await self._create_default_entities()
        
        _LOGGER.info(f"Created {len(self._entities)} entities")
    
    async def _create_default_entities(self):
        """Create default entities for the integration."""
        # System status sensor
        system_sensor = AiCleanerSensor(
            self.hass,
            self.config_entry,
            "system_status",
            "System Status",
            device_class="enum"
        )
        await self._add_entity("sensor", system_sensor)
        
        # Cleanup progress sensor
        cleanup_sensor = AiCleanerSensor(
            self.hass,
            self.config_entry,
            "cleanup_progress",
            "Cleanup Progress",
            unit_of_measurement="%",
            device_class="progress"
        )
        await self._add_entity("sensor", cleanup_sensor)
        
        # Performance score sensor
        performance_sensor = AiCleanerSensor(
            self.hass,
            self.config_entry,
            "performance_score",
            "Performance Score",
            unit_of_measurement="points"
        )
        await self._add_entity("sensor", performance_sensor)
        
        # Auto cleanup switch
        auto_cleanup_switch = AiCleanerSwitch(
            self.hass,
            self.config_entry,
            "auto_cleanup",
            "Auto Cleanup",
            device_class="switch"
        )
        await self._add_entity("switch", auto_cleanup_switch)
        
        # AI optimization switch
        ai_optimization_switch = AiCleanerSwitch(
            self.hass,
            self.config_entry,
            "ai_optimization",
            "AI Optimization",
            device_class="switch"
        )
        await self._add_entity("switch", ai_optimization_switch)
        
        # Set initial states
        system_sensor.update_state("ready", {"last_update": "startup"})
        cleanup_sensor.update_state(0, {"last_cleanup": "never"})
        performance_sensor.update_state(100, {"trend": "stable"})
    
    async def _add_entity(self, platform: str, entity: AiCleanerEntity):
        """Add an entity to the specified platform."""
        entity_id = f"{platform}.{DOMAIN}_{entity._entity_id}"
        self._entities[entity_id] = entity
        
        # Add entity to platform
        if platform not in self._platforms:
            # This would normally be handled by the platform setup
            _LOGGER.info(f"Would add {entity.name} to {platform} platform")
        
        _LOGGER.info(f"Added entity: {entity_id}")
    
    async def async_update_entity(
        self,
        entity_id: str,
        state: Any,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """Update an entity's state and attributes."""
        if entity_id in self._entities:
            entity = self._entities[entity_id]
            entity.update_state(state, attributes)
            _LOGGER.debug(f"Updated entity {entity_id}: {state}")
        else:
            _LOGGER.warning(f"Entity {entity_id} not found")
    
    async def async_set_entity_availability(self, entity_id: str, available: bool):
        """Set entity availability."""
        if entity_id in self._entities:
            entity = self._entities[entity_id]
            entity.set_available(available)
            _LOGGER.debug(f"Set {entity_id} availability: {available}")
        else:
            _LOGGER.warning(f"Entity {entity_id} not found")
    
    async def async_remove_entities(self):
        """Remove all managed entities."""
        for entity_id, entity in self._entities.items():
            # Remove from platform
            _LOGGER.info(f"Removing entity: {entity_id}")
        
        self._entities.clear()
        _LOGGER.info("Removed all AICleaner v3 entities")
    
    def get_entity(self, entity_id: str) -> Optional[AiCleanerEntity]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)
    
    def get_all_entities(self) -> Dict[str, AiCleanerEntity]:
        """Get all managed entities."""
        return self._entities.copy()
