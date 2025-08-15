# AICleaner V3 Architecture Documentation

This document provides a comprehensive overview of the AICleaner V3 add-on architecture, design patterns, and implementation details.

## 🏗️ System Overview

AICleaner V3 is a sophisticated Home Assistant add-on that provides AI-powered cleaning task management with intelligent zone monitoring. The system follows modern architectural patterns with emphasis on reliability, scalability, and maintainability.

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant Core                      │
├─────────────────────────────────────────────────────────────┤
│  MQTT Discovery  │    HTTP API    │    Entity Registry      │
└─────────┬───────────────┬─────────────────┬─────────────────┘
          │               │                 │
┌─────────▼───────────────▼─────────────────▼─────────────────┐
│                  AICleaner V3 Add-on                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ Web UI      │ │ MQTT Client │ │    Configuration        ││
│  │ (Enhanced)  │ │ Discovery   │ │    Management           ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ AI Provider │ │ Zone Monitor│ │    Resource             ││
│  │ Factory     │ │ System      │ │    Management           ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
          │               │                 │
┌─────────▼─────┐ ┌───────▼──────┐ ┌───────▼──────────────────┐
│   AI APIs     │ │ HA Entities  │ │     Local Storage        │
│ (Cloud/Local) │ │ (Camera/Todo)│ │   (Config/Logs/Cache)    │
└───────────────┘ └──────────────┘ └──────────────────────────┘
```

## 🧩 Core Components

### 1. Configuration Management System

**Location**: `src/config_loader.py`, `src/config_mapper.py`

**Responsibilities**:
- Parse Home Assistant addon options
- Map addon configuration to internal application config
- Provide resilient configuration loading with fallbacks
- Handle configuration validation and sanitization

**Key Features**:
- Dual-mode configuration: bashio + jq fallback
- Configuration schema validation
- Environment variable export
- Live configuration reloading

```python
class ConfigurationLoader:
    def __init__(self):
        self.config_cache = {}
        self.last_reload = None
    
    def load_configuration(self) -> Dict[str, Any]:
        """Load and validate configuration from multiple sources"""
        
    def get_ai_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get AI provider specific configuration"""
        
    async def reload_config(self, new_config: Dict):
        """Reload configuration with validation"""
```

### 2. AI Provider Factory

**Location**: `src/ai_provider.py`

**Responsibilities**:
- Manage multiple AI providers (OpenAI, Anthropic, Gemini, Ollama)
- Implement intelligent failover and load balancing
- Track provider performance and health
- Handle circuit breaker patterns for resilience

**Architecture**:

```python
# Provider Registry with Circuit Breaker
class ProviderRegistry:
    def __init__(self):
        self._health_status: Dict[str, CircuitBreakerState] = {}
        self._performance_scores: Dict[str, ProviderPerformanceScore] = {}
        self._disabled_providers: Set[str] = set()

# Failover Engine
class FailoverEngine:
    def get_failover_sequence(self, original_provider, original_model):
        """Generate intelligent failover sequence"""
        # 1. Same provider, different models
        # 2. Compatible models on other providers
        # 3. Best available providers with default models

# Provider Implementations
class OpenAIProvider(AIProvider): ...
class AnthropicProvider(AIProvider): ...  
class GeminiProvider(AIProvider): ...
class OllamaProvider(AIProvider): ...
```

**Key Features**:
- Circuit breaker pattern for provider health
- Performance-based provider selection
- Automatic failover sequences
- Cost and latency optimization

### 3. Enhanced Web UI

**Location**: `src/web_ui_enhanced.py`

**Responsibilities**:
- Provide web-based configuration interface
- Handle entity discovery and selection
- Offer real-time status monitoring
- Enable AI generation testing

**Architecture**:

```python
class EnhancedWebUI:
    def __init__(self, app_instance):
        self.web_app = web.Application(middlewares=[self.json_error_middleware])
        self.setup_routes()
    
    @web.middleware
    async def json_error_middleware(self, request, handler):
        """Prevent stdout contamination of JSON responses"""
    
    async def api_entities(self, request):
        """Discover and return available HA entities"""
    
    async def api_test_generation(self, request):
        """Test AI generation with current configuration"""
```

**Key Features**:
- JSON response contamination prevention
- Home Assistant entity discovery
- Real-time configuration testing
- Professional web interface

### 4. MQTT Integration System

**Location**: `main.py` (MQTT handling), integrated throughout

**Responsibilities**:
- Auto-discovery of entities in Home Assistant
- Real-time status publishing
- Command processing from HA
- Entity lifecycle management

**Entity Schema**:

```yaml
# Status Sensor
sensor.aicleaner_status:
  name: "AICleaner Status"
  state_topic: "aicleaner/{device_id}/state"
  value_template: "{{ value_json.status }}"

# Control Switch  
switch.aicleaner_enabled:
  name: "AICleaner Enabled" 
  command_topic: "aicleaner/{device_id}/set"
  state_topic: "aicleaner/{device_id}/state"

# Configuration Status
sensor.aicleaner_config_status:
  name: "AICleaner Configuration Status"
  state_topic: "aicleaner/{device_id}/config"
```

## 🔄 Data Flow Architecture

### 1. Configuration Flow

```
Addon Options (HA UI) 
    ↓ 
run.sh (Environment Variables) 
    ↓ 
config_mapper.py (Internal Config) 
    ↓ 
config_loader.py (Application Config)
    ↓
Service Initialization
```

### 2. AI Processing Flow

```
Image Capture (Camera Entity)
    ↓
AI Provider Selection (Performance-based)
    ↓
AI Generation Request
    ↓
Failover Logic (If needed)
    ↓
Task Creation (Todo Entity)
    ↓
Status Update (MQTT)
```

### 3. Monitoring Flow

```
Zone Monitor
    ↓
Entity State Changes
    ↓
AI Analysis Trigger
    ↓
Task Generation
    ↓
MQTT Status Publishing
    ↓
Home Assistant Integration
```

## 🔒 Security Architecture

### 1. Container Security

```dockerfile
# Non-root execution
RUN adduser -D -s /bin/bash -h /app appuser
USER appuser

# Minimal privileges
RUN mkdir -p /app/data /app/logs /app/temp
WORKDIR /app

# Read-only root filesystem (where possible)
```

### 2. API Security

```python
@web.middleware  
async def json_error_middleware(self, request, handler):
    """Security middleware for API endpoints"""
    # Input validation
    # Rate limiting (future enhancement)
    # Authentication (if needed)
    # CORS handling
```

### 3. Configuration Security

```bash
# Environment variable isolation
export GEMINI_API_KEY="$PRIMARY_API_KEY"
export OPENAI_API_KEY=""
export ANTHROPIC_API_KEY=""

# Secure defaults
export DEBUG_MODE="${DEBUG_MODE:-false}"
export LOG_LEVEL="${LOG_LEVEL:-info}"
```

## 🚀 Performance Architecture

### 1. Caching Strategy

```python
class ConfigurationLoader:
    def __init__(self):
        self.config_cache = {}  # Configuration caching
        
class AIProviderFactory:
    _providers_cache: Dict[str, AIProvider] = {}  # Provider instance caching
```

### 2. Resource Management

```python
class ResourceMonitor:
    """Monitor system resources and adjust behavior"""
    def monitor_memory_usage(self): ...
    def monitor_cpu_usage(self): ...
    def adjust_processing_load(self): ...
```

### 3. Asynchronous Processing

```python
class EnhancedAICleaner:
    async def run(self):
        """Main async event loop"""
        # Web UI server
        web_task = asyncio.create_task(self.start_web_ui())
        
        # Main processing loop
        while self.running:
            await asyncio.sleep(30)  # Non-blocking processing
```

## 📊 Monitoring and Observability

### 1. Logging Architecture

```python
# Centralized logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,  # Prevent stdout contamination
    force=True
)
```

### 2. Performance Metrics

```python
@dataclass
class ProviderPerformanceScore:
    latency_ms: float = 0.0
    error_rate: float = 0.0  
    cost_efficiency: float = 0.0
    success_rate: float = 100.0
    weighted_score: float = 0.0
```

### 3. Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

## 🔄 Scalability Considerations

### 1. Horizontal Scaling

The addon is designed as a single-instance service but includes patterns that support future scaling:

- **Stateless Design**: Configuration and state managed externally
- **Event-Driven Architecture**: MQTT-based communication
- **Provider Abstraction**: Easy to add new AI providers

### 2. Performance Scaling

```python
# Circuit breaker for provider scaling
class CircuitBreakerState:
    def should_attempt_request(self) -> bool:
        """Intelligent request throttling"""
        
# Performance-based provider selection
def select_best_available_provider(self, exclude_providers: Set[str]):
    """Dynamic provider selection for optimal performance"""
```

## 🧪 Testing Architecture

### 1. Configuration Testing

```bash
# Configuration validation
python3 src/config_mapper.py --test
python3 src/config_loader.py --validate
```

### 2. Provider Testing

```python
# AI provider testing
async def test_provider_availability():
    for provider_name in AIProviderFactory.get_available_providers():
        provider = factory.create_provider(provider_name, config)
        assert await provider.is_available()
```

### 3. Integration Testing

```bash
# End-to-end testing
./run.sh --test-mode
curl http://localhost:8080/api/status
```

## 🔮 Future Architecture Enhancements

### 1. Microservices Evolution

```
Current: Monolithic Add-on
    ↓
Future: Distributed Services
├── AI Processing Service
├── Configuration Service  
├── Monitoring Service
└── Web UI Service
```

### 2. Advanced AI Pipeline

```python
class AIProcessingPipeline:
    """Future: Advanced AI processing pipeline"""
    def __init__(self):
        self.preprocessors = []
        self.ai_providers = []
        self.postprocessors = []
        
    async def process(self, image_data):
        # Image preprocessing
        # Multi-provider consensus  
        # Result post-processing
        # Confidence scoring
```

### 3. Machine Learning Integration

```python
class LearningSystem:
    """Future: Learning and adaptation"""
    def learn_from_feedback(self, task, user_feedback):
        """Improve AI prompts based on user feedback"""
        
    def optimize_provider_selection(self, historical_data):
        """ML-based provider selection optimization"""
```

This architecture provides a solid foundation for current functionality while maintaining extensibility for future enhancements. The design emphasizes reliability, security, and maintainability while providing excellent user experience through the Home Assistant ecosystem.