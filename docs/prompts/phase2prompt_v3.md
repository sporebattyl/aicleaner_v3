# Phase 2 Development Prompt (v3): Actionable Implementation Plan

## Collaborators: Gemini & Claude

---

## 1. High-Level Objective

**Goal**: Evolve the `aicleaner_v3` system from a reactive cleaner into a **proactive, intelligent cleaning assistant**.

This will be achieved by implementing a central AI orchestration layer and enhancing our existing AI components with predictive analytics and advanced scene understanding.

## 2. Core Architectural Decision: The AI Coordinator

To ensure a clean, maintainable, and scalable architecture, we will introduce a new central orchestration layer: the **AI Coordinator**.

**File**: `ai/ai_coordinator.py`
**Purpose**: This class will be the single point of contact for all AI-related tasks. It will abstract the complexity of the individual AI components (`MultiModelAIOptimizer`, `PredictiveAnalytics`, `AdvancedSceneUnderstanding`) from the rest of the application, preventing tight coupling and making the system easier to manage.

---

## 3. Implementation Plan (Phased Approach)

### **Task 1: Create the AI Coordinator Skeleton**

**Your first task is to create the `ai/ai_coordinator.py` file with the following skeleton.** This establishes the foundation for all subsequent AI enhancements.

```python
# ai/ai_coordinator.py

import logging
from typing import Dict, Any, Optional

from .multi_model_ai import MultiModelAIOptimizer
from .predictive_analytics import PredictiveAnalytics
from .scene_understanding import AdvancedSceneUnderstanding
from ..utils.service_registry import ServiceRegistry

class AICoordinator:
    """
    Orchestrates all AI components for a cohesive analysis pipeline.
    This is the single entry point for AI-related tasks.
    """
    def __init__(self, config: Dict[str, Any], services: ServiceRegistry):
        self.logger = logging.getLogger(__name__)
        self.config = config.get("ai_enhancements", {})
        
        # Retrieve AI components from the service registry
        self.multi_model_ai: MultiModelAIOptimizer = services.get("multi_model_ai")
        self.predictive_analytics: PredictiveAnalytics = services.get("predictive_analytics")
        self.scene_understanding: AdvancedSceneUnderstanding = services.get("scene_understanding")

    async def analyze_zone(self, zone_name: str, image_path: str, priority: str) -> Dict[str, Any]:
        """
        Performs a full, orchestrated analysis of a zone.

        Args:
            zone_name: The name of the zone to analyze.
            image_path: The path to the captured image.
            priority: The priority of the analysis request ('manual', 'scheduled', etc.).

        Returns:
            A comprehensive analysis result dictionary.
        """
        self.logger.info(f"Starting orchestrated AI analysis for zone: {zone_name}")

        # 1. Select the best AI model based on priority and config
        model_choice = self._select_model(priority)

        # 2. Get the core analysis from the MultiModelAIOptimizer
        core_analysis = await self.multi_model_ai.analyze_image(
            image_path, 
            model=model_choice,
            prompt="Analyze this scene for cleanliness." # This will be enhanced
        )

        # 3. Enhance the analysis with scene understanding
        scene_details = await self.scene_understanding.get_detailed_scene_context(core_analysis)

        # 4. Get predictive insights for this zone
        predictions = await self.predictive_analytics.get_prediction_for_zone(zone_name)

        # 5. Combine all insights into a final result
        final_result = self._compile_final_analysis(core_analysis, scene_details, predictions)
        
        self.logger.info(f"Completed orchestrated AI analysis for zone: {zone_name}")
        return final_result

    def _select_model(self, priority: str) -> str:
        """Selects the appropriate AI model based on configuration and priority."""
        model_prefs = self.config.get("model_selection", {})
        if priority == "manual":
            return model_prefs.get("detailed_analysis", "gemini-pro")
        elif priority == "complex": # A new priority for difficult scenes
            return model_prefs.get("complex_reasoning", "claude-sonnet")
        else: # Scheduled, retry, etc.
            return model_prefs.get("simple_analysis", "gemini-flash")

    def _compile_final_analysis(self, core: Dict, scene: Dict, preds: Dict) -> Dict[str, Any]:
        """Combines all AI outputs into a single, comprehensive result."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "core_assessment": core,
            "scene_understanding": scene,
            "predictive_insights": preds,
            "generated_tasks": [] # To be populated based on scene understanding
        }

```

### **Task 2: Integrate the AI Coordinator into the `ZoneManager`**

