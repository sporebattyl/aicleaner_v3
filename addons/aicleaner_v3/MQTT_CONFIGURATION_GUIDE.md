# AIcleaner V3 External MQTT Configuration Guide

This guide explains how to configure the AIcleaner V3 addon to use an external MQTT broker instead of Home Assistant's internal MQTT service.

## Overview

The addon has been modified to support external MQTT broker configuration through the Home Assistant addon configuration interface. The configuration options are already defined in `config.yaml` and the code has been updated to handle external MQTT connections.

## Configuration Steps

### 1. Access Addon Configuration

1. Navigate to **Settings** → **Add-ons** → **AICleaner V3**
2. Click on the **Configuration** tab
3. Update the configuration with your external MQTT broker settings

### 2. Required Configuration

Add the following configuration to your addon options:

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

### 3. Configuration Options Explained

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `mqtt_external_broker` | boolean | `false` | Enable external MQTT broker connection |
| `mqtt_host` | string | `""` | External MQTT broker hostname or IP address |
| `mqtt_port` | integer | `1883` | External MQTT broker port |
| `mqtt_username` | string | `""` | MQTT broker username (optional) |
| `mqtt_password` | string | `""` | MQTT broker password (optional) |
| `mqtt_discovery_prefix` | string | `"homeassistant"` | MQTT discovery topic prefix |

### 4. Apply Configuration

1. **Save** the configuration in the addon settings
2. **Restart** the addon for changes to take effect

## How It Works

When you configure the external MQTT settings, the addon:

1. **Configuration Mapping**: The `config_mapper.py` reads your addon options and creates an internal configuration
2. **MQTT Client Setup**: The MQTT service connects to your external broker instead of the internal one
3. **Entity Discovery**: Publishes entity discovery messages to your external MQTT broker
4. **Status Updates**: All MQTT communication goes through your external broker

## Internal Configuration Generated

Your addon options are automatically mapped to this internal configuration:

```yaml
general:
  active_provider: ollama
  log_level: INFO
mqtt:
  auto_discovery:
    topic_prefix: homeassistant
  broker:
    host: 192.168.88.17
    port: 1883
    external: true
    auth:
      username: drewcifer
      password: Minds63qq!
```

## Expected Results

After applying the configuration and restarting:

1. **Connection Status**: The addon should show "Connected" instead of "MQTT service not available"
2. **Entity Discovery**: Home Assistant entities should be auto-discovered via your external MQTT broker
3. **Web UI**: The JSON parsing errors should be resolved and the UI should display correctly
4. **MQTT Topics**: You can monitor MQTT topics on your external broker to see discovery payloads

## Troubleshooting

### Check Addon Logs
Monitor the addon logs for connection status:
```
Settings → Add-ons → AICleaner V3 → Log
```

Look for messages like:
- "MQTT connection established"
- "External MQTT broker configured"
- "Entity discovery published"

### Verify MQTT Connection
You can test the MQTT connection manually:
```bash
mosquitto_pub -h 192.168.88.17 -p 1883 -u drewcifer -P Minds63qq! -t test/topic -m "test"
```

### Common Issues

1. **Connection Refused**: Check that the MQTT broker is accessible from the Home Assistant network
2. **Authentication Failed**: Verify username and password are correct
3. **Discovery Not Working**: Ensure `mqtt_discovery_prefix` matches your Home Assistant MQTT integration prefix

## Files Modified

The following files have been updated to support external MQTT configuration:

- `/home/drewcifer/aicleaner_v3/addons/aicleaner_v3/config.yaml` - Added external MQTT options
- `/home/drewcifer/aicleaner_v3/addons/aicleaner_v3/src/config_mapper.py` - Maps addon options to internal config

## Alternative Manual Configuration

If you need to manually configure the external MQTT settings, you can:

1. Copy `/home/drewcifer/aicleaner_v3/addons/aicleaner_v3/external_mqtt_options.json` to `/data/options.json` inside the addon container
2. Restart the addon

However, it's recommended to use the Home Assistant addon configuration interface for proper integration.