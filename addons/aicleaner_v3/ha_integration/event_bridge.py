"""
Home Assistant Event Bridge
Phase 4A: Enhanced HA Integration

Bridges events between Home Assistant and the AICleaner v3 web interface,
providing real-time updates and bidirectional communication.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum

from homeassistant.core import HomeAssistant, Event, State
from homeassistant.const import EVENT_STATE_CHANGED, EVENT_SERVICE_CALL_REGISTERED
from homeassistant.helpers.event import async_track_state_change_event

from utils.unified_logger import get_logger

logger = get_logger(__name__)

class EventType(Enum):
    """Types of events bridged between HA and web interface"""
    STATE_CHANGED = "state_changed"
    SERVICE_CALLED = "service_called"
    DEVICE_UPDATED = "device_updated"
    PROVIDER_STATUS = "provider_status"
    SYSTEM_HEALTH = "system_health"
    AUTOMATION_TRIGGERED = "automation_triggered"
    CONFIGURATION_CHANGED = "configuration_changed"
    ERROR_OCCURRED = "error_occurred"

@dataclass
class BridgedEvent:
    """Represents an event bridged between HA and web interface"""
    event_type: EventType
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    entity_id: Optional[str] = None
    area: Optional[str] = None
    severity: str = "info"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "entity_id": self.entity_id,
            "area": self.area,
            "severity": self.severity
        }

class HAEventBridge:
    """
    Event Bridge between Home Assistant and AICleaner v3 Web Interface
    
    Provides real-time event synchronization and bidirectional communication
    """
    
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.event_listeners: Dict[str, Callable] = {}
        self.websocket_clients: Set[Any] = set()
        self._ha_listeners: List[Callable] = []
        self.event_history: List[BridgedEvent] = []
        self.max_history_size = 1000
        
    async def async_initialize(self):
        """Initialize the event bridge"""
        try:
            # Set up Home Assistant event listeners
            await self._setup_ha_listeners()
            
            # Set up web interface event handlers
            await self._setup_web_handlers()
            
            logger.info("Event bridge initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize event bridge: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        # Remove Home Assistant listeners
        for listener in self._ha_listeners:
            listener()
        self._ha_listeners.clear()
        
        # Clear websocket clients
        self.websocket_clients.clear()
        
        logger.info("Event bridge cleaned up")
    
    async def _setup_ha_listeners(self):
        """Set up Home Assistant event listeners"""
        try:
            # Listen for state changes
            self._ha_listeners.append(
                self.hass.bus.async_listen(
                    EVENT_STATE_CHANGED,
                    self._handle_ha_state_change
                )
            )
            
            # Listen for service calls
            self._ha_listeners.append(
                self.hass.bus.async_listen(
                    "call_service",
                    self._handle_ha_service_call
                )
            )
            
            # Listen for automation triggers
            self._ha_listeners.append(
                self.hass.bus.async_listen(
                    "automation_triggered",
                    self._handle_ha_automation_trigger
                )
            )
            
            # Listen for device registry updates
            self._ha_listeners.append(
                self.hass.bus.async_listen(
                    "device_registry_updated",
                    self._handle_ha_device_update
                )
            )
            
            # Listen for configuration changes
            self._ha_listeners.append(
                self.hass.bus.async_listen(
                    "component_loaded",
                    self._handle_ha_config_change
                )
            )
            
            logger.info("Home Assistant event listeners set up")
            
        except Exception as e:
            logger.error(f"Error setting up HA listeners: {e}")
            raise
    
    async def _setup_web_handlers(self):
        """Set up web interface event handlers"""
        try:
            # Register event handlers for web interface
            self.event_listeners = {
                "provider_control": self._handle_web_provider_control,
                "zone_control": self._handle_web_zone_control,
                "strategy_update": self._handle_web_strategy_update,
                "device_control": self._handle_web_device_control,
                "automation_trigger": self._handle_web_automation_trigger,
                "configuration_update": self._handle_web_config_update
            }
            
            logger.info("Web interface event handlers set up")
            
        except Exception as e:
            logger.error(f"Error setting up web handlers: {e}")
            raise
    
    async def _handle_ha_state_change(self, event: Event):
        """Handle Home Assistant state changes"""
        try:
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            
            if not entity_id or not new_state:
                return
            
            # Filter relevant state changes
            if not self._is_relevant_entity(entity_id):
                return
            
            # Create bridged event
            bridged_event = BridgedEvent(
                event_type=EventType.STATE_CHANGED,
                timestamp=datetime.now(),
                source="home_assistant",
                data={
                    "entity_id": entity_id,
                    "new_state": new_state.state,
                    "old_state": old_state.state if old_state else None,
                    "attributes": dict(new_state.attributes) if new_state.attributes else {},
                    "domain": entity_id.split(".")[0]
                },
                entity_id=entity_id,
                area=self._get_entity_area(entity_id)
            )
            
            # Add to history and broadcast
            await self._add_event_to_history(bridged_event)
            await self._broadcast_to_websockets(bridged_event)
            
            logger.debug(f"Bridged state change: {entity_id} = {new_state.state}")
            
        except Exception as e:
            logger.error(f"Error handling HA state change: {e}")
    
    async def _handle_ha_service_call(self, event: Event):
        """Handle Home Assistant service calls"""
        try:
            domain = event.data.get("domain")
            service = event.data.get("service")
            service_data = event.data.get("service_data", {})
            
            # Filter AICleaner service calls
            if domain == "aicleaner_v3":
                bridged_event = BridgedEvent(
                    event_type=EventType.SERVICE_CALLED,
                    timestamp=datetime.now(),
                    source="home_assistant",
                    data={
                        "domain": domain,
                        "service": service,
                        "service_data": service_data
                    }
                )
                
                await self._add_event_to_history(bridged_event)
                await self._broadcast_to_websockets(bridged_event)
                
                logger.info(f"Bridged service call: {domain}.{service}")
                
        except Exception as e:
            logger.error(f"Error handling HA service call: {e}")
    
    async def _handle_ha_automation_trigger(self, event: Event):
        """Handle Home Assistant automation triggers"""
        try:
            automation_id = event.data.get("name")
            trigger_data = event.data.get("trigger", {})
            
            bridged_event = BridgedEvent(
                event_type=EventType.AUTOMATION_TRIGGERED,
                timestamp=datetime.now(),
                source="home_assistant",
                data={
                    "automation_id": automation_id,
                    "trigger": trigger_data
                }
            )
            
            await self._add_event_to_history(bridged_event)
            await self._broadcast_to_websockets(bridged_event)
            
            logger.info(f"Bridged automation trigger: {automation_id}")
            
        except Exception as e:
            logger.error(f"Error handling HA automation trigger: {e}")
    
    async def _handle_ha_device_update(self, event: Event):
        """Handle Home Assistant device registry updates"""
        try:
            action = event.data.get("action")
            device_id = event.data.get("device_id")
            
            bridged_event = BridgedEvent(
                event_type=EventType.DEVICE_UPDATED,
                timestamp=datetime.now(),
                source="home_assistant",
                data={
                    "action": action,
                    "device_id": device_id
                }
            )
            
            await self._add_event_to_history(bridged_event)
            await self._broadcast_to_websockets(bridged_event)
            
            logger.info(f"Bridged device update: {device_id} ({action})")
            
        except Exception as e:
            logger.error(f"Error handling HA device update: {e}")
    
    async def _handle_ha_config_change(self, event: Event):
        """Handle Home Assistant configuration changes"""
        try:
            component = event.data.get("component")
            
            bridged_event = BridgedEvent(
                event_type=EventType.CONFIGURATION_CHANGED,
                timestamp=datetime.now(),
                source="home_assistant",
                data={
                    "component": component
                }
            )
            
            await self._add_event_to_history(bridged_event)
            await self._broadcast_to_websockets(bridged_event)
            
            logger.info(f"Bridged config change: {component}")
            
        except Exception as e:
            logger.error(f"Error handling HA config change: {e}")
    
    async def _handle_web_provider_control(self, event_data: Dict[str, Any]):
        """Handle provider control requests from web interface"""
        try:
            provider_id = event_data.get("provider_id")
            action = event_data.get("action")
            
            # Call Home Assistant service
            await self.hass.services.async_call(
                "aicleaner_v3",
                "control_provider",
                {
                    "provider_id": provider_id,
                    "action": action
                }
            )
            
            logger.info(f"Web provider control: {provider_id} {action}")
            
        except Exception as e:
            logger.error(f"Error handling web provider control: {e}")
    
    async def _handle_web_zone_control(self, event_data: Dict[str, Any]):
        """Handle zone control requests from web interface"""
        try:
            zone_id = event_data.get("zone_id")
            action = event_data.get("action")
            
            # Call Home Assistant service
            await self.hass.services.async_call(
                "aicleaner_v3",
                "control_zone",
                {
                    "zone_id": zone_id,
                    "action": action
                }
            )
            
            logger.info(f"Web zone control: {zone_id} {action}")
            
        except Exception as e:
            logger.error(f"Error handling web zone control: {e}")
    
    async def _handle_web_strategy_update(self, event_data: Dict[str, Any]):
        """Handle strategy update requests from web interface"""
        try:
            strategy = event_data.get("strategy")
            
            # Call Home Assistant service
            await self.hass.services.async_call(
                "aicleaner_v3",
                "set_strategy",
                {
                    "strategy": strategy
                }
            )
            
            logger.info(f"Web strategy update: {strategy}")
            
        except Exception as e:
            logger.error(f"Error handling web strategy update: {e}")
    
    async def _handle_web_device_control(self, event_data: Dict[str, Any]):
        """Handle device control requests from web interface"""
        try:
            entity_id = event_data.get("entity_id")
            action = event_data.get("action")
            parameters = event_data.get("parameters", {})
            
            # Determine service based on entity domain and action
            domain = entity_id.split(".")[0]
            service = None
            
            if action == "turn_on":
                service = "turn_on"
            elif action == "turn_off":
                service = "turn_off"
            elif action == "toggle":
                service = "toggle"
            
            if service:
                # Call Home Assistant service
                await self.hass.services.async_call(
                    domain,
                    service,
                    {
                        "entity_id": entity_id,
                        **parameters
                    }
                )
                
                logger.info(f"Web device control: {entity_id} {action}")
            
        except Exception as e:
            logger.error(f"Error handling web device control: {e}")
    
    async def _handle_web_automation_trigger(self, event_data: Dict[str, Any]):
        """Handle automation trigger requests from web interface"""
        try:
            automation_id = event_data.get("automation_id")
            
            # Call Home Assistant service
            await self.hass.services.async_call(
                "automation",
                "trigger",
                {
                    "entity_id": f"automation.{automation_id}"
                }
            )
            
            logger.info(f"Web automation trigger: {automation_id}")
            
        except Exception as e:
            logger.error(f"Error handling web automation trigger: {e}")
    
    async def _handle_web_config_update(self, event_data: Dict[str, Any]):
        """Handle configuration update requests from web interface"""
        try:
            config_type = event_data.get("type")
            config_data = event_data.get("data")
            
            # Call Home Assistant service
            await self.hass.services.async_call(
                "aicleaner_v3",
                "reload_config",
                {
                    "type": config_type,
                    "data": config_data
                }
            )
            
            logger.info(f"Web config update: {config_type}")
            
        except Exception as e:
            logger.error(f"Error handling web config update: {e}")
    
    def _is_relevant_entity(self, entity_id: str) -> bool:
        """Check if entity is relevant for bridging"""
        try:
            # Include AICleaner entities
            if entity_id.startswith("sensor.aicleaner_v3_") or \
               entity_id.startswith("switch.aicleaner_v3_") or \
               entity_id.startswith("select.aicleaner_v3_"):
                return True
            
            # Include common automation-relevant entities
            relevant_domains = [
                "light", "switch", "sensor", "binary_sensor", "camera",
                "climate", "cover", "fan", "lock", "vacuum", "media_player"
            ]
            
            domain = entity_id.split(".")[0]
            return domain in relevant_domains
            
        except Exception:
            return False
    
    def _get_entity_area(self, entity_id: str) -> Optional[str]:
        """Get area name for entity"""
        try:
            # This would need to be implemented with registry access
            # For now, return None
            return None
            
        except Exception:
            return None
    
    async def _add_event_to_history(self, event: BridgedEvent):
        """Add event to history with size management"""
        try:
            self.event_history.append(event)
            
            # Trim history if too large
            if len(self.event_history) > self.max_history_size:
                self.event_history = self.event_history[-self.max_history_size:]
                
        except Exception as e:
            logger.error(f"Error adding event to history: {e}")
    
    async def _broadcast_to_websockets(self, event: BridgedEvent):
        """Broadcast event to all connected WebSocket clients"""
        try:
            if not self.websocket_clients:
                return
            
            event_json = json.dumps(event.to_dict())
            
            # Send to all connected clients
            disconnected_clients = []
            for client in self.websocket_clients:
                try:
                    await client.send_text(event_json)
                except Exception as e:
                    logger.warning(f"Failed to send to WebSocket client: {e}")
                    disconnected_clients.append(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.websocket_clients.discard(client)
                
        except Exception as e:
            logger.error(f"Error broadcasting to WebSockets: {e}")
    
    # Public API methods
    
    def add_websocket_client(self, client):
        """Add a WebSocket client for event broadcasting"""
        self.websocket_clients.add(client)
        logger.info(f"Added WebSocket client. Total clients: {len(self.websocket_clients)}")
    
    def remove_websocket_client(self, client):
        """Remove a WebSocket client"""
        self.websocket_clients.discard(client)
        logger.info(f"Removed WebSocket client. Total clients: {len(self.websocket_clients)}")
    
    async def handle_web_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle events from web interface"""
        try:
            handler = self.event_listeners.get(event_type)
            if handler:
                await handler(event_data)
            else:
                logger.warning(f"No handler for web event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling web event {event_type}: {e}")
    
    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent event history"""
        try:
            recent_events = self.event_history[-limit:] if limit > 0 else self.event_history
            return [event.to_dict() for event in recent_events]
            
        except Exception as e:
            logger.error(f"Error getting event history: {e}")
            return []
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event statistics"""
        try:
            stats = {
                "total_events": len(self.event_history),
                "websocket_clients": len(self.websocket_clients),
                "event_types": {},
                "sources": {}
            }
            
            # Count by event type
            for event in self.event_history:
                event_type = event.event_type.value
                stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1
            
            # Count by source
            for event in self.event_history:
                source = event.source
                stats["sources"][source] = stats["sources"].get(source, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting event statistics: {e}")
            return {}