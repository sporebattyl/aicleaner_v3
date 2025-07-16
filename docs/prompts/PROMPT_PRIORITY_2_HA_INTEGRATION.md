# AICleaner Implementation Prompt: Priority 2 - User-Facing Features

## 1. Context & Objective

**Background:** The core architectural simplification from Priority 1 is complete. The addon now has a unified `SystemMonitor` and a simple, profile-based configuration system (`inference_tuning`).

**Your Objective:** Your task is to build the user-facing features in Home Assistant that expose the power of the new `SystemMonitor`. This involves creating a simple health check service, corresponding sensors, and a clear alerting strategy.

---

## 2. Implementation Requirements

### Task 2.1: Implement the Health Check Service & Score

- **Action:** Create a `aicleaner.run_health_check` service in Home Assistant.
- **Details:**
  - This service will trigger a 30-second health check within the `SystemMonitor`.
  - The check should calculate a "Health Score" (0-100) based on the weighted average we agreed upon:
    - **Average Inference Latency (60% weight):** Use a representative prompt (e.g., "Analyze this room for cleaning tasks") to test.
    - **Error Rate (30% weight):** Track failures during the test.
    - **Resource Pressure (10% weight):** Check current CPU/Memory usage against a baseline.
  - The service should update the state of the new sensors created in the next task.

### Task 2.2: Implement Home Assistant Integration

- **Action:** Create the necessary HA entities for the health and performance features.
- **Sensor Details:**
  - `sensor.aicleaner_health_score`: Stores the 0-100 score.
  - `sensor.aicleaner_average_response_time`: Stores the latency in `ms`.
  - `binary_sensor.aicleaner_health_alert`: State is `on` if there is a non-critical performance warning, `off` otherwise. The problem description should be stored as an attribute.
- **Service Details:**
  - Expose the `aicleaner.run_health_check` service.
  - Expose an `aicleaner.apply_performance_profile` service that allows the user to change the active profile (`auto`, `balanced`, etc.) and shows a "Restart Required" message.

### Task 2.3: Implement the Alerting Strategy

- **Action:** Implement the dual-mode alerting logic within the `SystemMonitor`.
- **Details:**
  - **Critical Alerts:** (e.g., Ollama is offline, cannot connect to Home Assistant). These events MUST trigger a **persistent Home Assistant notification**.
  - **Performance Warnings:** (e.g., "Response time has degraded by 30%", "Memory usage is high"). These events should **NOT** create a notification. Instead, they should set the `binary_sensor.aicleaner_health_alert` to `on` and populate an attribute with the warning details.

---

## 3. Acceptance Criteria

- The `aicleaner.run_health_check` service is available in Home Assistant and functions correctly.
- The three specified HA sensor entities are created and update their state when the health check service is run.
- Critical errors result in a persistent notification in Home Assistant.
- Performance issues result in the `binary_sensor` changing state, but do not create a notification.
- The `aicleaner.apply_performance_profile` service is available and functions correctly.

---

## 4. Final Deliverable: Review Request File

When you have completed all of the above tasks, create a new markdown file named `REVIEW_PRIORITY_2.md`.

In this file, please provide the following:
1.  A summary of the new services and sensors you created.
2.  Screenshots from a test Home Assistant instance showing the new entities in the UI.
3.  A code snippet demonstrating how you implemented the weighted Health Score calculation.
4.  An example of a critical alert notification and a performance warning attribute.
5.  Confirmation that all tests pass.
