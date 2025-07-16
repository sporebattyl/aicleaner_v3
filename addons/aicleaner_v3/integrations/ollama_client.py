"""
Ollama client for AI Cleaner addon.
Handles communication with local Ollama server for LLM inference.
Supports vision models (LLaVA) and text models (Mistral, Llama2).
"""

import os
import logging
import asyncio
import time
import json
import base64
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

try:
    import ollama
    from ollama import AsyncClient, Client
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class OptimizationOptions:
    """Options for model optimization during inference."""
    quantization_level: str = "auto"  # auto, fp16, int8, int4
    use_gpu: bool = False
    context_length: int = 2048
    batch_size: int = 1
    temperature: float = 0.1
    top_p: float = 0.9
    num_predict: int = 512
    repeat_penalty: float = 1.1
    seed: Optional[int] = None


class ModelOptimizer:
    """Handles model optimization for Ollama inference."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._gpu_available = self._detect_gpu()

    def _detect_gpu(self) -> bool:
        """Detect if GPU acceleration is available."""
        try:
            if TORCH_AVAILABLE:
                return torch.cuda.is_available()
            return False
        except Exception:
            return False

    def get_optimized_options(self, model_name: str, optimization_options: OptimizationOptions) -> Dict[str, Any]:
        """Get optimized inference options for a model."""
        options = {
            "temperature": optimization_options.temperature,
            "top_p": optimization_options.top_p,
            "num_predict": optimization_options.num_predict,
            "repeat_penalty": optimization_options.repeat_penalty
        }

        # Add seed if specified
        if optimization_options.seed is not None:
            options["seed"] = optimization_options.seed

        # GPU optimization
        if optimization_options.use_gpu and self._gpu_available:
            options["num_gpu"] = 1
            options["gpu_layers"] = -1  # Use all GPU layers
        else:
            options["num_gpu"] = 0

        # Context length optimization
        if "llava" in model_name.lower():
            # Vision models typically need more context
            options["num_ctx"] = min(optimization_options.context_length, 4096)
        else:
            # Text models can use smaller context for efficiency
            options["num_ctx"] = min(optimization_options.context_length, 2048)

        # Quantization hints (Ollama handles this internally)
        if optimization_options.quantization_level != "auto":
            options["quantization"] = optimization_options.quantization_level

        return options


class OllamaClient:
    """
    Ollama client for local LLM inference with automatic model management.
    
    Features:
    - Vision analysis using LLaVA models
    - Text generation using Mistral/Llama2 models
    - Automatic model downloading and management
    - Health checks and fallback handling
    - Resource monitoring and optimization
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Ollama client.
        
        Args:
            config: Configuration dictionary with Ollama settings
        """
        self.logger = logging.getLogger(__name__)
        self.config = config.get("local_llm", {})
        
        # Ollama server configuration
        self.host = self.config.get("ollama_host", "localhost:11434")
        self.enabled = self.config.get("enabled", False)
        
        # Model preferences
        self.preferred_models = self.config.get("preferred_models", {
            "vision": "llava:13b",
            "text": "mistral:7b", 
            "task_generation": "mistral:7b",
            "fallback": "llama2:7b"
        })
        
        # Resource limits
        self.resource_limits = self.config.get("resource_limits", {
            "max_cpu_usage": 80,
            "max_memory_usage": 4096,  # MB
        })
        
        # Performance tuning
        self.performance_tuning = self.config.get("performance_tuning", {
            "quantization_level": 4,  # 4-bit quantization
            "batch_size": 1,
            "timeout_seconds": 120
        })
        
        # Auto-download and concurrency settings
        self.auto_download = self.config.get("auto_download", True)
        self.max_concurrent = self.config.get("max_concurrent", 1)
        
        # Initialize clients
        self.client = None
        self.async_client = None
        self._available_models = set()
        self._model_status = {}

        # Initialize optimizer
        self.optimizer = ModelOptimizer()

        # Performance tracking
        self._inference_cache = {}
        self._performance_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "average_response_time": 0.0,
            "gpu_usage_count": 0
        }
        
    async def initialize(self):
        """Initialize the Ollama client and check availability."""
        self.logger.info("Initializing Ollama client")
        
        if not OLLAMA_AVAILABLE:
            self.logger.error("Ollama package not available. Install with: pip install ollama")
            return False
            
        if not self.enabled:
            self.logger.info("Ollama client disabled in configuration")
            return False
            
        try:
            # Initialize clients
            self.client = Client(host=f"http://{self.host}")
            self.async_client = AsyncClient(host=f"http://{self.host}")
            
            # Check server availability
            if not await self._check_server_health():
                self.logger.error(f"Ollama server not available at {self.host}")
                return False
                
            # Update available models
            await self._update_available_models()
            
            # Auto-download preferred models if enabled
            if self.auto_download:
                await self._ensure_preferred_models()
                
            self.logger.info(f"Ollama client initialized successfully with {len(self._available_models)} models")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Ollama client: {e}")
            return False
    
    async def analyze_image_local(self, image_path: str, model: str = None, prompt: str = None,
                                 optimization_options: OptimizationOptions = None) -> Dict[str, Any]:
        """
        Analyze image using local vision model with optimization.

        Args:
            image_path: Path to image file
            model: Model to use (defaults to preferred vision model)
            prompt: Custom prompt for analysis
            optimization_options: Options for model optimization

        Returns:
            Dictionary with analysis results
        """
        if not self.async_client:
            raise Exception("Ollama client not initialized")
            
        # Use preferred vision model if not specified
        if not model:
            model = self.preferred_models.get("vision", "llava:13b")

        # Set default optimization options
        if optimization_options is None:
            optimization_options = OptimizationOptions(
                use_gpu=self.optimizer._gpu_available,
                quantization_level="auto"
            )

        # Check if model is available
        if not await self.check_model_availability(model):
            if self.auto_download:
                self.logger.info(f"Downloading model {model}")
                if not await self.download_model(model):
                    raise Exception(f"Failed to download model {model}")
            else:
                raise Exception(f"Model {model} not available")

        # Check cache for similar requests
        cache_key = self._generate_cache_key(image_path, model, prompt)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self._performance_stats["cache_hits"] += 1
            self.logger.debug(f"Cache hit for image analysis with {model}")
            return cached_result
        
        # Default prompt for cleaning analysis
        if not prompt:
            prompt = """Analyze this image for cleaning tasks. Identify:
