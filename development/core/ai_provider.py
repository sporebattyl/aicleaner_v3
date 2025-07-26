"""
Simple AI Provider Factory for AICleaner v3 Core Service
Supports OpenAI, Anthropic, Google (Gemini), and Ollama providers
"""

import time
import asyncio
import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

from .service_registry import Reloadable

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Standard response format for all AI providers"""
    text: str
    model: str
    provider: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    cost: Dict[str, float]  # amount, currency (USD)
    response_time_ms: float


class ProviderHealthStatus(Enum):
    """Circuit breaker states for provider health"""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    CIRCUIT_OPEN = "circuit_open"
    DISABLED = "disabled"


@dataclass
class ProviderPerformanceScore:
    """Performance metrics and scoring for provider selection"""
    latency_ms: float = 0.0
    error_rate: float = 0.0
    cost_efficiency: float = 0.0
    success_rate: float = 100.0
    weighted_score: float = 0.0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()
    
    def calculate_weighted_score(self, weights: Dict[str, float]) -> float:
        """Calculate weighted performance score"""
        self.weighted_score = (
            (100 - self.latency_ms / 10) * weights.get('latency', 0.3) +
            (100 - self.error_rate) * weights.get('error_rate', 0.4) + 
            self.cost_efficiency * weights.get('cost', 0.2) +
            self.success_rate * weights.get('success_rate', 0.1)
        )
        return self.weighted_score


@dataclass 
class CircuitBreakerState:
    """Circuit breaker state for a provider"""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: ProviderHealthStatus = ProviderHealthStatus.HEALTHY
    next_retry_time: Optional[datetime] = None
    
    def should_attempt_request(self) -> bool:
        """Check if request should be attempted based on circuit breaker state"""
        if self.state == ProviderHealthStatus.HEALTHY:
            return True
        elif self.state == ProviderHealthStatus.DEGRADED:
            return True  # Allow but track carefully
        elif self.state == ProviderHealthStatus.CIRCUIT_OPEN:
            return self.next_retry_time and datetime.now() >= self.next_retry_time
        else:  # DISABLED
            return False
    
    def record_success(self):
        """Record successful request"""
        self.failure_count = 0
        self.state = ProviderHealthStatus.HEALTHY
        self.next_retry_time = None
    
    def record_failure(self, threshold: int = 5, base_timeout: int = 300):
        """Record failed request and update circuit breaker state"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= threshold:
            self.state = ProviderHealthStatus.CIRCUIT_OPEN
            # Exponential backoff: base_timeout * 2^(failure_count - threshold)
            backoff_multiplier = 2 ** (self.failure_count - threshold)
            timeout_seconds = min(base_timeout * backoff_multiplier, 3600)  # Max 1 hour
            self.next_retry_time = datetime.now() + timedelta(seconds=timeout_seconds)
        elif self.failure_count >= threshold // 2:
            self.state = ProviderHealthStatus.DEGRADED


