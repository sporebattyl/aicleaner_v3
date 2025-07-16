"""
Improved Performance Monitor
HA API integration for performance monitoring with proper patterns
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

class ImprovedPerformanceMonitor:
    """Improved performance monitor with proper HA integration."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the performance monitor."""
        self.hass = hass
        self._metrics: Dict[str, Any] = {}
        self._monitoring_active = False
        self._update_interval = timedelta(seconds=30)
        self._performance_history: List[Dict[str, Any]] = []
        self._max_history_size = 100
        self._cancel_monitoring = None
    
    async def async_start_monitoring(self) -> bool:
        """Start performance monitoring."""
        if self._monitoring_active:
            _LOGGER.warning("Performance monitoring already active")
            return True
            
        try:
            # Initialize metrics
            await self._initialize_metrics()
            
            # Start periodic monitoring
            self._cancel_monitoring = async_track_time_interval(
                self.hass,
                self._async_update_metrics,
                self._update_interval
            )
            
            self._monitoring_active = True
            _LOGGER.info("Performance monitoring started")
            
            # Fire startup event
            self.hass.bus.async_fire("aicleaner_v3_monitoring_started", {
                "interval": self._update_interval.total_seconds()
            })
            
            return True
            
        except Exception as e:
            _LOGGER.error(f"Failed to start performance monitoring: {e}")
            return False
    
    async def async_stop_monitoring(self):
        """Stop performance monitoring."""
        if not self._monitoring_active:
            return
            
        if self._cancel_monitoring:
            self._cancel_monitoring()
            self._cancel_monitoring = None
            
        self._monitoring_active = False
        _LOGGER.info("Performance monitoring stopped")
        
        # Fire stop event
        self.hass.bus.async_fire("aicleaner_v3_monitoring_stopped", {})
    
    async def _initialize_metrics(self):
        """Initialize performance metrics."""
        self._metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "network_latency": 0.0,
            "ha_api_response_time": 0.0,
            "entity_count": 0,
            "service_call_count": 0,
            "error_count": 0,
            "last_update": datetime.now().isoformat()
        }
        
        # Get initial system metrics
        await self._collect_system_metrics()
        await self._collect_ha_metrics()
    
    @callback
    async def _async_update_metrics(self, now: datetime):
        """Update performance metrics periodically."""
        try:
            start_time = time.time()
            
            # Collect system metrics
            await self._collect_system_metrics()
            
            # Collect HA-specific metrics
            await self._collect_ha_metrics()
            
            # Update collection time
            collection_time = (time.time() - start_time) * 1000
            self._metrics["collection_time_ms"] = collection_time
            self._metrics["last_update"] = now.isoformat()
            
            # Store in history
            self._store_metrics_history()
            
            # Update entities if available
            await self._update_performance_entities()
            
            # Fire metrics update event
            self.hass.bus.async_fire("aicleaner_v3_metrics_updated", {
                "metrics": self._metrics.copy(),
                "collection_time_ms": collection_time
            })
            
        except Exception as e:
            _LOGGER.error(f"Error updating performance metrics: {e}")
            self._metrics["error_count"] += 1
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics."""
        try:
            import psutil
            
            # CPU usage
            self._metrics["cpu_usage"] = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self._metrics["memory_usage"] = memory.percent
            self._metrics["memory_available_gb"] = memory.available / (1024**3)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self._metrics["disk_usage"] = (disk.used / disk.total) * 100
            self._metrics["disk_free_gb"] = disk.free / (1024**3)
            
        except ImportError:
            _LOGGER.warning("psutil not available, using basic metrics")
            # Fallback to basic metrics
            self._metrics["cpu_usage"] = 0.0
            self._metrics["memory_usage"] = 0.0
            self._metrics["disk_usage"] = 0.0
        except Exception as e:
            _LOGGER.error(f"Error collecting system metrics: {e}")
    
    async def _collect_ha_metrics(self):
        """Collect Home Assistant specific metrics."""
        try:
            # Entity count
            states = self.hass.states.async_all()
            self._metrics["entity_count"] = len(states)
            
            # Count entities by domain
            domain_counts = {}
            for state in states:
                domain = state.entity_id.split('.')[0]
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            self._metrics["entities_by_domain"] = domain_counts
            
            # HA API response time test
            start_time = time.time()
            await self._test_ha_api_response()
            self._metrics["ha_api_response_time"] = (time.time() - start_time) * 1000
            
            # Service call statistics
            # Note: This would require additional tracking in a real implementation
            self._metrics["service_call_count"] = getattr(self, '_service_calls', 0)
            
        except Exception as e:
            _LOGGER.error(f"Error collecting HA metrics: {e}")
    
    async def _test_ha_api_response(self):
        """Test HA API response time."""
        try:
            # Simple test: get current time
            current_time = dt_util.now()
            # This is a minimal test - in practice you might test actual API calls
            return current_time
        except Exception as e:
            _LOGGER.error(f"HA API test failed: {e}")
            return None
    
    def _store_metrics_history(self):
        """Store current metrics in history."""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "metrics": self._metrics.copy()
        }
        
        self._performance_history.append(history_entry)
        
        # Limit history size
        if len(self._performance_history) > self._max_history_size:
            self._performance_history.pop(0)
    
    async def _update_performance_entities(self):
        """Update performance-related entities."""
        try:
            # Update performance score entity
            performance_score = self._calculate_performance_score()
            
            # Fire entity update events
            self.hass.bus.async_fire("aicleaner_v3_entity_update", {
                "entity_id": "sensor.aicleaner_v3_performance_score",
                "state": performance_score,
                "attributes": {
                    "cpu_usage": self._metrics.get("cpu_usage", 0),
                    "memory_usage": self._metrics.get("memory_usage", 0),
                    "disk_usage": self._metrics.get("disk_usage", 0),
                    "api_response_time": self._metrics.get("ha_api_response_time", 0)
                }
            })
            
        except Exception as e:
            _LOGGER.error(f"Error updating performance entities: {e}")
    
    def _calculate_performance_score(self) -> int:
        """Calculate overall performance score (0-100)."""
        try:
            cpu = self._metrics.get("cpu_usage", 0)
            memory = self._metrics.get("memory_usage", 0)
            disk = self._metrics.get("disk_usage", 0)
            api_time = self._metrics.get("ha_api_response_time", 0)
            
            # Simple scoring algorithm
            cpu_score = max(0, 100 - cpu)
            memory_score = max(0, 100 - memory)
            disk_score = max(0, 100 - disk)
            api_score = max(0, 100 - min(api_time / 10, 100))  # 10ms = 90 points
            
            # Weighted average
            total_score = (cpu_score * 0.3 + memory_score * 0.3 + 
                          disk_score * 0.2 + api_score * 0.2)
            
            return int(total_score)
            
        except Exception as e:
            _LOGGER.error(f"Error calculating performance score: {e}")
            return 50  # Default score
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self._metrics.copy()
    
    def get_metrics_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get performance metrics history."""
        if limit:
            return self._performance_history[-limit:]
        return self._performance_history.copy()
    
    def is_monitoring_active(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring_active
