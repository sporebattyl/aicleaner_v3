# Contributing to AICleaner v3

Thank you for your interest in contributing to AICleaner v3! This document provides guidelines and information for contributors.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- A clear and descriptive title
- Steps to reproduce the behavior
- Expected behavior vs actual behavior
- Screenshots or logs (if applicable)
- System information (Home Assistant version, architecture, etc.)
- AICleaner v3 version and configuration

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- A clear and descriptive title
- Detailed description of the proposed feature
- Use case and benefits
- Possible implementation approach (if you have ideas)

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Update documentation as needed
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.11 or later
- Docker (for containerized development)
- Home Assistant development environment (optional)

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/drewcifer/aicleaner_v3.git
   cd aicleaner_v3
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. Copy and edit configuration:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your settings
   ```

5. Run tests:
   ```bash
   pytest
   ```

### Docker Development

1. Build the development image:
   ```bash
   docker build -t aicleaner_v3:dev .
   ```

2. Run with development settings:
   ```bash
   docker run -it --rm \
     -v $(pwd):/app \
     -v $(pwd)/config.yaml:/app/config.yaml \
     -p 8000:8000 \
     aicleaner_v3:dev
   ```

## Coding Standards

### Python Style

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Code Quality

- Write docstrings for all public functions and classes
- Add comprehensive error handling
- Include logging for important operations
- Write unit tests for new functionality

### Example Code Style

```python
async def process_ai_request(
    request: AIRequest,
    provider: AIProvider,
    timeout: float = 30.0
) -> AIResponse:
    """
    Process an AI request through the specified provider.
    
    Args:
        request: The AI request to process
        provider: The AI provider to use
        timeout: Request timeout in seconds
        
    Returns:
        The AI response
        
    Raises:
        AIProviderError: If the provider request fails
        TimeoutError: If the request times out
    """
    logger.info(f"Processing request with {provider.name}")
    
    try:
        response = await provider.process(request, timeout=timeout)
        logger.debug(f"Request completed successfully")
        return response
    except Exception as e:
        logger.error(f"Request failed: {e}")
        raise AIProviderError(f"Provider {provider.name} failed: {e}")
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ai_providers.py

# Run with coverage
pytest --cov=aicleaner_v3

# Run integration tests
pytest tests/integration/
```

### Writing Tests

- Write unit tests for all new functions
- Include integration tests for complex features
- Mock external dependencies (API calls, file I/O)
- Test both success and error cases

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from aicleaner_v3.ai.providers.openai_provider import OpenAIProvider

class TestOpenAIProvider:
    @pytest.fixture
    def provider(self):
        config = Mock()
        config.api_key = "test-key"
        return OpenAIProvider(config)
    
    @patch('aicleaner_v3.ai.providers.openai_provider.openai.ChatCompletion.create')
    async def test_process_request_success(self, mock_create, provider):
        # Arrange
        mock_create.return_value = {"choices": [{"message": {"content": "test"}}]}
        request = Mock()
        
        # Act
        response = await provider.process_request(request)
        
        # Assert
        assert response.text == "test"
        mock_create.assert_called_once()
```

## Documentation

### Code Documentation

- Use Google-style docstrings
- Document all public APIs
- Include usage examples for complex functions
- Keep documentation up to date with code changes

### User Documentation

- Update README.md for user-facing changes
- Update INSTALL.md for installation/configuration changes
- Add changelog entries for all changes
- Include screenshots for UI changes

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. Update version in relevant files
2. Update CHANGELOG.md
3. Run full test suite
4. Update documentation
5. Create release PR
6. Tag release after merge
7. Build and publish Docker images

## Architecture Guidelines

### Module Organization

```
aicleaner_v3/
├── ai/                 # AI provider implementations
├── core/              # Core functionality
├── ha_integration/    # Home Assistant integration
├── performance/       # Performance and resource management
├── security/          # Security features
├── ui/               # Web interface
└── tests/            # Test suite
```

### Design Principles

- **Modularity**: Keep components loosely coupled
- **Async/Await**: Use async patterns throughout
- **Error Handling**: Comprehensive error handling and recovery
- **Security**: Security-first design
- **Performance**: Optimize for Home Assistant environments
- **Testability**: Design for easy testing

### Dependencies

- Minimize external dependencies
- Pin dependency versions
- Regularly update dependencies for security
- Document dependency choices

## Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Pull Request Reviews**: Code review and feedback

### Resources

- [Home Assistant Developer Documentation](https://developers.home-assistant.io/)
- [Python Async/Await Guide](https://docs.python.org/3/library/asyncio.html)
- [Docker Best Practices](https://docs.docker.com/develop/best-practices/)

## Recognition

Contributors will be recognized in:

- CHANGELOG.md for significant contributions
- README.md contributors section
- GitHub contributors list

Thank you for contributing to AICleaner v3! 🎉