class FailoverEngine:
    """Intelligent provider failover with compatibility mapping and performance-based selection"""
    
    def __init__(self, config: Dict[str, Any], provider_registry: 'ProviderRegistry'):
        self.config = config
        self.provider_registry = provider_registry
        self._ai_providers_config = config.get('ai_providers', {})
        self._failover_rules = config.get('performance', {}).get('failover_rules', {})
        
    def get_provider_priorities(self) -> List[str]:
        """Get provider priority order from configuration"""
        return self._ai_providers_config.get('provider_priorities', ['ollama', 'gemini', 'openai', 'anthropic'])
    
    def get_model_compatibility_map(self) -> Dict[str, List[str]]:
        """Get model compatibility mapping from configuration"""
        return self._ai_providers_config.get('model_compatibility_map', {})
    
    def find_compatible_models(self, original_model: str) -> List[str]:
        """Find compatible models for fallback"""
        compatibility_map = self.get_model_compatibility_map()
        return compatibility_map.get(original_model, [])
    
    def get_same_provider_models(self, provider_name: str, exclude_model: str = None) -> List[str]:
        """Get other models from the same provider for same-provider-first failover"""
        provider_config = self._ai_providers_config.get(provider_name, {})
        models = list(provider_config.get('models', {}).keys())
        
        # Remove the original model that failed
        if exclude_model and exclude_model in models:
            models.remove(exclude_model)
            
        return models
    
    def calculate_provider_score(self, provider_name: str) -> float:
        """Calculate overall provider score for selection"""
        if not self.provider_registry.is_provider_available(provider_name):
            return 0.0
        
        performance_score = self.provider_registry.get_performance_score(provider_name)
        if not performance_score:
            return 50.0  # Default neutral score for new providers
        
        # Boost score based on recency of data
        time_since_update = (datetime.now() - performance_score.last_updated).total_seconds()
        freshness_multiplier = max(0.5, 1.0 - (time_since_update / 3600))  # Degrade over 1 hour
        
        return performance_score.weighted_score * freshness_multiplier
    
    def select_best_available_provider(self, exclude_providers: Set[str] = None) -> Optional[str]:
        """Select the best available provider based on priorities and performance"""
        exclude_providers = exclude_providers or set()
        priorities = self.get_provider_priorities()
        
        # First, try providers in priority order that are available
        available_providers = []
        for provider_name in priorities:
            if provider_name in exclude_providers:
                continue
            if self.provider_registry.is_provider_available(provider_name):
                score = self.calculate_provider_score(provider_name)
                available_providers.append((provider_name, score))
        
        if not available_providers:
            return None
        
        # Sort by score (descending) and return the best
        available_providers.sort(key=lambda x: x[1], reverse=True)
        return available_providers[0][0]
    
    def get_failover_sequence(self, original_provider: str, original_model: str) -> List[Dict[str, str]]:
        """
        Generate intelligent failover sequence:
        1. Same provider, different models
        2. Compatible models on other providers  
        3. Best available providers with default models
        """
        failover_sequence = []
        same_provider_first = self._failover_rules.get('same_provider_first', True)
        
        if same_provider_first:
            # Phase 1: Try other models from same provider
            same_provider_models = self.get_same_provider_models(original_provider, original_model)
            for model in same_provider_models:
                failover_sequence.append({
                    'provider': original_provider,
                    'model': model,
                    'reason': 'same_provider_fallback'
                })
        
        # Phase 2: Try compatible models on other providers
        compatible_models = self.find_compatible_models(original_model)
        priorities = self.get_provider_priorities()
        
        # Try each compatible model on providers in priority order
        for compatible_model in compatible_models:
            for provider_name in priorities:
                if provider_name == original_provider:
                    continue  # Skip original provider
                
                # Check if this provider has this model
                provider_config = self._ai_providers_config.get(provider_name, {})
                available_models = list(provider_config.get('models', {}).keys())
                
                if compatible_model in available_models:
                    failover_sequence.append({
                        'provider': provider_name,
                        'model': compatible_model,
                        'reason': 'compatible_model_fallback'
                    })
        
        # Phase 3: Try best available providers with their default models
        exclude_providers = {original_provider}
        for _ in range(3):  # Try up to 3 additional providers
            best_provider = self.select_best_available_provider(exclude_providers)
            if not best_provider:
                break
            
            provider_config = self._ai_providers_config.get(best_provider, {})
            default_model = provider_config.get('default_model')
            
            if default_model:
                failover_sequence.append({
                    'provider': best_provider,
                    'model': default_model,
                    'reason': 'best_available_provider'
                })
            
            exclude_providers.add(best_provider)
        
        return failover_sequence


