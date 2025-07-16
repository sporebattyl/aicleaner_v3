# Phase 3 Development Prompt (v2): Local LLM Integration & Advanced Features

## Context: Building on Phase 2 Success

**Phase 2 Status**: ✅ **COMPLETE** - 87 tests passing, performance exceeding targets by 10-500x
- AI Coordinator implemented with orchestration capabilities
- Object database with hybrid prioritization (Safety/Hygiene → Aesthetics)
- Enhanced task generation with room-specific intelligence
- Comprehensive caching and performance optimization

## Collaborators: Gemini & Claude

---

## 1. High-Level Objective

**Goal**: Transform the `aicleaner_v3` system into a **privacy-first, cost-effective, and fully autonomous cleaning assistant** by implementing local LLM capabilities while maintaining cloud fallback options.

This builds on our successful Phase 2 implementation by adding local AI processing, advanced analytics, and deployment optimization.

## 2. Architectural Foundation: Leveraging Phase 2 Success

Our Phase 2 implementation provides a solid foundation:
- **AI Coordinator**: Central orchestration layer (✅ implemented)
- **Object Database**: 20+ household objects with characteristics (✅ implemented)
- **Hybrid Prioritization**: Safety/Hygiene → Aesthetics (✅ implemented)
- **Performance Optimization**: 497x cache speedup, sub-ms operations (✅ implemented)

**Phase 3 builds on this foundation** by adding local processing capabilities and advanced features.

---

## 3. Implementation Plan (Phased Approach)

### **Phase 3A: Local LLM Integration and Offline Capability**

#### **Task 3A.1: Local LLM Client Implementation**

**File**: `integrations/ollama_client.py`
**Purpose**: Enable communication with local Ollama LLM instances

**Key Requirements:**
```python
class OllamaClient:
    """Client for local Ollama LLM communication"""
    
    async def analyze_image_local(self, image_path: str, model: str, prompt: str) -> Dict[str, Any]:
        """Analyze image using local vision model (LLaVA, Bakllava)"""
        
    async def generate_tasks_local(self, analysis: str, context: Dict) -> List[Dict]:
        """Generate cleaning tasks using local LLM"""
        
    async def check_model_availability(self, model: str) -> bool:
        """Check if model is available locally"""
        
    async def download_model(self, model: str) -> bool:
        """Download model if not available"""
```

**Configuration Integration:**
```yaml
ai_enhancements:
  local_llm:
    enabled: true
    ollama_host: "localhost:11434"
    preferred_models:
      vision: "llava:13b"
      text: "mistral:7b"
      fallback: "gemini"
    auto_download: true
    max_concurrent: 1
```

#### **Task 3A.2: Intelligent Model Router Enhancement**

**File**: `ai/model_router.py` (new)
**Purpose**: Smart routing between local and cloud models

**Routing Logic:**
1. **Local First**: Try local models if available and enabled
2. **Cloud Fallback**: Use Gemini/Claude if local fails or unavailable
3. **Cached Fallback**: Use cached responses as last resort
4. **Performance Monitoring**: Track success rates and response times

**Integration with AI Coordinator:**
- Enhance existing `AICoordinator._select_model()` method
- Add local model preference logic
- Implement automatic fallback strategies

#### **Task 3A.3: Local Model Manager**

**File**: `core/local_model_manager.py` (new)
**Purpose**: Manage local model lifecycle and resources

**Key Features:**
- Automatic model downloading and updates
- Resource usage monitoring (CPU, memory, disk)
- Model performance optimization
- Health checks and model validation

### **Phase 3B: Advanced Analytics and Gamification**

#### **Task 3B.1: Enhanced Predictive Analytics**

**File**: `ai/predictive_analytics.py` (enhance existing)
**Purpose**: Leverage local LLMs for privacy-preserving analytics

**New Capabilities:**
- **Pattern Recognition**: Analyze cleaning patterns using local models
- **Seasonal Adjustments**: Predict seasonal cleaning needs
- **Usage Optimization**: Optimize cleaning schedules based on household patterns
- **Privacy-First**: All analytics run locally without external API calls

#### **Task 3B.2: Gamification System Implementation**

**File**: `gamification/gamification.py` (enhance existing)
**Purpose**: Increase user engagement through achievement systems

**Features to Implement:**
- **Cleaning Streaks**: Track consecutive days of cleaning
- **Achievement System**: Unlock badges for cleaning milestones
- **Progress Tracking**: Visual progress indicators in Home Assistant
- **Challenge System**: Weekly/monthly cleaning challenges

### **Phase 3C: System Optimization and Deployment**

#### **Task 3C.1: Performance Optimization for Local LLMs**

**Focus Areas:**
- **Model Quantization**: Implement model optimization techniques
- **Memory Management**: Efficient model loading/unloading
- **Batch Processing**: Optimize multiple zone analysis
- **Prompt Engineering**: Optimize prompts for local model efficiency

