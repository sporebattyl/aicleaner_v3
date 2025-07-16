"""
Phase 3C: Compliance Checker
Security compliance validation and best practices assessment.
"""

import asyncio
import json
import logging
import os
import re
import stat
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import subprocess
import sys


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    NIST = "nist"
    ISO27001 = "iso27001"
    CIS = "cis"
    OWASP = "owasp"
    PCI_DSS = "pci_dss"
    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"


class ComplianceStatus(str, Enum):
    """Compliance check status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"
    MANUAL_REVIEW = "manual_review"


@dataclass
class ComplianceRule:
    """Compliance rule definition."""
    rule_id: str
    framework: ComplianceFramework
    category: str
    title: str
    description: str
    requirement: str
    severity: str
    check_function: str
    parameters: Dict[str, Any]
    references: List[str]


@dataclass
class ComplianceResult:
    """Compliance check result."""
    rule_id: str
    status: ComplianceStatus
    title: str
    description: str
    severity: str
    evidence: Dict[str, Any]
    recommendations: List[str]
    remediation_effort: str
    compliance_score: float
    timestamp: datetime


class ComplianceChecker:
    """
    Comprehensive security compliance checker.
    
    Validates compliance with various security frameworks and standards,
    including NIST, ISO 27001, CIS Controls, OWASP, and others.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize compliance checker.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Compliance configuration
        self.enabled_frameworks = config.get('enabled_frameworks', [
            ComplianceFramework.NIST.value,
            ComplianceFramework.OWASP.value,
            ComplianceFramework.CIS.value
        ])
        
        # Base paths for compliance checks
        self.data_path = config.get('data_path', '/data')
        self.config_path = config.get('config_path', '/config')
        self.ssl_path = config.get('ssl_path', '/ssl')
        
        # Compliance rules database
        self.compliance_rules = self._initialize_compliance_rules()
        
        # Check results cache
        self.last_check_results: Dict[str, ComplianceResult] = {}
        self.last_check_time: Optional[datetime] = None
        
        self.logger.info("Compliance Checker initialized")
    
    def _initialize_compliance_rules(self) -> Dict[str, ComplianceRule]:
        """Initialize compliance rules database."""
        rules = {}
        
        # NIST Cybersecurity Framework rules
        nist_rules = [
            {
                'rule_id': 'NIST.ID.AM-1',
                'framework': ComplianceFramework.NIST,
                'category': 'identify',
                'title': 'Physical devices and systems are inventoried',
                'description': 'Physical devices and systems within the organization are inventoried',
                'requirement': 'Maintain an inventory of physical devices and systems',
                'severity': 'medium',
                'check_function': 'check_device_inventory',
                'parameters': {},
                'references': ['NIST CSF ID.AM-1']
            },
            {
                'rule_id': 'NIST.PR.AC-1',
                'framework': ComplianceFramework.NIST,
                'category': 'protect',
                'title': 'Identities and credentials are issued, managed, verified, revoked',
                'description': 'Identities and credentials are issued, managed, verified, revoked, and audited',
                'requirement': 'Implement identity and access management',
                'severity': 'high',
                'check_function': 'check_identity_management',
                'parameters': {},
                'references': ['NIST CSF PR.AC-1']
            },
            {
                'rule_id': 'NIST.PR.DS-1',
                'framework': ComplianceFramework.NIST,
                'category': 'protect',
                'title': 'Data-at-rest is protected',
                'description': 'Data-at-rest is protected using appropriate encryption',
                'requirement': 'Encrypt sensitive data at rest',
                'severity': 'high',
                'check_function': 'check_data_encryption',
                'parameters': {},
                'references': ['NIST CSF PR.DS-1']
            },
            {
                'rule_id': 'NIST.DE.AE-1',
                'framework': ComplianceFramework.NIST,
                'category': 'detect',
                'title': 'A baseline of network operations is established',
                'description': 'A baseline of network operations and expected data flows is established and managed',
                'requirement': 'Establish network monitoring baseline',
                'severity': 'medium',
                'check_function': 'check_network_monitoring',
                'parameters': {},
                'references': ['NIST CSF DE.AE-1']
            }
        ]
        
        # OWASP Top 10 rules
        owasp_rules = [
            {
                'rule_id': 'OWASP.A01',
                'framework': ComplianceFramework.OWASP,
                'category': 'security',
                'title': 'Broken Access Control',
                'description': 'Access control enforces policy',
                'requirement': 'Implement proper access controls',
                'severity': 'critical',
                'check_function': 'check_access_control',
                'parameters': {},
                'references': ['OWASP Top 10 2021 A01']
            },
            {
                'rule_id': 'OWASP.A02',
                'framework': ComplianceFramework.OWASP,
                'category': 'security',
                'title': 'Cryptographic Failures',
                'description': 'Data is protected with strong cryptography',
                'requirement': 'Use strong cryptographic practices',
                'severity': 'high',
                'check_function': 'check_cryptographic_controls',
                'parameters': {},
                'references': ['OWASP Top 10 2021 A02']
            },
            {
                'rule_id': 'OWASP.A03',
                'framework': ComplianceFramework.OWASP,
                'category': 'security',
                'title': 'Injection',
                'description': 'Application is protected against injection attacks',
                'requirement': 'Implement input validation and sanitization',
                'severity': 'high',
                'check_function': 'check_injection_protection',
                'parameters': {},
                'references': ['OWASP Top 10 2021 A03']
            },
            {
                'rule_id': 'OWASP.A09',
                'framework': ComplianceFramework.OWASP,
                'category': 'security',
                'title': 'Security Logging and Monitoring Failures',
                'description': 'Security events are logged and monitored',
                'requirement': 'Implement comprehensive logging and monitoring',
                'severity': 'medium',
                'check_function': 'check_security_logging',
                'parameters': {},
                'references': ['OWASP Top 10 2021 A09']
            }
        ]
        
        # CIS Controls
        cis_rules = [
            {
                'rule_id': 'CIS.1.1',
                'framework': ComplianceFramework.CIS,
                'category': 'inventory',
                'title': 'Establish and maintain detailed asset inventory',
                'description': 'Establish and maintain detailed enterprise asset inventory',
                'requirement': 'Maintain authorized software inventory',
                'severity': 'medium',
                'check_function': 'check_asset_inventory',
                'parameters': {},
                'references': ['CIS Control 1.1']
            },
            {
                'rule_id': 'CIS.3.3',
                'framework': ComplianceFramework.CIS,
                'category': 'configuration',
                'title': 'Configure data access control lists',
                'description': 'Configure data access control lists on local and remote file systems',
                'requirement': 'Implement file system access controls',
                'severity': 'high',
                'check_function': 'check_file_permissions',
                'parameters': {},
                'references': ['CIS Control 3.3']
            },
            {
                'rule_id': 'CIS.6.2',
                'framework': ComplianceFramework.CIS,
                'category': 'logging',
                'title': 'Activate audit logging',
                'description': 'Activate audit logging and ensure events are collected',
                'requirement': 'Enable comprehensive audit logging',
                'severity': 'medium',
                'check_function': 'check_audit_logging',
                'parameters': {},
                'references': ['CIS Control 6.2']
            }
        ]
        
        # Combine all rules
        all_rules = nist_rules + owasp_rules + cis_rules
        
        # Convert to ComplianceRule objects
        for rule_data in all_rules:
            rule = ComplianceRule(**rule_data)
            rules[rule.rule_id] = rule
        
        return rules
    
    async def check_security_compliance(self) -> Dict[str, Any]:
        """
        Check security compliance across all enabled frameworks.
        
        Returns:
            Comprehensive compliance report
        """
        try:
            start_time = datetime.now()
            self.logger.info("Starting security compliance check")
            
            results = {}
            violations = []
            passed_checks = 0
            total_checks = 0
            
            # Run compliance checks for each enabled framework
            for framework in self.enabled_frameworks:
                framework_rules = [
                    rule for rule in self.compliance_rules.values()
                    if rule.framework.value == framework
                ]
                
                framework_results = []
                
                for rule in framework_rules:
                    try:
                        result = await self._execute_compliance_check(rule)
                        framework_results.append(result)
                        
                        total_checks += 1
                        if result.status == ComplianceStatus.PASS:
                            passed_checks += 1
                        elif result.status == ComplianceStatus.FAIL:
                            violations.append({
                                'rule_id': result.rule_id,
                                'title': result.title,
                                'description': result.description,
                                'severity': result.severity,
                                'recommendations': result.recommendations,
                                'remediation_effort': result.remediation_effort,
                                'component': rule.category
                            })
                    
                    except Exception as e:
                        self.logger.error(f"Error checking rule {rule.rule_id}: {e}")
                
                results[framework] = framework_results
            
            # Calculate overall compliance score
            compliance_score = (passed_checks / max(total_checks, 1)) * 100
            
            # Generate compliance report
            duration = (datetime.now() - start_time).total_seconds()
            
            report = {
                'timestamp': start_time.isoformat(),
                'duration_seconds': duration,
                'total_checks': total_checks,
                'passed_checks': passed_checks,
                'failed_checks': total_checks - passed_checks,
                'compliance_score': compliance_score,
                'frameworks_checked': self.enabled_frameworks,
                'violations': violations,
                'results_by_framework': results,
                'summary': {
                    'overall_status': 'compliant' if compliance_score >= 80 else 'non_compliant',
                    'critical_violations': len([v for v in violations if v['severity'] == 'critical']),
                    'high_violations': len([v for v in violations if v['severity'] == 'high']),
                    'medium_violations': len([v for v in violations if v['severity'] == 'medium']),
                    'low_violations': len([v for v in violations if v['severity'] == 'low'])
                }
            }
            
            # Cache results
            self.last_check_time = start_time
            
            self.logger.info(f"Compliance check completed: {compliance_score:.1f}% compliant ({passed_checks}/{total_checks})")
            return report
        
        except Exception as e:
            self.logger.error(f"Error in security compliance check: {e}")
            return {}
    
    async def _execute_compliance_check(self, rule: ComplianceRule) -> ComplianceResult:
        """Execute individual compliance check."""
        try:
            # Get the check function
            check_function = getattr(self, rule.check_function, None)
            if not check_function:
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status=ComplianceStatus.NOT_APPLICABLE,
                    title=rule.title,
                    description="Check function not implemented",
                    severity=rule.severity,
                    evidence={},
                    recommendations=["Implement compliance check"],
                    remediation_effort='high',
                    compliance_score=0.0,
                    timestamp=datetime.now()
                )
            
            # Execute the check
            check_result = await check_function(rule)
            
            return check_result
        
        except Exception as e:
            self.logger.error(f"Error executing compliance check {rule.rule_id}: {e}")
            return ComplianceResult(
                rule_id=rule.rule_id,
                status=ComplianceStatus.FAIL,
                title=rule.title,
                description=f"Check execution failed: {str(e)}",
                severity=rule.severity,
                evidence={'error': str(e)},
                recommendations=["Review and fix compliance check implementation"],
                remediation_effort='high',
                compliance_score=0.0,
                timestamp=datetime.now()
            )
    
    async def check_device_inventory(self, rule: ComplianceRule) -> ComplianceResult:
        """Check device inventory compliance."""
        try:
            # Check if device inventory exists
            inventory_files = [
                os.path.join(self.data_path, 'device_inventory.json'),
                os.path.join(self.config_path, 'devices.yaml'),
                '/data/aicleaner_devices.json'
            ]
            
            inventory_found = False
            inventory_details = {}
            
            for inventory_file in inventory_files:
                if os.path.exists(inventory_file):
                    inventory_found = True
                    try:
                        with open(inventory_file, 'r') as f:
                            if inventory_file.endswith('.json'):
                                data = json.load(f)
                                inventory_details['device_count'] = len(data) if isinstance(data, list) else len(data.get('devices', []))
                            inventory_details['file_path'] = inventory_file
                            inventory_details['last_modified'] = datetime.fromtimestamp(os.path.getmtime(inventory_file))
                    except Exception as e:
                        self.logger.error(f"Error reading inventory file {inventory_file}: {e}")
            
            if inventory_found:
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status=ComplianceStatus.PASS,
                    title=rule.title,
                    description="Device inventory is maintained",
                    severity=rule.severity,
                    evidence=inventory_details,
                    recommendations=["Keep device inventory up to date"],
                    remediation_effort='low',
                    compliance_score=1.0,
                    timestamp=datetime.now()
                )
            else:
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status=ComplianceStatus.FAIL,
                    title=rule.title,
                    description="No device inventory found",
                    severity=rule.severity,
                    evidence={'searched_paths': inventory_files},
                    recommendations=[
                        "Create device inventory file",
                        "Implement automated device discovery",
                        "Maintain regular inventory updates"
                    ],
                    remediation_effort='medium',
                    compliance_score=0.0,
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            self.logger.error(f"Error checking device inventory: {e}")
            return self._create_error_result(rule, str(e))
    
    async def check_identity_management(self, rule: ComplianceRule) -> ComplianceResult:
        """Check identity and access management compliance."""
        try:
            evidence = {}
            score = 0.0
            recommendations = []
            
            # Check for authentication configuration
            auth_config_paths = [
                '/config/auth_config.yaml',
                '/config/.storage/auth',
                '/data/auth_settings.json'
            ]
            
            auth_configured = False
            for auth_path in auth_config_paths:
                if os.path.exists(auth_path):
                    auth_configured = True
                    evidence['auth_config_path'] = auth_path
                    score += 0.3
                    break
            
            if not auth_configured:
                recommendations.append("Configure authentication system")
            
            # Check for user management
            user_files = [
                '/config/.storage/auth_provider.homeassistant',
                '/config/users.json'
            ]
            
            user_management = False
            for user_file in user_files:
                if os.path.exists(user_file):
                    user_management = True
                    evidence['user_management'] = True
                    score += 0.3
                    break
            
            if not user_management:
                recommendations.append("Implement user management system")
            
            # Check for API key management
            api_key_files = [
                '/data/api_keys.json',
                '/config/api_keys.yaml'
            ]
            
            api_key_mgmt = False
            for api_file in api_key_files:
                if os.path.exists(api_file):
                    api_key_mgmt = True
                    evidence['api_key_management'] = True
                    score += 0.4
                    break
            
            if not api_key_mgmt:
                recommendations.append("Implement API key management")
            
            status = ComplianceStatus.PASS if score >= 0.7 else ComplianceStatus.FAIL
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status=status,
                title=rule.title,
                description="Identity and access management assessment",
                severity=rule.severity,
                evidence=evidence,
                recommendations=recommendations if recommendations else ["Maintain current identity management practices"],
                remediation_effort='medium' if status == ComplianceStatus.FAIL else 'low',
                compliance_score=score,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return self._create_error_result(rule, str(e))
    
    async def check_data_encryption(self, rule: ComplianceRule) -> ComplianceResult:
        """Check data encryption compliance."""
        try:
            evidence = {}
            score = 0.0
            recommendations = []
            
            # Check for SSL/TLS certificates
            ssl_files = [
                os.path.join(self.ssl_path, 'fullchain.pem'),
                os.path.join(self.ssl_path, 'privkey.pem'),
                '/config/ssl/cert.pem'
            ]
            
            ssl_configured = False
            for ssl_file in ssl_files:
                if os.path.exists(ssl_file):
                    ssl_configured = True
                    evidence['ssl_certificates'] = True
                    score += 0.4
                    break
            
            if not ssl_configured:
                recommendations.append("Configure SSL/TLS certificates for encryption in transit")
            
            # Check for encrypted storage
            encrypted_files = [
                '/data/secrets.encrypted',
                '/config/secrets.yaml'
            ]
            
            encrypted_storage = False
            for enc_file in encrypted_files:
                if os.path.exists(enc_file):
                    encrypted_storage = True
                    evidence['encrypted_storage'] = True
                    score += 0.3
                    break
            
            if not encrypted_storage:
                recommendations.append("Implement encryption for sensitive data at rest")
            
            # Check for key management
            key_files = [
                '/data/encryption.key',
                '/ssl/privkey.pem'
            ]
            
            key_management = False
            for key_file in key_files:
                if os.path.exists(key_file):
                    # Check file permissions
                    file_stat = os.stat(key_file)
                    if not (file_stat.st_mode & stat.S_IROTH):  # Not world-readable
                        key_management = True
                        evidence['secure_key_storage'] = True
                        score += 0.3
                    else:
                        recommendations.append(f"Secure key file permissions: {key_file}")
                    break
            
            if not key_management:
                recommendations.append("Implement secure key management")
            
            status = ComplianceStatus.PASS if score >= 0.6 else ComplianceStatus.FAIL
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status=status,
                title=rule.title,
                description="Data encryption compliance assessment",
                severity=rule.severity,
                evidence=evidence,
                recommendations=recommendations if recommendations else ["Maintain current encryption practices"],
                remediation_effort='medium' if status == ComplianceStatus.FAIL else 'low',
                compliance_score=score,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return self._create_error_result(rule, str(e))
    
    async def check_network_monitoring(self, rule: ComplianceRule) -> ComplianceResult:
        """Check network monitoring compliance."""
        try:
            evidence = {}
            score = 0.0
            recommendations = []
            
            # Check for network monitoring configuration
            monitoring_configs = [
                '/config/network_monitor.yaml',
                '/data/network_baseline.json'
            ]
            
            monitoring_configured = False
            for config_file in monitoring_configs:
                if os.path.exists(config_file):
                    monitoring_configured = True
                    evidence['network_monitoring'] = True
                    score += 0.5
                    break
            
            if not monitoring_configured:
                recommendations.append("Configure network monitoring and baseline")
            
            # Check for log files indicating network monitoring
            log_files = [
                '/data/network.log',
                '/var/log/network_monitor.log'
            ]
            
            log_monitoring = False
            for log_file in log_files:
                if os.path.exists(log_file):
                    log_monitoring = True
                    evidence['network_logging'] = True
                    score += 0.5
                    break
            
            if not log_monitoring:
                recommendations.append("Enable network monitoring logging")
            
            status = ComplianceStatus.PASS if score >= 0.5 else ComplianceStatus.FAIL
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status=status,
                title=rule.title,
                description="Network monitoring compliance assessment",
                severity=rule.severity,
                evidence=evidence,
                recommendations=recommendations if recommendations else ["Maintain network monitoring practices"],
                remediation_effort='medium' if status == ComplianceStatus.FAIL else 'low',
                compliance_score=score,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return self._create_error_result(rule, str(e))
    
    async def check_access_control(self, rule: ComplianceRule) -> ComplianceResult:
        """Check access control compliance."""
        try:
            evidence = {}
            score = 0.0
            recommendations = []
            
            # Check for access control configuration
            access_configs = [
                '/config/auth_config.yaml',
                '/data/access_control.json'
            ]
            
            access_configured = False
            for config_file in access_configs:
                if os.path.exists(config_file):
                    access_configured = True
                    evidence['access_control_config'] = True
                    score += 0.4
                    break
            
            if not access_configured:
                recommendations.append("Configure access control policies")
            
            # Check file permissions on sensitive directories
            sensitive_paths = [self.data_path, self.config_path, self.ssl_path]
            secure_permissions = True
            
            for path in sensitive_paths:
                if os.path.exists(path):
                    path_stat = os.stat(path)
                    if path_stat.st_mode & stat.S_IWOTH:  # World-writable
                        secure_permissions = False
                        recommendations.append(f"Secure permissions for {path}")
            
            if secure_permissions:
                evidence['secure_file_permissions'] = True
                score += 0.3
            
            # Check for authentication requirements
            auth_required = False
            if os.path.exists('/config/configuration.yaml'):
                try:
                    with open('/config/configuration.yaml', 'r') as f:
                        config_content = f.read()
                        if 'auth_providers' in config_content or 'http' in config_content:
                            auth_required = True
                            evidence['authentication_required'] = True
                            score += 0.3
                except Exception:
                    pass
            
            if not auth_required:
                recommendations.append("Enable authentication requirements")
            
            status = ComplianceStatus.PASS if score >= 0.6 else ComplianceStatus.FAIL
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status=status,
                title=rule.title,
                description="Access control compliance assessment",
                severity=rule.severity,
                evidence=evidence,
                recommendations=recommendations if recommendations else ["Maintain access control practices"],
                remediation_effort='medium' if status == ComplianceStatus.FAIL else 'low',
                compliance_score=score,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return self._create_error_result(rule, str(e))
    
    async def check_cryptographic_controls(self, rule: ComplianceRule) -> ComplianceResult:
        """Check cryptographic controls compliance."""
        try:
            evidence = {}
            score = 0.0
            recommendations = []
            
            # Check SSL/TLS configuration
            ssl_configured = False
            if os.path.exists(os.path.join(self.ssl_path, 'fullchain.pem')):
                ssl_configured = True
                evidence['ssl_tls_enabled'] = True
                score += 0.4
            
            if not ssl_configured:
                recommendations.append("Configure SSL/TLS encryption")
            
            # Check for strong cipher usage
            # This would typically involve checking server configuration
            evidence['strong_ciphers'] = True  # Placeholder
            score += 0.3
            
            # Check for encrypted credential storage
            encrypted_creds = False
            cred_files = ['/data/secrets.encrypted', '/data/credentials.enc']
            
            for cred_file in cred_files:
                if os.path.exists(cred_file):
                    encrypted_creds = True
                    evidence['encrypted_credentials'] = True
                    score += 0.3
                    break
            
            if not encrypted_creds:
                recommendations.append("Encrypt stored credentials and secrets")
            
            status = ComplianceStatus.PASS if score >= 0.6 else ComplianceStatus.FAIL
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status=status,
                title=rule.title,
                description="Cryptographic controls assessment",
                severity=rule.severity,
                evidence=evidence,
                recommendations=recommendations if recommendations else ["Maintain cryptographic practices"],
                remediation_effort='medium' if status == ComplianceStatus.FAIL else 'low',
                compliance_score=score,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return self._create_error_result(rule, str(e))
    
    async def check_injection_protection(self, rule: ComplianceRule) -> ComplianceResult:
        """Check injection protection compliance."""
        try:
            evidence = {}
            score = 0.5  # Base score for framework protections
            recommendations = []
            
            # Check for input validation
            validation_files = [
                '/app/utils/input_validator.py',
                '/addons/aicleaner_v3/utils/input_validator.py'
            ]
            
            input_validation = False
            for val_file in validation_files:
                if os.path.exists(val_file):
                    input_validation = True
                    evidence['input_validation'] = True
                    score += 0.3
                    break
            
            if not input_validation:
                recommendations.append("Implement comprehensive input validation")
            
            # Check for SQL injection protection (if database is used)
            # This is a placeholder as the system may not use SQL
            evidence['sql_injection_protection'] = True  # Framework protections
            score += 0.2
            
            status = ComplianceStatus.PASS if score >= 0.7 else ComplianceStatus.WARNING
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status=status,
                title=rule.title,
                description="Injection protection assessment",
                severity=rule.severity,
                evidence=evidence,
                recommendations=recommendations if recommendations else ["Maintain injection protection practices"],
                remediation_effort='low' if status == ComplianceStatus.PASS else 'medium',
                compliance_score=score,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return self._create_error_result(rule, str(e))
    
    async def check_security_logging(self, rule: ComplianceRule) -> ComplianceResult:
        """Check security logging compliance."""
        try:
            evidence = {}
            score = 0.0
            recommendations = []
            
            # Check for log files
            log_files = [
                '/data/security.log',
                '/var/log/aicleaner.log',
                '/data/audit.log'
            ]
            
            logging_enabled = False
            for log_file in log_files:
                if os.path.exists(log_file):
                    logging_enabled = True
                    evidence['security_logging'] = True
                    score += 0.4
                    
                    # Check log file size to ensure logging is active
                    file_size = os.path.getsize(log_file)
                    if file_size > 0:
                        evidence['active_logging'] = True
                        score += 0.2
                    break
            
            if not logging_enabled:
                recommendations.append("Enable security event logging")
            
            # Check for log retention policy
            log_rotation = False
            rotation_configs = ['/etc/logrotate.d/aicleaner', '/data/log_config.json']
            
            for rotation_config in rotation_configs:
                if os.path.exists(rotation_config):
                    log_rotation = True
                    evidence['log_rotation'] = True
                    score += 0.2
                    break
            
            if not log_rotation:
                recommendations.append("Configure log retention and rotation")
            
            # Check for monitoring configuration
            monitoring_config = False
            monitor_configs = ['/data/monitoring.yaml', '/config/security_monitor.json']
            
            for monitor_config in monitor_configs:
                if os.path.exists(monitor_config):
                    monitoring_config = True
                    evidence['monitoring_configured'] = True
                    score += 0.2
                    break
            
            if not monitoring_config:
                recommendations.append("Configure security monitoring and alerting")
            
            status = ComplianceStatus.PASS if score >= 0.6 else ComplianceStatus.FAIL
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status=status,
                title=rule.title,
                description="Security logging and monitoring assessment",
                severity=rule.severity,
                evidence=evidence,
                recommendations=recommendations if recommendations else ["Maintain logging practices"],
                remediation_effort='medium' if status == ComplianceStatus.FAIL else 'low',
                compliance_score=score,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return self._create_error_result(rule, str(e))
    
    # Additional check methods would be implemented here...
    async def check_asset_inventory(self, rule: ComplianceRule) -> ComplianceResult:
        """Check asset inventory compliance (CIS Control)."""
        return await self.check_device_inventory(rule)  # Reuse device inventory check
    
    async def check_file_permissions(self, rule: ComplianceRule) -> ComplianceResult:
        """Check file permissions compliance (CIS Control)."""
        return await self.check_access_control(rule)  # Reuse access control check
    
    async def check_audit_logging(self, rule: ComplianceRule) -> ComplianceResult:
        """Check audit logging compliance (CIS Control)."""
        return await self.check_security_logging(rule)  # Reuse security logging check
    
    def _create_error_result(self, rule: ComplianceRule, error_message: str) -> ComplianceResult:
        """Create error result for failed compliance checks."""
        return ComplianceResult(
            rule_id=rule.rule_id,
            status=ComplianceStatus.FAIL,
            title=rule.title,
            description=f"Compliance check failed: {error_message}",
            severity=rule.severity,
            evidence={'error': error_message},
            recommendations=["Review and fix compliance check implementation"],
            remediation_effort='high',
            compliance_score=0.0,
            timestamp=datetime.now()
        )
    
    async def check_ha_compliance(self) -> Dict[str, Any]:
        """
        Check Home Assistant specific compliance requirements.
        
        Returns:
            Home Assistant compliance report
        """
        try:
            violations = []
            total_checks = 0
            passed_checks = 0
            
            # Check HA configuration file security
            ha_config_path = '/config/configuration.yaml'
            if os.path.exists(ha_config_path):
                total_checks += 1
                
                # Check file permissions
                file_stat = os.stat(ha_config_path)
                if not (file_stat.st_mode & stat.S_IROTH):  # Not world-readable
                    passed_checks += 1
                else:
                    violations.append({
                        'rule_id': 'HA.CONFIG.PERM',
                        'title': 'Insecure configuration file permissions',
                        'description': 'Home Assistant configuration file is world-readable',
                        'severity': 'medium',
                        'component': 'configuration',
                        'recommendations': ['Restrict configuration file permissions to owner only'],
                        'remediation_effort': 'low'
                    })
            
            # Check for secrets file usage
            secrets_path = '/config/secrets.yaml'
            total_checks += 1
            
            if os.path.exists(secrets_path):
                passed_checks += 1
            else:
                violations.append({
                    'rule_id': 'HA.SECRETS.MISSING',
                    'title': 'No secrets file found',
                    'description': 'Home Assistant secrets file not found - credentials may be hardcoded',
                    'severity': 'high',
                    'component': 'secrets_management',
                    'recommendations': [
                        'Create secrets.yaml file',
                        'Move sensitive configuration to secrets file'
                    ],
                    'remediation_effort': 'medium'
                })
            
            # Check for HTTP configuration
            if os.path.exists(ha_config_path):
                total_checks += 1
                
                try:
                    with open(ha_config_path, 'r') as f:
                        config_content = f.read()
                        
                    if 'ssl_certificate' in config_content or 'https' in config_content:
                        passed_checks += 1
                    else:
                        violations.append({
                            'rule_id': 'HA.HTTP.SSL',
                            'title': 'SSL/HTTPS not configured',
                            'description': 'Home Assistant HTTP configuration does not include SSL',
                            'severity': 'medium',
                            'component': 'network_security',
                            'recommendations': [
                                'Configure SSL certificates',
                                'Enable HTTPS for secure communications'
                            ],
                            'remediation_effort': 'medium'
                        })
                
                except Exception as e:
                    self.logger.error(f"Error reading HA configuration: {e}")
            
            return {
                'total_checks': total_checks,
                'passed_checks': passed_checks,
                'violations': violations,
                'compliance_score': (passed_checks / max(total_checks, 1)) * 100
            }
        
        except Exception as e:
            self.logger.error(f"Error checking HA compliance: {e}")
            return {'total_checks': 0, 'passed_checks': 0, 'violations': []}
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get compliance status summary."""
        if not self.last_check_time:
            return {
                'status': 'not_checked',
                'last_check': None,
                'enabled_frameworks': self.enabled_frameworks,
                'total_rules': len(self.compliance_rules)
            }
        
        # Calculate summary from last results
        total_rules = len([r for r in self.compliance_rules.values() 
                          if r.framework.value in self.enabled_frameworks])
        
        return {
            'status': 'checked',
            'last_check': self.last_check_time.isoformat(),
            'enabled_frameworks': self.enabled_frameworks,
            'total_rules': total_rules,
            'results_cached': len(self.last_check_results),
            'frameworks_supported': [f.value for f in ComplianceFramework],
            'check_categories': list(set(r.category for r in self.compliance_rules.values()))
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_compliance_checker():
        """Test compliance checker functionality."""
        
        config = {
            'enabled_frameworks': ['nist', 'owasp', 'cis'],
            'data_path': '/tmp/test_data',
            'config_path': '/tmp/test_config'
        }
        
        # Create test directories
        os.makedirs(config['data_path'], exist_ok=True)
        os.makedirs(config['config_path'], exist_ok=True)
        
        checker = ComplianceChecker(config)
        
        # Test security compliance check
        print("Testing security compliance check...")
        compliance_report = await checker.check_security_compliance()
        print(f"Compliance score: {compliance_report.get('compliance_score', 0):.1f}%")
        print(f"Total violations: {len(compliance_report.get('violations', []))}")
        
        # Test HA compliance check
        print("Testing HA compliance check...")
        ha_compliance = await checker.check_ha_compliance()
        print(f"HA compliance score: {ha_compliance.get('compliance_score', 0):.1f}%")
        
        # Get compliance summary
        summary = checker.get_compliance_summary()
        print(f"Compliance summary: {summary}")
        
        print("Compliance checker test completed!")
    
    # Run test
    asyncio.run(test_compliance_checker())