# AICleaner V3 Installation Guide

## Quick Start

### 1. Prerequisites

- Python 3.10+ (recommended: 3.11 or 3.12)
- pip (Python package manager)
- At least 2GB RAM available
- Network access for AI provider APIs

### 2. Installation

#### Option A: Using pip (Recommended)
```bash
pip install -e .
```

#### Option B: Development Installation
```bash
# Clone and install in development mode
pip install -e ".[dev]"
```

#### Option C: Manual Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run directly
python -m src.main
```

### 3. Configuration

#### Create Configuration File
```bash
# Copy example configuration
cp config.example.yaml config.yaml

# Edit with your API keys
nano config.yaml
```

#### Minimum Required Configuration
```yaml
# config.yaml
gemini:
  api_key: "your-gemini-api-key-here"
```

#### Environment Variables (Optional)
```bash
# Copy environment example
cp .env.example .env

# Set your API key
export AICLEANER_GEMINI_API_KEY="your-api-key"
```

### 4. Verification

#### Test Installation
```bash
# Check help
aicleaner --help

# Test configuration
aicleaner --check-config

# Run health check
aicleaner-health
```

#### Verify Web API
```bash
# Start the service
aicleaner --daemon

# Check health endpoint (in another terminal)
curl http://localhost:8080/health
```

### 5. Usage Examples

#### Basic Image Processing
```bash
# Process a directory
aicleaner process /path/to/photos

# Process with specific config
aicleaner process /path/to/photos --config config.yaml

# Process with preview (no deletion)
aicleaner process /path/to/photos --preview
```

#### Daemon Mode (Production)
```bash
# Start as background service
aicleaner daemon --config config.production.yaml

# Start with specific directories to watch
aicleaner daemon --watch-dir /data/photos --watch-dir /backup/images

# Start with web API on custom port
aicleaner daemon --web-port 9090
```

#### Home Assistant Integration
```bash
# Start with MQTT enabled
aicleaner daemon --mqtt-host homeassistant.local

# Start with specific MQTT credentials
aicleaner daemon --mqtt-user homeassistant --mqtt-pass secret
```

## Advanced Configuration

### Production Deployment
```bash
# Use production configuration template
cp config.production.yaml config.yaml

# Set environment variables
export AICLEANER_GEMINI_API_KEY="your-production-key"
export AICLEANER_MQTT_HOST="your-mqtt-broker"
export AICLEANER_LOG_LEVEL="INFO"

# Start with production settings
aicleaner daemon --config config.yaml
```

### Docker Deployment
```bash
# Build container
docker build -t aicleaner:3.0.0 .

# Run with mounted configuration
docker run -d \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v /data/photos:/data/photos \
  -p 8080:8080 \
  aicleaner:3.0.0
```

### Home Assistant Addon
1. Add repository to Home Assistant
2. Install AICleaner addon
3. Configure via addon UI
4. Start addon service

## Troubleshooting

### Common Issues

#### ImportError: No module named 'pydantic'
```bash
# Install missing dependencies
pip install -r requirements.txt
```

#### API Key Issues
```bash
# Verify API key is set
aicleaner --check-config

# Test API connectivity
curl -H "Authorization: Bearer $AICLEANER_GEMINI_API_KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models"
```

#### Permission Errors
```bash
# Ensure proper permissions on photo directories
chmod -R 755 /path/to/photos

# Run with appropriate user permissions
sudo -u photouser aicleaner process /path/to/photos
```

#### MQTT Connection Issues
```bash
# Test MQTT connectivity
mosquitto_pub -h your-mqtt-host -t "test/topic" -m "test"

# Check MQTT credentials
aicleaner --check-mqtt
```

### Performance Optimization

#### Memory Usage
```yaml
# Reduce batch size for lower memory usage
processing:
  batch_size: 5
  max_image_size_mb: 5.0
```

#### API Rate Limiting
```yaml
# Configure rate limits
performance:
  max_requests_per_minute: 30
  enable_rate_limiting: true
```

### Logging and Debugging

#### Enable Debug Logging
```bash
# Set debug level
export AICLEANER_LOG_LEVEL="DEBUG"
aicleaner process /path/to/photos

# Or in config
logging:
  level: "DEBUG"
  file_path: "/var/log/aicleaner.log"
```

#### Health Monitoring
```bash
# Get system status
curl http://localhost:8080/status

# Get detailed metrics
curl http://localhost:8080/metrics

# Force health check
curl -X POST http://localhost:8080/health/check
```

## Support

- Documentation: [docs.aicleaner.dev](https://docs.aicleaner.dev)
- Issues: [GitHub Issues](https://github.com/aicleaner/aicleaner/issues)
- Community: [Discord Server](https://discord.gg/aicleaner)
- Email: support@aicleaner.dev

## Security Notes

- Store API keys securely (environment variables recommended)
- Use HTTPS for web API in production
- Enable MQTT TLS encryption for sensitive data
- Regularly update dependencies: `pip install --upgrade -r requirements.txt`
- Review logs for security events: `grep -i error /var/log/aicleaner.log`