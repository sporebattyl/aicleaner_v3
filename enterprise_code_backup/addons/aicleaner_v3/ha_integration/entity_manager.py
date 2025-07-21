"""
Home Assistant Entity Manager
Phase 4A: Enhanced Home Assistant Integration

Manages the lifecycle of Home Assistant entities and device registry integration.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime
import json

from .models import (
    HADeviceInfo,
    HASensorConfig,
    HABinarySensorConfig,
    HASwitchConfig,
    HAButtonConfig,
    HASelectConfig,
    HAEntityState,
    HAEntityType,
    EntityDefinition
)
from .ha_client import HAClient
from .config_schema import HAIntegrationConfig

logger = logging.getLogger(__name__)

class EntityManager:
    """
    Manages Home Assistant entity registration, updates, and lifecycle
    
    Provides methods for creating, updating, and managing AICleaner entities
    within the Home Assistant ecosystem.
    """
    
    def __init__(self, ha_client: HAClient, config: HAIntegrationConfig):
        self.ha_client = ha_client
        self.config = config
        self.registered_entities: Dict[str, EntityDefinition] = {}
        self.entity_states: Dict[str, HAEntityState] = {}
        self.device_info: Optional[HADeviceInfo] = None
        self.update_callbacks: Dict[str, Callable] = {}
        self.state_update_lock = asyncio.Lock()
        
    async def initialize(self) -> bool:
        """
        Initialize the entity manager and register device
        
        Returns:
            True if successful
        """
        try:
            logger.info("Initializing Home Assistant entity manager...")
            
            # Create device info
            self.device_info = self._create_device_info()
            
            # Register device in HA device registry
            if self.config.enable_device_registry:
                if not await self._register_device():
                    logger.error("Failed to register device")
                    return False
            
            # Register default entities
            if self.config.auto_register_entities:
                await self._register_default_entities()
            
            logger.info("Entity manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize entity manager: {e}")
            return False
    
    def _create_device_info(self) -> HADeviceInfo:
        """Create device information for Home Assistant device registry"""
        return HADeviceInfo(
            identifiers=[f"aicleaner_v3_{self.config.device_name.lower().replace(' ', '_')}"],
            name=self.config.device_name,
            manufacturer=self.config.device_manufacturer,
            model=self.config.device_model,
            sw_version="3.0.0",  # TODO: Get from version file
            suggested_area=self.config.suggested_area,
            configuration_url="/api/config"  # URL relative to ingress
        )
    
    async def _register_device(self) -> bool:
        """Register device in Home Assistant device registry"""
        try:
            device_config = {
                "device": self.device_info.dict(),
                "platform": "aicleaner_v3"
            }
            
            url = f"{self.ha_client.config.rest_api_url}/config/device_registry"
            
            async with self.ha_client.session.post(url, json=device_config) as response:
                if response.status in [200, 201]:
                    logger.info(f"Device registered: {self.device_info.name}")
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(f"Device registration failed: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Device registration error: {e}")
            return False
    
    async def _register_default_entities(self):
        """Register default AICleaner entities"""
        default_entities = [
            # System status sensor
            EntityDefinition(
                entity_type=HAEntityType.SENSOR,
                object_id="status",
                name="AICleaner Status",
                config=HASensorConfig(
                    name="AICleaner Status",
                    unique_id=f"{self.config.entity_prefix}status",
                    icon="mdi:robot-vacuum",
                    device=self.device_info
                ),
                initial_state="idle",
                update_callback="get_system_status"
            ),
            
            # Active cleaning binary sensor
            EntityDefinition(
                entity_type=HAEntityType.BINARY_SENSOR,
                object_id="active",
                name="AICleaner Active",
                config=HABinarySensorConfig(
                    name="AICleaner Active",
                    unique_id=f"{self.config.entity_prefix}active",
                    device_class="running",
                    icon="mdi:robot-vacuum",
                    device=self.device_info
                ),
                initial_state=False,
                update_callback="get_active_status"
            ),
            
            # Error status binary sensor
            EntityDefinition(
                entity_type=HAEntityType.BINARY_SENSOR,
                object_id="error",
                name="AICleaner Error",
                config=HABinarySensorConfig(
                    name="AICleaner Error",
                    unique_id=f"{self.config.entity_prefix}error",
                    device_class="problem",
                    icon="mdi:alert-circle",
                    device=self.device_info
                ),
                initial_state=False,
                update_callback="get_error_status"
            ),
            
            # Master switch
            EntityDefinition(
                entity_type=HAEntityType.SWITCH,
                object_id="master_switch",
                name="AICleaner Master Switch",
                config=HASwitchConfig(
                    name="AICleaner Master Switch",
                    unique_id=f"{self.config.entity_prefix}master_switch",
                    icon="mdi:power",
                    device=self.device_info
                ),
                initial_state=True,
                update_callback="get_master_switch_state"
            ),
            
            # Last cleaned timestamp
            EntityDefinition(
                entity_type=HAEntityType.SENSOR,
                object_id="last_cleaned",
                name="Last Cleaned",
                config=HASensorConfig(
                    name="Last Cleaned",
                    unique_id=f"{self.config.entity_prefix}last_cleaned",
                    device_class="timestamp",
                    icon="mdi:clock",
                    device=self.device_info
                ),
                initial_state=None,
                update_callback="get_last_cleaned_time"
            ),
            
            # Cleaning mode select
            EntityDefinition(
                entity_type=HAEntityType.SELECT,
                object_id="cleaning_mode",
                name="Cleaning Mode",
                config=HASelectConfig(
                    name="Cleaning Mode",
                    unique_id=f"{self.config.entity_prefix}cleaning_mode",
                    options=["eco", "normal", "deep", "auto"],
                    icon="mdi:tune",
                    device=self.device_info
                ),
                initial_state="normal",
                update_callback="get_cleaning_mode"
            ),
            
            # Emergency stop button
            EntityDefinition(
                entity_type=HAEntityType.BUTTON,
                object_id="emergency_stop",
                name="Emergency Stop",
                config=HAButtonConfig(
                    name="Emergency Stop",
                    unique_id=f"{self.config.entity_prefix}emergency_stop",
                    icon="mdi:stop-circle",
                    device=self.device_info
                ),
                initial_state=None,
                update_callback=None
            )
        ]
        
        # Register each entity
        for entity_def in default_entities:
            await self.register_entity(entity_def)
    
    async def register_entity(self, entity_def: EntityDefinition) -> bool:
        """
        Register a new entity with Home Assistant
        
        Args:
            entity_def: Entity definition
            
        Returns:
            True if successful
        """
        try:
            entity_id = f"{entity_def.entity_type.value}.{self.config.entity_prefix}{entity_def.object_id}"
            
            # Prepare entity configuration for HA
            entity_config = self._prepare_entity_config(entity_def)
            
            # Register with HA
            if not await self.ha_client.register_entity(entity_config):
                logger.error(f"Failed to register entity: {entity_id}")
                return False
            
            # Store entity definition
            self.registered_entities[entity_id] = entity_def
            
            # Set initial state if provided
            if entity_def.initial_state is not None:
                await self.update_entity_state(
                    entity_id, 
                    entity_def.initial_state,
                    self._get_entity_attributes(entity_def)
                )
            
            # Register update callback
            if entity_def.update_callback:
                self.update_callbacks[entity_id] = entity_def.update_callback
            
            logger.info(f"Entity registered: {entity_id}")
            return True
            
        except Exception as e:
            logger.error(f"Entity registration failed: {e}")
            return False
    
    def _prepare_entity_config(self, entity_def: EntityDefinition) -> Dict[str, Any]:
        """Prepare entity configuration for Home Assistant registration"""
        base_config = {
            "platform": "aicleaner_v3",
            "unique_id": entity_def.config.unique_id,
            "name": entity_def.config.name,
            "device": entity_def.config.device.dict()
        }
        
        # Add entity-specific configuration
        if hasattr(entity_def.config, 'icon') and entity_def.config.icon:
            base_config["icon"] = entity_def.config.icon
        
        if hasattr(entity_def.config, 'device_class') and entity_def.config.device_class:
            base_config["device_class"] = entity_def.config.device_class
        
        if hasattr(entity_def.config, 'unit_of_measurement') and entity_def.config.unit_of_measurement:
            base_config["unit_of_measurement"] = entity_def.config.unit_of_measurement
        
        if hasattr(entity_def.config, 'options') and entity_def.config.options:
            base_config["options"] = entity_def.config.options
        
        # Add entity category if specified
        if hasattr(entity_def.config, 'entity_category') and entity_def.config.entity_category:
            base_config["entity_category"] = entity_def.config.entity_category
        
        return base_config
    
    def _get_entity_attributes(self, entity_def: EntityDefinition) -> Dict[str, Any]:
        """Get default attributes for an entity"""
        attributes = {
            "friendly_name": entity_def.config.name,
            "managed_by": "AICleaner v3",
            "last_updated": datetime.now().isoformat()
        }
        
        # Add entity-specific attributes
        if entity_def.entity_type == HAEntityType.SENSOR:
            if hasattr(entity_def.config, 'unit_of_measurement') and entity_def.config.unit_of_measurement:
                attributes["unit_of_measurement"] = entity_def.config.unit_of_measurement
        
        return attributes
    
    async def update_entity_state(self, entity_id: str, state: Any, 
                                 attributes: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update entity state in Home Assistant
        
        Args:
            entity_id: Full entity ID
            state: New state value
            attributes: Additional attributes
            
        Returns:
            True if successful
        """
        async with self.state_update_lock:
            try:
                # Prepare attributes
                final_attributes = attributes or {}
                
                # Add entity definition attributes if available
                if entity_id in self.registered_entities:
                    entity_def = self.registered_entities[entity_id]
                    default_attrs = self._get_entity_attributes(entity_def)
                    final_attributes.update(default_attrs)
                
                # Update last_updated timestamp
                final_attributes["last_updated"] = datetime.now().isoformat()
                
                # Update state in HA
                success = await self.ha_client.update_entity_state(
                    entity_id, state, final_attributes
                )
                
                if success:
                    # Update local state cache
                    self.entity_states[entity_id] = HAEntityState(
                        entity_id=entity_id,
                        state=state,
                        attributes=final_attributes,
                        last_updated=datetime.now()
                    )
                    
                    logger.debug(f"Entity state updated: {entity_id} = {state}")
                
                return success
                
            except Exception as e:
                logger.error(f"Failed to update entity state: {e}")
                return False
    
    async def update_multiple_entities(self, updates: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Update multiple entity states efficiently
        
        Args:
            updates: List of update dictionaries with 'entity_id', 'state', 'attributes'
            
        Returns:
            Dictionary mapping entity_id to success status
        """
        results = {}
        
        # Process updates concurrently with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(10)
        
        async def update_single(update):
            async with semaphore:
                entity_id = update["entity_id"]
                state = update["state"]
                attributes = update.get("attributes")
                
                success = await self.update_entity_state(entity_id, state, attributes)
                return entity_id, success
        
        # Execute all updates
        tasks = [update_single(update) for update in updates]
        update_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in update_results:
            if isinstance(result, Exception):
                logger.error(f"Entity update error: {result}")
            else:
                entity_id, success = result
                results[entity_id] = success
        
        return results
    
    async def refresh_entity_states(self, entity_ids: Optional[List[str]] = None) -> bool:
        """
        Refresh entity states using registered update callbacks
        
        Args:
            entity_ids: Specific entities to refresh (all if None)
            
        Returns:
            True if successful
        """
        try:
            entities_to_refresh = entity_ids or list(self.registered_entities.keys())
            
            updates = []
            for entity_id in entities_to_refresh:
                if entity_id in self.update_callbacks:
                    callback_name = self.update_callbacks[entity_id]
                    
                    # Get new state from callback
                    new_state = await self._execute_update_callback(callback_name, entity_id)
                    
                    if new_state is not None:
                        updates.append({
                            "entity_id": entity_id,
                            "state": new_state,
                            "attributes": {"updated_via": "refresh"}
                        })
            
            # Update all entities
            if updates:
                results = await self.update_multiple_entities(updates)
                success_count = sum(1 for success in results.values() if success)
                logger.info(f"Refreshed {success_count}/{len(updates)} entity states")
                return success_count == len(updates)
            
            return True
            
        except Exception as e:
            logger.error(f"Entity state refresh failed: {e}")
            return False
    
    async def _execute_update_callback(self, callback_name: str, entity_id: str) -> Any:
        """
        Execute entity update callback to get current state
        
        Args:
            callback_name: Name of callback function
            entity_id: Entity ID being updated
            
        Returns:
            Current entity state or None
        """
        try:
            # This would interface with AICleaner's core systems
            # For now, return mock values based on callback name
            
            if callback_name == "get_system_status":
                return "idle"  # TODO: Get from core system
            elif callback_name == "get_active_status":
                return False  # TODO: Get from cleaning manager
            elif callback_name == "get_error_status":
                return False  # TODO: Get from error manager
            elif callback_name == "get_master_switch_state":
                return True  # TODO: Get from configuration
            elif callback_name == "get_last_cleaned_time":
                return None  # TODO: Get from cleaning history
            elif callback_name == "get_cleaning_mode":
                return "normal"  # TODO: Get from current settings
            else:
                logger.warning(f"Unknown update callback: {callback_name}")
                return None
                
        except Exception as e:
            logger.error(f"Update callback failed: {callback_name} - {e}")
            return None
    
    async def unregister_entity(self, entity_id: str) -> bool:
        """
        Unregister entity from Home Assistant
        
        Args:
            entity_id: Full entity ID
            
        Returns:
            True if successful
        """
        try:
            # Remove from HA entity registry
            url = f"{self.ha_client.config.rest_api_url}/config/entity_registry/{entity_id}"
            
            async with self.ha_client.session.delete(url) as response:
                if response.status in [200, 204]:
                    # Remove from local tracking
                    self.registered_entities.pop(entity_id, None)
                    self.entity_states.pop(entity_id, None)
                    self.update_callbacks.pop(entity_id, None)
                    
                    logger.info(f"Entity unregistered: {entity_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(f"Entity unregistration failed: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Entity unregistration error: {e}")
            return False
    
    async def get_entity_state(self, entity_id: str) -> Optional[HAEntityState]:
        """
        Get current entity state
        
        Args:
            entity_id: Full entity ID
            
        Returns:
            Entity state or None
        """
        return self.entity_states.get(entity_id)
    
    def get_registered_entities(self) -> List[str]:
        """Get list of registered entity IDs"""
        return list(self.registered_entities.keys())
    
    def get_entity_count(self) -> int:
        """Get number of registered entities"""
        return len(self.registered_entities)
    
    async def start_periodic_updates(self, interval: int = None):
        """
        Start periodic entity state updates
        
        Args:
            interval: Update interval in seconds (uses config default if None)
        """
        update_interval = interval or self.config.update_interval
        
        async def update_loop():
            while True:
                try:
                    await self.refresh_entity_states()
                    await asyncio.sleep(update_interval)
                except Exception as e:
                    logger.error(f"Periodic update error: {e}")
                    await asyncio.sleep(60)  # Wait longer on error
        
        asyncio.create_task(update_loop())
        logger.info(f"Started periodic entity updates (interval: {update_interval}s)")
    
    async def cleanup(self):
        """Cleanup entity manager resources"""
        logger.info("Cleaning up entity manager...")
        
        # Unregister all entities if needed
        if self.config.auto_register_entities:
            for entity_id in list(self.registered_entities.keys()):
                await self.unregister_entity(entity_id)
        
        # Clear local state
        self.registered_entities.clear()
        self.entity_states.clear()
        self.update_callbacks.clear()
        
        logger.info("Entity manager cleanup complete")