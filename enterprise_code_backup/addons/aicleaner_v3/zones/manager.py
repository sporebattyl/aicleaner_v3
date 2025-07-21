"""
Phase 3B: Zone Configuration Manager
Central orchestrator for zone creation, configuration, and optimization.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import Zone, Device, Rule
from .config import ZoneConfigEngine
from .optimization import ZoneOptimizationEngine
from .monitoring import ZonePerformanceMonitor
from .ha_integration import HomeAssistantIntegration
from .logger import setup_logger, ZoneContextLogger, ZoneOperationLogger
from .utils import retry, timing, validate_zone_id

# Import existing phase components
from ..devices.device_discovery import DeviceDiscoveryManager, DeviceInfo
from ..ai.monitoring.performance_monitor import AIPerformanceMonitor


class ZoneManager:
    """
    Central zone management system with intelligent automation and optimization.
    
    Provides comprehensive zone creation, configuration, monitoring, and adaptation
    capabilities with integration to existing AICleaner v3 phases.
    """
    
    def __init__(self, hass, config):
        """
        Initialize zone manager.
        
        Args:
            hass: Home Assistant instance
            config: Configuration dictionary
        """
        self.hass = hass
        self.config = config
        
        # Initialize components
        self.device_discovery = DeviceDiscoveryManager(hass, config)
        self.ai_performance_monitor = hass.data.get('ai_performance_monitor')
        self.config_engine = ZoneConfigEngine(config)
        self.optimization_engine = ZoneOptimizationEngine(config)
        self.performance_monitor = ZonePerformanceMonitor(hass, config)
        self.ha_integration = HomeAssistantIntegration(hass, config)
        
        # Zone storage
        self.zones: Dict[str, Zone] = {}
        self.zone_device_mapping: Dict[str, str] = {}  # device_id -> zone_id
        
        # Concurrency control
        self.lock = asyncio.Lock()
        
        # Logging
        self.logger = setup_logger(__name__)
        self.operation_logger = ZoneOperationLogger(self.logger)
        
        # Background tasks
        self._optimization_task = None
        self._monitoring_task = None
        self._running = False
        
        self.logger.info("Zone Manager initialized")
    
    async def start(self) -> None:
        """Start zone manager background tasks."""
        if self._running:
            return
        
        self._running = True
        
        # Start background tasks
        self._optimization_task = asyncio.create_task(self._optimization_loop())
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Initialize HA integration
        await self.ha_integration.initialize()
        
        self.logger.info("Zone Manager started")
    
    async def stop(self) -> None:
        """Stop zone manager background tasks."""
        self._running = False
        
        # Cancel background tasks
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Zone Manager stopped")
    
    @retry(exceptions=(Exception,), tries=3, delay=2.0)
    @timing
    async def create_zone(self, zone_config: Dict[str, Any]) -> Zone:
        """
        Create a new zone with comprehensive validation and setup.
        
        Args:
            zone_config: Zone configuration dictionary
            
        Returns:
            Created Zone object
            
        Raises:
            ValueError: If configuration is invalid
            Exception: If zone creation fails
        """
        async with self.lock:
            return await self.operation_logger.log_operation(
                'create_zone',
                zone_config.get('id', 'unknown'),
                zone_config.get('name', 'Unknown Zone'),
                self._create_zone_impl,
                zone_config
            )
    
    async def _create_zone_impl(self, zone_config: Dict[str, Any]) -> Zone:
        """Internal zone creation implementation."""
        # Validate configuration
        if not self.config_engine.validate_config(zone_config):
            raise ValueError(f"Invalid zone configuration for: {zone_config.get('name', 'Unnamed Zone')}")
        
        # Check for duplicate zone ID
        zone_id = zone_config['id']
        if not validate_zone_id(zone_id):
            raise ValueError(f"Invalid zone ID format: {zone_id}")
        
        if zone_id in self.zones:
            self.logger.warning(f"Zone with ID {zone_id} already exists. Updating existing zone.")
            return await self.update_zone(zone_id, zone_config)
        
        # Create zone object
        zone = Zone(**zone_config)
        
        # Initialize zone performance metrics
        zone.performance_metrics.zone_id = zone.id
        zone._update_performance_metrics()
        
        # Store zone
        self.zones[zone_id] = zone
        
        # Update device mappings
        for device in zone.devices:
            self.zone_device_mapping[device.id] = zone_id
        
        # Register with Home Assistant
        await self.ha_integration.register_zone(zone)
        
        # Start monitoring for this zone
        await self.performance_monitor.start_zone_monitoring(zone)
        
        # Report to AI performance monitor
        if self.ai_performance_monitor:
            self.ai_performance_monitor.record_cache_hit()  # Zone created successfully
        
        self.logger.info(f"Created zone: {zone.name} (ID: {zone.id}) with {len(zone.devices)} devices")
        
        return zone
    
    @retry(exceptions=(Exception,), tries=3, delay=2.0)
    @timing
    async def update_zone(self, zone_id: str, zone_config: Dict[str, Any]) -> Zone:
        """
        Update existing zone configuration.
        
        Args:
            zone_id: Zone identifier
            zone_config: Updated zone configuration
            
        Returns:
            Updated Zone object
            
        Raises:
            ValueError: If zone not found or configuration invalid
        """
        async with self.lock:
            return await self.operation_logger.log_operation(
                'update_zone',
                zone_id,
                zone_config.get('name', 'Unknown Zone'),
                self._update_zone_impl,
                zone_id,
                zone_config
            )
    
    async def _update_zone_impl(self, zone_id: str, zone_config: Dict[str, Any]) -> Zone:
        """Internal zone update implementation."""
        if zone_id not in self.zones:
            raise ValueError(f"Zone with ID {zone_id} not found")
        
        # Validate configuration
        if not self.config_engine.validate_config(zone_config):
            raise ValueError(f"Invalid configuration for zone ID {zone_id}")
        
        # Get existing zone
        existing_zone = self.zones[zone_id]
        
        # Update device mappings (remove old devices)
        for device in existing_zone.devices:
            if device.id in self.zone_device_mapping:
                del self.zone_device_mapping[device.id]
        
        # Create updated zone
        updated_zone = Zone(**zone_config)
        updated_zone.id = zone_id  # Ensure ID consistency
        updated_zone.date_created = existing_zone.date_created  # Preserve creation date
        updated_zone.last_modified = datetime.now()
        
        # Update device mappings (add new devices)
        for device in updated_zone.devices:
            self.zone_device_mapping[device.id] = zone_id
        
        # Store updated zone
        self.zones[zone_id] = updated_zone
        
        # Update Home Assistant integration
        await self.ha_integration.update_zone(updated_zone)
        
        self.logger.info(f"Updated zone: {updated_zone.name} (ID: {zone_id})")
        
        return updated_zone
    
    @retry(exceptions=(Exception,), tries=3, delay=2.0)
    @timing
    async def delete_zone(self, zone_id: str) -> bool:
        """
        Delete a zone and clean up resources.
        
        Args:
            zone_id: Zone identifier
            
        Returns:
            True if deletion successful
            
        Raises:
            ValueError: If zone not found
        """
        async with self.lock:
            return await self.operation_logger.log_operation(
                'delete_zone',
                zone_id,
                self.zones.get(zone_id, Zone(id=zone_id, name='Unknown')).name,
                self._delete_zone_impl,
                zone_id
            )
    
    async def _delete_zone_impl(self, zone_id: str) -> bool:
        """Internal zone deletion implementation."""
        if zone_id not in self.zones:
            raise ValueError(f"Zone with ID {zone_id} not found")
        
        zone = self.zones[zone_id]
        
        # Remove device mappings
        for device in zone.devices:
            if device.id in self.zone_device_mapping:
                del self.zone_device_mapping[device.id]
        
        # Stop monitoring
        await self.performance_monitor.stop_zone_monitoring(zone_id)
        
        # Remove from Home Assistant
        await self.ha_integration.remove_zone(zone)
        
        # Remove from storage
        del self.zones[zone_id]
        
        self.logger.info(f"Deleted zone: {zone.name} (ID: {zone_id})")
        
        return True
    
    async def get_zone(self, zone_id: str) -> Optional[Zone]:
        """
        Retrieve a zone by ID.
        
        Args:
            zone_id: Zone identifier
            
        Returns:
            Zone object or None if not found
        """
        async with self.lock:
            if zone_id not in self.zones:
                self.logger.warning(f"Zone with ID {zone_id} not found")
                return None
            
            return self.zones[zone_id]
    
    async def list_zones(self) -> List[Zone]:
        """
        List all zones.
        
        Returns:
            List of Zone objects
        """
        async with self.lock:
            return list(self.zones.values())
    
    async def add_device_to_zone(self, zone_id: str, device_info: DeviceInfo) -> bool:
        """
        Add a device to a zone.
        
        Args:
            zone_id: Target zone identifier
            device_info: Device information from discovery
            
        Returns:
            True if device added successfully
        """
        async with self.lock:
            if zone_id not in self.zones:
                self.logger.error(f"Zone {zone_id} not found")
                return False
            
            zone = self.zones[zone_id]
            
            # Convert DeviceInfo to Device model
            device = Device(
                id=device_info.mac_address,
                name=device_info.device_name or device_info.device_type,
                type=device_info.device_type,
                manufacturer=device_info.manufacturer,
                model=device_info.model,
                ip_address=device_info.ip_address,
                mac_address=device_info.mac_address,
                capabilities=device_info.capabilities,
                last_seen=device_info.last_seen
            )
            
            # Add device to zone
            zone.add_device(device)
            
            # Update device mapping
            self.zone_device_mapping[device.id] = zone_id
            
            # Update HA integration
            await self.ha_integration.update_zone(zone)
            
            self.logger.info(f"Added device {device.name} to zone {zone.name}")
            
            return True
    
    async def remove_device_from_zone(self, zone_id: str, device_id: str) -> bool:
        """
        Remove a device from a zone.
        
        Args:
            zone_id: Zone identifier
            device_id: Device identifier
            
        Returns:
            True if device removed successfully
        """
        async with self.lock:
            if zone_id not in self.zones:
                self.logger.error(f"Zone {zone_id} not found")
                return False
            
            zone = self.zones[zone_id]
            
            # Remove device from zone
            if zone.remove_device(device_id):
                # Update device mapping
                if device_id in self.zone_device_mapping:
                    del self.zone_device_mapping[device_id]
                
                # Update HA integration
                await self.ha_integration.update_zone(zone)
                
                self.logger.info(f"Removed device {device_id} from zone {zone.name}")
                return True
            
            return False
    
    async def execute_zone_automation(self, zone_id: str) -> Dict[str, Any]:
        """
        Execute all automation rules for a zone.
        
        Args:
            zone_id: Zone identifier
            
        Returns:
            Execution results dictionary
        """
        if zone_id not in self.zones:
            return {'success': False, 'error': 'Zone not found'}
        
        zone = self.zones[zone_id]
        execution_results = {
            'zone_id': zone_id,
            'zone_name': zone.name,
            'rules_executed': 0,
            'rules_successful': 0,
            'rules_failed': 0,
            'execution_time_ms': 0,
            'errors': []
        }
        
        start_time = datetime.now()
        
        # Execute enabled rules
        for rule in zone.get_enabled_rules():
            if rule.is_due_for_execution():
                execution_results['rules_executed'] += 1
                
                try:
                    rule_start_time = datetime.now()
                    
                    # Execute rule through config engine
                    await self.config_engine.execute_rule_action(zone, rule)
                    
                    rule_execution_time = (datetime.now() - rule_start_time).total_seconds() * 1000
                    rule.record_execution(True, rule_execution_time)
                    
                    execution_results['rules_successful'] += 1
                    
                    self.logger.info(f"Successfully executed rule {rule.name} in zone {zone.name}")
                    
                except Exception as e:
                    rule_execution_time = (datetime.now() - rule_start_time).total_seconds() * 1000
                    rule.record_execution(False, rule_execution_time, str(e))
                    
                    execution_results['rules_failed'] += 1
                    execution_results['errors'].append({
                        'rule_id': rule.id,
                        'rule_name': rule.name,
                        'error': str(e)
                    })
                    
                    self.logger.error(f"Failed to execute rule {rule.name} in zone {zone.name}: {e}")
        
        # Calculate total execution time
        execution_results['execution_time_ms'] = (datetime.now() - start_time).total_seconds() * 1000
        execution_results['success'] = execution_results['rules_failed'] == 0
        
        return execution_results
    
    async def optimize_zone(self, zone_id: str) -> Dict[str, Any]:
        """
        Optimize a zone using ML-based optimization engine.
        
        Args:
            zone_id: Zone identifier
            
        Returns:
            Optimization results dictionary
        """
        if zone_id not in self.zones:
            return {'success': False, 'error': 'Zone not found'}
        
        zone = self.zones[zone_id]
        
        try:
            # Perform optimization
            optimized_zone = await self.optimization_engine.optimize(zone)
            
            # Update zone if optimization successful
            if optimized_zone:
                self.zones[zone_id] = optimized_zone
                await self.ha_integration.update_zone(optimized_zone)
                
                self.logger.info(f"Successfully optimized zone {zone.name}")
                
                return {
                    'success': True,
                    'zone_id': zone_id,
                    'zone_name': zone.name,
                    'optimization_score': optimized_zone.performance_metrics.optimization_score,
                    'improvements': {
                        'device_efficiency': 'improved',
                        'automation_optimization': 'applied'
                    }
                }
            else:
                return {'success': False, 'error': 'Optimization failed'}
                
        except Exception as e:
            self.logger.error(f"Error optimizing zone {zone.name}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_zone_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive zone management statistics.
        
        Returns:
            Statistics dictionary
        """
        total_zones = len(self.zones)
        total_devices = sum(len(zone.devices) for zone in self.zones.values())
        total_rules = sum(len(zone.rules) for zone in self.zones.values())
        
        active_zones = len([zone for zone in self.zones.values() if zone.is_active])
        active_devices = sum(len(zone.get_active_devices()) for zone in self.zones.values())
        enabled_rules = sum(len(zone.get_enabled_rules()) for zone in self.zones.values())
        
        total_energy_consumption = sum(zone.calculate_energy_consumption() for zone in self.zones.values())
        average_health_score = sum(zone.get_zone_health_score() for zone in self.zones.values()) / max(total_zones, 1)
        
        return {
            'total_zones': total_zones,
            'active_zones': active_zones,
            'total_devices': total_devices,
            'active_devices': active_devices,
            'total_rules': total_rules,
            'enabled_rules': enabled_rules,
            'total_energy_consumption': total_energy_consumption,
            'average_health_score': average_health_score,
            'zone_details': {
                zone_id: {
                    'name': zone.name,
                    'device_count': len(zone.devices),
                    'rule_count': len(zone.rules),
                    'health_score': zone.get_zone_health_score(),
                    'energy_consumption': zone.calculate_energy_consumption(),
                    'is_active': zone.is_active
                }
                for zone_id, zone in self.zones.items()
            }
        }
    
    async def _optimization_loop(self) -> None:
        """Background optimization loop."""
        optimization_interval = self.config.get('optimization_interval_hours', 6) * 3600  # Convert to seconds
        
        while self._running:
            try:
                # Wait for optimization interval
                await asyncio.sleep(optimization_interval)
                
                if not self._running:
                    break
                
                # Optimize all zones with auto-optimization enabled
                for zone_id, zone in self.zones.items():
                    if zone.auto_optimization and zone.is_active:
                        try:
                            await self.optimize_zone(zone_id)
                        except Exception as e:
                            self.logger.error(f"Error in optimization loop for zone {zone.name}: {e}")
                
                self.logger.info("Completed optimization cycle for all zones")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        monitoring_interval = self.config.get('monitoring_interval_minutes', 5) * 60  # Convert to seconds
        
        while self._running:
            try:
                # Wait for monitoring interval
                await asyncio.sleep(monitoring_interval)
                
                if not self._running:
                    break
                
                # Update performance metrics for all zones
                for zone in self.zones.values():
                    try:
                        await self.performance_monitor.update_zone_metrics(zone)
                    except Exception as e:
                        self.logger.error(f"Error updating metrics for zone {zone.name}: {e}")
                
                self.logger.debug("Completed monitoring cycle for all zones")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_zone_manager():
        """Test zone manager functionality."""
        
        # Mock Home Assistant object
        class MockHass:
            def __init__(self):
                self.data = {}
        
        hass = MockHass()
        config = {
            'optimization_interval_hours': 1,
            'monitoring_interval_minutes': 1
        }
        
        # Initialize zone manager
        zone_manager = ZoneManager(hass, config)
        await zone_manager.start()
        
        # Test zone creation
        zone_config = {
            'id': 'living_room',
            'name': 'Living Room',
            'description': 'Main living area',
            'location': 'Ground Floor',
            'devices': [],
            'rules': []
        }
        
        zone = await zone_manager.create_zone(zone_config)
        print(f"Created zone: {zone.name}")
        
        # Test zone listing
        zones = await zone_manager.list_zones()
        print(f"Total zones: {len(zones)}")
        
        # Test statistics
        stats = await zone_manager.get_zone_statistics()
        print(f"Zone statistics: {stats}")
        
        # Cleanup
        await zone_manager.stop()
        print("Zone manager test completed!")
    
    # Run test
    asyncio.run(test_zone_manager())