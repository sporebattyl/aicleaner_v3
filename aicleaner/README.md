# AI Cleaner v3

A sophisticated AI-powered photo cleaning system built on a privacy-first provider pattern architecture. Automatically analyzes and organizes your photo collection using configurable LLM providers with graceful failover and comprehensive health monitoring.

## 🚀 Quick Start

```bash
# 1. Install the package
pip install -e .

# 2. Copy example configuration
cp config.minimal.yaml config.yaml

# 3. Configure your Gemini API key
nano config.yaml  # Edit gemini.api_key

# 4. Run the cleaner
aicleaner daemon --config config.yaml

# 5. Check health status
curl http://localhost:8080/health
```

## 🏗️ Architecture Overview

AI Cleaner v3 implements a **Provider Pattern** architecture with **3 Privacy Levels** and **PDCA methodology**:

- **Provider Pattern**: Pluggable async LLM backends (Gemini, Ollama, future extensions)
- **Privacy Spectrum**: Fast (API), Hybrid (metadata→API), Private (local Ollama)
- **PDCA Integration**: Plan-Do-Check-Act cycles with subagent orchestration
- **Health Monitoring**: Circuit breaker patterns with automatic failover
- **Home Assistant**: Native MQTT integration with device discovery

### Core Components

```
src/
├── providers/           # LLM provider implementations
│   ├── base_provider.py    # Abstract provider interface
│   └── gemini_provider.py  # Google Gemini implementation
├── core/               # Core orchestration logic
│   ├── orchestrator.py     # Provider selection & coordination
│   └── health.py           # Health monitoring & circuit breakers
├── config/             # Configuration management
│   ├── schema.py           # Pydantic configuration schemas
│   └── loader.py           # Multi-source configuration loading
└── main.py             # Application entry point & API server
```

## 🔧 Configuration

### Quick Configuration

**Minimal Setup (Gemini only):**
```yaml
gemini:
  api_key: "your-gemini-api-key"
```

**Production Setup:**
```yaml
gemini:
  api_key: "your-gemini-api-key"
  model: "gemini-1.5-flash"
  
processing:
  privacy_level: "fast"
  batch_size: 10
  max_image_size_mb: 10.0
  
health:
  check_interval: 60
  max_failures: 3
  
logging:
  level: "INFO"
  file_path: "/var/log/aicleaner.log"
  
home_assistant:
  enabled: true
  mqtt_host: "localhost"
  mqtt_port: 1883
  device_name: "AI Cleaner"
```

### Privacy Levels

1. **Fast**: Raw images → API (speed priority)
2. **Hybrid**: Local metadata extraction → API (balanced privacy/speed) 
3. **Private**: Everything via external Ollama (maximum privacy)

### Environment Variables

```bash
# Provider Configuration
AICLEANER_GEMINI_API_KEY="your-api-key"
AICLEANER_PRIVACY_LEVEL="fast"

# Home Assistant Integration
AICLEANER_MQTT_HOST="homeassistant.local" 
AICLEANER_MQTT_USERNAME="your-mqtt-user"
AICLEANER_MQTT_PASSWORD="your-mqtt-password"
```

## 🎯 Usage Examples

### Command Line Interface

```bash
# Start daemon mode with API server
aicleaner daemon --config config.yaml

# Process a directory once
aicleaner process /path/to/photos --config config.yaml

# Watch directory for new images
aicleaner watch /path/to/photos --config config.yaml

# Check system status
aicleaner status

# Force provider health check
aicleaner health-check --provider gemini
```

### API Endpoints

```bash
# Health check
GET /health

# System status
GET /status

# Start processing
POST /process
{
  "directory": "/path/to/photos",
  "privacy_level": "fast"
}

# Get processing results
GET /results/{job_id}

# Provider metrics
GET /metrics

# Home Assistant status
GET /ha-status
```

### Python API

```python
from aicleaner import AICleanerApp

# Initialize application
app = AICleanerApp()
await app.initialize("config.yaml")

# Process images
results = await app.process_directory(
    "/path/to/photos",
    privacy_level="fast",
    progress_callback=lambda p: print(f"Progress: {p}%")
)

# Check provider health
health = await app.get_provider_health("gemini")
print(f"Provider status: {health.status}")
```

## 🏥 Health Monitoring

### Circuit Breaker Protection

AI Cleaner implements sophisticated circuit breaker patterns:

- **Closed**: Normal operation
- **Open**: Provider blocked after failures
- **Half-Open**: Testing provider recovery

### Health Metrics

```bash
# Get comprehensive health status
curl http://localhost:8080/metrics

{
  "system_health": {
    "overall_status": "healthy",
    "active_providers": ["gemini"],
    "circuit_breakers": {
      "gemini": "closed"
    }
  },
  "provider_metrics": {
    "gemini": {
      "avg_response_time": 1.2,
      "success_rate": 0.98,
      "requests_processed": 1542
    }
  }
}
```

### Home Assistant Integration

Automatic device discovery creates sensors for:
- System health status
- Provider availability  
- Processing statistics
- Circuit breaker states
- Performance metrics

## 🐳 Deployment

### Home Assistant Addon

1. Copy addon files to Home Assistant
2. Configure via addon options:
   ```json
   {
     "gemini_api_key": "your-key",
     "privacy_level": "fast",
     "batch_size": 10
   }
   ```
