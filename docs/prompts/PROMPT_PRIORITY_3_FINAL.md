# AICleaner Final Prompt: Priority 3 - Adaptive Monitoring

## 1. Final Implementation Context

This is the final implementation step. The addon is now architecturally simple and has a user-friendly interface in Home Assistant. The last task is to add a layer of intelligence to the backend, making the monitoring system "smart" and resource-efficient, as per our collaborative plan.

## 2. Objective

Execute the **Priority 3** item from our plan: Implement adaptive monitoring frequency within the `SystemMonitor`.

## 3. Implementation Requirements

### Task 3.1: Implement Adaptive Monitoring Frequency

-   **Action:** The `SystemMonitor`'s background loop must dynamically adjust its own check frequency based on system stability.
-   **Core Logic:**
    1.  The monitor starts with a default frequency (e.g., 60 seconds).
    2.  It maintains a `stability_counter`.
    3.  If a check passes and all key metrics (latency, error rate, resource pressure) are within normal bounds, increment the counter.
    4.  If the counter exceeds a threshold (e.g., 10 stable checks), **decrease** the monitoring frequency (run less often) by multiplying by a factor (e.g., 1.2), up to a maximum of 300 seconds.
    5.  If a check detects an anomaly or a performance warning, reset the counter to 0 and **increase** the monitoring frequency (run more often) by multiplying by a factor (e.g., 0.8), down to a minimum of 30 seconds.
-   **Goal:** This will reduce system overhead when performance is good and increase vigilance when problems are detected.

### Task 3.2: Defer Advanced Concepts

-   **Action:** Do **not** implement the more complex ideas from the initial refined prompt at this time. This includes:
    -   Predictive anomaly detection.
    -   Smart alert escalation based on user response history.
    -   Resource-aware monitoring *intensity* (we are only changing the *frequency*).
-   **Reason:** We are prioritizing the core value of adaptive frequency, which provides the biggest benefit with the least complexity, per our agreed-upon principle of "Minimum Viable Intelligence."

## 4. Final Deliverable: Review Request File

Upon completion, create a new markdown file named `REVIEW_PRIORITY_3_COMPLETE.md`. In this file, provide:
1.  A code snippet of your final implementation of the adaptive monitoring loop within `SystemMonitor`.
2.  An explanation of how you tested this time-based, adaptive behavior.
3.  Example log outputs demonstrating the monitoring frequency changing in response to both stable and unstable simulated system states.
4.  Confirmation that all tests pass.
