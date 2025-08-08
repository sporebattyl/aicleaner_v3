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

# Debug: Check if options.json exists and is readable
if [ -f /data/options.json ]; then
    bashio::log.info "✓ Configuration file /data/options.json found"
    OPTIONS_SIZE=$(stat -f%z /data/options.json 2>/dev/null || stat -c%s /data/options.json 2>/dev/null || echo "unknown")
    bashio::log.info "  File size: ${OPTIONS_SIZE} bytes"
    
    # Show first few lines of options.json for debugging (excluding sensitive data)
    bashio::log.debug "=== Configuration Content Preview ==="
    if command -v jq >/dev/null 2>&1; then
        # Use jq to pretty-print and redact sensitive fields
        jq 'with_entries(if (.key | contains("password") or contains("api_key")) then .value = "***REDACTED***" else . end)' /data/options.json 2>/dev/null | head -20 | while read line; do
            bashio::log.debug "  $line"
        done
    else
        # Fallback to basic head command with redaction
        head -20 /data/options.json | sed 's/"[^"]*password[^"]*"[[:space:]]*:[[:space:]]*"[^"]*"/"***REDACTED***"/gi' | sed 's/"[^"]*api_key[^"]*"[[:space:]]*:[[:space:]]*"[^"]*"/"***REDACTED***"/gi' | while read line; do
            bashio::log.debug "  $line"
        done
    fi
    bashio::log.debug "=== End Configuration Preview ==="
else
    bashio::log.error "❌ Configuration file /data/options.json NOT FOUND!"
    bashio::log.error "This indicates a serious configuration parsing issue."
    bashio::log.error "Please check your addon configuration in Home Assistant UI."
fi

# Test individual configuration reads with detailed error reporting
bashio::log.info "Testing configuration value parsing..."

# Primary API key validation
if bashio::config.has_value 'primary_api_key'; then
    API_KEY_LENGTH=$(bashio::config 'primary_api_key' | wc -c)
    if [ "$API_KEY_LENGTH" -gt 1 ]; then
        bashio::log.info "✓ Primary API key found (length: ${API_KEY_LENGTH} chars)"
        
        # Basic API key format validation for Gemini keys
        PRIMARY_KEY=$(bashio::config 'primary_api_key')
        if [[ "$PRIMARY_KEY" == AIzaSy* ]]; then
            bashio::log.info "  ✓ API key format appears to be valid Gemini key"
        else
            bashio::log.warning "  ⚠️  API key format unusual (expected AIzaSy* for Gemini)"
        fi
    else
        bashio::log.warning "Primary API key is empty. Will use local Ollama as fallback."
    fi
else
    bashio::log.warning "No primary API key provided. Will use local Ollama as fallback."
fi

# Backup API keys validation
if bashio::config.has_value 'backup_api_keys'; then
    BACKUP_KEYS_RAW=$(bashio::config 'backup_api_keys')
    bashio::log.info "✓ Backup API keys configuration found"
    bashio::log.debug "  Raw backup_api_keys value: '$BACKUP_KEYS_RAW'"
    
    # Check if it's a valid JSON array
    if echo "$BACKUP_KEYS_RAW" | jq . >/dev/null 2>&1; then
        BACKUP_COUNT=$(echo "$BACKUP_KEYS_RAW" | jq '. | length' 2>/dev/null || echo "0")
        bashio::log.info "  ✓ Valid JSON array with $BACKUP_COUNT entries"
    else
        bashio::log.error "  ❌ backup_api_keys is not valid JSON array format!"
        bashio::log.error "  Expected: [] (empty array) or [\"key1\", \"key2\"] (array of keys)"
        bashio::log.error "  Got: '$BACKUP_KEYS_RAW'"
        bashio::log.error "  Please fix this in Home Assistant addon configuration UI"
    fi
else
    bashio::log.info "No backup API keys configured (optional)"
fi

