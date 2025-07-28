"""
Logging Initialization for AICleaner v3
Provides unified logging setup for production deployment

This module initializes the appropriate logging system based on the
deployment environment and configuration.
"""

import os
import sys
from typing import Optional, Dict, Any
from pathlib import Path

from .simple_logging import SimpleLogConfig, SimpleLoggingManager, get_simple_logger
from .diagnostics import DiagnosticTool


def detect_environment() -> str:
    """Detect the deployment environment"""
    if os.getenv('HASSIO_TOKEN') or os.getenv('SUPERVISOR_TOKEN'):
        return 'hassio'
    elif os.getenv('DOCKER_CONTAINER'):
        return 'docker'
    elif 'pytest' in sys.modules:
        return 'test'
    else:
        return 'development'


def get_default_config(environment: str = None) -> SimpleLogConfig:
    """Get default logging configuration based on environment"""
    if environment is None:
        environment = detect_environment()
    
    base_config = SimpleLogConfig()
    
    if environment == 'hassio':
        # Home Assistant addon environment
        base_config.log_directory = "/data/logs"
        base_config.log_level = SimpleLogConfig.LogLevel.INFO
        base_config.enable_console = True
        base_config.enable_file = True
        base_config.enable_ha_integration = True
        base_config.enable_security_logging = True
        base_config.enable_performance_logging = False  # Disabled for performance
        base_config.max_log_size = 5 * 1024 * 1024  # 5MB
        base_config.backup_count = 3
        base_config.buffer_size = 50  # Reduced for resource constraints
        base_config.flush_interval = 15.0  # Increased for efficiency
        
    elif environment == 'docker':
        # Docker container environment
        base_config.log_directory = "/app/logs"
        base_config.log_level = SimpleLogConfig.LogLevel.INFO
        base_config.enable_console = True
        base_config.enable_file = True
        base_config.enable_ha_integration = False
        base_config.enable_security_logging = True
        base_config.enable_performance_logging = False
        
    elif environment == 'test':
        # Test environment
        base_config.log_directory = "/tmp/aicleaner_test_logs"
        base_config.log_level = SimpleLogConfig.LogLevel.DEBUG
        base_config.enable_console = False  # Avoid test output noise
        base_config.enable_file = True
        base_config.enable_ha_integration = False
        base_config.enable_security_logging = False
        base_config.enable_performance_logging = False
        base_config.buffer_size = 10
        base_config.flush_interval = 1.0
        
    else:
        # Development environment
        base_config.log_directory = "./logs"
        base_config.log_level = SimpleLogConfig.LogLevel.DEBUG
        base_config.enable_console = True
        base_config.enable_file = True
        base_config.enable_ha_integration = False
        base_config.enable_security_logging = True
        base_config.enable_performance_logging = True
    
    return base_config


def load_config_from_file(config_path: str) -> Optional[SimpleLogConfig]:
    """Load logging configuration from file"""
    try:
        import yaml
        
        config_file = Path(config_path)
        if not config_file.exists():
            return None
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        logging_config = config_data.get('logging', {})
        if not logging_config:
            return None
        
        # Create config from loaded data
        config = SimpleLogConfig()
        
        # Map configuration values
        if 'log_level' in logging_config:
            level_map = {
                'debug': SimpleLogConfig.LogLevel.DEBUG,
                'info': SimpleLogConfig.LogLevel.INFO,
                'warning': SimpleLogConfig.LogLevel.WARNING,
                'error': SimpleLogConfig.LogLevel.ERROR,
                'critical': SimpleLogConfig.LogLevel.CRITICAL
            }
            config.log_level = level_map.get(logging_config['log_level'].lower(), SimpleLogConfig.LogLevel.INFO)
        
        if 'log_directory' in logging_config:
            config.log_directory = logging_config['log_directory']
        
        if 'max_log_size' in logging_config:
            config.max_log_size = logging_config['max_log_size']
        
        if 'backup_count' in logging_config:
            config.backup_count = logging_config['backup_count']
        
        if 'enable_console' in logging_config:
            config.enable_console = logging_config['enable_console']
        
        if 'enable_file' in logging_config:
            config.enable_file = logging_config['enable_file']
        
        if 'enable_ha_integration' in logging_config:
            config.enable_ha_integration = logging_config['enable_ha_integration']
        
        if 'enable_security_logging' in logging_config:
            config.enable_security_logging = logging_config['enable_security_logging']
        
        if 'enable_performance_logging' in logging_config:
            config.enable_performance_logging = logging_config['enable_performance_logging']
        
        return config
    
    except Exception as e:
        print(f"Error loading logging configuration: {e}")
        return None


