# AICleaner Final Prompt: Priority 2 - User-Facing Features

## 1. Final Implementation Context

With the core refactoring from Priority 1 complete, the addon now has a simplified architecture. This prompt focuses on building the user-facing entities in Home Assistant to expose the new monitoring capabilities in a simple and intuitive way.

## 2. Objective

Execute the **Priority 2** items from our collaborative plan. This involves creating a Home Assistant service for health checks, the associated sensors to display the results, and implementing the planned alerting strategy.

## 3. Implementation Requirements

### Task 2.1: Implement the Health Check Service & Score

-   **Action:** Create the `aicleaner.run_health_check` service.
-   **Details:** This service should trigger a 30-second health check in the `SystemMonitor`. The check must calculate a **Health Score (0-100)** using the agreed-upon weighted average:
    -   **Average Inference Latency (60% weight):** Tested with a representative prompt.
    -   **Error Rate (30% weight):** Track failures during the test.
    -   **Resource Pressure (10% weight):** Check CPU/Memory usage.

### Task 2.2: Implement Home Assistant Integration

-   **Action:** Create the required HA entities.
-   **Sensors:**
    -   `sensor.aicleaner_health_score` (Unit: `score`)
    -   `sensor.aicleaner_average_response_time` (Unit: `ms`)
    -   `binary_sensor.aicleaner_health_alert` (Device Class: `problem`). This sensor's attributes should hold the reason for the alert (e.g., `reason: "Response time has degraded by 30%"`).
-   **Services:**
    -   Expose `aicleaner.run_health_check`.
    -   Expose `aicleaner.apply_performance_profile` which requires a restart (show a message in the UI).

### Task 2.3: Implement the Alerting Strategy

-   **Action:** Implement the dual-mode alerting logic in `SystemMonitor`.
-   **Details:**
    -   **Critical Alerts** (e.g., Ollama offline): MUST trigger a **persistent Home Assistant notification**.
    -   **Performance Warnings** (e.g., high memory usage): MUST set `binary_sensor.aicleaner_health_alert` to `on` and populate the `reason` attribute. MUST NOT create a user-facing notification.

## 4. Final Deliverable: Review Request File

Upon completion, create a new markdown file named `REVIEW_PRIORITY_2_COMPLETE.md`. In this file, provide:
1.  A summary of the new services and sensors.
2.  Screenshots from a test HA instance showing the new entities.
3.  A code snippet of the Health Score calculation.
4.  An example of a critical alert notification and a performance warning attribute.
5.  Confirmation that all tests pass.
