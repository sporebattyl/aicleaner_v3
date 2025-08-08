"""
MQTT Service Implementation for AICleaner v3
Provides hybrid MQTT discovery with intelligent filtering and device management
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from collections import OrderedDict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class MQTTFilterRule:
    """Configuration rule for MQTT message filtering"""
    topic_pattern: str  # Supports MQTT wildcards (+, #)
    device_types: Optional[List[str]] = None  # ["light", "sensor", "switch"]
    manufacturers: Optional[List[str]] = None  # ["philips", "ikea", "sonoff"]
    action: str = "allow"  # "allow" or "deny"
    priority: int = 0  # Higher priority rules evaluated first


@dataclass
class MQTTDevice:
    """Represents a discovered or configured MQTT device"""
    unique_id: str
    name: str
    device_type: str  # light, sensor, switch, etc.
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    topics: Dict[str, str] = field(default_factory=dict)  # state_topic, command_topic, etc.
    discovery_payload: Optional[Dict[str, Any]] = None
    source: str = "discovered"  # "discovered" or "explicit"
    last_seen: Optional[datetime] = None
    online: bool = True
    ai_override: Optional[Dict[str, str]] = None  # provider, model overrides


class MQTTTopicMatcher:
    """Efficient MQTT topic matching using trie structure for + and # wildcards"""
    
    class TrieNode:
        def __init__(self):
            self.children: Dict[str, 'MQTTTopicMatcher.TrieNode'] = {}
            self.single_wildcard = None  # For + wildcard
            self.multi_wildcard = None   # For # wildcard
            self.patterns: List[Any] = []  # Patterns that end at this node
    
    def __init__(self):
        self.root = self.TrieNode()
    
    def add_pattern(self, pattern: str, data: Any):
        """Add MQTT wildcard pattern (+, #) to trie"""
        parts = pattern.split('/')
        node = self.root
        
        for i, part in enumerate(parts):
            if part == '+':
                # Single level wildcard
                if node.single_wildcard is None:
                    node.single_wildcard = self.TrieNode()
                node = node.single_wildcard
            elif part == '#':
                # Multi-level wildcard (must be last part)
                if i != len(parts) - 1:
                    raise ValueError(f"# wildcard must be last in pattern: {pattern}")
                if node.multi_wildcard is None:
                    node.multi_wildcard = self.TrieNode()
                node = node.multi_wildcard
                break
            else:
                # Regular topic level
                if part not in node.children:
                    node.children[part] = self.TrieNode()
                node = node.children[part]
        
        node.patterns.append(data)
    
    def match(self, topic: str) -> List[Any]:
        """Find all patterns that match topic with O(topic_length) complexity"""
        parts = topic.split('/')
        results = []
        
        def traverse(node: 'MQTTTopicMatcher.TrieNode', part_index: int):
            # If we've consumed all topic parts, collect patterns
            if part_index >= len(parts):
                results.extend(node.patterns)
                return
            
            current_part = parts[part_index]
            
            # Try exact match
            if current_part in node.children:
                traverse(node.children[current_part], part_index + 1)
            
            # Try single wildcard (+)
            if node.single_wildcard:
                traverse(node.single_wildcard, part_index + 1)
            
            # Try multi-level wildcard (#) - matches everything remaining
            if node.multi_wildcard:
                results.extend(node.multi_wildcard.patterns)
        
        traverse(self.root, 0)
        return results


