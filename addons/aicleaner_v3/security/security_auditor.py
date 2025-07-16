"""
Phase 3C: Security Auditor
Central security audit orchestrator and comprehensive security assessment engine.
"""

import asyncio
import json
import logging
import os
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .vulnerability_scanner import VulnerabilityScanner
from .access_control import AccessControlManager
from .security_monitor import SecurityMonitor
from .threat_detection import ThreatDetector
from .compliance_checker import ComplianceChecker


class SecurityLevel(str, Enum):
    """Security assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditScope(str, Enum):
    """Audit scope options."""
    QUICK = "quick"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    DEEP = "deep"


@dataclass
class SecurityFinding:
    """Security audit finding."""
    id: str
    title: str
    description: str
    severity: SecurityLevel
    category: str
    affected_component: str
    evidence: Dict[str, Any]
    recommendations: List[str]
    cve_references: List[str]
    remediation_effort: str  # low, medium, high
    timestamp: datetime


@dataclass
class SecurityReport:
    """Comprehensive security audit report."""
    audit_id: str
    timestamp: datetime
    scope: AuditScope
    duration_seconds: float
    overall_score: float
    security_level: SecurityLevel
    findings: List[SecurityFinding]
    summary: Dict[str, Any]
    recommendations: List[str]
    compliance_status: Dict[str, Any]
    next_audit_recommended: datetime


class SecurityAuditor:
    """
    Comprehensive security auditor for AICleaner v3.
    
    Provides end-to-end security assessment including vulnerability scanning,
    access control analysis, threat detection, and compliance checking.
    """
    
    def __init__(self, hass, config: Dict[str, Any]):
        """
        Initialize security auditor.
        
        Args:
            hass: Home Assistant instance
            config: Configuration dictionary
        """
        self.hass = hass
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize security components
        self.vulnerability_scanner = VulnerabilityScanner(config)
        self.access_control = AccessControlManager(hass, config)
        self.security_monitor = SecurityMonitor(hass, config)
        self.threat_detector = ThreatDetector(config)
        self.compliance_checker = ComplianceChecker(config)
        
        # Audit configuration
        self.audit_history_path = config.get('audit_history_path', '/data/security_audits')
        self.max_audit_history = config.get('max_audit_history', 50)
        self.auto_audit_interval_hours = config.get('auto_audit_interval_hours', 24)
        
        # Security thresholds
        self.security_thresholds = {
            SecurityLevel.LOW: 80,
            SecurityLevel.MEDIUM: 60,
            SecurityLevel.HIGH: 40,
            SecurityLevel.CRITICAL: 20
        }
        
        # Component weights for overall scoring
        self.component_weights = {
            'vulnerability_scan': 0.25,
            'access_control': 0.20,
            'threat_detection': 0.20,
            'compliance': 0.20,
            'monitoring': 0.15
        }
        
        # Audit state
        self.current_audit_id: Optional[str] = None
        self.audit_in_progress = False
        self.last_audit_time: Optional[datetime] = None
        
        # Auto-audit task
        self._auto_audit_task: Optional[asyncio.Task] = None
        
        self.logger.info("Security Auditor initialized")
    
    async def start_auto_audit(self) -> None:
        """Start automatic security auditing."""
        if self._auto_audit_task:
            return
        
        self._auto_audit_task = asyncio.create_task(self._auto_audit_loop())
        self.logger.info("Auto-audit started")
    
    async def stop_auto_audit(self) -> None:
        """Stop automatic security auditing."""
        if self._auto_audit_task:
            self._auto_audit_task.cancel()
            try:
                await self._auto_audit_task
            except asyncio.CancelledError:
                pass
            self._auto_audit_task = None
        
        self.logger.info("Auto-audit stopped")
    
    async def _auto_audit_loop(self) -> None:
        """Automatic audit loop."""
        while True:
            try:
                await asyncio.sleep(self.auto_audit_interval_hours * 3600)
                
                # Run standard audit
                self.logger.info("Running scheduled security audit")
                await self.run_security_audit(scope=AuditScope.STANDARD)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in auto-audit loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def run_security_audit(self, scope: AuditScope = AuditScope.STANDARD) -> SecurityReport:
        """
        Run comprehensive security audit.
        
        Args:
            scope: Audit scope and depth
            
        Returns:
            Security audit report
        """
        if self.audit_in_progress:
            raise RuntimeError("Security audit already in progress")
        
        audit_id = self._generate_audit_id()
        start_time = datetime.now()
        
        try:
            self.audit_in_progress = True
            self.current_audit_id = audit_id
            
            self.logger.info(f"Starting security audit {audit_id} with scope: {scope.value}")
            
            # Initialize findings list
            all_findings: List[SecurityFinding] = []
            component_scores = {}
            
            # 1. Vulnerability Scanning
            self.logger.info("Running vulnerability scan...")
            vuln_findings, vuln_score = await self._run_vulnerability_scan(scope)
            all_findings.extend(vuln_findings)
            component_scores['vulnerability_scan'] = vuln_score
            
            # 2. Access Control Analysis
            self.logger.info("Analyzing access controls...")
            access_findings, access_score = await self._run_access_control_audit(scope)
            all_findings.extend(access_findings)
            component_scores['access_control'] = access_score
            
            # 3. Threat Detection Analysis
            self.logger.info("Running threat detection analysis...")
            threat_findings, threat_score = await self._run_threat_detection_audit(scope)
            all_findings.extend(threat_findings)
            component_scores['threat_detection'] = threat_score
            
            # 4. Compliance Checking
            self.logger.info("Checking compliance...")
            compliance_findings, compliance_score, compliance_status = await self._run_compliance_audit(scope)
            all_findings.extend(compliance_findings)
            component_scores['compliance'] = compliance_score
            
            # 5. Security Monitoring Analysis
            self.logger.info("Analyzing security monitoring...")
            monitor_findings, monitor_score = await self._run_monitoring_audit(scope)
            all_findings.extend(monitor_findings)
            component_scores['monitoring'] = monitor_score
            
            # Calculate overall security score
            overall_score = self._calculate_overall_score(component_scores)
            security_level = self._determine_security_level(overall_score)
            
            # Generate summary and recommendations
            summary = self._generate_audit_summary(component_scores, all_findings)
            recommendations = self._generate_recommendations(all_findings, component_scores)
            
            # Create audit report
            duration = (datetime.now() - start_time).total_seconds()
            
            report = SecurityReport(
                audit_id=audit_id,
                timestamp=start_time,
                scope=scope,
                duration_seconds=duration,
                overall_score=overall_score,
                security_level=security_level,
                findings=all_findings,
                summary=summary,
                recommendations=recommendations,
                compliance_status=compliance_status,
                next_audit_recommended=self._calculate_next_audit_time(security_level)
            )
            
            # Save audit report
            await self._save_audit_report(report)
            
            # Update audit state
            self.last_audit_time = start_time
            
            self.logger.info(
                f"Security audit {audit_id} completed. "
                f"Score: {overall_score:.1f}/100, Level: {security_level.value}, "
                f"Findings: {len(all_findings)}, Duration: {duration:.1f}s"
            )
            
            return report
        
        finally:
            self.audit_in_progress = False
            self.current_audit_id = None
    
    async def _run_vulnerability_scan(self, scope: AuditScope) -> Tuple[List[SecurityFinding], float]:
        """Run vulnerability scanning."""
        findings = []
        
        try:
            # Scan dependencies
            dependency_vulns = await self.vulnerability_scanner.scan_dependencies()
            for vuln in dependency_vulns:
                finding = SecurityFinding(
                    id=f"vuln_dep_{vuln.get('id', 'unknown')}",
                    title=f"Vulnerable Dependency: {vuln.get('package', 'Unknown')}",
                    description=vuln.get('description', 'Vulnerable dependency detected'),
                    severity=SecurityLevel(vuln.get('severity', 'medium')),
                    category="vulnerability",
                    affected_component=vuln.get('package', 'dependencies'),
                    evidence=vuln,
                    recommendations=vuln.get('recommendations', []),
                    cve_references=vuln.get('cve_references', []),
                    remediation_effort=vuln.get('remediation_effort', 'medium'),
                    timestamp=datetime.now()
                )
                findings.append(finding)
            
            # Scan configuration
            if scope in [AuditScope.STANDARD, AuditScope.COMPREHENSIVE, AuditScope.DEEP]:
                config_vulns = await self.vulnerability_scanner.scan_configuration()
                for vuln in config_vulns:
                    finding = SecurityFinding(
                        id=f"vuln_config_{hashlib.md5(str(vuln).encode()).hexdigest()[:8]}",
                        title=f"Configuration Vulnerability: {vuln.get('title', 'Unknown')}",
                        description=vuln.get('description', 'Configuration vulnerability detected'),
                        severity=SecurityLevel(vuln.get('severity', 'medium')),
                        category="configuration",
                        affected_component=vuln.get('component', 'configuration'),
                        evidence=vuln,
                        recommendations=vuln.get('recommendations', []),
                        cve_references=[],
                        remediation_effort=vuln.get('remediation_effort', 'low'),
                        timestamp=datetime.now()
                    )
                    findings.append(finding)
            
            # Scan file permissions
            if scope in [AuditScope.COMPREHENSIVE, AuditScope.DEEP]:
                permission_issues = await self.vulnerability_scanner.scan_file_permissions()
                for issue in permission_issues:
                    finding = SecurityFinding(
                        id=f"vuln_perm_{hashlib.md5(issue.get('file', '').encode()).hexdigest()[:8]}",
                        title=f"File Permission Issue: {issue.get('file', 'Unknown')}",
                        description=issue.get('description', 'Insecure file permissions detected'),
                        severity=SecurityLevel(issue.get('severity', 'low')),
                        category="permissions",
                        affected_component=issue.get('file', 'filesystem'),
                        evidence=issue,
                        recommendations=issue.get('recommendations', []),
                        cve_references=[],
                        remediation_effort='low',
                        timestamp=datetime.now()
                    )
                    findings.append(finding)
            
            # Calculate vulnerability score
            if not findings:
                score = 100.0
            else:
                # Weight by severity
                severity_weights = {
                    SecurityLevel.LOW: 1,
                    SecurityLevel.MEDIUM: 3,
                    SecurityLevel.HIGH: 5,
                    SecurityLevel.CRITICAL: 10
                }
                
                total_weight = sum(severity_weights[f.severity] for f in findings)
                max_possible = len(findings) * severity_weights[SecurityLevel.CRITICAL]
                score = max(0, 100 - (total_weight / max(max_possible, 1)) * 100)
            
            return findings, score
        
        except Exception as e:
            self.logger.error(f"Error in vulnerability scan: {e}")
            return [], 0.0
    
    async def _run_access_control_audit(self, scope: AuditScope) -> Tuple[List[SecurityFinding], float]:
        """Run access control analysis."""
        findings = []
        
        try:
            # Check authentication
            auth_issues = await self.access_control.audit_authentication()
            for issue in auth_issues:
                finding = SecurityFinding(
                    id=f"access_auth_{hashlib.md5(str(issue).encode()).hexdigest()[:8]}",
                    title=f"Authentication Issue: {issue.get('title', 'Unknown')}",
                    description=issue.get('description', 'Authentication security issue'),
                    severity=SecurityLevel(issue.get('severity', 'medium')),
                    category="authentication",
                    affected_component=issue.get('component', 'authentication'),
                    evidence=issue,
                    recommendations=issue.get('recommendations', []),
                    cve_references=[],
                    remediation_effort=issue.get('remediation_effort', 'medium'),
                    timestamp=datetime.now()
                )
                findings.append(finding)
            
            # Check authorization
            if scope in [AuditScope.STANDARD, AuditScope.COMPREHENSIVE, AuditScope.DEEP]:
                authz_issues = await self.access_control.audit_authorization()
                for issue in authz_issues:
                    finding = SecurityFinding(
                        id=f"access_authz_{hashlib.md5(str(issue).encode()).hexdigest()[:8]}",
                        title=f"Authorization Issue: {issue.get('title', 'Unknown')}",
                        description=issue.get('description', 'Authorization security issue'),
                        severity=SecurityLevel(issue.get('severity', 'medium')),
                        category="authorization",
                        affected_component=issue.get('component', 'authorization'),
                        evidence=issue,
                        recommendations=issue.get('recommendations', []),
                        cve_references=[],
                        remediation_effort=issue.get('remediation_effort', 'medium'),
                        timestamp=datetime.now()
                    )
                    findings.append(finding)
            
            # Check API security
            if scope in [AuditScope.COMPREHENSIVE, AuditScope.DEEP]:
                api_issues = await self.access_control.audit_api_security()
                for issue in api_issues:
                    finding = SecurityFinding(
                        id=f"access_api_{hashlib.md5(str(issue).encode()).hexdigest()[:8]}",
                        title=f"API Security Issue: {issue.get('title', 'Unknown')}",
                        description=issue.get('description', 'API security issue'),
                        severity=SecurityLevel(issue.get('severity', 'medium')),
                        category="api_security",
                        affected_component=issue.get('component', 'api'),
                        evidence=issue,
                        recommendations=issue.get('recommendations', []),
                        cve_references=[],
                        remediation_effort=issue.get('remediation_effort', 'medium'),
                        timestamp=datetime.now()
                    )
                    findings.append(finding)
            
            # Calculate access control score
            score = max(0, 100 - len(findings) * 10)  # Simple scoring
            return findings, score
        
        except Exception as e:
            self.logger.error(f"Error in access control audit: {e}")
            return [], 0.0
    
    async def _run_threat_detection_audit(self, scope: AuditScope) -> Tuple[List[SecurityFinding], float]:
        """Run threat detection analysis."""
        findings = []
        
        try:
            # Analyze recent threats
            threats = await self.threat_detector.analyze_threats(
                hours_back=24 if scope == AuditScope.QUICK else 168
            )
            
            for threat in threats:
                finding = SecurityFinding(
                    id=f"threat_{threat.get('id', hashlib.md5(str(threat).encode()).hexdigest()[:8])}",
                    title=f"Threat Detected: {threat.get('type', 'Unknown')}",
                    description=threat.get('description', 'Security threat detected'),
                    severity=SecurityLevel(threat.get('severity', 'medium')),
                    category="threat",
                    affected_component=threat.get('component', 'system'),
                    evidence=threat,
                    recommendations=threat.get('recommendations', []),
                    cve_references=[],
                    remediation_effort=threat.get('remediation_effort', 'medium'),
                    timestamp=datetime.now()
                )
                findings.append(finding)
            
            # Check anomaly detection
            if scope in [AuditScope.STANDARD, AuditScope.COMPREHENSIVE, AuditScope.DEEP]:
                anomalies = await self.threat_detector.detect_anomalies()
                for anomaly in anomalies:
                    finding = SecurityFinding(
                        id=f"anomaly_{hashlib.md5(str(anomaly).encode()).hexdigest()[:8]}",
                        title=f"Anomaly Detected: {anomaly.get('type', 'Unknown')}",
                        description=anomaly.get('description', 'Security anomaly detected'),
                        severity=SecurityLevel(anomaly.get('severity', 'low')),
                        category="anomaly",
                        affected_component=anomaly.get('component', 'system'),
                        evidence=anomaly,
                        recommendations=anomaly.get('recommendations', []),
                        cve_references=[],
                        remediation_effort='low',
                        timestamp=datetime.now()
                    )
                    findings.append(finding)
            
            # Calculate threat detection score
            score = max(0, 100 - len(findings) * 15)
            return findings, score
        
        except Exception as e:
            self.logger.error(f"Error in threat detection audit: {e}")
            return [], 0.0
    
    async def _run_compliance_audit(self, scope: AuditScope) -> Tuple[List[SecurityFinding], float, Dict[str, Any]]:
        """Run compliance checking."""
        findings = []
        
        try:
            # Check security best practices
            compliance_result = await self.compliance_checker.check_security_compliance()
            
            for violation in compliance_result.get('violations', []):
                finding = SecurityFinding(
                    id=f"compliance_{violation.get('rule_id', 'unknown')}",
                    title=f"Compliance Violation: {violation.get('title', 'Unknown')}",
                    description=violation.get('description', 'Compliance violation detected'),
                    severity=SecurityLevel(violation.get('severity', 'medium')),
                    category="compliance",
                    affected_component=violation.get('component', 'system'),
                    evidence=violation,
                    recommendations=violation.get('recommendations', []),
                    cve_references=[],
                    remediation_effort=violation.get('remediation_effort', 'medium'),
                    timestamp=datetime.now()
                )
                findings.append(finding)
            
            # Check Home Assistant compliance
            if scope in [AuditScope.STANDARD, AuditScope.COMPREHENSIVE, AuditScope.DEEP]:
                ha_compliance = await self.compliance_checker.check_ha_compliance()
                for violation in ha_compliance.get('violations', []):
                    finding = SecurityFinding(
                        id=f"ha_compliance_{violation.get('rule_id', 'unknown')}",
                        title=f"HA Compliance Issue: {violation.get('title', 'Unknown')}",
                        description=violation.get('description', 'Home Assistant compliance issue'),
                        severity=SecurityLevel(violation.get('severity', 'low')),
                        category="ha_compliance",
                        affected_component=violation.get('component', 'home_assistant'),
                        evidence=violation,
                        recommendations=violation.get('recommendations', []),
                        cve_references=[],
                        remediation_effort=violation.get('remediation_effort', 'low'),
                        timestamp=datetime.now()
                    )
                    findings.append(finding)
            
            # Calculate compliance score
            total_checks = compliance_result.get('total_checks', 1)
            passed_checks = compliance_result.get('passed_checks', 0)
            score = (passed_checks / total_checks) * 100
            
            return findings, score, compliance_result
        
        except Exception as e:
            self.logger.error(f"Error in compliance audit: {e}")
            return [], 0.0, {}
    
    async def _run_monitoring_audit(self, scope: AuditScope) -> Tuple[List[SecurityFinding], float]:
        """Run security monitoring analysis."""
        findings = []
        
        try:
            # Check monitoring coverage
            monitoring_status = await self.security_monitor.get_monitoring_status()
            
            if not monitoring_status.get('enabled', False):
                finding = SecurityFinding(
                    id="monitor_disabled",
                    title="Security Monitoring Disabled",
                    description="Security monitoring is not enabled",
                    severity=SecurityLevel.HIGH,
                    category="monitoring",
                    affected_component="security_monitor",
                    evidence=monitoring_status,
                    recommendations=["Enable security monitoring", "Configure monitoring alerts"],
                    cve_references=[],
                    remediation_effort='low',
                    timestamp=datetime.now()
                )
                findings.append(finding)
            
            # Check alert configuration
            alert_config = monitoring_status.get('alert_config', {})
            if not alert_config.get('enabled', False):
                finding = SecurityFinding(
                    id="alerts_disabled",
                    title="Security Alerts Disabled",
                    description="Security alerting is not configured",
                    severity=SecurityLevel.MEDIUM,
                    category="monitoring",
                    affected_component="security_monitor",
                    evidence=alert_config,
                    recommendations=["Configure security alerts", "Set up notification channels"],
                    cve_references=[],
                    remediation_effort='low',
                    timestamp=datetime.now()
                )
                findings.append(finding)
            
            # Check log retention
            if scope in [AuditScope.COMPREHENSIVE, AuditScope.DEEP]:
                log_config = monitoring_status.get('log_config', {})
                retention_days = log_config.get('retention_days', 0)
                if retention_days < 30:
                    finding = SecurityFinding(
                        id="log_retention_low",
                        title="Insufficient Log Retention",
                        description=f"Log retention is only {retention_days} days (recommended: 30+ days)",
                        severity=SecurityLevel.LOW,
                        category="monitoring",
                        affected_component="logging",
                        evidence=log_config,
                        recommendations=["Increase log retention to at least 30 days"],
                        cve_references=[],
                        remediation_effort='low',
                        timestamp=datetime.now()
                    )
                    findings.append(finding)
            
            # Calculate monitoring score
            score = 100.0
            if not monitoring_status.get('enabled', False):
                score -= 40
            if not alert_config.get('enabled', False):
                score -= 30
            if monitoring_status.get('log_config', {}).get('retention_days', 0) < 30:
                score -= 10
            
            return findings, max(0, score)
        
        except Exception as e:
            self.logger.error(f"Error in monitoring audit: {e}")
            return [], 0.0
    
    def _calculate_overall_score(self, component_scores: Dict[str, float]) -> float:
        """Calculate weighted overall security score."""
        total_score = 0.0
        total_weight = 0.0
        
        for component, score in component_scores.items():
            weight = self.component_weights.get(component, 0.0)
            total_score += score * weight
            total_weight += weight
        
        return total_score / max(total_weight, 1.0)
    
    def _determine_security_level(self, score: float) -> SecurityLevel:
        """Determine security level based on score."""
        if score >= self.security_thresholds[SecurityLevel.LOW]:
            return SecurityLevel.LOW
        elif score >= self.security_thresholds[SecurityLevel.MEDIUM]:
            return SecurityLevel.MEDIUM
        elif score >= self.security_thresholds[SecurityLevel.HIGH]:
            return SecurityLevel.HIGH
        else:
            return SecurityLevel.CRITICAL
    
    def _generate_audit_summary(self, component_scores: Dict[str, float], 
                               findings: List[SecurityFinding]) -> Dict[str, Any]:
        """Generate audit summary."""
        findings_by_severity = {level.value: 0 for level in SecurityLevel}
        findings_by_category = {}
        
        for finding in findings:
            findings_by_severity[finding.severity.value] += 1
            category = finding.category
            findings_by_category[category] = findings_by_category.get(category, 0) + 1
        
        return {
            'total_findings': len(findings),
            'findings_by_severity': findings_by_severity,
            'findings_by_category': findings_by_category,
            'component_scores': component_scores,
            'critical_issues': len([f for f in findings if f.severity == SecurityLevel.CRITICAL]),
            'high_priority_issues': len([f for f in findings if f.severity == SecurityLevel.HIGH]),
            'components_audited': len(component_scores),
            'average_component_score': sum(component_scores.values()) / len(component_scores) if component_scores else 0
        }
    
    def _generate_recommendations(self, findings: List[SecurityFinding], 
                                 component_scores: Dict[str, float]) -> List[str]:
        """Generate overall recommendations."""
        recommendations = []
        
        # Priority recommendations based on critical findings
        critical_findings = [f for f in findings if f.severity == SecurityLevel.CRITICAL]
        if critical_findings:
            recommendations.append("URGENT: Address critical security findings immediately")
            for finding in critical_findings[:3]:  # Top 3 critical
                recommendations.extend(finding.recommendations[:1])  # Top recommendation each
        
        # Component-specific recommendations
        for component, score in component_scores.items():
            if score < 60:
                if component == 'vulnerability_scan':
                    recommendations.append("Update dependencies and apply security patches")
                elif component == 'access_control':
                    recommendations.append("Review and strengthen access control mechanisms")
                elif component == 'threat_detection':
                    recommendations.append("Enhance threat detection and response capabilities")
                elif component == 'compliance':
                    recommendations.append("Address compliance violations and implement security best practices")
                elif component == 'monitoring':
                    recommendations.append("Improve security monitoring and alerting coverage")
        
        # General recommendations
        high_findings = [f for f in findings if f.severity == SecurityLevel.HIGH]
        if high_findings:
            recommendations.append("Address high-severity security issues within 48 hours")
        
        if len(findings) > 10:
            recommendations.append("Consider implementing automated security remediation")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _calculate_next_audit_time(self, security_level: SecurityLevel) -> datetime:
        """Calculate recommended next audit time based on security level."""
        now = datetime.now()
        
        if security_level == SecurityLevel.CRITICAL:
            return now + timedelta(hours=6)  # 6 hours for critical
        elif security_level == SecurityLevel.HIGH:
            return now + timedelta(hours=24)  # 24 hours for high
        elif security_level == SecurityLevel.MEDIUM:
            return now + timedelta(days=7)  # 1 week for medium
        else:
            return now + timedelta(days=30)  # 1 month for low
    
    def _generate_audit_id(self) -> str:
        """Generate unique audit ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(os.urandom(16)).hexdigest()[:8]
        return f"audit_{timestamp}_{random_suffix}"
    
    async def _save_audit_report(self, report: SecurityReport) -> None:
        """Save audit report to storage."""
        try:
            os.makedirs(self.audit_history_path, exist_ok=True)
            
            # Save detailed report
            report_file = os.path.join(self.audit_history_path, f"{report.audit_id}.json")
            report_data = {
                'audit_id': report.audit_id,
                'timestamp': report.timestamp.isoformat(),
                'scope': report.scope.value,
                'duration_seconds': report.duration_seconds,
                'overall_score': report.overall_score,
                'security_level': report.security_level.value,
                'findings': [
                    {
                        'id': f.id,
                        'title': f.title,
                        'description': f.description,
                        'severity': f.severity.value,
                        'category': f.category,
                        'affected_component': f.affected_component,
                        'evidence': f.evidence,
                        'recommendations': f.recommendations,
                        'cve_references': f.cve_references,
                        'remediation_effort': f.remediation_effort,
                        'timestamp': f.timestamp.isoformat()
                    }
                    for f in report.findings
                ],
                'summary': report.summary,
                'recommendations': report.recommendations,
                'compliance_status': report.compliance_status,
                'next_audit_recommended': report.next_audit_recommended.isoformat()
            }
            
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            # Cleanup old reports
            await self._cleanup_old_reports()
            
            self.logger.info(f"Saved audit report: {report_file}")
        
        except Exception as e:
            self.logger.error(f"Error saving audit report: {e}")
    
    async def _cleanup_old_reports(self) -> None:
        """Clean up old audit reports."""
        try:
            if not os.path.exists(self.audit_history_path):
                return
            
            # Get all report files
            files = [f for f in os.listdir(self.audit_history_path) if f.endswith('.json')]
            files.sort(reverse=True)  # Most recent first
            
            # Remove excess files
            if len(files) > self.max_audit_history:
                for old_file in files[self.max_audit_history:]:
                    file_path = os.path.join(self.audit_history_path, old_file)
                    os.remove(file_path)
                    self.logger.debug(f"Removed old audit report: {old_file}")
        
        except Exception as e:
            self.logger.error(f"Error cleaning up old reports: {e}")
    
    async def get_audit_status(self) -> Dict[str, Any]:
        """Get current audit status."""
        return {
            'audit_in_progress': self.audit_in_progress,
            'current_audit_id': self.current_audit_id,
            'last_audit_time': self.last_audit_time.isoformat() if self.last_audit_time else None,
            'auto_audit_enabled': self._auto_audit_task is not None,
            'auto_audit_interval_hours': self.auto_audit_interval_hours,
            'audit_history_path': self.audit_history_path
        }
    
    async def get_latest_report(self) -> Optional[SecurityReport]:
        """Get the latest audit report."""
        try:
            if not os.path.exists(self.audit_history_path):
                return None
            
            files = [f for f in os.listdir(self.audit_history_path) if f.endswith('.json')]
            if not files:
                return None
            
            # Get most recent file
            latest_file = max(files)
            file_path = os.path.join(self.audit_history_path, latest_file)
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Convert back to SecurityReport object
            findings = [
                SecurityFinding(
                    id=f['id'],
                    title=f['title'],
                    description=f['description'],
                    severity=SecurityLevel(f['severity']),
                    category=f['category'],
                    affected_component=f['affected_component'],
                    evidence=f['evidence'],
                    recommendations=f['recommendations'],
                    cve_references=f['cve_references'],
                    remediation_effort=f['remediation_effort'],
                    timestamp=datetime.fromisoformat(f['timestamp'])
                )
                for f in data['findings']
            ]
            
            return SecurityReport(
                audit_id=data['audit_id'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                scope=AuditScope(data['scope']),
                duration_seconds=data['duration_seconds'],
                overall_score=data['overall_score'],
                security_level=SecurityLevel(data['security_level']),
                findings=findings,
                summary=data['summary'],
                recommendations=data['recommendations'],
                compliance_status=data['compliance_status'],
                next_audit_recommended=datetime.fromisoformat(data['next_audit_recommended'])
            )
        
        except Exception as e:
            self.logger.error(f"Error loading latest report: {e}")
            return None


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_security_auditor():
        """Test security auditor functionality."""
        
        # Mock Home Assistant object
        class MockHass:
            def __init__(self):
                self.data = {}
        
        hass = MockHass()
        config = {
            'audit_history_path': '/tmp/test_audits',
            'auto_audit_interval_hours': 1
        }
        
        auditor = SecurityAuditor(hass, config)
        
        # Test quick audit
        print("Running quick security audit...")
        report = await auditor.run_security_audit(scope=AuditScope.QUICK)
        
        print(f"Audit completed:")
        print(f"  ID: {report.audit_id}")
        print(f"  Score: {report.overall_score:.1f}/100")
        print(f"  Level: {report.security_level.value}")
        print(f"  Findings: {len(report.findings)}")
        print(f"  Duration: {report.duration_seconds:.1f}s")
        
        # Test audit status
        status = await auditor.get_audit_status()
        print(f"Audit status: {status}")
        
        print("Security auditor test completed!")
    
    # Run test
    asyncio.run(test_security_auditor())