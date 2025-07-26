# AICleaner V3 - Installation Guide

## Quick Installation

### 1. Add Repository to Home Assistant
1. Go to **Supervisor** → **Add-on Store** → **⋮** (three dots menu) → **Repositories**
2. Add this URL:
   ```
   https://github.com/sporebattyl/aicleaner_v3
   ```
3. Click **Add**

### 2. Install the Add-on
1. Find "AICleaner V3" in the add-on store
2. Click **Install**
3. Wait for installation to complete

### 3. Basic Configuration
```yaml
log_level: info
device_id: aicleaner_v3
primary_api_key: "your-google-ai-api-key"  # Optional but recommended
default_camera: "camera.your_camera"       # Select from dropdown
default_todo_list: "todo.your_list"        # Select from dropdown
debug_mode: false
auto_dashboard: true
```

### 4. Start the Add-on
1. Click **Start**
2. Enable **Auto-start** if desired
3. Check logs for successful startup

## What's Next?

- **Entity Selection**: Use the dropdowns in configuration to select cameras and todo lists
- **Zone Setup**: Enable zones for advanced multi-room monitoring
- **Web Interface**: Access via Home Assistant Ingress for advanced configuration
- **Dashboard**: Auto-created cards will appear in your dashboard

## Need Help?

See the main [README.md](README.md) for detailed configuration, troubleshooting, and API documentation.