1. Objects that need cleaning or organizing
2. Areas that appear dirty or cluttered
3. Safety or hygiene concerns
4. Specific cleaning actions needed

Provide a detailed analysis focusing on cleanliness and organization."""
        
        try:
            # Read and encode image
            image_data = await self._read_image_file(image_path)

            # Get optimized inference options
            inference_options = self.optimizer.get_optimized_options(model, optimization_options)

            # Prepare messages for vision model
            messages = [{
                'role': 'user',
                'content': prompt,
                'images': [image_data]
            }]

            # Track performance
            self._performance_stats["total_requests"] += 1
            if optimization_options.use_gpu and self.optimizer._gpu_available:
                self._performance_stats["gpu_usage_count"] += 1

            # Generate response with timeout and optimization
            start_time = time.time()
            response = await asyncio.wait_for(
                self.async_client.chat(
                    model=model,
                    messages=messages,
                    options=inference_options
                ),
                timeout=self.performance_tuning.get("timeout_seconds", 120)
            )
            
            analysis_time = time.time() - start_time

            # Update performance stats
            self._update_performance_stats(analysis_time)

            # Extract and structure response
            result = {
                "text": response['message']['content'],
                "model": model,
                "provider": "ollama",
                "prompt": prompt,
                "timestamp": time.time(),
                "analysis_time": analysis_time,
                "confidence": self._estimate_confidence(response['message']['content']),
                "optimization_used": {
                    "quantization_level": optimization_options.quantization_level,
                    "gpu_acceleration": optimization_options.use_gpu and self.optimizer._gpu_available,
                    "context_length": optimization_options.context_length
                }
            }

            # Cache the result
            self._cache_result(cache_key, result)

            self.logger.debug(f"Image analysis completed in {analysis_time:.2f}s using {model} with optimization")
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout analyzing image with model {model}")
            raise Exception(f"Analysis timeout after {self.performance_tuning.get('timeout_seconds', 120)}s")
        except Exception as e:
            self.logger.error(f"Error analyzing image with model {model}: {e}")
            raise
    
    async def generate_tasks_local(self, analysis: str, context: Dict[str, Any],
                                  optimization_options: OptimizationOptions = None) -> List[Dict[str, Any]]:
        """
        Generate cleaning tasks using local text model.
        
        Args:
            analysis: Image analysis text
            context: Context information (zone, purpose, etc.)
            
        Returns:
            List of generated tasks
        """
        if not self.async_client:
            raise Exception("Ollama client not initialized")
            
        # Use preferred task generation model
        model = self.preferred_models.get("task_generation", "mistral:7b")

        # Set default optimization options
        if optimization_options is None:
            optimization_options = OptimizationOptions(
                use_gpu=self.optimizer._gpu_available,
                quantization_level="auto",
                context_length=1024,  # Smaller context for task generation
                num_predict=256  # Shorter responses for tasks
            )

        # Check model availability
        if not await self.check_model_availability(model):
            if self.auto_download:
                if not await self.download_model(model):
                    raise Exception(f"Failed to download model {model}")
            else:
                raise Exception(f"Model {model} not available")

        # Check cache for similar requests
        cache_key = self._generate_cache_key(analysis, model, str(context))
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self._performance_stats["cache_hits"] += 1
            self.logger.debug(f"Cache hit for task generation with {model}")
            return cached_result
        
        # Build context-aware prompt
        zone_name = context.get("zone_name", "unknown")
        zone_purpose = context.get("zone_purpose", "general")
        
        prompt = f"""Based on this image analysis of a {zone_purpose} area called "{zone_name}":

