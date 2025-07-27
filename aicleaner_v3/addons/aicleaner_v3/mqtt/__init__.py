"""
MQTT Integration Module
Phase 4B: MQTT Discovery System

This module provides MQTT adapter functionality for Home Assistant integration
through MQTT Discovery protocol. Maintains clean separation from core systems
using the established adapter pattern.
"""

from .adapter import MQTTAdapter
from .config import MQTTConfig

__all__ = ['MQTTAdapter', 'MQTTConfig']