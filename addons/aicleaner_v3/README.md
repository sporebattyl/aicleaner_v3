# AICleaner V3 Add-on

**AI-powered cleaning task management with intelligent zone monitoring and automatic dashboard integration for Home Assistant.**

[![Version](https://img.shields.io/badge/version-1.2.4-blue.svg)](https://github.com/sporebattyl/aicleaner_v3)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Addon-blue.svg)](https://www.home-assistant.io/)
[![Docker](https://img.shields.io/badge/docker-multi--arch-blue.svg)](https://hub.docker.com/)

## 🚀 Quick Start

### Prerequisites
- Home Assistant OS, Supervised, or Container installation
- At least one camera entity in Home Assistant
- At least one todo list entity (shopping lists, tasks, etc.)
- **Optional but recommended**: MQTT integration for enhanced features

### Installation

1. **Add Repository** (if installing from GitHub):
   - In Home Assistant, go to **Settings** → **Add-ons** → **Add-on Store**
   - Click **⋮** (three dots) → **Repositories**
   - Add: `https://github.com/sporebattyl/aicleaner_v3`

2. **Install Add-on**:
   - Find "AICleaner V3" in the add-on store
   - Click **Install**

3. **Basic Configuration**:
   ```yaml
   default_camera: "camera.living_room_camera"  # Your camera entity ID
   default_todo_list: "todo.cleaning_tasks"     # Your todo list entity ID
   primary_api_key: ""                          # Optional: AI API key (uses local Ollama if empty)
   ```

4. **Start the Add-on**:
   - Click **Start**
   - Check the **Log** tab for startup messages
   - Access via **Home Assistant sidebar** → **AICleaner V3**

## 📋 Configuration Reference

### Essential Settings

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `default_camera` | string | ✅ Yes | `""` | Camera entity ID for monitoring |
| `default_todo_list` | string | ✅ Yes | `""` | Todo list entity ID for task creation |
| `log_level` | list | No | `info` | Log verbosity: debug, info, warning, error |
| `device_id` | string | No | `aicleaner_v3` | Unique device identifier |

### AI Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `primary_api_key` | string | No | `""` | Primary AI API key (Gemini, OpenAI, etc.) |
| `backup_api_keys` | list | No | `[]` | Backup API keys for failover |

> **Note**: If no API keys are provided, the add-on will use local Ollama for AI processing.

### MQTT Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `mqtt_discovery_prefix` | string | No | `homeassistant` | MQTT discovery prefix |
| `mqtt_external_broker` | boolean | No | `false` | Use external MQTT broker |
| `mqtt_host` | string | No* | `""` | External MQTT broker host |
| `mqtt_port` | port | No | `1883` | External MQTT broker port |
| `mqtt_username` | string | No | `""` | External MQTT username |
| `mqtt_password` | password | No | `""` | External MQTT password |

*Required if `mqtt_external_broker` is `true`

### Advanced Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `enable_zones` | boolean | No | `false` | Enable zone-based monitoring |
| `zones` | list | No | `[]` | Zone definitions for advanced monitoring |
| `debug_mode` | boolean | No | `false` | Enable debug logging |
| `auto_dashboard` | boolean | No | `true` | Auto-create dashboard cards |

## 🔧 Setup Guide

### Step 1: Find Your Entity IDs

1. **Camera Entities**:
   - Go to **Settings** → **Devices & Services** → **Entities**
   - Filter by "camera" or search for your camera name
   - Copy the entity ID (e.g., `camera.living_room_camera`)

2. **Todo List Entities**:
   - Look for todo/shopping list entities
   - Common examples: `todo.shopping_list`, `todo.tasks`
   - Or create a new one in **Settings** → **Devices & Services** → **Add Integration** → "Shopping List"

### Step 2: MQTT Setup (Recommended)

**Option A: Home Assistant MQTT Broker (Recommended)**
1. Install **Mosquitto broker** add-on from the Add-on Store
2. Configure username/password in Mosquitto settings
3. Add **MQTT** integration in **Settings** → **Devices & Services**
4. Restart AICleaner V3 add-on

**Option B: External MQTT Broker**
1. Set `mqtt_external_broker: true` in AICleaner V3 configuration
2. Configure `mqtt_host`, `mqtt_port`, `mqtt_username`, `mqtt_password`
3. Restart the add-on

### Step 3: AI Provider Setup (Optional)

**Local Processing (Default)**
- No setup required - uses local Ollama
- Slower but completely private

**Cloud AI (Recommended for better performance)**
1. **Gemini AI** (Recommended):
   - Get API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Add to `primary_api_key` field

2. **OpenAI/Anthropic**:
   - Get API keys from respective providers
   - Add to configuration

## 🎮 Usage

### Web Interface
1. Access via Home Assistant sidebar → **AICleaner V3**
2. View real-time status and configuration
3. Test AI generation capabilities
4. Monitor entity selections

### Home Assistant Integration
- **Entities**: Automatically created via MQTT discovery
  - `sensor.aicleaner_status` - Current status
  - `switch.aicleaner_enabled` - Enable/disable monitoring
  - `sensor.aicleaner_config_status` - Configuration status

### Automation Example
```yaml
animation:
  - alias: "AICleaner Notification"
    trigger:
      platform: state
      entity_id: sensor.aicleaner_status
      to: "task_created"
    action:
      service: notify.mobile_app
      data:
        message: "New cleaning task created by AICleaner!"
```

## 🏗️ Architecture

### Multi-Architecture Support
- **amd64** - Intel/AMD 64-bit
- **aarch64** - ARM 64-bit (Raspberry Pi 4, etc.)
- **armhf** - ARM 32-bit (Raspberry Pi 3, etc.)
- **armv7** - ARMv7 32-bit

### AI Provider Failover
1. **Primary Provider** - Your configured API key
2. **Backup Providers** - Additional API keys for redundancy
3. **Local Fallback** - Ollama for offline operation

### Security Features
- Non-root container execution
- Encrypted API key storage
- Input validation and sanitization
- Secure MQTT communication

## 🔍 Troubleshooting

### Common Issues

**"Configuration needed" Status**
- Ensure `default_camera` and `default_todo_list` are set
- Verify entity IDs exist in Home Assistant

**"MQTT unavailable" Warning**
- Install and configure MQTT broker (see MQTT Setup above)
- Check MQTT integration in Home Assistant

**AI Generation Failures**
- Check API key validity
- Verify internet connection for cloud providers
- Check logs for specific error messages

**Web Interface Not Loading**
- Ensure add-on is started and running
- Check Home Assistant ingress configuration
- Try refreshing the browser

### Debug Mode
Enable debug logging in configuration:
```yaml
debug_mode: true
log_level: debug
```

### Log Analysis
Check add-on logs in Home Assistant:
1. **Settings** → **Add-ons** → **AICleaner V3**
2. Click **Log** tab
3. Look for error messages and warnings

## 📚 Advanced Usage

### Zone-Based Monitoring
Enable advanced zone monitoring for different areas:

```yaml
enable_zones: true
zones:
  - name: "Kitchen"
    camera: "camera.kitchen_cam"
    todo_list: "todo.kitchen_tasks"
    ai_prompt: "Focus on kitchen cleanliness"
  - name: "Living Room"
    camera: "camera.living_room"
    todo_list: "todo.living_room_tasks"
    ai_prompt: "Look for general tidiness"
```

### API Integration
The add-on provides REST API endpoints:
- `GET /api/status` - Current status
- `GET /api/config` - Current configuration
- `POST /api/test_generation` - Test AI generation

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/sporebattyl/aicleaner_v3/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sporebattyl/aicleaner_v3/discussions)
- **Documentation**: [Full Documentation](https://github.com/sporebattyl/aicleaner_v3/wiki)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Home Assistant community for excellent addon framework
- AI providers (Google, OpenAI, Anthropic) for powerful APIs
- Ollama project for local AI capabilities