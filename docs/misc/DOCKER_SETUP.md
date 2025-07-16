# Docker Setup Guide for AICleaner v3

Complete guide for setting up AICleaner v3 with Ollama using Docker containers.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Docker Compose Configurations](#docker-compose-configurations)
- [Environment Variables](#environment-variables)
- [Volume Management](#volume-management)
- [Networking](#networking)
- [Health Checks](#health-checks)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements

- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 2.0 or later
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Storage**: 20GB free space minimum (for models and data)
- **CPU**: x86_64 or ARM64 architecture

### Platform Support

- ✅ Linux (Ubuntu, Debian, CentOS, RHEL, Alpine)
- ✅ macOS (Intel and Apple Silicon)
- ✅ Windows (with WSL2)
- ✅ Home Assistant OS
- ✅ Raspberry Pi 4 (ARM64)

### Installation Check

```bash
# Verify Docker installation
docker --version
docker-compose --version

# Check system resources
free -h
df -h
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/aicleaner-v3.git
cd aicleaner-v3

# Create data directories
mkdir -p data/{ollama_models,aicleaner,config,logs}

# Make scripts executable
chmod +x scripts/*.sh
```

### 2. Basic Setup (Recommended for First-Time Users)

```bash
# Start with basic configuration
docker-compose -f docker-compose.basic.yml up -d

# Check status
docker-compose -f docker-compose.basic.yml ps
docker-compose -f docker-compose.basic.yml logs -f
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

Required environment variables:
```bash
HA_TOKEN=your_home_assistant_token
HA_URL=http://your-home-assistant:8123
```

## 📁 Docker Compose Configurations

### Basic Configuration (`docker-compose.basic.yml`)

**Use Case**: Testing, development, first-time setup
**Features**: 
- Minimal resource usage
- Basic networking
- Essential services only

```bash
docker-compose -f docker-compose.basic.yml up -d
```

### Production Configuration (`docker-compose.production.yml`)

**Use Case**: Production deployments
**Features**:
- Resource limits and reservations
- Security hardening
- Monitoring integration
- Logging configuration

```bash
docker-compose -f docker-compose.production.yml up -d
```

### Development Configuration (`docker-compose.development.yml`)

**Use Case**: Development and debugging
**Features**:
- Code hot-reload
- Debug ports exposed
- Development tools included
- Test runner integration

```bash
docker-compose -f docker-compose.development.yml up -d
```

### Home Assistant Addon (`docker-compose.ha-addon.yml`)

**Use Case**: Home Assistant OS integration
**Features**:
- HA Supervisor integration
- Addon-specific networking
- HA volume structure

```bash
docker-compose -f docker-compose.ha-addon.yml up -d
```

## 🌍 Environment Variables

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `localhost:11434` | Ollama server address |
| `OLLAMA_AUTO_DOWNLOAD` | `true` | Auto-download models |
| `AICLEANER_LOG_LEVEL` | `INFO` | Logging level |
| `AICLEANER_PRIVACY_LEVEL` | `standard` | Privacy mode |

### Home Assistant Integration

| Variable | Required | Description |
|----------|----------|-------------|
| `HA_TOKEN` | ✅ | Home Assistant long-lived token |
| `HA_URL` | ✅ | Home Assistant URL |
| `SUPERVISOR_TOKEN` | HA OS only | Supervisor API token |

### Performance Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_MEMORY_USAGE` | `4096` | Max memory in MB |
| `MAX_CPU_USAGE` | `80` | Max CPU percentage |
| `QUANTIZATION_LEVEL` | `4` | Model quantization (4, 8, 16) |

### Complete Environment File Example

```bash
# Ollama Configuration
OLLAMA_HOST=ollama:11434
OLLAMA_MODELS_PATH=/data/models
OLLAMA_AUTO_DOWNLOAD=true

# AICleaner Configuration
AICLEANER_DATA_PATH=/data/aicleaner
AICLEANER_LOG_LEVEL=INFO
AICLEANER_PRIVACY_LEVEL=standard

# Home Assistant Integration
HA_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
HA_URL=http://homeassistant:8123

# Performance Settings
MAX_MEMORY_USAGE=4096
MAX_CPU_USAGE=80
QUANTIZATION_LEVEL=4

# Optional: Cloud AI Fallback
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

## 💾 Volume Management

### Volume Structure

```
data/
├── ollama_models/     # Ollama model storage
├── aicleaner/         # AICleaner application data
├── config/            # Configuration files
└── logs/              # Log files
```

### Volume Configuration Options

#### Bind Mounts (Recommended for Development)

```yaml
volumes:
  - ./data/ollama_models:/data/models
  - ./data/aicleaner:/data/aicleaner
  - ./config.yaml:/app/config.yaml:ro
```

#### Named Volumes (Recommended for Production)

```yaml
volumes:
  ollama_models:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/aicleaner/data/ollama_models
```

### Backup and Restore

```bash
# Backup volumes
docker run --rm -v aicleaner_data:/data -v $(pwd):/backup alpine tar czf /backup/aicleaner-backup.tar.gz /data

# Restore volumes
docker run --rm -v aicleaner_data:/data -v $(pwd):/backup alpine tar xzf /backup/aicleaner-backup.tar.gz -C /
```

## 🌐 Networking

### Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │  AICleaner  │◄──►│   Ollama    │    │Home Assistant│    │
│  │   :8099     │    │   :11434    │    │   :8123     │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
│         │                                       │          │
│         └───────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Custom Network Configuration

```yaml
networks:
  aicleaner_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Port Mapping

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| AICleaner | 8099 | 8099 | Web interface |
| Ollama | 11434 | 11434 | API endpoint |
| Debug | 5678 | 5678 | Remote debugging |

## 🏥 Health Checks

### Container Health Monitoring

Each service includes comprehensive health checks:

#### AICleaner Health Check
```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import requests; requests.get('http://localhost:8099', timeout=5)"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

#### Ollama Health Check
```yaml
healthcheck:
  test: ["/scripts/health-check.sh", "quick"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 120s
```

### Manual Health Checks

```bash
# Check container health
docker-compose ps

# Check specific service health
docker inspect aicleaner-app-basic --format='{{.State.Health.Status}}'

# Run manual health check
docker exec aicleaner-ollama-basic /scripts/health-check.sh full
```

## 🔧 Advanced Configuration

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      memory: 4G
      cpus: '2.0'
    reservations:
      memory: 2G
      cpus: '1.0'
```

### Security Hardening

```yaml
security_opt:
  - no-new-privileges:true
read_only: false
tmpfs:
  - /tmp:noexec,nosuid,size=100m
```

### Logging Configuration

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 📊 Monitoring and Maintenance

### Log Management

```bash
# View logs
docker-compose logs -f aicleaner
docker-compose logs -f ollama

# Log rotation
docker-compose exec aicleaner logrotate /etc/logrotate.conf
```

### Performance Monitoring

```bash
# Container resource usage
docker stats

# Ollama model status
docker exec aicleaner-ollama-basic ollama list

# AICleaner metrics
curl http://localhost:8099/metrics
```

### Updates and Maintenance

```bash
# Update containers
docker-compose pull
docker-compose up -d

# Clean up unused resources
docker system prune -f
docker volume prune -f
```

## 🔗 Integration with Home Assistant

### Home Assistant Configuration

Add to your `configuration.yaml`:

```yaml
# AICleaner integration
rest:
  - resource: "http://aicleaner:8099/api/status"
    scan_interval: 30
    sensor:
      - name: "AICleaner Status"
        value_template: "{{ value_json.status }}"

# Camera entities for zone monitoring
camera:
  - platform: generic
    name: "Living Room Camera"
    still_image_url: "http://your-camera-ip/snapshot"
```

### Automation Example

```yaml
automation:
  - alias: "AICleaner Zone Analysis"
    trigger:
      - platform: time_pattern
        hours: "/1"  # Every hour
    action:
      - service: rest_command.aicleaner_analyze
        data:
          zone: "living_room"
```

## 🆘 Next Steps

1. **Quick Start**: Follow the [QUICK_START.md](QUICK_START.md) guide
2. **Troubleshooting**: Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
3. **Configuration**: Review [CONFIGURATION.md](CONFIGURATION.md) for detailed options
4. **Support**: Join our community or open an issue on GitHub

---

**Need Help?** 
- 📖 [Quick Start Guide](QUICK_START.md)
- 🔧 [Troubleshooting Guide](TROUBLESHOOTING.md)
- ⚙️ [Configuration Reference](CONFIGURATION.md)
- 💬 [Community Support](https://github.com/yourusername/aicleaner-v3/discussions)
