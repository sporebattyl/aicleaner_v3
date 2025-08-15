"""
AICleaner V3 - Advanced AI-powered content analysis and management system.

This package provides intelligent content analysis, privacy filtering, and
automated content management capabilities for various AI provider integrations.
"""

from .core.orchestrator import Orchestrator
from .core.health import HealthMonitor
from .providers.base_provider import BaseProvider
from .providers.gemini_provider import GeminiProvider
from .config.loader import ConfigurationLoader
from .config.schema import ConfigSchema

__version__ = "3.0.0"
__author__ = "AICleaner Team"
__description__ = "Advanced AI-powered content analysis and management system"

# Package level exports
__all__ = [
    "Orchestrator",
    "HealthMonitor", 
    "BaseProvider",
    "GeminiProvider",
    "ConfigurationLoader",
    "ConfigSchema",
]

# Version information
VERSION_INFO = {
    "major": 3,
    "minor": 0,
    "patch": 0,
    "pre_release": None,
}