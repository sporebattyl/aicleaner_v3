"""
Phase 3C: Threat Detector
Advanced threat detection and anomaly analysis for security monitoring.
"""

import asyncio
import json
import logging
import math
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque
import hashlib
import re


class ThreatType(str, Enum):
    """Types of security threats."""
    BRUTE_FORCE = "brute_force"
    DOS_ATTACK = "dos_attack"
    CREDENTIAL_STUFFING = "credential_stuffing"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    MALWARE_ACTIVITY = "malware_activity"
    INSIDER_THREAT = "insider_threat"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    CONFIGURATION_ABUSE = "configuration_abuse"
    API_ABUSE = "api_abuse"


class AnomalyType(str, Enum):
    """Types of security anomalies."""
    STATISTICAL = "statistical"
    BEHAVIORAL = "behavioral"
    TEMPORAL = "temporal"
    FREQUENCY = "frequency"
    PATTERN = "pattern"
    OUTLIER = "outlier"


@dataclass
class ThreatIndicator:
    """Threat indicator data structure."""
    indicator_id: str
    indicator_type: str
    value: str
    threat_types: List[ThreatType]
    confidence: float
    last_seen: datetime
    first_seen: datetime
    occurrence_count: int
    source: str
    description: str


@dataclass
class Anomaly:
    """Anomaly detection result."""
    anomaly_id: str
    anomaly_type: AnomalyType
    timestamp: datetime
    confidence: float
    severity: str
    description: str
    affected_entities: List[str]
    baseline_value: Optional[float]
    observed_value: Optional[float]
    deviation_score: float
    context: Dict[str, Any]


@dataclass
class ThreatDetection:
    """Threat detection result."""
    detection_id: str
    threat_type: ThreatType
    timestamp: datetime
    confidence: float
    severity: str
    source_ips: List[str]
    target_entities: List[str]
    indicators: List[ThreatIndicator]
    anomalies: List[Anomaly]
    description: str
    recommendations: List[str]
    raw_evidence: Dict[str, Any]


