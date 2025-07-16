# Phase 3 Development Prompt (v4 - FINAL): Local LLM Integration & Advanced Features

## Context: Building on Phase 2 Success + Gemini Collaboration

**Phase 2 Status**: ✅ **COMPLETE** - 87 tests passing, performance exceeding targets by 10-500x
- AI Coordinator implemented with orchestration capabilities
- Object database with hybrid prioritization (Safety/Hygiene → Aesthetics)
- Enhanced task generation with room-specific intelligence
- Comprehensive caching and performance optimization

**Gemini Collaboration**: ✅ **COMPLETE** - All technical questions answered and approach validated

---

## 1. High-Level Objective

**Goal**: Transform the `aicleaner_v3` system into a **privacy-first, cost-effective, and fully autonomous cleaning assistant** by implementing local LLM capabilities while maintaining cloud fallback options.

## 2. Implementation Plan (Validated & Refined)

### **Phase 3A: Local LLM Integration (Priority 1)**

#### **Task 3A.1: Local LLM Client Implementation**
**File**: `integrations/ollama_client.py`

**Recommended Models (per Gemini):**
- **Vision**: `llava:13b` or `bakllava:7b` (balance of capability/resources)
- **Text/Tasks**: `mistral:7b` (optimal for cleaning task generation)
- **Fallback**: `llama2:7b` (general text tasks)

**Key Implementation Details:**
```python
class OllamaClient:
    async def analyze_image_local(self, image_path: str, model: str, prompt: str) -> Dict[str, Any]:
        # Implement 4-bit/8-bit quantization for memory efficiency
        # Use concise, explicit prompts optimized for local models
        
    async def generate_tasks_local(self, analysis: str, context: Dict) -> List[Dict]:
        # Batch multiple zone analysis if Ollama API supports it
        # Implement confidence scoring for quality checks
        
    async def check_model_availability(self, model: str) -> bool:
        # Health checks and model validation
        
    async def download_model(self, model: str) -> bool:
        # Automatic model management with progress tracking
```

**Configuration (Enhanced):**
```yaml
ai_enhancements:
  local_llm:
    enabled: true
    ollama_host: "localhost:11434"
    preferred_models:
      vision: "llava:13b"
      text: "mistral:7b"
      task_generation: "mistral:7b"
      fallback: "gemini"
    resource_limits:
      max_cpu_usage: 80
      max_memory_usage: 4096  # MB
    performance_tuning:
      quantization_level: 4  # 4-bit quantization
      batch_size: 1
      timeout_seconds: 120
    auto_download: true
    max_concurrent: 1
```

#### **Task 3A.2: Model Router Integration**
**File**: Enhance `ai/ai_coordinator.py` (per Gemini recommendation)

**Fallback Criteria (per Gemini):**
1. Local model unavailability (Ollama not running, model not downloaded)
2. Local model failure (inference error, timeout)
3. Low confidence score on local output
4. Explicit user preference for cloud models

**Implementation Strategy:**
```python
class AICoordinator:
    async def _select_and_route_model(self, priority: str, analysis_type: str) -> Tuple[str, str]:
        # Returns (model_name, provider) where provider is 'local' or 'cloud'
        # Implement confidence scoring and automatic fallback
```

#### **Task 3A.3: Local Model Manager**
**File**: `core/local_model_manager.py`

**Key Features:**
- Dynamic model loading/unloading based on demand
- Resource monitoring and optimization
- Automatic model updates and health checks
- Performance metrics tracking

### **Phase 3B: Advanced Analytics & Gamification (Priority 2)**

#### **Task 3B.1: Privacy-Preserving Analytics**
**File**: Enhance `ai/predictive_analytics.py`

**Data Strategy (per Gemini):**
- **Store**: Only aggregated, anonymized data for trends
- **Process**: Raw sensitive data in real-time, discard immediately
- **Privacy**: Local processing by default, opt-in for detailed analytics

#### **Task 3B.2: Gamification System**
**File**: Enhance `gamification/gamification.py`

**Core Features:**
- Cleaning streaks and achievement badges
- Progress tracking in Home Assistant
- Weekly/monthly challenges
- Privacy-first design (all data local)

### **Phase 3C: Deployment & Optimization (Priority 3)**

#### **Task 3C.1: Docker & Setup Simplification**
**Deliverables:**
- Pre-configured Docker containers with Ollama
- `docker-compose` examples for easy setup
- Automatic Ollama installation scripts
- Clear setup documentation

**Minimum Viable Setup:**
1. Ollama installed and running
2. AICleaner addon configured to point to Ollama
3. Automatic model downloading enabled

#### **Task 3C.2: Performance Optimization**
**Focus Areas:**
- 4-bit/8-bit model quantization
- Dynamic model loading/unloading
- Batch processing optimization
- Prompt engineering for local models

---

## 3. Answers to Gemini's Questions for Claude

### **1. Architectural Review - Model Router Design**
**Answer**: Gemini's recommendation to integrate the Model Router into the AI Coordinator is sound for this scope. This approach:
- ✅ **Simplifies architecture** - avoids inter-service communication overhead
- ✅ **Maintains cohesion** - keeps AI orchestration logic centralized
- ✅ **Enables easy testing** - single component to mock and test
- ⚠️ **Future consideration**: If routing logic becomes complex, we can extract it later

**Alternative for future scalability**: Consider a Strategy pattern implementation within the AI Coordinator for different routing strategies.

### **2. Testing Strategy - Critical Integration Tests**
**Priority Test Types:**
1. **Fallback Reliability Tests**: Simulate Ollama failures, network issues, model unavailability
2. **Performance Comparison Tests**: Validate local vs cloud analysis quality and speed
3. **Resource Constraint Tests**: Test behavior under memory/CPU limits
4. **End-to-End Workflow Tests**: Full analysis pipeline with local models
5. **Configuration Validation Tests**: Test all local LLM configuration scenarios