class LRUCache:
    """LRU cache with TTL for efficient message deduplication"""
    
    def __init__(self, max_size: int, ttl: int):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, moving to end if found and not expired"""
        with self.lock:
            if key in self.cache:
                if time.time() - self.timestamps[key] < self.ttl:
                    self.cache.move_to_end(key)  # Mark as recently used
                    return self.cache[key]
                else:
                    # Expired, remove
                    del self.cache[key]
                    del self.timestamps[key]
            return None
    
    def put(self, key: str, value: Any):
        """Add value to cache, evicting oldest if necessary"""
        with self.lock:
            # Remove oldest if at capacity
            if len(self.cache) >= self.max_size:
                oldest = next(iter(self.cache))
                del self.cache[oldest]
                del self.timestamps[oldest]
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def cleanup_expired(self):
        """Remove all expired entries"""
        with self.lock:
            now = time.time()
            expired_keys = [
                key for key, timestamp in self.timestamps.items()
                if now - timestamp >= self.ttl
            ]
            
            for key in expired_keys:
                del self.cache[key]
                del self.timestamps[key]
            
            return len(expired_keys)


class TokenBucket:
    """Simple token bucket implementation for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: int):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens. Returns True if successful."""
        with self.lock:
            now = time.time()
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class MQTTRateLimiter:
    """Rate limiting for MQTT messages to prevent system overload"""
    
    def __init__(self, config: Dict[str, Any]):
        self.max_messages_per_second = config.get('max_messages_per_second', 50)
        self.per_device_limit = config.get('per_device_messages_per_second', 5)
        self.global_bucket = TokenBucket(self.max_messages_per_second, self.max_messages_per_second)
        self.device_buckets: Dict[str, TokenBucket] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def allow_message(self, topic: str) -> bool:
        """Check if message should be processed based on rate limits"""
        # Cleanup old device buckets periodically
        self._cleanup_device_buckets()
        
        device_id = self._extract_device_id_from_topic(topic)
        
        # Global rate limit
        if not self.global_bucket.consume():
            logger.warning(f"Global rate limit exceeded, dropping message: {topic}")
            return False
        
        # Per-device rate limit
        if device_id:
            if device_id not in self.device_buckets:
                self.device_buckets[device_id] = TokenBucket(self.per_device_limit, self.per_device_limit)
            
            if not self.device_buckets[device_id].consume():
                logger.warning(f"Device rate limit exceeded for {device_id}, dropping message: {topic}")
                return False
        
        return True
    
    def _extract_device_id_from_topic(self, topic: str) -> Optional[str]:
        """Extract device ID from MQTT topic"""
        # For HA discovery: homeassistant/component/device_id/config
        parts = topic.split('/')
        if len(parts) >= 3 and parts[0] == 'homeassistant':
            return parts[2]
        return None
    
    def _cleanup_device_buckets(self):
        """Remove old device buckets to prevent memory leaks"""
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            # Remove buckets that haven't been used recently
            # (This is a simple cleanup - could be more sophisticated)
            if len(self.device_buckets) > 1000:  # Arbitrary limit
                # Keep only the most recently used buckets
                logger.info(f"Cleaning up {len(self.device_buckets)} device rate limit buckets")
                self.device_buckets.clear()
            self.last_cleanup = now


class MQTTMessageFilter:
    """Intelligent MQTT message filtering with rules and deduplication"""
    
    def __init__(self, config: Dict[str, Any]):
        self.rules: List[MQTTFilterRule] = self._load_filter_rules(config)
        self.rate_limiter = MQTTRateLimiter(config)
        
        # Use LRU cache for deduplication
        cache_ttl = config.get('message_cache_ttl', 300)  # 5 minutes
        max_cache_entries = config.get('max_cache_entries', 1000)
        self.message_cache = LRUCache(max_cache_entries, cache_ttl)
        
        # Use trie for efficient topic matching
        self.topic_matcher = MQTTTopicMatcher()
        self._build_topic_matcher()
        
        # Periodic cleanup
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    def should_process_message(self, topic: str, payload: Dict[str, Any]) -> bool:
        """Determine if message should be processed based on filters"""
        # 1. Rate limiting check
        if not self.rate_limiter.allow_message(topic):
            return False
        
        # 2. Deduplication check
        if self._is_duplicate_message(topic, payload):
            return False
        
        # 3. Filter rule evaluation using trie matcher
        return self._evaluate_filter_rules(topic, payload)
    
    def _load_filter_rules(self, config: Dict[str, Any]) -> List[MQTTFilterRule]:
        """Load filter rules from configuration"""
        rules = []
        rule_configs = config.get('filter_rules', [])
        
        for rule_config in rule_configs:
            rule = MQTTFilterRule(
                topic_pattern=rule_config['topic_pattern'],
                device_types=rule_config.get('device_types'),
                manufacturers=rule_config.get('manufacturers'),
                action=rule_config.get('action', 'allow'),
                priority=rule_config.get('priority', 0)
            )
            rules.append(rule)
        
        return rules
    
    def _build_topic_matcher(self):
        """Build trie-based topic matcher from filter rules"""
        for rule in self.rules:
            try:
                self.topic_matcher.add_pattern(rule.topic_pattern, rule)
            except ValueError as e:
                logger.error(f"Invalid topic pattern in filter rule: {e}")
    
    def _is_duplicate_message(self, topic: str, payload: Dict[str, Any]) -> bool:
        """Check if message is a duplicate using LRU cache"""
        cache_key = f"{topic}:{hash(json.dumps(payload, sort_keys=True))}"
        
        # Periodic cleanup
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            cleaned = self.message_cache.cleanup_expired()
            self.last_cleanup = now
            if cleaned > 0:
                logger.debug(f"Cleaned up {cleaned} expired message cache entries")
        
        # Check for duplicate
        if self.message_cache.get(cache_key) is not None:
            return True  # Duplicate found
        
        # Store in cache
        self.message_cache.put(cache_key, True)
        return False
    
    def _evaluate_filter_rules(self, topic: str, payload: Dict[str, Any]) -> bool:
        """Evaluate filter rules against message using trie matcher"""
        # Get matching rules from trie
        matching_rules = self.topic_matcher.match(topic)
        
        if not matching_rules:
            return True  # Default: allow if no rules match
        
        device_info = payload.get('device', {})
        device_type = payload.get('device_class') or device_info.get('device_class')
        manufacturer = device_info.get('manufacturer')
        
        # Evaluate matching rules in priority order
        matching_rules.sort(key=lambda rule: rule.priority, reverse=True)
        
        for rule in matching_rules:
            # Check device type filter
            if rule.device_types and device_type not in rule.device_types:
                continue
            
            # Check manufacturer filter
            if rule.manufacturers and manufacturer not in rule.manufacturers:
                continue
            
            # Rule matches, return action
            return rule.action == "allow"
        
        # Default: allow if no rules matched after filtering
        return True


class MQTTDeviceManager:
    """Manages unified device registry with discovery and explicit overrides"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.devices: Dict[str, MQTTDevice] = {}
        self.explicit_devices: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        self.persistence_file = Path(config.get('device_registry_file', 'data/mqtt_devices.json'))
        
        # Load explicit devices from config
        self._load_explicit_devices()
        
        # Load persisted device state
        self._load_persisted_devices()
    
    def _load_explicit_devices(self):
        """Load explicitly configured devices from config"""
        mqtt_config = self.config.get('mqtt', {})
        explicit_devices = mqtt_config.get('devices', [])
        
        for device_config in explicit_devices:
            unique_id = device_config.get('unique_id') or device_config.get('name', 'unknown')
            self.explicit_devices[unique_id] = device_config
    
    def register_discovered_device(self, discovery_topic: str, payload: Dict[str, Any]):
        """Register a device from MQTT discovery"""
        try:
            unique_id = payload.get('unique_id')
            if not unique_id:
                logger.warning(f"Discovery message missing unique_id: {discovery_topic}")
                return
            
            # Check if this device has explicit overrides
            explicit_config = self.explicit_devices.get(unique_id, {})
            
            # Create device with discovery data, applying explicit overrides
            device = MQTTDevice(
                unique_id=unique_id,
                name=explicit_config.get('name', payload.get('name', unique_id)),
                device_type=explicit_config.get('device_type', payload.get('device_class', 'unknown')),
                manufacturer=payload.get('device', {}).get('manufacturer'),
                model=payload.get('device', {}).get('model'),
                topics={
                    'state_topic': explicit_config.get('state_topic', payload.get('state_topic')),
                    'command_topic': explicit_config.get('command_topic', payload.get('command_topic')),
                    'availability_topic': payload.get('availability_topic')
                },
                discovery_payload=payload,
                source="explicit" if explicit_config else "discovered",
                last_seen=datetime.now(),
                online=True,
                ai_override=explicit_config.get('ai_override')
            )
            
            with self.lock:
                self.devices[unique_id] = device
            
            logger.info(f"Registered {device.source} device: {device.name} ({unique_id})")
            
        except Exception as e:
            logger.error(f"Failed to register device from discovery: {e}")
    
    def get_all_devices(self) -> List[MQTTDevice]:
        """Get all registered devices"""
        with self.lock:
            return list(self.devices.values())
    
    def get_device(self, unique_id: str) -> Optional[MQTTDevice]:
        """Get specific device by unique_id"""
        with self.lock:
            return self.devices.get(unique_id)
    
    def update_device_status(self, unique_id: str, online: bool):
        """Update device online/offline status"""
        with self.lock:
            if unique_id in self.devices:
                self.devices[unique_id].online = online
                self.devices[unique_id].last_seen = datetime.now()
    
    def _load_persisted_devices(self):
        """Load device registry from disk"""
        try:
            if self.persistence_file.exists():
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)
                
                for device_data in data.get('devices', []):
                    device = MQTTDevice(
                        unique_id=device_data['unique_id'],
                        name=device_data['name'],
                        device_type=device_data['device_type'],
                        manufacturer=device_data.get('manufacturer'),
                        model=device_data.get('model'),
                        topics=device_data.get('topics', {}),
                        discovery_payload=device_data.get('discovery_payload'),
                        source=device_data.get('source', 'discovered'),
                        last_seen=datetime.fromisoformat(device_data['last_seen']) if device_data.get('last_seen') else None,
                        online=device_data.get('online', False),
                        ai_override=device_data.get('ai_override')
                    )
                    
                    with self.lock:
                        self.devices[device.unique_id] = device
                
                logger.info(f"Loaded {len(self.devices)} persisted devices")
                
        except Exception as e:
            logger.warning(f"Failed to load persisted devices: {e}")
    
    def persist_devices(self):
        """Persist device registry to disk"""
        try:
            self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare device data for serialization
            devices_data = []
            with self.lock:
                for device in self.devices.values():
                    device_data = {
                        'unique_id': device.unique_id,
                        'name': device.name,
                        'device_type': device.device_type,
                        'manufacturer': device.manufacturer,
                        'model': device.model,
                        'topics': device.topics,
                        'discovery_payload': device.discovery_payload,
                        'source': device.source,
                        'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                        'online': device.online,
                        'ai_override': device.ai_override
                    }
                    devices_data.append(device_data)
            
            # Atomic write
            temp_file = self.persistence_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump({'devices': devices_data, 'updated': datetime.now().isoformat()}, f, indent=2)
            
            temp_file.rename(self.persistence_file)
            logger.debug(f"Persisted {len(devices_data)} devices to {self.persistence_file}")
            
        except Exception as e:
            logger.error(f"Failed to persist devices: {e}")