class ThreatDetector:
    """
    Advanced threat detection and anomaly analysis system.
    
    Provides machine learning-based threat detection, behavioral analysis,
    and statistical anomaly detection for comprehensive security monitoring.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize threat detector.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Threat detection configuration
        self.detection_enabled = config.get('threat_detection_enabled', True)
        self.anomaly_detection_enabled = config.get('anomaly_detection_enabled', True)
        self.ml_detection_enabled = config.get('ml_detection_enabled', False)
        
        # Detection thresholds
        self.confidence_thresholds = {
            'high': config.get('high_confidence_threshold', 0.8),
            'medium': config.get('medium_confidence_threshold', 0.6),
            'low': config.get('low_confidence_threshold', 0.4)
        }
        
        # Behavioral baselines
        self.behavioral_baselines: Dict[str, Dict[str, Any]] = {}
        self.baseline_window_days = config.get('baseline_window_days', 7)
        self.baseline_update_interval = config.get('baseline_update_hours', 6)
        
        # Statistical models
        self.statistical_models: Dict[str, Dict[str, Any]] = {}
        self.anomaly_threshold = config.get('anomaly_threshold', 2.5)  # Standard deviations
        
        # Threat indicators database
        self.threat_indicators: Dict[str, ThreatIndicator] = {}
        self.indicator_retention_days = config.get('indicator_retention_days', 30)
        
        # Event history for analysis
        self.event_history: deque = deque(maxlen=10000)
        self.analysis_window_hours = config.get('analysis_window_hours', 24)
        
        # Known attack patterns
        self.attack_patterns = {
            'brute_force_patterns': [
                r'failed.*login.*\d{2,}',
                r'authentication.*failure.*repeated',
                r'invalid.*credential.*multiple'
            ],
            'dos_patterns': [
                r'request.*rate.*exceeded',
                r'connection.*limit.*reached',
                r'resource.*exhausted'
            ],
            'privilege_escalation_patterns': [
                r'sudo.*attempt.*unauthorized',
                r'elevation.*privilege.*detected',
                r'admin.*access.*unauthorized'
            ],
            'malware_patterns': [
                r'suspicious.*file.*execution',
                r'malicious.*code.*detected',
                r'virus.*signature.*match'
            ]
        }
        
        # IP reputation data (simplified)
        self.malicious_ips = set()
        self.suspicious_ips = set()
        
        # Machine learning models (placeholders for actual ML implementation)
        self.ml_models = {}
        
        self.logger.info("Threat Detector initialized")
    
    async def analyze_threats(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Analyze recent events for threats.
        
        Args:
            hours_back: Hours of history to analyze
            
        Returns:
            List of detected threats
        """
        threats = []
        
        try:
            if not self.detection_enabled:
                return threats
            
            # Get recent events for analysis
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            recent_events = [
                event for event in self.event_history
                if hasattr(event, 'timestamp') and event.timestamp >= cutoff_time
            ]
            
            if not recent_events:
                return threats
            
            # Detect brute force attacks
            brute_force_threats = await self._detect_brute_force_attacks(recent_events)
            threats.extend(brute_force_threats)
            
            # Detect DoS attacks
            dos_threats = await self._detect_dos_attacks(recent_events)
            threats.extend(dos_threats)
            
            # Detect credential stuffing
            credential_threats = await self._detect_credential_stuffing(recent_events)
            threats.extend(credential_threats)
            
            # Detect privilege escalation
            privilege_threats = await self._detect_privilege_escalation(recent_events)
            threats.extend(privilege_threats)
            
            # Detect insider threats
            insider_threats = await self._detect_insider_threats(recent_events)
            threats.extend(insider_threats)
            
            # Detect API abuse
            api_threats = await self._detect_api_abuse(recent_events)
            threats.extend(api_threats)
            
            self.logger.info(f"Analyzed {len(recent_events)} events, detected {len(threats)} threats")
            
        except Exception as e:
            self.logger.error(f"Error analyzing threats: {e}")
        
        return threats
    
    async def _detect_brute_force_attacks(self, events: List[Any]) -> List[Dict[str, Any]]:
        """Detect brute force attacks in events."""
        threats = []
        
        try:
            # Group failed login attempts by IP
            failed_logins_by_ip = defaultdict(list)
            
            for event in events:
                if (hasattr(event, 'event_type') and 
                    event.event_type.value == 'login_failure' and
                    hasattr(event, 'ip_address') and event.ip_address):
                    failed_logins_by_ip[event.ip_address].append(event)
            
            # Analyze each IP for brute force patterns
            for ip_address, login_events in failed_logins_by_ip.items():
                if len(login_events) >= 5:  # Configurable threshold
                    # Calculate attack characteristics
                    time_span = (max(e.timestamp for e in login_events) - 
                               min(e.timestamp for e in login_events)).total_seconds()
                    
                    attack_rate = len(login_events) / max(time_span / 60, 1)  # attempts per minute
                    
                    # Determine confidence and severity
                    confidence = min(0.9, 0.3 + (len(login_events) - 5) * 0.1)
                    severity = 'critical' if len(login_events) >= 20 else 'high'
                    
                    threat = {
                        'id': hashlib.md5(f"brute_force_{ip_address}_{login_events[0].timestamp}".encode()).hexdigest()[:16],
                        'type': 'brute_force',
                        'severity': severity,
                        'confidence': confidence,
                        'source_ip': ip_address,
                        'description': f"Brute force attack detected from {ip_address} with {len(login_events)} failed attempts",
                        'attack_rate': attack_rate,
                        'total_attempts': len(login_events),
                        'time_span_minutes': time_span / 60,
                        'target_users': list(set(e.user_id for e in login_events if hasattr(e, 'user_id') and e.user_id)),
                        'recommendations': [
                            f"Block IP address {ip_address}",
                            "Enable account lockout policies",
                            "Implement CAPTCHA after failed attempts",
                            "Monitor for successful logins from this IP"
                        ],
                        'remediation_effort': 'low',
                        'component': 'authentication'
                    }
                    
                    threats.append(threat)
        
        except Exception as e:
            self.logger.error(f"Error detecting brute force attacks: {e}")
        
        return threats
    
    async def _detect_dos_attacks(self, events: List[Any]) -> List[Dict[str, Any]]:
        """Detect denial of service attacks."""
        threats = []
        
        try:
            # Group API requests by IP and time windows
            api_requests_by_ip = defaultdict(list)
            
            for event in events:
                if (hasattr(event, 'event_type') and 
                    event.event_type.value == 'api_access' and
                    hasattr(event, 'ip_address') and event.ip_address):
                    api_requests_by_ip[event.ip_address].append(event)
            
            # Analyze request patterns for DoS indicators
            for ip_address, request_events in api_requests_by_ip.items():
                if len(request_events) >= 100:  # High request volume threshold
                    
                    # Calculate request rate
                    time_span = (max(e.timestamp for e in request_events) - 
                               min(e.timestamp for e in request_events)).total_seconds()
                    
                    request_rate = len(request_events) / max(time_span / 60, 1)  # requests per minute
                    
                    # Check for DoS characteristics
                    if request_rate >= 10:  # High request rate
                        confidence = min(0.9, 0.4 + (request_rate - 10) * 0.05)
                        severity = 'critical' if request_rate >= 50 else 'high'
                        
                        threat = {
                            'id': hashlib.md5(f"dos_{ip_address}_{request_events[0].timestamp}".encode()).hexdigest()[:16],
                            'type': 'dos_attack',
                            'severity': severity,
                            'confidence': confidence,
                            'source_ip': ip_address,
                            'description': f"DoS attack detected from {ip_address} with {request_rate:.1f} requests/min",
                            'request_rate': request_rate,
                            'total_requests': len(request_events),
                            'time_span_minutes': time_span / 60,
                            'recommendations': [
                                f"Rate limit IP address {ip_address}",
                                "Implement DDoS protection",
                                "Consider blocking the IP temporarily",
                                "Monitor network resources"
                            ],
                            'remediation_effort': 'medium',
                            'component': 'network'
                        }
                        
                        threats.append(threat)
        
        except Exception as e:
            self.logger.error(f"Error detecting DoS attacks: {e}")
        
        return threats
    
    async def _detect_credential_stuffing(self, events: List[Any]) -> List[Dict[str, Any]]:
        """Detect credential stuffing attacks."""
        threats = []
        
        try:
            # Look for failed logins across multiple usernames from same IP
            login_attempts_by_ip = defaultdict(lambda: {'users': set(), 'events': []})
            
            for event in events:
                if (hasattr(event, 'event_type') and 
                    event.event_type.value in ['login_failure', 'login_success'] and
                    hasattr(event, 'ip_address') and event.ip_address and
                    hasattr(event, 'user_id') and event.user_id):
                    
                    ip_data = login_attempts_by_ip[event.ip_address]
                    ip_data['users'].add(event.user_id)
                    ip_data['events'].append(event)
            
            # Analyze for credential stuffing patterns
            for ip_address, ip_data in login_attempts_by_ip.items():
                unique_users = len(ip_data['users'])
                total_attempts = len(ip_data['events'])
                
                # Credential stuffing indicators: many users, many attempts
                if unique_users >= 5 and total_attempts >= 20:
                    failed_attempts = [e for e in ip_data['events'] 
                                     if hasattr(e, 'event_type') and e.event_type.value == 'login_failure']
                    
                    success_rate = (total_attempts - len(failed_attempts)) / total_attempts
                    
                    # Low success rate indicates credential stuffing
                    if success_rate <= 0.1:  # Less than 10% success rate
                        confidence = min(0.9, 0.5 + (unique_users - 5) * 0.05)
                        severity = 'high'
                        
                        threat = {
                            'id': hashlib.md5(f"credential_stuffing_{ip_address}_{ip_data['events'][0].timestamp}".encode()).hexdigest()[:16],
                            'type': 'credential_stuffing',
                            'severity': severity,
                            'confidence': confidence,
                            'source_ip': ip_address,
                            'description': f"Credential stuffing attack from {ip_address} targeting {unique_users} users",
                            'unique_users_targeted': unique_users,
                            'total_attempts': total_attempts,
                            'success_rate': success_rate,
                            'recommendations': [
                                f"Block IP address {ip_address}",
                                "Implement account lockout policies",
                                "Enable multi-factor authentication",
                                "Monitor for compromised credentials"
                            ],
                            'remediation_effort': 'medium',
                            'component': 'authentication'
                        }
                        
                        threats.append(threat)
        
        except Exception as e:
            self.logger.error(f"Error detecting credential stuffing: {e}")
        
        return threats
    
    async def _detect_privilege_escalation(self, events: List[Any]) -> List[Dict[str, Any]]:
        """Detect privilege escalation attempts."""
        threats = []
        
        try:
            # Look for suspicious privilege-related activities
            privilege_events = []
            
            for event in events:
                if hasattr(event, 'description'):
                    description = event.description.lower()
                    
                    # Check for privilege escalation indicators
                    escalation_indicators = [
                        'sudo', 'admin', 'root', 'privilege', 'elevation',
                        'unauthorized', 'escalation', 'permission denied'
                    ]
                    
                    if any(indicator in description for indicator in escalation_indicators):
                        privilege_events.append(event)
            
            # Group by user and analyze patterns
            events_by_user = defaultdict(list)
            for event in privilege_events:
                if hasattr(event, 'user_id') and event.user_id:
                    events_by_user[event.user_id].append(event)
            
            # Analyze each user's privilege-related activity
            for user_id, user_events in events_by_user.items():
                if len(user_events) >= 3:  # Multiple privilege-related events
                    
                    # Check for escalation patterns
                    escalation_attempts = 0
                    for event in user_events:
                        if hasattr(event, 'description'):
                            desc = event.description.lower()
                            if any(word in desc for word in ['denied', 'failed', 'unauthorized']):
                                escalation_attempts += 1
                    
                    if escalation_attempts >= 2:
                        confidence = min(0.8, 0.4 + escalation_attempts * 0.1)
                        severity = 'high' if escalation_attempts >= 5 else 'medium'
                        
                        threat = {
                            'id': hashlib.md5(f"privilege_escalation_{user_id}_{user_events[0].timestamp}".encode()).hexdigest()[:16],
                            'type': 'privilege_escalation',
                            'severity': severity,
                            'confidence': confidence,
                            'user_id': user_id,
                            'description': f"Privilege escalation attempts detected for user {user_id}",
                            'escalation_attempts': escalation_attempts,
                            'total_events': len(user_events),
                            'recommendations': [
                                f"Review user {user_id} permissions",
                                "Audit privilege escalation attempts",
                                "Implement principle of least privilege",
                                "Monitor user activity closely"
                            ],
                            'remediation_effort': 'medium',
                            'component': 'authorization'
                        }
                        
                        threats.append(threat)
        
        except Exception as e:
            self.logger.error(f"Error detecting privilege escalation: {e}")
        
        return threats
    
    async def _detect_insider_threats(self, events: List[Any]) -> List[Dict[str, Any]]:
        """Detect insider threat indicators."""
        threats = []
        
        try:
            # Analyze user behavior patterns
            user_activities = defaultdict(lambda: {
                'login_times': [],
                'access_patterns': [],
                'config_changes': 0,
                'data_access': 0,
                'unusual_activities': []
            })
            
            for event in events:
                if hasattr(event, 'user_id') and event.user_id:
                    user_data = user_activities[event.user_id]
                    
                    if hasattr(event, 'timestamp'):
                        # Track login times
                        if hasattr(event, 'event_type') and event.event_type.value == 'login_success':
                            user_data['login_times'].append(event.timestamp)
                        
                        # Track configuration changes
                        elif hasattr(event, 'event_type') and event.event_type.value == 'config_change':
                            user_data['config_changes'] += 1
                        
                        # Track data access
                        elif hasattr(event, 'event_type') and event.event_type.value == 'api_access':
                            user_data['data_access'] += 1
                        
                        # Track unusual activities
                        if hasattr(event, 'description'):
                            unusual_indicators = ['download', 'export', 'backup', 'copy', 'transfer']
                            if any(indicator in event.description.lower() for indicator in unusual_indicators):
                                user_data['unusual_activities'].append(event)
            
            # Analyze each user for insider threat indicators
            for user_id, user_data in user_activities.items():
                threat_score = 0
                indicators = []
                
                # Check for unusual login times
                if user_data['login_times']:
                    login_hours = [t.hour for t in user_data['login_times']]
                    unusual_hours = [h for h in login_hours if h < 6 or h > 22]  # Outside business hours
                    
                    if len(unusual_hours) >= 3:
                        threat_score += 0.2
                        indicators.append(f"Unusual login times: {len(unusual_hours)} logins outside business hours")
                
                # Check for excessive configuration changes
                if user_data['config_changes'] >= 10:
                    threat_score += 0.3
                    indicators.append(f"Excessive configuration changes: {user_data['config_changes']}")
                
                # Check for high data access
                if user_data['data_access'] >= 100:
                    threat_score += 0.2
                    indicators.append(f"High data access volume: {user_data['data_access']} API calls")
                
                # Check for unusual activities
                if len(user_data['unusual_activities']) >= 5:
                    threat_score += 0.3
                    indicators.append(f"Unusual activities: {len(user_data['unusual_activities'])} suspicious actions")
                
                # Generate threat if score is significant
                if threat_score >= 0.5:
                    confidence = min(0.8, threat_score)
                    severity = 'high' if threat_score >= 0.7 else 'medium'
                    
                    threat = {
                        'id': hashlib.md5(f"insider_threat_{user_id}_{datetime.now()}".encode()).hexdigest()[:16],
                        'type': 'insider_threat',
                        'severity': severity,
                        'confidence': confidence,
                        'user_id': user_id,
                        'description': f"Insider threat indicators detected for user {user_id}",
                        'threat_score': threat_score,
                        'indicators': indicators,
                        'recommendations': [
                            f"Review user {user_id} access and activities",
                            "Implement additional monitoring",
                            "Consider access restrictions",
                            "Conduct security interview if necessary"
                        ],
                        'remediation_effort': 'high',
                        'component': 'user_behavior'
                    }
                    
                    threats.append(threat)
        
        except Exception as e:
            self.logger.error(f"Error detecting insider threats: {e}")
        
        return threats
    
    async def _detect_api_abuse(self, events: List[Any]) -> List[Dict[str, Any]]:
        """Detect API abuse patterns."""
        threats = []
        
        try:
            # Analyze API usage patterns
            api_usage = defaultdict(lambda: {
                'endpoints': defaultdict(int),
                'methods': defaultdict(int),
                'response_codes': defaultdict(int),
                'total_requests': 0
            })
            
            for event in events:
                if (hasattr(event, 'event_type') and 
                    event.event_type.value == 'api_access' and
                    hasattr(event, 'ip_address') and event.ip_address):
                    
                    usage_data = api_usage[event.ip_address]
                    usage_data['total_requests'] += 1
                    
                    # Extract API details from event
                    if hasattr(event, 'details'):
                        details = event.details
                        
                        if 'endpoint' in details:
                            usage_data['endpoints'][details['endpoint']] += 1
                        
                        if 'method' in details:
                            usage_data['methods'][details['method']] += 1
                        
                        if 'response_code' in details:
                            usage_data['response_codes'][details['response_code']] += 1
            
            # Analyze each IP for API abuse
            for ip_address, usage_data in api_usage.items():
                threat_indicators = []
                abuse_score = 0
                
                # Check for excessive requests
                if usage_data['total_requests'] >= 200:
                    abuse_score += 0.3
                    threat_indicators.append(f"High request volume: {usage_data['total_requests']} requests")
                
                # Check for error rate abuse
                error_codes = [code for code in usage_data['response_codes'].keys() 
                              if str(code).startswith(('4', '5'))]
                total_errors = sum(usage_data['response_codes'][code] for code in error_codes)
                error_rate = total_errors / max(usage_data['total_requests'], 1)
                
                if error_rate >= 0.3:  # High error rate
                    abuse_score += 0.2
                    threat_indicators.append(f"High error rate: {error_rate:.1%}")
                
                # Check for endpoint scanning
                unique_endpoints = len(usage_data['endpoints'])
                if unique_endpoints >= 20:
                    abuse_score += 0.3
                    threat_indicators.append(f"Endpoint scanning: {unique_endpoints} different endpoints")
                
                # Check for method abuse
                if 'DELETE' in usage_data['methods'] and usage_data['methods']['DELETE'] >= 10:
                    abuse_score += 0.2
                    threat_indicators.append(f"Excessive DELETE operations: {usage_data['methods']['DELETE']}")
                
                # Generate threat if abuse detected
                if abuse_score >= 0.4:
                    confidence = min(0.9, abuse_score)
                    severity = 'high' if abuse_score >= 0.7 else 'medium'
                    
                    threat = {
                        'id': hashlib.md5(f"api_abuse_{ip_address}_{datetime.now()}".encode()).hexdigest()[:16],
                        'type': 'api_abuse',
                        'severity': severity,
                        'confidence': confidence,
                        'source_ip': ip_address,
                        'description': f"API abuse detected from {ip_address}",
                        'abuse_score': abuse_score,
                        'indicators': threat_indicators,
                        'total_requests': usage_data['total_requests'],
                        'error_rate': error_rate,
                        'unique_endpoints': unique_endpoints,
                        'recommendations': [
                            f"Rate limit IP address {ip_address}",
                            "Implement API abuse detection",
                            "Review API security policies",
                            "Consider blocking suspicious patterns"
                        ],
                        'remediation_effort': 'medium',
                        'component': 'api'
                    }
                    
                    threats.append(threat)
        
        except Exception as e:
            self.logger.error(f"Error detecting API abuse: {e}")
        
        return threats
    
    async def detect_anomalies(self) -> List[Dict[str, Any]]:
        """
        Detect statistical and behavioral anomalies.
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        try:
            if not self.anomaly_detection_enabled:
                return anomalies
            
            # Detect statistical anomalies
            statistical_anomalies = await self._detect_statistical_anomalies()
            anomalies.extend(statistical_anomalies)
            
            # Detect behavioral anomalies
            behavioral_anomalies = await self._detect_behavioral_anomalies()
            anomalies.extend(behavioral_anomalies)
            
            # Detect temporal anomalies
            temporal_anomalies = await self._detect_temporal_anomalies()
            anomalies.extend(temporal_anomalies)
            
            self.logger.info(f"Detected {len(anomalies)} anomalies")
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
        
        return anomalies
    
    async def _detect_statistical_anomalies(self) -> List[Dict[str, Any]]:
        """Detect statistical anomalies using Z-score analysis."""
        anomalies = []
        
        try:
            # Analyze recent event patterns
            current_time = datetime.now()
            recent_events = [
                event for event in self.event_history
                if hasattr(event, 'timestamp') and 
                (current_time - event.timestamp).total_seconds() <= 3600  # Last hour
            ]
            
            if len(recent_events) < 10:  # Need minimum data points
                return anomalies
            
            # Calculate hourly event rates for baseline
            hourly_rates = []
            for hour_offset in range(24, 168):  # 24-168 hours ago (1-7 days)
                hour_start = current_time - timedelta(hours=hour_offset + 1)
                hour_end = current_time - timedelta(hours=hour_offset)
                
                hour_events = [
                    event for event in self.event_history
                    if hasattr(event, 'timestamp') and hour_start <= event.timestamp < hour_end
                ]
                
                hourly_rates.append(len(hour_events))
            
            if len(hourly_rates) < 24:  # Need baseline data
                return anomalies
            
            # Calculate statistical measures
            mean_rate = statistics.mean(hourly_rates)
            std_dev = statistics.stdev(hourly_rates) if len(hourly_rates) > 1 else 0
            
            if std_dev == 0:
                return anomalies
            
            # Check current hour rate against baseline
            current_rate = len(recent_events)
            z_score = (current_rate - mean_rate) / std_dev
            
            # Detect anomaly if Z-score exceeds threshold
            if abs(z_score) >= self.anomaly_threshold:
                confidence = min(0.9, abs(z_score) / 5.0)
                severity = 'high' if abs(z_score) >= 4 else 'medium'
                
                anomaly = {
                    'id': hashlib.md5(f"statistical_anomaly_{current_time}".encode()).hexdigest()[:16],
                    'type': 'statistical',
                    'severity': severity,
                    'confidence': confidence,
                    'description': f"Statistical anomaly in event rate: {current_rate} events (baseline: {mean_rate:.1f}±{std_dev:.1f})",
                    'z_score': z_score,
                    'current_value': current_rate,
                    'baseline_mean': mean_rate,
                    'baseline_std': std_dev,
                    'recommendations': [
                        "Investigate cause of event rate anomaly",
                        "Check system health",
                        "Review recent changes"
                    ],
                    'remediation_effort': 'low',
                    'component': 'system'
                }
                
                anomalies.append(anomaly)
        
        except Exception as e:
            self.logger.error(f"Error detecting statistical anomalies: {e}")
        
        return anomalies
    
    async def _detect_behavioral_anomalies(self) -> List[Dict[str, Any]]:
        """Detect behavioral anomalies in user patterns."""
        anomalies = []
        
        try:
            # Analyze user behavior patterns
            current_time = datetime.now()
            user_behaviors = defaultdict(lambda: {
                'current_activity': 0,
                'historical_avg': 0,
                'login_pattern': [],
                'access_pattern': []
            })
            
            # Collect current hour activity
            hour_ago = current_time - timedelta(hours=1)
            current_events = [
                event for event in self.event_history
                if hasattr(event, 'timestamp') and event.timestamp >= hour_ago and
                hasattr(event, 'user_id') and event.user_id
            ]
            
            for event in current_events:
                user_behaviors[event.user_id]['current_activity'] += 1
            
            # Collect historical activity for comparison
            for hour_offset in range(24, 168):  # 1-7 days ago
                hour_start = current_time - timedelta(hours=hour_offset + 1)
                hour_end = current_time - timedelta(hours=hour_offset)
                
                hour_events = [
                    event for event in self.event_history
                    if hasattr(event, 'timestamp') and hour_start <= event.timestamp < hour_end and
                    hasattr(event, 'user_id') and event.user_id
                ]
                
                user_activities = defaultdict(int)
                for event in hour_events:
                    user_activities[event.user_id] += 1
                
                # Update historical averages
                for user_id, activity in user_activities.items():
                    if user_id in user_behaviors:
                        user_behaviors[user_id]['historical_avg'] += activity
            
            # Calculate averages and detect anomalies
            for user_id, behavior in user_behaviors.items():
                if behavior['historical_avg'] > 0:
                    avg_activity = behavior['historical_avg'] / min(144, len(self.event_history))  # 6 days * 24 hours
                    
                    if avg_activity > 0 and behavior['current_activity'] > 0:
                        ratio = behavior['current_activity'] / avg_activity
                        
                        # Detect significant deviations
                        if ratio >= 3.0 or ratio <= 0.3:
                            confidence = min(0.8, abs(math.log(ratio)) / 3)
                            severity = 'medium' if ratio >= 5.0 or ratio <= 0.2 else 'low'
                            
                            anomaly = {
                                'id': hashlib.md5(f"behavioral_anomaly_{user_id}_{current_time}".encode()).hexdigest()[:16],
                                'type': 'behavioral',
                                'severity': severity,
                                'confidence': confidence,
                                'user_id': user_id,
                                'description': f"Behavioral anomaly for user {user_id}: {behavior['current_activity']} vs avg {avg_activity:.1f}",
                                'activity_ratio': ratio,
                                'current_activity': behavior['current_activity'],
                                'average_activity': avg_activity,
                                'recommendations': [
                                    f"Review user {user_id} recent activity",
                                    "Check for account compromise",
                                    "Verify legitimate activity"
                                ],
                                'remediation_effort': 'medium',
                                'component': 'user_behavior'
                            }
                            
                            anomalies.append(anomaly)
        
        except Exception as e:
            self.logger.error(f"Error detecting behavioral anomalies: {e}")
        
        return anomalies
    
    async def _detect_temporal_anomalies(self) -> List[Dict[str, Any]]:
        """Detect temporal anomalies in event timing."""
        anomalies = []
        
        try:
            current_time = datetime.now()
            current_hour = current_time.hour
            
            # Analyze activity by hour of day
            hourly_activity = defaultdict(list)
            
            # Collect historical hourly data
            for hour_offset in range(24, 168):  # 1-7 days ago
                event_time = current_time - timedelta(hours=hour_offset)
                hour_key = event_time.hour
                
                hour_start = event_time.replace(minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=1)
                
                hour_events = [
                    event for event in self.event_history
                    if hasattr(event, 'timestamp') and hour_start <= event.timestamp < hour_end
                ]
                
                hourly_activity[hour_key].append(len(hour_events))
            
            # Get current hour activity
            current_hour_start = current_time.replace(minute=0, second=0, microsecond=0)
            current_hour_events = [
                event for event in self.event_history
                if hasattr(event, 'timestamp') and event.timestamp >= current_hour_start
            ]
            
            current_activity = len(current_hour_events)
            
            # Check if current activity is anomalous for this hour
            if current_hour in hourly_activity and len(hourly_activity[current_hour]) >= 3:
                historical_activities = hourly_activity[current_hour]
                avg_activity = statistics.mean(historical_activities)
                std_activity = statistics.stdev(historical_activities) if len(historical_activities) > 1 else 0
                
                if std_activity > 0:
                    z_score = (current_activity - avg_activity) / std_activity
                    
                    if abs(z_score) >= 2.0:  # Significant deviation
                        confidence = min(0.8, abs(z_score) / 4.0)
                        severity = 'medium' if abs(z_score) >= 3.0 else 'low'
                        
                        anomaly = {
                            'id': hashlib.md5(f"temporal_anomaly_{current_hour}_{current_time}".encode()).hexdigest()[:16],
                            'type': 'temporal',
                            'severity': severity,
                            'confidence': confidence,
                            'description': f"Temporal anomaly at hour {current_hour}: {current_activity} events vs avg {avg_activity:.1f}",
                            'hour_of_day': current_hour,
                            'z_score': z_score,
                            'current_activity': current_activity,
                            'average_activity': avg_activity,
                            'recommendations': [
                                f"Investigate unusual activity at hour {current_hour}",
                                "Check for scheduled tasks or automated processes",
                                "Review system logs for this time period"
                            ],
                            'remediation_effort': 'low',
                            'component': 'temporal_patterns'
                        }
                        
                        anomalies.append(anomaly)
        
        except Exception as e:
            self.logger.error(f"Error detecting temporal anomalies: {e}")
        
        return anomalies
    
    def add_event_to_history(self, event: Any) -> None:
        """Add event to analysis history."""
        self.event_history.append(event)
    
    def update_threat_indicator(self, indicator_type: str, value: str, 
                               threat_types: List[ThreatType], confidence: float) -> None:
        """Update threat indicator database."""
        indicator_id = hashlib.md5(f"{indicator_type}_{value}".encode()).hexdigest()
        
        if indicator_id in self.threat_indicators:
            indicator = self.threat_indicators[indicator_id]
            indicator.last_seen = datetime.now()
            indicator.occurrence_count += 1
        else:
            indicator = ThreatIndicator(
                indicator_id=indicator_id,
                indicator_type=indicator_type,
                value=value,
                threat_types=threat_types,
                confidence=confidence,
                last_seen=datetime.now(),
                first_seen=datetime.now(),
                occurrence_count=1,
                source='system',
                description=f"{indicator_type} indicator: {value}"
            )
            self.threat_indicators[indicator_id] = indicator
    
    def get_threat_intelligence(self) -> Dict[str, Any]:
        """Get threat intelligence summary."""
        current_time = datetime.now()
        
        # Recent indicators
        recent_indicators = [
            indicator for indicator in self.threat_indicators.values()
            if (current_time - indicator.last_seen).days <= 7
        ]
        
        # Threat statistics
        threat_stats = defaultdict(int)
        for indicator in recent_indicators:
            for threat_type in indicator.threat_types:
                threat_stats[threat_type.value] += 1
        
        return {
            'total_indicators': len(self.threat_indicators),
            'recent_indicators': len(recent_indicators),
            'threat_type_distribution': dict(threat_stats),
            'detection_capabilities': {
                'brute_force': True,
                'dos_attacks': True,
                'credential_stuffing': True,
                'privilege_escalation': True,
                'insider_threats': True,
                'api_abuse': True,
                'anomaly_detection': self.anomaly_detection_enabled
            },
            'configuration': {
                'anomaly_threshold': self.anomaly_threshold,
                'confidence_thresholds': self.confidence_thresholds,
                'analysis_window_hours': self.analysis_window_hours
            }
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_threat_detector():
        """Test threat detector functionality."""
        
        config = {
            'threat_detection_enabled': True,
            'anomaly_detection_enabled': True,
            'anomaly_threshold': 2.0
        }
        
        detector = ThreatDetector(config)
        
        # Test threat analysis
        print("Testing threat detection...")
        threats = await detector.analyze_threats(hours_back=24)
        print(f"Detected {len(threats)} threats")
        
        # Test anomaly detection
        print("Testing anomaly detection...")
        anomalies = await detector.detect_anomalies()
        print(f"Detected {len(anomalies)} anomalies")
        
        # Get threat intelligence
        intelligence = detector.get_threat_intelligence()
        print(f"Threat intelligence: {intelligence}")
        
        print("Threat detector test completed!")
    
    # Run test
    asyncio.run(test_threat_detector())