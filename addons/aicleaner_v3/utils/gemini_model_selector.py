"""
Advanced Gemini Model Selection Algorithm
Optimizes model selection based on task characteristics and rate limit availability.

This module implements the intelligent model selection framework from CLAUDE.md
to ensure optimal Gemini collaboration with maximum uptime and efficiency.
"""

import re
import time
import json
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ApiKeyInfo:
    """Information about an API key and its usage"""
    key: str
    priority: int
    last_used: Optional[datetime] = None
    consecutive_failures: int = 0
    models: Dict[str, Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.models is None:
            self.models = {}


@dataclass 
class ModelUsageInfo:
    """Usage information for a specific model on a specific key"""
    daily_usage: int = 0
    minute_usage: int = 0
    last_reset_daily: Optional[datetime] = None
    last_reset_minute: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0


class GeminiApiManager:
    """
    Singleton manager for intelligent Gemini API key cycling and rate limit tracking.
    
    Provides persistent tracking of API usage across Claude sessions and automatically
    selects the optimal API key + model combination to maximize availability.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(GeminiApiManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.data_file = Path.home() / ".aicleaner" / "gemini_api_usage.json"
        self.data_file.parent.mkdir(exist_ok=True)
        
        # API keys in priority order (from CLAUDE.md)
        self.api_keys = [
            ApiKeyInfo("AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro", priority=1),
            ApiKeyInfo("AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc", priority=2), 
            ApiKeyInfo("AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo", priority=3),
            ApiKeyInfo("AIzaSyAUrUCFIL2D4Lq5nQyfHfigHI0QgtH9oTI", priority=4)
        ]
        
        # Model rate limits (RPM, RPD)
        self.model_limits = {
            "gemini-2.5-pro": {"rpm": 5, "rpd": 100},
            "gemini-2.5-flash": {"rpm": 10, "rpd": 250},
            "gemini-2.5-flash-lite": {"rpm": 15, "rpd": 1000},
            "gemini-2.0-flash": {"rpm": 15, "rpd": 200},
            "gemini-2.0-flash-lite": {"rpm": 30, "rpd": 200}
        }
        
        self._load_usage_data()
        logger.info("GeminiApiManager initialized with persistent usage tracking")
    
    def _load_usage_data(self):
        """Load usage data from persistent storage"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                # Update API key info with loaded data
                for api_key in self.api_keys:
                    key_data = data.get("keys", {}).get(api_key.key, {})
                    api_key.last_used = datetime.fromisoformat(key_data["last_used"]) if key_data.get("last_used") else None
                    api_key.consecutive_failures = key_data.get("consecutive_failures", 0)
                    
                    # Load model usage info
                    api_key.models = {}
                    for model_name, model_data in key_data.get("models", {}).items():
                        usage_info = ModelUsageInfo(
                            daily_usage=model_data.get("daily_usage", 0),
                            minute_usage=model_data.get("minute_usage", 0),
                            last_reset_daily=datetime.fromisoformat(model_data["last_reset_daily"]) if model_data.get("last_reset_daily") else None,
                            last_reset_minute=datetime.fromisoformat(model_data["last_reset_minute"]) if model_data.get("last_reset_minute") else None,
                            last_failure=datetime.fromisoformat(model_data["last_failure"]) if model_data.get("last_failure") else None,
                            consecutive_failures=model_data.get("consecutive_failures", 0)
                        )
                        api_key.models[model_name] = usage_info
                
                logger.debug("Loaded API usage data from persistent storage")
            else:
                logger.debug("No existing usage data found, starting fresh")
                
        except Exception as e:
            logger.warning(f"Failed to load usage data: {e}, starting fresh")
    
    def _save_usage_data(self):
        """Save usage data to persistent storage"""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "keys": {}
            }
            
            for api_key in self.api_keys:
                key_data = {
                    "priority": api_key.priority,
                    "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
                    "consecutive_failures": api_key.consecutive_failures,
                    "models": {}
                }
                
                for model_name, usage_info in api_key.models.items():
                    key_data["models"][model_name] = {
                        "daily_usage": usage_info.daily_usage,
                        "minute_usage": usage_info.minute_usage,
                        "last_reset_daily": usage_info.last_reset_daily.isoformat() if usage_info.last_reset_daily else None,
                        "last_reset_minute": usage_info.last_reset_minute.isoformat() if usage_info.last_reset_minute else None,
                        "last_failure": usage_info.last_failure.isoformat() if usage_info.last_failure else None,
                        "consecutive_failures": usage_info.consecutive_failures
                    }
                
                data["keys"][api_key.key] = key_data
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.debug("Saved API usage data to persistent storage")
            
        except Exception as e:
            logger.error(f"Failed to save usage data: {e}")
    
    def _reset_usage_if_needed(self, api_key: ApiKeyInfo, model_name: str):
        """Reset usage counters if reset time has passed"""
        now = datetime.now()
        
        if model_name not in api_key.models:
            api_key.models[model_name] = ModelUsageInfo()
        
        usage_info = api_key.models[model_name]
        
        # Reset daily usage (assumes UTC midnight reset)
        if usage_info.last_reset_daily is None or (now.date() > usage_info.last_reset_daily.date()):
            usage_info.daily_usage = 0
            usage_info.last_reset_daily = now.replace(hour=0, minute=0, second=0, microsecond=0)
            logger.debug(f"Reset daily usage for {api_key.key[:10]}.../{model_name}")
        
        # Reset minute usage (every minute)
        if usage_info.last_reset_minute is None or (now - usage_info.last_reset_minute).total_seconds() >= 60:
            usage_info.minute_usage = 0
            usage_info.last_reset_minute = now.replace(second=0, microsecond=0)
    
    def get_optimal_key_model_combination(self, model_name: str) -> Optional[Tuple[str, str]]:
        """
        Get the optimal API key for the given model based on usage patterns.
        
        Returns:
            Tuple of (api_key, model_name) or None if no suitable combination available
        """
        with self._lock:
            now = datetime.now()
            available_combinations = []
            
            for api_key in self.api_keys:
                self._reset_usage_if_needed(api_key, model_name)
                
                if model_name not in api_key.models:
                    api_key.models[model_name] = ModelUsageInfo()
                
                usage_info = api_key.models[model_name]
                limits = self.model_limits.get(model_name, {"rpm": 10, "rpd": 100})
                
                # Check if this combination is available
                is_available = True
                score = 0
                
                # Check rate limits
                if usage_info.daily_usage >= limits["rpd"]:
                    is_available = False
                elif usage_info.minute_usage >= limits["rpm"]:
                    is_available = False
                
                # Check for recent failures (exponential backoff)
                if usage_info.last_failure:
                    backoff_seconds = min(60 * (2 ** usage_info.consecutive_failures), 3600)  # Max 1 hour
                    if (now - usage_info.last_failure).total_seconds() < backoff_seconds:
                        is_available = False
                
                if is_available:
                    # Calculate preference score (lower is better)
                    score = api_key.priority  # Base priority
                    score += usage_info.daily_usage / limits["rpd"] * 10  # Usage penalty
                    score += usage_info.consecutive_failures * 2  # Failure penalty
                    
                    # Prefer less recently used keys for load balancing
                    if api_key.last_used:
                        minutes_since_use = (now - api_key.last_used).total_seconds() / 60
                        score -= min(minutes_since_use / 60, 2)  # Bonus for not recently used
                    
                    available_combinations.append((score, api_key.key, model_name))
            
            if available_combinations:
                # Sort by score (lower is better) and return the best
                available_combinations.sort()
                best_score, best_key, best_model = available_combinations[0]
                logger.debug(f"Selected optimal combination: {best_key[:10]}.../{best_model} (score: {best_score:.2f})")
                return (best_key, best_model)
            
            logger.warning(f"No available API key combinations for model {model_name}")
            return None
    
    def record_success(self, api_key: str, model_name: str):
        """Record a successful API call"""
        with self._lock:
            # Find the API key object
            key_obj = next((k for k in self.api_keys if k.key == api_key), None)
            if not key_obj:
                logger.warning(f"Unknown API key for success recording: {api_key[:10]}...")
                return
            
            # Update usage tracking
            key_obj.last_used = datetime.now()
            key_obj.consecutive_failures = 0
            
            if model_name not in key_obj.models:
                key_obj.models[model_name] = ModelUsageInfo()
            
            usage_info = key_obj.models[model_name]
            usage_info.daily_usage += 1
            usage_info.minute_usage += 1
            usage_info.consecutive_failures = 0
            
            self._save_usage_data()
            logger.debug(f"Recorded success for {api_key[:10]}.../{model_name}")
    
    def record_failure(self, api_key: str, model_name: str, error_type: str = "rate_limit"):
        """Record a failed API call"""
        with self._lock:
            # Find the API key object
            key_obj = next((k for k in self.api_keys if k.key == api_key), None)
            if not key_obj:
                logger.warning(f"Unknown API key for failure recording: {api_key[:10]}...")
                return
            
            now = datetime.now()
            key_obj.consecutive_failures += 1
            
            if model_name not in key_obj.models:
                key_obj.models[model_name] = ModelUsageInfo()
            
            usage_info = key_obj.models[model_name]
            usage_info.last_failure = now
            usage_info.consecutive_failures += 1
            
            self._save_usage_data()
            logger.debug(f"Recorded failure for {api_key[:10]}.../{model_name}: {error_type}")
    
    def get_fallback_sequence(self, primary_model: str) -> List[str]:
        """Get intelligent fallback sequence for when primary model fails"""
        # Use the availability-optimized sequence from the framework
        fallback_models = [
            "gemini-2.5-flash-lite",  # 1,000 RPD - best for sustained work
            "gemini-2.0-flash-lite",  # 30 RPM - best for immediate availability
            "gemini-2.0-flash",       # 15 RPM
            "gemini-2.5-flash",       # 10 RPM
            "gemini-2.5-pro"          # 5 RPM
        ]
        
        # Remove primary model from fallback sequence
        if primary_model in fallback_models:
            fallback_models.remove(primary_model)
        
        return fallback_models
    
    def get_api_health_status(self) -> Dict[str, Any]:
        """Get health status of all API keys and models"""
        status = {
            "total_keys": len(self.api_keys),
            "healthy_keys": 0,
            "keys": {},
            "models": {},
            "last_updated": datetime.now().isoformat()
        }
        
        for api_key in self.api_keys:
            key_status = {
                "priority": api_key.priority,
                "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
                "consecutive_failures": api_key.consecutive_failures,
                "healthy": api_key.consecutive_failures < 3,
                "models": {}
            }
            
            if key_status["healthy"]:
                status["healthy_keys"] += 1
            
            for model_name, usage_info in api_key.models.items():
                limits = self.model_limits.get(model_name, {"rpm": 10, "rpd": 100})
                
                model_status = {
                    "daily_usage": usage_info.daily_usage,
                    "daily_limit": limits["rpd"],
                    "minute_usage": usage_info.minute_usage,
                    "minute_limit": limits["rpm"],
                    "usage_percentage": (usage_info.daily_usage / limits["rpd"]) * 100,
                    "available": usage_info.daily_usage < limits["rpd"] and usage_info.minute_usage < limits["rpm"],
                    "last_failure": usage_info.last_failure.isoformat() if usage_info.last_failure else None
                }
                
                key_status["models"][model_name] = model_status
                
                # Aggregate model stats
                if model_name not in status["models"]:
                    status["models"][model_name] = {
                        "total_usage": 0,
                        "available_keys": 0,
                        "total_keys": 0
                    }
                
                status["models"][model_name]["total_usage"] += usage_info.daily_usage
                status["models"][model_name]["total_keys"] += 1
                if model_status["available"]:
                    status["models"][model_name]["available_keys"] += 1
            
            status["keys"][api_key.key[:10] + "..."] = key_status
        
        return status


