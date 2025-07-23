"""
Model Optimizer - Base class for provider-specific optimizers
Defines the interface for model optimization and hot-swapping
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OptimizationType(Enum):
    QUANTIZATION = "quantization"
    CACHING = "caching"
    MEMORY = "memory"
    PERFORMANCE = "performance"
    AUTO = "auto"


@dataclass
class OptimizationResult:
    success: bool
    optimization_type: OptimizationType
    performance_improvement: float
    memory_savings: float
    details: Dict[str, Any]
    timestamp: datetime
    error_message: Optional[str] = None


class ModelOptimizer(ABC):
    """
    Abstract base class for provider-specific model optimizers
    
    Defines the interface for:
    - Model optimization (quantization, caching, etc.)
    - Hot-swapping of optimizations
    - Performance monitoring and reporting
    """

    def __init__(self, provider_name: str, config: Dict[str, Any]):
        self.provider_name = provider_name
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")
        
        # Optimization state
        self.is_initialized = False
        self.current_optimizations: Dict[str, Any] = {}
        self.optimization_history: List[OptimizationResult] = []
        
        # Hot-swap state
        self._hot_swap_prepared = False
        self._hot_swap_data: Optional[Dict[str, Any]] = None
        self._fallback_state: Optional[Dict[str, Any]] = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the optimizer - must be implemented by subclasses"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the optimizer - must be implemented by subclasses"""
        pass

    @abstractmethod
    async def optimize(self, optimization_type: OptimizationType, 
                      progress_callback: Optional[Callable[[float], None]] = None) -> OptimizationResult:
        """
        Perform optimization - must be implemented by subclasses
        
        Args:
            optimization_type: Type of optimization to perform
            progress_callback: Optional callback for progress updates (0.0 to 1.0)
            
        Returns:
            OptimizationResult with success status and details
        """
        pass

    @abstractmethod
    async def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status - must be implemented by subclasses"""
        pass

    async def prepare_hot_swap(self, new_config: Dict[str, Any]) -> None:
        """
        Prepare for hot-swap optimization change
        Base implementation - can be overridden by subclasses
        """
        try:
            self.logger.info(f"Preparing hot-swap for {self.provider_name}")
            
            # Save current state as fallback
            self._fallback_state = self.current_optimizations.copy()
            
            # Prepare new optimization in background
            self._hot_swap_data = new_config.copy()
            
            # Subclasses can override this to do provider-specific preparation
            await self._prepare_provider_hot_swap(new_config)
            
            self._hot_swap_prepared = True
            self.logger.info(f"Hot-swap prepared for {self.provider_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to prepare hot-swap for {self.provider_name}: {e}")
            self._hot_swap_prepared = False
            self._hot_swap_data = None
            raise

    async def execute_hot_swap(self) -> bool:
        """
        Execute the prepared hot-swap
        Base implementation - can be overridden by subclasses
        """
        if not self._hot_swap_prepared or not self._hot_swap_data:
            self.logger.error("Hot-swap not prepared")
            return False
        
        try:
            self.logger.info(f"Executing hot-swap for {self.provider_name}")
            
            # Execute provider-specific hot-swap
            success = await self._execute_provider_hot_swap(self._hot_swap_data)
            
            if success:
                # Update current state
                self.current_optimizations.update(self._hot_swap_data)
                self.logger.info(f"Hot-swap completed successfully for {self.provider_name}")
            else:
                # Rollback to fallback state
                await self._rollback_hot_swap()
                self.logger.warning(f"Hot-swap failed, rolled back for {self.provider_name}")
            
            # Clean up hot-swap state
            self._hot_swap_prepared = False
            self._hot_swap_data = None
            self._fallback_state = None
            
            return success
            
        except Exception as e:
            self.logger.error(f"Hot-swap execution failed for {self.provider_name}: {e}")
            await self._rollback_hot_swap()
            return False

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this optimizer"""
        try:
            # Calculate metrics from optimization history
            if not self.optimization_history:
                return {"status": "no_optimizations"}
            
            successful_optimizations = [
                opt for opt in self.optimization_history if opt.success
            ]
            
            if not successful_optimizations:
                return {"status": "no_successful_optimizations"}
            
            # Calculate averages
            avg_performance_improvement = sum(
                opt.performance_improvement for opt in successful_optimizations
            ) / len(successful_optimizations)
            
            avg_memory_savings = sum(
                opt.memory_savings for opt in successful_optimizations
            ) / len(successful_optimizations)
            
            # Success rate
            success_rate = len(successful_optimizations) / len(self.optimization_history)
            
            # Recent performance (last 5 optimizations)
            recent_optimizations = self.optimization_history[-5:]
            recent_success_rate = sum(1 for opt in recent_optimizations if opt.success) / len(recent_optimizations)
            
            return {
                "provider": self.provider_name,
                "total_optimizations": len(self.optimization_history),
                "successful_optimizations": len(successful_optimizations),
                "success_rate": success_rate,
                "recent_success_rate": recent_success_rate,
                "avg_performance_improvement": avg_performance_improvement,
                "avg_memory_savings": avg_memory_savings,
                "current_optimizations": self.current_optimizations,
                "last_optimization": self.optimization_history[-1].timestamp.isoformat() if self.optimization_history else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics for {self.provider_name}: {e}")
            return {"error": str(e)}

    async def auto_optimize(self, target_performance: Dict[str, float]) -> List[OptimizationResult]:
        """
        Automatically determine and apply optimal optimizations
        Base implementation - can be overridden by subclasses
        """
        results = []
        
        try:
            self.logger.info(f"Starting auto-optimization for {self.provider_name}")
            
            # Determine which optimizations to apply based on target performance
            optimization_plan = await self._plan_auto_optimization(target_performance)
            
            # Execute optimizations in order
            for i, (opt_type, opt_config) in enumerate(optimization_plan):
                progress_callback = lambda p: self.logger.debug(f"Auto-optimization step {i+1}/{len(optimization_plan)}: {p*100:.1f}%")
                
                result = await self.optimize(opt_type, progress_callback)
                results.append(result)
                
                # Stop if optimization failed
                if not result.success:
                    self.logger.warning(f"Auto-optimization step failed: {result.error_message}")
                    break
            
            self.logger.info(f"Auto-optimization completed for {self.provider_name}, {len(results)} steps executed")
            return results
            
        except Exception as e:
            self.logger.error(f"Auto-optimization failed for {self.provider_name}: {e}")
            # Return failed result
            failed_result = OptimizationResult(
                success=False,
                optimization_type=OptimizationType.AUTO,
                performance_improvement=0.0,
                memory_savings=0.0,
                details={},
                timestamp=datetime.now(),
                error_message=str(e)
            )
            return [failed_result]

    # Protected methods for subclass implementation

    async def _prepare_provider_hot_swap(self, new_config: Dict[str, Any]) -> None:
        """Provider-specific hot-swap preparation - override in subclasses"""
        pass

    async def _execute_provider_hot_swap(self, new_config: Dict[str, Any]) -> bool:
        """Provider-specific hot-swap execution - override in subclasses"""
        return True

    async def _rollback_hot_swap(self) -> None:
        """Rollback hot-swap to previous state"""
        if self._fallback_state:
            self.current_optimizations = self._fallback_state.copy()
            self.logger.info(f"Rolled back hot-swap for {self.provider_name}")

    async def _plan_auto_optimization(self, target_performance: Dict[str, float]) -> List[tuple]:
        """
        Plan automatic optimization steps
        Returns list of (optimization_type, config) tuples
        """
        plan = []
        
        # Basic auto-optimization strategy - override in subclasses for provider-specific logic
        target_response_time = target_performance.get("response_time", 10.0)
        target_memory_usage = target_performance.get("memory_usage", 4000.0)  # MB
        
        # If response time target is aggressive, prioritize performance
        if target_response_time < 5.0:
            plan.append((OptimizationType.PERFORMANCE, {"aggressive": True}))
            plan.append((OptimizationType.CACHING, {"cache_size": "large"}))
        
        # If memory target is tight, prioritize memory optimization
        if target_memory_usage < 2000.0:
            plan.append((OptimizationType.QUANTIZATION, {"level": "aggressive"}))
            plan.append((OptimizationType.MEMORY, {"optimization_level": "high"}))
        
        # Default optimization plan
        if not plan:
            plan.extend([
                (OptimizationType.QUANTIZATION, {"level": "balanced"}),
                (OptimizationType.CACHING, {"cache_size": "medium"}),
                (OptimizationType.MEMORY, {"optimization_level": "medium"})
            ])
        
        return plan

    def _record_optimization_result(self, result: OptimizationResult) -> None:
        """Record an optimization result in history"""
        self.optimization_history.append(result)
        
        # Maintain history size (keep last 100 results)
        max_history = 100
        if len(self.optimization_history) > max_history:
            self.optimization_history = self.optimization_history[-max_history:]
        
        # Log result
        if result.success:
            self.logger.info(
                f"Optimization {result.optimization_type.value} completed: "
                f"{result.performance_improvement:.1f}% performance, "
                f"{result.memory_savings:.1f}MB memory savings"
            )
        else:
            self.logger.error(
                f"Optimization {result.optimization_type.value} failed: {result.error_message}"
            )