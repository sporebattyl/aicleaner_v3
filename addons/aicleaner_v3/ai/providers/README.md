# AI Provider System - Phase 2A Implementation

## Overview

The AI Provider System is a comprehensive, enterprise-grade solution for managing multiple AI providers with intelligent routing, load balancing, failover, and performance optimization. This implementation meets all Phase 2A requirements for AI Model Provider Optimization.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Provider Manager                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Routing   │  │ Load Bal.   │  │   Failover Mgmt     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Rate Limit  │  │ Health Mon. │  │   Credential Mgr    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  OpenAI     │  │ Anthropic   │  │      Google         │  │
│  │  Provider   │  │  Provider   │  │     Provider        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐                                           │
│  │   Ollama    │                                           │
│  │  Provider   │                                           │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 🚀 Multi-Provider Support
- **OpenAI GPT-4V**: Production-ready with vision capabilities
- **Anthropic Claude 3.5 Sonnet**: Advanced reasoning and safety
- **Google Gemini 1.5 Flash/Pro**: Fast inference and large context
- **Ollama**: Local model support for privacy and cost control

### 🔄 Intelligent Routing
- **Round Robin**: Even distribution across providers
- **Least Loaded**: Route to provider with lowest current load
- **Fastest Response**: Route to provider with best response times
- **Cost Optimal**: Route to most cost-effective provider
- **Priority Based**: Route based on configured provider priorities
- **Adaptive**: Smart routing based on multiple factors

### 🛡️ Reliability & Resilience
- **Automatic Failover**: Seamless switching on provider failures
- **Circuit Breakers**: Prevent cascade failures
- **Health Monitoring**: Continuous provider health checks
- **Error Recovery**: Intelligent retry and fallback mechanisms

### 💰 Cost Management
- **Budget Controls**: Daily spending limits per provider
- **Cost Tracking**: Real-time cost monitoring and reporting
- **Rate Limiting**: Configurable request and token limits
- **Quota Management**: Automatic quota enforcement

### 🔐 Security
- **Credential Management**: Encrypted API key storage
- **API Key Rotation**: Automated credential lifecycle management
- **Secure Communication**: TLS encryption for all API calls
- **Access Controls**: Role-based provider access

### 📊 Performance Optimization
- **Connection Pooling**: Efficient HTTP connection management
- **Request Batching**: Batch processing for improved throughput
- **Response Caching**: Intelligent caching with TTL
- **Performance Monitoring**: Real-time metrics and alerting

## Quick Start

### 1. Configuration

```python
config = {
    "selection_strategy": "adaptive",
    "batch_size": 5,
    "cache_ttl": 300,
    "providers": {
        "openai": {
            "enabled": True,
            "priority": 1,
            "model_name": "gpt-4-vision-preview",
            "rate_limit_rpm": 60,
            "daily_budget": 10.0
        },
        "anthropic": {
            "enabled": True,
            "priority": 2,
            "model_name": "claude-3-5-sonnet-20241022",
            "rate_limit_rpm": 50,
            "daily_budget": 10.0
        }
    }
}
```

### 2. Initialize Manager

```python
from ai.providers import AIProviderManager

manager = AIProviderManager(config, data_path="/data")
await manager.initialize()
```

### 3. Process Requests

```python
from ai.providers.base_provider import AIRequest

request = AIRequest(
    request_id="analysis_1",
    prompt="Analyze this kitchen image for cleaning tasks",
    image_path="/path/to/image.jpg"
)

response = await manager.process_request(request)
print(f"Response: {response.response_text}")
print(f"Provider: {response.provider}")
print(f"Cost: ${response.cost:.4f}")
```

## Detailed Usage

### Provider Configuration

Each provider can be configured with specific parameters:

```python
provider_config = {
    "enabled": True,                    # Enable/disable provider
    "priority": 1,                      # Provider priority (1=highest)
    "weight": 1.0,                      # Load balancing weight
    "model_name": "gpt-4-vision-preview", # Model to use
    "rate_limit_rpm": 60,               # Requests per minute
    "rate_limit_tpm": 10000,            # Tokens per minute
    "daily_budget": 10.0,               # Daily spending limit ($)
    "cost_per_request": 0.01,           # Estimated cost per request
    "timeout_seconds": 30,              # Request timeout
    "max_retries": 3,                   # Retry attempts
    "health_check_interval": 300        # Health check frequency (seconds)
}
```

### Routing Rules

Configure custom routing rules for specific request types:

