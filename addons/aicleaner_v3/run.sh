#!/usr/bin/env bashio

# ==============================================================================
# AICleaner V3 Add-on Startup Script
# ==============================================================================

bashio::log.info "Starting AICleaner V3 add-on..."

# ==============================================================================
# Configuration Helper Functions
# ==============================================================================

# Resilient configuration reader with jq fallback
read_config_with_jq() {
    local key="$1"
    local default_value="$2"
    
    # Try to read with jq, providing fallback for null/missing values
    local value
    if [ -f /data/options.json ]; then
        value=$(jq -r ".$key // empty" /data/options.json 2>/dev/null)
        if [ -n "$value" ] && [ "$value" != "null" ]; then
            echo "$value"
        elif [ -n "$default_value" ]; then
            echo "$default_value"
        else
            echo ""
        fi
    else
        echo "${default_value:-}"
    fi
}

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
    local jq_value
    jq_value=$(read_config_with_jq "$key" "$default_value")
    if [ -n "$jq_value" ]; then
        bashio::log.debug "Using jq fallback for config key: $key"
        echo "$jq_value"
        return 0
    fi
    
    # Return default if nothing found
    echo "${default_value:-}"
}

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

# Primary API key validation with resilient config reading
PRIMARY_KEY=$(read_config_resilient 'primary_api_key' '')
if [ -n "$PRIMARY_KEY" ] && [ "$PRIMARY_KEY" != "null" ]; then
    API_KEY_LENGTH=${#PRIMARY_KEY}
    if [ "$API_KEY_LENGTH" -gt 1 ]; then
        bashio::log.info "✓ Primary API key found (length: ${API_KEY_LENGTH} chars)"
        
        # Basic API key format validation for Gemini keys
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

# Configuration Sanitization: Fix common schema validation issues
bashio::log.info "Performing configuration sanitization..."

# Check for backup_api_keys issue that breaks bashio schema validation
BACKUP_KEYS_RAW_JQ=$(read_config_with_jq 'backup_api_keys' '')
if [ -n "$BACKUP_KEYS_RAW_JQ" ]; then
    bashio::log.debug "Raw backup_api_keys from jq: '$BACKUP_KEYS_RAW_JQ'"
    
    # Check if backup_api_keys is set to literal string "str" (common config error)
    if [ "$BACKUP_KEYS_RAW_JQ" = "str" ]; then
        bashio::log.warning "⚠️  Detected backup_api_keys='str' - this breaks bashio schema validation"
        bashio::log.info "🔧 Auto-fixing: Converting 'str' to empty array []"
        
        # Create a temporary fixed configuration
        TEMP_CONFIG="/tmp/options_fixed.json"
        jq '.backup_api_keys = []' /data/options.json > "$TEMP_CONFIG" 2>/dev/null
        if [ $? -eq 0 ]; then
            cp "$TEMP_CONFIG" /data/options.json
            bashio::log.info "✓ Configuration sanitized - backup_api_keys fixed to empty array"
        else
            bashio::log.warning "Could not auto-fix configuration, continuing with fallback parsing"
        fi
        rm -f "$TEMP_CONFIG"
    fi
fi

# Backup API keys validation with resilient reading
BACKUP_KEYS_RAW=$(read_config_resilient 'backup_api_keys' '[]')
if [ -n "$BACKUP_KEYS_RAW" ] && [ "$BACKUP_KEYS_RAW" != "[]" ]; then
    bashio::log.info "✓ Backup API keys configuration found"
    bashio::log.debug "  Raw backup_api_keys value: '$BACKUP_KEYS_RAW'"
    
    # Check if it's a valid JSON array
    if echo "$BACKUP_KEYS_RAW" | jq . >/dev/null 2>&1; then
        BACKUP_COUNT=$(echo "$BACKUP_KEYS_RAW" | jq '. | length' 2>/dev/null || echo "0")
        bashio::log.info "  ✓ Valid JSON array with $BACKUP_COUNT entries"
    else
        bashio::log.warning "  ⚠️  backup_api_keys format unusual, using fallback parsing"
        bashio::log.debug "  Got: '$BACKUP_KEYS_RAW'"
    fi
else
    bashio::log.info "No backup API keys configured (optional)"
fi

# Validate device ID format with resilient reading
DEVICE_ID=$(read_config_resilient 'device_id' 'aicleaner_v3')
bashio::log.info "🔍 DEBUG: Device ID from resilient config: '$DEVICE_ID'"

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

# Export configuration with error handling using resilient config reading
export LOG_LEVEL=$(read_config_resilient "log_level" "info")
export PRIMARY_API_KEY="$PRIMARY_KEY"  # Use the key we already read with resilient method
export MQTT_DISCOVERY_PREFIX=$(read_config_resilient "mqtt_discovery_prefix" "homeassistant")
export DEBUG_MODE=$(read_config_resilient "debug_mode" "false")
export AUTO_DASHBOARD=$(read_config_resilient "auto_dashboard" "true")

bashio::log.info "Configuration exported with resilient reading:"
bashio::log.info "  ✓ LOG_LEVEL: $LOG_LEVEL"
bashio::log.info "  ✓ PRIMARY_API_KEY: ${PRIMARY_API_KEY:+***SET***}"
bashio::log.info "  ✓ MQTT_DISCOVERY_PREFIX: $MQTT_DISCOVERY_PREFIX" 
bashio::log.info "  ✓ DEBUG_MODE: $DEBUG_MODE"
bashio::log.info "  ✓ AUTO_DASHBOARD: $AUTO_DASHBOARD"

# Handle backup API keys specially (JSON array) with resilient reading
BACKUP_KEYS_EXPORT=$(read_config_resilient 'backup_api_keys' '[]')
# Validate JSON before processing
if echo "$BACKUP_KEYS_EXPORT" | jq . >/dev/null 2>&1; then
    export BACKUP_API_KEYS=$(echo "$BACKUP_KEYS_EXPORT" | jq -c '.')
    BACKUP_COUNT=$(echo "$BACKUP_KEYS_EXPORT" | jq '. | length' 2>/dev/null || echo "0")
    bashio::log.info "  ✓ BACKUP_API_KEYS exported as valid JSON ($BACKUP_COUNT keys)"
else
    export BACKUP_API_KEYS="[]"
    bashio::log.warning "  ⚠️  backup_api_keys invalid JSON format, using empty array"
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
# Resilient MQTT broker configuration with bashio/jq fallback
bashio::log.info "Validating MQTT configuration..."

# Try resilient configuration reading for mqtt_external_broker
MQTT_EXTERNAL_RAW=$(read_config_resilient 'mqtt_external_broker' 'false')
if [ -n "$MQTT_EXTERNAL_RAW" ] && [ "$MQTT_EXTERNAL_RAW" != "false" ]; then
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
    bashio::log.info "ℹ️  mqtt_external_broker not configured or set to false, using internal MQTT"
    MQTT_EXTERNAL="false"  # Default fallback
fi

bashio::log.info "🔍 DEBUG: External MQTT broker setting (normalized): '$MQTT_EXTERNAL'"

# Validate external MQTT configuration before proceeding
if [[ "$MQTT_EXTERNAL" == "true" ]]; then
    bashio::log.info "External MQTT broker enabled - validating configuration..."
    
    # Pre-validate required external MQTT settings using resilient config reading
    MQTT_HOST_CHECK=$(read_config_resilient 'mqtt_host' '')
    if [ -z "$MQTT_HOST_CHECK" ]; then
        bashio::log.error "❌ External MQTT enabled but mqtt_host not configured!"
        bashio::log.error "Please set mqtt_host in addon configuration"
        bashio::exit.nok "Missing mqtt_host for external MQTT broker"
    fi
    
    MQTT_PORT_CHECK=$(read_config_resilient 'mqtt_port' '1883')
    if [ "$MQTT_PORT_CHECK" = "1883" ]; then
        bashio::log.info "ℹ️  mqtt_port using default (1883)"
    fi
    
    bashio::log.info "✓ External MQTT broker configuration validation passed"
fi

if [[ "$MQTT_EXTERNAL" == "true" ]]; then
    # External MQTT broker configured - use resilient config reading
    MQTT_HOST_VALUE=$(read_config_resilient 'mqtt_host' '')
    MQTT_PORT_VALUE=$(read_config_resilient 'mqtt_port' '1883')
    MQTT_USERNAME_VALUE=$(read_config_resilient 'mqtt_username' '')
    MQTT_PASSWORD_VALUE=$(read_config_resilient 'mqtt_password' '')
    
    bashio::log.info "🔍 DEBUG: External MQTT host value: '$MQTT_HOST_VALUE'"
    bashio::log.info "🔍 DEBUG: External MQTT port: '$MQTT_PORT_VALUE'"
    bashio::log.info "🔍 DEBUG: External MQTT username: '$MQTT_USERNAME_VALUE'"
    
    if [[ -n "$MQTT_HOST_VALUE" ]]; then
        export MQTT_HOST="$MQTT_HOST_VALUE"
        export MQTT_PORT="$MQTT_PORT_VALUE"
        export MQTT_USER="$MQTT_USERNAME_VALUE"
        export MQTT_PASSWORD="$MQTT_PASSWORD_VALUE"
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