#### **Task 3C.2: Enhanced Testing and Validation**

**New Test Requirements:**
- **Local LLM Tests**: Validate local model integration
- **Fallback Testing**: Ensure graceful degradation
- **Performance Tests**: Validate local vs cloud performance
- **Integration Tests**: End-to-end testing with local models

---

## 4. Questions for Gemini

### **Technical Implementation Questions:**

1. **Local Model Selection**: Which specific Ollama models do you recommend for:
   - Vision analysis (LLaVA variants, Bakllava, etc.)
   - Text generation (Mistral, Llama2, CodeLlama)
   - Task generation and reasoning

2. **Prompt Engineering**: How should we adapt our existing prompts for local models?
   - Should we use different prompt structures for local vs cloud models?
   - What are the optimal prompt lengths for local model efficiency?

3. **Performance Optimization**: What specific techniques should we implement for:
   - Model quantization and optimization
   - Memory management for resource-constrained environments
   - Batch processing for multiple zones

4. **Fallback Strategy**: How should we handle the transition between local and cloud models?
   - What criteria should trigger fallback to cloud models?
   - How do we maintain consistency in analysis quality?

### **Architecture and Integration Questions:**

5. **Model Router Design**: Should the model router be:
   - A separate service that the AI Coordinator calls?
   - Integrated directly into the AI Coordinator?
   - A middleware layer between components?

6. **Configuration Management**: How should we structure the configuration for:
   - Model preferences per analysis type
   - Resource limits and performance tuning
   - Automatic model management settings

7. **Analytics Privacy**: For the predictive analytics running locally:
   - What data should we store vs process in real-time?
   - How do we balance accuracy with privacy?
   - Should we implement differential privacy techniques?

### **User Experience Questions:**

8. **Setup Complexity**: How can we minimize the setup complexity for users?
   - Should we provide pre-configured Docker containers?
   - What's the minimum viable local setup?

9. **Performance Expectations**: What should users expect in terms of:
   - Analysis speed compared to cloud models
   - Resource usage (CPU, memory, disk)
   - Model download times and storage requirements

---

## 5. Answers to Previous Gemini Questions

### **From Phase 2 Implementation Summary:**

1. **✅ Hybrid Prioritization**: The Safety/Hygiene → Aesthetics approach is fully implemented and tested
2. **✅ Object Database**: 20+ objects implemented, easily extensible for additional types
3. **✅ Performance Benchmarks**: All targets exceeded significantly (497x cache speedup, 1,153 ops/sec)
4. **✅ Edge Cases**: Comprehensive error handling and graceful degradation implemented
5. **✅ Room-Specific Handling**: Kitchen dishes get "Clean and put away", bathroom towels get "Hang", etc.

### **Additional Improvements Made:**
- **Enhanced Task Structure**: Tasks now include priority, urgency, estimated time, safety level
- **Context-Aware Actions**: Room-specific handling based on object database
- **Performance Caching**: Object database lookups cached with LRU eviction
- **Comprehensive Testing**: 87 tests with 100% pass rate

---

## 6. Success Criteria for Phase 3

### **Functional Requirements:**
- [ ] Addon can operate completely offline using local LLMs
- [ ] Seamless fallback between local and cloud models
- [ ] Comparable analysis quality between local and cloud models
- [ ] Automatic model management with minimal user intervention
- [ ] Enhanced privacy with no external API calls in local-only mode

### **Performance Requirements:**
- [ ] Local analysis completes within 2x cloud model time
- [ ] Memory usage stays under 4GB for local models
- [ ] Model switching occurs within 30 seconds
- [ ] 95% uptime for local model availability

### **Quality Requirements:**
- [ ] Maintain 100% test pass rate
- [ ] All new code follows TDD and AAA testing principles
- [ ] Component-based design with clear interfaces
- [ ] Comprehensive documentation for local setup

---

## 7. Collaboration Workflow

**Gemini Focus Areas:**
- Local LLM integration and optimization
- Prompt engineering for local models
- Performance tuning and resource management
- Privacy-preserving analytics implementation

**Claude Focus Areas:**
- Architectural integration and model routing
- Testing framework enhancement
- Configuration management
- Documentation and deployment guides

**Shared Responsibilities:**
- End-to-end integration testing
- Performance validation and optimization
- User experience refinement
- Final system validation

---

## 8. Next Steps

1. **Gemini**: Please review this refined prompt and provide feedback on:
   - Technical approach and model recommendations
   - Performance optimization strategies
   - Privacy and analytics considerations

2. **Implementation Priority**: Which Phase 3 task should we tackle first?
   - 3A.1 (Local LLM Client) for immediate local capability?
   - 3A.2 (Model Router) for intelligent routing?
   - 3B.1 (Enhanced Analytics) for improved predictions?

3. **Resource Planning**: What are the minimum system requirements we should target for local LLM operation?

**Ready to begin Phase 3 implementation upon Gemini's feedback and agreement on approach.**
