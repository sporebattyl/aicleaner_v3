# Contributing to AICleaner V3

Thank you for your interest in contributing to AICleaner V3! This guide will help you get started.

## 🚀 Quick Start

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create** a feature branch
4. **Make** your changes
5. **Test** thoroughly
6. **Submit** a pull request

## 🛠️ Development Setup

### Prerequisites
- Docker installed
- Home Assistant test instance (recommended)
- Python 3.11+ for local development

### Local Development
```bash
# Clone your fork
git clone https://github.com/your-username/aicleaner_v3.git
cd aicleaner_v3

# Build development image
docker build -t aicleaner_v3:dev .

# Run tests
python -m pytest src/test_simple.py -v
```

## 📋 Guidelines

### Code Standards
- **Python**: Follow PEP 8 style guidelines
- **Security**: Never commit API keys or sensitive data
- **Testing**: Add tests for new features
- **Documentation**: Update README.md for user-facing changes

### Commit Messages
Use conventional commit format:
```
feat: add new AI model support
fix: resolve camera connection timeout
docs: update installation instructions
test: add validation tests for zones
```

### Pull Request Process
1. **Update** documentation if needed
2. **Add** tests for new functionality
3. **Ensure** all tests pass
4. **Validate** addon builds correctly
5. **Describe** changes in PR description

## 🧪 Testing

### Manual Testing
- Test addon installation in Home Assistant
- Verify configuration UI works correctly
- Test AI integration with sample data
- Validate MQTT discovery functionality

### Automated Testing
```bash
# Run unit tests
python -m pytest src/ -v

# Test configuration validation
python src/config_validator.py

# Test web UI
python src/test_simple.py
```

## 🔒 Security

### Security Guidelines
- Never log sensitive information (API keys, tokens)
- Validate all user inputs
- Use secure communication (HTTPS, WSS)
- Follow principle of least privilege

### Reporting Security Issues
Please report security vulnerabilities privately to:
- Email: [Create issue with "Security" label]
- Include detailed reproduction steps
- Allow time for fix before public disclosure

## 📚 Documentation

### User Documentation
- Update README.md for user-facing changes
- Add configuration examples
- Include troubleshooting steps
- Update API documentation

### Developer Documentation
- Comment complex code sections
- Update inline documentation
- Add architectural decisions to docs/

## 🐛 Bug Reports

### Before Reporting
1. Check existing issues
2. Test with minimal configuration
3. Gather relevant logs
4. Try latest version

### Include in Bug Reports
- Home Assistant version
- Addon version and architecture
- Configuration (sanitized)
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs

## 💡 Feature Requests

### Good Feature Requests
- Solve real user problems
- Are technically feasible
- Fit the addon's scope
- Include implementation details
- Consider backward compatibility

### Feature Development
1. **Discuss** in GitHub Discussions first
2. **Create** issue with detailed proposal
3. **Wait** for maintainer feedback
4. **Implement** with tests and docs
5. **Submit** pull request

## 🏗️ Architecture

### Core Components
- `main.py` - Application entry point
- `web_ui.py` - Web interface and API
- `ai_provider.py` - AI model integration
- `mqtt_service.py` - MQTT communication
- `config_loader.py` - Configuration management

### Key Principles
- **Modularity**: Separate concerns into distinct modules
- **Security**: Input validation and sanitization
- **Reliability**: Comprehensive error handling
- **Performance**: Efficient resource usage
- **Usability**: Simple configuration and setup

## 📞 Getting Help

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Home Assistant Community**: Integration discussions

### Response Times
- **Bug reports**: Within 48 hours
- **Feature requests**: Within 1 week
- **Pull requests**: Within 1 week
- **Security issues**: Within 24 hours

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be:
- Listed in CHANGELOG.md for their contributions
- Mentioned in release notes
- Added to README.md acknowledgments

Thank you for helping make AICleaner V3 better! 🤖