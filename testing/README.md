# AICleaner v3 Testing Framework

Comprehensive testing suite for production validation of AICleaner v3 Home Assistant addon.

## Quick Start

```bash
# Run all tests
python -m testing.run_tests --all

# Run specific test suites
python -m testing.run_tests --performance
python -m testing.run_tests --integration
python -m testing.run_tests --security

# Generate specific report format
python -m testing.run_tests --all --report-format json
python -m testing.run_tests --all --report-format html
```

## Test Suites

### 1. Performance Benchmarks (`--performance`)
- **Logging Performance**: Tests logging system throughput and resource usage
- **Memory Usage**: Monitors memory consumption and leak detection
- **Concurrent Operations**: Tests performance under concurrent load
- **Diagnostic Tools**: Benchmarks diagnostic system performance

### 2. Integration Tests (`--integration`)
- **Home Assistant API**: Tests connectivity to HA API
- **Supervisor API**: Tests addon integration with HA Supervisor
- **Service Registration**: Verifies addon services are properly registered
- **Entity Registration**: Checks if addon entities are available
- **Ingress Access**: Tests addon web interface accessibility
- **Performance Under Load**: API performance testing

### 3. Security Scans (`--security`)
- **Hardcoded Secrets**: Scans for API keys, passwords, tokens in source code
- **File Permissions**: Checks sensitive files have appropriate permissions
- **Input Validation**: Identifies potential injection vulnerabilities
- **Configuration Security**: Reviews addon configuration for security issues
- **Dependency Vulnerabilities**: Checks for known vulnerable packages

## Environment Setup

### For Integration Tests
```bash
# Set Home Assistant credentials
export HA_URL="http://your-ha-ip:8123"
export HA_ACCESS_TOKEN="your-long-lived-access-token"

# Or for addon development
export SUPERVISOR_TOKEN="your-supervisor-token"
```

### For Security Tests
```bash
# Optional: Install safety for dependency scanning
pip install safety
```

## Test Reports

The framework generates comprehensive reports in multiple formats:

- **Markdown** (`.md`): Human-readable report with tables and summaries
- **JSON** (`.json`): Machine-readable data for automation
- **HTML** (`.html`): Web-viewable report with styling

Reports are saved in the `test_reports/` directory by default.

## Usage Examples

### Complete Test Run
```bash
# Run all tests and generate all report formats
python -m testing.run_tests --all

# Run with custom output filename
python -m testing.run_tests --all --output-file production_validation
```

### Performance Testing Only
```bash
# Run performance benchmarks
python -m testing.run_tests --performance

# Run with verbose output
python -m testing.run_tests --performance --verbose
```

### Security Scanning
```bash
# Run security scan on current directory
python -m testing.run_tests --security

# Run with JSON report only
python -m testing.run_tests --security --report-format json
```

### Integration Testing
```bash
# Set up environment variables first
export HA_URL="http://localhost:8123"
export HA_ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Run integration tests
python -m testing.run_tests --integration
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: AICleaner v3 Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install safety
      - name: Run tests
        run: |
          python -m testing.run_tests --all --report-format json
      - name: Upload test results
        uses: actions/upload-artifact@v2
        if: always()
        with:
          name: test-results
          path: test_reports/
```

## Test Configuration

### Environment Variables
- `HA_URL`: Home Assistant instance URL (default: `http://localhost:8123`)
- `HA_ACCESS_TOKEN`: Long-lived access token for HA API
- `SUPERVISOR_TOKEN`: Supervisor API token (for addon development)
- `ENVIRONMENT`: Test environment name (for reporting)

### Performance Thresholds
The framework includes configurable performance thresholds:
- Logging performance: < 5 seconds for 1000 messages
- Memory growth: < 50MB during sustained operations
- API response time: < 2 seconds average
- Health check duration: < 5 seconds

### Security Scanning Configuration
- **File Extensions**: `.py`, `.yaml`, `.yml`, `.json`, `.txt`, `.md`, `.sh`, `.env`
- **Skip Directories**: `.git`, `.venv`, `__pycache__`, `node_modules`, `testing`
- **Sensitive Files**: `config.yaml`, `secrets.yaml`, `.env`, `*.pem`, `*.key`

## Troubleshooting

### Common Issues

1. **Integration Tests Failing**
   - Ensure Home Assistant is running and accessible
   - Check that access token is valid and has necessary permissions
   - Verify network connectivity to HA instance

2. **Performance Tests Slow**
   - Check system resource availability
   - Ensure no other resource-intensive processes are running
   - Consider adjusting performance thresholds for your environment

3. **Security Tests False Positives**
   - Review detected issues to confirm they're actual problems
   - Add exclusions for known false positives
   - Use environment variables for sensitive configuration

### Debug Mode
```bash
# Run with verbose logging
python -m testing.run_tests --all --verbose

# Run individual test modules for debugging
python -m testing.test_performance
python -m testing.test_integration_ha
python -m testing.test_security
```

## Extending the Framework

### Adding New Tests
1. Create test module in `testing/` directory
2. Implement test functions that return structured results
3. Update `run_tests.py` to include your new test suite
4. Update report generator to handle new result types

### Custom Report Formats
1. Extend `TestReportGenerator` class in `generate_report.py`
2. Add new format method (e.g., `generate_csv_report`)
3. Update CLI arguments to support new format

## Best Practices

1. **Run Tests Regularly**: Include testing in your development workflow
2. **Monitor Performance**: Track performance metrics over time
3. **Security First**: Run security scans before every release
4. **Integration Validation**: Test with real Home Assistant instances
5. **Report Review**: Always review test reports before deployment

## Support

For issues with the testing framework:
1. Check the logs in `test_reports/` for detailed error information
2. Review the generated reports for specific failure details
3. Run individual test modules to isolate issues
4. Check environment setup and dependencies