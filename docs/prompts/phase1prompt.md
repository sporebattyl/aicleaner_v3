## 🤖 **Implementation Task: AI Cleaner Refactoring (Phase 1A)**

**Context:** You are implementing Phase 1A of the AI-powered Home Assistant addon for camera feed monitoring and cleaning task creation. This is a refactoring task, not a rewrite. Claude and Gemini have completed extensive collaborative design work and finalized the technical architecture.

**Objective:** Extract the `ZoneAnalyzer` class and implement async queue management with state persistence as specified in the project design.

### **📚 Required Documentation References:**

**CRITICAL**: Before beginning implementation, review these documentation sources:

1. **Home Assistant Developer Documentation:**
   - Primary: https://developers.home-assistant.io/
   - Addon Development: https://developers.home-assistant.io/docs/add-ons/
   - Integration Standards: https://developers.home-assistant.io/docs/creating_integration/

2. **Home Assistant User Documentation:**
   - Core Documentation: https://www.home-assistant.io/docs/
   - Todo Lists: https://www.home-assistant.io/integrations/local_todo/
   - MQTT Integration: https://www.home-assistant.io/integrations/mqtt/

3. **Project Design Document:**
   - **MUST READ**: `projectdesign.md` in this directory
   - Contains complete Phase 1A specifications and success criteria
   - Provides context for future phases and overall architecture

### **🎯 Project Design Context:**

This implementation is **Phase 1A** of a comprehensive 3-phase refactoring project:
- **Phase 1**: Core Refactoring and Asynchronous Processing
- **Phase 2**: Advanced AI Features and Integration
- **Phase 3**: System Optimization and Deployment

**Your work establishes the foundation** for all subsequent phases. The modular architecture you create will support future AI enhancements, gamification, and predictive analytics.

---

### **Key Deliverables & Specifications:**

1.  **Modular Structure:** Create the following directory structure:
    ```
    /addons/aicleaner_v3/
    ├── core/
    │   ├── __init__.py
    │   ├── analyzer.py          # ZoneAnalyzer (async queue design)
    │   ├── scheduler.py         # Zone scheduling logic
    │   ├── state_manager.py     # File-based state persistence
    │   └── performance_monitor.py  # Configurable HA sensor updates
    ├── integrations/
    │   ├── __init__.py
    │   ├── ha_client.py         # Home Assistant API wrapper
    │   ├── mqtt_manager.py      # MQTT discovery & updates
    │   └── gemini_client.py     # Gemini API with retry logic
    ```

2.  **`ZoneAnalyzer` Implementation:**
    *   **Hybrid Queue:** Use `asyncio.PriorityQueue` for analysis requests and `asyncio.Semaphore` for resource limiting.
    *   **Priority System:** Implement the agreed-upon priority: Manual (1), High Messiness (2), Scheduled (3), Retry (4).
    *   **Configuration:** Support global concurrent analysis limits with per-zone overrides.
    *   **Worker Pool:** Implement configurable concurrent analysis workers.

3.  **State Management:**
    *   Implement a 9-state progression tracking system: `IMAGE_CAPTURED` → `LOCAL_ANALYSIS_COMPLETE` → `GEMINI_API_CALL_INITIATED` → `GEMINI_API_CALL_SUCCESS` → `TASK_GENERATION_COMPLETE` → `HA_TODO_CREATION_INITIATED` → `HA_TODO_CREATION_SUCCESS` → `NOTIFICATIONS_SENT` → `CYCLE_COMPLETE`.
    *   Ensure **file-based persistence** for state, with HA entity attributes used for display only.

4.  **Performance Monitoring:**
    *   Integrate configurable sensor updates for `analysis_duration`, `api_calls_today`, and `cost_estimate_today`.
    *   Ensure resource management and idempotent operations.

---

### **Critical Constraints & Requirements:**

*   **Preserve ALL existing functionality** from `/addons/aicleaner_v3/aicleaner.py`. This is a refactoring, not a rewrite.
*   **Follow Home Assistant Standards**: Use the documentation references above to ensure compliance with current HA addon development practices.
*   **Apply TDD Principles**: Use Test-Driven Development throughout - write tests first, then implement functionality.
*   **Use AAA Testing Pattern**: Structure all tests with Arrange, Act, Assert methodology for clarity and maintainability.
*   **Implement Component-Based Design**: Create modular, loosely-coupled components with clear interfaces and single responsibilities.
*   Maintain compatibility with `config.yaml` and existing user settings.
*   Integrate seamlessly with the Home Assistant addon architecture (MQTT, notifications, etc.).
*   Implement robust error handling, including retry logic.
*   Use `async/await` patterns throughout.
*   Implement proper logging and comprehensive docstrings.
*   **Test thoroughly** to prevent regressions.

### **🔍 Implementation Validation:**

Before submitting your work, verify against these checkpoints:

1. **Documentation Compliance**: Code follows current HA addon standards from developers.home-assistant.io
2. **Project Design Alignment**: Implementation matches specifications in `projectdesign.md`
3. **TDD Implementation**: All new functionality has corresponding tests written first
4. **AAA Test Structure**: All tests follow Arrange-Act-Assert pattern with clear sections
5. **Component Design**: Each module has single responsibility, clear interfaces, and loose coupling
6. **Functionality Preservation**: All existing features continue to work without regression
7. **Architecture Foundation**: Modular structure supports future Phase 2 and Phase 3 enhancements
8. **Integration Standards**: MQTT, notifications, and HA API usage follows current best practices

### **📋 Success Criteria (from Project Design):**

*   ✅ Addon starts without errors after refactoring
*   ✅ All existing zones continue to function normally
*   ✅ New async queue system handles concurrent analysis
*   ✅ State persistence works across addon restarts
*   ✅ Performance sensors update correctly in Home Assistant
*   ✅ Configuration options work as before
*   ✅ All existing functionality from `aicleaner.py` is preserved

---

**Start implementation immediately. Focus on clean, production-ready code that adheres strictly to these specifications and follows current Home Assistant development standards.**