def initialize_logging(config_path: str = None, environment: str = None) -> SimpleLoggingManager:
    """Initialize logging system"""
    try:
        # Try to load configuration from file first
        config = None
        if config_path:
            config = load_config_from_file(config_path)
        
        # Fall back to default configuration
        if config is None:
            config = get_default_config(environment)
        
        # Ensure log directory exists
        log_dir = Path(config.log_directory)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create and return logging manager
        manager = SimpleLoggingManager(config)
        
        # Log initialization
        logger = get_simple_logger("logging_init")
        logger.info(f"Logging initialized for environment: {environment or detect_environment()}")
        logger.info(f"Log directory: {config.log_directory}")
        logger.info(f"Log level: {config.log_level.name}")
        
        return manager
    
    except Exception as e:
        print(f"Error initializing logging: {e}")
        # Return basic logging manager as fallback
        return SimpleLoggingManager(SimpleLogConfig())


def setup_diagnostic_monitoring(interval_minutes: int = 60) -> None:
    """Setup periodic diagnostic monitoring"""
    try:
        import asyncio
        import threading
        
        def diagnostic_monitor():
            """Run diagnostic monitoring"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def monitor_loop():
                diagnostic_tool = DiagnosticTool()
                logger = get_simple_logger("diagnostic_monitor")
                
                while True:
                    try:
                        # Perform health check
                        health_check = diagnostic_tool.perform_health_check()
                        
                        if health_check.overall_status != "healthy":
                            logger.warning(f"Health check failed: {len(health_check.issues)} issues found")
                            for issue in health_check.issues:
                                logger.warning(f"Issue: {issue}")
                        else:
                            logger.debug("Health check passed")
                        
                        # Wait for next check
                        await asyncio.sleep(interval_minutes * 60)
                    
                    except Exception as e:
                        logger.error(f"Error in diagnostic monitor: {e}")
                        await asyncio.sleep(60)  # Wait 1 minute before retrying
            
            loop.run_until_complete(monitor_loop())
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(
            target=diagnostic_monitor,
            name="DiagnosticMonitor",
            daemon=True
        )
        monitor_thread.start()
        
        logger = get_simple_logger("diagnostic_setup")
        logger.info(f"Diagnostic monitoring started (interval: {interval_minutes} minutes)")
    
    except Exception as e:
        print(f"Error setting up diagnostic monitoring: {e}")


def get_logging_info() -> Dict[str, Any]:
    """Get current logging system information"""
    from .simple_logging import get_logging_stats
    
    try:
        environment = detect_environment()
        stats = get_logging_stats()
        
        return {
            "environment": environment,
            "stats": stats,
            "config": {
                "log_directory": stats.get("log_directory", "unknown"),
                "handlers": list(stats.get("handlers", {}).keys())
            }
        }
    except Exception as e:
        return {
            "environment": detect_environment(),
            "error": str(e)
        }


# Convenience function for quick setup
def quick_setup(config_path: str = None, enable_diagnostics: bool = True) -> SimpleLoggingManager:
    """Quick logging setup with optional diagnostics"""
    manager = initialize_logging(config_path)
    
    if enable_diagnostics:
        setup_diagnostic_monitoring()
    
    return manager