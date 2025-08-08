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

# Robust environment variable helpers for HA addon development
def get_int_env(key: str, default: int) -> int:
    """Get integer environment variable with robust handling of empty strings.
    
    Args:
        key: Environment variable name
        default: Default value if variable is unset or empty
        
    Returns:
        Integer value from environment or default
        
    Raises:
        ValueError: If variable is set but cannot be converted to int
    """
    value = os.getenv(key)
    if not value or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value for {key}='{value}', using default {default}")
        return default

def get_str_env(key: str, default: str = "") -> str:
    """Get string environment variable with empty string handling.
    
    Args:
        key: Environment variable name  
        default: Default value if variable is unset or empty
        
    Returns:
        String value from environment or default
    """
    value = os.getenv(key)
    return value if value and value.strip() else default

def get_json_env(key: str, default: str = "[]") -> any:
    """Get JSON environment variable with robust error handling.
    
    Args:
        key: Environment variable name
        default: Default JSON string if variable is unset or empty
        
    Returns:
        Parsed JSON value from environment or default
    """
    value = os.getenv(key)
    if not value or not value.strip():
        return json.loads(default)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON value for {key}='{value}', using default {default}")
        return json.loads(default)

# Try to import the enhanced web UI
try:
    from web_ui_enhanced import EnhancedWebUI
    HAS_ENHANCED_UI = True
except ImportError:
    HAS_ENHANCED_UI = False
    logging.warning("Enhanced web UI not available, falling back to basic functionality")

# Configure logging
logger = logging.getLogger(__name__)

# Configuration from environment variables with comprehensive validation
logger.info("[MAIN] Loading configuration from environment variables...")

# Debug: Show all environment variables for configuration debugging
config_env_vars = [
    "PRIMARY_API_KEY", "BACKUP_API_KEYS", "DEVICE_ID", "MQTT_DISCOVERY_PREFIX",
    "MQTT_HOST", "MQTT_PORT", "MQTT_USER", "MQTT_PASSWORD", "LOG_LEVEL",
    "DEBUG_MODE", "AUTO_DASHBOARD", "SUPERVISOR_TOKEN", "HOMEASSISTANT_API"
]

logger.info("[MAIN] Environment variables status:")
for var in config_env_vars:
    value = os.getenv(var)
    if var in ["PRIMARY_API_KEY", "BACKUP_API_KEYS", "MQTT_PASSWORD", "SUPERVISOR_TOKEN"]:
        logger.info(f"[MAIN]   {var}: {'***SET***' if value else '***NOT SET***'}")
    else:
        logger.info(f"[MAIN]   {var}: {value if value else '***NOT SET***'}")

# Configuration loading with validation
PRIMARY_API_KEY = os.getenv("PRIMARY_API_KEY")
if PRIMARY_API_KEY:
    logger.info(f"[MAIN] ✓ Primary API key loaded (length: {len(PRIMARY_API_KEY)})")
else:
    logger.info("[MAIN] ⚠️  No primary API key - will use Ollama fallback")

BACKUP_API_KEYS = get_json_env("BACKUP_API_KEYS", "[]")
if isinstance(BACKUP_API_KEYS, list) and len(BACKUP_API_KEYS) > 0:
    logger.info(f"[MAIN] ✓ Backup API keys loaded: {len(BACKUP_API_KEYS)} keys")
else:
    logger.info("[MAIN] ℹ️  No backup API keys configured")

DEVICE_ID = os.getenv("DEVICE_ID", "aicleaner_v3")
if DEVICE_ID:
    logger.info(f"[MAIN] ✓ Device ID: {DEVICE_ID}")
else:
    logger.info("[MAIN] ❌ Device ID is empty - this will cause issues")

DISCOVERY_PREFIX = os.getenv("MQTT_DISCOVERY_PREFIX", "homeassistant")
if DISCOVERY_PREFIX:
    logger.info(f"[MAIN] ✓ MQTT Discovery Prefix: {DISCOVERY_PREFIX}")
else:
    logger.info("[MAIN] ❌ MQTT Discovery Prefix is empty")

# MQTT Configuration - robust handling for when MQTT service unavailable
MQTT_HOST = get_str_env("MQTT_HOST")
MQTT_PORT = get_int_env("MQTT_PORT", 1883)
MQTT_USER = get_str_env("MQTT_USER")
MQTT_PASSWORD = get_str_env("MQTT_PASSWORD")

# Log MQTT configuration status with detailed validation
if MQTT_HOST:
    logger.info(f"[MAIN] ✓ MQTT broker configured: {MQTT_HOST}:{MQTT_PORT}")
    if MQTT_USER:
        logger.info(f"[MAIN] ✓ MQTT authentication configured for user: {MQTT_USER}")
    else:
        logger.info("[MAIN] ℹ️  MQTT using anonymous connection")
else:
    logger.info("[MAIN] ⚠️  MQTT broker not configured - entity discovery disabled")

# Home Assistant API validation
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN")
HOMEASSISTANT_API = os.getenv("HOMEASSISTANT_API", "http://supervisor/core/api")

