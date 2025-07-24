# AICleaner V3 Home Assistant Add-on

![Logo](https://github.com/drewcifer/aicleaner_v3/raw/main/images/logo.png)

[![GitHub Release](https://img.shields.io/github/release/drewcifer/aicleaner_v3.svg?style=flat-square)](https://github.com/drewcifer/aicleaner_v3/releases)
[![License](https://img.shields.io/github/license/drewcifer/aicleaner_v3.svg?style=flat-square)](LICENSE)

## About

AICleaner V3 is an AI-powered Home Assistant add-on designed for personal, hobbyist use. It provides intelligent device management, MQTT discovery, and AI-enhanced automation capabilities to make your smart home more responsive and intuitive.

## Features

- **🤖 AI-Powered Automation**: Advanced AI integration for intelligent device control
- **📡 MQTT Discovery**: Automatic device discovery and entity registration  
- **🔄 Multi-Provider Support**: OpenAI, Google Gemini, Anthropic Claude, and Ollama
- **📊 Performance Monitoring**: Built-in performance tracking and optimization
- **🏠 Native HA Integration**: Deep Home Assistant integration with Supervisor API
- **🛡️ Security First**: Built-in security scanning and validation
- **📈 Real-time Analytics**: Comprehensive monitoring and reporting

## Installation

### Method 1: Add-on Store (Recommended)

1. **Add Repository**: In Home Assistant, navigate to **Supervisor → Add-on Store → ⋮ → Repositories**
2. **Add URL**: `https://github.com/drewcifer/aicleaner_v3`
3. **Find Add-on**: Look for "AICleaner V3" in the add-on store
4. **Install**: Click "Install" and wait for completion
5. **Configure**: Set your AI provider API keys in the Configuration tab
6. **Start**: Click "Start" to launch the add-on

### Method 2: Manual Installation

```bash
# SSH into your Home Assistant instance
cd /addons
git clone https://github.com/drewcifer/aicleaner_v3.git
# Restart Supervisor to detect the new add-on
```

## Configuration

The add-on supports extensive configuration through the Home Assistant UI:

### Basic Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `log_level` | Logging verbosity | `info` |
| `primary_api_key` | Primary AI provider API key | `""` |
| `backup_api_keys` | Fallback API keys for reliability | `[]` |
| `mqtt_discovery_prefix` | MQTT discovery topic prefix | `homeassistant` |
| `device_id` | Unique device identifier | `aicleaner_v3` |

### Advanced Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `testing_mode` | Enable testing and debug features | `false` |
| `performance_monitoring` | Enable performance tracking | `true` |
| `ai_provider_timeout` | AI provider timeout in seconds | `30` |

### Example Configuration

```yaml
log_level: info
primary_api_key: "sk-your-openai-api-key-here"
backup_api_keys:
  - "your-gemini-api-key"
  - "your-anthropic-api-key"
mqtt_discovery_prefix: "homeassistant"
device_id: "aicleaner_living_room"
testing_mode: false
performance_monitoring: true
ai_provider_timeout: 30
```

## Usage

Once installed and configured:

1. **Entities**: The add-on automatically creates Home Assistant entities:
   - `sensor.aicleaner_v3_status` - Addon status and health
   - `switch.aicleaner_v3_enabled` - Enable/disable automation

2. **Services**: Available Home Assistant services:
   - `aicleaner_v3.reload_config` - Reload configuration
   - `aicleaner_v3.restart_ai_providers` - Restart AI connections

3. **Automations**: Use the entities in your Home Assistant automations:
   ```yaml
   - alias: "AICleaner Status Monitor"
     trigger:
       - platform: state
         entity_id: sensor.aicleaner_v3_status
         to: "error"
     action:
       - service: notify.notify
         data:
           message: "AICleaner encountered an error"
   ```

## API Providers

### Supported Providers

- **OpenAI**: GPT-3.5, GPT-4 models
- **Google Gemini**: Gemini Pro, Gemini Pro Vision
- **Anthropic Claude**: Claude 3 Haiku, Sonnet, Opus
- **Ollama**: Local LLM deployment

### API Key Setup

1. **OpenAI**: Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. **Google Gemini**: Generate API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
3. **Anthropic**: Obtain key from [Anthropic Console](https://console.anthropic.com/)
4. **Ollama**: Install locally or use remote instance

## Troubleshooting

### Common Issues

#### Add-on Won't Start
- **Check logs**: Supervisor → AICleaner V3 → Logs
- **Verify API keys**: Ensure API keys are valid and have sufficient credits
- **Network connectivity**: Confirm internet access for AI providers

#### No Entities Created
- **MQTT integration**: Ensure MQTT is configured in Home Assistant
- **Discovery prefix**: Verify `mqtt_discovery_prefix` matches HA configuration
- **Device ID conflicts**: Try changing `device_id` to a unique value

#### Poor Performance
- **Resource allocation**: Ensure adequate CPU/RAM available
- **AI provider timeouts**: Increase `ai_provider_timeout` for slow networks
- **Disable performance monitoring**: Set `performance_monitoring: false` for resource-constrained systems

### Debug Mode

Enable debug logging for troubleshooting:

```yaml
log_level: debug
testing_mode: true
```

### Support

- **Issues**: [GitHub Issues](https://github.com/drewcifer/aicleaner_v3/issues)
- **Documentation**: [Full Documentation](https://github.com/drewcifer/aicleaner_v3/wiki)
- **Community**: [Home Assistant Community Forum](https://community.home-assistant.io/)

## Development

### Testing Framework

AICleaner V3 includes comprehensive testing:

```bash
# Run integration tests
cd addons/aicleaner_v3
./scripts/run-ha-tests.sh

# Manual testing setup
./scripts/setup-ha-token.sh
docker-compose -f docker-compose.test.yml up
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Run the test suite
4. Submit a pull request

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Home Assistant  │◄──►│   AICleaner V3  │◄──►│  AI Providers   │
│                 │    │                 │    │                 │
│ • Entities      │    │ • MQTT Bridge   │    │ • OpenAI        │
│ • Services      │    │ • AI Coordinator│    │ • Gemini        │
│ • Automations   │    │ • Device Mgmt   │    │ • Claude        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Performance

- **Memory Usage**: ~50-100MB typical
- **CPU Usage**: <5% on modern hardware
- **Network**: Minimal, only for AI API calls
- **Storage**: <10MB installation size

## Security

- **Non-privileged**: Runs without root privileges
- **Network isolation**: Only required network access
- **API key encryption**: Secure storage of sensitive data
- **Regular updates**: Automated security scanning

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.