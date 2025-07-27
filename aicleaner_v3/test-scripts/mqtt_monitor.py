#!/usr/bin/env python3
"""
MQTT Monitor for AICleaner v3 Testing
Monitors MQTT messages for validation and debugging
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any, List
import paho.mqtt.client as mqtt
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MQTTMonitor:
    """MQTT message monitor for testing validation"""
    
    def __init__(self, host='mosquitto-test', port=1883, username='aicleaner', password='test_password'):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        
        self.client = None
        self.running = True
        self.messages = []
        self.discovery_messages = {}
        self.state_messages = {}
        
        # Statistics
        self.stats = {
            'total_messages': 0,
            'discovery_messages': 0,
            'state_messages': 0,
            'command_messages': 0,
            'other_messages': 0,
            'start_time': datetime.now()
        }
    
    def setup_client(self):
        """Set up MQTT client"""
        self.client = mqtt.Client()
        
        # Set credentials
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        return self.client
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
            
            # Subscribe to all topics for comprehensive monitoring
            subscriptions = [
                ("homeassistant/#", 0),      # HA Discovery
                ("aicleaner/#", 0),          # AICleaner topics
                ("$SYS/#", 0),              # Broker system topics
                ("+/+/+", 0),               # Catch-all for other patterns
            ]
            
            for topic, qos in subscriptions:
                client.subscribe(topic, qos)
                logger.info(f"Subscribed to topic: {topic}")
                
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")
            self.running = False
    
    def on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        logger.warning(f"Disconnected from MQTT broker, return code {rc}")
    
    def on_message(self, client, userdata, msg):
        """Callback for MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            timestamp = datetime.now().isoformat()
            
            # Create message record
            message_record = {
                'timestamp': timestamp,
                'topic': topic,
                'payload': payload,
                'qos': msg.qos,
                'retain': msg.retain
            }
            
            # Store message
            self.messages.append(message_record)
            
            # Update statistics
            self.stats['total_messages'] += 1
            
            # Categorize and process messages
            self.categorize_message(message_record)
            
            # Print formatted message
            self.print_message(message_record)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def categorize_message(self, message: Dict[str, Any]):
        """Categorize and store messages by type"""
        topic = message['topic']
        payload = message['payload']
        
        try:
            # Home Assistant Discovery messages
            if topic.startswith('homeassistant/'):
                self.stats['discovery_messages'] += 1
                
                # Try to parse as JSON for discovery messages
                try:
                    discovery_data = json.loads(payload)
                    self.discovery_messages[topic] = {
                        'timestamp': message['timestamp'],
                        'data': discovery_data
                    }
                    logger.info(f"📡 Discovery message: {topic}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in discovery message: {topic}")
            
            # AICleaner state messages
            elif topic.startswith('aicleaner/') and '/state' in topic:
                self.stats['state_messages'] += 1
                
                try:
                    state_data = json.loads(payload)
                    self.state_messages[topic] = {
                        'timestamp': message['timestamp'],
                        'data': state_data
                    }
                    logger.info(f"📊 State update: {topic}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in state message: {topic}")
            
            # AICleaner command messages
            elif topic.startswith('aicleaner/') and '/set' in topic:
                self.stats['command_messages'] += 1
                logger.info(f"⚡ Command message: {topic} = {payload}")
            
            # Other messages
            else:
                self.stats['other_messages'] += 1
                
        except Exception as e:
            logger.error(f"Error categorizing message: {e}")
    
    def print_message(self, message: Dict[str, Any]):
        """Print formatted message to console"""
        topic = message['topic']
        payload = message['payload']
        timestamp = message['timestamp']
        
        # Different formatting for different message types
        if topic.startswith('homeassistant/'):
            print(f"🏠 [{timestamp}] DISCOVERY: {topic}")
            try:
                data = json.loads(payload)
                print(f"   📋 {json.dumps(data, indent=2)}")
            except:
                print(f"   📋 {payload}")
        
        elif topic.startswith('aicleaner/'):
            print(f"🤖 [{timestamp}] AICLEANER: {topic}")
            try:
                data = json.loads(payload)
                print(f"   📊 {json.dumps(data, indent=2)}")
            except:
                print(f"   📊 {payload}")
        
        elif topic.startswith('$SYS/'):
            # System messages - less verbose
            print(f"🔧 [{timestamp}] SYSTEM: {topic} = {payload}")
        
        else:
            print(f"📨 [{timestamp}] OTHER: {topic} = {payload}")
        
        print()  # Empty line for readability
    
    def print_stats(self):
        """Print monitoring statistics"""
        uptime = datetime.now() - self.stats['start_time']
        
        print("=" * 60)
        print("📈 MQTT MONITOR STATISTICS")
        print("=" * 60)
        print(f"⏱️  Uptime: {uptime}")
        print(f"📊 Total Messages: {self.stats['total_messages']}")
        print(f"🏠 Discovery Messages: {self.stats['discovery_messages']}")
        print(f"📡 State Messages: {self.stats['state_messages']}")
        print(f"⚡ Command Messages: {self.stats['command_messages']}")
        print(f"📨 Other Messages: {self.stats['other_messages']}")
        print(f"🤖 AICleaner Devices: {len(self.discovery_messages)}")
        print("=" * 60)
        print()
    
    def get_validation_data(self) -> Dict[str, Any]:
        """Get data for test validation"""
        return {
            'stats': self.stats.copy(),
            'discovery_messages': self.discovery_messages.copy(),
            'state_messages': self.state_messages.copy(),
            'recent_messages': self.messages[-50:] if self.messages else []
        }
    
    def run(self):
        """Main monitoring loop"""
        logger.info("Starting MQTT Monitor...")
        logger.info(f"Connecting to MQTT broker at {self.host}:{self.port}")
        
        # Install paho-mqtt dependency
        import subprocess
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'paho-mqtt'], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("paho-mqtt dependency installed")
        except subprocess.CalledProcessError:
            logger.warning("Could not install paho-mqtt - assuming it's already available")
        
        # Set up client
        if not self.setup_client():
            logger.error("Failed to set up MQTT client")
            return False
        
        try:
            # Connect to broker
            self.client.connect(self.host, self.port, keepalive=60)
            
            # Start network loop in separate thread
            self.client.loop_start()
            
            logger.info("MQTT Monitor started successfully")
            logger.info("Monitoring all MQTT traffic...")
            
            # Main monitoring loop
            stats_interval = 30  # Print stats every 30 seconds
            last_stats = time.time()
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    # Print periodic statistics
                    if current_time - last_stats >= stats_interval:
                        self.print_stats()
                        last_stats = current_time
                    
                    time.sleep(1)
                    
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt")
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(5)
        
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
        
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
            logger.info("MQTT Monitor stopped")
        
        return True

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get configuration from environment
    mqtt_host = os.getenv('MQTT_HOST', 'mosquitto-test')
    mqtt_port = int(os.getenv('MQTT_PORT', 1883))
    mqtt_user = os.getenv('MQTT_USER', 'aicleaner')
    mqtt_password = os.getenv('MQTT_PASSWORD', 'test_password')
    
    logger.info(f"MQTT Configuration: {mqtt_host}:{mqtt_port} (user: {mqtt_user})")
    
    # Create and run monitor
    monitor = MQTTMonitor(mqtt_host, mqtt_port, mqtt_user, mqtt_password)
    
    try:
        monitor.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()