# Project Design Document: AI Cleaner Addon Refactoring

This document outlines the comprehensive project plan for refactoring and enhancing the AI-powered Home Assistant addon. It details the various phases, their objectives, key components, and success criteria, providing a roadmap for future development.

## Project Overview

The primary goal of this project is to refactor the existing AI Cleaner Home Assistant addon to improve its modularity, scalability, performance, and robustness. This involves extracting core functionalities into dedicated modules, implementing asynchronous processing, enhancing state management, and integrating advanced monitoring capabilities.

## Development Principles

**All phases of this project must adhere to these core development principles:**

### **Test-Driven Development (TDD)**
- Write tests first, then implement functionality
- Ensure comprehensive test coverage for all new components
- Use tests as living documentation of expected behavior
- Refactor with confidence knowing tests will catch regressions

### **AAA Testing Pattern**
- Structure all tests with **Arrange, Act, Assert** methodology
- **Arrange**: Set up test data, mocks, and initial conditions
- **Act**: Execute the functionality being tested
- **Assert**: Verify the expected outcomes and side effects
- Maintain clear separation between test phases for readability

### **Component-Based Design**
- Create modular, loosely-coupled components with clear interfaces
- Follow Single Responsibility Principle - each component has one clear purpose
- Design for dependency injection and testability
- Ensure components can be developed, tested, and maintained independently
- Use composition over inheritance where appropriate

## Phase 1: Core Refactoring and Asynchronous Processing

**Objective:** Establish a robust, modular, and asynchronous core for the AI Cleaner addon, focusing on efficient zone analysis and state management.

### Phase 1A: Core Async Refactoring (Currently Underway)

**Objective:** Extract the `ZoneAnalyzer` class and implement the async queue management with state persistence.

**Key Components:**
*   **Modular Structure:**
    *   `/addons/aicleaner_v3/core/`: Contains core logic (analyzer, scheduler, state manager, performance monitor).
    *   `/addons/aicleaner_v3/integrations/`: Contains external integrations (HA client, MQTT manager, Gemini client).
*   **`ZoneAnalyzer` (in `core/analyzer.py`):**
    *   **Hybrid Queue:** `asyncio.PriorityQueue` for analysis requests.
    *   **Resource Limiting:** `asyncio.Semaphore` for concurrent analysis control.
    *   **Priority System:** Implement priority scoring (Manual: 1, High Messiness: 2, Scheduled: 3, Retry: 4).
    *   **Configuration:** Support global concurrent analysis limits with per-zone overrides.
    *   **Worker Pool:** Configurable concurrent analysis workers.
*   **State Management (in `core/state_manager.py`):**
    *   **9-State Progression:** Implement tracking for `IMAGE_CAPTURED` → `LOCAL_ANALYSIS_COMPLETE` → `GEMINI_API_CALL_INITIATED` → `GEMINI_API_CALL_SUCCESS` → `TASK_GENERATION_COMPLETE` → `HA_TODO_CREATION_INITIATED` → `HA_TODO_CREATION_SUCCESS` → `NOTIFICATIONS_SENT` → `CYCLE_COMPLETE`.
    *   **Persistence:** File-based storage for state (`/data/aicleaner_state.json` by default).
    *   **HA Display:** HA entity attributes used for displaying current state (not for persistence).
*   **Performance Monitoring (in `core/performance_monitor.py`):**
    *   **HA Sensors:** Integrate configurable sensor updates for `analysis_duration`, `api_calls_today`, and `cost_estimate_today`.
    *   **Resource Management:** Ensure efficient use of resources.
    *   **Idempotent Operations:** Design for reliable retry behavior.
*   **Integration Points:** Update `aicleaner.py` to utilize the new modular components.

