# AI Cleaner Architecture Blueprint

## Overview
This document provides the complete architectural blueprint for the AI Cleaner Home Assistant addon. The DO agent should implement the Python logic based on this foundation.

## Core Principles

### 1. PDCA Methodology Implementation
- **Plan**: AI analyzes images and creates cleaning plans
- **Do**: Tasks are created in Home Assistant todo lists  
- **Check**: Progress monitoring through sensors
- **Act**: Adaptive improvements based on outcomes

### 2. Headless Design
- No custom web interface
- Native Home Assistant integration only
- Configuration through addon options
- Status through HA entities

### 3. Privacy-First Architecture
- Configurable privacy levels: minimal, standard, detailed
- Optional image saving with user consent
- Local processing preference (Ollama > Gemini)
- No external data transmission without explicit consent

## Module Structure

```
/home/drewcifer/aicleaner_v3/ai_cleaner/
├── config.yaml              # HA addon configuration
├── Dockerfile               # Container build definition
├── requirements.txt         # Python dependencies
├── run.sh                   # Entry point script
├── ARCHITECTURE.md          # This document
├── src/
│   ├── __init__.py
│   ├── main.py             # Application entry point
│   ├── config.py           # Configuration management
│   └── app.py              # Main application class
└── core/
    ├── __init__.py
    ├── providers/          # AI Provider implementations
    │   ├── __init__.py
    │   ├── base.py         # Abstract base provider
    │   ├── gemini.py       # Google Gemini provider
    │   └── ollama.py       # Local Ollama provider
    ├── analysis/           # Image analysis and processing
    │   ├── __init__.py
    │   ├── image_processor.py
    │   └── cleanliness_analyzer.py
    ├── ha_integration/     # Home Assistant integration
    │   ├── __init__.py
    │   ├── mqtt_client.py  # MQTT entity management
    │   ├── api_client.py   # HA REST API client
    │   └── entities.py     # Entity definitions
    ├── pdca/              # PDCA methodology
    │   ├── __init__.py
    │   ├── planner.py     # AI-driven planning
    │   ├── executor.py    # Task execution
    │   ├── checker.py     # Progress monitoring
    │   └── actor.py       # Adaptive improvements
    └── utils/             # Utility functions
        ├── __init__.py
        ├── logging.py     # Structured logging
        ├── async_helpers.py
        └── validation.py
```

## Implementation Requirements

### 1. Configuration Management (`src/config.py`)
```python
class AiCleanerConfig:
    """Configuration manager with validation and defaults"""
    
    # Required fields
    log_level: str = "info"
    ai_provider: str = "gemini"
    
    # AI Provider configuration
    gemini_api_key: Optional[str] = None
    ollama_host: str = "http://host.docker.internal:11434"
    
    # Entity configuration
    camera_entity: Optional[str] = None
    todo_entity: Optional[str] = None
    
    # Zone configuration
    enable_zones: bool = False
    zones: List[ZoneConfig] = []
    
    # Privacy settings
    privacy_level: str = "standard"  # minimal, standard, detailed
    save_images: bool = False
    
    # PDCA settings
    analysis_interval: int = 300  # 5 minutes
    auto_create_tasks: bool = True
```

### 2. Main Application (`src/main.py` & `src/app.py`)
```python
class AiCleanerApp:
    """Main application orchestrator"""
    
    async def start(self):
        """Initialize and start the application"""
        # 1. Load configuration
        # 2. Initialize AI provider
        # 3. Setup HA integration
        # 4. Start PDCA cycle
        # 5. Setup health monitoring
    
    async def pdca_cycle(self):
        """Main PDCA execution loop"""
        while True:
            try:
                # Plan: Analyze current state
                plan = await self.planner.create_plan()
                
                # Do: Execute plan
                await self.executor.execute_plan(plan)
                
                # Check: Monitor progress
                progress = await self.checker.check_progress()
                
                # Act: Make improvements
                await self.actor.adapt_based_on_progress(progress)
                
                # Wait for next cycle
                await asyncio.sleep(self.config.analysis_interval)
            except Exception as e:
                logger.error(f"PDCA cycle error: {e}")
                await asyncio.sleep(60)  # Error backoff
```