**Test Implementation:**
```python
# tests/test_local_llm_integration.py
class TestLocalLLMIntegration:
    async def test_ollama_fallback_on_failure(self):
        # Simulate Ollama server down, verify cloud fallback
    
    async def test_model_quality_consistency(self):
        # Compare local vs cloud analysis results
    
    async def test_resource_limit_handling(self):
        # Test behavior under memory constraints
```

### **3. Deployment Considerations**
**Recommended Strategies:**
1. **Home Assistant Add-on Store**: Package as official HA add-on with Ollama integration
2. **HACS Integration**: Provide HACS-compatible installation for advanced users
3. **Supervisor Add-on**: Create companion Ollama supervisor add-on for HA OS
4. **Documentation Hub**: Comprehensive setup guides for different HA installation types

**Tools to Investigate:**
- **Portainer**: For Docker container management in HA
- **HA Supervisor API**: For add-on lifecycle management
- **MQTT Discovery**: For automatic HA entity creation

### **4. Documentation Focus - Critical Priorities**
**Tier 1 (Essential):**
1. **Quick Start Guide**: 5-minute setup for Docker users
2. **Troubleshooting Guide**: Common Ollama/local model issues
3. **Configuration Reference**: Complete config.yaml documentation
4. **Performance Tuning**: Hardware requirements and optimization tips

**Tier 2 (Important):**
1. **Architecture Overview**: How local/cloud routing works
2. **Model Selection Guide**: Which models for different use cases
3. **Privacy Guide**: What data is processed locally vs cloud

### **5. Gamification & Analytics Design**
**Engagement Strategy:**
1. **Progressive Disclosure**: Start simple, unlock advanced features
2. **Meaningful Metrics**: Focus on cleanliness improvement, not just activity
3. **Social Features**: Family/household leaderboards (optional)
4. **Seasonal Challenges**: Align with real cleaning needs (spring cleaning, etc.)

**Privacy-First Analytics:**
1. **Local Aggregation**: All personal data stays on device
2. **Opt-in Sharing**: Anonymous trend data for community insights
3. **Transparent Metrics**: Clear explanation of what's tracked and why

---

## 4. Success Criteria & Validation

### **Functional Requirements:**
- [ ] Addon operates offline using local LLMs with automatic fallback
- [ ] Analysis quality comparable between local and cloud (within 10% accuracy)
- [ ] Automatic model management with zero user intervention
- [ ] Privacy-first analytics with local processing

### **Performance Requirements:**
- [ ] Local analysis within 2x cloud model time (per Gemini expectations)
- [ ] Memory usage under 4GB for recommended models
- [ ] Model switching under 30 seconds
- [ ] 95% uptime for local model availability

### **Quality Requirements:**
- [ ] Maintain 100% test pass rate (current: 87 tests)
- [ ] TDD and AAA testing principles for all new code
- [ ] Component-based design with clear interfaces
- [ ] Comprehensive documentation for setup and troubleshooting

---

## 5. Implementation Priority & Timeline

### **Phase 3A (Weeks 1-3): Local LLM Foundation**
1. **Week 1**: Ollama client implementation and basic integration
2. **Week 2**: Model router integration into AI Coordinator
3. **Week 3**: Local model manager and resource optimization

### **Phase 3B (Weeks 4-5): Advanced Features**
1. **Week 4**: Privacy-preserving analytics enhancement
2. **Week 5**: Gamification system implementation

### **Phase 3C (Week 6): Deployment & Polish**
1. **Week 6**: Docker containers, documentation, final testing

---

## 6. Risk Assessment & Mitigation

### **High-Risk Areas:**
1. **Local Model Performance**: May be significantly slower than cloud
   - **Mitigation**: Set realistic expectations, provide performance tuning guides
2. **Setup Complexity**: Ollama installation may be challenging for some users
   - **Mitigation**: Pre-configured Docker containers, automated scripts
3. **Resource Consumption**: Local models may overwhelm low-end hardware
   - **Mitigation**: Clear hardware requirements, automatic resource monitoring

### **Medium-Risk Areas:**
1. **Model Compatibility**: Ollama API changes may break integration
   - **Mitigation**: Version pinning, compatibility testing
2. **Fallback Reliability**: Cloud fallback may not work seamlessly
   - **Mitigation**: Comprehensive fallback testing, user feedback loops

---

## 7. Ready for New Agent Handoff

### **✅ Readiness Assessment:**

1. **Scope Clarity**: ✅ Clear objectives and deliverables defined
2. **Technical Specifications**: ✅ Detailed implementation requirements with Gemini validation
3. **Architecture Decisions**: ✅ Key architectural choices made and justified
4. **Success Criteria**: ✅ Measurable functional, performance, and quality requirements
5. **Risk Mitigation**: ✅ Identified risks with mitigation strategies
6. **Timeline**: ✅ Realistic 6-week implementation plan
7. **Testing Strategy**: ✅ Comprehensive testing approach defined
8. **Documentation Plan**: ✅ Clear documentation priorities established

### **🎯 This prompt is READY for handoff to a new Claude agent.**

**Handoff Package Includes:**
- Complete technical specifications validated by Gemini
- Detailed implementation plan with priorities
- Comprehensive testing strategy
- Risk assessment and mitigation plans
- Clear success criteria and timeline
- Foundation of 87 passing tests to build upon

**New Agent Instructions:**
1. Start with Phase 3A.1 (Ollama Client Implementation)
2. Follow TDD principles with AAA testing structure
3. Maintain 100% test pass rate throughout implementation
4. Refer to Phase 2 implementation for architectural patterns
5. Validate each milestone against success criteria before proceeding
