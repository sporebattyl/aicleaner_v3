# AICleaner V3 Real Testing Guide

## Current Status: ✅ REAL Testing Environment Active

**Home Assistant:** http://localhost:8123  
**Test MQTT Broker:** localhost:1884  
**Container Status:** Running and healthy

## Step-by-Step Real Testing Process

### 1. Initial Home Assistant Setup
1. Open http://localhost:8123 in your browser
2. Complete the initial setup wizard:
   - Create admin user account
   - Set your location (for timezone)
   - Choose whether to share analytics (your choice)
   - Complete onboarding

### 2. Install AICleaner V3 Addon (REAL INSTALLATION)
1. Navigate to: **Settings → Add-ons → Add-on Store**
2. Look for **"AICleaner V3"** under **"Local add-ons"** section
3. Click on it and select **"Install"**
   - This will trigger the real Docker build process
   - It will install all Python dependencies from requirements.txt
   - This may take 2-5 minutes depending on your system

### 3. Configure Addon with Real Credentials
Once installed, go to the **Configuration** tab and set:

```yaml
# AI Provider Settings (USE YOUR REAL API KEYS)
active_provider: "ollama"  # or "openai", "anthropic", "gemini"
api_key_openai: "sk-your-real-openai-key"
api_key_gemini: "your-real-gemini-key"
ollama_base_url: "http://host.docker.internal:11434"  # if running Ollama locally

# MQTT Broker Settings (for test environment)
mqtt_host: "mqtt-dev-test"  # Container name for internal communication
mqtt_port: 1883
mqtt_username: ""  # Empty for test broker
mqtt_password: ""  # Empty for test broker

# Logging
log_level: "debug"  # For testing purposes
```

### 4. Start the Addon and Monitor
1. Click **"Start"** in the addon interface
2. Go to the **"Log"** tab immediately
3. Watch for:
   - ✅ Successful startup messages
   - ✅ MQTT broker connection
   - ✅ AI provider authentication
   - ❌ Any error messages or exceptions

### 5. Test Core Functionality
1. Navigate to **Developer Tools → Services**
2. Look for services starting with `aicleaner_v3`
3. Call a test service with sample data
4. Check the **Log** tab for processing results

### 6. Verify Entity Creation
1. Go to **Settings → Devices & Services → Entities**
2. Search for "aicleaner"
3. Verify entities are created and have reasonable states

## Performance Monitoring Commands

```bash
# Monitor container resource usage in real-time
docker stats

# Check addon logs
docker-compose logs -f homeassistant

# Check MQTT broker logs  
docker-compose logs -f mosquitto

# System resource monitoring
htop
```

## Success Criteria for This Phase

- [ ] HA setup completed successfully
- [ ] AICleaner addon installs without build errors
- [ ] Addon starts without crashes  
- [ ] MQTT connection established
- [ ] At least one AI provider authenticates successfully
- [ ] Entities appear in HA with valid states
- [ ] Service calls execute without errors
- [ ] No memory leaks after 30 minutes of operation

## Next Phase: Hardware-Specific Testing

Once basic functionality is verified in this Docker environment, we'll deploy to:
1. **AMD 8845HS system** - Performance and multi-core utilization testing
2. **Intel N100 system** - Stability and resource constraint testing

## Troubleshooting

**If addon fails to install:**
- Check Docker logs: `docker-compose logs homeassistant`
- Verify Dockerfile syntax in `addons/aicleaner_v3/Dockerfile`

**If addon crashes on startup:**
- Check addon logs in HA UI
- Verify requirements.txt dependencies are valid
- Check for missing environment variables

**If MQTT connection fails:**
- Verify MQTT broker is running: `docker-compose ps`
- Check broker logs: `docker-compose logs mosquitto`
- Confirm container networking with: `docker network ls`