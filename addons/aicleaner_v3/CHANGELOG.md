# Changelog

All notable changes to the AICleaner V3 Add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.4] - 2025-01-21

### Added
- Complete production-ready Home Assistant Add-on
- Enhanced AI Provider Factory with intelligent failover
- Comprehensive configuration validation and resilient parsing
- Advanced performance monitoring and circuit breaker patterns
- Multi-provider AI support with automatic fallback (Gemini, OpenAI, Anthropic, Ollama)
- Enhanced Web UI with entity discovery and configuration management
- Intelligent configuration mapping between HA addon options and internal config
- Comprehensive MQTT discovery with auto-entity registration
- Zone-based monitoring capabilities for advanced use cases
- Real-time status monitoring and control via MQTT entities
- Professional deployment documentation and setup guides

### Enhanced
- Robust error handling with comprehensive logging to stderr
- JSON API response contamination prevention
- Multi-architecture Docker builds (amd64, aarch64, armhf, armv7)
- Optimized dependency management with Alpine packages
- Professional README with comprehensive setup instructions
- Advanced troubleshooting guides and configuration examples

### Fixed
- Resolved stdout contamination preventing web UI JSON responses
- Fixed critical AsyncIO thread error in signal handler preventing startup
- Resolved configuration parsing failures with resilient jq fallback
- Fixed bashio schema validation failures with configuration sanitization
- Corrected JSON parsing errors in web API endpoints

### Security
- Non-root container execution with proper user permissions
- Secure API key handling with environment variable isolation
- Input validation and sanitization across all interfaces
- Secure MQTT communication with authentication support
- Container security hardening and minimal attack surface

### Performance
- Intelligent AI provider selection based on performance metrics
- Circuit breaker patterns for provider resilience
- Efficient caching and resource management
- Optimized Docker layers for faster builds and deployments
- Performance monitoring with detailed metrics collection

### Documentation
- Comprehensive installation and configuration guide
- Complete entity reference with examples
- Advanced usage patterns and automation examples
- Detailed troubleshooting guide with common solutions
- Professional API documentation for developers
- Multi-architecture deployment instructions

## [1.2.3] - 2025-01-20

### Fixed
- Configuration parsing improvements with jq fallback
- Enhanced error handling for addon options validation
- Improved MQTT connection stability

## [1.2.2] - 2025-01-19

### Fixed
- Resolved critical configuration parsing failures
- Added resilient bashio/jq hybrid configuration loading
- Fixed schema validation issues with backup_api_keys

## [1.2.1] - 2025-01-18

### Fixed
- AsyncIO signal handler threading issues
- Startup stability improvements
- Enhanced logging and error reporting

## [1.2.0] - 2025-01-17

### Added
- Enhanced web UI with entity selection capabilities
- Advanced configuration management system
- Improved AI provider failover mechanisms
- Zone-based monitoring support

## [1.1.0] - 2025-01-15

### Added
- Multi-provider AI support (OpenAI, Anthropic, Google Gemini)
- MQTT discovery for automatic entity creation
- Web-based configuration interface
- External MQTT broker support

## [1.0.0] - 2025-01-10

### Added
- Initial release of AICleaner V3 as Home Assistant Add-on
- Basic AI-powered image analysis
- Todo list integration
- Docker containerization
- Multi-architecture support