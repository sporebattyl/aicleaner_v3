"""
Ollama Provider Implementation
Phase 2A: AI Model Provider Optimization

Provides Ollama local model integration with enhanced features including
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
from PIL import Image

try:
    import psutil
except ImportError:
    psutil = None

from .base_provider import (
    BaseAIProvider, AIProviderConfiguration, AIRequest, AIResponse,
    AIProviderStatus, AIProviderError
)
from .rate_limiter import RateLimiter, RateLimitConfig
from .health_monitor import HealthMonitor

# Performance optimization - Phase 5A
from performance.ai_cache import get_ai_cache


class OllamaProvider(BaseAIProvider):
    """
    Ollama local model provider with enhanced features.
    
    Features:
    - Dynamic model loading and unloading
    - Resource-aware health checks
    - API-based capability detection
    - Connection pooling
    - Advanced error handling
    - Performance monitoring
    """
    
    def __init__(self, config: AIProviderConfiguration):
        """
        Initialize Ollama provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__(config)
        
        # Ollama specific configuration
        self.base_url = config.base_url or "http://localhost:11434"
        self.default_model_name = config.model_name or "llava:13b"
        self.temperature = 0.1
        self.max_tokens = 4000
        
        # Dynamic model management
        self.active_model: Optional[str] = None
        self.active_model_timer: Optional[asyncio.TimerHandle] = None
        self.model_unload_timeout = 120  # seconds
        
        # Resource-aware health check thresholds
        self.resource_thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 90.0,
        }
        
        # Rate limiter (more lenient for local models)
        rate_config = RateLimitConfig(
            requests_per_minute=config.rate_limit_rpm or 120,
            tokens_per_minute=config.rate_limit_tpm or 50000,
            daily_budget=config.daily_budget or 0.0,  # No cost for local models
            cost_per_request=0.0,  # No cost for local models
            cost_per_token=0.0
        )
        self._rate_limiter = RateLimiter("ollama", rate_config)
        
        # Health monitor
        self._health_monitor = HealthMonitor("ollama", {
            "health_check_interval": config.health_check_interval
        })
        
        # Connection pool
        self._connector = None
        self._session = None
        
        # Model management
        self.available_models = []
        self.model_loaded = False
        
        self.logger.info(f"Ollama provider initialized with model: {self.model_name}")
    
    async def initialize(self) -> bool:
        """Initialize Ollama provider"""
        try:
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
            
            # Test connection and load models
            await self.health_check()
            await self._load_available_models()
            
            # Ensure model is loaded
            if not await self._ensure_model_loaded():
                self.logger.warning(f"Model {self.model_name} not available, using default")
            
            # Start health monitoring
            if self.config.health_check_interval > 0:
                await self._health_monitor.start_monitoring()
            
            self.status = AIProviderStatus.HEALTHY
            self.logger.info("Ollama provider initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama provider: {e}")
            self.status = AIProviderStatus.UNAVAILABLE
            return False
    
    async def health_check(self) -> AIProviderStatus:
        """Perform health check"""
        try:
            # Check Ollama service health
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    self.status = AIProviderStatus.HEALTHY
                    self.logger.debug("Ollama health check passed")
                else:
                    self.status = AIProviderStatus.UNAVAILABLE
                    self.logger.warning(f"Ollama health check failed: {response.status}")
                    
        except aiohttp.ClientError as e:
            self.status = AIProviderStatus.UNAVAILABLE
            self.logger.error(f"Ollama connection failed: {e}")
            
        except Exception as e:
            self.status = AIProviderStatus.UNAVAILABLE
            self.logger.error(f"Ollama health check failed: {e}")
        
        return self.status
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """Process AI request with caching"""
        start_time = time.time()
        
        # Check cache first - Phase 5A
        cache = get_ai_cache()
        cached_response = await cache.get("ollama", self.model_name, request.prompt, {
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "has_image": bool(request.image_path or request.image_data)
        })
        
        if cached_response:
            self.logger.debug(f"Cache hit for Ollama request: {request.request_id}")
            return AIResponse(
                request_id=request.request_id,
                response_text=cached_response["response_text"],
                model_used=cached_response["model_used"],
                provider="ollama",
                confidence=cached_response.get("confidence", 0.9),
                cost=0.0,  # No cost for cached response (local model)
                response_time=time.time() - start_time,
                cached=True,
                metadata=cached_response.get("metadata", {})
            )
        
        try:
            # Prepare request payload
            payload = self._prepare_payload(request)
            
            # Estimate tokens for rate limiting
            estimated_tokens = self._estimate_tokens(request.prompt)
            
            # Check rate limits
            rate_result = await self._rate_limiter.check_rate_limit(estimated_tokens)
            if not rate_result.allowed:
                raise AIProviderError(
                    f"Rate limit exceeded: {rate_result.reason}",
                    error_code="RATE_LIMIT_EXCEEDED",
                    provider="ollama",
                    retryable=True
                )
            
            # Make API call
            async with self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    raise AIProviderError(
                        f"Ollama API error: {response.status}",
                        error_code="API_ERROR",
                        provider="ollama",
                        retryable=True
                    )
                
                # Process streaming response
                response_text = ""
                async for line in response.content:
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            response_text += data["response"]
                        if data.get("done", False):
                            break
            
            # Calculate cost (always 0 for local models)
            cost = 0.0
            
            # Record request
            response_time = time.time() - start_time
            self._rate_limiter.record_request(
                tokens_used=estimated_tokens,
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
                provider="ollama",
                confidence=0.8,  # Local models generally have lower confidence
                cost=cost,
                response_time=response_time,
                metadata={
                    "usage": {
                        "estimated_tokens": estimated_tokens
                    },
                    "local_model": True,
                    "base_url": self.base_url
                }
            )
            
            # Cache successful response - Phase 5A
            cache_data = {
                "response_text": response_text,
                "model_used": self.model_name,
                "confidence": 0.9,
                "metadata": ai_response.metadata
            }
            await cache.set("ollama", self.model_name, request.prompt, cache_data, {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "has_image": bool(request.image_path or request.image_data)
            })
            
            self.logger.debug(f"Ollama request completed: {request.request_id}")
            return ai_response
            
        except aiohttp.ClientError as e:
            # Record error for health monitoring
            self._health_monitor.record_performance(
                response_time=time.time() - start_time,
                cost=0.0,
                error=True
            )
            
            raise AIProviderError(
                f"Ollama connection error: {str(e)}",
                error_code="CONNECTION_ERROR",
                provider="ollama",
                retryable=True,
                details={"error": str(e)}
            )
            
        except asyncio.TimeoutError:
            raise AIProviderError(
                "Request timeout",
                error_code="TIMEOUT",
                provider="ollama",
                retryable=True
            )
            
        except Exception as e:
            # Record error for health monitoring
            self._health_monitor.record_performance(
                response_time=time.time() - start_time,
                cost=0.0,
                error=True
            )
            
            raise AIProviderError(
                f"Ollama request failed: {str(e)}",
                error_code="API_ERROR",
                provider="ollama",
                retryable=True,
                details={"error": str(e)}
            )
    
    def _prepare_payload(self, request: AIRequest) -> Dict[str, Any]:
        """Prepare request payload for Ollama API"""
        payload = {
            "model": self.model_name,
            "prompt": request.prompt,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        
        # Add image if provided
        if request.image_path:
            try:
                image_data = self._encode_image(request.image_path)
                payload["images"] = [image_data]
            except Exception as e:
                self.logger.error(f"Failed to encode image: {e}")
                raise AIProviderError(
                    "Failed to encode image",
                    error_code="IMAGE_ENCODING_ERROR",
                    provider="ollama",
                    retryable=False
                )
        
        elif request.image_data:
            # Use provided image data
            image_data = base64.b64encode(request.image_data).decode('utf-8')
            payload["images"] = [image_data]
        
        return payload
    
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
    
    async def _load_available_models(self):
        """Load available models from Ollama"""
        try:
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    self.available_models = data.get("models", [])
                    self.logger.info(f"Loaded {len(self.available_models)} available models")
                else:
                    self.logger.warning(f"Failed to load models: {response.status}")
        except Exception as e:
            self.logger.error(f"Error loading available models: {e}")
    
    async def _ensure_model_loaded(self) -> bool:
        """Ensure the specified model is loaded"""
        # Check if model is in available models
        model_names = [model["name"] for model in self.available_models]
        
        if self.model_name not in model_names:
            self.logger.warning(f"Model {self.model_name} not found in available models")
            # Try to use the first available model
            if self.available_models:
                self.model_name = self.available_models[0]["name"]
                self.logger.info(f"Switched to available model: {self.model_name}")
            else:
                return False
        
        # Test model with a simple request
        try:
            payload = {
                "model": self.model_name,
                "prompt": "test",
                "stream": False
            }
            
            async with self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    self.model_loaded = True
                    return True
                else:
                    self.logger.error(f"Model test failed: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error testing model: {e}")
            return False
    
    async def validate_credentials(self) -> bool:
        """Validate Ollama connection (no credentials needed)"""
        try:
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200
        except Exception as e:
            self.logger.error(f"Connection validation failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Ollama model information"""
        model_info = {
            "provider": "ollama",
            "model": self.model_name,
            "capabilities": ["text_analysis"],
            "max_tokens": self.max_tokens,
            "input_cost_per_token": 0.0,
            "output_cost_per_token": 0.0,
            "base_url": self.base_url,
            "local_model": True
        }
        
        # Add vision capabilities if it's a vision model
        if "llava" in self.model_name.lower() or "vision" in self.model_name.lower():
            model_info["capabilities"].extend(["image_analysis", "multi_modal"])
            model_info["supported_formats"] = ["jpeg", "png", "gif", "webp"]
        
        return model_info
    
    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        Get Ollama provider capabilities for context-aware fallback selection.
        
        Returns:
            Dictionary with capability flags
        """
        # Check if it's a vision model
        has_vision = "llava" in self.model_name.lower() or "vision" in self.model_name.lower()
        
        # Check if it's a code-focused model
        has_code_generation = any(term in self.model_name.lower() for term in 
                                ["code", "coder", "deepseek", "granite", "starcoder"])
        
        return {
            "vision": has_vision,              # Vision support depends on model
            "code_generation": has_code_generation or "llama" in self.model_name.lower(),  # Many models can code
            "instruction_following": True,     # Most local models follow instructions well
            "multimodal": has_vision,         # Multimodal if vision enabled
            "local_model": True              # Always local
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
        
        # Local models can handle more concurrency
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
                    provider="ollama",
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
        """Get list of available Ollama models"""
        try:
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    
                    # Format models for consistency
                    formatted_models = []
                    for model in models:
                        formatted_models.append({
                            "id": model["name"],
                            "name": model["name"],
                            "size": model.get("size", 0),
                            "modified": model.get("modified_at", ""),
                            "capabilities": self._get_model_capabilities(model["name"]),
                            "local_model": True
                        })
                    
                    return formatted_models
                else:
                    self.logger.error(f"Failed to get models: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error getting available models: {e}")
            return []
    
    def _get_model_capabilities(self, model_name: str) -> List[str]:
        """Get capabilities for a model"""
        capabilities = ["text_analysis"]
        
        if "llava" in model_name.lower() or "vision" in model_name.lower():
            capabilities.extend(["image_analysis", "multi_modal"])
        
        if "instruct" in model_name.lower():
            capabilities.append("instruction_following")
        
        if "code" in model_name.lower():
            capabilities.append("code_generation")
        
        return capabilities
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry"""
        try:
            payload = {"name": model_name}
            
            async with self._session.post(
                f"{self.base_url}/api/pull",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    # Stream the pull progress
                    async for line in response.content:
                        if line:
                            data = json.loads(line)
                            if "status" in data:
                                self.logger.info(f"Pull progress: {data['status']}")
                            if data.get("status") == "success":
                                self.logger.info(f"Successfully pulled model: {model_name}")
                                await self._load_available_models()
                                return True
                    return False
                else:
                    self.logger.error(f"Failed to pull model: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    async def delete_model(self, model_name: str) -> bool:
        """Delete a model from Ollama"""
        try:
            payload = {"name": model_name}
            
            async with self._session.delete(
                f"{self.base_url}/api/delete",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    self.logger.info(f"Successfully deleted model: {model_name}")
                    await self._load_available_models()
                    return True
                else:
                    self.logger.error(f"Failed to delete model: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error deleting model {model_name}: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown Ollama provider"""
        await super().shutdown()
        
        # Stop health monitoring
        if self._health_monitor:
            await self._health_monitor.stop_monitoring()
        
        # Close connection pool
        if self._session:
            await self._session.close()
        
        if self._connector:
            await self._connector.close()
        
        self.logger.info("Ollama provider shutdown complete")
    
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
            "provider": "ollama",
            "model": self.model_name,
            "base_url": self.base_url,
            "model_loaded": self.model_loaded,
            "available_models": len(self.available_models),
            "requests": {
                "total": base_metrics.total_requests,
                "successful": base_metrics.successful_requests,
                "failed": base_metrics.failed_requests,
                "success_rate": base_metrics.success_rate
            },
            "performance": {
                "average_response_time": base_metrics.average_response_time,
                "total_cost": base_metrics.total_cost,
                "cost_per_request": 0.0  # Always 0 for local models
            },
            "rate_limiting": rate_metrics,
            "health": self.get_health_status()
        }