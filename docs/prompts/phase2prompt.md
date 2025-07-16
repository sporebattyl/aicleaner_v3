# Phase 2 Development Prompt: AI Enhancements & Predictive Analytics

##  collaborators: Gemini & Claude

---

## 1. Introduction & High-Level Goal

This document outlines the requirements for Phase 2 of the `aicleaner_v3` project. The primary goal of this phase is to evolve the system from a reactive cleaner to a proactive, intelligent cleaning assistant. This will be achieved by integrating advanced AI-powered features, including predictive analytics and enhanced scene understanding.

Building upon the solid, modular foundation established in Phase 1, you will work together to implement the features detailed below.

## 2. Core Objectives

1.  **Predictive Analytics for Cleaning:** Develop a system that can predict future cleaning needs based on historical data and usage patterns.
2.  **Advanced Scene Understanding:** Enhance the AI's ability to interpret images, moving from a simple "messy/clean" assessment to identifying specific objects, clutter types, and their locations.
3.  **Dynamic AI Model Selection:** Implement a cost-aware optimizer that can dynamically choose the most appropriate AI model (local vs. various cloud APIs) for a given analysis task.
4.  **Seamless Integration:** Ensure all new features are elegantly integrated into the existing architecture, maintaining stability and performance.

## 3. Detailed Feature Requirements

### 3.1. PredictiveAnalytics Module (`ai/predictive_analytics.py`)

-   **Create `PredictiveAnalytics` Class:**
    -   This class will be responsible for analyzing historical data to forecast cleaning needs.
    -   It should be able to load historical analysis data (e.g., from the state manager's records).
-   **Develop Prediction Model:**
    -   Implement a model (statistical or a simple ML model) that analyzes factors like:
        -   Time of day/day of week.
        -   Frequency of zone use.
        -   Time since last cleaning.
        -   Historical messiness scores.
    -   The output should be a prediction of *when* a zone is likely to require cleaning next (e.g., "in 2 hours," "by this evening").
-   **Generate Proactive Suggestions:**
    -   Based on predictions, the system should be able to generate proactive cleaning tasks or alerts (e.g., "The kitchen is likely to need a light tidy-up in the next hour.").
-   **Integration:**
    -   The `ZoneScheduler` should be able to consult the `PredictiveAnalytics` module to adjust its scheduling dynamically.

### 3.2. Advanced Scene Understanding (`ai/scene_understanding.py`)

-   **Enhance `AdvancedSceneUnderstanding` Class:**
    -   Move beyond a single cleanliness score.
    -   The model should identify and list specific items contributing to mess (e.g., "shoes on floor," "magazines on table," "dishes in sink").
    -   It should be able to provide basic location information for objects if possible (e.g., "near the window").
-   **Generate Granular Tasks:**
    -   The output should enable the creation of highly specific to-do items, such as "Pick up the 3 books on the living room floor" instead of "Clean living room."
-   **Multi-Modal Input (Optional Stretch Goal):**
    -   Design the system to potentially accept multiple images or sensor data (e.g., from motion sensors) to improve context and accuracy.

### 3.3. Multi-Model AI Optimizer (`ai/multi_model_ai.py`)

-   **Dynamic Model Selection Logic:**
    -   Implement a "cost and complexity" based router.
    -   For simple analyses (e.g., a scheduled check-in on a typically clean room), a faster, cheaper local model or a less powerful API might be sufficient.
    -   For complex scenes or high-priority manual requests, a more powerful model like Gemini 1.5 Pro or Claude 3 Opus should be used.
-   **Enhanced Caching:**
    -   Improve the result caching mechanism.
    -   Cache not just the final assessment but also the intermediate results (like object identification) to avoid re-processing.

### 3.4. Configuration (`config.yaml`)

-   **Add Enable/Disable Flags:**
    -   Introduce boolean flags to enable or disable `predictive_analytics` and `advanced_scene_understanding` on a global or per-zone basis.
-   **Prediction Thresholds:**
    -   Allow users to configure the sensitivity of the predictive model (e.g., a threshold for when to trigger a proactive notification).

### 3.5. Testing

-   **New Test Files:**
    -   Create `tests/test_predictive_analytics.py`.
    -   Create `tests/test_scene_understanding.py`.
-   **Updated Tests:**
    -   Modify existing tests for `ZoneAnalyzer` and `ZoneScheduler` to account for the new AI-driven logic.
-   **100% Pass Rate:** All existing and new tests must pass before the phase is considered complete.

## 4. Collaboration & Development Guidelines

-   **Adhere to Existing Architecture:** Leverage the component-based design. Use the `ServiceRegistry` for accessing shared services.
-   **Maintain Code Quality:** All code must be PEP 8 compliant, well-documented with docstrings, and include type hinting.
-   **Iterative Approach:** Feel free to implement one feature at a time, ensuring it's stable and tested before moving to the next.
-   **Communication:** As you are two different agents, clearly state which part of the prompt you are addressing in your responses.

## 5. Final Deliverables

1.  All specified features implemented in the codebase.
2.  A complete and passing test suite.
3.  An updated `README.md` if any new setup or configuration is required.
4.  A final `phase2completion_final.md` report detailing the work done, verification steps, and test results.

---

**Let's begin. Good luck, Gemini and Claude!**
