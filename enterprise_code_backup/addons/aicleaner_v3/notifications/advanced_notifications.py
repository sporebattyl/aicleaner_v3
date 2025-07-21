"""
Advanced Notification System for AICleaner
Provides smart timing, personalization, and multi-channel delivery
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import re


class NotificationChannel(Enum):
    """Notification delivery channels"""
    HOME_ASSISTANT = "home_assistant"
    MOBILE_PUSH = "mobile_push"
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationTiming(Enum):
    """Notification timing strategies"""
    IMMEDIATE = "immediate"
    SMART_DELAY = "smart_delay"
    SCHEDULED = "scheduled"
    QUIET_HOURS_RESPECT = "quiet_hours_respect"


@dataclass
class NotificationTemplate:
    """Template for notifications"""
    id: str
    name: str
    title_template: str
    message_template: str
    category: str
    priority: NotificationPriority
    channels: List[NotificationChannel]
    timing: NotificationTiming
    personalization_enabled: bool = True
    variables: List[str] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = []


@dataclass
class NotificationRule:
    """Rules for when to send notifications"""
    id: str
    name: str
    trigger_conditions: Dict[str, Any]
    template_id: str
    enabled: bool = True
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    max_frequency: int = 5  # Max notifications per hour
    cooldown_minutes: int = 15


@dataclass
class NotificationHistory:
    """History of sent notifications"""
    id: str
    template_id: str
    title: str
    message: str
    channels: List[str]
    sent_at: str
    priority: str
    success: bool
    error_message: Optional[str] = None


class AdvancedNotificationSystem:
    """
    Advanced notification system for AICleaner
    
    Features:
    - Smart timing based on user patterns
    - Multi-channel delivery (HA, mobile, email, etc.)
    - Personalized message templates
    - Notification rules and frequency limits
    - Quiet hours and do-not-disturb modes
    - Rich notification content with actions
    - Analytics and delivery tracking
    """
    
    def __init__(self, data_path: str = "/data/notifications"):
        """
        Initialize advanced notification system
        
        Args:
            data_path: Path to store notification data
        """
        self.data_path = data_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Load notification configuration
        self.templates = self._load_templates()
        self.rules = self._load_rules()
        self.history = self._load_history()
        self.user_preferences = self._load_user_preferences()
        
        # Initialize default templates and rules
        self._initialize_defaults()
        
        self.logger.info("Advanced notification system initialized")
    
    def _load_templates(self) -> List[NotificationTemplate]:
        """Load notification templates from file"""
        templates_file = os.path.join(self.data_path, "templates.json")
        
        if os.path.exists(templates_file):
            try:
                with open(templates_file, 'r') as f:
                    data = json.load(f)
                templates = []
                for item in data:
                    # Convert enum strings back to enums
                    item['priority'] = NotificationPriority(item['priority'])
                    item['channels'] = [NotificationChannel(ch) for ch in item['channels']]
                    item['timing'] = NotificationTiming(item['timing'])
                    templates.append(NotificationTemplate(**item))
                return templates
            except Exception as e:
                self.logger.error(f"Error loading notification templates: {e}")
        
        return []
    
    def _save_templates(self):
        """Save notification templates to file"""
        templates_file = os.path.join(self.data_path, "templates.json")
        
        try:
            data = []
            for template in self.templates:
                template_dict = asdict(template)
                template_dict['priority'] = template.priority.value
                template_dict['channels'] = [ch.value for ch in template.channels]
                template_dict['timing'] = template.timing.value
                data.append(template_dict)
            
            with open(templates_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug("Notification templates saved")
        except Exception as e:
            self.logger.error(f"Error saving notification templates: {e}")
    
    def _load_rules(self) -> List[NotificationRule]:
        """Load notification rules from file"""
        rules_file = os.path.join(self.data_path, "rules.json")
        
        if os.path.exists(rules_file):
            try:
                with open(rules_file, 'r') as f:
                    data = json.load(f)
                return [NotificationRule(**item) for item in data]
            except Exception as e:
                self.logger.error(f"Error loading notification rules: {e}")
        
        return []
    
    def _save_rules(self):
        """Save notification rules to file"""
        rules_file = os.path.join(self.data_path, "rules.json")
        
        try:
            with open(rules_file, 'w') as f:
                json.dump([asdict(rule) for rule in self.rules], f, indent=2)
            self.logger.debug("Notification rules saved")
        except Exception as e:
            self.logger.error(f"Error saving notification rules: {e}")
    
    def _load_history(self) -> List[NotificationHistory]:
        """Load notification history from file"""
        history_file = os.path.join(self.data_path, "history.json")
        
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                # Keep only last 1000 notifications
                return [NotificationHistory(**item) for item in data[-1000:]]
            except Exception as e:
                self.logger.error(f"Error loading notification history: {e}")
        
        return []
    
    def _save_history(self):
        """Save notification history to file"""
        history_file = os.path.join(self.data_path, "history.json")
        
        try:
            # Keep only last 1000 notifications
            recent_history = self.history[-1000:] if len(self.history) > 1000 else self.history
            with open(history_file, 'w') as f:
                json.dump([asdict(item) for item in recent_history], f, indent=2)
            self.logger.debug("Notification history saved")
        except Exception as e:
            self.logger.error(f"Error saving notification history: {e}")
    
    def _load_user_preferences(self) -> Dict[str, Any]:
        """Load user notification preferences"""
        prefs_file = os.path.join(self.data_path, "user_preferences.json")
        
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading user preferences: {e}")
        
        # Return default preferences
        return {
            'enabled_channels': ['home_assistant'],
            'quiet_hours_start': '22:00',
            'quiet_hours_end': '07:00',
            'max_notifications_per_hour': 5,
            'personalization_enabled': True,
            'smart_timing_enabled': True,
            'priority_filter': 'normal',  # minimum priority to show
            'do_not_disturb': False,
            'preferred_language': 'en',
            'timezone': 'UTC'
        }
    
    def _save_user_preferences(self):
        """Save user notification preferences"""
        prefs_file = os.path.join(self.data_path, "user_preferences.json")
        
        try:
            with open(prefs_file, 'w') as f:
                json.dump(self.user_preferences, f, indent=2)
            self.logger.debug("User preferences saved")
        except Exception as e:
            self.logger.error(f"Error saving user preferences: {e}")
    
    def _initialize_defaults(self):
        """Initialize default templates and rules if none exist"""
        if not self.templates:
            self._create_default_templates()
        
        if not self.rules:
            self._create_default_rules()
    
    def _create_default_templates(self):
        """Create default notification templates"""
        default_templates = [
            NotificationTemplate(
                id="task_completed",
                name="Task Completed",
                title_template="✅ Task Completed in {zone_name}",
                message_template="Great job! You completed '{task_description}' in {zone_name}. {motivational_message}",
                category="achievement",
                priority=NotificationPriority.NORMAL,
                channels=[NotificationChannel.HOME_ASSISTANT, NotificationChannel.MOBILE_PUSH],
                timing=NotificationTiming.IMMEDIATE,
                variables=["zone_name", "task_description", "motivational_message"]
            ),
            NotificationTemplate(
                id="achievement_unlocked",
                name="Achievement Unlocked",
                title_template="🏆 Achievement Unlocked!",
                message_template="Congratulations! You've earned the '{achievement_title}' achievement. {achievement_description}",
                category="gamification",
                priority=NotificationPriority.HIGH,
                channels=[NotificationChannel.HOME_ASSISTANT, NotificationChannel.MOBILE_PUSH],
                timing=NotificationTiming.IMMEDIATE,
                variables=["achievement_title", "achievement_description"]
            ),
            NotificationTemplate(
                id="daily_challenge",
                name="Daily Challenge",
                title_template="🎯 Daily Challenge Available",
                message_template="New challenge: {challenge_title}. {challenge_description} Reward: {points} points!",
                category="gamification",
                priority=NotificationPriority.NORMAL,
                channels=[NotificationChannel.HOME_ASSISTANT],
                timing=NotificationTiming.SCHEDULED,
                variables=["challenge_title", "challenge_description", "points"]
            ),
            NotificationTemplate(
                id="cleaning_reminder",
                name="Cleaning Reminder",
                title_template="🧹 Cleaning Reminder",
                message_template="It's time to clean {zone_name}. Predicted tasks: {predicted_tasks}",
                category="reminder",
                priority=NotificationPriority.NORMAL,
                channels=[NotificationChannel.HOME_ASSISTANT],
                timing=NotificationTiming.SMART_DELAY,
                variables=["zone_name", "predicted_tasks"]
            ),
            NotificationTemplate(
                id="streak_milestone",
                name="Streak Milestone",
                title_template="🔥 {streak_days}-Day Streak!",
                message_template="Amazing! You've maintained a {streak_days}-day cleaning streak. Keep up the excellent work!",
                category="milestone",
                priority=NotificationPriority.HIGH,
                channels=[NotificationChannel.HOME_ASSISTANT, NotificationChannel.MOBILE_PUSH],
                timing=NotificationTiming.IMMEDIATE,
                variables=["streak_days"]
            ),
            NotificationTemplate(
                id="system_alert",
                name="System Alert",
                title_template="⚠️ AICleaner Alert",
                message_template="System notification: {alert_message}",
                category="system",
                priority=NotificationPriority.URGENT,
                channels=[NotificationChannel.HOME_ASSISTANT, NotificationChannel.MOBILE_PUSH],
                timing=NotificationTiming.IMMEDIATE,
                variables=["alert_message"]
            )
        ]
        
        self.templates = default_templates
        self._save_templates()
        self.logger.info(f"Created {len(default_templates)} default notification templates")

    def _create_default_rules(self):
        """Create default notification rules"""
        default_rules = [
            NotificationRule(
                id="task_completion_rule",
                name="Task Completion Notifications",
                trigger_conditions={"event": "task_completed"},
                template_id="task_completed",
                max_frequency=3,
                cooldown_minutes=5
            ),
            NotificationRule(
                id="achievement_rule",
                name="Achievement Notifications",
                trigger_conditions={"event": "achievement_unlocked"},
                template_id="achievement_unlocked",
                max_frequency=10,
                cooldown_minutes=1
            ),
            NotificationRule(
                id="daily_challenge_rule",
                name="Daily Challenge Notifications",
                trigger_conditions={"event": "daily_challenge_available"},
                template_id="daily_challenge",
                max_frequency=1,
                cooldown_minutes=1440  # Once per day
            ),
            NotificationRule(
                id="streak_milestone_rule",
                name="Streak Milestone Notifications",
                trigger_conditions={"event": "streak_milestone", "min_streak": 3},
                template_id="streak_milestone",
                max_frequency=1,
                cooldown_minutes=1440  # Once per day
            ),
            NotificationRule(
                id="system_alert_rule",
                name="System Alert Notifications",
                trigger_conditions={"event": "system_alert"},
                template_id="system_alert",
                max_frequency=5,
                cooldown_minutes=60
            )
        ]

        self.rules = default_rules
        self._save_rules()
        self.logger.info(f"Created {len(default_rules)} default notification rules")

    def send_notification(self, event_type: str, variables: Dict[str, Any],
                         priority_override: Optional[NotificationPriority] = None) -> bool:
        """
        Send a notification based on event type and variables

        Args:
            event_type: Type of event triggering the notification
            variables: Variables to substitute in the template
            priority_override: Override the template priority

        Returns:
            True if notification was sent successfully
        """
        try:
            # Find matching rule
            matching_rule = None
            for rule in self.rules:
                if (rule.enabled and
                    rule.trigger_conditions.get("event") == event_type and
                    self._check_rule_conditions(rule, variables)):
                    matching_rule = rule
                    break

            if not matching_rule:
                self.logger.debug(f"No matching rule found for event: {event_type}")
                return False

            # Check frequency limits
            if not self._check_frequency_limits(matching_rule):
                self.logger.debug(f"Frequency limit exceeded for rule: {matching_rule.name}")
                return False

            # Check quiet hours
            if not self._check_quiet_hours(matching_rule):
                self.logger.debug(f"Notification blocked by quiet hours: {matching_rule.name}")
                return False

            # Find template
            template = next((t for t in self.templates if t.id == matching_rule.template_id), None)
            if not template:
                self.logger.error(f"Template not found: {matching_rule.template_id}")
                return False

            # Generate notification content
            title, message = self._generate_content(template, variables)

            # Determine priority
            priority = priority_override or template.priority

            # Send to channels
            success = self._send_to_channels(template.channels, title, message, priority, variables)

            # Record in history
            self._record_notification(template, title, message, priority, success)

            return success

        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False

    def _check_rule_conditions(self, rule: NotificationRule, variables: Dict[str, Any]) -> bool:
        """Check if rule conditions are met"""
        conditions = rule.trigger_conditions

        # Check minimum streak for streak milestones
        if "min_streak" in conditions:
            streak = variables.get("streak_days", 0)
            if streak < conditions["min_streak"]:
                return False

        # Add more condition checks as needed
        return True

    def _check_frequency_limits(self, rule: NotificationRule) -> bool:
        """Check if notification frequency limits are respected"""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        # Count recent notifications for this rule
        recent_count = sum(1 for notification in self.history
                          if (notification.template_id == rule.template_id and
                              datetime.fromisoformat(notification.sent_at.replace('Z', '+00:00')) > one_hour_ago))

        return recent_count < rule.max_frequency

    def _check_quiet_hours(self, rule: NotificationRule) -> bool:
        """Check if current time respects quiet hours"""
        if self.user_preferences.get('do_not_disturb', False):
            return False

        now = datetime.now(timezone.utc)
        current_time = now.strftime('%H:%M')

        quiet_start = rule.quiet_hours_start
        quiet_end = rule.quiet_hours_end

        # Handle quiet hours that span midnight
        if quiet_start > quiet_end:
            return not (current_time >= quiet_start or current_time <= quiet_end)
        else:
            return not (quiet_start <= current_time <= quiet_end)

    def _generate_content(self, template: NotificationTemplate, variables: Dict[str, Any]) -> tuple:
        """Generate notification title and message from template"""
        title = template.title_template
        message = template.message_template

        # Substitute variables
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            title = title.replace(placeholder, str(var_value))
            message = message.replace(placeholder, str(var_value))

        # Add personalization if enabled
        if template.personalization_enabled and self.user_preferences.get('personalization_enabled', True):
            title, message = self._add_personalization(title, message, variables)

        return title, message

    def _add_personalization(self, title: str, message: str, variables: Dict[str, Any]) -> tuple:
        """Add personalization to notification content"""
        # Add user's preferred greeting time
        now = datetime.now(timezone.utc)
        hour = now.hour

        if 5 <= hour < 12:
            greeting = "Good morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
        elif 17 <= hour < 22:
            greeting = "Good evening"
        else:
            greeting = "Hello"

        # Add personal touch to certain messages
        if "Great job" in message:
            message = message.replace("Great job", f"{greeting}! Great job")
        elif "Congratulations" in message:
            message = f"{greeting}! {message}"

        return title, message

    def _send_to_channels(self, channels: List[NotificationChannel], title: str,
                         message: str, priority: NotificationPriority,
                         variables: Dict[str, Any]) -> bool:
        """Send notification to specified channels"""
        enabled_channels = self.user_preferences.get('enabled_channels', ['home_assistant'])
        success = True

        for channel in channels:
            if channel.value not in enabled_channels:
                continue

            try:
                if channel == NotificationChannel.HOME_ASSISTANT:
                    success &= self._send_to_home_assistant(title, message, priority, variables)
                elif channel == NotificationChannel.MOBILE_PUSH:
                    success &= self._send_mobile_push(title, message, priority, variables)
                elif channel == NotificationChannel.EMAIL:
                    success &= self._send_email(title, message, priority, variables)
                # Add more channels as needed

            except Exception as e:
                self.logger.error(f"Error sending to {channel.value}: {e}")
                success = False

        return success

    def _send_to_home_assistant(self, title: str, message: str,
                               priority: NotificationPriority, variables: Dict[str, Any]) -> bool:
        """Send notification to Home Assistant"""
        try:
            # This would integrate with Home Assistant's notification service
            # For now, just log the notification
            self.logger.info(f"HA Notification: {title} - {message}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending HA notification: {e}")
            return False

    def _send_mobile_push(self, title: str, message: str,
                         priority: NotificationPriority, variables: Dict[str, Any]) -> bool:
        """Send mobile push notification"""
        try:
            # This would integrate with mobile push service
            # For now, just log the notification
            self.logger.info(f"Mobile Push: {title} - {message}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending mobile push: {e}")
            return False

    def _send_email(self, title: str, message: str,
                   priority: NotificationPriority, variables: Dict[str, Any]) -> bool:
        """Send email notification"""
        try:
            # This would integrate with email service
            # For now, just log the notification
            self.logger.info(f"Email: {title} - {message}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False

    def _record_notification(self, template: NotificationTemplate, title: str,
                           message: str, priority: NotificationPriority, success: bool):
        """Record notification in history"""
        notification = NotificationHistory(
            id=f"notif_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            template_id=template.id,
            title=title,
            message=message,
            channels=[ch.value for ch in template.channels],
            sent_at=datetime.now(timezone.utc).isoformat(),
            priority=priority.value,
            success=success
        )

        self.history.append(notification)
        self._save_history()

    def get_notification_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent notification history"""
        recent_history = self.history[-limit:] if len(self.history) > limit else self.history
        return [asdict(notification) for notification in reversed(recent_history)]

    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        if not self.history:
            return {'total_sent': 0, 'success_rate': 0.0, 'by_category': {}, 'by_channel': {}}

        total_sent = len(self.history)
        successful = sum(1 for n in self.history if n.success)
        success_rate = successful / total_sent if total_sent > 0 else 0.0

        # Group by template category
        by_category = {}
        by_channel = {}

        for notification in self.history:
            template = next((t for t in self.templates if t.id == notification.template_id), None)
            if template:
                category = template.category
                by_category[category] = by_category.get(category, 0) + 1

            for channel in notification.channels:
                by_channel[channel] = by_channel.get(channel, 0) + 1

        return {
            'total_sent': total_sent,
            'successful': successful,
            'success_rate': success_rate,
            'by_category': by_category,
            'by_channel': by_channel
        }

    def update_user_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Update user notification preferences"""
        try:
            self.user_preferences.update(preferences)
            self._save_user_preferences()
            self.logger.info("User notification preferences updated")
            return True
        except Exception as e:
            self.logger.error(f"Error updating user preferences: {e}")
            return False

    def get_user_preferences(self) -> Dict[str, Any]:
        """Get current user notification preferences"""
        return self.user_preferences.copy()

    def get_system_status(self) -> Dict[str, Any]:
        """Get notification system status"""
        return {
            'templates_loaded': len(self.templates),
            'rules_loaded': len(self.rules),
            'history_entries': len(self.history),
            'enabled_channels': self.user_preferences.get('enabled_channels', []),
            'do_not_disturb': self.user_preferences.get('do_not_disturb', False),
            'personalization_enabled': self.user_preferences.get('personalization_enabled', True),
            'smart_timing_enabled': self.user_preferences.get('smart_timing_enabled', True),
            'data_path': self.data_path,
            'system_health': 'healthy'
        }
