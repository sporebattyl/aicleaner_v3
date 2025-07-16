"""
Zone scheduler for AI Cleaner addon.
Handles zone scheduling and analysis triggering.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .analyzer import AnalysisPriority

class ZoneScheduler:
    """
    Zone scheduler.
    
    Features:
    - Scheduled zone analysis
    - Dynamic scheduling based on cleanliness
    - Manual analysis triggering
    """
    
    def __init__(self, zone_analyzer, config):
        """
        Initialize the zone scheduler.
        
        Args:
            zone_analyzer: Zone analyzer
            state_manager: State manager
            config: Configuration
        """
        self.zone_analyzer = zone_analyzer
        self.config = config
        
        self.logger = logging.getLogger("zone_scheduler")
        
        # Zone schedules
        self.zone_schedules = {}
        
        # Running flag
        self.running = False
        
        # Scheduler task
        self.scheduler_task = None
        
    async def start(self):
        """Start the zone scheduler."""
        self.logger.info("Starting zone scheduler")
        self.running = True
        
        # Initialize zone schedules
        await self._initialize_zone_schedules()
        
        # Start scheduler loop
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
    async def stop(self):
        """Stop the zone scheduler."""
        self.logger.info("Stopping zone scheduler")
        self.running = False
        
        # Cancel scheduler task
        if self.scheduler_task:
            self.scheduler_task.cancel()
            
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
                
        self.scheduler_task = None
        
        self.logger.info("Zone scheduler stopped")
        
    async def trigger_analysis(self, zone_name: str, priority: AnalysisPriority = AnalysisPriority.MANUAL) -> str:
        """
        Trigger zone analysis.
        
        Args:
            zone_name: Zone name
            priority: Analysis priority
            
        Returns:
            Analysis ID
        """
        # Queue analysis
        analysis_id = await self.zone_analyzer.queue_analysis(zone_name, priority)
        
        # Update next analysis time
        if zone_name in self.zone_schedules:
            # Get update frequency
            zone_config = self._get_zone_config(zone_name)
            update_frequency = zone_config.get("update_frequency", 6)  # Default: 6 hours
            
            # Calculate next analysis time
            next_analysis = datetime.now(timezone.utc) + timedelta(hours=update_frequency)
            
            # Update schedule
            self.zone_schedules[zone_name]["next_analysis"] = next_analysis
            
            self.logger.info(f"Updated next analysis time for zone {zone_name}: {next_analysis.isoformat()}")
            
        return analysis_id
        
    async def _initialize_zone_schedules(self):
        """Initialize zone schedules."""
        # Get zones from config
        zones = self.config.get("zones", [])
        
        for zone in zones:
            zone_name = zone.get("name")
            
            if zone_name:
                # Get update frequency
                update_frequency = zone.get("update_frequency", 6)  # Default: 6 hours
                
                # Calculate initial analysis time (staggered)
                initial_delay = len(self.zone_schedules) * 10  # 10 seconds between zones
                initial_analysis = datetime.now(timezone.utc) + timedelta(seconds=initial_delay)
                
                # Create schedule
                self.zone_schedules[zone_name] = {
                    "update_frequency": update_frequency,
                    "next_analysis": initial_analysis
                }
                
        self.logger.info(f"Initialized schedules for {len(self.zone_schedules)} zones")
        
    async def _scheduler_loop(self):
        """Scheduler loop."""
        try:
            while self.running:
                # Check for zones that need analysis
                await self._check_schedules()
                
                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            # Task cancelled
            pass
            
        except Exception as e:
            self.logger.error(f"Error in scheduler loop: {e}")
            
    async def _check_schedules(self):
        """Check zone schedules."""
        now = datetime.now(timezone.utc)
        
        for zone_name, schedule in self.zone_schedules.items():
            next_analysis = schedule.get("next_analysis")
            
            if next_analysis and now >= next_analysis:
                # Time to analyze zone
                self.logger.info(f"Scheduled analysis for zone {zone_name}")
                
                # Trigger analysis
                await self.trigger_analysis(zone_name, AnalysisPriority.SCHEDULED)
                
    def _get_zone_config(self, zone_name: str) -> Dict[str, Any]:
        """
        Get zone configuration.
        
        Args:
            zone_name: Zone name
            
        Returns:
            Zone configuration
        """
        # Get zones from config
        zones = self.config.get("zones", [])
        
        # Find zone
        for zone in zones:
            if zone.get("name") == zone_name:
                return zone
                
        return None


