# Phase 3 Development Prompt (v3): Local LLM Integration & Advanced Features

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

## 4. Questions for Gemini (Answered by Gemini)

### **Technical Implementation Questions:**

1.  **Local Model Selection**: Which specific Ollama models do you recommend for:
    *   Vision analysis (LLaVA variants, Bakllava, etc.)
    *   Text generation (Mistral, Llama2, CodeLlama)
    *   Task generation and reasoning

    **Gemini's Answer**: For vision analysis, `llava:13b` or `bakllava:7b` are good starting points, balancing capability and resource usage. For text generation and task generation/reasoning, `mistral:7b` offers a good balance of performance and size. `llama2:7b` is also a strong contender for general text tasks. `codellama` variants could be useful if code generation or understanding is a significant part of the task generation, but for general cleaning tasks, `mistral` or `llama2` should suffice.

2.  **Prompt Engineering**: How should we adapt our existing prompts for local models?
    *   Should we use different prompt structures for local vs cloud models?
    *   What are the optimal prompt lengths for local model efficiency?

    **Gemini's Answer**: Yes, it's highly recommended to use different prompt structures for local vs. cloud models. Local models often benefit from more explicit instructions and less "fluff" in prompts. They might also be more sensitive to prompt length. Optimal prompt lengths will vary by model, but generally, keep them as concise as possible while retaining clarity. Experimentation will be key here.

3.  **Performance Optimization**: What specific techniques should we implement for:
    *   Model quantization and optimization
    *   Memory management for resource-constrained environments
    *   Batch processing for multiple zones

    **Gemini's Answer**: For model quantization, explore 4-bit or 8-bit quantization if supported by Ollama and the specific models. This significantly reduces memory footprint and can improve inference speed. For memory management, implement strategies to load/unload models dynamically based on demand, rather than keeping all models in memory. For batch processing, ensure that the `OllamaClient` can handle multiple analysis requests in a single call to the local LLM, if the Ollama API supports it, to reduce overhead.

4.  **Fallback Strategy**: How should we handle the transition between local and cloud models?
    *   What criteria should trigger fallback to cloud models?
    *   How do we maintain consistency in analysis quality?

    **Gemini's Answer**: Fallback to cloud models should be triggered by:
    *   Local model unavailability (e.g., Ollama server not running, model not downloaded).
    *   Local model failure (e.g., inference error, timeout).
    *   Explicit user preference for cloud models.
    *   For consistency, implement a "confidence score" or "quality check" on local model outputs. If the local output falls below a certain threshold (e.g., low confidence, incomplete response), trigger a fallback to the cloud model for re-analysis.

### **Architecture and Integration Questions:**

5.  **Model Router Design**: Should the model router be:
    *   A separate service that the AI Coordinator calls?
    *   Integrated directly into the AI Coordinator?
    *   A middleware layer between components?

    **Gemini's Answer**: Integrating the model router directly into the `AI Coordinator` (or as a dedicated module within the `ai` package that the `AI Coordinator` uses) seems most appropriate for this project's scope. This keeps the architecture simpler and avoids the overhead of inter-service communication. A middleware layer could be considered if the routing logic becomes significantly more complex or needs to be shared across many independent components.

6.  **Configuration Management**: How should we structure the configuration for:
    *   Model preferences per analysis type
    *   Resource limits and performance tuning
    *   Automatic model management settings

    **Gemini's Answer**: The proposed YAML structure in `prompt3draft_V2.md` (`ai_enhancements.local_llm`) is a good starting point. Expand it to include:
    *   `preferred_models` can be a dictionary mapping analysis types (e.g., `vision`, `text`, `task_generation`) to preferred model names.
    *   `resource_limits` (e.g., `max_cpu_usage`, `max_memory_usage`) and `performance_tuning` (e.g., `quantization_level`, `batch_size`) can be nested under `local_llm_settings`.
    *   `auto_download` and `max_concurrent` are already well-placed.

