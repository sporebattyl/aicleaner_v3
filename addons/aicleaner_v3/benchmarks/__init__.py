"""
Benchmarks package for AICleaner Phase 3C.2
Contains dedicated benchmark scripts for performance testing and load testing.
"""

__version__ = "1.0.0"
__author__ = "AICleaner Development Team"

# Import main benchmark classes for easy access
try:
    from .load_test_suite import LoadTestSuite
    from .performance_regression_suite import PerformanceRegressionSuite
    from .local_vs_cloud_benchmark import LocalVsCloudBenchmark
    from .system_stress_test import SystemStressTest
    
    __all__ = [
        'LoadTestSuite',
        'PerformanceRegressionSuite', 
        'LocalVsCloudBenchmark',
        'SystemStressTest'
    ]
    
except ImportError:
    # Graceful degradation if dependencies are not available
    __all__ = []
