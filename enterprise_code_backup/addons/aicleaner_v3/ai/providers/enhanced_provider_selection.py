"""
Enhanced Provider Selection System
Cloud Integration Optimization - Phase 4

Advanced provider selection with content-aware routing, cost optimization,
performance-based selection, and predictive failover capabilities.
"""

import asyncio
import json
import logging
import math
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .enhanced_config import (
    ContentType, ProcessingPriority, ProviderTier, 
    EnhancedAIProviderConfiguration, ProviderCapability
)
from .content_analyzer import ContentAnalysisResult
from ..base_provider import AIRequest, AIResponse, BaseAIProvider, AIProviderStatus


class SelectionStrategy(Enum):
    """Provider selection strategies"""
    WEIGHTED_SCORING = "weighted_scoring"        # Balanced approach
    COST_OPTIMIZED = "cost_optimized"           # Minimize costs
    PERFORMANCE_OPTIMIZED = "performance_optimized"  # Maximize speed/quality
    CAPABILITY_FIRST = "capability_first"       # Prioritize capability match
    RELIABILITY_FIRST = "reliability_first"     # Prioritize reliability


@dataclass
class SelectionWeights:
    """Weights for provider selection scoring"""
    capability_match: float = 0.4
    cost_efficiency: float = 0.3
    performance_score: float = 0.3
    reliability_score: float = 0.0   # Optional additional weight
    
    def normalize(self):
        """Normalize weights to sum to 1.0"""
        total = self.capability_match + self.cost_efficiency + self.performance_score + self.reliability_score
        if total > 0:
            self.capability_match /= total
            self.cost_efficiency /= total
            self.performance_score /= total
            self.reliability_score /= total


@dataclass
class PerformanceMetrics:
    """Performance metrics for provider selection"""
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    success_count: int = 0
    failure_count: int = 0
    total_cost: float = 0.0
    last_updated: float = field(default_factory=time.time)
    ema_response_time: float = 0.0
    ema_alpha: float = 0.2
    
    def update(self, response_time: float, success: bool, cost: float = 0.0):
        """Update metrics with new data point"""
        self.response_times.append(response_time)
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.total_cost += cost
        self.last_updated = time.time()
        
        # Update exponential moving average
        if self.ema_response_time == 0.0:
            self.ema_response_time = response_time
        else:
            self.ema_response_time = (self.ema_alpha * response_time + 
                                    (1 - self.ema_alpha) * self.ema_response_time)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    @property
    def response_time_std(self) -> float:
        """Calculate response time standard deviation"""
        return statistics.stdev(self.response_times) if len(self.response_times) > 1 else 0.0


@dataclass
class ProviderScore:
    """Detailed scoring for provider selection"""
    provider_name: str
    total_score: float
    capability_score: float
    cost_score: float
    performance_score: float
    reliability_score: float
    reasoning: List[str] = field(default_factory=list)
    disqualified: bool = False
    disqualification_reason: str = ""


@dataclass
class SelectionContext:
    """Context for provider selection"""
    request: AIRequest
    content_analysis: ContentAnalysisResult
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    budget_constraint: Optional[float] = None
    quality_threshold: float = 0.7
    max_response_time: Optional[float] = None
    require_privacy_pipeline: bool = False
    user_preferences: Dict[str, Any] = field(default_factory=dict)


class EnhancedProviderSelector:
    """
    Enhanced Provider Selection System with intelligent routing and optimization.
    
    Features:
    - Content-aware provider matching
    - Cost optimization with quality tradeoffs
    - Performance-based selection with EMA tracking
    - Dynamic provider ranking
    - Predictive failover triggers
    - Multi-strategy selection algorithms
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None,
        selection_strategy: SelectionStrategy = SelectionStrategy.WEIGHTED_SCORING,
        selection_weights: Optional[SelectionWeights] = None
    ):
        """
        Initialize Enhanced Provider Selector.
        
        Args:
            config: Configuration dictionary
            selection_strategy: Selection strategy to use
            selection_weights: Custom weights for scoring
        """
        self.config = config or {}
        self.selection_strategy = selection_strategy
        self.selection_weights = selection_weights or SelectionWeights()
        self.selection_weights.normalize()
        
        self.logger = logging.getLogger("enhanced_provider_selector")
        
        # Provider performance tracking
        self.performance_metrics: Dict[str, PerformanceMetrics] = {}
        self.provider_rankings: Dict[ContentType, List[str]] = {}
        
        # Cost optimization
        self.daily_budgets: Dict[str, float] = {}
        self.daily_costs: Dict[str, float] = defaultdict(float)
        
        # Failover prediction
        self.failover_thresholds: Dict[str, float] = {}
        self.predictive_failover_enabled = self.config.get("predictive_failover", True)
        
        # Cold start handling
        self.cold_start_score = self.config.get("cold_start_score", 0.5)
        self.min_requests_for_stability = self.config.get("min_requests_for_stability", 10)
        
        # Ranking update frequency
        self.last_ranking_update = 0.0
        self.ranking_update_interval = self.config.get("ranking_update_interval", 60)  # 1 minute
        
        self.logger.info(f"Enhanced Provider Selector initialized with strategy: {selection_strategy.value}")
    
    async def select_provider(
        self,
        providers: Dict[str, BaseAIProvider],
        provider_configs: Dict[str, EnhancedAIProviderConfiguration],
        context: SelectionContext
    ) -> Optional[BaseAIProvider]:
        """
        Select the optimal provider for the given context.
        
        Args:
            providers: Available provider instances
            provider_configs: Provider configurations
            context: Selection context
            
        Returns:
            Selected provider or None if no suitable provider found
        """
        start_time = time.time()
        
        try:
            # Update provider rankings if needed
            await self._update_rankings_if_needed(provider_configs, context.content_analysis.content_type)
            
            # Filter available providers
            available_providers = self._filter_available_providers(
                providers, provider_configs, context
            )
            
            if not available_providers:
                self.logger.warning("No available providers found for selection")
                return None
            
            # Score providers
            scores = await self._score_providers(
                available_providers, provider_configs, context
            )
            
            # Select best provider
            selected_provider = self._select_best_provider(scores, providers)
            
            if selected_provider:
                selection_time = time.time() - start_time
                
                self.logger.info(
                    json.dumps({
                        "event": "provider_selected",
                        "provider": selected_provider.config.name,
                        "content_type": context.content_analysis.content_type.value,
                        "selection_strategy": self.selection_strategy.value,
                        "selection_time": selection_time,
                        "total_score": next(s.total_score for s in scores if s.provider_name == selected_provider.config.name),
                        "available_providers": len(available_providers)
                    })
                )
            
            return selected_provider
            
        except Exception as e:
            self.logger.error(f"Provider selection failed: {e}")
            return None
    
    def _filter_available_providers(
        self,
        providers: Dict[str, BaseAIProvider],
        provider_configs: Dict[str, EnhancedAIProviderConfiguration],
        context: SelectionContext
    ) -> List[str]:
        """Filter providers based on availability and basic requirements"""
        available = []
        
        for provider_name, provider in providers.items():
            config = provider_configs.get(provider_name)
            if not config:
                continue
            
            # Check basic availability
            if not config.enabled or not provider.is_available():
                continue
            
            # Check capability requirements
            if not config.can_handle_content(context.content_analysis.content_type):
                continue
            
            # Check privacy requirements
            if context.require_privacy_pipeline and not config.capabilities.supports_function_calling:
                # Assuming privacy pipeline requires function calling capability
                continue
            
            # Check budget constraints
            if context.budget_constraint:
                estimated_cost = config.get_cost_estimate(
                    context.content_analysis.content_type,
                    context.content_analysis.size_estimate
                )
                if estimated_cost > context.budget_constraint:
                    continue
            
            # Check daily budget
            provider_daily_cost = self.daily_costs.get(provider_name, 0.0)
            provider_daily_budget = self.daily_budgets.get(provider_name, config.cost_optimization.daily_budget)
            if provider_daily_cost >= provider_daily_budget * 0.95:  # 95% of budget used
                continue
            
            # Check predictive failover
            if self._should_predict_failover(provider_name, context):
                continue
            
            available.append(provider_name)
        
        return available
    
    async def _score_providers(
        self,
        available_providers: List[str],
        provider_configs: Dict[str, EnhancedAIProviderConfiguration],
        context: SelectionContext
    ) -> List[ProviderScore]:
        """Score available providers based on selection strategy"""
        scores = []
        
        for provider_name in available_providers:
            config = provider_configs[provider_name]
            
            # Calculate individual scores
            capability_score = self._calculate_capability_score(config, context)
            cost_score = self._calculate_cost_score(config, context)
            performance_score = self._calculate_performance_score(provider_name, context)
            reliability_score = self._calculate_reliability_score(provider_name, config)
            
            # Apply strategy-specific adjustments
            if self.selection_strategy == SelectionStrategy.COST_OPTIMIZED:
                adjusted_weights = SelectionWeights(0.2, 0.6, 0.2, 0.0)
            elif self.selection_strategy == SelectionStrategy.PERFORMANCE_OPTIMIZED:
                adjusted_weights = SelectionWeights(0.3, 0.1, 0.6, 0.0)
            elif self.selection_strategy == SelectionStrategy.CAPABILITY_FIRST:
                adjusted_weights = SelectionWeights(0.7, 0.1, 0.2, 0.0)
            elif self.selection_strategy == SelectionStrategy.RELIABILITY_FIRST:
                adjusted_weights = SelectionWeights(0.2, 0.2, 0.2, 0.4)
            else:
                adjusted_weights = self.selection_weights
            
            adjusted_weights.normalize()
            
            # Calculate total score
            total_score = (
                capability_score * adjusted_weights.capability_match +
                cost_score * adjusted_weights.cost_efficiency +
                performance_score * adjusted_weights.performance_score +
                reliability_score * adjusted_weights.reliability_score
            )
            
            # Generate reasoning
            reasoning = []
            reasoning.append(f"Capability match: {capability_score:.2f}")
            reasoning.append(f"Cost efficiency: {cost_score:.2f}")
            reasoning.append(f"Performance: {performance_score:.2f}")
            if adjusted_weights.reliability_score > 0:
                reasoning.append(f"Reliability: {reliability_score:.2f}")
            
            provider_score = ProviderScore(
                provider_name=provider_name,
                total_score=total_score,
                capability_score=capability_score,
                cost_score=cost_score,
                performance_score=performance_score,
                reliability_score=reliability_score,
                reasoning=reasoning
            )
            
            scores.append(provider_score)
        
        # Sort by total score (descending)
        scores.sort(key=lambda x: x.total_score, reverse=True)
        
        return scores
    
    def _calculate_capability_score(
        self,
        config: EnhancedAIProviderConfiguration,
        context: SelectionContext
    ) -> float:
        """Calculate capability match score (0-1)"""
        score = 0.0
        total_weight = 0.0
        
        # Content type capability
        if config.can_handle_content(context.content_analysis.content_type):
            score += 0.4
        total_weight += 0.4
        
        # Specific capability requirements
        if context.content_analysis.content_type == ContentType.IMAGE:
            if config.capabilities.vision_capabilities:
                score += 0.3
            total_weight += 0.3
        
        elif context.content_analysis.content_type == ContentType.CODE:
            code_quality = config.capabilities.code_generation_quality
            score += code_quality * 0.3
            total_weight += 0.3
        
        elif context.content_analysis.content_type == ContentType.MULTIMODAL:
            if config.capabilities.multimodal_support:
                score += 0.3
            total_weight += 0.3
        
        # Model size/token limit capability
        if context.content_analysis.size_estimate > 0:
            token_adequacy = min(1.0, config.capabilities.max_tokens / context.content_analysis.size_estimate)
            score += token_adequacy * 0.2
        else:
            score += 0.2
        total_weight += 0.2
        
        # Instruction following capability
        instruction_score = config.capabilities.instruction_following
        score += instruction_score * 0.1
        total_weight += 0.1
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_cost_score(
        self,
        config: EnhancedAIProviderConfiguration,
        context: SelectionContext
    ) -> float:
        """Calculate cost efficiency score (0-1, higher is better)"""
        estimated_cost = config.get_cost_estimate(
            context.content_analysis.content_type,
            context.content_analysis.size_estimate
        )
        
        # Apply priority adjustments
        priority_multipliers = {
            ProcessingPriority.CRITICAL: 0.5,    # Cost less important for critical tasks
            ProcessingPriority.HIGH: 0.7,
            ProcessingPriority.NORMAL: 1.0,
            ProcessingPriority.LOW: 1.3,          # Cost more important for low priority
            ProcessingPriority.BATCH: 1.5
        }
        
        adjusted_cost = estimated_cost * priority_multipliers.get(context.priority, 1.0)
        
        # Normalize cost score (exponential preference curve)
        # Lower cost = higher score
        if adjusted_cost <= 0:
            return 1.0
        
        # Use exponential decay for cost preference
        cost_score = math.exp(-adjusted_cost * 10)  # Adjust multiplier based on typical cost ranges
        
        # Consider budget utilization
        provider_name = config.name
        daily_cost = self.daily_costs.get(provider_name, 0.0)
        daily_budget = self.daily_budgets.get(provider_name, config.cost_optimization.daily_budget)
        
        if daily_budget > 0:
            budget_utilization = daily_cost / daily_budget
            if budget_utilization > 0.8:  # Penalize if >80% budget used
                cost_score *= (1.0 - budget_utilization) * 5  # Penalty factor
        
        return max(0.0, min(1.0, cost_score))
    
    def _calculate_performance_score(self, provider_name: str, context: SelectionContext) -> float:
        """Calculate performance score based on historical data (0-1)"""
        metrics = self.performance_metrics.get(provider_name)
        
        if not metrics or metrics.success_count + metrics.failure_count < self.min_requests_for_stability:
            # Cold start - use default score
            return self.cold_start_score
        
        # Success rate component (0-1)
        success_rate = metrics.success_rate
        
        # Response time component (0-1)
        if metrics.ema_response_time > 0:
            # Get timeout for this content type
            max_acceptable_time = context.max_response_time or 10.0
            time_score = max(0.0, 1.0 - (metrics.ema_response_time / max_acceptable_time))
        else:
            time_score = self.cold_start_score
        
        # Stability component (0-1) - lower standard deviation is better
        if len(metrics.response_times) > 5:
            stability_score = max(0.0, 1.0 - (metrics.response_time_std / metrics.avg_response_time))
        else:
            stability_score = self.cold_start_score
        
        # Combine components
        performance_score = (
            success_rate * 0.4 +
            time_score * 0.4 +
            stability_score * 0.2
        )
        
        return max(0.0, min(1.0, performance_score))
    
    def _calculate_reliability_score(
        self,
        provider_name: str,
        config: EnhancedAIProviderConfiguration
    ) -> float:
        """Calculate reliability score (0-1)"""
        # Base reliability from configuration
        base_reliability = config.capabilities.reliability_score
        
        # Adjust based on provider tier
        tier_multipliers = {
            ProviderTier.CLOUD_PREMIUM: 1.0,
            ProviderTier.CLOUD_STANDARD: 0.9,
            ProviderTier.LOCAL_GPU: 0.8,
            ProviderTier.LOCAL_CPU: 0.7
        }
        
        tier_multiplier = tier_multipliers.get(config.provider_tier, 0.8)
        
        # Adjust based on recent performance
        metrics = self.performance_metrics.get(provider_name)
        if metrics and metrics.success_count + metrics.failure_count >= 5:
            recent_reliability = metrics.success_rate
            # Weight recent performance more heavily
            reliability_score = (base_reliability * 0.3 + recent_reliability * 0.7) * tier_multiplier
        else:
            reliability_score = base_reliability * tier_multiplier
        
        return max(0.0, min(1.0, reliability_score))
    
    def _select_best_provider(
        self,
        scores: List[ProviderScore],
        providers: Dict[str, BaseAIProvider]
    ) -> Optional[BaseAIProvider]:
        """Select the best provider from scored results"""
        if not scores:
            return None
        
        # Get the highest scoring provider
        best_score = scores[0]
        
        # Log selection reasoning
        self.logger.debug(
            json.dumps({
                "event": "provider_scoring_complete",
                "selected": best_score.provider_name,
                "total_score": best_score.total_score,
                "capability_score": best_score.capability_score,
                "cost_score": best_score.cost_score,
                "performance_score": best_score.performance_score,
                "reasoning": best_score.reasoning,
                "all_scores": [(s.provider_name, s.total_score) for s in scores[:5]]  # Top 5
            })
        )
        
        return providers.get(best_score.provider_name)
    
    def _should_predict_failover(self, provider_name: str, context: SelectionContext) -> bool:
        """Check if predictive failover should trigger for provider"""
        if not self.predictive_failover_enabled:
            return False
        
        metrics = self.performance_metrics.get(provider_name)
        if not metrics or len(metrics.response_times) < 5:
            return False
        
        # Check response time trend
        recent_times = list(metrics.response_times)[-10:]  # Last 10 requests
        if len(recent_times) < 5:
            return False
        
        avg_recent = statistics.mean(recent_times)
        threshold = self.failover_thresholds.get(provider_name, 2.0)  # 2 std devs by default
        
        if metrics.response_time_std > 0:
            z_score = (avg_recent - metrics.avg_response_time) / metrics.response_time_std
            if z_score > threshold:
                self.logger.warning(f"Predictive failover triggered for {provider_name}: z-score {z_score:.2f}")
                return True
        
        # Check failure rate trend
        recent_failures = sum(1 for i in range(-5, 0) if i < len(recent_times) and not metrics.success_count)
        if recent_failures >= 3:  # 3 failures in last 5 requests
            self.logger.warning(f"Predictive failover triggered for {provider_name}: high recent failure rate")
            return True
        
        return False
    
    async def _update_rankings_if_needed(
        self,
        provider_configs: Dict[str, EnhancedAIProviderConfiguration],
        content_type: ContentType
    ):
        """Update provider rankings if needed"""
        current_time = time.time()
        if current_time - self.last_ranking_update < self.ranking_update_interval:
            return
        
        # Calculate rankings for each content type
        for ct in ContentType:
            rankings = []
            for provider_name, config in provider_configs.items():
                if config.can_handle_content(ct):
                    performance_score = config.get_performance_score(ct)
                    rankings.append((provider_name, performance_score))
            
            # Sort by performance score (descending)
            rankings.sort(key=lambda x: x[1], reverse=True)
            self.provider_rankings[ct] = [name for name, _ in rankings]
        
        self.last_ranking_update = current_time
        self.logger.debug("Provider rankings updated")
    
    def update_provider_performance(
        self,
        provider_name: str,
        response_time: float,
        success: bool,
        cost: float = 0.0
    ):
        """Update provider performance metrics"""
        if provider_name not in self.performance_metrics:
            self.performance_metrics[provider_name] = PerformanceMetrics()
        
        self.performance_metrics[provider_name].update(response_time, success, cost)
        
        # Update daily cost tracking
        if cost > 0:
            today = datetime.now().strftime("%Y-%m-%d")
            cost_key = f"{provider_name}_{today}"
            self.daily_costs[cost_key] = self.daily_costs.get(cost_key, 0.0) + cost
    
    def set_daily_budget(self, provider_name: str, budget: float):
        """Set daily budget for provider"""
        self.daily_budgets[provider_name] = budget
    
    def set_failover_threshold(self, provider_name: str, threshold: float):
        """Set predictive failover threshold for provider"""
        self.failover_thresholds[provider_name] = threshold
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get provider selection statistics"""
        stats = {
            "selection_strategy": self.selection_strategy.value,
            "selection_weights": {
                "capability_match": self.selection_weights.capability_match,
                "cost_efficiency": self.selection_weights.cost_efficiency,
                "performance_score": self.selection_weights.performance_score,
                "reliability_score": self.selection_weights.reliability_score
            },
            "provider_metrics": {},
            "daily_costs": dict(self.daily_costs),
            "rankings": {ct.value: names for ct, names in self.provider_rankings.items()}
        }
        
        for provider_name, metrics in self.performance_metrics.items():
            stats["provider_metrics"][provider_name] = {
                "success_rate": metrics.success_rate,
                "avg_response_time": metrics.avg_response_time,
                "ema_response_time": metrics.ema_response_time,
                "total_requests": metrics.success_count + metrics.failure_count,
                "total_cost": metrics.total_cost
            }
        
        return stats
    
    def reset_daily_costs(self):
        """Reset daily cost tracking (called at midnight)"""
        today = datetime.now().strftime("%Y-%m-%d")
        keys_to_remove = [key for key in self.daily_costs.keys() if not key.endswith(today)]
        for key in keys_to_remove:
            del self.daily_costs[key]
        
        self.logger.info("Daily costs reset")