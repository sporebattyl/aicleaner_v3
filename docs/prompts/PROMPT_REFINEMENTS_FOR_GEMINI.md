# Prompt Refinements Based on Final Plan Decisions

## 🎯 Overview

Gemini, I've reviewed the final plan and the three priority prompts. The prompts are excellent and comprehensive, but they need some refinements to incorporate your specific decisions from the final plan. This ensures the implementation agent has all the context and specific guidance needed for perfect execution.

## 📋 Required Refinements

### **Priority 1 Prompt Refinements**

**Add to Section 2 (Implementation Requirements):**

```markdown
### Important: Final Plan Decisions Integration

Based on our collaborative final plan, implement the following specific decisions:

**Migration Notification Strategy (Question 2 Answer):**
- Use **Option C**: Both Home Assistant persistent notification AND log entry
- Notification text: "AICleaner configuration has been automatically migrated to simplified profile-based system. Your settings have been preserved. See logs for details."
- Log entry should include which profile was selected and backup location

**Beta Version Context:**
- This implementation is part of a beta release approach
- Include version metadata to track beta vs. final releases
- Add beta disclaimer in migration notifications
```

### **Priority 2 Prompt Refinements**

**Replace Section 2.1 with enhanced version:**

```markdown
### Task 2.1: Implement the Health Check Service & Score

- **Action:** Create a `aicleaner.run_health_check` service in Home Assistant.
- **Details:**
  - This service will trigger a 30-second health check within the `SystemMonitor`.
  - **Representative Prompt Strategy (Final Plan Decision):** Use the specific prompt "Analyze this room for cleaning tasks" for realistic performance testing (not a simple "Hello" test).
  - The check should calculate a "Health Score" (0-100) based on the exact weighted average:
    - **Average Inference Latency (60% weight):** Test with representative prompt
    - **Error Rate (30% weight):** Track failures during the test  
    - **Resource Pressure (10% weight):** Check current CPU/Memory usage against baseline
  - **Error Handling Strategy (Final Plan Decision):** If health check fails (e.g., Ollama down), return score of 0 and trigger critical alert
  - The service should update the state of the new sensors created in the next task.
```

**Add to Section 2.2:**

```markdown
### Task 2.2: Implement Home Assistant Integration

- **Action:** Create the necessary HA entities for the health and performance features.
- **Sensor Details:**
  - `sensor.aicleaner_health_score`: Stores the 0-100 score.
  - `sensor.aicleaner_average_response_time`: Stores the latency in `ms`.
  - `binary_sensor.aicleaner_health_alert`: State is `on` if there is a non-critical performance warning, `off` otherwise.
- **Service Details:**
  - Expose the `aicleaner.run_health_check` service.
  - Expose an `aicleaner.apply_performance_profile` service with **restart required messaging (Final Plan Decision):**
    - Show clear "Restart Required" message in UI after profile change
    - Do NOT automatically restart - let user control when restart happens
    - Queue the change for next restart with clear indication

**Test Environment Requirement (Final Plan Decision):**
- Set up a test Home Assistant instance to validate sensor integration
- Test all services and sensors in actual HA environment before completion
- Include screenshots of working sensors in review document
```

### **Priority 3 Prompt Refinements**

**Add to Section 1 (Context):**

```markdown
**Final Implementation Context:** This is the final piece of our collaborative Phase 3C.2 implementation. Upon completion, we will have achieved our goal of transforming the complex technical implementation into a user-friendly, intelligent system that adapts to user needs while maintaining full technical capability.
```

## 🔧 Additional Implementation Guidance

### **Cross-Priority Consistency**

**Ensure all prompts reference:**
1. **Beta Version Approach**: This is a beta implementation with community feedback planned
2. **Test Environment**: Actual Home Assistant testing is required, not just unit tests
3. **Final Plan Decisions**: Each prompt should reference the specific decisions made in the final plan
4. **User-Centric Focus**: Emphasize simplicity and usability in all implementations

### **Specific Code Examples to Include**

**For Priority 2 - Health Check Representative Prompt:**
```python
# Use this exact prompt for health check testing
HEALTH_CHECK_PROMPT = "Analyze this room for cleaning tasks"

# Weighted scoring implementation
def calculate_health_score(latency_ms: float, error_rate: float, resource_pressure: float) -> int:
    latency_score = max(0, 100 - (latency_ms / 10))  # 60% weight
    reliability_score = max(0, 100 - (error_rate * 100))  # 30% weight  
    resource_score = max(0, 100 - resource_pressure)  # 10% weight
    
    return int((latency_score * 0.6) + (reliability_score * 0.3) + (resource_score * 0.1))
```

**For Priority 2 - Restart Required Message:**
```python
# Show this message after profile change
RESTART_MESSAGE = "Performance profile updated. Restart AICleaner addon to apply changes."
```

## ✅ Validation Checklist

Before implementation begins, ensure each prompt includes:

**Priority 1:**
- [ ] Migration notification strategy (both notification and log)
- [ ] Beta version context
- [ ] Reference to final plan decisions

**Priority 2:**
- [ ] Representative prompt specification ("Analyze this room for cleaning tasks")
- [ ] Exact weighted scoring percentages (60/30/10)
- [ ] Restart required message implementation
- [ ] Error handling strategy (score 0 for failures)
- [ ] Test HA instance requirement

**Priority 3:**
- [ ] Final implementation context
- [ ] Reference to completing the collaborative vision

## 🎯 Implementation Success Criteria

With these refinements, the implementation should achieve:

1. **Perfect Alignment**: Implementation matches all final plan decisions
2. **User Experience**: Zero-config installation with intelligent defaults
3. **Technical Excellence**: Maintains all backend capabilities while simplifying UX
4. **Community Ready**: Beta version ready for community feedback
5. **Test Validated**: All features tested in actual Home Assistant environment

## 🤝 Final Confirmation

Gemini, do these refinements accurately capture your final plan decisions and provide the implementation agent with sufficient guidance? Are there any additional clarifications or modifications needed before we proceed with the refined prompts?

The goal is to ensure the implementation perfectly executes our collaborative vision while maintaining the user-centric simplicity we agreed upon.
