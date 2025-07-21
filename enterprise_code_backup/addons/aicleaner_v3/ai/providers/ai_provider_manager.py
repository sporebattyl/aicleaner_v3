"""
AI Provider Manager
Phase 2A: AI Model Provider Optimization

Central management system for all AI providers with intelligent routing,
load balancing, failover, and performance optimization.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from .base_provider import (
    BaseAIProvider, AIProviderConfiguration, AIRequest, AIResponse,
    AIProviderStatus, AIProviderError, AIProviderMetrics
)
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .ollama_provider import OllamaProvider
from .llamacpp_amd_provider import LlamaCppAMDProvider
from .credential_manager import CredentialManager
from .health_monitor import HealthMonitor
from .load_balancer import LoadBalancer, LoadBalancingStrategy, create_single_user_load_balancer


class ProviderSelectionStrategy(Enum):
    """Provider selection strategies"""
    PRIORITY_BASED = "priority_based"


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


class AIProviderManager:
    """
    Central AI Provider Manager with priority-based routing and management.
    Simplified for single-user context.
    
    Features:
    - Multi-provider support with unified interface
    - Priority-based provider selection
    - Automated failover and error recovery
    - Credential management integration
    """
    
    def __init__(self, config: Dict[str, Any], data_path: str = "/data", hass=None):
        """
        Initialize AI Provider Manager.
        
        Args:
            config: Configuration dictionary
            data_path: Path for storing data
            hass: Home Assistant instance for notifications
        """
        self.config = config
        self.data_path = data_path
        self.hass = hass
        self.logger = logging.getLogger("ai_provider_manager")
        
        # Provider management
        self.providers: Dict[str, BaseAIProvider] = {}
        self.provider_configs: Dict[str, ProviderConfig] = {}
        self.provider_classes = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "google": GoogleProvider,
            "ollama": OllamaProvider,
            "llamacpp_amd": LlamaCppAMDProvider
        }
        
        # Advanced load balancing
        manager_config = config.get("ai_provider_manager", {})
        self.load_balancer = create_single_user_load_balancer(manager_config)
        
        # Performance tracking
        self.request_history: List[Dict[str, Any]] = []
        
        # Credential management
        self.credential_manager = CredentialManager(config, data_path)
        
        # Health monitoring
        self.health_monitor = HealthMonitor("ai_provider_manager", config)
        
        
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
                    
                    # Register with load balancer
                    self.load_balancer.register_provider(provider_name)
                    
                    
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
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing request {request.request_id}: {e}")
            
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
        """Select the best provider for the request using advanced load balancing"""
        # Use the advanced load balancer for provider selection
        selected_provider_name = self.load_balancer.select_provider(self.providers, request)
        
        if selected_provider_name and selected_provider_name in self.providers:
            provider = self.providers[selected_provider_name]
            self.logger.debug(f"Load balancer selected provider: {selected_provider_name}")
            return provider
        
        # Fallback to simple priority-based selection if load balancer fails
        available_providers = self._get_available_providers()
        if available_providers:
            self.logger.warning("Load balancer failed, falling back to priority-based selection")
            return self._select_priority_based(available_providers)
        
        return None
    
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
    
    def _select_priority_based_enhanced(self, available_providers: List[str], request: AIRequest) -> BaseAIProvider:
        """Enhanced priority-based selection with request context consideration"""
        if not available_providers:
            return None
        
        # Sort by priority but also consider provider capabilities and performance
        provider_scores = []
        
        for provider_name in available_providers:
            if provider_name not in self.provider_configs:
                continue
                
            provider = self.providers[provider_name]
            config = self.provider_configs[provider_name]
            
            # Base priority score (lower priority number = higher score)
            priority_score = 10.0 / max(config.priority, 1)
            
            # Performance bonus for local providers (no network latency)
            performance_bonus = 2.0 if provider_name in ["llamacpp_amd", "ollama"] else 0.0
            
            # Capability matching bonus
            capability_bonus = 0.0
            if request.image_path or request.image_data:
                if provider.capabilities.get("vision", False):
                    capability_bonus += 3.0
            
            if self._is_code_request(request.prompt):
                if provider.capabilities.get("code_generation", False):
                    capability_bonus += 1.5
            
            # Health and availability bonus
            health_bonus = 2.0 if provider.is_healthy() else 0.0
            
            total_score = priority_score + performance_bonus + capability_bonus + health_bonus
            provider_scores.append((provider_name, total_score))
        
        # Select provider with highest score
        provider_scores.sort(key=lambda x: x[1], reverse=True)
        selected_provider = provider_scores[0][0]
        
        self.logger.debug(f"Enhanced provider selection: {selected_provider} "
                         f"(score: {provider_scores[0][1]:.1f})")
        
        return self.providers[selected_provider]
    
    def _is_complex_request(self, request: AIRequest) -> bool:
        """
        Determine if a request is complex and might benefit from cloud providers.
        
        Args:
            request: AI request to analyze
            
        Returns:
            True if request appears complex
        """
        prompt = request.prompt.lower()
        
        # Indicators of complex requests that might benefit from cloud providers
        complex_indicators = [
            "analyze", "research", "comprehensive", "detailed analysis",
            "compare and contrast", "in-depth", "thorough examination",
            "professional report", "academic", "scientific", "technical specification",
            "multi-step", "complex problem", "advanced", "sophisticated"
        ]
        
        # Long prompts might be complex
        if len(request.prompt) > 1000:
            return True
        
        # Check for complex task indicators
        return any(indicator in prompt for indicator in complex_indicators)
    
    async def _process_with_provider(self, provider: BaseAIProvider, 
                                  request: AIRequest) -> AIResponse:
        """Process request with specific provider and track metrics"""
        start_time = time.time()
        provider_name = provider.config.name
        
        try:
            response = await provider.process_request_with_retry(request)
            
            # Calculate metrics
            response_time = time.time() - start_time
            success = not response.error
            cost = response.cost
            
            # Update load balancer metrics
            self.load_balancer.update_provider_metrics(provider_name, success, response_time, cost)
            
            return response
            
        except AIProviderError as e:
            # Calculate metrics for failed request
            response_time = time.time() - start_time
            
            # Update load balancer metrics
            self.load_balancer.update_provider_metrics(provider_name, False, response_time, 0.0)
            
            # Try fallback if available
            if e.retryable:
                fallback_provider = await self._get_fallback_provider(provider.config.name, request)
                if fallback_provider:
                    self.logger.info(f"Falling back to provider: {fallback_provider.config.name}")
                    return await self._process_with_provider(fallback_provider, request)
            
            raise e
    
    async def _get_fallback_provider(self, failed_provider: str, request: AIRequest = None) -> Optional[BaseAIProvider]:
        """Get context-aware fallback provider for failed provider"""
        available_providers = [
            name for name in self._get_available_providers()
            if name != failed_provider
        ]
        
        if not available_providers:
            return None
        
        # Filter providers based on request requirements if request is provided
        if request:
            filtered_providers = self._filter_providers_by_capabilities(available_providers, request)
            if filtered_providers:
                available_providers = filtered_providers
        
        # Select fallback using priority
        selected_provider = self._select_priority_based(available_providers)
        
        if selected_provider:
            self.logger.info(
                f"Selected fallback provider: {selected_provider.config.name} for failed provider: {failed_provider}"
            )
            
            # Send HA notification about fallback
            await self._send_ha_notification(
                f"AI Provider Fallback",
                f"Switched from {failed_provider} to {selected_provider.config.name}",
                "warning"
            )
        
        return selected_provider
    
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
            old_state = breaker["state"]
            breaker["failure_count"] = 0
            breaker["state"] = "closed"
            
            # Log recovery if state changed
            if old_state != "closed":
                self.logger.info(
                    f"Circuit breaker state transition: {old_state} -> closed for provider: {provider_name} (recovered)"
                )
        else:
            breaker["failure_count"] += 1
            breaker["last_failure"] = time.time()
            
            # Update circuit breaker if too many failures (faster opening)
            max_failures = breaker.get("max_failures", 3)
            if breaker["failure_count"] >= max_failures:
                old_state = breaker["state"]
                breaker["state"] = "open"
                
                # Log state transition
                self.logger.warning(
                    f"Circuit breaker state transition: {old_state} -> open for provider: {provider_name} "
                    f"(failures: {breaker['failure_count']}/{max_failures})"
                )
                
                # Send HA notification (async call needs to be handled properly)
                asyncio.create_task(self._send_ha_notification(
                    f"AI Provider Circuit Breaker",
                    f"Provider {provider_name} circuit breaker opened after {breaker['failure_count']} failures",
                    "error"
                ))
    
    
    
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers with load balancer and ML model metrics"""
        status = {}
        
        for provider_name, provider in self.providers.items():
            # Get load balancer stats for this provider
            lb_stats = self.load_balancer.get_provider_stats(provider_name)
            
            # Get ML model stats if available
            ml_stats = provider.get_ml_model_stats()
            
            status[provider_name] = {
                "status": provider.get_status().value,
                "health": provider.is_healthy(),
                "available": provider.is_available(),
                "active_requests": provider.get_active_requests(),
                "metrics": provider.get_metrics().__dict__,
                "load_balancer_stats": lb_stats,
                "ml_model_stats": ml_stats
            }
        
        return status
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            "overall_stats": self.stats,
            "provider_status": self.get_provider_status(),
            "cache_stats": {
                "entries": len(self.cache),
                "hit_rate": self._calculate_cache_hit_rate()
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
    
    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get overall load balancer statistics"""
        return self.load_balancer.get_load_balancer_stats()
    
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
    
    def _filter_providers_by_capabilities(self, provider_names: List[str], request: AIRequest) -> List[str]:
        """
        Filter providers based on request requirements and their capabilities.
        
        Args:
            provider_names: List of available provider names
            request: AI request to analyze for requirements
            
        Returns:
            List of provider names that can handle the request
        """
        if not provider_names:
            return []
        
        # Determine request requirements
        requires_vision = bool(request.image_path or request.image_data)
        requires_code = self._is_code_request(request.prompt)
        
        suitable_providers = []
        
        for provider_name in provider_names:
            if provider_name not in self.providers:
                continue
                
            provider = self.providers[provider_name]
            capabilities = provider.capabilities
            
            # Check vision requirement
            if requires_vision and not capabilities.get("vision", False):
                self.logger.debug(f"Provider {provider_name} skipped: no vision capability")
                continue
            
            # Check code generation requirement
            if requires_code and not capabilities.get("code_generation", False):
                self.logger.debug(f"Provider {provider_name} skipped: no code generation capability")
                continue
            
            # Check if provider supports instruction following
            if not capabilities.get("instruction_following", True):
                self.logger.debug(f"Provider {provider_name} skipped: poor instruction following")
                continue
            
            suitable_providers.append(provider_name)
            self.logger.debug(f"Provider {provider_name} suitable for request requirements")
        
        return suitable_providers
    
    def _is_code_request(self, prompt: str) -> bool:
        """
        Determine if a prompt is requesting code generation.
        
        Args:
            prompt: Request prompt to analyze
            
        Returns:
            True if prompt appears to be code-related
        """
        code_indicators = [
            "write code", "generate code", "create function", "implement",
            "debug", "fix code", "optimize code", "refactor",
            "python", "javascript", "java", "c++", "html", "css",
            "algorithm", "data structure", "api", "class", "method",
            "function", "variable", "loop", "condition", "error",
            "syntax", "compile", "execute", "script", "program"
        ]
        
        prompt_lower = prompt.lower()
        return any(indicator in prompt_lower for indicator in code_indicators)
    
    async def _send_ha_notification(self, title: str, message: str, level: str = "info"):
        """
        Send notification to Home Assistant.
        
        Args:
            title: Notification title
            message: Notification message
            level: Notification level (info, warning, error)
        """
        if not self.hass:
            return
        
        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"aicleaner_ai_{int(time.time())}",
                },
                blocking=True,
            )
            
            self.logger.debug(f"Sent HA notification: {title} - {message}")
            
        except Exception as e:
            self.logger.error(f"Failed to send HA notification: {e}")