if SUPERVISOR_TOKEN:
    logger.info(f"[MAIN] ✓ Home Assistant API access available")
    logger.info(f"[MAIN]   API endpoint: {HOMEASSISTANT_API}")
else:
    logger.info("[MAIN] ❌ SUPERVISOR_TOKEN not available - Home Assistant API access limited")

# Configuration summary
logger.info("[MAIN] Configuration summary:")
logger.info(f"[MAIN]   - AI Provider: {'Cloud API' if PRIMARY_API_KEY else 'Local Ollama'}")
logger.info(f"[MAIN]   - MQTT: {'Enabled' if MQTT_HOST else 'Disabled'}")
logger.info(f"[MAIN]   - HA API: {'Available' if SUPERVISOR_TOKEN else 'Limited'}")
logger.info(f"[MAIN]   - Device ID: {DEVICE_ID}")
logger.info(f"[MAIN]   - Discovery Prefix: {DISCOVERY_PREFIX}")

# Configuration validation warnings
config_warnings = []
if not PRIMARY_API_KEY:
    config_warnings.append("No AI API key - limited to local Ollama")
if not MQTT_HOST:
    config_warnings.append("No MQTT broker - entity discovery disabled")
if not SUPERVISOR_TOKEN:
    config_warnings.append("No HA API access - limited functionality")

if config_warnings:
    logger.info("[MAIN] Configuration warnings:")
    for warning in config_warnings:
        logger.info(f"[MAIN]   ⚠️  {warning}")
else:
    logger.info("[MAIN] ✓ All major configuration components are available")

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
            logger.info("✓ Successfully connected to MQTT Broker!")
            self.status = "connected"
            
            # Subscribe to command topic
            client.subscribe(f"aicleaner/{DEVICE_ID}/set")
            logger.info(f"✓ Subscribed to command topic: aicleaner/{DEVICE_ID}/set")
            
            # Register entities and publish initial state
            self.register_entities()
            self.publish_state()
            
            self.status = "idle"
            self.publish_state()
            logger.info("✓ MQTT initialization complete - entity discovery enabled")
        else:
            # More detailed error reporting
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error code {rc}")
            logger.error(f"❌ MQTT connection failed: {error_msg}")
            self.status = "error"
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnect callback"""
        if rc != 0:
            logger.warning(f"⚠️ Unexpected MQTT disconnection (code: {rc})")
            logger.info("Will attempt to reconnect automatically...")
        else:
            logger.info("MQTT client disconnected gracefully")
        self.status = "disconnected"
    
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
                    logger.info("✓ AICleaner enabled via MQTT command")
                elif payload == "OFF":
                    self.enabled = False
                    self.status = "disabled"
                    logger.info("⏸️ AICleaner disabled via MQTT command")
                
                self.publish_state()
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def setup_mqtt(self):
        """Set up MQTT client and connection with graceful fallbacks"""
        if not MQTT_HOST or MQTT_HOST.strip() == "":
            logger.warning("🔌 MQTT host not configured - entity discovery disabled")
            logger.info("📋 To enable MQTT features:")
            logger.info("  Option 1 - HA Internal MQTT:")
            logger.info("    1. Install 'Mosquitto broker' addon")
            logger.info("    2. Configure MQTT integration in Home Assistant")
            logger.info("    3. Restart this addon")
            logger.info("  Option 2 - External MQTT:")
            logger.info("    1. Enable 'mqtt_external_broker' in addon config")
            logger.info("    2. Set mqtt_host, mqtt_port, mqtt_username, mqtt_password")
            logger.info("    3. Restart this addon")
            logger.info("🔄 Addon will continue with local functionality only")
            return False
        
        # Enhanced connection with retry logic
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔗 Attempting MQTT connection to {MQTT_HOST}:{MQTT_PORT} (attempt {attempt + 1}/{max_retries})")
                
                # Create new client for each attempt to avoid state issues
                self.mqtt_client = mqtt.Client()
                
                # Set credentials if provided
                if MQTT_USER and MQTT_PASSWORD:
                    self.mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
                    logger.info(f"🔐 Using MQTT authentication for user: {MQTT_USER}")
                else:
                    logger.info("🔓 Using anonymous MQTT connection")
                
                self.mqtt_client.on_connect = self.on_mqtt_connect
                self.mqtt_client.on_message = self.on_mqtt_message
                self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
                
                # Set connection timeouts for faster failure detection
                self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
                self.mqtt_client.loop_start()
                
                logger.info(f"✓ MQTT connection established to {MQTT_HOST}:{MQTT_PORT}")
                return True
                
            except ConnectionRefusedError as e:
                logger.error(f"❌ Connection refused to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
                logger.error(f"Please verify the broker is running and accessible")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    continue
            except Exception as e:
                logger.error(f"❌ MQTT connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    continue
        
        logger.error(f"❌ All MQTT connection attempts failed to {MQTT_HOST}:{MQTT_PORT}")
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
        # Cleanup web UI resources
        if self.web_ui:
            asyncio.create_task(self.web_ui.shutdown())
    
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
        
        # Cleanup resources before stopping
        if self.web_ui:
            await self.web_ui.shutdown()
        
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