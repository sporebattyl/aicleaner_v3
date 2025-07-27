# AICleaner V3 - Home Assistant Add-on

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield] ![Supports armhf Architecture][armhf-shield] ![Supports armv7 Architecture][armv7-shield] ![Supports i386 Architecture][i386-shield]

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

An intelligent Home Assistant add-on that uses AI to monitor your home cameras and automatically generate cleaning task lists based on visual analysis. Never miss a mess with AI-powered zone monitoring and automated task management.

## 🚀 Features

- **🤖 AI-Powered Visual Analysis**: Uses advanced AI models to analyze camera feeds and identify cleaning tasks
- **🏠 Intelligent Zone Monitoring**: Configure multiple zones with custom cameras and purposes
- **📋 Automated Task Generation**: Automatically creates and manages cleaning tasks in Home Assistant todo lists
- **🔄 MQTT Discovery Integration**: Seamlessly integrates with Home Assistant via MQTT
- **📊 Dashboard Integration**: Auto-configures dashboard cards for easy monitoring
- **🛡️ Comprehensive Validation**: Input validation and error handling for reliable operation
- **🔒 Security-First Design**: Secure configuration with proper permissions and validation
- **🌐 Web Interface**: Built-in web UI for configuration and monitoring
- **⚡ Health Monitoring**: Real-time system health checks and error reporting
- **🔔 Smart Notifications**: User notifications for critical events and errors

## 📋 Requirements

### Home Assistant Requirements
- **Home Assistant**: Version 2023.1.0 or newer
- **MQTT Integration**: Must be configured and running
- **Camera Entities**: At least one camera entity for monitoring
- **Todo Integration**: For task list management

### Hardware Requirements
- **Memory**: 512MB RAM minimum, 1GB recommended
- **Storage**: 100MB available space
- **CPU**: ARM64, AMD64, or compatible architecture

### API Keys (Optional)
- **Google AI API Key**: For cloud-based AI analysis (recommended)
- **Backup API Keys**: Additional keys for redundancy
- **Local Ollama**: Alternative to cloud APIs (requires separate setup)

## 🛠️ Installation

### 1. Add the Repository
Add this repository to your Home Assistant add-on store:

```
https://github.com/drewcifer/aicleaner_v3
```

### 2. Install the Add-on
1. Navigate to **Supervisor** → **Add-on Store**
2. Find "AICleaner V3" in the store
3. Click **Install**

### 3. Configure the Add-on
Edit the add-on configuration with your preferences:

```yaml
log_level: info
device_id: aicleaner_v3
primary_api_key: "your-google-ai-api-key"  # Optional
backup_api_keys: []                        # Optional
mqtt_discovery_prefix: homeassistant
debug_mode: false
auto_dashboard: true
```

### 4. Start the Add-on
1. Click **Start**
2. Enable **Auto-start** if desired
3. Check logs for successful startup

## ⚙️ Configuration

### Required Settings

| Parameter | Description | Default | Type |
|-----------|-------------|---------|------|
| `log_level` | Logging verbosity (debug, info, warning, error) | `info` | `list` |
| `device_id` | Unique device identifier | `aicleaner_v3` | `str` |

### API Configuration

| Parameter | Description | Default | Type |
|-----------|-------------|---------|------|
| `primary_api_key` | Primary Google AI API key | `""` | `password?` |
| `backup_api_keys` | List of backup API keys | `[]` | `[password?]` |

### MQTT Settings

| Parameter | Description | Default | Type |
|-----------|-------------|---------|------|
| `mqtt_discovery_prefix` | MQTT discovery prefix | `homeassistant` | `str` |

### Advanced Options

| Parameter | Description | Default | Type |
|-----------|-------------|---------|------|
| `debug_mode` | Enable debug logging | `false` | `bool` |
| `auto_dashboard` | Auto-configure dashboard | `true` | `bool` |

## 🏠 Zone Configuration

Access the web interface via Home Assistant Ingress or at the addon's web port.

### Adding Zones
1. Click **Configure Zones**
2. Click **Add New Zone**
3. Configure zone parameters:
   - **Zone Name**: Descriptive name (e.g., "Kitchen")
   - **Purpose**: What this zone is for (e.g., "Cooking and dining area")
   - **Camera Entity**: Select monitoring camera
   - **Todo List Entity**: Select target todo list
   - **Check Interval**: Minutes between checks (1-1440)
   - **Ignore Rules**: Things to ignore (optional)

### Zone Examples

```yaml
# Kitchen Zone
name: "Kitchen"
purpose: "Cooking and dining area"
camera_entity: "camera.kitchen"
todo_list_entity: "todo.household_tasks"
interval_minutes: 30
ignore_rules:
  - "normal cooking mess"
  - "dishes in sink"

# Living Room Zone
name: "Living Room"
purpose: "Entertainment and relaxation area"
camera_entity: "camera.living_room"
todo_list_entity: "todo.cleaning_tasks"
interval_minutes: 60
ignore_rules:
  - "throw pillows"
  - "remote controls"
```

