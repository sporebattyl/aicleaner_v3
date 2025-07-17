# AICleaner v3 Testing Infrastructure

Comprehensive testing infrastructure for the AICleaner v3 simplified architecture.

## Directory Structure

```
tests/
├── configs/                          # Test configuration files
│   ├── test_config_basic.yaml       # Single provider configuration
│   ├── test_config_multi_provider.yaml # Multi-provider with priorities
│   ├── test_config_legacy.yaml      # Legacy format for migration testing
│   └── test_config_edge_cases.yaml  # Edge cases and advanced configurations
├── unit/                             # Unit tests
│   ├── __init__.py
│   └── test_config_validation.py    # Configuration validation unit tests
├── integration/                      # Integration tests
│   ├── __init__.py
│   └── test_architecture.py         # Architecture integration tests
├── run_tests.py                      # Main test runner
├── validate_architecture.py         # Architecture validation script
├── pytest.ini                       # Pytest configuration
└── README.md                         # This file
```

## Test Configuration Files

### test_config_basic.yaml
Simple single provider configuration for basic testing:
- Single Ollama provider
- Minimal required fields
- Good for testing basic functionality

### test_config_multi_provider.yaml
Multi-provider configuration with failover:
- Ollama (priority 1)
- OpenAI (priority 2) 
- Gemini (priority 3)
- Tests fallback system logic

### test_config_legacy.yaml
Legacy configuration format:
- Tests migration from old format
- Validates backward compatibility
- Contains old-style provider definitions

### test_config_edge_cases.yaml
Advanced configuration scenarios:
- Provider with all optional fields
- Disabled providers
- Custom settings and rate limits
- Tests edge cases and validation

## Running Tests

### Quick Validation
```bash
# Run architecture validation
python tests/validate_architecture.py

# Run integration tests  
python tests/integration/test_architecture.py

# Run all tests
python tests/run_tests.py
```

### Using Pytest
```bash
# Run all tests with pytest
python -m pytest tests/

# Run specific test file
python -m pytest tests/unit/test_config_validation.py -v

# Run with coverage (if installed)
python -m pytest tests/ --cov=ai --cov=core
```

### Test Categories

#### Architecture Validation (`validate_architecture.py`)
- ✅ Directory structure validation
- ✅ Configuration file validation
- ✅ Provider connectivity testing
- ✅ Fallback system validation  
- ✅ Performance baseline testing
- ✅ Environment setup validation

#### Integration Tests (`integration/test_architecture.py`)
- ✅ AIProviderManager initialization
- ✅ Provider capability detection
- ✅ Fallback system logic
- ✅ Configuration migration
- ✅ Error handling and recovery
- ✅ Response generation testing

#### Unit Tests (`unit/test_config_validation.py`)
- ✅ Configuration validation logic
- ✅ Provider-specific validation
- ✅ Priority validation
- ✅ Error case handling
- ✅ Edge case validation

## Test Dependencies

Required packages (auto-installed):
```
pytest>=7.0.0
pytest-asyncio>=0.21.0
aiohttp>=3.8.0
pyyaml>=6.0
```

Optional packages:
```
psutil>=5.9.0  # For memory usage testing
coverage>=7.0.0  # For test coverage reporting
```

## Expected Test Results

### Successful Run Output
```
🚀 Starting AICleaner v3 Comprehensive Test Suite
==================================================

🌍 Validating Environment Setup...
✅ PASS Python Version: Python 3.11.x
✅ PASS Package: yaml: Available
✅ PASS Package: aiohttp: Available

🏗️  Validating Directory Structure...
✅ PASS Directory: ai: Directory exists
✅ PASS Directory: core: Directory exists
✅ PASS Directory Structure: All required directories present

📋 Validating Test Configurations...
✅ PASS Config: test_config_basic.yaml: Configuration structure valid
✅ PASS Config: test_config_multi_provider.yaml: Configuration structure valid
✅ PASS Config: test_config_legacy.yaml: Configuration structure valid

🔌 Validating Provider Connectivity...
⚠️  WARN Connectivity: Ollama: Connection timeout (expected if not running)
⚠️  WARN Connectivity: OpenAI API: Authentication required (expected with test key)

🔄 Validating Fallback System...
✅ PASS Fallback Priority Order: Providers correctly ordered by priority
✅ PASS Provider 1 Validation: All required fields present

⚡ Validating Performance Baseline...
✅ PASS Configuration Loading Performance: Loaded in 15.23ms
ℹ️  INFO Memory Usage: psutil not available for memory testing

🎉 ALL TESTS PASSED - Testing infrastructure is ready!
```

## Integration with Development Workflow

### Pre-Development Validation
```bash
# Before starting development, validate environment
python tests/validate_architecture.py
```

### During Development
```bash
# Run relevant tests for changes
python -m pytest tests/unit/ -v

# Run integration tests after major changes
python tests/integration/test_architecture.py
```

### Pre-Commit Testing
```bash
# Run full test suite before committing
python tests/run_tests.py
```

## Extending the Test Suite

### Adding New Test Configurations
1. Create new YAML file in `tests/configs/`
2. Follow naming convention: `test_config_[purpose].yaml`
3. Add validation in `validate_architecture.py`

### Adding New Unit Tests
1. Create test file in `tests/unit/`
2. Follow naming convention: `test_[module].py`
3. Use pytest conventions and async/await patterns

### Adding New Integration Tests
1. Add tests to `tests/integration/test_architecture.py`
2. Or create new integration test files
3. Mock external dependencies appropriately

## Troubleshooting

### Common Issues

**Import Errors**: Ensure project root is in Python path
```python
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
```

**Connectivity Tests Failing**: Expected for test environment
- Ollama timeout is normal if not running locally
- OpenAI auth error is expected with test keys

**Missing Dependencies**: Auto-install in test scripts
```python
try:
    import pytest
except ImportError:
    os.system("pip install pytest pytest-asyncio")
```

### Test Data

All test configurations use:
- Environment variables for API keys (`env(API_KEY_NAME)`)
- Standard timeout values (90-120 seconds)
- Priority-based ordering (1 = highest priority)
- Mock providers where external services aren't available

This testing infrastructure provides comprehensive validation of the AICleaner v3 architecture and ensures all components work correctly together.