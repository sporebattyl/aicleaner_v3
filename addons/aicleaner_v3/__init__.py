"""
AICleaner Package - Intelligent Multi-Zone Cleanliness Management
Component-based design following TDD principles
"""

# Import core components
from .core.analyzer import ZoneAnalyzer
from .core.analysis_queue import AnalysisPriority
from .core.state_manager import AnalysisState
from .core.scheduler import ZoneScheduler
from .core.state_manager import StateManager
from .core.performance_monitor import PerformanceMonitor

# Import integration components
from .integrations.ha_client import HAClient
from .integrations.mqtt_manager import MQTTManager
from .integrations.gemini_client import GeminiClient

# Import existing components for backward compatibility
try:
    from .aicleaner import AICleaner, Zone
    from .configuration_manager import ConfigurationManager
    from .notification_engine import NotificationEngine
    from .ignore_rules_manager import IgnoreRulesManager
except ImportError:
    # These may not be available during testing
    pass

# Import external dependencies for test patching
try:
    from google.generativeai.generative_models import GenerativeModel
    from pathlib import Path
except ImportError:
    # Fallback for environments without these dependencies
    GenerativeModel = None
    Path = None

__version__ = "2.1.0"
__all__ = [
    # Core components
    'ZoneAnalyzer',
    'AnalysisPriority',
    'AnalysisState',
    'ZoneScheduler',
    'StateManager',
    'PerformanceMonitor',
    
    # Integration components
    'HAClient',
    'MQTTManager',
    'GeminiClient',
    
    # Legacy components
    'AICleaner',
    'Zone',
    'ConfigurationManager',
    'NotificationEngine',
    'IgnoreRulesManager',
    
    # External dependencies
    'GenerativeModel',
    'Path'
]