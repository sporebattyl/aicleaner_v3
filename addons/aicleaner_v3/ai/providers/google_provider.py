"""
Google Gemini Provider Implementation
Phase 2A: AI Model Provider Optimization

Provides Google Gemini integration with enhanced features including
connection pooling, request batching, and advanced error handling.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
from PIL import Image

from .base_provider import (
    BaseAIProvider, AIProviderConfiguration, AIRequest, AIResponse,
    AIProviderStatus, AIProviderError
)
from .rate_limiter import RateLimiter, RateLimitConfig
from .health_monitor import HealthMonitor

try:
    import google.generativeai as genai
    from google.generativeai import GenerativeModel
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class GoogleProvider(BaseAIProvider):
    """
    Google Gemini provider with enhanced features.
    
    Features:
    - Gemini 1.5 Flash/Pro image analysis
    - Connection pooling
    - Request batching
    - Advanced error handling
    - Cost tracking
    - Performance monitoring
    """
    
    def __init__(self, config: AIProviderConfiguration):
        """
        Initialize Google provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__(config)
        
        if not GOOGLE_AVAILABLE:
            raise AIProviderError(
                "Google Generative AI package not available",
                error_code="PACKAGE_NOT_AVAILABLE",
                provider="google",
                retryable=False
            )
        
        # Google specific configuration
        self.model = None
        self.model_name = config.model_name or "gemini-1.5-flash"
        self.temperature = 0.1
        self.max_output_tokens = 4000
        
        # Rate limiter
        rate_config = RateLimitConfig(
            requests_per_minute=config.rate_limit_rpm,
            tokens_per_minute=config.rate_limit_tpm,
            daily_budget=config.daily_budget,
            cost_per_request=config.cost_per_request,
            cost_per_token=0.0000005  # Gemini token cost
        )
        self._rate_limiter = RateLimiter("google", rate_config)
        
        # Health monitor
        self._health_monitor = HealthMonitor("google", {
            "health_check_interval": config.health_check_interval
        })
        
        # Connection pool
        self._connector = None
        self._session = None
        
        # Cost tracking - Gemini pricing
        if "flash" in self.model_name:
            self.cost_per_input_token = 0.00000075
            self.cost_per_output_token = 0.000003
        else:  # Pro model
            self.cost_per_input_token = 0.00000125
            self.cost_per_output_token = 0.000005
        
        # Safety settings
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        self.logger.info(f"Google provider initialized with model: {self.model_name}")
    
    async def initialize(self) -> bool:
        """Initialize Google provider"""
        try:
            # Configure API
            genai.configure(api_key=self.config.api_key)
            
            # Create model
            self.model = GenerativeModel(
                self.model_name,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_output_tokens,
                    "response_mime_type": "text/plain"
                },
                safety_settings=self.safety_settings
            )
            
            # Create connection pool
            self._connector = aiohttp.TCPConnector(
                limit=self.config.connection_pool_size,
                limit_per_host=self.config.connection_pool_size,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            )
            
            # Test connection
            await self.health_check()
            
            # Start health monitoring
            if self.config.health_check_interval > 0:
                await self._health_monitor.start_monitoring()
            
            self.status = AIProviderStatus.HEALTHY
            self.logger.info("Google provider initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Google provider: {e}")
            self.status = AIProviderStatus.UNAVAILABLE
            return False
    
    async def health_check(self) -> AIProviderStatus:
        """Perform health check"""
        try:
            # Simple health check - generate content
            response = await asyncio.to_thread(
                self.model.generate_content,
                "test"
            )
            
            if response.text:
                self.status = AIProviderStatus.HEALTHY
                self.logger.debug("Google health check passed")
            else:
                self.status = AIProviderStatus.DEGRADED
                self.logger.warning("Google health check returned no text")
                
        except Exception as e:
            error_str = str(e).lower()
            if "authentication" in error_str or "api key" in error_str:
                self.status = AIProviderStatus.AUTHENTICATION_ERROR
                self.logger.error("Google authentication failed")
            elif "quota" in error_str or "rate limit" in error_str:
                self.status = AIProviderStatus.RATE_LIMITED
                self.logger.warning("Google rate limit exceeded")
            else:
                self.status = AIProviderStatus.UNAVAILABLE
                self.logger.error(f"Google health check failed: {e}")
        
        return self.status
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """Process AI request"""
        start_time = time.time()
        
        try:
            # Prepare content
            content_parts = self._prepare_content(request)
            
            # Estimate tokens for rate limiting
            estimated_tokens = self._estimate_tokens(request.prompt)
            
            # Check rate limits
            rate_result = await self._rate_limiter.check_rate_limit(estimated_tokens)
            if not rate_result.allowed:
                raise AIProviderError(
                    f"Rate limit exceeded: {rate_result.reason}",
                    error_code="RATE_LIMIT_EXCEEDED",
                    provider="google",
                    retryable=True
                )
            
            # Make API call
            response = await asyncio.to_thread(
                self.model.generate_content,
                content_parts
            )
            
            # Check for blocking
            if response.candidates[0].finish_reason.name == "SAFETY":
                raise AIProviderError(
                    "Content blocked by safety filters",
                    error_code="CONTENT_BLOCKED",
                    provider="google",
                    retryable=False
                )
            
            # Extract response
            response_text = response.text
            
            # Calculate cost (Gemini doesn't provide token usage, so estimate)
            estimated_input_tokens = estimated_tokens
            estimated_output_tokens = len(response_text) // 4
            cost = self._calculate_cost(estimated_input_tokens, estimated_output_tokens)
            
            # Record request
            response_time = time.time() - start_time
            self._rate_limiter.record_request(
                tokens_used=estimated_input_tokens + estimated_output_tokens,
                cost=cost,
                response_time=response_time,
                error=False
            )
            
            # Record performance for health monitoring
            self._health_monitor.record_performance(
                response_time=response_time,
                cost=cost,
                error=False
            )
            
            # Create response
            ai_response = AIResponse(
                request_id=request.request_id,
                response_text=response_text,
                model_used=self.model_name,
                provider="google",
                confidence=0.9,  # Google doesn't provide confidence scores
                cost=cost,
                response_time=response_time,
                metadata={
                    "usage": {
                        "estimated_input_tokens": estimated_input_tokens,
                        "estimated_output_tokens": estimated_output_tokens,
                        "estimated_total_tokens": estimated_input_tokens + estimated_output_tokens
                    },
                    "finish_reason": response.candidates[0].finish_reason.name,
                    "safety_ratings": [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name
                        }
                        for rating in response.candidates[0].safety_ratings
                    ]
                }
            )
            
            self.logger.debug(f"Google request completed: {request.request_id}")
            return ai_response
            
        except Exception as e:
            # Record error for health monitoring
            self._health_monitor.record_performance(
                response_time=time.time() - start_time,
                cost=0.0,
                error=True
            )
            
            error_str = str(e).lower()
            if "authentication" in error_str or "api key" in error_str:
                self.status = AIProviderStatus.AUTHENTICATION_ERROR
                raise AIProviderError(
                    "Authentication failed",
                    error_code="AUTHENTICATION_ERROR",
                    provider="google",
                    retryable=False,
                    details={"error": str(e)}
                )
            elif "quota" in error_str or "rate limit" in error_str:
                self.status = AIProviderStatus.RATE_LIMITED
                raise AIProviderError(
                    "Rate limit exceeded",
                    error_code="RATE_LIMIT_EXCEEDED",
                    provider="google",
                    retryable=True,
                    details={"error": str(e)}
                )
            elif "timeout" in error_str:
                raise AIProviderError(
                    "Request timeout",
                    error_code="TIMEOUT",
                    provider="google",
                    retryable=True,
                    details={"error": str(e)}
                )
            else:
                raise AIProviderError(
                    f"Google request failed: {str(e)}",
                    error_code="API_ERROR",
                    provider="google",
                    retryable=True,
                    details={"error": str(e)}
                )
    
    def _prepare_content(self, request: AIRequest) -> List[Any]:
        """Prepare content for Google API"""
        content_parts = []
        
        # Add text prompt
        content_parts.append(request.prompt)
        
        # Add image if provided
        if request.image_path:
            try:
                image = Image.open(request.image_path)
                content_parts.append(image)
            except Exception as e:
                self.logger.error(f"Failed to open image: {e}")
                raise AIProviderError(
                    "Failed to open image",
                    error_code="IMAGE_ERROR",
                    provider="google",
                    retryable=False
                )
        
        elif request.image_data:
            try:
                # Convert bytes to PIL Image
                from io import BytesIO
                image = Image.open(BytesIO(request.image_data))
                content_parts.append(image)
            except Exception as e:
                self.logger.error(f"Failed to process image data: {e}")
                raise AIProviderError(
                    "Failed to process image data",
                    error_code="IMAGE_ERROR",
                    provider="google",
                    retryable=False
                )
        
        return content_parts
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate request cost"""
        input_cost = input_tokens * self.cost_per_input_token
        output_cost = output_tokens * self.cost_per_output_token
        return input_cost + output_cost
    
    async def validate_credentials(self) -> bool:
        """Validate Google credentials"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                "test"
            )
            return bool(response.text)
        except Exception as e:
            self.logger.error(f"Credential validation failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Google model information"""
        return {
            "provider": "google",
            "model": self.model_name,
            "capabilities": [
                "text_analysis",
                "image_analysis",
                "json_output",
                "multi_modal",
                "reasoning",
                "code_generation"
            ],
            "max_tokens": self.max_output_tokens,
            "input_cost_per_token": self.cost_per_input_token,
            "output_cost_per_token": self.cost_per_output_token,
            "supported_formats": ["jpeg", "png", "gif", "webp"],
            "context_window": 1000000 if "1.5" in self.model_name else 32000
        }
    
    async def batch_process_requests(self, requests: List[AIRequest]) -> List[AIResponse]:
        """
        Process multiple requests efficiently.
        
        Args:
            requests: List of AI requests
            
        Returns:
            List of AI responses
        """
        if not requests:
            return []
        
        # Google doesn't have native batching, so we'll use concurrency
        # with rate limiting
        semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        async def process_with_semaphore(request: AIRequest) -> AIResponse:
            async with semaphore:
                return await self.process_request_with_retry(request)
        
        # Process requests concurrently
        tasks = [process_with_semaphore(request) for request in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                # Create error response
                error_response = AIResponse(
                    request_id=requests[i].request_id,
                    response_text="",
                    model_used=self.model_name,
                    provider="google",
                    confidence=0.0,
                    cost=0.0,
                    response_time=0.0,
                    error=str(response)
                )
                processed_responses.append(error_response)
            else:
                processed_responses.append(response)
        
        return processed_responses
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available Google models"""
        try:
            # Get models from API
            models = await asyncio.to_thread(genai.list_models)
            
            available_models = []
            for model in models:
                # Filter for vision-capable models
                if "vision" in model.name.lower() or "gemini" in model.name.lower():
                    available_models.append({
                        "id": model.name,
                        "name": model.display_name,
                        "capabilities": self._get_model_capabilities(model.name),
                        "supported_generation_methods": model.supported_generation_methods,
                        "input_token_limit": model.input_token_limit,
                        "output_token_limit": model.output_token_limit
                    })
            
            return available_models
            
        except Exception as e:
            self.logger.error(f"Failed to get available models: {e}")
            # Return known models as fallback
            return [
                {
                    "id": "gemini-1.5-flash",
                    "name": "Gemini 1.5 Flash",
                    "capabilities": ["text_analysis", "image_analysis", "multi_modal"],
                    "context_window": 1000000
                },
                {
                    "id": "gemini-1.5-pro",
                    "name": "Gemini 1.5 Pro",
                    "capabilities": ["text_analysis", "image_analysis", "multi_modal", "reasoning"],
                    "context_window": 1000000
                }
            ]
    
    def _get_model_capabilities(self, model_name: str) -> List[str]:
        """Get capabilities for a model"""
        capabilities = ["text_analysis"]
        
        if "vision" in model_name.lower() or "gemini" in model_name.lower():
            capabilities.extend(["image_analysis", "multi_modal"])
        
        if "pro" in model_name.lower():
            capabilities.extend(["reasoning", "code_generation"])
        
        capabilities.append("json_output")
        
        return capabilities
    
    async def shutdown(self):
        """Shutdown Google provider"""
        await super().shutdown()
        
        # Stop health monitoring
        if self._health_monitor:
            await self._health_monitor.stop_monitoring()
        
        # Close connection pool
        if self._session:
            await self._session.close()
        
        if self._connector:
            await self._connector.close()
        
        self.logger.info("Google provider shutdown complete")
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get rate limit status"""
        return self._rate_limiter.get_rate_limit_status()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status"""
        return self._health_monitor.get_health_summary()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        base_metrics = self.get_metrics()
        rate_metrics = self._rate_limiter.get_performance_metrics()
        
        return {
            "provider": "google",
            "model": self.model_name,
            "requests": {
                "total": base_metrics.total_requests,
                "successful": base_metrics.successful_requests,
                "failed": base_metrics.failed_requests,
                "success_rate": base_metrics.success_rate
            },
            "performance": {
                "average_response_time": base_metrics.average_response_time,
                "total_cost": base_metrics.total_cost,
                "cost_per_request": base_metrics.total_cost / max(1, base_metrics.total_requests)
            },
            "rate_limiting": rate_metrics,
            "health": self.get_health_status()
        }