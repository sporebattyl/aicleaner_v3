"""
Diagnostic Tools for AICleaner v3
Simple diagnostic and troubleshooting utilities for single-user deployment

This module provides essential diagnostic capabilities for troubleshooting
AICleaner v3 issues in a Home Assistant addon environment.
"""

import asyncio
import json
import os
import platform
import psutil
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import subprocess
import requests
import yaml

from .simple_logging import get_simple_logger, get_logging_stats


@dataclass
class SystemInfo:
    """System information for diagnostics"""
    platform: str
    python_version: str
    memory_total: int
    memory_available: int
    disk_total: int
    disk_free: int
    cpu_count: int
    cpu_percent: float
    load_average: Tuple[float, float, float]
    uptime: float


@dataclass
class AddonInfo:
    """Addon-specific information"""
    version: str
    config_path: str
    log_directory: str
    total_log_files: int
    total_log_size: int
    last_restart: Optional[datetime]
    ha_api_accessible: bool
    mqtt_connected: bool


@dataclass
class HealthCheck:
    """Health check results"""
    timestamp: datetime
    overall_status: str
    system_healthy: bool
    addon_healthy: bool
    api_accessible: bool
    logs_healthy: bool
    issues: List[str]
    recommendations: List[str]


class DiagnosticTool:
    """Main diagnostic tool for AICleaner v3"""
    
    def __init__(self, addon_root: str = "/data"):
        self.addon_root = Path(addon_root)
        self.logger = get_simple_logger("diagnostics")
        self.config_path = self.addon_root / "config.yaml"
        self.log_directory = self.addon_root / "logs"
        
    def get_system_info(self) -> SystemInfo:
        """Get system information"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Load average (Unix-like systems)
            try:
                load_avg = os.getloadavg()
            except (OSError, AttributeError):
                load_avg = (0.0, 0.0, 0.0)
            
            return SystemInfo(
                platform=platform.platform(),
                python_version=sys.version,
                memory_total=memory.total,
                memory_available=memory.available,
                disk_total=disk.total,
                disk_free=disk.free,
                cpu_count=psutil.cpu_count(),
                cpu_percent=psutil.cpu_percent(interval=1),
                load_average=load_avg,
                uptime=time.time() - psutil.boot_time()
            )
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return SystemInfo(
                platform="unknown",
                python_version=sys.version,
                memory_total=0,
                memory_available=0,
                disk_total=0,
                disk_free=0,
                cpu_count=0,
                cpu_percent=0.0,
                load_average=(0.0, 0.0, 0.0),
                uptime=0.0
            )
    
    def get_addon_info(self) -> AddonInfo:
        """Get addon-specific information"""
        try:
            # Get version from config
            version = "unknown"
            try:
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    version = config.get('version', 'unknown')
            except Exception:
                pass
            
            # Get log information
            total_log_files = 0
            total_log_size = 0
            if self.log_directory.exists():
                for log_file in self.log_directory.rglob("*.log*"):
                    total_log_files += 1
                    try:
                        total_log_size += log_file.stat().st_size
                    except OSError:
                        pass
            
            # Check last restart (simplified)
            last_restart = None
            try:
                if self.log_directory.exists():
                    main_log = self.log_directory / "aicleaner.log"
                    if main_log.exists():
                        stat = main_log.stat()
                        last_restart = datetime.fromtimestamp(stat.st_mtime)
            except Exception:
                pass
            
            # Check HA API accessibility
            ha_api_accessible = self._check_ha_api()
            
            # Check MQTT connection (simplified)
            mqtt_connected = self._check_mqtt_connection()
            
            return AddonInfo(
                version=version,
                config_path=str(self.config_path),
                log_directory=str(self.log_directory),
                total_log_files=total_log_files,
                total_log_size=total_log_size,
                last_restart=last_restart,
                ha_api_accessible=ha_api_accessible,
                mqtt_connected=mqtt_connected
            )
        except Exception as e:
            self.logger.error(f"Error getting addon info: {e}")
            return AddonInfo(
                version="unknown",
                config_path=str(self.config_path),
                log_directory=str(self.log_directory),
                total_log_files=0,
                total_log_size=0,
                last_restart=None,
                ha_api_accessible=False,
                mqtt_connected=False
            )
    
    def _check_ha_api(self) -> bool:
        """Check if Home Assistant API is accessible"""
        try:
            # Try to access supervisor API
            supervisor_token = os.getenv('SUPERVISOR_TOKEN')
            if not supervisor_token:
                return False
            
            headers = {
                'Authorization': f'Bearer {supervisor_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                'http://supervisor/core/api/config',
                headers=headers,
                timeout=5
            )
            
            return response.status_code == 200
        except Exception:
            return False
    
    def _check_mqtt_connection(self) -> bool:
        """Check MQTT connection status (simplified)"""
        try:
            # This is a simplified check - in a real implementation,
            # you'd check the actual MQTT client status
            return True  # Placeholder
        except Exception:
            return False
    
    def perform_health_check(self) -> HealthCheck:
        """Perform comprehensive health check"""
        timestamp = datetime.now()
        issues = []
        recommendations = []
        
        # Get system and addon info
        system_info = self.get_system_info()
        addon_info = self.get_addon_info()
        
        # Check system health
        system_healthy = True
        
        # Memory check
        memory_usage = (system_info.memory_total - system_info.memory_available) / system_info.memory_total
        if memory_usage > 0.9:  # 90% memory usage
            system_healthy = False
            issues.append(f"High memory usage: {memory_usage:.1%}")
            recommendations.append("Consider reducing memory usage or increasing available memory")
        
        # Disk space check
        disk_usage = (system_info.disk_total - system_info.disk_free) / system_info.disk_total
        if disk_usage > 0.9:  # 90% disk usage
            system_healthy = False
            issues.append(f"Low disk space: {disk_usage:.1%} used")
            recommendations.append("Free up disk space or increase storage capacity")
        
        # CPU check
        if system_info.cpu_percent > 80:  # 80% CPU usage
            system_healthy = False
            issues.append(f"High CPU usage: {system_info.cpu_percent:.1f}%")
            recommendations.append("Check for high CPU processes or reduce system load")
        
        # Check addon health
        addon_healthy = True
        
        # Log size check
        if addon_info.total_log_size > 100 * 1024 * 1024:  # 100MB
            addon_healthy = False
            issues.append(f"Large log files: {addon_info.total_log_size / (1024*1024):.1f}MB")
            recommendations.append("Consider reducing log level or cleaning old logs")
        
        # API accessibility check
        api_accessible = addon_info.ha_api_accessible
        if not api_accessible:
            issues.append("Home Assistant API not accessible")
            recommendations.append("Check network connectivity and API permissions")
        
        # Logging health check
        logs_healthy = True
        try:
            log_stats = get_logging_stats()
            if log_stats.get('error_rate', 0) > 0.1:  # 10% error rate
                logs_healthy = False
                issues.append(f"High error rate in logs: {log_stats['error_rate']:.1%}")
                recommendations.append("Check recent error messages and resolve underlying issues")
        except Exception:
            logs_healthy = False
            issues.append("Unable to get logging statistics")
            recommendations.append("Check logging system configuration")
        
        # Overall status
        overall_healthy = system_healthy and addon_healthy and api_accessible and logs_healthy
        overall_status = "healthy" if overall_healthy else "unhealthy"
        
        return HealthCheck(
            timestamp=timestamp,
            overall_status=overall_status,
            system_healthy=system_healthy,
            addon_healthy=addon_healthy,
            api_accessible=api_accessible,
            logs_healthy=logs_healthy,
            issues=issues,
            recommendations=recommendations
        )
    
    def get_recent_logs(self, lines: int = 100) -> List[str]:
        """Get recent log entries"""
        try:
            main_log = self.log_directory / "aicleaner.log"
            if not main_log.exists():
                return ["No log file found"]
            
            # Use tail command if available, otherwise read file
            try:
                result = subprocess.run(
                    ['tail', '-n', str(lines), str(main_log)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.stdout.strip().split('\n') if result.stdout else []
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Fallback to reading file
                with open(main_log, 'r') as f:
                    all_lines = f.readlines()
                    return [line.strip() for line in all_lines[-lines:]]
        except Exception as e:
            return [f"Error reading logs: {e}"]
    
    def get_error_logs(self, hours: int = 24) -> List[str]:
        """Get recent error log entries"""
        try:
            main_log = self.log_directory / "aicleaner.log"
            if not main_log.exists():
                return ["No log file found"]
            
            error_lines = []
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with open(main_log, 'r') as f:
                for line in f:
                    if 'ERROR' in line or 'CRITICAL' in line:
                        # Simple time check (this could be improved)
                        try:
                            # Extract timestamp from log line
                            timestamp_str = line.split(' - ')[0]
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            if log_time >= cutoff_time:
                                error_lines.append(line.strip())
                        except (ValueError, IndexError):
                            # If timestamp parsing fails, include the line anyway
                            error_lines.append(line.strip())
            
            return error_lines[-100:]  # Return last 100 error entries
        except Exception as e:
            return [f"Error reading error logs: {e}"]
    
    def generate_diagnostic_report(self) -> Dict[str, Any]:
        """Generate comprehensive diagnostic report"""
        try:
            system_info = self.get_system_info()
            addon_info = self.get_addon_info()
            health_check = self.perform_health_check()
            recent_logs = self.get_recent_logs(50)
            error_logs = self.get_error_logs(24)
            log_stats = get_logging_stats()
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "system_info": asdict(system_info),
                "addon_info": asdict(addon_info),
                "health_check": asdict(health_check),
                "logging_stats": log_stats,
                "recent_logs": recent_logs,
                "error_logs": error_logs,
                "recommendations": health_check.recommendations
            }
            
            return report
        except Exception as e:
            self.logger.error(f"Error generating diagnostic report: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": f"Failed to generate report: {e}"
            }
    
    def save_diagnostic_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """Save diagnostic report to file"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"diagnostic_report_{timestamp}.json"
            
            report_path = self.addon_root / filename
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Diagnostic report saved to {report_path}")
            return str(report_path)
        except Exception as e:
            self.logger.error(f"Error saving diagnostic report: {e}")
            return ""
    
    def cleanup_old_logs(self, days: int = 7) -> int:
        """Clean up old log files"""
        try:
            if not self.log_directory.exists():
                return 0
            
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            removed_count = 0
            
            for log_file in self.log_directory.rglob("*.log*"):
                try:
                    if log_file.stat().st_mtime < cutoff_time:
                        log_file.unlink()
                        removed_count += 1
                except OSError:
                    continue
            
            self.logger.info(f"Cleaned up {removed_count} old log files")
            return removed_count
        except Exception as e:
            self.logger.error(f"Error cleaning up logs: {e}")
            return 0


# Convenience functions
def get_diagnostic_tool() -> DiagnosticTool:
    """Get diagnostic tool instance"""
    return DiagnosticTool()


def quick_health_check() -> HealthCheck:
    """Perform quick health check"""
    return get_diagnostic_tool().perform_health_check()


def generate_diagnostic_report() -> Dict[str, Any]:
    """Generate diagnostic report"""
    return get_diagnostic_tool().generate_diagnostic_report()


def save_diagnostic_report(filename: str = None) -> str:
    """Generate and save diagnostic report"""
    tool = get_diagnostic_tool()
    report = tool.generate_diagnostic_report()
    return tool.save_diagnostic_report(report, filename)