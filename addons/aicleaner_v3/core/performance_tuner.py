"""
Performance Tuner for AICleaner Phase 3C.2
Auto-tuning engine with adaptive configuration and usage pattern learning.
"""

import asyncio
import logging
import time
import json
import os
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import threading

try:
    from core.resource_monitor import ResourceMonitor, ResourceMetrics
    from core.performance_benchmarks import PerformanceBenchmarks, BenchmarkResult
    from core.local_model_manager import LocalModelManager, OptimizationConfig, QuantizationLevel
    from core.production_monitor import ProductionMonitor, PerformanceMetric
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


class TuningStrategy(Enum):
    """Auto-tuning strategies."""
    CONSERVATIVE = "conservative"  # Minimal changes, prioritize stability
    BALANCED = "balanced"         # Balance performance and stability
    AGGRESSIVE = "aggressive"     # Maximize performance, accept some risk
    ADAPTIVE = "adaptive"         # Learn from usage patterns


class TuningObjective(Enum):
    """Optimization objectives."""
    MINIMIZE_LATENCY = "minimize_latency"
    MAXIMIZE_THROUGHPUT = "maximize_throughput"
    MINIMIZE_RESOURCE_USAGE = "minimize_resource_usage"
    MAXIMIZE_ACCURACY = "maximize_accuracy"
    BALANCE_ALL = "balance_all"


@dataclass
class TuningParameter:
    """Definition of a tunable parameter."""
    name: str
    current_value: Any
    min_value: Any
    max_value: Any
    step_size: Any
    parameter_type: str  # int, float, bool, enum
    impact_weight: float = 1.0  # How much this parameter affects performance
    stability_risk: float = 0.5  # Risk of instability when changing (0-1)


@dataclass
class TuningExperiment:
    """Record of a tuning experiment."""
    experiment_id: str
    timestamp: str
    parameters: Dict[str, Any]
    baseline_metrics: Dict[str, float]
    result_metrics: Dict[str, float]
    improvement_score: float
    success: bool
    duration_seconds: float
    notes: str = ""


@dataclass
class TuningRecommendation:
    """Recommendation from the tuning engine."""
    parameter_name: str
    current_value: Any
    recommended_value: Any
    expected_improvement: float
    confidence: float
    risk_level: str  # low, medium, high
    reasoning: str


