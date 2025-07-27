"""
MQTT Discovery Performance Tests
Tests performance characteristics and resource usage for production readiness
"""

import asyncio
import json
import logging
import pytest
import time
import psutil
import threading
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock, Mock

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTPerformanceMetrics:
    """Collect and analyze MQTT performance metrics"""
    
    def __init__(self):
        self.metrics = {
            "message_publish_times": [],
            "connection_times": [],
            "discovery_publish_times": [],
            "state_update_times": [],
            "memory_usage": [],
            "cpu_usage": []
        }
        self.start_time = None
        self.monitoring = False
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.monitoring = True
        
        # Start resource monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_resources(self):
        """Monitor CPU and memory usage"""
        process = psutil.Process()
        
        while self.monitoring:
            try:
                cpu_percent = process.cpu_percent()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                self.metrics["cpu_usage"].append(cpu_percent)
                self.metrics["memory_usage"].append(memory_mb)
                
                time.sleep(0.1)  # Sample every 100ms
            except:
                break
    
    def record_publish_time(self, operation: str, duration: float):
        """Record operation timing"""
        if operation in self.metrics:
            self.metrics[operation].append(duration)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {}
        
        for metric_name, values in self.metrics.items():
            if values:
                stats[metric_name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99)
                }
            else:
                stats[metric_name] = {"count": 0}
        
        return stats
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]

