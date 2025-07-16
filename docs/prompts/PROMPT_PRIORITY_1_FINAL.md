# AICleaner Final Prompt: Priority 1 - Core Simplification

## 1. Final Implementation Context

This is the first of three final implementation steps for Phase 3C.2. Based on our collaborative plan, your objective is to perform a crucial refactoring to simplify the addon's architecture and configuration before adding new features.

## 2. Objective

Execute the **Priority 1** items from our collaborative plan. This involves refactoring the monitoring systems into a unified `SystemMonitor`, simplifying the configuration to be profile-based, and clarifying terminology in the code.

## 3. Implementation Requirements

### Task 1.1: Refactor to a Unified `SystemMonitor`

-   **Action:** Consolidate the logic from `ResourceMonitor`, `AlertManager`, and `ProductionMonitor` into a single new class: `core/system_monitor.py`.
-   **Details:** The new `SystemMonitor` class should encapsulate the logic of the old classes. They can remain as internal helper classes if needed, but the rest of the application should only interact with `SystemMonitor`. Update `AICoordinator` to inject and use only this new, unified monitor.

### Task 1.2: Implement Profile-Based Configuration

-   **Action:** Refactor `config.yaml` and the logic that consumes it.
-   **Details:**
    -   Rename the top-level key from `performance_optimization` to `inference_tuning`.
    -   This section should only contain `enabled: true` and `profile: "auto"` (with options: `auto`, `resource_efficient`, `balanced`, `maximum_performance`).
    -   Implement the automatic migration logic as planned: on startup, detect the old config, map it to a new profile, back up the old block to `performance_optimization_backup`, and write the new simplified block.

### Task 1.3: Clarify Terminology

-   **Action:** Apply the agreed-upon terminology changes consistently across the codebase.
-   **Renames:** `optimize_model()` -> `configure_inference_settings()`, `_apply_quantization()` -> `_set_quantization_preference()`, `optimization_applied` -> `inference_configured`.

## 4. Final Deliverable: Review Request File

Upon completion, create a new markdown file named `REVIEW_PRIORITY_1_COMPLETE.md`. In this file, provide:
1.  A summary of the refactoring.
2.  Code diffs for `AICoordinator`, `SystemMonitor`, and `config.yaml`.
3.  A description of how you implemented and tested the configuration migration.
4.  Confirmation that all 113 existing tests pass.
