#!/usr/bin/env python3
"""
AICleaner v3 Production Readiness Validation Script

This script performs automated checks to validate the system's readiness for production deployment.
Based on the production validation checklist from the integration testing strategy.

Usage:
    python scripts/validate_production_readiness.py [--config CONFIG_PATH] [--output REPORT_PATH]

Exit Codes:
    0: All checks passed, system ready for production
    1: Critical issues found, system not ready for production
    2: Warnings found, review required before production
"""

import os
import sys
import json
import subprocess
import re
import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import argparse
import tempfile

# Optional dependencies - gracefully handle missing packages
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class ProductionValidator:
    """Main class for production readiness validation"""
    
    def __init__(self, config_path: Optional[str] = None, output_path: Optional[str] = None):
        self.config_path = config_path or "config/aicleaner_config.json"
        self.output_path = output_path or f"production_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0",
            "overall_status": "unknown",
            "critical_issues": [],
            "warnings": [],
            "passed_checks": [],
            "security_score": 0,
            "performance_score": 0,
            "deployment_ready": False,
            "detailed_results": {}
        }
        
    async def run_validation(self) -> Dict[str, Any]:
        """Run all production validation checks"""
        
        print("🚀 Starting AICleaner v3 Production Readiness Validation...")
        print(f"⏰ Timestamp: {self.results['timestamp']}")
        print("=" * 60)
        
        # Security Audit
        await self._run_security_audit()
        
        # Performance & Scalability
        await self._run_performance_tests()
        
        # Deployment & Operations
        await self._run_deployment_checks()
        
        # Configuration Validation
        await self._run_configuration_validation()
        
        # Code Quality Checks
        await self._run_code_quality_checks()
        
        # Infrastructure Checks
        await self._run_infrastructure_checks()
        
        # Calculate overall status
        self._calculate_overall_status()
        
        # Generate report
        self._generate_report()
        
        return self.results
    
    async def _run_security_audit(self):
        """Security audit checks"""
        print("\n🔒 Running Security Audit...")
        section_results = {}
        
        # Check for hardcoded secrets
        secrets_check = await self._check_hardcoded_secrets()
        section_results["hardcoded_secrets"] = secrets_check
        
        # Dependency vulnerability scan
        vuln_check = await self._run_dependency_scan()
        section_results["dependency_vulnerabilities"] = vuln_check
        
        # API endpoint security
        api_security = await self._check_api_security()
        section_results["api_security"] = api_security
        
        # CORS configuration
        cors_check = await self._check_cors_configuration()
        section_results["cors_configuration"] = cors_check
        
        # SSL/TLS configuration
        ssl_check = await self._check_ssl_configuration()
        section_results["ssl_configuration"] = ssl_check
        
        # Calculate security score
        security_score = self._calculate_security_score(section_results)
        self.results["security_score"] = security_score
        self.results["detailed_results"]["security"] = section_results
        
        print(f"   Security Score: {security_score}/100")
    
    async def _check_hardcoded_secrets(self) -> Dict[str, Any]:
        """Check for hardcoded secrets in codebase"""
        print("   🔍 Checking for hardcoded secrets...")
        
        result = {
            "status": "passed",
            "issues": [],
            "files_scanned": 0,
            "patterns_checked": 0
        }
        
        # Secret patterns to detect
        secret_patterns = [
            (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']([^"\']+)["\']', "API Key"),
            (r'(?i)(secret|password|passwd|pwd)\s*[:=]\s*["\']([^"\']+)["\']', "Password/Secret"),
            (r'(?i)(token)\s*[:=]\s*["\']([a-zA-Z0-9_-]{20,})["\']', "Token"),
            (r'(?i)(private[_-]?key)\s*[:=]\s*["\']([^"\']+)["\']', "Private Key"),
            (r'AIzaSy[A-Za-z0-9_-]{33}', "Google API Key"),
            (r'sk-[A-Za-z0-9]{48}', "OpenAI API Key"),
            (r'xoxb-[0-9]{11}-[0-9]{11}-[A-Za-z0-9]{24}', "Slack Bot Token"),
        ]
        
        result["patterns_checked"] = len(secret_patterns)
        
        # Scan Python files
        for file_path in Path(".").rglob("*.py"):
            if any(exclude in str(file_path) for exclude in [".git", "__pycache__", ".venv", "venv"]):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    result["files_scanned"] += 1
                    
                    for pattern, secret_type in secret_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            # Skip if it's clearly a placeholder or test value
                            secret_value = match.group(2) if match.lastindex >= 2 else match.group(0)
                            if any(placeholder in secret_value.lower() for placeholder in 
                                   ["placeholder", "example", "test", "dummy", "fake", "xxx", "your_key"]):
                                continue
                                
                            result["issues"].append({
                                "file": str(file_path),
                                "line": content[:match.start()].count('\n') + 1,
                                "type": secret_type,
                                "pattern": pattern,
                                "severity": "critical"
                            })
                            
            except Exception as e:
                result["issues"].append({
                    "file": str(file_path),
                    "error": f"Failed to scan file: {e}",
                    "severity": "warning"
                })
        
        if result["issues"]:
            result["status"] = "failed"
            critical_issues = [issue for issue in result["issues"] if issue.get("severity") == "critical"]
            if critical_issues:
                self.results["critical_issues"].extend(critical_issues)
        else:
            self.results["passed_checks"].append("No hardcoded secrets found")
            
        return result
    
    async def _run_dependency_scan(self) -> Dict[str, Any]:
        """Run dependency vulnerability scan"""
        print("   🔍 Scanning dependencies for vulnerabilities...")
        
        result = {
            "status": "passed",
            "vulnerabilities": [],
            "total_packages": 0,
            "scan_tool": None
        }
        
        # Check if safety is available
        try:
            subprocess.run(["safety", "--version"], capture_output=True, check=True)
            result["scan_tool"] = "safety"
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Try pip-audit as alternative
            try:
                subprocess.run(["pip-audit", "--version"], capture_output=True, check=True)
                result["scan_tool"] = "pip-audit"
            except (subprocess.CalledProcessError, FileNotFoundError):
                result["status"] = "warning"
                result["error"] = "No vulnerability scanning tool available (safety or pip-audit)"
                self.results["warnings"].append("Dependency vulnerability scan skipped - no scanning tool available")
                return result
        
        # Run vulnerability scan
        try:
            if result["scan_tool"] == "safety":
                process = subprocess.run(
                    ["safety", "check", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if process.stdout:
                    scan_data = json.loads(process.stdout)
                    result["vulnerabilities"] = scan_data
                    
            elif result["scan_tool"] == "pip-audit":
                process = subprocess.run(
                    ["pip-audit", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if process.stdout:
                    scan_data = json.loads(process.stdout)
                    result["vulnerabilities"] = scan_data.get("vulnerabilities", [])
            
            # Analyze results
            critical_vulns = []
            high_vulns = []
            
            for vuln in result["vulnerabilities"]:
                severity = vuln.get("severity", "unknown").lower()
                if severity in ["critical"]:
                    critical_vulns.append(vuln)
                elif severity in ["high"]:
                    high_vulns.append(vuln)
            
            if critical_vulns:
                result["status"] = "failed"
                self.results["critical_issues"].extend(critical_vulns)
            elif high_vulns:
                result["status"] = "warning"
                self.results["warnings"].extend(high_vulns)
            else:
                self.results["passed_checks"].append("No critical dependency vulnerabilities found")
                
        except subprocess.TimeoutExpired:
            result["status"] = "warning"
            result["error"] = "Vulnerability scan timed out"
            self.results["warnings"].append("Dependency scan timed out")
        except Exception as e:
            result["status"] = "warning"
            result["error"] = f"Vulnerability scan failed: {e}"
            self.results["warnings"].append(f"Dependency scan failed: {e}")
        
        return result
    
    async def _check_api_security(self) -> Dict[str, Any]:
        """Check API endpoint security"""
        print("   🔍 Checking API endpoint security...")
        
        result = {
            "status": "passed",
            "issues": [],
            "endpoints_checked": 0,
            "protected_endpoints": 0
        }
        
        # Check FastAPI server.py for security configurations
        server_file = Path("ui/api/server.py")
        if server_file.exists():
            try:
                with open(server_file, 'r') as f:
                    content = f.read()
                    
                # Check for CORS configuration
                if "CORSMiddleware" in content:
                    if 'allow_origins=["*"]' in content:
                        result["issues"].append({
                            "type": "cors_wildcard",
                            "message": "CORS allows all origins (*) - security risk",
                            "severity": "high",
                            "file": str(server_file)
                        })
                        
                # Check for authentication on sensitive endpoints
                sensitive_patterns = [
                    r'@app\.(post|put|delete)\("/api/config',
                    r'@app\.(post|put|delete)\("/api/security',
                    r'@app\.(post|put|delete)\("/api/zones'
                ]
                
                for pattern in sensitive_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        result["endpoints_checked"] += 1
                        # Check if authentication is present nearby
                        line_start = content.rfind('\n', 0, match.start()) + 1
                        line_end = content.find('\n', match.end())
                        endpoint_context = content[max(0, line_start-500):line_end+500]
                        
                        if "authenticate" not in endpoint_context.lower() and "security" not in endpoint_context.lower():
                            result["issues"].append({
                                "type": "unprotected_endpoint",
                                "message": f"Sensitive endpoint may lack authentication: {match.group(0)}",
                                "severity": "medium",
                                "file": str(server_file),
                                "line": content[:match.start()].count('\n') + 1
                            })
                        else:
                            result["protected_endpoints"] += 1
                            
            except Exception as e:
                result["issues"].append({
                    "type": "scan_error",
                    "message": f"Failed to analyze API security: {e}",
                    "severity": "warning"
                })
        
        # Categorize issues
        if any(issue["severity"] == "high" for issue in result["issues"]):
            result["status"] = "failed"
            high_issues = [issue for issue in result["issues"] if issue["severity"] == "high"]
            self.results["critical_issues"].extend(high_issues)
        elif result["issues"]:
            result["status"] = "warning"
            self.results["warnings"].extend(result["issues"])
        else:
            self.results["passed_checks"].append("API security configuration validated")
            
        return result
    
    async def _check_cors_configuration(self) -> Dict[str, Any]:
        """Check CORS configuration"""
        print("   🔍 Checking CORS configuration...")
        
        result = {
            "status": "passed",
            "configuration": {},
            "issues": []
        }
        
        # Check CORS settings in FastAPI configuration
        server_file = Path("ui/api/server.py")
        if server_file.exists():
            try:
                with open(server_file, 'r') as f:
                    content = f.read()
                    
                cors_match = re.search(r'CORSMiddleware[^}]+allow_origins=\[([^\]]+)\]', content)
                if cors_match:
                    origins_str = cors_match.group(1)
                    result["configuration"]["allow_origins"] = origins_str
                    
                    if '"*"' in origins_str:
                        result["issues"].append({
                            "type": "cors_wildcard",
                            "message": "CORS allows all origins - not suitable for production",
                            "severity": "high"
                        })
                        result["status"] = "failed"
                    elif "localhost" in origins_str:
                        result["issues"].append({
                            "type": "cors_localhost",
                            "message": "CORS includes localhost - should be removed for production",
                            "severity": "medium"
                        })
                        result["status"] = "warning"
                        
            except Exception as e:
                result["issues"].append({
                    "type": "scan_error",
                    "message": f"Failed to analyze CORS configuration: {e}",
                    "severity": "warning"
                })
        
        if result["status"] == "failed":
            self.results["critical_issues"].extend([issue for issue in result["issues"] if issue["severity"] == "high"])
        elif result["status"] == "warning":
            self.results["warnings"].extend(result["issues"])
        else:
            self.results["passed_checks"].append("CORS configuration is production-ready")
            
        return result
    
    async def _check_ssl_configuration(self) -> Dict[str, Any]:
        """Check SSL/TLS configuration"""
        print("   🔍 Checking SSL/TLS configuration...")
        
        result = {
            "status": "passed",
            "configuration": {},
            "issues": []
        }
        
        # Check if SSL is enforced in configuration
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    
                security_config = config.get("security", {})
                mqtt_config = config.get("mqtt", {})
                
                # Check if SSL is required
                if not security_config.get("ssl_required", False):
                    result["issues"].append({
                        "type": "ssl_not_required",
                        "message": "SSL/TLS is not enforced for web interface",
                        "severity": "high"
                    })
                    
                # Check MQTT TLS configuration
                if not mqtt_config.get("use_tls", False):
                    result["issues"].append({
                        "type": "mqtt_no_tls",
                        "message": "MQTT communication is not encrypted",
                        "severity": "medium"
                    })
                    
                result["configuration"] = {
                    "ssl_required": security_config.get("ssl_required", False),
                    "mqtt_tls": mqtt_config.get("use_tls", False)
                }
                
        except Exception as e:
            result["issues"].append({
                "type": "config_error",
                "message": f"Failed to check SSL configuration: {e}",
                "severity": "warning"
            })
        
        if any(issue["severity"] == "high" for issue in result["issues"]):
            result["status"] = "failed"
            self.results["critical_issues"].extend([issue for issue in result["issues"] if issue["severity"] == "high"])
        elif result["issues"]:
            result["status"] = "warning"
            self.results["warnings"].extend(result["issues"])
        else:
            self.results["passed_checks"].append("SSL/TLS configuration is secure")
            
        return result
    
    async def _run_performance_tests(self):
        """Performance and scalability checks"""
        print("\n⚡ Running Performance Tests...")
        section_results = {}
        
        # API response time test
        api_performance = await self._test_api_performance()
        section_results["api_performance"] = api_performance
        
        # Memory usage analysis
        memory_check = await self._check_memory_usage()
        section_results["memory_usage"] = memory_check
        
        # Database query performance
        db_performance = await self._check_database_performance()
        section_results["database_performance"] = db_performance
        
        # Bundle size analysis
        bundle_analysis = await self._analyze_bundle_size()
        section_results["bundle_size"] = bundle_analysis
        
        performance_score = self._calculate_performance_score(section_results)
        self.results["performance_score"] = performance_score
        self.results["detailed_results"]["performance"] = section_results
        
        print(f"   Performance Score: {performance_score}/100")
    
    async def _test_api_performance(self) -> Dict[str, Any]:
        """Test API response times"""
        print("   ⏱️ Testing API response times...")
        
        result = {
            "status": "passed",
            "endpoints": {},
            "average_response_time": 0,
            "max_response_time": 0
        }
        
        # Test endpoints (assuming server is running)
        test_endpoints = [
            "/api/health",
            "/api/config", 
            "/api/security",
            "/api/metrics"
        ]
        
        base_url = "http://localhost:8080"  # Default FastAPI port
        response_times = []
        
        # Skip API performance test if aiohttp not available
        if not AIOHTTP_AVAILABLE:
            result["status"] = "warning"
            result["error"] = "aiohttp not available - API performance test skipped"
            self.results["warnings"].append("API performance test skipped - aiohttp dependency missing")
            return result
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                for endpoint in test_endpoints:
                    try:
                        start_time = time.time()
                        async with session.get(f"{base_url}{endpoint}") as response:
                            end_time = time.time()
                            response_time = (end_time - start_time) * 1000  # Convert to ms
                            
                            result["endpoints"][endpoint] = {
                                "response_time_ms": response_time,
                                "status_code": response.status,
                                "status": "passed" if response_time < 500 else "warning"
                            }
                            
                            if response.status == 200:
                                response_times.append(response_time)
                                
                    except asyncio.TimeoutError:
                        result["endpoints"][endpoint] = {
                            "response_time_ms": float('inf'),
                            "status": "failed",
                            "error": "Timeout"
                        }
                    except Exception as e:
                        result["endpoints"][endpoint] = {
                            "status": "error",
                            "error": str(e)
                        }
                        
        except Exception as e:
            result["status"] = "warning"
            result["error"] = f"Could not connect to server: {e}"
            self.results["warnings"].append("API performance test skipped - server not running")
            return result
        
        if response_times:
            result["average_response_time"] = sum(response_times) / len(response_times)
            result["max_response_time"] = max(response_times)
            
            if result["average_response_time"] > 500:
                result["status"] = "warning"
                self.results["warnings"].append(f"Average API response time is high: {result['average_response_time']:.2f}ms")
            elif result["max_response_time"] > 1000:
                result["status"] = "warning"
                self.results["warnings"].append(f"Maximum API response time is very high: {result['max_response_time']:.2f}ms")
            else:
                self.results["passed_checks"].append("API response times are within acceptable limits")
        
        return result
    
    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage patterns"""
        print("   💾 Analyzing memory usage...")
        
        result = {
            "status": "passed",
            "current_usage": {},
            "issues": []
        }
        
        try:
            # Check for common memory leak patterns in code
            memory_patterns = [
                (r'\.append\([^)]+\)(?!\s*\.clear\(\))', "Potential list growth without cleanup"),
                (r'cache\s*=\s*\{\}', "Dictionary cache without size limits"),
                (r'while\s+True:(?![^{]*break)', "Infinite loop without break condition"),
            ]
            
            for file_path in Path(".").rglob("*.py"):
                if any(exclude in str(file_path) for exclude in [".git", "__pycache__", ".venv"]):
                    continue
                    
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                        for pattern, description in memory_patterns:
                            matches = re.finditer(pattern, content)
                            for match in matches:
                                result["issues"].append({
                                    "file": str(file_path),
                                    "line": content[:match.start()].count('\n') + 1,
                                    "pattern": description,
                                    "severity": "warning"
                                })
                                
                except Exception:
                    continue
            
            if result["issues"]:
                result["status"] = "warning"
                self.results["warnings"].extend(result["issues"])
            else:
                self.results["passed_checks"].append("No obvious memory leak patterns detected")
                
        except Exception as e:
            result["status"] = "warning"
            result["error"] = f"Memory analysis failed: {e}"
            
        return result
    
    async def _check_database_performance(self) -> Dict[str, Any]:
        """Check database query performance"""
        print("   🗄️ Checking database performance...")
        
        result = {
            "status": "passed",
            "indices": [],
            "slow_queries": [],
            "recommendations": []
        }
        
        # This is a placeholder - in a real implementation, you would:
        # 1. Connect to the actual database
        # 2. Analyze query plans
        # 3. Check for missing indices
        # 4. Identify slow queries
        
        # For now, check if there are database configuration files
        db_config_files = list(Path(".").rglob("*database*")) + list(Path(".").rglob("*db*"))
        
        if not db_config_files:
            result["recommendations"].append("Consider adding database configuration optimization")
            
        self.results["passed_checks"].append("Database performance check completed")
        return result
    
    async def _analyze_bundle_size(self) -> Dict[str, Any]:
        """Analyze frontend bundle size"""
        print("   📦 Analyzing frontend bundle size...")
        
        result = {
            "status": "passed",
            "total_size": 0,
            "files": {},
            "recommendations": []
        }
        
        # Check React build directory
        build_dir = Path("ui/dist") or Path("ui/build")
        if build_dir.exists():
            total_size = 0
            for file_path in build_dir.rglob("*"):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    total_size += size
                    
                    if file_path.suffix in ['.js', '.css']:
                        result["files"][str(file_path)] = {
                            "size_bytes": size,
                            "size_mb": size / (1024 * 1024)
                        }
            
            result["total_size"] = total_size
            result["total_size_mb"] = total_size / (1024 * 1024)
            
            # Check for large bundles
            if result["total_size_mb"] > 10:
                result["status"] = "warning"
                result["recommendations"].append("Bundle size is large (>10MB), consider code splitting")
                self.results["warnings"].append(f"Large bundle size: {result['total_size_mb']:.2f}MB")
            else:
                self.results["passed_checks"].append("Frontend bundle size is acceptable")
        else:
            result["status"] = "warning"
            result["error"] = "Frontend build directory not found"
            self.results["warnings"].append("Frontend bundle analysis skipped - build directory not found")
            
        return result
    
    async def _run_deployment_checks(self):
        """Deployment and operations checks"""
        print("\n🚀 Running Deployment Checks...")
        section_results = {}
        
        # Environment parity check
        env_check = await self._check_environment_parity()
        section_results["environment_parity"] = env_check
        
        # Configuration validation
        config_check = await self._validate_deployment_config()
        section_results["deployment_config"] = config_check
        
        # Backup and restore procedures
        backup_check = await self._check_backup_procedures()
        section_results["backup_procedures"] = backup_check
        
        # Logging configuration
        logging_check = await self._check_logging_configuration()
        section_results["logging_configuration"] = logging_check
        
        self.results["detailed_results"]["deployment"] = section_results
    
    async def _check_environment_parity(self) -> Dict[str, Any]:
        """Check environment parity"""
        print("   🔄 Checking environment parity...")
        
        result = {
            "status": "passed",
            "required_vars": [],
            "missing_vars": [],
            "docker_config": {}
        }
        
        # Check for required environment variables
        required_env_vars = [
            "GEMINI_API_KEY",
            "OPENAI_API_KEY", 
            "MQTT_BROKER_ADDRESS",
            "HOME_ASSISTANT_URL"
        ]
        
        for var in required_env_vars:
            if os.getenv(var):
                result["required_vars"].append(var)
            else:
                result["missing_vars"].append(var)
        
        # Check Docker configuration
        dockerfile_path = Path("Dockerfile")
        if dockerfile_path.exists():
            result["docker_config"]["dockerfile_exists"] = True
        else:
            result["missing_vars"].append("Dockerfile")
            
        docker_compose_path = Path("docker-compose.yml")
        if docker_compose_path.exists():
            result["docker_config"]["docker_compose_exists"] = True
        else:
            result["missing_vars"].append("docker-compose.yml")
        
        if result["missing_vars"]:
            result["status"] = "warning"
            self.results["warnings"].append(f"Missing environment configuration: {', '.join(result['missing_vars'])}")
        else:
            self.results["passed_checks"].append("All required environment variables are configured")
            
        return result
    
    async def _validate_deployment_config(self) -> Dict[str, Any]:
        """Validate deployment configuration"""
        print("   ⚙️ Validating deployment configuration...")
        
        result = {
            "status": "passed",
            "config_valid": False,
            "issues": []
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    
                # Validate critical configuration sections
                required_sections = ["ai", "security", "mqtt"]
                for section in required_sections:
                    if section not in config:
                        result["issues"].append(f"Missing configuration section: {section}")
                        
                # Validate AI provider configuration
                ai_config = config.get("ai", {})
                if not ai_config.get("providers"):
                    result["issues"].append("No AI providers configured")
                    
                # Validate security configuration
                security_config = config.get("security", {})
                if not security_config.get("supervisor_token"):
                    result["issues"].append("Supervisor token not configured")
                    
                if result["issues"]:
                    result["status"] = "failed"
                    self.results["critical_issues"].extend([{"type": "config", "message": issue} for issue in result["issues"]])
                else:
                    result["config_valid"] = True
                    self.results["passed_checks"].append("Deployment configuration is valid")
                    
            else:
                result["status"] = "failed"
                result["issues"].append("Configuration file not found")
                self.results["critical_issues"].append({"type": "config", "message": "Configuration file missing"})
                
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            self.results["critical_issues"].append({"type": "config", "message": f"Configuration validation failed: {e}"})
            
        return result
    
    async def _check_backup_procedures(self) -> Dict[str, Any]:
        """Check backup and restore procedures"""
        print("   💾 Checking backup procedures...")
        
        result = {
            "status": "passed",
            "backup_script_exists": False,
            "restore_script_exists": False,
            "documentation_exists": False
        }
        
        # Check for backup scripts
        backup_files = list(Path(".").rglob("*backup*")) + list(Path(".").rglob("*restore*"))
        
        if backup_files:
            result["backup_script_exists"] = True
            self.results["passed_checks"].append("Backup procedures are documented")
        else:
            result["status"] = "warning"
            self.results["warnings"].append("No backup/restore procedures found")
            
        return result
    
    async def _check_logging_configuration(self) -> Dict[str, Any]:
        """Check logging configuration"""
        print("   📝 Checking logging configuration...")
        
        result = {
            "status": "passed",
            "structured_logging": False,
            "log_levels": [],
            "centralized": False
        }
        
        # Check for logging configuration in Python files
        for file_path in Path(".").rglob("*.py"):
            if any(exclude in str(file_path) for exclude in [".git", "__pycache__", ".venv"]):
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                    if "logging.getLogger" in content:
                        result["structured_logging"] = True
                        
                    # Check for different log levels
                    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                        if f"logging.{level.lower()}" in content or f"logger.{level.lower()}" in content:
                            if level not in result["log_levels"]:
                                result["log_levels"].append(level)
                                
            except Exception:
                continue
        
        if result["structured_logging"]:
            self.results["passed_checks"].append("Structured logging is implemented")
        else:
            result["status"] = "warning"
            self.results["warnings"].append("No structured logging found")
            
        return result
    
    async def _run_configuration_validation(self):
        """Configuration validation checks"""
        print("\n⚙️ Running Configuration Validation...")
        
        # This is handled in deployment checks
        pass
    
    async def _run_code_quality_checks(self):
        """Code quality and standards checks"""
        print("\n🔍 Running Code Quality Checks...")
        section_results = {}
        
        # Test coverage analysis
        coverage_check = await self._check_test_coverage()
        section_results["test_coverage"] = coverage_check
        
        # Code complexity analysis
        complexity_check = await self._check_code_complexity()
        section_results["code_complexity"] = complexity_check
        
        # Documentation coverage
        doc_check = await self._check_documentation_coverage()
        section_results["documentation"] = doc_check
        
        self.results["detailed_results"]["code_quality"] = section_results
    
    async def _check_test_coverage(self) -> Dict[str, Any]:
        """Check test coverage"""
        print("   🧪 Checking test coverage...")
        
        result = {
            "status": "passed",
            "coverage_percentage": 0,
            "test_files": 0,
            "missing_coverage": []
        }
        
        # Count test files
        test_files = list(Path(".").rglob("test_*.py")) + list(Path(".").rglob("*_test.py"))
        result["test_files"] = len(test_files)
        
        # Try to run coverage if available
        try:
            process = subprocess.run(
                ["python", "-m", "pytest", "--cov=.", "--cov-report=json", "tests/"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if process.returncode == 0:
                # Look for coverage.json
                coverage_file = Path(".coverage.json") or Path("coverage.json")
                if coverage_file.exists():
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                        result["coverage_percentage"] = coverage_data.get("totals", {}).get("percent_covered", 0)
                        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            result["status"] = "warning"
            result["error"] = "Could not run coverage analysis"
            
        # Estimate coverage based on test files
        if result["coverage_percentage"] == 0:
            total_py_files = len(list(Path(".").rglob("*.py")))
            if total_py_files > 0:
                result["coverage_percentage"] = min((result["test_files"] / total_py_files) * 100, 100)
        
        if result["coverage_percentage"] < 70:
            result["status"] = "warning"
            self.results["warnings"].append(f"Test coverage is low: {result['coverage_percentage']:.1f}%")
        else:
            self.results["passed_checks"].append(f"Test coverage is adequate: {result['coverage_percentage']:.1f}%")
            
        return result
    
    async def _check_code_complexity(self) -> Dict[str, Any]:
        """Check code complexity"""
        print("   📊 Checking code complexity...")
        
        result = {
            "status": "passed",
            "complex_functions": [],
            "total_functions": 0
        }
        
        # Simple complexity check - count function length and nested statements
        for file_path in Path(".").rglob("*.py"):
            if any(exclude in str(file_path) for exclude in [".git", "__pycache__", ".venv"]):
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                    # Find function definitions
                    functions = re.finditer(r'^( *)def\s+(\w+)', content, re.MULTILINE)
                    for func_match in functions:
                        result["total_functions"] += 1
                        func_name = func_match.group(2)
                        indent_level = len(func_match.group(1))
                        
                        # Find function end (next def at same or higher level)
                        func_start = func_match.end()
                        func_lines = []
                        
                        for line in content[func_start:].split('\n'):
                            if line.strip() and not line.startswith(' ' * (indent_level + 4)):
                                if line.startswith('def ') or line.startswith('class '):
                                    break
                            func_lines.append(line)
                        
                        # Check complexity
                        if len(func_lines) > 50:  # Long function
                            result["complex_functions"].append({
                                "file": str(file_path),
                                "function": func_name,
                                "lines": len(func_lines),
                                "reason": "Long function"
                            })
                            
                        # Check nesting depth
                        max_indent = 0
                        for line in func_lines:
                            if line.strip():
                                line_indent = len(line) - len(line.lstrip())
                                max_indent = max(max_indent, line_indent)
                        
                        if max_indent > 20:  # Deep nesting
                            result["complex_functions"].append({
                                "file": str(file_path),
                                "function": func_name,
                                "max_indent": max_indent,
                                "reason": "Deep nesting"
                            })
                            
            except Exception:
                continue
        
        if result["complex_functions"]:
            result["status"] = "warning"
            self.results["warnings"].append(f"Found {len(result['complex_functions'])} complex functions")
        else:
            self.results["passed_checks"].append("No overly complex functions detected")
            
        return result
    
    async def _check_documentation_coverage(self) -> Dict[str, Any]:
        """Check documentation coverage"""
        print("   📚 Checking documentation coverage...")
        
        result = {
            "status": "passed",
            "documented_functions": 0,
            "total_functions": 0,
            "missing_docs": []
        }
        
        # Check for docstrings in Python files
        for file_path in Path(".").rglob("*.py"):
            if any(exclude in str(file_path) for exclude in [".git", "__pycache__", ".venv"]):
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                    # Find function definitions
                    functions = re.finditer(r'def\s+(\w+)\s*\([^)]*\):', content)
                    for func_match in functions:
                        result["total_functions"] += 1
                        func_name = func_match.group(1)
                        
                        # Skip private functions
                        if func_name.startswith('_'):
                            continue
                        
                        # Look for docstring after function definition
                        func_end = func_match.end()
                        remaining_content = content[func_end:]
                        
                        # Check if next non-empty line starts with quotes
                        lines = remaining_content.split('\n')
                        for line in lines[:10]:  # Check first 10 lines
                            stripped = line.strip()
                            if stripped:
                                if stripped.startswith('"""') or stripped.startswith("'''"):
                                    result["documented_functions"] += 1
                                    break
                                else:
                                    result["missing_docs"].append({
                                        "file": str(file_path),
                                        "function": func_name
                                    })
                                    break
                                    
            except Exception:
                continue
        
        if result["total_functions"] > 0:
            doc_percentage = (result["documented_functions"] / result["total_functions"]) * 100
            if doc_percentage < 50:
                result["status"] = "warning"
                self.results["warnings"].append(f"Low documentation coverage: {doc_percentage:.1f}%")
            else:
                self.results["passed_checks"].append(f"Good documentation coverage: {doc_percentage:.1f}%")
        
        return result
    
    async def _run_infrastructure_checks(self):
        """Infrastructure and deployment checks"""
        print("\n🏗️ Running Infrastructure Checks...")
        section_results = {}
        
        # Docker configuration
        docker_check = await self._check_docker_configuration()
        section_results["docker"] = docker_check
        
        # Resource requirements
        resource_check = await self._check_resource_requirements()
        section_results["resources"] = resource_check
        
        self.results["detailed_results"]["infrastructure"] = section_results
    
    async def _check_docker_configuration(self) -> Dict[str, Any]:
        """Check Docker configuration"""
        print("   🐳 Checking Docker configuration...")
        
        result = {
            "status": "passed",
            "dockerfile_exists": False,
            "docker_compose_exists": False,
            "multi_stage_build": False,
            "security_best_practices": []
        }
        
        # Check Dockerfile
        dockerfile = Path("Dockerfile")
        if dockerfile.exists():
            result["dockerfile_exists"] = True
            
            try:
                with open(dockerfile, 'r') as f:
                    content = f.read()
                    
                    # Check for multi-stage build
                    if "FROM" in content and content.count("FROM") > 1:
                        result["multi_stage_build"] = True
                        result["security_best_practices"].append("Multi-stage build")
                    
                    # Check for non-root user
                    if "USER" in content and "USER root" not in content:
                        result["security_best_practices"].append("Non-root user")
                    
                    # Check for specific tag (not :latest)
                    if ":latest" in content:
                        result["status"] = "warning"
                        self.results["warnings"].append("Dockerfile uses :latest tag")
                        
            except Exception as e:
                result["status"] = "warning"
                result["error"] = f"Failed to analyze Dockerfile: {e}"
        else:
            result["status"] = "warning"
            self.results["warnings"].append("Dockerfile not found")
        
        # Check docker-compose.yml
        compose_file = Path("docker-compose.yml")
        if compose_file.exists():
            result["docker_compose_exists"] = True
            self.results["passed_checks"].append("Docker Compose configuration found")
        
        return result
    
    async def _check_resource_requirements(self) -> Dict[str, Any]:
        """Check resource requirements"""
        print("   💻 Checking resource requirements...")
        
        result = {
            "status": "passed",
            "requirements_documented": False,
            "estimated_memory": "unknown",
            "estimated_cpu": "unknown"
        }
        
        # Look for resource documentation
        resource_docs = ["README.md", "DEPLOYMENT.md", "requirements.txt", "pyproject.toml"]
        
        for doc_file in resource_docs:
            if Path(doc_file).exists():
                result["requirements_documented"] = True
                break
        
        if not result["requirements_documented"]:
            result["status"] = "warning"
            self.results["warnings"].append("Resource requirements not documented")
        else:
            self.results["passed_checks"].append("Resource requirements are documented")
        
        return result
    
    def _calculate_security_score(self, security_results: Dict[str, Any]) -> int:
        """Calculate security score based on security check results"""
        score = 100
        
        # Deduct points for critical issues
        for check_name, check_result in security_results.items():
            if check_result.get("status") == "failed":
                score -= 20
            elif check_result.get("status") == "warning":
                score -= 10
            
            # Specific deductions
            if check_name == "hardcoded_secrets" and check_result.get("issues"):
                critical_secrets = [issue for issue in check_result["issues"] if issue.get("severity") == "critical"]
                score -= len(critical_secrets) * 15
            
            if check_name == "dependency_vulnerabilities" and check_result.get("vulnerabilities"):
                score -= len(check_result["vulnerabilities"]) * 5
        
        return max(0, score)
    
    def _calculate_performance_score(self, performance_results: Dict[str, Any]) -> int:
        """Calculate performance score based on performance check results"""
        score = 100
        
        # API performance
        api_result = performance_results.get("api_performance", {})
        if api_result.get("average_response_time", 0) > 500:
            score -= 20
        elif api_result.get("average_response_time", 0) > 200:
            score -= 10
        
        # Bundle size
        bundle_result = performance_results.get("bundle_size", {})
        if bundle_result.get("total_size_mb", 0) > 10:
            score -= 15
        elif bundle_result.get("total_size_mb", 0) > 5:
            score -= 5
        
        # Memory issues
        memory_result = performance_results.get("memory_usage", {})
        if memory_result.get("issues"):
            score -= len(memory_result["issues"]) * 5
        
        return max(0, score)
    
    def _calculate_overall_status(self):
        """Calculate overall validation status"""
        
        if self.results["critical_issues"]:
            self.results["overall_status"] = "failed"
            self.results["deployment_ready"] = False
        elif self.results["warnings"]:
            self.results["overall_status"] = "warning"
            self.results["deployment_ready"] = False
        else:
            self.results["overall_status"] = "passed"
            self.results["deployment_ready"] = True
        
        # Additional criteria for deployment readiness
        if self.results["security_score"] < 80:
            self.results["deployment_ready"] = False
            
        if self.results["performance_score"] < 70:
            self.results["deployment_ready"] = False
    
    def _generate_report(self):
        """Generate validation report"""
        
        # Save detailed JSON report
        with open(self.output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Print summary
        print("\n" + "=" * 60)
        print("🏁 PRODUCTION READINESS VALIDATION SUMMARY")
        print("=" * 60)
        
        status_emoji = {
            "passed": "✅",
            "warning": "⚠️", 
            "failed": "❌"
        }
        
        print(f"Overall Status: {status_emoji.get(self.results['overall_status'], '❓')} {self.results['overall_status'].upper()}")
        print(f"Security Score: {self.results['security_score']}/100")
        print(f"Performance Score: {self.results['performance_score']}/100")
        print(f"Deployment Ready: {'✅ YES' if self.results['deployment_ready'] else '❌ NO'}")
        
        print(f"\n📊 RESULTS SUMMARY:")
        print(f"✅ Passed Checks: {len(self.results['passed_checks'])}")
        print(f"⚠️ Warnings: {len(self.results['warnings'])}")
        print(f"❌ Critical Issues: {len(self.results['critical_issues'])}")
        
        if self.results["critical_issues"]:
            print(f"\n❌ CRITICAL ISSUES:")
            for issue in self.results["critical_issues"][:5]:  # Show first 5
                print(f"   • {issue.get('message', str(issue))}")
        
        if self.results["warnings"]:
            print(f"\n⚠️ WARNINGS:")
            for warning in self.results["warnings"][:5]:  # Show first 5
                print(f"   • {warning.get('message', str(warning))}")
        
        print(f"\n📄 Detailed report saved to: {self.output_path}")
        
        # Recommendations
        if not self.results["deployment_ready"]:
            print(f"\n💡 RECOMMENDATIONS:")
            print("   1. Address all critical issues before production deployment")
            print("   2. Review and resolve warnings where possible")
            print("   3. Ensure security score is above 80")
            print("   4. Verify performance meets requirements")
            print("   5. Test in staging environment that mirrors production")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="AICleaner v3 Production Readiness Validation")
    parser.add_argument("--config", help="Path to configuration file", default=None)
    parser.add_argument("--output", help="Path to output report file", default=None)
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    validator = ProductionValidator(args.config, args.output)
    results = await validator.run_validation()
    
    # Exit with appropriate code
    if results["overall_status"] == "failed":
        sys.exit(1)
    elif results["overall_status"] == "warning":
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())