"""
Phase 2A: AI Model Optimization Framework
Advanced AI model optimization with performance tuning and adaptive selection.
"""

import asyncio
import time
import json
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
from datetime import datetime, timedelta

# Import AI providers from Phase 1B
from ..providers.ai_provider_manager import AIProviderManager
from ..providers.base_provider import BaseProvider


class OptimizationStrategy(Enum):
    """AI model optimization strategies."""
    PERFORMANCE = "performance"      # Prioritize speed
    COST = "cost"                   # Prioritize cost efficiency
    QUALITY = "quality"             # Prioritize response quality
    BALANCED = "balanced"           # Balance all factors
    ADAPTIVE = "adaptive"           # Dynamic optimization


@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for AI model optimization."""
    response_time_ms: float = 0.0
    cost_per_request: float = 0.0
    quality_score: float = 0.0
    success_rate: float = 0.0
    token_efficiency: float = 0.0
    cache_hit_rate: float = 0.0
    
    requests_count: int = 0
    total_cost: float = 0.0
    total_time_ms: float = 0.0
    failed_requests: int = 0
    
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class OptimizationConfig:
    """Configuration for AI model optimization."""
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    
    # Performance targets
    max_response_time_ms: float = 2000.0
    min_quality_score: float = 0.8
    max_cost_per_request: float = 0.05
    target_success_rate: float = 0.95
    
    # Optimization settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    enable_request_batching: bool = True
    batch_size: int = 5
    batch_timeout_ms: float = 100.0
    
    # Resource limits
    daily_cost_budget: float = 10.0
    hourly_request_limit: int = 1000
    concurrent_request_limit: int = 10
    
    # Quality settings
    enable_quality_monitoring: bool = True
    quality_threshold: float = 0.7
    enable_adaptive_selection: bool = True


class PromptOptimizer:
    """Advanced prompt optimization system."""
    
    def __init__(self):
        self.optimization_cache = {}
        self.performance_history = {}
        
    def optimize_prompt(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Optimize prompt for better AI model performance.
        
        Args:
            prompt: Original prompt text
            context: Request context for optimization
            
        Returns:
            Optimized prompt
        """
        # Generate cache key
        cache_key = self._generate_cache_key(prompt, context)
        
        if cache_key in self.optimization_cache:
            return self.optimization_cache[cache_key]
        
        # Apply optimization techniques
        optimized = self._apply_optimization_techniques(prompt, context)
        
        # Cache optimized prompt
        self.optimization_cache[cache_key] = optimized
        
        return optimized
    
    def _apply_optimization_techniques(self, prompt: str, context: Dict[str, Any]) -> str:
        """Apply various prompt optimization techniques."""
        optimized = prompt
        
        # 1. Context-aware prompt enhancement
        if context.get('task_type') == 'device_analysis':
            optimized = self._enhance_device_analysis_prompt(optimized)
        elif context.get('task_type') == 'automation_suggestion':
            optimized = self._enhance_automation_prompt(optimized)
        
        # 2. Token efficiency optimization
        optimized = self._optimize_token_usage(optimized)
        
        # 3. Quality enhancement
        optimized = self._enhance_prompt_quality(optimized)
        
        return optimized
    
    def _enhance_device_analysis_prompt(self, prompt: str) -> str:
        """Enhance prompts for device analysis tasks."""
        enhancement = """
        Please analyze the device data systematically:
        1. Identify device type and capabilities
        2. Assess current performance metrics
        3. Suggest optimization opportunities
        4. Provide actionable recommendations
        
        Focus on energy efficiency and automation potential.
        """
        return f"{enhancement}\n\n{prompt}"
    
    def _enhance_automation_prompt(self, prompt: str) -> str:
        """Enhance prompts for automation suggestions."""
        enhancement = """
        For automation suggestions, consider:
        1. User behavior patterns
        2. Energy efficiency
        3. Convenience improvements
        4. Safety considerations
        
        Provide specific, implementable automation rules.
        """
        return f"{enhancement}\n\n{prompt}"
    
    def _optimize_token_usage(self, prompt: str) -> str:
        """Optimize prompt for token efficiency."""
        # Remove redundant words and phrases
        optimizations = [
            ("please ", ""),
            ("could you ", ""),
            ("I would like you to ", ""),
            ("  ", " "),  # Multiple spaces
        ]
        
        optimized = prompt
        for old, new in optimizations:
            optimized = optimized.replace(old, new)
        
        return optimized.strip()
    
    def _enhance_prompt_quality(self, prompt: str) -> str:
        """Enhance prompt quality for better responses."""
        if not prompt.endswith('.'):
            prompt += '.'
        
        # Add structure hints
        if 'analyze' in prompt.lower() and 'format' not in prompt.lower():
            prompt += "\n\nPlease format your response with clear sections and bullet points."
        
        return prompt
    
    def _generate_cache_key(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate cache key for prompt optimization."""
        content = f"{prompt}:{json.dumps(context, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()


class ResponseCache:
    """Intelligent response caching system."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
        self.lock = threading.RLock()
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and valid."""
        with self.lock:
            if cache_key not in self.cache:
                self.cache_stats['misses'] += 1
                return None
            
            entry = self.cache[cache_key]
            
            # Check if cache entry is still valid
            if self._is_cache_entry_valid(entry):
                self.cache_stats['hits'] += 1
                return entry['response']
            else:
                # Remove expired entry
                del self.cache[cache_key]
                self.cache_stats['misses'] += 1
                return None
    
    def put(self, cache_key: str, response: Dict[str, Any], quality_score: float = 1.0):
        """Cache response with quality score."""
        if not self.config.enable_caching:
            return
        
        with self.lock:
            # Only cache high-quality responses
            if quality_score >= self.config.quality_threshold:
                self.cache[cache_key] = {
                    'response': response,
                    'timestamp': datetime.now(),
                    'quality_score': quality_score
                }
                
                # Implement simple LRU eviction if cache gets too large
                if len(self.cache) > 1000:
                    self._evict_oldest_entries(100)
    
    def _is_cache_entry_valid(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid."""
        age = datetime.now() - entry['timestamp']
        return age.total_seconds() < self.config.cache_ttl_seconds
    
    def _evict_oldest_entries(self, count: int):
        """Evict oldest cache entries."""
        if len(self.cache) <= count:
            return
        
        # Sort by timestamp and remove oldest
        sorted_items = sorted(
            self.cache.items(),
            key=lambda x: x[1]['timestamp']
        )
        
        for i in range(count):
            cache_key = sorted_items[i][0]
            del self.cache[cache_key]
            self.cache_stats['evictions'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        with self.lock:
            total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
            hit_rate = self.cache_stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'cache_size': len(self.cache),
                'hit_rate': hit_rate,
                'total_hits': self.cache_stats['hits'],
                'total_misses': self.cache_stats['misses'],
                'total_evictions': self.cache_stats['evictions']
            }


class AIModelOptimizer:
    """
    Advanced AI Model Optimization System.
    
    Provides intelligent model selection, performance optimization,
    and resource management for AI operations.
    """
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.provider_manager = AIProviderManager()
        self.prompt_optimizer = PromptOptimizer()
        self.response_cache = ResponseCache(self.config)
        
        # Performance tracking
        self.metrics = {}
        self.request_history = []
        self.cost_tracker = {
            'daily_spent': 0.0,
            'hourly_requests': 0,
            'last_reset': datetime.now()
        }
        
        # Threading for async operations
        self.executor = ThreadPoolExecutor(max_workers=self.config.concurrent_request_limit)
        self.logger = logging.getLogger(__name__)
    
    async def optimize_ai_request(
        self,
        prompt: str,
        context: Dict[str, Any] = None,
        preferred_provider: str = None
    ) -> Dict[str, Any]:
        """
        Optimize and execute AI request with intelligent provider selection.
        
        Args:
            prompt: Request prompt
            context: Request context
            preferred_provider: Preferred AI provider (optional)
            
        Returns:
            Optimized AI response with metadata
        """
        context = context or {}
        request_start = time.time()
        
        try:
            # 1. Check budget and rate limits
            if not self._check_resource_limits():
                raise Exception("Resource limits exceeded")
            
            # 2. Generate cache key
            cache_key = self._generate_request_cache_key(prompt, context)
            
            # 3. Check cache first
            cached_response = self.response_cache.get(cache_key)
            if cached_response:
                self.logger.debug(f"Cache hit for request: {cache_key[:8]}...")
                return self._format_response(cached_response, from_cache=True)
            
            # 4. Optimize prompt
            optimized_prompt = self.prompt_optimizer.optimize_prompt(prompt, context)
            
            # 5. Select optimal provider
            selected_provider = await self._select_optimal_provider(
                optimized_prompt, context, preferred_provider
            )
            
            # 6. Execute request with optimization
            response = await self._execute_optimized_request(
                selected_provider, optimized_prompt, context
            )
            
            # 7. Evaluate response quality
            quality_score = self._evaluate_response_quality(response, context)
            
            # 8. Cache high-quality responses
            if quality_score >= self.config.quality_threshold:
                self.response_cache.put(cache_key, response, quality_score)
            
            # 9. Update metrics
            execution_time = (time.time() - request_start) * 1000
            self._update_metrics(selected_provider, execution_time, quality_score, response)
            
            return self._format_response(response, {
                'provider': selected_provider,
                'quality_score': quality_score,
                'execution_time_ms': execution_time,
                'from_cache': False
            })
            
        except Exception as e:
            self.logger.error(f"AI request optimization failed: {str(e)}")
            # Try fallback provider if available
            return await self._handle_request_failure(prompt, context, str(e))
    
    async def _select_optimal_provider(
        self,
        prompt: str,
        context: Dict[str, Any],
        preferred_provider: str = None
    ) -> str:
        """Select optimal AI provider based on optimization strategy."""
        
        if preferred_provider and self._is_provider_available(preferred_provider):
            return preferred_provider
        
        available_providers = self.provider_manager.get_available_providers()
        
        if not available_providers:
            raise Exception("No AI providers available")
        
        if len(available_providers) == 1:
            return available_providers[0]
        
        # Apply optimization strategy
        if self.config.strategy == OptimizationStrategy.PERFORMANCE:
            return self._select_fastest_provider(available_providers)
        elif self.config.strategy == OptimizationStrategy.COST:
            return self._select_cheapest_provider(available_providers)
        elif self.config.strategy == OptimizationStrategy.QUALITY:
            return self._select_highest_quality_provider(available_providers)
        elif self.config.strategy == OptimizationStrategy.ADAPTIVE:
            return self._select_adaptive_provider(available_providers, context)
        else:  # BALANCED
            return self._select_balanced_provider(available_providers)
    
    def _select_fastest_provider(self, providers: List[str]) -> str:
        """Select provider with fastest average response time."""
        best_provider = providers[0]
        best_time = float('inf')
        
        for provider in providers:
            metrics = self._get_provider_metrics(provider)
            if metrics.response_time_ms < best_time:
                best_time = metrics.response_time_ms
                best_provider = provider
        
        return best_provider
    
    def _select_cheapest_provider(self, providers: List[str]) -> str:
        """Select provider with lowest cost per request."""
        best_provider = providers[0]
        best_cost = float('inf')
        
        for provider in providers:
            metrics = self._get_provider_metrics(provider)
            if metrics.cost_per_request < best_cost:
                best_cost = metrics.cost_per_request
                best_provider = provider
        
        return best_provider
    
    def _select_highest_quality_provider(self, providers: List[str]) -> str:
        """Select provider with highest quality score."""
        best_provider = providers[0]
        best_quality = 0.0
        
        for provider in providers:
            metrics = self._get_provider_metrics(provider)
            if metrics.quality_score > best_quality:
                best_quality = metrics.quality_score
                best_provider = provider
        
        return best_provider
    
    def _select_adaptive_provider(self, providers: List[str], context: Dict[str, Any]) -> str:
        """Select provider adaptively based on context and current performance."""
        # Consider task complexity
        task_type = context.get('task_type', 'general')
        
        if task_type == 'complex_analysis':
            # Use high-quality provider for complex tasks
            return self._select_highest_quality_provider(providers)
        elif task_type == 'simple_query':
            # Use fastest/cheapest for simple tasks
            return self._select_fastest_provider(providers)
        else:
            # Use balanced approach
            return self._select_balanced_provider(providers)
    
    def _select_balanced_provider(self, providers: List[str]) -> str:
        """Select provider with best balance of performance, cost, and quality."""
        best_provider = providers[0]
        best_score = 0.0
        
        for provider in providers:
            metrics = self._get_provider_metrics(provider)
            
            # Calculate balanced score (normalize and weight metrics)
            performance_score = max(0, 1 - (metrics.response_time_ms / 5000))  # 5s max
            cost_score = max(0, 1 - (metrics.cost_per_request / 0.1))  # $0.1 max
            quality_score = metrics.quality_score
            
            balanced_score = (
                performance_score * 0.3 +
                cost_score * 0.3 +
                quality_score * 0.4
            )
            
            if balanced_score > best_score:
                best_score = balanced_score
                best_provider = provider
        
        return best_provider
    
    async def _execute_optimized_request(
        self,
        provider: str,
        prompt: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute AI request with optimization techniques."""
        
        # Apply request-specific optimizations
        request_config = self._optimize_request_config(provider, context)
        
        # Execute with timeout and retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.provider_manager.generate_response(
                    provider=provider,
                    prompt=prompt,
                    config=request_config
                )
                
                # Validate response
                if self._validate_response(response):
                    return response
                else:
                    raise Exception("Invalid response format")
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                # Wait before retry with exponential backoff
                wait_time = (2 ** attempt) * 0.5
                await asyncio.sleep(wait_time)
        
        raise Exception("Request failed after all retries")
    
    def _optimize_request_config(self, provider: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize request configuration for specific provider."""
        base_config = {
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        # Provider-specific optimizations
        if provider == 'openai':
            base_config.update({
                'temperature': 0.6,  # Slightly more focused
                'top_p': 0.9
            })
        elif provider == 'anthropic':
            base_config.update({
                'temperature': 0.7,
                'max_tokens': 1500  # Claude handles longer responses well
            })
        elif provider == 'google':
            base_config.update({
                'temperature': 0.8,  # Gemini benefits from slightly higher creativity
                'top_k': 40
            })
        
        # Task-specific optimizations
        task_type = context.get('task_type', 'general')
        if task_type == 'device_analysis':
            base_config['temperature'] = 0.3  # More deterministic for analysis
        elif task_type == 'creative_automation':
            base_config['temperature'] = 0.9  # More creative for suggestions
        
        return base_config
    
    def _evaluate_response_quality(self, response: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Evaluate AI response quality."""
        quality_score = 0.0
        
        # Basic response validation
        if not response or 'content' not in response:
            return 0.0
        
        content = response['content']
        
        # Length appropriateness (not too short, not too long)
        length_score = 0.0
        if 50 <= len(content) <= 2000:
            length_score = 1.0
        elif len(content) < 50:
            length_score = len(content) / 50
        else:
            length_score = 2000 / len(content)
        
        quality_score += length_score * 0.2
        
        # Content relevance (basic keyword matching)
        relevance_score = self._calculate_relevance_score(content, context)
        quality_score += relevance_score * 0.3
        
        # Structure quality (paragraphs, lists, etc.)
        structure_score = self._calculate_structure_score(content)
        quality_score += structure_score * 0.2
        
        # Completeness (ends properly, addresses the prompt)
        completeness_score = self._calculate_completeness_score(content)
        quality_score += completeness_score * 0.3
        
        return min(1.0, quality_score)
    
    def _calculate_relevance_score(self, content: str, context: Dict[str, Any]) -> float:
        """Calculate content relevance score."""
        # Simple keyword matching approach
        keywords = context.get('keywords', [])
        if not keywords:
            return 0.8  # Default relevance
        
        matches = sum(1 for keyword in keywords if keyword.lower() in content.lower())
        return min(1.0, matches / len(keywords))
    
    def _calculate_structure_score(self, content: str) -> float:
        """Calculate content structure quality score."""
        score = 0.0
        
        # Check for proper sentence structure
        sentences = content.split('.')
        if len(sentences) >= 2:
            score += 0.4
        
        # Check for lists or structured content
        if any(marker in content for marker in ['-', '*', '1.', '2.', '\n•']):
            score += 0.3
        
        # Check for paragraph breaks
        if '\n\n' in content:
            score += 0.3
        
        return min(1.0, score)
    
    def _calculate_completeness_score(self, content: str) -> float:
        """Calculate response completeness score."""
        # Check if response ends properly
        if content.strip().endswith(('.', '!', '?')):
            return 1.0
        elif len(content.strip()) > 100:
            return 0.8  # Likely complete but poor punctuation
        else:
            return 0.3  # Likely incomplete
    
    def _get_provider_metrics(self, provider: str) -> ModelPerformanceMetrics:
        """Get performance metrics for a provider."""
        if provider not in self.metrics:
            self.metrics[provider] = ModelPerformanceMetrics()
        return self.metrics[provider]
    
    def _update_metrics(
        self,
        provider: str,
        execution_time: float,
        quality_score: float,
        response: Dict[str, Any]
    ):
        """Update performance metrics for a provider."""
        metrics = self._get_provider_metrics(provider)
        
        # Update metrics
        metrics.requests_count += 1
        metrics.total_time_ms += execution_time
        metrics.response_time_ms = metrics.total_time_ms / metrics.requests_count
        
        # Estimate cost (provider-specific)
        estimated_cost = self._estimate_request_cost(provider, response)
        metrics.total_cost += estimated_cost
        metrics.cost_per_request = metrics.total_cost / metrics.requests_count
        
        # Update quality score (rolling average)
        if metrics.requests_count == 1:
            metrics.quality_score = quality_score
        else:
            metrics.quality_score = (
                metrics.quality_score * 0.9 + quality_score * 0.1
            )
        
        # Update success rate
        metrics.success_rate = (
            (metrics.requests_count - metrics.failed_requests) / metrics.requests_count
        )
        
        metrics.last_updated = datetime.now()
        
        # Update cost tracking
        self.cost_tracker['daily_spent'] += estimated_cost
        self.cost_tracker['hourly_requests'] += 1
    
    def _estimate_request_cost(self, provider: str, response: Dict[str, Any]) -> float:
        """Estimate cost for a request based on provider and usage."""
        # Simplified cost estimation
        token_count = len(response.get('content', '').split())
        
        cost_per_token = {
            'openai': 0.00002,      # Approximate GPT-4 pricing
            'anthropic': 0.000015,  # Approximate Claude pricing
            'google': 0.00001,      # Approximate Gemini pricing
            'ollama': 0.0           # Local model, no API cost
        }
        
        return cost_per_token.get(provider, 0.00002) * token_count
    
    def _check_resource_limits(self) -> bool:
        """Check if resource limits allow new requests."""
        now = datetime.now()
        
        # Reset daily/hourly counters if needed
        if now.date() > self.cost_tracker['last_reset'].date():
            self.cost_tracker['daily_spent'] = 0.0
            self.cost_tracker['last_reset'] = now
        
        if now.hour != self.cost_tracker['last_reset'].hour:
            self.cost_tracker['hourly_requests'] = 0
            self.cost_tracker['last_reset'] = now
        
        # Check limits
        if self.cost_tracker['daily_spent'] >= self.config.daily_cost_budget:
            self.logger.warning("Daily cost budget exceeded")
            return False
        
        if self.cost_tracker['hourly_requests'] >= self.config.hourly_request_limit:
            self.logger.warning("Hourly request limit exceeded")
            return False
        
        return True
    
    def _is_provider_available(self, provider: str) -> bool:
        """Check if a provider is available and healthy."""
        return self.provider_manager.is_provider_healthy(provider)
    
    def _validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate AI response format and content."""
        if not isinstance(response, dict):
            return False
        
        if 'content' not in response:
            return False
        
        content = response['content']
        if not isinstance(content, str) or len(content.strip()) < 10:
            return False
        
        return True
    
    def _generate_request_cache_key(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        cache_content = {
            'prompt': prompt,
            'context': {k: v for k, v in context.items() if k != 'request_id'}
        }
        content_str = json.dumps(cache_content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]
    
    async def _handle_request_failure(
        self,
        prompt: str,
        context: Dict[str, Any],
        error: str
    ) -> Dict[str, Any]:
        """Handle request failures with fallback mechanisms."""
        
        # Try fallback provider
        available_providers = self.provider_manager.get_available_providers()
        
        if available_providers:
            fallback_provider = available_providers[0]
            self.logger.warning(f"Attempting fallback to provider: {fallback_provider}")
            
            try:
                response = await self.provider_manager.generate_response(
                    provider=fallback_provider,
                    prompt=prompt,
                    config={'temperature': 0.5, 'max_tokens': 500}
                )
                
                return self._format_response(response, {
                    'provider': fallback_provider,
                    'fallback': True,
                    'original_error': error
                })
                
            except Exception as fallback_error:
                self.logger.error(f"Fallback also failed: {str(fallback_error)}")
        
        # Return error response
        return {
            'success': False,
            'error': error,
            'content': 'AI service temporarily unavailable. Please try again later.',
            'metadata': {
                'fallback_attempted': len(available_providers) > 0,
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _format_response(self, response: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format AI response with optimization metadata."""
        return {
            'success': True,
            'content': response.get('content', ''),
            'metadata': {
                'optimization_enabled': True,
                'cache_stats': self.response_cache.get_stats(),
                'timestamp': datetime.now().isoformat(),
                **(metadata or {})
            }
        }
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics."""
        total_requests = sum(metrics.requests_count for metrics in self.metrics.values())
        
        return {
            'total_requests': total_requests,
            'provider_metrics': {
                provider: {
                    'requests': metrics.requests_count,
                    'avg_response_time_ms': metrics.response_time_ms,
                    'avg_cost_per_request': metrics.cost_per_request,
                    'avg_quality_score': metrics.quality_score,
                    'success_rate': metrics.success_rate
                }
                for provider, metrics in self.metrics.items()
            },
            'cache_stats': self.response_cache.get_stats(),
            'cost_tracking': self.cost_tracker.copy(),
            'optimization_config': {
                'strategy': self.config.strategy.value,
                'caching_enabled': self.config.enable_caching,
                'batching_enabled': self.config.enable_request_batching,
                'quality_monitoring': self.config.enable_quality_monitoring
            }
        }


# Example usage and testing
if __name__ == "__main__":
    async def test_optimization():
        """Test AI model optimization system."""
        
        config = OptimizationConfig(
            strategy=OptimizationStrategy.BALANCED,
            enable_caching=True,
            enable_quality_monitoring=True
        )
        
        optimizer = AIModelOptimizer(config)
        
        # Test optimization
        test_prompt = "Analyze this smart home device and suggest optimizations"
        test_context = {
            'task_type': 'device_analysis',
            'device_type': 'smart_thermostat',
            'keywords': ['energy', 'efficiency', 'automation']
        }
        
        result = await optimizer.optimize_ai_request(test_prompt, test_context)
        
        print("Optimization Result:")
        print(f"Success: {result['success']}")
        print(f"Content: {result['content'][:100]}...")
        print(f"Metadata: {result['metadata']}")
        
        # Get stats
        stats = optimizer.get_optimization_stats()
        print(f"\nOptimization Stats: {stats}")
    
    # Run test
    asyncio.run(test_optimization())