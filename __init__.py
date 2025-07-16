"""
AICleaner Package - Intelligent Multi-Zone Cleanliness Management
Component-based design following TDD principles
"""

from .aicleaner import AICleaner, Zone, HAClient
from .configuration_manager import ConfigurationManager
from .notification_engine import NotificationEngine
from .ignore_rules_manager import IgnoreRulesManager

# Import external dependencies for test patching
try:
    from google.generativeai.generative_models import GenerativeModel
    from pathlib import Path
except ImportError:
    # Fallback for environments without these dependencies
    GenerativeModel = None
    Path = None

__version__ = "2.0.0"
__all__ = [
    'AICleaner',
    'Zone',
    'HAClient',
    'ConfigurationManager',
    'NotificationEngine',
    'IgnoreRulesManager',
    'GenerativeModel',
    'Path'
]
