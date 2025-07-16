import asyncio
import logging
import os
import time
import uuid
import json
import re
from enum import Enum, auto
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from PIL import Image
from .state_manager import AnalysisState
from .zone_manager import ZoneManager
from rules.ignore_rules_manager import IgnoreRulesManager
from ai.multi_model_ai import MultiModelAIOptimizer
from ai.predictive_analytics import PredictiveAnalytics
from ai.scene_understanding import AdvancedSceneUnderstanding
from notifications.notification_engine import NotificationEngine
from .analysis_queue import AnalysisQueueManager, AnalysisPriority

class ZoneAnalyzer:
    """
    Zone analyzer.

    Features:
    - Async queue management
    - Priority-based analysis
    - Resource limiting
    - Worker pool
    """

    def __init__(self, ha_client, state_manager, config, multi_model_ai_optimizer):
        """
        Initialize the zone analyzer.

        Args:
            ha_client: Home Assistant client
            gemini_client: Gemini client
            state_manager: State manager
            config: Configuration
        """
        self.ha_client = ha_client
        self.state_manager = state_manager
        self.config = config
        self.multi_model_ai_optimizer = multi_model_ai_optimizer
        self.logger = logging.getLogger("zone_analyzer")

        # Initialize queue manager
        self.queue_manager = AnalysisQueueManager(config)

        # Initialize managers for each zone
        self.zone_managers: Dict[str, ZoneManager] = {}
        self.zone_semaphores: Dict[str, asyncio.Semaphore] = {}

    @property
    def analysis_queue(self):
        """Expose the analysis queue for testing purposes."""
        return self.queue_manager.queue

    async def start(self):
        """Start the zone analyzer."""
        self.logger.info("Starting zone analyzer")
        self.running = True

        # Initialize zone semaphores and managers
        await self._initialize_zone_components()

        # Start the queue manager
        await self.queue_manager.start()

        self.logger.info("Zone analyzer started.")

    async def stop(self):
        """Stop the zone analyzer."""
        self.logger.info("Stopping zone analyzer")
        self.running = False

        # Stop the queue manager
        await self.queue_manager.stop()

        self.logger.info("Zone analyzer stopped.")

    async def queue_analysis(self, zone_name: str, priority: AnalysisPriority = AnalysisPriority.SCHEDULED) -> str:
        """
        Queue zone analysis.

        Args:
            zone_name: Zone name
            priority: Analysis priority

        Returns:
            Analysis ID
        """
        # Validate zone exists
        if not self._get_zone_config(zone_name):
            raise ValueError(f"Zone '{zone_name}' not found in configuration")

        # Create analysis function for this zone
        async def analysis_func(zone_name: str, analysis_id: str):
            await self._perform_zone_analysis(zone_name, analysis_id)

        # Queue the analysis using the queue manager
        analysis_id = await self.queue_manager.queue_analysis(
            zone_name=zone_name,
            priority=priority,
            analysis_func=analysis_func
        )

        self.logger.info(f"Queued analysis for zone {zone_name} with priority {priority.name} (ID: {analysis_id})")

        # Update state to indicate analysis has been queued
        await self.state_manager.update_analysis_state(
            analysis_id,
            AnalysisState.IMAGE_CAPTURED,
            {
                "zone_name": zone_name,
                "priority": priority.name
            }
        )

        return analysis_id

    async def _perform_zone_analysis(self, zone_name: str, analysis_id: str):
        """
        Perform analysis for a specific zone.

        Args:
            zone_name: Zone name
            analysis_id: Analysis ID
        """
        try:
            # Get zone manager
            zone_manager = self.zone_managers.get(zone_name)
            if not zone_manager:
                raise ValueError(f"Zone manager not found for zone: {zone_name}")

            # Capture image
            zone_config = self._get_zone_config(zone_name)
            image_path = await self.ha_client.capture_image(zone_config['camera_entity'])

            if not image_path:
                raise Exception("Failed to capture image")

            # Update state
            await self.state_manager.update_analysis_state(
                analysis_id,
                AnalysisState.IMAGE_CAPTURED,
                {"zone_name": zone_name, "image_path": image_path}
            )

            # Perform analysis using zone manager
            result = await zone_manager.analyze_image_batch_optimized(image_path)

            if result:
                # Update state to complete
                await self.state_manager.update_analysis_state(
                    analysis_id,
                    AnalysisState.CYCLE_COMPLETE,
                    {"zone_name": zone_name, "result": result}
                )
            else:
                raise Exception("Analysis failed")

        except Exception as e:
            self.logger.error(f"Error performing zone analysis for {zone_name}: {e}")
            raise

    async def _initialize_zone_components(self):
        """
        Initialize zone semaphores and managers.
        """
        # Get zones from config
        zones = self.config.get("zones", [])

        for zone_config in zones:
            zone_name = zone_config.get("name")

            if zone_name:
                # Get max concurrent analyses for zone
                max_concurrent = zone_config.get(
                    "max_concurrent_analyses",
                    self.config.get("max_concurrent_analyses", 2)
                )

                # Create semaphore
                self.zone_semaphores[zone_name] = asyncio.Semaphore(max_concurrent)
                # Initialize ZoneManager for each zone
                self.zone_managers[zone_name] = ZoneManager(
                    zone_config,
                    self.ha_client,
                    self.state_manager,
                    self.multi_model_ai_optimizer,
                    self.config
                )

        self.logger.info(f"Initialized components for {len(self.zone_semaphores)} zones")

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
