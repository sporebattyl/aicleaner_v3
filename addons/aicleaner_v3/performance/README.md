# Performance Regression Testing Framework

## Overview

The Performance Regression Testing Framework provides comprehensive performance regression testing capabilities for AICleaner v3. This framework is specifically designed for Home Assistant addons and focuses on single-user deployment optimization.

## Features

### Core Capabilities
- **Automated Baseline Management**: Create, store, and manage performance baselines
- **Statistical Regression Detection**: Detect performance regressions with confidence intervals
- **Comprehensive Test Types**: Latency, throughput, memory usage, CPU usage, and more
- **Trend Analysis**: Analyze performance trends over time with statistical significance
- **CI/CD Integration**: Native support for GitHub Actions, GitLab CI, Jenkins, and more

### Reporting and Visualization
- **HTML Reports**: Comprehensive HTML reports with charts and analysis
- **JSON Exports**: Machine-readable reports for automation
- **Performance Charts**: Trend charts, component comparisons, regression timelines
- **Real-time Notifications**: Slack, Discord, and Microsoft Teams integration

### Quality Gates
- **Performance Gates**: Enforce performance quality standards in CI/CD
- **Configurable Thresholds**: Define acceptable regression levels
- **Automated Alerting**: Immediate notifications for critical regressions

## Installation

### Prerequisites
```bash
# Required dependencies
pip install asyncio sqlalchemy pydantic psutil

# Optional dependencies for full functionality
pip install matplotlib scipy requests numpy
```

### Framework Setup
```python
from addons.aicleaner_v3.performance import (
    PerformanceRegressionFramework,
    RegressionTestConfig,
    RegressionTestType
)

# Initialize configuration
config = RegressionTestConfig(
    test_iterations=10,
    warm_up_iterations=3,
    enabled_components=['ai_providers', 'system_monitor', 'ha_integration']
)

# Create framework instance
framework = PerformanceRegressionFramework(config, "/data/performance")
```

## Quick Start Guide

### 1. Creating Performance Baselines

```python
import asyncio
from addons.aicleaner_v3.performance import (
    PerformanceRegressionFramework,
    RegressionTestConfig,
    RegressionTestType
)

async def main():
    # Initialize framework
    config = RegressionTestConfig()
    framework = PerformanceRegressionFramework(config, "/data/performance")
    
    # Define test function
    async def test_ai_analysis():
        # Your AI analysis code here
        await asyncio.sleep(0.1)  # Simulate processing time
        return "analysis_result"
    
    # Create baseline
    success = await framework.create_baseline(
        component='ai_providers',
        operation='analyze_image',
        test_type=RegressionTestType.LATENCY,
        test_func=test_ai_analysis,
        version='1.0.0'
    )
    
    print(f"Baseline created: {success}")

# Run the example
asyncio.run(main())
```

### 2. Running Regression Tests

```python
async def run_regression_test():
    config = RegressionTestConfig()
    framework = PerformanceRegressionFramework(config, "/data/performance")
    
    # Test function with potentially different performance
    async def test_ai_analysis():
        await asyncio.sleep(0.15)  # Slightly slower
        return "analysis_result"
    
    # Run regression test
    result = await framework.run_regression_test(
        component='ai_providers',
        operation='analyze_image',
        test_type=RegressionTestType.LATENCY,
        test_func=test_ai_analysis
    )
    
    if result.is_regression:
        print(f"Regression detected: {result.change_percentage:.1f}% degradation")
        print(f"Severity: {result.regression_severity.value}")
    else:
        print(f"No regression: {result.change_percentage:.1f}% change")

asyncio.run(run_regression_test())
```

### 3. Comprehensive Test Suite

```python
async def run_comprehensive_suite():
    config = RegressionTestConfig(
        enabled_components=['ai_providers', 'system_monitor', 'ha_integration']
    )
    framework = PerformanceRegressionFramework(config, "/data/performance")
    
    # Run comprehensive test suite
    results = await framework.run_comprehensive_regression_suite()
    
    print(f"Total tests: {results['summary']['total_tests']}")
    print(f"Regressions: {results['summary']['regressions_detected']}")
    print(f"Critical regressions: {results['summary']['critical_regressions']}")

asyncio.run(run_comprehensive_suite())
```

