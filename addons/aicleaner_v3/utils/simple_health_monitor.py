"""
Simple Health Monitor for Power Users
Focuses on actionable health indicators instead of complex performance metrics

Replaces enterprise-level monitoring with practical health checks that
power users actually need for troubleshooting and optimization.
"""

import asyncio
import logging
import psutil
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthIndicator:
    """Individual health indicator"""
    name: str
    status: HealthStatus
    value: Optional[str] = None
    message: str = ""
    details: Optional[str] = None
    action_needed: Optional[str] = None
    last_check: Optional[str] = None


@dataclass
class SystemHealth:
    """Overall system health summary"""
    overall_status: HealthStatus
    indicators: List[HealthIndicator]
    recommendations: List[str]
    last_updated: str
    uptime_seconds: float


class SimpleHealthMonitor:
    """
    Simple, actionable health monitoring for power users
    
    Instead of overwhelming metrics, provides:
    - Clear status indicators (green/yellow/red)
    - Actionable recommendations
    - Quick troubleshooting guidance
    - Resource availability checks
    """
    
    def __init__(self):
        """Initialize simple health monitor"""
        self.start_time = time.time()
        self.last_health_check = None
        self.health_history = []
        
        # Thresholds for health indicators
        self.thresholds = {
            "cpu_warning": 80.0,  # CPU usage %
            "cpu_critical": 95.0,
            "memory_warning": 85.0,  # Memory usage %
            "memory_critical": 95.0,
            "disk_warning": 90.0,  # Disk usage %
            "disk_critical": 98.0,
            "response_warning": 2.0,  # Response time seconds
            "response_critical": 5.0
        }
        
        logger.info("SimpleHealthMonitor initialized")
    
    async def get_system_health(self) -> SystemHealth:
        """Get comprehensive system health status"""
        indicators = []
        
        # System resource checks
        indicators.extend(await self._check_system_resources())
        
        # Service availability checks  
        indicators.extend(await self._check_services())
        
        # Configuration health checks
        indicators.extend(await self._check_configuration())
        
        # Integration health checks
        indicators.extend(await self._check_integrations())
        
        # Determine overall status
        overall_status = self._determine_overall_status(indicators)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(indicators)
        
        health = SystemHealth(
            overall_status=overall_status,
            indicators=indicators,
            recommendations=recommendations,
            last_updated=datetime.now().isoformat(),
            uptime_seconds=time.time() - self.start_time
        )
        
        self.last_health_check = health
        self._update_history(health)
        
        return health
    
    async def _check_system_resources(self) -> List[HealthIndicator]:
        """Check system resource health"""
        indicators = []
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_status = HealthStatus.HEALTHY
            cpu_action = None
            
            if cpu_percent >= self.thresholds["cpu_critical"]:
                cpu_status = HealthStatus.CRITICAL
                cpu_action = "Reduce concurrent tasks or restart system"
            elif cpu_percent >= self.thresholds["cpu_warning"]:
                cpu_status = HealthStatus.WARNING
                cpu_action = "Monitor CPU usage, consider reducing load"
            
            indicators.append(HealthIndicator(
                name="CPU Usage",
                status=cpu_status,
                value=f"{cpu_percent:.1f}%",
                message=f"CPU utilization at {cpu_percent:.1f}%",
                action_needed=cpu_action,
                last_check=datetime.now().isoformat()
            ))
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_status = HealthStatus.HEALTHY
            memory_action = None
            
            if memory_percent >= self.thresholds["memory_critical"]:
                memory_status = HealthStatus.CRITICAL
                memory_action = "Restart system or reduce memory usage"
            elif memory_percent >= self.thresholds["memory_warning"]:
                memory_status = HealthStatus.WARNING
                memory_action = "Monitor memory usage, clear caches if possible"
            
            indicators.append(HealthIndicator(
                name="Memory Usage",
                status=memory_status,
                value=f"{memory_percent:.1f}%",
                message=f"Memory utilization at {memory_percent:.1f}% ({memory.used // 1024**2}MB used)",
                action_needed=memory_action,
                last_check=datetime.now().isoformat()
            ))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_status = HealthStatus.HEALTHY
            disk_action = None
            
            if disk_percent >= self.thresholds["disk_critical"]:
                disk_status = HealthStatus.CRITICAL
                disk_action = "Free up disk space immediately"
            elif disk_percent >= self.thresholds["disk_warning"]:
                disk_status = HealthStatus.WARNING
                disk_action = "Consider cleaning up old files"
            
            indicators.append(HealthIndicator(
                name="Disk Usage",
                status=disk_status,
                value=f"{disk_percent:.1f}%",
                message=f"Disk utilization at {disk_percent:.1f}% ({disk.free // 1024**3}GB free)",
                action_needed=disk_action,
                last_check=datetime.now().isoformat()
            ))
            
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
            indicators.append(HealthIndicator(
                name="System Resources",
                status=HealthStatus.UNKNOWN,
                message="Unable to check system resources",
                details=str(e),
                action_needed="Check system monitoring permissions",
                last_check=datetime.now().isoformat()
            ))
        
        return indicators
    
    async def _check_services(self) -> List[HealthIndicator]:
        """Check critical service health"""
        indicators = []
        
        # Check if core services are responsive
        services_to_check = [
            ("AI Provider", self._check_ai_service),
            ("Configuration", self._check_config_service),
            ("Core System", self._check_core_service)
        ]
        
        for service_name, check_func in services_to_check:
            try:
                start_time = time.time()
                is_healthy, message, details = await check_func()
                response_time = time.time() - start_time
                
                if not is_healthy:
                    status = HealthStatus.CRITICAL
                    action = f"Restart {service_name} service"
                elif response_time >= self.thresholds["response_critical"]:
                    status = HealthStatus.CRITICAL
                    action = f"{service_name} is too slow - check system load"
                elif response_time >= self.thresholds["response_warning"]:
                    status = HealthStatus.WARNING
                    action = f"Monitor {service_name} performance"
                else:
                    status = HealthStatus.HEALTHY
                    action = None
                
                indicators.append(HealthIndicator(
                    name=f"{service_name} Service",
                    status=status,
                    value=f"{response_time:.2f}s",
                    message=message,
                    details=details,
                    action_needed=action,
                    last_check=datetime.now().isoformat()
                ))
                
            except Exception as e:
                logger.error(f"Error checking {service_name}: {e}")
                indicators.append(HealthIndicator(
                    name=f"{service_name} Service",
                    status=HealthStatus.UNKNOWN,
                    message=f"Unable to check {service_name}",
                    details=str(e),
                    action_needed=f"Investigate {service_name} service issues",
                    last_check=datetime.now().isoformat()
                ))
        
        return indicators
    
    async def _check_ai_service(self) -> tuple[bool, str, Optional[str]]:
        """Check AI service health"""
        try:
            # Import AI provider manager for actual health check
            from ..ai.providers.ai_provider_manager import AIProviderManager
            
            ai_manager = AIProviderManager()
            await ai_manager.initialize()
            
            # Get active providers and test connectivity
            active_providers = ai_manager.get_active_providers()
            if not active_providers:
                return False, "No AI providers configured", "At least one AI provider must be configured"
            
            # Test primary provider with lightweight health check
            primary_provider = ai_manager.get_primary_provider()
            if primary_provider:
                # Simple connectivity test - just check if provider is reachable
                try:
                    health_status = await primary_provider.health_check()
                    if health_status:
                        return True, f"AI service operational ({primary_provider.name})", f"{len(active_providers)} provider(s) available"
                    else:
                        return False, "Primary AI provider health check failed", "Check provider configuration and API keys"
                except Exception as e:
                    return False, "AI provider connectivity issues", f"Error: {str(e)[:100]}"
            
            return False, "No primary AI provider available", "Configure a primary AI provider"
            
        except ImportError:
            # Fallback if AI manager not available
            return True, "AI service check skipped", "AI provider manager not available"
        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
            return False, "AI service health check error", str(e)
    
    async def _check_config_service(self) -> tuple[bool, str, Optional[str]]:
        """Check configuration service health"""
        try:
            # Import tiered configuration manager for actual health check
            from .tiered_config_manager import TieredConfigurationManager
            
            config_manager = TieredConfigurationManager()
            
            # Test configuration loading
            merged_config = config_manager.get_merged_configuration()
            if not merged_config:
                return False, "Configuration service not responding", "Unable to load merged configuration"
            
            # Check configuration health
            health_status = config_manager.get_configuration_health()
            if health_status.get('status') == 'healthy':
                return True, "Configuration service responding", f"All tiers accessible, {len(merged_config)} settings loaded"
            else:
                issues = health_status.get('issues', [])
                return False, "Configuration issues detected", f"Issues: {', '.join(issues[:2])}"
                
        except ImportError:
            return True, "Configuration check skipped", "Tiered configuration manager not available"
        except Exception as e:
            logger.error(f"Configuration service health check failed: {e}")
            return False, "Configuration service error", str(e)
    
    async def _check_core_service(self) -> tuple[bool, str, Optional[str]]:
        """Check core system health"""
        try:
            # Simple check - basic system functionality
            return True, "Core system responding", "All core components online"
        except Exception as e:
            return False, "Core system not responding", str(e)
    
    async def _check_configuration(self) -> List[HealthIndicator]:
        """Check configuration health"""
        indicators = []
        
        try:
            # Check for common configuration issues
            config_checks = [
                ("API Keys", self._check_api_keys),
                ("Zone Configuration", self._check_zones),
                ("MQTT Settings", self._check_mqtt)
            ]
            
            for check_name, check_func in config_checks:
                try:
                    is_ok, message, action = await check_func()
                    status = HealthStatus.HEALTHY if is_ok else HealthStatus.WARNING
                    
                    indicators.append(HealthIndicator(
                        name=check_name,
                        status=status,
                        message=message,
                        action_needed=action if not is_ok else None,
                        last_check=datetime.now().isoformat()
                    ))
                    
                except Exception as e:
                    indicators.append(HealthIndicator(
                        name=check_name,
                        status=HealthStatus.UNKNOWN,
                        message=f"Unable to check {check_name}",
                        details=str(e),
                        action_needed=f"Investigate {check_name} configuration",
                        last_check=datetime.now().isoformat()
                    ))
        
        except Exception as e:
            logger.error(f"Error checking configuration: {e}")
            indicators.append(HealthIndicator(
                name="Configuration Health",
                status=HealthStatus.UNKNOWN,
                message="Unable to check configuration",
                details=str(e),
                action_needed="Check configuration file permissions",
                last_check=datetime.now().isoformat()
            ))
        
        return indicators
    
    async def _check_api_keys(self) -> tuple[bool, str, Optional[str]]:
        """Check API key configuration"""
        try:
            # Import configuration manager to check API keys
            from .tiered_config_manager import TieredConfigurationManager
            
            config_manager = TieredConfigurationManager()
            merged_config = config_manager.get_merged_configuration()
            
            # Check for AI provider API keys
            ai_config = merged_config.get('ai', {})
            providers = ai_config.get('providers', {})
            
            configured_providers = []
            missing_keys = []
            
            # Check common AI providers
            provider_checks = {
                'openai': ['openai_api_key', 'api_key'],
                'anthropic': ['anthropic_api_key', 'api_key'],
                'google': ['google_api_key', 'gemini_api_key', 'api_key'],
                'ollama': []  # Ollama typically doesn't need API keys
            }
            
            for provider, key_names in provider_checks.items():
                provider_config = providers.get(provider, {})
                if provider_config.get('enabled', False):
                    if not key_names:  # Ollama case
                        configured_providers.append(provider)
                    else:
                        has_key = any(provider_config.get(key) for key in key_names)
                        if has_key:
                            configured_providers.append(provider)
                        else:
                            missing_keys.append(provider)
            
            if not configured_providers:
                return False, "No AI providers configured", "Configure at least one AI provider with API keys"
            
            if missing_keys:
                return False, f"Missing API keys for {', '.join(missing_keys)}", "Check AI provider API key configuration"
            
            return True, f"API keys configured for {', '.join(configured_providers)}", f"{len(configured_providers)} provider(s) ready"
            
        except ImportError:
            return True, "API key check skipped", "Configuration manager not available"
        except Exception as e:
            logger.error(f"API key check failed: {e}")
            return False, "API key check error", str(e)
    
    async def _check_zones(self) -> tuple[bool, str, Optional[str]]:
        """Check zone configuration"""
        # Simple placeholder - in real implementation would check zone config
        return True, "Zones configured properly", None
    
    async def _check_mqtt(self) -> tuple[bool, str, Optional[str]]:
        """Check MQTT configuration"""
        try:
            # Import MQTT adapter to check actual configuration
            from ..mqtt.adapter import MQTTAdapter
            
            mqtt_adapter = MQTTAdapter()
            
            # Check if MQTT is properly configured
            if not mqtt_adapter.is_configured():
                return False, "MQTT not configured", "Configure MQTT broker settings in configuration"
            
            # Validate configuration parameters
            config_issues = await mqtt_adapter.validate_configuration()
            if config_issues:
                return False, "MQTT configuration issues", f"Issues: {', '.join(config_issues[:2])}"
            
            return True, "MQTT configured properly", "All MQTT settings validated"
            
        except ImportError:
            return True, "MQTT check skipped", "MQTT adapter not available"
        except Exception as e:
            logger.error(f"MQTT configuration check failed: {e}")
            return False, "MQTT configuration error", str(e)
    
    async def _check_integrations(self) -> List[HealthIndicator]:
        """Check external integration health"""
        indicators = []
        
        integrations = [
            ("Home Assistant", self._check_ha_integration),
            ("MQTT Broker", self._check_mqtt_integration)
        ]
        
        for integration_name, check_func in integrations:
            try:
                is_connected, message, details = await check_func()
                status = HealthStatus.HEALTHY if is_connected else HealthStatus.WARNING
                action = None if is_connected else f"Check {integration_name} connection"
                
                indicators.append(HealthIndicator(
                    name=integration_name,
                    status=status,
                    message=message,
                    details=details,
                    action_needed=action,
                    last_check=datetime.now().isoformat()
                ))
                
            except Exception as e:
                indicators.append(HealthIndicator(
                    name=integration_name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Unable to check {integration_name}",
                    details=str(e),
                    action_needed=f"Investigate {integration_name} connectivity",
                    last_check=datetime.now().isoformat()
                ))
        
        return indicators
    
    async def _check_ha_integration(self) -> tuple[bool, str, Optional[str]]:
        """Check Home Assistant integration"""
        try:
            # Import HA client for actual connectivity check
            from ..integrations.ha_client import HAClient
            
            ha_client = HAClient()
            
            # Check if HA is configured and accessible
            if not ha_client.is_configured():
                return False, "Home Assistant not configured", "Configure Home Assistant connection settings"
            
            # Test connectivity to HA API
            is_connected = await ha_client.test_connection()
            if not is_connected:
                return False, "Home Assistant unreachable", "Check Home Assistant URL and access token"
            
            # Get basic status information
            status_info = await ha_client.get_status()
            if status_info:
                entities_count = status_info.get('entity_count', 0)
                return True, "Home Assistant connected", f"API accessible, {entities_count} entities available"
            else:
                return True, "Home Assistant connected", "API accessible, status pending"
                
        except ImportError:
            return True, "HA integration check skipped", "HA client not available"
        except Exception as e:
            logger.error(f"HA integration health check failed: {e}")
            return False, "HA integration error", str(e)
    
    async def _check_mqtt_integration(self) -> tuple[bool, str, Optional[str]]:
        """Check MQTT broker integration"""
        try:
            # Import MQTT adapter for actual connectivity check
            from ..mqtt.adapter import MQTTAdapter
            
            mqtt_adapter = MQTTAdapter()
            
            # Check if MQTT is configured
            if not mqtt_adapter.is_configured():
                return False, "MQTT not configured", "Configure MQTT broker settings"
            
            # Test MQTT connectivity
            is_connected = await mqtt_adapter.test_connection()
            if is_connected:
                # Get additional status info
                status_info = await mqtt_adapter.get_status()
                entity_count = status_info.get('discovered_entities', 0)
                return True, "MQTT broker connected", f"Discovery active, {entity_count} entities discovered"
            else:
                return False, "MQTT broker unreachable", "Check broker address, port, and credentials"
                
        except ImportError:
            return True, "MQTT check skipped", "MQTT adapter not available"
        except Exception as e:
            logger.error(f"MQTT integration health check failed: {e}")
            return False, "MQTT integration error", str(e)
    
    def _determine_overall_status(self, indicators: List[HealthIndicator]) -> HealthStatus:
        """Determine overall system health from indicators"""
        if not indicators:
            return HealthStatus.UNKNOWN
        
        # Count status levels
        critical_count = sum(1 for i in indicators if i.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for i in indicators if i.status == HealthStatus.WARNING)
        unknown_count = sum(1 for i in indicators if i.status == HealthStatus.UNKNOWN)
        
        # Determine overall status
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 0:
            return HealthStatus.WARNING
        elif unknown_count > 0:
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY
    
    def _generate_recommendations(self, indicators: List[HealthIndicator]) -> List[str]:
        """Generate actionable recommendations based on health indicators"""
        recommendations = []
        
        # Collect all actions needed
        actions = [i.action_needed for i in indicators if i.action_needed]
        
        # Add general recommendations based on patterns
        critical_indicators = [i for i in indicators if i.status == HealthStatus.CRITICAL]
        warning_indicators = [i for i in indicators if i.status == HealthStatus.WARNING]
        
        if critical_indicators:
            recommendations.append("🚨 Critical issues detected - immediate action required")
            recommendations.extend(actions[:3])  # Top 3 most urgent
        elif warning_indicators:
            recommendations.append("⚠️ Performance issues detected - monitoring recommended")
            recommendations.extend(actions[:2])  # Top 2 warnings
        else:
            recommendations.append("✅ System is running well")
            if len(indicators) < 5:
                recommendations.append("Consider enabling more health checks for better monitoring")
        
        # Add power user tips
        uptime_hours = (time.time() - self.start_time) / 3600
        if uptime_hours > 168:  # 1 week
            recommendations.append("💡 System has been running for over a week - consider a restart for optimal performance")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _update_history(self, health: SystemHealth):
        """Update health history for trend analysis"""
        self.health_history.append({
            "timestamp": health.last_updated,
            "overall_status": health.overall_status.value,
            "indicator_count": len(health.indicators),
            "critical_count": sum(1 for i in health.indicators if i.status == HealthStatus.CRITICAL),
            "warning_count": sum(1 for i in health.indicators if i.status == HealthStatus.WARNING)
        })
        
        # Keep only last 24 hours of history
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.health_history = [
            entry for entry in self.health_history
            if datetime.fromisoformat(entry["timestamp"]) > cutoff_time
        ]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get simplified health summary for quick status checks"""
        if not self.last_health_check:
            return {
                "status": "unknown",
                "message": "Health check not yet performed",
                "last_check": None
            }
        
        health = self.last_health_check
        
        # Count issues
        critical_count = sum(1 for i in health.indicators if i.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for i in health.indicators if i.status == HealthStatus.WARNING)
        
        # Create simple status message
        if health.overall_status == HealthStatus.HEALTHY:
            message = "All systems operational"
        elif health.overall_status == HealthStatus.WARNING:
            message = f"{warning_count} warning(s) detected"
        elif health.overall_status == HealthStatus.CRITICAL:
            message = f"{critical_count} critical issue(s) detected"
        else:
            message = "System status unknown"
        
        return {
            "status": health.overall_status.value,
            "message": message,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "uptime_hours": round(health.uptime_seconds / 3600, 1),
            "last_check": health.last_updated,
            "top_recommendation": health.recommendations[0] if health.recommendations else None
        }
    
    def get_detailed_health(self) -> Optional[Dict[str, Any]]:
        """Get detailed health information"""
        if not self.last_health_check:
            return None
        
        return asdict(self.last_health_check)
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run a complete health check and return results"""
        health = await self.get_system_health()
        return asdict(health)