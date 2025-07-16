"""
Mobile Integration for AICleaner
Provides mobile-specific features and optimizations
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class MobileFeature(Enum):
    """Mobile-specific features"""
    PUSH_NOTIFICATIONS = "push_notifications"
    LOCATION_AWARENESS = "location_awareness"
    VOICE_COMMANDS = "voice_commands"
    QUICK_ACTIONS = "quick_actions"
    OFFLINE_MODE = "offline_mode"
    GESTURE_CONTROLS = "gesture_controls"


@dataclass
class MobileConfig:
    """Mobile configuration settings"""
    enable_push_notifications: bool = True
    enable_location_awareness: bool = False
    enable_voice_commands: bool = False
    enable_quick_actions: bool = True
    enable_offline_mode: bool = False
    enable_gesture_controls: bool = True
    notification_sound: str = "default"
    vibration_pattern: str = "default"
    theme_preference: str = "auto"  # auto, light, dark
    compact_mode: bool = False


@dataclass
class QuickAction:
    """Represents a quick action for mobile interface"""
    id: str
    title: str
    icon: str
    action_type: str  # service_call, navigation, toggle
    target: str
    parameters: Dict[str, Any]
    enabled: bool = True


class MobileIntegration:
    """
    Mobile integration system for AICleaner
    
    Features:
    - Mobile-optimized interface configurations
    - Push notification management
    - Quick action shortcuts
    - Gesture control support
    - Location-aware features
    - Offline mode capabilities
    """
    
    def __init__(self, config_path: str = "/data/mobile"):
        """
        Initialize mobile integration system
        
        Args:
            config_path: Path to store mobile configuration
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure config directory exists
        os.makedirs(config_path, exist_ok=True)
        
        # Load mobile configuration
        self.mobile_config = self._load_mobile_config()
        self.quick_actions = self._load_quick_actions()
        
        self.logger.info("Mobile integration system initialized")
    
    def _load_mobile_config(self) -> MobileConfig:
        """Load mobile configuration from file"""
        config_file = os.path.join(self.config_path, "mobile_config.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                return MobileConfig(**data)
            except Exception as e:
                self.logger.error(f"Error loading mobile config: {e}")
        
        # Return default configuration
        return MobileConfig()
    
    def _save_mobile_config(self):
        """Save mobile configuration to file"""
        config_file = os.path.join(self.config_path, "mobile_config.json")
        
        try:
            with open(config_file, 'w') as f:
                json.dump(asdict(self.mobile_config), f, indent=2)
            self.logger.debug("Mobile configuration saved")
        except Exception as e:
            self.logger.error(f"Error saving mobile config: {e}")
    
    def _load_quick_actions(self) -> List[QuickAction]:
        """Load quick actions configuration"""
        actions_file = os.path.join(self.config_path, "quick_actions.json")
        
        if os.path.exists(actions_file):
            try:
                with open(actions_file, 'r') as f:
                    data = json.load(f)
                return [QuickAction(**action) for action in data]
            except Exception as e:
                self.logger.error(f"Error loading quick actions: {e}")
        
        # Return default quick actions
        return self._get_default_quick_actions()
    
    def _get_default_quick_actions(self) -> List[QuickAction]:
        """Get default quick actions for mobile interface"""
        return [
            QuickAction(
                id="analyze_all",
                title="Analyze All Zones",
                icon="mdi:magnify-scan",
                action_type="service_call",
                target="aicleaner.analyze_all_zones",
                parameters={}
            ),
            QuickAction(
                id="emergency_clean",
                title="Emergency Clean",
                icon="mdi:alert-circle",
                action_type="service_call",
                target="aicleaner.emergency_clean",
                parameters={"priority": "high"}
            ),
            QuickAction(
                id="pause_all",
                title="Pause All",
                icon="mdi:pause",
                action_type="service_call",
                target="aicleaner.pause_all",
                parameters={}
            ),
            QuickAction(
                id="view_analytics",
                title="View Analytics",
                icon="mdi:chart-line",
                action_type="navigation",
                target="analytics",
                parameters={}
            ),
            QuickAction(
                id="quick_settings",
                title="Quick Settings",
                icon="mdi:cog-outline",
                action_type="navigation",
                target="config",
                parameters={}
            )
        ]
    
    def _save_quick_actions(self):
        """Save quick actions to file"""
        actions_file = os.path.join(self.config_path, "quick_actions.json")
        
        try:
            with open(actions_file, 'w') as f:
                json.dump([asdict(action) for action in self.quick_actions], f, indent=2)
            self.logger.debug("Quick actions saved")
        except Exception as e:
            self.logger.error(f"Error saving quick actions: {e}")
    
    def get_mobile_config(self) -> Dict[str, Any]:
        """Get current mobile configuration"""
        return asdict(self.mobile_config)
    
    def update_mobile_config(self, updates: Dict[str, Any]) -> bool:
        """
        Update mobile configuration
        
        Args:
            updates: Dictionary of configuration updates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update configuration
            for key, value in updates.items():
                if hasattr(self.mobile_config, key):
                    setattr(self.mobile_config, key, value)
            
            # Save updated configuration
            self._save_mobile_config()
            
            self.logger.info(f"Mobile configuration updated: {list(updates.keys())}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating mobile config: {e}")
            return False
    
    def get_quick_actions(self) -> List[Dict[str, Any]]:
        """Get current quick actions"""
        return [asdict(action) for action in self.quick_actions if action.enabled]
    
    def add_quick_action(self, action_data: Dict[str, Any]) -> bool:
        """
        Add a new quick action
        
        Args:
            action_data: Quick action configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            action = QuickAction(**action_data)
            self.quick_actions.append(action)
            self._save_quick_actions()
            
            self.logger.info(f"Quick action added: {action.title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding quick action: {e}")
            return False
    
    def remove_quick_action(self, action_id: str) -> bool:
        """
        Remove a quick action
        
        Args:
            action_id: ID of the action to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.quick_actions = [action for action in self.quick_actions if action.id != action_id]
            self._save_quick_actions()
            
            self.logger.info(f"Quick action removed: {action_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing quick action: {e}")
            return False
    
    def get_mobile_optimized_layout(self, screen_size: str = "mobile") -> Dict[str, Any]:
        """
        Get mobile-optimized layout configuration
        
        Args:
            screen_size: Screen size category (mobile, tablet, desktop)
            
        Returns:
            Layout configuration
        """
        layouts = {
            "mobile": {
                "grid_columns": 1,
                "card_padding": "12px",
                "font_size": "14px",
                "button_height": "44px",
                "compact_mode": True,
                "show_icons": True,
                "show_descriptions": False,
                "max_items_per_view": 5
            },
            "tablet": {
                "grid_columns": 2,
                "card_padding": "16px",
                "font_size": "15px",
                "button_height": "40px",
                "compact_mode": False,
                "show_icons": True,
                "show_descriptions": True,
                "max_items_per_view": 8
            },
            "desktop": {
                "grid_columns": 3,
                "card_padding": "20px",
                "font_size": "16px",
                "button_height": "36px",
                "compact_mode": False,
                "show_icons": True,
                "show_descriptions": True,
                "max_items_per_view": 12
            }
        }
        
        return layouts.get(screen_size, layouts["mobile"])
    
    def generate_mobile_manifest(self) -> Dict[str, Any]:
        """
        Generate Progressive Web App manifest for mobile installation
        
        Returns:
            PWA manifest configuration
        """
        return {
            "name": "AICleaner",
            "short_name": "AICleaner",
            "description": "Intelligent Multi-Zone Cleanliness Management",
            "start_url": "/local/aicleaner/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#2196f3",
            "orientation": "portrait-primary",
            "icons": [
                {
                    "src": "/local/aicleaner/icons/icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "/local/aicleaner/icons/icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ],
            "categories": ["productivity", "utilities"],
            "lang": "en",
            "dir": "ltr"
        }
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Get mobile notification configuration"""
        return {
            "enabled": self.mobile_config.enable_push_notifications,
            "sound": self.mobile_config.notification_sound,
            "vibration": self.mobile_config.vibration_pattern,
            "badge": True,
            "actions": [
                {
                    "action": "view",
                    "title": "View Details",
                    "icon": "/local/aicleaner/icons/view.png"
                },
                {
                    "action": "dismiss",
                    "title": "Dismiss",
                    "icon": "/local/aicleaner/icons/dismiss.png"
                }
            ]
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get mobile integration system status"""
        return {
            "mobile_config_loaded": bool(self.mobile_config),
            "quick_actions_count": len(self.quick_actions),
            "enabled_features": [
                feature.value for feature in MobileFeature
                if getattr(self.mobile_config, f"enable_{feature.value}", False)
            ],
            "config_path": self.config_path,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
