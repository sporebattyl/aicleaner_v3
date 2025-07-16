# ⚙️ AICleaner v3 Configuration Reference

Complete reference for configuring AICleaner v3 with Ollama integration.

## 📋 Table of Contents

- [Configuration Files](#configuration-files)
- [Environment Variables](#environment-variables)
- [Local LLM Settings](#local-llm-settings)
- [AI Enhancements](#ai-enhancements)
- [Privacy Settings](#privacy-settings)
- [Performance Tuning](#performance-tuning)
- [Home Assistant Integration](#home-assistant-integration)
- [Zone Configuration](#zone-configuration)
- [Advanced Settings](#advanced-settings)

## 📁 Configuration Files

### Primary Configuration (`config.yaml`)

Main configuration file for AICleaner v3:

```yaml
# AICleaner v3 Configuration
display_name: "AI Cleaner v3"

# Local LLM Configuration
local_llm:
  enabled: true
  host: "ollama:11434"
  auto_download: true
  preferred_models:
    vision: "llava:13b"
    text: "mistral:7b"
  performance_tuning:
    timeout_seconds: 120
    max_concurrent_requests: 2
    memory_limit_mb: 4096
    quantization_level: 4

# Additional sections...
```

### Environment Variables (`.env`)

Environment-specific settings:

```bash
# Ollama Configuration
OLLAMA_HOST=ollama:11434
OLLAMA_MODELS_PATH=/data/models
OLLAMA_AUTO_DOWNLOAD=true

# AICleaner Configuration
AICLEANER_DATA_PATH=/data/aicleaner
AICLEANER_LOG_LEVEL=INFO
AICLEANER_PRIVACY_LEVEL=standard

# Home Assistant Integration
HA_TOKEN=your_token_here
HA_URL=http://homeassistant:8123
```

## 🌍 Environment Variables

### Core Variables

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `OLLAMA_HOST` | `localhost:11434` | Ollama server address | ✅ |
| `OLLAMA_MODELS_PATH` | `/data/models` | Model storage path | ✅ |
| `OLLAMA_AUTO_DOWNLOAD` | `true` | Auto-download models | ❌ |
| `AICLEANER_DATA_PATH` | `/data/aicleaner` | Data storage path | ✅ |
| `AICLEANER_LOG_LEVEL` | `INFO` | Logging level | ❌ |
| `AICLEANER_PRIVACY_LEVEL` | `standard` | Privacy mode | ❌ |

### Home Assistant Variables

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `HA_TOKEN` | - | Long-lived access token | ✅ |
| `HA_URL` | `http://homeassistant:8123` | HA instance URL | ✅ |
| `SUPERVISOR_TOKEN` | - | HA Supervisor token | HA OS only |
| `HASSIO_TOKEN` | - | Hassio API token | HA OS only |

### Performance Variables

| Variable | Default | Description | Range |
|----------|---------|-------------|-------|
| `MAX_MEMORY_USAGE` | `4096` | Max memory (MB) | 1024-16384 |
| `MAX_CPU_USAGE` | `80` | Max CPU percentage | 10-100 |
| `QUANTIZATION_LEVEL` | `4` | Model quantization | 4, 8, 16 |
| `TIMEOUT_SECONDS` | `120` | Request timeout | 30-600 |

### Optional Cloud AI Variables

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `GEMINI_API_KEY` | - | Google Gemini API key | ❌ |
| `ANTHROPIC_API_KEY` | - | Anthropic Claude API key | ❌ |
| `OPENAI_API_KEY` | - | OpenAI API key | ❌ |

## 🤖 Local LLM Settings

### Basic Configuration

```yaml
local_llm:
  enabled: true                    # Enable local LLM processing
  host: "ollama:11434"            # Ollama server address
  auto_download: true             # Auto-download missing models
  fallback_to_cloud: false       # Use cloud AI if local fails
```

### Model Configuration

```yaml
local_llm:
  preferred_models:
    vision: "llava:13b"           # Vision analysis model
    text: "mistral:7b"            # Text generation model
    fallback: "llama2:7b"         # Fallback text model
  
  model_aliases:
    "llava": "llava:13b"          # Model shortcuts
    "mistral": "mistral:7b"
    "llama": "llama2:7b"
```

### Performance Tuning

```yaml
local_llm:
  performance_tuning:
    timeout_seconds: 120          # Request timeout
    max_concurrent_requests: 2    # Concurrent inference limit
    memory_limit_mb: 4096         # Memory limit per model
    quantization_level: 4         # Model quantization (4, 8, 16)
    keep_alive_minutes: 60        # Model keep-alive time
    preload_models: true          # Preload models at startup
```

### Advanced Model Settings

```yaml
local_llm:
  model_settings:
    llava:13b:
      temperature: 0.7            # Response creativity
      top_p: 0.9                  # Nucleus sampling
      top_k: 40                   # Top-k sampling
      repeat_penalty: 1.1         # Repetition penalty
      context_length: 4096        # Context window size
    
    mistral:7b:
      temperature: 0.8
      top_p: 0.95
      max_tokens: 512             # Max response length
```

## 🧠 AI Enhancements

### Predictive Analytics

```yaml
ai_enhancements:
  predictive_analytics:
    enabled: true                 # Enable analytics
    privacy_preserving: true      # Use privacy-preserving methods
    retention_days: 30            # Data retention period
    learning_rate: 0.01           # Model learning rate
    confidence_threshold: 0.8     # Prediction confidence threshold
    
    features:
      pattern_recognition: true   # Recognize cleaning patterns
      seasonal_adjustment: true   # Adjust for seasons
      user_behavior_modeling: true # Model user preferences
```

### Gamification System

```yaml
ai_enhancements:
  gamification:
    enabled: true                 # Enable gamification
    privacy_first: true           # Privacy-first design
    home_assistant_integration: true # HA integration
    
    scoring:
      base_points: 10             # Base points per task
      difficulty_multiplier: 1.5  # Difficulty bonus
      streak_bonus: 2.0           # Streak multiplier
      perfect_room_bonus: 50      # Perfect room bonus
    
    achievements:
      enabled: true               # Enable achievements
      notification_style: "subtle" # Notification style
```

### Scene Understanding

```yaml
ai_enhancements:
  scene_understanding:
    enabled: true                 # Enable scene analysis
    confidence_threshold: 0.7     # Detection confidence
    object_detection: true        # Detect objects
    spatial_analysis: true        # Analyze spatial relationships
    context_awareness: true       # Context-aware analysis
```

## 🔒 Privacy Settings

### Privacy Levels

```yaml
privacy:
  level: "standard"               # strict, standard, relaxed
  data_retention_days: 30         # Data retention period
  analytics_enabled: true         # Enable analytics
  telemetry_enabled: false        # Disable telemetry
  
  data_processing:
    local_only: true              # Process data locally only
    anonymization: true           # Anonymize personal data
    encryption_at_rest: true      # Encrypt stored data
    secure_transmission: true     # Use secure protocols
```

### GDPR Compliance

```yaml
privacy:
  gdpr_compliance:
    enabled: true                 # Enable GDPR features
    consent_required: true        # Require explicit consent
    data_portability: true        # Enable data export
    right_to_deletion: true       # Enable data deletion
    privacy_by_design: true       # Privacy by design
```

## 🚀 Performance Tuning

### Resource Management

```yaml
performance:
  max_memory_usage: 4096          # Max memory in MB
  max_cpu_usage: 80               # Max CPU percentage
  cache_ttl_seconds: 300          # Cache time-to-live
  batch_processing: true          # Enable batch processing
  
  optimization:
    model_caching: true           # Cache loaded models
    result_caching: true          # Cache analysis results
    image_preprocessing: true     # Optimize images
    parallel_processing: true     # Use parallel processing
```

### Scaling Configuration

```yaml
performance:
  scaling:
    auto_scaling: true            # Enable auto-scaling
    min_workers: 1                # Minimum workers
    max_workers: 4                # Maximum workers
    scale_threshold: 0.8          # CPU threshold for scaling
    scale_cooldown: 300           # Cooldown period (seconds)
```

## 🏠 Home Assistant Integration

### Basic Integration

```yaml
home_assistant:
  api_url: "http://homeassistant:8123"  # HA API URL
  token: "${HA_TOKEN}"                  # Access token
  timeout_seconds: 30                   # Request timeout
  retry_attempts: 3                     # Retry failed requests
```

### Entity Configuration

```yaml
home_assistant:
  entities:
    sensors:
      create_status_sensor: true       # Create status sensor
      create_metrics_sensors: true     # Create metrics sensors
      sensor_prefix: "aicleaner"       # Sensor name prefix
    
    cameras:
      snapshot_timeout: 10             # Snapshot timeout
      image_quality: "high"            # Image quality
      cache_snapshots: true            # Cache snapshots
    
    todo_lists:
      auto_create: true                # Auto-create todo lists
      list_prefix: "cleaning"          # List name prefix
      task_completion_tracking: true   # Track task completion
```

### Automation Integration

```yaml
home_assistant:
  automation:
    webhook_enabled: true             # Enable webhooks
    webhook_path: "/api/webhook"      # Webhook endpoint
    event_publishing: true            # Publish events
    service_calls: true               # Enable service calls
```

## 🏠 Zone Configuration

### Basic Zone Setup

```yaml
zones:
  - name: "Living Room"               # Zone display name
    camera_entity: "camera.living_room" # Camera entity ID
    todo_list_entity: "todo.living_room_cleaning" # Todo list entity
    purpose: "Living room for relaxation" # Zone purpose
    interval_minutes: 60              # Analysis interval
    enabled: true                     # Zone enabled
```

### Advanced Zone Settings

```yaml
zones:
  - name: "Kitchen"
    camera_entity: "camera.kitchen"
    todo_list_entity: "todo.kitchen_cleaning"
    purpose: "Kitchen for cooking and dining"
    interval_minutes: 30
    
    # Scheduling
    schedule:
      specific_times: ["08:00", "18:00"] # Specific analysis times
      random_offset_minutes: 15         # Random offset
      skip_when_occupied: true          # Skip if occupied
    
    # Analysis settings
    analysis:
      sensitivity: "high"               # Detection sensitivity
      confidence_threshold: 0.8        # Confidence threshold
      focus_areas: ["countertop", "sink"] # Focus on specific areas
    
    # Ignore rules
    ignore_rules:
      - "Ignore items on the counter during cooking hours"
      - "Don't worry about dishes in the sink"
      - "Ignore temporary items on the island"
    
    # Notifications
    notifications:
      enabled: true                     # Enable notifications
      priority: "normal"                # Notification priority
      quiet_hours: ["22:00", "07:00"]  # Quiet hours
```

## 🔧 Advanced Settings

### Logging Configuration

```yaml
logging:
  level: "INFO"                       # DEBUG, INFO, WARNING, ERROR
  file: "/logs/aicleaner.log"         # Log file path
  max_size_mb: 10                     # Max log file size
  backup_count: 5                     # Number of backup files
  
  formatters:
    console: "%(levelname)s: %(message)s"
    file: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  loggers:
    aicleaner: "INFO"                 # Main application
    ollama: "WARNING"                 # Ollama client
    homeassistant: "INFO"             # HA integration
```

### Development Settings

```yaml
development:
  debug_mode: false                   # Enable debug mode
  test_mode: false                    # Enable test mode
  mock_cameras: false                 # Use mock cameras
  mock_ollama: false                  # Use mock Ollama
  
  profiling:
    enabled: false                    # Enable profiling
    output_dir: "/tmp/profiles"       # Profile output directory
  
  testing:
    auto_test: false                  # Run tests automatically
    test_data_dir: "/app/test_data"   # Test data directory
```

### Integration Settings

```yaml
integrations:
  mqtt:
    enabled: false                    # Enable MQTT
    host: "mqtt.local"                # MQTT broker host
    port: 1883                        # MQTT broker port
    username: ""                      # MQTT username
    password: ""                      # MQTT password
    topic_prefix: "aicleaner"         # Topic prefix
  
  webhooks:
    enabled: true                     # Enable webhooks
    secret_key: "your-secret-key"     # Webhook secret
    allowed_ips: ["192.168.1.0/24"]   # Allowed IP ranges
```

## 📝 Configuration Validation

### Validation Commands

```bash
# Validate configuration
docker exec aicleaner-app-basic python -m aicleaner.config validate

# Test Ollama connection
docker exec aicleaner-app-basic python -m aicleaner.test ollama

# Test Home Assistant connection
docker exec aicleaner-app-basic python -m aicleaner.test homeassistant
```

### Configuration Templates

```bash
# Generate default configuration
docker exec aicleaner-app-basic python -m aicleaner.config generate

# Generate configuration for specific use case
docker exec aicleaner-app-basic python -m aicleaner.config generate --template production
```

---

**💡 Pro Tip**: Start with the default configuration and gradually customize settings based on your specific needs. Always validate configuration changes before deploying to production!
