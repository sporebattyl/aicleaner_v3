"""
Base AI Provider Interface
Phase 2A: AI Model Provider Optimization

Provides the abstract base class for all AI providers with standardized interface,
error handling, and monitoring capabilities.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image
from .ml_model_selector import MLModelSelector


class AIProviderStatus(Enum):
    """AI Provider status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTHENTICATION_ERROR = "authentication_error"
    UNKNOWN = "unknown"


class AIProviderError(Exception):
    """Base exception for AI provider errors"""
    
    def __init__(self, message: str, error_code: str = None, provider: str = None, 
                 retryable: bool = True, details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.provider = provider
        self.retryable = retryable
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


@dataclass
class AIProviderMetrics:
    """Metrics tracking for AI provider performance"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    total_cost: float = 0.0
    average_response_time: float = 0.0
    success_rate: float = 0.0
    last_request_time: Optional[str] = None
    last_error: Optional[str] = None
    quota_remaining: Optional[int] = None
    rate_limit_reset: Optional[str] = None


@dataclass
class AIProviderConfiguration:
    """Configuration for AI provider"""
    name: str
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 10000
    cost_per_request: float = 0.01
    daily_budget: float = 10.0
    model_name: str = ""
    api_key: str = ""
    base_url: Optional[str] = None
    priority: int = 1
    health_check_interval: int = 300
    
    # Advanced configuration
    connection_pool_size: int = 10
    request_timeout: int = 30
    retry_backoff_factor: float = 2.0
    max_concurrent_requests: int = 5


@dataclass
class AIRequest:
    """Standardized AI request structure"""
    request_id: str
    prompt: str
    image_path: Optional[str] = None
    image_data: Optional[bytes] = None
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    context: Optional[Dict[str, Any]] = None
    priority: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AIResponse:
    """Standardized AI response structure"""
    request_id: str
    response_text: str
    model_used: str
    provider: str
    confidence: float
    cost: float
    response_time: float
    cached: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers with standardized interface.
    
    Features:
    - Request/response standardization
    - Error handling and recovery
    - Performance metrics tracking
    - Rate limiting and quota management
    - Health monitoring
    - Structured logging
    """
    
    def __init__(self, config: AIProviderConfiguration):
        """
        Initialize the AI provider.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"ai_provider.{config.name}")
        self.metrics = AIProviderMetrics()
        self.status = AIProviderStatus.UNKNOWN
        self.last_health_check = datetime.now()
        
        # Initialize connection pool and rate limiter
        self._connection_pool = None
        self._rate_limiter = None
        self._health_monitor = None
        
        # Request tracking
        self._active_requests: Dict[str, float] = {}
        self._request_queue: List[AIRequest] = []
        
        # ML model selector (initialized by subclasses if they support multiple models)
        self.ml_model_selector: Optional[MLModelSelector] = None
        
        self.logger.info(f"Initialized AI provider: {config.name}")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider and establish connections.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> AIProviderStatus:
        """
        Perform health check and return current status.
        
        Returns:
            Current provider status
        """
        pass
    
    @abstractmethod
    async def process_request(self, request: AIRequest) -> AIResponse:
        """
        Process an AI request and return response.
        
        Args:
            request: Standardized AI request
            
        Returns:
            Standardized AI response
        """
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Validate provider credentials.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about available models.
        
        Returns:
            Dictionary with model information
        """
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> Dict[str, bool]:
        """
        Get provider capabilities for context-aware fallback selection.
        
        Returns:
            Dictionary with capability flags:
            - vision: Can process images
            - code_generation: Can generate code
            - instruction_following: Can follow instructions
            - multimodal: Supports multiple input types
            - local_model: Is a local model
        """
        pass
    
    async def analyze_image(self, image_path: str, prompt: str, 
                          context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """
        Analyze an image with the given prompt.
        
        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            context: Optional context information
            
        Returns:
            Analysis response
        """
        request = AIRequest(
            request_id=f"{self.config.name}_{int(time.time())}_{hash(prompt) % 10000}",
            prompt=prompt,
            image_path=image_path,
            context=context
        )
        
        return await self.process_request_with_retry(request)
    
    async def process_request_with_retry(self, request: AIRequest) -> AIResponse:
        """
        Process request with retry logic and error handling.
        
        Args:
            request: AI request to process
            
        Returns:
            AI response or error response
        """
        start_time = time.time()
        last_error = None
        
        # Update metrics
        self.metrics.total_requests += 1
        self._active_requests[request.request_id] = start_time
        
        try:
            # Log request start
            self.logger.info(
                json.dumps({
                    "event": "request_start",
                    "request_id": request.request_id,
                    "provider": self.config.name,
                    "model": request.model_name or self.config.model_name,
                    "has_image": bool(request.image_path or request.image_data),
                    "prompt_length": len(request.prompt),
                    "priority": request.priority
                })
            )
            
            for attempt in range(self.config.max_retries + 1):
                try:
                    # Check rate limits
                    if self._rate_limiter and not await self._rate_limiter.check_rate_limit():
                        self.status = AIProviderStatus.RATE_LIMITED
                        raise AIProviderError(
                            "Rate limit exceeded",
                            error_code="RATE_LIMIT_EXCEEDED",
                            provider=self.config.name,
                            retryable=True
                        )
                    
                    # Process the request
                    response = await asyncio.wait_for(
                        self.process_request(request),
                        timeout=self.config.timeout_seconds
                    )
                    
                    # Update metrics on success
                    response_time = time.time() - start_time
                    self.metrics.successful_requests += 1
                    self.metrics.total_response_time += response_time
                    self.metrics.average_response_time = (
                        self.metrics.total_response_time / self.metrics.successful_requests
                    )
                    self.metrics.success_rate = (
                        self.metrics.successful_requests / self.metrics.total_requests
                    )
                    self.metrics.total_cost += response.cost
                    self.metrics.last_request_time = datetime.now().isoformat()
                    
                    # Log successful response
                    self.logger.info(
                        json.dumps({
                            "event": "request_success",
                            "request_id": request.request_id,
                            "provider": self.config.name,
                            "model": response.model_used,
                            "response_time": response_time,
                            "cost": response.cost,
                            "confidence": response.confidence,
                            "attempt": attempt + 1,
                            "cached": response.cached
                        })
                    )
                    
                    # Update status if previously degraded
                    if self.status in [AIProviderStatus.DEGRADED, AIProviderStatus.UNAVAILABLE]:
                        self.status = AIProviderStatus.HEALTHY
                    
                    return response
                    
                except asyncio.TimeoutError:
                    last_error = AIProviderError(
                        f"Request timeout after {self.config.timeout_seconds} seconds",
                        error_code="TIMEOUT",
                        provider=self.config.name,
                        retryable=True
                    )
                    
                except AIProviderError as e:
                    last_error = e
                    if not e.retryable:
                        break
                        
                except Exception as e:
                    last_error = AIProviderError(
                        f"Unexpected error: {str(e)}",
                        error_code="INTERNAL_ERROR",
                        provider=self.config.name,
                        retryable=True,
                        details={"exception_type": type(e).__name__}
                    )
                
                # Log retry attempt
                if attempt < self.config.max_retries:
                    retry_delay = self.config.retry_backoff_factor ** attempt
                    self.logger.warning(
                        json.dumps({
                            "event": "request_retry",
                            "request_id": request.request_id,
                            "provider": self.config.name,
                            "attempt": attempt + 1,
                            "max_retries": self.config.max_retries,
                            "error": str(last_error),
                            "retry_delay": retry_delay
                        })
                    )
                    await asyncio.sleep(retry_delay)
            
            # All retries failed
            self.metrics.failed_requests += 1
            self.metrics.last_error = str(last_error)
            self.status = AIProviderStatus.DEGRADED
            
            # Log final failure
            self.logger.error(
                json.dumps({
                    "event": "request_failed",
                    "request_id": request.request_id,
                    "provider": self.config.name,
                    "error": str(last_error),
                    "error_code": last_error.error_code if last_error else "UNKNOWN",
                    "attempts": self.config.max_retries + 1,
                    "total_time": time.time() - start_time
                })
            )
            
            # Return error response
            return AIResponse(
                request_id=request.request_id,
                response_text="",
                model_used=self.config.model_name,
                provider=self.config.name,
                confidence=0.0,
                cost=0.0,
                response_time=time.time() - start_time,
                error=str(last_error),
                metadata={"error_code": last_error.error_code if last_error else "UNKNOWN"}
            )
            
        finally:
            # Clean up active request tracking
            if request.request_id in self._active_requests:
                del self._active_requests[request.request_id]
    
    def get_metrics(self) -> AIProviderMetrics:
        """Get current provider metrics"""
        return self.metrics
    
    def get_status(self) -> AIProviderStatus:
        """Get current provider status"""
        return self.status
    
    def get_active_requests(self) -> int:
        """Get number of active requests"""
        return len(self._active_requests)
    
    def increment_active_requests(self):
        """Increment the count of active requests."""
        request_id = f"req_{time.time()}_{len(self._active_requests)}"
        self._active_requests[request_id] = time.time()
    
    def decrement_active_requests(self):
        """Decrement the count of active requests."""
        if self._active_requests:
            # Remove the oldest request key to decrement the count
            oldest_key = min(self._active_requests, key=self._active_requests.get)
            del self._active_requests[oldest_key]
    
    def is_healthy(self) -> bool:
        """Check if provider is healthy"""
        return self.status == AIProviderStatus.HEALTHY
    
    def is_available(self) -> bool:
        """Check if provider is available for requests"""
        return self.status not in [
            AIProviderStatus.UNAVAILABLE,
            AIProviderStatus.AUTHENTICATION_ERROR
        ]
    
    def get_cost_stats(self) -> Dict[str, float]:
        """Get cost statistics"""
        return {
            "total_cost": self.metrics.total_cost,
            "daily_budget": self.config.daily_budget,
            "budget_remaining": max(0, self.config.daily_budget - self.metrics.total_cost),
            "cost_per_request": self.metrics.total_cost / max(1, self.metrics.total_requests),
            "budget_utilization": (self.metrics.total_cost / self.config.daily_budget) * 100
        }
    
    def get_recommended_model(self, request: AIRequest) -> Optional[str]:
        """Get ML-recommended model for request"""
        if self.ml_model_selector:
            try:
                return self.ml_model_selector.recommend_model(
                    request.prompt, 
                    request.image_path, 
                    request.image_data
                )
            except Exception as e:
                self.logger.warning(f"ML model selection failed: {e}")
                return None
        return None
    
    def update_model_performance(self, model_name: str, request: AIRequest, 
                               success: bool, response_time: float, cost: float):
        """Update ML model performance metrics"""
        if self.ml_model_selector:
            try:
                self.ml_model_selector.update_performance(
                    model_name, 
                    request.prompt, 
                    success, 
                    response_time, 
                    cost,
                    request.image_path, 
                    request.image_data
                )
            except Exception as e:
                self.logger.warning(f"ML performance update failed: {e}")
    
    def get_ml_model_stats(self) -> Optional[Dict[str, Any]]:
        """Get ML model selection statistics"""
        if self.ml_model_selector:
            try:
                return self.ml_model_selector.get_model_stats()
            except Exception as e:
                self.logger.warning(f"ML stats retrieval failed: {e}")
                return None
        return None
    
    def reset_daily_metrics(self):
        """Reset daily metrics (called at midnight)"""
        self.metrics.total_cost = 0.0
        self.metrics.total_requests = 0
        self.metrics.successful_requests = 0
        self.metrics.failed_requests = 0
        self.metrics.total_response_time = 0.0
        self.metrics.average_response_time = 0.0
        self.metrics.success_rate = 0.0
        self.logger.info(f"Daily metrics reset for provider: {self.config.name}")
    
    async def shutdown(self):
        """Shutdown the provider gracefully"""
        self.logger.info(f"Shutting down provider: {self.config.name}")
        
        # Wait for active requests to complete (with timeout)
        if self._active_requests:
            self.logger.info(f"Waiting for {len(self._active_requests)} active requests to complete")
            timeout = 30  # seconds
            start_time = time.time()
            
            while self._active_requests and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.1)
        
        # Close connections
        if self._connection_pool:
            await self._connection_pool.close()
        
        self.status = AIProviderStatus.UNAVAILABLE
        self.logger.info(f"Provider shutdown complete: {self.config.name}")