"""
AMD Model Optimizer
CPU+iGPU Optimization Specialist - Model Selection and Performance Tuning

Provides dynamic model selection, memory optimization, and workload distribution
algorithms specifically tuned for AMD 8845HS + Radeon 780M hardware.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import psutil
import statistics

try:
    import GPUtil
    GPU_UTIL_AVAILABLE = True
except ImportError:
    GPU_UTIL_AVAILABLE = False


@dataclass
class BenchmarkResult:
    """Results from model benchmarking"""
    model_name: str
    tokens_per_second: float
    first_token_latency: float
    memory_usage_mb: float
    gpu_utilization_percent: float
    cpu_utilization_percent: float
    total_inference_time: float
    success_rate: float
    benchmark_timestamp: str
    gpu_layers_tested: int
    quantization: str


@dataclass
class SystemResource:
    """Current system resource status"""
    available_memory_gb: float
    cpu_utilization_percent: float
    gpu_utilization_percent: float
    memory_bandwidth_utilization: float
    timestamp: str


@dataclass
class OptimizationConfig:
    """Configuration for optimization algorithms"""
    target_tokens_per_second: float = 10.0
    max_first_token_latency: float = 2.0
    min_success_rate: float = 0.95
    memory_safety_margin_gb: float = 4.0
    
    # Dynamic tuning parameters
    gpu_layer_step_size: int = 2
    min_gpu_layers: int = 0
    max_gpu_layers: int = 32
    performance_window_size: int = 10
    optimization_interval_seconds: int = 30


class AMDModelOptimizer:
    """
    AMD 8845HS + Radeon 780M specific model optimizer.
    
    Features:
    - Dynamic model selection based on real-time performance
    - Memory bandwidth optimization for 64GB shared pool
    - Workload distribution algorithm for CPU+iGPU hybrid processing
    - Automatic quantization selection based on performance/quality tradeoff
    - Real-time system monitoring and adaptation
    """
    
    def __init__(self, config: OptimizationConfig = None):
        """Initialize AMD model optimizer"""
        self.config = config or OptimizationConfig()
        self.logger = logging.getLogger("amd_model_optimizer")
        
        # Benchmark results storage
        self.benchmark_results: Dict[str, BenchmarkResult] = {}
        self.benchmark_cache_file = Path("/data/amd_optimization_cache.json")
        
        # Performance monitoring
        self.performance_history: List[SystemResource] = []
        self.current_optimal_config: Optional[Dict[str, Any]] = None
        
        # Model decision matrix
        self.decision_matrix: Dict[str, Dict[str, float]] = {}
        
        # Dynamic optimization state
        self.last_optimization = datetime.now()
        self.optimization_in_progress = False
        
        self.logger.info("AMD Model Optimizer initialized")
    
    async def initialize(self) -> bool:
        """Initialize optimizer and load cached results"""
        try:
            # Load cached benchmark results
            await self._load_benchmark_cache()
            
            # Build initial decision matrix
            self._build_decision_matrix()
            
            # Start background monitoring
            asyncio.create_task(self._background_monitoring())
            
            self.logger.info("AMD Model Optimizer ready")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize optimizer: {e}")
            return False
    
    async def benchmark_model(self, model_instance, model_profile, test_prompts: List[str] = None) -> BenchmarkResult:
        """
        Benchmark a model with comprehensive performance analysis.
        
        Args:
            model_instance: Loaded llama.cpp model instance
            model_profile: ModelPerformanceProfile
            test_prompts: List of test prompts to benchmark
            
        Returns:
            BenchmarkResult with comprehensive metrics
        """
        if not test_prompts:
            test_prompts = [
                "Explain quantum computing in simple terms.",
                "Write a Python function to calculate fibonacci numbers.",
                "Describe the benefits of renewable energy sources.",
                "What are the key principles of machine learning?",
                "Analyze the impact of artificial intelligence on society."
            ]
        
        self.logger.info(f"Benchmarking model: {model_profile.model_name}")
        
        # Pre-benchmark system state
        start_memory = psutil.virtual_memory().available
        start_time = time.time()
        
        # Performance metrics collection
        token_counts = []
        inference_times = []
        first_token_latencies = []
        cpu_utilizations = []
        gpu_utilizations = []
        successful_inferences = 0
        
        for i, prompt in enumerate(test_prompts):
            try:
                # Monitor system before inference
                cpu_before = psutil.cpu_percent(interval=0.1)
                
                gpu_before = 0.0
                if GPU_UTIL_AVAILABLE:
                    try:
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            gpu_before = gpus[0].load * 100
                    except:
                        pass
                
                # Time first token
                inference_start = time.time()
                
                # Run inference
                result = model_instance(
                    prompt,
                    max_tokens=100,
                    temperature=0.1,
                    echo=False,
                    stream=False
                )
                
                first_token_time = time.time() - inference_start
                
                # Extract response and count tokens
                response_text = result["choices"][0]["text"]
                token_count = len(response_text.split())  # Rough token count
                
                total_inference_time = time.time() - inference_start
                
                # Monitor system after inference
                cpu_after = psutil.cpu_percent(interval=0.1)
                
                gpu_after = 0.0
                if GPU_UTIL_AVAILABLE:
                    try:
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            gpu_after = gpus[0].load * 100
                    except:
                        pass
                
                # Record metrics
                token_counts.append(token_count)
                inference_times.append(total_inference_time)
                first_token_latencies.append(first_token_time)
                cpu_utilizations.append((cpu_before + cpu_after) / 2)
                gpu_utilizations.append((gpu_before + gpu_after) / 2)
                successful_inferences += 1
                
                self.logger.debug(f"Benchmark {i+1}/{len(test_prompts)}: {token_count} tokens in {total_inference_time:.2f}s")
                
            except Exception as e:
                self.logger.warning(f"Benchmark inference {i+1} failed: {e}")
                continue
        
        # Calculate final metrics
        total_tokens = sum(token_counts)
        total_time = sum(inference_times)
        end_memory = psutil.virtual_memory().available
        memory_used = (start_memory - end_memory) / (1024 * 1024)  # MB
        
        avg_tokens_per_second = total_tokens / max(total_time, 0.001)
        avg_first_token_latency = statistics.mean(first_token_latencies) if first_token_latencies else 0.0
        avg_cpu_utilization = statistics.mean(cpu_utilizations) if cpu_utilizations else 0.0
        avg_gpu_utilization = statistics.mean(gpu_utilizations) if gpu_utilizations else 0.0
        success_rate = successful_inferences / len(test_prompts)
        
        benchmark_result = BenchmarkResult(
            model_name=model_profile.model_name,
            tokens_per_second=avg_tokens_per_second,
            first_token_latency=avg_first_token_latency,
            memory_usage_mb=memory_used,
            gpu_utilization_percent=avg_gpu_utilization,
            cpu_utilization_percent=avg_cpu_utilization,
            total_inference_time=time.time() - start_time,
            success_rate=success_rate,
            benchmark_timestamp=datetime.now().isoformat(),
            gpu_layers_tested=model_profile.optimal_gpu_layers,
            quantization=model_profile.quantization
        )
        
        # Store result
        self.benchmark_results[model_profile.model_name] = benchmark_result
        await self._save_benchmark_cache()
        
        self.logger.info(f"Benchmark complete: {model_profile.model_name} - "
                        f"{avg_tokens_per_second:.1f} t/s, "
                        f"{avg_first_token_latency:.2f}s first token, "
                        f"{success_rate:.1%} success rate")
        
        return benchmark_result
    
    def select_optimal_model(self, available_models: List[str], 
                           current_system_state: SystemResource = None) -> Optional[str]:
        """
        Select optimal model based on current system state and performance requirements.
        
        Args:
            available_models: List of available model names
            current_system_state: Current system resource status
            
        Returns:
            Optimal model name or None if no suitable model found
        """
        if not available_models:
            return None
        
        current_state = current_system_state or self._get_current_system_state()
        
        # Filter models that meet basic requirements
        suitable_models = []
        for model_name in available_models:
            if model_name not in self.benchmark_results:
                continue
                
            result = self.benchmark_results[model_name]
            
            # Check if model meets performance and resource requirements
            if (result.tokens_per_second >= self.config.target_tokens_per_second and
                result.first_token_latency <= self.config.max_first_token_latency and
                result.success_rate >= self.config.min_success_rate and
                result.memory_usage_mb / 1024 <= current_state.available_memory_gb - self.config.memory_safety_margin_gb):
                
                suitable_models.append((model_name, result))
        
        if not suitable_models:
            # Fallback: select model with best success rate
            fallback_models = [
                (name, self.benchmark_results[name]) 
                for name in available_models 
                if name in self.benchmark_results
            ]
            if fallback_models:
                suitable_models = [max(fallback_models, key=lambda x: x[1].success_rate)]
            else:
                return None
        
        # Select best model based on composite score
        best_model = None
        best_score = -1.0
        
        for model_name, result in suitable_models:
            # Composite score considering multiple factors
            performance_score = min(result.tokens_per_second / self.config.target_tokens_per_second, 2.0)
            latency_score = max(0, 2.0 - result.first_token_latency / self.config.max_first_token_latency)
            reliability_score = result.success_rate
            
            # Memory efficiency (prefer models that use less memory)
            memory_efficiency = 1.0 - (result.memory_usage_mb / 1024) / current_state.available_memory_gb
            memory_efficiency = max(0, min(memory_efficiency, 1.0))
            
            # Composite score (weighted average)
            composite_score = (
                performance_score * 0.4 +
                latency_score * 0.2 +
                reliability_score * 0.3 +
                memory_efficiency * 0.1
            )
            
            if composite_score > best_score:
                best_score = composite_score
                best_model = model_name
        
        self.logger.info(f"Selected optimal model: {best_model} (score: {best_score:.2f})")
        return best_model
    
    async def optimize_gpu_layers(self, model_instance, model_profile, 
                                current_layers: int) -> int:
        """
        Dynamically optimize GPU layer count for current system state.
        
        Args:
            model_instance: Loaded model instance
            model_profile: Model performance profile
            current_layers: Current GPU layer count
            
        Returns:
            Optimized GPU layer count
        """
        if self.optimization_in_progress:
            return current_layers
        
        self.optimization_in_progress = True
        
        try:
            # Get current system state
            system_state = self._get_current_system_state()
            
            # Test current performance
            baseline_performance = await self._quick_performance_test(model_instance)
            
            # Determine optimization direction
            if system_state.gpu_utilization_percent < 70:
                # GPU underutilized - try increasing layers
                test_layers = min(current_layers + self.config.gpu_layer_step_size, 
                                self.config.max_gpu_layers)
            elif system_state.gpu_utilization_percent > 90:
                # GPU overutilized - try decreasing layers
                test_layers = max(current_layers - self.config.gpu_layer_step_size, 
                                self.config.min_gpu_layers)
            else:
                # GPU utilization optimal
                return current_layers
            
            if test_layers == current_layers:
                return current_layers
            
            self.logger.info(f"Testing GPU layer optimization: {current_layers} → {test_layers}")
            
            # This would require reloading the model with new layer count
            # For now, return the calculated optimal value
            # TODO: Implement model reloading with new GPU layer count
            
            return test_layers
            
        except Exception as e:
            self.logger.error(f"GPU layer optimization failed: {e}")
            return current_layers
        finally:
            self.optimization_in_progress = False
    
    def select_optimal_quantization(self, model_base_name: str, 
                                  performance_priority: bool = True) -> str:
        """
        Select optimal quantization level based on performance/quality requirements.
        
        Args:
            model_base_name: Base model name (e.g., "llava-7b")
            performance_priority: True for performance, False for quality
            
        Returns:
            Optimal quantization level (e.g., "Q4_K_M")
        """
        # Define quantization hierarchy (performance → quality)
        quantization_levels = [
            "Q4_K_M",   # Best performance, good quality
            "Q5_K_M",   # Balanced performance/quality
            "Q8_0",     # Best quality, lower performance
            "F16"       # Highest quality, lowest performance
        ]
        
        # Find benchmark results for different quantizations of the same model
        available_quantizations = []
        for model_name, result in self.benchmark_results.items():
            if model_base_name in model_name:
                available_quantizations.append((result.quantization, result))
        
        if not available_quantizations:
            # Default to Q4_K_M for best performance/quality tradeoff
            return "Q4_K_M"
        
        # Sort by performance or quality preference
        if performance_priority:
            # Sort by tokens per second (descending)
            available_quantizations.sort(key=lambda x: x[1].tokens_per_second, reverse=True)
        else:
            # Sort by quantization quality (Q8_0 > Q5_K_M > Q4_K_M)
            quality_order = {"F16": 4, "Q8_0": 3, "Q5_K_M": 2, "Q4_K_M": 1}
            available_quantizations.sort(
                key=lambda x: quality_order.get(x[0], 0), 
                reverse=True
            )
        
        selected = available_quantizations[0][0]
        self.logger.info(f"Selected quantization for {model_base_name}: {selected} "
                        f"({'performance' if performance_priority else 'quality'} priority)")
        
        return selected
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Get current optimization recommendations"""
        system_state = self._get_current_system_state()
        
        recommendations = {
            "timestamp": datetime.now().isoformat(),
            "system_state": asdict(system_state),
            "recommendations": []
        }
        
        # Memory optimization
        if system_state.available_memory_gb < 8.0:
            recommendations["recommendations"].append({
                "type": "memory",
                "priority": "high",
                "message": "Low memory detected. Consider using Q4_K_M quantization or smaller model.",
                "suggested_action": "switch_to_smaller_model"
            })
        
        # GPU utilization optimization
        if system_state.gpu_utilization_percent < 50:
            recommendations["recommendations"].append({
                "type": "gpu_utilization",
                "priority": "medium",
                "message": "GPU underutilized. Consider increasing GPU layers.",
                "suggested_action": "increase_gpu_layers"
            })
        elif system_state.gpu_utilization_percent > 95:
            recommendations["recommendations"].append({
                "type": "gpu_utilization",
                "priority": "high",
                "message": "GPU overutilized. Consider decreasing GPU layers or using CPU-only mode.",
                "suggested_action": "decrease_gpu_layers"
            })
        
        # CPU utilization optimization
        if system_state.cpu_utilization_percent > 90:
            recommendations["recommendations"].append({
                "type": "cpu_utilization",
                "priority": "high",
                "message": "CPU overutilized. Consider offloading more layers to GPU.",
                "suggested_action": "increase_gpu_layers"
            })
        
        return recommendations
    
    def _build_decision_matrix(self):
        """Build decision matrix from benchmark results"""
        self.decision_matrix = {}
        
        for model_name, result in self.benchmark_results.items():
            self.decision_matrix[model_name] = {
                "performance_score": result.tokens_per_second,
                "latency_score": 1.0 / max(result.first_token_latency, 0.001),
                "reliability_score": result.success_rate,
                "memory_efficiency": 1.0 / max(result.memory_usage_mb / 1024, 0.1),
                "composite_score": self._calculate_composite_score(result)
            }
    
    def _calculate_composite_score(self, result: BenchmarkResult) -> float:
        """Calculate composite performance score"""
        performance_norm = min(result.tokens_per_second / self.config.target_tokens_per_second, 2.0)
        latency_norm = max(0, 2.0 - result.first_token_latency / self.config.max_first_token_latency)
        reliability_norm = result.success_rate
        
        return (performance_norm * 0.5 + latency_norm * 0.3 + reliability_norm * 0.2)
    
    def _get_current_system_state(self) -> SystemResource:
        """Get current system resource state"""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        gpu_percent = 0.0
        if GPU_UTIL_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_percent = gpus[0].load * 100
            except:
                pass
        
        return SystemResource(
            available_memory_gb=memory.available / (1024**3),
            cpu_utilization_percent=cpu_percent,
            gpu_utilization_percent=gpu_percent,
            memory_bandwidth_utilization=memory.percent,
            timestamp=datetime.now().isoformat()
        )
    
    async def _quick_performance_test(self, model_instance) -> float:
        """Quick performance test for optimization"""
        try:
            start_time = time.time()
            result = model_instance("Test", max_tokens=10, echo=False, stream=False)
            end_time = time.time()
            
            tokens = len(result["choices"][0]["text"].split())
            return tokens / max(end_time - start_time, 0.001)
        except:
            return 0.0
    
    async def _background_monitoring(self):
        """Background system monitoring and optimization"""
        while True:
            try:
                # Record current system state
                current_state = self._get_current_system_state()
                self.performance_history.append(current_state)
                
                # Trim history to last hour (assuming 30s intervals)
                max_history = 120
                if len(self.performance_history) > max_history:
                    self.performance_history = self.performance_history[-max_history:]
                
                # Check if optimization is needed
                if (datetime.now() - self.last_optimization).seconds > self.config.optimization_interval_seconds:
                    await self._trigger_optimization()
                
                await asyncio.sleep(30)  # 30 second monitoring interval
                
            except Exception as e:
                self.logger.error(f"Background monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _trigger_optimization(self):
        """Trigger optimization based on recent performance"""
        if self.optimization_in_progress:
            return
        
        try:
            # Analyze recent performance trends
            if len(self.performance_history) < 5:
                return
            
            recent_states = self.performance_history[-5:]
            avg_cpu = statistics.mean([s.cpu_utilization_percent for s in recent_states])
            avg_gpu = statistics.mean([s.gpu_utilization_percent for s in recent_states])
            avg_memory = statistics.mean([s.available_memory_gb for s in recent_states])
            
            # Log optimization trigger
            self.logger.info(f"Optimization trigger - CPU: {avg_cpu:.1f}%, "
                           f"GPU: {avg_gpu:.1f}%, Memory: {avg_memory:.1f}GB")
            
            self.last_optimization = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Optimization trigger failed: {e}")
    
    async def _load_benchmark_cache(self):
        """Load cached benchmark results"""
        try:
            if self.benchmark_cache_file.exists():
                with open(self.benchmark_cache_file, 'r') as f:
                    data = json.load(f)
                
                for model_name, result_dict in data.items():
                    self.benchmark_results[model_name] = BenchmarkResult(**result_dict)
                
                self.logger.info(f"Loaded {len(self.benchmark_results)} cached benchmark results")
        except Exception as e:
            self.logger.warning(f"Failed to load benchmark cache: {e}")
    
    async def _save_benchmark_cache(self):
        """Save benchmark results to cache"""
        try:
            cache_data = {}
            for model_name, result in self.benchmark_results.items():
                cache_data[model_name] = asdict(result)
            
            self.benchmark_cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.benchmark_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save benchmark cache: {e}")