class GeminiModel(Enum):
    """Available Gemini models with their characteristics"""
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"  
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite"


@dataclass
class ModelCapabilities:
    """Model capabilities and rate limits"""
    model: GeminiModel
    rpm_free: int  # Requests per minute
    rpd_free: int  # Requests per day
    context_window: int  # Context window size
    thinking_enabled: bool
    best_for: List[str]
    cost_efficiency: int  # 1-5 scale (5 = most efficient)
    speed_rating: int     # 1-5 scale (5 = fastest)


class TaskType(Enum):
    """Task type classification"""
    COMPLEX_ANALYSIS = "complex_analysis"
    BALANCED_DEVELOPMENT = "balanced_development"
    QUICK_ITERATION = "quick_iteration"
    HIGH_VOLUME = "high_volume"
    SUSTAINED_WORK = "sustained_work"


class UrgencyLevel(Enum):
    """Urgency level for task completion"""
    IMMEDIATE = "immediate"      # Need response ASAP
    STANDARD = "standard"        # Normal collaboration pace
    SUSTAINED = "sustained"      # Long work session
    BATCH = "batch"             # High volume processing


@dataclass
class TaskCharacteristics:
    """Characteristics of a specific task"""
    prompt: str
    context_files: List[str] = None
    task_type: Optional[TaskType] = None
    urgency: UrgencyLevel = UrgencyLevel.STANDARD
    conversation_stage: str = "initial"  # initial, followup, mid-conversation
    expected_duration: Optional[str] = None  # "15min", "2hours", etc.