### 3. AI Provider Architecture (`core/providers/`)

#### Base Provider Interface
```python
from abc import ABC, abstractmethod

class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    async def analyze_image(self, image_data: bytes, prompt: str) -> str:
        """Analyze image and return description"""
        pass
    
    @abstractmethod
    async def create_cleaning_plan(self, analysis: str, context: dict) -> dict:
        """Create structured cleaning plan"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
```

#### Gemini Provider Implementation
```python
class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider"""
    
    def __init__(self, api_key: str):
        self.client = genai.GenerativeModel('gemini-1.5-pro')
        # Configure with safety settings and generation config
    
    async def analyze_image(self, image_data: bytes, prompt: str) -> str:
        # Implement Gemini vision analysis
        pass
    
    async def create_cleaning_plan(self, analysis: str, context: dict) -> dict:
        # Generate structured cleaning plan
        pass
```

#### Ollama Provider Implementation  
```python
class OllamaProvider(BaseAIProvider):
    """Local Ollama AI provider"""
    
    def __init__(self, host: str):
        self.client = ollama.AsyncClient(host=host)
    
    async def analyze_image(self, image_data: bytes, prompt: str) -> str:
        # Implement Ollama vision analysis
        # Use llava or similar vision model
        pass
```

### 4. Home Assistant Integration (`core/ha_integration/`)

#### MQTT Client
```python
class MQTTClient:
    """MQTT client for HA entity management"""
    
    async def create_sensor(self, sensor_id: str, config: dict):
        """Create HA sensor via MQTT discovery"""
        # Publish discovery config
        # Handle sensor state updates
        pass
    
    async def create_todo_list(self, list_id: str, name: str):
        """Create HA todo list entity"""
        pass
    
    async def add_todo_item(self, list_id: str, item: dict):
        """Add item to todo list"""
        pass
```

#### API Client
```python
class HAAPIClient:
    """Home Assistant REST API client"""
    
    async def get_camera_snapshot(self, entity_id: str) -> bytes:
        """Get camera snapshot via HA API"""
        pass
    
    async def call_service(self, domain: str, service: str, data: dict):
        """Call HA service"""
        pass
```

### 5. PDCA Implementation (`core/pdca/`)

#### Planner
```python
class AIPlanner:
    """AI-driven cleaning plan creation"""
    
    async def create_plan(self) -> CleaningPlan:
        """Analyze current state and create plan"""
        # 1. Get camera snapshots
        # 2. Analyze images with AI
        # 3. Create structured cleaning plan
        # 4. Prioritize tasks based on urgency/importance
        pass
```

#### Executor
```python
class TaskExecutor:
    """Execute cleaning plans via HA integration"""
    
    async def execute_plan(self, plan: CleaningPlan):
        """Convert plan to HA entities and tasks"""
        # 1. Create todo items
        # 2. Update sensor states
        # 3. Send notifications if configured
        pass
```

#### Checker
```python
class ProgressChecker:
    """Monitor cleaning progress"""
    
    async def check_progress(self) -> ProgressReport:
        """Assess progress on current tasks"""
        # 1. Check todo item completion
        # 2. Re-analyze areas if needed
        # 3. Generate progress metrics
        pass
```

#### Actor
```python
class AdaptiveActor:
    """Implement continuous improvement"""
    
    async def adapt_based_on_progress(self, progress: ProgressReport):
        """Improve future plans based on outcomes"""
        # 1. Analyze what worked/didn't work
        # 2. Update AI prompts and strategies
        # 3. Adjust scheduling and priorities
        pass
```

### 6. Data Models

