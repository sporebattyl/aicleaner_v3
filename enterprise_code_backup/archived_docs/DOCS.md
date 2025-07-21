# AICleaner v3 Documentation

## Overview
AICleaner v3 is an advanced AI-powered Home Assistant addon that provides intelligent device management, automation, and optimization capabilities.

## Features
- **Multi-AI Provider Support**: OpenAI, Gemini, Claude, and more
- **Intelligent Zone Management**: ML-optimized automation zones
- **Advanced Security**: End-to-end encryption, audit logging, compliance checking
- **Performance Optimization**: Automatic resource management and optimization
- **Comprehensive Monitoring**: Real-time analytics and reporting

## Installation
1. Add this repository to your Home Assistant addon store
2. Install the AICleaner v3 addon
3. Configure your AI providers and zones
4. Start the addon

## Configuration
### AI Providers
Configure your AI providers in the addon options:
```yaml
ai_providers:
  - provider: openai
    enabled: true
    api_key: your_api_key_here
    model: gpt-4
  - provider: gemini
    enabled: true
    api_key: your_gemini_key_here
    model: gemini-pro
```

### Zones
Define automation zones:
```yaml
zones:
  - name: "Living Room"
    enabled: true
    devices:
      - light.living_room_main
      - switch.living_room_fan
    automation_rules:
      - motion_detection
      - energy_optimization
```

### Security
Enable security features:
```yaml
security:
  enabled: true
  encryption: true
  audit_logging: true
  ssl_certificate: /ssl/cert.pem
  ssl_key: /ssl/key.pem
```

### Performance
Configure performance settings:
```yaml
performance:
  auto_optimization: true
  resource_monitoring: true
  caching: true
  max_memory_mb: 1024
  max_cpu_percent: 80
```

## API Reference
### REST API
- `GET /api/status` - Get system status
- `GET /api/zones` - List all zones
- `POST /api/zones` - Create new zone
- `PUT /api/zones/{id}` - Update zone
- `DELETE /api/zones/{id}` - Delete zone

### WebSocket API
- `status` - Real-time system status
- `metrics` - Performance metrics
- `alerts` - Security alerts

## Troubleshooting
### Common Issues
1. **AI Provider Connection Issues**
   - Check API keys
   - Verify internet connection
   - Check provider status

2. **Performance Issues**
   - Enable resource monitoring
   - Adjust memory limits
   - Check system resources

3. **Security Issues**
   - Verify SSL certificates
   - Check firewall settings
   - Review audit logs

### Logs
Check addon logs for detailed error information:
```bash
tail -f /config/addons_config/aicleaner_v3/logs/aicleaner.log
```

## Support
- GitHub Issues: https://github.com/yourusername/aicleaner_v3/issues
- Documentation: https://github.com/yourusername/aicleaner_v3/wiki
- Community Forum: https://community.home-assistant.io/

## License
MIT License - see LICENSE file for details.
