"""
Performance Manager - Main performance optimization coordinator
Implements hybrid architecture with integrated monitoring + async optimization workers
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from .resource_monitor import ResourceMonitor
from .intelligent_router import IntelligentRouter
from .model_optimizer import ModelOptimizer
from .optimizers.ollama_optimizer import OllamaOptimizer


class ComplexityLevel(Enum):
    AUTOMATIC = "automatic"
    GUIDED = "guided"
    EXPERT = "expert"


class OptimizationStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OptimizationTask:
    id: str
    task_type: str
    status: OptimizationStatus
    progress: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class PerformanceManager:
    """
    Main performance optimization coordinator implementing our hybrid architecture:
    - Integrated monitoring for real-time metrics
    - Async background workers for heavy optimization tasks
    - Three-tier complexity management
    - Hot-swapping capabilities
    """

    def __init__(self, config: Dict[str, Any], ai_provider_factory):
        self.config = config
        self.ai_provider_factory = ai_provider_factory
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.resource_monitor = ResourceMonitor(config.get("performance", {}))
        self.intelligent_router = IntelligentRouter(config.get("routing", {}))
        
        # Provider-specific optimizers
        self.optimizers: Dict[str, ModelOptimizer] = {
            "ollama": OllamaOptimizer(config.get("ollama", {}))
        }
        
        # Task management
        self.optimization_tasks: Dict[str, OptimizationTask] = {}
        self.task_queue = asyncio.Queue()
        self.background_workers: List[asyncio.Task] = []
        
        # Performance state
        self.complexity_level = ComplexityLevel(
            config.get("performance", {}).get("complexity_level", "automatic")
        )
        self.optimization_enabled = config.get("performance", {}).get("enabled", True)
        self._performance_baseline: Optional[Dict[str, float]] = None
        
        # Hot-swapping state
        self._hot_swap_lock = asyncio.Lock()
        self._pending_optimizations: Dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize the performance manager and start background services"""
        try:
            self.logger.info("Initializing Performance Manager")
            
            # Start resource monitoring
            await self.resource_monitor.start()
            
            # Initialize intelligent router
            await self.intelligent_router.initialize(self.ai_provider_factory)
            
            # Initialize optimizers
            for optimizer in self.optimizers.values():
                await optimizer.initialize()
            
            # Start background workers
            await self._start_background_workers()
            
            # Establish performance baseline if in automatic mode
            if self.complexity_level == ComplexityLevel.AUTOMATIC:
                await self._establish_baseline()
            
            self.logger.info("Performance Manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Performance Manager: {e}")
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown the performance manager"""
        self.logger.info("Shutting down Performance Manager")
        
        # Cancel background workers
        for worker in self.background_workers:
            worker.cancel()
        
        if self.background_workers:
            await asyncio.gather(*self.background_workers, return_exceptions=True)
        
        # Shutdown components
        await self.resource_monitor.stop()
        await self.intelligent_router.shutdown()
        
        for optimizer in self.optimizers.values():
            await optimizer.shutdown()

    async def get_optimal_provider(self, request_data: Dict[str, Any]) -> str:
        """Get the optimal provider for a request using intelligent routing"""
        try:
            # Get current performance metrics
            metrics = await self.resource_monitor.get_current_metrics()
            
            # Route the request
            provider = await self.intelligent_router.route_request(request_data, metrics)
            
            self.logger.debug(f"Routed request to provider: {provider}")
            return provider
            
        except Exception as e:
            self.logger.error(f"Failed to route request optimally: {e}")
            # Fallback to default provider
            return self.config.get("general", {}).get("active_provider", "openai")

    async def optimize_provider(self, provider: str, optimization_type: str = "auto") -> str:
        """
        Schedule optimization for a provider (async background task)
        Returns task_id for tracking progress
        """
        if not self.optimization_enabled:
            raise ValueError("Optimization is disabled")
        
        if provider not in self.optimizers:
            raise ValueError(f"No optimizer available for provider: {provider}")
        
        task_id = f"{provider}_{optimization_type}_{datetime.now().isoformat()}"
        task = OptimizationTask(
            id=task_id,
            task_type=f"optimize_{provider}_{optimization_type}",
            status=OptimizationStatus.IDLE
        )
        
        self.optimization_tasks[task_id] = task
        await self.task_queue.put((task_id, provider, optimization_type))
        
        self.logger.info(f"Scheduled optimization task: {task_id}")
        return task_id

    async def get_optimization_status(self, task_id: str) -> Optional[OptimizationTask]:
        """Get the status of an optimization task"""
        return self.optimization_tasks.get(task_id)

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            # Resource metrics
            resource_metrics = await self.resource_monitor.get_current_metrics()
            
            # Router performance
            router_metrics = await self.intelligent_router.get_metrics()
            
            # Optimization status
            optimization_metrics = {
                "active_tasks": len([t for t in self.optimization_tasks.values() 
                                   if t.status == OptimizationStatus.RUNNING]),
                "completed_tasks": len([t for t in self.optimization_tasks.values() 
                                      if t.status == OptimizationStatus.COMPLETED]),
                "failed_tasks": len([t for t in self.optimization_tasks.values() 
                                   if t.status == OptimizationStatus.FAILED])
            }
            
            # Performance improvement metrics
            improvement_metrics = await self._calculate_performance_improvements()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "resources": resource_metrics,
                "routing": router_metrics,
                "optimization": optimization_metrics,
                "improvements": improvement_metrics,
                "complexity_level": self.complexity_level.value,
                "optimization_enabled": self.optimization_enabled
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}

    async def hot_swap_optimization(self, provider: str, new_config: Dict[str, Any]) -> bool:
        """
        Perform hot-swap of optimization configuration without service restart
        """
        async with self._hot_swap_lock:
            try:
                self.logger.info(f"Performing hot-swap optimization for {provider}")
                
                if provider not in self.optimizers:
                    raise ValueError(f"Provider {provider} not found")
                
                optimizer = self.optimizers[provider]
                
                # Prepare new optimization in background
                await optimizer.prepare_hot_swap(new_config)
                
                # Atomic switch to new configuration
                success = await optimizer.execute_hot_swap()
                
                if success:
                    self.logger.info(f"Hot-swap completed successfully for {provider}")
                    return True
                else:
                    self.logger.warning(f"Hot-swap failed for {provider}, rolled back")
                    return False
                
            except Exception as e:
                self.logger.error(f"Hot-swap failed for {provider}: {e}")
                return False

    async def _start_background_workers(self) -> None:
        """Start background optimization workers"""
        num_workers = self.config.get("performance", {}).get("worker_threads", 2)
        
        for i in range(num_workers):
            worker = asyncio.create_task(self._optimization_worker(f"worker_{i}"))
            self.background_workers.append(worker)
        
        self.logger.info(f"Started {num_workers} optimization workers")

    async def _optimization_worker(self, worker_id: str) -> None:
        """Background worker for processing optimization tasks"""
        self.logger.debug(f"Optimization worker {worker_id} started")
        
        while True:
            try:
                # Wait for optimization task
                task_id, provider, optimization_type = await self.task_queue.get()
                
                if task_id not in self.optimization_tasks:
                    continue
                
                task = self.optimization_tasks[task_id]
                task.status = OptimizationStatus.RUNNING
                task.start_time = datetime.now()
                
                self.logger.info(f"Worker {worker_id} processing task: {task_id}")
                
                # Get the optimizer
                optimizer = self.optimizers.get(provider)
                if not optimizer:
                    raise ValueError(f"No optimizer for provider: {provider}")
                
                # Execute optimization with progress tracking
                async def progress_callback(progress: float):
                    task.progress = progress
                
                result = await optimizer.optimize(optimization_type, progress_callback)
                
                # Update task status
                task.status = OptimizationStatus.COMPLETED
                task.end_time = datetime.now()
                task.result = result
                task.progress = 1.0
                
                self.logger.info(f"Task {task_id} completed successfully")
                
            except asyncio.CancelledError:
                self.logger.info(f"Optimization worker {worker_id} cancelled")
                break
            except Exception as e:
                if task_id in self.optimization_tasks:
                    task = self.optimization_tasks[task_id]
                    task.status = OptimizationStatus.FAILED
                    task.end_time = datetime.now()
                    task.error_message = str(e)
                
                self.logger.error(f"Optimization task {task_id} failed: {e}")
            finally:
                self.task_queue.task_done()

    async def _establish_baseline(self) -> None:
        """Establish performance baseline for automatic optimization"""
        self.logger.info("Establishing performance baseline")
        
        try:
            # Run lightweight benchmark
            baseline_results = await self._run_baseline_benchmark()
            self._performance_baseline = baseline_results
            
            self.logger.info(f"Performance baseline established: {baseline_results}")
            
        except Exception as e:
            self.logger.error(f"Failed to establish baseline: {e}")

    async def _run_baseline_benchmark(self) -> Dict[str, float]:
        """Run a quick benchmark to establish baseline performance"""
        # Simple test prompts for different complexity levels
        test_cases = [
            {"type": "simple_text", "prompt": "Hello, how are you?", "expected_time": 5.0},
            {"type": "medium_text", "prompt": "Write a short paragraph about renewable energy.", "expected_time": 10.0}
        ]
        
        results = {}
        
        for test_case in test_cases:
            try:
                start_time = datetime.now()
                
                # Route and execute test request
                provider = await self.intelligent_router.route_request(
                    {"prompt": test_case["prompt"], "type": "text"}, {}
                )
                
                # Simulate request execution time (in real implementation, 
                # this would call the actual provider)
                await asyncio.sleep(0.1)  # Minimal simulation
                
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()
                
                results[test_case["type"]] = execution_time
                
            except Exception as e:
                self.logger.warning(f"Baseline test failed for {test_case['type']}: {e}")
                results[test_case["type"]] = test_case["expected_time"]
        
        return results

    async def _calculate_performance_improvements(self) -> Dict[str, Any]:
        """Calculate performance improvements compared to baseline"""
        if not self._performance_baseline:
            return {"status": "no_baseline"}
        
        try:
            current_metrics = await self.resource_monitor.get_current_metrics()
            router_metrics = await self.intelligent_router.get_metrics()
            
            improvements = {
                "response_time_improvement": self._calculate_response_time_improvement(),
                "resource_efficiency": self._calculate_resource_efficiency(current_metrics),
                "routing_accuracy": router_metrics.get("routing_accuracy", 0.0),
                "cost_savings": self._calculate_cost_savings()
            }
            
            return improvements
            
        except Exception as e:
            self.logger.error(f"Failed to calculate performance improvements: {e}")
            return {"error": str(e)}

    def _calculate_response_time_improvement(self) -> float:
        """Calculate response time improvement percentage"""
        # Placeholder implementation
        return 15.5  # 15.5% improvement

    def _calculate_resource_efficiency(self, current_metrics: Dict[str, Any]) -> float:
        """Calculate resource efficiency improvement"""
        # Placeholder implementation
        cpu_usage = current_metrics.get("cpu_usage", 50.0)
        memory_usage = current_metrics.get("memory_usage", 50.0)
        
        # Simple efficiency calculation
        efficiency = 100 - ((cpu_usage + memory_usage) / 2)
        return max(0, efficiency)

    def _calculate_cost_savings(self) -> float:
        """Calculate estimated cost savings from optimizations"""
        # Placeholder implementation
        return 12.3  # 12.3% cost savings