"""
Core module for AI Cleaner Home Assistant addon.
Contains all the main components for image analysis and cleaning task management.
"""

from .config import (
    get_config,
    reload_config,
    AiCleanerConfig,
    ConfigManager,
    ConfigurationError,
    ZoneConfig
)

from .camera_manager import (
    CameraManager,
    ImageData,
    CameraError
)

from .ha_link import (
    HAEntityManager,
    HAAPIClient,
    MQTTManager,
    HAEntity,
    HAEntityError,
    EntityType
)

from .scheduler import (
    ZoneScheduler,
    AdaptiveScheduler,
    ScheduledTask,
    ScheduleType,
    SchedulePriority
)

from .analysis_manager import (
    AnalysisManager,
    PDCACycle,
    PDCAPhase,
    AnalysisState
)

__all__ = [
    # Configuration
    'get_config',
    'reload_config',
    'AiCleanerConfig',
    'ConfigManager',
    'ConfigurationError',
    'ZoneConfig',
    
    # Camera Management
    'CameraManager',
    'ImageData',
    'CameraError',
    
    # Home Assistant Integration
    'HAEntityManager',
    'HAAPIClient',
    'MQTTManager',
    'HAEntity',
    'HAEntityError',
    'EntityType',
    
    # Scheduling
    'ZoneScheduler',
    'AdaptiveScheduler',
    'ScheduledTask',
    'ScheduleType',
    'SchedulePriority',
    
    # Analysis Management
    'AnalysisManager',
    'PDCACycle',
    'PDCAPhase',
    'AnalysisState',
]

__version__ = "1.0.0"
__author__ = "AI Cleaner Team"
__description__ = "Core components for AI-powered home cleaning analysis"