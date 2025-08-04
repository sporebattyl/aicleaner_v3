#!/usr/bin/env bashio

# ==============================================================================
# AICleaner V3 Add-on Startup Script
# ==============================================================================

bashio::log.info "Starting AICleaner V3 add-on..."

# --- 0. ENVIRONMENT CHECK ---
bashio::log.info "Checking addon environment..."

# Check for /data/options.json - critical for addon configuration
if [ ! -f /data/options.json ]; then
    bashio::log.warning "Configuration file /data/options.json not found."
    bashio::log.warning "This may occur during initial setup or development environment."
    bashio::log.info "Creating default configuration file..."
    
    # Ensure /data directory exists
    mkdir -p /data
    
    # Create default options.json with all required fields
    cat > /data/options.json << 'EOF'
{
  "log_level": "info",
  "device_id": "aicleaner_v3",
  "primary_api_key": "",
  "backup_api_keys": [],
  "mqtt_discovery_prefix": "homeassistant",
  "default_camera": "",
  "default_todo_list": "",
  "enable_zones": false,
  "zones": [],
  "debug_mode": false,
  "auto_dashboard": true
}
EOF
    bashio::log.info "✓ Default configuration created. Please configure via Home Assistant addon UI."
fi

# --- 1. VALIDATE CONFIGURATION ---
bashio::log.info "Validating add-on configuration..."

# Primary API key is optional - fallback to Ollama if not provided
if ! bashio::config.has_value 'primary_api_key'; then
  bashio::log.warning "No primary API key provided. Will use local Ollama as fallback."
fi

# Validate device ID format
DEVICE_ID=$(bashio::config 'device_id')
if [[ ! "$DEVICE_ID" =~ ^[a-zA-Z0-9_]+$ ]]; then
  bashio::exit.fatal "Device ID must contain only letters, numbers, and underscores."
fi

# --- 2. EXPORT CONFIGURATION ---
# The Python application will read configuration from environment variables
bashio::log.info "Exporting configuration to environment variables..."

export LOG_LEVEL=$(bashio::config 'log_level')
export PRIMARY_API_KEY=$(bashio::config 'primary_api_key')
export BACKUP_API_KEYS=$(bashio::config 'backup_api_keys' | jq -c '.')
export MQTT_DISCOVERY_PREFIX=$(bashio::config 'mqtt_discovery_prefix')
export DEVICE_ID="$DEVICE_ID"
export DEBUG_MODE=$(bashio::config 'debug_mode')
export AUTO_DASHBOARD=$(bashio::config 'auto_dashboard')

# Export API keys for application use
export GEMINI_API_KEY="$PRIMARY_API_KEY"
export OPENAI_API_KEY=""
export ANTHROPIC_API_KEY=""

# --- 3. MQTT CONFIGURATION ---
# Check for external MQTT broker configuration first
if bashio::config.has_value 'mqtt_external_broker' && bashio::config.true 'mqtt_external_broker'; then
    # External MQTT broker configured
    if bashio::config.has_value 'mqtt_host' && [ "$(bashio::config 'mqtt_host')" != "" ]; then
        export MQTT_HOST=$(bashio::config 'mqtt_host')
        export MQTT_PORT=$(bashio::config 'mqtt_port')
        export MQTT_USER=$(bashio::config 'mqtt_username')
        export MQTT_PASSWORD=$(bashio::config 'mqtt_password')
        bashio::log.info "✓ External MQTT broker configured: ${MQTT_HOST}:${MQTT_PORT}"
        bashio::log.info "✓ Using external MQTT broker for entity discovery"
    else
        bashio::log.error "External MQTT enabled but mqtt_host not configured!"
        bashio::exit.nok "Please configure mqtt_host in addon options"
    fi
elif bashio::services.available "mqtt"; then
    # Home Assistant provides MQTT broker details when mqtt service is requested
    export MQTT_HOST=$(bashio::services mqtt "host")
    export MQTT_PORT=$(bashio::services mqtt "port")
    export MQTT_USER=$(bashio::services mqtt "username")
    export MQTT_PASSWORD=$(bashio::services mqtt "password")
    bashio::log.info "✓ HA internal MQTT broker configured: ${MQTT_HOST}:${MQTT_PORT}"
    bashio::log.info "✓ Entity discovery and MQTT features will be available"
else
    bashio::log.warning "⚠️  MQTT service not available - entity discovery disabled"
    bashio::log.warning "To enable full functionality, either:"
    bashio::log.warning "Option 1 - Use HA Internal MQTT:"
    bashio::log.warning "  1. Install 'Mosquitto broker' addon from Add-on Store"
    bashio::log.warning "  2. Configure username/password in Mosquitto addon"
    bashio::log.warning "  3. Add MQTT integration in Settings > Devices & Services"
    bashio::log.warning "Option 2 - Use External MQTT:"
    bashio::log.warning "  1. Enable 'mqtt_external_broker' in addon configuration"
    bashio::log.warning "  2. Set mqtt_host, mqtt_port, mqtt_username, mqtt_password"
    bashio::log.warning "  3. Restart this addon after MQTT setup is complete"
    bashio::log.info "Addon will continue with reduced functionality..."
    
    # Following HA addon best practices: don't export empty variables
    # The Python application will use defaults when these variables are unset
    bashio::log.debug "MQTT environment variables not exported (service unavailable)"
fi

# --- 4. HOME ASSISTANT API ---
# Supervisor provides HA API access automatically via SUPERVISOR_TOKEN environment variable
# SUPERVISOR_TOKEN is provided by Home Assistant when hassio_api: true is set in config.yaml
export HOMEASSISTANT_API="http://supervisor/core/api"

bashio::log.info "Configuration loaded successfully:"
bashio::log.info "- Log Level: ${LOG_LEVEL}"
bashio::log.info "- Device ID: ${DEVICE_ID}"
bashio::log.info "- MQTT Discovery Prefix: ${MQTT_DISCOVERY_PREFIX}"

# --- 5. GENERATE CONFIGURATION ---
bashio::log.info "Mapping addon options to internal configuration..."

# Run configuration mapper to create app_config.user.yaml from addon options
python3 /app/src/config_mapper.py

if [ $? -eq 0 ]; then
    bashio::log.info "✓ Configuration mapping completed successfully"
else
    bashio::exit.fatal "Configuration mapping failed"
fi

# --- 6. START APPLICATION ---
bashio::log.info "Starting AICleaner V3 application..."

# Switch to app user and execute the main application
exec python3 /app/src/main.py