**Success Criteria:**
*   **Functionality**: Addon starts without errors after refactoring.
*   **Compatibility**: All existing zones continue to function normally.
*   **Performance**: New async queue system handles concurrent analysis.
*   **Persistence**: State persistence works across addon restarts.
*   **Integration**: Performance sensors update correctly in Home Assistant.
*   **Configuration**: Configuration options work as before.
*   **Preservation**: All existing functionality from `aicleaner.py` is preserved.
*   **Testing**: Comprehensive test suite with TDD implementation and AAA structure.
*   **Architecture**: Component-based design with clear interfaces and single responsibilities.
*   **Quality**: Code follows Home Assistant development standards and best practices.

### Phase 1B: Enhanced Error Recovery and Configuration

**Objective:** Implement robust error handling, retry mechanisms, and flexible configuration options.

**Key Components:**
*   **Retry Logic:** Implement exponential backoff and circuit breaker patterns for API calls and state transitions.
*   **Fallback Strategies:** Define and implement fallback mechanisms for failed analyses (e.g., default actions, notification of failure).
*   **Configuration Manager Refinement:** Enhance `configuration_manager.py` to handle new global and per-zone settings, including dynamic updates.
*   **User Feedback:** Provide clear error messages and status updates to the user via HA notifications or logs.

**Success Criteria:**
*   Addon gracefully recovers from transient errors without crashing.
*   Failed operations are retried according to defined policies.
*   Users can easily configure new parameters (e.g., retry attempts, timeouts).
*   Error notifications are informative and actionable.

## Phase 2: Advanced AI Features and Integration

**Objective:** Integrate and optimize advanced AI capabilities, leveraging the new modular architecture.

### Phase 2A: Multi-Model AI and Scene Understanding

**Objective:** Enhance the AI analysis capabilities by integrating multiple AI models and improving scene understanding.

**Key Components:**
*   **Multi-Model AI (in `aicleaner/multi_model_ai.py`):**
    *   Implement logic to dynamically select and utilize different AI models based on context or configuration.
    *   Develop a unified interface for interacting with various AI services (e.g., Gemini, other vision APIs).
*   **Scene Understanding (in `aicleaner/scene_understanding.py`):**
    *   Develop modules for more granular object detection, spatial reasoning, and context awareness within camera feeds.
    *   Integrate with the `ZoneAnalyzer` to provide richer analysis results.

**Success Criteria:**
*   Addon can utilize multiple AI models for analysis.
*   Improved accuracy and detail in mess detection and scene interpretation.
*   Seamless integration of new AI capabilities into the analysis pipeline.

### Phase 2B: Local LLM Integration and Offline Capability

**Objective:** Enable the addon to run completely locally using self-hosted LLMs like Ollama, providing privacy, cost savings, and independence from external APIs.

**Key Components:**
*   **Local LLM Client (in `integrations/ollama_client.py`):**
    *   Implement Ollama API integration for local LLM communication
    *   Support for multiple local models (llama2, codellama, mistral, etc.)
    *   Model management and automatic downloading capabilities
*   **Vision Model Integration (in `core/local_vision.py`):**
    *   Integrate local vision models (LLaVA, Bakllava, etc.) for image analysis
    *   Implement image preprocessing and optimization for local models
    *   Support for multimodal prompts combining text and images
*   **Intelligent Model Router (in `core/model_router.py`):**
    *   Smart routing between Gemini API, local LLMs, and local vision models
    *   Fallback strategies: Local → Cloud → Cached responses
    *   Performance monitoring and automatic model selection based on availability
*   **Local Model Manager (in `core/local_model_manager.py`):**
    *   Automatic model downloading and updates
    *   Model performance monitoring and optimization
    *   Resource usage management (CPU, memory, disk space)
*   **Prompt Engineering for Local Models:**
    *   Optimize prompts specifically for local LLM capabilities
    *   Implement structured output parsing for consistent task generation
    *   Create model-specific prompt templates

**Configuration Enhancements:**
*   **Model Selection Options:**
    ```yaml
    ai_provider: "auto"  # auto, gemini, ollama, local_only
    ollama_host: "localhost:11434"
    preferred_models:
      vision: "llava:13b"
      text: "mistral:7b"
      fallback: "gemini"
    ```
