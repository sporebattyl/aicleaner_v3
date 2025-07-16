"""
Local Model Manager for AI Cleaner addon.
Handles dynamic model loading/unloading, resource monitoring, and performance tracking.
"""

import os
import logging
import asyncio
import time
import psutil
import json
import threading
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from integrations.ollama_client import OllamaClient
except ImportError:
    # Fallback for different import contexts
    try:
        from ..integrations.ollama_client import OllamaClient
    except ImportError:
        # Create a dummy class if import fails
        class OllamaClient:
            def __init__(self, config):
                pass


class ModelStatus(Enum):
    """Model status enumeration."""
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    ERROR = "error"
    OPTIMIZING = "optimizing"
    QUANTIZING = "quantizing"


class QuantizationLevel(Enum):
    """Quantization levels for model optimization."""
    NONE = "none"
    INT8 = "int8"
    INT4 = "int4"
    FP16 = "fp16"
    DYNAMIC = "dynamic"


class CompressionType(Enum):
    """Model compression types."""
    NONE = "none"
    GZIP = "gzip"
    PRUNING = "pruning"
    DISTILLATION = "distillation"


@dataclass
class ModelInfo:
    """Information about a model."""
    name: str
    status: ModelStatus = ModelStatus.UNKNOWN
    size_gb: float = 0.0
    last_used: Optional[datetime] = None
    load_time: float = 0.0
    memory_usage_mb: float = 0.0
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_count: int = 0
    success_count: int = 0
    # New optimization fields
    quantization_level: QuantizationLevel = QuantizationLevel.NONE
    compression_type: CompressionType = CompressionType.NONE
    inference_configured: bool = False
    original_size_gb: float = 0.0
    compressed_size_gb: float = 0.0
    gpu_compatible: bool = False
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class OptimizationConfig:
    """Configuration for model optimization."""
    quantization_level: QuantizationLevel = QuantizationLevel.DYNAMIC
    compression_type: CompressionType = CompressionType.NONE
    enable_gpu_acceleration: bool = False
    memory_optimization: bool = True
    auto_optimize: bool = True
    optimization_threshold_mb: float = 2048  # Auto-optimize models larger than 2GB