**Goal**: Decouple the `ZoneManager` from the individual AI components by making it call the new `AICoordinator`.

**File to Modify**: `core/zone_manager.py` (or equivalent analysis processing location)

**Action**:
Refactor the analysis logic inside `ZoneManager` (likely in a method like `_process_analysis` or `analyze_image_batch_optimized`).

**FROM (Conceptual Before):**
```python
# OLD LOGIC - Calling individual components
# result1 = self.multi_model_ai.analyze(...)
# result2 = self.scene_understanding.analyze(...)
```

**TO (New Implementation):**
```python
# NEW LOGIC - Single call to the coordinator
# self.ai_coordinator is initialized in the ZoneManager's __init__
analysis_result = await self.ai_coordinator.analyze_zone(
    zone_name=zone_name,
    image_path=image_path,
    priority=analysis_request.priority.name.lower()
)
# ... then process the unified analysis_result
```

### **Task 3: Enhance the Individual AI Components**

Now, enhance the underlying AI modules that the `AICoordinator` calls.

1.  **`ai/multi_model_ai.py`**:
    -   **Goal**: Improve caching.
    -   **Action**: Modify the caching mechanism to store and retrieve intermediate results (like raw API responses or object lists) in addition to the final analysis. This avoids costly re-processing.

2.  **`ai/predictive_analytics.py`**:
    -   **Goal**: Integrate with the scheduler.
    -   **Action**: Implement the `get_prediction_for_zone` method. It should analyze historical data from the `StateManager` and return a dictionary containing keys like `next_predicted_cleaning_time` and `cleaning_urgency_score`.

3.  **`ai/scene_understanding.py`**:
    -   **Goal**: Generate granular tasks.
    -   **Action**: Implement the `get_detailed_scene_context` method. It should take the raw analysis from `MultiModelAI` and extract a list of specific objects, their locations, and generate highly specific, actionable task descriptions (e.g., "Pick up the red toy car near the sofa").

### **Task 4: Update Configuration**

**Goal**: Make all new features configurable.
**File to Modify**: `config.yaml`

**Action**: Add the following sections to your `config.yaml`. The application should gracefully handle these keys being absent for backwards compatibility.

```yaml
ai_enhancements:
  # Master switches for new features
  predictive_analytics: true
  advanced_scene_understanding: true
  smart_model_selection: true
  
  # Model selection preferences
  model_selection:
    simple_analysis: "gemini-flash"
    detailed_analysis: "gemini-pro"
    complex_reasoning: "claude-sonnet"
    
  # Prediction settings
  predictions:
    enable_proactive_scheduling: true
    prediction_confidence_threshold: 0.7
    
  # Scene understanding settings
  scene_analysis:
    enable_object_tracking: true
    enable_location_detection: true
```

### **Task 5: Comprehensive Testing**

**Goal**: Ensure 100% reliability and maintain our quality standards.

**Action**:
1.  **Create New Test Files**:
    -   `tests/test_ai_coordinator.py`
    -   Update `tests/test_predictive_analytics.py` and `tests/test_scene_understanding.py` for the new methods.
2.  **Update Existing Tests**:
    -   Modify `tests/test_zone_manager.py` to mock the `AICoordinator` instead of the individual AI components.
3.  **Maintain 100% Pass Rate**: All 18 existing tests plus all new tests must pass.

---

## 4. Collaboration Workflow

-   **Gemini**: Your primary focus will be on the core AI logic within the `MultiModelAIOptimizer`, `PredictiveAnalytics`, and `AdvancedSceneUnderstanding` components. You will implement the enhanced algorithms for caching, prediction, and scene detail extraction.
-   **Claude**: Your primary focus will be on the architectural integration. You will implement the `AICoordinator`, refactor the `ZoneManager` to use it, and create the new test files (`test_ai_coordinator.py`) to ensure the orchestration works as expected.
-   **Both**: You will both collaborate on the final integration and debugging, ensuring the end-to-end pipeline is flawless.

## 5. Final Deliverables

1.  **Code**: All new and modified Python files (`ai_coordinator.py`, etc.).
2.  **Configuration**: The updated `config.yaml` structure integrated into the `ConfigurationManager`.
3.  **Tests**: A complete and **100% passing** test suite.
4.  **Documentation**: A final `phase2completion_final.md` report.

---

**Let's begin. Please start with Task 1: Creating the `ai/ai_coordinator.py` file and class skeleton.**