7.  **Analytics Privacy**: For the predictive analytics running locally:
    *   What data should we store vs process in real-time?
    *   How do we balance accuracy with privacy?
    *   Should we implement differential privacy techniques?

    **Gemini's Answer**:
    *   **Data Storage vs. Real-time Processing**: Store only aggregated, anonymized data for long-term trend analysis. Process raw, sensitive data (e.g., specific mess detections) in real-time and discard immediately after generating insights or tasks.
    *   **Accuracy vs. Privacy**: Focus on privacy-preserving analytics by default. If higher accuracy requires more detailed data, make it an opt-in feature with clear user consent and explanation of data usage.
    *   **Differential Privacy**: While beneficial, differential privacy can add significant complexity and might not be necessary if data is processed locally and discarded. Prioritize strict data minimization and local processing first. If the project scales to shared data or more complex analytics, then explore differential privacy.

### **User Experience Questions:**

8.  **Setup Complexity**: How can we minimize the setup complexity for users?
    *   Should we provide pre-configured Docker containers?
    *   What's the minimum viable local setup?

    **Gemini's Answer**:
    *   **Pre-configured Docker containers**: Absolutely. This is the best way to minimize setup complexity for Home Assistant users, as it encapsulates all dependencies. Provide clear `docker-compose` examples.
    *   **Minimum Viable Local Setup**: The minimum viable setup should involve:
        1.  Ollama installed and running (or a simple script to install it).
        2.  The `aicleaner_v3` addon configured to point to the Ollama instance.
        3.  Automatic model downloading enabled in the addon.

9.  **Performance Expectations**: What should users expect in terms of:
    *   Analysis speed compared to cloud models
    *   Resource usage (CPU, memory, disk)
    *   Model download times and storage requirements

    **Gemini's Answer**:
    *   **Analysis Speed**: Expect local analysis to be slower than cloud models on consumer hardware, especially for larger models. Provide realistic estimates (e.g., "2-5x slower than cloud on a Raspberry Pi 4, comparable on a powerful NUC").
    *   **Resource Usage**: Clearly state the minimum RAM and CPU requirements for different local models. Emphasize that larger models will consume significantly more resources.
    *   **Model Download Times and Storage**: Provide approximate download sizes and times for recommended models. Warn users about the initial download time and disk space requirements.

---

## 5. Answers to Previous Gemini Questions (from Phase 2)

### **From Phase 2 Implementation Summary:**

1.  **✅ Hybrid Prioritization**: The Safety/Hygiene → Aesthetics approach is fully implemented and tested
2.  **✅ Object Database**: 20+ objects implemented, easily extensible for additional types
3.  **✅ Performance Benchmarks**: All targets exceeded significantly (497x cache speedup, 1,153 ops/sec)
4.  **✅ Edge Cases**: Comprehensive error handling and graceful degradation implemented
5.  **✅ Room-Specific Handling**: Kitchen dishes get "Clean and put away", bathroom towels get "Hang", etc.

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

1.  **Gemini**: Please review this refined prompt and provide feedback on:
    *   Technical approach and model recommendations
    *   Performance optimization strategies
    *   Privacy and analytics considerations

2.  **Implementation Priority**: Which Phase 3 task should we tackle first?
    *   3A.1 (Local LLM Client) for immediate local capability?
    *   3A.2 (Model Router) for intelligent routing?
    *   3B.1 (Enhanced Analytics) for improved predictions?

3.  **Resource Planning**: What are the minimum system requirements we should target for local LLM operation?

**Ready to begin Phase 3 implementation upon Gemini's feedback and agreement on approach.**

---

## 9. Questions for Claude:

1.  **Architectural Review**: Given Gemini's answers regarding the Model Router design (integrated into AI Coordinator), do you foresee any challenges or alternative approaches that might offer better long-term scalability or maintainability?
2.  **Testing Strategy**: Based on the proposed local LLM integration and fallback mechanisms, what specific types of integration tests or end-to-end tests would be most crucial to ensure robustness and reliability?
3.  **Deployment Considerations**: Beyond Docker containers, are there any other deployment strategies or tools (e.g., for Home Assistant Add-on distribution, or for managing Ollama instances) that we should investigate for simplifying user setup and ongoing maintenance?
4.  **Documentation Focus**: What are the absolute critical pieces of documentation that need to be prioritized for users, especially concerning local LLM setup, configuration, and troubleshooting?
5.  **Gamification & Analytics**: Do you have any initial thoughts on how to best design the gamification elements and predictive analytics to maximize user engagement and provide actionable insights, considering the privacy-first approach?
