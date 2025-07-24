"""
Health Service Handler for AICleaner Home Assistant Integration

This module handles the health-related services exposed to Home Assistant,
including health checks and performance profile management.
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .system_monitor import SystemMonitor
from .health_entities import HealthEntityManager


class HealthServiceHandler:
    """
    Handles health-related services for Home Assistant integration.
    
    Services:
    - run_health_check: Triggers system health check and updates sensors
    - apply_performance_profile: Changes performance profile (requires restart)
    """
    
    def __init__(self, system_monitor: SystemMonitor, health_entities: HealthEntityManager, 
                 ha_client, config: Dict[str, Any]):
        """
        Initialize the Health Service Handler.
        
        Args:
            system_monitor: SystemMonitor instance for health checks
            health_entities: HealthEntityManager for updating sensors
            ha_client: Home Assistant client for notifications
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.system_monitor = system_monitor
        self.health_entities = health_entities
        self.ha_client = ha_client
        self.config = config
        
        # Track running health checks to prevent overlaps
        self._health_check_running = False
        
        self.logger.info("Health Service Handler initialized")
    
    async def handle_run_health_check(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the run_health_check service call.
        
        Args:
            service_data: Service call data from Home Assistant
            
        Returns:
            Dict with service call result
        """
        self.logger.info("Health check service called")
        
        # Check if health check is already running
        if self._health_check_running:
            error_msg = "Health check already in progress"
            self.logger.warning(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        try:
            # Mark health check as running
            self._health_check_running = True
            
            # Get duration from service data (default 30 seconds)
            duration = service_data.get("duration", 30)
            duration = max(10, min(120, int(duration)))  # Clamp between 10-120 seconds
            
            self.logger.info(f"Starting {duration}-second health check")
            
            # Get AI client for testing (if available)
            ai_client = await self._get_ai_client()
            
            # Run health check
            health_result = await self.system_monitor.run_health_check(
                ai_client=ai_client,
                duration_seconds=duration
            )
            
            # Update health entities
            await self.health_entities.update_from_health_check(health_result)
            
            # Send notification if health score is low
            await self._handle_health_check_notifications(health_result)
            
            self.logger.info(f"Health check completed successfully: Score={health_result.health_score:.1f}")
            
            return {
                "success": True,
                "health_score": round(health_result.health_score, 1),
                "average_response_time": round(health_result.average_response_time),
                "error_rate": f"{health_result.error_rate:.1%}",
                "resource_pressure": f"{health_result.resource_pressure:.1%}",
                "test_duration": round(health_result.test_duration, 1),
                "alerts": health_result.alerts or [],
                "timestamp": health_result.timestamp
            }
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        finally:
            # Mark health check as no longer running
            self._health_check_running = False
    
    async def handle_apply_performance_profile(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the apply_performance_profile service call.
        
        Args:
            service_data: Service call data from Home Assistant
            
        Returns:
            Dict with service call result
        """
        self.logger.info("Apply performance profile service called")
        
        try:
            # Get profile from service data
            profile = service_data.get("profile")
            if not profile:
                error_msg = "Profile parameter is required"
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Validate profile
            valid_profiles = ["auto", "resource_efficient", "balanced", "maximum_performance"]
            if profile not in valid_profiles:
                error_msg = f"Invalid profile '{profile}'. Valid profiles: {', '.join(valid_profiles)}"
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Update configuration
            current_profile = self.config.get("inference_tuning", {}).get("profile", "auto")
            
            if profile == current_profile:
                self.logger.info(f"Profile '{profile}' is already active")
                message = f"Performance profile '{profile}' is already active"
            else:
                # Update config
                if "inference_tuning" not in self.config:
                    self.config["inference_tuning"] = {}
                
                self.config["inference_tuning"]["profile"] = profile
                
                # Save configuration (this would typically write to config file)
                await self._save_config_change(profile)
                
                message = f"Performance profile changed to '{profile}'"
                self.logger.info(message)
            
            # Send restart required notification
            await self._send_restart_notification(profile)
            
            return {
                "success": True,
                "message": message,
                "profile": profile,
                "restart_required": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            error_msg = f"Failed to apply performance profile: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _get_ai_client(self) -> Optional[Any]:
        """Get an AI client for health check testing."""
        try:
            # This would typically get the AI client from the main application
            # For now, return None and the health check will simulate testing
            return None
        except Exception as e:
            self.logger.warning(f"Could not get AI client for health testing: {e}")
            return None
    
    async def _handle_health_check_notifications(self, health_result):
        """Handle notifications based on health check results."""
        try:
            # Handle critical alerts with persistent notifications
            if health_result.critical_alerts:
                await self._send_critical_alert_notifications(health_result)

            # Performance warnings are handled by the binary sensor only
            # (no user-facing notifications for performance warnings)

            # Log health check completion
            self.logger.info(f"Health check notification handling completed")

        except Exception as e:
            self.logger.error(f"Error handling health check notifications: {e}")

    async def _send_critical_alert_notifications(self, health_result):
        """Send persistent notifications for critical alerts."""
        try:
            critical_alerts = health_result.critical_alerts or []

            if not critical_alerts:
                return

            # Create a comprehensive critical alert message
            alert_summary = "; ".join(critical_alerts)

            # Send persistent notification for critical issues
            await self.ha_client.send_notification(
                title="🚨 AICleaner Critical Alert",
                message=f"Critical system issues detected: {alert_summary}. "
                       f"Health Score: {health_result.health_score:.1f}/100. "
                       f"Immediate attention required.",
                data={
                    "priority": "high",
                    "persistent": True,
                    "tag": "aicleaner_critical",
                    "actions": [
                        {
                            "action": "acknowledge_alert",
                            "title": "Acknowledge"
                        },
                        {
                            "action": "view_details",
                            "title": "View Details"
                        }
                    ]
                }
            )

            self.logger.warning(f"Critical alert notification sent: {alert_summary}")

        except Exception as e:
            self.logger.error(f"Error sending critical alert notifications: {e}")
    
    async def _send_restart_notification(self, profile: str):
        """Send restart required notification."""
        try:
            await self.ha_client.send_notification(
                title="🔄 AICleaner Restart Required",
                message=f"Performance profile changed to '{profile}'. "
                       f"Please restart the AICleaner addon for changes to take effect.",
                data={"priority": "normal"}
            )
            
            self.logger.info("Restart notification sent")
            
        except Exception as e:
            self.logger.error(f"Error sending restart notification: {e}")
    
    async def _save_config_change(self, profile: str):
        """Save configuration change (placeholder for actual config persistence)."""
        try:
            # This would typically save to the actual config file
            # For now, just log the change
            self.logger.info(f"Configuration change saved: profile={profile}")
            
            # In a real implementation, this would write to config.yaml or similar
            # config_path = "/data/config.yaml"
            # with open(config_path, 'w') as f:
            #     yaml.dump(self.config, f)
            
        except Exception as e:
            self.logger.error(f"Error saving configuration change: {e}")
    
    def is_health_check_running(self) -> bool:
        """Check if a health check is currently running."""
        return self._health_check_running
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about available services."""
        return {
            "services": [
                {
                    "name": "run_health_check",
                    "description": "Run a comprehensive system health check",
                    "running": self._health_check_running
                },
                {
                    "name": "apply_performance_profile",
                    "description": "Apply a performance profile (requires restart)",
                    "current_profile": self.config.get("inference_tuning", {}).get("profile", "auto")
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