3. Start addon - automatic MQTT discovery

### Docker Deployment

```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -e .
CMD ["aicleaner", "daemon", "--config", "config.yaml"]
```

```bash
# Build and run
docker build -t aicleaner .
docker run -v /photos:/photos -p 8080:8080 aicleaner
```

### Systemd Service

```ini
[Unit]
Description=AI Cleaner Service
After=network.target

[Service]
Type=simple
User=aicleaner
ExecStart=/usr/local/bin/aicleaner daemon --config /etc/aicleaner/config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 🔒 Security & Privacy

### Privacy Levels Explained

**Fast Mode (Gemini API):**
- Raw images sent to Google's Gemini API
- Fastest processing speed
- Minimal privacy protection
- Best for non-sensitive images

**Hybrid Mode (Coming Soon):**
- Local metadata extraction (faces, objects, EXIF)
- Only metadata sent to API
- Balanced speed/privacy
- Good for personal photos

**Private Mode (Ollama Required):**
- Everything processed locally
- Requires external Ollama instance
- Maximum privacy protection
- Slower processing speed

### Security Best Practices

- Store API keys in environment variables
- Use HTTPS for API endpoints
- Enable MQTT authentication
- Monitor provider health logs
- Regular dependency updates

## 🔧 Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/your-repo/aicleaner.git
cd aicleaner

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Code formatting
black src/
ruff check src/

# Type checking
mypy src/
```

### Adding New Providers

1. **Implement Provider Interface:**
```python
from aicleaner.providers import LLMProvider, AnalysisResult

class CustomProvider(LLMProvider):
    async def analyze(self, image_data, prompt, privacy_level):
        # Your implementation
        return AnalysisResult(...)
    
    async def health_check(self):
        # Health check implementation
        pass
```

2. **Register in Configuration:**
```python
# Add to config/schema.py
class CustomConfig(BaseModel):
    api_endpoint: str
    api_key: str
```

3. **Update Orchestrator:**
```python
# Add to core/orchestrator.py
if self.config.custom:
    custom_provider = CustomProvider(self.config.custom)
    self.provider_registry.register_provider("custom", custom_provider)
```

## 📊 Performance & Monitoring

### Key Metrics

- **Processing Speed**: Images per minute
- **Provider Health**: Response times, error rates
- **System Resources**: Memory, CPU usage
- **Circuit Breaker Status**: Open/Closed/Half-Open states

### Monitoring Integration

**Prometheus Metrics:**
```
# Processing metrics
aicleaner_images_processed_total
aicleaner_processing_duration_seconds
aicleaner_provider_health_status

# Provider metrics  
aicleaner_provider_requests_total
aicleaner_provider_errors_total
aicleaner_provider_response_time_seconds
```

**Grafana Dashboard:**
- System overview with health status
- Provider performance comparison
- Processing throughput trends
- Error rate monitoring

## 🐛 Troubleshooting

### Common Issues

**Import Error: "No module named aicleaner"**
```bash
# Install in development mode
pip install -e .
```

**Provider Health Check Failing**
```bash
# Check API key configuration
aicleaner health-check --provider gemini --verbose

# Verify network connectivity
curl https://generativelanguage.googleapis.com/v1beta/models
```

**High Memory Usage**
```bash
# Reduce batch size in config
processing:
  batch_size: 5  # Default: 10
```

**MQTT Connection Issues**
```bash
# Test MQTT connectivity
mosquitto_pub -h localhost -t test -m "hello"

# Check Home Assistant MQTT settings
homeassistant:
  mqtt_host: "homeassistant.local"
  mqtt_username: "your-user"
  mqtt_password: "your-password"
```

### Debug Mode

```bash
# Enable detailed logging
aicleaner daemon --config config.yaml --log-level DEBUG

# Export health history
aicleaner export-health --output health_report.json
```

## 📈 Roadmap

### Phase 1: "It Just Works" ✅
- [x] Gemini provider implementation
- [x] Configuration management
- [x] Health monitoring system  
- [x] Web API and Home Assistant integration
- [x] Production deployment ready

### Phase 2: "Power User" (Next)
- [ ] Ollama provider implementation
- [ ] Hybrid privacy mode with local metadata
- [ ] Performance dashboard
- [ ] Batch processing optimization
- [ ] Advanced filtering options

### Phase 3: "Resilient System" (Future)
- [ ] Multi-provider load balancing
- [ ] Advanced circuit breaker patterns
- [ ] Machine learning model optimization
- [ ] Custom analysis prompt templates
- [ ] Integration with cloud storage providers

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Development Standards

- **Code Style**: Black formatting, Ruff linting
- **Type Hints**: Full mypy compatibility
- **Testing**: Pytest with >90% coverage
- **Documentation**: Docstring for all public methods
- **Async**: All I/O operations must be async

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Gemini**: For providing the AI analysis capabilities
- **Home Assistant**: For the excellent MQTT integration patterns
- **Pydantic**: For robust configuration management
- **FastAPI**: For the async web framework foundation

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/aicleaner/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/aicleaner/discussions)
- **Home Assistant Forum**: [AI Cleaner Thread](https://community.home-assistant.io/)

---

**Made with ❤️ for the Home Assistant community**