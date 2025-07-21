# AICleaner v3 Installation Guide

This guide provides detailed instructions for installing and configuring AICleaner v3 as a Home Assistant add-on.

## Prerequisites

Before installing AICleaner v3, ensure your system meets the following requirements:

### System Requirements

- **Home Assistant**: Core 2024.1.0 or later
- **Memory**: Minimum 512MB RAM available (1GB+ recommended)
- **Storage**: Minimum 500MB free space
- **Network**: Internet connection for AI provider access
- **Architecture**: Supports amd64, arm64, armv7, armhf, i386

### Supported Home Assistant Installations

- Home Assistant OS (Recommended)
- Home Assistant Supervised
- Home Assistant Container (with add-ons support)
- Home Assistant Core (manual installation required)

## Installation Methods

### Method 1: Add-on Store Installation (Recommended)

#### Step 1: Add Custom Repository

1. Open Home Assistant in your web browser
2. Navigate to **Supervisor** → **Add-on Store**
3. Click the **⋮** menu in the top-right corner
4. Select **Repositories**
5. Add the repository URL:
   ```
   https://github.com/drewcifer/aicleaner_v3
   ```
6. Click **Add** and wait for the repository to load

#### Step 2: Install the Add-on

1. In the Add-on Store, search for "AICleaner v3"
2. Click on the **AICleaner v3** add-on
3. Click **Install**
4. Wait for the installation to complete (this may take several minutes)

#### Step 3: Basic Configuration

1. Click the **Configuration** tab
2. Configure the following required settings:

```yaml
log_level: info
primary_api_key: "your-api-key-here"
backup_api_keys:
  - "backup-key-1"
  - "backup-key-2"
device_id: "aicleaner_v3"
mqtt_discovery_prefix: "homeassistant"
```

3. Replace `"your-api-key-here"` with your actual AI provider API key
4. Add backup API keys for failover (optional)
5. Customize device_id if you have multiple instances
6. Click **Save**

#### Step 4: Start the Add-on

1. Click the **Info** tab
2. Toggle **Start on boot** (recommended)
3. Click **Start**
4. Monitor the **Log** tab for startup messages
5. Once started, click **Open Web UI** to access the interface

## Configuration Guide

### API Keys Setup

#### OpenAI API Key

1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Click **Create new secret key**
3. Copy the key and add it to your configuration
4. Ensure you have sufficient credits/quota

#### Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click **Create API Key**
3. Copy the key and add it to your configuration
4. Enable the Generative Language API in Google Cloud Console

#### Anthropic Claude API Key

1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Navigate to **API Keys**
3. Click **Create Key**
4. Copy the key and add it to your configuration

### Zone Configuration

Configure zones to organize your smart home devices:

```yaml
zones:
  - name: "Living Room"
    enabled: true
    devices:
      - light.living_room_main
      - switch.living_room_fan
      - sensor.living_room_temperature
    automation_rules:
      - "optimize_lighting_based_on_time"
      - "adjust_climate_for_occupancy"
  
  - name: "Bedroom"
    enabled: true
    devices:
      - light.bedroom_ceiling
      - climate.bedroom_ac
      - binary_sensor.bedroom_motion
    automation_rules:
      - "nighttime_optimization"
      - "morning_routine"
```

### Security Configuration

Enable security features for enhanced protection:

```yaml
security:
  enabled: true
  encryption: true
  audit_logging: true
```

### Performance Tuning

Optimize performance for your system:

```yaml
performance:
  auto_optimization: true
  resource_monitoring: true
  caching: true
  max_memory_mb: 1024        # Adjust based on available RAM
  max_cpu_percent: 70        # Adjust based on system load
```

## Troubleshooting

### Common Installation Issues

#### Add-on Won't Install

**Symptoms**: Installation fails or times out

**Solutions**:
1. Check Home Assistant supervisor logs
2. Ensure sufficient disk space (>500MB)
3. Verify internet connectivity
4. Try restarting Home Assistant supervisor

#### Add-on Won't Start

**Symptoms**: Add-on shows "stopped" status

**Solutions**:
1. Check add-on logs for error messages
2. Verify configuration syntax is correct
3. Ensure API keys are valid
4. Check available memory (need 512MB+)

### Getting Support

If you encounter issues:

1. **Check Documentation**: Review this guide and README.md
2. **Search Issues**: Check GitHub issues for similar problems
3. **Create Issue**: Report on GitHub with full details
4. **Community**: Ask on Home Assistant Community forum

## Updates

### Automatic Updates

The add-on will check for updates automatically. To update:

1. Go to **Supervisor** → **Add-ons** → **AICleaner v3**
2. Click **Update** if available
3. Review changelog before updating
4. Click **Update** to proceed
5. Restart the add-on if required

---

For additional support, visit the [AICleaner v3 GitHub repository](https://github.com/drewcifer/aicleaner_v3) or the [Home Assistant Community](https://community.home-assistant.io/).