"""
Home Assistant Supervisor API Integration
Phase 5B: Resource Management

Integration with Home Assistant Supervisor API for advanced resource monitoring,
addon management, and system-level resource coordination.
"""

import asyncio
import logging
import aiohttp
import os
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class SupervisorInfo:
    """Home Assistant Supervisor information"""
    version: str
    version_latest: str
    update_available: bool
    channel: str
    arch: str
    supported_arch: List[str]
    healthy: bool
    supported: bool


@dataclass
class AddonInfo:
    """Addon information from Supervisor"""
    slug: str
    name: str
    description: str
    version: str
    version_latest: str
    update_available: bool
    state: str  # started, stopped, error
    boot: str   # auto, manual
    build: bool
    network: Optional[Dict[str, Any]]
    host_network: bool
    privileged: bool
    apparmor: str
    devices: List[str]
    auto_update: bool
    ingress: bool
    panel_icon: str
    panel_title: str
    panel_admin: bool
    options: Dict[str, Any]
    schema: Dict[str, Any]


@dataclass
class SystemStats:
    """System statistics from Supervisor"""
    cpu_percent: float
    memory_usage: int
    memory_limit: int
    memory_percent: float
    network_rx: int
    network_tx: int
    blk_read: int
    blk_write: int


class SupervisorAPIClient:
    """
    Home Assistant Supervisor API client for resource management integration.
    
    Features:
    - System resource monitoring via Supervisor API
    - Addon management and resource allocation
    - Host system information retrieval
    - Resource limit configuration
    - Integration with Home Assistant core systems
    """
    
    def __init__(self,
                 supervisor_token: Optional[str] = None,
                 base_url: str = "http://supervisor",
                 timeout: float = 30.0):
        """
        Initialize Supervisor API client.
        
        Args:
            supervisor_token: Supervisor API token (auto-detected if None)
            base_url: Supervisor API base URL
            timeout: Request timeout in seconds
        """
        self.supervisor_token = supervisor_token or self._get_supervisor_token()
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # API session
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Cache for system info
        self._system_info_cache: Optional[Dict[str, Any]] = None
        self._cache_expiry: Optional[datetime] = None
        self._cache_ttl = 60  # Cache TTL in seconds
        
        # Callbacks
        self._resource_callbacks: List[Callable] = []
        self._addon_callbacks: List[Callable] = []
        
        logger.info("Supervisor API client initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self) -> None:
        """Ensure HTTP session is available."""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.supervisor_token}",
                "Content-Type": "application/json"
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _get_supervisor_token(self) -> str:
        """Get Supervisor API token from environment."""
        # Try multiple possible sources for the token
        token_sources = [
            os.getenv("SUPERVISOR_TOKEN"),
            os.getenv("HASSIO_TOKEN"),
            "/run/secrets/hassio_token"
        ]
        
        for source in token_sources:
            if source:
                if os.path.isfile(source):
                    try:
                        with open(source, 'r') as f:
                            return f.read().strip()
                    except Exception as e:
                        logger.debug(f"Could not read token from {source}: {e}")
                else:
                    return source
        
        logger.warning("No Supervisor token found - API functionality will be limited")
        return ""
    
    async def _make_request(self, 
                           method: str,
                           endpoint: str,
                           **kwargs) -> Dict[str, Any]:
        """Make API request to Supervisor."""
        await self._ensure_session()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            async with self._session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("result") == "ok":
                        return data.get("data", {})
                    else:
                        raise aiohttp.ClientError(f"API error: {data.get('message', 'Unknown error')}")
                else:
                    error_text = await response.text()
                    raise aiohttp.ClientError(f"HTTP {response.status}: {error_text}")
        
        except aiohttp.ClientError:
            raise
        except Exception as e:
            raise aiohttp.ClientError(f"Request failed: {str(e)}")
    
    async def get_supervisor_info(self) -> SupervisorInfo:
        """Get Supervisor information."""
        data = await self._make_request("GET", "/supervisor/info")
        
        return SupervisorInfo(
            version=data.get("version", "unknown"),
            version_latest=data.get("version_latest", "unknown"),
            update_available=data.get("update_available", False),
            channel=data.get("channel", "unknown"),
            arch=data.get("arch", "unknown"),
            supported_arch=data.get("supported_arch", []),
            healthy=data.get("healthy", False),
            supported=data.get("supported", False)
        )
    
    async def get_addon_info(self, addon_slug: str = None) -> AddonInfo:
        """Get addon information."""
        # If no slug provided, try to detect current addon
        if addon_slug is None:
            addon_slug = os.getenv("ADDON_SLUG", "aicleaner_v3")
        
        data = await self._make_request("GET", f"/addons/{addon_slug}/info")
        
        return AddonInfo(
            slug=data.get("slug", addon_slug),
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            version=data.get("version", "unknown"),
            version_latest=data.get("version_latest", "unknown"),
            update_available=data.get("update_available", False),
            state=data.get("state", "unknown"),
            boot=data.get("boot", "manual"),
            build=data.get("build", False),
            network=data.get("network"),
            host_network=data.get("host_network", False),
            privileged=data.get("privileged", False),
            apparmor=data.get("apparmor", "disable"),
            devices=data.get("devices", []),
            auto_update=data.get("auto_update", False),
            ingress=data.get("ingress", False),
            panel_icon=data.get("panel_icon", ""),
            panel_title=data.get("panel_title", ""),
            panel_admin=data.get("panel_admin", False),
            options=data.get("options", {}),
            schema=data.get("schema", {})
        )
    
    async def get_addon_stats(self, addon_slug: str = None) -> SystemStats:
        """Get addon resource statistics."""
        if addon_slug is None:
            addon_slug = os.getenv("ADDON_SLUG", "aicleaner_v3")
        
        data = await self._make_request("GET", f"/addons/{addon_slug}/stats")
        
        return SystemStats(
            cpu_percent=data.get("cpu_percent", 0.0),
            memory_usage=data.get("memory_usage", 0),
            memory_limit=data.get("memory_limit", 0),
            memory_percent=data.get("memory_percent", 0.0),
            network_rx=data.get("network_rx", 0),
            network_tx=data.get("network_tx", 0),
            blk_read=data.get("blk_read", 0),
            blk_write=data.get("blk_write", 0)
        )
    
    async def get_host_info(self) -> Dict[str, Any]:
        """Get host system information."""
        # Use cache if available and not expired
        current_time = datetime.now()
        if (self._system_info_cache and 
            self._cache_expiry and 
            current_time < self._cache_expiry):
            return self._system_info_cache
        
        try:
            data = await self._make_request("GET", "/host/info")
            
            # Cache the result
            self._system_info_cache = data
            self._cache_expiry = current_time.replace(second=current_time.second + self._cache_ttl)
            
            return data
        
        except Exception as e:
            logger.warning(f"Could not get host info: {e}")
            return {}
    
    async def get_system_resources(self) -> Dict[str, Any]:
        """Get comprehensive system resource information."""
        try:
            # Get multiple resource sources
            host_info = await self.get_host_info()
            supervisor_info = await self.get_supervisor_info()
            
            try:
                addon_stats = await self.get_addon_stats()
                addon_info = await self.get_addon_info()
            except Exception as e:
                logger.debug(f"Could not get addon info: {e}")
                addon_stats = None
                addon_info = None
            
            # Compile comprehensive resource info
            resources = {
                "host": {
                    "hostname": host_info.get("hostname", "unknown"),
                    "operating_system": host_info.get("operating_system", "unknown"),
                    "kernel": host_info.get("kernel", "unknown"),
                    "architecture": host_info.get("architecture", "unknown"),
                    "virtualization": host_info.get("virtualization", "unknown"),
                    "deployment": host_info.get("deployment", "unknown"),
                    "disk_total": host_info.get("disk_total", 0),
                    "disk_used": host_info.get("disk_used", 0),
                    "disk_free": host_info.get("disk_free", 0)
                },
                "supervisor": {
                    "version": supervisor_info.version,
                    "healthy": supervisor_info.healthy,
                    "supported": supervisor_info.supported,
                    "arch": supervisor_info.arch,
                    "channel": supervisor_info.channel,
                    "update_available": supervisor_info.update_available
                },
                "addon": None,
                "timestamp": datetime.now().isoformat()
            }
            
            if addon_info and addon_stats:
                resources["addon"] = {
                    "name": addon_info.name,
                    "version": addon_info.version,
                    "state": addon_info.state,
                    "stats": {
                        "cpu_percent": addon_stats.cpu_percent,
                        "memory_usage_mb": addon_stats.memory_usage / (1024 * 1024),
                        "memory_limit_mb": addon_stats.memory_limit / (1024 * 1024),
                        "memory_percent": addon_stats.memory_percent,
                        "network_rx_mb": addon_stats.network_rx / (1024 * 1024),
                        "network_tx_mb": addon_stats.network_tx / (1024 * 1024),
                        "blk_read_mb": addon_stats.blk_read / (1024 * 1024),
                        "blk_write_mb": addon_stats.blk_write / (1024 * 1024)
                    }
                }
            
            return resources
        
        except Exception as e:
            logger.error(f"Error getting system resources: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def restart_addon(self, addon_slug: str = None) -> bool:
        """Restart addon via Supervisor API."""
        if addon_slug is None:
            addon_slug = os.getenv("ADDON_SLUG", "aicleaner_v3")
        
        try:
            await self._make_request("POST", f"/addons/{addon_slug}/restart")
            logger.info(f"Addon {addon_slug} restart requested")
            return True
        except Exception as e:
            logger.error(f"Failed to restart addon {addon_slug}: {e}")
            return False
    
    async def stop_addon(self, addon_slug: str = None) -> bool:
        """Stop addon via Supervisor API."""
        if addon_slug is None:
            addon_slug = os.getenv("ADDON_SLUG", "aicleaner_v3")
        
        try:
            await self._make_request("POST", f"/addons/{addon_slug}/stop")
            logger.info(f"Addon {addon_slug} stop requested")
            return True
        except Exception as e:
            logger.error(f"Failed to stop addon {addon_slug}: {e}")
            return False
    
    async def update_addon_options(self, 
                                  options: Dict[str, Any], 
                                  addon_slug: str = None) -> bool:
        """Update addon options via Supervisor API."""
        if addon_slug is None:
            addon_slug = os.getenv("ADDON_SLUG", "aicleaner_v3")
        
        try:
            payload = {"options": options}
            await self._make_request("POST", f"/addons/{addon_slug}/options", json=payload)
            logger.info(f"Addon {addon_slug} options updated")
            return True
        except Exception as e:
            logger.error(f"Failed to update addon options for {addon_slug}: {e}")
            return False
    
    async def get_addon_logs(self, 
                            addon_slug: str = None,
                            lines: int = 100) -> List[str]:
        """Get addon logs via Supervisor API."""
        if addon_slug is None:
            addon_slug = os.getenv("ADDON_SLUG", "aicleaner_v3")
        
        try:
            # Note: Logs endpoint typically returns plain text, not JSON
            url = f"{self.base_url}/addons/{addon_slug}/logs"
            
            await self._ensure_session()
            async with self._session.get(url) as response:
                if response.status == 200:
                    log_text = await response.text()
                    log_lines = log_text.strip().split('\n')
                    return log_lines[-lines:] if len(log_lines) > lines else log_lines
                else:
                    logger.error(f"Failed to get logs: HTTP {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Error getting addon logs: {e}")
            return []
    
    async def check_supervisor_health(self) -> Dict[str, Any]:
        """Check Supervisor and system health."""
        health_status = {
            "supervisor_healthy": False,
            "api_responsive": False,
            "addon_running": False,
            "host_accessible": False,
            "resource_pressure": False,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Test API responsiveness
            supervisor_info = await self.get_supervisor_info()
            health_status["api_responsive"] = True
            health_status["supervisor_healthy"] = supervisor_info.healthy
            
            # Check addon status
            try:
                addon_info = await self.get_addon_info()
                health_status["addon_running"] = addon_info.state == "started"
            except Exception:
                pass
            
            # Check host accessibility
            try:
                host_info = await self.get_host_info()
                health_status["host_accessible"] = bool(host_info)
            except Exception:
                pass
            
            # Check resource pressure
            try:
                addon_stats = await self.get_addon_stats()
                memory_pressure = addon_stats.memory_percent > 85
                cpu_pressure = addon_stats.cpu_percent > 80
                health_status["resource_pressure"] = memory_pressure or cpu_pressure
                
                health_status["resource_details"] = {
                    "memory_percent": addon_stats.memory_percent,
                    "cpu_percent": addon_stats.cpu_percent,
                    "memory_pressure": memory_pressure,
                    "cpu_pressure": cpu_pressure
                }
            except Exception:
                pass
        
        except Exception as e:
            health_status["error"] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health_status
    
    def register_resource_callback(self, callback: Callable) -> None:
        """Register callback for resource events."""
        self._resource_callbacks.append(callback)
    
    def register_addon_callback(self, callback: Callable) -> None:
        """Register callback for addon events."""
        self._addon_callbacks.append(callback)


class SupervisorResourceManager:
    """
    Resource manager that integrates with Home Assistant Supervisor.
    """
    
    def __init__(self, supervisor_client: SupervisorAPIClient):
        """
        Initialize Supervisor resource manager.
        
        Args:
            supervisor_client: Supervisor API client
        """
        self.supervisor_client = supervisor_client
        self._monitoring_enabled = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._resource_history: List[Dict[str, Any]] = []
        
    async def start_monitoring(self, interval: float = 60.0) -> None:
        """Start monitoring Supervisor resources."""
        if self._monitoring_enabled:
            logger.warning("Supervisor monitoring already enabled")
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
        self._monitoring_enabled = True
        
        logger.info("Supervisor resource monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring Supervisor resources."""
        if not self._monitoring_enabled:
            return
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        self._monitoring_enabled = False
        logger.info("Supervisor resource monitoring stopped")
    
    async def _monitoring_loop(self, interval: float) -> None:
        """Main monitoring loop."""
        while self._monitoring_enabled:
            try:
                # Get comprehensive resource information
                resources = await self.supervisor_client.get_system_resources()
                
                # Store in history
                self._resource_history.append(resources)
                
                # Keep only recent history
                if len(self._resource_history) > 100:
                    self._resource_history = self._resource_history[-100:]
                
                # Check for resource issues
                await self._check_resource_health(resources)
                
                await asyncio.sleep(interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Supervisor monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _check_resource_health(self, resources: Dict[str, Any]) -> None:
        """Check resource health and trigger callbacks."""
        if "addon" in resources and resources["addon"]:
            addon_stats = resources["addon"]["stats"]
            
            # Check memory pressure
            if addon_stats["memory_percent"] > 90:
                logger.warning(f"High memory usage: {addon_stats['memory_percent']:.1f}%")
            
            # Check CPU pressure
            if addon_stats["cpu_percent"] > 85:
                logger.warning(f"High CPU usage: {addon_stats['cpu_percent']:.1f}%")
    
    def get_resource_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get resource usage trends."""
        if not self._resource_history:
            return {"error": "No resource data available"}
        
        # Filter recent data
        cutoff_time = datetime.now().replace(hour=datetime.now().hour - hours)
        recent_data = []
        
        for entry in self._resource_history:
            try:
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if entry_time >= cutoff_time:
                    recent_data.append(entry)
            except (KeyError, ValueError):
                continue
        
        if not recent_data:
            return {"error": "Insufficient recent data"}
        
        # Calculate trends
        addon_data = [entry for entry in recent_data if entry.get("addon")]
        
        if not addon_data:
            return {"error": "No addon data available"}
        
        memory_values = [entry["addon"]["stats"]["memory_percent"] for entry in addon_data]
        cpu_values = [entry["addon"]["stats"]["cpu_percent"] for entry in addon_data]
        
        return {
            "time_period_hours": hours,
            "data_points": len(addon_data),
            "memory": {
                "current": memory_values[-1] if memory_values else 0,
                "average": sum(memory_values) / len(memory_values),
                "min": min(memory_values),
                "max": max(memory_values)
            },
            "cpu": {
                "current": cpu_values[-1] if cpu_values else 0,
                "average": sum(cpu_values) / len(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values)
            }
        }


# Global instances
_supervisor_client: Optional[SupervisorAPIClient] = None
_supervisor_resource_manager: Optional[SupervisorResourceManager] = None


def get_supervisor_client() -> SupervisorAPIClient:
    """Get global Supervisor API client instance."""
    global _supervisor_client
    
    if _supervisor_client is None:
        _supervisor_client = SupervisorAPIClient()
    
    return _supervisor_client


def get_supervisor_resource_manager() -> SupervisorResourceManager:
    """Get global Supervisor resource manager instance."""
    global _supervisor_resource_manager
    
    if _supervisor_resource_manager is None:
        client = get_supervisor_client()
        _supervisor_resource_manager = SupervisorResourceManager(client)
    
    return _supervisor_resource_manager


async def start_supervisor_monitoring(interval: float = 60.0) -> None:
    """Start Supervisor monitoring."""
    manager = get_supervisor_resource_manager()
    await manager.start_monitoring(interval)


async def stop_supervisor_monitoring() -> None:
    """Stop Supervisor monitoring."""
    global _supervisor_resource_manager, _supervisor_client
    
    if _supervisor_resource_manager:
        await _supervisor_resource_manager.stop_monitoring()
    
    if _supervisor_client:
        await _supervisor_client.close()


async def get_supervisor_system_resources() -> Dict[str, Any]:
    """Get Supervisor system resources."""
    client = get_supervisor_client()
    return await client.get_system_resources()


async def check_supervisor_health() -> Dict[str, Any]:
    """Check Supervisor health status."""
    client = get_supervisor_client()
    return await client.check_supervisor_health()