*   **Performance Tuning:**
    ```yaml
    local_model_settings:
      max_tokens: 500
      temperature: 0.1
      timeout: 120  # seconds
      concurrent_requests: 1
    ```

**Success Criteria:**
*   Addon can operate completely offline using local LLMs
*   Seamless fallback between local and cloud models
*   Comparable analysis quality between local and cloud models
*   Automatic model management with minimal user intervention
*   Significant cost reduction for users with high usage
*   Enhanced privacy with no external API calls when using local-only mode

### Phase 2C: Gamification and Predictive Analytics

**Objective:** Introduce gamification elements and predictive analytics to enhance user engagement and proactive cleaning.

**Key Components:**
*   **Gamification (in `aicleaner/gamification.py`):**
    *   Implement a system for tracking user cleaning habits, streaks, and achievements.
    *   Integrate with HA sensors/attributes to display gamification metrics.
    *   Develop notification strategies for gamification events.
*   **Predictive Analytics (in `aicleaner/predictive_analytics.py`):**
    *   Analyze historical data (mess patterns, cleaning times) to predict future cleaning needs.
    *   Generate proactive cleaning suggestions or schedule tasks based on predictions.
    *   Leverage local LLM capabilities for privacy-preserving analytics

**Success Criteria:**
*   Users are more engaged with cleaning tasks through gamification.
*   Addon can accurately predict future cleaning requirements.
*   Proactive cleaning suggestions lead to a cleaner environment.
*   Analytics run locally without compromising user privacy.

## Phase 3: System Optimization and Deployment

**Objective:** Optimize the addon for performance, resource usage, ease of deployment, and local LLM efficiency.

### Phase 3A: Performance Tuning and Resource Management

**Objective:** Identify and resolve performance bottlenecks, and optimize resource consumption.

**Key Components:**
*   **Profiling:** Use profiling tools to identify CPU, memory, and I/O hotspots.
*   **Code Optimization:** Refactor critical sections for improved efficiency.
*   **Resource Monitoring:** Implement detailed internal monitoring of resource usage.
*   **Image Processing Optimization:** Optimize image capture, resizing, and transmission.
*   **Local LLM Optimization:**
    *   Optimize model loading and memory management for local LLMs
    *   Implement model quantization and optimization techniques
    *   Create efficient batching strategies for multiple zone analysis
    *   Optimize prompt engineering for faster local model responses

**Success Criteria:**
*   Reduced CPU and memory footprint for both cloud and local operations.
*   Faster analysis times with optimized local model performance.
*   Stable performance under heavy load with local LLM resource management.
*   Efficient local model switching and memory usage.

### Phase 3B: Packaging, Testing, and Documentation

**Objective:** Prepare the addon for wider distribution through comprehensive testing and documentation.

**Key Components:**
*   **Automated Testing:** Expand unit, integration, and end-to-end tests to cover all new and refactored components using TDD and AAA patterns.
*   **Test Quality Assurance:** Ensure all tests follow AAA structure and provide comprehensive coverage.
*   **Component Validation:** Verify all components follow single responsibility principle and have clear interfaces.
*   **CI/CD Integration:** Set up continuous integration and deployment pipelines with automated testing.
*   **Documentation:** Update `README.md`, `DOCS.md`, and create detailed API documentation.
*   **Packaging:** Ensure the addon is correctly packaged for Home Assistant distribution.

**Success Criteria:**
*   High test coverage with minimal regressions using TDD methodology.
*   All tests follow AAA pattern for clarity and maintainability.
*   Component-based architecture with clear separation of concerns.
*   Automated build and deployment process with quality gates.
*   Clear and comprehensive documentation for users and developers.
*   Smooth installation and operation for end-users.

---

This project design document will serve as a living guide, subject to updates and refinements as development progresses.
