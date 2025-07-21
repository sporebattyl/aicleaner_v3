"""
Home Assistant Integration Module
Phase 4A: Enhanced Home Assistant Integration

This module provides seamless integration between AICleaner v3 and Home Assistant,
enabling bi-directional communication, entity management, and unified user experience.
"""

from .ha_client import HAClient
from .entity_manager import EntityManager
from .service_handler import ServiceHandler
from .ingress_middleware import IngressMiddleware
from .models import (
    HADeviceInfo,
    HASensorConfig,
    HABinarySensorConfig,
    HASwitchConfig,
    HAServiceConfig
)

__all__ = [
    'HAClient',
    'EntityManager', 
    'ServiceHandler',
    'IngressMiddleware',
    'HADeviceInfo',
    'HASensorConfig',
    'HABinarySensorConfig',
    'HASwitchConfig',
    'HAServiceConfig'
]

__version__ = "1.0.0"
__author__ = "AICleaner v3 Development Team"