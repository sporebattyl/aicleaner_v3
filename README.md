# AICleaner v3 - v1.0.0 - Home Assistant Add-on

[![GitHub Release](https://img.shields.io/github/release/drewcifer/aicleaner_v3.svg?style=flat-square)](https://github.com/drewcifer/aicleaner_v3/releases)
[![License](https://img.shields.io/github/license/drewcifer/aicleaner_v3.svg?style=flat-square)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg?style=flat-square)](https://www.home-assistant.io/)

Advanced AI-powered Home Assistant automation with intelligent device management, multi-provider AI integration, and comprehensive privacy protection.

## ✨ Features

### 🤖 **Multi-Provider AI Integration**
- Support for OpenAI, Anthropic, Google Gemini, and Ollama
- Intelligent load balancing and failover
- Cost optimization with budget tracking
- Real-time performance monitoring

### 🏠 **Smart Home Integration**
- Native Home Assistant entities and services
- Automatic device discovery and classification
- Zone-based automation management
- Real-time event synchronization

### 🔒 **Privacy & Security**
- Advanced privacy pipeline with face/license plate redaction
- Comprehensive security auditing
- Encrypted configuration storage
- Local processing with optional cloud integration

### 🎯 **Intelligent Automation**
- ML-powered device optimization
- Adaptive automation rules
- Performance analytics and insights
- Voice control and mobile app integration

### 📊 **Management Interface**
- Beautiful web-based dashboard
- Real-time system monitoring
- Provider management and analytics
- Comprehensive logging and diagnostics

## 🚀 Quick Start

### Prerequisites
- Home Assistant Core 2024.1.0 or later
- At least 512MB RAM available
- Internet connection for AI provider access

### Installation

1. **Add the Repository**
   ```
   Add this repository to your Home Assistant Add-on Store:
   https://github.com/drewcifer/aicleaner_v3
   ```

2. **Install the Add-on**
   - Navigate to **Supervisor > Add-on Store**
   - Find "AICleaner v3" and click **Install**
   - Wait for installation to complete

3. **Configure the Add-on**
   - Click **Configuration** tab
   - Add your AI provider API keys
   - Configure zones and automation preferences
   - Click **Save**

4. **Start the Add-on**
   - Click **Start** and wait for startup
   - Check the **Log** tab for any errors
   - The web interface will be available via **Open Web UI**

### Basic Configuration

```yaml
log_level: info
ai_providers:
  - provider: openai
    enabled: true
    api_key: "your-openai-api-key"
    model: "gpt-4o"
  - provider: gemini
    enabled: true
    api_key: "your-gemini-api-key"
    model: "gemini-1.5-pro"
zones:
  - name: "Living Room"
    enabled: true
    devices: []
    automation_rules: []
security:
  enabled: true
  audit_logging: true
performance:
  auto_optimization: true
  resource_monitoring: true
  caching: true
privacy:
  enabled: true
  level: "balanced"
```

## 📱 Usage

### Home Assistant Dashboard

Add AICleaner v3 entities to your dashboard:

```yaml
type: entities
title: AICleaner v3
entities:
  - entity: sensor.aicleaner_v3_system_health
    name: System Health
  - entity: sensor.aicleaner_v3_total_requests
    name: Total Requests
  - entity: sensor.aicleaner_v3_active_providers
    name: Active Providers
  - entity: switch.aicleaner_v3_system_enabled
    name: System Enabled
```

### Automation Examples

**Enable backup provider on main provider failure:**
```yaml
automation:
  - alias: "AICleaner Failover"
    trigger:
      - platform: state
        entity_id: sensor.aicleaner_v3_system_health
        to: "degraded"
    action:
      - service: aicleaner_v3.control_provider
        data:
          provider_id: "backup_provider"
          action: "enable"
```

**Daily cost monitoring:**
```yaml
automation:
  - alias: "AICleaner Cost Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.aicleaner_v3_daily_cost
        above: 5.00
    action:
      - service: notify.mobile_app
        data:
          message: "AICleaner daily cost exceeded $5.00"
```

### Services

| Service | Description |
|---------|-------------|
| `aicleaner_v3.reload_config` | Reload configuration |
| `aicleaner_v3.control_provider` | Enable/disable providers |
| `aicleaner_v3.control_zone` | Control automation zones |
| `aicleaner_v3.set_strategy` | Update load balancing strategy |

### Web Interface

Access the web interface through:
- **Sidebar**: Click "AICleaner v3" in the Home Assistant sidebar
- **Add-on Page**: Click "Open Web UI" on the add-on page
- **Direct URL**: `http://your-home-assistant:8000`

## 🔧 Configuration Reference

### AI Providers

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `provider` | string | - | Provider name (openai, gemini, anthropic, ollama) |
| `enabled` | boolean | false | Enable/disable provider |
| `api_key` | password | - | API key for cloud providers |
| `model` | string | - | Model to use (optional) |
| `max_tokens` | integer | 2000 | Maximum tokens per request |

### Zones

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | - | Zone name |
| `enabled` | boolean | false | Enable/disable zone |
| `devices` | list | [] | List of device entity IDs |
| `automation_rules` | list | [] | Automation rules for the zone |

### Security

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | true | Enable security features |
| `encryption` | boolean | true | Encrypt configuration |
| `audit_logging` | boolean | true | Enable audit logging |

### Performance

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `auto_optimization` | boolean | true | Enable auto-optimization |
| `resource_monitoring` | boolean | true | Monitor resource usage |
| `caching` | boolean | true | Enable response caching |
| `max_memory_mb` | integer | 512 | Maximum memory usage |
| `max_cpu_percent` | integer | 80 | Maximum CPU usage |

### Privacy

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | true | Enable privacy features |
| `level` | string | balanced | Privacy level (speed/balanced/paranoid) |

## 📊 Monitoring

### Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.aicleaner_v3_system_health` | sensor | Overall system health |
| `sensor.aicleaner_v3_total_requests` | sensor | Total API requests |
| `sensor.aicleaner_v3_active_providers` | sensor | Number of active providers |
| `sensor.aicleaner_v3_daily_cost` | sensor | Daily usage cost |
| `switch.aicleaner_v3_system_enabled` | switch | System enable/disable |
| `sensor.aicleaner_v3_provider_*_status` | sensor | Provider status |
| `switch.aicleaner_v3_provider_*_enabled` | switch | Provider enable/disable |

### Logs

Monitor add-on logs through:
- **Home Assistant**: Supervisor > Add-ons > AICleaner v3 > Log
- **Web Interface**: Logs tab in the web interface
- **Log Files**: Available in `/share/aicleaner_v3/logs/`

## 🛠️ Troubleshooting

### Common Issues

**Add-on won't start:**
1. Check Home Assistant logs for errors
2. Verify API keys are valid
3. Ensure sufficient memory available
4. Check network connectivity

**Web interface not accessible:**
1. Verify ingress is enabled in Home Assistant
2. Check port 8000 is not blocked
3. Restart the add-on
4. Check add-on logs for errors

**AI providers not responding:**
1. Verify API keys are correct
2. Check provider status in web interface
3. Review rate limits and quotas
4. Test network connectivity

### Getting Help

1. **Check Logs**: Always check add-on logs first
2. **Documentation**: Review configuration documentation
3. **Issues**: Create an issue on GitHub with logs and configuration
4. **Community**: Visit the Home Assistant Community forum

## 🔄 Updates

The add-on will automatically check for updates. To update:

1. Go to **Supervisor > Add-ons > AICleaner v3**
2. Click **Update** if available
3. Wait for update to complete
4. Restart the add-on

## 🤝 Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Home Assistant team for the amazing platform
- AI providers for their excellent APIs
- Community contributors and testers

---

**Made with ❤️ for the Home Assistant community**