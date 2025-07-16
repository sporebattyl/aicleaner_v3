"""
AI Provider Manager
Phase 2A: AI Model Provider Optimization

Central management system for all AI providers with intelligent routing,
load balancing, failover, and performance optimization.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random

from .base_provider import (
    BaseAIProvider, AIProviderConfiguration, AIRequest, AIResponse,
    AIProviderStatus, AIProviderError, AIProviderMetrics
)
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .ollama_provider import OllamaProvider
from .credential_manager import CredentialManager
from .health_monitor import HealthMonitor, HealthReport


class ProviderSelectionStrategy(Enum):
    """Provider selection strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    FASTEST_RESPONSE = "fastest_response"
    COST_OPTIMAL = "cost_optimal"
    PRIORITY_BASED = "priority_based"
    ADAPTIVE = "adaptive"


@dataclass
class ProviderConfig:
    """Configuration for a provider"""
    name: str
    provider_class: str
    enabled: bool = True
    priority: int = 1
    weight: float = 1.0
    fallback_enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingRule:
    """Routing rule for requests"""
    condition: str
    provider: str
    priority: int = 1
    enabled: bool = True


class AIProviderManager:
    """
    Central AI Provider Manager with intelligent routing and management.
    
    Features:
    - Multi-provider support with unified interface
    - Intelligent request routing and load balancing
    - Automated failover and error recovery
    - Performance monitoring and optimization
    - Cost tracking and budget management
    - Credential management integration
    - Health monitoring and alerting
    - Request batching and optimization
    """
    
    def __init__(self, config: Dict[str, Any], data_path: str = "/data"):
        """
        Initialize AI Provider Manager.
        
        Args:
            config: Configuration dictionary
            data_path: Path for storing data
        """
        self.config = config
        self.data_path = data_path
        self.logger = logging.getLogger("ai_provider_manager")
        
        # Provider management
        self.providers: Dict[str, BaseAIProvider] = {}
        self.provider_configs: Dict[str, ProviderConfig] = {}
        self.provider_classes = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "google": GoogleProvider,
            "ollama": OllamaProvider
        }
        
        # Routing and load balancing
        self.selection_strategy = ProviderSelectionStrategy(
            config.get("selection_strategy", "adaptive")
        )
        self.routing_rules: List[RoutingRule] = []
        self.round_robin_index = 0
        
        # Performance tracking
        self.request_history: List[Dict[str, Any]] = []
        self.provider_performance: Dict[str, Dict[str, float]] = {}
        
        # Credential management
        self.credential_manager = CredentialManager(config, data_path)
        
        # Health monitoring
        self.health_monitor = HealthMonitor("ai_provider_manager", config)
        
        # Request queue and batching
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.batch_size = config.get("batch_size", 5)
        self.batch_timeout = config.get("batch_timeout", 1.0)
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Caching
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = config.get("cache_ttl", 300)
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_cost": 0.0,
            "provider_usage": {},
            "average_response_time": 0.0
        }
        
        # Load provider configurations during initialization
        self._load_provider_configs()
        
        self.logger.info("AI Provider Manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize all providers and components"""
        try:
            # Initialize credential manager
            await self.credential_manager.health_check()
            
            # Initialize providers
            await self._initialize_providers()
            
            # Start health monitoring
            await self.health_monitor.start_monitoring()
            
            # Start request processing
            asyncio.create_task(self._process_request_queue())
            
            self.logger.info(f"AI Provider Manager initialized with {len(self.providers)} providers")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Provider Manager: {e}")
            return False
    
    def _load_provider_configs(self):
        """Load provider configurations from config"""
        providers_config = self.config.get("providers", {})
        
        for provider_name, provider_config in providers_config.items():
            if provider_name in self.provider_classes:
                self.provider_configs[provider_name] = ProviderConfig(
                    name=provider_name,
                    provider_class=provider_name,
                    enabled=provider_config.get("enabled", True),
                    priority=provider_config.get("priority", 1),
                    weight=provider_config.get("weight", 1.0),
                    fallback_enabled=provider_config.get("fallback_enabled", True),
                    config=provider_config
                )
                
                self.logger.info(f"Loaded configuration for provider: {provider_name}")
    
    async def _initialize_providers(self):
        """Initialize all configured providers"""
        for provider_name, provider_config in self.provider_configs.items():
            if not provider_config.enabled:
                continue
            
            try:
                # Get credentials
                api_key = self.credential_manager.get_credential(provider_name, "api_key")
                if not api_key and provider_name != "ollama":
                    self.logger.warning(f"No API key found for {provider_name}")
                    continue
                
                # Create provider configuration
                provider_ai_config = AIProviderConfiguration(
                    name=provider_name,
                    enabled=provider_config.enabled,
                    priority=provider_config.priority,
                    api_key=api_key or "",
                    model_name=provider_config.config.get("model_name", ""),
                    base_url=provider_config.config.get("base_url"),
                    rate_limit_rpm=provider_config.config.get("rate_limit_rpm", 60),
                    rate_limit_tpm=provider_config.config.get("rate_limit_tpm", 10000),
                    daily_budget=provider_config.config.get("daily_budget", 10.0),
                    cost_per_request=provider_config.config.get("cost_per_request", 0.01),
                    timeout_seconds=provider_config.config.get("timeout_seconds", 30),
                    max_retries=provider_config.config.get("max_retries", 3),
                    health_check_interval=provider_config.config.get("health_check_interval", 300)
                )
                
                # Create provider instance
                provider_class = self.provider_classes[provider_name]
                provider = provider_class(provider_ai_config)
                
                # Initialize provider
                if await provider.initialize():
                    self.providers[provider_name] = provider
                    self.logger.info(f"Successfully initialized provider: {provider_name}")
                    
                    # Initialize circuit breaker
                    self.circuit_breakers[provider_name] = {
                        "state": "closed",
                        "failure_count": 0,
                        "last_failure": None,
                        "timeout": 60  # seconds
                    }
                    
                    # Initialize performance tracking
                    self.provider_performance[provider_name] = {
                        "response_time": 0.0,
                        "success_rate": 1.0,
                        "cost_per_request": 0.0,
                        "load": 0.0
                    }
                    
                    # Initialize stats
                    self.stats["provider_usage"][provider_name] = 0
                    
                else:
                    self.logger.error(f"Failed to initialize provider: {provider_name}")
                    
            except Exception as e:
                self.logger.error(f"Error initializing provider {provider_name}: {e}")
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """
        Process AI request with intelligent routing.
        
        Args:
            request: AI request to process
            
        Returns:
            AI response
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                self.logger.debug(f"Cache hit for request: {request.request_id}")
                return cached_response
            
            # Select provider
            provider = await self._select_provider(request)
            if not provider:
                raise AIProviderError(
                    "No available providers",
                    error_code="NO_PROVIDERS_AVAILABLE",
                    provider="manager",
                    retryable=False
                )
            
            # Process request
            response = await self._process_with_provider(provider, request)
            
            # Cache response
            self._cache_response(cache_key, response)
            
            # Update statistics
            self._update_stats(provider.config.name, response, time.time() - start_time)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing request {request.request_id}: {e}")
            
            # Update failure statistics
            self.stats["failed_requests"] += 1
            
            # Return error response
            return AIResponse(
                request_id=request.request_id,
                response_text="",
                model_used="unknown",
                provider="manager",
                confidence=0.0,
                cost=0.0,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def _select_provider(self, request: AIRequest) -> Optional[BaseAIProvider]:
        """Select the best provider for the request"""
        available_providers = self._get_available_providers()
        
        if not available_providers:
            return None
        
        # Apply routing rules first
        for rule in self.routing_rules:
            if rule.enabled and self._matches_routing_rule(request, rule):
                if rule.provider in available_providers:
                    return self.providers[rule.provider]
        
        # Use selection strategy
        if self.selection_strategy == ProviderSelectionStrategy.ROUND_ROBIN:
            return self._select_round_robin(available_providers)
        elif self.selection_strategy == ProviderSelectionStrategy.LEAST_LOADED:
            return self._select_least_loaded(available_providers)
        elif self.selection_strategy == ProviderSelectionStrategy.FASTEST_RESPONSE:
            return self._select_fastest_response(available_providers)
        elif self.selection_strategy == ProviderSelectionStrategy.COST_OPTIMAL:
            return self._select_cost_optimal(available_providers)
        elif self.selection_strategy == ProviderSelectionStrategy.PRIORITY_BASED:
            return self._select_priority_based(available_providers)
        else:  # ADAPTIVE
            return self._select_adaptive(available_providers)
    
    def _get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        available = []
        
        for provider_name, provider in self.providers.items():
            # Check circuit breaker
            if self._is_circuit_breaker_open(provider_name):
                continue
            
            # Check provider health
            if provider.is_available():
                available.append(provider_name)
        
        return available
    
    def _select_round_robin(self, available_providers: List[str]) -> BaseAIProvider:
        """Select provider using round-robin strategy"""
        if not available_providers:
            return None
        
        provider_name = available_providers[self.round_robin_index % len(available_providers)]
        self.round_robin_index += 1
        
        return self.providers[provider_name]
    
    def _select_least_loaded(self, available_providers: List[str]) -> BaseAIProvider:
        """Select provider with least load"""
        if not available_providers:
            return None
        
        best_provider = None
        min_load = float('inf')
        
        for provider_name in available_providers:
            provider = self.providers[provider_name]
            load = provider.get_active_requests()
            
            if load < min_load:
                min_load = load
                best_provider = provider
        
        return best_provider
    
    def _select_fastest_response(self, available_providers: List[str]) -> BaseAIProvider:
        """Select provider with fastest response time"""
        if not available_providers:
            return None
        
        best_provider = None
        min_response_time = float('inf')
        
        for provider_name in available_providers:
            provider = self.providers[provider_name]
            response_time = provider.get_metrics().average_response_time
            
            if response_time < min_response_time:
                min_response_time = response_time
                best_provider = provider
        
        return best_provider
    
    def _select_cost_optimal(self, available_providers: List[str]) -> BaseAIProvider:
        """Select provider with optimal cost"""
        if not available_providers:
            return None
        
        best_provider = None
        min_cost = float('inf')
        
        for provider_name in available_providers:
            provider = self.providers[provider_name]
            metrics = provider.get_metrics()
            cost_per_request = metrics.total_cost / max(1, metrics.total_requests)
            
            if cost_per_request < min_cost:
                min_cost = cost_per_request
                best_provider = provider
        
        return best_provider
    
    def _select_priority_based(self, available_providers: List[str]) -> BaseAIProvider:
        """Select provider based on priority"""
        if not available_providers:
            return None
        
        # Sort by priority (lower number = higher priority)
        sorted_providers = sorted(
            available_providers,
            key=lambda p: self.provider_configs[p].priority
        )
        
        return self.providers[sorted_providers[0]]
    
    def _select_adaptive(self, available_providers: List[str]) -> BaseAIProvider:
        """Select provider using adaptive strategy"""
        if not available_providers:
            return None
        
        # Calculate scores for each provider
        scores = {}
        
        for provider_name in available_providers:
            provider = self.providers[provider_name]
            config = self.provider_configs[provider_name]
            metrics = provider.get_metrics()
            
            # Calculate weighted score
            response_time_score = 1.0 / max(0.1, metrics.average_response_time)
            success_rate_score = metrics.success_rate
            cost_score = 1.0 / max(0.01, metrics.total_cost / max(1, metrics.total_requests))
            load_score = 1.0 / max(1, provider.get_active_requests())
            
            score = (
                response_time_score * 0.3 +
                success_rate_score * 0.3 +
                cost_score * 0.2 +
                load_score * 0.2
            ) * config.weight
            
            scores[provider_name] = score
        
        # Select provider with highest score
        best_provider = max(scores, key=scores.get)
        return self.providers[best_provider]
    
    async def _process_with_provider(self, provider: BaseAIProvider, 
                                  request: AIRequest) -> AIResponse:
        """Process request with specific provider"""
        try:
            response = await provider.process_request_with_retry(request)
            
            # Update circuit breaker on success
            self._update_circuit_breaker(provider.config.name, success=True)
            
            return response
            
        except AIProviderError as e:
            # Update circuit breaker on failure
            self._update_circuit_breaker(provider.config.name, success=False)
            
            # Try fallback if available
            if e.retryable:
                fallback_provider = await self._get_fallback_provider(provider.config.name)
                if fallback_provider:
                    self.logger.info(f"Falling back to provider: {fallback_provider.config.name}")
                    return await self._process_with_provider(fallback_provider, request)
            
            raise e
    
    async def _get_fallback_provider(self, failed_provider: str) -> Optional[BaseAIProvider]:
        """Get fallback provider for failed provider"""
        available_providers = [
            name for name in self._get_available_providers()
            if name != failed_provider
        ]
        
        if not available_providers:
            return None
        
        # Select fallback using priority
        return self._select_priority_based(available_providers)
    
    def _is_circuit_breaker_open(self, provider_name: str) -> bool:
        """Check if circuit breaker is open for provider"""
        if provider_name not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[provider_name]
        
        if breaker["state"] == "open":
            # Check if timeout has passed
            if breaker["last_failure"]:
                time_since_failure = time.time() - breaker["last_failure"]
                if time_since_failure > breaker["timeout"]:
                    # Move to half-open state
                    breaker["state"] = "half-open"
                    return False
            return True
        
        return False
    
    def _update_circuit_breaker(self, provider_name: str, success: bool):
        """Update circuit breaker state"""
        if provider_name not in self.circuit_breakers:
            return
        
        breaker = self.circuit_breakers[provider_name]
        
        if success:
            breaker["failure_count"] = 0
            breaker["state"] = "closed"
        else:
            breaker["failure_count"] += 1
            breaker["last_failure"] = time.time()
            
            # Open circuit breaker if too many failures
            if breaker["failure_count"] >= 5:
                breaker["state"] = "open"
                self.logger.warning(f"Circuit breaker opened for provider: {provider_name}")
    
    def _generate_cache_key(self, request: AIRequest) -> str:
        """Generate cache key for request"""
        import hashlib
        
        # Create key from prompt and image
        key_data = request.prompt
        if request.image_path:
            with open(request.image_path, 'rb') as f:
                key_data += hashlib.md5(f.read()).hexdigest()
        
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[AIResponse]:
        """Get cached response if valid"""
        if cache_key not in self.cache:
            return None
        
        cache_entry = self.cache[cache_key]
        
        # Check if cache is still valid
        if time.time() - cache_entry["timestamp"] > self.cache_ttl:
            del self.cache[cache_key]
            return None
        
        # Update cached response
        response = cache_entry["response"]
        response.cached = True
        
        return response
    
    def _cache_response(self, cache_key: str, response: AIResponse):
        """Cache response"""
        self.cache[cache_key] = {
            "response": response,
            "timestamp": time.time()
        }
    
    def _update_stats(self, provider_name: str, response: AIResponse, total_time: float):
        """Update statistics"""
        self.stats["total_requests"] += 1
        self.stats["total_cost"] += response.cost
        self.stats["provider_usage"][provider_name] += 1
        
        if response.error:
            self.stats["failed_requests"] += 1
        else:
            self.stats["successful_requests"] += 1
        
        # Update average response time
        self.stats["average_response_time"] = (
            (self.stats["average_response_time"] * (self.stats["total_requests"] - 1) + total_time) /
            self.stats["total_requests"]
        )
    
    def _matches_routing_rule(self, request: AIRequest, rule: RoutingRule) -> bool:
        """Check if request matches routing rule"""
        # Simple rule matching - can be extended
        if rule.condition == "image_analysis" and (request.image_path or request.image_data):
            return True
        elif rule.condition == "text_only" and not (request.image_path or request.image_data):
            return True
        
        return False
    
    async def _process_request_queue(self):
        """Process requests from queue with batching"""
        while True:
            try:
                batch = []
                
                # Collect requests for batch
                timeout_start = time.time()
                while len(batch) < self.batch_size and (time.time() - timeout_start) < self.batch_timeout:
                    try:
                        request = await asyncio.wait_for(
                            self.request_queue.get(),
                            timeout=self.batch_timeout
                        )
                        batch.append(request)
                    except asyncio.TimeoutError:
                        break
                
                # Process batch
                if batch:
                    await self._process_batch(batch)
                
            except Exception as e:
                self.logger.error(f"Error in request queue processing: {e}")
                await asyncio.sleep(1)
    
    async def _process_batch(self, batch: List[AIRequest]):
        """Process a batch of requests"""
        # Group requests by optimal provider
        provider_batches = {}
        
        for request in batch:
            provider = await self._select_provider(request)
            if provider:
                provider_name = provider.config.name
                if provider_name not in provider_batches:
                    provider_batches[provider_name] = []
                provider_batches[provider_name].append(request)
        
        # Process each provider's batch
        tasks = []
        for provider_name, requests in provider_batches.items():
            provider = self.providers[provider_name]
            if hasattr(provider, 'batch_process_requests'):
                tasks.append(provider.batch_process_requests(requests))
            else:
                # Fallback to individual processing
                for request in requests:
                    tasks.append(self._process_with_provider(provider, request))
        
        # Wait for all tasks
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def batch_process_requests(self, requests: List[AIRequest]) -> List[AIResponse]:
        """
        Process multiple requests efficiently.
        
        Args:
            requests: List of requests to process
            
        Returns:
            List of responses
        """
        responses = []
        
        for request in requests:
            response = await self.process_request(request)
            responses.append(response)
        
        return responses
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {}
        
        for provider_name, provider in self.providers.items():
            status[provider_name] = {
                "status": provider.get_status().value,
                "health": provider.is_healthy(),
                "available": provider.is_available(),
                "active_requests": provider.get_active_requests(),
                "metrics": provider.get_metrics().__dict__,
                "circuit_breaker": self.circuit_breakers.get(provider_name, {})
            }
        
        return status
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            "overall_stats": self.stats,
            "provider_performance": self.provider_performance,
            "provider_status": self.get_provider_status(),
            "cache_stats": {
                "entries": len(self.cache),
                "hit_rate": self._calculate_cache_hit_rate()
            },
            "routing": {
                "strategy": self.selection_strategy.value,
                "rules": [rule.__dict__ for rule in self.routing_rules]
            }
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        # This would need to be tracked separately
        return 0.0
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all providers"""
        health_report = {
            "overall_health": "healthy",
            "providers": {},
            "manager_health": "healthy"
        }
        
        for provider_name, provider in self.providers.items():
            try:
                status = await provider.health_check()
                health_report["providers"][provider_name] = {
                    "status": status.value,
                    "last_check": datetime.now().isoformat()
                }
                
                if status not in [AIProviderStatus.HEALTHY, AIProviderStatus.DEGRADED]:
                    health_report["overall_health"] = "degraded"
                    
            except Exception as e:
                health_report["providers"][provider_name] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }
                health_report["overall_health"] = "degraded"
        
        return health_report
    
    async def shutdown(self):
        """Shutdown all providers and manager"""
        self.logger.info("Shutting down AI Provider Manager")
        
        # Stop health monitoring
        await self.health_monitor.stop_monitoring()
        
        # Shutdown all providers
        for provider_name, provider in self.providers.items():
            try:
                await provider.shutdown()
                self.logger.info(f"Shutdown provider: {provider_name}")
            except Exception as e:
                self.logger.error(f"Error shutting down provider {provider_name}: {e}")
        
        self.logger.info("AI Provider Manager shutdown complete")
    
    def add_routing_rule(self, rule: RoutingRule):
        """Add a routing rule"""
        self.routing_rules.append(rule)
        self.logger.info(f"Added routing rule: {rule.condition} -> {rule.provider}")
    
    def remove_routing_rule(self, condition: str):
        """Remove routing rule by condition"""
        self.routing_rules = [r for r in self.routing_rules if r.condition != condition]
        self.logger.info(f"Removed routing rule: {condition}")
    
    def set_selection_strategy(self, strategy: ProviderSelectionStrategy):
        """Set provider selection strategy"""
        self.selection_strategy = strategy
        self.logger.info(f"Set selection strategy to: {strategy.value}")
    
    def clear_cache(self):
        """Clear response cache"""
        self.cache.clear()
        self.logger.info("Response cache cleared")
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary across all providers"""
        total_cost = 0.0
        provider_costs = {}
        
        for provider_name, provider in self.providers.items():
            metrics = provider.get_metrics()
            provider_costs[provider_name] = {
                "total_cost": metrics.total_cost,
                "requests": metrics.total_requests,
                "cost_per_request": metrics.total_cost / max(1, metrics.total_requests)
            }
            total_cost += metrics.total_cost
        
        return {
            "total_cost": total_cost,
            "provider_costs": provider_costs,
            "average_cost_per_request": total_cost / max(1, self.stats["total_requests"])
        }