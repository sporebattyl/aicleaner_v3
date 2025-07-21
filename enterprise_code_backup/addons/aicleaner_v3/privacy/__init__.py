"""
Privacy Pipeline for AICleaner v3
Phase 4D: Privacy Preprocessing System

Modular privacy preprocessing pipeline that protects user privacy before 
sending data to cloud APIs while maintaining performance targets.

Features:
- Face detection and blurring/redaction
- Text detection and PII sanitization  
- Object anonymization (license plates, documents, screens)
- AMD 780M iGPU optimization with ONNX Runtime
- Configurable privacy levels (Speed, Balanced, Paranoid)
- Modular DAG architecture for parallel processing
- <5 second processing target
"""

from .privacy_pipeline import PrivacyPipeline
from .model_manager import ModelManager
from .privacy_config import PrivacyConfig, PrivacyLevel, RedactionMode
from .dag_processor import DAGProcessor, ProcessingNode
from .detection_nodes import FaceDetectionNode, ObjectDetectionNode, TextDetectionNode, PIIAnalysisNode
from .anonymization_engine import AnonymizationEngine

__all__ = [
    'PrivacyPipeline',
    'ModelManager', 
    'PrivacyConfig',
    'PrivacyLevel',
    'RedactionMode',
    'DAGProcessor',
    'ProcessingNode',
    'FaceDetectionNode',
    'ObjectDetectionNode', 
    'TextDetectionNode',
    'PIIAnalysisNode',
    'AnonymizationEngine'
]

__version__ = "1.0.0"