{analysis}

Generate 3-5 specific, actionable cleaning tasks. Each task should be:
- Specific and clear
- Appropriate for the {zone_purpose} area
- Prioritized by safety/hygiene first, then aesthetics
- Realistic and achievable

Format as JSON array with objects containing:
- "task": task description
- "priority": "high", "medium", or "low"
- "category": "safety", "hygiene", or "aesthetics"
- "estimated_time": time in minutes

Example format:
[
  {{"task": "Clean spilled liquid on counter", "priority": "high", "category": "hygiene", "estimated_time": 5}},
  {{"task": "Organize items on shelf", "priority": "medium", "category": "aesthetics", "estimated_time": 10}}
]"""

        try:
            # Get optimized inference options
            inference_options = self.optimizer.get_optimized_options(model, optimization_options)

            messages = [{
                'role': 'user',
                'content': prompt
            }]

            # Track performance
            self._performance_stats["total_requests"] += 1
            if optimization_options.use_gpu and self.optimizer._gpu_available:
                self._performance_stats["gpu_usage_count"] += 1

            start_time = time.time()
            response = await asyncio.wait_for(
                self.async_client.chat(
                    model=model,
                    messages=messages,
                    options=inference_options
                ),
                timeout=self.performance_tuning.get("timeout_seconds", 120)
            )
            
            generation_time = time.time() - start_time

            # Update performance stats
            self._update_performance_stats(generation_time)

            # Parse JSON response
            tasks = self._parse_task_response(response['message']['content'])

            # Add optimization metadata to tasks
            for task in tasks:
                task["optimization_used"] = {
                    "quantization_level": optimization_options.quantization_level,
                    "gpu_acceleration": optimization_options.use_gpu and self.optimizer._gpu_available,
                    "generation_time": generation_time
                }

            # Cache the result
            self._cache_result(cache_key, tasks)

            self.logger.debug(f"Generated {len(tasks)} tasks in {generation_time:.2f}s using {model} with optimization")
            return tasks
            
        except Exception as e:
            self.logger.error(f"Error generating tasks with model {model}: {e}")
            raise
    
    async def check_model_availability(self, model: str) -> bool:
        """Check if a model is available locally."""
        try:
            if not self.client:
                return False
                
            # Check if model is in our cached list
            if model in self._available_models:
                return True
                
            # Refresh available models and check again
            await self._update_available_models()
            return model in self._available_models
            
        except Exception as e:
            self.logger.error(f"Error checking model availability for {model}: {e}")
            return False
    
    async def download_model(self, model: str) -> bool:
        """Download a model if auto-download is enabled."""
        if not self.auto_download:
            self.logger.warning(f"Auto-download disabled, cannot download {model}")
            return False
            
        try:
            self.logger.info(f"Starting download of model {model}")
            
            # Use sync client for pull operation
            self.client.pull(model)
            
            # Update available models
            await self._update_available_models()
            
            # Verify download
            if model in self._available_models:
                self.logger.info(f"Successfully downloaded model {model}")
                return True
            else:
                self.logger.error(f"Model {model} not found after download")
                return False
                
        except Exception as e:
            self.logger.error(f"Error downloading model {model}: {e}")
            return False
    
    async def _check_server_health(self) -> bool:
        """Check if Ollama server is running and accessible."""
        try:
            # Try to list models as a health check
            models = self.client.list()
            return True
        except Exception as e:
            self.logger.error(f"Ollama server health check failed: {e}")
            return False
    
    async def _update_available_models(self):
        """Update the list of available models."""
        try:
            models_response = self.client.list()
            self._available_models = {model['name'] for model in models_response['models']}
            self.logger.debug(f"Updated available models: {self._available_models}")
        except Exception as e:
            self.logger.error(f"Error updating available models: {e}")
            self._available_models = set()
    
    async def _ensure_preferred_models(self):
        """Ensure preferred models are available, download if needed."""
        for model_type, model_name in self.preferred_models.items():
            if model_type == "fallback":  # Skip fallback model for auto-download
                continue
                
            if not await self.check_model_availability(model_name):
                self.logger.info(f"Preferred {model_type} model {model_name} not available, downloading...")
                await self.download_model(model_name)
    
    async def _read_image_file(self, image_path: str) -> bytes:
        """Read and return image file as bytes."""
        try:
            with open(image_path, 'rb') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading image file {image_path}: {e}")
            raise
    
    def _estimate_confidence(self, response_text: str) -> float:
        """Estimate confidence score based on response characteristics."""
        # Simple heuristic based on response length and specificity
        if not response_text:
            return 0.0
            
        # Longer, more detailed responses generally indicate higher confidence
        length_score = min(len(response_text) / 500, 1.0)  # Normalize to 0-1
        
        # Check for uncertainty indicators
        uncertainty_words = ['maybe', 'possibly', 'might', 'unclear', 'uncertain', 'not sure']
        uncertainty_count = sum(1 for word in uncertainty_words if word in response_text.lower())
        uncertainty_penalty = uncertainty_count * 0.1
        
        confidence = max(0.1, length_score - uncertainty_penalty)
        return min(confidence, 1.0)
    
    def _parse_task_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse task generation response into structured format."""
        try:
            # Try to extract JSON from response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                tasks = json.loads(json_str)
                
                # Validate task structure
                validated_tasks = []
                for task in tasks:
                    if isinstance(task, dict) and 'task' in task:
                        validated_task = {
                            'task': task.get('task', ''),
                            'priority': task.get('priority', 'medium'),
                            'category': task.get('category', 'aesthetics'),
                            'estimated_time': task.get('estimated_time', 10)
                        }
                        validated_tasks.append(validated_task)
                
                return validated_tasks
            else:
                # Fallback: create simple task from response
                return [{
                    'task': response_text[:100] + '...' if len(response_text) > 100 else response_text,
                    'priority': 'medium',
                    'category': 'aesthetics',
                    'estimated_time': 10
                }]
                
        except Exception as e:
            self.logger.error(f"Error parsing task response: {e}")
            # Return fallback task
            return [{
                'task': 'Review and clean the area based on analysis',
                'priority': 'medium',
                'category': 'aesthetics',
                'estimated_time': 15
            }]

    def _generate_cache_key(self, *args) -> str:
        """Generate a cache key from arguments."""
        key_data = "|".join(str(arg) for arg in args)
        return hashlib.md5(key_data.encode()).hexdigest()[:16]

    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if available and not expired."""
        try:
            if cache_key in self._inference_cache:
                cached_item = self._inference_cache[cache_key]
                # Check if cache is still valid (5 minutes TTL)
                if time.time() - cached_item["timestamp"] < 300:
                    return cached_item["result"]
                else:
                    # Remove expired cache entry
                    del self._inference_cache[cache_key]
            return None
        except Exception as e:
            self.logger.debug(f"Error getting cached result: {e}")
            return None

    def _cache_result(self, cache_key: str, result: Any):
        """Cache a result with timestamp."""
        try:
            # Limit cache size to prevent memory issues
            if len(self._inference_cache) > 100:
                # Remove oldest entries
                oldest_keys = sorted(
                    self._inference_cache.keys(),
                    key=lambda k: self._inference_cache[k]["timestamp"]
                )[:20]
                for key in oldest_keys:
                    del self._inference_cache[key]

            self._inference_cache[cache_key] = {
                "result": result,
                "timestamp": time.time()
            }
        except Exception as e:
            self.logger.debug(f"Error caching result: {e}")

    def _update_performance_stats(self, response_time: float):
        """Update performance statistics."""
        try:
            # Update average response time using exponential moving average
            alpha = 0.1  # Smoothing factor
            if self._performance_stats["average_response_time"] == 0:
                self._performance_stats["average_response_time"] = response_time
            else:
                self._performance_stats["average_response_time"] = (
                    alpha * response_time +
                    (1 - alpha) * self._performance_stats["average_response_time"]
                )
        except Exception as e:
            self.logger.debug(f"Error updating performance stats: {e}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        total_requests = self._performance_stats["total_requests"]
        cache_hit_rate = (
            self._performance_stats["cache_hits"] / total_requests
            if total_requests > 0 else 0
        )
        gpu_usage_rate = (
            self._performance_stats["gpu_usage_count"] / total_requests
            if total_requests > 0 else 0
        )

        return {
            "total_requests": total_requests,
            "cache_hits": self._performance_stats["cache_hits"],
            "cache_hit_rate": cache_hit_rate,
            "average_response_time": self._performance_stats["average_response_time"],
            "gpu_usage_rate": gpu_usage_rate,
            "gpu_available": self.optimizer._gpu_available,
            "cached_results": len(self._inference_cache)
        }

    def clear_cache(self):
        """Clear the inference cache."""
        self._inference_cache.clear()
        self.logger.info("Inference cache cleared")

    def reset_performance_stats(self):
        """Reset performance statistics."""
        self._performance_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "average_response_time": 0.0,
            "gpu_usage_count": 0
        }
        self.logger.info("Performance statistics reset")
