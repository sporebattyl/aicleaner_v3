"""
Main Privacy Pipeline for AICleaner v3
Orchestrates privacy preprocessing with configurable DAG and ONNX Runtime optimization
"""

import asyncio
import logging
import time
import cv2
import numpy as np
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import hashlib

from .privacy_config import PrivacyConfig, PrivacyLevel, create_default_privacy_config
from .model_manager import ModelManager
from .dag_processor import DAGProcessor, ProcessingContext
from .detection_nodes import FaceDetectionNode, ObjectDetectionNode, TextDetectionNode, PIIAnalysisNode
from .anonymization_engine import AnonymizationEngine, AnonymizationResult


class PrivacyPipeline:
    """
    Main Privacy Pipeline for AICleaner v3
    
    Features:
    - Configurable privacy levels (Speed, Balanced, Paranoid)
    - AMD 780M iGPU optimization with ONNX Runtime
    - Modular DAG architecture for parallel processing
    - <5 second processing target
    - Face detection and blurring/redaction
    - Text detection and PII sanitization
    - Object anonymization (license plates, documents, screens)
    - Performance monitoring and optimization
    """
    
    def __init__(self, config: Optional[PrivacyConfig] = None):
        """
        Initialize Privacy Pipeline
        
        Args:
            config: Privacy pipeline configuration (uses default if None)
        """
        self.config = config or create_default_privacy_config()
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.model_manager: Optional[ModelManager] = None
        self.dag_processor: Optional[DAGProcessor] = None
        self.anonymization_engine: Optional[AnonymizationEngine] = None
        
        # Performance tracking
        self.processing_stats = {
            'total_images_processed': 0,
            'successful_processing': 0,
            'failed_processing': 0,
            'average_processing_time': 0.0,
            'total_processing_time': 0.0,
            'privacy_level_usage': {level.value: 0 for level in PrivacyLevel}
        }
        
        # Cache for repeated processing (optional)
        self.result_cache: Dict[str, Any] = {}
        self.cache_enabled = False
        
        self.logger.info(f"Privacy Pipeline initialized with {self.config.level.value} privacy level")
    
    async def initialize(self) -> bool:
        """
        Initialize all pipeline components
        
        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing Privacy Pipeline components...")
            
            # Initialize model manager
            self.model_manager = ModelManager(self.config)
            if not await self.model_manager.initialize():
                self.logger.error("Failed to initialize Model Manager")
                return False
            
            # Initialize DAG processor
            self.dag_processor = DAGProcessor(self.config)
            self._setup_dag_nodes()
            
            # Initialize anonymization engine
            self.anonymization_engine = AnonymizationEngine(self.config)
            
            # Validate configuration
            validation_errors = self.config.validate()
            if validation_errors:
                self.logger.warning(f"Configuration validation warnings: {validation_errors}")
            
            # Validate models
            model_validation = self.model_manager.validate_models()
            missing_models = [k for k, v in model_validation.items() if not v]
            if missing_models:
                self.logger.warning(f"Missing models for current privacy level: {missing_models}")
            
            self.logger.info("Privacy Pipeline initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Privacy Pipeline: {e}")
            return False
    
    def _setup_dag_nodes(self):
        """Setup DAG nodes and dependencies"""
        if not self.dag_processor or not self.model_manager:
            raise RuntimeError("DAG processor or model manager not initialized")
        
        # Create detection nodes
        face_node = FaceDetectionNode(self.config, self.model_manager)
        object_node = ObjectDetectionNode(self.config, self.model_manager)
        text_node = TextDetectionNode(self.config, self.model_manager)
        pii_node = PIIAnalysisNode(self.config, self.model_manager)
        
        # Add nodes to DAG
        self.dag_processor.add_node(face_node)
        self.dag_processor.add_node(object_node)
        self.dag_processor.add_node(text_node)
        self.dag_processor.add_node(pii_node)
        
        # Setup dependencies
        # PII analysis depends on text detection
        self.dag_processor.add_dependency("pii_analysis", "text_detection")
        
        # Face and object detection can run in parallel (no dependencies)
        # Text detection can run in parallel with face/object detection
        
        self.logger.debug("DAG nodes and dependencies configured")
    
    async def process_image(self, image_input: Union[str, np.ndarray], 
                          privacy_level: Optional[PrivacyLevel] = None,
                          bypass: bool = False) -> Dict[str, Any]:
        """
        Process image through privacy pipeline
        
        Args:
            image_input: Image file path or numpy array
            privacy_level: Override privacy level (uses config level if None)
            bypass: Skip privacy processing (passthrough mode)
            
        Returns:
            Dictionary with processed image and metadata
        """
        start_time = time.time()
        processing_level = privacy_level or self.config.level
        
        try:
            # Load image if path provided
            if isinstance(image_input, str):
                image = cv2.imread(image_input)
                if image is None:
                    raise ValueError(f"Could not load image from {image_input}")
                image_path = image_input
            else:
                image = image_input.copy()
                image_path = ""
            
            # Validate image
            if image.size == 0:
                raise ValueError("Empty image provided")
            
            # Check cache if enabled
            cache_key = None
            if self.cache_enabled:
                cache_key = self._generate_cache_key(image, processing_level)
                cached_result = self.result_cache.get(cache_key)
                if cached_result:
                    self.logger.debug("Cache hit - returning cached result")
                    return cached_result
            
            # Handle bypass mode
            if bypass:
                self.logger.info("Bypass mode - returning original image")
                return self._create_result(
                    image, 0, time.time() - start_time, "bypassed", {}
                )
            
            # Resize image if too large
            resized_image = self._resize_image_if_needed(image)
            
            # Check if any detection nodes are enabled for this privacy level
            if not self._has_enabled_nodes(processing_level):
                self.logger.info(f"No detection nodes enabled for {processing_level.value} - returning original image")
                return self._create_result(
                    image, 0, time.time() - start_time, "no_nodes_enabled", {}
                )
            
            # Process through DAG
            context = await self.dag_processor.process(resized_image, image_path)
            
            # Apply anonymization
            anonymization_result = await self.anonymization_engine.anonymize_image(context)
            
            # Scale result back to original size if image was resized
            final_image = self._scale_result_to_original(
                anonymization_result.anonymized_image, image, resized_image
            )
            
            processing_time = time.time() - start_time
            
            # Create result
            result = self._create_result(
                final_image,
                anonymization_result.regions_processed,
                processing_time,
                "success",
                {
                    "detection_results": {k: v.__dict__ for k, v in context.detection_results.items()},
                    "anonymization_stats": anonymization_result.redaction_stats,
                    "dag_performance": self.dag_processor.get_performance_report(),
                    "privacy_level": processing_level.value,
                    "image_resized": image.shape != resized_image.shape
                }
            )
            
            # Cache result if enabled
            if self.cache_enabled and cache_key:
                self.result_cache[cache_key] = result
            
            # Update statistics
            self._update_processing_stats(processing_time, True, processing_level)
            
            self.logger.info(f"Successfully processed image in {processing_time:.3f}s "
                           f"({anonymization_result.regions_processed} regions anonymized)")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Image processing failed after {processing_time:.3f}s: {e}")
            
            # Update failure statistics
            self._update_processing_stats(processing_time, False, processing_level)
            
            # Return original image with error information
            original_image = image if 'image' in locals() else np.zeros((100, 100, 3), dtype=np.uint8)
            return self._create_result(
                original_image, 0, processing_time, "error", {"error": str(e)}
            )
    
    async def process_image_batch(self, image_inputs: List[Union[str, np.ndarray]], 
                                privacy_level: Optional[PrivacyLevel] = None) -> List[Dict[str, Any]]:
        """
        Process multiple images in batch
        
        Args:
            image_inputs: List of image paths or numpy arrays
            privacy_level: Override privacy level
            
        Returns:
            List of processing results
        """
        if self.config.performance.async_processing:
            # Process in parallel
            tasks = [
                self.process_image(image_input, privacy_level)
                for image_input in image_inputs
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Process sequentially
            results = []
            for image_input in image_inputs:
                result = await self.process_image(image_input, privacy_level)
                results.append(result)
            return results
    
    def _resize_image_if_needed(self, image: np.ndarray) -> np.ndarray:
        """Resize image if it exceeds maximum size limits"""
        h, w = image.shape[:2]
        max_h, max_w = self.config.performance.max_image_size
        
        if h <= max_h and w <= max_w:
            return image
        
        # Calculate scale factor
        scale = min(max_w / w, max_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        self.logger.debug(f"Resizing image from {w}x{h} to {new_w}x{new_h}")
        return cv2.resize(image, (new_w, new_h))
    
    def _scale_result_to_original(self, processed_image: np.ndarray, 
                                original_image: np.ndarray, 
                                resized_image: np.ndarray) -> np.ndarray:
        """Scale processed image back to original size if needed"""
        if original_image.shape == resized_image.shape:
            return processed_image
        
        original_h, original_w = original_image.shape[:2]
        return cv2.resize(processed_image, (original_w, original_h))
    
    def _has_enabled_nodes(self, privacy_level: PrivacyLevel) -> bool:
        """Check if any nodes are enabled for the given privacy level"""
        if not self.dag_processor:
            return False
        
        for node in self.dag_processor.nodes.values():
            if node.is_enabled_for_level(privacy_level):
                return True
        
        return False
    
    def _generate_cache_key(self, image: np.ndarray, privacy_level: PrivacyLevel) -> str:
        """Generate cache key for image and privacy level"""
        image_hash = hashlib.md5(image.tobytes()).hexdigest()
        return f"{image_hash}_{privacy_level.value}"
    
    def _create_result(self, image: np.ndarray, regions_processed: int, 
                      processing_time: float, status: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized result dictionary"""
        return {
            "anonymized_image": image,
            "regions_processed": regions_processed,
            "processing_time": processing_time,
            "status": status,
            "privacy_level": self.config.level.value,
            "metadata": metadata,
            "timestamp": time.time()
        }
    
    def _update_processing_stats(self, processing_time: float, success: bool, privacy_level: PrivacyLevel):
        """Update processing statistics"""
        self.processing_stats['total_images_processed'] += 1
        self.processing_stats['total_processing_time'] += processing_time
        self.processing_stats['privacy_level_usage'][privacy_level.value] += 1
        
        if success:
            self.processing_stats['successful_processing'] += 1
        else:
            self.processing_stats['failed_processing'] += 1
        
        # Update average processing time
        self.processing_stats['average_processing_time'] = (
            self.processing_stats['total_processing_time'] / 
            self.processing_stats['total_images_processed']
        )
    
    def switch_privacy_level(self, new_level: PrivacyLevel):
        """
        Switch to a new privacy level
        
        Args:
            new_level: New privacy level to use
        """
        old_level = self.config.level
        self.config.level = new_level
        
        if self.model_manager:
            self.model_manager.switch_privacy_level(new_level)
        
        self.logger.info(f"Switched privacy level: {old_level.value} -> {new_level.value}")
    
    def enable_caching(self, max_cache_size: int = 100):
        """
        Enable result caching
        
        Args:
            max_cache_size: Maximum number of results to cache
        """
        self.cache_enabled = True
        self.max_cache_size = max_cache_size
        self.logger.info(f"Result caching enabled (max size: {max_cache_size})")
    
    def disable_caching(self):
        """Disable result caching"""
        self.cache_enabled = False
        self.result_cache.clear()
        self.logger.info("Result caching disabled")
    
    def clear_cache(self):
        """Clear result cache"""
        self.result_cache.clear()
        self.logger.info("Result cache cleared")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report
        
        Returns:
            Dictionary with performance metrics
        """
        base_report = {
            "pipeline_stats": self.processing_stats.copy(),
            "configuration": {
                "privacy_level": self.config.level.value,
                "enabled": self.config.enabled,
                "parallel_processing": self.config.performance.parallel_processing,
                "model_caching": self.config.performance.model_caching,
                "async_processing": self.config.performance.async_processing
            },
            "cache_stats": {
                "enabled": self.cache_enabled,
                "entries": len(self.result_cache),
                "max_size": getattr(self, 'max_cache_size', 0)
            }
        }
        
        # Add component performance reports
        if self.model_manager:
            base_report["model_manager"] = self.model_manager.get_performance_stats()
        
        if self.dag_processor:
            base_report["dag_processor"] = self.dag_processor.get_performance_report()
        
        if self.anonymization_engine:
            base_report["anonymization_engine"] = self.anonymization_engine.get_performance_stats()
        
        return base_report
    
    def reset_statistics(self):
        """Reset all performance statistics"""
        self.processing_stats = {
            'total_images_processed': 0,
            'successful_processing': 0,
            'failed_processing': 0,
            'average_processing_time': 0.0,
            'total_processing_time': 0.0,
            'privacy_level_usage': {level.value: 0 for level in PrivacyLevel}
        }
        
        if self.dag_processor:
            self.dag_processor.reset_statistics()
        
        self.logger.info("Performance statistics reset")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all pipeline components
        
        Returns:
            Health check results
        """
        health_report = {
            "overall_health": "healthy",
            "components": {},
            "timestamp": time.time()
        }
        
        try:
            # Check model manager
            if self.model_manager:
                model_validation = self.model_manager.validate_models()
                health_report["components"]["model_manager"] = {
                    "status": "healthy" if all(model_validation.values()) else "degraded",
                    "model_validation": model_validation
                }
                
                if not all(model_validation.values()):
                    health_report["overall_health"] = "degraded"
            
            # Check DAG processor
            if self.dag_processor:
                dag_errors = self.dag_processor.validate_graph()
                health_report["components"]["dag_processor"] = {
                    "status": "healthy" if not dag_errors else "error",
                    "validation_errors": dag_errors
                }
                
                if dag_errors:
                    health_report["overall_health"] = "error"
            
            # Check configuration
            config_errors = self.config.validate()
            health_report["components"]["configuration"] = {
                "status": "healthy" if not config_errors else "warning",
                "validation_errors": config_errors
            }
            
            if config_errors:
                health_report["overall_health"] = "degraded"
            
        except Exception as e:
            health_report["overall_health"] = "error"
            health_report["error"] = str(e)
        
        return health_report
    
    async def shutdown(self):
        """Shutdown privacy pipeline and clean up resources"""
        self.logger.info("Shutting down Privacy Pipeline")
        
        try:
            if self.model_manager:
                await self.model_manager.shutdown()
            
            self.clear_cache()
            
            self.logger.info("Privacy Pipeline shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


# Convenience functions for easy usage
async def create_privacy_pipeline(config_dict: Optional[Dict[str, Any]] = None) -> PrivacyPipeline:
    """
    Create and initialize a privacy pipeline
    
    Args:
        config_dict: Configuration dictionary (uses defaults if None)
        
    Returns:
        Initialized PrivacyPipeline instance
    """
    if config_dict:
        config = PrivacyConfig.from_dict(config_dict)
    else:
        config = create_default_privacy_config()
    
    pipeline = PrivacyPipeline(config)
    
    if not await pipeline.initialize():
        raise RuntimeError("Failed to initialize privacy pipeline")
    
    return pipeline


async def process_image_with_privacy(image_input: Union[str, np.ndarray],
                                   privacy_level: PrivacyLevel = PrivacyLevel.BALANCED,
                                   config_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to process a single image with privacy protection
    
    Args:
        image_input: Image path or numpy array
        privacy_level: Privacy level to use
        config_dict: Optional configuration dictionary
        
    Returns:
        Processing result dictionary
    """
    pipeline = await create_privacy_pipeline(config_dict)
    
    try:
        result = await pipeline.process_image(image_input, privacy_level)
        return result
    finally:
        await pipeline.shutdown()