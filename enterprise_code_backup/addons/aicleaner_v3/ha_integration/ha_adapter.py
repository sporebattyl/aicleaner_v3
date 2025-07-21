"""
Home Assistant Adapter
Phase 4A: Enhanced Home Assistant Integration

Acts as a bridge between AICleaner core systems and Home Assistant,
providing a clean interface that decouples core logic from HA dependencies.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class HomeAssistantAdapter:
    """
    Acts as a bridge to the Home Assistant instance.
    
    This adapter provides a clean interface for core systems to interact
    with Home Assistant without directly depending on the hass object.
    """
    
    def __init__(self, hass=None):
        """
        Initialize the Home Assistant adapter.
        
        Args:
            hass: Home Assistant instance (can be None for testing/standalone mode)
        """
        self._hass = hass
        self._mock_mode = hass is None
        self._mock_states: Dict[str, Any] = {}
        self._service_calls: List[Dict[str, Any]] = []
        
        if self._mock_mode:
            logger.info("HomeAssistantAdapter initialized in mock mode")
        else:
            logger.info("HomeAssistantAdapter initialized with real HA instance")
    
    def is_available(self) -> bool:
        """Check if Home Assistant is available"""
        return not self._mock_mode and self._hass is not None
    
    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Gets the state of a Home Assistant entity.
        
        Args:
            entity_id: The entity ID to query
            
        Returns:
            Entity state information or None if not found
        """
        try:
            if self._mock_mode:
                # Return mock state for testing
                mock_state = self._mock_states.get(entity_id, {
                    "entity_id": entity_id,
                    "state": "unknown",
                    "attributes": {},
                    "last_changed": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                })
                logger.debug(f"Mock state for {entity_id}: {mock_state}")
                return mock_state
            
            if not self._hass:
                return None
                
            state = self._hass.states.get(entity_id)
            if state:
                return {
                    "entity_id": state.entity_id,
                    "state": state.state,
                    "attributes": dict(state.attributes),
                    "last_changed": state.last_changed.isoformat() if state.last_changed else None,
                    "last_updated": state.last_updated.isoformat() if state.last_updated else None
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting state for {entity_id}: {e}")
            return None
    
    async def call_service(self, domain: str, service: str, service_data: Optional[Dict[str, Any]] = None, target: Optional[Dict[str, Any]] = None) -> bool:
        """
        Calls a Home Assistant service.
        
        Args:
            domain: Service domain (e.g., 'vacuum', 'light')
            service: Service name (e.g., 'start', 'turn_on')
            service_data: Service data/parameters
            target: Service target (entity_id, area_id, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            service_call = {
                "domain": domain,
                "service": service,
                "service_data": service_data or {},
                "target": target or {},
                "timestamp": datetime.now().isoformat()
            }
            
            if self._mock_mode:
                # Log service call for testing
                self._service_calls.append(service_call)
                logger.info(f"Mock service call: {domain}.{service} with data: {service_data}")
                return True
            
            if not self._hass:
                logger.warning("No Home Assistant instance available for service call")
                return False
            
            await self._hass.services.async_call(
                domain=domain,
                service=service,
                service_data=service_data or {},
                target=target
            )
            
            logger.info(f"Called HA service: {domain}.{service}")
            return True
            
        except Exception as e:
            logger.error(f"Error calling service {domain}.{service}: {e}")
            return False
    
    async def set_state(self, entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None) -> bool:
        """
        Sets the state of a Home Assistant entity.
        
        Args:
            entity_id: The entity ID to update
            state: New state value
            attributes: Optional attributes to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self._mock_mode:
                # Update mock state
                self._mock_states[entity_id] = {
                    "entity_id": entity_id,
                    "state": state,
                    "attributes": attributes or {},
                    "last_changed": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
                logger.debug(f"Mock state set for {entity_id}: {state}")
                return True
            
            if not self._hass:
                return False
            
            self._hass.states.async_set(
                entity_id=entity_id,
                new_state=state,
                attributes=attributes
            )
            
            logger.debug(f"Set HA state: {entity_id} = {state}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting state for {entity_id}: {e}")
            return False
    
    async def fire_event(self, event_type: str, event_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Fires a Home Assistant event.
        
        Args:
            event_type: Type of event to fire
            event_data: Event data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self._mock_mode:
                logger.info(f"Mock event fired: {event_type} with data: {event_data}")
                return True
            
            if not self._hass:
                return False
            
            self._hass.bus.async_fire(
                event_type=event_type,
                event_data=event_data or {}
            )
            
            logger.debug(f"Fired HA event: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error firing event {event_type}: {e}")
            return False
    
    async def get_entities(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all entities, optionally filtered by domain.
        
        Args:
            domain: Optional domain filter (e.g., 'sensor', 'switch')
            
        Returns:
            List of entity information
        """
        try:
            if self._mock_mode:
                # Return mock entities
                mock_entities = []
                for entity_id, state_info in self._mock_states.items():
                    if domain is None or entity_id.startswith(f"{domain}."):
                        mock_entities.append(state_info)
                return mock_entities
            
            if not self._hass:
                return []
            
            entities = []
            for state in self._hass.states.async_all():
                if domain is None or state.entity_id.startswith(f"{domain}."):
                    entities.append({
                        "entity_id": state.entity_id,
                        "state": state.state,
                        "attributes": dict(state.attributes),
                        "last_changed": state.last_changed.isoformat() if state.last_changed else None,
                        "last_updated": state.last_updated.isoformat() if state.last_updated else None
                    })
            
            return entities
            
        except Exception as e:
            logger.error(f"Error getting entities: {e}")
            return []
    
    async def is_entity_available(self, entity_id: str) -> bool:
        """
        Check if an entity is available (not unavailable or unknown).
        
        Args:
            entity_id: The entity ID to check
            
        Returns:
            True if entity is available, False otherwise
        """
        state_info = await self.get_state(entity_id)
        if not state_info:
            return False
        
        state = state_info.get("state", "").lower()
        return state not in ["unavailable", "unknown", ""]
    
    def get_mock_service_calls(self) -> List[Dict[str, Any]]:
        """Get list of service calls made in mock mode (for testing)"""
        return self._service_calls.copy()
    
    def clear_mock_data(self) -> None:
        """Clear mock data (for testing)"""
        self._mock_states.clear()
        self._service_calls.clear()
    
    def set_mock_state(self, entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Set mock state for testing"""
        self._mock_states[entity_id] = {
            "entity_id": entity_id,
            "state": state,
            "attributes": attributes or {},
            "last_changed": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get adapter status information"""
        return {
            "mock_mode": self._mock_mode,
            "ha_available": self.is_available(),
            "mock_states_count": len(self._mock_states),
            "service_calls_count": len(self._service_calls)
        }