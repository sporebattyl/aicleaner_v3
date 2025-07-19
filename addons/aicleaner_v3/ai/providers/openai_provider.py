"""
OpenAI Provider Implementation
Phase 2A: AI Model Provider Optimization

Provides OpenAI GPT-4V integration with enhanced features including
connection pooling, request batching, and advanced error handling.
"""

import asyncio
import base64
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp

from .base_provider import (
    BaseAIProvider, AIProviderConfiguration, AIRequest, AIResponse,
    AIProviderStatus, AIProviderError
)
from .rate_limiter import RateLimiter, RateLimitConfig
from .health_monitor import HealthMonitor
from .ml_model_selector import MLModelSelector

# Performance optimization - Phase 5A
from performance.ai_cache import get_ai_cache

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI GPT-4V provider with enhanced features.
    
    Features:
    - GPT-4V image analysis
    - Connection pooling
    - Request batching
    - Advanced error handling
    - Cost tracking
    - Performance monitoring
    """
    
    def __init__(self, config: AIProviderConfiguration):
        """
        Initialize OpenAI provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__(config)
        
        if not OPENAI_AVAILABLE:
            raise AIProviderError(
                "OpenAI package not available",
                error_code="PACKAGE_NOT_AVAILABLE",
                provider="openai",
                retryable=False
            )
        
        # OpenAI specific configuration
        self.client = None
        self.async_client = None
        self.model_name = config.model_name or "gpt-4-vision-preview"
        self.max_tokens = 4000
        self.temperature = 0.1
        
        # Available models for ML selection
        self.available_models = [
            "gpt-4o",
            "gpt-4o-mini", 
            "gpt-4-turbo",
            "gpt-4-vision-preview"
        ]
        self.default_model = "gpt-4o-mini"
        
        # Initialize ML model selector
        self.ml_model_selector = MLModelSelector(
            provider_name="openai",
            models=self.available_models,
            default_model=self.default_model
        )
        
        # Rate limiter
        rate_config = RateLimitConfig(
            requests_per_minute=config.rate_limit_rpm,
            tokens_per_minute=config.rate_limit_tpm,
            daily_budget=config.daily_budget,
            cost_per_request=config.cost_per_request,
            cost_per_token=0.00003  # GPT-4V token cost
        )
        self._rate_limiter = RateLimiter("openai", rate_config)
        
        # Health monitor
        self._health_monitor = HealthMonitor("openai", {
            "health_check_interval": config.health_check_interval
        })
        
        # Connection pool
        self._connector = None
        self._session = None
        
        # Cost tracking
        self.cost_per_input_token = 0.00003
        self.cost_per_output_token = 0.00006
        
        self.logger.info(f"OpenAI provider initialized with model: {self.model_name}")
    
    async def initialize(self) -> bool:
        """Initialize OpenAI provider"""
        try:
            # Initialize OpenAI client
            self.client = openai.OpenAI(
                api_key=self.config.api_key,
                timeout=self.config.timeout_seconds
            )
            
            self.async_client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                timeout=self.config.timeout_seconds
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
            self.logger.info("OpenAI provider initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI provider: {e}")
            self.status = AIProviderStatus.UNAVAILABLE
            return False
    
    async def health_check(self) -> AIProviderStatus:
        """Perform health check"""
        try:
            # Simple health check - list models
            response = await self.async_client.models.list()
            
            if response.data:
                self.status = AIProviderStatus.HEALTHY
                self.logger.debug("OpenAI health check passed")
            else:
                self.status = AIProviderStatus.DEGRADED
                self.logger.warning("OpenAI health check returned no models")
                
        except openai.AuthenticationError:
            self.status = AIProviderStatus.AUTHENTICATION_ERROR
            self.logger.error("OpenAI authentication failed")
            
        except openai.RateLimitError:
            self.status = AIProviderStatus.RATE_LIMITED
            self.logger.warning("OpenAI rate limit exceeded")
            
        except Exception as e:
            self.status = AIProviderStatus.UNAVAILABLE
            self.logger.error(f"OpenAI health check failed: {e}")
        
        return self.status
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """Process AI request with ML model selection and caching"""
        start_time = time.time()
        
        # Get ML-recommended model
        recommended_model = self.get_recommended_model(request)
        model_to_use = recommended_model if recommended_model else self.model_name
        
        # Check cache first - Phase 5A
        cache = get_ai_cache()
        cached_response = await cache.get("openai", model_to_use, request.prompt, {
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "has_image": bool(request.image_path or request.image_data)
        })
        
        if cached_response:
            self.logger.debug(f"Cache hit for OpenAI request: {request.request_id}")
            return AIResponse(
                request_id=request.request_id,
                response_text=cached_response["response_text"],
                model_used=cached_response["model_used"],
                provider="openai",
                confidence=cached_response.get("confidence", 0.9),
                cost=0.0,  # No cost for cached response
                response_time=time.time() - start_time,
                cached=True,
                metadata=cached_response.get("metadata", {})
            )
        
        try:
            
            # Prepare messages
            messages = self._prepare_messages(request)
            
            # Estimate tokens for rate limiting
            estimated_tokens = self._estimate_tokens(request.prompt)
            
            # Check rate limits
            rate_result = await self._rate_limiter.check_rate_limit(estimated_tokens)
            if not rate_result.allowed:
                raise AIProviderError(
                    f"Rate limit exceeded: {rate_result.reason}",
                    error_code="RATE_LIMIT_EXCEEDED",
                    provider="openai",
                    retryable=True
                )
            
            # Make API call with selected model
            response = await self.async_client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False
            )
            
            # Extract response
            response_text = response.choices[0].message.content
            
            # Calculate actual cost
            usage = response.usage
            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)
            
            # Record request
            response_time = time.time() - start_time
            self._rate_limiter.record_request(
                tokens_used=usage.total_tokens,
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
            
            # Update ML model performance
            self.update_model_performance(model_to_use, request, True, response_time, cost)
            
            # Create response
            ai_response = AIResponse(
                request_id=request.request_id,
                response_text=response_text,
                model_used=model_to_use,
                provider="openai",
                confidence=0.9,  # OpenAI doesn't provide confidence scores
                cost=cost,
                response_time=response_time,
                metadata={
                    "usage": {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens
                    },
                    "finish_reason": response.choices[0].finish_reason,
                    "ml_recommended_model": recommended_model
                }
            )
            
            # Cache successful response - Phase 5A
            cache_data = {
                "response_text": response_text,
                "model_used": model_to_use,
                "confidence": 0.9,
                "metadata": ai_response.metadata
            }
            await cache.set("openai", model_to_use, request.prompt, cache_data, {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "has_image": bool(request.image_path or request.image_data)
            })
            
            self.logger.debug(f"OpenAI request completed: {request.request_id} with model: {model_to_use}")
            return ai_response
            
        except openai.AuthenticationError as e:
            self.status = AIProviderStatus.AUTHENTICATION_ERROR
            # Update ML model performance for failed request
            response_time = time.time() - start_time
            self.update_model_performance(model_to_use, request, False, response_time, 0.0)
            
            raise AIProviderError(
                "Authentication failed",
                error_code="AUTHENTICATION_ERROR",
                provider="openai",
                retryable=False,
                details={"error": str(e)}
            )
            
        except openai.RateLimitError as e:
            self.status = AIProviderStatus.RATE_LIMITED
            # Update ML model performance for failed request
            response_time = time.time() - start_time
            self.update_model_performance(model_to_use, request, False, response_time, 0.0)
            
            raise AIProviderError(
                "Rate limit exceeded",
                error_code="RATE_LIMIT_EXCEEDED",
                provider="openai",
                retryable=True,
                details={"error": str(e)}
            )
            
        except openai.APITimeoutError as e:
            # Update ML model performance for failed request
            response_time = time.time() - start_time
            self.update_model_performance(model_to_use, request, False, response_time, 0.0)
            
            raise AIProviderError(
                "Request timeout",
                error_code="TIMEOUT",
                provider="openai",
                retryable=True,
                details={"error": str(e)}
            )
            
        except Exception as e:
            # Record error for health monitoring
            response_time = time.time() - start_time
            self._health_monitor.record_performance(
                response_time=response_time,
                cost=0.0,
                error=True
            )
            
            # Update ML model performance for failed request
            self.update_model_performance(model_to_use, request, False, response_time, 0.0)
            
            raise AIProviderError(
                f"OpenAI request failed: {str(e)}",
                error_code="API_ERROR",
                provider="openai",
                retryable=True,
                details={"error": str(e)}
            )
    
    def _prepare_messages(self, request: AIRequest) -> List[Dict[str, Any]]:
        """Prepare messages for OpenAI API"""
        messages = []
        
        # System message
        system_message = {
            "role": "system",
            "content": "You are an AI assistant specialized in image analysis and cleaning task generation. Provide detailed, accurate responses in JSON format when requested."
        }
        messages.append(system_message)
        
        # User message with image
        user_content = []
        
        # Add text prompt
        user_content.append({
            "type": "text",
            "text": request.prompt
        })
        
        # Add image if provided
        if request.image_path:
            try:
                image_data = self._encode_image(request.image_path)
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}"
                    }
                })
            except Exception as e:
                self.logger.error(f"Failed to encode image: {e}")
                raise AIProviderError(
                    "Failed to encode image",
                    error_code="IMAGE_ENCODING_ERROR",
                    provider="openai",
                    retryable=False
                )
        
        elif request.image_data:
            # Use provided image data
            image_data = base64.b64encode(request.image_data).decode('utf-8')
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                }
            })
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        return messages
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to encode image {image_path}: {e}")
            raise
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate request cost"""
        input_cost = prompt_tokens * self.cost_per_input_token
        output_cost = completion_tokens * self.cost_per_output_token
        return input_cost + output_cost
    
    async def validate_credentials(self) -> bool:
        """Validate OpenAI credentials"""
        try:
            response = await self.async_client.models.list()
            return bool(response.data)
        except Exception as e:
            self.logger.error(f"Credential validation failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information"""
        return {
            "provider": "openai",
            "model": self.model_name,
            "capabilities": [
                "text_analysis",
                "image_analysis",
                "json_output",
                "multi_modal"
            ],
            "max_tokens": self.max_tokens,
            "input_cost_per_token": self.cost_per_input_token,
            "output_cost_per_token": self.cost_per_output_token,
            "supported_formats": ["jpeg", "png", "gif", "webp"]
        }
    
    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        Get OpenAI provider capabilities for context-aware fallback selection.
        
        Returns:
            Dictionary with capability flags
        """
        return {
            "vision": True,                    # GPT-4V supports image analysis
            "code_generation": True,           # Excellent at code generation
            "instruction_following": True,     # Strong instruction following
            "multimodal": True,               # Supports text and images
            "local_model": False              # Cloud-based service
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
        
        # OpenAI doesn't have native batching, so we'll use concurrency
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
                    provider="openai",
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
        """Get list of available OpenAI models"""
        try:
            response = await self.async_client.models.list()
            
            # Filter for vision-capable models
            vision_models = []
            for model in response.data:
                if "vision" in model.id or "gpt-4" in model.id:
                    vision_models.append({
                        "id": model.id,
                        "created": model.created,
                        "owned_by": model.owned_by,
                        "capabilities": self._get_model_capabilities(model.id)
                    })
            
            return vision_models
            
        except Exception as e:
            self.logger.error(f"Failed to get available models: {e}")
            return []
    
    def _get_model_capabilities(self, model_id: str) -> List[str]:
        """Get capabilities for a model"""
        capabilities = ["text_analysis"]
        
        if "vision" in model_id or "gpt-4" in model_id:
            capabilities.extend(["image_analysis", "multi_modal"])
        
        if "gpt-4" in model_id:
            capabilities.append("json_output")
        
        return capabilities
    
    async def shutdown(self):
        """Shutdown OpenAI provider"""
        await super().shutdown()
        
        # Stop health monitoring
        if self._health_monitor:
            await self._health_monitor.stop_monitoring()
        
        # Close connection pool
        if self._session:
            await self._session.close()
        
        if self._connector:
            await self._connector.close()
        
        self.logger.info("OpenAI provider shutdown complete")
    
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
            "provider": "openai",
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