```python
from ai.providers import RoutingRule

# Route image analysis to vision-capable providers
image_rule = RoutingRule(
    condition="image_analysis",
    provider="openai",
    priority=1,
    enabled=True
)

manager.add_routing_rule(image_rule)
```

### Batch Processing

Process multiple requests efficiently:

```python
requests = [
    AIRequest(request_id=f"batch_{i}", prompt=f"Task {i}")
    for i in range(10)
]

responses = await manager.batch_process_requests(requests)
```

### Health Monitoring

Check provider health status:

```python
health_report = await manager.health_check()
print(f"Overall Health: {health_report['overall_health']}")

for provider, status in health_report['providers'].items():
    print(f"{provider}: {status['status']}")
```

### Performance Metrics

Get comprehensive performance metrics:

```python
metrics = manager.get_performance_metrics()
print(f"Total Requests: {metrics['overall_stats']['total_requests']}")
print(f"Success Rate: {metrics['overall_stats']['successful_requests'] / metrics['overall_stats']['total_requests']:.2%}")
```

### Cost Tracking

Monitor costs across providers:

```python
cost_summary = manager.get_cost_summary()
print(f"Total Cost: ${cost_summary['total_cost']:.2f}")

for provider, costs in cost_summary['provider_costs'].items():
    print(f"{provider}: ${costs['total_cost']:.2f} ({costs['requests']} requests)")
```

## Advanced Features

### Custom Selection Strategies

Implement custom provider selection logic:

```python
from ai.providers import ProviderSelectionStrategy

# Use cost-optimal selection
manager.set_selection_strategy(ProviderSelectionStrategy.COST_OPTIMAL)

# Use adaptive selection (default)
manager.set_selection_strategy(ProviderSelectionStrategy.ADAPTIVE)
```

### Circuit Breaker Configuration

Circuit breakers automatically disable failing providers:

```python
# Circuit breaker opens after 5 consecutive failures
# Remains open for 60 seconds before trying again
circuit_breaker_config = {
    "failure_threshold": 5,
    "timeout_seconds": 60,
    "half_open_max_calls": 3
}
```

### Credential Management

Securely manage API keys:

```python
from ai.providers import CredentialManager

cred_manager = CredentialManager(config, "/data")

# Store encrypted credential
cred_manager.store_credential("openai", "api_key", "sk-...")

# Validate credentials
is_valid = await cred_manager.validate_credential("openai", "api_key")
```

### Rate Limiting

Configure fine-grained rate limiting:

```python
from ai.providers import RateLimitConfig

rate_config = RateLimitConfig(
    requests_per_minute=60,
    tokens_per_minute=10000,
    requests_per_hour=3600,
    daily_budget=25.0,
    burst_allowance=10,
    enable_adaptive_throttling=True
)
```

## Monitoring and Observability

### Structured Logging

All operations are logged with structured JSON format:

```json
{
    "event": "request_success",
    "request_id": "analysis_123",
    "provider": "openai",
    "model": "gpt-4-vision-preview",
    "response_time": 2.1,
    "cost": 0.03,
    "confidence": 0.95,
    "cached": false,
    "timestamp": "2024-01-15T10:30:45Z"
}
```

### Health Alerts

Health monitoring generates alerts for issues:

```json
{
    "event": "health_alert",
    "provider": "anthropic",
    "metric": "response_time",
    "status": "critical",
    "value": 12.5,
    "threshold": 10.0,
    "message": "Response time exceeded critical threshold"
}
```

### Performance Dashboards

Export metrics to monitoring systems:

```python
# Prometheus metrics
metrics = manager.get_performance_metrics()

# Custom dashboard data
dashboard_data = {
    "providers": len(manager.providers),
    "healthy_providers": sum(1 for p in manager.providers.values() if p.is_healthy()),
    "total_requests": metrics['overall_stats']['total_requests'],
    "average_response_time": metrics['overall_stats']['average_response_time'],
    "total_cost": metrics['overall_stats']['total_cost']
}
```

## Error Handling

### Progressive Error Disclosure

- **End Users**: Simple, actionable error messages
- **Operators**: Detailed error context and recovery steps
- **Developers**: Full stack traces and debugging information

### Error Categories

1. **Configuration Errors**: Invalid API keys, model names
2. **Rate Limit Errors**: Quota exceeded, budget limits
3. **Network Errors**: Timeouts, connection failures
4. **Provider Errors**: Model errors, content filtering
5. **System Errors**: Internal failures, resource exhaustion

### Recovery Mechanisms

- **Automatic Retry**: Exponential backoff for transient errors
- **Provider Fallback**: Switch to alternative providers
- **Circuit Breaking**: Isolate failing providers
- **Graceful Degradation**: Partial functionality during outages

