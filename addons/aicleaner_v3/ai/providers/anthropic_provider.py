"""
Anthropic Claude Provider Implementation
Phase 2A: AI Model Provider Optimization

Provides Anthropic Claude integration with enhanced features including
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

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicProvider(BaseAIProvider):
    """
    Anthropic Claude provider with enhanced features.
    
    Features:
    - Claude 3.5 Sonnet image analysis
    - Connection pooling
    - Request batching
    - Advanced error handling
    - Cost tracking
    - Performance monitoring
    """
    
    def __init__(self, config: AIProviderConfiguration):
        """
        Initialize Anthropic provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__(config)
        
        if not ANTHROPIC_AVAILABLE:
            raise AIProviderError(
                "Anthropic package not available",
                error_code="PACKAGE_NOT_AVAILABLE",
                provider="anthropic",
                retryable=False
            )
        
        # Anthropic specific configuration
        self.client = None
        self.model_name = config.model_name or "claude-3-5-sonnet-20241022"
        self.max_tokens = 4000
        self.temperature = 0.1
        
        # Rate limiter
        rate_config = RateLimitConfig(
            requests_per_minute=config.rate_limit_rpm,
            tokens_per_minute=config.rate_limit_tpm,
            daily_budget=config.daily_budget,
            cost_per_request=config.cost_per_request,
            cost_per_token=0.000015  # Claude token cost
        )
        self._rate_limiter = RateLimiter("anthropic", rate_config)
        
        # Health monitor
        self._health_monitor = HealthMonitor("anthropic", {
            "health_check_interval": config.health_check_interval
        })
        
        # Connection pool
        self._connector = None
        self._session = None
        
        # Cost tracking
        self.cost_per_input_token = 0.000015
        self.cost_per_output_token = 0.000075
        
        self.logger.info(f"Anthropic provider initialized with model: {self.model_name}")
    
    async def initialize(self) -> bool:
        """Initialize Anthropic provider"""
        try:
            # Initialize Anthropic client
            self.client = anthropic.AsyncAnthropic(
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
            self.logger.info("Anthropic provider initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Anthropic provider: {e}")
            self.status = AIProviderStatus.UNAVAILABLE
            return False
    
    async def health_check(self) -> AIProviderStatus:
        """Perform health check"""
        try:
            # Simple health check - make a minimal request
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            
            if response.content:
                self.status = AIProviderStatus.HEALTHY
                self.logger.debug("Anthropic health check passed")
            else:
                self.status = AIProviderStatus.DEGRADED
                self.logger.warning("Anthropic health check returned no content")
                
        except anthropic.AuthenticationError:
            self.status = AIProviderStatus.AUTHENTICATION_ERROR
            self.logger.error("Anthropic authentication failed")
            
        except anthropic.RateLimitError:
            self.status = AIProviderStatus.RATE_LIMITED
            self.logger.warning("Anthropic rate limit exceeded")
            
        except Exception as e:
            self.status = AIProviderStatus.UNAVAILABLE
            self.logger.error(f"Anthropic health check failed: {e}")
        
        return self.status
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """Process AI request"""
        start_time = time.time()
        
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
                    provider="anthropic",
                    retryable=True
                )
            
            # Make API call
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=messages
            )
            
            # Extract response
            response_text = response.content[0].text
            
            # Calculate actual cost
            usage = response.usage
            cost = self._calculate_cost(usage.input_tokens, usage.output_tokens)
            
            # Record request
            response_time = time.time() - start_time
            self._rate_limiter.record_request(
                tokens_used=usage.input_tokens + usage.output_tokens,
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
                provider="anthropic",
                confidence=0.9,  # Anthropic doesn't provide confidence scores
                cost=cost,
                response_time=response_time,
                metadata={
                    "usage": {
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "total_tokens": usage.input_tokens + usage.output_tokens
                    },
                    "stop_reason": response.stop_reason,
                    "stop_sequence": response.stop_sequence
                }
            )
            
            self.logger.debug(f"Anthropic request completed: {request.request_id}")
            return ai_response
            
        except anthropic.AuthenticationError as e:
            self.status = AIProviderStatus.AUTHENTICATION_ERROR
            raise AIProviderError(
                "Authentication failed",
                error_code="AUTHENTICATION_ERROR",
                provider="anthropic",
                retryable=False,
                details={"error": str(e)}
            )
            
        except anthropic.RateLimitError as e:
            self.status = AIProviderStatus.RATE_LIMITED
            raise AIProviderError(
                "Rate limit exceeded",
                error_code="RATE_LIMIT_EXCEEDED",
                provider="anthropic",
                retryable=True,
                details={"error": str(e)}
            )
            
        except anthropic.APITimeoutError as e:
            raise AIProviderError(
                "Request timeout",
                error_code="TIMEOUT",
                provider="anthropic",
                retryable=True,
                details={"error": str(e)}
            )
            
        except Exception as e:
            # Record error for health monitoring
            self._health_monitor.record_performance(
                response_time=time.time() - start_time,
                cost=0.0,
                error=True
            )
            
            raise AIProviderError(
                f"Anthropic request failed: {str(e)}",
                error_code="API_ERROR",
                provider="anthropic",
                retryable=True,
                details={"error": str(e)}
            )
    
    def _prepare_messages(self, request: AIRequest) -> List[Dict[str, Any]]:
        """Prepare messages for Anthropic API"""
        messages = []
        
        # User message with content
        content = []
        
        # Add image if provided
        if request.image_path:
            try:
                image_data = self._encode_image(request.image_path)
                image_format = self._get_image_format(request.image_path)
                
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f"image/{image_format}",
                        "data": image_data
                    }
                })
            except Exception as e:
                self.logger.error(f"Failed to encode image: {e}")
                raise AIProviderError(
                    "Failed to encode image",
                    error_code="IMAGE_ENCODING_ERROR",
                    provider="anthropic",
                    retryable=False
                )
        
        elif request.image_data:
            # Use provided image data
            image_data = base64.b64encode(request.image_data).decode('utf-8')
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data
                }
            })
        
        # Add text prompt
        content.append({
            "type": "text",
            "text": request.prompt
        })
        
        messages.append({
            "role": "user",
            "content": content
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
    
    def _get_image_format(self, image_path: str) -> str:
        """Get image format from path"""
        if image_path.lower().endswith('.png'):
            return 'png'
        elif image_path.lower().endswith('.gif'):
            return 'gif'
        elif image_path.lower().endswith('.webp'):
            return 'webp'
        else:
            return 'jpeg'
    
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
        """Validate Anthropic credentials"""
        try:
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            return bool(response.content)
        except Exception as e:
            self.logger.error(f"Credential validation failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Anthropic model information"""
        return {
            "provider": "anthropic",
            "model": self.model_name,
            "capabilities": [
                "text_analysis",
                "image_analysis",
                "json_output",
                "multi_modal",
                "reasoning"
            ],
            "max_tokens": self.max_tokens,
            "input_cost_per_token": self.cost_per_input_token,
            "output_cost_per_token": self.cost_per_output_token,
            "supported_formats": ["jpeg", "png", "gif", "webp"],
            "context_window": 200000
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
        
        # Anthropic doesn't have native batching, so we'll use concurrency
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
                    provider="anthropic",
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
        """Get list of available Anthropic models"""
        # Anthropic doesn't have a models endpoint, so return known models
        return [
            {
                "id": "claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet",
                "capabilities": ["text_analysis", "image_analysis", "reasoning", "json_output"],
                "max_tokens": 4096,
                "context_window": 200000
            },
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "capabilities": ["text_analysis", "image_analysis", "reasoning", "json_output"],
                "max_tokens": 4096,
                "context_window": 200000
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "capabilities": ["text_analysis", "image_analysis", "reasoning", "json_output"],
                "max_tokens": 4096,
                "context_window": 200000
            }
        ]
    
    async def shutdown(self):
        """Shutdown Anthropic provider"""
        await super().shutdown()
        
        # Stop health monitoring
        if self._health_monitor:
            await self._health_monitor.stop_monitoring()
        
        # Close connection pool
        if self._session:
            await self._session.close()
        
        if self._connector:
            await self._connector.close()
        
        self.logger.info("Anthropic provider shutdown complete")
    
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
            "provider": "anthropic",
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