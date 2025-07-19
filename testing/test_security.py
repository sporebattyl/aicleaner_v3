"""
Security Testing Module for AICleaner v3
Tests for security vulnerabilities and best practices
"""

import os
import re
import stat
import json
import yaml
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set
import hashlib
import sys

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from addons.aicleaner_v3.core.simple_logging import get_simple_logger

logger = get_simple_logger("test_security")


class SecurityTester:
    """Security vulnerability scanner and tester"""
    
    # Patterns that might indicate hardcoded secrets
    SECRET_PATTERNS = {
        'api_key': r'api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})',
        'password': r'password["\']?\s*[:=]\s*["\']?([^"\'\s]{8,})',
        'secret': r'secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})',
        'token': r'token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})',
        'key': r'["\']key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})',
        'auth': r'auth["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})',
    }
    
    # Common secret indicators
    SECRET_KEYWORDS = [
        'password', 'passwd', 'pwd', 'secret', 'key', 'token', 'auth',
        'credential', 'api_key', 'apikey', 'private_key', 'access_token',
        'session_key', 'auth_token', 'bearer', 'jwt'
    ]
    
    # File extensions to scan
    SCAN_EXTENSIONS = {'.py', '.yaml', '.yml', '.json', '.txt', '.md', '.sh', '.env'}
    
    # Directories to skip
    SKIP_DIRECTORIES = {
        '.git', '.venv', 'venv', '__pycache__', '.pytest_cache', 'node_modules',
        'testing', '.tox', 'build', 'dist', '.mypy_cache'
    }
    
    # Files that should have restricted permissions
    SENSITIVE_FILES = {
        'config.yaml', 'secrets.yaml', '.env', 'private_key.pem',
        'ssl_certificate.pem', 'ssl_key.pem', 'database.db'
    }
    
    def __init__(self, scan_path: str = "."):
        self.scan_path = Path(scan_path)
        self.issues = []
        self.files_scanned = 0
        self.secrets_found = 0
    
    def scan_for_hardcoded_secrets(self) -> List[Dict[str, Any]]:
        """Scan for hardcoded secrets in source files"""
        logger.info("Scanning for hardcoded secrets...")
        
        secret_issues = []
        
        for file_path in self._get_files_to_scan():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Check for secret patterns
                for secret_type, pattern in self.SECRET_PATTERNS.items():
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Get line number
                        line_num = content[:match.start()].count('\n') + 1
                        
                        # Check if it's likely a real secret (not a comment or documentation)
                        line_content = content.split('\n')[line_num - 1] if line_num <= len(content.split('\n')) else ""
                        
                        if not self._is_false_positive(line_content, match.group(1)):
                            secret_issues.append({
                                "check": "Hardcoded Secret",
                                "severity": "High",
                                "file": str(file_path),
                                "line": line_num,
                                "secret_type": secret_type,
                                "details": f"Potential {secret_type} found: {match.group(1)[:10]}..."
                            })
                            self.secrets_found += 1
                
                # Check for secret keywords in variable names
                for line_num, line in enumerate(content.split('\n'), 1):
                    for keyword in self.SECRET_KEYWORDS:
                        if keyword in line.lower() and '=' in line:
                            # Extract the value after the equals sign
                            value_match = re.search(r'=\s*["\']?([^"\'\s\n]+)', line)
                            if value_match and len(value_match.group(1)) > 8:
                                if not self._is_false_positive(line, value_match.group(1)):
                                    secret_issues.append({
                                        "check": "Potential Secret Variable",
                                        "severity": "Medium",
                                        "file": str(file_path),
                                        "line": line_num,
                                        "secret_type": keyword,
                                        "details": f"Variable containing '{keyword}' with value: {value_match.group(1)[:10]}..."
                                    })
                
                self.files_scanned += 1
                
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        logger.info(f"Secret scan completed. Scanned {self.files_scanned} files, found {len(secret_issues)} potential issues")
        return secret_issues
    
    def _is_false_positive(self, line: str, value: str) -> bool:
        """Check if a potential secret is likely a false positive"""
        # Skip comments
        if line.strip().startswith('#') or line.strip().startswith('//'):
            return True
        
        # Skip common false positives
        false_positives = {
            'your_api_key_here', 'example_key', 'sample_token', 'placeholder',
            'dummy_secret', 'test_key', 'fake_token', 'insert_key_here',
            'your_password', 'change_me', 'replace_this', 'todo'
        }
        
        if value.lower() in false_positives:
            return True
        
        # Skip very short values
        if len(value) < 8:
            return True
        
        # Skip environment variable references
        if value.startswith('$') or value.startswith('${') or value.startswith('%%'):
            return True
        
        # Skip obvious documentation examples
        if 'example' in value.lower() or 'sample' in value.lower() or 'demo' in value.lower():
            return True
        
        return False
    
    def check_file_permissions(self) -> List[Dict[str, Any]]:
        """Check file permissions for sensitive files"""
        logger.info("Checking file permissions...")
        
        permission_issues = []
        
        for file_path in self._get_all_files():
            try:
                stat_info = file_path.stat()
                permissions = stat.S_IMODE(stat_info.st_mode)
                
                # Check if file is sensitive
                if file_path.name in self.SENSITIVE_FILES or file_path.suffix in {'.key', '.pem', '.p12'}:
                    # Check for world-readable permissions
                    if permissions & stat.S_IROTH:
                        permission_issues.append({
                            "check": "Insecure File Permissions",
                            "severity": "High",
                            "file": str(file_path),
                            "details": f"Sensitive file is world-readable ({oct(permissions)})"
                        })
                    
                    # Check for group-readable permissions
                    elif permissions & stat.S_IRGRP:
                        permission_issues.append({
                            "check": "Insecure File Permissions",
                            "severity": "Medium",
                            "file": str(file_path),
                            "details": f"Sensitive file is group-readable ({oct(permissions)})"
                        })
                
                # Check for world-writable files
                if permissions & stat.S_IWOTH:
                    permission_issues.append({
                        "check": "World-Writable File",
                        "severity": "High",
                        "file": str(file_path),
                        "details": f"File is world-writable ({oct(permissions)})"
                    })
                
            except Exception as e:
                logger.warning(f"Could not check permissions for {file_path}: {e}")
        
        logger.info(f"Permission check completed. Found {len(permission_issues)} issues")
        return permission_issues
    
    def check_input_validation(self) -> List[Dict[str, Any]]:
        """Check for potential input validation issues"""
        logger.info("Checking for input validation issues...")
        
        validation_issues = []
        
        # Patterns that might indicate unsafe input handling
        unsafe_patterns = {
            'sql_injection': r'(execute|query|cursor)\s*\(\s*["\']?[^"\']*%s',
            'command_injection': r'(os\.system|subprocess|exec|eval)\s*\(\s*[^)]*\+',
            'path_traversal': r'open\s*\(\s*[^)]*\+\s*[^)]*\)',
            'unsafe_yaml': r'yaml\.load\s*\(\s*[^,)]*\)',
            'unsafe_pickle': r'pickle\.loads?\s*\(\s*[^)]*\)',
        }
        
        for file_path in self._get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for issue_type, pattern in unsafe_patterns.items():
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        
                        validation_issues.append({
                            "check": "Input Validation",
                            "severity": "Medium",
                            "file": str(file_path),
                            "line": line_num,
                            "issue_type": issue_type,
                            "details": f"Potential {issue_type.replace('_', ' ')} vulnerability"
                        })
                
            except Exception as e:
                logger.warning(f"Could not check input validation for {file_path}: {e}")
        
        logger.info(f"Input validation check completed. Found {len(validation_issues)} issues")
        return validation_issues
    
    def check_configuration_security(self) -> List[Dict[str, Any]]:
        """Check configuration files for security issues"""
        logger.info("Checking configuration security...")
        
        config_issues = []
        
        # Check config.yaml for security settings
        config_path = self.scan_path / "config.yaml"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Check for insecure settings
                if isinstance(config, dict):
                    # Check for privileged mode
                    if config.get('privileged', False):
                        config_issues.append({
                            "check": "Configuration Security",
                            "severity": "High",
                            "file": str(config_path),
                            "details": "Addon configured with privileged mode"
                        })
                    
                    # Check for host network access
                    if config.get('host_network', False):
                        config_issues.append({
                            "check": "Configuration Security",
                            "severity": "Medium",
                            "file": str(config_path),
                            "details": "Addon configured with host network access"
                        })
                    
                    # Check for excessive capabilities
                    capabilities = config.get('capabilities', [])
                    if capabilities:
                        dangerous_caps = ['SYS_ADMIN', 'NET_ADMIN', 'SYS_PTRACE', 'SYS_MODULE']
                        for cap in dangerous_caps:
                            if cap in capabilities:
                                config_issues.append({
                                    "check": "Configuration Security",
                                    "severity": "High",
                                    "file": str(config_path),
                                    "details": f"Addon requests dangerous capability: {cap}"
                                })
                
            except Exception as e:
                logger.warning(f"Could not check configuration security: {e}")
        
        logger.info(f"Configuration security check completed. Found {len(config_issues)} issues")
        return config_issues
    
    def check_dependencies(self) -> List[Dict[str, Any]]:
        """Check for known vulnerable dependencies"""
        logger.info("Checking dependencies for vulnerabilities...")
        
        dependency_issues = []
        
        # Check requirements.txt
        requirements_path = self.scan_path / "requirements.txt"
        if requirements_path.exists():
            try:
                # Use safety check if available
                result = subprocess.run(
                    ['safety', 'check', '-r', str(requirements_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0 and result.stdout:
                    # Parse safety output
                    for line in result.stdout.split('\n'):
                        if 'vulnerability' in line.lower():
                            dependency_issues.append({
                                "check": "Dependency Vulnerability",
                                "severity": "High",
                                "file": str(requirements_path),
                                "details": line.strip()
                            })
                
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Safety not available, perform basic checks
                try:
                    with open(requirements_path, 'r') as f:
                        requirements = f.read()
                    
                    # Check for known vulnerable packages (basic check)
                    vulnerable_packages = {
                        'jinja2': '2.10',  # Example: versions before 2.10.1 had issues
                        'requests': '2.20.0',  # Example: versions before 2.20.0 had issues
                    }
                    
                    for package, min_version in vulnerable_packages.items():
                        if package in requirements:
                            dependency_issues.append({
                                "check": "Dependency Security",
                                "severity": "Medium",
                                "file": str(requirements_path),
                                "details": f"Consider updating {package} to version {min_version} or higher"
                            })
                
                except Exception as e:
                    logger.warning(f"Could not check dependencies: {e}")
        
        logger.info(f"Dependency check completed. Found {len(dependency_issues)} issues")
        return dependency_issues
    
    def _get_files_to_scan(self) -> List[Path]:
        """Get list of files to scan for secrets"""
        files = []
        for ext in self.SCAN_EXTENSIONS:
            files.extend(self.scan_path.rglob(f"*{ext}"))
        
        # Filter out files in skip directories
        filtered_files = []
        for file_path in files:
            if not any(skip_dir in file_path.parts for skip_dir in self.SKIP_DIRECTORIES):
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _get_python_files(self) -> List[Path]:
        """Get list of Python files to scan"""
        files = list(self.scan_path.rglob("*.py"))
        return [f for f in files if not any(skip_dir in f.parts for skip_dir in self.SKIP_DIRECTORIES)]
    
    def _get_all_files(self) -> List[Path]:
        """Get list of all files to check"""
        files = []
        for root, dirs, filenames in os.walk(self.scan_path):
            # Skip directories we don't want to scan
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRECTORIES]
            
            for filename in filenames:
                files.append(Path(root) / filename)
        
        return files
    
    def run_all_security_checks(self) -> List[Dict[str, Any]]:
        """Run all security checks"""
        logger.info("Starting comprehensive security scan...")
        
        all_issues = []
        
        try:
            # Run individual checks
            all_issues.extend(self.scan_for_hardcoded_secrets())
            all_issues.extend(self.check_file_permissions())
            all_issues.extend(self.check_input_validation())
            all_issues.extend(self.check_configuration_security())
            all_issues.extend(self.check_dependencies())
            
        except Exception as e:
            logger.error(f"Error during security scan: {e}")
            all_issues.append({
                "check": "Security Scan Error",
                "severity": "High",
                "file": "N/A",
                "details": f"Security scan failed: {str(e)}"
            })
        
        logger.info(f"Security scan completed. Found {len(all_issues)} total issues")
        return all_issues


def run_security_checks(scan_path: str = ".") -> List[Dict[str, Any]]:
    """Main function to run security checks"""
    tester = SecurityTester(scan_path)
    return tester.run_all_security_checks()


if __name__ == "__main__":
    # Run security checks if script is executed directly
    scan_path = sys.argv[1] if len(sys.argv) > 1 else "."
    issues = run_security_checks(scan_path)
    
    # Print summary
    print(f"\n=== Security Scan Summary ===")
    if not issues:
        print("✅ No security issues found!")
    else:
        severity_counts = {}
        for issue in issues:
            severity = issue.get("severity", "Unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        print(f"Found {len(issues)} security issues:")
        for severity, count in sorted(severity_counts.items()):
            print(f"  {severity}: {count}")
    print("=============================")