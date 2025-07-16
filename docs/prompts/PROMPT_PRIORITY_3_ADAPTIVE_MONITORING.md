# AICleaner Implementation Prompt: Priority 3 - Advanced Backend Logic

## 1. Context & Objective

**Background:** The core refactoring (Priority 1) and the user-facing Home Assistant integration (Priority 2) are now complete. We have a simplified, robust system with a `SystemMonitor` and user-facing health check features.

**Your Objective:** Your task is to implement the final piece of advanced backend logic from our collaborative plan: making the monitoring system "smart" by giving it the ability to adapt its own behavior based on system stability.

---

## 2. Implementation Requirements

### Task 3.1: Implement Adaptive Monitoring in `SystemMonitor`

- **Action:** Enhance the `SystemMonitor`'s background monitoring loop to be adaptive.
- **Details:**
  - The monitor should have a configurable check frequency, defaulting to a safe interval (e.g., 60 seconds).
  - Implement a "stability counter." Every time the monitor runs and finds that all metrics are within normal, stable parameters, this counter should increment.
  - If the stability counter reaches a certain threshold (e.g., 10 consecutive stable checks), the monitoring frequency should be **decreased** (e.g., multiplied by 1.2, up to a maximum of 300 seconds). This reduces overhead on a healthy system.
  - If the monitor detects a performance anomaly or a critical alert, the stability counter should be reset to zero, and the monitoring frequency should be **increased** (e.g., multiplied by 0.8, down to a minimum of 30 seconds). This provides more granular data when it's most needed.

```python
# Pseudocode for the adaptive loop logic within SystemMonitor

async def _adaptive_monitoring_loop(self):
    while self.monitoring_active:
        try:
            is_stable = await self._check_system_stability()

            if is_stable:
                self._stability_counter += 1
                if self._stability_counter > 10:
                    # Decrease frequency (run less often)
                    self._check_frequency = min(300, self._check_frequency * 1.2)
            else:
                self._stability_counter = 0
                # Increase frequency (run more often)
                self._check_frequency = max(30, self._check_frequency * 0.8)

            await asyncio.sleep(self._check_frequency)

        except Exception as e:
            # Handle errors and reset to default frequency
            self._check_frequency = 60
            await asyncio.sleep(self._check_frequency)
```

---

## 3. Acceptance Criteria

- The `SystemMonitor`'s background loop is no longer fixed but adjusts its own `sleep` interval based on system performance.
- The logic correctly reduces monitoring frequency on a stable system to minimize overhead.
- The logic correctly increases monitoring frequency during periods of instability or high load.
- The changes are well-contained within the `SystemMonitor` and do not add complexity to other parts of the application.
- All existing tests still pass.

---

## 4. Final Deliverable: Review Request File

When you have completed this task, create a new markdown file named `REVIEW_PRIORITY_3.md`.

In this file, please provide the following:
1.  A code snippet of your implementation of the `_adaptive_monitoring_loop`.
2.  An explanation of how you tested this time-based, adaptive behavior.
3.  Example log outputs demonstrating the monitoring frequency changing in response to simulated system states (both stable and unstable).
4.  Confirmation that all tests pass.
