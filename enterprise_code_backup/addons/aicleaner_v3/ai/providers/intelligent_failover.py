"""
Intelligent Failover System
Cloud Integration Optimization - Phase 5

Advanced failover system with predictive capabilities, intelligent cloud→local
routing, and optimized recovery strategies for cloud API optimization.
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import threading

from .enhanced_config import (
    ContentType, ProcessingPriority, ProviderTier, 
    EnhancedAIProviderConfiguration
)
from .content_analyzer import ContentAnalysisResult
from ..base_provider import AIRequest, AIResponse, BaseAIProvider, AIProviderStatus, AIProviderError


class FailoverReason(Enum):
    """Reasons for failover activation"""
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    RESPONSE_TIMEOUT = "response_timeout"
    QUALITY_THRESHOLD = "quality_threshold"
    COST_BUDGET_EXCEEDED = "cost_budget_exceeded"
    PREDICTIVE_PERFORMANCE = "predictive_performance"
    CIRCUIT_BREAKER = "circuit_breaker"
    MANUAL_OVERRIDE = "manual_override"
    PRIVACY_REQUIREMENT = "privacy_requirement"


class FailoverStrategy(Enum):
    """Failover strategies"""
    TIER_BASED = "tier_based"                    # Cloud Premium → Cloud Standard → Local GPU → Local CPU
    CAPABILITY_PRESERVING = "capability_preserving"  # Maintain content type capabilities
    COST_AWARE = "cost_aware"                    # Consider cost implications
    PERFORMANCE_OPTIMIZED = "performance_optimized"  # Optimize for speed
    PRIVACY_PRESERVING = "privacy_preserving"   # Ensure privacy requirements


@dataclass
class FailoverTarget:
    """Failover target configuration"""
    provider_name: str
    provider_tier: ProviderTier
    expected_performance: float = 0.5  # Expected performance score (0-1)
    cost_multiplier: float = 1.0       # Cost multiplier vs original
    capability_match: float = 1.0      # Capability match score (0-1)
    privacy_safe: bool = True          # Maintains privacy requirements
    estimated_delay: float = 0.0       # Additional delay in seconds


@dataclass
class FailoverEvent:
    """Failover event record"""
    timestamp: float
    original_provider: str
    target_provider: str
    reason: FailoverReason
    content_type: ContentType
    success: bool
    performance_impact: float = 0.0    # Performance change (-1 to 1)
    cost_impact: float = 0.0           # Cost change (positive = more expensive)
    recovery_time: float = 0.0         # Time to recover in seconds


@dataclass
class ProviderHealth:
    """Provider health monitoring"""
    provider_name: str
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=50))
    error_types: defaultdict = field(default_factory=lambda: defaultdict(int))
    health_score: float = 1.0          # 0-1 health score
    degradation_trend: float = 0.0     # -1 to 1, negative = degrading


class IntelligentFailoverManager:
    """
    Intelligent Failover Manager with predictive capabilities and optimized
    cloud→local routing for maximum reliability and performance.
    
    Features:
    - Predictive failover based on performance trends
    - Intelligent cloud→local routing with capability preservation
    - Multi-tier failover strategies
    - Cost-aware failover decisions
    - Privacy-preserving failover paths
    - Automatic recovery detection and management
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None,
        strategy: FailoverStrategy = FailoverStrategy.TIER_BASED
    ):
        """
        Initialize Intelligent Failover Manager.
        
        Args:
            config: Configuration dictionary
            strategy: Failover strategy to use
        """
        self.config = config or {}
        self.strategy = strategy
        self.logger = logging.getLogger("intelligent_failover")
        
        # Provider health tracking
        self.provider_health: Dict[str, ProviderHealth] = {}
        
        # Failover configuration
        self.enable_predictive_failover = self.config.get("enable_predictive_failover", True)
        self.predictive_threshold = self.config.get("predictive_threshold", 0.3)  # Health score threshold
        self.max_consecutive_failures = self.config.get("max_consecutive_failures", 3)
        self.circuit_breaker_timeout = self.config.get("circuit_breaker_timeout", 60.0)  # seconds
        
        # Performance thresholds
        self.response_time_threshold = self.config.get("response_time_threshold", 10.0)  # seconds
        self.quality_threshold = self.config.get("quality_threshold", 0.7)
        self.degradation_threshold = self.config.get("degradation_threshold", -0.3)  # 30% degradation
        
        # Failover history and analytics
        self.failover_history: List[FailoverEvent] = []
        self.max_history_size = self.config.get("max_history_size", 1000)
        
        # Tier-based failover mapping
        self.tier_fallback_order = [
            ProviderTier.CLOUD_PREMIUM,
            ProviderTier.CLOUD_STANDARD,
            ProviderTier.LOCAL_GPU,
            ProviderTier.LOCAL_CPU
        ]
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Start health monitoring
        self._start_health_monitoring()
        
        self.logger.info(f"Intelligent Failover Manager initialized with strategy: {strategy.value}")
    
    def _start_health_monitoring(self):
        """Start background health monitoring"""
        def health_monitor():
            while True:
                try:
                    self._update_health_scores()
                    self._detect_degradation_trends()
                    self._cleanup_old_history()
                    time.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {e}")
                    time.sleep(60)  # Retry after 1 minute on error
        
        monitor_thread = threading.Thread(target=health_monitor, daemon=True)
        monitor_thread.start()
    
    async def should_failover(
        self,
        provider_name: str,
        provider_config: EnhancedAIProviderConfiguration,
        content_analysis: ContentAnalysisResult,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[FailoverReason]]:
        """
        Determine if failover should be triggered for provider.
        
        Args:
            provider_name: Provider to check
            provider_config: Provider configuration
            content_analysis: Content analysis result
            context: Additional context
            
        Returns:
            Tuple of (should_failover, reason)
        """
        try:
            # Check provider availability
            if not provider_config.enabled:
                return True, FailoverReason.PROVIDER_UNAVAILABLE
            
            # Get provider health
            health = self.provider_health.get(provider_name)
            if not health:
                # No health data, allow provider to be used
                return False, None
            
            # Check consecutive failures
            if health.consecutive_failures >= self.max_consecutive_failures:
                return True, FailoverReason.CIRCUIT_BREAKER
            
            # Check health score for predictive failover
            if self.enable_predictive_failover and health.health_score < self.predictive_threshold:
                return True, FailoverReason.PREDICTIVE_PERFORMANCE
            
            # Check degradation trend
            if health.degradation_trend < self.degradation_threshold:
                return True, FailoverReason.PREDICTIVE_PERFORMANCE
            
            # Check recent response times
            if health.response_times:
                recent_avg = statistics.mean(list(health.response_times)[-10:])  # Last 10 requests
                timeout = provider_config.get_timeout(content_analysis.content_type)
                if recent_avg > timeout * 0.8:  # 80% of timeout threshold
                    return True, FailoverReason.RESPONSE_TIMEOUT
            
            # Check privacy requirements
            if content_analysis.privacy_sensitive and context:
                require_local = context.get("require_local_processing", False)
                if require_local and provider_config.provider_tier in [ProviderTier.CLOUD_PREMIUM, ProviderTier.CLOUD_STANDARD]:
                    return True, FailoverReason.PRIVACY_REQUIREMENT
            
            # Check cost budget
            if context and context.get("budget_constraint"):
                estimated_cost = provider_config.get_cost_estimate(
                    content_analysis.content_type,
                    content_analysis.size_estimate
                )
                if estimated_cost > context["budget_constraint"]:
                    return True, FailoverReason.COST_BUDGET_EXCEEDED
            
            return False, None
            
        except Exception as e:
            self.logger.error(f"Failover check error for {provider_name}: {e}")
            return False, None
    
    async def get_failover_targets(
        self,
        failed_provider: str,
        failed_config: EnhancedAIProviderConfiguration,
        all_configs: Dict[str, EnhancedAIProviderConfiguration],
        content_analysis: ContentAnalysisResult,
        context: Optional[Dict[str, Any]] = None
    ) -> List[FailoverTarget]:
        """
        Get ordered list of failover targets for failed provider.
        
        Args:
            failed_provider: Name of failed provider
            failed_config: Configuration of failed provider
            all_configs: All available provider configurations
            content_analysis: Content analysis result
            context: Additional context
            
        Returns:
            Ordered list of failover targets
        """
        targets = []
        
        try:
            # Filter available providers (excluding failed one)
            available_configs = {
                name: config for name, config in all_configs.items()
                if name != failed_provider and config.enabled
            }
            
            if self.strategy == FailoverStrategy.TIER_BASED:
                targets = self._get_tier_based_targets(
                    failed_config, available_configs, content_analysis
                )
            
            elif self.strategy == FailoverStrategy.CAPABILITY_PRESERVING:
                targets = self._get_capability_preserving_targets(
                    failed_config, available_configs, content_analysis
                )
            
            elif self.strategy == FailoverStrategy.COST_AWARE:
                targets = self._get_cost_aware_targets(
                    failed_config, available_configs, content_analysis, context
                )
            
            elif self.strategy == FailoverStrategy.PERFORMANCE_OPTIMIZED:
                targets = self._get_performance_optimized_targets(
                    failed_config, available_configs, content_analysis
                )
            
            elif self.strategy == FailoverStrategy.PRIVACY_PRESERVING:
                targets = self._get_privacy_preserving_targets(
                    failed_config, available_configs, content_analysis, context
                )
            
            # Filter out unhealthy targets
            healthy_targets = []
            for target in targets:
                health = self.provider_health.get(target.provider_name)
                if not health or health.health_score > 0.3:  # Minimum health threshold
                    healthy_targets.append(target)
            
            self.logger.info(
                json.dumps({
                    "event": "failover_targets_generated",
                    "failed_provider": failed_provider,
                    "strategy": self.strategy.value,
                    "content_type": content_analysis.content_type.value,
                    "target_count": len(healthy_targets),
                    "targets": [t.provider_name for t in healthy_targets[:3]]  # Top 3
                })
            )
            
            return healthy_targets
            
        except Exception as e:
            self.logger.error(f"Error generating failover targets: {e}")
            return []
    
    def _get_tier_based_targets(
        self,
        failed_config: EnhancedAIProviderConfiguration,
        available_configs: Dict[str, EnhancedAIProviderConfiguration],
        content_analysis: ContentAnalysisResult
    ) -> List[FailoverTarget]:
        """Generate tier-based failover targets"""
        targets = []
        failed_tier_index = self.tier_fallback_order.index(failed_config.provider_tier)
        
        # Try same tier first (different provider)
        same_tier_providers = [
            (name, config) for name, config in available_configs.items()
            if config.provider_tier == failed_config.provider_tier and 
               config.can_handle_content(content_analysis.content_type)
        ]
        
        for name, config in same_tier_providers:
            health = self.provider_health.get(name)
            expected_performance = health.health_score if health else 0.5
            
            targets.append(FailoverTarget(
                provider_name=name,
                provider_tier=config.provider_tier,
                expected_performance=expected_performance,
                cost_multiplier=1.0,  # Same tier, similar cost
                capability_match=1.0,  # Same tier, same capabilities
                estimated_delay=1.0   # Minimal delay for same tier
            ))
        
        # Then try lower tiers
        for tier in self.tier_fallback_order[failed_tier_index + 1:]:
            tier_providers = [
                (name, config) for name, config in available_configs.items()
                if config.provider_tier == tier and 
                   config.can_handle_content(content_analysis.content_type)
            ]
            
            for name, config in tier_providers:
                health = self.provider_health.get(name)
                expected_performance = health.health_score if health else 0.5
                
                # Calculate cost and performance adjustments
                cost_multiplier = self._calculate_tier_cost_multiplier(failed_config.provider_tier, tier)
                capability_match = self._calculate_capability_match(failed_config, config, content_analysis)
                estimated_delay = self._calculate_tier_delay(failed_config.provider_tier, tier)
                
                targets.append(FailoverTarget(
                    provider_name=name,
                    provider_tier=tier,
                    expected_performance=expected_performance * capability_match,
                    cost_multiplier=cost_multiplier,
                    capability_match=capability_match,
                    privacy_safe=tier in [ProviderTier.LOCAL_GPU, ProviderTier.LOCAL_CPU],
                    estimated_delay=estimated_delay
                ))
        
        # Sort by expected performance (descending)
        targets.sort(key=lambda x: x.expected_performance, reverse=True)
        return targets
    
    def _get_capability_preserving_targets(
        self,
        failed_config: EnhancedAIProviderConfiguration,
        available_configs: Dict[str, EnhancedAIProviderConfiguration],
        content_analysis: ContentAnalysisResult
    ) -> List[FailoverTarget]:
        """Generate capability-preserving failover targets"""
        targets = []
        
        for name, config in available_configs.items():
            if not config.can_handle_content(content_analysis.content_type):
                continue
            
            capability_match = self._calculate_capability_match(failed_config, config, content_analysis)
            
            # Only consider providers with high capability match
            if capability_match < 0.7:
                continue
            
            health = self.provider_health.get(name)
            expected_performance = health.health_score if health else 0.5
            
            targets.append(FailoverTarget(
                provider_name=name,
                provider_tier=config.provider_tier,
                expected_performance=expected_performance * capability_match,
                cost_multiplier=self._calculate_tier_cost_multiplier(failed_config.provider_tier, config.provider_tier),
                capability_match=capability_match,
                privacy_safe=config.provider_tier in [ProviderTier.LOCAL_GPU, ProviderTier.LOCAL_CPU]
            ))
        
        # Sort by capability match first, then performance
        targets.sort(key=lambda x: (x.capability_match, x.expected_performance), reverse=True)
        return targets
    
    def _get_cost_aware_targets(
        self,
        failed_config: EnhancedAIProviderConfiguration,
        available_configs: Dict[str, EnhancedAIProviderConfiguration],
        content_analysis: ContentAnalysisResult,
        context: Optional[Dict[str, Any]]
    ) -> List[FailoverTarget]:
        """Generate cost-aware failover targets"""
        targets = []
        budget_constraint = context.get("budget_constraint") if context else None
        
        for name, config in available_configs.items():
            if not config.can_handle_content(content_analysis.content_type):
                continue
            
            # Calculate estimated cost
            estimated_cost = config.get_cost_estimate(
                content_analysis.content_type,
                content_analysis.size_estimate
            )
            
            # Skip if over budget
            if budget_constraint and estimated_cost > budget_constraint:
                continue
            
            health = self.provider_health.get(name)
            expected_performance = health.health_score if health else 0.5
            capability_match = self._calculate_capability_match(failed_config, config, content_analysis)
            
            # Calculate cost efficiency score
            cost_efficiency = 1.0 / (estimated_cost + 0.001)  # Avoid division by zero
            
            targets.append(FailoverTarget(
                provider_name=name,
                provider_tier=config.provider_tier,
                expected_performance=expected_performance * capability_match * cost_efficiency,
                cost_multiplier=estimated_cost / max(0.001, failed_config.get_cost_estimate(content_analysis.content_type, content_analysis.size_estimate)),
                capability_match=capability_match,
                privacy_safe=config.provider_tier in [ProviderTier.LOCAL_GPU, ProviderTier.LOCAL_CPU]
            ))
        
        # Sort by cost efficiency and performance
        targets.sort(key=lambda x: x.expected_performance, reverse=True)
        return targets
    
    def _get_performance_optimized_targets(
        self,
        failed_config: EnhancedAIProviderConfiguration,
        available_configs: Dict[str, EnhancedAIProviderConfiguration],
        content_analysis: ContentAnalysisResult
    ) -> List[FailoverTarget]:
        """Generate performance-optimized failover targets"""
        targets = []
        
        for name, config in available_configs.items():
            if not config.can_handle_content(content_analysis.content_type):
                continue
            
            health = self.provider_health.get(name)
            if not health:
                continue
            
            # Focus on response time and success rate
            response_time_score = 1.0
            if health.response_times:
                avg_time = statistics.mean(health.response_times)
                timeout = config.get_timeout(content_analysis.content_type)
                response_time_score = max(0.1, 1.0 - (avg_time / timeout))
            
            success_rate = health.consecutive_successes / max(1, health.consecutive_successes + health.consecutive_failures)
            
            performance_score = (response_time_score * 0.6 + success_rate * 0.4) * health.health_score
            capability_match = self._calculate_capability_match(failed_config, config, content_analysis)
            
            targets.append(FailoverTarget(
                provider_name=name,
                provider_tier=config.provider_tier,
                expected_performance=performance_score * capability_match,
                cost_multiplier=self._calculate_tier_cost_multiplier(failed_config.provider_tier, config.provider_tier),
                capability_match=capability_match,
                privacy_safe=config.provider_tier in [ProviderTier.LOCAL_GPU, ProviderTier.LOCAL_CPU]
            ))
        
        # Sort by performance score
        targets.sort(key=lambda x: x.expected_performance, reverse=True)
        return targets
    
    def _get_privacy_preserving_targets(
        self,
        failed_config: EnhancedAIProviderConfiguration,
        available_configs: Dict[str, EnhancedAIProviderConfiguration],
        content_analysis: ContentAnalysisResult,
        context: Optional[Dict[str, Any]]
    ) -> List[FailoverTarget]:
        """Generate privacy-preserving failover targets"""
        targets = []
        require_local = context.get("require_local_processing", content_analysis.privacy_sensitive)
        
        for name, config in available_configs.items():
            if not config.can_handle_content(content_analysis.content_type):
                continue
            
            # Prioritize local providers for privacy
            is_local = config.provider_tier in [ProviderTier.LOCAL_GPU, ProviderTier.LOCAL_CPU]
            
            if require_local and not is_local:
                continue
            
            health = self.provider_health.get(name)
            expected_performance = health.health_score if health else 0.5
            capability_match = self._calculate_capability_match(failed_config, config, content_analysis)
            
            # Boost score for local providers
            privacy_boost = 1.5 if is_local else 1.0
            
            targets.append(FailoverTarget(
                provider_name=name,
                provider_tier=config.provider_tier,
                expected_performance=expected_performance * capability_match * privacy_boost,
                cost_multiplier=self._calculate_tier_cost_multiplier(failed_config.provider_tier, config.provider_tier),
                capability_match=capability_match,
                privacy_safe=is_local
            ))
        
        # Sort by privacy safety first, then performance
        targets.sort(key=lambda x: (x.privacy_safe, x.expected_performance), reverse=True)
        return targets
    
    def _calculate_tier_cost_multiplier(self, from_tier: ProviderTier, to_tier: ProviderTier) -> float:
        """Calculate cost multiplier when switching between tiers"""
        tier_costs = {
            ProviderTier.CLOUD_PREMIUM: 2.0,
            ProviderTier.CLOUD_STANDARD: 1.0,
            ProviderTier.LOCAL_GPU: 0.3,
            ProviderTier.LOCAL_CPU: 0.1
        }
        
        from_cost = tier_costs.get(from_tier, 1.0)
        to_cost = tier_costs.get(to_tier, 1.0)
        
        return to_cost / from_cost
    
    def _calculate_capability_match(
        self,
        failed_config: EnhancedAIProviderConfiguration,
        target_config: EnhancedAIProviderConfiguration,
        content_analysis: ContentAnalysisResult
    ) -> float:
        """Calculate capability match score between providers"""
        score = 0.0
        
        # Content type support
        if target_config.can_handle_content(content_analysis.content_type):
            score += 0.4
        
        # Specific capability comparison
        if content_analysis.content_type == ContentType.IMAGE:
            if (failed_config.capabilities.vision_capabilities and 
                target_config.capabilities.vision_capabilities):
                score += 0.3
        elif content_analysis.content_type == ContentType.CODE:
            failed_quality = failed_config.capabilities.code_generation_quality
            target_quality = target_config.capabilities.code_generation_quality
            score += min(target_quality / max(0.1, failed_quality), 1.0) * 0.3
        elif content_analysis.content_type == ContentType.MULTIMODAL:
            if (failed_config.capabilities.multimodal_support and 
                target_config.capabilities.multimodal_support):
                score += 0.3
        
        # Token limit adequacy
        if content_analysis.size_estimate > 0:
            failed_adequacy = failed_config.capabilities.max_tokens / content_analysis.size_estimate
            target_adequacy = target_config.capabilities.max_tokens / content_analysis.size_estimate
            adequacy_ratio = min(target_adequacy / max(0.1, failed_adequacy), 1.0)
            score += adequacy_ratio * 0.2
        else:
            score += 0.2
        
        # Instruction following capability
        failed_instruction = failed_config.capabilities.instruction_following
        target_instruction = target_config.capabilities.instruction_following
        instruction_ratio = min(target_instruction / max(0.1, failed_instruction), 1.0)
        score += instruction_ratio * 0.1
        
        return min(1.0, score)
    
    def _calculate_tier_delay(self, from_tier: ProviderTier, to_tier: ProviderTier) -> float:
        """Calculate expected delay when switching between tiers"""
        # Local providers may have initialization delay
        if to_tier in [ProviderTier.LOCAL_GPU, ProviderTier.LOCAL_CPU]:
            if from_tier in [ProviderTier.CLOUD_PREMIUM, ProviderTier.CLOUD_STANDARD]:
                return 2.0  # 2 seconds for local model loading
        
        return 0.5  # Minimal delay for cloud-to-cloud switching
    
    def record_provider_outcome(
        self,
        provider_name: str,
        response_time: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Record provider outcome for health monitoring"""
        with self.lock:
            if provider_name not in self.provider_health:
                self.provider_health[provider_name] = ProviderHealth(provider_name=provider_name)
            
            health = self.provider_health[provider_name]
            current_time = time.time()
            
            if success:
                health.last_success = current_time
                health.consecutive_successes += 1
                health.consecutive_failures = 0
            else:
                health.last_failure = current_time
                health.consecutive_failures += 1
                health.consecutive_successes = 0
                
                if error:
                    health.error_types[error] += 1
            
            health.response_times.append(response_time)
    
    def record_failover_event(
        self,
        original_provider: str,
        target_provider: str,
        reason: FailoverReason,
        content_type: ContentType,
        success: bool,
        performance_impact: float = 0.0,
        cost_impact: float = 0.0
    ):
        """Record failover event for analytics"""
        event = FailoverEvent(
            timestamp=time.time(),
            original_provider=original_provider,
            target_provider=target_provider,
            reason=reason,
            content_type=content_type,
            success=success,
            performance_impact=performance_impact,
            cost_impact=cost_impact
        )
        
        with self.lock:
            self.failover_history.append(event)
            
            # Trim history if too large
            if len(self.failover_history) > self.max_history_size:
                self.failover_history = self.failover_history[-self.max_history_size//2:]
        
        self.logger.info(
            json.dumps({
                "event": "failover_recorded",
                "original_provider": original_provider,
                "target_provider": target_provider,
                "reason": reason.value,
                "content_type": content_type.value,
                "success": success,
                "performance_impact": performance_impact,
                "cost_impact": cost_impact
            })
        )
    
    def _update_health_scores(self):
        """Update health scores for all providers"""
        with self.lock:
            for provider_name, health in self.provider_health.items():
                # Calculate success rate
                total_requests = health.consecutive_successes + health.consecutive_failures
                if total_requests > 0:
                    success_rate = health.consecutive_successes / total_requests
                else:
                    success_rate = 1.0
                
                # Calculate response time score
                if health.response_times:
                    avg_time = statistics.mean(health.response_times)
                    time_score = max(0.0, 1.0 - (avg_time / 30.0))  # Normalize against 30s
                else:
                    time_score = 1.0
                
                # Calculate recency score (recent activity is better)
                current_time = time.time()
                last_activity = max(health.last_success, health.last_failure)
                if last_activity > 0:
                    hours_since_activity = (current_time - last_activity) / 3600
                    recency_score = max(0.1, 1.0 - (hours_since_activity / 24))  # Decay over 24 hours
                else:
                    recency_score = 0.5
                
                # Combined health score
                health.health_score = (success_rate * 0.5 + time_score * 0.3 + recency_score * 0.2)
    
    def _detect_degradation_trends(self):
        """Detect performance degradation trends"""
        with self.lock:
            for provider_name, health in self.provider_health.items():
                if len(health.response_times) < 10:
                    continue
                
                # Compare recent performance to historical
                all_times = list(health.response_times)
                recent_times = all_times[-5:]  # Last 5 requests
                historical_times = all_times[-20:-5]  # Previous 15 requests
                
                if len(historical_times) < 5:
                    continue
                
                recent_avg = statistics.mean(recent_times)
                historical_avg = statistics.mean(historical_times)
                
                if historical_avg > 0:
                    degradation = (recent_avg - historical_avg) / historical_avg
                    health.degradation_trend = max(-1.0, min(1.0, degradation))
                else:
                    health.degradation_trend = 0.0
    
    def _cleanup_old_history(self):
        """Clean up old failover history"""
        with self.lock:
            if len(self.failover_history) > self.max_history_size:
                self.failover_history = self.failover_history[-self.max_history_size//2:]
    
    def get_failover_statistics(self) -> Dict[str, Any]:
        """Get comprehensive failover statistics"""
        with self.lock:
            stats = {
                "total_failovers": len(self.failover_history),
                "failover_reasons": defaultdict(int),
                "provider_health": {},
                "recent_failovers": []
            }
            
            # Analyze failover reasons
            for event in self.failover_history:
                stats["failover_reasons"][event.reason.value] += 1
            
            # Provider health summary
            for provider_name, health in self.provider_health.items():
                stats["provider_health"][provider_name] = {
                    "health_score": health.health_score,
                    "consecutive_failures": health.consecutive_failures,
                    "consecutive_successes": health.consecutive_successes,
                    "degradation_trend": health.degradation_trend,
                    "avg_response_time": statistics.mean(health.response_times) if health.response_times else 0.0
                }
            
            # Recent failovers (last 10)
            recent_events = sorted(self.failover_history, key=lambda x: x.timestamp, reverse=True)[:10]
            for event in recent_events:
                stats["recent_failovers"].append({
                    "timestamp": datetime.fromtimestamp(event.timestamp).isoformat(),
                    "original_provider": event.original_provider,
                    "target_provider": event.target_provider,
                    "reason": event.reason.value,
                    "success": event.success
                })
            
            return dict(stats)
    
    def reset_provider_health(self, provider_name: str):
        """Reset health data for provider (useful after manual intervention)"""
        with self.lock:
            if provider_name in self.provider_health:
                health = self.provider_health[provider_name]
                health.consecutive_failures = 0
                health.consecutive_successes = 0
                health.health_score = 1.0
                health.degradation_trend = 0.0
                health.error_types.clear()
                
                self.logger.info(f"Reset health data for provider: {provider_name}")
    
    async def shutdown(self):
        """Shutdown failover manager gracefully"""
        self.logger.info("Shutting down Intelligent Failover Manager")
        
        with self.lock:
            # Save critical state if needed
            pass
        
        self.logger.info("Intelligent Failover Manager shutdown complete")