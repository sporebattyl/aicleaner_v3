"""
Metrics Manager for AICleaner v3 Core Service
Handles background persistence of performance metrics with power-user features
"""

import json
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class ProviderMetrics:
    """Detailed metrics for a specific AI provider"""
    requests: int = 0
    cost_usd: float = 0.0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    avg_response_time_ms: float = 0.0
    error_count: int = 0
    model_usage: Dict[str, int] = field(default_factory=dict)  # model_name -> request_count


@dataclass
class MetricsSnapshot:
    """Single metrics snapshot with comprehensive data"""
    timestamp: str
    uptime_seconds: float
    # Incremental values for this snapshot period
    period_requests: int  # New requests since last snapshot
    period_errors: int    # New errors since last snapshot
    total_requests: int   # Cumulative total (for reference)
    total_errors: int     # Cumulative total (for reference)
    requests_per_minute: float
    average_response_time_ms: float
    error_rate: float
    providers: Dict[str, ProviderMetrics] = field(default_factory=dict)
    total_cost_usd: float = 0.0


@dataclass
class HourlyRollup:
    """Hourly aggregated metrics for efficient historical analysis"""
    hour_timestamp: str  # ISO format truncated to hour
    total_requests: int = 0
    total_errors: int = 0
    total_cost_usd: float = 0.0
    avg_response_time_ms: float = 0.0
    providers: Dict[str, ProviderMetrics] = field(default_factory=dict)


