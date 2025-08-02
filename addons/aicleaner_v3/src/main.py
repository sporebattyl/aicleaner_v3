#!/usr/bin/env python3
"""
AICleaner V3 Add-on Enhanced Main Application
Entry point with enhanced web UI for configuration
"""

import os
import json
import logging
import signal
import sys
import asyncio
from typing import Dict, Any, List
import paho.mqtt.client as mqtt

# Try to import the enhanced web UI
try:
    from web_ui_enhanced import EnhancedWebUI
    HAS_ENHANCED_UI = True
except ImportError:
    HAS_ENHANCED_UI = False
    logging.warning("Enhanced web UI not available, falling back to basic functionality")

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

class EnhancedAICleaner:
    """Enhanced AICleaner application class with web UI"""
    
    def __init__(self):
        self.mqtt_client = None
        self.running = True
        self.status = "starting"
        self.enabled = True
        self.ai_response_count = 0
        self.last_ai_request = None
        self.web_ui = None
        
        # Initialize enhanced web UI if available
        if HAS_ENHANCED_UI:
            self.web_ui = EnhancedWebUI(self)
            logger.info("Enhanced web UI initialized")
        
    def load_addon_options(self) -> Dict[str, Any]:
        """Load addon options from /data/options.json"""
        options_file = '/data/options.json'
        if os.path.exists(options_file):
            try:
                with open(options_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading options.json: {e}")
        return {}
        
    def get_device_config(self) -> Dict[str, Any]:
        """Returns the device configuration payload for MQTT discovery"""
        return {
            "identifiers": [DEVICE_ID],
            "name": "AICleaner V3",
            "manufacturer": "AICleaner Project",
            "model": "AICleaner V3 Enhanced Add-on",
            "sw_version": "1.1.0-enhanced"
        }
    
    def register_entities(self):
        """Publishes MQTT discovery messages for all entities"""
        logger.info("Registering entities with Home Assistant via MQTT Discovery...")
        
        if not self.mqtt_client:
            logger.error("MQTT client not connected")
            return
        
        # Load addon options to get configured entities
        options = self.load_addon_options()
        default_camera = options.get('default_camera', '')
        default_todo_list = options.get('default_todo_list', '')
        
        logger.info(f"Configured entities - Camera: {default_camera}, Todo: {default_todo_list}")
        
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
        
        # 3. Configuration Status Sensor
        config_topic = f"{DISCOVERY_PREFIX}/sensor/{DEVICE_ID}/config_status/config"
        config_payload = {
            "name": "AICleaner Configuration Status",
            "unique_id": f"{DEVICE_ID}_config_status",
            "state_topic": f"aicleaner/{DEVICE_ID}/config",
            "value_template": "{{ value_json.status }}",
            "icon": "mdi:cog",
            "device": self.get_device_config()
        }
        self.mqtt_client.publish(config_topic, json.dumps(config_payload), retain=True)
        
        logger.info("Entity registration complete.")
    
    def publish_state(self):
        """Publishes current state to MQTT"""
        if not self.mqtt_client:
            return
            
        # Load current configuration
        options = self.load_addon_options()
        
        state = {
            "status": self.status,
            "enabled": "ON" if self.enabled else "OFF",
            "timestamp": str(asyncio.get_event_loop().time())
        }
        
        config_state = {
            "status": "configured" if options.get('default_camera') and options.get('default_todo_list') else "needs_configuration",
            "camera": options.get('default_camera', ''),
            "todo_list": options.get('default_todo_list', ''),
            "timestamp": str(asyncio.get_event_loop().time())
        }
        
        self.mqtt_client.publish(
            f"aicleaner/{DEVICE_ID}/state",
            json.dumps(state),
            retain=True
        )
        
        self.mqtt_client.publish(
            f"aicleaner/{DEVICE_ID}/config",
            json.dumps(config_state),
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
        """Set up MQTT client and connection with graceful fallbacks"""
        if not MQTT_HOST or MQTT_HOST.strip() == "":
            logger.warning("🔌 MQTT host not configured - entity discovery disabled")
            logger.info("📋 To enable MQTT features:")
            logger.info("  1. Install 'Mosquitto broker' addon")
            logger.info("  2. Configure MQTT integration in Home Assistant")
            logger.info("  3. Restart this addon")
            logger.info("🔄 Addon will continue with local functionality only")
            return False
        
        try:
            self.mqtt_client = mqtt.Client()
            
            # Set credentials if provided (optional for testing)
            if MQTT_USER and MQTT_PASSWORD:
                self.mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
                logger.info(f"🔐 Using MQTT authentication for user: {MQTT_USER}")
            else:
                logger.info("🔓 Using anonymous MQTT connection")
            
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            
            # Set connection timeouts for faster failure detection
            self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            logger.info(f"🔗 MQTT connection established to {MQTT_HOST}:{MQTT_PORT}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Could not connect to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
            logger.error(f"📄 Error details: {e}")
            logger.warning("🔄 Continuing with reduced functionality (no entity discovery)")
            self.mqtt_client = None
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.status = "stopping"
        if self.mqtt_client:
            self.publish_state()
            self.mqtt_client.disconnect()
    
    async def start_web_ui(self):
        """Start the enhanced web UI server"""
        if self.web_ui:
            try:
                await self.web_ui.start_server(host='0.0.0.0', port=8080)
            except Exception as e:
                logger.error(f"Failed to start web UI: {e}")
    
    async def run(self):
        """Main application loop"""
        logger.info("Starting Enhanced AICleaner V3...")
        
        # Start web UI server if available
        if self.web_ui:
            web_task = asyncio.create_task(self.start_web_ui())
            logger.info("Web UI server task created")
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Set up MQTT connection
        mqtt_available = self.setup_mqtt()
        if mqtt_available:
            logger.info("✅ Full functionality available (MQTT + AI + Web UI)")
        else:
            logger.info("⚠️  Limited functionality (Web UI + AI only, no entity discovery)")
        
        logger.info("🚀 Enhanced AICleaner V3 started successfully")
        
        # Main loop
        while self.running:
            try:
                # Publish periodic state updates
                if self.mqtt_client:
                    self.publish_state()
                
                # Check configuration status
                options = self.load_addon_options()
                has_camera = bool(options.get('default_camera', '').strip())
                has_todo = bool(options.get('default_todo_list', '').strip())
                
                if has_camera and has_todo:
                    # Perform AI cleaning tasks (placeholder for now)
                    if self.enabled and self.status not in ["error", "stopping"]:
                        logger.debug(f"✅ Active monitoring: camera={options['default_camera']}, todo={options['default_todo_list']}")
                        await asyncio.sleep(30)  # Process every 30 seconds
                    else:
                        logger.debug("⏸️  Addon disabled - monitoring paused")
                        await asyncio.sleep(5)   # Check more frequently when disabled
                else:
                    # Provide helpful configuration guidance
                    missing = []
                    if not has_camera:
                        missing.append("camera entity")
                    if not has_todo:
                        missing.append("todo list entity")
                    
                    logger.info(f"⚙️  Configuration needed: missing {' and '.join(missing)}")
                    logger.info("🌐 Please visit the web interface to configure entities")
                    
                    if self.mqtt_client:
                        logger.debug("📡 MQTT available - entities will auto-register once configured")
                    else:
                        logger.debug("🔌 MQTT unavailable - manual entity configuration required")
                    
                    await asyncio.sleep(15)  # Check configuration less frequently
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.status = "error"
                await asyncio.sleep(10)
        
        logger.info("Enhanced AICleaner V3 stopped")
        return True

def main():
    """Main entry point"""
    logger.info("Enhanced AICleaner V3 Add-on starting up...")
    
    # Create and run enhanced application
    app = EnhancedAICleaner()
    
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()