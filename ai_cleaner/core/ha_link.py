"""
Home Assistant integration module for AI Cleaner addon.
Manages entity creation, updates, and communication via MQTT and REST API.
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import uuid

try:
    import aiomqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    aiomqtt = None

from .config import get_config, AiCleanerConfig
from .providers.base import CleaningPlan, CleaningTask, ImageAnalysis


logger = logging.getLogger(__name__)


class HAEntityError(Exception):
    """Home Assistant entity-related exception."""
    pass


class EntityType:
    """Home Assistant entity types."""
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    TODO = "todo"
    SWITCH = "switch"
    BUTTON = "button"


class HAEntity:
    """Represents a Home Assistant entity."""
    
    def __init__(self, entity_type: str, object_id: str, name: str, config: Dict[str, Any]):
        self.entity_type = entity_type
        self.object_id = object_id
        self.entity_id = f"{entity_type}.ai_cleaner_{object_id}"
        self.name = name
        self.config = config
        self.last_updated = datetime.now()
    
    def get_discovery_topic(self) -> str:
        """Get MQTT discovery topic for this entity."""
        return f"homeassistant/{self.entity_type}/ai_cleaner/{self.object_id}/config"
    
    def get_state_topic(self) -> str:
        """Get MQTT state topic for this entity."""
        return f"homeassistant/{self.entity_type}/ai_cleaner/{self.object_id}/state"
    
    def get_attributes_topic(self) -> str:
        """Get MQTT attributes topic for this entity."""
        return f"homeassistant/{self.entity_type}/ai_cleaner/{self.object_id}/attr"
    
    def get_discovery_config(self) -> Dict[str, Any]:
        """Get discovery configuration for this entity."""
        base_config = {
            "name": self.name,
            "unique_id": f"ai_cleaner_{self.object_id}",
            "state_topic": self.get_state_topic(),
            "json_attributes_topic": self.get_attributes_topic(),
            "device": {
                "identifiers": ["ai_cleaner"],
                "name": "AI Cleaner",
                "model": "Home Assistant Addon",
                "manufacturer": "AI Cleaner",
                "sw_version": "1.0.0"
            }
        }
        
        # Merge with entity-specific configuration
        base_config.update(self.config)
        return base_config


class MQTTManager:
    """Manages MQTT communication with Home Assistant."""
    
    def __init__(self, config: AiCleanerConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._client: Optional[aiomqtt.Client] = None
        self._entities: Dict[str, HAEntity] = {}
        self._connected = False
        self._reconnect_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        """Connect to MQTT broker."""
        if not MQTT_AVAILABLE:
            self.logger.error("MQTT not available - aiomqtt not installed")
            return False
        
        try:
            mqtt_config = self.config.get_mqtt_config()
            
            self._client = aiomqtt.Client(
                hostname=mqtt_config['host'],
                port=mqtt_config['port'],
                username=mqtt_config.get('username'),
                password=mqtt_config.get('password'),
                identifier=f"ai_cleaner_{uuid.uuid4().hex[:8]}",
                clean_session=True,
                keepalive=60
            )
            
            await self._client.__aenter__()
            self._connected = True
            
            # Start reconnection handler
            self._reconnect_task = asyncio.create_task(self._handle_reconnection())
            
            self.logger.info(f"Connected to MQTT broker at {mqtt_config['host']}:{mqtt_config['port']}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception as e:
                self.logger.warning(f"Error disconnecting MQTT client: {e}")
        
        self._connected = False
        self.logger.info("Disconnected from MQTT broker")
    
    async def _handle_reconnection(self):
        """Handle MQTT reconnection attempts."""
        while True:
            try:
                if not self._connected:
                    self.logger.info("Attempting MQTT reconnection...")
                    if await self.connect():
                        # Republish all entities after reconnection
                        await self._republish_entities()
                
                await asyncio.sleep(30)  # Check every 30 seconds
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in reconnection handler: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _republish_entities(self):
        """Republish all entities after reconnection."""
        for entity in self._entities.values():
            try:
                await self.publish_discovery(entity)
            except Exception as e:
                self.logger.error(f"Failed to republish entity {entity.entity_id}: {e}")
    
    async def publish_discovery(self, entity: HAEntity) -> bool:
        """Publish entity discovery configuration."""
        if not self._connected or not self._client:
            return False
        
        try:
            topic = entity.get_discovery_topic()
            config = entity.get_discovery_config()
            
            await self._client.publish(
                topic, 
                json.dumps(config),
                qos=1,
                retain=True
            )
            
            self._entities[entity.entity_id] = entity
            self.logger.debug(f"Published discovery for {entity.entity_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to publish discovery for {entity.entity_id}: {e}")
            return False
    
    async def publish_state(self, entity_id: str, state: Any, attributes: Optional[Dict[str, Any]] = None) -> bool:
        """Publish entity state and attributes."""
        if not self._connected or not self._client or entity_id not in self._entities:
            return False
        
        try:
            entity = self._entities[entity_id]
            
            # Publish state
            await self._client.publish(
                entity.get_state_topic(),
                str(state),
                qos=1,
                retain=True
            )
            
            # Publish attributes if provided
            if attributes:
                await self._client.publish(
                    entity.get_attributes_topic(),
                    json.dumps(attributes),
                    qos=1,
                    retain=True
                )
            
            entity.last_updated = datetime.now()
            self.logger.debug(f"Published state for {entity_id}: {state}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to publish state for {entity_id}: {e}")
            return False
    
    async def remove_entity(self, entity_id: str) -> bool:
        """Remove entity by publishing empty discovery config."""
        if entity_id not in self._entities:
            return False
        
        try:
            entity = self._entities[entity_id]
            
            # Publish empty config to remove entity
            await self._client.publish(
                entity.get_discovery_topic(),
                "",
                qos=1,
                retain=True
            )
            
            # Remove from local cache
            del self._entities[entity_id]
            
            self.logger.info(f"Removed entity {entity_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to remove entity {entity_id}: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if MQTT client is connected."""
        return self._connected


