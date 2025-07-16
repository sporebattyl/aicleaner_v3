"""
Centralized Configuration Validation System for AI Cleaner v3

This module provides comprehensive validation for all configuration settings,
ensuring that the application starts with valid configuration and provides
helpful error messages and recommendations for invalid settings.

Features:
- Validates all ai_enhancements configuration sections
- Provides detailed error messages and warnings
- Offers configuration recommendations
- Supports graceful fallbacks for missing settings
- Validates data types, ranges, and dependencies
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from enum import Enum


class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult:
    """Container for validation results"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.recommendations: List[str] = []
    
    def add_error(self, message: str):
        """Add an error message"""
        self.errors.append(message)
    
    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)
    
    def add_info(self, message: str):
        """Add an info message"""
        self.info.append(message)
    
    def add_recommendation(self, message: str):
        """Add a recommendation"""
        self.recommendations.append(message)
    
    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid (no errors)"""
        return len(self.errors) == 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        return {
            "valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "info_count": len(self.info),
            "recommendation_count": len(self.recommendations),
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "recommendations": self.recommendations
        }


class ConfigValidator:
    """
    Centralized configuration validator for AI Cleaner v3
    
    Validates all configuration sections and provides detailed feedback
    on configuration issues, recommendations, and best practices.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize configuration validator
        
        Args:
            config: Full configuration dictionary to validate
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.result = ValidationResult()
    
    def validate_full_config(self) -> ValidationResult:
        """
        Validate the complete configuration
        
        Returns:
            ValidationResult with all validation findings
        """
        self.logger.info("Starting comprehensive configuration validation")
        
        # Validate core configuration
        self._validate_core_config()
        
        # Validate AI enhancements configuration
        self._validate_ai_enhancements()
        
        # Validate zones configuration
        self._validate_zones_config()
        
        # Generate recommendations
        self._generate_recommendations()
        
        self.logger.info(f"Configuration validation complete: {self.result.get_summary()}")
        return self.result
    
    def _validate_core_config(self):
        """Validate core configuration settings"""
        # Check required core settings
        required_core = ["ha_url", "ha_token"]
        for setting in required_core:
            if setting not in self.config:
                self.result.add_error(f"Missing required core setting: {setting}")
            elif not self.config[setting]:
                self.result.add_error(f"Core setting '{setting}' cannot be empty")
        
        # Validate optional core settings
        if "analysis_workers" in self.config:
            workers = self.config["analysis_workers"]
            if not isinstance(workers, int) or workers < 1 or workers > 10:
                self.result.add_warning("analysis_workers should be an integer between 1 and 10")
        
        if "max_concurrent_analyses" in self.config:
            max_concurrent = self.config["max_concurrent_analyses"]
            if not isinstance(max_concurrent, int) or max_concurrent < 1 or max_concurrent > 20:
                self.result.add_warning("max_concurrent_analyses should be an integer between 1 and 20")
    
    def _validate_ai_enhancements(self):
        """Validate AI enhancements configuration section"""
        ai_config = self.config.get("ai_enhancements", {})
        
        if not ai_config:
            self.result.add_warning("ai_enhancements section is missing - using default settings")
            return
        
        # Validate feature toggles
        self._validate_feature_toggles(ai_config)
        
        # Validate model selection
        self._validate_model_selection(ai_config)
        
        # Validate caching configuration
        self._validate_caching_config(ai_config)
        
        # Validate scene understanding settings
        self._validate_scene_understanding_config(ai_config)
        
        # Validate predictive analytics settings
        self._validate_predictive_analytics_config(ai_config)
        
        # Validate multi-model AI settings
        self._validate_multi_model_ai_config(ai_config)
    
    def _validate_feature_toggles(self, ai_config: Dict[str, Any]):
        """Validate feature toggle settings"""
        toggles = ["advanced_scene_understanding", "predictive_analytics"]
        
        for toggle in toggles:
            if toggle in ai_config:
                value = ai_config[toggle]
                if not isinstance(value, bool):
                    self.result.add_error(f"Feature toggle '{toggle}' must be a boolean (true/false)")
    
    def _validate_model_selection(self, ai_config: Dict[str, Any]):
        """Validate model selection configuration"""
        model_config = ai_config.get("model_selection", {})
        
        if not model_config:
            self.result.add_info("model_selection not configured - using default model preferences")
            return
        
        valid_models = ["gemini-pro", "gemini-flash", "claude-sonnet", "gpt-4v"]
        required_selections = ["detailed_analysis", "complex_reasoning", "simple_analysis"]
        
        for selection in required_selections:
            if selection in model_config:
                model = model_config[selection]
                if model not in valid_models:
                    self.result.add_error(f"Invalid model '{model}' for {selection}. Valid models: {valid_models}")
    
    def _validate_caching_config(self, ai_config: Dict[str, Any]):
        """Validate caching configuration"""
        cache_config = ai_config.get("caching", {})
        
        if not cache_config:
            self.result.add_info("caching configuration not found - using defaults")
            return
        
        # Validate boolean settings
        bool_settings = ["enabled", "intermediate_caching"]
        for setting in bool_settings:
            if setting in cache_config and not isinstance(cache_config[setting], bool):
                self.result.add_error(f"Caching setting '{setting}' must be a boolean")
        
        # Validate numeric settings
        if "ttl_seconds" in cache_config:
            ttl = cache_config["ttl_seconds"]
            if not isinstance(ttl, int) or ttl < 60 or ttl > 3600:
                self.result.add_warning("ttl_seconds should be between 60 and 3600 seconds")
        
        if "max_cache_entries" in cache_config:
            max_entries = cache_config["max_cache_entries"]
            if not isinstance(max_entries, int) or max_entries < 100 or max_entries > 10000:
                self.result.add_warning("max_cache_entries should be between 100 and 10000")
    
    def _validate_scene_understanding_config(self, ai_config: Dict[str, Any]):
        """Validate scene understanding configuration"""
        scene_config = ai_config.get("scene_understanding_settings", {})
        
        if not scene_config:
            self.result.add_info("scene_understanding_settings not configured - using defaults")
            return
        
        # Validate numeric ranges
        numeric_validations = [
            ("max_objects_detected", 1, 50),
            ("max_generated_tasks", 1, 20),
        ]
        
        for setting, min_val, max_val in numeric_validations:
            if setting in scene_config:
                value = scene_config[setting]
                if not isinstance(value, int) or value < min_val or value > max_val:
                    self.result.add_warning(f"{setting} should be an integer between {min_val} and {max_val}")
        
        # Validate confidence threshold
        if "confidence_threshold" in scene_config:
            threshold = scene_config["confidence_threshold"]
            if not isinstance(threshold, (int, float)) or threshold < 0.0 or threshold > 1.0:
                self.result.add_error("confidence_threshold must be a number between 0.0 and 1.0")
        
        # Validate boolean settings
        bool_settings = ["enable_seasonal_adjustments", "enable_time_context"]
        for setting in bool_settings:
            if setting in scene_config and not isinstance(scene_config[setting], bool):
                self.result.add_error(f"Scene understanding setting '{setting}' must be a boolean")
    
    def _validate_predictive_analytics_config(self, ai_config: Dict[str, Any]):
        """Validate predictive analytics configuration"""
        pred_config = ai_config.get("predictive_analytics_settings", {})
        
        if not pred_config:
            self.result.add_info("predictive_analytics_settings not configured - using defaults")
            return
        
        # Validate numeric settings
        numeric_validations = [
            ("history_days", 1, 365),
            ("prediction_horizon_hours", 1, 168),  # 1 week max
            ("min_data_points", 1, 100),
        ]
        
        for setting, min_val, max_val in numeric_validations:
            if setting in pred_config:
                value = pred_config[setting]
                if not isinstance(value, int) or value < min_val or value > max_val:
                    self.result.add_warning(f"{setting} should be an integer between {min_val} and {max_val}")
        
        # Validate boolean settings
        bool_settings = ["enable_urgency_scoring", "enable_pattern_detection"]
        for setting in bool_settings:
            if setting in pred_config and not isinstance(pred_config[setting], bool):
                self.result.add_error(f"Predictive analytics setting '{setting}' must be a boolean")
    
    def _validate_multi_model_ai_config(self, ai_config: Dict[str, Any]):
        """Validate multi-model AI configuration"""
        ai_model_config = ai_config.get("multi_model_ai", {})
        
        if not ai_model_config:
            self.result.add_info("multi_model_ai configuration not found - using defaults")
            return
        
        # Validate boolean settings
        bool_settings = ["enable_fallback", "performance_tracking"]
        for setting in bool_settings:
            if setting in ai_model_config and not isinstance(ai_model_config[setting], bool):
                self.result.add_error(f"Multi-model AI setting '{setting}' must be a boolean")
        
        # Validate numeric settings
        if "max_retries" in ai_model_config:
            retries = ai_model_config["max_retries"]
            if not isinstance(retries, int) or retries < 1 or retries > 10:
                self.result.add_warning("max_retries should be between 1 and 10")
        
        if "timeout_seconds" in ai_model_config:
            timeout = ai_model_config["timeout_seconds"]
            if not isinstance(timeout, int) or timeout < 5 or timeout > 300:
                self.result.add_warning("timeout_seconds should be between 5 and 300")
    
    def _validate_zones_config(self):
        """Validate zones configuration"""
        zones = self.config.get("zones", [])
        
        if not zones:
            self.result.add_error("No zones configured - at least one zone is required")
            return
        
        for i, zone in enumerate(zones):
            if not isinstance(zone, dict):
                self.result.add_error(f"Zone {i} must be a dictionary")
                continue
            
            # Check required zone fields
            required_fields = ["name", "camera_entity", "todo_list_entity", "purpose"]
            for field in required_fields:
                if field not in zone:
                    self.result.add_error(f"Zone {i} missing required field: {field}")
                elif not zone[field]:
                    self.result.add_error(f"Zone {i} field '{field}' cannot be empty")
    
    def _generate_recommendations(self):
        """Generate configuration recommendations"""
        ai_config = self.config.get("ai_enhancements", {})
        
        # Performance recommendations
        if ai_config.get("caching", {}).get("enabled", True):
            self.result.add_recommendation("Caching is enabled - this will improve performance")
        
        # Feature recommendations
        if not ai_config.get("advanced_scene_understanding", True):
            self.result.add_recommendation("Consider enabling advanced_scene_understanding for better task generation")
        
        if not ai_config.get("predictive_analytics", True):
            self.result.add_recommendation("Consider enabling predictive_analytics for proactive cleaning insights")
        
        # Model selection recommendations
        model_config = ai_config.get("model_selection", {})
        if not model_config:
            self.result.add_recommendation("Configure model_selection for optimal AI model usage")