class MetricsManager:
    """
    Background metrics persistence manager for power users.
    Features: Real-time snapshots, hourly rollups, efficient storage, atomic writes.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        performance_config = config.get('performance', {})
        
        # Configuration
        self.metrics_file = Path(performance_config.get('metrics_file', '/data/metrics.json'))
        self.flush_interval = performance_config.get('metrics_flush_interval', 60)
        self.retention_days = performance_config.get('metrics_retention_days', 30)
        self.rollup_enabled = performance_config.get('metrics_rollup_enabled', True)
        
        # In-memory storage
        self.snapshots: List[MetricsSnapshot] = []
        self.hourly_rollups: List[HourlyRollup] = []
        self.lock = Lock()
        self.running = False
        self.background_task = None
        
        # Track previous cumulative totals for delta calculation
        self.last_cumulative_requests = 0
        self.last_cumulative_errors = 0
        self.last_rollup_snapshot_index = 0
        
        # Ensure metrics directory exists
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing metrics
        self._load_existing_metrics()
    
    def _load_existing_metrics(self):
        """Load existing metrics from file"""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                
                # Load snapshots
                for item in data.get('snapshots', []):
                    # Convert provider metrics to ProviderMetrics objects
                    providers = {}
                    for provider_name, provider_data in item.get('providers', {}).items():
                        if isinstance(provider_data, dict):
                            providers[provider_name] = ProviderMetrics(**provider_data)
                        else:
                            # Legacy format compatibility
                            providers[provider_name] = ProviderMetrics()
                    
                    item['providers'] = providers
                    
                    # Handle legacy snapshots without period_ fields
                    if 'period_requests' not in item:
                        item['period_requests'] = 0
                    if 'period_errors' not in item:
                        item['period_errors'] = 0
                    
                    snapshot = MetricsSnapshot(**item)
                    self.snapshots.append(snapshot)
                
                # Update tracking based on loaded data
                if self.snapshots:
                    latest = self.snapshots[-1]
                    self.last_cumulative_requests = latest.total_requests
                    self.last_cumulative_errors = latest.total_errors
                    self.last_rollup_snapshot_index = len(self.snapshots)
                
                # Load rollups
                for item in data.get('hourly_rollups', []):
                    providers = {}
                    for provider_name, provider_data in item.get('providers', {}).items():
                        if isinstance(provider_data, dict):
                            providers[provider_name] = ProviderMetrics(**provider_data)
                    
                    item['providers'] = providers
                    rollup = HourlyRollup(**item)
                    self.hourly_rollups.append(rollup)
                
                logger.info(f"Loaded {len(self.snapshots)} snapshots and {len(self.hourly_rollups)} rollups")
                
        except Exception as e:
            logger.warning(f"Failed to load existing metrics: {e}")
            self.snapshots = []
            self.hourly_rollups = []
    
    def add_snapshot(self, service_metrics: Dict[str, Any], ai_responses: List[Any] = None):
        """
        Add a new metrics snapshot from service data and AI responses.
        
        Args:
            service_metrics: Current service metrics dict
            ai_responses: Recent AI responses for detailed provider metrics
        """
        # Calculate incremental values
        current_total_requests = service_metrics.get('total_requests', 0)
        current_total_errors = service_metrics.get('total_errors', 0)
        
        period_requests = current_total_requests - self.last_cumulative_requests
        period_errors = current_total_errors - self.last_cumulative_errors
        
        # Update tracking
        self.last_cumulative_requests = current_total_requests
        self.last_cumulative_errors = current_total_errors
        
        # Calculate provider metrics from AI responses
        providers = {}
        total_cost = 0.0
        
        # Process detailed provider metrics if available
        if ai_responses:
            provider_data = {}
            
            for response in ai_responses:
                provider_name = response.provider
                if provider_name not in provider_data:
                    provider_data[provider_name] = {
                        'requests': 0,
                        'total_cost': 0.0,
                        'total_tokens': 0,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'response_times': [],
                        'errors': 0,
                        'models': {}
                    }
                
                pdata = provider_data[provider_name]
                pdata['requests'] += 1
                pdata['total_cost'] += response.cost.get('amount', 0.0)
                pdata['total_tokens'] += response.usage.get('total_tokens', 0)
                pdata['input_tokens'] += response.usage.get('prompt_tokens', 0)
                pdata['output_tokens'] += response.usage.get('completion_tokens', 0)
                pdata['response_times'].append(response.response_time_ms)
                
                # Track errors from AI responses (robust handling)
                if isinstance(response, dict):
                    if response.get('error') or response.get('status') == 'error':
                        pdata['errors'] += 1
                else:  # Assume it's an object
                    if hasattr(response, 'error') and response.error:
                        pdata['errors'] += 1
                    elif hasattr(response, 'status') and response.status == 'error':
                        pdata['errors'] += 1
                
                # Track model usage
                model = response.model
                if model not in pdata['models']:
                    pdata['models'][model] = 0
                pdata['models'][model] += 1
            
            # Convert to ProviderMetrics objects
            for provider_name, pdata in provider_data.items():
                avg_response_time = sum(pdata['response_times']) / len(pdata['response_times']) if pdata['response_times'] else 0
                
                providers[provider_name] = ProviderMetrics(
                    requests=pdata['requests'],
                    cost_usd=pdata['total_cost'],
                    total_tokens=pdata['total_tokens'],
                    input_tokens=pdata['input_tokens'],
                    output_tokens=pdata['output_tokens'],
                    avg_response_time_ms=round(avg_response_time, 2),
                    error_count=pdata['errors'],
                    model_usage=pdata['models']
                )
                total_cost += pdata['total_cost']
        
        # Create snapshot
        snapshot = MetricsSnapshot(
            timestamp=datetime.now().isoformat(),
            uptime_seconds=service_metrics.get('uptime_seconds', 0),
            period_requests=period_requests,
            period_errors=period_errors,
            total_requests=current_total_requests,
            total_errors=current_total_errors,
            requests_per_minute=service_metrics.get('requests_per_minute', 0),
            average_response_time_ms=service_metrics.get('average_response_time_ms', 0),
            error_rate=service_metrics.get('error_rate', 0),
            providers=providers,
            total_cost_usd=round(total_cost, 4)
        )
        
        with self.lock:
            self.snapshots.append(snapshot)
            self._cleanup_old_snapshots()
    
    def _cleanup_old_snapshots(self):
        """Remove snapshots older than retention period"""
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        cutoff_iso = cutoff_time.isoformat()
        
        self.snapshots = [
            s for s in self.snapshots 
            if s.timestamp > cutoff_iso
        ]
        
        # Also cleanup old rollups
        self.hourly_rollups = [
            r for r in self.hourly_rollups
            if r.hour_timestamp > cutoff_iso[:13]  # Compare hour strings
        ]
    
    def _generate_hourly_rollups(self):
        """Generate hourly rollups from snapshots (incremental approach)"""
        # Only process snapshots that haven't been rolled up yet
        new_snapshots = self.snapshots[self.last_rollup_snapshot_index:]
        if not new_snapshots:
            return
        
        # Group NEW snapshots by hour
        hourly_groups = {}
        for snapshot in new_snapshots:
            hour_key = snapshot.timestamp[:13]  # YYYY-MM-DDTHH
            if hour_key not in hourly_groups:
                hourly_groups[hour_key] = []
            hourly_groups[hour_key].append(snapshot)
        
        for hour_key, snapshots_in_hour in hourly_groups.items():
            # Find existing rollup or create new one
            existing_rollup = next((r for r in self.hourly_rollups if r.hour_timestamp == hour_key), None)
            
            # Calculate incremental aggregates for this hour (using period_ values)
            period_requests = sum(s.period_requests for s in snapshots_in_hour)
            period_errors = sum(s.period_errors for s in snapshots_in_hour)
            period_cost = sum(s.total_cost_usd for s in snapshots_in_hour)
            avg_response_time = sum(s.average_response_time_ms for s in snapshots_in_hour) / len(snapshots_in_hour)
            
            # Aggregate provider metrics
            provider_aggregates = {}
            for snapshot in snapshots_in_hour:
                for provider_name, provider_metrics in snapshot.providers.items():
                    if provider_name not in provider_aggregates:
                        provider_aggregates[provider_name] = ProviderMetrics()
                    
                    agg = provider_aggregates[provider_name]
                    agg.requests += provider_metrics.requests
                    agg.cost_usd += provider_metrics.cost_usd
                    agg.total_tokens += provider_metrics.total_tokens
                    agg.input_tokens += provider_metrics.input_tokens
                    agg.output_tokens += provider_metrics.output_tokens
                    agg.error_count += provider_metrics.error_count
                    
                    # Merge model usage
                    for model, count in provider_metrics.model_usage.items():
                        if model not in agg.model_usage:
                            agg.model_usage[model] = 0
                        agg.model_usage[model] += count
            
            # Calculate average response times for providers
            for provider_name, agg in provider_aggregates.items():
                provider_snapshots = [s.providers.get(provider_name) for s in snapshots_in_hour 
                                    if provider_name in s.providers]
                if provider_snapshots:
                    avg_provider_time = sum(p.avg_response_time_ms for p in provider_snapshots) / len(provider_snapshots)
                    agg.avg_response_time_ms = round(avg_provider_time, 2)
            
            if existing_rollup:
                # Update existing rollup with incremental values
                existing_rollup.total_requests += period_requests
                existing_rollup.total_errors += period_errors
                existing_rollup.total_cost_usd += period_cost
                # Update avg response time (simple average of averages)
                existing_rollup.avg_response_time_ms = (existing_rollup.avg_response_time_ms + avg_response_time) / 2
                
                # Merge provider aggregates into existing rollup
                for provider_name, new_metrics in provider_aggregates.items():
                    if provider_name in existing_rollup.providers:
                        existing_metrics = existing_rollup.providers[provider_name]
                        existing_metrics.requests += new_metrics.requests
                        existing_metrics.cost_usd += new_metrics.cost_usd
                        existing_metrics.total_tokens += new_metrics.total_tokens
                        existing_metrics.input_tokens += new_metrics.input_tokens
                        existing_metrics.output_tokens += new_metrics.output_tokens
                        existing_metrics.error_count += new_metrics.error_count
                        
                        # Merge model usage
                        for model, count in new_metrics.model_usage.items():
                            if model not in existing_metrics.model_usage:
                                existing_metrics.model_usage[model] = 0
                            existing_metrics.model_usage[model] += count
                    else:
                        existing_rollup.providers[provider_name] = new_metrics
            else:
                # Create new rollup
                rollup = HourlyRollup(
                    hour_timestamp=hour_key,
                    total_requests=period_requests,
                    total_errors=period_errors,
                    total_cost_usd=round(period_cost, 4),
                    avg_response_time_ms=round(avg_response_time, 2),
                    providers=provider_aggregates
                )
                
                self.hourly_rollups.append(rollup)
        
        # Update tracking
        self.last_rollup_snapshot_index = len(self.snapshots)
    
    def _persist_to_file(self):
        """Atomically write metrics to file with improved error handling"""
        temp_file = self.metrics_file.with_suffix('.tmp')
        
        try:
            # Generate hourly rollups if enabled
            if self.rollup_enabled:
                self._generate_hourly_rollups()
            
            # Prepare data structure
            data = {
                'metadata': {
                    'version': '1.0',
                    'created': datetime.now().isoformat(),
                    'retention_days': self.retention_days,
                    'rollup_enabled': self.rollup_enabled,
                    'total_snapshots': len(self.snapshots),
                    'total_rollups': len(self.hourly_rollups)
                },
                'snapshots': [asdict(s) for s in self.snapshots],
                'hourly_rollups': [asdict(r) for r in self.hourly_rollups] if self.rollup_enabled else []
            }
            
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)  # default=str handles any remaining objects
            
            # Atomic rename
            temp_file.rename(self.metrics_file)
            
            logger.debug(f"Persisted {len(self.snapshots)} snapshots and {len(self.hourly_rollups)} rollups")
            
        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}")
        finally:
            # Cleanup temp file if it exists
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError as e:
                    logger.warning(f"Failed to clean up temporary metrics file {temp_file}: {e}")
    
    async def start_background_task(self):
        """Start background metrics collection task"""
        self.running = True
        self.background_task = asyncio.create_task(self._background_loop())
        logger.info("Metrics manager background task started")
    
    async def stop_background_task(self):
        """Stop background task and final persist"""
        self.running = False
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        
        # Final persist on shutdown
        self._persist_to_file()
        logger.info("Metrics manager stopped and final persist completed")
    
    async def _background_loop(self):
        """Background loop for periodic metrics persistence"""
        while self.running:
            try:
                await asyncio.sleep(self.flush_interval)
                
                if self.snapshots:
                    self._persist_to_file()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics background loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    def get_metrics_summary(self, hours: int = 24, use_rollups: bool = True) -> Dict[str, Any]:
        """
        Get metrics summary for the last N hours.
        
        Args:
            hours: Number of hours to look back
            use_rollups: Use hourly rollups for efficiency when possible
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        if use_rollups and self.rollup_enabled and hours >= 2:
            # Use rollups for efficiency
            cutoff_hour = cutoff_time.strftime('%Y-%m-%dT%H')
            recent_rollups = [
                r for r in self.hourly_rollups 
                if r.hour_timestamp >= cutoff_hour
            ]
            
            if recent_rollups:
                return self._summary_from_rollups(recent_rollups, hours)
        
        # Fallback to snapshot-based calculation
        cutoff_iso = cutoff_time.isoformat()
        recent_snapshots = [
            s for s in self.snapshots 
            if s.timestamp > cutoff_iso
        ]
        
        return self._summary_from_snapshots(recent_snapshots, hours)
    
    def _summary_from_rollups(self, rollups: List[HourlyRollup], hours: int) -> Dict[str, Any]:
        """Generate summary from hourly rollups"""
        if not rollups:
            return {'period_hours': hours, 'data_points': 0, 'source': 'rollups'}
        
        total_requests = sum(r.total_requests for r in rollups)
        total_errors = sum(r.total_errors for r in rollups)
        total_cost = sum(r.total_cost_usd for r in rollups)
        avg_response_time = sum(r.avg_response_time_ms for r in rollups) / len(rollups)
        
        # Provider aggregates
        provider_stats = {}
        for rollup in rollups:
            for provider, metrics in rollup.providers.items():
                if provider not in provider_stats:
                    provider_stats[provider] = {
                        'total_requests': 0,
                        'total_cost': 0.0,
                        'total_tokens': 0,
                        'avg_response_time_ms': 0.0,
                        'model_usage': {}
                    }
                
                stats = provider_stats[provider]
                stats['total_requests'] += metrics.requests
                stats['total_cost'] += metrics.cost_usd
                stats['total_tokens'] += metrics.total_tokens
                
                # Merge model usage
                for model, count in metrics.model_usage.items():
                    if model not in stats['model_usage']:
                        stats['model_usage'][model] = 0
                    stats['model_usage'][model] += count
        
        # Calculate average response times
        for provider in provider_stats:
            provider_rollups = [r.providers.get(provider) for r in rollups if provider in r.providers]
            if provider_rollups:
                avg_time = sum(p.avg_response_time_ms for p in provider_rollups) / len(provider_rollups)
                provider_stats[provider]['avg_response_time_ms'] = round(avg_time, 2)
        
        return {
            'period_hours': hours,
            'data_points': len(rollups),
            'source': 'rollups',
            'total_requests': total_requests,
            'total_errors': total_errors,
            'error_rate': (total_errors / total_requests * 100) if total_requests > 0 else 0,
            'average_response_time_ms': round(avg_response_time, 2),
            'total_cost_usd': round(total_cost, 4),
            'provider_stats': provider_stats,
            'first_data_point': rollups[0].hour_timestamp,
            'last_data_point': rollups[-1].hour_timestamp
        }
    
    def _summary_from_snapshots(self, snapshots: List[MetricsSnapshot], hours: int) -> Dict[str, Any]:
        """Generate summary from raw snapshots"""
        if not snapshots:
            return {'period_hours': hours, 'data_points': 0, 'source': 'snapshots'}
        
        # Use latest snapshot for current totals (snapshots are cumulative)
        latest = snapshots[-1]
        earliest = snapshots[0]
        
        # Calculate deltas for the period
        period_requests = latest.total_requests - earliest.total_requests
        period_errors = latest.total_errors - earliest.total_errors
        
        # Provider stats from latest snapshot
        provider_stats = {}
        for provider, metrics in latest.providers.items():
            provider_stats[provider] = {
                'total_requests': metrics.requests,
                'total_cost': metrics.cost_usd,
                'total_tokens': metrics.total_tokens,
                'avg_response_time_ms': metrics.avg_response_time_ms,
                'model_usage': metrics.model_usage
            }
        
        return {
            'period_hours': hours,
            'data_points': len(snapshots),
            'source': 'snapshots',
            'total_requests': period_requests,
            'total_errors': period_errors,
            'error_rate': (period_errors / period_requests * 100) if period_requests > 0 else 0,
            'average_response_time_ms': latest.average_response_time_ms,
            'total_cost_usd': latest.total_cost_usd,
            'provider_stats': provider_stats,
            'first_data_point': earliest.timestamp,
            'last_data_point': latest.timestamp
        }
    
    def clear_all_metrics(self):
        """Clear all metrics (for testing or reset)"""
        with self.lock:
            self.snapshots = []
            self.hourly_rollups = []
        
        # Remove metrics file
        if self.metrics_file.exists():
            self.metrics_file.unlink()
        
        logger.info("All metrics cleared")
    
    def export_metrics(self, format: str = 'json') -> Dict[str, Any]:
        """Export all metrics data for backup or analysis"""
        with self.lock:
            data = {
                'metadata': {
                    'exported_at': datetime.now().isoformat(),
                    'total_snapshots': len(self.snapshots),
                    'total_rollups': len(self.hourly_rollups),
                    'retention_days': self.retention_days
                },
                'snapshots': [asdict(s) for s in self.snapshots],
                'hourly_rollups': [asdict(r) for r in self.hourly_rollups]
            }
        
        return data