# AICleaner - Gemini Review and Claude Implementation Plan

## 1. Gemini's Review of Priority 3

I have reviewed the final prompt for Priority 3, which focuses on implementing an adaptive monitoring frequency in the `SystemMonitor`. The goal is to make the monitoring system more intelligent and resource-efficient by adjusting the check frequency based on system stability.

### Key Requirements:

- The `SystemMonitor`'s background loop must dynamically adjust its own check frequency.
- The system starts with a default frequency (e.g., 60 seconds).
- A `stability_counter` is maintained.
- If a check passes and key metrics are within normal bounds, the counter is incremented.
- If the counter exceeds a threshold (e.g., 10 stable checks), the monitoring frequency is decreased (up to a maximum of 300 seconds).
- If a check detects an anomaly, the counter is reset, and the monitoring frequency is increased (down to a minimum of 30 seconds).
- More advanced concepts like predictive anomaly detection and smart alert escalation are to be deferred.

## 2. Gemini's Actions (To be Verified by Claude)

I have already completed the following tasks, which should be reviewed and verified by Claude before proceeding:

- **Health Check Service:** Implemented the `aicleaner.run_health_check` service in `SystemMonitor` and exposed it via `HAClient`.
- **Home Assistant Integration:** Created the necessary Home Assistant sensors (`sensor.aicleaner_health_score`, `sensor.aicleaner_average_response_time`, `binary_sensor.aicleaner_health_alert`) and services (`aicleaner.run_health_check`, `aicleaner.apply_performance_profile`).
- **Alerting Strategy:** Implemented the dual-mode alerting logic in `SystemMonitor` for critical and performance-related issues.

## 3. Claude's Implementation Plan

Based on my review, here is the recommended implementation plan for Claude:

### Task 1: Verify Gemini's Work

- Review the changes made to `core/system_monitor.py` and `integrations/ha_client.py` to ensure they are correct and meet the requirements of Priority 2.
- Run the tests to confirm that all existing and new functionality is working as expected.

### Task 2: Implement Adaptive Monitoring Frequency

- **Modify `core/system_monitor.py`:**
    - Add a `_monitoring_loop` method to `SystemMonitor` that contains the adaptive frequency logic.
    - Update the `start_monitoring` method to call `_monitoring_loop` as a background task.
    - Implement the `stability_counter` and the logic for increasing and decreasing the monitoring frequency.

### Task 3: Test the Implementation

- **Create `tests/test_adaptive_monitoring.py`:**
    - Write a test that verifies the adaptive frequency logic.
    - The test should simulate both stable and unstable system states and assert that the monitoring frequency changes accordingly.

### Task 4: Create Review File

- **Create `REVIEW_PRIORITY_3_COMPLETE.md`:**
    - Provide a code snippet of the final implementation of the adaptive monitoring loop.
    - Explain how the adaptive behavior was tested.
    - Include example log outputs demonstrating the frequency changes.
    - Confirm that all tests pass.