class GeminiModelSelector:
    """
    Advanced Gemini model selection with rate limit tracking and fallback management
    
    Implements the 2025 optimization framework for maximum collaboration uptime.
    """
    
    def __init__(self):
        """Initialize model selector with capabilities and intelligent API management"""
        self.model_capabilities = {
            GeminiModel.GEMINI_2_5_PRO: ModelCapabilities(
                model=GeminiModel.GEMINI_2_5_PRO,
                rpm_free=5,
                rpd_free=100,
                context_window=1048576,
                thinking_enabled=True,
                best_for=["complex reasoning", "architecture", "large codebases"],
                cost_efficiency=2,
                speed_rating=3
            ),
            GeminiModel.GEMINI_2_5_FLASH: ModelCapabilities(
                model=GeminiModel.GEMINI_2_5_FLASH,
                rpm_free=10,
                rpd_free=250,
                context_window=1048576,
                thinking_enabled=True,
                best_for=["balanced development", "code generation"],
                cost_efficiency=3,
                speed_rating=4
            ),
            GeminiModel.GEMINI_2_5_FLASH_LITE: ModelCapabilities(
                model=GeminiModel.GEMINI_2_5_FLASH_LITE,
                rpm_free=15,
                rpd_free=1000,  # Highest daily limit!
                context_window=1000000,
                thinking_enabled=False,
                best_for=["high throughput", "sustained work", "cost efficiency"],
                cost_efficiency=5,
                speed_rating=5
            ),
            GeminiModel.GEMINI_2_0_FLASH: ModelCapabilities(
                model=GeminiModel.GEMINI_2_0_FLASH,
                rpm_free=15,
                rpd_free=200,
                context_window=1048576,
                thinking_enabled=False,
                best_for=["tool use", "speed", "next-gen features"],
                cost_efficiency=4,
                speed_rating=5
            ),
            GeminiModel.GEMINI_2_0_FLASH_LITE: ModelCapabilities(
                model=GeminiModel.GEMINI_2_0_FLASH_LITE,
                rpm_free=30,  # Highest per-minute rate!
                rpd_free=200,
                context_window=1048576,
                thinking_enabled=False,
                best_for=["quick iteration", "cost efficiency", "immediate response"],
                cost_efficiency=5,
                speed_rating=5
            )
        }
        
        # Initialize intelligent API management
        self.api_manager = GeminiApiManager()
        
        # Keywords for task type classification
        self.keyword_patterns = {
            "complex": ["analyze", "architecture", "comprehensive", "review", "evaluate", "assess", "audit"],
            "medium": ["implement", "code", "refactor", "design", "create", "develop", "debug"],
            "simple": ["confirm", "quick", "simple", "yes", "no", "check", "verify", "validate"],
            "batch": ["batch", "multiple", "bulk", "mass", "generate", "process"]
        }
    
    def classify_task_type(self, characteristics: TaskCharacteristics) -> TaskType:
        """Classify task based on characteristics"""
        prompt = characteristics.prompt.lower()
        context_count = len(characteristics.context_files) if characteristics.context_files else 0
        
        # Check for explicit task type
        if characteristics.task_type:
            return characteristics.task_type
        
        # Analyze prompt for complexity indicators
        complex_score = sum(1 for kw in self.keyword_patterns["complex"] if kw in prompt)
        medium_score = sum(1 for kw in self.keyword_patterns["medium"] if kw in prompt)
        simple_score = sum(1 for kw in self.keyword_patterns["simple"] if kw in prompt)
        batch_score = sum(1 for kw in self.keyword_patterns["batch"] if kw in prompt)
        
        # Context file count influence
        if context_count > 5:
            complex_score += 2
        elif context_count > 2:
            medium_score += 1
        
        # Prompt length influence
        prompt_length = len(characteristics.prompt)
        if prompt_length > 1000:
            complex_score += 2
        elif prompt_length > 500:
            medium_score += 1
        elif prompt_length < 100:
            simple_score += 1
        
        # Urgency influence
        if characteristics.urgency == UrgencyLevel.IMMEDIATE:
            return TaskType.QUICK_ITERATION
        elif characteristics.urgency == UrgencyLevel.SUSTAINED:
            return TaskType.SUSTAINED_WORK
        elif characteristics.urgency == UrgencyLevel.BATCH:
            return TaskType.HIGH_VOLUME
        
        # Determine task type based on scores
        max_score = max(complex_score, medium_score, simple_score, batch_score)
        
        if batch_score == max_score:
            return TaskType.HIGH_VOLUME
        elif complex_score == max_score:
            return TaskType.COMPLEX_ANALYSIS
        elif simple_score == max_score:
            return TaskType.QUICK_ITERATION
        else:
            return TaskType.BALANCED_DEVELOPMENT
    
    def select_primary_model(self, characteristics: TaskCharacteristics) -> GeminiModel:
        """Select the optimal primary model for the task"""
        task_type = self.classify_task_type(characteristics)
        urgency = characteristics.urgency
        
        # Task-based model selection matrix
        if task_type == TaskType.COMPLEX_ANALYSIS:
            return GeminiModel.GEMINI_2_5_PRO
        
        elif task_type == TaskType.BALANCED_DEVELOPMENT:
            if urgency == UrgencyLevel.SUSTAINED:
                return GeminiModel.GEMINI_2_5_FLASH_LITE  # Best RPD for long sessions
            else:
                return GeminiModel.GEMINI_2_5_FLASH
        
        elif task_type == TaskType.QUICK_ITERATION:
            if urgency == UrgencyLevel.IMMEDIATE:
                return GeminiModel.GEMINI_2_0_FLASH_LITE  # Highest RPM
            else:
                return GeminiModel.GEMINI_2_5_FLASH_LITE
        
        elif task_type in [TaskType.HIGH_VOLUME, TaskType.SUSTAINED_WORK]:
            return GeminiModel.GEMINI_2_5_FLASH_LITE  # Best for sustained availability
        
        # Default fallback
        return GeminiModel.GEMINI_2_5_FLASH_LITE
    
    def get_availability_optimized_fallback_sequence(self, primary_model: GeminiModel) -> List[GeminiModel]:
        """Get fallback sequence optimized for maximum availability"""
        # Start with lite models for best availability
        base_sequence = [
            GeminiModel.GEMINI_2_5_FLASH_LITE,  # 1,000 RPD - best for sustained work
            GeminiModel.GEMINI_2_0_FLASH_LITE,  # 30 RPM - best for immediate availability
            GeminiModel.GEMINI_2_0_FLASH,       # 15 RPM, 200 RPD
            GeminiModel.GEMINI_2_5_FLASH,       # 10 RPM, 250 RPD  
            GeminiModel.GEMINI_2_5_PRO          # 5 RPM, 100 RPD
        ]
        
        # Remove primary model from sequence
        if primary_model in base_sequence:
            base_sequence.remove(primary_model)
        
        return base_sequence
    
    def calculate_model_score(self, model: GeminiModel, characteristics: TaskCharacteristics) -> float:
        """Calculate suitability score for a model given task characteristics"""
        capabilities = self.model_capabilities[model]
        score = 0.0
        
        # Task type alignment
        task_type = self.classify_task_type(characteristics)
        
        if task_type == TaskType.COMPLEX_ANALYSIS and model == GeminiModel.GEMINI_2_5_PRO:
            score += 10
        elif task_type == TaskType.BALANCED_DEVELOPMENT and model in [GeminiModel.GEMINI_2_5_FLASH, GeminiModel.GEMINI_2_5_FLASH_LITE]:
            score += 8
        elif task_type == TaskType.QUICK_ITERATION and model in [GeminiModel.GEMINI_2_0_FLASH_LITE, GeminiModel.GEMINI_2_5_FLASH_LITE]:
            score += 9
        elif task_type in [TaskType.HIGH_VOLUME, TaskType.SUSTAINED_WORK] and model == GeminiModel.GEMINI_2_5_FLASH_LITE:
            score += 10
        
        # Urgency alignment
        if characteristics.urgency == UrgencyLevel.IMMEDIATE:
            score += capabilities.rpm_free / 5  # Favor high RPM
        elif characteristics.urgency in [UrgencyLevel.SUSTAINED, UrgencyLevel.BATCH]:
            score += capabilities.rpd_free / 100  # Favor high RPD
        
        # Cost efficiency bonus
        score += capabilities.cost_efficiency
        
        # Speed rating bonus  
        score += capabilities.speed_rating
        
        return score
    
    def get_optimal_collaboration_strategy(self, characteristics: TaskCharacteristics) -> Dict[str, Any]:
        """Get comprehensive collaboration strategy for the task"""
        primary_model = self.select_primary_model(characteristics)
        fallback_sequence = self.get_availability_optimized_fallback_sequence(primary_model)
        task_type = self.classify_task_type(characteristics)
        
        # Calculate scores for all models
        model_scores = {}
        for model in GeminiModel:
            model_scores[model] = self.calculate_model_score(model, characteristics)
        
        # Determine optimal parameters
        primary_capabilities = self.model_capabilities[primary_model]
        
        strategy = {
            "primary_model": primary_model.value,
            "fallback_sequence": [model.value for model in fallback_sequence],
            "task_type": task_type.value,
            "estimated_requests": self._estimate_request_count(characteristics),
            "recommended_session_duration": self._get_recommended_duration(primary_model, characteristics),
            "thinking_budget": self._get_thinking_budget(primary_model, task_type),
            "context_optimization": self._get_context_recommendations(primary_model, characteristics),
            "availability_prediction": self._predict_availability(primary_model),
            "model_scores": {model.value: score for model, score in model_scores.items()},
            "rate_limit_strategy": {
                "total_combinations": 20,  # 4 API keys × 5 models
                "expected_success_rate": "99%+",
                "fallback_explanation": "Lite models provide sustained availability"
            }
        }
        
        return strategy
    
    def _estimate_request_count(self, characteristics: TaskCharacteristics) -> int:
        """Estimate number of requests needed for the task"""
        if characteristics.expected_duration:
            if "hour" in characteristics.expected_duration:
                hours = int(re.search(r'(\d+)', characteristics.expected_duration).group(1))
                return hours * 10  # Estimate 10 requests per hour
            elif "min" in characteristics.expected_duration:
                minutes = int(re.search(r'(\d+)', characteristics.expected_duration).group(1))
                return max(1, minutes // 5)  # Estimate 1 request per 5 minutes
        
        # Default estimates based on task type
        task_type = self.classify_task_type(characteristics)
        estimates = {
            TaskType.COMPLEX_ANALYSIS: 15,
            TaskType.BALANCED_DEVELOPMENT: 8,
            TaskType.QUICK_ITERATION: 3,
            TaskType.HIGH_VOLUME: 25,
            TaskType.SUSTAINED_WORK: 30
        }
        return estimates.get(task_type, 5)
    
    def _get_recommended_duration(self, model: GeminiModel, characteristics: TaskCharacteristics) -> str:
        """Get recommended session duration based on model capabilities"""
        capabilities = self.model_capabilities[model]
        
        if characteristics.urgency == UrgencyLevel.IMMEDIATE:
            return "15-30 minutes"
        elif characteristics.urgency == UrgencyLevel.SUSTAINED:
            if capabilities.rpd_free >= 500:
                return "2-4 hours"
            else:
                return "1-2 hours"
        else:
            return "30-60 minutes"
    
    def _get_thinking_budget(self, model: GeminiModel, task_type: TaskType) -> str:
        """Get recommended thinking budget for the model/task combination"""
        capabilities = self.model_capabilities[model]
        
        if not capabilities.thinking_enabled:
            return "low"  # Lite models don't have thinking enabled
        
        if task_type == TaskType.COMPLEX_ANALYSIS:
            return "high"
        elif task_type == TaskType.BALANCED_DEVELOPMENT:
            return "medium"
        else:
            return "low"
    
    def _get_context_recommendations(self, model: GeminiModel, characteristics: TaskCharacteristics) -> Dict[str, Any]:
        """Get context optimization recommendations for the model"""
        capabilities = self.model_capabilities[model]
        context_count = len(characteristics.context_files) if characteristics.context_files else 0
        
        recommendations = {
            "max_files": 10,
            "include_patterns": ["**/*.py"],
            "exclude_patterns": ["**/__pycache__/**", "**/test_*.py"],
            "prioritize_recent": True
        }
        
        # Adjust based on model capabilities
        if model == GeminiModel.GEMINI_2_5_PRO:
            recommendations["max_files"] = 50
            recommendations["include_framework_files"] = True
        elif model in [GeminiModel.GEMINI_2_5_FLASH_LITE, GeminiModel.GEMINI_2_0_FLASH_LITE]:
            recommendations["max_files"] = 3
            recommendations["focus_specific_files"] = True
        
        return recommendations
    
    def _predict_availability(self, model: GeminiModel) -> Dict[str, Any]:
        """Predict model availability based on rate limits"""
        capabilities = self.model_capabilities[model]
        
        # Calculate availability score based on rate limits
        rpm_score = capabilities.rpm_free / 30  # Normalize to 30 RPM max
        rpd_score = capabilities.rpd_free / 1000  # Normalize to 1000 RPD max
        
        availability_score = (rpm_score + rpd_score) / 2
        
        prediction = {
            "availability_score": round(availability_score, 2),
            "rpm_capacity": capabilities.rpm_free,
            "rpd_capacity": capabilities.rpd_free,
            "sustainability": "excellent" if capabilities.rpd_free >= 500 else "good" if capabilities.rpd_free >= 200 else "limited",
            "immediate_response": "excellent" if capabilities.rpm_free >= 20 else "good" if capabilities.rpm_free >= 10 else "limited"
        }
        
        return prediction
    
    def get_optimal_api_key_model_combination(self, characteristics: TaskCharacteristics) -> Optional[Tuple[str, str]]:
        """
        Get the optimal API key + model combination for the given task.
        
        Returns:
            Tuple of (api_key, model_name) or None if no suitable combination available
        """
        # First get the optimal model for the task
        primary_model = self.select_primary_model(characteristics)
        
        # Try to get an API key for the primary model
        combination = self.api_manager.get_optimal_key_model_combination(primary_model.value)
        if combination:
            return combination
        
        # If primary model unavailable, try fallback models
        fallback_models = self.get_availability_optimized_fallback_sequence(primary_model)
        for fallback_model in fallback_models:
            combination = self.api_manager.get_optimal_key_model_combination(fallback_model.value)
            if combination:
                logger.info(f"Using fallback model {fallback_model.value} instead of {primary_model.value}")
                return combination
        
        return None
    
    def record_api_call_success(self, api_key: str, model_name: str):
        """Record a successful API call for learning and optimization"""
        self.api_manager.record_success(api_key, model_name)
    
    def record_api_call_failure(self, api_key: str, model_name: str, error_type: str = "rate_limit"):
        """Record a failed API call for learning and optimization"""
        self.api_manager.record_failure(api_key, model_name, error_type)
    
    def get_api_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of all API keys and models"""
        return self.api_manager.get_api_health_status()
    
    def get_enhanced_collaboration_strategy(self, characteristics: TaskCharacteristics) -> Dict[str, Any]:
        """
        Get enhanced collaboration strategy that includes intelligent API key selection.
        
        This is the new recommended method that replaces get_optimal_collaboration_strategy
        with full API intelligence integration.
        """
        # Get the base strategy
        strategy = self.get_optimal_collaboration_strategy(characteristics)
        
        # Add intelligent API key selection
        optimal_combination = self.get_optimal_api_key_model_combination(characteristics)
        
        if optimal_combination:
            api_key, model_name = optimal_combination
            strategy["api_key"] = api_key
            strategy["selected_model"] = model_name
            strategy["api_intelligence"] = {
                "intelligent_selection": True,
                "selected_key_priority": next(
                    k.priority for k in self.api_manager.api_keys if k.key == api_key
                ),
                "fallback_available": len(self.api_manager.get_fallback_sequence(model_name)) > 0
            }
        else:
            strategy["api_key"] = None
            strategy["selected_model"] = None
            strategy["api_intelligence"] = {
                "intelligent_selection": False,
                "error": "No available API key combinations",
                "recommendation": "Wait for rate limits to reset or check API key status"
            }
        
        # Add API health summary
        health_status = self.get_api_health_status()
        strategy["api_health"] = {
            "healthy_keys": health_status["healthy_keys"],
            "total_keys": health_status["total_keys"],
            "availability_percentage": (health_status["healthy_keys"] / health_status["total_keys"]) * 100
        }
        
        return strategy


# Convenience functions for easy integration

def select_optimal_model(prompt: str, context_files: List[str] = None, urgency: str = "standard") -> str:
    """
    Simple function to select optimal Gemini model for a task
    
    Args:
        prompt: The task prompt/description
        context_files: List of context files (optional)
        urgency: "immediate", "standard", "sustained", or "batch"
    
    Returns:
        Model name as string (e.g., "gemini-2.5-flash-lite")
    """
    selector = GeminiModelSelector()
    
    urgency_map = {
        "immediate": UrgencyLevel.IMMEDIATE,
        "standard": UrgencyLevel.STANDARD,
        "sustained": UrgencyLevel.SUSTAINED,
        "batch": UrgencyLevel.BATCH
    }
    
    characteristics = TaskCharacteristics(
        prompt=prompt,
        context_files=context_files or [],
        urgency=urgency_map.get(urgency, UrgencyLevel.STANDARD)
    )
    
    model = selector.select_primary_model(characteristics)
    return model.value


def get_fallback_models(primary_model: str) -> List[str]:
    """Get optimal fallback sequence for a primary model"""
    selector = GeminiModelSelector()
    primary = GeminiModel(primary_model)
    fallback_sequence = selector.get_availability_optimized_fallback_sequence(primary)
    return [model.value for model in fallback_sequence]


def get_collaboration_strategy(prompt: str, context_files: List[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Get comprehensive collaboration strategy for a task with intelligent API cycling.
    
    This function now includes full API intelligence for seamless Gemini collaboration.
    """
    selector = GeminiModelSelector()
    
    characteristics = TaskCharacteristics(
        prompt=prompt,
        context_files=context_files or [],
        urgency=UrgencyLevel(kwargs.get("urgency", "standard")),
        conversation_stage=kwargs.get("conversation_stage", "initial"),
        expected_duration=kwargs.get("expected_duration")
    )
    
    # Use the enhanced strategy with API intelligence
    return selector.get_enhanced_collaboration_strategy(characteristics)


def get_optimal_api_key_model(prompt: str, context_files: List[str] = None, urgency: str = "standard") -> Optional[Tuple[str, str]]:
    """
    Get the optimal API key + model combination for a task.
    
    Args:
        prompt: The task prompt/description
        context_files: List of context files (optional) 
        urgency: "immediate", "standard", "sustained", or "batch"
    
    Returns:
        Tuple of (api_key, model_name) or None if no combination available
    """
    selector = GeminiModelSelector()
    
    urgency_map = {
        "immediate": UrgencyLevel.IMMEDIATE,
        "standard": UrgencyLevel.STANDARD,
        "sustained": UrgencyLevel.SUSTAINED,
        "batch": UrgencyLevel.BATCH
    }
    
    characteristics = TaskCharacteristics(
        prompt=prompt,
        context_files=context_files or [],
        urgency=urgency_map.get(urgency, UrgencyLevel.STANDARD)
    )
    
    return selector.get_optimal_api_key_model_combination(characteristics)


def record_gemini_success(api_key: str, model_name: str):
    """
    Record a successful Gemini API call for intelligent learning.
    
    This should be called after every successful API interaction to improve
    the selection algorithm's accuracy.
    """
    selector = GeminiModelSelector()
    selector.record_api_call_success(api_key, model_name)


def record_gemini_failure(api_key: str, model_name: str, error_type: str = "rate_limit"):
    """
    Record a failed Gemini API call for intelligent learning.
    
    This should be called after every failed API interaction to improve
    the selection algorithm's accuracy and implement proper backoff.
    """
    selector = GeminiModelSelector()
    selector.record_api_call_failure(api_key, model_name, error_type)


def get_gemini_health_status() -> Dict[str, Any]:
    """
    Get comprehensive health status of all Gemini API keys and models.
    
    Returns detailed information about usage, availability, and health of all
    API key + model combinations.
    """
    selector = GeminiModelSelector()
    return selector.get_api_health_status()


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    selector = GeminiModelSelector()
    
    # Test different scenarios
    test_cases = [
        {
            "prompt": "Perform comprehensive architectural review of the AI provider system",
            "context_files": ["ai/providers/*.py", "core/*.py"],
            "urgency": "standard"
        },
        {
            "prompt": "Quick fix for the bug in line 42",
            "context_files": ["utils/simple_health_monitor.py"],
            "urgency": "immediate"
        },
        {
            "prompt": "Generate documentation for all API endpoints", 
            "context_files": ["api/*.py"],
            "urgency": "batch"
        },
        {
            "prompt": "Extended development session for Phase 3 features",
            "context_files": ["addons/aicleaner_v3/**/*.py"],
            "urgency": "sustained"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        strategy = get_collaboration_strategy(**test_case)
        print(f"Primary Model: {strategy['primary_model']}")
        print(f"Task Type: {strategy['task_type']}")
        print(f"Fallback Sequence: {strategy['fallback_sequence'][:2]}...")  # Show first 2
        print(f"Availability Prediction: {strategy['availability_prediction']['sustainability']}")