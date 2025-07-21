#!/usr/bin/env python3
"""
Simple MQTT Test Client for AICleaner v3 Testing
Tests basic MQTT functionality with embedded or external broker
"""

import json
import logging
import socket
import sys
import threading
import time
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleMQTTClient:
    """Simple MQTT client for testing with embedded broker"""
    
    def __init__(self, host='127.0.0.1', port=1883):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.messages_received = []
        self.running = False
    
    def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            
            # Wait for CONNACK
            response = self.socket.recv(1024).decode('utf-8')
            if 'CONNACK' in response:
                self.connected = True
                logger.info(f"✅ Connected to MQTT broker at {self.host}:{self.port}")
                
                # Start message handler thread
                self.running = True
                handler_thread = threading.Thread(target=self._message_handler, daemon=True)
                handler_thread.start()
                
                return True
            else:
                logger.error(f"Unexpected response: {response}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def _message_handler(self):
        """Handle incoming messages"""
        buffer = ""
        while self.running and self.connected:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                lines = buffer.split('\n')
                buffer = lines[-1]  # Keep incomplete line
                
                for line in lines[:-1]:
                    if line.strip():
                        self._process_message(line.strip())
            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error in message handler: {e}")
                break
    
    def _process_message(self, message: str):
        """Process received message"""
        if message.startswith('MESSAGE|'):
            parts = message.split('|', 2)
            if len(parts) >= 3:
                topic = parts[1]
                payload = parts[2]
                
                msg_record = {
                    'topic': topic,
                    'payload': payload,
                    'timestamp': datetime.now().isoformat()
                }
                self.messages_received.append(msg_record)
                
                logger.info(f"📨 Received: {topic} = {payload}")
        elif message == 'PONG':
            logger.debug("Received PONG")
    
    def subscribe(self, topic: str) -> bool:
        """Subscribe to topic"""
        if not self.connected:
            return False
        
        try:
            message = f"SUBSCRIBE|{topic}\n"
            self.socket.send(message.encode('utf-8'))
            logger.info(f"📡 Subscribed to: {topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic}: {e}")
            return False
    
    def publish(self, topic: str, payload: str, retain: bool = False) -> bool:
        """Publish message"""
        if not self.connected:
            return False
        
        try:
            retain_flag = "true" if retain else "false"
            message = f"PUBLISH|{topic}|{payload}|{retain_flag}\n"
            self.socket.send(message.encode('utf-8'))
            logger.info(f"📤 Published to {topic}: {payload}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            return False
    
    def ping(self) -> bool:
        """Send ping to broker"""
        if not self.connected:
            return False
        
        try:
            self.socket.send(b"PING|\n")
            return True
        except Exception as e:
            logger.error(f"Failed to ping: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from broker"""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        logger.info("Disconnected from MQTT broker")

def test_mqtt_basic_functionality(host='127.0.0.1', port=1883):
    """Test basic MQTT functionality"""
    logger.info("🧪 Testing Basic MQTT Functionality")
    logger.info("=" * 50)
    
    # Create client
    client = SimpleMQTTClient(host, port)
    
    # Test connection
    if not client.connect():
        logger.error("❌ Connection test failed")
        return False
    
    logger.info("✅ Connection test passed")
    
    # Test subscription
    test_topic = "test/aicleaner"
    if not client.subscribe(test_topic):
        logger.error("❌ Subscription test failed")
        client.disconnect()
        return False
    
    logger.info("✅ Subscription test passed")
    
    # Test publishing
    test_payload = json.dumps({"test": "message", "timestamp": datetime.now().isoformat()})
    if not client.publish(test_topic, test_payload):
        logger.error("❌ Publishing test failed")
        client.disconnect()
        return False
    
    logger.info("✅ Publishing test passed")
    
    # Wait for message to be received
    time.sleep(2)
    
    # Check if message was received
    received_messages = [msg for msg in client.messages_received if msg['topic'] == test_topic]
    if not received_messages:
        logger.error("❌ Message delivery test failed")
        client.disconnect()
        return False
    
    logger.info("✅ Message delivery test passed")
    
    # Test retained messages
    retain_topic = "test/retained"
    retain_payload = json.dumps({"retained": True, "timestamp": datetime.now().isoformat()})
    if not client.publish(retain_topic, retain_payload, retain=True):
        logger.error("❌ Retained message test failed")
        client.disconnect()
        return False
    
    logger.info("✅ Retained message test passed")
    
    # Test ping
    if not client.ping():
        logger.error("❌ Ping test failed")
        client.disconnect()
        return False
    
    logger.info("✅ Ping test passed")
    
    # Clean up
    client.disconnect()
    
    logger.info("=" * 50)
    logger.info("🎉 All MQTT tests passed!")
    logger.info(f"📊 Messages received: {len(client.messages_received)}")
    
    return True

def test_aicleaner_mqtt_simulation(host='127.0.0.1', port=1883):
    """Simulate AICleaner MQTT communication"""
    logger.info("🤖 Testing AICleaner MQTT Simulation")
    logger.info("=" * 50)
    
    # Create two clients - one for AICleaner, one for Home Assistant
    aicleaner_client = SimpleMQTTClient(host, port)
    ha_client = SimpleMQTTClient(host, port)
    
    # Connect both clients
    if not aicleaner_client.connect() or not ha_client.connect():
        logger.error("❌ Failed to connect clients")
        return False
    
    # HA client subscribes to discovery messages
    ha_client.subscribe("homeassistant/#")
    ha_client.subscribe("aicleaner/#")
    
    time.sleep(1)
    
    # AICleaner publishes discovery messages (retained)
    device_id = "aicleaner_v3_test"
    
    # Status sensor discovery
    status_discovery = {
        "name": "AICleaner Status",
        "unique_id": f"{device_id}_status",
        "state_topic": f"aicleaner/{device_id}/state",
        "value_template": "{{ value_json.status }}",
        "icon": "mdi:robot",
        "device": {
            "identifiers": [device_id],
            "name": "AICleaner V3",
            "manufacturer": "AICleaner Project",
            "model": "AICleaner V3 Add-on",
            "sw_version": "1.0.0"
        }
    }
    
    aicleaner_client.publish(
        f"homeassistant/sensor/{device_id}/status/config",
        json.dumps(status_discovery),
        retain=True
    )
    
    # Switch discovery
    switch_discovery = {
        "name": "AICleaner Enabled",
        "unique_id": f"{device_id}_enabled",
        "state_topic": f"aicleaner/{device_id}/state",
        "command_topic": f"aicleaner/{device_id}/set",
        "value_template": "{{ value_json.enabled }}",
        "payload_on": "ON",
        "payload_off": "OFF",
        "icon": "mdi:toggle-switch",
        "device": {
            "identifiers": [device_id],
            "name": "AICleaner V3",
            "manufacturer": "AICleaner Project",
            "model": "AICleaner V3 Add-on",
            "sw_version": "1.0.0"
        }
    }
    
    aicleaner_client.publish(
        f"homeassistant/switch/{device_id}/enabled/config",
        json.dumps(switch_discovery),
        retain=True
    )
    
    # Publish initial state
    initial_state = {
        "status": "idle",
        "enabled": "OFF",
        "timestamp": datetime.now().isoformat()
    }
    
    aicleaner_client.publish(
        f"aicleaner/{device_id}/state",
        json.dumps(initial_state),
        retain=True
    )
    
    # Wait for messages to be processed
    time.sleep(2)
    
    # Check discovery messages received
    discovery_messages = [
        msg for msg in ha_client.messages_received 
        if msg['topic'].startswith('homeassistant/')
    ]
    
    state_messages = [
        msg for msg in ha_client.messages_received 
        if '/state' in msg['topic']
    ]
    
    logger.info(f"📡 Discovery messages received: {len(discovery_messages)}")
    logger.info(f"📊 State messages received: {len(state_messages)}")
    
    # Simulate HA sending a command
    ha_client.publish(f"aicleaner/{device_id}/set", "ON")
    
    time.sleep(1)
    
    # AICleaner responds to command
    updated_state = {
        "status": "enabled",
        "enabled": "ON",
        "timestamp": datetime.now().isoformat()
    }
    
    aicleaner_client.publish(
        f"aicleaner/{device_id}/state",
        json.dumps(updated_state),
        retain=True
    )
    
    time.sleep(1)
    
    # Clean up
    aicleaner_client.disconnect()
    ha_client.disconnect()
    
    # Validate results
    success = len(discovery_messages) >= 2 and len(state_messages) >= 1
    
    if success:
        logger.info("🎉 AICleaner MQTT simulation successful!")
    else:
        logger.error("❌ AICleaner MQTT simulation failed")
    
    logger.info("=" * 50)
    return success

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple MQTT Test Client")
    parser.add_argument("--host", default="127.0.0.1", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--test", choices=["basic", "aicleaner", "all"], default="all", help="Test type")
    
    args = parser.parse_args()
    
    success = True
    
    if args.test in ["basic", "all"]:
        success &= test_mqtt_basic_functionality(args.host, args.port)
    
    if args.test in ["aicleaner", "all"]:
        success &= test_aicleaner_mqtt_simulation(args.host, args.port)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()