## Advanced Usage

### Custom Test Configuration

```python
from addons.aicleaner_v3.performance import RegressionTestConfig

config = RegressionTestConfig(
    # Test execution settings
    test_iterations=20,
    warm_up_iterations=5,
    test_timeout_seconds=300,
    cooldown_seconds=2,
    
    # Regression detection thresholds
    minor_threshold=0.05,      # 5% degradation
    moderate_threshold=0.15,   # 15% degradation
    major_threshold=0.30,      # 30% degradation
    
    # Statistical settings
    confidence_level=0.95,
    minimum_sample_size=10,
    outlier_threshold=2.0,
    
    # Components to test
    enabled_components=[
        'ai_providers',
        'system_monitor',
        'ha_integration',
        'zone_management'
    ],
    
    # Test types to run
    enabled_test_types=[
        RegressionTestType.LATENCY,
        RegressionTestType.THROUGHPUT,
        RegressionTestType.MEMORY_USAGE,
        RegressionTestType.CPU_USAGE
    ]
)
```

### Performance Reporting

```python
from addons.aicleaner_v3.performance import PerformanceReporter

async def generate_performance_report():
    framework = PerformanceRegressionFramework(config, "/data/performance")
    reporter = PerformanceReporter(framework, "/data/reports")
    
    # Generate comprehensive report
    report = await reporter.generate_comprehensive_report(time_window_days=30)
    
    print(f"Report ID: {report.report_id}")
    print(f"Total tests: {report.total_tests}")
    print(f"Regressions: {report.regressions_detected}")
    print(f"Critical alerts: {len(report.critical_alerts)}")
    
    # Generate CI/CD compatible report
    ci_report = reporter.generate_ci_cd_report(list(framework.test_results))
    print(f"CI/CD Exit code: {ci_report['exit_code']}")

asyncio.run(generate_performance_report())
```

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/performance.yml`:

```yaml
name: Performance Regression Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  performance-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run performance regression tests
      run: |
        python -m addons.aicleaner_v3.performance.ci_cd_integration
      env:
        ENABLE_PERFORMANCE_GATES: true
        FAIL_ON_CRITICAL_REGRESSION: true
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
    
    - name: Upload performance artifacts
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: performance-results
        path: |
          /tmp/performance_ci/reports/
          /tmp/performance_ci/performance_artifacts_*/
        retention-days: 30
```

### GitLab CI

Add to `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - performance

performance_regression_tests:
  stage: performance
  image: python:3.11
  timeout: 30m
  
  before_script:
    - python -m pip install --upgrade pip
    - pip install -r requirements.txt
  
  script:
    - python -m addons.aicleaner_v3.performance.ci_cd_integration
  
  variables:
    ENABLE_PERFORMANCE_GATES: "true"
    FAIL_ON_CRITICAL_REGRESSION: "true"
  
  artifacts:
    reports:
      junit: performance_artifacts/performance_results.xml
    paths:
      - performance_artifacts/
    expire_in: 30 days
    when: always
  
  only:
    - main
    - develop
    - merge_requests
```

### Programmatic CI/CD Integration

```python
from addons.aicleaner_v3.performance import CICDIntegration, CICDConfig

async def run_ci_cd_tests():
    # Configure CI/CD integration
    ci_config = CICDConfig(
        enable_performance_gates=True,
        fail_on_critical_regression=True,
        fail_on_major_regression=False,
        max_acceptable_regressions=3,
        
        # Notifications
        slack_webhook_url=os.environ.get('SLACK_WEBHOOK_URL'),
        discord_webhook_url=os.environ.get('DISCORD_WEBHOOK_URL'),
        
        # Artifacts
        upload_artifacts=True,
        artifact_retention_days=30
    )
    
    # Initialize framework
    framework_config = RegressionTestConfig()
    framework = PerformanceRegressionFramework(framework_config, "/data/performance")
    
    # Run CI/CD tests
    integration = CICDIntegration(ci_config, framework, "/tmp/performance_ci")
    result = await integration.run_ci_cd_performance_tests()
    
    print(f"CI/CD Result: {result.message}")
    print(f"Exit code: {result.exit_code}")
    
    return result.exit_code