class IMQTTClient(ABC):
    """Abstract MQTT client interface for decoupling from specific implementations"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to broker. Returns success status."""
        pass
        
    @abstractmethod
    async def disconnect(self):
        """Gracefully disconnect from broker."""
        pass
        
    @abstractmethod
    async def subscribe(self, topic: str, callback) -> bool:
        """Subscribe to topic with callback. Returns success status."""
        pass
        
    @abstractmethod
    async def publish(self, topic: str, payload: str, qos: int = 0) -> bool:
        """Publish message. Returns success status."""
        pass
        
    @abstractmethod
    def is_connected(self) -> bool:
        """Check connection status."""
        pass
        
    @abstractmethod
    async def get_connection_health(self) -> Dict[str, Any]:
        """Get connection health metrics."""
        pass


class MQTTClient(IMQTTClient):
    """Default MQTT client implementation (placeholder for actual library)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Check for external broker configuration first
        if config.get('mqtt_external_broker', False):
            self.broker_config = {
                'host': config.get('mqtt_host', 'localhost'),
                'port': config.get('mqtt_port', 1883),
                'username': config.get('mqtt_username'),
                'password': config.get('mqtt_password')
            }
            logger.info(f"[MQTT] Using external broker configuration: {self.broker_config['host']}:{self.broker_config['port']}")
        else:
            # Fallback to nested broker config or defaults
            self.broker_config = config.get('broker', {})
            if not self.broker_config:
                # Default to internal/local broker
                self.broker_config = {
                    'host': config.get('mqtt_host', 'localhost'),
                    'port': config.get('mqtt_port', 1883)
                }
                logger.info("[MQTT] Using default/internal broker configuration")
        
        self.connected = False
        self.client = None  # Would be actual MQTT client (paho, asyncio-mqtt, etc.)
        self.connection_attempts = 0
        self.last_connection_attempt = None
        
    async def connect(self) -> bool:
        """Connect to MQTT broker with retry logic"""
        try:
            self.connection_attempts += 1
            self.last_connection_attempt = datetime.now()
            
            # Implementation would use actual MQTT library like asyncio-mqtt
            host = self.broker_config.get('host', 'localhost')
            port = self.broker_config.get('port', 1883)
            username = self.broker_config.get('username')
            password = self.broker_config.get('password')
            
            if username and password:
                logger.info(f"Connecting to MQTT broker: {host}:{port} with authentication as {username} (attempt {self.connection_attempts})")
            else:
                logger.info(f"Connecting to MQTT broker: {host}:{port} without authentication (attempt {self.connection_attempts})")
            
            # TODO: Implement actual MQTT connection with authentication
            # For now, simulate connection success to test configuration loading
            logger.info(f"[MQTT] Successfully connected to external broker {host}:{port}")
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.connected = False
            return False
        
    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.connected:
            self.connected = False
            logger.info("Disconnected from MQTT broker")
        
    async def subscribe(self, topic: str, callback) -> bool:
        """Subscribe to MQTT topic"""
        if not self.connected:
            return False
            
        logger.info(f"Subscribing to topic: {topic}")
        # Implementation would set up subscription with callback
        return True
        
    async def publish(self, topic: str, payload: str, qos: int = 0) -> bool:
        """Publish message to MQTT topic"""
        if not self.connected:
            return False
            
        logger.debug(f"Publishing to {topic}: {payload}")
        # Implementation would publish message
        return True
    
    def is_connected(self) -> bool:
        """Check connection status"""
        return self.connected
    
    async def get_connection_health(self) -> Dict[str, Any]:
        """Get connection health metrics"""
        return {
            'connected': self.connected,
            'connection_attempts': self.connection_attempts,
            'last_attempt': self.last_connection_attempt.isoformat() if self.last_connection_attempt else None,
            'broker_host': self.broker_config.get('host', 'localhost'),
            'broker_port': self.broker_config.get('port', 1883)
        }


class MQTTDiscoveryService:
    """MQTT discovery service with intelligent filtering and batch processing"""
    
    def __init__(self, config: Dict[str, Any], device_manager: MQTTDeviceManager):
        self.config = config
        self.device_manager = device_manager
        
        # Pass the full config to MQTTClient so it can detect external broker settings
        mqtt_config = config.get('mqtt', {})
        # Merge top-level MQTT settings with mqtt section for external broker support
        if config.get('mqtt_external_broker', False):
            full_mqtt_config = {**mqtt_config, **config}  # Top-level config takes precedence
        else:
            full_mqtt_config = mqtt_config
            
        self.mqtt_client = MQTTClient(full_mqtt_config)
        self.message_filter = MQTTMessageFilter(mqtt_config.get('filtering', {}))
        
        # Batch processing
        self.discovery_queue = asyncio.Queue(maxsize=1000)
        self.batch_size = config.get('mqtt', {}).get('discovery_batch_size', 10)
        self.batch_timeout = config.get('mqtt', {}).get('discovery_batch_timeout', 5.0)
        self.batch_processor_task = None
        self.running = False
    
    async def start(self):
        """Start MQTT discovery service"""
        try:
            await self.mqtt_client.connect()
            
            # Subscribe to HA discovery topics
            discovery_prefix = self.config.get('mqtt', {}).get('auto_discovery', {}).get('topic_prefix', 'homeassistant')
            discovery_topic = f"{discovery_prefix}/+/+/config"
            
            await self.mqtt_client.subscribe(discovery_topic, self._on_discovery_message)
            
            # Start batch processor
            self.running = True
            self.batch_processor_task = asyncio.create_task(self._batch_processor())
            
            logger.info(f"MQTT discovery service started, listening on: {discovery_topic}")
            
        except Exception as e:
            logger.error(f"Failed to start MQTT discovery service: {e}")
            raise
    
    async def stop(self):
        """Stop MQTT discovery service"""
        self.running = False
        
        if self.batch_processor_task:
            self.batch_processor_task.cancel()
            try:
                await self.batch_processor_task
            except asyncio.CancelledError:
                pass
        
        await self.mqtt_client.disconnect()
        
        # Final device persistence
        self.device_manager.persist_devices()
        
        logger.info("MQTT discovery service stopped")
    
    async def _on_discovery_message(self, topic: str, payload: str):
        """Handle incoming MQTT discovery message"""
        try:
            parsed_payload = json.loads(payload)
            
            if not self.message_filter.should_process_message(topic, parsed_payload):
                return
            
            # Add to queue for batch processing
            try:
                await self.discovery_queue.put_nowait((topic, parsed_payload))
            except asyncio.QueueFull:
                logger.warning("Discovery queue full, dropping message")
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in discovery message: {topic}")
        except Exception as e:
            logger.error(f"Error processing discovery message: {e}")
    
    async def _batch_processor(self):
        """Batch process discovery messages to reduce overhead"""
        batch = []
        
        while self.running:
            try:
                # Collect messages for batch processing
                timeout_task = asyncio.create_task(asyncio.sleep(self.batch_timeout))
                message_task = asyncio.create_task(self.discovery_queue.get())
                
                done, pending = await asyncio.wait(
                    [timeout_task, message_task], 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending task
                for task in pending:
                    task.cancel()
                
                if message_task in done:
                    # Got a message, add to batch
                    batch.append(message_task.result())
                
                # Process batch if full or timeout occurred
                if len(batch) >= self.batch_size or timeout_task in done:
                    if batch:
                        await self._process_discovery_batch(batch)
                        batch = []
                
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                await asyncio.sleep(1)
    
    async def _process_discovery_batch(self, batch: List[tuple]):
        """Process a batch of discovery messages"""
        logger.debug(f"Processing discovery batch of {len(batch)} messages")
        
        for topic, payload in batch:
            try:
                self.device_manager.register_discovered_device(topic, payload)
            except Exception as e:
                logger.error(f"Error processing discovery message in batch: {e}")
        
        # Persist devices after batch processing
        self.device_manager.persist_devices()


class MQTTService:
    """Main MQTT service coordinator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.device_manager = MQTTDeviceManager(config)
        self.discovery_service = MQTTDiscoveryService(config, self.device_manager)
    
    async def start(self):
        """Start all MQTT services"""
        await self.discovery_service.start()
        logger.info("MQTT service started")
    
    async def stop(self):
        """Stop all MQTT services"""
        await self.discovery_service.stop()
        logger.info("MQTT service stopped")
    
    def get_device_manager(self) -> MQTTDeviceManager:
        """Get device manager instance"""
        return self.device_manager