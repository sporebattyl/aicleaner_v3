# 🚀 AICleaner v3 Quick Start Guide

Get AICleaner v3 with Ollama running in 5 minutes using Docker!

## ⚡ 5-Minute Setup

### Step 1: Prerequisites (30 seconds)

Ensure you have Docker installed:
```bash
docker --version
docker-compose --version
```

**Minimum Requirements:**
- 4GB RAM
- 10GB free disk space
- Docker 20.10+
- Docker Compose 2.0+

### Step 2: Download and Setup (1 minute)

```bash
# Clone the repository
git clone https://github.com/yourusername/aicleaner-v3.git
cd aicleaner-v3

# Create data directories
mkdir -p data/{ollama_models,aicleaner,config,logs}

# Make scripts executable
chmod +x scripts/*.sh
```

### Step 3: Configure Environment (1 minute)

Create your environment file:
```bash
# Copy the template
cp .env.example .env

# Edit with your Home Assistant details
nano .env
```

**Required settings in `.env`:**
```bash
# Home Assistant Integration (REQUIRED)
HA_TOKEN=your_long_lived_access_token_here
HA_URL=http://your-home-assistant-ip:8123

# Ollama Configuration (defaults are fine)
OLLAMA_HOST=ollama:11434
OLLAMA_AUTO_DOWNLOAD=true
```

**🔑 Getting your Home Assistant Token:**
1. Go to Home Assistant → Profile → Long-Lived Access Tokens
2. Click "Create Token"
3. Copy the token and paste it in `.env`

### Step 4: Start Services (2 minutes)

```bash
# Start AICleaner with Ollama
docker-compose -f docker-compose.basic.yml up -d

# Watch the startup process
docker-compose -f docker-compose.basic.yml logs -f
```

**What happens during startup:**
1. 🐳 Docker containers start
2. 🤖 Ollama server initializes
3. 📥 Models download automatically (llava:13b, mistral:7b)
4. 🏠 AICleaner connects to Home Assistant
5. ✅ System ready!

### Step 5: Verify Installation (30 seconds)

```bash
# Check service status
docker-compose -f docker-compose.basic.yml ps

# Test Ollama
curl http://localhost:11434/api/tags

# Test AICleaner
curl http://localhost:8099
```

**Expected output:**
```
NAME                     COMMAND                  SERVICE             STATUS              PORTS
aicleaner-app-basic      "./run.sh"               aicleaner           Up 2 minutes        0.0.0.0:8099->8099/tcp
aicleaner-ollama-basic   "/scripts/start-olla…"   ollama              Up 2 minutes        0.0.0.0:11434->11434/tcp
```

## 🎯 Access Your Installation

### Web Interface
- **AICleaner Dashboard**: http://localhost:8099
- **Ollama API**: http://localhost:11434

### Home Assistant Integration
AICleaner will automatically:
- 📷 Connect to your camera entities
- 📝 Create todo lists for cleaning tasks
- 🔔 Send notifications
- 📊 Update sensors with cleaning status

## 🔧 Basic Configuration

### Add Your First Zone

Edit `config.yaml`:
```yaml
zones:
  - name: "Living Room"
    camera_entity: "camera.living_room"
    todo_list_entity: "todo.living_room_cleaning"
    purpose: "Living room for relaxation and entertainment"
    interval_minutes: 60
    ignore_rules:
      - "Ignore items on the coffee table"
      - "Don't worry about books on the bookshelf"
```

### Restart to Apply Changes
```bash
docker-compose -f docker-compose.basic.yml restart aicleaner
```

## 📱 Using AICleaner

### Manual Analysis
```bash
# Trigger analysis for a specific zone
curl -X POST http://localhost:8099/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"zone": "living_room"}'
```

### Check Status
```bash
# Get system status
curl http://localhost:8099/api/status

# Get available models
curl http://localhost:11434/api/tags

# Check logs
docker-compose -f docker-compose.basic.yml logs aicleaner
```

## 🔍 Verification Checklist

- [ ] ✅ Docker containers are running
- [ ] ✅ Ollama API responds at http://localhost:11434
- [ ] ✅ AICleaner web interface loads at http://localhost:8099
- [ ] ✅ Models are downloaded (check with `curl http://localhost:11434/api/tags`)
- [ ] ✅ Home Assistant connection is working
- [ ] ✅ Camera entities are accessible
- [ ] ✅ Todo lists are created

## 🚨 Common Quick Fixes

### Container Won't Start
```bash
# Check logs for errors
docker-compose -f docker-compose.basic.yml logs

# Restart services
docker-compose -f docker-compose.basic.yml restart
```

### Ollama Models Not Downloading
```bash
# Manual model download
docker exec aicleaner-ollama-basic ollama pull llava:13b
docker exec aicleaner-ollama-basic ollama pull mistral:7b
```

### Home Assistant Connection Issues
```bash
# Test HA connection
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-ha-ip:8123/api/states

# Check AICleaner logs
docker-compose -f docker-compose.basic.yml logs aicleaner | grep -i "home assistant"
```

### Permission Issues
```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/
chmod -R 755 data/
```

## 🎉 Success! What's Next?

### Explore Features
1. **🎮 Gamification**: Earn points for cleaning tasks
2. **📊 Analytics**: View cleaning patterns and insights
3. **🔒 Privacy**: All processing happens locally
4. **🤖 AI Models**: Vision analysis with LLaVA, text with Mistral

### Advanced Setup
- **Production Deployment**: Use `docker-compose.production.yml`
- **Development**: Use `docker-compose.development.yml`
- **Home Assistant OS**: Use `docker-compose.ha-addon.yml`

### Customization
- **Add More Zones**: Configure multiple rooms
- **Adjust Models**: Try different Ollama models
- **Tune Performance**: Optimize for your hardware
- **Cloud Fallback**: Add Gemini/Claude API keys

## 📚 Learn More

- 📖 **[Complete Setup Guide](DOCKER_SETUP.md)** - Detailed configuration options
- 🔧 **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
- ⚙️ **[Configuration Reference](CONFIGURATION.md)** - All settings explained
- 🏠 **[Home Assistant Integration](HA_INTEGRATION.md)** - Advanced HA features

## 💬 Need Help?

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Community support and tips
- **Documentation**: Comprehensive guides and references

---

**🎊 Congratulations!** You now have AICleaner v3 running with local AI models. Your cleaning tasks will never be the same! 

**⏱️ Total Setup Time**: ~5 minutes
**🔋 Status**: Ready to clean smarter, not harder!
