"""
Alert Manager for AICleaner Phase 3C.2
Provides configurable performance alerts, notifications, and escalation management.
"""

import asyncio
import logging
import time
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import threading

try:
    from core.resource_monitor import ResourceAlert, AlertLevel, ResourceType
except ImportError:
    # Fallback definitions if resource_monitor is not available
    from enum import Enum
    from dataclasses import dataclass
    
    class AlertLevel(Enum):
        INFO = "info"
        WARNING = "warning"
        CRITICAL = "critical"
        EMERGENCY = "emergency"
    
    class ResourceType(Enum):
        CPU = "cpu"
        MEMORY = "memory"
        DISK = "disk"
        NETWORK = "network"
        GPU = "gpu"
        PROCESS = "process"
    
    @dataclass
    class ResourceAlert:
        alert_id: str
        timestamp: str
        resource_type: ResourceType
        alert_level: AlertLevel
        message: str
        current_value: float
        threshold_value: float
        metadata: Dict[str, Any] = None


class AlertStatus(Enum):
    """Alert status enumeration."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class NotificationChannel(Enum):
    """Notification channel types."""
    LOG = "log"
    HOME_ASSISTANT = "home_assistant"
    MQTT = "mqtt"
    WEBHOOK = "webhook"
    EMAIL = "email"


@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    name: str
    resource_type: ResourceType
    threshold_value: float
    comparison_operator: str  # >, <, >=, <=, ==, !=
    alert_level: AlertLevel
    enabled: bool = True
    cooldown_minutes: int = 5
    escalation_minutes: int = 30
    notification_channels: List[NotificationChannel] = None
    metadata: Dict[str, Any] = None


@dataclass
class AlertInstance:
    """Active alert instance."""
    alert_id: str
    rule_id: str
    resource_alert: ResourceAlert
    status: AlertStatus
    created_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    escalated: bool = False
    notification_count: int = 0
    last_notification: Optional[str] = None


class AlertManager:
    """
    Advanced alert management system for AICleaner.
    
    Features:
    - Configurable alert rules and thresholds
    - Multiple notification channels
    - Alert escalation and acknowledgment
    - Alert suppression and cooldown
    - Performance trend analysis
    - Integration with Home Assistant and MQTT
    """
    
    def __init__(self, config: Dict[str, Any], data_path: str = "/data/alert_manager"):
        """
        Initialize Alert Manager.
        
        Args:
            config: Configuration dictionary
            data_path: Path to store alert data
        """
        self.logger = logging.getLogger(__name__)
        self.config = config.get("performance_optimization", {})
        self.data_path = data_path
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Alert configuration
        self.monitoring_config = self.config.get("monitoring", {})
        self.alert_thresholds = self.monitoring_config.get("alert_thresholds", {})
        
        # Alert storage
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, AlertInstance] = {}
        self.alert_history = deque(maxlen=10000)
        
        # Notification channels
        self.notification_channels: Dict[NotificationChannel, Callable] = {}
        self.notification_queue = asyncio.Queue()
        
        # Alert state
        self.alert_suppression: Set[str] = set()  # Suppressed rule IDs
        self.cooldown_tracker: Dict[str, float] = {}  # Rule ID -> last alert time
        
        # Background tasks
        self._notification_task = None
        self._escalation_task = None
        self._cleanup_task = None
        self.running = False
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize default alert rules
        self._initialize_default_rules()
        
        self.logger.info("Alert Manager initialized")

    def _initialize_default_rules(self):
        """Initialize default alert rules from configuration."""
        try:
            # CPU alert rule
            cpu_threshold = self.alert_thresholds.get("cpu_usage_percent", 95)
            self.add_alert_rule(AlertRule(
                rule_id="cpu_high_usage",
                name="High CPU Usage",
                resource_type=ResourceType.CPU,
                threshold_value=cpu_threshold,
                comparison_operator=">=",
                alert_level=AlertLevel.WARNING,
                cooldown_minutes=5,
                escalation_minutes=15,
                notification_channels=[NotificationChannel.LOG, NotificationChannel.HOME_ASSISTANT]
            ))
            
            # Memory alert rule
            memory_threshold = self.alert_thresholds.get("memory_usage_percent", 90)
            self.add_alert_rule(AlertRule(
                rule_id="memory_high_usage",
                name="High Memory Usage",
                resource_type=ResourceType.MEMORY,
                threshold_value=memory_threshold,
                comparison_operator=">=",
                alert_level=AlertLevel.WARNING,
                cooldown_minutes=5,
                escalation_minutes=20,
                notification_channels=[NotificationChannel.LOG, NotificationChannel.HOME_ASSISTANT]
            ))
            
            # Disk alert rule
            disk_threshold = self.alert_thresholds.get("disk_usage_percent", 95)
            self.add_alert_rule(AlertRule(
                rule_id="disk_high_usage",
                name="High Disk Usage",
                resource_type=ResourceType.DISK,
                threshold_value=disk_threshold,
                comparison_operator=">=",
                alert_level=AlertLevel.CRITICAL,
                cooldown_minutes=10,
                escalation_minutes=30,
                notification_channels=[NotificationChannel.LOG, NotificationChannel.HOME_ASSISTANT]
            ))
            
            # Response time alert rule
            response_threshold = self.alert_thresholds.get("response_time_seconds", 60)
            self.add_alert_rule(AlertRule(
                rule_id="slow_response_time",
                name="Slow Response Time",
                resource_type=ResourceType.PROCESS,
                threshold_value=response_threshold,
                comparison_operator=">=",
                alert_level=AlertLevel.WARNING,
                cooldown_minutes=3,
                escalation_minutes=10,
                notification_channels=[NotificationChannel.LOG]
            ))
            
        except Exception as e:
            self.logger.error(f"Error initializing default alert rules: {e}")

    async def start(self):
        """Start the alert manager."""
        if self.running:
            self.logger.warning("Alert Manager already running")
            return
        
        self.running = True
        
        # Start background tasks
        self._notification_task = asyncio.create_task(self._notification_loop())
        self._escalation_task = asyncio.create_task(self._escalation_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info("Alert Manager started")

    async def stop(self):
        """Stop the alert manager."""
        self.running = False
        
        # Cancel background tasks
        if self._notification_task:
            self._notification_task.cancel()
        if self._escalation_task:
            self._escalation_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Save current state
        await self._save_alert_data()
        
        self.logger.info("Alert Manager stopped")

    def add_alert_rule(self, rule: AlertRule):
        """Add or update an alert rule."""
        with self._lock:
            self.alert_rules[rule.rule_id] = rule
        self.logger.info(f"Added alert rule: {rule.name}")

    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        with self._lock:
            if rule_id in self.alert_rules:
                del self.alert_rules[rule_id]
                self.logger.info(f"Removed alert rule: {rule_id}")
                return True
        return False

    def suppress_alert_rule(self, rule_id: str, duration_minutes: int = 60):
        """Suppress an alert rule for a specified duration."""
        with self._lock:
            self.alert_suppression.add(rule_id)
        
        # Schedule unsuppression
        async def unsuppress():
            await asyncio.sleep(duration_minutes * 60)
            with self._lock:
                self.alert_suppression.discard(rule_id)
            self.logger.info(f"Alert rule {rule_id} unsuppressed")
        
        asyncio.create_task(unsuppress())
        self.logger.info(f"Alert rule {rule_id} suppressed for {duration_minutes} minutes")

    def register_notification_channel(self, channel: NotificationChannel, handler: Callable):
        """Register a notification channel handler."""
        self.notification_channels[channel] = handler
        self.logger.info(f"Registered notification channel: {channel.value}")

    async def process_resource_alert(self, resource_alert: ResourceAlert):
        """Process a resource alert against configured rules."""
        try:
            matching_rules = self._find_matching_rules(resource_alert)
            
            for rule in matching_rules:
                if not rule.enabled or rule.rule_id in self.alert_suppression:
                    continue
                
                # Check cooldown
                if self._is_in_cooldown(rule.rule_id):
                    continue
                
                # Check if alert should be triggered
                if self._should_trigger_alert(resource_alert, rule):
                    await self._create_alert_instance(resource_alert, rule)
                    
        except Exception as e:
            self.logger.error(f"Error processing resource alert: {e}")

    def _find_matching_rules(self, resource_alert: ResourceAlert) -> List[AlertRule]:
        """Find alert rules that match the resource alert."""
        matching_rules = []
        
        with self._lock:
            for rule in self.alert_rules.values():
                if rule.resource_type == resource_alert.resource_type:
                    matching_rules.append(rule)
        
        return matching_rules

    def _should_trigger_alert(self, resource_alert: ResourceAlert, rule: AlertRule) -> bool:
        """Check if an alert should be triggered based on the rule."""
        try:
            current_value = resource_alert.current_value
            threshold = rule.threshold_value
            operator = rule.comparison_operator
            
            if operator == ">=":
                return current_value >= threshold
            elif operator == ">":
                return current_value > threshold
            elif operator == "<=":
                return current_value <= threshold
            elif operator == "<":
                return current_value < threshold
            elif operator == "==":
                return current_value == threshold
            elif operator == "!=":
                return current_value != threshold
            else:
                self.logger.warning(f"Unknown comparison operator: {operator}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error evaluating alert rule: {e}")
            return False

    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if a rule is in cooldown period."""
        if rule_id not in self.cooldown_tracker:
            return False
        
        rule = self.alert_rules.get(rule_id)
        if not rule:
            return False
        
        last_alert_time = self.cooldown_tracker[rule_id]
        cooldown_seconds = rule.cooldown_minutes * 60
        
        return (time.time() - last_alert_time) < cooldown_seconds

    async def _create_alert_instance(self, resource_alert: ResourceAlert, rule: AlertRule):
        """Create a new alert instance."""
        try:
            alert_instance = AlertInstance(
                alert_id=f"{rule.rule_id}_{int(time.time())}",
                rule_id=rule.rule_id,
                resource_alert=resource_alert,
                status=AlertStatus.ACTIVE,
                created_at=datetime.now(timezone.utc).isoformat()
            )
            
            with self._lock:
                self.active_alerts[alert_instance.alert_id] = alert_instance
                self.alert_history.append(alert_instance)
                self.cooldown_tracker[rule.rule_id] = time.time()
            
            # Queue for notification
            await self.notification_queue.put(alert_instance)
            
            self.logger.info(f"Created alert instance: {alert_instance.alert_id}")
            
        except Exception as e:
            self.logger.error(f"Error creating alert instance: {e}")

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acknowledge an active alert."""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
                self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
        return False

    async def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """Resolve an active alert."""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc).isoformat()
                del self.active_alerts[alert_id]
                self.logger.info(f"Alert {alert_id} resolved by {resolved_by}")
                return True
        return False

    async def get_active_alerts(self) -> List[AlertInstance]:
        """Get all active alerts."""
        with self._lock:
            return list(self.active_alerts.values())

    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics and summary."""
        with self._lock:
            active_count = len(self.active_alerts)
            total_count = len(self.alert_history)

            # Count by status
            status_counts = defaultdict(int)
            for alert in self.alert_history:
                status_counts[alert.status.value] += 1

            # Count by alert level
            level_counts = defaultdict(int)
            for alert in self.alert_history:
                level_counts[alert.resource_alert.alert_level.value] += 1

            # Count by resource type
            resource_counts = defaultdict(int)
            for alert in self.alert_history:
                resource_counts[alert.resource_alert.resource_type.value] += 1

            return {
                "active_alerts": active_count,
                "total_alerts": total_count,
                "status_distribution": dict(status_counts),
                "level_distribution": dict(level_counts),
                "resource_distribution": dict(resource_counts),
                "suppressed_rules": len(self.alert_suppression),
                "configured_rules": len(self.alert_rules)
            }

    async def _notification_loop(self):
        """Background task for processing notifications."""
        while self.running:
            try:
                # Wait for alert to notify
                alert_instance = await asyncio.wait_for(
                    self.notification_queue.get(),
                    timeout=1.0
                )

                await self._send_notifications(alert_instance)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in notification loop: {e}")

    async def _send_notifications(self, alert_instance: AlertInstance):
        """Send notifications for an alert instance."""
        try:
            rule = self.alert_rules.get(alert_instance.rule_id)
            if not rule or not rule.notification_channels:
                return

            for channel in rule.notification_channels:
                if channel in self.notification_channels:
                    try:
                        handler = self.notification_channels[channel]
                        await handler(alert_instance)
                        alert_instance.notification_count += 1
                        alert_instance.last_notification = datetime.now(timezone.utc).isoformat()
                    except Exception as e:
                        self.logger.error(f"Error sending notification via {channel.value}: {e}")

        except Exception as e:
            self.logger.error(f"Error sending notifications: {e}")

    async def _escalation_loop(self):
        """Background task for alert escalation."""
        while self.running:
            try:
                current_time = time.time()

                with self._lock:
                    alerts_to_escalate = []
                    for alert in self.active_alerts.values():
                        if (alert.status == AlertStatus.ACTIVE and
                            not alert.escalated and
                            alert.rule_id in self.alert_rules):

                            rule = self.alert_rules[alert.rule_id]
                            created_timestamp = datetime.fromisoformat(
                                alert.created_at.replace('Z', '+00:00')
                            ).timestamp()

                            if (current_time - created_timestamp) > (rule.escalation_minutes * 60):
                                alerts_to_escalate.append(alert)

                # Escalate alerts
                for alert in alerts_to_escalate:
                    await self._escalate_alert(alert)

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in escalation loop: {e}")
                await asyncio.sleep(60)

    async def _escalate_alert(self, alert_instance: AlertInstance):
        """Escalate an alert to higher severity."""
        try:
            alert_instance.escalated = True

            # Increase alert level
            current_level = alert_instance.resource_alert.alert_level
            if current_level == AlertLevel.WARNING:
                alert_instance.resource_alert.alert_level = AlertLevel.CRITICAL
            elif current_level == AlertLevel.CRITICAL:
                alert_instance.resource_alert.alert_level = AlertLevel.EMERGENCY

            # Send escalation notification
            await self.notification_queue.put(alert_instance)

            self.logger.warning(f"Escalated alert {alert_instance.alert_id} to {alert_instance.resource_alert.alert_level.value}")

        except Exception as e:
            self.logger.error(f"Error escalating alert: {e}")

    async def _cleanup_loop(self):
        """Background task for cleanup and maintenance."""
        while self.running:
            try:
                # Save alert data
                await self._save_alert_data()

                # Clean up old resolved alerts
                await self._cleanup_old_alerts()

                # Wait for next cleanup cycle (every hour)
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)

    async def _save_alert_data(self):
        """Save alert data to disk."""
        try:
            data = {
                "alert_rules": {k: asdict(v) for k, v in self.alert_rules.items()},
                "active_alerts": {k: asdict(v) for k, v in self.active_alerts.items()},
                "alert_history": [asdict(a) for a in list(self.alert_history)],
                "alert_suppression": list(self.alert_suppression),
                "cooldown_tracker": self.cooldown_tracker,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

            filepath = os.path.join(self.data_path, "alert_manager_data.json")
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Error saving alert data: {e}")

    async def _cleanup_old_alerts(self):
        """Clean up old resolved alerts."""
        try:
            # Keep alerts for 7 days
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
            cutoff_timestamp = cutoff_time.isoformat()

            with self._lock:
                # Clean up alert history
                self.alert_history = deque(
                    [a for a in self.alert_history
                     if a.created_at >= cutoff_timestamp or a.status == AlertStatus.ACTIVE],
                    maxlen=self.alert_history.maxlen
                )

        except Exception as e:
            self.logger.error(f"Error cleaning up old alerts: {e}")

    # Default notification handlers
    async def _log_notification_handler(self, alert_instance: AlertInstance):
        """Default log notification handler."""
        rule = self.alert_rules.get(alert_instance.rule_id)
        rule_name = rule.name if rule else "Unknown Rule"

        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.CRITICAL: logging.ERROR,
            AlertLevel.EMERGENCY: logging.CRITICAL
        }.get(alert_instance.resource_alert.alert_level, logging.WARNING)

        message = f"ALERT [{rule_name}]: {alert_instance.resource_alert.message}"
        if alert_instance.escalated:
            message += " [ESCALATED]"

        self.logger.log(log_level, message)

    async def _home_assistant_notification_handler(self, alert_instance: AlertInstance):
        """Home Assistant notification handler."""
        # This would integrate with Home Assistant notification service
        # For now, just log the intent
        self.logger.info(f"Would send HA notification for alert: {alert_instance.alert_id}")

    def _register_default_handlers(self):
        """Register default notification handlers."""
        self.register_notification_channel(
            NotificationChannel.LOG,
            self._log_notification_handler
        )
        self.register_notification_channel(
            NotificationChannel.HOME_ASSISTANT,
            self._home_assistant_notification_handler
        )
