# AICleaner V3 Add-on

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield] ![Supports armhf Architecture][armhf-shield] ![Supports armv7 Architecture][armv7-shield] ![Supports i386 Architecture][i386-shield]

AI-powered cleaning and optimization for your Home Assistant smart home.

## About

AICleaner V3 is an intelligent automation system that uses artificial intelligence to analyze, clean, and optimize your smart home data and device interactions. This add-on provides seamless integration with Home Assistant through MQTT discovery and native entity registration.

## Features

- 🤖 **AI-Powered Processing**: Uses advanced AI models for intelligent data analysis
- 🏠 **Native HA Integration**: Automatic entity registration via MQTT discovery
- 🔄 **Multi-Provider Support**: Supports OpenAI, Anthropic, and Google AI with automatic failover
- 🛡️ **Security First**: Encrypted API key storage and secure communication
- 📊 **Real-time Status**: Live status monitoring and control through Home Assistant
- 🔧 **Easy Configuration**: Simple web-based configuration through HA interface

## Installation

1. Add this repository to your Home Assistant add-on store:
   ```
   https://github.com/drewcifer/aicleaner_v3
   ```

2. Install the "AICleaner V3" add-on

3. Configure your API keys and settings

4. Start the add-on

## Configuration

### Required Settings

| Option | Description | Default |
|--------|-------------|---------|
| `primary_api_key` | Primary API key for your chosen AI provider | - |
| `device_id` | Unique identifier for this instance | `aicleaner_v3` |

### Optional Settings

| Option | Description | Default |
|--------|-------------|---------|
| `log_level` | Logging level (trace, debug, info, warning, error, fatal) | `info` |
| `backup_api_keys` | Array of backup API keys for failover | `[]` |
| `mqtt_discovery_prefix` | MQTT discovery topic prefix | `homeassistant` |

### Example Configuration

```yaml
log_level: info
primary_api_key: "sk-your-api-key-here"
backup_api_keys:
  - "sk-backup-key-1"
  - "sk-backup-key-2"
device_id: "aicleaner_v3"
mqtt_discovery_prefix: "homeassistant"
```

## Entities

The add-on automatically creates the following entities in Home Assistant:

### Sensors
- `sensor.aicleaner_status` - Current operational status
- `sensor.aicleaner_last_run` - Timestamp of last processing run

### Switches
- `switch.aicleaner_enabled` - Enable/disable the service

### Services
- `aicleaner.start_processing` - Manually trigger processing
- `aicleaner.reload_config` - Reload configuration

## Support

If you encounter issues:

1. Check the add-on logs in Home Assistant
2. Verify your API keys are valid
3. Ensure MQTT broker is running
4. Review the configuration settings

For bug reports and feature requests, visit: https://github.com/drewcifer/aicleaner_v3/issues

## Changelog & Releases

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg