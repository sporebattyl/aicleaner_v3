"""
Intelligent Router - Cross-provider request routing with performance optimization
Analyzes requests and routes them to the optimal AI provider
"""

import asyncio
import logging
import hashlib
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class RequestComplexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VISION = "vision"


@dataclass
class RequestMetrics:
    provider: str
    complexity: RequestComplexity
    response_time: float
    success: bool
    cost: float
    timestamp: datetime


@dataclass
class ProviderCapabilities:
    name: str
    supports_vision: bool
    supports_local: bool
    max_tokens: int
    cost_per_token: float
    avg_response_time: float
    availability_score: float


class IntelligentRouter:
    """
    Cross-provider intelligent routing system
    Analyzes request complexity and routes to optimal provider based on:
    - Request complexity (token count, keywords, metadata)
    - Provider capabilities and performance
    - Current resource usage
    - Cost optimization
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Routing configuration
        self.enable_cost_optimization = config.get("enable_cost_optimization", True)
        self.enable_performance_routing = config.get("enable_performance_routing", True)
        self.local_preference_threshold = config.get("local_preference_threshold", 0.7)
        
        # Provider capabilities (will be populated during initialization)
        self.provider_capabilities: Dict[str, ProviderCapabilities] = {}
        
        # Performance tracking
        self.request_history: List[RequestMetrics] = []
        self.max_history_size = config.get("max_history_size", 1000)
        
        # Request complexity patterns
        self.complexity_patterns = {
            RequestComplexity.SIMPLE: [
                r"^(hello|hi|hey|good\s+(morning|afternoon|evening))",
                r"^(thank you|thanks|please|yes|no)$",
                r"^\w+\?$",  # Single word questions
            ],
            RequestComplexity.VISION: [
                r"(analyze|describe|what.*see|image|picture|photo|visual)",
                r"(identify|recognize|detect|find.*image)",
                r"(camera|video|screenshot|scan)"
            ],
            RequestComplexity.COMPLEX: [
                r"(write.*essay|compose.*article|generate.*report)",
                r"(explain.*detail|analyze.*thoroughly|comprehensive)",
                r"(code.*implementation|programming.*solution)"
            ]
        }
        
        # Provider routing rules
        self.routing_rules = {
            RequestComplexity.SIMPLE: {
                "preferred_local": True,
                "fallback_cloud": ["gemini", "openai"],
                "max_response_time": 5.0
            },
            RequestComplexity.MEDIUM: {
                "preferred_local": True,
                "fallback_cloud": ["gemini", "openai", "anthropic"],
                "max_response_time": 15.0
            },
            RequestComplexity.COMPLEX: {
                "preferred_local": False,
                "fallback_cloud": ["anthropic", "openai", "gemini"],
                "max_response_time": 30.0
            },
            RequestComplexity.VISION: {
                "preferred_local": False,
                "cloud_only": ["gemini", "openai"],
                "max_response_time": 30.0
            }
        }

    async def initialize(self, ai_provider_factory) -> None:
        """Initialize the router with provider capabilities"""
        self.logger.info("Initializing Intelligent Router")
        
        try:
            # Get available providers from factory
            available_providers = getattr(ai_provider_factory, 'get_available_providers', lambda: [])()
            
            # Initialize provider capabilities
            for provider_name in available_providers:
                capabilities = await self._detect_provider_capabilities(provider_name)
                self.provider_capabilities[provider_name] = capabilities
            
            # If no providers detected, use default configuration
            if not self.provider_capabilities:
                self._initialize_default_capabilities()
            
            self.logger.info(f"Initialized routing for {len(self.provider_capabilities)} providers")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize router: {e}")
            self._initialize_default_capabilities()

    async def shutdown(self) -> None:
        """Shutdown the router"""
        self.logger.info("Shutting down Intelligent Router")
        # Clean up any resources if needed

    async def route_request(self, request_data: Dict[str, Any], 
                          resource_metrics: Dict[str, Any]) -> str:
        """
        Route a request to the optimal provider
        
        Args:
            request_data: Request information including prompt, type, metadata
            resource_metrics: Current system resource metrics
            
        Returns:
            Optimal provider name
        """
        try:
            # Analyze request complexity
            complexity = self._analyze_request_complexity(request_data)
            
            # Get routing candidates
            candidates = self._get_routing_candidates(complexity, resource_metrics)
            
            # Select optimal provider
            optimal_provider = await self._select_optimal_provider(
                candidates, complexity, request_data, resource_metrics
            )
            
            self.logger.debug(f"Routed {complexity.value} request to {optimal_provider}")
            return optimal_provider
            
        except Exception as e:
            self.logger.error(f"Routing failed: {e}")
            # Return fallback provider
            return self._get_fallback_provider()

    async def record_request_result(self, provider: str, request_data: Dict[str, Any],
                                   response_time: float, success: bool, cost: float = 0.0) -> None:
        """Record the result of a request for learning purposes"""
        complexity = self._analyze_request_complexity(request_data)
        
        metric = RequestMetrics(
            provider=provider,
            complexity=complexity,
            response_time=response_time,
            success=success,
            cost=cost,
            timestamp=datetime.now()
        )
        
        self.request_history.append(metric)
        
        # Maintain history size
        if len(self.request_history) > self.max_history_size:
            self.request_history = self.request_history[-self.max_history_size:]
        
        # Update provider capabilities based on performance
        await self._update_provider_performance(provider, metric)

    async def get_metrics(self) -> Dict[str, Any]:
        """Get routing performance metrics"""
        if not self.request_history:
            return {"status": "no_data"}
        
        try:
            # Calculate routing accuracy (successful requests / total requests)
            total_requests = len(self.request_history)
            successful_requests = sum(1 for r in self.request_history if r.success)
            routing_accuracy = successful_requests / total_requests if total_requests > 0 else 0
            
            # Provider performance
            provider_stats = {}
            for provider_name in self.provider_capabilities:
                provider_requests = [r for r in self.request_history if r.provider == provider_name]
                if provider_requests:
                    avg_response_time = sum(r.response_time for r in provider_requests) / len(provider_requests)
                    success_rate = sum(1 for r in provider_requests if r.success) / len(provider_requests)
                    total_cost = sum(r.cost for r in provider_requests)
                    
                    provider_stats[provider_name] = {
                        "requests": len(provider_requests),
                        "avg_response_time": avg_response_time,
                        "success_rate": success_rate,
                        "total_cost": total_cost
                    }
            
            # Complexity distribution
            complexity_stats = {}
            for complexity in RequestComplexity:
                complexity_requests = [r for r in self.request_history if r.complexity == complexity]
                complexity_stats[complexity.value] = len(complexity_requests)
            
            return {
                "routing_accuracy": routing_accuracy,
                "total_requests": total_requests,
                "provider_performance": provider_stats,
                "complexity_distribution": complexity_stats,
                "avg_response_time": sum(r.response_time for r in self.request_history) / total_requests,
                "total_cost": sum(r.cost for r in self.request_history)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate metrics: {e}")
            return {"error": str(e)}

    def _analyze_request_complexity(self, request_data: Dict[str, Any]) -> RequestComplexity:
        """Analyze request complexity based on content and metadata"""
        prompt = request_data.get("prompt", "")
        request_type = request_data.get("type", "text")
        
        # Check for vision requests
        if request_type == "vision" or "image" in request_data:
            return RequestComplexity.VISION
        
        # Analyze prompt content
        prompt_lower = prompt.lower()
        
        # Check complexity patterns in order of specificity
        for complexity, patterns in self.complexity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower):
                    return complexity
        
        # Analyze based on prompt length and characteristics
        token_count = self._estimate_token_count(prompt)
        
        if token_count <= 20:
            return RequestComplexity.SIMPLE
        elif token_count <= 100:
            return RequestComplexity.MEDIUM
        else:
            return RequestComplexity.COMPLEX

    def _estimate_token_count(self, text: str) -> int:
        """Rough estimation of token count (1 token ≈ 0.75 words)"""
        words = len(text.split())
        return int(words * 1.33)  # Approximate token count

    def _get_routing_candidates(self, complexity: RequestComplexity, 
                               resource_metrics: Dict[str, Any]) -> List[str]:
        """Get list of candidate providers for a given complexity"""
        rules = self.routing_rules.get(complexity, {})
        candidates = []
        
        # Check if we should prefer local providers
        if rules.get("preferred_local", False):
            local_providers = [
                name for name, caps in self.provider_capabilities.items()
                if caps.supports_local
            ]
            # Only use local if system resources are adequate
            cpu_usage = resource_metrics.get("cpu", {}).get("usage_percent", 100)
            memory_usage = resource_metrics.get("memory", {}).get("usage_percent", 100)
            
            if cpu_usage < 80 and memory_usage < 80:
                candidates.extend(local_providers)
        
        # Add cloud fallbacks
        cloud_providers = rules.get("fallback_cloud", [])
        for provider in cloud_providers:
            if provider in self.provider_capabilities:
                candidates.append(provider)
        
        # For vision requests, only use providers that support it
        if complexity == RequestComplexity.VISION:
            candidates = [
                name for name in candidates
                if self.provider_capabilities[name].supports_vision
            ]
            
            # Add cloud-only providers for vision
            cloud_only = rules.get("cloud_only", [])
            for provider in cloud_only:
                if provider in self.provider_capabilities and provider not in candidates:
                    candidates.append(provider)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                unique_candidates.append(candidate)
        
        return unique_candidates if unique_candidates else list(self.provider_capabilities.keys())

    async def _select_optimal_provider(self, candidates: List[str], 
                                      complexity: RequestComplexity,
                                      request_data: Dict[str, Any],
                                      resource_metrics: Dict[str, Any]) -> str:
        """Select the optimal provider from candidates"""
        if not candidates:
            return self._get_fallback_provider()
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Score each candidate
        scores = {}
        for candidate in candidates:
            score = await self._calculate_provider_score(
                candidate, complexity, request_data, resource_metrics
            )
            scores[candidate] = score
        
        # Return provider with highest score
        optimal_provider = max(scores.keys(), key=lambda p: scores[p])
        
        self.logger.debug(f"Provider scores: {scores}, selected: {optimal_provider}")
        return optimal_provider

    async def _calculate_provider_score(self, provider: str, complexity: RequestComplexity,
                                       request_data: Dict[str, Any],
                                       resource_metrics: Dict[str, Any]) -> float:
        """Calculate a score for a provider based on multiple factors"""
        capabilities = self.provider_capabilities.get(provider)
        if not capabilities:
            return 0.0
        
        score = 0.0
        
        # Base availability score
        score += capabilities.availability_score * 30
        
        # Performance score (inverse of response time)
        max_response_time = self.routing_rules.get(complexity, {}).get("max_response_time", 30.0)
        if capabilities.avg_response_time > 0:
            response_time_score = max(0, (max_response_time - capabilities.avg_response_time) / max_response_time)
            score += response_time_score * 25
        
        # Cost optimization score
        if self.enable_cost_optimization:
            # Lower cost gets higher score
            max_cost = max(caps.cost_per_token for caps in self.provider_capabilities.values())
            if max_cost > 0:
                cost_score = (max_cost - capabilities.cost_per_token) / max_cost
                score += cost_score * 20
        
        # Local provider bonus if resources allow
        if capabilities.supports_local:
            cpu_usage = resource_metrics.get("cpu", {}).get("usage_percent", 100)
            memory_usage = resource_metrics.get("memory", {}).get("usage_percent", 100)
            
            if cpu_usage < 70 and memory_usage < 70:
                score += 15  # Bonus for local processing
        
        # Recent performance bonus
        recent_performance = self._get_recent_provider_performance(provider)
        score += recent_performance * 10
        
        return score

    def _get_recent_provider_performance(self, provider: str) -> float:
        """Get recent performance score for a provider (0-1)"""
        # Look at last 10 requests for this provider
        recent_requests = [
            r for r in self.request_history[-50:]
            if r.provider == provider
        ][-10:]
        
        if not recent_requests:
            return 0.5  # Neutral score for unknown performance
        
        success_rate = sum(1 for r in recent_requests if r.success) / len(recent_requests)
        return success_rate

    async def _detect_provider_capabilities(self, provider_name: str) -> ProviderCapabilities:
        """Detect capabilities of a provider"""
        # This would be implemented to query actual provider capabilities
        # For now, return reasonable defaults based on provider name
        
        defaults = {
            "ollama": ProviderCapabilities(
                name=provider_name,
                supports_vision=False,  # Most Ollama models don't support vision
                supports_local=True,
                max_tokens=4096,
                cost_per_token=0.0,  # Local is free
                avg_response_time=8.0,
                availability_score=0.9
            ),
            "openai": ProviderCapabilities(
                name=provider_name,
                supports_vision=True,
                supports_local=False,
                max_tokens=4096,
                cost_per_token=0.00002,
                avg_response_time=3.0,
                availability_score=0.95
            ),
            "anthropic": ProviderCapabilities(
                name=provider_name,
                supports_vision=True,
                supports_local=False,
                max_tokens=8192,
                cost_per_token=0.00003,
                avg_response_time=4.0,
                availability_score=0.93
            ),
            "gemini": ProviderCapabilities(
                name=provider_name,
                supports_vision=True,
                supports_local=False,
                max_tokens=8192,
                cost_per_token=0.000015,
                avg_response_time=3.5,
                availability_score=0.92
            )
        }
        
        return defaults.get(provider_name, ProviderCapabilities(
            name=provider_name,
            supports_vision=False,
            supports_local=False,
            max_tokens=4096,
            cost_per_token=0.00002,
            avg_response_time=5.0,
            availability_score=0.8
        ))

    def _initialize_default_capabilities(self) -> None:
        """Initialize with default provider capabilities"""
        default_providers = ["openai", "anthropic", "gemini", "ollama"]
        
        for provider in default_providers:
            self.provider_capabilities[provider] = asyncio.run(
                self._detect_provider_capabilities(provider)
            )

    def _get_fallback_provider(self) -> str:
        """Get fallback provider when routing fails"""
        # Return first available provider or default
        if self.provider_capabilities:
            return next(iter(self.provider_capabilities.keys()))
        return "openai"  # Ultimate fallback

    async def _update_provider_performance(self, provider: str, metric: RequestMetrics) -> None:
        """Update provider performance based on recent results"""
        if provider not in self.provider_capabilities:
            return
        
        capabilities = self.provider_capabilities[provider]
        
        # Update average response time with exponential moving average
        alpha = 0.1  # Smoothing factor
        capabilities.avg_response_time = (
            alpha * metric.response_time + 
            (1 - alpha) * capabilities.avg_response_time
        )
        
        # Update availability score based on success/failure
        if metric.success:
            capabilities.availability_score = min(1.0, capabilities.availability_score + 0.01)
        else:
            capabilities.availability_score = max(0.0, capabilities.availability_score - 0.05)