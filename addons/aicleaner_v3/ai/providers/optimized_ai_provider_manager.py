"""
Optimized AI Provider Manager
Cloud Integration Optimization - Final Integration

Enhanced AI Provider Manager that integrates all cloud optimization components:
- Enhanced configuration system
- Intelligent content analysis
- Smart caching with Privacy Pipeline integration
- Content-aware provider selection
- Intelligent failover with predictive capabilities
- Comprehensive performance monitoring
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from .enhanced_config import (
    ContentType, ProcessingPriority, ProviderTier, 
    EnhancedAIProviderConfiguration, ProviderCapability
)
from .content_analyzer import ContentAnalyzer, ContentAnalysisResult
from .smart_cache import SmartCache, CacheStrategy
from .enhanced_provider_selection import (
    EnhancedProviderSelector, SelectionStrategy, SelectionWeights, SelectionContext
)
from .intelligent_failover import (
    IntelligentFailoverManager, FailoverStrategy, FailoverReason
)
from .performance_monitor import (
    EnhancedPerformanceMonitor, MetricType, AlertLevel
)

# Import existing base classes
from ..base_provider import (
    BaseAIProvider, AIProviderConfiguration, AIRequest, AIResponse,
    AIProviderStatus, AIProviderError, AIProviderMetrics
)
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .ollama_provider import OllamaProvider
from .credential_manager import CredentialManager
from .health_monitor import HealthMonitor


class OptimizedAIProviderManager:
    """
    Optimized AI Provider Manager with comprehensive cloud integration optimization.
    
    This manager integrates all optimization components to provide:
    - <10 second cloud processing times
    - Intelligent content-aware routing
    - Smart caching with Privacy Pipeline integration
    - Predictive failover capabilities
    - Cost optimization and tracking
    - Real-time performance monitoring
    
    Features:
    - Content-type specific processing optimization
    - Multi-tier failover (Cloud Premium → Cloud Standard → Local GPU → Local CPU)
    - Privacy-preserving request routing
    - Intelligent caching with configurable strategies
    - Performance-based provider selection
    - Cost tracking and budget management
    - Real-time analytics and alerting
    """
    
    def __init__(self, config: Dict[str, Any], data_path: str = "/data", hass=None):
        """
        Initialize Optimized AI Provider Manager.
        
        Args:
            config: Configuration dictionary
            data_path: Path for storing data
            hass: Home Assistant instance for notifications
        """
        self.config = config
        self.data_path = data_path
        self.hass = hass
        self.logger = logging.getLogger("optimized_ai_provider_manager")
        
        # Enhanced provider configurations
        self.enhanced_configs: Dict[str, EnhancedAIProviderConfiguration] = {}
        self.providers: Dict[str, BaseAIProvider] = {}
        
        # Core optimization components
        self.content_analyzer = ContentAnalyzer(config.get("content_analyzer", {}))
        self.smart_cache = SmartCache(
            config.get("smart_cache", {}),
            strategy=CacheStrategy(config.get("cache_strategy", "privacy_aware"))
        )
        self.provider_selector = EnhancedProviderSelector(
            config.get("provider_selector", {}),
            selection_strategy=SelectionStrategy(config.get("selection_strategy", "weighted_scoring"))
        )
        self.failover_manager = IntelligentFailoverManager(
            config.get("failover_manager", {}),
            strategy=FailoverStrategy(config.get("failover_strategy", "tier_based"))
        )
        self.performance_monitor = EnhancedPerformanceMonitor(
            config.get("performance_monitor", {}),
            data_retention_days=config.get("data_retention_days", 30)
        )
        
        # Legacy support
        self.credential_manager = CredentialManager(config, data_path)
        self.health_monitor = HealthMonitor("optimized_ai_provider_manager", config)
        
        # Provider class mapping
        self.provider_classes = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "google": GoogleProvider,
            "ollama": OllamaProvider
        }
        
        # Performance tracking
        self.request_history: List[Dict[str, Any]] = []
        self.optimization_enabled = config.get("optimization_enabled", True)
        
        # Load configurations
        self._load_enhanced_configurations()
        
        self.logger.info("Optimized AI Provider Manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize all providers and optimization components"""
        try:
            self.logger.info("Initializing Optimized AI Provider Manager...")
            
            # Initialize core components
            await self.credential_manager.health_check()
            await self.health_monitor.start_monitoring()
            
            # Initialize providers with enhanced configurations
            await self._initialize_enhanced_providers()
            
            # Set up performance monitoring
            self._setup_performance_monitoring()
            
            # Set up cost budgets
            self._setup_cost_budgets()
            
            self.logger.info(f"Optimized AI Provider Manager initialized with {len(self.providers)} providers")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Optimized AI Provider Manager: {e}")
            return False
    
    def _load_enhanced_configurations(self):
        """Load enhanced provider configurations"""
        providers_config = self.config.get("providers", {})
        
        for provider_name, provider_config in providers_config.items():
            if provider_name in self.provider_classes:
                # Create enhanced configuration
                enhanced_config = self._create_enhanced_config(provider_name, provider_config)
                self.enhanced_configs[provider_name] = enhanced_config
                
                self.logger.info(f"Loaded enhanced configuration for provider: {provider_name}")
    
    def _create_enhanced_config(
        self,
        provider_name: str,
        provider_config: Dict[str, Any]
    ) -> EnhancedAIProviderConfiguration:
        """Create enhanced configuration from legacy config"""
        
        # Determine provider tier
        tier_mapping = {
            "openai": ProviderTier.CLOUD_PREMIUM,
            "anthropic": ProviderTier.CLOUD_PREMIUM,
            "google": ProviderTier.CLOUD_STANDARD,
            "ollama": ProviderTier.LOCAL_CPU
        }
        provider_tier = tier_mapping.get(provider_name, ProviderTier.CLOUD_STANDARD)
        
        # Create capabilities based on provider type
        capabilities = self._create_provider_capabilities(provider_name, provider_config)
        
        # Get API key
        api_key = self.credential_manager.get_credential(provider_name, "api_key") or ""
        
        return EnhancedAIProviderConfiguration(
            name=provider_name,
            provider_tier=provider_tier,
            enabled=provider_config.get("enabled", True),
            priority=provider_config.get("priority", 1),
            api_key=api_key,
            model_name=provider_config.get("model_name", ""),
            base_url=provider_config.get("base_url"),
            capabilities=capabilities
        )
    
    def _create_provider_capabilities(
        self,
        provider_name: str,
        provider_config: Dict[str, Any]
    ) -> ProviderCapability:
        """Create provider capabilities based on provider type"""
        
        capability_templates = {
            "openai": ProviderCapability(
                content_types={ContentType.TEXT, ContentType.CODE, ContentType.IMAGE, ContentType.MULTIMODAL},
                max_tokens=32000,
                supports_streaming=True,
                supports_function_calling=True,
                vision_capabilities=True,
                code_generation_quality=0.95,
                instruction_following=0.95,
                multimodal_support=True,
                latency_profile="fast",
                cost_efficiency="medium",
                reliability_score=0.95
            ),
            "anthropic": ProviderCapability(
                content_types={ContentType.TEXT, ContentType.CODE, ContentType.MULTIMODAL},
                max_tokens=200000,
                supports_streaming=True,
                supports_function_calling=True,
                vision_capabilities=True,
                code_generation_quality=0.98,
                instruction_following=0.98,
                multimodal_support=True,
                latency_profile="standard",
                cost_efficiency="medium",
                reliability_score=0.97
            ),
            "google": ProviderCapability(
                content_types={ContentType.TEXT, ContentType.CODE, ContentType.IMAGE, ContentType.MULTIMODAL},
                max_tokens=1000000,
                supports_streaming=True,
                supports_function_calling=True,
                vision_capabilities=True,
                code_generation_quality=0.92,
                instruction_following=0.90,
                multimodal_support=True,
                latency_profile="fast",
                cost_efficiency="high",
                reliability_score=0.92
            ),
            "ollama": ProviderCapability(
                content_types={ContentType.TEXT, ContentType.CODE},
                max_tokens=4096,
                supports_streaming=True,
                supports_function_calling=False,
                vision_capabilities=False,
                code_generation_quality=0.85,
                instruction_following=0.85,
                multimodal_support=False,
                latency_profile="slow",
                cost_efficiency="high",  # Local = no API costs
                reliability_score=0.90
            )
        }
        
        return capability_templates.get(provider_name, ProviderCapability())
    
    async def _initialize_enhanced_providers(self):
        """Initialize providers with enhanced configurations"""
        for provider_name, enhanced_config in self.enhanced_configs.items():
            if not enhanced_config.enabled:
                continue
            
            try:
                # Create legacy configuration for compatibility
                legacy_config = AIProviderConfiguration(
                    name=provider_name,
                    enabled=enhanced_config.enabled,
                    priority=enhanced_config.priority,
                    api_key=enhanced_config.api_key,
                    model_name=enhanced_config.model_name,
                    base_url=enhanced_config.base_url,
                    timeout_seconds=enhanced_config.get_timeout(ContentType.TEXT),
                    max_retries=3,
                    rate_limit_rpm=60,
                    rate_limit_tpm=10000,
                    daily_budget=enhanced_config.cost_optimization.daily_budget,
                    cost_per_request=0.01,
                    health_check_interval=300
                )
                
                # Create provider instance
                provider_class = self.provider_classes[provider_name]
                provider = provider_class(legacy_config)
                
                # Initialize provider
                if await provider.initialize():
                    self.providers[provider_name] = provider
                    self.logger.info(f"Successfully initialized enhanced provider: {provider_name}")
                else:
                    self.logger.error(f"Failed to initialize enhanced provider: {provider_name}")
                    
            except Exception as e:
                self.logger.error(f"Error initializing enhanced provider {provider_name}: {e}")
    
    def _setup_performance_monitoring(self):
        """Set up performance monitoring for all providers"""
        for provider_name in self.enhanced_configs:
            # Set budget limits
            config = self.enhanced_configs[provider_name]
            self.performance_monitor.set_budget_limit(
                provider_name,
                config.cost_optimization.daily_budget
            )
            
            # Set custom alert thresholds
            self.performance_monitor.set_alert_threshold(
                MetricType.RESPONSE_TIME, AlertLevel.WARNING,
                config.get_timeout(ContentType.TEXT) * 0.8
            )
    
    def _setup_cost_budgets(self):
        """Set up cost budgets for provider selection"""
        for provider_name, config in self.enhanced_configs.items():
            self.provider_selector.set_daily_budget(
                provider_name,
                config.cost_optimization.daily_budget
            )
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """
        Process AI request with full optimization pipeline.
        
        Args:
            request: AI request to process
            
        Returns:
            Optimized AI response
        """
        start_time = time.time()
        request_id = request.request_id
        
        try:
            # Step 1: Content Analysis
            content_analysis = await self._analyze_request_content(request)
            
            # Step 2: Check Cache
            if self.optimization_enabled:
                cached_response = await self.smart_cache.get(request, content_analysis)
                if cached_response:
                    self.logger.info(f"Cache hit for request {request_id}")
                    return cached_response
            
            # Step 3: Provider Selection
            selected_provider = await self._select_optimal_provider(request, content_analysis)
            if not selected_provider:
                raise AIProviderError(
                    "No suitable providers available",
                    error_code="NO_PROVIDERS_AVAILABLE",
                    provider="manager",
                    retryable=False
                )
            
            # Step 4: Record request start
            self.performance_monitor.record_request_start(
                selected_provider.config.name, request, content_analysis
            )
            
            # Step 5: Process with failover handling
            response = await self._process_with_enhanced_failover(
                selected_provider, request, content_analysis
            )
            
            # Step 6: Record completion and cache response
            self.performance_monitor.record_request_completion(
                selected_provider.config.name, request, response, content_analysis
            )
            
            if self.optimization_enabled and not response.error:
                await self.smart_cache.put(request, response, content_analysis)
            
            # Step 7: Update provider performance
            self.provider_selector.update_provider_performance(
                selected_provider.config.name,
                response.response_time,
                not bool(response.error),
                response.cost
            )
            
            self.failover_manager.record_provider_outcome(
                selected_provider.config.name,
                response.response_time,
                not bool(response.error),
                response.error
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing optimized request {request_id}: {e}")
            
            # Return error response
            return AIResponse(
                request_id=request_id,
                response_text="",
                model_used="unknown",
                provider="optimized_manager",
                confidence=0.0,
                cost=0.0,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def _analyze_request_content(self, request: AIRequest) -> ContentAnalysisResult:
        """Analyze request content for optimization"""
        try:
            content_analysis = await self.content_analyzer.analyze_content(
                content=request.prompt,
                image_path=request.image_path,
                image_data=request.image_data,
                context=request.context
            )
            
            self.logger.debug(
                json.dumps({
                    "event": "content_analysis_complete",
                    "request_id": request.request_id,
                    "content_type": content_analysis.content_type.value,
                    "complexity_score": content_analysis.complexity_score,
                    "size_estimate": content_analysis.size_estimate,
                    "privacy_sensitive": content_analysis.privacy_sensitive
                })
            )
            
            return content_analysis
            
        except Exception as e:
            self.logger.error(f"Content analysis failed: {e}")
            # Return basic analysis as fallback
            return ContentAnalysisResult(
                content_type=ContentType.TEXT,
                primary_type="text",
                confidence=0.5
            )
    
    async def _select_optimal_provider(
        self,
        request: AIRequest,
        content_analysis: ContentAnalysisResult
    ) -> Optional[BaseAIProvider]:
        """Select optimal provider using enhanced selection logic"""
        try:
            # Create selection context
            context = SelectionContext(
                request=request,
                content_analysis=content_analysis,
                priority=ProcessingPriority(request.priority) if request.priority else ProcessingPriority.NORMAL,
                budget_constraint=request.context.get("budget_constraint") if request.context else None,
                require_privacy_pipeline=content_analysis.privacy_sensitive
            )
            
            # Use enhanced provider selector
            if self.optimization_enabled:
                selected_provider = await self.provider_selector.select_provider(
                    self.providers,
                    self.enhanced_configs,
                    context
                )
            else:
                # Fallback to simple selection
                selected_provider = self._simple_provider_selection(content_analysis)
            
            return selected_provider
            
        except Exception as e:
            self.logger.error(f"Provider selection failed: {e}")
            return self._simple_provider_selection(content_analysis)
    
    def _simple_provider_selection(self, content_analysis: ContentAnalysisResult) -> Optional[BaseAIProvider]:
        """Simple fallback provider selection"""
        available_providers = [
            provider for provider in self.providers.values()
            if provider.is_available()
        ]
        
        if not available_providers:
            return None
        
        # Basic content-aware selection
        if content_analysis.content_type in [ContentType.IMAGE, ContentType.MULTIMODAL]:
            vision_providers = [p for p in available_providers if p.config.name in ["openai", "google"]]
            if vision_providers:
                return vision_providers[0]
        
        # Return first available provider
        return available_providers[0]
    
    async def _process_with_enhanced_failover(
        self,
        provider: BaseAIProvider,
        request: AIRequest,
        content_analysis: ContentAnalysisResult
    ) -> AIResponse:
        """Process request with enhanced failover capabilities"""
        try:
            # Check if failover should be triggered preemptively
            if self.optimization_enabled:
                should_failover, reason = await self.failover_manager.should_failover(
                    provider.config.name,
                    self.enhanced_configs[provider.config.name],
                    content_analysis
                )
                
                if should_failover:
                    self.logger.warning(f"Preemptive failover triggered for {provider.config.name}: {reason.value}")
                    return await self._execute_failover(provider, request, content_analysis, reason)
            
            # Process with primary provider
            response = await provider.process_request_with_retry(request)
            
            # Check response quality for post-processing failover
            if self.optimization_enabled and response.confidence < 0.7 and not response.error:
                self.logger.info(f"Low confidence response from {provider.config.name}, attempting failover")
                failover_response = await self._execute_failover(
                    provider, request, content_analysis, FailoverReason.QUALITY_THRESHOLD
                )
                
                # Use failover response if significantly better
                if failover_response.confidence > response.confidence + 0.1:
                    return failover_response
            
            return response
            
        except AIProviderError as e:
            if self.optimization_enabled and e.retryable:
                self.logger.info(f"Provider error, attempting failover: {e}")
                return await self._execute_failover(
                    provider, request, content_analysis, FailoverReason.PROVIDER_UNAVAILABLE
                )
            raise e
        except Exception as e:
            self.logger.error(f"Unexpected error in provider processing: {e}")
            raise AIProviderError(str(e), provider=provider.config.name)
    
    async def _execute_failover(
        self,
        failed_provider: BaseAIProvider,
        request: AIRequest,
        content_analysis: ContentAnalysisResult,
        reason: FailoverReason
    ) -> AIResponse:
        """Execute intelligent failover to alternative providers"""
        try:
            # Get failover targets
            failover_targets = await self.failover_manager.get_failover_targets(
                failed_provider.config.name,
                self.enhanced_configs[failed_provider.config.name],
                self.enhanced_configs,
                content_analysis
            )
            
            if not failover_targets:
                raise AIProviderError(
                    "No failover targets available",
                    error_code="NO_FAILOVER_TARGETS",
                    provider=failed_provider.config.name,
                    retryable=False
                )
            
            # Try failover targets in order
            for target in failover_targets[:3]:  # Try top 3 targets
                target_provider = self.providers.get(target.provider_name)
                if not target_provider or not target_provider.is_available():
                    continue
                
                try:
                    self.logger.info(f"Attempting failover to {target.provider_name}")
                    
                    # Apply estimated delay if needed
                    if target.estimated_delay > 0:
                        await asyncio.sleep(target.estimated_delay)
                    
                    response = await target_provider.process_request_with_retry(request)
                    
                    # Record successful failover
                    self.failover_manager.record_failover_event(
                        failed_provider.config.name,
                        target.provider_name,
                        reason,
                        content_analysis.content_type,
                        success=not bool(response.error),
                        performance_impact=target.expected_performance - 1.0,
                        cost_impact=(target.cost_multiplier - 1.0) * response.cost
                    )
                    
                    # Update response metadata
                    response.metadata.update({
                        "failover_used": True,
                        "original_provider": failed_provider.config.name,
                        "failover_reason": reason.value,
                        "failover_provider": target.provider_name
                    })
                    
                    return response
                    
                except Exception as e:
                    self.logger.warning(f"Failover to {target.provider_name} failed: {e}")
                    continue
            
            # All failover attempts failed
            raise AIProviderError(
                "All failover attempts failed",
                error_code="FAILOVER_EXHAUSTED",
                provider=failed_provider.config.name,
                retryable=False
            )
            
        except Exception as e:
            self.logger.error(f"Failover execution failed: {e}")
            raise AIProviderError(
                f"Failover execution failed: {e}",
                error_code="FAILOVER_ERROR",
                provider=failed_provider.config.name,
                retryable=False
            )
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get comprehensive optimization status"""
        return {
            "optimization_enabled": self.optimization_enabled,
            "providers": {
                name: {
                    "status": provider.get_status().value,
                    "available": provider.is_available(),
                    "tier": self.enhanced_configs[name].provider_tier.value,
                    "capabilities": list(self.enhanced_configs[name].capabilities.content_types)
                }
                for name, provider in self.providers.items()
            },
            "cache_stats": self.smart_cache.get_stats().__dict__,
            "provider_selection_stats": self.provider_selector.get_provider_stats(),
            "failover_stats": self.failover_manager.get_failover_statistics(),
            "system_health": self.performance_monitor.get_system_health(),
            "optimization_recommendations": [
                rec.__dict__ for rec in self.performance_monitor.get_optimization_recommendations()
            ]
        }
    
    def get_performance_summary(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary for specific provider or all providers"""
        if provider_name:
            summary = self.performance_monitor.get_provider_summary(provider_name)
            return summary.__dict__ if summary else {}
        else:
            return {
                name: summary.__dict__
                for name, summary in {
                    name: self.performance_monitor.get_provider_summary(name)
                    for name in self.providers.keys()
                }.items()
                if summary is not None
            }
    
    def get_cost_analysis(self) -> Dict[str, Any]:
        """Get comprehensive cost analysis"""
        analysis = {
            "total_daily_cost": 0.0,
            "providers": {},
            "budget_status": {},
            "cost_trends": {}
        }
        
        for provider_name in self.providers.keys():
            cost_summary = self.performance_monitor.get_cost_summary(provider_name, "daily")
            analysis["providers"][provider_name] = cost_summary
            analysis["total_daily_cost"] += cost_summary.get("cost", 0.0)
            
            # Budget status
            budget = cost_summary.get("budget", 0.0)
            utilization = cost_summary.get("utilization", 0.0)
            
            if utilization > 0.9:
                status = "critical"
            elif utilization > 0.8:
                status = "warning"
            else:
                status = "healthy"
            
            analysis["budget_status"][provider_name] = {
                "status": status,
                "utilization": utilization,
                "remaining": cost_summary.get("remaining", 0.0)
            }
        
        return analysis
    
    async def clear_cache(self):
        """Clear all cached responses"""
        self.smart_cache.clear_all()
        self.content_analyzer.clear_cache()
        self.logger.info("All caches cleared")
    
    async def reset_provider_metrics(self, provider_name: str):
        """Reset metrics for specific provider"""
        self.failover_manager.reset_provider_health(provider_name)
        self.logger.info(f"Reset metrics for provider: {provider_name}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of optimized system"""
        health_report = {
            "overall_health": "healthy",
            "optimization_status": "enabled" if self.optimization_enabled else "disabled",
            "components": {},
            "providers": {},
            "alerts": []
        }
        
        try:
            # Check providers
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
            
            # Check optimization components
            system_health = self.performance_monitor.get_system_health()
            health_report["components"]["performance_monitor"] = system_health
            
            if system_health["status"] in ["critical", "degraded"]:
                health_report["overall_health"] = system_health["status"]
            
            # Get recent alerts
            recent_alerts = self.performance_monitor.get_recent_alerts(5)
            health_report["alerts"] = [
                {
                    "timestamp": datetime.fromtimestamp(alert.timestamp).isoformat(),
                    "level": alert.alert_level.value,
                    "provider": alert.provider_name,
                    "message": alert.message
                }
                for alert in recent_alerts
            ]
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            health_report["overall_health"] = "error"
            health_report["error"] = str(e)
        
        return health_report
    
    async def shutdown(self):
        """Shutdown optimized manager and all components"""
        self.logger.info("Shutting down Optimized AI Provider Manager")
        
        try:
            # Shutdown optimization components
            await self.smart_cache.shutdown()
            await self.failover_manager.shutdown()
            await self.performance_monitor.shutdown()
            
            # Shutdown providers
            for provider_name, provider in self.providers.items():
                try:
                    await provider.shutdown()
                    self.logger.info(f"Shutdown provider: {provider_name}")
                except Exception as e:
                    self.logger.error(f"Error shutting down provider {provider_name}: {e}")
            
            # Shutdown legacy components
            await self.health_monitor.stop_monitoring()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        
        self.logger.info("Optimized AI Provider Manager shutdown complete")
    
    # Legacy compatibility methods
    def get_provider_status(self) -> Dict[str, Any]:
        """Legacy method for provider status"""
        return self.get_optimization_status()["providers"]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Legacy method for performance metrics"""
        return {
            "optimization_status": self.get_optimization_status(),
            "performance_summary": self.get_performance_summary(),
            "cost_analysis": self.get_cost_analysis()
        }
    
    def clear_cache_legacy(self):
        """Legacy cache clear method"""
        asyncio.create_task(self.clear_cache())
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Legacy cost summary method"""
        return self.get_cost_analysis()