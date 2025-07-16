# Priority 1: Core Refactoring - REFINED

## Context

You are implementing Priority 1 of the Phase 3C.2 performance optimization refinement for AICleaner. This is part of a **beta release approach** based on collaborative planning with Gemini to transform complex technical implementation into user-friendly, intelligent performance optimization.

**Final Plan Integration:** This implementation incorporates specific decisions from our collaborative final plan, including migration notification strategy, terminology clarification, and user-centric simplification approach.

## Objective

Refactor the existing complex performance optimization components into a unified, simplified architecture while preserving all technical capabilities and ensuring seamless migration for existing users.

## Implementation Requirements

### Task 1.1: Consolidate into SystemMonitor

**Action:** Create a new unified `SystemMonitor` class that consolidates `ResourceMonitor`, `AlertManager`, and `ProductionMonitor` functionality.

**Implementation Details:**
- **File:** `core/system_monitor.py`
- **Architecture:** Single public interface with internal specialized components
- **Key Methods:**
  - `async def get_health_status() -> HealthStatus`
  - `async def start_monitoring()`
  - `async def stop_monitoring()`
  - `async def get_performance_summary() -> Dict[str, Any]`

**Internal Components (not exposed to users):**
```python
class SystemMonitor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("inference_tuning", {})
        
        # Internal components - users never interact with these directly
        self._resource_tracker = ResourceTracker()
        self._alert_processor = AlertProcessor() 
        self._trend_analyzer = TrendAnalyzer()
        
        # Adaptive monitoring state
        self._check_frequency = 60  # Start with 60-second intervals
        self._stability_counter = 0
        self._last_anomaly_time = 0
```

### Task 1.2: Implement Profile-Based Configuration

**Action:** Replace complex `performance_optimization` config section with simple profile-based approach.

**New Configuration Structure:**
```yaml
# New simplified config.yaml structure
inference_tuning:
  enabled: true
  profile: "auto"  # auto, resource_efficient, balanced, maximum_performance
  
  # Advanced users only (hidden from main UI)
  advanced_overrides: {}
  
  # Internal migration tracking
  _migrated_from_complex_config: false
```

**Migration Strategy (Final Plan Decision - Option C: Both notification and log):**
```python
async def migrate_legacy_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """Automatically migrate complex configs to profile-based."""
    if "performance_optimization" in config:
        # Analyze old settings and map to closest profile
        legacy_settings = config["performance_optimization"]
        
        # Determine best profile match
        if legacy_settings.get("quantization", {}).get("default_level") == "int4":
            profile = "resource_efficient"
        elif legacy_settings.get("gpu_acceleration", {}).get("enabled"):
            profile = "maximum_performance"
        else:
            profile = "balanced"
        
        # Create new config
        new_config = {
            "inference_tuning": {
                "enabled": True,
                "profile": profile,
                "_migrated_from_complex_config": True
            }
        }
        
        # Backup old config
        config["performance_optimization_backup"] = config.pop("performance_optimization")
        
        # FINAL PLAN DECISION: Both notification and log
        await self._send_migration_notification(profile)
        self.logger.info(f"Migrated configuration to '{profile}' profile. Backup saved as 'performance_optimization_backup'")
        
        return new_config

async def _send_migration_notification(self, profile: str):
    """Send Home Assistant notification about migration."""
    notification_text = (
        f"AICleaner configuration has been automatically migrated to simplified "
        f"profile-based system. Selected profile: '{profile}'. Your settings have "
        f"been preserved. See logs for details. [BETA VERSION]"
    )
    # Implementation will send HA persistent notification
```

### Task 1.3: Terminology Clarification

**Action:** Rename methods and variables to clarify that AICleaner configures inference settings, not model files.

**Refactoring Map:**
- `optimize_model()` → `configure_inference_settings()`
- `_apply_quantization()` → `_set_quantization_preference()`
- `_apply_compression()` → `_set_compression_preference()`
- `optimization_applied` → `inference_configured`
- `performance_optimization` → `inference_tuning`
- `OptimizationConfig` → `InferenceConfig`

**Documentation Updates:**
```python
async def configure_inference_settings(self, model_name: str, config: InferenceConfig) -> bool:
    """
    Configure inference settings for a model.
    
    IMPORTANT: AICleaner does not modify model files. Instead, it configures
    Ollama's inference parameters (quantization, context size, etc.) to
    optimize performance based on your system capabilities.
    
    Args:
        model_name: Name of the model to configure
        config: Inference configuration settings
        
    Returns:
        True if configuration was applied successfully
    """
```

### Task 1.4: Update Integration Points

**Action:** Update all references to old components in existing code.

**Files to Update:**
- `ai/ai_coordinator.py` - Replace component references
- `core/local_model_manager.py` - Update method calls
- `integrations/ollama_client.py` - Update configuration handling
- `config.yaml` - Replace configuration section

**Integration Pattern:**
```python
# In AICoordinator.__init__()
if PERFORMANCE_OPTIMIZATION_AVAILABLE:
    self.system_monitor = SystemMonitor(config)
    self.optimization_profiles = OptimizationProfileManager()
else:
    self.system_monitor = None
    self.optimization_profiles = None
```

## Beta Version Context

**Important:** This implementation is part of a beta release approach:
- Include version metadata to track beta vs. final releases
- Add beta disclaimer in migration notifications
- Prepare for community feedback integration
- Maintain backward compatibility during beta period

## Acceptance Criteria

### Functional Requirements
- [ ] `SystemMonitor` successfully consolidates all monitoring functionality
- [ ] Profile-based configuration works with all existing optimization profiles
- [ ] Migration logic handles 100% of existing complex configurations
- [ ] All terminology is updated consistently across codebase
- [ ] Integration points are updated and functional

### User Experience Requirements
- [ ] Zero-config installation works with "auto" profile
- [ ] Migration notifications are clear and informative (both HA notification and log)
- [ ] Advanced users can still access full capabilities via `advanced_overrides`
- [ ] Beta version context is clear in all user-facing messages

### Technical Requirements
- [ ] All existing functionality is preserved
- [ ] Performance overhead is minimal
- [ ] Error handling is comprehensive
- [ ] Thread safety is maintained
- [ ] Graceful degradation when dependencies unavailable

### Migration Requirements
- [ ] Complex configs are automatically detected and migrated
- [ ] Original configs are backed up safely
- [ ] Users are notified via both HA notification and logs
- [ ] Migration can be reversed if needed
- [ ] Migration works across all supported configuration variations

## Testing Requirements

- **Unit Tests:** Test each component in isolation
- **Integration Tests:** Test component interactions
- **Migration Tests:** Test migration with various complex configs
- **Performance Tests:** Ensure no performance regression
- **User Experience Tests:** Validate zero-config installation

## Success Metrics

1. **Simplification:** New users can use the system without reading documentation
2. **Migration:** 100% success rate for existing configuration migration
3. **Performance:** No measurable performance degradation
4. **Maintainability:** Codebase is easier to understand and modify
5. **User Satisfaction:** Beta feedback indicates improved usability

This refactoring transforms the complex technical implementation into a user-friendly system while maintaining all advanced capabilities for power users.
