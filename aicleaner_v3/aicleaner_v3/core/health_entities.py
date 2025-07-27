"""
Health Monitoring Entities for AICleaner Home Assistant Integration

This module manages the health monitoring entities that expose system health
metrics to Home Assistant, including health score, response time, and alerts.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from .system_monitor import HealthCheckResult


@dataclass
class HealthEntity:
    """Health monitoring entity configuration."""
    entity_id: str
    name: str
    entity_type: str  # "sensor" or "binary_sensor"
    icon: str
    unit_of_measurement: Optional[str] = None
    device_class: Optional[str] = None
    state_class: Optional[str] = None


class HealthEntityManager:
    """
    Manages health monitoring entities for Home Assistant integration.
    
    Features:
    - Creates and manages health score sensor
    - Creates and manages response time sensor  
    - Creates and manages health alert binary sensor
    - Updates entity states based on health check results
    - Handles entity registration and state management
    """
    
    def __init__(self, ha_client, config: Dict[str, Any]):
        """
        Initialize the Health Entity Manager.
        
        Args:
            ha_client: Home Assistant client for API communication
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.ha_client = ha_client
        self.config = config
        
        # Entity definitions
        self.entities = self._define_entities()
        
        # Current state tracking
        self.current_states = {}
        
        self.logger.info("Health Entity Manager initialized")
    
    def _define_entities(self) -> Dict[str, HealthEntity]:
        """Define the health monitoring entities."""
        return {
            "health_score": HealthEntity(
                entity_id="sensor.aicleaner_health_score",
                name="AICleaner Health Score",
                entity_type="sensor",
                icon="mdi:heart-pulse",
                unit_of_measurement="score",
                state_class="measurement"
            ),
            "response_time": HealthEntity(
                entity_id="sensor.aicleaner_average_response_time",
                name="AICleaner Average Response Time",
                entity_type="sensor",
                icon="mdi:timer",
                unit_of_measurement="ms",
                state_class="measurement"
            ),
            "health_alert": HealthEntity(
                entity_id="binary_sensor.aicleaner_health_alert",
                name="AICleaner Health Alert",
                entity_type="binary_sensor",
                icon="mdi:alert-circle",
                device_class="problem"
            )
        }
    
    async def initialize_entities(self):
        """Initialize all health monitoring entities in Home Assistant."""
        self.logger.info("Initializing health monitoring entities")
        
        try:
            # Initialize each entity with default state
            for entity_key, entity in self.entities.items():
                await self._initialize_entity(entity)
            
            self.logger.info("Health monitoring entities initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing health entities: {e}")
            raise
    
    async def _initialize_entity(self, entity: HealthEntity):
        """Initialize a single entity with default state."""
        try:
            # Set initial state based on entity type
            if entity.entity_type == "sensor":
                initial_state = 0
            elif entity.entity_type == "binary_sensor":
                initial_state = "off"
            else:
                initial_state = "unknown"
            
            # Create initial attributes
            attributes = {
                "friendly_name": entity.name,
                "icon": entity.icon,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            # Add entity-specific attributes
            if entity.unit_of_measurement:
                attributes["unit_of_measurement"] = entity.unit_of_measurement
            if entity.device_class:
                attributes["device_class"] = entity.device_class
            if entity.state_class:
                attributes["state_class"] = entity.state_class
            
            # Set initial state
            success = await self.ha_client.set_state(
                entity.entity_id, 
                initial_state, 
                attributes
            )
            
            if success:
                self.current_states[entity.entity_id] = {
                    "state": initial_state,
                    "attributes": attributes
                }
                self.logger.debug(f"Initialized entity {entity.entity_id}")
            else:
                self.logger.warning(f"Failed to initialize entity {entity.entity_id}")
                
        except Exception as e:
            self.logger.error(f"Error initializing entity {entity.entity_id}: {e}")
    
    async def update_from_health_check(self, health_result: HealthCheckResult):
        """
        Update all health entities based on health check results.
        
        Args:
            health_result: Health check result containing metrics
        """
        self.logger.info("Updating health entities from health check results")
        
        try:
            # Update health score sensor
            await self._update_health_score_sensor(health_result)
            
            # Update response time sensor
            await self._update_response_time_sensor(health_result)
            
            # Update health alert binary sensor
            await self._update_health_alert_sensor(health_result)
            
            self.logger.info("Health entities updated successfully")
            
        except Exception as e:
            self.logger.error(f"Error updating health entities: {e}")
    
    async def _update_health_score_sensor(self, health_result: HealthCheckResult):
        """Update the health score sensor."""
        entity = self.entities["health_score"]
        
        # Round health score to 1 decimal place
        health_score = round(health_result.health_score, 1)
        
        attributes = {
            "friendly_name": entity.name,
            "icon": entity.icon,
            "unit_of_measurement": entity.unit_of_measurement,
            "state_class": entity.state_class,
            "last_updated": health_result.timestamp,
            "test_duration": round(health_result.test_duration, 1),
            "total_tests": health_result.details.get("total_tests", 0),
            "successful_tests": health_result.details.get("successful_tests", 0),
            "failed_tests": health_result.details.get("failed_tests", 0)
        }
        
        await self._update_entity_state(entity.entity_id, health_score, attributes)
    
    async def _update_response_time_sensor(self, health_result: HealthCheckResult):
        """Update the response time sensor."""
        entity = self.entities["response_time"]
        
        # Round response time to nearest millisecond
        response_time = round(health_result.average_response_time)
        
        attributes = {
            "friendly_name": entity.name,
            "icon": entity.icon,
            "unit_of_measurement": entity.unit_of_measurement,
            "state_class": entity.state_class,
            "last_updated": health_result.timestamp,
            "min_response_time": round(health_result.details.get("min_response_time", 0)),
            "max_response_time": round(health_result.details.get("max_response_time", 0)),
            "error_rate": f"{health_result.error_rate:.1%}",
            "resource_pressure": f"{health_result.resource_pressure:.1%}"
        }
        
        await self._update_entity_state(entity.entity_id, response_time, attributes)
    
    async def _update_health_alert_sensor(self, health_result: HealthCheckResult):
        """Update the health alert binary sensor."""
        entity = self.entities["health_alert"]

        # Use performance warnings for the binary sensor (not critical alerts)
        performance_warnings = health_result.performance_warnings or []
        has_performance_warnings = bool(performance_warnings)
        state = "on" if has_performance_warnings else "off"

        attributes = {
            "friendly_name": entity.name,
            "icon": entity.icon,
            "device_class": entity.device_class,
            "last_updated": health_result.timestamp,
            "health_score": round(health_result.health_score, 1),
            "warning_count": len(performance_warnings),
            "critical_alert_count": len(health_result.critical_alerts or [])
        }

        # Add performance warning details
        if performance_warnings:
            attributes["reason"] = "; ".join(performance_warnings)
            attributes["performance_warnings"] = performance_warnings
        else:
            attributes["reason"] = "No performance issues detected"
            attributes["performance_warnings"] = []

        # Add critical alerts info (for reference, but these trigger separate notifications)
        if health_result.critical_alerts:
            attributes["critical_alerts"] = health_result.critical_alerts
        else:
            attributes["critical_alerts"] = []

        await self._update_entity_state(entity.entity_id, state, attributes)
    
    async def _update_entity_state(self, entity_id: str, state: Any, attributes: Dict[str, Any]):
        """Update an entity's state and attributes."""
        try:
            success = await self.ha_client.set_state(entity_id, state, attributes)
            
            if success:
                self.current_states[entity_id] = {
                    "state": state,
                    "attributes": attributes
                }
                self.logger.debug(f"Updated entity {entity_id} with state: {state}")
            else:
                self.logger.warning(f"Failed to update entity {entity_id}")
                
        except Exception as e:
            self.logger.error(f"Error updating entity {entity_id}: {e}")
    
    def get_entity_states(self) -> Dict[str, Any]:
        """Get current states of all health entities."""
        return self.current_states.copy()
    
    async def reset_entities(self):
        """Reset all entities to default states."""
        self.logger.info("Resetting health entities to default states")
        
        for entity_key, entity in self.entities.items():
            try:
                if entity.entity_type == "sensor":
                    await self._update_entity_state(entity.entity_id, 0, {
                        "friendly_name": entity.name,
                        "icon": entity.icon,
                        "last_updated": datetime.now(timezone.utc).isoformat()
                    })
                elif entity.entity_type == "binary_sensor":
                    await self._update_entity_state(entity.entity_id, "off", {
                        "friendly_name": entity.name,
                        "icon": entity.icon,
                        "reason": "System reset",
                        "last_updated": datetime.now(timezone.utc).isoformat()
                    })
            except Exception as e:
                self.logger.error(f"Error resetting entity {entity.entity_id}: {e}")
