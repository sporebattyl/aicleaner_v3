# Phase 2 Development Prompt (v4): Actionable Implementation Plan

## Collaborators: Gemini & Claude

---

## 1. Progress Tracker

-   [✅] **Task 1: Create the AI Coordinator Skeleton** (Completed by Gemini)
-   [▶️] **Task 2: Integrate AI Coordinator into ZoneAnalyzer** (Current Task - Claude)
-   [ ] **Task 3: Enhance Individual AI Components** (Next for Gemini)
-   [ ] **Task 4: Update Configuration**
-   [ ] **Task 5: Comprehensive Testing**

---

## 2. Implementation Plan (Phased Approach)

### **Task 1: Create the AI Coordinator Skeleton**

-   **Status**: ✅ **COMPLETE**
-   **File Created**: `ai/ai_coordinator.py`
-   **Notes**: The foundational class `AICoordinator` has been created. It currently uses placeholder logic and will be fully enabled as we complete the subsequent tasks.

### **Task 2: Integrate AI Coordinator into the `ZoneAnalyzer`**

-   **Status**: ▶️ **IN PROGRESS**
-   **Assigned To**: **Claude**
-   **Goal**: Decouple the `ZoneAnalyzer` from individual AI components by making it call the new `AICoordinator`.
-   **File to Modify**: `core/analyzer.py`

**Action Required**:

Refactor the `_process_analysis` method within the `ZoneAnalyzer` class.

1.  **Inject `AICoordinator`**: Modify `ZoneAnalyzer.__init__` to accept an `ai_coordinator` instance.
2.  **Refactor Logic**: Replace the direct calls to `multi_model_ai_optimizer` and other AI-related processing with a single call to the coordinator.

**Conceptual Code Changes:**

```python
# core/analyzer.py

# In ZoneAnalyzer.__init__:
# self.ai_coordinator = ai_coordinator

# In ZoneAnalyzer._process_analysis:

# --- BEFORE (Current Logic) ---
# # Multiple direct calls to different AI components
# analysis_result = await self.multi_model_ai_optimizer.analyze_batch_optimized(...)
# # ... other processing steps ...
# tasks = self._parse_gemini_json_response(analysis_result)


# --- AFTER (New Implementation) ---
# A single, clean call to the AI Coordinator
comprehensive_analysis = await self.ai_coordinator.analyze_zone(
    zone_name=request["zone_name"],
    image_path=image_path, # The path captured earlier in the method
    priority=request["priority"].name.lower()
)
# ... then process the unified `comprehensive_analysis` dictionary ...

```

### **Task 3: Enhance the Individual AI Components**

-   **Status**: ⏹️ **PENDING**
-   **Assigned To**: **Gemini**
-   **Goal**: Implement the core AI logic that the `AICoordinator` will orchestrate.

**Action Required**:

1.  **`ai/multi_model_ai.py` (Enhanced Caching)**:
    -   Modify the caching mechanism to store raw API responses. The cache key should be a hash of the `(model_name, image_path, prompt)`. This allows for more flexible reuse of results.

2.  **`ai/predictive_analytics.py` (Implement Prediction Logic)**:
    -   Implement the `get_prediction_for_zone(zone_name)` method.
    -   It should fetch historical data using `self.state_manager.get_zone_state(zone_name)`.
    -   The method must return a dictionary with `next_predicted_cleaning_time` (ISO string) and `cleaning_urgency_score` (float 0.0-1.0).

3.  **`ai/scene_understanding.py` (Implement Granular Analysis)**:
    -   Implement the `get_detailed_scene_context(core_analysis)` method.
    -   It should parse the `core_analysis` dictionary and return a structured dictionary, for example:
        ```json
        {
          "objects": [
            {"name": "book", "location": "floor", "count": 3},
            {"name": "cup", "location": "table", "count": 1}
          ],
          "generated_tasks": [
            "Pick up the 3 books from the floor.",
            "Remove the cup from the table."
          ]
        }
        ```

### **Task 4: Update Configuration**

-   **Status**: ⏹️ **PENDING**
-   **Goal**: Make all new features configurable.
-   **Action**: Integrate the new `ai_enhancements` section from `phase2prompt_v3.md` into the `ConfigurationManager` and ensure the values are accessible by the AI components.

### **Task 5: Comprehensive Testing**

-   **Status**: ⏹️ **PENDING**
-   **Goal**: Ensure 100% reliability.
-   **Action**:
    1.  **Create `tests/test_ai_coordinator.py`**.
    2.  **Update `tests/test_analyzer.py`** to mock the `AICoordinator`.
    3.  **Create/Update tests** for the enhanced methods in the individual AI components.
    4.  Ensure all existing and new tests pass.

---

## 3. Collaboration Workflow & Deliverables

(This section remains unchanged from `v3`)

---

**Claude, please proceed with Task 2. Let me know if you require any clarification or support.**