## 🌐 Web Interface

The add-on provides a comprehensive web interface accessible via Home Assistant Ingress:

### Status Monitoring
- **Real-time Status**: Addon health and operational state
- **Connection Health**: MQTT and core service connectivity
- **AI Metrics**: Request counts and last analysis time
- **Component Status**: Individual system component health

### Configuration Tools
- **Zone Management**: Add, edit, and remove monitoring zones
- **Configuration Validation**: Comprehensive system validation
- **Error Monitoring**: Recent errors and system issues
- **Notification History**: User notification tracking

### Available Actions
- **Test AI Generation**: Verify AI connectivity and functionality
- **Refresh Status**: Update system status display
- **Show Configuration**: View current addon configuration
- **Configure Zones**: Manage zone settings and parameters
- **Validate Configuration**: Run comprehensive system checks

## 🛡️ Security Features

### Input Validation
- **Entity ID Validation**: Ensures proper Home Assistant entity format
- **Zone Name Sanitization**: Prevents injection attacks and invalid characters
- **API Key Validation**: Secure API key format verification
- **File Path Protection**: Prevents directory traversal attacks

### Permission Management
- **Non-privileged Execution**: Runs as non-root user
- **Minimal Permissions**: Only required Home Assistant API access
- **Secure File Access**: Restricted to designated data directories
- **Environment Validation**: Secure environment variable handling

### Error Handling
- **Comprehensive Error Classification**: Categorized error handling
- **User-friendly Messages**: Clear error communication
- **Automatic Notifications**: Critical error alerting
- **Persistent Logging**: Error tracking and analysis

## 📊 Monitoring & Health Checks

### Health Endpoints
Access these endpoints via the web interface:

- `/api/health` - Comprehensive system health status
- `/api/errors` - Recent error information and statistics
- `/api/notifications` - Notification history
- `/api/validate_config` - Configuration validation results

### Health Check Components
- **Addon Status**: Core application health
- **MQTT Connection**: Message broker connectivity
- **Core Service**: AI processing service availability
- **Error Handler**: Error management system status

### MQTT Discovery Topics
```
homeassistant/sensor/aicleaner_v3_status/config
homeassistant/sensor/aicleaner_v3_last_analysis/config
homeassistant/button/aicleaner_v3_analyze_now/config
```

### Log Files
- `/data/aicleaner.log` - Application logs with rotation
- `/data/error_log.json` - Structured error tracking
- `/data/zones.json` - Zone configuration backup

## 🚨 Troubleshooting

### Common Issues

#### Add-on Won't Start
1. **Check Logs**: Review Home Assistant supervisor logs
2. **MQTT Status**: Verify MQTT integration is running
3. **Permissions**: Ensure required Home Assistant API permissions
4. **Configuration**: Use web interface validation tool

**Solution Steps:**
```bash
# Check MQTT integration
# Home Assistant → Settings → Devices & Services → MQTT

# Validate configuration
# Use web interface → Validate Configuration

# Check addon logs
# Supervisor → AICleaner V3 → Log tab
```

#### AI Analysis Not Working
1. **API Keys**: Verify Google AI API key configuration
2. **Connectivity**: Check internet connection
3. **Service Test**: Use "Test AI Generation" in web interface
4. **Error Logs**: Review API-specific errors

#### Camera Access Issues
1. **Entity Verification**: Confirm camera entities exist
2. **Permissions**: Check camera stream access rights
3. **Availability**: Ensure cameras are not locked by other services
4. **Testing**: Verify camera access in Home Assistant

#### Task Creation Problems
1. **Todo Integration**: Verify Home Assistant todo integration
2. **Entity Access**: Check todo list entity permissions
3. **Zone Configuration**: Review zone-to-todo list mappings

### Debug Mode
Enable comprehensive debugging:

```yaml
debug_mode: true
log_level: debug
```

### Configuration Validation
Use the built-in validation system:
1. Access web interface
2. Click **Validate Configuration**
3. Review validation results
4. Address reported issues

## 🔄 API Reference

### Core Endpoints

#### Status Information
```http
GET /api/status
Content-Type: application/json

Response:
{
  "status": "connected",
  "enabled": true,
  "mqtt_connected": true,
  "core_service_health": true,
  "ai_response_count": 42,
  "last_ai_request": "2024-01-15T10:30:00Z"
}
```

#### Health Monitoring
```http
GET /api/health
Content-Type: application/json

Response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "addon": {"status": "connected", "enabled": true},
    "mqtt": {"connected": true},
    "core_service": {"available": true}
  }
}
```

