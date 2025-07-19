"""
Real-time Configuration Synchronization Module for AICleaner v3

This module provides real-time configuration synchronization capabilities
for AICleaner v3, enabling configuration changes to be synchronized across
multiple instances in real-time.

Key Features:
- Event-driven configuration synchronization
- WebSocket-based real-time communication
- Conflict resolution with last-write-wins strategy
- Integration with configuration versioning system
- Network resilience and graceful failure handling
- Home Assistant addon optimized deployment

Classes:
    SyncMessage: Message format for configuration sync
    ConfigWatcher: Watches configuration files for changes
    ConfigSyncServer: WebSocket server for configuration sync
    ConfigSyncClient: WebSocket client for configuration sync
    ConfigSyncManager: Main synchronization manager

Factory Functions:
    create_single_instance_sync: Create sync manager for single instance
    create_ha_addon_sync: Create sync manager for Home Assistant addon
    create_development_sync: Create sync manager for development environment
"""

from .config_sync import (
    SyncMessage,
    ConfigWatcher,
    ConfigSyncServer,
    ConfigSyncClient,
    ConfigSyncManager,
    create_single_instance_sync,
    create_ha_addon_sync,
    create_development_sync
)

__all__ = [
    'SyncMessage',
    'ConfigWatcher',
    'ConfigSyncServer',
    'ConfigSyncClient',
    'ConfigSyncManager',
    'create_single_instance_sync',
    'create_ha_addon_sync',
    'create_development_sync'
]

__version__ = '1.0.0'
__author__ = 'AICleaner v3 Development Team'
__description__ = 'Real-time Configuration Synchronization for AICleaner v3'

# Default configuration for Home Assistant addon
DEFAULT_ADDON_CONFIG = {
    'sync_port': 8765,
    'peer_urls': [],
    'enable_sync_server': False,
    'conflict_resolution': 'last_write_wins',
    'max_versions': 10,
    'watch_interval': 1.0,
    'reconnect_delay': 5.0,
    'heartbeat_interval': 30.0
}

# Default configuration for development environment
DEFAULT_DEV_CONFIG = {
    'sync_port': 8765,
    'peer_urls': [],
    'enable_sync_server': True,
    'conflict_resolution': 'last_write_wins',
    'max_versions': 50,
    'watch_interval': 0.5,
    'reconnect_delay': 2.0,
    'heartbeat_interval': 10.0
}

def get_default_config(deployment_type: str = 'addon'):
    """
    Get default configuration for specific deployment type.
    
    Args:
        deployment_type: 'addon', 'development', or 'production'
        
    Returns:
        Dictionary with default configuration
    """
    if deployment_type == 'addon':
        return DEFAULT_ADDON_CONFIG.copy()
    elif deployment_type == 'development':
        return DEFAULT_DEV_CONFIG.copy()
    elif deployment_type == 'production':
        return {
            'sync_port': 8765,
            'peer_urls': [],
            'enable_sync_server': True,
            'conflict_resolution': 'last_write_wins',
            'max_versions': 20,
            'watch_interval': 2.0,
            'reconnect_delay': 10.0,
            'heartbeat_interval': 60.0
        }
    else:
        raise ValueError(f"Unknown deployment type: {deployment_type}")

def validate_sync_config(config: dict) -> bool:
    """
    Validate synchronization configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid, False otherwise
    """
    required_keys = ['sync_port', 'peer_urls', 'enable_sync_server']
    
    for key in required_keys:
        if key not in config:
            return False
    
    # Validate types
    if not isinstance(config['sync_port'], int):
        return False
    if not isinstance(config['peer_urls'], list):
        return False
    if not isinstance(config['enable_sync_server'], bool):
        return False
    
    # Validate port range
    if not (1 <= config['sync_port'] <= 65535):
        return False
    
    # Validate peer URLs
    for url in config['peer_urls']:
        if not isinstance(url, str) or not url.startswith('ws://'):
            return False
    
    return True

def create_sync_manager_from_config(config_path: str, config_base_dir: str, 
                                   sync_config: dict, deployment_type: str = 'addon'):
    """
    Create configuration sync manager from configuration.
    
    Args:
        config_path: Path to configuration file
        config_base_dir: Base directory for configuration
        sync_config: Synchronization configuration
        deployment_type: Type of deployment ('addon', 'development', 'production')
        
    Returns:
        ConfigSyncManager instance
    """
    if not validate_sync_config(sync_config):
        raise ValueError("Invalid synchronization configuration")
    
    if deployment_type == 'addon':
        return create_ha_addon_sync(config_path, config_base_dir, sync_config)
    elif deployment_type == 'development':
        return create_development_sync(config_path, config_base_dir)
    elif deployment_type == 'production':
        return ConfigSyncManager(
            config_path=config_path,
            config_base_dir=config_base_dir,
            sync_port=sync_config['sync_port'],
            peer_urls=sync_config['peer_urls'],
            enable_server=sync_config['enable_sync_server']
        )
    else:
        raise ValueError(f"Unknown deployment type: {deployment_type}")

# Logging configuration
import logging
from utils.unified_logger import get_logger

logger = get_logger(__name__)

def setup_sync_logging(level: str = 'INFO'):
    """
    Setup logging for synchronization module.
    
    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    """
    logger.setLevel(getattr(logging, level.upper()))
    logger.info(f"Configuration sync module initialized with logging level: {level}")

# Initialize logging
setup_sync_logging()