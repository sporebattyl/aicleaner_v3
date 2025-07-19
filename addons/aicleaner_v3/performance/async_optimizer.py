"""
Async Concurrent Operations Optimizer
Phase 5A: Performance Optimization

Optimizes async operations to run concurrently instead of sequentially.
"""

import asyncio
import time
from typing import List, Dict, Any, Callable, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import functools

class AsyncOptimizer:
    """Optimizes async operations for better performance"""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        
    async def run_concurrent_with_limit(self, tasks: List[Callable], 
                                       *args, **kwargs) -> List[Any]:
        """
        Run multiple async tasks concurrently with a semaphore limit
        
        Args:
            tasks: List of async callables to execute
            *args, **kwargs: Arguments to pass to each task
            
        Returns:
            List of results from all tasks
        """
        async def limited_task(task):
            async with self.semaphore:
                return await task(*args, **kwargs)
        
        # Create limited tasks
        limited_tasks = [limited_task(task) for task in tasks]
        
        # Run all tasks concurrently
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)
        
        return results
    
    async def batch_process(self, items: List[Any], 
                           processor: Callable[[Any], Any],
                           batch_size: int = 10) -> List[Any]:
        """
        Process items in batches concurrently
        
        Args:
            items: List of items to process
            processor: Async function to process each item
            batch_size: Number of items to process concurrently
            
        Returns:
            List of processed results
        """
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_tasks = [processor(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
        
        return results

class AIProviderOptimizer(AsyncOptimizer):
    """Specialized optimizer for AI provider operations"""
    
    def __init__(self, max_concurrent_providers: int = 5):
        super().__init__(max_concurrent_providers)
        self.provider_cache = {}
        
    async def call_providers_concurrent(self, 
                                      providers: List[Dict[str, Any]], 
                                      prompt: str,
                                      timeout: float = 30.0) -> Dict[str, Any]:
        """
        Call multiple AI providers concurrently and return the fastest response
        
        Args:
            providers: List of provider configurations
            prompt: Prompt to send to providers
            timeout: Timeout for each provider call
            
        Returns:
            Dict with results from all providers
        """
        async def call_single_provider(provider: Dict[str, Any]) -> Dict[str, Any]:
            """Call a single AI provider with timeout"""
            try:
                start_time = time.time()
                
                # Simulate AI provider call
                # In real implementation, this would call actual provider
                await asyncio.sleep(0.1 + len(prompt) * 0.001)  # Simulate processing time
                
                response_time = time.time() - start_time
                
                return {
                    "provider": provider.get("name", "unknown"),
                    "success": True,
                    "response": f"Response from {provider.get('name')} for: {prompt[:50]}...",
                    "response_time": response_time,
                    "timestamp": time.time()
                }
                
            except asyncio.TimeoutError:
                return {
                    "provider": provider.get("name", "unknown"),
                    "success": False,
                    "error": "Timeout",
                    "response_time": timeout,
                    "timestamp": time.time()
                }
            except Exception as e:
                return {
                    "provider": provider.get("name", "unknown"),
                    "success": False,
                    "error": str(e),
                    "response_time": 0,
                    "timestamp": time.time()
                }
        
        # Create timeout wrapper for each provider call
        async def timeout_wrapper(provider):
            try:
                return await asyncio.wait_for(
                    call_single_provider(provider), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                return {
                    "provider": provider.get("name", "unknown"),
                    "success": False,
                    "error": "Timeout",
                    "response_time": timeout,
                    "timestamp": time.time()
                }
        
        # Run all provider calls concurrently
        start_time = time.time()
        tasks = [timeout_wrapper(provider) for provider in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Process results
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_results.append({
                    "provider": "unknown",
                    "success": False,
                    "error": str(result),
                    "response_time": 0,
                    "timestamp": time.time()
                })
            elif result.get("success"):
                successful_results.append(result)
            else:
                failed_results.append(result)
        
        return {
            "successful": successful_results,
            "failed": failed_results,
            "total_providers": len(providers),
            "successful_count": len(successful_results),
            "failed_count": len(failed_results),
            "total_time": total_time,
            "fastest_response": min(successful_results, 
                                  key=lambda x: x["response_time"]) if successful_results else None
        }
    
    async def health_check_all_providers(self, 
                                       providers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform health checks on all providers concurrently
        
        Args:
            providers: List of provider configurations
            
        Returns:
            Dict with health status of all providers
        """
        async def health_check_provider(provider: Dict[str, Any]) -> Dict[str, Any]:
            """Health check for a single provider"""
            try:
                start_time = time.time()
                
                # Simulate health check
                await asyncio.sleep(0.05)  # Quick health check
                
                response_time = time.time() - start_time
                
                return {
                    "provider": provider.get("name", "unknown"),
                    "healthy": True,
                    "response_time": response_time,
                    "last_check": time.time()
                }
                
            except Exception as e:
                return {
                    "provider": provider.get("name", "unknown"),
                    "healthy": False,
                    "error": str(e),
                    "response_time": 0,
                    "last_check": time.time()
                }
        
        # Run health checks concurrently
        start_time = time.time()
        tasks = [health_check_provider(provider) for provider in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Process results
        healthy_providers = []
        unhealthy_providers = []
        
        for result in results:
            if isinstance(result, Exception):
                unhealthy_providers.append({
                    "provider": "unknown",
                    "healthy": False,
                    "error": str(result),
                    "response_time": 0,
                    "last_check": time.time()
                })
            elif result.get("healthy"):
                healthy_providers.append(result)
            else:
                unhealthy_providers.append(result)
        
        return {
            "healthy": healthy_providers,
            "unhealthy": unhealthy_providers,
            "total_providers": len(providers),
            "healthy_count": len(healthy_providers),
            "unhealthy_count": len(unhealthy_providers),
            "total_check_time": total_time,
            "overall_health": len(healthy_providers) > 0
        }

class ConfigOptimizer(AsyncOptimizer):
    """Specialized optimizer for configuration operations"""
    
    async def load_configs_concurrent(self, 
                                    config_sources: List[str]) -> Dict[str, Any]:
        """
        Load multiple configuration files concurrently
        
        Args:
            config_sources: List of configuration file paths
            
        Returns:
            Dict with loaded configurations
        """
        async def load_single_config(config_path: str) -> Dict[str, Any]:
            """Load a single configuration file"""
            try:
                # Simulate config loading
                await asyncio.sleep(0.01)  # Simulate file I/O
                
                return {
                    "source": config_path,
                    "success": True,
                    "config": {"setting": f"value_from_{config_path}"},
                    "load_time": 0.01
                }
                
            except Exception as e:
                return {
                    "source": config_path,
                    "success": False,
                    "error": str(e),
                    "load_time": 0
                }
        
        # Load all configs concurrently
        tasks = [load_single_config(source) for source in config_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge successful configs
        merged_config = {}
        load_results = []
        
        for result in results:
            if isinstance(result, Exception):
                load_results.append({
                    "source": "unknown",
                    "success": False,
                    "error": str(result),
                    "load_time": 0
                })
            else:
                load_results.append(result)
                if result.get("success") and result.get("config"):
                    merged_config.update(result["config"])
        
        return {
            "merged_config": merged_config,
            "load_results": load_results,
            "successful_loads": len([r for r in load_results if r.get("success")]),
            "failed_loads": len([r for r in load_results if not r.get("success")])
        }

# Global optimizers
ai_optimizer = AIProviderOptimizer(max_concurrent_providers=5)
config_optimizer = ConfigOptimizer(max_concurrent_tasks=10)
general_optimizer = AsyncOptimizer(max_concurrent_tasks=20)

# Convenience functions
async def optimize_ai_provider_calls(providers: List[Dict], prompt: str) -> Dict[str, Any]:
    """Optimize AI provider calls using concurrent execution"""
    return await ai_optimizer.call_providers_concurrent(providers, prompt)

async def optimize_health_checks(providers: List[Dict]) -> Dict[str, Any]:
    """Optimize provider health checks using concurrent execution"""
    return await ai_optimizer.health_check_all_providers(providers)

async def optimize_config_loading(config_sources: List[str]) -> Dict[str, Any]:
    """Optimize configuration loading using concurrent execution"""
    return await config_optimizer.load_configs_concurrent(config_sources)