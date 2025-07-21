"""
Network I/O Management System
Phase 5B: Resource Management

Advanced network monitoring, connection pooling, and bandwidth management
for optimal Home Assistant integration and AI provider communication.
"""

import asyncio
import logging
import time
import psutil
import aiohttp
from typing import Dict, Any, List, Optional, Callable, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import socket
import ssl

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Network connection states"""
    ESTABLISHED = "established"
    LISTENING = "listening"
    TIME_WAIT = "time_wait"
    CLOSE_WAIT = "close_wait"
    SYN_SENT = "syn_sent"
    SYN_RECV = "syn_recv"


@dataclass
class NetworkStats:
    """Network usage statistics"""
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errin: int
    errout: int
    dropin: int
    dropout: int
    connection_count: int
    active_connections: List[Dict[str, Any]]
    bandwidth_utilization: float  # Percentage
    latency_ms: float = 0.0


@dataclass
class ConnectionPoolStats:
    """Connection pool statistics"""
    pool_size: int
    active_connections: int
    idle_connections: int
    total_requests: int
    failed_requests: int
    average_response_time: float
    connection_reuse_rate: float


class NetworkManager:
    """
    Advanced network I/O management system.
    
    Features:
    - Real-time network monitoring
    - Connection pooling and reuse
    - Bandwidth monitoring and throttling
    - Network latency tracking
    - Connection health monitoring
    - AI provider connection optimization
    - Home Assistant network integration
    """
    
    def __init__(self,
                 max_connections: int = 100,
                 connection_timeout: float = 30.0,
                 read_timeout: float = 60.0,
                 max_bandwidth_mbps: Optional[float] = None,
                 monitoring_interval: float = 15.0):
        """
        Initialize network manager.
        
        Args:
            max_connections: Maximum concurrent connections
            connection_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            max_bandwidth_mbps: Maximum bandwidth in Mbps (None for unlimited)
            monitoring_interval: Network monitoring interval in seconds
        """
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.read_timeout = read_timeout
        self.max_bandwidth_mbps = max_bandwidth_mbps
        self.monitoring_interval = monitoring_interval
        
        # Network monitoring
        self._monitoring_enabled = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Network statistics
        self._stats_history: deque = deque(maxlen=200)
        self._current_stats: Optional[NetworkStats] = None
        self._baseline_stats: Optional[NetworkStats] = None
        
        # Connection management
        self._connection_pools: Dict[str, aiohttp.ClientSession] = {}
        self._pool_stats: Dict[str, ConnectionPoolStats] = {}
        self._active_requests: Dict[str, datetime] = {}
        
        # Performance tracking
        self._request_history: deque = deque(maxlen=1000)
        self._latency_samples: deque = deque(maxlen=100)
        self._bandwidth_samples: deque = deque(maxlen=50)
        
        # Throttling and limits
        self._request_semaphore = asyncio.Semaphore(max_connections)
        self._bandwidth_limiter: Optional[asyncio.Semaphore] = None
        self._rate_limits: Dict[str, Tuple[int, datetime]] = {}  # host -> (count, window_start)
        
        # Callbacks
        self._connection_callbacks: List[Callable] = []
        self._performance_callbacks: List[Callable] = []
        
        # SSL context for secure connections
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = True
        self._ssl_context.verify_mode = ssl.CERT_REQUIRED  # Production security
        
        logger.info(f"Network manager initialized (max connections: {max_connections})")
    
    async def start_monitoring(self) -> None:
        """Start network monitoring."""
        if self._monitoring_enabled:
            logger.warning("Network monitoring already enabled")
            return
        
        try:
            # Initialize connection pools
            await self._initialize_connection_pools()
            
            # Take baseline measurement
            self._baseline_stats = await self._get_network_stats()
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._monitoring_enabled = True
            
            logger.info("Network monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start network monitoring: {e}")
            raise
    
    async def stop_monitoring(self) -> None:
        """Stop network monitoring."""
        if not self._monitoring_enabled:
            return
        
        try:
            # Stop monitoring task
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
                self._monitoring_task = None
            
            # Close connection pools
            await self._cleanup_connection_pools()
            
            self._monitoring_enabled = False
            
            logger.info("Network monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping network monitoring: {e}")
    
    async def get_optimized_session(self, host: str) -> aiohttp.ClientSession:
        """Get optimized connection session for a host."""
        if host not in self._connection_pools:
            await self._create_connection_pool(host)
        
        return self._connection_pools[host]
    
    async def make_request(self, 
                          method: str,
                          url: str,
                          **kwargs) -> aiohttp.ClientResponse:
        """Make optimized HTTP request with monitoring."""
        host = self._extract_host(url)
        request_id = f"{method}_{url}_{int(time.time())}"
        
        # Apply rate limiting
        if not await self._check_rate_limit(host):
            raise aiohttp.ClientError(f"Rate limit exceeded for {host}")
        
        # Acquire connection semaphore
        async with self._request_semaphore:
            start_time = time.perf_counter()
            
            try:
                # Get optimized session
                session = await self.get_optimized_session(host)
                
                # Track active request
                self._active_requests[request_id] = datetime.now()
                
                # Make request with timeout
                timeout = aiohttp.ClientTimeout(
                    total=kwargs.get('timeout', self.read_timeout),
                    connect=self.connection_timeout
                )
                
                async with session.request(method, url, timeout=timeout, **kwargs) as response:
                    # Record performance metrics
                    response_time = time.perf_counter() - start_time
                    self._record_request_performance(host, response_time, True)
                    
                    return response
            
            except Exception as e:
                # Record failed request
                response_time = time.perf_counter() - start_time
                self._record_request_performance(host, response_time, False)
                raise
            
            finally:
                # Clean up tracking
                self._active_requests.pop(request_id, None)
    
    async def check_connectivity(self, hosts: List[str]) -> Dict[str, Dict[str, Any]]:
        """Check connectivity to multiple hosts."""
        connectivity_results = {}
        
        for host in hosts:
            try:
                start_time = time.perf_counter()
                
                # Parse host and port
                if ':' in host:
                    hostname, port = host.rsplit(':', 1)
                    port = int(port)
                else:
                    hostname = host
                    port = 443  # Default HTTPS port
                
                # Test TCP connection
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(hostname, port),
                        timeout=5.0
                    )
                    writer.close()
                    await writer.wait_closed()
                    tcp_reachable = True
                except:
                    tcp_reachable = False
                
                # Test HTTP request
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://{host}",
                            timeout=aiohttp.ClientTimeout(total=5.0)
                        ) as response:
                            http_reachable = response.status < 500
                except:
                    http_reachable = False
                
                latency = (time.perf_counter() - start_time) * 1000
                
                connectivity_results[host] = {
                    "tcp_reachable": tcp_reachable,
                    "http_reachable": http_reachable,
                    "latency_ms": latency,
                    "status": "healthy" if tcp_reachable and http_reachable else "degraded"
                }
                
            except Exception as e:
                connectivity_results[host] = {
                    "tcp_reachable": False,
                    "http_reachable": False,
                    "latency_ms": -1,
                    "status": "unreachable",
                    "error": str(e)
                }
        
        return connectivity_results
    
    async def _get_network_stats(self) -> NetworkStats:
        """Get current network statistics."""
        try:
            # Get network I/O statistics
            net_io = psutil.net_io_counters()
            
            # Get connection statistics
            connections = psutil.net_connections()
            active_connections = []
            connection_count = len(connections)
            
            for conn in connections[:20]:  # Limit to first 20 for performance
                try:
                    conn_info = {
                        "family": conn.family.name if hasattr(conn.family, 'name') else str(conn.family),
                        "type": conn.type.name if hasattr(conn.type, 'name') else str(conn.type),
                        "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "unknown",
                        "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "unknown",
                        "status": conn.status,
                        "pid": conn.pid
                    }
                    active_connections.append(conn_info)
                except (AttributeError, TypeError):
                    continue
            
            # Calculate bandwidth utilization (simplified)
            bandwidth_utilization = 0.0
            if self._baseline_stats and self.max_bandwidth_mbps:
                bytes_delta = (net_io.bytes_sent + net_io.bytes_recv) - \
                             (self._baseline_stats.bytes_sent + self._baseline_stats.bytes_recv)
                
                # Estimate current bandwidth usage
                if hasattr(self, '_last_stats_time'):
                    time_delta = time.time() - self._last_stats_time
                    if time_delta > 0:
                        current_bps = bytes_delta / time_delta
                        current_mbps = (current_bps * 8) / (1024 * 1024)
                        bandwidth_utilization = min((current_mbps / self.max_bandwidth_mbps) * 100, 100)
            
            # Calculate average latency
            avg_latency = 0.0
            if self._latency_samples:
                avg_latency = sum(self._latency_samples) / len(self._latency_samples)
            
            self._last_stats_time = time.time()
            
            return NetworkStats(
                bytes_sent=net_io.bytes_sent,
                bytes_recv=net_io.bytes_recv,
                packets_sent=net_io.packets_sent,
                packets_recv=net_io.packets_recv,
                errin=net_io.errin,
                errout=net_io.errout,
                dropin=net_io.dropin,
                dropout=net_io.dropout,
                connection_count=connection_count,
                active_connections=active_connections,
                bandwidth_utilization=bandwidth_utilization,
                latency_ms=avg_latency
            )
            
        except Exception as e:
            logger.error(f"Error getting network stats: {e}")
            return NetworkStats(0, 0, 0, 0, 0, 0, 0, 0, 0, [], 0.0, 0.0)
    
    def _extract_host(self, url: str) -> str:
        """Extract host from URL."""
        try:
            if url.startswith('http://'):
                url = url[7:]
            elif url.startswith('https://'):
                url = url[8:]
            
            host = url.split('/')[0]
            return host.split(':')[0]  # Remove port if present
        except:
            return "unknown"
    
    async def _check_rate_limit(self, host: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        """Check if request is within rate limit."""
        current_time = datetime.now()
        
        if host in self._rate_limits:
            count, window_start = self._rate_limits[host]
            
            # Reset window if expired
            if (current_time - window_start).total_seconds() >= window_seconds:
                self._rate_limits[host] = (1, current_time)
                return True
            
            # Check if within limit
            if count >= max_requests:
                return False
            
            # Increment counter
            self._rate_limits[host] = (count + 1, window_start)
        else:
            # First request for this host
            self._rate_limits[host] = (1, current_time)
        
        return True
    
    def _record_request_performance(self, host: str, response_time: float, success: bool) -> None:
        """Record request performance metrics."""
        request_data = {
            "host": host,
            "response_time": response_time,
            "success": success,
            "timestamp": datetime.now()
        }
        
        self._request_history.append(request_data)
        
        # Update latency samples (only for successful requests)
        if success:
            self._latency_samples.append(response_time * 1000)  # Convert to ms
        
        # Update pool statistics
        if host in self._pool_stats:
            stats = self._pool_stats[host]
            stats.total_requests += 1
            if not success:
                stats.failed_requests += 1
            
            # Update average response time
            if stats.total_requests > 1:
                stats.average_response_time = (
                    (stats.average_response_time * (stats.total_requests - 1) + response_time) /
                    stats.total_requests
                )
            else:
                stats.average_response_time = response_time
    
    async def _initialize_connection_pools(self) -> None:
        """Initialize optimized connection pools."""
        # Common hosts that AICleaner connects to
        common_hosts = [
            "api.openai.com",
            "generativelanguage.googleapis.com",
            "api.anthropic.com",
            "localhost"  # Home Assistant
        ]
        
        for host in common_hosts:
            await self._create_connection_pool(host)
    
    async def _create_connection_pool(self, host: str) -> None:
        """Create optimized connection pool for a host."""
        try:
            # Configure connector with optimizations
            connector = aiohttp.TCPConnector(
                limit=20,  # Maximum connections per host
                limit_per_host=10,  # Maximum connections per individual host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
                ssl=self._ssl_context
            )
            
            # Create session with optimizations
            timeout = aiohttp.ClientTimeout(
                total=self.read_timeout,
                connect=self.connection_timeout
            )
            
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "User-Agent": "AICleaner/3.0",
                    "Connection": "keep-alive"
                }
            )
            
            self._connection_pools[host] = session
            
            # Initialize pool statistics
            self._pool_stats[host] = ConnectionPoolStats(
                pool_size=20,
                active_connections=0,
                idle_connections=0,
                total_requests=0,
                failed_requests=0,
                average_response_time=0.0,
                connection_reuse_rate=0.0
            )
            
            logger.debug(f"Created connection pool for {host}")
            
        except Exception as e:
            logger.error(f"Error creating connection pool for {host}: {e}")
    
    async def _cleanup_connection_pools(self) -> None:
        """Clean up connection pools."""
        for host, session in self._connection_pools.items():
            try:
                await session.close()
                logger.debug(f"Closed connection pool for {host}")
            except Exception as e:
                logger.error(f"Error closing connection pool for {host}: {e}")
        
        self._connection_pools.clear()
        self._pool_stats.clear()
    
    def register_connection_callback(self, callback: Callable) -> None:
        """Register callback for connection events."""
        self._connection_callbacks.append(callback)
    
    def register_performance_callback(self, callback: Callable) -> None:
        """Register callback for performance events."""
        self._performance_callbacks.append(callback)
    
    async def _monitoring_loop(self) -> None:
        """Main network monitoring loop."""
        while self._monitoring_enabled:
            try:
                # Get current network stats
                stats = await self._get_network_stats()
                self._current_stats = stats
                
                # Store in history
                self._stats_history.append({
                    "timestamp": datetime.now(),
                    "stats": stats
                })
                
                # Update pool statistics
                await self._update_pool_statistics()
                
                # Check for performance issues
                await self._check_network_performance()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in network monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _update_pool_statistics(self) -> None:
        """Update connection pool statistics."""
        for host, session in self._connection_pools.items():
            try:
                if host in self._pool_stats:
                    stats = self._pool_stats[host]
                    
                    # Get connector info if available
                    if hasattr(session, '_connector') and session._connector:
                        connector = session._connector
                        if hasattr(connector, '_conns'):
                            # Update connection counts
                            total_conns = sum(len(conns) for conns in connector._conns.values())
                            stats.active_connections = total_conns
                            stats.idle_connections = stats.pool_size - total_conns
                            
                            # Calculate connection reuse rate
                            if stats.total_requests > 0:
                                stats.connection_reuse_rate = (
                                    max(0, stats.total_requests - total_conns) / stats.total_requests
                                ) * 100
            
            except Exception as e:
                logger.debug(f"Error updating pool stats for {host}: {e}")
    
    async def _check_network_performance(self) -> None:
        """Check network performance and trigger callbacks."""
        if not self._current_stats:
            return
        
        try:
            # Check for high latency
            if self._current_stats.latency_ms > 1000:  # 1 second
                for callback in self._performance_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback("high_latency", self._current_stats)
                        else:
                            callback("high_latency", self._current_stats)
                    except Exception as e:
                        logger.error(f"Error in performance callback: {e}")
            
            # Check for high error rate
            recent_requests = [r for r in self._request_history 
                             if (datetime.now() - r["timestamp"]).total_seconds() < 300]  # Last 5 minutes
            
            if recent_requests:
                failed_requests = [r for r in recent_requests if not r["success"]]
                error_rate = (len(failed_requests) / len(recent_requests)) * 100
                
                if error_rate > 10:  # 10% error rate
                    for callback in self._performance_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback("high_error_rate", {"error_rate": error_rate})
                            else:
                                callback("high_error_rate", {"error_rate": error_rate})
                        except Exception as e:
                            logger.error(f"Error in performance callback: {e}")
        
        except Exception as e:
            logger.error(f"Error checking network performance: {e}")
    
    def get_network_report(self) -> Dict[str, Any]:
        """Get comprehensive network report."""
        stats = self._current_stats
        
        if not stats:
            return {"error": "No network data available"}
        
        # Calculate performance metrics
        recent_requests = [r for r in self._request_history 
                          if (datetime.now() - r["timestamp"]).total_seconds() < 3600]  # Last hour
        
        performance_metrics = {
            "total_requests": len(recent_requests),
            "successful_requests": len([r for r in recent_requests if r["success"]]),
            "failed_requests": len([r for r in recent_requests if not r["success"]]),
            "error_rate": 0.0,
            "average_latency": 0.0
        }
        
        if recent_requests:
            performance_metrics["error_rate"] = (
                performance_metrics["failed_requests"] / len(recent_requests)
            ) * 100
            
            successful_requests = [r for r in recent_requests if r["success"]]
            if successful_requests:
                performance_metrics["average_latency"] = (
                    sum(r["response_time"] for r in successful_requests) / 
                    len(successful_requests)
                ) * 1000  # Convert to ms
        
        return {
            "current_stats": {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "connection_count": stats.connection_count,
                "bandwidth_utilization": stats.bandwidth_utilization,
                "latency_ms": stats.latency_ms,
                "error_count": stats.errin + stats.errout,
                "drop_count": stats.dropin + stats.dropout
            },
            "performance_metrics": performance_metrics,
            "connection_pools": {
                host: {
                    "pool_size": pool_stats.pool_size,
                    "active_connections": pool_stats.active_connections,
                    "total_requests": pool_stats.total_requests,
                    "failed_requests": pool_stats.failed_requests,
                    "average_response_time": pool_stats.average_response_time,
                    "connection_reuse_rate": pool_stats.connection_reuse_rate
                }
                for host, pool_stats in self._pool_stats.items()
            },
            "monitoring_config": {
                "monitoring_enabled": self._monitoring_enabled,
                "max_connections": self.max_connections,
                "connection_timeout": self.connection_timeout,
                "read_timeout": self.read_timeout,
                "max_bandwidth_mbps": self.max_bandwidth_mbps
            }
        }


# Global network manager instance
_network_manager: Optional[NetworkManager] = None


def get_network_manager(
    max_connections: int = 100,
    connection_timeout: float = 30.0,
    read_timeout: float = 60.0
) -> NetworkManager:
    """
    Get global network manager instance.
    
    Args:
        max_connections: Maximum concurrent connections
        connection_timeout: Connection timeout in seconds
        read_timeout: Read timeout in seconds
        
    Returns:
        NetworkManager instance
    """
    global _network_manager
    
    if _network_manager is None:
        _network_manager = NetworkManager(
            max_connections=max_connections,
            connection_timeout=connection_timeout,
            read_timeout=read_timeout
        )
    
    return _network_manager


async def start_network_monitoring() -> None:
    """Start global network monitoring."""
    manager = get_network_manager()
    await manager.start_monitoring()


async def stop_network_monitoring() -> None:
    """Stop global network monitoring."""
    global _network_manager
    if _network_manager:
        await _network_manager.stop_monitoring()


async def get_optimized_session(host: str) -> aiohttp.ClientSession:
    """Get optimized connection session for a host."""
    manager = get_network_manager()
    return await manager.get_optimized_session(host)


async def make_optimized_request(method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
    """Make optimized HTTP request with monitoring."""
    manager = get_network_manager()
    return await manager.make_request(method, url, **kwargs)


async def check_network_connectivity(hosts: List[str]) -> Dict[str, Dict[str, Any]]:
    """Check connectivity to multiple hosts."""
    manager = get_network_manager()
    return await manager.check_connectivity(hosts)