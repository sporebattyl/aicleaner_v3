"""
AICleaner v3 Home Assistant Integration Test Suite
Comprehensive tests for Phase 4A HA integration components.
"""

__version__ = "1.0.0"

# Test module imports
from .test_entity_manager import TestAICleanerEntityManager, TestAICleanerSensor
from .test_service_manager import TestAICleanerServiceManager
from .test_config_flow import TestAICleanerConfigFlow, TestAICleanerOptionsFlowHandler
from .test_supervisor_api import TestSupervisorAPI
from .test_performance_monitor import TestPerformanceMonitor

__all__ = [
    "TestAICleanerEntityManager",
    "TestAICleanerSensor", 
    "TestAICleanerServiceManager",
    "TestAICleanerConfigFlow",
    "TestAICleanerOptionsFlowHandler",
    "TestSupervisorAPI",
    "TestPerformanceMonitor"
]