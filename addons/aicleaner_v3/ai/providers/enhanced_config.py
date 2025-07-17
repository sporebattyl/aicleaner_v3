"""
Enhanced AI Provider Configuration
Cloud Integration Optimization - Phase 1

Advanced configuration system with content-type awareness, dynamic timeouts,
and intelligent provider capabilities for cloud API optimization.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta


class ContentType(Enum):
    """Supported content types for AI processing"""
    TEXT = "text"
    IMAGE = "image"
    CODE = "code"
    MULTIMODAL = "multimodal"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    STRUCTURED_DATA = "structured_data"


class ProviderTier(Enum):
    """Provider tier classification for failover optimization"""
    CLOUD_PREMIUM = "cloud_premium"       # High-performance cloud APIs
    CLOUD_STANDARD = "cloud_standard"     # Standard cloud APIs
    LOCAL_GPU = "local_gpu"               # Local GPU processing
    LOCAL_CPU = "local_cpu"               # Local CPU processing


class ProcessingPriority(Enum):
    """Processing priority levels for request routing"""
    CRITICAL = 1      # Security, safety-critical tasks
    HIGH = 2          # Real-time user interactions
    NORMAL = 3        # Standard automation tasks
    LOW = 4           # Background processing
    BATCH = 5         # Batch/scheduled processing


@dataclass
class ContentTypeConfig:
    """Configuration for specific content type processing"""
    timeout_seconds: float = 10.0
    max_retries: int = 2
    cost_weight: float = 1.0              # Cost multiplier for this content type
    quality_threshold: float = 0.8        # Minimum acceptable quality score
    preferred_providers: List[str] = field(default_factory=list)
    fallback_providers: List[str] = field(default_factory=list)
    cache_ttl_seconds: int = 3600         # Cache time-to-live
    requires_privacy_pipeline: bool = False


@dataclass
class ProviderCapability:
    """Detailed provider capabilities for content-aware routing"""
    content_types: Set[ContentType] = field(default_factory=set)
    max_tokens: int = 4096
    supports_streaming: bool = False
    supports_function_calling: bool = False
    vision_capabilities: bool = False
    code_generation_quality: float = 0.8   # 0-1 quality score
    instruction_following: float = 0.9      # 0-1 quality score
    multimodal_support: bool = False
    latency_profile: str = "standard"       # "fast", "standard", "slow"
    cost_efficiency: str = "medium"         # "low", "medium", "high"
    reliability_score: float = 0.95        # 0-1 reliability score


@dataclass
class DynamicTimeout:
    """Dynamic timeout configuration based on performance history"""
    base_timeout: float = 10.0
    min_timeout: float = 3.0
    max_timeout: float = 30.0
    adjustment_factor: float = 0.1         # How much to adjust based on performance
    percentile_target: float = 0.95        # Target percentile for timeout calculation
    history_window: int = 100              # Number of requests to consider for adjustment


@dataclass
class CostOptimization:
    """Cost optimization configuration"""
    daily_budget: float = 50.0
    cost_per_token_limit: float = 0.0001
    prefer_cheaper_providers: bool = True
    cost_quality_tradeoff: float = 0.7     # 0=cost only, 1=quality only
    budget_alerts: List[float] = field(default_factory=lambda: [0.5, 0.8, 0.95])


@dataclass
class FailoverConfig:
    """Advanced failover configuration"""
    enable_predictive_failover: bool = True
    response_time_threshold: float = 8.0   # Switch providers if response time exceeds
    failure_rate_threshold: float = 0.3    # Switch if failure rate exceeds 30%
    circuit_breaker_threshold: int = 3
    circuit_breaker_timeout: float = 30.0
    local_fallback_enabled: bool = True
    cross_tier_failover: bool = True       # Allow cloud → local failover


class EnhancedConfig:
    """Simple enhanced config alias for testing"""
    
    def __init__(self):
        self.providers = {
            "openai": {"enabled": True, "priority": 1},
            "anthropic": {"enabled": True, "priority": 2},
            "google": {"enabled": True, "priority": 3}
        }
        self.caching_enabled = True
        self.performance_monitoring = True

class EnhancedAIProviderConfiguration:
    """
    Enhanced AI Provider Configuration with content-type awareness,
    dynamic timeouts, and intelligent optimization capabilities.
    
    Features:
    - Content-type specific configurations
    - Dynamic timeout adjustment based on performance
    - Advanced cost optimization
    - Intelligent failover strategies
    - Provider capability mapping
    """
    
    def __init__(
        self,
        name: str,
        provider_tier: ProviderTier = ProviderTier.CLOUD_STANDARD,
        enabled: bool = True,
        priority: int = 1,
        api_key: str = "",
        model_name: str = "",
        base_url: Optional[str] = None,
        capabilities: Optional[ProviderCapability] = None,
        content_configs: Optional[Dict[ContentType, ContentTypeConfig]] = None,
        dynamic_timeout: Optional[DynamicTimeout] = None,
        cost_optimization: Optional[CostOptimization] = None,
        failover_config: Optional[FailoverConfig] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.provider_tier = provider_tier
        self.enabled = enabled
        self.priority = priority
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        
        # Enhanced configurations
        self.capabilities = capabilities or ProviderCapability()
        self.content_configs = content_configs or self._default_content_configs()
        self.dynamic_timeout = dynamic_timeout or DynamicTimeout()
        self.cost_optimization = cost_optimization or CostOptimization()
        self.failover_config = failover_config or FailoverConfig()
        self.custom_config = custom_config or {}
        
        # Performance tracking
        self.performance_history: Dict[ContentType, List[Tuple[float, bool]]] = {}
        self.cost_tracking: Dict[ContentType, List[float]] = {}
        self.last_updated = datetime.now()
        
        # Logger
        self.logger = logging.getLogger(f"enhanced_config.{name}")
        
    def _default_content_configs(self) -> Dict[ContentType, ContentTypeConfig]:
        """Create default content type configurations"""
        return {
            ContentType.TEXT: ContentTypeConfig(
                timeout_seconds=5.0,
                max_retries=2,
                cost_weight=1.0,
                cache_ttl_seconds=3600
            ),
            ContentType.IMAGE: ContentTypeConfig(
                timeout_seconds=8.0,
                max_retries=2,
                cost_weight=2.0,
                cache_ttl_seconds=7200
            ),
            ContentType.CODE: ContentTypeConfig(
                timeout_seconds=10.0,
                max_retries=3,
                cost_weight=1.5,
                quality_threshold=0.9,
                cache_ttl_seconds=1800
            ),
            ContentType.MULTIMODAL: ContentTypeConfig(
                timeout_seconds=12.0,
                max_retries=2,
                cost_weight=3.0,
                cache_ttl_seconds=1800
            ),
            ContentType.DOCUMENT: ContentTypeConfig(
                timeout_seconds=15.0,
                max_retries=2,
                cost_weight=2.5,
                cache_ttl_seconds=14400
            )
        }
    
    def get_timeout(self, content_type: ContentType, priority: ProcessingPriority = ProcessingPriority.NORMAL) -> float:
        """
        Get optimized timeout for content type and priority.
        
        Args:
            content_type: Type of content being processed
            priority: Processing priority level
            
        Returns:
            Optimized timeout in seconds
        """
        # Get base timeout from content config
        content_config = self.content_configs.get(content_type, ContentTypeConfig())
        base_timeout = content_config.timeout_seconds
        
        # Apply dynamic timeout adjustment
        adjusted_timeout = self._calculate_dynamic_timeout(content_type, base_timeout)
        
        # Apply priority multiplier
        priority_multipliers = {
            ProcessingPriority.CRITICAL: 0.7,    # Faster timeout for critical tasks
            ProcessingPriority.HIGH: 0.8,
            ProcessingPriority.NORMAL: 1.0,
            ProcessingPriority.LOW: 1.3,
            ProcessingPriority.BATCH: 1.5
        }
        
        final_timeout = adjusted_timeout * priority_multipliers.get(priority, 1.0)
        
        # Ensure timeout is within bounds
        return max(
            self.dynamic_timeout.min_timeout,
            min(final_timeout, self.dynamic_timeout.max_timeout)
        )
    
    def _calculate_dynamic_timeout(self, content_type: ContentType, base_timeout: float) -> float:
        """Calculate dynamic timeout based on performance history"""
        if content_type not in self.performance_history:
            return base_timeout
        
        history = self.performance_history[content_type]
        if len(history) < 10:  # Need minimum history for adjustment
            return base_timeout
        
        # Get recent successful response times
        recent_times = [
            response_time for response_time, success in history[-self.dynamic_timeout.history_window:]
            if success
        ]
        
        if not recent_times:
            return base_timeout
        
        # Calculate target timeout based on percentile
        recent_times.sort()
        percentile_index = int(len(recent_times) * self.dynamic_timeout.percentile_target)
        target_timeout = recent_times[min(percentile_index, len(recent_times) - 1)]
        
        # Apply adjustment factor
        adjustment = (target_timeout - base_timeout) * self.dynamic_timeout.adjustment_factor
        return base_timeout + adjustment
    
    def can_handle_content(self, content_type: ContentType) -> bool:
        """Check if provider can handle the specified content type"""
        return content_type in self.capabilities.content_types
    
    def get_cost_estimate(self, content_type: ContentType, input_size: int) -> float:
        """
        Estimate cost for processing content of given type and size.
        
        Args:
            content_type: Type of content
            input_size: Size in tokens/pixels/etc
            
        Returns:
            Estimated cost in USD
        """
        content_config = self.content_configs.get(content_type, ContentTypeConfig())
        base_cost = input_size * 0.0001  # Base cost per token
        
        # Apply content type multiplier
        adjusted_cost = base_cost * content_config.cost_weight
        
        # Apply provider efficiency factor
        efficiency_multipliers = {
            "low": 0.7,
            "medium": 1.0,
            "high": 1.5
        }
        efficiency_factor = efficiency_multipliers.get(self.capabilities.cost_efficiency, 1.0)
        
        return adjusted_cost * efficiency_factor
    
    def update_performance_history(self, content_type: ContentType, response_time: float, 
                                 success: bool, cost: float = 0.0):
        """Update performance history for dynamic optimization"""
        if content_type not in self.performance_history:
            self.performance_history[content_type] = []
        if content_type not in self.cost_tracking:
            self.cost_tracking[content_type] = []
        
        # Add performance data
        self.performance_history[content_type].append((response_time, success))
        self.cost_tracking[content_type].append(cost)
        
        # Limit history size
        max_history = self.dynamic_timeout.history_window * 2
        if len(self.performance_history[content_type]) > max_history:
            self.performance_history[content_type] = self.performance_history[content_type][-max_history:]
        if len(self.cost_tracking[content_type]) > max_history:
            self.cost_tracking[content_type] = self.cost_tracking[content_type][-max_history:]
        
        self.last_updated = datetime.now()
    
    def get_performance_score(self, content_type: ContentType) -> float:
        """
        Calculate performance score for content type (0-1, higher is better).
        Combines speed, reliability, and cost efficiency.
        """
        if content_type not in self.performance_history:
            return 0.5  # Default neutral score
        
        history = self.performance_history[content_type]
        if not history:
            return 0.5
        
        # Calculate success rate
        recent_history = history[-50:]  # Last 50 requests
        success_rate = sum(1 for _, success in recent_history if success) / len(recent_history)
        
        # Calculate average response time score (lower is better)
        successful_times = [time for time, success in recent_history if success]
        if successful_times:
            avg_time = sum(successful_times) / len(successful_times)
            content_config = self.content_configs.get(content_type, ContentTypeConfig())
            time_score = max(0, 1 - (avg_time / content_config.timeout_seconds))
        else:
            time_score = 0
        
        # Calculate cost efficiency score
        if content_type in self.cost_tracking and self.cost_tracking[content_type]:
            recent_costs = self.cost_tracking[content_type][-50:]
            avg_cost = sum(recent_costs) / len(recent_costs)
            cost_score = max(0, 1 - (avg_cost / 0.01))  # Normalize against $0.01 baseline
        else:
            cost_score = 0.5
        
        # Weighted combination
        performance_score = (
            success_rate * 0.4 +
            time_score * 0.4 +
            cost_score * 0.2
        )
        
        return min(1.0, max(0.0, performance_score))
    
    def should_use_for_content(self, content_type: ContentType, priority: ProcessingPriority = ProcessingPriority.NORMAL) -> bool:
        """
        Determine if this provider should be used for the given content type and priority.
        
        Args:
            content_type: Type of content to process
            priority: Processing priority
            
        Returns:
            True if provider is suitable
        """
        # Check basic capability
        if not self.can_handle_content(content_type):
            return False
        
        # Check if provider is enabled and available
        if not self.enabled:
            return False
        
        # Check performance score threshold
        performance_score = self.get_performance_score(content_type)
        content_config = self.content_configs.get(content_type, ContentTypeConfig())
        
        if performance_score < content_config.quality_threshold:
            return False
        
        # Check budget constraints for cost-sensitive priorities
        if priority in [ProcessingPriority.LOW, ProcessingPriority.BATCH]:
            daily_cost = sum(sum(costs) for costs in self.cost_tracking.values())
            if daily_cost >= self.cost_optimization.daily_budget * 0.9:  # 90% of budget used
                return False
        
        return True
    
    def get_optimization_metrics(self) -> Dict[str, Any]:
        """Get comprehensive optimization metrics"""
        metrics = {
            "provider_name": self.name,
            "provider_tier": self.provider_tier.value,
            "last_updated": self.last_updated.isoformat(),
            "content_type_performance": {},
            "cost_summary": {},
            "dynamic_timeouts": {}
        }
        
        # Content type performance
        for content_type in ContentType:
            if content_type in self.performance_history:
                metrics["content_type_performance"][content_type.value] = {
                    "performance_score": self.get_performance_score(content_type),
                    "request_count": len(self.performance_history[content_type]),
                    "can_handle": self.can_handle_content(content_type)
                }
        
        # Cost summary
        total_cost = sum(sum(costs) for costs in self.cost_tracking.values())
        metrics["cost_summary"] = {
            "total_cost": total_cost,
            "daily_budget": self.cost_optimization.daily_budget,
            "budget_utilization": total_cost / self.cost_optimization.daily_budget,
            "cost_efficiency": self.capabilities.cost_efficiency
        }
        
        # Dynamic timeouts
        for content_type in ContentType:
            metrics["dynamic_timeouts"][content_type.value] = self.get_timeout(content_type)
        
        return metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization"""
        return {
            "name": self.name,
            "provider_tier": self.provider_tier.value,
            "enabled": self.enabled,
            "priority": self.priority,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "capabilities": {
                "content_types": [ct.value for ct in self.capabilities.content_types],
                "max_tokens": self.capabilities.max_tokens,
                "supports_streaming": self.capabilities.supports_streaming,
                "vision_capabilities": self.capabilities.vision_capabilities,
                "code_generation_quality": self.capabilities.code_generation_quality,
                "latency_profile": self.capabilities.latency_profile,
                "cost_efficiency": self.capabilities.cost_efficiency,
                "reliability_score": self.capabilities.reliability_score
            },
            "optimization_metrics": self.get_optimization_metrics()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedAIProviderConfiguration':
        """Create configuration from dictionary"""
        capabilities = ProviderCapability(
            content_types=set(ContentType(ct) for ct in data.get("capabilities", {}).get("content_types", [])),
            max_tokens=data.get("capabilities", {}).get("max_tokens", 4096),
            supports_streaming=data.get("capabilities", {}).get("supports_streaming", False),
            vision_capabilities=data.get("capabilities", {}).get("vision_capabilities", False),
            code_generation_quality=data.get("capabilities", {}).get("code_generation_quality", 0.8),
            latency_profile=data.get("capabilities", {}).get("latency_profile", "standard"),
            cost_efficiency=data.get("capabilities", {}).get("cost_efficiency", "medium"),
            reliability_score=data.get("capabilities", {}).get("reliability_score", 0.95)
        )
        
        return cls(
            name=data["name"],
            provider_tier=ProviderTier(data.get("provider_tier", "cloud_standard")),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 1),
            model_name=data.get("model_name", ""),
            base_url=data.get("base_url"),
            capabilities=capabilities
        )