# Validate device ID format
DEVICE_ID=$(bashio::config 'device_id')
bashio::log.info "🔍 DEBUG: Raw device_id from bashio: '$DEVICE_ID'"

# Handle null/empty device_id
if [[ "$DEVICE_ID" == "null" || -z "$DEVICE_ID" || "$DEVICE_ID" == "" ]]; then
    bashio::log.warning "Device ID is null/empty, using default: aicleaner_v3"
    DEVICE_ID="aicleaner_v3"
fi

if [[ ! "$DEVICE_ID" =~ ^[a-zA-Z0-9_]+$ ]]; then
  bashio::exit.fatal "Device ID must contain only letters, numbers, and underscores."
fi

bashio::log.info "✓ Device ID validated: '$DEVICE_ID'"

# --- 2. EXPORT CONFIGURATION ---
# The Python application will read configuration from environment variables
bashio::log.info "Exporting configuration to environment variables..."

# Safe configuration export with fallbacks
safe_config_export() {
    local key="$1"
    local default="$2"
    local env_var="$3"
    
    if bashio::config.has_value "$key"; then
        local value=$(bashio::config "$key")
        if [ -n "$value" ]; then
            export "$env_var"="$value"
            bashio::log.info "  ✓ $env_var exported successfully"
        else
            export "$env_var"="$default"
            bashio::log.warning "  ⚠️  $key is empty, using default: '$default'"
        fi
    else
        export "$env_var"="$default"
        bashio::log.warning "  ⚠️  $key not found, using default: '$default'"
    fi
}

# Export configuration with error handling
safe_config_export "log_level" "info" "LOG_LEVEL"
safe_config_export "primary_api_key" "" "PRIMARY_API_KEY"
safe_config_export "mqtt_discovery_prefix" "homeassistant" "MQTT_DISCOVERY_PREFIX"
safe_config_export "debug_mode" "false" "DEBUG_MODE"
safe_config_export "auto_dashboard" "true" "AUTO_DASHBOARD"

# Handle backup API keys specially (JSON array)
if bashio::config.has_value 'backup_api_keys'; then
    BACKUP_KEYS_RAW=$(bashio::config 'backup_api_keys')
    # Validate JSON before processing
    if echo "$BACKUP_KEYS_RAW" | jq . >/dev/null 2>&1; then
        export BACKUP_API_KEYS=$(echo "$BACKUP_KEYS_RAW" | jq -c '.')
        bashio::log.info "  ✓ BACKUP_API_KEYS exported as valid JSON"
    else
        export BACKUP_API_KEYS="[]"
        bashio::log.error "  ❌ backup_api_keys contains invalid JSON, using empty array"
        bashio::log.error "  Please fix backup_api_keys in Home Assistant UI (should be [] or list of strings)"
    fi
else
    export BACKUP_API_KEYS="[]"
    bashio::log.info "  ✓ BACKUP_API_KEYS set to empty array (default)"
fi

# Device ID was already validated above
export DEVICE_ID="$DEVICE_ID"
bashio::log.info "  ✓ DEVICE_ID exported: '$DEVICE_ID'"

# Export API keys for application use
export GEMINI_API_KEY="$PRIMARY_API_KEY"
export OPENAI_API_KEY=""
export ANTHROPIC_API_KEY=""

# Validate critical exports
bashio::log.info "Validating exported environment variables..."
[ -n "$LOG_LEVEL" ] && bashio::log.info "  ✓ LOG_LEVEL: $LOG_LEVEL" || bashio::log.error "  ❌ LOG_LEVEL is empty"
[ -n "$DEVICE_ID" ] && bashio::log.info "  ✓ DEVICE_ID: $DEVICE_ID" || bashio::log.error "  ❌ DEVICE_ID is empty"
[ -n "$MQTT_DISCOVERY_PREFIX" ] && bashio::log.info "  ✓ MQTT_DISCOVERY_PREFIX: $MQTT_DISCOVERY_PREFIX" || bashio::log.error "  ❌ MQTT_DISCOVERY_PREFIX is empty"

