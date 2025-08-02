# AICleaner V3

AI-powered cleaning task management with intelligent zone monitoring and automatic dashboard integration.

## Installation

1. Add this repository to your Home Assistant Add-on Store
2. Find "AICleaner V3" in the add-on store
3. Click Install
4. **IMPORTANT**: Set up MQTT integration first (see MQTT Setup section below)
5. Configure the add-on (see Configuration section)
6. Click Start

## MQTT Setup (Required for Full Functionality)

AICleaner V3 requires MQTT for entity discovery and automatic integration with Home Assistant. Without MQTT, the addon will work with limited functionality.

### Step 1: Install Mosquitto Broker

1. Go to **Settings → Add-ons → Add-on Store**
2. Search for "Mosquitto broker"
3. Click **Install**
4. Once installed, go to the **Configuration** tab
5. Add a user account in the "Logins" section:
   ```yaml
   logins:
     - username: aicleaner
       password: your_secure_password
   ```
6. Click **Save**
7. Go to the **Info** tab and click **Start**
8. Enable **"Start on boot"** for reliability

### Step 2: Configure MQTT Integration

1. Go to **Settings → Devices & Services**
2. If MQTT integration is not already configured:
   - Click **+ Add Integration**
   - Search for "MQTT" and select it
   - **Broker**: Use `core-mosquitto` (for the addon) or your external broker IP
   - **Port**: `1883` (default)
   - **Username**: Enter the username from Step 1
   - **Password**: Enter the password from Step 1
   - Click **Submit**

### Step 3: Verify MQTT Setup

1. Go to **Settings → Devices & Services → MQTT**
2. You should see the MQTT integration configured
3. In the addon logs, you should see:
   ```
   ✓ MQTT broker configured: core-mosquitto:1883
   ✓ Entity discovery and MQTT features will be available
   ```

### Troubleshooting MQTT

If you see warnings like "MQTT service not available":

1. **Check Mosquitto Status**: Ensure the Mosquitto broker addon is running
2. **Verify MQTT Integration**: Go to Settings → Devices & Services and confirm MQTT is configured
3. **Restart AICleaner**: After setting up MQTT, restart the AICleaner addon
4. **Check Logs**: Look for MQTT connection messages in the addon logs

**Note**: The addon will continue to work without MQTT, but with reduced functionality (no automatic entity discovery).

## Configuration

### Basic Configuration

**Default Camera**: Enter the entity ID of your camera (e.g., `camera.rowan_room_fluent`)
- Find your camera entity IDs in Home Assistant under Settings → Devices & Services → Entities

**Default Todo List**: Enter the entity ID of your todo list (e.g., `todo.rowan_room_cleaning_to_do`)
- Create todo lists in Home Assistant and find their entity IDs in the same location

### Advanced Options

- **Debug Mode**: Enable detailed logging for troubleshooting
- **Enable Zones**: Advanced zone-based monitoring (requires additional configuration)
- **Auto Dashboard**: Automatically create Home Assistant dashboard cards

## Usage

1. Configure your camera and todo list entities
2. Start the add-on
3. The addon will monitor your specified camera for cleaning tasks
4. Tasks will be automatically added to your specified todo list
5. View progress through the AICleaner interface in your Home Assistant sidebar

## Support

For issues and feature requests, visit: https://github.com/sporebattyl/aicleaner_v3