```python
@dataclass
class ZoneConfig:
    id: str
    name: str
    camera_entity: Optional[str] = None
    priority: int = 3  # 1-5 scale
    schedule: Optional[str] = None

@dataclass
class CleaningTask:
    id: str
    title: str
    description: str
    priority: int
    zone_id: Optional[str] = None
    estimated_time: int  # minutes
    created_at: datetime

@dataclass
class CleaningPlan:
    id: str
    tasks: List[CleaningTask]
    created_at: datetime
    analysis_summary: str
    confidence_score: float

@dataclass
class ProgressReport:
    plan_id: str
    completed_tasks: List[str]
    pending_tasks: List[str]
    progress_percentage: float
    next_analysis_time: datetime
```

## Entity Definitions

### Sensors
- `sensor.ai_cleaner_status`: Overall system status
- `sensor.ai_cleaner_last_analysis`: Timestamp of last analysis  
- `sensor.ai_cleaner_task_count`: Number of active tasks
- `sensor.ai_cleaner_confidence`: AI confidence in last analysis

### Todo Lists
- `todo.cleaning_tasks`: Main cleaning task list
- `todo.zone_{zone_id}_tasks`: Zone-specific tasks (if zones enabled)

### Binary Sensors
- `binary_sensor.ai_cleaner_analysis_needed`: Indicates if analysis is due
- `binary_sensor.ai_cleaner_ai_available`: AI provider availability

## Error Handling Strategy

### 1. Graceful Degradation
- Fall back to Ollama if Gemini unavailable
- Continue with logging if MQTT unavailable
- Basic functionality even without camera access

### 2. Retry Logic
- Exponential backoff for API failures
- Circuit breaker pattern for unreliable services
- Health checks with automatic recovery

### 3. User Communication
- Clear error messages in HA notifications
- Diagnostic sensors for troubleshooting
- Comprehensive logging at appropriate levels

## Security Considerations

### 1. API Key Management
- Secure storage of API keys
- Key rotation support
- Validation of key formats

### 2. Image Handling
- Privacy-first processing
- Optional local-only mode
- Secure temporary file handling
- Configurable image retention

### 3. Network Security
- TLS for external API calls
- Input validation for all external data
- Rate limiting for API usage

## Performance Requirements

### 1. Resource Efficiency
- Async/await throughout for I/O operations
- Connection pooling for HTTP clients
- Memory-efficient image processing

### 2. Scalability
- Support for multiple zones
- Configurable analysis intervals
- Adaptive resource usage

### 3. Reliability
- Health checks and monitoring
- Automatic restart on critical failures
- State persistence across restarts

## Testing Strategy

### 1. Unit Tests
- Mock AI providers for testing
- Test configuration validation
- Test PDCA component interactions

### 2. Integration Tests
- Test MQTT entity creation
- Test HA API interactions
- Test complete PDCA cycles

### 3. End-to-End Tests
- Test full addon lifecycle
- Test error scenarios
- Test configuration changes

## Implementation Priorities

### Phase 1: Core Foundation
1. Configuration management
2. Basic AI provider integration
3. Simple image analysis
4. HA entity creation

### Phase 2: PDCA Implementation
1. Planning logic
2. Task execution
3. Progress monitoring
4. Basic adaptation

### Phase 3: Advanced Features
1. Multi-zone support
2. Advanced scheduling
3. Detailed analytics
4. Performance optimization

### Phase 4: Polish and Reliability
1. Comprehensive error handling
2. Advanced logging and diagnostics
3. Performance tuning
4. Documentation and examples

## Success Metrics

### 1. Functional Goals
- Successful image analysis and task creation
- Reliable HA integration
- Effective PDCA cycle execution
- User-friendly configuration

### 2. Performance Goals
- < 30s for image analysis
- < 5s for task creation
- 99%+ uptime after startup
- Minimal resource usage

### 3. Quality Goals
- Comprehensive error handling
- Clear logging and diagnostics
- Maintainable, well-documented code
- Positive user experience

## Next Steps for DO Agent

The DO agent should implement this architecture by:

1. Creating the main application structure in `src/`
2. Implementing core modules in order of priority
3. Adding comprehensive error handling and logging
4. Creating unit and integration tests
5. Documenting implementation details

Focus on creating a robust, maintainable codebase that follows Home Assistant addon best practices and provides a solid foundation for future enhancements.