# --- 3. MQTT CONFIGURATION ---
# Check for external MQTT broker configuration first
bashio::log.info "Validating MQTT configuration..."

if bashio::config.has_value 'mqtt_external_broker'; then
    MQTT_EXTERNAL_RAW=$(bashio::config 'mqtt_external_broker')
    bashio::log.info "✓ MQTT external broker setting found: '$MQTT_EXTERNAL_RAW'"
    
    # Normalize boolean value - handle various boolean representations
    case "${MQTT_EXTERNAL_RAW,,}" in
        "true"|"1"|"yes"|"on"|"enabled")
            MQTT_EXTERNAL="true"
            bashio::log.info "  ✓ Normalized to: true"
            ;;
        "false"|"0"|"no"|"off"|"disabled"|"")
            MQTT_EXTERNAL="false"
            bashio::log.info "  ✓ Normalized to: false"
            ;;
        *)
            bashio::log.warning "  ⚠️  Unusual boolean value: '$MQTT_EXTERNAL_RAW'"
            bashio::log.warning "  Attempting to interpret as boolean..."
            # Try to interpret as JSON boolean
            if echo "$MQTT_EXTERNAL_RAW" | jq . >/dev/null 2>&1; then
                if [[ "$(echo "$MQTT_EXTERNAL_RAW" | jq -r '.')" == "true" ]]; then
                    MQTT_EXTERNAL="true"
                    bashio::log.info "  ✓ JSON boolean interpretation: true"
                else
                    MQTT_EXTERNAL="false"
                    bashio::log.info "  ✓ JSON boolean interpretation: false"
                fi
            else
                bashio::log.warning "  Using default: false"
                MQTT_EXTERNAL="false"
            fi
            ;;
    esac
else
    bashio::log.warning "⚠️  mqtt_external_broker setting not found in configuration"
    MQTT_EXTERNAL="false"  # Default fallback
fi

bashio::log.info "🔍 DEBUG: External MQTT broker setting (normalized): '$MQTT_EXTERNAL'"

# Validate external MQTT configuration before proceeding
if [[ "$MQTT_EXTERNAL" == "true" ]]; then
    bashio::log.info "External MQTT broker enabled - validating configuration..."
    
    # Pre-validate required external MQTT settings
    if ! bashio::config.has_value 'mqtt_host'; then
        bashio::log.error "❌ External MQTT enabled but mqtt_host not configured!"
        bashio::log.error "Please set mqtt_host in addon configuration"
        bashio::exit.nok "Missing mqtt_host for external MQTT broker"
    fi
    
    if ! bashio::config.has_value 'mqtt_port'; then
        bashio::log.warning "⚠️  mqtt_port not set, will use default (1883)"
    fi
    
    bashio::log.info "✓ External MQTT broker configuration validation passed"
fi

if [[ "$MQTT_EXTERNAL" == "true" ]]; then
    # External MQTT broker configured
    MQTT_HOST_VALUE=$(bashio::config 'mqtt_host')
    bashio::log.info "🔍 DEBUG: External MQTT host value: '$MQTT_HOST_VALUE'"
    bashio::log.info "🔍 DEBUG: External MQTT port: '$(bashio::config 'mqtt_port')'"
    bashio::log.info "🔍 DEBUG: External MQTT username: '$(bashio::config 'mqtt_username')'"
    
    if [[ -n "$MQTT_HOST_VALUE" ]]; then
        export MQTT_HOST="$MQTT_HOST_VALUE"
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
    bashio::log.info "🔍 DEBUG: HA internal MQTT service detected - host: $MQTT_HOST, port: $MQTT_PORT"
    bashio::log.info "✓ HA internal MQTT broker configured: ${MQTT_HOST}:${MQTT_PORT}"
    bashio::log.info "✓ Entity discovery and MQTT features will be available"
else
    bashio::log.info "🔍 DEBUG: MQTT service check failed - bashio::services.available mqtt returned false"
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