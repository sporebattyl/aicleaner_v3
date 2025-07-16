"""
AICleaner Service Registry

This module handles automatic registration of AICleaner services with Home Assistant.
It reads service definitions from services.yaml and registers them via the Home Assistant API.
"""

import os
import yaml
import json
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """
    Handles automatic registration of AICleaner services with Home Assistant.
    
    This class:
    1. Reads service definitions from services.yaml
    2. Registers services with Home Assistant via API
    3. Handles service call routing to appropriate handlers
    4. Provides service status monitoring
    """
    
    def __init__(self, ha_client, addon_path: str = "/app"):
        """
        Initialize the service registry.
        
        Args:
            ha_client: Home Assistant API client instance
            addon_path: Path to the addon directory containing services.yaml
        """
        self.ha_client = ha_client
        self.addon_path = Path(addon_path)
        self.services_file = self.addon_path / "services.yaml"
        self.service_handlers = {}
        self.registered_services = []
        
    def load_service_definitions(self) -> Dict[str, Any]:
        """
        Load service definitions from services.yaml file.
        
        Returns:
            Dictionary containing service definitions
        """
        try:
            if not self.services_file.exists():
                logger.warning(f"Services file not found: {self.services_file}")
                return {}
                
            with open(self.services_file, 'r') as f:
                services = yaml.safe_load(f) or {}
                
            logger.info(f"Loaded {len(services)} service definitions from {self.services_file}")
            return services
            
        except Exception as e:
            logger.error(f"Error loading service definitions: {e}")
            return {}
            
    def register_service_handler(self, service_name: str, handler_func):
        """
        Register a handler function for a specific service.
        
        Args:
            service_name: Name of the service (e.g., 'run_analysis')
            handler_func: Function to call when service is invoked
        """
        self.service_handlers[service_name] = handler_func
        logger.debug(f"Registered handler for service: {service_name}")
        
    def register_services_with_ha(self) -> bool:
        """
        Register all services with Home Assistant via API.
        
        Returns:
            True if all services registered successfully, False otherwise
        """
        services = self.load_service_definitions()
        
        if not services:
            logger.warning("No services to register")
            return False
            
        success_count = 0
        total_count = len(services)
        
        for service_name, service_config in services.items():
            try:
                if self._register_single_service(service_name, service_config):
                    success_count += 1
                    self.registered_services.append(service_name)
                    
            except Exception as e:
                logger.error(f"Error registering service {service_name}: {e}")
                
        logger.info(f"Service registration complete: {success_count}/{total_count} successful")
        return success_count == total_count
        
    def _register_single_service(self, service_name: str, service_config: Dict[str, Any]) -> bool:
        """
        Register a single service with Home Assistant.
        
        Args:
            service_name: Name of the service
            service_config: Service configuration from services.yaml
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # For Home Assistant addons, services are automatically registered
            # when the services.yaml file exists and is properly formatted.
            # We just need to ensure our handlers are ready.
            
            logger.info(f"Service '{service_name}' ready for registration")
            logger.debug(f"Service config: {service_config}")
            
            # Validate service configuration
            if not isinstance(service_config, dict):
                logger.error(f"Invalid service config for {service_name}: must be a dictionary")
                return False
                
            if 'description' not in service_config:
                logger.warning(f"Service {service_name} missing description")
                
            # Service will be automatically registered by Home Assistant
            # when the addon restarts with the services.yaml file present
            return True
            
        except Exception as e:
            logger.error(f"Error in service registration for {service_name}: {e}")
            return False
            
    def handle_service_call(self, service_name: str, service_data: Dict[str, Any]) -> Any:
        """
        Handle a service call by routing to the appropriate handler.
        
        Args:
            service_name: Name of the service being called
            service_data: Data passed to the service call
            
        Returns:
            Result from the service handler
        """
        try:
            if service_name not in self.service_handlers:
                logger.error(f"No handler registered for service: {service_name}")
                return None
                
            handler = self.service_handlers[service_name]
            logger.info(f"Handling service call: {service_name} with data: {service_data}")
            
            result = handler(service_data)
            logger.debug(f"Service {service_name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error handling service call {service_name}: {e}")
            raise
            
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get status information about registered services.
        
        Returns:
            Dictionary containing service status information
        """
        return {
            'services_file_exists': self.services_file.exists(),
            'services_loaded': len(self.load_service_definitions()),
            'handlers_registered': len(self.service_handlers),
            'registered_services': self.registered_services.copy(),
            'available_handlers': list(self.service_handlers.keys())
        }
        
    def validate_service_definitions(self) -> List[str]:
        """
        Validate service definitions and return any issues found.
        
        Returns:
            List of validation error messages
        """
        issues = []
        services = self.load_service_definitions()
        
        if not services:
            issues.append("No service definitions found")
            return issues
            
        for service_name, service_config in services.items():
            # Validate service name
            if not service_name or not isinstance(service_name, str):
                issues.append(f"Invalid service name: {service_name}")
                continue
                
            # Validate service config
            if not isinstance(service_config, dict):
                issues.append(f"Service {service_name}: configuration must be a dictionary")
                continue
                
            # Check required fields
            if 'description' not in service_config:
                issues.append(f"Service {service_name}: missing required 'description' field")
                
            # Validate fields if present
            if 'fields' in service_config:
                fields = service_config['fields']
                if not isinstance(fields, dict):
                    issues.append(f"Service {service_name}: 'fields' must be a dictionary")
                else:
                    for field_name, field_config in fields.items():
                        if not isinstance(field_config, dict):
                            issues.append(f"Service {service_name}, field {field_name}: configuration must be a dictionary")
                            
        return issues
        
    def setup_default_handlers(self, aicleaner_instance):
        """
        Set up default service handlers for AICleaner services.
        
        Args:
            aicleaner_instance: Instance of the main AICleaner class
        """
        # Register handlers for all defined services
        self.register_service_handler('run_analysis', aicleaner_instance.handle_service_run_analysis)
        
        # Add handlers for additional services
        if hasattr(aicleaner_instance, 'handle_service_refresh_zones'):
            self.register_service_handler('refresh_zones', aicleaner_instance.handle_service_refresh_zones)
            
        if hasattr(aicleaner_instance, 'handle_service_toggle_zone'):
            self.register_service_handler('toggle_zone', aicleaner_instance.handle_service_toggle_zone)
            
        if hasattr(aicleaner_instance, 'handle_service_update_zone_config'):
            self.register_service_handler('update_zone_config', aicleaner_instance.handle_service_update_zone_config)
            
        if hasattr(aicleaner_instance, 'handle_service_get_zone_status'):
            self.register_service_handler('get_zone_status', aicleaner_instance.handle_service_get_zone_status)
            
        if hasattr(aicleaner_instance, 'handle_service_clear_zone_tasks'):
            self.register_service_handler('clear_zone_tasks', aicleaner_instance.handle_service_clear_zone_tasks)
            
        if hasattr(aicleaner_instance, 'handle_service_restart_addon'):
            self.register_service_handler('restart_addon', aicleaner_instance.handle_service_restart_addon)
            
        logger.info(f"Set up {len(self.service_handlers)} default service handlers")
        
    def log_service_registration_status(self):
        """Log detailed information about service registration status."""
        status = self.get_service_status()
        
        logger.info("=== Service Registration Status ===")
        logger.info(f"Services file exists: {status['services_file_exists']}")
        logger.info(f"Services loaded: {status['services_loaded']}")
        logger.info(f"Handlers registered: {status['handlers_registered']}")
        logger.info(f"Registered services: {', '.join(status['registered_services'])}")
        logger.info(f"Available handlers: {', '.join(status['available_handlers'])}")
        
        # Validate service definitions
        issues = self.validate_service_definitions()
        if issues:
            logger.warning("Service definition issues found:")
            for issue in issues:
                logger.warning(f"  - {issue}")
        else:
            logger.info("All service definitions are valid")
            
        logger.info("=== End Service Registration Status ===")