class ProviderRegistry:
    """Thread-safe registry for provider health and performance tracking"""
    
    def __init__(self):
        self.lock = Lock()
        self._health_status: Dict[str, CircuitBreakerState] = {}
        self._performance_scores: Dict[str, ProviderPerformanceScore] = {}
        self._disabled_providers: Set[str] = set()
    
    def get_circuit_breaker_state(self, provider_name: str) -> CircuitBreakerState:
        """Get circuit breaker state for provider"""
        with self.lock:
            if provider_name not in self._health_status:
                self._health_status[provider_name] = CircuitBreakerState()
            return self._health_status[provider_name]
    
    def record_provider_success(self, provider_name: str):
        """Record successful provider request"""
        with self.lock:
            circuit_breaker = self.get_circuit_breaker_state(provider_name)
            circuit_breaker.record_success()
    
    def record_provider_failure(self, provider_name: str, threshold: int = 5):
        """Record failed provider request"""
        with self.lock:
            circuit_breaker = self.get_circuit_breaker_state(provider_name)
            circuit_breaker.record_failure(threshold)
    
    def is_provider_available(self, provider_name: str) -> bool:
        """Check if provider is available for requests"""
        if provider_name in self._disabled_providers:
            return False
        
        circuit_breaker = self.get_circuit_breaker_state(provider_name)
        return circuit_breaker.should_attempt_request()
    
    def update_performance_score(self, provider_name: str, score: ProviderPerformanceScore):
        """Update performance score for provider"""
        with self.lock:
            self._performance_scores[provider_name] = score
    
    def get_performance_score(self, provider_name: str) -> Optional[ProviderPerformanceScore]:
        """Get performance score for provider"""
        with self.lock:
            return self._performance_scores.get(provider_name)
    
    def disable_provider(self, provider_name: str):
        """Manually disable provider"""
        with self.lock:
            self._disabled_providers.add(provider_name)
    
    def enable_provider(self, provider_name: str):
        """Manually enable provider"""
        with self.lock:
            self._disabled_providers.discard(provider_name)
            # Reset circuit breaker state
            if provider_name in self._health_status:
                self._health_status[provider_name].record_success()
    
    def get_all_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive status for all providers"""
        with self.lock:
            status = {}
            for provider_name, circuit_breaker in self._health_status.items():
                performance = self._performance_scores.get(provider_name)
                status[provider_name] = {
                    'health_status': circuit_breaker.state.value,
                    'failure_count': circuit_breaker.failure_count,
                    'last_failure': circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None,
                    'next_retry': circuit_breaker.next_retry_time.isoformat() if circuit_breaker.next_retry_time else None,
                    'disabled': provider_name in self._disabled_providers,
                    'performance_score': performance.weighted_score if performance else 0.0,
                    'available': self.is_provider_available(provider_name)
                }
            return status


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__.lower().replace('provider', '')
        
    @abstractmethod
    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> AIResponse:
        """Generate text using the AI provider"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is available and configured"""
        pass
    
    @abstractmethod
    def get_models(self) -> List[str]:
        """Get list of available models for this provider"""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.default_model = config.get('default_model', 'gpt-4o')
        
    async def is_available(self) -> bool:
        """Check if OpenAI is configured with API key"""
        return bool(self.api_key and self.api_key != '${OPENAI_API_KEY}')
    
    def get_models(self) -> List[str]:
        """Get configured OpenAI models"""
        models_config = self.config.get('models', {})
        return list(models_config.keys()) if models_config else [self.default_model]
    
    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> AIResponse:
        """Generate text using OpenAI API"""
        if not self.is_available():
            raise ValueError("OpenAI provider not properly configured")
            
        start_time = time.time()
        
        # Use specified model or default
        model_name = model or self.default_model
        
        # Get model-specific configuration
        models_config = self.config.get('models', {})
        model_config = models_config.get(model_name, {})
        
        # Merge parameters: kwargs override model config
        params = {
            'temperature': model_config.get('temperature', 0.7),
            'max_tokens': model_config.get('max_tokens', 4096),
            **kwargs
        }
        
        try:
            # Import OpenAI here to avoid dependency issues if not installed
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            response = await client.chat.completions.acreate(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                **params
            )
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Extract usage information
            usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
            
            # Estimate cost (rough approximation - update with actual pricing)
            cost_per_1k_tokens = 0.03  # Rough estimate for GPT-4
            cost_amount = (usage['total_tokens'] / 1000) * cost_per_1k_tokens
            
            return AIResponse(
                text=response.choices[0].message.content,
                model=model_name,
                provider="openai",
                usage=usage,
                cost={"amount": cost_amount, "currency": "USD"},
                response_time_ms=response_time_ms
            )
            
        except ImportError:
            raise ValueError("OpenAI library not installed. Run: pip install openai")
        except ValueError as e:
            logger.error(f"OpenAI configuration error: {e}")
            raise
        except ConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            raise
        except TimeoutError as e:
            logger.error(f"OpenAI request timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected OpenAI error: {e}", exc_info=True)
            raise


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.default_model = config.get('default_model', 'claude-3-5-sonnet-20241022')
        
    async def is_available(self) -> bool:
        """Check if Anthropic is configured with API key"""
        return bool(self.api_key and self.api_key != '${ANTHROPIC_API_KEY}')
    
    def get_models(self) -> List[str]:
        """Get configured Anthropic models"""
        models_config = self.config.get('models', {})
        return list(models_config.keys()) if models_config else [self.default_model]
    
    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> AIResponse:
        """Generate text using Anthropic API"""
        if not self.is_available():
            raise ValueError("Anthropic provider not properly configured")
            
        start_time = time.time()
        model_name = model or self.default_model
        
        # Get model-specific configuration
        models_config = self.config.get('models', {})
        model_config = models_config.get(model_name, {})
        
        params = {
            'max_tokens': model_config.get('max_tokens', 4096),
            'temperature': model_config.get('temperature', 0.7),
            **kwargs
        }
        
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = await client.messages.acreate(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                **params
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Extract usage information
            usage = {
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens
            }
            
            # Estimate cost
            cost_per_1k_tokens = 0.015  # Rough estimate for Claude
            cost_amount = (usage['total_tokens'] / 1000) * cost_per_1k_tokens
            
            return AIResponse(
                text=response.content[0].text,
                model=model_name,
                provider="anthropic",
                usage=usage,
                cost={"amount": cost_amount, "currency": "USD"},
                response_time_ms=response_time_ms
            )
            
        except ImportError:
            raise ValueError("Anthropic library not installed. Run: pip install anthropic")
        except ValueError as e:
            logger.error(f"Anthropic configuration error: {e}")
            raise
        except ConnectionError as e:
            logger.error(f"Anthropic connection error: {e}")
            raise
        except TimeoutError as e:
            logger.error(f"Anthropic request timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected Anthropic error: {e}", exc_info=True)
            raise


class GeminiProvider(AIProvider):
    """Google Gemini provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.default_model = config.get('default_model', 'gemini-2.5-pro')
        
    async def is_available(self) -> bool:
        """Check if Gemini is configured with API key"""
        return bool(self.api_key and self.api_key != '${GEMINI_API_KEY}')
    
    def get_models(self) -> List[str]:
        """Get configured Gemini models"""
        models_config = self.config.get('models', {})
        return list(models_config.keys()) if models_config else [self.default_model]
    
    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> AIResponse:
        """Generate text using Gemini API"""
        if not self.is_available():
            raise ValueError("Gemini provider not properly configured")
            
        start_time = time.time()
        model_name = model or self.default_model
        
        # Get model-specific configuration
        models_config = self.config.get('models', {})
        model_config = models_config.get(model_name, {})
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            
            # Configure generation parameters
            gen_config = model_config.get('generation_config', {})
            generation_config = {
                'temperature': kwargs.get('temperature', gen_config.get('temperature', 0.8)),
                'max_output_tokens': kwargs.get('max_tokens', gen_config.get('max_output_tokens', 8192)),
            }
            
            model_instance = genai.GenerativeModel(
                model_name,
                generation_config=generation_config
            )
            
            response = await model_instance.generate_content_async(prompt)
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Gemini usage information (may be limited)
            usage = {
                'prompt_tokens': getattr(response.usage_metadata, 'prompt_token_count', 0),
                'completion_tokens': getattr(response.usage_metadata, 'candidates_token_count', 0),
                'total_tokens': getattr(response.usage_metadata, 'total_token_count', 0)
            }
            
            # Estimate cost (Gemini is often free/low cost)
            cost_per_1k_tokens = 0.001  # Very rough estimate
            cost_amount = (usage['total_tokens'] / 1000) * cost_per_1k_tokens
            
            return AIResponse(
                text=response.text,
                model=model_name,
                provider="gemini",
                usage=usage,
                cost={"amount": cost_amount, "currency": "USD"},
                response_time_ms=response_time_ms
            )
            
        except ImportError:
            raise ValueError("Google Generative AI library not installed. Run: pip install google-generativeai")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise


class OllamaProvider(AIProvider):
    """Ollama local provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.default_model = config.get('default_model', 'llama3.2')
        
    async def is_available(self) -> bool:
        """Check if Ollama server is reachable"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except:
            return False
    
    def get_models(self) -> List[str]:
        """Get configured Ollama models"""
        models_config = self.config.get('models', {})
        return list(models_config.keys()) if models_config else [self.default_model]
    
    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> AIResponse:
        """Generate text using Ollama API"""
        if not self.is_available():
            raise ValueError("Ollama server not reachable")
            
        start_time = time.time()
        model_name = model or self.default_model
        
        # Get model-specific configuration
        models_config = self.config.get('models', {})
        model_config = models_config.get(model_name, {})
        model_options = model_config.get('options', {})
        
        params = {
            'temperature': kwargs.get('temperature', model_options.get('temperature', 0.8)),
            'num_ctx': kwargs.get('num_ctx', model_options.get('num_ctx', 4096)),
            **kwargs
        }
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    'model': model_name,
                    'prompt': prompt,
                    'stream': False,
                    'options': params
                }
                
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status != 200:
                        raise ValueError(f"Ollama API error: {response.status}")
                    
                    result = await response.json()
                    
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    # Ollama provides some usage info
                    usage = {
                        'prompt_tokens': result.get('prompt_eval_count', 0),
                        'completion_tokens': result.get('eval_count', 0),
                        'total_tokens': result.get('prompt_eval_count', 0) + result.get('eval_count', 0)
                    }
                    
                    # Local models have no cost
                    cost = {"amount": 0.0, "currency": "USD"}
                    
                    return AIResponse(
                        text=result['response'],
                        model=model_name,
                        provider="ollama",
                        usage=usage,
                        cost=cost,
                        response_time_ms=response_time_ms
                    )
                    
        except ImportError:
            raise ValueError("aiohttp library not installed. Run: pip install aiohttp")
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise


class AIProviderFactory:
    """
    Simple factory for creating AI providers.
    Power-user focused - no complex registration or enterprise patterns.
    """
    
    _providers = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'gemini': GeminiProvider,
        'ollama': OllamaProvider
    }
    
    @classmethod
    def create_provider(cls, provider_name: str, config: Dict[str, Any]) -> AIProvider:
        """Create an AI provider instance"""
        if provider_name not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(f"Unknown provider '{provider_name}'. Available: {available}")
        
        provider_class = cls._providers[provider_name]
        return provider_class(config)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of supported provider names"""
        return list(cls._providers.keys())


class AIService(Reloadable):
    """
    Simple AI service that manages providers and handles requests.
    Uses configuration to determine active provider and fallbacks.
    """
    
    def __init__(self, config_loader):
        from .config_loader import ConfigurationLoader
        self.config_loader: ConfigurationLoader = config_loader
        self._providers_cache: Dict[str, AIProvider] = {}
        self.provider_registry = ProviderRegistry()
        self._config = self.config_loader.load_configuration()
        self.failover_engine = FailoverEngine(self._config, self.provider_registry)
        
    def get_provider(self, provider_name: Optional[str] = None) -> AIProvider:
        """Get AI provider instance (cached)"""
        # Use specified provider or get active provider from config
        if not provider_name:
            provider_name = self.config_loader.get_active_provider()
        
        # Return cached provider if available
        if provider_name in self._providers_cache:
            return self._providers_cache[provider_name]
        
        # Create new provider
        try:
            provider_config = self.config_loader.get_ai_provider_config(provider_name)
            provider = AIProviderFactory.create_provider(provider_name, provider_config)
            
            # Cache the provider
            self._providers_cache[provider_name] = provider
            
            return provider
        except Exception as e:
            logger.error(f"Failed to create provider {provider_name}: {e}")
            raise
    
    async def generate(self, prompt: str, provider: Optional[str] = None, 
                      model: Optional[str] = None, **kwargs) -> AIResponse:
        """Generate text using specified or default provider with intelligent failover"""
        original_provider = provider or self.config_loader.get_active_provider()
        original_model = model or self._get_default_model_for_provider(original_provider)
        
        # First attempt with requested provider/model
        try:
            return await self._attempt_generation(prompt, original_provider, original_model, **kwargs)
        except Exception as first_error:
            logger.warning(f"Primary generation failed ({original_provider}/{original_model}): {first_error}")
            
            # Get failover sequence and attempt each option
            failover_sequence = self.failover_engine.get_failover_sequence(original_provider, original_model)
            max_retries = self._config.get('performance', {}).get('failover_rules', {}).get('max_retries_before_switch', 3)
            
            for i, fallback in enumerate(failover_sequence[:max_retries]):
                try:
                    logger.info(f"Attempting failover {i+1}/{max_retries}: {fallback['provider']}/{fallback['model']} ({fallback['reason']})")
                    response = await self._attempt_generation(
                        prompt, 
                        fallback['provider'], 
                        fallback['model'], 
                        **kwargs
                    )
                    
                    # Log successful failover
                    logger.info(f"Successful failover to {fallback['provider']}/{fallback['model']}")
                    return response
                    
                except Exception as fallback_error:
                    logger.warning(f"Failover attempt {i+1} failed ({fallback['provider']}/{fallback['model']}): {fallback_error}")
                    continue
            
            # All failover attempts failed
            raise ValueError(f"All provider failover attempts exhausted. Original error: {first_error}")

    async def _attempt_generation(self, prompt: str, provider_name: str, model_name: str, **kwargs) -> AIResponse:
        """Attempt generation with a specific provider/model combination"""
        # Check circuit breaker state
        if not self.provider_registry.is_provider_available(provider_name):
            raise ValueError(f"Provider {provider_name} is currently unavailable (circuit breaker open)")
        
        ai_provider = self.get_provider(provider_name)
        
        if not await ai_provider.is_available():
            self.provider_registry.record_provider_failure(provider_name)
            raise ValueError(f"Provider {provider_name} is not available")
        
        try:
            start_time = time.time()
            response = await ai_provider.generate(prompt, model_name, **kwargs)
            
            # Record success and update performance metrics
            self.provider_registry.record_provider_success(provider_name)
            
            # Calculate and update performance score
            performance_score = ProviderPerformanceScore(
                latency_ms=response.response_time_ms,
                error_rate=0.0,  # Success case
                cost_efficiency=self._calculate_cost_efficiency(response.cost),
                success_rate=100.0  # This single request was successful
            )
            
            # Get weights from config and calculate score
            weights = self._get_performance_weights()
            performance_score.calculate_weighted_score(weights)
            self.provider_registry.update_performance_score(provider_name, performance_score)
            
            return response
            
        except Exception as e:
            # Record failure for circuit breaker
            self.provider_registry.record_provider_failure(provider_name)
            logger.error(f"Provider {provider_name} request failed: {e}")
            raise
    
    async def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all configured providers"""
        config = self.config_loader.load_configuration()
        ai_providers = config.get('ai_providers', {})
        
        status = {}
        for provider_name in ai_providers.keys():
            try:
                provider = self.get_provider(provider_name)
                status[provider_name] = {
                    'available': await provider.is_available(),
                    'models': provider.get_models(),
                    'last_request': None,  # Would track in production
                    'error_count': 0       # Would track in production
                }
            except Exception as e:
                status[provider_name] = {
                    'available': False,
                    'models': [],
                    'error': str(e)
                }
        
        return status
    
    def clear_provider_cache(self):
        """Clear provider cache (useful for config reloads)"""
        self._providers_cache.clear()
    
    def _calculate_cost_efficiency(self, cost: Dict[str, float]) -> float:
        """Calculate cost efficiency score (higher is better)"""
        cost_amount = cost.get('amount', 0.0)
        if cost_amount == 0.0:
            return 100.0  # Free is most efficient
        # Normalize cost to 0-100 scale (assuming $0.10 per request is baseline)
        baseline_cost = 0.10
        efficiency = max(0, 100 - (cost_amount / baseline_cost) * 100)
        return min(100.0, efficiency)
    
    def _get_performance_weights(self) -> Dict[str, float]:
        """Get performance scoring weights from configuration"""
        performance_config = self._config.get('performance', {})
        weights = performance_config.get('performance_weight', {})
        
        # Default weights if not configured
        default_weights = {
            'latency': 0.3,
            'error_rate': 0.4,
            'cost': 0.2,
            'success_rate': 0.1
        }
        
        return {key: weights.get(key, default_value) for key, default_value in default_weights.items()}
    
    def get_provider_registry_status(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive provider registry status"""
        return self.provider_registry.get_all_provider_status()
    
    def disable_provider(self, provider_name: str):
        """Manually disable a provider"""
        self.provider_registry.disable_provider(provider_name)
    
    def enable_provider(self, provider_name: str):
        """Manually enable a provider"""
        self.provider_registry.enable_provider(provider_name)
    
    def _get_default_model_for_provider(self, provider_name: str) -> str:
        """Get the default model for a given provider"""
        provider_config = self._config.get('ai_providers', {}).get(provider_name, {})
        return provider_config.get('default_model', 'unknown')
    
    async def validate_config(self, new_config: Dict) -> tuple[bool, Optional[str]]:
        """
        Validates the new AI service configuration.
        Checks if the active provider exists and has necessary keys.
        """
        logger.info("AIService: Performing validation of new config.")
        new_active_provider = new_config.get('general', {}).get('active_provider')
        new_ai_providers_config = new_config.get('ai_providers', {})

        if not new_active_provider:
            return False, "New configuration missing 'general.active_provider'."
        
        if new_active_provider not in new_ai_providers_config:
            return False, f"New active provider '{new_active_provider}' not found in 'ai_providers' section."
        
        # Add more specific validation for provider keys if needed (e.g., API keys, URLs)
        # For example:
        # if new_active_provider == 'openai' and not new_ai_providers_config.get('openai', {}).get('api_key'):
        #     return False, "OpenAI API key missing in new configuration."

        logger.info("AIService: New configuration validated successfully.")
        return True, None

    async def reload_config(self, new_config: Dict):
        """Applies the new AI service configuration with initialize-then-swap pattern."""
        logger.info("AIService: Applying new configuration.")
        
        # Store old config for potential rollback
        old_config = self._config
        old_providers_cache = self._providers_cache.copy()
        
        try:
            # Update configuration
            self._config = new_config
            
            # Clear provider cache to force recreation with new config
            self._providers_cache.clear()
            
            # Initialize new providers with new config (lazy initialization will happen on first use)
            logger.info("AIService: Provider cache cleared, new providers will be initialized on demand.")
            
            logger.info("AIService: Configuration reloaded successfully.")
            
        except Exception as e:
            # Rollback on failure
            logger.error(f"AIService: Configuration reload failed, rolling back: {e}")
            self._config = old_config
            self._providers_cache = old_providers_cache
            raise