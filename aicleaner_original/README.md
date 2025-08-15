# AICleaner V3 - Fresh Start Implementation

A clean, modern implementation of AICleaner with **visual annotations**, **4-level privacy spectrum**, and **PDCA-based architecture**.

## 🌟 Key Features

- **Visual Annotations**: Tasks highlighted with bounding boxes on images
- **Privacy Spectrum**: 4 levels from cloud-fast to local-private 
- **PDCA Architecture**: Plan-Do-Check-Act methodology with intelligent provider fallbacks
- **External LLM Support**: Connect to user-managed Ollama instances
- **Real Testing**: No mock testing - designed for real-world reliability

## 🏗️ Architecture Overview

### Core Components

- **Privacy Engine**: 4-level image processing (raw → sanitized → metadata → local)
- **Annotation Engine**: Bounding box overlays with task highlighting
- **PDCA Orchestrator**: Intelligent provider selection with health monitoring
- **Provider System**: Pluggable LLM backends (Gemini, Ollama, extensible)
- **Configuration**: Pydantic-based validation with comprehensive schema

### Privacy Levels

1. **Level 1 - Raw**: Images → Cloud API (fastest, no privacy)
2. **Level 2 - Sanitized**: Face-blurred images → Cloud API (**recommended balance**)
3. **Level 3 - Metadata**: Text descriptions → Cloud API (high privacy, limited accuracy)
4. **Level 4 - Local**: Everything via external Ollama (maximum privacy)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Providers

Copy and edit the example configuration:

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys and preferences
```

**For Gemini (Cloud)**:
```yaml
providers:
  gemini:
    api_key: "your-gemini-api-key-here"
    model: "gemini-pro-vision"
```

**For Ollama (Local)**:
```yaml
providers:
  ollama:
    host: "localhost"  # Your Ollama server
    port: 11434
    vision_model: "llava:13b"
```

### 3. Run the Application

```bash
python src/main.py --config config.yaml
```

**Validation Mode**:
```bash
python src/main.py --config config.yaml --validate-only
```

## 📊 Usage Examples

### Basic Image Analysis

```python
from main import AICleanerApplication

app = AICleanerApplication("config.yaml")
await app.initialize()

# Analyze image with default privacy level
with open("kitchen.jpg", "rb") as f:
    image_data = f.read()

result = await app.analyze_image(
    image_bytes=image_data,
    prompt="Identify cleaning tasks in this kitchen"
)

print(f"Found {len(result['tasks'])} cleaning tasks")
for task in result['tasks']:
    print(f"- {task['description']} (Priority: {task['priority']})")
```

### Privacy Level Override

```python
from core.privacy_engine import PrivacyLevel

# Use maximum privacy (local processing only)
result = await app.analyze_image(
    image_bytes=image_data,
    privacy_level=PrivacyLevel.LEVEL_4_LOCAL
)

# Use sanitized images for cloud processing  
result = await app.analyze_image(
    image_bytes=image_data,
    privacy_level=PrivacyLevel.LEVEL_2_SANITIZED
)
```

### Health Monitoring

```python
health = await app.get_system_health()
print(f"System Status: {health['status']}")
print(f"Providers: {list(health['providers'].keys())}")
print(f"Requests Processed: {health['requests_processed']}")
```

## 🔧 Configuration Guide

### Privacy Engine Settings

```yaml
privacy:
  default_level: 2              # Recommended: Level 2 (sanitized)
  face_blur_strength: 99        # Face blur intensity
  text_blur_strength: 15        # Text region blur intensity
```

### Visual Annotations

```yaml
annotation:
  enable_annotations: true      # Enable bounding boxes
  box_color: [255, 0, 0]       # Red bounding boxes
  show_confidence: true         # Display confidence scores
  number_tasks: true           # Number tasks in order
```

### Provider Fallback Chain

```yaml
primary_provider: gemini        # Try Gemini first
fallback_providers:            # Fallback order
  - gemini_backup
  - ollama
```

## 🧪 Testing Strategy

This implementation uses **real testing only** - no mocks unless explicitly justified.

### Test Requirements

- **Real Gemini API**: Test account with valid API key
- **Real Ollama Instance**: Running server with vision models
- **Real Images**: Camera feeds or test image sets
- **Live Environment**: Home Assistant instance for integration testing

### Running Tests

```bash
# Unit tests with real dependencies
pytest tests/unit/ -v

# Integration tests (requires live services)
pytest tests/integration/ -v