class HAAPIClient:
    """Home Assistant REST API client."""
    
    def __init__(self, config: AiCleanerConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._session: Optional[aiohttp.ClientSession] = None
        self.base_url = config.ha_url
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is available."""
        if self._session is None or self._session.closed:
            headers = {
                'User-Agent': 'AI-Cleaner/1.0',
                'Content-Type': 'application/json'
            }
            
            if self.config.ha_token:
                headers['Authorization'] = f'Bearer {self.config.ha_token.get_secret_value()}'
            
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=headers
            )
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def call_service(self, domain: str, service: str, data: Optional[Dict[str, Any]] = None, target: Optional[Dict[str, Any]] = None) -> bool:
        """Call Home Assistant service."""
        await self._ensure_session()
        
        try:
            url = f"{self.base_url}/api/services/{domain}/{service}"
            
            payload = {}
            if data:
                payload.update(data)
            if target:
                payload['target'] = target
            
            async with self._session.post(url, json=payload) as response:
                if response.status == 200:
                    self.logger.debug(f"Called service {domain}.{service}")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Service call failed: HTTP {response.status} - {error_text}")
                    return False
        
        except Exception as e:
            self.logger.error(f"Error calling service {domain}.{service}: {e}")
            return False
    
    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity state from Home Assistant."""
        await self._ensure_session()
        
        try:
            url = f"{self.base_url}/api/states/{entity_id}"
            
            async with self._session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.warning(f"Failed to get state for {entity_id}: HTTP {response.status}")
                    return None
        
        except Exception as e:
            self.logger.error(f"Error getting state for {entity_id}: {e}")
            return None
    
    async def send_notification(self, title: str, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send notification via Home Assistant."""
        notification_data = {
            'title': title,
            'message': message
        }
        
        if data:
            notification_data['data'] = data
        
        return await self.call_service('notify', 'persistent_notification', notification_data)


class HAEntityManager:
    """Manages Home Assistant entities for AI Cleaner."""
    
    def __init__(self, config: Optional[AiCleanerConfig] = None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        
        self.mqtt_manager = MQTTManager(self.config)
        self.api_client = HAAPIClient(self.config)
        
        self._status_entities: Dict[str, HAEntity] = {}
        self._todo_entities: Dict[str, HAEntity] = {}
    
    async def initialize(self) -> bool:
        """Initialize the entity manager."""
        try:
            # Connect to MQTT
            if not await self.mqtt_manager.connect():
                self.logger.warning("MQTT connection failed - entity creation will be disabled")
                return False
            
            # Create core entities
            await self._create_core_entities()
            
            self.logger.info("HA Entity Manager initialized successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to initialize HA Entity Manager: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the entity manager."""
        await self.mqtt_manager.disconnect()
        await self.api_client.close()
    
    async def _create_core_entities(self):
        """Create core AI Cleaner entities."""
        # Status sensor
        status_entity = HAEntity(
            entity_type=EntityType.SENSOR,
            object_id="status",
            name="AI Cleaner Status",
            config={
                "icon": "mdi:robot-vacuum",
                "device_class": None,
            }
        )
        
        await self.mqtt_manager.publish_discovery(status_entity)
        await self.mqtt_manager.publish_state(
            status_entity.entity_id,
            "initializing",
            {"last_analysis": None, "active_tasks": 0}
        )
        
        self._status_entities["status"] = status_entity
        
        # Last analysis sensor
        analysis_entity = HAEntity(
            entity_type=EntityType.SENSOR,
            object_id="last_analysis",
            name="AI Cleaner Last Analysis",
            config={
                "icon": "mdi:camera-timer",
                "device_class": "timestamp",
            }
        )
        
        await self.mqtt_manager.publish_discovery(analysis_entity)
        self._status_entities["last_analysis"] = analysis_entity
        
        # Task count sensor
        task_count_entity = HAEntity(
            entity_type=EntityType.SENSOR,
            object_id="task_count",
            name="AI Cleaner Active Tasks",
            config={
                "icon": "mdi:format-list-numbered",
                "unit_of_measurement": "tasks",
            }
        )
        
        await self.mqtt_manager.publish_discovery(task_count_entity)
        await self.mqtt_manager.publish_state(task_count_entity.entity_id, 0)
        self._status_entities["task_count"] = task_count_entity
        
        # Confidence sensor
        confidence_entity = HAEntity(
            entity_type=EntityType.SENSOR,
            object_id="confidence",
            name="AI Cleaner Analysis Confidence",
            config={
                "icon": "mdi:chart-line",
                "unit_of_measurement": "%",
            }
        )
        
        await self.mqtt_manager.publish_discovery(confidence_entity)
        self._status_entities["confidence"] = confidence_entity
        
        # Analysis needed binary sensor
        analysis_needed_entity = HAEntity(
            entity_type=EntityType.BINARY_SENSOR,
            object_id="analysis_needed",
            name="AI Cleaner Analysis Needed",
            config={
                "icon": "mdi:clock-alert",
                "device_class": "problem",
            }
        )
        
        await self.mqtt_manager.publish_discovery(analysis_needed_entity)
        await self.mqtt_manager.publish_state(analysis_needed_entity.entity_id, "OFF")
        self._status_entities["analysis_needed"] = analysis_needed_entity
        
        # AI provider available binary sensor
        ai_available_entity = HAEntity(
            entity_type=EntityType.BINARY_SENSOR,
            object_id="ai_available",
            name="AI Cleaner Provider Available",
            config={
                "icon": "mdi:brain",
                "device_class": "connectivity",
            }
        )
        
        await self.mqtt_manager.publish_discovery(ai_available_entity)
        self._status_entities["ai_available"] = ai_available_entity
    
    async def update_system_status(self, status: str, attributes: Optional[Dict[str, Any]] = None):
        """Update system status sensor."""
        if "status" in self._status_entities:
            entity_id = self._status_entities["status"].entity_id
            await self.mqtt_manager.publish_state(entity_id, status, attributes or {})
    
    async def update_last_analysis(self, timestamp: datetime, analysis: Optional[ImageAnalysis] = None):
        """Update last analysis timestamp and details."""
        if "last_analysis" in self._status_entities:
            entity_id = self._status_entities["last_analysis"].entity_id
            
            attributes = {
                "timestamp": timestamp.isoformat(),
            }
            
            if analysis:
                attributes.update({
                    "zone_id": analysis.zone_id,
                    "cleanliness_score": analysis.overall_cleanliness_score,
                    "confidence": analysis.confidence.value,
                    "summary": analysis.summary,
                    "task_count": len(analysis.suggested_tasks)
                })
            
            await self.mqtt_manager.publish_state(
                entity_id,
                timestamp.isoformat(),
                attributes
            )
    
    async def update_task_count(self, count: int, details: Optional[Dict[str, Any]] = None):
        """Update active task count."""
        if "task_count" in self._status_entities:
            entity_id = self._status_entities["task_count"].entity_id
            await self.mqtt_manager.publish_state(entity_id, count, details or {})
    
    async def update_confidence(self, confidence_percentage: float):
        """Update analysis confidence percentage."""
        if "confidence" in self._status_entities:
            entity_id = self._status_entities["confidence"].entity_id
            await self.mqtt_manager.publish_state(entity_id, int(confidence_percentage * 100))
    
    async def set_analysis_needed(self, needed: bool, reason: Optional[str] = None):
        """Set analysis needed binary sensor."""
        if "analysis_needed" in self._status_entities:
            entity_id = self._status_entities["analysis_needed"].entity_id
            state = "ON" if needed else "OFF"
            attributes = {"reason": reason} if reason else {}
            await self.mqtt_manager.publish_state(entity_id, state, attributes)
    
    async def set_ai_available(self, available: bool, provider: Optional[str] = None):
        """Set AI provider availability binary sensor."""
        if "ai_available" in self._status_entities:
            entity_id = self._status_entities["ai_available"].entity_id
            state = "ON" if available else "OFF"
            attributes = {"provider": provider} if provider else {}
            await self.mqtt_manager.publish_state(entity_id, state, attributes)
    
    async def create_todo_list(self, list_id: str, name: str) -> bool:
        """Create a todo list entity."""
        try:
            # Create todo entity via service call
            success = await self.api_client.call_service(
                'todo',
                'add_list',
                {'name': name}
            )
            
            if success:
                self.logger.info(f"Created todo list: {name}")
                return True
            else:
                self.logger.error(f"Failed to create todo list: {name}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error creating todo list {name}: {e}")
            return False
    
    async def add_todo_items(self, list_entity_id: str, tasks: List[CleaningTask]) -> int:
        """Add multiple todo items to a list."""
        added_count = 0
        
        for task in tasks:
            try:
                success = await self.api_client.call_service(
                    'todo',
                    'add_item',
                    {
                        'item': task.title,
                        'description': task.description,
                        'due_date': None  # Could add due dates based on urgency
                    },
                    target={'entity_id': list_entity_id}
                )
                
                if success:
                    added_count += 1
                    self.logger.debug(f"Added todo item: {task.title}")
                else:
                    self.logger.warning(f"Failed to add todo item: {task.title}")
            
            except Exception as e:
                self.logger.error(f"Error adding todo item {task.title}: {e}")
        
        self.logger.info(f"Added {added_count}/{len(tasks)} todo items to {list_entity_id}")
        return added_count
    
    async def send_cleaning_plan_notification(self, plan: CleaningPlan) -> bool:
        """Send notification about new cleaning plan."""
        if not self.config.enable_notifications:
            return False
        
        if len(plan.tasks) < self.config.notification_threshold:
            return False
        
        title = f"AI Cleaner: {len(plan.tasks)} Tasks Created"
        
        high_priority_tasks = [t for t in plan.tasks if t.urgency.value >= 3]
        if high_priority_tasks:
            message = f"Found {len(high_priority_tasks)} high priority cleaning tasks. Check your todo list for details."
        else:
            message = f"Created {len(plan.tasks)} cleaning tasks based on image analysis."
        
        data = {
            "zone_id": plan.zone_id,
            "task_count": len(plan.tasks),
            "priority_score": plan.priority_score,
            "plan_id": plan.plan_id
        }
        
        return await self.api_client.send_notification(title, message, data)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on HA integration."""
        health = {
            'status': 'healthy',
            'mqtt_connected': self.mqtt_manager.is_connected(),
            'entities_created': len(self._status_entities),
            'todo_lists': len(self._todo_entities),
            'errors': []
        }
        
        try:
            # Test API connectivity
            test_state = await self.api_client.get_state('sun.sun')
            if test_state is None:
                health['status'] = 'degraded'
                health['errors'].append('HA API not accessible')
        
        except Exception as e:
            health['status'] = 'unhealthy'
            health['errors'].append(f'Health check failed: {e}')
        
        return health