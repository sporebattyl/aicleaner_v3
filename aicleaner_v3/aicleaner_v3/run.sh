#!/usr/bin/env bashio

# ==============================================================================
# AICleaner V3 Add-on Startup Script
# ==============================================================================

bashio::log.info "Starting AICleaner V3 add-on..."

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
# Home Assistant provides MQTT broker details when mqtt service is requested
if bashio::services.available "mqtt"; then
    export MQTT_HOST=$(bashio::services mqtt "host")
    export MQTT_PORT=$(bashio::services mqtt "port")
    export MQTT_USER=$(bashio::services mqtt "username")
    export MQTT_PASSWORD=$(bashio::services mqtt "password")
    bashio::log.info "MQTT broker configured: ${MQTT_HOST}:${MQTT_PORT}"
else
    bashio::log.warning "MQTT service not available. Some features may not work."
fi

# --- 4. HOME ASSISTANT API ---
# Supervisor provides HA API access
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"
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