# Full test suite
pytest tests/ -v
```

## 📚 Implementation Phases

### Phase 1: Gemini + Visual Annotations ✅
- [x] Gemini provider with visual grounding
- [x] Bounding box annotation system
- [x] Basic privacy processing
- [x] PDCA orchestration framework

### Phase 2: Privacy Spectrum (In Progress)
- [x] 4-level privacy implementation
- [x] Image sanitization pipeline
- [x] Metadata extraction for Level 3
- [ ] User interface for privacy selection

### Phase 3: External LLM Integration (Planned)
- [x] Ollama provider template
- [x] External server health monitoring
- [ ] Model management interface
- [ ] Performance optimization

## 🏢 Home Assistant Integration

### Addon Configuration

```yaml
# addon config.yaml
privacy_level: 2                    # Default privacy level
primary_api_key: "your-key-here"    # Gemini API key
ollama_host: "localhost"            # External Ollama server
enable_annotations: true            # Visual annotations
auto_dashboard: true                # Auto-configure dashboard
```

### Entity Discovery

The system automatically creates Home Assistant entities:
- `sensor.aicleaner_v3_status` - System status
- `sensor.aicleaner_v3_last_analysis` - Last analysis time
- `switch.aicleaner_v3_enabled` - Enable/disable processing

## 🔍 Debugging and Monitoring

### Debug Mode

```bash
python src/main.py --debug --config config.yaml
```

### Performance Monitoring

```python
# Get performance metrics
performance = app.orchestrator.get_performance_metrics()
print(f"Success Rate: {performance['success_rate']:.1%}")
print(f"Average Processing Time: {performance['average_processing_time']:.2f}s")
```

### Health Endpoints

```python
health = await app.get_system_health()
# Returns comprehensive status of all components
```

## 🛡️ Security Considerations

### API Key Management
- Keys stored securely in configuration
- Masked in logs and exports
- Rotation support for backup keys

### Privacy Protection
- Face detection and blurring for Level 2
- Metadata-only processing for Level 3
- Complete local processing for Level 4

### Input Validation
- Comprehensive Pydantic schema validation
- Sanitization of all user inputs
- Error boundary isolation

## 🎯 Best Practices

### Configuration Management
- Use `config.example.yaml` as template
- Validate configuration with `--validate-only`
- Separate sensitive data (API keys) from general config

### Provider Selection
- Set Gemini as primary for best accuracy
- Configure Ollama fallback for privacy
- Use multiple Gemini keys for redundancy

### Privacy Selection
- Level 2 (sanitized) recommended for most users
- Level 4 (local) for maximum privacy needs
- Level 1 (raw) only when privacy not a concern

### Performance Optimization
- Monitor health endpoints regularly
- Use appropriate timeout values
- Configure resource limits for Ollama

## 🤝 Contributing

### Development Setup

```bash
git clone <repository>
cd "FRESH START AI CLEANER"
pip install -r requirements.txt
pip install -e .
```

### Code Quality

```bash
# Format code
black src/ tests/

# Type checking
mypy src/

# Run full test suite
pytest tests/ -v
```

### Architecture Principles
- **PDCA Methodology**: Plan-Do-Check-Act for all operations
- **Real Testing**: No mocks unless explicitly justified
- **Component Isolation**: Clear boundaries between modules
- **Configuration-Driven**: Behavior controlled by config, not code

## 📖 Documentation

- `docs/1_REFINED_ARCHITECTURE.md` - Detailed architecture overview
- `docs/2_IMPLEMENTATION_PHASES.md` - Development roadmap
- `docs/3_TESTING_STRATEGY.md` - Real testing methodology
- `docs/4_MIGRATION_STRATEGY.md` - Transition from legacy code

## ⚡ Performance

### Typical Processing Times
- **Level 1 (Raw)**: ~2-3 seconds
- **Level 2 (Sanitized)**: ~4-5 seconds  
- **Level 3 (Metadata)**: ~3-4 seconds
- **Level 4 (Local)**: ~15-30 seconds (depends on hardware)

### Resource Usage
- **Memory**: 200-500MB baseline
- **CPU**: Low when idle, spikes during processing
- **Storage**: Minimal (logs and config only)

## 🐛 Known Issues

- Local models (Ollama) don't typically provide bounding boxes
- Level 3 (metadata) may miss specific spatial details
- First-time Ollama model downloads are slow

## 📜 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Issues**: Use GitHub issues for bug reports
- **Discussions**: GitHub discussions for questions
- **Documentation**: See `/docs` directory for detailed guides

---

Built with ❤️ using modern Python, PDCA methodology, and real-world testing.