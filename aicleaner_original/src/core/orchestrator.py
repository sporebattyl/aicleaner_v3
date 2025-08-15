"""
Orchestrator for AICleaner V3
PDCA-based coordination of providers with privacy spectrum and health monitoring
Implements the "Arbiter" pattern for intelligent provider selection and fallback
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
import logging

from .privacy_engine import PrivacyEngine, PrivacyLevel, SanitizationResult
from .annotation_engine import AnnotationEngine
from ..providers.base_provider import (
    LLMProvider, ProviderRegistry, AnalysisResult, 
    ProviderStatus, ProviderHealth, Task
)

class OrchestratorMode(Enum):
    """Operating modes for the orchestrator"""
    PLAN = "plan"        # Planning phase - analyze requirements
    DO = "do"            # Doing phase - execute analysis  
    CHECK = "check"      # Checking phase - validate results
    ACT = "act"          # Acting phase - apply results and learn

@dataclass
class AnalysisRequest:
    """Request for image analysis"""
    image_bytes: bytes
    prompt: str
    privacy_level: PrivacyLevel
    preferred_provider: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class OrchestratorResult:
    """Complete result from orchestrator processing"""
    tasks: List[Task]
    annotated_image: Optional[bytes] = None
    processing_summary: Dict[str, Any] = None
    privacy_result: Optional[SanitizationResult] = None
    provider_used: Optional[str] = None
    fallback_used: bool = False
    total_processing_time: float = 0.0

@dataclass
class ProviderFallbackChain:
    """Defines fallback chain for provider selection"""
    primary: str
    secondary: Optional[str] = None
    tertiary: Optional[str] = None
    local_fallback: Optional[str] = None

class PDCAOrchestrator:
    """
    PDCA-based orchestrator implementing the Arbiter pattern
    Coordinates privacy processing, provider selection, and result validation
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.privacy_engine = PrivacyEngine(config.get('privacy', {}))
        self.annotation_engine = AnnotationEngine(config.get('annotation', {}))
        self.provider_registry = ProviderRegistry()
        
        # Performance tracking
        self._request_count = 0
        self._success_count = 0
        self._fallback_count = 0
        self._performance_history: List[Dict[str, Any]] = []
        
        # Provider selection strategy
        self.fallback_chains: Dict[PrivacyLevel, ProviderFallbackChain] = self._setup_fallback_chains()
    
    def _setup_fallback_chains(self) -> Dict[PrivacyLevel, ProviderFallbackChain]:
        """Setup fallback chains for different privacy levels"""
        chains = {}
        
        # Level 1 & 2 & 3: Cloud-first with local fallback
        cloud_chain = ProviderFallbackChain(
            primary="gemini",
            secondary="gemini_fallback", 
            local_fallback="ollama"
        )
        
        chains[PrivacyLevel.LEVEL_1_RAW] = cloud_chain
        chains[PrivacyLevel.LEVEL_2_SANITIZED] = cloud_chain
        chains[PrivacyLevel.LEVEL_3_METADATA] = cloud_chain
        
        # Level 4: Local-only
        chains[PrivacyLevel.LEVEL_4_LOCAL] = ProviderFallbackChain(
            primary="ollama",
            secondary=None,  # No cloud fallback for privacy level 4
            tertiary=None,
            local_fallback=None
        )
        
        return chains
    
    async def process_analysis_request(self, request: AnalysisRequest) -> OrchestratorResult:
        """
        Main entry point - processes analysis request through PDCA cycle
        
        Args:
            request: Analysis request with image and parameters
            
        Returns:
            Complete orchestrator result with tasks and annotations
        """
        start_time = time.time()
        self._request_count += 1
        
        try:
            # PLAN Phase: Analyze requirements and select strategy
            plan_result = await self._pdca_plan(request)
            
            # DO Phase: Execute the analysis
            do_result = await self._pdca_do(request, plan_result)
            
            # CHECK Phase: Validate results
            check_result = await self._pdca_check(do_result, request)
            
            # ACT Phase: Apply results and learn from outcome
            final_result = await self._pdca_act(check_result, start_time)
            
            self._success_count += 1
            return final_result
            
        except Exception as e:
            self.logger.error(f"Orchestrator processing failed: {e}")
            # Return error result
            return OrchestratorResult(
                tasks=[],
                processing_summary={"error": str(e), "success": False},
                total_processing_time=time.time() - start_time
            )
    
    async def _pdca_plan(self, request: AnalysisRequest) -> Dict[str, Any]:
        """
        PLAN Phase: Analyze request and determine optimal processing strategy
        """
        self.logger.info(f"PLAN: Analyzing request for privacy level {request.privacy_level.value}")
        
        # Determine fallback chain
        fallback_chain = self.fallback_chains[request.privacy_level]
        
        # Health check available providers
        available_providers = await self._check_provider_health(fallback_chain)
        
        # Select optimal provider
        selected_provider = self._select_optimal_provider(
            available_providers, 
            request.preferred_provider,
            fallback_chain
        )
        
        # Determine privacy processing requirements
        privacy_processing = self._determine_privacy_processing(request.privacy_level)
        
        plan = {
            "selected_provider": selected_provider,
            "available_providers": available_providers,
            "fallback_chain": fallback_chain,
            "privacy_processing": privacy_processing,
            "requires_annotation": True,
            "estimated_processing_time": self._estimate_processing_time(request, selected_provider)
        }
        
        self.logger.info(f"PLAN: Selected provider '{selected_provider}' for request")
        return plan
    
    async def _pdca_do(self, request: AnalysisRequest, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        DO Phase: Execute the analysis plan
        """
        self.logger.info(f"DO: Executing analysis with provider '{plan['selected_provider']}'")
        
        # Step 1: Privacy processing
        privacy_result = await self.privacy_engine.process_image(
            request.image_bytes, 
            request.privacy_level
        )
        
        # Step 2: LLM analysis
        analysis_result = await self._execute_llm_analysis(
            request, privacy_result, plan
        )
        
        # Step 3: Visual annotation (if applicable)
        annotated_image = None
        if plan["requires_annotation"] and analysis_result.tasks:
            # Use sanitized image if available, otherwise original
            image_for_annotation = privacy_result.sanitized_image or request.image_bytes
            if image_for_annotation:
                annotated_image = await self.annotation_engine.annotate_image(
                    image_for_annotation, 
                    analysis_result.tasks
                )
        
        return {
            "privacy_result": privacy_result,
            "analysis_result": analysis_result,
            "annotated_image": annotated_image,
            "provider_used": plan["selected_provider"],
            "plan": plan
        }
    
    async def _pdca_check(self, do_result: Dict[str, Any], original_request: AnalysisRequest) -> Dict[str, Any]:
        """
        CHECK Phase: Validate results and determine if retry is needed
        """
        analysis_result = do_result["analysis_result"]
        provider_used = do_result["provider_used"]
        
        self.logger.info(f"CHECK: Validating results from provider '{provider_used}'")
        
        # Validation criteria
        validation = {
            "has_tasks": len(analysis_result.tasks) > 0,
            "tasks_have_descriptions": all(task.description.strip() for task in analysis_result.tasks),
            "reasonable_task_count": 1 <= len(analysis_result.tasks) <= 20,
            "processing_successful": analysis_result is not None,
            "within_time_limit": True  # TODO: Add time limit checking
        }
        
        validation["overall_valid"] = all(validation.values())
        
        # If validation fails, try fallback provider
        if not validation["overall_valid"]:
            self.logger.warning(f"CHECK: Results validation failed, attempting fallback")
            
            fallback_result = await self._attempt_fallback(
                original_request, 
                do_result["plan"]
            )
            
            if fallback_result:
                do_result.update(fallback_result)
                validation["fallback_used"] = True
                self._fallback_count += 1
        
        do_result["validation"] = validation
        return do_result
    
    async def _pdca_act(self, check_result: Dict[str, Any], start_time: float) -> OrchestratorResult:
        """
        ACT Phase: Apply results and update system learning
        """
        total_time = time.time() - start_time
        
        # Update performance history
        performance_record = {
            "timestamp": time.time(),
            "provider_used": check_result["provider_used"],
            "privacy_level": check_result.get("privacy_result", {}).privacy_level,
            "task_count": len(check_result["analysis_result"].tasks),
            "processing_time": total_time,
            "validation_success": check_result["validation"]["overall_valid"],
            "fallback_used": check_result["validation"].get("fallback_used", False)
        }
        
        self._performance_history.append(performance_record)
        
        # Keep only recent history
        if len(self._performance_history) > 100:
            self._performance_history = self._performance_history[-100:]
        
        # Log performance
        self.logger.info(
            f"ACT: Completed analysis in {total_time:.2f}s, "
            f"found {len(check_result['analysis_result'].tasks)} tasks"
        )
        
        # Create processing summary
        processing_summary = {
            "success": True,
            "provider_used": check_result["provider_used"],
            "privacy_level": check_result["privacy_result"].privacy_level.value,
            "tasks_generated": len(check_result["analysis_result"].tasks),
            "processing_time": total_time,
            "fallback_used": check_result["validation"].get("fallback_used", False),
            "validation_details": check_result["validation"]
        }
        
        return OrchestratorResult(
            tasks=check_result["analysis_result"].tasks,
            annotated_image=check_result.get("annotated_image"),
            processing_summary=processing_summary,
            privacy_result=check_result["privacy_result"],
            provider_used=check_result["provider_used"],
            fallback_used=check_result["validation"].get("fallback_used", False),
            total_processing_time=total_time
        )
    
    async def _check_provider_health(self, fallback_chain: ProviderFallbackChain) -> Dict[str, ProviderHealth]:
        """Check health of all providers in fallback chain"""
        providers_to_check = [
            fallback_chain.primary,
            fallback_chain.secondary,
            fallback_chain.tertiary,
            fallback_chain.local_fallback
        ]
        providers_to_check = [p for p in providers_to_check if p is not None]
        
        health_results = {}
        
        # Check providers in parallel
        health_tasks = []
        for provider_name in providers_to_check:
            provider = self.provider_registry.get_provider(provider_name)
            if provider:
                health_tasks.append(self._safe_health_check(provider_name, provider))
        
        if health_tasks:
            health_checks = await asyncio.gather(*health_tasks, return_exceptions=True)
            
            for i, result in enumerate(health_checks):
                provider_name = providers_to_check[i]
                if isinstance(result, Exception):
                    health_results[provider_name] = ProviderHealth(
                        status=ProviderStatus.UNHEALTHY,
                        error_message=str(result)
                    )
                else:
                    health_results[provider_name] = result
        
        return health_results
    
    async def _safe_health_check(self, provider_name: str, provider: LLMProvider) -> ProviderHealth:
        """Safely perform health check with timeout"""
        try:
            return await asyncio.wait_for(provider.health_check(), timeout=10.0)
        except asyncio.TimeoutError:
            return ProviderHealth(
                status=ProviderStatus.UNHEALTHY,
                error_message="Health check timed out"
            )
        except Exception as e:
            return ProviderHealth(
                status=ProviderStatus.UNHEALTHY,
                error_message=str(e)
            )
    
    def _select_optimal_provider(
        self, 
        available_providers: Dict[str, ProviderHealth], 
        preferred_provider: Optional[str],
        fallback_chain: ProviderFallbackChain
    ) -> str:
        """Select the best available provider"""
        
        # If user specified a preference and it's healthy, use it
        if preferred_provider and preferred_provider in available_providers:
            if available_providers[preferred_provider].status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]:
                return preferred_provider
        
        # Otherwise, go through fallback chain
        for provider_name in [fallback_chain.primary, fallback_chain.secondary, 
                             fallback_chain.tertiary, fallback_chain.local_fallback]:
            if provider_name and provider_name in available_providers:
                if available_providers[provider_name].status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]:
                    return provider_name
        
        # If no providers are healthy, return the primary anyway (will fail gracefully)
        return fallback_chain.primary
    
    def _determine_privacy_processing(self, privacy_level: PrivacyLevel) -> Dict[str, Any]:
        """Determine what privacy processing is needed"""
        return {
            "level": privacy_level,
            "requires_sanitization": privacy_level == PrivacyLevel.LEVEL_2_SANITIZED,
            "metadata_only": privacy_level == PrivacyLevel.LEVEL_3_METADATA,
            "local_processing": privacy_level == PrivacyLevel.LEVEL_4_LOCAL
        }
    
    def _estimate_processing_time(self, request: AnalysisRequest, provider_name: str) -> float:
        """Estimate processing time based on historical data"""
        # Simple estimation based on privacy level and provider
        base_times = {
            PrivacyLevel.LEVEL_1_RAW: 2.0,
            PrivacyLevel.LEVEL_2_SANITIZED: 4.0,
            PrivacyLevel.LEVEL_3_METADATA: 3.0,
            PrivacyLevel.LEVEL_4_LOCAL: 15.0
        }
        
        provider_multipliers = {
            "gemini": 1.0,
            "ollama": 3.0
        }
        
        base_time = base_times.get(request.privacy_level, 5.0)
        multiplier = provider_multipliers.get(provider_name, 1.5)
        
        return base_time * multiplier
    
    async def _execute_llm_analysis(
        self, 
        request: AnalysisRequest, 
        privacy_result: SanitizationResult, 
        plan: Dict[str, Any]
    ) -> AnalysisResult:
        """Execute LLM analysis based on privacy processing result"""
        provider = self.provider_registry.get_provider(plan["selected_provider"])
        if not provider:
            raise ValueError(f"Provider {plan['selected_provider']} not found")
        
        # Prepare input based on privacy level
        if privacy_result.privacy_level == PrivacyLevel.LEVEL_3_METADATA:
            # For metadata-only, create a text prompt with the metadata
            metadata_prompt = f"{request.prompt}\n\nImage analysis: {privacy_result.metadata}"
            # Use empty bytes as placeholder since we're only sending metadata
            return await provider.analyze(b"", metadata_prompt)
        else:
            # Use the sanitized image (or original if no sanitization)
            image_to_analyze = privacy_result.sanitized_image or request.image_bytes
            return await provider.analyze(image_to_analyze, request.prompt)
    
    async def _attempt_fallback(self, request: AnalysisRequest, original_plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attempt fallback to next available provider"""
        fallback_chain = original_plan["fallback_chain"]
        available_providers = original_plan["available_providers"]
        
        # Find next available provider in chain
        current_provider = original_plan["selected_provider"]
        chain_providers = [
            fallback_chain.primary,
            fallback_chain.secondary,
            fallback_chain.tertiary,
            fallback_chain.local_fallback
        ]
        
        try:
            current_index = chain_providers.index(current_provider)
            for next_provider in chain_providers[current_index + 1:]:
                if (next_provider and next_provider in available_providers and 
                    available_providers[next_provider].status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]):
                    
                    self.logger.info(f"Attempting fallback to provider '{next_provider}'")
                    
                    # Create new plan with fallback provider
                    fallback_plan = original_plan.copy()
                    fallback_plan["selected_provider"] = next_provider
                    
                    # Execute with fallback provider
                    return await self._pdca_do(request, fallback_plan)
                    
        except (ValueError, Exception) as e:
            self.logger.error(f"Fallback attempt failed: {e}")
        
        return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics and statistics"""
        if not self._performance_history:
            return {"no_data": True}
        
        recent_history = self._performance_history[-20:]  # Last 20 requests
        
        return {
            "total_requests": self._request_count,
            "success_rate": self._success_count / self._request_count if self._request_count > 0 else 0,
            "fallback_rate": self._fallback_count / self._request_count if self._request_count > 0 else 0,
            "average_processing_time": sum(r["processing_time"] for r in recent_history) / len(recent_history),
            "most_used_provider": max(set(r["provider_used"] for r in recent_history), 
                                    key=lambda x: sum(1 for r in recent_history if r["provider_used"] == x)),
            "average_tasks_per_request": sum(r["task_count"] for r in recent_history) / len(recent_history)
        }
    
    def register_provider(self, provider: LLMProvider) -> None:
        """Register a new provider with the orchestrator"""
        self.provider_registry.register(provider)
        self.logger.info(f"Registered provider: {provider.name}")
    
    async def shutdown(self) -> None:
        """Clean shutdown of orchestrator"""
        self.logger.info("Shutting down orchestrator")
        # Could add cleanup logic here if needed