class PerformanceTuner:
    """
    Intelligent auto-tuning engine for AICleaner performance optimization.
    
    Features:
    - Adaptive parameter tuning based on usage patterns
    - Multiple optimization strategies
    - Safe experimentation with rollback capability
    - Learning from historical performance data
    - Automated A/B testing for parameter changes
    - Integration with monitoring and benchmarking systems
    """
    
    def __init__(self, config: Dict[str, Any], data_path: str = "/data/performance_tuner"):
        """
        Initialize Performance Tuner.
        
        Args:
            config: Configuration dictionary
            data_path: Path to store tuning data
        """
        self.logger = logging.getLogger(__name__)
        self.config = config.get("performance_optimization", {})
        self.data_path = data_path
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Tuning configuration
        self.auto_tuning_config = self.config.get("auto_tuning", {})
        self.tuning_enabled = self.auto_tuning_config.get("enabled", True)
        self.tuning_strategy = TuningStrategy(self.auto_tuning_config.get("performance_target", "balanced"))
        self.learning_rate = self.auto_tuning_config.get("learning_rate", 0.01)
        self.adaptation_interval = self.auto_tuning_config.get("adaptation_interval_hours", 24) * 3600
        
        # Tunable parameters
        self.tunable_parameters: Dict[str, TuningParameter] = {}
        self.parameter_history = defaultdict(list)
        
        # Experiment tracking
        self.experiments: List[TuningExperiment] = []
        self.current_experiment: Optional[TuningExperiment] = None
        
        # Performance tracking
        self.performance_history = deque(maxlen=1000)
        self.baseline_metrics = {}
        self.current_metrics = {}
        
        # Learning system
        self.usage_patterns = defaultdict(list)
        self.optimization_model = {}
        self.confidence_scores = defaultdict(float)
        
        # Components
        self.resource_monitor = None
        self.performance_benchmarks = None
        self.local_model_manager = None
        self.production_monitor = None
        
        # Tuning state
        self.tuning_active = False
        self.last_tuning_time = 0
        self.pending_changes = {}
        
        # Background tasks
        self._tuning_task = None
        self._monitoring_task = None
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize components and parameters
        if DEPENDENCIES_AVAILABLE:
            self._initialize_components()
        
        self._initialize_tunable_parameters()
        self._load_tuning_data()
        
        self.logger.info("Performance Tuner initialized")

    def _initialize_components(self):
        """Initialize monitoring and optimization components."""
        try:
            self.resource_monitor = ResourceMonitor({"performance_optimization": self.config})
            self.performance_benchmarks = PerformanceBenchmarks(self.data_path)
            # Note: LocalModelManager and ProductionMonitor would be injected in real usage
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")

    def _initialize_tunable_parameters(self):
        """Initialize the set of tunable parameters."""
        # Model optimization parameters
        self.register_parameter(TuningParameter(
            name="quantization_level",
            current_value="dynamic",
            min_value="none",
            max_value="int4",
            step_size=1,
            parameter_type="enum",
            impact_weight=0.8,
            stability_risk=0.3
        ))
        
        self.register_parameter(TuningParameter(
            name="context_window_size",
            current_value=2048,
            min_value=512,
            max_value=4096,
            step_size=256,
            parameter_type="int",
            impact_weight=0.6,
            stability_risk=0.2
        ))
        
        self.register_parameter(TuningParameter(
            name="batch_size",
            current_value=1,
            min_value=1,
            max_value=8,
            step_size=1,
            parameter_type="int",
            impact_weight=0.7,
            stability_risk=0.4
        ))
        
        self.register_parameter(TuningParameter(
            name="gpu_acceleration",
            current_value=False,
            min_value=False,
            max_value=True,
            step_size=1,
            parameter_type="bool",
            impact_weight=0.9,
            stability_risk=0.5
        ))
        
        # Resource management parameters
        self.register_parameter(TuningParameter(
            name="memory_limit_mb",
            current_value=4096,
            min_value=2048,
            max_value=8192,
            step_size=512,
            parameter_type="int",
            impact_weight=0.5,
            stability_risk=0.3
        ))
        
        self.register_parameter(TuningParameter(
            name="cpu_limit_percent",
            current_value=80,
            min_value=50,
            max_value=95,
            step_size=5,
            parameter_type="int",
            impact_weight=0.4,
            stability_risk=0.2
        ))

    def register_parameter(self, parameter: TuningParameter):
        """Register a tunable parameter."""
        self.tunable_parameters[parameter.name] = parameter
        self.logger.debug(f"Registered tunable parameter: {parameter.name}")

    async def start_auto_tuning(self):
        """Start the auto-tuning engine."""
        if not self.tuning_enabled:
            self.logger.info("Auto-tuning is disabled")
            return
        
        if self.tuning_active:
            self.logger.warning("Auto-tuning already active")
            return
        
        self.tuning_active = True
        
        # Start background tasks
        self._tuning_task = asyncio.create_task(self._tuning_loop())
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("Auto-tuning engine started")

    async def stop_auto_tuning(self):
        """Stop the auto-tuning engine."""
        self.tuning_active = False
        
        # Cancel background tasks
        if self._tuning_task:
            self._tuning_task.cancel()
        if self._monitoring_task:
            self._monitoring_task.cancel()
        
        # Save current state
        self._save_tuning_data()
        
        self.logger.info("Auto-tuning engine stopped")

    async def run_tuning_experiment(self, parameter_changes: Dict[str, Any], 
                                   duration_seconds: int = 300) -> TuningExperiment:
        """
        Run a controlled tuning experiment.
        
        Args:
            parameter_changes: Dictionary of parameter changes to test
            duration_seconds: Duration to run the experiment
            
        Returns:
            TuningExperiment with results
        """
        experiment_id = f"exp_{int(time.time())}"
        start_time = datetime.now(timezone.utc)
        
        self.logger.info(f"Starting tuning experiment {experiment_id}")
        
        # Get baseline metrics
        baseline_metrics = await self._collect_performance_metrics()
        
        # Create experiment record
        experiment = TuningExperiment(
            experiment_id=experiment_id,
            timestamp=start_time.isoformat(),
            parameters=parameter_changes.copy(),
            baseline_metrics=baseline_metrics,
            result_metrics={},
            improvement_score=0.0,
            success=False,
            duration_seconds=0.0
        )
        
        self.current_experiment = experiment
        
        try:
            # Apply parameter changes
            original_values = await self._apply_parameter_changes(parameter_changes)
            
            # Wait for system to stabilize
            await asyncio.sleep(30)
            
            # Run experiment for specified duration
            experiment_start = time.time()
            
            # Collect metrics during experiment
            metrics_samples = []
            while time.time() - experiment_start < duration_seconds:
                sample = await self._collect_performance_metrics()
                metrics_samples.append(sample)
                await asyncio.sleep(10)  # Sample every 10 seconds
            
            # Calculate average metrics
            result_metrics = self._average_metrics(metrics_samples)
            
            # Calculate improvement score
            improvement_score = self._calculate_improvement_score(baseline_metrics, result_metrics)
            
            # Update experiment record
            experiment.result_metrics = result_metrics
            experiment.improvement_score = improvement_score
            experiment.success = improvement_score > 0
            experiment.duration_seconds = time.time() - experiment_start
            
            # Revert changes if experiment failed or improvement is minimal
            if improvement_score < 0.05:  # Less than 5% improvement
                await self._apply_parameter_changes(original_values)
                experiment.notes = "Reverted due to insufficient improvement"
            else:
                experiment.notes = "Changes retained due to positive results"
            
        except Exception as e:
            experiment.success = False
            experiment.notes = f"Experiment failed: {str(e)}"
            self.logger.error(f"Experiment {experiment_id} failed: {e}")
        
        finally:
            self.current_experiment = None
            
            # Store experiment
            with self._lock:
                self.experiments.append(experiment)
            
            self._save_tuning_data()
        
        self.logger.info(f"Experiment {experiment_id} completed with score: {experiment.improvement_score:.3f}")
        return experiment

    async def get_tuning_recommendations(self) -> List[TuningRecommendation]:
        """Get current tuning recommendations based on analysis."""
        recommendations = []
        
        try:
            # Analyze current performance
            current_metrics = await self._collect_performance_metrics()
            
            # Analyze each parameter
            for param_name, parameter in self.tunable_parameters.items():
                recommendation = await self._analyze_parameter(parameter, current_metrics)
                if recommendation:
                    recommendations.append(recommendation)
            
            # Sort by expected improvement
            recommendations.sort(key=lambda r: r.expected_improvement, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error generating tuning recommendations: {e}")
        
        return recommendations

    async def _tuning_loop(self):
        """Background tuning loop."""
        while self.tuning_active:
            try:
                # Check if it's time for tuning
                if time.time() - self.last_tuning_time > self.adaptation_interval:
                    await self._perform_adaptive_tuning()
                    self.last_tuning_time = time.time()
                
                # Wait before next check
                await asyncio.sleep(3600)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in tuning loop: {e}")
                await asyncio.sleep(3600)

    async def _monitoring_loop(self):
        """Background monitoring loop for performance tracking."""
        while self.tuning_active:
            try:
                # Collect performance metrics
                metrics = await self._collect_performance_metrics()
                
                with self._lock:
                    self.performance_history.append({
                        "timestamp": time.time(),
                        "metrics": metrics
                    })
                
                # Update usage patterns
                self._update_usage_patterns(metrics)
                
                await asyncio.sleep(60)  # Collect every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)

    async def _perform_adaptive_tuning(self):
        """Perform adaptive tuning based on learned patterns."""
        self.logger.info("Performing adaptive tuning")
        
        try:
            # Get tuning recommendations
            recommendations = await self.get_tuning_recommendations()
            
            if not recommendations:
                self.logger.info("No tuning recommendations available")
                return
            
            # Select best recommendation based on strategy
            selected_recommendation = self._select_recommendation(recommendations)
            
            if selected_recommendation:
                # Run experiment with recommended change
                parameter_changes = {
                    selected_recommendation.parameter_name: selected_recommendation.recommended_value
                }
                
                experiment = await self.run_tuning_experiment(parameter_changes)
                
                # Update learning model based on results
                self._update_learning_model(experiment)
                
        except Exception as e:
            self.logger.error(f"Error in adaptive tuning: {e}")

    async def _collect_performance_metrics(self) -> Dict[str, float]:
        """Collect current performance metrics."""
        metrics = {}
        
        try:
            # Resource metrics
            if self.resource_monitor:
                resource_metrics = await self.resource_monitor.get_current_metrics()
                metrics.update({
                    "cpu_percent": resource_metrics.cpu_percent,
                    "memory_percent": resource_metrics.memory_percent,
                    "gpu_utilization": resource_metrics.gpu_utilization_percent
                })
            
            # Performance metrics from production monitor
            if self.production_monitor:
                perf_summary = self.production_monitor.get_performance_summary()
                metrics.update(perf_summary.get("current_metrics", {}))
            
            # Add timestamp
            metrics["timestamp"] = time.time()
            
        except Exception as e:
            self.logger.error(f"Error collecting performance metrics: {e}")
        
        return metrics

    async def _apply_parameter_changes(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Apply parameter changes and return original values."""
        original_values = {}
        
        for param_name, new_value in changes.items():
            if param_name in self.tunable_parameters:
                parameter = self.tunable_parameters[param_name]
                original_values[param_name] = parameter.current_value
                parameter.current_value = new_value
                
                # Apply the change to the actual system
                await self._apply_system_parameter(param_name, new_value)
        
        return original_values

    async def _apply_system_parameter(self, param_name: str, value: Any):
        """Apply a parameter change to the actual system."""
        try:
            if param_name == "quantization_level" and self.local_model_manager:
                # Update quantization level
                pass  # Implementation would update the model manager
            
            elif param_name == "gpu_acceleration" and self.local_model_manager:
                # Update GPU acceleration setting
                pass  # Implementation would update GPU settings
            
            # Add more parameter applications as needed
            
        except Exception as e:
            self.logger.error(f"Error applying parameter {param_name}: {e}")

    def _calculate_improvement_score(self, baseline: Dict[str, float], 
                                   result: Dict[str, float]) -> float:
        """Calculate improvement score between baseline and result metrics."""
        if not baseline or not result:
            return 0.0
        
        improvements = []
        
        # Response time improvement (lower is better)
        if "avg_response_time" in baseline and "avg_response_time" in result:
            if baseline["avg_response_time"] > 0:
                improvement = (baseline["avg_response_time"] - result["avg_response_time"]) / baseline["avg_response_time"]
                improvements.append(improvement * 0.4)  # 40% weight
        
        # CPU usage improvement (lower is better)
        if "cpu_percent" in baseline and "cpu_percent" in result:
            if baseline["cpu_percent"] > 0:
                improvement = (baseline["cpu_percent"] - result["cpu_percent"]) / baseline["cpu_percent"]
                improvements.append(improvement * 0.3)  # 30% weight
        
        # Memory usage improvement (lower is better)
        if "memory_percent" in baseline and "memory_percent" in result:
            if baseline["memory_percent"] > 0:
                improvement = (baseline["memory_percent"] - result["memory_percent"]) / baseline["memory_percent"]
                improvements.append(improvement * 0.3)  # 30% weight
        
        return sum(improvements) if improvements else 0.0

    def _average_metrics(self, metrics_samples: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate average metrics from samples."""
        if not metrics_samples:
            return {}
        
        averaged = {}
        
        # Get all metric keys
        all_keys = set()
        for sample in metrics_samples:
            all_keys.update(sample.keys())
        
        # Calculate averages
        for key in all_keys:
            if key != "timestamp":  # Skip timestamp
                values = [sample.get(key, 0) for sample in metrics_samples if key in sample]
                if values:
                    averaged[key] = statistics.mean(values)
        
        return averaged

    async def _analyze_parameter(self, parameter: TuningParameter, 
                                current_metrics: Dict[str, float]) -> Optional[TuningRecommendation]:
        """Analyze a parameter and generate recommendation if beneficial."""
        # This is a simplified analysis - in practice would be more sophisticated
        
        # Check if parameter has room for improvement
        if parameter.parameter_type == "bool":
            # For boolean parameters, recommend opposite if current performance is poor
            if current_metrics.get("cpu_percent", 0) > 80:
                return TuningRecommendation(
                    parameter_name=parameter.name,
                    current_value=parameter.current_value,
                    recommended_value=not parameter.current_value,
                    expected_improvement=0.1,
                    confidence=0.6,
                    risk_level="medium",
                    reasoning="High CPU usage suggests parameter change may help"
                )
        
        elif parameter.parameter_type == "int":
            # For integer parameters, suggest adjustments based on current performance
            if parameter.name == "context_window_size" and current_metrics.get("memory_percent", 0) > 85:
                new_value = max(parameter.min_value, parameter.current_value - parameter.step_size)
                if new_value != parameter.current_value:
                    return TuningRecommendation(
                        parameter_name=parameter.name,
                        current_value=parameter.current_value,
                        recommended_value=new_value,
                        expected_improvement=0.15,
                        confidence=0.7,
                        risk_level="low",
                        reasoning="High memory usage suggests reducing context window"
                    )
        
        return None

    def _select_recommendation(self, recommendations: List[TuningRecommendation]) -> Optional[TuningRecommendation]:
        """Select the best recommendation based on tuning strategy."""
        if not recommendations:
            return None
        
        if self.tuning_strategy == TuningStrategy.CONSERVATIVE:
            # Select lowest risk recommendation
            return min(recommendations, key=lambda r: r.risk_level == "high")
        
        elif self.tuning_strategy == TuningStrategy.AGGRESSIVE:
            # Select highest expected improvement
            return max(recommendations, key=lambda r: r.expected_improvement)
        
        else:  # BALANCED or ADAPTIVE
            # Balance improvement and risk
            scored_recommendations = []
            for rec in recommendations:
                risk_penalty = {"low": 0, "medium": 0.1, "high": 0.3}.get(rec.risk_level, 0.2)
                score = rec.expected_improvement * rec.confidence - risk_penalty
                scored_recommendations.append((score, rec))
            
            return max(scored_recommendations, key=lambda x: x[0])[1]

    def _update_usage_patterns(self, metrics: Dict[str, float]):
        """Update usage patterns for learning."""
        # Track patterns over time
        hour_of_day = datetime.now().hour
        
        with self._lock:
            self.usage_patterns[hour_of_day].append(metrics)
            
            # Keep only recent data (last 30 days)
            if len(self.usage_patterns[hour_of_day]) > 30:
                self.usage_patterns[hour_of_day] = self.usage_patterns[hour_of_day][-30:]

    def _update_learning_model(self, experiment: TuningExperiment):
        """Update the learning model based on experiment results."""
        # Simple learning model - in practice would be more sophisticated
        for param_name, param_value in experiment.parameters.items():
            if experiment.success:
                self.confidence_scores[param_name] = min(1.0, self.confidence_scores[param_name] + 0.1)
            else:
                self.confidence_scores[param_name] = max(0.0, self.confidence_scores[param_name] - 0.05)

    def _save_tuning_data(self):
        """Save tuning data to disk."""
        try:
            data = {
                "tunable_parameters": {k: asdict(v) for k, v in self.tunable_parameters.items()},
                "experiments": [asdict(exp) for exp in self.experiments],
                "confidence_scores": dict(self.confidence_scores),
                "last_tuning_time": self.last_tuning_time,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            filepath = os.path.join(self.data_path, "performance_tuner_data.json")
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving tuning data: {e}")

    def _load_tuning_data(self):
        """Load tuning data from disk."""
        try:
            filepath = os.path.join(self.data_path, "performance_tuner_data.json")
            
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                # Load confidence scores
                self.confidence_scores.update(data.get("confidence_scores", {}))
                
                # Load last tuning time
                self.last_tuning_time = data.get("last_tuning_time", 0)
                
                self.logger.info("Loaded tuning data from disk")
                
        except Exception as e:
            self.logger.error(f"Error loading tuning data: {e}")

    def get_tuning_status(self) -> Dict[str, Any]:
        """Get current tuning status and statistics."""
        return {
            "tuning_active": self.tuning_active,
            "tuning_strategy": self.tuning_strategy.value,
            "total_experiments": len(self.experiments),
            "successful_experiments": sum(1 for exp in self.experiments if exp.success),
            "last_tuning_time": self.last_tuning_time,
            "current_parameters": {k: v.current_value for k, v in self.tunable_parameters.items()},
            "confidence_scores": dict(self.confidence_scores)
        }