## Testing

### Unit Tests

```bash
# Run all provider tests
pytest tests/test_ai_provider_*.py -v

# Run specific test categories
pytest tests/test_credential_manager.py -v
pytest tests/test_rate_limiter.py -v
```

### Integration Tests

```bash
# Run end-to-end integration tests
pytest tests/test_ai_provider_integration.py -v

# Run performance benchmarks
pytest tests/test_ai_provider_integration.py::TestPerformanceBenchmarks -v
```

### Mock Testing

All tests use comprehensive mocking to avoid API costs:

```python
from unittest.mock import AsyncMock, patch

@patch('ai.providers.OpenAIProvider')
async def test_openai_integration(mock_openai):
    mock_openai.return_value.process_request.return_value = mock_response
    # Test logic here
```

## Production Deployment

### Environment Configuration

```yaml
# config.yaml
ai_providers:
  selection_strategy: "adaptive"
  health_check_interval: 300
  providers:
    openai:
      enabled: true
      priority: 1
      rate_limit_rpm: 100
      daily_budget: 50.0
    anthropic:
      enabled: true
      priority: 2
      rate_limit_rpm: 80
      daily_budget: 40.0
```

### Monitoring Setup

```python
# monitoring.py
import logging
from ai.providers import AIProviderManager

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize with production config
manager = AIProviderManager(production_config)
await manager.initialize()

# Start health monitoring
await manager.health_monitor.start_monitoring()
```

### Scaling Considerations

- **Connection Pools**: Increase pool sizes for high throughput
- **Rate Limits**: Configure per environment requirements
- **Caching**: Tune cache sizes and TTL for workload
- **Monitoring**: Set up alerts for key metrics

## Security Best Practices

### API Key Management

1. **Encryption**: All API keys encrypted at rest
2. **Rotation**: Regular key rotation (recommended: 90 days)
3. **Access Control**: Principle of least privilege
4. **Monitoring**: Log all credential access

### Network Security

1. **TLS**: All API communication over HTTPS
2. **Timeouts**: Reasonable timeout values
3. **Rate Limiting**: Prevent abuse
4. **Input Validation**: Sanitize all inputs

### Data Privacy

1. **PII Protection**: Remove sensitive data from logs
2. **Retention**: Configure appropriate data retention
3. **Compliance**: Follow GDPR, CCPA requirements
4. **Audit Trails**: Comprehensive audit logging

## Performance Optimization

### Response Time Optimization

- **Connection Pooling**: Reuse HTTP connections
- **Parallel Processing**: Concurrent request handling
- **Caching**: Cache frequent responses
- **Model Selection**: Choose appropriate models for use case

### Cost Optimization

- **Model Tiers**: Use appropriate model complexity
- **Batch Processing**: Combine multiple requests
- **Caching**: Reduce API calls through caching
- **Budget Controls**: Enforce spending limits

### Throughput Optimization

- **Load Balancing**: Distribute load across providers
- **Async Processing**: Non-blocking request handling
- **Queue Management**: Efficient request queuing
- **Provider Scaling**: Scale based on demand

## Troubleshooting

### Common Issues

1. **High Response Times**
   - Check provider health status
   - Review rate limiting configuration
   - Verify network connectivity

2. **Budget Exceeded**
   - Review daily spending limits
   - Check cost per request estimates
   - Monitor usage patterns

3. **Provider Failures**
   - Check API key validity
   - Verify model availability
   - Review error logs

### Debug Mode

Enable debug logging for detailed information:

```python
import logging
logging.getLogger("ai_provider").setLevel(logging.DEBUG)
```

### Health Checks

Use built-in health checks to diagnose issues:

```python
health_report = await manager.health_check()
for provider, status in health_report['providers'].items():
    if status['status'] != 'healthy':
        print(f"Issue with {provider}: {status}")
```

## Contributing

### Development Setup

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest tests/ -v`
4. Submit pull request

### Code Standards

- **Type Hints**: All functions must have type hints
- **Documentation**: Comprehensive docstrings
- **Testing**: 90%+ test coverage required
- **Linting**: Pass flake8 and mypy checks

### Adding New Providers

1. Implement `BaseAIProvider` interface
2. Add configuration schema
3. Write comprehensive tests
4. Update documentation
5. Submit pull request

## License

This implementation is part of the AICleaner v3 project and follows the project's licensing terms.

## Support

For issues and questions:
- Check the troubleshooting guide
- Review logs for error details
- Submit issues with reproduction steps
- Include system configuration and logs