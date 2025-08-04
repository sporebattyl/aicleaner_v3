# Quick Setup: External MQTT Broker Configuration

## Step-by-Step Configuration

### 1. Open Home Assistant Addon Configuration

1. Navigate to **Settings** → **Add-ons** in Home Assistant
2. Find and click on **AICleaner V3** addon
3. Click the **Configuration** tab

### 2. Update Addon Configuration

Replace the existing configuration with:

```json
{
  "log_level": "info",
  "device_id": "aicleaner_v3",
  "debug_mode": false,
  "auto_dashboard": true,
  "mqtt_external_broker": true,
  "mqtt_host": "192.168.88.17",
  "mqtt_port": 1883,
  "mqtt_username": "drewcifer",
  "mqtt_password": "Minds63qq!",
  "mqtt_discovery_prefix": "homeassistant"
}
```

### 3. Save and Restart

1. Click **Save** to save the configuration
2. Go to the **Info** tab
3. Click **Restart** to restart the addon with new settings

### 4. Verify Configuration

After restart, check:

1. **Addon Logs**: Go to **Log** tab and look for:
   - "External MQTT broker configured"
   - "MQTT connection established"
   - "Configuration loaded with X user settings"

2. **Web Interface**: Access the addon web interface (should show through ingress)
   - Status should show "Connected" instead of "MQTT service not available"
   - No JSON parsing errors

3. **MQTT Topics**: Monitor your external MQTT broker for discovery topics:
   - `homeassistant/sensor/aicleaner_v3_*/config`
   - `homeassistant/binary_sensor/aicleaner_v3_*/config`

## Expected Log Messages

Look for these messages in the addon logs:

```
INFO: Configuration loaded with 9 user settings
INFO: External MQTT broker configured: 192.168.88.17:1883
INFO: MQTT connection established
INFO: Entity discovery published
```

## Troubleshooting

### If the addon won't start:
- Check addon logs for error messages
- Verify MQTT broker is accessible from Home Assistant network
- Test MQTT connection manually:
  ```bash
  mosquitto_pub -h 192.168.88.17 -p 1883 -u drewcifer -P "Minds63qq!" -t test -m "test"
  ```

### If entities don't appear:
- Check that `mqtt_discovery_prefix` matches your HA MQTT integration setting
- Verify MQTT discovery is enabled in Home Assistant MQTT integration
- Check MQTT broker logs for incoming connections

### If web UI shows errors:
- Clear browser cache
- Check addon logs for Python/Flask errors
- Restart the addon

## Configuration Validation

The configuration has been tested and validated:
- ✅ External MQTT broker connection
- ✅ Authentication handling  
- ✅ Discovery topic publishing
- ✅ Internal config mapping
- ✅ YAML format generation

## Files Updated

This functionality was enabled by updating:
- `config.yaml` - Added external MQTT options to addon schema
- `src/config_mapper.py` - Maps addon options to internal configuration
- Configuration tested with `test_external_mqtt_config.py`

Your configuration is ready to use!