# Use in CI/CD pipeline
exit_code = asyncio.run(run_ci_cd_tests())
sys.exit(exit_code)
```

## Configuration Reference

### RegressionTestConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `test_iterations` | int | 10 | Number of test iterations to run |
| `warm_up_iterations` | int | 3 | Number of warm-up runs before testing |
| `test_timeout_seconds` | int | 300 | Maximum time for a single test |
| `cooldown_seconds` | int | 5 | Cooldown time between iterations |
| `minor_threshold` | float | 0.10 | Threshold for minor regressions (10%) |
| `moderate_threshold` | float | 0.25 | Threshold for moderate regressions (25%) |
| `major_threshold` | float | 0.50 | Threshold for major regressions (50%) |
| `confidence_level` | float | 0.95 | Statistical confidence level |
| `minimum_sample_size` | int | 5 | Minimum samples for statistical analysis |
| `outlier_threshold` | float | 2.0 | Standard deviations for outlier detection |
| `enabled_components` | List[str] | [...] | Components to include in testing |
| `enabled_test_types` | List[RegressionTestType] | [...] | Test types to run |

### CICDConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_performance_gates` | bool | True | Enable performance quality gates |
| `fail_on_critical_regression` | bool | True | Fail CI/CD on critical regressions |
| `fail_on_major_regression` | bool | False | Fail CI/CD on major regressions |
| `max_acceptable_regressions` | int | 3 | Maximum acceptable regression count |
| `auto_update_baselines` | bool | False | Automatically update baselines |
| `baseline_update_threshold` | float | 0.05 | Minimum improvement for baseline update |
| `enable_notifications` | bool | True | Enable notifications |
| `slack_webhook_url` | str | None | Slack webhook URL for notifications |
| `discord_webhook_url` | str | None | Discord webhook URL for notifications |
| `upload_artifacts` | bool | True | Upload test artifacts |
| `artifact_retention_days` | int | 30 | Artifact retention period |

## Test Types

### RegressionTestType Options

- **LATENCY**: Measures response time in milliseconds
- **THROUGHPUT**: Measures requests per second
- **MEMORY_USAGE**: Measures memory consumption in MB
- **CPU_USAGE**: Measures CPU utilization percentage
- **ERROR_RATE**: Measures error percentage
- **RESOURCE_UTILIZATION**: Measures overall resource usage
- **AI_RESPONSE_TIME**: Measures AI-specific response times
- **HA_INTEGRATION**: Measures Home Assistant integration performance
- **SYSTEM_HEALTH**: Measures overall system health metrics

### Test Implementation Examples

```python
# Latency test
async def test_latency():
    start_time = time.perf_counter()
    await your_function()
    end_time = time.perf_counter()
    return (end_time - start_time) * 1000  # Convert to milliseconds

# Throughput test
async def test_throughput():
    start_time = time.perf_counter()
    request_count = 0
    
    while (time.perf_counter() - start_time) < 30:  # Run for 30 seconds
        await your_function()
        request_count += 1
    
    return request_count / 30  # Requests per second

# Memory usage test
async def test_memory_usage():
    import psutil
    process = psutil.Process()
    
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
    await your_function()
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    return peak_memory - baseline_memory
```

## Best Practices

### 1. Baseline Management
- Create baselines for stable, well-performing code
- Use version tags to track baseline evolution
- Regularly review and update baselines for long-term improvements
- Document baseline creation context and assumptions

### 2. Test Design
- Use realistic test scenarios that match production workloads
- Include warm-up iterations to account for JIT compilation and caching
- Set appropriate timeouts based on expected operation duration
- Use sufficient iterations for statistical significance

