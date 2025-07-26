#!/usr/bin/env python3
"""
AICleaner V3 Add-on Main Application
Entry point for the Home Assistant add-on version of AICleaner V3
"""

import os
import json
import logging
import signal
import sys
import asyncio
from typing import Dict, Any, List
import paho.mqtt.client as mqtt

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
PRIMARY_API_KEY = os.getenv("PRIMARY_API_KEY")
BACKUP_API_KEYS = json.loads(os.getenv("BACKUP_API_KEYS", "[]"))
DEVICE_ID = os.getenv("DEVICE_ID", "aicleaner_v3")
DISCOVERY_PREFIX = os.getenv("MQTT_DISCOVERY_PREFIX", "homeassistant")

# MQTT Configuration
MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

# Home Assistant API
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN")
HOMEASSISTANT_API = os.getenv("HOMEASSISTANT_API", "http://supervisor/core/api")

class AICleaner:
    """Main AICleaner application class"""
    
    def __init__(self):
        self.mqtt_client = None
        self.running = True
        self.status = "starting"
        self.enabled = True
        
    def get_device_config(self) -> Dict[str, Any]:
        """Returns the device configuration payload for MQTT discovery"""
        return {
            "identifiers": [DEVICE_ID],
            "name": "AICleaner V3",
            "manufacturer": "AICleaner Project",
            "model": "AICleaner V3 Add-on",
            "sw_version": "1.0.0"
        }
    
    def register_entities(self):
        """Publishes MQTT discovery messages for all entities"""
        logger.info("Registering entities with Home Assistant via MQTT Discovery...")
        
        if not self.mqtt_client:
            logger.error("MQTT client not connected")
            return
        
        # 1. Status Sensor
        status_topic = f"{DISCOVERY_PREFIX}/sensor/{DEVICE_ID}/status/config"
        status_payload = {
            "name": "AICleaner Status",
            "unique_id": f"{DEVICE_ID}_status",
            "state_topic": f"aicleaner/{DEVICE_ID}/state",
            "value_template": "{{ value_json.status }}",
            "icon": "mdi:robot",
            "device": self.get_device_config()
        }
        self.mqtt_client.publish(status_topic, json.dumps(status_payload), retain=True)
        
        # 2. Enable/Disable Switch
        switch_topic = f"{DISCOVERY_PREFIX}/switch/{DEVICE_ID}/enabled/config"
        switch_payload = {
            "name": "AICleaner Enabled",
            "unique_id": f"{DEVICE_ID}_enabled",
            "state_topic": f"aicleaner/{DEVICE_ID}/state",
            "command_topic": f"aicleaner/{DEVICE_ID}/set",
            "value_template": "{{ value_json.enabled }}",
            "payload_on": "ON",
            "payload_off": "OFF",
            "icon": "mdi:toggle-switch",
            "device": self.get_device_config()
        }
        self.mqtt_client.publish(switch_topic, json.dumps(switch_payload), retain=True)
        
        logger.info("Entity registration complete.")
    
    def publish_state(self):
        """Publishes current state to MQTT"""
        if not self.mqtt_client:
            return
            
        state = {
            "status": self.status,
            "enabled": "ON" if self.enabled else "OFF",
            "timestamp": str(asyncio.get_event_loop().time())
        }
        
        self.mqtt_client.publish(
            f"aicleaner/{DEVICE_ID}/state",
            json.dumps(state),
            retain=True
        )
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            self.status = "connected"
            
            # Subscribe to command topic
            client.subscribe(f"aicleaner/{DEVICE_ID}/set")
            
            # Register entities and publish initial state
            self.register_entities()
            self.publish_state()
            
            self.status = "idle"
            self.publish_state()
        else:
            logger.error(f"Failed to connect to MQTT, return code {rc}")
            self.status = "error"
    
    def on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            
            logger.info(f"Received MQTT message: {topic} = {payload}")
            
            if topic == f"aicleaner/{DEVICE_ID}/set":
                if payload == "ON":
                    self.enabled = True
                    self.status = "enabled"
                    logger.info("AICleaner enabled via MQTT command")
                elif payload == "OFF":
                    self.enabled = False
                    self.status = "disabled"
                    logger.info("AICleaner disabled via MQTT command")
                
                self.publish_state()
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def setup_mqtt(self):
        """Set up MQTT client and connection"""
        if not MQTT_HOST:
            logger.error("MQTT host not configured")
            return False
        
        self.mqtt_client = mqtt.Client()
        
        # Set credentials if provided (optional for testing)
        if MQTT_USER and MQTT_PASSWORD:
            self.mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
            logger.info(f"Using MQTT authentication for user: {MQTT_USER}")
        else:
            logger.info("Using anonymous MQTT connection")
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        
        try:
            self.mqtt_client.connect(MQTT_HOST, MQTT_PORT)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Could not connect to MQTT broker at {MQTT_HOST}:{MQTT_PORT}. Error: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.status = "stopping"
        if self.mqtt_client:
            self.publish_state()
            self.mqtt_client.disconnect()
    
    async def run(self):
        """Main application loop"""
        logger.info("Starting AICleaner V3...")
        
        # Validate configuration
        if not PRIMARY_API_KEY:
            logger.error("Primary API key not configured")
            return False
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Set up MQTT connection
        if not self.setup_mqtt():
            return False
        
        logger.info("AICleaner V3 started successfully")
        
        # Main loop
        while self.running:
            try:
                # Publish periodic state updates
                self.publish_state()
                
                # Perform AI cleaning tasks (placeholder for now)
                if self.enabled and self.status not in ["error", "stopping"]:
                    # TODO: Add actual AI processing logic here
                    await asyncio.sleep(30)  # Process every 30 seconds
                else:
                    await asyncio.sleep(5)   # Check more frequently when disabled
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.status = "error"
                await asyncio.sleep(10)
        
        logger.info("AICleaner V3 stopped")
        return True

def main():
    """Main entry point"""
    logger.info("AICleaner V3 Add-on starting up...")
    
    # Validate critical configuration
    if not PRIMARY_API_KEY:
        logger.error("Primary API key is required")
        sys.exit(1)
    
    # Create and run application
    app = AICleaner()
    
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()