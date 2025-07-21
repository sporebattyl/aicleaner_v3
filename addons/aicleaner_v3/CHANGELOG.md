# Changelog

All notable changes to the AICleaner V3 Add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-21

### Added
- Initial release of AICleaner V3 as Home Assistant Add-on
- Native Home Assistant integration via MQTT discovery
- Multi-provider AI support (OpenAI, Anthropic, Google)
- API key failover and rotation support
- Real-time status monitoring and control
- Secure, non-privileged container execution
- Multi-architecture support (amd64, aarch64, armhf, armv7, i386)
- Comprehensive logging and error handling
- Web-based configuration through Home Assistant UI

### Security
- Non-root container execution
- Encrypted API key storage
- Secure MQTT communication
- Input validation and sanitization

### Documentation
- Complete installation and configuration guide
- Entity reference documentation
- Troubleshooting guide
- API reference for developers