#### Zone Management
```http
GET /api/zones
POST /api/zones
Content-Type: application/json

POST Body:
{
  "zones": [
    {
      "name": "Kitchen",
      "camera_entity": "camera.kitchen",
      "todo_list_entity": "todo.household",
      "interval_minutes": 30
    }
  ]
}
```

#### Configuration Validation
```http
GET /api/validate_config
Content-Type: application/json

Response:
{
  "overall_status": "valid",
  "timestamp": "2024-01-15T10:30:00Z",
  "validations": {
    "environment": {"valid": true},
    "security": {"secure": true},
    "dependencies": {"satisfied": true}
  }
}
```

## 🎛️ Dashboard Integration

When `auto_dashboard` is enabled, the addon automatically creates:

### Auto-Generated Cards
- **Status Card**: Real-time addon health and metrics
- **Zone Cards**: Individual monitoring cards for each zone
- **Control Panel**: Quick action buttons for manual operations
- **Statistics Card**: AI usage analytics and trends

### Manual Dashboard Configuration
If auto-dashboard is disabled, add cards manually:

```yaml
# Status Card
type: entities
title: AICleaner V3 Status
entities:
  - sensor.aicleaner_v3_status
  - sensor.aicleaner_v3_last_analysis
  - switch.aicleaner_v3_enabled

# Zone Monitoring Card
type: picture-entity
title: Kitchen Monitoring
entity: camera.kitchen
camera_image: camera.kitchen
tap_action:
  action: call-service
  service: aicleaner.analyze_zone
  service_data:
    zone_name: Kitchen
```

## 🔧 Development & Contributing

### Local Development Setup
```bash
# Clone repository
git clone https://github.com/drewcifer/aicleaner_v3.git
cd aicleaner_v3

# Build development image
docker build -t aicleaner_v3:dev aicleaner_v3/

# Run tests
python -m pytest tests/
```

### Project Structure
```
aicleaner_v3/
├── config.yaml              # Home Assistant addon configuration
├── Dockerfile               # Container build definition
├── requirements.txt         # Python dependencies
├── run.sh                  # Container startup script
├── README.md               # This documentation
└── src/                    # Application source code
    ├── main.py             # Main application entry point
    ├── web_ui.py           # Web interface and API endpoints
    ├── validation.py       # Input validation and sanitization
    ├── error_handler.py    # Error management and notifications
    ├── config_validator.py # Configuration validation system
    └── mqtt_client.py      # MQTT integration
```

### Contributing Guidelines
1. **Fork** the repository
2. **Create** a feature branch
3. **Implement** changes with tests
4. **Validate** code quality and security
5. **Submit** a pull request

## 📝 Changelog

### Version 1.0.0 (Current)
- ✨ **New**: AI-powered zone monitoring with camera analysis
- ✨ **New**: Comprehensive input validation and security framework
- ✨ **New**: MQTT discovery integration with automatic entity creation
- ✨ **New**: Automatic dashboard configuration and management
- ✨ **New**: Web-based configuration interface with real-time status
- ✨ **New**: Advanced error handling with user notifications
- ✨ **New**: Health monitoring system with API endpoints
- ✨ **New**: Configuration validation and security checks
- 🛡️ **Security**: Non-privileged container execution
- 🛡️ **Security**: Input sanitization and validation
- 📊 **Monitoring**: Comprehensive health checks and error tracking

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Home Assistant Community** for integration patterns and best practices
- **Google AI** for Gemini API and advanced AI capabilities
- **Ollama Project** for local AI model support
- **MQTT Community** for reliable messaging protocols
- **All Contributors** and beta testers

## 🆘 Support

### Getting Help
- **📋 Issues**: [GitHub Issues](https://github.com/drewcifer/aicleaner_v3/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/drewcifer/aicleaner_v3/discussions)
- **🏠 Forum**: [Home Assistant Community](https://community.home-assistant.io/)

### Before Reporting Issues
1. Check existing [issues](https://github.com/drewcifer/aicleaner_v3/issues)
2. Use configuration validation tool
3. Review addon logs
4. Test with minimal configuration

### Issue Report Template
```
**Environment:**
- Home Assistant Version: 
- Addon Version: 
- Architecture: 

**Configuration:**
[Sanitized configuration without API keys]

**Problem Description:**
[Clear description of the issue]

**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Behavior:**
[What should happen]

**Logs:**
[Relevant log entries]
```

## 🔗 Links

- **🏠 Repository**: https://github.com/drewcifer/aicleaner_v3
- **📚 Documentation**: [Project Wiki](https://github.com/drewcifer/aicleaner_v3/wiki)
- **🐛 Bug Reports**: [Issue Tracker](https://github.com/drewcifer/aicleaner_v3/issues)
- **💡 Feature Requests**: [Discussions](https://github.com/drewcifer/aicleaner_v3/discussions)

---

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg