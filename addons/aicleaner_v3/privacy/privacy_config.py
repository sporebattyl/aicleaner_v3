"""
Privacy Configuration System
Defines privacy levels, redaction modes, and configuration management
"""

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path


class PrivacyLevel(Enum):
    """Privacy processing levels with different performance/accuracy tradeoffs"""
    SPEED = "speed"        # Minimal processing for performance
    BALANCED = "balanced"  # Good balance of privacy and performance  
    PARANOID = "paranoid"  # Maximum privacy protection


class RedactionMode(Enum):
    """Different methods for anonymizing detected content"""
    BLUR = "blur"           # Gaussian blur
    PIXELATE = "pixelate"   # Pixelation effect
    BLACK_BOX = "black_box" # Solid black rectangle


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    name: str
    path: str
    enabled: bool = True
    confidence_threshold: float = 0.7
    max_detections: int = 100
    input_size: tuple = (640, 640)
    device_id: int = 0
    
    
@dataclass
class DetectionConfig:
    """Configuration for detection tasks"""
    enabled: bool = True
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    post_processing: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RedactionConfig:
    """Configuration for redaction/anonymization"""
    face_mode: RedactionMode = RedactionMode.BLUR
    license_plate_mode: RedactionMode = RedactionMode.BLACK_BOX
    pii_text_mode: RedactionMode = RedactionMode.BLACK_BOX
    blur_kernel_size: int = 21
    pixelate_block_size: int = 10
    expansion_factor: float = 1.1  # Expand bounding boxes by this factor


@dataclass
class PerformanceConfig:
    """Performance optimization configuration"""
    max_image_size: tuple = (1920, 1080)
    parallel_processing: bool = True
    model_caching: bool = True
    async_processing: bool = True
    gpu_memory_fraction: float = 0.8
    batch_size: int = 1


@dataclass
class PrivacyConfig:
    """Main privacy pipeline configuration"""
    enabled: bool = True
    level: PrivacyLevel = PrivacyLevel.BALANCED
    
    # Detection configurations
    face_detection: DetectionConfig = field(default_factory=DetectionConfig)
    object_detection: DetectionConfig = field(default_factory=DetectionConfig)
    text_detection: DetectionConfig = field(default_factory=DetectionConfig)
    pii_analysis: DetectionConfig = field(default_factory=DetectionConfig)
    
    # Redaction configuration
    redaction: RedactionConfig = field(default_factory=RedactionConfig)
    
    # Performance configuration
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Model paths
    model_base_path: str = "/data/privacy_models"
    
    # Logging
    log_level: str = "INFO"
    enable_performance_logging: bool = True
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'PrivacyConfig':
        """Create PrivacyConfig from dictionary"""
        try:
            # Extract main settings
            enabled = config_dict.get('enabled', True)
            level_str = config_dict.get('level', 'balanced')
            level = PrivacyLevel(level_str)
            
            # Create instance with basic settings
            config = cls(enabled=enabled, level=level)
            
            # Update model base path
            config.model_base_path = config_dict.get('model_base_path', config.model_base_path)
            
            # Update performance settings
            if 'performance' in config_dict:
                perf_dict = config_dict['performance']
                config.performance = PerformanceConfig(
                    max_image_size=tuple(perf_dict.get('max_image_size', (1920, 1080))),
                    parallel_processing=perf_dict.get('parallel_processing', True),
                    model_caching=perf_dict.get('model_caching', True),
                    async_processing=perf_dict.get('async_processing', True),
                    gpu_memory_fraction=perf_dict.get('gpu_memory_fraction', 0.8),
                    batch_size=perf_dict.get('batch_size', 1)
                )
            
            # Update redaction settings
            if 'redaction' in config_dict:
                redact_dict = config_dict['redaction']
                config.redaction = RedactionConfig(
                    face_mode=RedactionMode(redact_dict.get('face_mode', 'blur')),
                    license_plate_mode=RedactionMode(redact_dict.get('license_plate_mode', 'black_box')),
                    pii_text_mode=RedactionMode(redact_dict.get('pii_text_mode', 'black_box')),
                    blur_kernel_size=redact_dict.get('blur_kernel_size', 21),
                    pixelate_block_size=redact_dict.get('pixelate_block_size', 10),
                    expansion_factor=redact_dict.get('expansion_factor', 1.1)
                )
            
            # Update detection configurations
            config._update_detection_configs(config_dict)
            
            # Update logging settings
            config.log_level = config_dict.get('log_level', 'INFO')
            config.enable_performance_logging = config_dict.get('enable_performance_logging', True)
            
            return config
            
        except Exception as e:
            logging.error(f"Error creating PrivacyConfig from dict: {e}")
            raise ValueError(f"Invalid privacy configuration: {e}")
    
    def _update_detection_configs(self, config_dict: Dict[str, Any]):
        """Update detection configurations from dictionary"""
        detection_types = ['face_detection', 'object_detection', 'text_detection', 'pii_analysis']
        
        for det_type in detection_types:
            if det_type in config_dict:
                det_dict = config_dict[det_type]
                detection_config = DetectionConfig(
                    enabled=det_dict.get('enabled', True),
                    post_processing=det_dict.get('post_processing', {})
                )
                
                # Update model configurations
                if 'models' in det_dict:
                    for model_name, model_dict in det_dict['models'].items():
                        model_config = ModelConfig(
                            name=model_name,
                            path=model_dict.get('path', ''),
                            enabled=model_dict.get('enabled', True),
                            confidence_threshold=model_dict.get('confidence_threshold', 0.7),
                            max_detections=model_dict.get('max_detections', 100),
                            input_size=tuple(model_dict.get('input_size', (640, 640))),
                            device_id=model_dict.get('device_id', 0)
                        )
                        detection_config.models[model_name] = model_config
                
                setattr(self, det_type, detection_config)
    
    def get_models_for_level(self) -> Dict[str, str]:
        """Get model paths for current privacy level"""
        model_mapping = {
            PrivacyLevel.SPEED: {
                'face_detection': 'yunet.onnx',
                'object_detection': 'yolov8n.onnx',
                'text_detection': 'paddle_ocr_light.onnx'
            },
            PrivacyLevel.BALANCED: {
                'face_detection': 'retinaface.onnx', 
                'object_detection': 'yolov8m.onnx',
                'text_detection': 'paddle_ocr.onnx',
                'license_plate_detection': 'yolov8_license_plates.onnx'
            },
            PrivacyLevel.PARANOID: {
                'face_detection': 'scrfd.onnx',
                'object_detection': 'yolov8l.onnx', 
                'text_detection': 'paddle_ocr_server.onnx',
                'license_plate_detection': 'yolov8_license_plates_high_acc.onnx'
            }
        }
        
        models = model_mapping.get(self.level, model_mapping[PrivacyLevel.BALANCED])
        
        # Convert to full paths
        full_paths = {}
        for task, model_file in models.items():
            full_paths[task] = str(Path(self.model_base_path) / model_file)
        
        return full_paths
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Check model base path exists
        if not Path(self.model_base_path).exists():
            errors.append(f"Model base path does not exist: {self.model_base_path}")
        
        # Check required models exist for current level
        required_models = self.get_models_for_level()
        for task, model_path in required_models.items():
            if not Path(model_path).exists():
                errors.append(f"Required model not found for {task}: {model_path}")
        
        # Validate performance settings
        if self.performance.gpu_memory_fraction <= 0 or self.performance.gpu_memory_fraction > 1:
            errors.append("GPU memory fraction must be between 0 and 1")
        
        if self.performance.batch_size < 1:
            errors.append("Batch size must be at least 1")
        
        # Validate redaction settings
        if self.redaction.blur_kernel_size < 3 or self.redaction.blur_kernel_size % 2 == 0:
            errors.append("Blur kernel size must be odd and >= 3")
        
        if self.redaction.expansion_factor < 1.0:
            errors.append("Expansion factor must be >= 1.0")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'enabled': self.enabled,
            'level': self.level.value,
            'model_base_path': self.model_base_path,
            'face_detection': {
                'enabled': self.face_detection.enabled,
                'models': {name: {
                    'path': model.path,
                    'enabled': model.enabled,
                    'confidence_threshold': model.confidence_threshold,
                    'max_detections': model.max_detections,
                    'input_size': model.input_size,
                    'device_id': model.device_id
                } for name, model in self.face_detection.models.items()},
                'post_processing': self.face_detection.post_processing
            },
            'object_detection': {
                'enabled': self.object_detection.enabled,
                'models': {name: {
                    'path': model.path,
                    'enabled': model.enabled,
                    'confidence_threshold': model.confidence_threshold,
                    'max_detections': model.max_detections,
                    'input_size': model.input_size,
                    'device_id': model.device_id
                } for name, model in self.object_detection.models.items()},
                'post_processing': self.object_detection.post_processing
            },
            'text_detection': {
                'enabled': self.text_detection.enabled,
                'models': {name: {
                    'path': model.path,
                    'enabled': model.enabled,
                    'confidence_threshold': model.confidence_threshold,
                    'max_detections': model.max_detections,
                    'input_size': model.input_size,
                    'device_id': model.device_id
                } for name, model in self.text_detection.models.items()},
                'post_processing': self.text_detection.post_processing
            },
            'redaction': {
                'face_mode': self.redaction.face_mode.value,
                'license_plate_mode': self.redaction.license_plate_mode.value,
                'pii_text_mode': self.redaction.pii_text_mode.value,
                'blur_kernel_size': self.redaction.blur_kernel_size,
                'pixelate_block_size': self.redaction.pixelate_block_size,
                'expansion_factor': self.redaction.expansion_factor
            },
            'performance': {
                'max_image_size': self.performance.max_image_size,
                'parallel_processing': self.performance.parallel_processing,
                'model_caching': self.performance.model_caching,
                'async_processing': self.performance.async_processing,
                'gpu_memory_fraction': self.performance.gpu_memory_fraction,
                'batch_size': self.performance.batch_size
            },
            'log_level': self.log_level,
            'enable_performance_logging': self.enable_performance_logging
        }


def create_default_privacy_config() -> PrivacyConfig:
    """Create default privacy configuration"""
    return PrivacyConfig(
        enabled=True,
        level=PrivacyLevel.BALANCED,
        model_base_path="/data/privacy_models"
    )