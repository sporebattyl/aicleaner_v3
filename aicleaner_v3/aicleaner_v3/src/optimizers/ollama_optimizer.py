"""
Ollama Optimizer - Ollama-specific model optimization
Implements LRU memory management, quantization, and performance tuning
"""

import asyncio
import logging
import aiohttp
import json
from typing import Dict, Any, Optional, Callable, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..model_optimizer import ModelOptimizer, OptimizationType, OptimizationResult


@dataclass
class ModelInfo:
    name: str
    size_gb: float
    quantization: str
    last_used: datetime
    load_time: float
    is_loaded: bool = False


class OllamaOptimizer(ModelOptimizer):
    """
    Ollama-specific optimizer implementing:
    - LRU (Least Recently Used) model management
    - Dynamic quantization based on available resources
    - Smart model loading/unloading
    - Performance optimization for local models
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__("ollama", config)
        
        # Ollama-specific configuration
        self.ollama_base_url = config.get("base_url", "http://localhost:11434")
        self.max_memory_usage_gb = config.get("max_memory_gb", 8.0)
        self.model_idle_timeout = config.get("model_idle_timeout_minutes", 30)
        self.enable_auto_quantization = config.get("enable_auto_quantization", True)
        
        # Model management
        self.loaded_models: Dict[str, ModelInfo] = {}
        self.available_models: Dict[str, ModelInfo] = {}
        self.model_usage_stats: Dict[str, int] = {}  # Usage count
        
        # Quantization levels (best to worst quality)
        self.quantization_levels = [
            "q8_0",    # Best quality, largest size
            "q6_K",    # Good quality
            "q5_K_M",  # Balanced
            "q4_K_M",  # Good performance
            "q4_0",    # Fast inference
            "q3_K_M",  # Smaller size
            "q2_K"     # Smallest, fastest
        ]
        
        # Performance tracking
        self._model_performance: Dict[str, Dict[str, float]] = {}

    async def initialize(self) -> None:
        """Initialize the Ollama optimizer"""
        try:
            self.logger.info("Initializing Ollama optimizer")
            
            # Check Ollama availability
            if not await self._check_ollama_connection():
                raise ConnectionError("Cannot connect to Ollama service")
            
            # Discover available models
            await self._discover_models()
            
            # Start background tasks
            asyncio.create_task(self._model_management_loop())
            
            self.is_initialized = True
            self.logger.info(f"Ollama optimizer initialized with {len(self.available_models)} models")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama optimizer: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the Ollama optimizer"""
        self.logger.info("Shutting down Ollama optimizer")
        
        # Unload all models to free memory
        for model_name in list(self.loaded_models.keys()):
            await self._unload_model(model_name)
        
        self.is_initialized = False

    async def optimize(self, optimization_type: OptimizationType, 
                      progress_callback: Optional[Callable[[float], None]] = None) -> OptimizationResult:
        """Perform Ollama-specific optimization"""
        if not self.is_initialized:
            raise RuntimeError("Optimizer not initialized")
        
        start_time = datetime.now()
        
        try:
            if progress_callback:
                progress_callback(0.1)
            
            result = None
            
            if optimization_type == OptimizationType.QUANTIZATION:
                result = await self._optimize_quantization(progress_callback)
            elif optimization_type == OptimizationType.MEMORY:
                result = await self._optimize_memory(progress_callback)
            elif optimization_type == OptimizationType.PERFORMANCE:
                result = await self._optimize_performance(progress_callback)
            elif optimization_type == OptimizationType.AUTO:
                result = await self._optimize_auto(progress_callback)
            else:
                raise ValueError(f"Unsupported optimization type: {optimization_type}")
            
            if progress_callback:
                progress_callback(1.0)
            
            # Record result
            self._record_optimization_result(result)
            
            return result
            
        except Exception as e:
            error_result = OptimizationResult(
                success=False,
                optimization_type=optimization_type,
                performance_improvement=0.0,
                memory_savings=0.0,
                details={},
                timestamp=datetime.now(),
                error_message=str(e)
            )
            
            self._record_optimization_result(error_result)
            return error_result

    async def get_optimization_status(self) -> Dict[str, Any]:
        """Get current Ollama optimization status"""
        try:
            # Get memory usage
            total_memory_gb = sum(model.size_gb for model in self.loaded_models.values())
            memory_utilization = (total_memory_gb / self.max_memory_usage_gb) * 100
            
            # Get model statistics
            model_stats = {}
            for name, model in self.loaded_models.items():
                model_stats[name] = {
                    "size_gb": model.size_gb,
                    "quantization": model.quantization,
                    "last_used": model.last_used.isoformat(),
                    "usage_count": self.model_usage_stats.get(name, 0),
                    "is_loaded": model.is_loaded
                }
            
            return {
                "provider": self.provider_name,
                "memory_usage_gb": total_memory_gb,
                "memory_utilization_percent": memory_utilization,
                "max_memory_gb": self.max_memory_usage_gb,
                "loaded_models": len(self.loaded_models),
                "available_models": len(self.available_models),
                "model_stats": model_stats,
                "auto_quantization_enabled": self.enable_auto_quantization,
                "optimizations_applied": len(self.current_optimizations)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get optimization status: {e}")
            return {"error": str(e)}

    async def get_best_model_for_task(self, task_complexity: str, 
                                     max_response_time: float = 30.0) -> Optional[str]:
        """Get the best available model for a given task complexity"""
        try:
            # Ensure models are loaded based on usage and memory constraints
            await self._manage_model_loading()
            
            # Filter models by performance requirements
            suitable_models = []
            
            for name, model in self.available_models.items():
                # Get performance stats for this model
                perf_stats = self._model_performance.get(name, {})
                avg_response_time = perf_stats.get("avg_response_time", 15.0)
                
                # Check if model meets performance requirements
                if avg_response_time <= max_response_time:
                    suitable_models.append((name, model, avg_response_time))
            
            if not suitable_models:
                return None
            
            # Sort by performance and quantization quality
            suitable_models.sort(key=lambda x: (x[2], self._get_quantization_priority(x[1].quantization)))
            
            best_model_name = suitable_models[0][0]
            
            # Ensure the model is loaded
            await self._ensure_model_loaded(best_model_name)
            
            return best_model_name
            
        except Exception as e:
            self.logger.error(f"Failed to get best model for task: {e}")
            return None

    async def _optimize_quantization(self, progress_callback: Optional[Callable[[float], None]] = None) -> OptimizationResult:
        """Optimize model quantization based on available resources"""
        try:
            self.logger.info("Starting quantization optimization")
            
            if progress_callback:
                progress_callback(0.2)
            
            optimized_models = []
            total_memory_saved = 0.0
            
            # Get current memory pressure
            current_memory_gb = sum(model.size_gb for model in self.loaded_models.values())
            memory_pressure = current_memory_gb / self.max_memory_usage_gb
            
            if progress_callback:
                progress_callback(0.4)
            
            # Determine target quantization level based on memory pressure
            if memory_pressure > 0.9:
                target_quantization = "q3_K_M"  # Aggressive
            elif memory_pressure > 0.7:
                target_quantization = "q4_K_M"  # Balanced
            else:
                target_quantization = "q5_K_M"  # Conservative
            
            # Apply quantization to models that would benefit
            total_models = len(self.loaded_models)
            for i, (model_name, model) in enumerate(self.loaded_models.items()):
                if self._should_requantize_model(model, target_quantization):
                    original_size = model.size_gb
                    success = await self._requantize_model(model_name, target_quantization)
                    
                    if success:
                        new_size = await self._get_model_size(model_name)
                        memory_saved = original_size - new_size
                        total_memory_saved += memory_saved
                        optimized_models.append(model_name)
                        
                        self.logger.info(f"Requantized {model_name} to {target_quantization}, saved {memory_saved:.1f}GB")
                
                if progress_callback and total_models > 0:
                    progress_callback(0.4 + 0.5 * (i + 1) / total_models)
            
            # Calculate performance improvement (estimated)
            performance_improvement = min(25.0, len(optimized_models) * 5.0)
            
            return OptimizationResult(
                success=True,
                optimization_type=OptimizationType.QUANTIZATION,
                performance_improvement=performance_improvement,
                memory_savings=total_memory_saved * 1024,  # Convert to MB
                details={
                    "optimized_models": optimized_models,
                    "target_quantization": target_quantization,
                    "memory_pressure_before": memory_pressure,
                    "total_memory_saved_gb": total_memory_saved
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            raise Exception(f"Quantization optimization failed: {e}")

    async def _optimize_memory(self, progress_callback: Optional[Callable[[float], None]] = None) -> OptimizationResult:
        """Optimize memory usage through model management"""
        try:
            self.logger.info("Starting memory optimization")
            
            if progress_callback:
                progress_callback(0.2)
            
            memory_saved = 0.0
            unloaded_models = []
            
            # Get current memory usage
            current_memory = sum(model.size_gb for model in self.loaded_models.values())
            target_memory = self.max_memory_usage_gb * 0.7  # Target 70% utilization
            
            if progress_callback:
                progress_callback(0.4)
            
            if current_memory > target_memory:
                # Unload least recently used models
                models_by_usage = sorted(
                    self.loaded_models.items(),
                    key=lambda x: (x[1].last_used, self.model_usage_stats.get(x[0], 0))
                )
                
                for model_name, model in models_by_usage:
                    if current_memory - memory_saved <= target_memory:
                        break
                    
                    if await self._unload_model(model_name):
                        memory_saved += model.size_gb
                        unloaded_models.append(model_name)
                        self.logger.info(f"Unloaded {model_name} to save {model.size_gb:.1f}GB")
            
            if progress_callback:
                progress_callback(0.8)
            
            # Update current optimizations
            self.current_optimizations["memory_management"] = {
                "target_memory_gb": target_memory,
                "unloaded_models": unloaded_models
            }
            
            performance_improvement = min(20.0, len(unloaded_models) * 3.0)
            
            return OptimizationResult(
                success=True,
                optimization_type=OptimizationType.MEMORY,
                performance_improvement=performance_improvement,
                memory_savings=memory_saved * 1024,  # Convert to MB
                details={
                    "unloaded_models": unloaded_models,
                    "memory_saved_gb": memory_saved,
                    "target_memory_gb": target_memory,
                    "current_memory_gb": current_memory - memory_saved
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            raise Exception(f"Memory optimization failed: {e}")

    async def _optimize_performance(self, progress_callback: Optional[Callable[[float], None]] = None) -> OptimizationResult:
        """Optimize performance through model selection and caching"""
        try:
            self.logger.info("Starting performance optimization")
            
            if progress_callback:
                progress_callback(0.2)
            
            # Pre-load frequently used models
            frequent_models = sorted(
                self.model_usage_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]  # Top 3 most used models
            
            preloaded_models = []
            for model_name, usage_count in frequent_models:
                if model_name not in self.loaded_models and usage_count > 5:
                    if await self._ensure_model_loaded(model_name):
                        preloaded_models.append(model_name)
                        self.logger.info(f"Pre-loaded frequently used model: {model_name}")
            
            if progress_callback:
                progress_callback(0.6)
            
            # Optimize model configurations for performance
            optimized_configs = []
            for model_name in self.loaded_models:
                if await self._optimize_model_config_for_performance(model_name):
                    optimized_configs.append(model_name)
            
            if progress_callback:
                progress_callback(0.9)
            
            # Update current optimizations
            self.current_optimizations["performance"] = {
                "preloaded_models": preloaded_models,
                "optimized_configs": optimized_configs
            }
            
            # Estimate performance improvement
            performance_improvement = len(preloaded_models) * 8.0 + len(optimized_configs) * 3.0
            
            return OptimizationResult(
                success=True,
                optimization_type=OptimizationType.PERFORMANCE,
                performance_improvement=min(performance_improvement, 30.0),
                memory_savings=0.0,  # Performance optimization doesn't necessarily save memory
                details={
                    "preloaded_models": preloaded_models,
                    "optimized_configs": optimized_configs,
                    "frequent_model_stats": dict(frequent_models)
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            raise Exception(f"Performance optimization failed: {e}")

    async def _optimize_auto(self, progress_callback: Optional[Callable[[float], None]] = None) -> OptimizationResult:
        """Automatic optimization combining multiple strategies"""
        try:
            self.logger.info("Starting automatic optimization")
            
            # Determine current system state
            current_memory = sum(model.size_gb for model in self.loaded_models.values())
            memory_pressure = current_memory / self.max_memory_usage_gb
            
            total_performance_improvement = 0.0
            total_memory_savings = 0.0
            applied_optimizations = []
            
            # Step 1: Memory optimization if under pressure
            if memory_pressure > 0.8:
                if progress_callback:
                    progress_callback(0.2)
                
                memory_result = await self._optimize_memory(None)
                if memory_result.success:
                    total_memory_savings += memory_result.memory_savings
                    total_performance_improvement += memory_result.performance_improvement * 0.5
                    applied_optimizations.append("memory")
            
            # Step 2: Quantization optimization
            if progress_callback:
                progress_callback(0.5)
            
            quantization_result = await self._optimize_quantization(None)
            if quantization_result.success:
                total_memory_savings += quantization_result.memory_savings
                total_performance_improvement += quantization_result.performance_improvement * 0.7
                applied_optimizations.append("quantization")
            
            # Step 3: Performance optimization
            if progress_callback:
                progress_callback(0.8)
            
            performance_result = await self._optimize_performance(None)
            if performance_result.success:
                total_performance_improvement += performance_result.performance_improvement * 0.8
                applied_optimizations.append("performance")
            
            success = len(applied_optimizations) > 0
            
            return OptimizationResult(
                success=success,
                optimization_type=OptimizationType.AUTO,
                performance_improvement=min(total_performance_improvement, 50.0),
                memory_savings=total_memory_savings,
                details={
                    "applied_optimizations": applied_optimizations,
                    "memory_pressure_before": memory_pressure,
                    "total_steps": len(applied_optimizations)
                },
                timestamp=datetime.now(),
                error_message=None if success else "No optimizations could be applied"
            )
            
        except Exception as e:
            raise Exception(f"Auto optimization failed: {e}")

    # Helper methods

    async def _check_ollama_connection(self) -> bool:
        """Check if Ollama service is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_base_url}/api/version", timeout=5) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"Cannot connect to Ollama: {e}")
            return False

    async def _discover_models(self) -> None:
        """Discover available Ollama models"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for model_data in data.get("models", []):
                            name = model_data.get("name", "")
                            size_bytes = model_data.get("size", 0)
                            size_gb = size_bytes / (1024 ** 3)
                            
                            # Extract quantization from model name
                            quantization = "q4_0"  # Default
                            for quant in self.quantization_levels:
                                if quant in name.lower():
                                    quantization = quant
                                    break
                            
                            model_info = ModelInfo(
                                name=name,
                                size_gb=size_gb,
                                quantization=quantization,
                                last_used=datetime.now() - timedelta(days=1),  # Default to yesterday
                                load_time=5.0,  # Default estimate
                                is_loaded=False
                            )
                            
                            self.available_models[name] = model_info
        
        except Exception as e:
            self.logger.error(f"Failed to discover Ollama models: {e}")

    async def _ensure_model_loaded(self, model_name: str) -> bool:
        """Ensure a model is loaded into memory"""
        if model_name in self.loaded_models:
            # Update last used time
            self.loaded_models[model_name].last_used = datetime.now()
            return True
        
        # Check memory constraints
        if model_name not in self.available_models:
            return False
        
        model_info = self.available_models[model_name]
        current_memory = sum(m.size_gb for m in self.loaded_models.values())
        
        if current_memory + model_info.size_gb > self.max_memory_usage_gb:
            # Need to free up memory first
            await self._free_memory_for_model(model_info.size_gb)
        
        # Load the model
        try:
            async with aiohttp.ClientSession() as session:
                load_data = {"name": model_name, "keep_alive": "5m"}
                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=load_data,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        model_info.is_loaded = True
                        model_info.last_used = datetime.now()
                        self.loaded_models[model_name] = model_info
                        self.model_usage_stats[model_name] = self.model_usage_stats.get(model_name, 0) + 1
                        return True
                    
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
        
        return False

    async def _unload_model(self, model_name: str) -> bool:
        """Unload a model from memory"""
        try:
            if model_name not in self.loaded_models:
                return True
            
            # Tell Ollama to unload the model
            async with aiohttp.ClientSession() as session:
                unload_data = {"name": model_name, "keep_alive": 0}
                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=unload_data,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        self.loaded_models[model_name].is_loaded = False
                        del self.loaded_models[model_name]
                        return True
                        
        except Exception as e:
            self.logger.error(f"Failed to unload model {model_name}: {e}")
        
        return False

    async def _manage_model_loading(self) -> None:
        """Manage model loading based on usage patterns and memory constraints"""
        # This is called periodically to optimize memory usage
        current_time = datetime.now()
        idle_threshold = timedelta(minutes=self.model_idle_timeout)
        
        # Unload idle models
        idle_models = []
        for model_name, model in self.loaded_models.items():
            if current_time - model.last_used > idle_threshold:
                idle_models.append(model_name)
        
        for model_name in idle_models:
            await self._unload_model(model_name)
            self.logger.info(f"Unloaded idle model: {model_name}")

    async def _model_management_loop(self) -> None:
        """Background task for model management"""
        while self.is_initialized:
            try:
                await self._manage_model_loading()
                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                self.logger.error(f"Model management loop error: {e}")
                await asyncio.sleep(60)

    def _should_requantize_model(self, model: ModelInfo, target_quantization: str) -> bool:
        """Check if a model should be requantized"""
        current_priority = self._get_quantization_priority(model.quantization)
        target_priority = self._get_quantization_priority(target_quantization)
        
        # Only requantize to a more aggressive (smaller) quantization
        return target_priority > current_priority

    def _get_quantization_priority(self, quantization: str) -> int:
        """Get priority of quantization level (higher = more aggressive)"""
        try:
            return self.quantization_levels.index(quantization)
        except ValueError:
            return 0

    async def _requantize_model(self, model_name: str, target_quantization: str) -> bool:
        """Requantize a model (simplified implementation)"""
        # This would involve more complex logic to actually requantize models
        # For now, just simulate the process
        self.logger.info(f"Simulating requantization of {model_name} to {target_quantization}")
        
        # Update model info
        if model_name in self.loaded_models:
            self.loaded_models[model_name].quantization = target_quantization
            # Simulate size reduction
            self.loaded_models[model_name].size_gb *= 0.7
        
        return True

    async def _get_model_size(self, model_name: str) -> float:
        """Get current size of a model"""
        if model_name in self.loaded_models:
            return self.loaded_models[model_name].size_gb
        elif model_name in self.available_models:
            return self.available_models[model_name].size_gb
        return 0.0

    async def _optimize_model_config_for_performance(self, model_name: str) -> bool:
        """Optimize model configuration for better performance"""
        # Placeholder for performance configuration optimization
        self.logger.debug(f"Optimizing performance config for {model_name}")
        return True

    async def _free_memory_for_model(self, required_memory_gb: float) -> None:
        """Free up memory to load a new model"""
        current_memory = sum(model.size_gb for model in self.loaded_models.values())
        available_memory = self.max_memory_usage_gb - current_memory
        
        if available_memory >= required_memory_gb:
            return
        
        memory_to_free = required_memory_gb - available_memory
        
        # Sort models by least recently used
        models_by_lru = sorted(
            self.loaded_models.items(),
            key=lambda x: x[1].last_used
        )
        
        freed_memory = 0.0
        for model_name, model in models_by_lru:
            if freed_memory >= memory_to_free:
                break
            
            if await self._unload_model(model_name):
                freed_memory += model.size_gb
                self.logger.info(f"Freed {model.size_gb:.1f}GB by unloading {model_name}")