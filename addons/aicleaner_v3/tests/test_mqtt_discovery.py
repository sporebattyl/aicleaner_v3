import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mqtt_discovery.config import MQTTConfig
from mqtt_discovery.discovery_manager import MQTTDiscoveryManager
from mqtt_discovery.message_handler import MessageHandler
from mqtt_discovery.entity_registrar import EntityRegistrar
from mqtt_discovery.state_manager import StateManager
from mqtt_discovery.models import MQTTEntity, MQTTDevice

class TestMQTTDiscovery(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Mock Phase 4A components
        self.mock_entity_manager = MagicMock()
        self.mock_entity_manager.async_entity_exists = AsyncMock(return_value=False)
        self.mock_entity_manager.async_add_entity = AsyncMock()
        self.mock_entity_manager.async_update_state = AsyncMock()

        self.mock_performance_monitor = MagicMock()
        self.mock_performance_monitor.fire_performance_event = MagicMock()

    def tearDown(self):
        self.loop.close()

    def test_mqtt_config_initialization(self):
        """Test MQTT configuration initialization."""
        config = MQTTConfig()
        self.assertEqual(config.BROKER_ADDRESS, "localhost")
        self.assertEqual(config.BROKER_PORT, 1883)
        self.assertEqual(config.DISCOVERY_PREFIX, "homeassistant")
        self.assertEqual(config.QOS, 1)

    def test_mqtt_entity_model(self):
        """Test MQTT entity model creation."""
        config_payload = {
            "name": "Test Sensor",
            "unique_id": "test_sensor_123",
            "state_topic": "test/sensor/state"
        }
        
        entity = MQTTEntity(
            unique_id="test_sensor_123",
            component="sensor",
            config_payload=config_payload,
            state_topic="test/sensor/state"
        )
        
        self.assertEqual(entity.unique_id, "test_sensor_123")
        self.assertEqual(entity.component, "sensor")
        self.assertEqual(entity.state_topic, "test/sensor/state")
        self.assertEqual(entity.config_payload["name"], "Test Sensor")

    def test_mqtt_device_model(self):
        """Test MQTT device model creation."""
        device = MQTTDevice(
            identifiers=["device_123"],
            name="Test Device",
            model="Test Model",
            manufacturer="Test Manufacturer"
        )
        
        self.assertEqual(device.identifiers, ["device_123"])
        self.assertEqual(device.name, "Test Device")
        self.assertEqual(device.model, "Test Model")
        self.assertEqual(device.manufacturer, "Test Manufacturer")
        self.assertEqual(len(device.entities), 0)

    @patch('mqtt_discovery.client.aio_mqtt', None)
    def test_mqtt_client_import_error(self):
        """Test MQTT client handles missing aio_mqtt dependency."""
        from mqtt_discovery.client import MQTTClient
        
        config = MQTTConfig()
        message_queue = asyncio.Queue()
        client = MQTTClient(config, message_queue)
        
        async def run_test():
            with self.assertRaises(ImportError):
                await client.start()
        
        self.loop.run_until_complete(run_test())

    def test_entity_registrar_initialization(self):
        """Test EntityRegistrar initialization."""
        mock_state_manager = MagicMock()
        registrar = EntityRegistrar(self.mock_entity_manager, mock_state_manager)
        
        self.assertEqual(registrar.entity_manager, self.mock_entity_manager)
        self.assertEqual(registrar.state_manager, mock_state_manager)
        self.assertEqual(len(registrar._registered_devices), 0)

    def test_entity_registrar_missing_unique_id(self):
        """Test EntityRegistrar handles missing unique_id."""
        mock_state_manager = MagicMock()
        registrar = EntityRegistrar(self.mock_entity_manager, mock_state_manager)
        
        async def run_test():
            config_payload = {"name": "Test Sensor"}  # Missing unique_id
            await registrar.register_entity("sensor", "test_obj", config_payload)
            
            # Should not call entity_manager methods
            self.mock_entity_manager.async_entity_exists.assert_not_called()
            self.mock_entity_manager.async_add_entity.assert_not_called()
        
        self.loop.run_until_complete(run_test())

    def test_entity_registrar_existing_entity(self):
        """Test EntityRegistrar handles existing entities."""
        mock_state_manager = MagicMock()
        registrar = EntityRegistrar(self.mock_entity_manager, mock_state_manager)
        
        # Mock entity already exists
        self.mock_entity_manager.async_entity_exists.return_value = True
        
        async def run_test():
            config_payload = {"unique_id": "existing_entity", "name": "Test Sensor"}
            await registrar.register_entity("sensor", "test_obj", config_payload)
            
            # Should check existence but not add
            self.mock_entity_manager.async_entity_exists.assert_called_once_with("existing_entity")
            self.mock_entity_manager.async_add_entity.assert_not_called()
        
        self.loop.run_until_complete(run_test())

    def test_entity_registrar_successful_registration(self):
        """Test EntityRegistrar successful entity registration."""
        mock_state_manager = MagicMock()
        mock_state_manager.add_entity_subscription = AsyncMock()
        registrar = EntityRegistrar(self.mock_entity_manager, mock_state_manager)
        
        async def run_test():
            config_payload = {
                "unique_id": "new_entity",
                "name": "Test Sensor",
                "state_topic": "test/sensor/state"
            }
            await registrar.register_entity("sensor", "test_obj", config_payload)
            
            # Should register entity and subscribe to state topic
            self.mock_entity_manager.async_entity_exists.assert_called_once_with("new_entity")
            self.mock_entity_manager.async_add_entity.assert_called_once_with(config_payload)
            mock_state_manager.add_entity_subscription.assert_called_once_with("new_entity", "test/sensor/state")
        
        self.loop.run_until_complete(run_test())

    def test_state_manager_initialization(self):
        """Test StateManager initialization."""
        mock_client = MagicMock()
        state_manager = StateManager(self.mock_entity_manager, mock_client)
        
        self.assertEqual(state_manager.entity_manager, self.mock_entity_manager)
        self.assertEqual(state_manager.mqtt_client, mock_client)
        self.assertEqual(len(state_manager._state_topic_map), 0)

    def test_state_manager_add_subscription(self):
        """Test StateManager subscription handling."""
        mock_client = MagicMock()
        mock_client.subscribe = AsyncMock()
        state_manager = StateManager(self.mock_entity_manager, mock_client)
        
        async def run_test():
            await state_manager.add_entity_subscription("entity_123", "test/topic")
            
            # Should subscribe to topic and map it
            mock_client.subscribe.assert_called_once_with("test/topic")
            self.assertEqual(state_manager._state_topic_map["test/topic"], "entity_123")
        
        self.loop.run_until_complete(run_test())

    def test_state_manager_duplicate_subscription(self):
        """Test StateManager handles duplicate subscriptions."""
        mock_client = MagicMock()
        mock_client.subscribe = AsyncMock()
        state_manager = StateManager(self.mock_entity_manager, mock_client)
        
        async def run_test():
            # Add subscription twice
            await state_manager.add_entity_subscription("entity_123", "test/topic")
            await state_manager.add_entity_subscription("entity_456", "test/topic")
            
            # Should only subscribe once
            mock_client.subscribe.assert_called_once_with("test/topic")
            self.assertEqual(state_manager._state_topic_map["test/topic"], "entity_123")
        
        self.loop.run_until_complete(run_test())

    def test_state_manager_update_state(self):
        """Test StateManager state updates."""
        mock_client = MagicMock()
        state_manager = StateManager(self.mock_entity_manager, mock_client)
        
        # Pre-populate topic map
        state_manager._state_topic_map["test/topic"] = "entity_123"
        
        async def run_test():
            await state_manager.update_entity_state("test/topic", "new_state")
            
            # Should update entity state
            self.mock_entity_manager.async_update_state.assert_called_once_with("entity_123", "new_state")
        
        self.loop.run_until_complete(run_test())

    def test_state_manager_unmapped_topic(self):
        """Test StateManager handles unmapped topics."""
        mock_client = MagicMock()
        state_manager = StateManager(self.mock_entity_manager, mock_client)
        
        async def run_test():
            await state_manager.update_entity_state("unknown/topic", "new_state")
            
            # Should not update any entity
            self.mock_entity_manager.async_update_state.assert_not_called()
        
        self.loop.run_until_complete(run_test())

    def test_message_handler_initialization(self):
        """Test MessageHandler initialization."""
        config = MQTTConfig()
        queue = asyncio.Queue()
        mock_registrar = MagicMock()
        mock_state_manager = MagicMock()
        
        handler = MessageHandler(config, queue, mock_registrar, mock_state_manager)
        
        self.assertEqual(handler.config, config)
        self.assertEqual(handler.queue, queue)
        self.assertEqual(handler.registrar, mock_registrar)
        self.assertEqual(handler.state_manager, mock_state_manager)

    def test_message_handler_discovery_message(self):
        """Test MessageHandler discovery message handling."""
        config = MQTTConfig()
        queue = asyncio.Queue()
        mock_registrar = MagicMock()
        mock_registrar.register_entity = AsyncMock()
        mock_state_manager = MagicMock()
        
        handler = MessageHandler(config, queue, mock_registrar, mock_state_manager)
        
        async def run_test():
            discovery_payload = {
                "name": "Test Sensor",
                "unique_id": "test_123",
                "state_topic": "test/state"
            }
            
            await handler._handle_discovery_message(
                "homeassistant/sensor/device/temp/config",
                json.dumps(discovery_payload)
            )
            
            # Should call registrar
            mock_registrar.register_entity.assert_called_once_with("sensor", "temp", discovery_payload)
        
        self.loop.run_until_complete(run_test())

    def test_message_handler_invalid_json(self):
        """Test MessageHandler handles invalid JSON."""
        config = MQTTConfig()
        queue = asyncio.Queue()
        mock_registrar = MagicMock()
        mock_registrar.register_entity = AsyncMock()
        mock_state_manager = MagicMock()
        
        handler = MessageHandler(config, queue, mock_registrar, mock_state_manager)
        
        async def run_test():
            await handler._handle_discovery_message(
                "homeassistant/sensor/device/temp/config",
                "invalid json"
            )
            
            # Should not call registrar
            mock_registrar.register_entity.assert_not_called()
        
        self.loop.run_until_complete(run_test())

    def test_message_handler_empty_payload(self):
        """Test MessageHandler handles empty payload."""
        config = MQTTConfig()
        queue = asyncio.Queue()
        mock_registrar = MagicMock()
        mock_registrar.register_entity = AsyncMock()
        mock_state_manager = MagicMock()
        
        handler = MessageHandler(config, queue, mock_registrar, mock_state_manager)
        
        async def run_test():
            await handler._handle_discovery_message(
                "homeassistant/sensor/device/temp/config",
                ""
            )
            
            # Should not call registrar
            mock_registrar.register_entity.assert_not_called()
        
        self.loop.run_until_complete(run_test())

    def test_message_handler_queue_stats(self):
        """Test MessageHandler queue statistics."""
        config = MQTTConfig()
        queue = asyncio.Queue()
        mock_registrar = MagicMock()
        mock_state_manager = MagicMock()
        
        handler = MessageHandler(config, queue, mock_registrar, mock_state_manager)
        
        async def run_test():
            stats = await handler.get_queue_stats()
            
            # Should return queue statistics
            self.assertIn("queue_size", stats)
            self.assertIn("queue_empty", stats)
            self.assertIn("queue_full", stats)
            self.assertTrue(stats["queue_empty"])
            self.assertEqual(stats["queue_size"], 0)
        
        self.loop.run_until_complete(run_test())

    @patch('mqtt_discovery.client.MQTTClient')
    def test_discovery_manager_initialization(self, MockMQTTClient):
        """Test MQTTDiscoveryManager initialization."""
        manager = MQTTDiscoveryManager(self.mock_entity_manager, self.mock_performance_monitor)
        
        self.assertIsInstance(manager.config, MQTTConfig)
        self.assertFalse(manager.is_running())

    @patch('mqtt_discovery.client.MQTTClient')
    def test_discovery_manager_start_stop(self, MockMQTTClient):
        """Test MQTTDiscoveryManager start and stop lifecycle."""
        mock_client_instance = MockMQTTClient.return_value
        mock_client_instance.start = AsyncMock()
        mock_client_instance.stop = AsyncMock()
        mock_client_instance.subscribe = AsyncMock()
        
        manager = MQTTDiscoveryManager(self.mock_entity_manager, self.mock_performance_monitor)
        
        async def run_test():
            # Test start
            await manager.start()
            self.assertTrue(manager.is_running())
            
            # Test stop
            await manager.stop()
            self.assertFalse(manager.is_running())
        
        self.loop.run_until_complete(run_test())

    @patch('mqtt_discovery.client.MQTTClient')
    def test_discovery_manager_status(self, MockMQTTClient):
        """Test MQTTDiscoveryManager status reporting."""
        mock_client_instance = MockMQTTClient.return_value
        mock_client_instance.start = AsyncMock()
        mock_client_instance.subscribe = AsyncMock()
        
        manager = MQTTDiscoveryManager(self.mock_entity_manager, self.mock_performance_monitor)
        
        async def run_test():
            await manager.start()
            status = await manager.get_status()
            
            # Should return comprehensive status
            self.assertIn("running", status)
            self.assertIn("broker_address", status)
            self.assertIn("broker_port", status)
            self.assertIn("discovery_prefix", status)
            self.assertIn("queue_stats", status)
            self.assertIn("registered_devices_count", status)
            self.assertIn("total_entities", status)
            
            self.assertTrue(status["running"])
            self.assertEqual(status["broker_address"], "localhost")
            self.assertEqual(status["broker_port"], 1883)
            self.assertEqual(status["discovery_prefix"], "homeassistant")
            
            await manager.stop()
        
        self.loop.run_until_complete(run_test())

    @patch('mqtt_discovery.client.MQTTClient')
    def test_discovery_manager_restart(self, MockMQTTClient):
        """Test MQTTDiscoveryManager restart functionality."""
        mock_client_instance = MockMQTTClient.return_value
        mock_client_instance.start = AsyncMock()
        mock_client_instance.stop = AsyncMock()
        mock_client_instance.subscribe = AsyncMock()
        
        manager = MQTTDiscoveryManager(self.mock_entity_manager, self.mock_performance_monitor)
        
        async def run_test():
            await manager.start()
            self.assertTrue(manager.is_running())
            
            await manager.restart()
            self.assertTrue(manager.is_running())
            
            # Should have called stop and start
            self.assertEqual(mock_client_instance.stop.call_count, 2)  # stop + restart
            self.assertEqual(mock_client_instance.start.call_count, 2)  # start + restart
            
            await manager.stop()
        
        self.loop.run_until_complete(run_test())

if __name__ == '__main__':
    unittest.main()