### 3. Regression Detection
- Set thresholds appropriate for your performance requirements
- Consider the impact of false positives vs. false negatives
- Use confidence intervals to account for measurement variability
- Review regression alerts promptly to avoid accumulation

### 4. CI/CD Integration
- Run performance tests on consistent hardware
- Use performance gates to prevent degraded code from reaching production
- Set up notifications for immediate awareness of regressions
- Archive performance artifacts for historical analysis

### 5. Monitoring and Analysis
- Regularly review performance trends
- Investigate both regressions and unexpected improvements
- Use performance data to guide optimization efforts
- Correlate performance changes with code changes

## Troubleshooting

### Common Issues

#### 1. High Test Variability
```python
# Increase iterations and warm-up
config = RegressionTestConfig(
    test_iterations=20,
    warm_up_iterations=10,
    outlier_threshold=3.0  # More permissive outlier detection
)
```

#### 2. Test Timeouts
```python
# Increase timeout and reduce iterations
config = RegressionTestConfig(
    test_timeout_seconds=600,
    test_iterations=5
)
```

#### 3. Missing Baselines
```python
# Check if baseline exists
baseline = framework.baseline_storage.get_baseline(
    component, operation, test_type
)
if baseline is None:
    print("No baseline found - create one first")
```

#### 4. CI/CD Failures
```bash
# Check exit codes
echo $?  # 0 = success, 1 = performance gate failure, 2 = error

# Check logs
cat /tmp/performance_ci/ci_cd_result.json
```

### Performance Framework Diagnostics

```python
# Validate framework installation
from addons.aicleaner_v3.performance import validate_framework_installation
validate_framework_installation()

# Run test suite
from addons.aicleaner_v3.performance.test_regression_framework import run_all_tests
run_all_tests()

# Check framework info
from addons.aicleaner_v3.performance import print_framework_info
print_framework_info()
```

## API Reference

### Core Classes

#### PerformanceRegressionFramework
Main framework class for regression testing.

**Methods:**
- `create_baseline(component, operation, test_type, test_func, version)`: Create performance baseline
- `run_regression_test(component, operation, test_type, test_func)`: Run regression test
- `run_comprehensive_regression_suite()`: Run full test suite
- `get_test_history(component, operation, days)`: Get historical test results
- `cleanup_old_data()`: Clean up old data

#### PerformanceReporter
Generates comprehensive performance reports.

**Methods:**
- `generate_comprehensive_report(time_window_days)`: Generate full report
- `generate_ci_cd_report(test_results)`: Generate CI/CD compatible report

#### CICDIntegration
Integrates with CI/CD pipelines.

**Methods:**
- `run_ci_cd_performance_tests()`: Run CI/CD test suite
- `generate_github_actions_workflow()`: Generate GitHub Actions workflow
- `generate_gitlab_ci_config()`: Generate GitLab CI configuration

## Contributing

### Development Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `python -m addons.aicleaner_v3.performance test`
4. Validate installation: `python -m addons.aicleaner_v3.performance validate`

### Running Tests

```bash
# Run all tests
python -m addons.aicleaner_v3.performance test

# Run specific test class
python -m unittest addons.aicleaner_v3.performance.test_regression_framework.TestPerformanceRegressionFramework

# Run with verbose output
python -m unittest -v addons.aicleaner_v3.performance.test_regression_framework
```

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Include comprehensive docstrings
- Add unit tests for new features
- Update documentation for API changes

## License

This framework is released under the MIT License. See LICENSE file for details.

## Support

For questions, issues, or feature requests:
- GitHub Issues: [Link to repository issues]
- Documentation: [Link to full documentation]
- Email: support@aicleaner.com

## Changelog

### Version 1.0.0
- Initial release
- Core regression testing framework
- Statistical analysis and trend detection
- CI/CD integration with major platforms
- Comprehensive reporting and visualization
- Performance gate enforcement
- Multi-platform notification support