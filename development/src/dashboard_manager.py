#!/usr/bin/env python3
"""
AICleaner V3 Dashboard Manager
Automatically creates and manages Home Assistant dashboard configuration
"""

import os
import json
import logging
import aiohttp
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class DashboardManager:
    """Manages automatic dashboard configuration for AICleaner zones"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.ha_url = os.getenv('HA_URL', 'http://supervisor/core')
        self.supervisor_token = os.getenv('SUPERVISOR_TOKEN')
        self.dashboard_id = 'aicleaner_v3_dashboard'
        
    async def setup_dashboard(self, zones: List[Dict[str, Any]]) -> bool:
        """Set up automatic dashboard configuration for zones"""
        try:
            if not self.supervisor_token:
                logger.warning("SUPERVISOR_TOKEN not available, skipping dashboard setup")
                return False
                
            dashboard_config = self.generate_dashboard_config(zones)
            success = await self.create_or_update_dashboard(dashboard_config)
            
            if success:
                logger.info(f"Successfully configured dashboard with {len(zones)} zones")
                return True
            else:
                logger.error("Failed to configure dashboard")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up dashboard: {e}")
            return False
    
    def generate_dashboard_config(self, zones: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate dashboard configuration from zones"""
        views = []
        
        # Main overview view
        overview_cards = [
            {
                "type": "markdown",
                "content": f"# 🤖 AI Cleaner v3\n\nManaging **{len(zones)}** zones with intelligent cleaning assistance.\n\nGenerated at {self.get_current_time()}"
            }
        ]
        
        # Add zone status cards
        if zones:
            zone_entities = []
            for zone in zones:
                if zone.get('camera_entity'):
                    zone_entities.append({
                        "type": "picture-entity",
                        "entity": zone['camera_entity'],
                        "name": f"{zone.get('name', 'Unknown Zone')} Camera",
                        "show_state": True,
                        "show_name": True
                    })
                
                if zone.get('todo_list_entity'):
                    zone_entities.append({
                        "type": "todo-list",
                        "entity": zone['todo_list_entity'],
                        "title": f"{zone.get('name', 'Unknown Zone')} Tasks"
                    })
            
            if zone_entities:
                overview_cards.extend(zone_entities)
        
        views.append({
            "title": "Overview",
            "path": "overview",
            "icon": "mdi:robot-vacuum",
            "cards": overview_cards
        })
        
        # Individual zone views
        for i, zone in enumerate(zones):
            zone_cards = []
            
            # Zone info card
            zone_info = f"**Purpose:** {zone.get('purpose', 'Not specified')}\n\n"
            zone_info += f"**Check Interval:** {zone.get('interval_minutes', 60)} minutes\n\n"
            
            if zone.get('ignore_rules'):
                zone_info += "**Ignore Rules:**\n"
                for rule in zone['ignore_rules']:
                    zone_info += f"- {rule}\n"
            
            zone_cards.append({
                "type": "markdown",
                "content": f"# 📍 {zone.get('name', 'Zone')}\n\n{zone_info}"
            })
            
            # Camera card
            if zone.get('camera_entity'):
                zone_cards.append({
                    "type": "picture-entity",
                    "entity": zone['camera_entity'],
                    "camera_view": "live",
                    "show_state": True,
                    "show_name": True
                })
            
            # Todo list card
            if zone.get('todo_list_entity'):
                zone_cards.append({
                    "type": "todo-list",
                    "entity": zone['todo_list_entity'],
                    "title": "Zone Tasks"
                })
            
            views.append({
                "title": zone.get('name', f'Zone {i+1}'),
                "path": f"zone_{i+1}",
                "icon": "mdi:home-map-marker",
                "cards": zone_cards
            })
        
        return {
            "title": "AI Cleaner v3",
            "views": views
        }
    
    async def create_or_update_dashboard(self, config: Dict[str, Any]) -> bool:
        """Create or update the dashboard in Home Assistant"""
        try:
            headers = {
                'Authorization': f'Bearer {self.supervisor_token}',
                'Content-Type': 'application/json'
            }
            
            # Check if dashboard exists
            dashboard_url = f"{self.ha_url}/api/lovelace/dashboards/{self.dashboard_id}"
            
            async with aiohttp.ClientSession() as session:
                # Try to get existing dashboard
                try:
                    async with session.get(dashboard_url, headers=headers, timeout=10) as response:
                        dashboard_exists = response.status == 200
                except aiohttp.ClientError:
                    dashboard_exists = False
                
                if dashboard_exists:
                    # Update existing dashboard
                    async with session.put(dashboard_url, headers=headers, json=config, timeout=10) as response:
                        if response.status == 200:
                            logger.info("Updated existing dashboard configuration")
                            return True
                        else:
                            logger.error(f"Failed to update dashboard: HTTP {response.status}")
                            return False
                else:
                    # Create new dashboard
                    create_url = f"{self.ha_url}/api/lovelace/dashboards"
                    dashboard_data = {
                        "id": self.dashboard_id,
                        "title": "AI Cleaner v3",
                        "icon": "mdi:robot-vacuum",
                        "show_in_sidebar": True,
                        "require_admin": False,
                        "config": config
                    }
                    
                    async with session.post(create_url, headers=headers, json=dashboard_data, timeout=10) as response:
                        if response.status == 201:
                            logger.info("Created new dashboard configuration")
                            return True
                        else:
                            logger.error(f"Failed to create dashboard: HTTP {response.status}")
                            return False
                            
        except Exception as e:
            logger.error(f"Error managing dashboard: {e}")
            return False
    
    async def remove_dashboard(self) -> bool:
        """Remove the AICleaner dashboard"""
        try:
            if not self.supervisor_token:
                return False
                
            headers = {
                'Authorization': f'Bearer {self.supervisor_token}',
                'Content-Type': 'application/json'
            }
            
            dashboard_url = f"{self.ha_url}/api/lovelace/dashboards/{self.dashboard_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.delete(dashboard_url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        logger.info("Removed AICleaner dashboard")
                        return True
                    else:
                        logger.warning(f"Failed to remove dashboard: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error removing dashboard: {e}")
            return False
    
    def get_current_time(self) -> str:
        """Get formatted current time"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async def sync_zones_to_dashboard(self) -> bool:
        """Sync current zones configuration to dashboard"""
        try:
            zones_file = '/data/zones.json'
            if os.path.exists(zones_file):
                with open(zones_file, 'r') as f:
                    zones = json.load(f)
                return await self.setup_dashboard(zones)
            else:
                logger.info("No zones configuration found, creating default dashboard")
                return await self.setup_dashboard([])
                
        except Exception as e:
            logger.error(f"Error syncing zones to dashboard: {e}")
            return False