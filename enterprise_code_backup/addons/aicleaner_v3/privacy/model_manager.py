"""
Model Manager for Privacy Pipeline
Handles ONNX Runtime model loading, caching, and AMD 780M optimization
"""

import logging
import onnxruntime as ort
from typing import Dict, Optional, Any, List
from pathlib import Path
import threading
import time
from dataclasses import dataclass

from .privacy_config import PrivacyConfig, PrivacyLevel, ModelConfig


@dataclass
class ModelSession:
    """Wrapper for ONNX Runtime session with metadata"""
    session: ort.InferenceSession
    model_path: str
    last_used: float
    load_time: float
    input_shape: tuple
    output_names: List[str]
    memory_usage: int = 0


class ModelManager:
    """
    Manages ONNX Runtime models with AMD 780M optimization and dynamic loading.
    
    Features:
    - Dynamic model loading based on privacy level
    - AMD ROCm execution provider optimization
    - Model caching with LRU eviction
    - Thread-safe model access
    - Memory usage tracking
    """
    
    def __init__(self, config: PrivacyConfig):
        """
        Initialize Model Manager
        
        Args:
            config: Privacy pipeline configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Model storage
        self._loaded_models: Dict[str, ModelSession] = {}
        self._model_lock = threading.RLock()
        
        # Available providers (will be populated during initialization)
        self.available_providers: List[str] = []
        self.optimal_providers: List[str] = []
        
        # Model paths for different privacy levels
        self.model_paths = self._initialize_model_paths()
        
        # Performance tracking
        self.load_stats = {
            'models_loaded': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'load_failures': 0
        }
        
        self.logger.info(f"Model Manager initialized with {config.level.value} privacy level")
    
    def _initialize_model_paths(self) -> Dict[str, Dict[str, str]]:
        """Initialize model paths for all privacy levels"""
        base_path = Path(self.config.model_base_path)
        
        return {
            PrivacyLevel.SPEED.value: {
                'face_detection': str(base_path / "yunet.onnx"),
                'object_detection': str(base_path / "yolov8n.onnx"),
                'text_detection': str(base_path / "paddle_ocr_light.onnx")
            },
            PrivacyLevel.BALANCED.value: {
                'face_detection': str(base_path / "retinaface.onnx"),
                'object_detection': str(base_path / "yolov8m.onnx"),
                'text_detection': str(base_path / "paddle_ocr.onnx"),
                'license_plate_detection': str(base_path / "yolov8_license_plates.onnx")
            },
            PrivacyLevel.PARANOID.value: {
                'face_detection': str(base_path / "scrfd.onnx"),
                'object_detection': str(base_path / "yolov8l.onnx"),
                'text_detection': str(base_path / "paddle_ocr_server.onnx"),
                'license_plate_detection': str(base_path / "yolov8_license_plates_high_acc.onnx")
            }
        }
    
    async def initialize(self) -> bool:
        """
        Initialize the model manager and check available providers
        
        Returns:
            True if initialization successful
        """
        try:
            # Check available ONNX Runtime providers
            self.available_providers = ort.get_available_providers()
            self.logger.info(f"Available ONNX providers: {self.available_providers}")
            
            # Determine optimal provider order for AMD 780M
            self.optimal_providers = self._get_optimal_providers()
            self.logger.info(f"Using provider order: {self.optimal_providers}")
            
            # Pre-load models for current privacy level if caching enabled
            if self.config.performance.model_caching:
                await self._preload_models()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Manager: {e}")
            return False
    
    def _get_optimal_providers(self) -> List[str]:
        """
        Determine optimal execution provider order for AMD 780M
        
        Returns:
            List of providers in priority order
        """
        providers = []
        
        # AMD ROCm provider (best for AMD GPUs)
        if 'ROCMExecutionProvider' in self.available_providers:
            providers.append('ROCMExecutionProvider')
            self.logger.info("ROCm provider available for AMD iGPU acceleration")
        
        # DirectML provider (Windows alternative for AMD)
        elif 'DmlExecutionProvider' in self.available_providers:
            providers.append('DmlExecutionProvider')
            self.logger.info("DirectML provider available for AMD iGPU acceleration")
        
        # OpenVINO (if available, good for CPU+iGPU hybrid)
        if 'OpenVINOExecutionProvider' in self.available_providers:
            providers.append('OpenVINOExecutionProvider')
        
        # Always add CPU as fallback
        providers.append('CPUExecutionProvider')
        
        return providers
    
    def _create_session_options(self) -> ort.SessionOptions:
        """
        Create optimized session options for AMD 780M
        
        Returns:
            Configured SessionOptions
        """
        sess_options = ort.SessionOptions()
        
        # Enable all graph optimizations
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Enable memory pattern optimization
        sess_options.enable_mem_pattern = True
        
        # Set execution mode for performance
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        # Configure inter/intra op threads based on hardware
        sess_options.inter_op_num_threads = 4  # AMD 8845HS has 8 cores
        sess_options.intra_op_num_threads = 8  # Enable multi-threading within operations
        
        # Enable memory arena optimization
        sess_options.enable_cpu_mem_arena = True
        
        return sess_options
    
    def _create_provider_options(self) -> List[Dict[str, Any]]:
        """
        Create provider-specific options for AMD 780M optimization
        
        Returns:
            List of provider options
        """
        options = []
        
        for provider in self.optimal_providers:
            if provider == 'ROCMExecutionProvider':
                options.append({
                    'device_id': self.config.performance.gpu_memory_fraction,
                    'arena_extend_strategy': 'kSameAsRequested',
                    'gpu_mem_limit': int(8 * 1024 * 1024 * 1024 * self.config.performance.gpu_memory_fraction)  # 8GB * fraction
                })
            elif provider == 'DmlExecutionProvider':
                options.append({
                    'device_id': 0,
                    'enable_dynamic_graph_fusion': True
                })
            elif provider == 'OpenVINOExecutionProvider':
                options.append({
                    'device_type': 'GPU_FP16',  # Use FP16 for better performance
                    'enable_opencl_throttling': False
                })
            else:
                options.append({})
        
        return options
    
    async def get_model(self, model_type: str, privacy_level: Optional[PrivacyLevel] = None) -> Optional[ModelSession]:
        """
        Get model session for specified type and privacy level
        
        Args:
            model_type: Type of model (face_detection, object_detection, etc.)
            privacy_level: Privacy level (uses current config level if None)
            
        Returns:
            ModelSession if successful, None otherwise
        """
        if privacy_level is None:
            privacy_level = self.config.level
        
        model_key = f"{model_type}_{privacy_level.value}"
        
        with self._model_lock:
            # Check if model is already loaded
            if model_key in self._loaded_models:
                session = self._loaded_models[model_key]
                session.last_used = time.time()
                self.load_stats['cache_hits'] += 1
                self.logger.debug(f"Cache hit for model: {model_key}")
                return session
            
            # Load model if not in cache
            self.load_stats['cache_misses'] += 1
            return await self._load_model(model_type, privacy_level)
    
    async def _load_model(self, model_type: str, privacy_level: PrivacyLevel) -> Optional[ModelSession]:
        """
        Load ONNX model with AMD optimization
        
        Args:
            model_type: Type of model to load
            privacy_level: Privacy level for model selection
            
        Returns:
            ModelSession if successful, None otherwise
        """
        model_key = f"{model_type}_{privacy_level.value}"
        
        try:
            # Get model path
            model_paths = self.model_paths.get(privacy_level.value, {})
            model_path = model_paths.get(model_type)
            
            if not model_path or not Path(model_path).exists():
                self.logger.error(f"Model not found: {model_path}")
                self.load_stats['load_failures'] += 1
                return None
            
            self.logger.info(f"Loading model: {model_key} from {model_path}")
            start_time = time.time()
            
            # Create session options and provider options
            sess_options = self._create_session_options()
            provider_options = self._create_provider_options()
            
            # Create ONNX Runtime session
            session = ort.InferenceSession(
                model_path,
                sess_options=sess_options,
                providers=self.optimal_providers,
                provider_options=provider_options
            )
            
            load_time = time.time() - start_time
            
            # Get model metadata
            input_shape = session.get_inputs()[0].shape
            output_names = [output.name for output in session.get_outputs()]
            
            # Create model session wrapper
            model_session = ModelSession(
                session=session,
                model_path=model_path,
                last_used=time.time(),
                load_time=load_time,
                input_shape=tuple(input_shape) if input_shape else (1, 3, 640, 640),
                output_names=output_names
            )
            
            # Store in cache
            self._loaded_models[model_key] = model_session
            self.load_stats['models_loaded'] += 1
            
            self.logger.info(f"Successfully loaded {model_key} in {load_time:.2f}s")
            self.logger.debug(f"Model info - Input shape: {input_shape}, Outputs: {output_names}")
            
            # Clean up old models if cache is full
            await self._cleanup_cache()
            
            return model_session
            
        except Exception as e:
            self.logger.error(f"Failed to load model {model_key}: {e}")
            self.load_stats['load_failures'] += 1
            return None
    
    async def _preload_models(self):
        """Preload models for current privacy level"""
        current_models = self.model_paths.get(self.config.level.value, {})
        
        for model_type in current_models.keys():
            self.logger.info(f"Preloading {model_type} model...")
            await self.get_model(model_type)
    
    async def _cleanup_cache(self):
        """Clean up cache based on usage and memory limits"""
        max_models = 6  # Reasonable limit for iGPU memory
        
        if len(self._loaded_models) <= max_models:
            return
        
        # Sort models by last used time
        sorted_models = sorted(
            self._loaded_models.items(),
            key=lambda x: x[1].last_used
        )
        
        # Remove oldest models
        models_to_remove = len(self._loaded_models) - max_models
        for i in range(models_to_remove):
            model_key, model_session = sorted_models[i]
            self.logger.info(f"Evicting model from cache: {model_key}")
            del self._loaded_models[model_key]
    
    def switch_privacy_level(self, new_level: PrivacyLevel):
        """
        Switch to a new privacy level
        
        Args:
            new_level: New privacy level to use
        """
        with self._model_lock:
            old_level = self.config.level
            self.config.level = new_level
            
            self.logger.info(f"Switching privacy level: {old_level.value} -> {new_level.value}")
            
            # If caching is enabled, preload new models
            if self.config.performance.model_caching:
                # Schedule preloading in background
                import asyncio
                asyncio.create_task(self._preload_models())
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics
        
        Returns:
            Dictionary with performance metrics
        """
        with self._model_lock:
            return {
                'load_stats': self.load_stats.copy(),
                'loaded_models': len(self._loaded_models),
                'model_details': {
                    key: {
                        'load_time': session.load_time,
                        'last_used': session.last_used,
                        'input_shape': session.input_shape,
                        'output_count': len(session.output_names)
                    }
                    for key, session in self._loaded_models.items()
                },
                'available_providers': self.available_providers,
                'optimal_providers': self.optimal_providers
            }
    
    async def shutdown(self):
        """Shutdown model manager and clean up resources"""
        with self._model_lock:
            self.logger.info("Shutting down Model Manager")
            
            # Clear all loaded models
            for model_key in list(self._loaded_models.keys()):
                del self._loaded_models[model_key]
            
            self.logger.info("Model Manager shutdown complete")
    
    def validate_models(self) -> Dict[str, bool]:
        """
        Validate that required models exist for current privacy level
        
        Returns:
            Dictionary mapping model types to availability
        """
        current_models = self.model_paths.get(self.config.level.value, {})
        validation_results = {}
        
        for model_type, model_path in current_models.items():
            exists = Path(model_path).exists()
            validation_results[model_type] = exists
            
            if not exists:
                self.logger.warning(f"Required model not found: {model_path}")
        
        return validation_results