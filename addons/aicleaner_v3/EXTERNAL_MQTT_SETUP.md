# Quick Setup Guide: External MQTT Configuration

## Overview
This guide will help you configure the AIcleaner V3 addon to use your external MQTT broker at 192.168.88.17:1883.

## Step-by-Step Configuration

### 1. Access Addon Configuration
1. Go to **Settings** → **Add-ons** → **AIcleaner V3**
2. Click on the **Configuration** tab

### 2. Configure External MQTT Settings
Add these settings to your addon configuration:

```yaml
# Enable external MQTT broker
mqtt_external_broker: true
mqtt_host: "192.168.88.17"
mqtt_port: 1883
mqtt_username: "drewcifer"
mqtt_password: "Minds63qq!"

# Keep existing settings
log_level: "info"
device_id: "aicleaner_v3"
mqtt_discovery_prefix: "homeassistant"
```

### 3. Save and Restart
1. Click **Save**
2. Go to the **Info** tab
3. Click **Restart**

### 4. Verify Connection
1. Go to the **Log** tab
2. Look for these success messages:
   - ✅ `✓ External MQTT broker configured: 192.168.88.17:1883`
   - ✅ `✓ MQTT initialization complete - entity discovery enabled`
   - ✅ `✓ Enhanced web UI server started successfully`

### 5. Check Web Interface
1. Click **Open Web UI** button in addon
2. Verify the web interface loads without errors
3. Status should show "Connected" instead of error messages

## Expected Results

### ✅ Success Indicators:
- Addon connects to your MQTT broker at 192.168.88.17:1883
- New entities appear in Home Assistant:
  - `sensor.aicleaner_status`
  - `switch.aicleaner_enabled`
  - `sensor.aicleaner_configuration_status`
- Web UI loads without JSON parsing errors
- Status shows "Connected" instead of "MQTT service not available"

### 🔧 Troubleshooting:

#### If you see "Connection refused":
- Verify your MQTT broker is running on 192.168.88.17:1883
- Check firewall settings allow connection from Home Assistant
- Test connection: `telnet 192.168.88.17 1883`

#### If you see "Bad username or password":
- Double-check the username is exactly: `drewcifer`
- Double-check the password is exactly: `Minds63qq!`
- Verify these credentials work with your MQTT broker

#### If you see JSON parsing errors:
- Clear your browser cache
- Check addon logs for any API errors
- Restart the addon if needed

## Reverting to Internal MQTT (if needed)

If you need to switch back to Home Assistant's internal MQTT:

1. Set `mqtt_external_broker: false` (or remove the line)
2. Remove or comment out the external MQTT settings
3. Ensure you have Mosquitto broker addon installed
4. Restart the AIcleaner V3 addon

## Configuration Examples

### Full External MQTT Configuration:
```yaml
log_level: "info"
device_id: "aicleaner_v3"
primary_api_key: ""
backup_api_keys: []
mqtt_discovery_prefix: "homeassistant"
mqtt_external_broker: true
mqtt_host: "192.168.88.17"
mqtt_port: 1883
mqtt_username: "drewcifer"
mqtt_password: "Minds63qq!"
default_camera: ""
default_todo_list: ""
enable_zones: false
zones: []
debug_mode: false
auto_dashboard: true
```

### Internal MQTT Configuration (fallback):
```yaml
log_level: "info"
device_id: "aicleaner_v3"
primary_api_key: ""
backup_api_keys: []
mqtt_discovery_prefix: "homeassistant"
mqtt_external_broker: false
default_camera: ""
default_todo_list: ""
enable_zones: false
zones: []
debug_mode: false
auto_dashboard: true
```

## Next Steps

Once MQTT is working:
1. Configure your camera and todo list entities in the web UI
2. Test the AI functionality
3. Verify entities are discoverable in Home Assistant
4. Set up any automations using the new entities

---

**Need Help?** Check the addon logs for detailed error messages and troubleshooting information.