# AICleaner Implementation Prompt: Priority 1 - Core Simplification

## 1. Context & Objective

**Background:** We have just completed a collaborative review (`PHASE_3C2_FINAL_PLAN.md`) of the Phase 3C.2 implementation. We determined that while the features were technically impressive, they were too complex for the end-user. 

**Your Objective:** Your task is to execute the **Priority 1** items from our collaborative plan. This involves a significant refactoring of the performance and monitoring systems to simplify the architecture and the user-facing configuration, and to clarify the terminology used in the code.

---

## 2. Implementation Requirements

### Task 1.1: Refactor to a Unified `SystemMonitor`

- **Action:** Consolidate the logic from the existing `ResourceMonitor`, `AlertManager`, and `ProductionMonitor` classes into a single, new class: `core/system_monitor.py`.
- **Details:**
  - The new `SystemMonitor` class should encapsulate the internal logic of the old classes. You can keep the old classes as internal, private helper classes within the `system_monitor.py` file if it helps organize the code, but they should not be exposed to the rest of the application.
  - The `SystemMonitor` should have a clean, unified public interface, including a primary method like `async def get_health_status() -> HealthStatus:`.
  - Update the `AICoordinator` to remove the old monitors and inject only the new `SystemMonitor`.

### Task 1.2: Implement Profile-Based Configuration

- **Action:** Refactor the configuration in `config.yaml` and the logic that consumes it to be profile-based.
- **Details:**
  - Rename the top-level key in `config.yaml` from `performance_optimization` to `inference_tuning`.
  - The `inference_tuning` section should contain only two primary keys: `enabled: true` and `profile: "auto"`.
  - The user-selectable options for `profile` are: `auto`, `resource_efficient`, `balanced`, `maximum_performance`.
  - Implement the automatic migration logic. On startup, the addon must check for the existence of the old `performance_optimization` block. If found, it should:
    1.  Analyze the old settings to map to the most appropriate new profile.
    2.  Rename the old block to `performance_optimization_backup`.
    3.  Write the new, simplified `inference_tuning` block to the config.
    4.  Log a clear message to the user that their configuration has been automatically migrated.

### Task 1.3: Clarify Terminology

- **Action:** Refactor method and variable names throughout the codebase to more accurately reflect their function, as discussed in our plan.
- **Primary Renames:**
  - `optimize_model()` -> `configure_inference_settings()`
  - `_apply_quantization()` -> `_set_quantization_preference()`
  - `optimization_applied` -> `inference_configured`

---

## 3. Acceptance Criteria

- The old `ResourceMonitor`, `AlertManager`, and `ProductionMonitor` classes are no longer directly used by the `AICoordinator`.
- A new `SystemMonitor` class exists and is properly integrated.
- The `config.yaml` file is simplified, using the `inference_tuning.profile` setting.
- The startup logic correctly handles the migration of old configuration files.
- All specified terminology changes have been applied consistently across the codebase.
- All existing tests must continue to pass after the refactoring.

---

## 4. Final Deliverable: Review Request File

When you have completed all of the above tasks, create a new markdown file named `REVIEW_PRIORITY_1.md`.

In this file, please provide the following:
1.  A summary of the refactoring you performed.
2.  Code diffs showing the changes in `AICoordinator`, the creation of `SystemMonitor`, and the changes in `config.yaml`.
3.  A description of how you implemented and tested the configuration migration logic.
4.  Confirmation that all tests pass.