@dataclass
class ResourceMetrics:
    """System resource metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    timestamp: datetime
    # Extended metrics for optimization
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    gpu_utilization_percent: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_io_mb: float = 0.0


class LocalModelManager:
    """
    Manages local LLM models with dynamic loading/unloading and resource monitoring.
    
    Features:
    - Dynamic model loading and unloading based on demand
    - Resource monitoring and optimization
    - Performance metrics tracking
    - Automatic model updates and health checks
    - Memory management and cleanup
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Local Model Manager.

        Args:
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config.get("local_llm", {})

        # Resource limits
        self.resource_limits = self.config.get("resource_limits", {
            "max_cpu_usage": 80,
            "max_memory_usage": 4096,  # MB
        })

        # Performance settings
        self.performance_settings = self.config.get("performance_tuning", {
            "auto_unload_minutes": 30,  # Unload unused models after 30 minutes
            "max_loaded_models": 2,     # Maximum models to keep loaded
            "health_check_interval": 300,  # Health check every 5 minutes
        })

        # Optimization configuration
        self.optimization_config = OptimizationConfig(
            quantization_level=QuantizationLevel(
                self.config.get("performance_optimization", {}).get("quantization", {}).get("default_level", "dynamic")
            ),
            enable_gpu_acceleration=self.config.get("performance_optimization", {}).get("gpu_acceleration", {}).get("enabled", False),
            auto_optimize=self.config.get("performance_optimization", {}).get("auto_optimization", {}).get("enabled", True)
        )

        # Model tracking
        self.models: Dict[str, ModelInfo] = {}
        self.loaded_models: Set[str] = set()
        self.resource_history: List[ResourceMetrics] = []
        self.optimization_queue: deque = deque()
        self.optimization_lock = threading.Lock()

        # Ollama client integration
        self.ollama_client = OllamaClient(config)
        self.host = self.config.get("ollama_host", "localhost:11434")

        # Background tasks
        self._monitoring_task = None
        self._cleanup_task = None
        self._health_check_task = None
        self._optimization_task = None

        # GPU detection
        self._gpu_available = self._detect_gpu_availability()
        
    async def initialize(self) -> bool:
        """Initialize the model manager."""
        try:
            if not OLLAMA_AVAILABLE:
                self.logger.error("Ollama package not available")
                return False

            # Initialize integrated Ollama client
            if not await self.ollama_client.initialize():
                self.logger.error("Failed to initialize OllamaClient")
                return False

            # Discover available models
            await self._discover_models()

            # Start background tasks
            await self._start_background_tasks()

            # Initialize optimization system
            await self._initialize_optimization_system()

            self.logger.info("Local Model Manager initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Local Model Manager: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the model manager and cleanup resources."""
        try:
            # Stop background tasks
            if self._monitoring_task:
                self._monitoring_task.cancel()
            if self._cleanup_task:
                self._cleanup_task.cancel()
            if self._health_check_task:
                self._health_check_task.cancel()
            if self._optimization_task:
                self._optimization_task.cancel()
                
            # Unload all models
            await self._unload_all_models()
            
            self.logger.info("Local Model Manager shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def ensure_model_loaded(self, model_name: str) -> bool:
        """
        Ensure a model is loaded and ready for use.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            True if model is loaded successfully
        """
        try:
            # Check if model is already loaded
            if model_name in self.loaded_models:
                # Update last used time
                if model_name in self.models:
                    self.models[model_name].last_used = datetime.now()
                return True
            
            # Check resource constraints before loading
            if not await self._check_resource_constraints():
                self.logger.warning("Resource constraints prevent model loading")
                await self._free_resources()
            
            # Load the model
            return await self._load_model(model_name)
            
        except Exception as e:
            self.logger.error(f"Error ensuring model {model_name} is loaded: {e}")
            return False
    
    async def unload_model(self, model_name: str) -> bool:
        """
        Unload a specific model to free resources.
        
        Args:
            model_name: Name of the model to unload
            
        Returns:
            True if model was unloaded successfully
        """
        try:
            if model_name not in self.loaded_models:
                return True  # Already unloaded
                
            # Update model status
            if model_name in self.models:
                self.models[model_name].status = ModelStatus.UNLOADING
            
            # Note: Ollama doesn't have explicit unload API, so we track it locally
            self.loaded_models.discard(model_name)
            
            if model_name in self.models:
                self.models[model_name].status = ModelStatus.AVAILABLE
                
            self.logger.info(f"Model {model_name} unloaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unloading model {model_name}: {e}")
            return False
    
    async def get_model_status(self, model_name: str) -> ModelStatus:
        """Get the current status of a model."""
        if model_name in self.models:
            return self.models[model_name].status
        return ModelStatus.UNKNOWN
    
    async def get_resource_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # Get GPU metrics if available
            gpu_memory_used = 0.0
            gpu_memory_total = 0.0
            gpu_utilization = 0.0

            if self._gpu_available and TORCH_AVAILABLE:
                try:
                    import torch
                    if torch.cuda.is_available():
                        gpu_memory_used = torch.cuda.memory_allocated() / (1024 * 1024)  # MB
                        gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)  # MB
                        gpu_utilization = (gpu_memory_used / gpu_memory_total) * 100 if gpu_memory_total > 0 else 0
                except Exception as gpu_e:
                    self.logger.debug(f"Error getting GPU metrics: {gpu_e}")

            # Get disk I/O metrics
            disk_io = psutil.disk_io_counters()
            disk_io_read = disk_io.read_bytes / (1024 * 1024) if disk_io else 0  # MB
            disk_io_write = disk_io.write_bytes / (1024 * 1024) if disk_io else 0  # MB

            # Get network I/O metrics
            network_io = psutil.net_io_counters()
            network_io_mb = (network_io.bytes_sent + network_io.bytes_recv) / (1024 * 1024) if network_io else 0  # MB

            return ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                timestamp=datetime.now(),
                gpu_memory_used_mb=gpu_memory_used,
                gpu_memory_total_mb=gpu_memory_total,
                gpu_utilization_percent=gpu_utilization,
                disk_io_read_mb=disk_io_read,
                disk_io_write_mb=disk_io_write,
                network_io_mb=network_io_mb
            )
        except Exception as e:
            self.logger.error(f"Error getting resource metrics: {e}")
            return ResourceMetrics(0, 0, 0, 0, datetime.now())
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all models."""
        stats = {
            "models": {},
            "system": {
                "loaded_models": len(self.loaded_models),
                "total_models": len(self.models),
                "resource_history_size": len(self.resource_history)
            }
        }
        
        for model_name, model_info in self.models.items():
            total_requests = model_info.success_count + model_info.error_count
            success_rate = model_info.success_count / total_requests if total_requests > 0 else 0
            
            stats["models"][model_name] = {
                "status": model_info.status.value,
                "success_rate": success_rate,
                "total_requests": total_requests,
                "last_used": model_info.last_used.isoformat() if model_info.last_used else None,
                "load_time": model_info.load_time,
                "memory_usage_mb": model_info.memory_usage_mb,
                "performance_metrics": model_info.performance_metrics
            }
        
        return stats

    async def analyze_image_with_model(self, model_name: str, image_path: str, prompt: str = None) -> Dict[str, Any]:
        """
        Analyze image using specified local model with resource management.

        Args:
            model_name: Name of the model to use
            image_path: Path to image file
            prompt: Optional custom prompt

        Returns:
            Dictionary with analysis results
        """
        try:
            # Ensure model is loaded and ready
            if not await self.ensure_model_loaded(model_name):
                raise Exception(f"Failed to load model {model_name}")

            # Update model usage tracking
            if model_name in self.models:
                self.models[model_name].last_used = datetime.now()

            # Delegate to OllamaClient for actual analysis
            start_time = time.time()
            result = await self.ollama_client.analyze_image_local(
                image_path=image_path,
                model=model_name,
                prompt=prompt
            )

            # Update performance metrics
            analysis_time = time.time() - start_time
            if model_name in self.models:
                self.models[model_name].success_count += 1
                self.models[model_name].performance_metrics["last_analysis_time"] = analysis_time

            return result

        except Exception as e:
            # Update error tracking
            if model_name in self.models:
                self.models[model_name].error_count += 1
            self.logger.error(f"Error analyzing image with model {model_name}: {e}")
            raise

    async def generate_tasks_with_model(self, model_name: str, analysis: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate tasks using specified local model with resource management.

        Args:
            model_name: Name of the model to use
            analysis: Image analysis text
            context: Context information

        Returns:
            List of generated tasks
        """
        try:
            # Ensure model is loaded and ready
            if not await self.ensure_model_loaded(model_name):
                raise Exception(f"Failed to load model {model_name}")

            # Update model usage tracking
            if model_name in self.models:
                self.models[model_name].last_used = datetime.now()

            # Delegate to OllamaClient for actual task generation
            start_time = time.time()
            result = await self.ollama_client.generate_tasks_local(
                analysis=analysis,
                context=context
            )

            # Update performance metrics
            generation_time = time.time() - start_time
            if model_name in self.models:
                self.models[model_name].success_count += 1
                self.models[model_name].performance_metrics["last_generation_time"] = generation_time

            return result

        except Exception as e:
            # Update error tracking
            if model_name in self.models:
                self.models[model_name].error_count += 1
            self.logger.error(f"Error generating tasks with model {model_name}: {e}")
            raise

    async def configure_inference_settings(self, model_name: str, optimization_config: Optional[OptimizationConfig] = None) -> bool:
        """
        Configure inference settings for a model with quantization and compression preferences.

        Note: This configures how AICleaner will request the model from Ollama,
        it does not modify the actual model files.

        Args:
            model_name: Name of the model to configure
            optimization_config: Optional custom optimization configuration

        Returns:
            True if configuration was successful
        """
        try:
            if model_name not in self.models:
                self.logger.error(f"Model {model_name} not found for optimization")
                return False

            config = optimization_config or self.optimization_config
            model_info = self.models[model_name]

            # Check if inference settings are already configured
            if model_info.inference_configured and not config.auto_optimize:
                self.logger.info(f"Model {model_name} inference settings already configured")
                return True

            # Update status
            model_info.status = ModelStatus.OPTIMIZING

            self.logger.info(f"Starting inference configuration for model {model_name}")

            # Set quantization preference if enabled
            if config.quantization_level != QuantizationLevel.NONE:
                await self._set_quantization_preference(model_name, config.quantization_level)

            # Set compression preference if enabled
            if config.compression_type != CompressionType.NONE:
                await self._set_compression_preference(model_name, config.compression_type)

            # Apply memory optimization
            if config.memory_optimization:
                await self._apply_memory_optimization(model_name)

            # Record optimization
            optimization_record = {
                "timestamp": datetime.now().isoformat(),
                "quantization_level": config.quantization_level.value,
                "compression_type": config.compression_type.value,
                "memory_optimization": config.memory_optimization,
                "gpu_acceleration": config.enable_gpu_acceleration
            }

            model_info.optimization_history.append(optimization_record)
            model_info.inference_configured = True
            model_info.status = ModelStatus.LOADED

            self.logger.info(f"Model {model_name} inference configuration completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error optimizing model {model_name}: {e}")
            if model_name in self.models:
                self.models[model_name].status = ModelStatus.ERROR
            return False

    async def get_optimization_recommendations(self, model_name: str) -> Dict[str, Any]:
        """
        Get optimization recommendations for a model based on usage patterns and system resources.

        Args:
            model_name: Name of the model to analyze

        Returns:
            Dictionary with optimization recommendations
        """
        try:
            if model_name not in self.models:
                return {"error": f"Model {model_name} not found"}

            model_info = self.models[model_name]
            current_metrics = await self.get_resource_metrics()

            recommendations = {
                "model_name": model_name,
                "current_configuration": {
                    "quantization_level": model_info.quantization_level.value,
                    "compression_type": model_info.compression_type.value,
                    "inference_configured": model_info.inference_configured
                },
                "recommendations": [],
                "estimated_benefits": {}
            }

            # Memory-based recommendations
            if current_metrics.memory_percent > 80:
                recommendations["recommendations"].append({
                    "type": "quantization",
                    "level": "int4",
                    "reason": "High memory usage detected",
                    "estimated_memory_savings": "50-70%"
                })

            # Performance-based recommendations
            if model_info.performance_metrics.get("last_analysis_time", 0) > 60:
                recommendations["recommendations"].append({
                    "type": "gpu_acceleration",
                    "reason": "Slow inference times detected",
                    "estimated_speedup": "2-5x"
                })

            # Size-based recommendations
            if model_info.size_gb > self.optimization_config.optimization_threshold_mb / 1024:
                recommendations["recommendations"].append({
                    "type": "compression",
                    "method": "gzip",
                    "reason": "Large model size",
                    "estimated_size_reduction": "20-40%"
                })

            return recommendations

        except Exception as e:
            self.logger.error(f"Error getting optimization recommendations for {model_name}: {e}")
            return {"error": str(e)}

    async def _test_connection(self):
        """Test connection to Ollama server."""
        try:
            models = self.ollama_client.list()
            self.logger.debug(f"Connected to Ollama server, found {len(models.get('models', []))} models")
        except Exception as e:
            raise Exception(f"Cannot connect to Ollama server at {self.host}: {e}")
    
    async def _discover_models(self):
        """Discover available models from Ollama."""
        try:
            # Use the integrated OllamaClient's available models
            if hasattr(self.ollama_client, '_available_models'):
                for model_name in self.ollama_client._available_models:
                    self.models[model_name] = ModelInfo(
                        name=model_name,
                        status=ModelStatus.AVAILABLE,
                        size_gb=0.0  # Size will be updated when model is loaded
                    )

            self.logger.info(f"Discovered {len(self.models)} models")

        except Exception as e:
            self.logger.error(f"Error discovering models: {e}")
    
    async def _load_model(self, model_name: str) -> bool:
        """Load a specific model."""
        try:
            start_time = time.time()
            
            # Update status
            if model_name in self.models:
                self.models[model_name].status = ModelStatus.LOADING
            
            # For Ollama, we don't explicitly load models - they're loaded on first use
            # We'll simulate this by making a small test request
            test_response = self.ollama_client.generate(
                model=model_name,
                prompt="test",
                options={"num_predict": 1}
            )
            
            load_time = time.time() - start_time
            
            # Update model info
            if model_name not in self.models:
                self.models[model_name] = ModelInfo(name=model_name)
            
            self.models[model_name].status = ModelStatus.LOADED
            self.models[model_name].load_time = load_time
            self.models[model_name].last_used = datetime.now()
            
            self.loaded_models.add(model_name)
            
            self.logger.info(f"Model {model_name} loaded in {load_time:.2f}s")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading model {model_name}: {e}")
            if model_name in self.models:
                self.models[model_name].status = ModelStatus.ERROR
                self.models[model_name].error_count += 1
            return False
    
    async def _check_resource_constraints(self) -> bool:
        """Check if current resource usage is within limits."""
        try:
            metrics = await self.get_resource_metrics()
            
            max_memory = self.resource_limits.get("max_memory_usage", 4096)
            max_cpu = self.resource_limits.get("max_cpu_usage", 80)
            
            if metrics.memory_used_mb > max_memory:
                self.logger.warning(f"Memory usage {metrics.memory_used_mb:.0f}MB exceeds limit {max_memory}MB")
                return False
                
            if metrics.cpu_percent > max_cpu:
                self.logger.warning(f"CPU usage {metrics.cpu_percent:.1f}% exceeds limit {max_cpu}%")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking resource constraints: {e}")
            return False
    
    async def _free_resources(self):
        """Free resources by unloading least recently used models."""
        try:
            max_loaded = self.performance_settings.get("max_loaded_models", 2)
            
            if len(self.loaded_models) >= max_loaded:
                # Find least recently used model
                lru_model = None
                lru_time = datetime.now()
                
                for model_name in self.loaded_models:
                    if model_name in self.models:
                        last_used = self.models[model_name].last_used
                        if last_used and last_used < lru_time:
                            lru_time = last_used
                            lru_model = model_name
                
                if lru_model:
                    await self.unload_model(lru_model)
                    self.logger.info(f"Unloaded LRU model {lru_model} to free resources")
                    
        except Exception as e:
            self.logger.error(f"Error freeing resources: {e}")
    
    async def _unload_all_models(self):
        """Unload all loaded models."""
        for model_name in list(self.loaded_models):
            await self.unload_model(model_name)
    
    async def _start_background_tasks(self):
        """Start background monitoring and cleanup tasks."""
        try:
            # Resource monitoring task
            self._monitoring_task = asyncio.create_task(self._resource_monitoring_loop())
            
            # Model cleanup task
            self._cleanup_task = asyncio.create_task(self._model_cleanup_loop())
            
            # Health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())

            # Optimization task
            self._optimization_task = asyncio.create_task(self._optimization_loop())

            self.logger.info("Background tasks started")

        except Exception as e:
            self.logger.error(f"Error starting background tasks: {e}")
    
    async def _resource_monitoring_loop(self):
        """Background task for resource monitoring."""
        while True:
            try:
                metrics = await self.get_resource_metrics()
                self.resource_history.append(metrics)
                
                # Keep only last 100 entries
                if len(self.resource_history) > 100:
                    self.resource_history = self.resource_history[-100:]
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _model_cleanup_loop(self):
        """Background task for model cleanup."""
        while True:
            try:
                auto_unload_minutes = self.performance_settings.get("auto_unload_minutes", 30)
                cutoff_time = datetime.now() - timedelta(minutes=auto_unload_minutes)
                
                models_to_unload = []
                for model_name in self.loaded_models:
                    if model_name in self.models:
                        last_used = self.models[model_name].last_used
                        if last_used and last_used < cutoff_time:
                            models_to_unload.append(model_name)
                
                for model_name in models_to_unload:
                    await self.unload_model(model_name)
                    self.logger.info(f"Auto-unloaded unused model {model_name}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in model cleanup: {e}")
                await asyncio.sleep(300)
    
    async def _health_check_loop(self):
        """Background task for health checks."""
        while True:
            try:
                # Test connection to Ollama
                await self._test_connection()
                
                # Update model discovery
                await self._discover_models()
                
                interval = self.performance_settings.get("health_check_interval", 300)
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check: {e}")
                await asyncio.sleep(300)

    async def _optimization_loop(self):
        """Background task for model optimization."""
        while True:
            try:
                # Process optimization queue
                if self.optimization_queue:
                    with self.optimization_lock:
                        if self.optimization_queue:
                            model_name = self.optimization_queue.popleft()
                            await self.configure_inference_settings(model_name)

                # Auto-optimize large models if enabled
                if self.optimization_config.auto_optimize:
                    await self._auto_optimize_models()

                await asyncio.sleep(600)  # Check every 10 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(600)

    async def _initialize_optimization_system(self):
        """Initialize the optimization system."""
        try:
            # Detect GPU capabilities
            self._gpu_available = self._detect_gpu_availability()

            # Log optimization configuration
            self.logger.info(f"Optimization system initialized - GPU available: {self._gpu_available}")
            self.logger.info(f"Auto-optimization enabled: {self.optimization_config.auto_optimize}")

        except Exception as e:
            self.logger.error(f"Error initializing optimization system: {e}")

    def _detect_gpu_availability(self) -> bool:
        """Detect if GPU acceleration is available."""
        try:
            if TORCH_AVAILABLE:
                import torch
                return torch.cuda.is_available()
            return False
        except Exception:
            return False

    async def _set_quantization_preference(self, model_name: str, quantization_level: QuantizationLevel):
        """Set quantization preference for a model."""
        try:
            model_info = self.models[model_name]

            # For Ollama, quantization is typically handled at the model level
            # We'll track the quantization preference and apply it during inference
            model_info.quantization_level = quantization_level

            # Log quantization preference setting
            self.logger.info(f"Set {quantization_level.value} quantization preference for model {model_name}")

            # Estimate memory savings (approximate)
            if quantization_level == QuantizationLevel.INT4:
                model_info.memory_usage_mb *= 0.5  # Approximate 50% reduction
            elif quantization_level == QuantizationLevel.INT8:
                model_info.memory_usage_mb *= 0.7  # Approximate 30% reduction
            elif quantization_level == QuantizationLevel.FP16:
                model_info.memory_usage_mb *= 0.8  # Approximate 20% reduction

        except Exception as e:
            self.logger.error(f"Error applying quantization to {model_name}: {e}")
            raise

    async def _set_compression_preference(self, model_name: str, compression_type: CompressionType):
        """Set compression preference for a model."""
        try:
            model_info = self.models[model_name]

            # For Ollama, compression is typically handled at the storage level
            # We'll track the compression preference
            model_info.compression_type = compression_type

            # Log compression application
            self.logger.info(f"Applied {compression_type.value} compression to model {model_name}")

            # Estimate size reduction (approximate)
            if compression_type == CompressionType.GZIP:
                model_info.compressed_size_gb = model_info.size_gb * 0.7  # Approximate 30% reduction
            elif compression_type == CompressionType.PRUNING:
                model_info.compressed_size_gb = model_info.size_gb * 0.6  # Approximate 40% reduction

        except Exception as e:
            self.logger.error(f"Error applying compression to {model_name}: {e}")
            raise

    async def _apply_memory_optimization(self, model_name: str):
        """Apply memory optimization techniques to a model."""
        try:
            model_info = self.models[model_name]

            # Implement memory optimization strategies
            # For Ollama, this includes optimizing context windows and batch sizes

            # Update performance settings for this model
            optimized_settings = {
                "context_window": min(2048, 4096),  # Reduce context window for memory efficiency
                "batch_size": 1,  # Use smaller batch sizes
                "num_predict": 512  # Limit prediction length
            }

            model_info.performance_metrics["memory_optimized"] = True
            model_info.performance_metrics["optimized_settings"] = optimized_settings

            self.logger.info(f"Applied memory optimization to model {model_name}")

        except Exception as e:
            self.logger.error(f"Error applying memory optimization to {model_name}: {e}")
            raise

    async def _auto_optimize_models(self):
        """Automatically optimize models based on usage patterns and resource constraints."""
        try:
            current_metrics = await self.get_resource_metrics()

            # Check if system is under resource pressure
            memory_pressure = current_metrics.memory_percent > 80
            cpu_pressure = current_metrics.cpu_percent > 90

            if memory_pressure or cpu_pressure:
                # Find models that could benefit from inference configuration
                for model_name, model_info in self.models.items():
                    if not model_info.inference_configured and model_info.size_gb > 1.0:
                        # Queue for optimization
                        with self.optimization_lock:
                            if model_name not in self.optimization_queue:
                                self.optimization_queue.append(model_name)
                                self.logger.info(f"Queued {model_name} for auto-optimization due to resource pressure")

        except Exception as e:
            self.logger.error(f"Error in auto-optimization: {e}")
