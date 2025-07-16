"""
Phase 3C: Security Monitor
Real-time security monitoring, event detection, and alert generation.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import hashlib
import re


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Security event types."""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    API_ACCESS = "api_access"
    CONFIG_CHANGE = "config_change"
    FILE_ACCESS = "file_access"
    NETWORK_CONNECTION = "network_connection"
    SYSTEM_ERROR = "system_error"
    SECURITY_VIOLATION = "security_violation"
    ANOMALY_DETECTED = "anomaly_detected"
    THREAT_DETECTED = "threat_detected"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    severity: AlertSeverity
    source: str
    user_id: Optional[str]
    ip_address: Optional[str]
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAlert:
    """Security alert data structure."""
    alert_id: str
    alert_type: str
    severity: AlertSeverity
    timestamp: datetime
    title: str
    description: str
    events: List[SecurityEvent]
    affected_resources: List[str]
    recommendations: List[str]
    auto_resolved: bool = False
    acknowledged: bool = False
    resolved: bool = False


class SecurityMonitor:
    """
    Real-time security monitoring and alerting system.
    
    Monitors security events, detects patterns, generates alerts,
    and integrates with the security audit framework.
    """
    
    def __init__(self, hass, config: Dict[str, Any]):
        """
        Initialize security monitor.
        
        Args:
            hass: Home Assistant instance
            config: Configuration dictionary
        """
        self.hass = hass
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Event storage and processing
        self.event_buffer: deque = deque(maxlen=10000)
        self.event_history: Dict[str, List[SecurityEvent]] = defaultdict(list)
        self.active_alerts: Dict[str, SecurityAlert] = {}
        
        # Monitoring configuration
        self.monitoring_enabled = config.get('monitoring_enabled', True)
        self.alert_enabled = config.get('alert_enabled', True)
        self.event_retention_hours = config.get('event_retention_hours', 168)  # 7 days
        self.alert_retention_hours = config.get('alert_retention_hours', 720)  # 30 days
        
        # Alert thresholds
        self.alert_thresholds = {
            'failed_logins_per_hour': config.get('failed_logins_per_hour', 10),
            'api_requests_per_minute': config.get('api_requests_per_minute', 100),
            'config_changes_per_hour': config.get('config_changes_per_hour', 5),
            'error_rate_per_hour': config.get('error_rate_per_hour', 50),
            'anomaly_score_threshold': config.get('anomaly_score_threshold', 0.8)
        }
        
        # Pattern detection
        self.attack_patterns = {
            'brute_force': {
                'pattern': 'multiple_failed_logins',
                'threshold': 5,
                'window_minutes': 15,
                'severity': AlertSeverity.HIGH
            },
            'credential_stuffing': {
                'pattern': 'failed_logins_multiple_users',
                'threshold': 10,
                'window_minutes': 30,
                'severity': AlertSeverity.HIGH
            },
            'api_abuse': {
                'pattern': 'excessive_api_calls',
                'threshold': 1000,
                'window_minutes': 60,
                'severity': AlertSeverity.MEDIUM
            },
            'config_tampering': {
                'pattern': 'rapid_config_changes',
                'threshold': 3,
                'window_minutes': 10,
                'severity': AlertSeverity.CRITICAL
            }
        }
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[SecurityAlert], None]] = []
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'alerts_generated': 0,
            'false_positives': 0,
            'last_event_time': None,
            'last_alert_time': None
        }
        
        self.logger.info("Security Monitor initialized")
    
    async def start_monitoring(self) -> None:
        """Start security monitoring."""
        if self._running:
            return
        
        self._running = True
        
        # Start background tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Register with Home Assistant event bus
        await self._register_ha_listeners()
        
        self.logger.info("Security monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop security monitoring."""
        self._running = False
        
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Security monitoring stopped")
    
    async def _register_ha_listeners(self) -> None:
        """Register Home Assistant event listeners."""
        try:
            if hasattr(self.hass, 'bus'):
                # Listen for authentication events
                self.hass.bus.async_listen('user_login', self._handle_ha_login_event)
                self.hass.bus.async_listen('user_logout', self._handle_ha_logout_event)
                
                # Listen for configuration changes
                self.hass.bus.async_listen('config_entry_changed', self._handle_ha_config_event)
                
                # Listen for service calls
                self.hass.bus.async_listen('call_service', self._handle_ha_service_call)
                
                # Listen for state changes that might indicate security events
                self.hass.bus.async_listen('state_changed', self._handle_ha_state_change)
            
            self.logger.info("Registered Home Assistant event listeners")
        
        except Exception as e:
            self.logger.error(f"Error registering HA listeners: {e}")
    
    async def _handle_ha_login_event(self, event) -> None:
        """Handle Home Assistant login events."""
        try:
            event_data = event.data
            user_id = event_data.get('user_id')
            ip_address = event_data.get('ip_address')
            success = event_data.get('success', True)
            
            if success:
                await self.record_event(
                    event_type=EventType.LOGIN_SUCCESS,
                    severity=AlertSeverity.INFO,
                    source='home_assistant',
                    user_id=user_id,
                    ip_address=ip_address,
                    description=f"User {user_id} logged in successfully",
                    details={'event_data': event_data}
                )
            else:
                await self.record_event(
                    event_type=EventType.LOGIN_FAILURE,
                    severity=AlertSeverity.MEDIUM,
                    source='home_assistant',
                    user_id=user_id,
                    ip_address=ip_address,
                    description=f"Failed login attempt for user {user_id}",
                    details={'event_data': event_data}
                )
        
        except Exception as e:
            self.logger.error(f"Error handling HA login event: {e}")
    
    async def _handle_ha_logout_event(self, event) -> None:
        """Handle Home Assistant logout events."""
        try:
            event_data = event.data
            user_id = event_data.get('user_id')
            
            await self.record_event(
                event_type=EventType.LOGIN_SUCCESS,
                severity=AlertSeverity.INFO,
                source='home_assistant',
                user_id=user_id,
                description=f"User {user_id} logged out",
                details={'event_data': event_data}
            )
        
        except Exception as e:
            self.logger.error(f"Error handling HA logout event: {e}")
    
    async def _handle_ha_config_event(self, event) -> None:
        """Handle Home Assistant configuration change events."""
        try:
            event_data = event.data
            entry_id = event_data.get('entry_id')
            action = event_data.get('action')
            
            await self.record_event(
                event_type=EventType.CONFIG_CHANGE,
                severity=AlertSeverity.LOW,
                source='home_assistant',
                description=f"Configuration entry {entry_id} {action}",
                details={'event_data': event_data}
            )
        
        except Exception as e:
            self.logger.error(f"Error handling HA config event: {e}")
    
    async def _handle_ha_service_call(self, event) -> None:
        """Handle Home Assistant service call events."""
        try:
            event_data = event.data
            domain = event_data.get('domain')
            service = event_data.get('service')
            
            # Monitor security-sensitive service calls
            sensitive_services = ['shell_command', 'python_script', 'hassio']
            if domain in sensitive_services:
                await self.record_event(
                    event_type=EventType.API_ACCESS,
                    severity=AlertSeverity.MEDIUM,
                    source='home_assistant',
                    description=f"Sensitive service call: {domain}.{service}",
                    details={'event_data': event_data}
                )
        
        except Exception as e:
            self.logger.error(f"Error handling HA service call event: {e}")
    
    async def _handle_ha_state_change(self, event) -> None:
        """Handle Home Assistant state change events."""
        try:
            event_data = event.data
            entity_id = event_data.get('entity_id')
            
            # Monitor security-related entities
            if entity_id and any(keyword in entity_id for keyword in ['alarm', 'security', 'lock', 'camera']):
                new_state = event_data.get('new_state')
                if new_state:
                    state_value = new_state.state
                    
                    # Check for security state changes
                    if 'alarm' in entity_id and state_value in ['triggered', 'armed_away', 'armed_home']:
                        severity = AlertSeverity.HIGH if state_value == 'triggered' else AlertSeverity.INFO
                        
                        await self.record_event(
                            event_type=EventType.SECURITY_VIOLATION if state_value == 'triggered' else EventType.API_ACCESS,
                            severity=severity,
                            source='home_assistant',
                            description=f"Security entity {entity_id} changed to {state_value}",
                            details={'event_data': event_data}
                        )
        
        except Exception as e:
            self.logger.error(f"Error handling HA state change event: {e}")
    
    async def record_event(self, event_type: EventType, severity: AlertSeverity,
                          source: str, description: str,
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None,
                          raw_data: Optional[Dict[str, Any]] = None) -> SecurityEvent:
        """
        Record a security event.
        
        Args:
            event_type: Type of security event
            severity: Event severity
            source: Event source
            description: Event description
            user_id: User ID if applicable
            ip_address: IP address if applicable
            details: Additional event details
            raw_data: Raw event data
            
        Returns:
            Created security event
        """
        try:
            # Generate event ID
            event_id = self._generate_event_id(event_type, source)
            
            # Create event
            event = SecurityEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=datetime.now(),
                severity=severity,
                source=source,
                user_id=user_id,
                ip_address=ip_address,
                description=description,
                details=details or {},
                raw_data=raw_data or {}
            )
            
            # Store event
            self.event_buffer.append(event)
            self.event_history[event_type.value].append(event)
            
            # Update statistics
            self.stats['events_processed'] += 1
            self.stats['last_event_time'] = event.timestamp
            
            # Log event
            self.logger.info(
                f"Security event recorded: {event_type.value}",
                extra={
                    'event_id': event_id,
                    'event_type': event_type.value,
                    'severity': severity.value,
                    'source': source,
                    'user_id': user_id,
                    'ip_address': ip_address,
                    'description': description
                }
            )
            
            # Check for immediate alerts
            if self.alert_enabled:
                await self._check_immediate_alerts(event)
            
            return event
        
        except Exception as e:
            self.logger.error(f"Error recording security event: {e}")
            raise
    
    def _generate_event_id(self, event_type: EventType, source: str) -> str:
        """Generate unique event ID."""
        timestamp = datetime.now().isoformat()
        data = f"{event_type.value}_{source}_{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    async def _check_immediate_alerts(self, event: SecurityEvent) -> None:
        """Check if event should trigger immediate alerts."""
        try:
            # Check for critical events
            if event.severity == AlertSeverity.CRITICAL:
                await self._generate_alert(
                    alert_type='critical_event',
                    severity=AlertSeverity.CRITICAL,
                    title=f"Critical Security Event: {event.event_type.value}",
                    description=event.description,
                    events=[event],
                    affected_resources=[event.source],
                    recommendations=[
                        "Investigate immediately",
                        "Check system logs",
                        "Verify system integrity"
                    ]
                )
            
            # Check for security violations
            if event.event_type == EventType.SECURITY_VIOLATION:
                await self._generate_alert(
                    alert_type='security_violation',
                    severity=event.severity,
                    title="Security Violation Detected",
                    description=event.description,
                    events=[event],
                    affected_resources=[event.source],
                    recommendations=[
                        "Review security logs",
                        "Check access controls",
                        "Investigate potential breach"
                    ]
                )
        
        except Exception as e:
            self.logger.error(f"Error checking immediate alerts: {e}")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for pattern detection."""
        while self._running:
            try:
                # Check for attack patterns
                await self._detect_attack_patterns()
                
                # Check threshold-based alerts
                await self._check_threshold_alerts()
                
                # Update alert status
                await self._update_alert_status()
                
                # Sleep for monitoring interval
                await asyncio.sleep(60)  # Check every minute
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _detect_attack_patterns(self) -> None:
        """Detect attack patterns in recent events."""
        try:
            current_time = datetime.now()
            
            for pattern_name, pattern_config in self.attack_patterns.items():
                window_start = current_time - timedelta(minutes=pattern_config['window_minutes'])
                
                # Get recent events for pattern analysis
                recent_events = [
                    event for event in self.event_buffer
                    if event.timestamp >= window_start
                ]
                
                # Check specific patterns
                if await self._check_pattern(pattern_name, pattern_config, recent_events):
                    # Generate alert for detected pattern
                    await self._generate_pattern_alert(pattern_name, pattern_config, recent_events)
        
        except Exception as e:
            self.logger.error(f"Error detecting attack patterns: {e}")
    
    async def _check_pattern(self, pattern_name: str, pattern_config: Dict[str, Any],
                            events: List[SecurityEvent]) -> bool:
        """Check if specific attack pattern is detected."""
        try:
            pattern_type = pattern_config['pattern']
            threshold = pattern_config['threshold']
            
            if pattern_type == 'multiple_failed_logins':
                # Check for multiple failed logins from same IP
                failed_logins = [
                    e for e in events
                    if e.event_type == EventType.LOGIN_FAILURE
                ]
                
                ip_counts = defaultdict(int)
                for event in failed_logins:
                    if event.ip_address:
                        ip_counts[event.ip_address] += 1
                
                return any(count >= threshold for count in ip_counts.values())
            
            elif pattern_type == 'failed_logins_multiple_users':
                # Check for failed logins across multiple users
                failed_logins = [
                    e for e in events
                    if e.event_type == EventType.LOGIN_FAILURE
                ]
                
                unique_users = set(e.user_id for e in failed_logins if e.user_id)
                return len(unique_users) >= threshold
            
            elif pattern_type == 'excessive_api_calls':
                # Check for excessive API calls
                api_calls = [
                    e for e in events
                    if e.event_type == EventType.API_ACCESS
                ]
                
                return len(api_calls) >= threshold
            
            elif pattern_type == 'rapid_config_changes':
                # Check for rapid configuration changes
                config_changes = [
                    e for e in events
                    if e.event_type == EventType.CONFIG_CHANGE
                ]
                
                return len(config_changes) >= threshold
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error checking pattern {pattern_name}: {e}")
            return False
    
    async def _generate_pattern_alert(self, pattern_name: str, pattern_config: Dict[str, Any],
                                     events: List[SecurityEvent]) -> None:
        """Generate alert for detected attack pattern."""
        try:
            # Check if alert already exists for this pattern
            existing_alert = None
            for alert in self.active_alerts.values():
                if alert.alert_type == f"pattern_{pattern_name}" and not alert.resolved:
                    existing_alert = alert
                    break
            
            if existing_alert:
                # Update existing alert with new events
                existing_alert.events.extend(events)
                existing_alert.timestamp = datetime.now()
                return
            
            # Generate new alert
            await self._generate_alert(
                alert_type=f"pattern_{pattern_name}",
                severity=AlertSeverity(pattern_config['severity']),
                title=f"Attack Pattern Detected: {pattern_name.replace('_', ' ').title()}",
                description=f"Detected {pattern_name} attack pattern with {len(events)} related events",
                events=events,
                affected_resources=list(set(e.source for e in events)),
                recommendations=[
                    f"Investigate {pattern_name} attack pattern",
                    "Review affected resources",
                    "Consider blocking suspicious IPs",
                    "Strengthen security controls"
                ]
            )
        
        except Exception as e:
            self.logger.error(f"Error generating pattern alert: {e}")
    
    async def _check_threshold_alerts(self) -> None:
        """Check threshold-based alerts."""
        try:
            current_time = datetime.now()
            
            # Check failed logins per hour
            hour_ago = current_time - timedelta(hours=1)
            failed_logins = [
                e for e in self.event_buffer
                if e.event_type == EventType.LOGIN_FAILURE and e.timestamp >= hour_ago
            ]
            
            if len(failed_logins) >= self.alert_thresholds['failed_logins_per_hour']:
                await self._generate_threshold_alert(
                    'failed_logins_threshold',
                    AlertSeverity.HIGH,
                    f"High number of failed logins: {len(failed_logins)} in last hour",
                    failed_logins
                )
            
            # Check API request rate
            minute_ago = current_time - timedelta(minutes=1)
            api_requests = [
                e for e in self.event_buffer
                if e.event_type == EventType.API_ACCESS and e.timestamp >= minute_ago
            ]
            
            if len(api_requests) >= self.alert_thresholds['api_requests_per_minute']:
                await self._generate_threshold_alert(
                    'api_rate_threshold',
                    AlertSeverity.MEDIUM,
                    f"High API request rate: {len(api_requests)} in last minute",
                    api_requests
                )
        
        except Exception as e:
            self.logger.error(f"Error checking threshold alerts: {e}")
    
    async def _generate_threshold_alert(self, alert_type: str, severity: AlertSeverity,
                                       description: str, events: List[SecurityEvent]) -> None:
        """Generate threshold-based alert."""
        try:
            # Check if alert already exists
            existing_alert = None
            for alert in self.active_alerts.values():
                if alert.alert_type == alert_type and not alert.resolved:
                    existing_alert = alert
                    break
            
            if existing_alert:
                return  # Don't spam threshold alerts
            
            await self._generate_alert(
                alert_type=alert_type,
                severity=severity,
                title=f"Threshold Alert: {alert_type.replace('_', ' ').title()}",
                description=description,
                events=events,
                affected_resources=list(set(e.source for e in events)),
                recommendations=[
                    "Review recent activity",
                    "Check for anomalous behavior",
                    "Consider adjusting thresholds"
                ]
            )
        
        except Exception as e:
            self.logger.error(f"Error generating threshold alert: {e}")
    
    async def _generate_alert(self, alert_type: str, severity: AlertSeverity,
                             title: str, description: str,
                             events: List[SecurityEvent],
                             affected_resources: List[str],
                             recommendations: List[str]) -> SecurityAlert:
        """Generate security alert."""
        try:
            # Generate alert ID
            alert_id = self._generate_alert_id(alert_type)
            
            # Create alert
            alert = SecurityAlert(
                alert_id=alert_id,
                alert_type=alert_type,
                severity=severity,
                timestamp=datetime.now(),
                title=title,
                description=description,
                events=events,
                affected_resources=affected_resources,
                recommendations=recommendations
            )
            
            # Store alert
            self.active_alerts[alert_id] = alert
            
            # Update statistics
            self.stats['alerts_generated'] += 1
            self.stats['last_alert_time'] = alert.timestamp
            
            # Log alert
            self.logger.warning(
                f"Security alert generated: {title}",
                extra={
                    'alert_id': alert_id,
                    'alert_type': alert_type,
                    'severity': severity.value,
                    'title': title,
                    'description': description,
                    'affected_resources': affected_resources
                }
            )
            
            # Notify callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")
            
            return alert
        
        except Exception as e:
            self.logger.error(f"Error generating alert: {e}")
            raise
    
    def _generate_alert_id(self, alert_type: str) -> str:
        """Generate unique alert ID."""
        timestamp = datetime.now().isoformat()
        data = f"{alert_type}_{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    async def _update_alert_status(self) -> None:
        """Update alert status and auto-resolve where appropriate."""
        try:
            current_time = datetime.now()
            
            for alert in list(self.active_alerts.values()):
                if alert.resolved:
                    continue
                
                # Auto-resolve old threshold alerts
                if alert.alert_type.endswith('_threshold'):
                    if (current_time - alert.timestamp).hours >= 1:
                        alert.auto_resolved = True
                        alert.resolved = True
                        self.logger.info(f"Auto-resolved alert {alert.alert_id}")
        
        except Exception as e:
            self.logger.error(f"Error updating alert status: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while self._running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Cleanup every hour
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old events and alerts."""
        try:
            current_time = datetime.now()
            
            # Clean up old events
            event_cutoff = current_time - timedelta(hours=self.event_retention_hours)
            
            for event_type in list(self.event_history.keys()):
                self.event_history[event_type] = [
                    event for event in self.event_history[event_type]
                    if event.timestamp > event_cutoff
                ]
            
            # Clean up old resolved alerts
            alert_cutoff = current_time - timedelta(hours=self.alert_retention_hours)
            old_alerts = [
                alert_id for alert_id, alert in self.active_alerts.items()
                if alert.resolved and alert.timestamp < alert_cutoff
            ]
            
            for alert_id in old_alerts:
                del self.active_alerts[alert_id]
            
            if old_alerts:
                self.logger.info(f"Cleaned up {len(old_alerts)} old alerts")
        
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    def register_alert_callback(self, callback: Callable[[SecurityAlert], None]) -> None:
        """Register callback for security alerts."""
        self.alert_callbacks.append(callback)
    
    async def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge a security alert."""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.acknowledged = True
                
                self.logger.info(f"Alert {alert_id} acknowledged by {user_id}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error acknowledging alert: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str, user_id: str) -> bool:
        """Resolve a security alert."""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                
                self.logger.info(f"Alert {alert_id} resolved by {user_id}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error resolving alert: {e}")
            return False
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring status."""
        current_time = datetime.now()
        
        # Calculate recent activity
        hour_ago = current_time - timedelta(hours=1)
        recent_events = len([e for e in self.event_buffer if e.timestamp >= hour_ago])
        
        active_alert_count = len([a for a in self.active_alerts.values() if not a.resolved])
        
        return {
            'enabled': self.monitoring_enabled,
            'alert_config': {
                'enabled': self.alert_enabled,
                'thresholds': self.alert_thresholds
            },
            'log_config': {
                'retention_days': self.event_retention_hours // 24
            },
            'statistics': {
                **self.stats,
                'recent_events_hour': recent_events,
                'active_alerts': active_alert_count,
                'total_events_buffered': len(self.event_buffer)
            },
            'pattern_detection': {
                'patterns_configured': len(self.attack_patterns),
                'patterns': list(self.attack_patterns.keys())
            }
        }
    
    def get_recent_events(self, hours: int = 24, event_type: Optional[EventType] = None) -> List[SecurityEvent]:
        """Get recent security events."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        events = [e for e in self.event_buffer if e.timestamp >= cutoff_time]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return sorted(events, key=lambda x: x.timestamp, reverse=True)
    
    def get_active_alerts(self) -> List[SecurityAlert]:
        """Get active security alerts."""
        return [a for a in self.active_alerts.values() if not a.resolved]


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_security_monitor():
        """Test security monitor functionality."""
        
        # Mock Home Assistant object
        class MockHass:
            def __init__(self):
                self.data = {}
                self.bus = None
        
        hass = MockHass()
        config = {
            'monitoring_enabled': True,
            'alert_enabled': True,
            'failed_logins_per_hour': 5
        }
        
        monitor = SecurityMonitor(hass, config)
        await monitor.start_monitoring()
        
        # Test event recording
        print("Testing event recording...")
        await monitor.record_event(
            event_type=EventType.LOGIN_FAILURE,
            severity=AlertSeverity.MEDIUM,
            source='test',
            description='Test failed login',
            ip_address='127.0.0.1',
            user_id='test_user'
        )
        
        # Test multiple events to trigger pattern
        for i in range(6):
            await monitor.record_event(
                event_type=EventType.LOGIN_FAILURE,
                severity=AlertSeverity.MEDIUM,
                source='test',
                description=f'Test failed login {i}',
                ip_address='127.0.0.1',
                user_id=f'test_user_{i}'
            )
        
        # Wait for pattern detection
        await asyncio.sleep(2)
        
        # Get monitoring status
        status = monitor.get_monitoring_status()
        print(f"Monitoring status: {status}")
        
        # Get active alerts
        alerts = monitor.get_active_alerts()
        print(f"Active alerts: {len(alerts)}")
        
        await monitor.stop_monitoring()
        print("Security monitor test completed!")
    
    # Run test
    asyncio.run(test_security_monitor())