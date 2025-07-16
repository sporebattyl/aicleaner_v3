"""
Performance monitor for AI Cleaner addon.
Tracks and reports performance metrics.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

class PerformanceMonitor:
    """
    Performance monitor.
    
    Features:
    - Analysis duration tracking
    - API call tracking
    - Cost estimation
    - HA sensor updates
    """
    
    def __init__(self, ha_client, state_manager, config):
        """
        Initialize the performance monitor.
        
        Args:
            ha_client: Home Assistant client
            state_manager: State manager
            config: Configuration
        """
        self.ha_client = ha_client
        self.state_manager = state_manager
        self.config = config
        
        self.logger = logging.getLogger("performance_monitor")
        
        # Update interval
        self.update_interval = config.get("performance_update_interval", 300)  # 5 minutes
        
        # Running flag
        self.running = False
        
        # Update task
        self.update_task = None
        
    async def initialize(self):
        """Initialize the performance monitor."""
        self.logger.info("Initializing performance monitor")
        
        # Start update loop
        self.update_task = asyncio.create_task(self._update_loop())
        
    async def shutdown(self):
        """
        Shutdown the performance monitor.
        """
        self.logger.info("Shutting down performance monitor")
        self.running = False
        
        # Cancel update task
        if self.update_task:
            self.update_task.cancel()
            
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
                
        self.update_task = None
        
        self.logger.info("Performance monitor shut down")
        
    async def _update_loop(self):
        """
        Update loop.
        """
        try:
            # Initial update
            await self._update_sensors()
            
            # Update loop
            while self.running:
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
                # Update sensors
                await self._update_sensors()
                
        except asyncio.CancelledError:
            # Task cancelled
            pass
            
        except Exception as e:
            self.logger.error(f"Error in update loop: {e}")
            
    async def _update_sensors(self):
        """
        Update sensors.
        """
        try:
            # Update analysis duration sensor
            await self._update_analysis_duration_sensor()
            
            # Update API calls sensor
            await self._update_api_calls_sensor()
            
            # Update cost estimate sensor
            await self._update_cost_estimate_sensor()
            
        except Exception as e:
            self.logger.error(f"Error updating sensors: {e}")
            
    async def _update_analysis_duration_sensor(self):
        """
        Update analysis duration sensor.
        """
        try:
            # Get analysis duration stats
            stats = await self.state_manager.get_analysis_duration_stats()
            
            # Format average duration
            average_duration = stats.get("average", 0.0)
            formatted_duration = f"{average_duration:.2f}"
            
            # Update sensor
            await self.ha_client.update_sensor(
                "sensor.aicleaner_analysis_duration_average",
                formatted_duration,
                {
                    "unit_of_measurement": "seconds",
                    "min": stats.get("min", 0.0),
                    "max": stats.get("max", 0.0),
                    "count": stats.get("count", 0),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "friendly_name": "AI Cleaner Average Analysis Duration",
                    "icon": "mdi:timer-sand"
                }
            )
            
            self.logger.debug(f"Updated analysis duration sensor: {formatted_duration} seconds")
            
        except Exception as e:
            self.logger.error(f"Error updating analysis duration sensor: {e}")
            
    async def _update_api_calls_sensor(self):
        """
        Update API calls sensor.
        """
        try:
            # Get API calls today
            api_calls = await self.state_manager.get_api_calls_today()
            
            # Update sensor
            await self.ha_client.update_sensor(
                "sensor.aicleaner_api_calls_today",
                api_calls,
                {
                    "unit_of_measurement": "calls",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "friendly_name": "AI Cleaner API Calls Today",
                    "icon": "mdi:cloud-upload"
                }
            )
            
            self.logger.debug(f"Updated API calls sensor: {api_calls} calls today")
            
        except Exception as e:
            self.logger.error(f"Error updating API calls sensor: {e}")
            
    async def _update_cost_estimate_sensor(self):
        """
        Update cost estimate sensor.
        """
        try:
            # Get cost estimate today
            cost_estimate = await self.state_manager.get_cost_estimate_today()
            
            # Format cost estimate
            formatted_cost = f"{cost_estimate:.4f}"
            
            # Update sensor
            await self.ha_client.update_sensor(
                "sensor.aicleaner_cost_estimate_today",
                formatted_cost,
                {
                    "unit_of_measurement": "USD",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "friendly_name": "AI Cleaner Estimated Cost Today",
                    "icon": "mdi:currency-usd"
                }
            )
            
            self.logger.debug(f"Updated cost estimate sensor: ${formatted_cost} today")
            
        except Exception as e:
            self.logger.error(f"Error updating cost estimate sensor: {e}")