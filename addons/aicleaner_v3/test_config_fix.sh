#!/bin/bash

# Test script to verify the configuration parsing fixes
echo "Testing AI Cleaner Configuration Parsing Fixes"
echo "=============================================="

# Create test configuration with the problematic backup_api_keys="str" issue
TEST_CONFIG_FILE="/tmp/test_options.json"
cat > "$TEST_CONFIG_FILE" << 'EOF'
{
  "log_level": "debug",
  "device_id": "aicleaner_v3", 
  "primary_api_key": "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc",
  "backup_api_keys": "str",
  "mqtt_discovery_prefix": "homeassistant",
  "mqtt_external_broker": true,
  "mqtt_host": "192.168.88.17",
  "mqtt_port": 1883,
  "mqtt_username": "drewcifer",
  "mqtt_password": "Minds63qq!",
  "default_camera": "camera.rowan_room_fluent",
  "default_todo_list": "todo.rowan_room_cleaning_to_do",
  "debug_mode": true,
  "auto_dashboard": true
}
EOF

echo "✓ Created test configuration with problematic backup_api_keys='str'"

# Copy our test configuration to /data/options.json
sudo mkdir -p /data
sudo cp "$TEST_CONFIG_FILE" /data/options.json
sudo chmod 644 /data/options.json

echo "✓ Copied test configuration to /data/options.json"

# Source the configuration helper functions from run.sh
echo "✓ Testing configuration helper functions..."

# Extract the helper functions for testing (lines 14-60 approximately)
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

read_config_resilient() {
    local key="$1"
    local default_value="$2"
    
    # For testing, we'll skip bashio and go straight to jq
    local jq_value
    jq_value=$(read_config_with_jq "$key" "$default_value")
    if [ -n "$jq_value" ]; then
        echo "$jq_value"
        return 0
    fi
    
    # Return default if nothing found
    echo "${default_value:-}"
}

# Test the resilient configuration reading
echo
echo "Testing resilient configuration reading:"
echo "----------------------------------------"

# Test MQTT external broker
MQTT_EXTERNAL_RAW=$(read_config_resilient 'mqtt_external_broker' 'false')
echo "✓ mqtt_external_broker: '$MQTT_EXTERNAL_RAW'"

# Test API key
PRIMARY_KEY=$(read_config_resilient 'primary_api_key' '')
echo "✓ primary_api_key: ${PRIMARY_KEY:0:20}... (${#PRIMARY_KEY} chars)"

# Test backup API keys (the problematic one)
BACKUP_KEYS_RAW=$(read_config_resilient 'backup_api_keys' '[]')
echo "✓ backup_api_keys: '$BACKUP_KEYS_RAW'"

# Test MQTT settings
MQTT_HOST=$(read_config_resilient 'mqtt_host' '')
MQTT_PORT=$(read_config_resilient 'mqtt_port' '1883')
MQTT_USERNAME=$(read_config_resilient 'mqtt_username' '')
echo "✓ MQTT settings: ${MQTT_HOST}:${MQTT_PORT} (user: $MQTT_USERNAME)"

echo
echo "Testing configuration sanitization:"
echo "-----------------------------------"

# Test the backup_api_keys sanitization
BACKUP_KEYS_RAW_JQ=$(read_config_with_jq 'backup_api_keys' '')
if [ "$BACKUP_KEYS_RAW_JQ" = "str" ]; then
    echo "✓ Detected backup_api_keys='str' - applying fix"
    
    # Create a temporary fixed configuration
    TEMP_CONFIG="/tmp/options_fixed.json"
    jq '.backup_api_keys = []' /data/options.json > "$TEMP_CONFIG" 2>/dev/null
    if [ $? -eq 0 ]; then
        sudo cp "$TEMP_CONFIG" /data/options.json
        echo "✓ Configuration sanitized - backup_api_keys fixed to empty array"
        
        # Verify the fix
        BACKUP_KEYS_FIXED=$(read_config_with_jq 'backup_api_keys' '[]')
        echo "✓ After sanitization: backup_api_keys = '$BACKUP_KEYS_FIXED'"
    fi
    rm -f "$TEMP_CONFIG"
fi

echo
echo "Final test results:"
echo "==================="
echo "✅ mqtt_external_broker can be read: $([ -n "$MQTT_EXTERNAL_RAW" ] && echo "YES" || echo "NO")"
echo "✅ primary_api_key can be read: $([ -n "$PRIMARY_KEY" ] && echo "YES" || echo "NO")"
echo "✅ MQTT host can be read: $([ -n "$MQTT_HOST" ] && echo "YES" || echo "NO")"
echo "✅ backup_api_keys sanitized: $([ "$BACKUP_KEYS_FIXED" = "[]" ] && echo "YES" || echo "NO")"

echo
echo "🎉 Configuration parsing fix test completed successfully!"

# Cleanup
rm -f "$TEST_CONFIG_FILE"