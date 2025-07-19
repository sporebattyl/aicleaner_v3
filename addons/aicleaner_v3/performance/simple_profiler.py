"""
Simple Performance Profiler for AICleaner v3
Phase 5A: Performance Optimization

Lightweight profiling using only Python built-in modules for Home Assistant compatibility.
"""

import asyncio
import cProfile
import io
import pstats
import time
import tracemalloc
import sys
import os
import resource
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import json
from functools import wraps
from contextlib import contextmanager

class SimpleProfiler:
    """Lightweight performance profiler using only built-in Python modules"""
    
    def __init__(self, output_dir: str = "/tmp/performance"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metrics = {}
        
    def profile_function(self, func_name: Optional[str] = None):
        """Decorator to profile individual functions"""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                name = func_name or f"{func.__module__}.{func.__qualname__}"
                
                # Start memory tracking
                tracemalloc.start()
                start_time = time.perf_counter()
                start_memory = self._get_memory_usage()
                
                try:
                    # Execute function
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    # Record metrics
                    end_time = time.perf_counter()
                    end_memory = self._get_memory_usage()
                    
                    # Get memory trace
                    current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    
                    # Store metrics
                    self.metrics[name] = {
                        "execution_time": end_time - start_time,
                        "memory_start_mb": start_memory,
                        "memory_end_mb": end_memory,
                        "memory_peak_bytes": peak,
                        "memory_current_bytes": current,
                        "timestamp": datetime.now().isoformat(),
                        "args_count": len(args),
                        "kwargs_count": len(kwargs)
                    }
                    
                    return result
                    
                except Exception as e:
                    tracemalloc.stop()
                    # Record error metrics
                    end_time = time.perf_counter()
                    self.metrics[name] = {
                        "execution_time": end_time - start_time,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    raise
                    
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                name = func_name or f"{func.__module__}.{func.__qualname__}"
                
                tracemalloc.start()
                start_time = time.perf_counter()
                start_memory = self._get_memory_usage()
                
                try:
                    result = func(*args, **kwargs)
                    
                    end_time = time.perf_counter()
                    end_memory = self._get_memory_usage()
                    
                    current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    
                    self.metrics[name] = {
                        "execution_time": end_time - start_time,
                        "memory_start_mb": start_memory,
                        "memory_end_mb": end_memory,
                        "memory_peak_bytes": peak,
                        "memory_current_bytes": current,
                        "timestamp": datetime.now().isoformat(),
                        "args_count": len(args),
                        "kwargs_count": len(kwargs)
                    }
                    
                    return result
                    
                except Exception as e:
                    tracemalloc.stop()
                    end_time = time.perf_counter()
                    self.metrics[name] = {
                        "execution_time": end_time - start_time,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    @contextmanager
    def profile_block(self, block_name: str):
        """Context manager to profile code blocks"""
        tracemalloc.start()
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            self.metrics[block_name] = {
                "execution_time": end_time - start_time,
                "memory_start_mb": start_memory,
                "memory_end_mb": end_memory,
                "memory_peak_bytes": peak,
                "memory_current_bytes": current,
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB using resource module"""
        try:
            # Get RSS memory usage in KB, convert to MB
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        except:
            return 0.0
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get basic system metrics using built-in modules"""
        try:
            # Get process memory info
            memory_mb = self._get_memory_usage()
            
            # Get current working directory disk usage
            stat = os.statvfs('.')
            total_space = stat.f_frsize * stat.f_blocks
            free_space = stat.f_frsize * stat.f_bavail
            used_space = total_space - free_space
            
            return {
                "process_memory_mb": memory_mb,
                "disk_total_gb": total_space / (1024 ** 3),
                "disk_free_gb": free_space / (1024 ** 3),
                "disk_used_gb": used_space / (1024 ** 3),
                "disk_percent": (used_space / total_space) * 100,
                "python_version": sys.version,
                "platform": sys.platform,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def profile_cprofile(self, func: Callable, *args, **kwargs):
        """Detailed cProfile analysis of a function"""
        pr = cProfile.Profile()
        
        try:
            if asyncio.iscoroutinefunction(func):
                # Handle async functions
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                pr.enable()
                result = loop.run_until_complete(func(*args, **kwargs))
                pr.disable()
                loop.close()
            else:
                pr.enable()
                result = func(*args, **kwargs)
                pr.disable()
            
            # Save cProfile results
            stats_file = self.output_dir / f"cprofile_{self.session_id}_{func.__name__}.stats"
            pr.dump_stats(str(stats_file))
            
            # Generate human-readable report
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s)
            ps.sort_stats('cumulative')
            ps.print_stats(20)  # Top 20 functions
            
            report_file = self.output_dir / f"cprofile_{self.session_id}_{func.__name__}.txt"
            with open(report_file, 'w') as f:
                f.write(s.getvalue())
            
            return result, str(report_file)
            
        except Exception as e:
            pr.disable()
            raise e
    
    def save_metrics(self, filename: Optional[str] = None):
        """Save collected metrics to JSON file"""
        if not filename:
            filename = f"performance_metrics_{self.session_id}.json"
        
        filepath = self.output_dir / filename
        
        # Add system metrics
        report_data = {
            "session_id": self.session_id,
            "system_metrics": self.get_system_metrics(),
            "function_metrics": self.metrics,
            "summary": self._generate_summary()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        return str(filepath)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate performance summary statistics"""
        if not self.metrics:
            return {}
        
        execution_times = [m.get("execution_time", 0) for m in self.metrics.values() if "execution_time" in m]
        memory_peaks = [m.get("memory_peak_bytes", 0) for m in self.metrics.values() if "memory_peak_bytes" in m]
        
        return {
            "total_functions_profiled": len(self.metrics),
            "average_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            "max_execution_time": max(execution_times) if execution_times else 0,
            "min_execution_time": min(execution_times) if execution_times else 0,
            "total_execution_time": sum(execution_times),
            "average_memory_peak_bytes": sum(memory_peaks) / len(memory_peaks) if memory_peaks else 0,
            "max_memory_peak_bytes": max(memory_peaks) if memory_peaks else 0,
            "functions_with_errors": len([m for m in self.metrics.values() if "error" in m])
        }
    
    def print_summary(self):
        """Print performance summary to console"""
        summary = self._generate_summary()
        system_metrics = self.get_system_metrics()
        
        print(f"\n{'='*60}")
        print(f"AICleaner v3 Performance Profile Summary")
        print(f"Session ID: {self.session_id}")
        print(f"{'='*60}")
        
        print(f"\nSystem Metrics:")
        print(f"  Process Memory: {system_metrics.get('process_memory_mb', 'N/A'):.1f} MB")
        print(f"  Disk Usage: {system_metrics.get('disk_percent', 'N/A'):.1f}% ({system_metrics.get('disk_used_gb', 'N/A'):.1f} GB)")
        print(f"  Python Version: {system_metrics.get('python_version', 'N/A')}")
        print(f"  Platform: {system_metrics.get('platform', 'N/A')}")
        
        print(f"\nFunction Profiling Summary:")
        print(f"  Functions Profiled: {summary.get('total_functions_profiled', 0)}")
        print(f"  Total Execution Time: {summary.get('total_execution_time', 0):.4f}s")
        print(f"  Average Execution Time: {summary.get('average_execution_time', 0):.4f}s")
        print(f"  Max Execution Time: {summary.get('max_execution_time', 0):.4f}s")
        print(f"  Average Memory Peak: {summary.get('average_memory_peak_bytes', 0)/1024:.2f} KB")
        print(f"  Max Memory Peak: {summary.get('max_memory_peak_bytes', 0)/1024:.2f} KB")
        print(f"  Functions with Errors: {summary.get('functions_with_errors', 0)}")
        
        print(f"\nTop 5 Slowest Functions:")
        sorted_metrics = sorted(
            [(k, v) for k, v in self.metrics.items() if "execution_time" in v],
            key=lambda x: x[1]["execution_time"],
            reverse=True
        )[:5]
        
        for i, (func_name, metrics) in enumerate(sorted_metrics, 1):
            print(f"  {i}. {func_name}: {metrics['execution_time']:.4f}s")
        
        print(f"\nTop 5 Memory-Intensive Functions:")
        sorted_memory = sorted(
            [(k, v) for k, v in self.metrics.items() if "memory_peak_bytes" in v],
            key=lambda x: x[1]["memory_peak_bytes"],
            reverse=True
        )[:5]
        
        for i, (func_name, metrics) in enumerate(sorted_memory, 1):
            peak_kb = metrics['memory_peak_bytes'] / 1024
            print(f"  {i}. {func_name}: {peak_kb:.2f} KB")
        
        print(f"{'='*60}")

# Global profiler instance
profiler = SimpleProfiler()

# Convenience decorators
def profile_api_endpoint(endpoint_name: Optional[str] = None):
    """Decorator specifically for FastAPI endpoints"""
    return profiler.profile_function(f"api.{endpoint_name}" if endpoint_name else None)

def profile_ai_provider(provider_name: Optional[str] = None):
    """Decorator specifically for AI provider operations"""
    return profiler.profile_function(f"ai_provider.{provider_name}" if provider_name else None)

def profile_database_operation(operation_name: Optional[str] = None):
    """Decorator specifically for database operations"""
    return profiler.profile_function(f"database.{operation_name}" if operation_name else None)