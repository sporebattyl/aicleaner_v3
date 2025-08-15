#!/usr/bin/env bashio

# ==============================================================================
# AI Cleaner Add-on Startup Script
# ==============================================================================

bashio::log.info "Starting AI Cleaner add-on..."

# ==============================================================================
# Configuration Functions
# ==============================================================================

# Enhanced configuration reader with bashio primary, jq fallback
read_config_resilient() {
    local key="$1"
    local default_value="$2"
    
    # Try bashio first
    if bashio::config.has_value "$key"; then
        local bashio_value
        bashio_value=$(bashio::config "$key")
        if [ -n "$bashio_value" ] && [ "$bashio_value" != "null" ]; then
            echo "$bashio_value"
            return 0
        fi
    fi
    
    # Fall back to jq
    if [ -f /data/options.json ]; then
        local jq_value
        jq_value=$(jq -r ".$key // empty" /data/options.json 2>/dev/null)
        if [ -n "$jq_value" ] && [ "$jq_value" != "null" ]; then
            bashio::log.debug "Using jq fallback for config key: $key"
            echo "$jq_value"
            return 0
        fi
    fi
    
    # Return default if nothing found
    echo "${default_value:-}"
}

# ==============================================================================
# Environment Setup
# ==============================================================================

bashio::log.info "Setting up addon environment..."

# Check for configuration file
if [ ! -f /data/options.json ]; then
    bashio::log.warning "Configuration file /data/options.json not found."
    bashio::log.info "Creating default configuration..."
    
    mkdir -p /data
    cat > /data/options.json << 'EOF'
{
  "log_level": "info",
  "ai_provider": "gemini",
  "gemini_api_key": "",
  "ollama_host": "http://host.docker.internal:11434",
  "camera_entity": "",
  "todo_entity": "",
  "enable_zones": false,
  "zones": [],
  "privacy_level": "standard",
  "save_images": false,
  "analysis_interval": 300,
  "auto_create_tasks": true
}
EOF
    bashio::log.info "✓ Default configuration created"
fi

# ==============================================================================
# Configuration Validation
# ==============================================================================

bashio::log.info "Validating addon configuration..."

# Read core configuration
LOG_LEVEL=$(read_config_resilient "log_level" "info")
AI_PROVIDER=$(read_config_resilient "ai_provider" "gemini")
GEMINI_API_KEY=$(read_config_resilient "gemini_api_key" "")
OLLAMA_HOST=$(read_config_resilient "ollama_host" "http://host.docker.internal:11434")
CAMERA_ENTITY=$(read_config_resilient "camera_entity" "")
TODO_ENTITY=$(read_config_resilient "todo_entity" "")
ENABLE_ZONES=$(read_config_resilient "enable_zones" "false")
PRIVACY_LEVEL=$(read_config_resilient "privacy_level" "standard")
SAVE_IMAGES=$(read_config_resilient "save_images" "false")
ANALYSIS_INTERVAL=$(read_config_resilient "analysis_interval" "300")
AUTO_CREATE_TASKS=$(read_config_resilient "auto_create_tasks" "true")

# Validate AI provider configuration
case "$AI_PROVIDER" in
    "gemini")
        if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "null" ]; then
            bashio::log.warning "Gemini API key not configured. Please set gemini_api_key in addon options."
            bashio::log.warning "The addon will attempt to use Ollama as fallback."
            AI_PROVIDER="ollama"
        else
            bashio::log.info "✓ Gemini AI provider configured"
        fi
        ;;
    "ollama")
        bashio::log.info "✓ Ollama AI provider configured (host: $OLLAMA_HOST)"
        ;;
    *)
        bashio::log.warning "Unknown AI provider: $AI_PROVIDER. Defaulting to ollama."
        AI_PROVIDER="ollama"
        ;;
esac

# Validate entity configuration
if [ -z "$CAMERA_ENTITY" ] || [ "$CAMERA_ENTITY" = "null" ]; then
    bashio::log.warning "No camera entity configured. Image analysis will be limited."
fi

if [ -z "$TODO_ENTITY" ] || [ "$TODO_ENTITY" = "null" ]; then
    bashio::log.warning "No todo entity configured. Tasks will be logged only."
fi

bashio::log.info "Configuration validation completed:"
bashio::log.info "  - AI Provider: $AI_PROVIDER"
bashio::log.info "  - Camera Entity: ${CAMERA_ENTITY:-'Not configured'}"
bashio::log.info "  - Todo Entity: ${TODO_ENTITY:-'Not configured'}"
bashio::log.info "  - Privacy Level: $PRIVACY_LEVEL"
bashio::log.info "  - Analysis Interval: ${ANALYSIS_INTERVAL}s"

# ==============================================================================
# MQTT Configuration
# ==============================================================================

bashio::log.info "Configuring MQTT connection..."

# Check for MQTT availability
if bashio::services.available "mqtt"; then
    export MQTT_HOST=$(bashio::services mqtt "host")
    export MQTT_PORT=$(bashio::services mqtt "port")
    export MQTT_USER=$(bashio::services mqtt "username")
    export MQTT_PASSWORD=$(bashio::services mqtt "password")
    export MQTT_DISCOVERY_PREFIX="homeassistant"
    
    bashio::log.info "✓ MQTT broker configured: ${MQTT_HOST}:${MQTT_PORT}"
else
    bashio::log.warning "⚠️ MQTT service not available"
    bashio::log.warning "To enable entity creation:"
    bashio::log.warning "  1. Install 'Mosquitto broker' addon"
    bashio::log.warning "  2. Configure MQTT integration in Settings > Devices & Services"
    bashio::log.warning "Addon will continue with reduced functionality..."
fi

# ==============================================================================
# Home Assistant API Setup
# ==============================================================================

export HOMEASSISTANT_API="http://supervisor/core/api"
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"

bashio::log.info "Home Assistant API configured"

# ==============================================================================
# Environment Export
# ==============================================================================

bashio::log.info "Exporting configuration to environment..."

# Core configuration
export LOG_LEVEL="$LOG_LEVEL"
export AI_PROVIDER="$AI_PROVIDER"
export GEMINI_API_KEY="$GEMINI_API_KEY"
export OLLAMA_HOST="$OLLAMA_HOST"
export CAMERA_ENTITY="$CAMERA_ENTITY"
export TODO_ENTITY="$TODO_ENTITY"
export ENABLE_ZONES="$ENABLE_ZONES"
export PRIVACY_LEVEL="$PRIVACY_LEVEL"
export SAVE_IMAGES="$SAVE_IMAGES"
export ANALYSIS_INTERVAL="$ANALYSIS_INTERVAL"
export AUTO_CREATE_TASKS="$AUTO_CREATE_TASKS"

# Handle zones configuration
ZONES_JSON=$(read_config_resilient 'zones' '[]')
if echo "$ZONES_JSON" | jq . >/dev/null 2>&1; then
    export ZONES_CONFIG=$(echo "$ZONES_JSON" | jq -c '.')
    ZONES_COUNT=$(echo "$ZONES_JSON" | jq '. | length' 2>/dev/null || echo "0")
    bashio::log.info "✓ Zones configuration exported ($ZONES_COUNT zones)"
else
    export ZONES_CONFIG="[]"
    bashio::log.warning "⚠️ Invalid zones configuration, using empty array"
fi

bashio::log.info "Environment variables exported successfully"

# ==============================================================================
# Python Application Startup
# ==============================================================================

bashio::log.info "Starting AI Cleaner application..."

# Change to application directory
cd /app

# Start the Python application
exec python3 src/main.py