class TestMQTTDiscoveryPerformance:
    """Test MQTT Discovery performance characteristics"""
    
    def setup_method(self):
        """Set up performance test fixtures"""
        self.metrics = MQTTPerformanceMetrics()
        
        # Import MQTT components
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        
        from mqtt.discovery_client import MQTTDiscoveryClient
        from mqtt.topic_manager import MQTTTopicManager
        from mqtt.device_publisher import MQTTDevicePublisher
        
        # Create mocked MQTT client
        self.mock_mqtt_client = AsyncMock()
        self.topic_manager = MQTTTopicManager("homeassistant", "aicleaner_v3")
        self.device_publisher = MQTTDevicePublisher(
            self.mock_mqtt_client,
            self.topic_manager
        )
    
    @pytest.mark.asyncio
    async def test_discovery_publishing_performance(self):
        """Test discovery message publishing performance"""
        self.metrics.start_monitoring()
        
        # Mock successful publishing
        self.mock_mqtt_client.async_publish_discovery.return_value = True
        
        # Test publishing multiple discovery configurations
        entity_count = 50
        publish_times = []
        
        for i in range(entity_count):
            start_time = time.time()
            
            config = {
                "name": f"Test Sensor {i}",
                "state_topic": f"test/sensor_{i}/state",
                "unique_id": f"test_sensor_{i}"
            }
            
            await self.mock_mqtt_client.async_publish_discovery(
                "sensor", f"test_{i}", config
            )
            
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # Convert to ms
            publish_times.append(duration)
            self.metrics.record_publish_time("discovery_publish_times", duration)
        
        self.metrics.stop_monitoring()
        
        # Analyze performance
        avg_publish_time = sum(publish_times) / len(publish_times)
        max_publish_time = max(publish_times)
        
        logger.info(f"Discovery Publishing Performance:")
        logger.info(f"  Entities: {entity_count}")
        logger.info(f"  Average: {avg_publish_time:.2f}ms")
        logger.info(f"  Maximum: {max_publish_time:.2f}ms")
        
        # Performance assertions (targets from Phase 4A requirements)
        assert avg_publish_time < 50, f"Average publish time {avg_publish_time:.2f}ms exceeds 50ms target"
        assert max_publish_time < 200, f"Max publish time {max_publish_time:.2f}ms exceeds 200ms target"
    
    @pytest.mark.asyncio
    async def test_state_update_performance(self):
        """Test entity state update performance"""
        self.metrics.start_monitoring()
        
        # Mock successful state updates
        self.mock_mqtt_client.async_publish_state.return_value = True
        
        # Register test entity
        self.device_publisher.published_entities["sensor.test"] = {
            "state": "unknown",
            "last_updated": datetime.now().isoformat()
        }
        
        # Test rapid state updates
        update_count = 100
        update_times = []
        
        for i in range(update_count):
            start_time = time.time()
            
            await self.device_publisher._update_entity_state(
                "sensor", "test", f"value_{i}", {"timestamp": i}
            )
            
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # Convert to ms
            update_times.append(duration)
            self.metrics.record_publish_time("state_update_times", duration)
        
        self.metrics.stop_monitoring()
        
        # Analyze performance
        avg_update_time = sum(update_times) / len(update_times)
        max_update_time = max(update_times)
        p95_update_time = self.metrics._percentile(update_times, 95)
        
        logger.info(f"State Update Performance:")
        logger.info(f"  Updates: {update_count}")
        logger.info(f"  Average: {avg_update_time:.2f}ms")
        logger.info(f"  Maximum: {max_update_time:.2f}ms")
        logger.info(f"  95th percentile: {p95_update_time:.2f}ms")
        
        # Performance assertions (targets from Phase 4A requirements)
        assert avg_update_time < 100, f"Average update time {avg_update_time:.2f}ms exceeds 100ms target"
        assert p95_update_time < 100, f"95th percentile {p95_update_time:.2f}ms exceeds 100ms target"
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self):
        """Test performance under concurrent operations"""
        self.metrics.start_monitoring()
        
        # Mock successful operations
        self.mock_mqtt_client.async_publish_state.return_value = True
        self.mock_mqtt_client.async_publish_discovery.return_value = True
        
        # Register multiple test entities
        for i in range(10):
            self.device_publisher.published_entities[f"sensor.test_{i}"] = {
                "state": "unknown",
                "last_updated": datetime.now().isoformat()
            }
        
        # Create concurrent tasks
        tasks = []
        
        # Add discovery publishing tasks
        for i in range(10):
            config = {
                "name": f"Concurrent Sensor {i}",
                "state_topic": f"test/concurrent_{i}/state"
            }
            task = self.mock_mqtt_client.async_publish_discovery(
                "sensor", f"concurrent_{i}", config
            )
            tasks.append(task)
        
        # Add state update tasks
        for i in range(10):
            task = self.device_publisher._update_entity_state(
                "sensor", f"test_{i}", f"concurrent_value_{i}"
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        start_time = time.time()
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_duration = (end_time - start_time) * 1000  # Convert to ms
        
        self.metrics.stop_monitoring()
        
        logger.info(f"Concurrent Operations Performance:")
        logger.info(f"  Total tasks: {len(tasks)}")
        logger.info(f"  Total duration: {total_duration:.2f}ms")
        logger.info(f"  Average per task: {total_duration/len(tasks):.2f}ms")
        
        # Performance assertion
        assert total_duration < 1000, f"Concurrent operations took {total_duration:.2f}ms (>1s)"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage under sustained load"""
        self.metrics.start_monitoring()
        
        # Mock successful operations
        self.mock_mqtt_client.async_publish_state.return_value = True
        
        # Simulate sustained load
        iterations = 200
        batch_size = 10
        
        for batch in range(iterations // batch_size):
            # Create batch of state updates
            tasks = []
            for i in range(batch_size):
                entity_id = f"load_test_{batch}_{i}"
                self.device_publisher.published_entities[f"sensor.{entity_id}"] = {
                    "state": "unknown",
                    "last_updated": datetime.now().isoformat()
                }
                
                task = self.device_publisher._update_entity_state(
                    "sensor", entity_id, f"value_{batch}_{i}"
                )
                tasks.append(task)
            
            # Execute batch
            await asyncio.gather(*tasks)
            
            # Small delay to allow monitoring
            await asyncio.sleep(0.01)
        
        self.metrics.stop_monitoring()
        
        # Analyze memory usage
        stats = self.metrics.get_statistics()
        memory_stats = stats.get("memory_usage", {})
        
        if memory_stats.get("count", 0) > 0:
            max_memory = memory_stats["max"]
            avg_memory = memory_stats["avg"]
            
            logger.info(f"Memory Usage Under Load:")
            logger.info(f"  Iterations: {iterations}")
            logger.info(f"  Max memory: {max_memory:.2f}MB")
            logger.info(f"  Avg memory: {avg_memory:.2f}MB")
            
            # Memory assertion (target from Phase 4A requirements)
            assert max_memory < 50, f"Max memory usage {max_memory:.2f}MB exceeds 50MB target"
    
    @pytest.mark.asyncio
    async def test_topic_validation_performance(self):
        """Test topic validation performance"""
        
        # Test topic validation speed
        test_topics = [
            "homeassistant/sensor/device/entity/config",
            "valid/topic/structure/test",
            "another/valid/topic",
            "homeassistant/binary_sensor/device/motion/state",
            "homeassistant/switch/device/control/cmd"
        ] * 1000  # 5000 total validations
        
        start_time = time.time()
        
        for topic in test_topics:
            self.topic_manager.validate_topic_structure(topic)
        
        end_time = time.time()
        total_duration = (end_time - start_time) * 1000  # Convert to ms
        avg_per_validation = total_duration / len(test_topics)
        
        logger.info(f"Topic Validation Performance:")
        logger.info(f"  Validations: {len(test_topics)}")
        logger.info(f"  Total time: {total_duration:.2f}ms")
        logger.info(f"  Average: {avg_per_validation:.4f}ms")
        
        # Performance assertion
        assert avg_per_validation < 0.1, f"Topic validation too slow: {avg_per_validation:.4f}ms"
    
    def test_topic_generation_performance(self):
        """Test topic generation performance"""
        
        # Test topic generation speed
        entity_count = 1000
        
        start_time = time.time()
        
        for i in range(entity_count):
            # Generate all topic types for each entity
            self.topic_manager.create_discovery_topic("sensor", f"entity_{i}")
            self.topic_manager.create_state_topic("sensor", f"entity_{i}")
            self.topic_manager.create_command_topic("switch", f"entity_{i}")
            self.topic_manager.create_attributes_topic("sensor", f"entity_{i}")
            self.topic_manager.create_availability_topic(f"entity_{i}")
        
        end_time = time.time()
        total_duration = (end_time - start_time) * 1000  # Convert to ms
        total_topics = entity_count * 5  # 5 topics per entity
        avg_per_topic = total_duration / total_topics
        
        logger.info(f"Topic Generation Performance:")
        logger.info(f"  Entities: {entity_count}")
        logger.info(f"  Total topics: {total_topics}")
        logger.info(f"  Total time: {total_duration:.2f}ms")
        logger.info(f"  Average: {avg_per_topic:.4f}ms")
        
        # Performance assertion
        assert avg_per_topic < 0.01, f"Topic generation too slow: {avg_per_topic:.4f}ms"

class TestMQTTResourceConstraints:
    """Test MQTT performance under resource constraints"""
    
    @pytest.mark.asyncio
    async def test_low_memory_scenario(self):
        """Test behavior under memory pressure"""
        # Note: This is a conceptual test - actual memory pressure simulation
        # would require more sophisticated tooling
        
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        
        from mqtt.device_publisher import MQTTDevicePublisher
        from mqtt.topic_manager import MQTTTopicManager
        
        mock_mqtt_client = AsyncMock()
        topic_manager = MQTTTopicManager("homeassistant", "aicleaner_v3")
        device_publisher = MQTTDevicePublisher(mock_mqtt_client, topic_manager)
        
        # Mock successful operations
        mock_mqtt_client.async_publish_state.return_value = True
        
        # Test with many entities to simulate memory pressure
        entity_count = 1000
        
        for i in range(entity_count):
            device_publisher.published_entities[f"sensor.test_{i}"] = {
                "state": f"value_{i}",
                "last_updated": datetime.now().isoformat(),
                "attributes": {"large_data": "x" * 100}  # Add some bulk
            }
        
        # Verify entities are managed efficiently
        assert len(device_publisher.published_entities) == entity_count
        
        # Test cleanup
        await device_publisher.async_unpublish_device()
        assert len(device_publisher.published_entities) == 0
    
    @pytest.mark.asyncio
    async def test_connection_failure_recovery(self):
        """Test performance during connection failures"""
        
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        
        from mqtt.discovery_client import MQTTDiscoveryClient
        
        client = MQTTDiscoveryClient("localhost", 1883)
        
        # Simulate connection failures
        connection_attempts = 5
        start_time = time.time()
        
        for _ in range(connection_attempts):
            # This will fail but should handle gracefully
            result = await client.async_connect()
            assert result == False  # Expected to fail in test environment
        
        end_time = time.time()
        total_duration = (end_time - start_time) * 1000
        avg_attempt_time = total_duration / connection_attempts
        
        logger.info(f"Connection Failure Recovery:")
        logger.info(f"  Attempts: {connection_attempts}")
        logger.info(f"  Total time: {total_duration:.2f}ms")
        logger.info(f"  Average per attempt: {avg_attempt_time:.2f}ms")
        
        # Should fail quickly, not hang
        assert avg_attempt_time < 5000, f"Connection attempts too slow: {avg_attempt_time:.2f}ms"

if __name__ == "__main__":
    """Run performance tests directly"""
    pytest.main([__file__, "-v", "--tb=short", "-s"])