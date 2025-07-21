"""
Performance Benchmark Suite for Privacy Pipeline
Tests privacy processing performance to ensure <5 second target on AMD 780M
"""

import asyncio
import logging
import time
import statistics
import cv2
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import json
from dataclasses import dataclass, field
from datetime import datetime

from .privacy_config import PrivacyConfig, PrivacyLevel
from .privacy_pipeline import PrivacyPipeline


@dataclass
class BenchmarkResult:
    """Result from a single benchmark test"""
    test_name: str
    privacy_level: str
    image_size: Tuple[int, int]
    processing_time: float
    regions_processed: int
    memory_usage_mb: float
    gpu_utilization: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Complete benchmark suite results"""
    suite_name: str
    timestamp: datetime
    hardware_info: Dict[str, Any]
    results: List[BenchmarkResult] = field(default_factory=list)
    summary_stats: Dict[str, Any] = field(default_factory=dict)


class PrivacyPerformanceBenchmark:
    """
    Performance benchmark suite for privacy pipeline
    
    Features:
    - Multi-resolution image testing
    - Privacy level performance comparison
    - Memory and GPU utilization monitoring
    - Statistical analysis and reporting
    - Target <5 second processing verification
    """
    
    def __init__(self, config: PrivacyConfig):
        """
        Initialize performance benchmark
        
        Args:
            config: Privacy pipeline configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Test parameters
        self.test_resolutions = [
            (640, 480),     # VGA
            (1280, 720),    # HD
            (1920, 1080),   # Full HD
            (2560, 1440),   # QHD
            (3840, 2160)    # 4K
        ]
        
        self.privacy_levels = [PrivacyLevel.SPEED, PrivacyLevel.BALANCED, PrivacyLevel.PARANOID]
        
        # Performance targets
        self.target_processing_time = 5.0  # 5 seconds max
        self.target_memory_usage = 4096    # 4GB max
        
        self.logger.info("Performance benchmark suite initialized")
    
    async def run_full_benchmark(self, iterations: int = 3) -> BenchmarkSuite:
        """
        Run complete benchmark suite
        
        Args:
            iterations: Number of iterations per test
            
        Returns:
            Complete benchmark results
        """
        start_time = datetime.now()
        
        self.logger.info(f"Starting full benchmark suite with {iterations} iterations")
        
        # Initialize benchmark suite
        suite = BenchmarkSuite(
            suite_name=f"Privacy Pipeline Benchmark {start_time.strftime('%Y%m%d_%H%M%S')}",
            timestamp=start_time,
            hardware_info=self._get_hardware_info()
        )
        
        # Run benchmarks for each privacy level and resolution
        for privacy_level in self.privacy_levels:
            for resolution in self.test_resolutions:
                test_name = f"{privacy_level.value}_{resolution[0]}x{resolution[1]}"
                
                self.logger.info(f"Running benchmark: {test_name}")
                
                # Run multiple iterations
                iteration_results = []
                for i in range(iterations):
                    result = await self._run_single_benchmark(
                        test_name, privacy_level, resolution
                    )
                    iteration_results.append(result)
                
                # Calculate average results
                avg_result = self._calculate_average_result(iteration_results)
                suite.results.append(avg_result)
        
        # Generate summary statistics
        suite.summary_stats = self._generate_summary_stats(suite.results)
        
        # Log results
        self._log_benchmark_results(suite)
        
        return suite
    
    async def _run_single_benchmark(self, test_name: str, privacy_level: PrivacyLevel, 
                                  resolution: Tuple[int, int]) -> BenchmarkResult:
        """
        Run a single benchmark test
        
        Args:
            test_name: Name of the test
            privacy_level: Privacy level to test
            resolution: Image resolution (width, height)
            
        Returns:
            Benchmark result
        """
        try:
            # Create test image
            test_image = self._create_test_image(resolution)
            
            # Initialize privacy pipeline with test configuration
            test_config = self._create_test_config(privacy_level)
            pipeline = PrivacyPipeline(test_config)
            
            if not await pipeline.initialize():
                return BenchmarkResult(
                    test_name=test_name,
                    privacy_level=privacy_level.value,
                    image_size=resolution,
                    processing_time=0.0,
                    regions_processed=0,
                    memory_usage_mb=0.0,
                    gpu_utilization=0.0,
                    success=False,
                    error_message="Pipeline initialization failed"
                )
            
            # Warm up (first run is often slower)
            await pipeline.process_image(test_image)
            
            # Measure memory before processing
            memory_before = self._get_memory_usage()
            
            # Run actual benchmark
            start_time = time.time()
            result = await pipeline.process_image(test_image, privacy_level)
            processing_time = time.time() - start_time
            
            # Measure memory after processing
            memory_after = self._get_memory_usage()
            memory_usage = memory_after - memory_before
            
            # Get GPU utilization (if available)
            gpu_utilization = self._get_gpu_utilization()
            
            # Clean up
            await pipeline.shutdown()
            
            return BenchmarkResult(
                test_name=test_name,
                privacy_level=privacy_level.value,
                image_size=resolution,
                processing_time=processing_time,
                regions_processed=result.get("regions_processed", 0),
                memory_usage_mb=memory_usage,
                gpu_utilization=gpu_utilization,
                success=result.get("status") == "success",
                metadata={
                    "target_met": processing_time <= self.target_processing_time,
                    "privacy_metadata": result.get("privacy_metadata", {}),
                    "pipeline_metadata": result.get("metadata", {})
                }
            )
            
        except Exception as e:
            self.logger.error(f"Benchmark {test_name} failed: {e}")
            return BenchmarkResult(
                test_name=test_name,
                privacy_level=privacy_level.value,
                image_size=resolution,
                processing_time=0.0,
                regions_processed=0,
                memory_usage_mb=0.0,
                gpu_utilization=0.0,
                success=False,
                error_message=str(e)
            )
    
    def _create_test_image(self, resolution: Tuple[int, int]) -> np.ndarray:
        """
        Create synthetic test image with privacy-sensitive content
        
        Args:
            resolution: Image resolution (width, height)
            
        Returns:
            Test image as numpy array
        """
        width, height = resolution
        
        # Create base image with gradient background
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add gradient background
        for y in range(height):
            for x in range(width):
                image[y, x] = [
                    min(255, x * 255 // width),
                    min(255, y * 255 // height),
                    min(255, (x + y) * 255 // (width + height))
                ]
        
        # Add simulated face regions (rectangles that look like faces)
        face_count = max(1, min(5, (width * height) // (640 * 480)))
        for i in range(face_count):
            x = int(width * 0.2 + (i * width * 0.6 / face_count))
            y = int(height * 0.3)
            w = int(width * 0.1)
            h = int(height * 0.15)
            
            # Draw face-like rectangle
            cv2.rectangle(image, (x, y), (x + w, y + h), (255, 220, 177), -1)
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 0), 2)
            
            # Add eyes
            eye_y = y + h // 3
            cv2.circle(image, (x + w // 3, eye_y), 5, (0, 0, 0), -1)
            cv2.circle(image, (x + 2 * w // 3, eye_y), 5, (0, 0, 0), -1)
        
        # Add simulated text regions
        text_count = max(2, min(8, (width * height) // (320 * 240)))
        for i in range(text_count):
            x = int(width * 0.1 + (i % 3) * width * 0.3)
            y = int(height * 0.7 + (i // 3) * height * 0.1)
            w = int(width * 0.2)
            h = int(height * 0.05)
            
            # Draw text-like rectangle
            cv2.rectangle(image, (x, y), (x + w, y + h), (255, 255, 255), -1)
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 0), 1)
            
            # Add simulated text lines
            for line in range(3):
                line_y = y + (line + 1) * h // 4
                cv2.line(image, (x + 5, line_y), (x + w - 5, line_y), (0, 0, 0), 1)
        
        # Add simulated objects (screens, license plates)
        if width >= 1280:  # Only for larger images
            # Laptop screen
            laptop_x = int(width * 0.1)
            laptop_y = int(height * 0.5)
            laptop_w = int(width * 0.3)
            laptop_h = int(height * 0.2)
            cv2.rectangle(image, (laptop_x, laptop_y), (laptop_x + laptop_w, laptop_y + laptop_h), (50, 50, 50), -1)
            cv2.rectangle(image, (laptop_x + 10, laptop_y + 10), (laptop_x + laptop_w - 10, laptop_y + laptop_h - 10), (100, 150, 255), -1)
            
            # License plate
            plate_x = int(width * 0.6)
            plate_y = int(height * 0.8)
            plate_w = int(width * 0.15)
            plate_h = int(height * 0.05)
            cv2.rectangle(image, (plate_x, plate_y), (plate_x + plate_w, plate_y + plate_h), (255, 255, 255), -1)
            cv2.rectangle(image, (plate_x, plate_y), (plate_x + plate_w, plate_y + plate_h), (0, 0, 0), 2)
        
        return image
    
    def _create_test_config(self, privacy_level: PrivacyLevel) -> PrivacyConfig:
        """Create test configuration for privacy level"""
        test_config = PrivacyConfig(
            enabled=True,
            level=privacy_level,
            model_base_path="/data/privacy_models"
        )
        
        # Enable performance logging for benchmarks
        test_config.enable_performance_logging = True
        
        return test_config
    
    def _get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware information for benchmark context"""
        import platform
        import psutil
        
        info = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "python_version": platform.python_version()
        }
        
        # Try to get GPU info
        try:
            import subprocess
            result = subprocess.run(['lspci'], capture_output=True, text=True)
            if 'AMD' in result.stdout and ('Radeon' in result.stdout or 'GPU' in result.stdout):
                info["gpu"] = "AMD Radeon (detected via lspci)"
        except:
            info["gpu"] = "Unknown"
        
        return info
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    
    def _get_gpu_utilization(self) -> float:
        """Get GPU utilization percentage (if available)"""
        try:
            # Try to get AMD GPU utilization
            import subprocess
            result = subprocess.run(['radeontop', '-d', '-', '-l', '1'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                # Parse radeontop output
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'gpu' in line.lower():
                        # Extract utilization percentage
                        parts = line.split()
                        for part in parts:
                            if '%' in part:
                                return float(part.replace('%', ''))
        except:
            pass
        
        return 0.0  # Return 0 if unable to get GPU utilization
    
    def _calculate_average_result(self, results: List[BenchmarkResult]) -> BenchmarkResult:
        """Calculate average result from multiple iterations"""
        if not results:
            raise ValueError("No results to average")
        
        first_result = results[0]
        
        # Calculate averages
        avg_processing_time = statistics.mean([r.processing_time for r in results if r.success])
        avg_memory_usage = statistics.mean([r.memory_usage_mb for r in results if r.success])
        avg_gpu_utilization = statistics.mean([r.gpu_utilization for r in results if r.success])
        avg_regions_processed = statistics.mean([r.regions_processed for r in results if r.success])
        
        success_rate = sum(1 for r in results if r.success) / len(results)
        
        return BenchmarkResult(
            test_name=first_result.test_name,
            privacy_level=first_result.privacy_level,
            image_size=first_result.image_size,
            processing_time=avg_processing_time,
            regions_processed=int(avg_regions_processed),
            memory_usage_mb=avg_memory_usage,
            gpu_utilization=avg_gpu_utilization,
            success=success_rate >= 0.8,  # 80% success rate threshold
            metadata={
                "iterations": len(results),
                "success_rate": success_rate,
                "processing_time_std": statistics.stdev([r.processing_time for r in results if r.success]) if len([r for r in results if r.success]) > 1 else 0,
                "target_met": avg_processing_time <= self.target_processing_time
            }
        )
    
    def _generate_summary_stats(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Generate summary statistics from benchmark results"""
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            return {"error": "No successful benchmark results"}
        
        processing_times = [r.processing_time for r in successful_results]
        memory_usage = [r.memory_usage_mb for r in successful_results]
        
        # Performance targets analysis
        target_met_count = sum(1 for r in successful_results if r.processing_time <= self.target_processing_time)
        target_met_percentage = (target_met_count / len(successful_results)) * 100
        
        # Privacy level analysis
        level_stats = {}
        for level in self.privacy_levels:
            level_results = [r for r in successful_results if r.privacy_level == level.value]
            if level_results:
                level_stats[level.value] = {
                    "avg_processing_time": statistics.mean([r.processing_time for r in level_results]),
                    "avg_memory_usage": statistics.mean([r.memory_usage_mb for r in level_results]),
                    "target_met_percentage": (sum(1 for r in level_results if r.processing_time <= self.target_processing_time) / len(level_results)) * 100
                }
        
        return {
            "total_tests": len(results),
            "successful_tests": len(successful_results),
            "success_rate": len(successful_results) / len(results) if results else 0,
            "target_met_percentage": target_met_percentage,
            "performance_stats": {
                "avg_processing_time": statistics.mean(processing_times),
                "min_processing_time": min(processing_times),
                "max_processing_time": max(processing_times),
                "processing_time_std": statistics.stdev(processing_times) if len(processing_times) > 1 else 0,
                "avg_memory_usage": statistics.mean(memory_usage),
                "max_memory_usage": max(memory_usage)
            },
            "privacy_level_stats": level_stats,
            "recommendations": self._generate_recommendations(successful_results)
        }
    
    def _generate_recommendations(self, results: List[BenchmarkResult]) -> List[str]:
        """Generate performance recommendations based on results"""
        recommendations = []
        
        processing_times = [r.processing_time for r in results]
        avg_time = statistics.mean(processing_times)
        max_time = max(processing_times)
        
        if max_time > self.target_processing_time:
            recommendations.append(f"Performance target not met: max time {max_time:.2f}s > {self.target_processing_time}s")
            recommendations.append("Consider using Speed privacy level for time-critical applications")
        
        if avg_time > self.target_processing_time * 0.8:
            recommendations.append("Average processing time close to target - monitor for performance degradation")
        
        memory_usage = [r.memory_usage_mb for r in results]
        max_memory = max(memory_usage)
        
        if max_memory > self.target_memory_usage:
            recommendations.append(f"High memory usage detected: {max_memory:.0f}MB > {self.target_memory_usage}MB")
            recommendations.append("Consider enabling model swapping to reduce memory footprint")
        
        # GPU utilization recommendations
        gpu_usage = [r.gpu_utilization for r in results if r.gpu_utilization > 0]
        if gpu_usage:
            avg_gpu = statistics.mean(gpu_usage)
            if avg_gpu < 50:
                recommendations.append("Low GPU utilization - check ROCm/DirectML setup for AMD 780M optimization")
        else:
            recommendations.append("No GPU utilization detected - verify ONNX Runtime GPU providers are working")
        
        return recommendations
    
    def _log_benchmark_results(self, suite: BenchmarkSuite):
        """Log benchmark results summary"""
        self.logger.info("=== PRIVACY PIPELINE BENCHMARK RESULTS ===")
        self.logger.info(f"Suite: {suite.suite_name}")
        self.logger.info(f"Hardware: {suite.hardware_info.get('processor', 'Unknown')} | "
                        f"Memory: {suite.hardware_info.get('memory_total_gb', 'Unknown')}GB | "
                        f"GPU: {suite.hardware_info.get('gpu', 'Unknown')}")
        
        stats = suite.summary_stats
        self.logger.info(f"Tests: {stats.get('successful_tests', 0)}/{stats.get('total_tests', 0)} successful")
        self.logger.info(f"Target Met: {stats.get('target_met_percentage', 0):.1f}% of tests")
        
        perf_stats = stats.get('performance_stats', {})
        self.logger.info(f"Avg Processing Time: {perf_stats.get('avg_processing_time', 0):.3f}s")
        self.logger.info(f"Max Processing Time: {perf_stats.get('max_processing_time', 0):.3f}s")
        self.logger.info(f"Avg Memory Usage: {perf_stats.get('avg_memory_usage', 0):.1f}MB")
        
        # Log recommendations
        recommendations = stats.get('recommendations', [])
        if recommendations:
            self.logger.info("RECOMMENDATIONS:")
            for rec in recommendations:
                self.logger.info(f"  - {rec}")
        
        self.logger.info("==========================================")
    
    def save_results(self, suite: BenchmarkSuite, output_path: str):
        """Save benchmark results to JSON file"""
        try:
            # Convert to serializable format
            results_data = {
                "suite_name": suite.suite_name,
                "timestamp": suite.timestamp.isoformat(),
                "hardware_info": suite.hardware_info,
                "summary_stats": suite.summary_stats,
                "results": [
                    {
                        "test_name": r.test_name,
                        "privacy_level": r.privacy_level,
                        "image_size": r.image_size,
                        "processing_time": r.processing_time,
                        "regions_processed": r.regions_processed,
                        "memory_usage_mb": r.memory_usage_mb,
                        "gpu_utilization": r.gpu_utilization,
                        "success": r.success,
                        "error_message": r.error_message,
                        "metadata": r.metadata
                    }
                    for r in suite.results
                ]
            }
            
            with open(output_path, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            self.logger.info(f"Benchmark results saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save benchmark results: {e}")


async def run_performance_benchmark(config_path: str = "config.yaml", 
                                  iterations: int = 3) -> BenchmarkSuite:
    """
    Convenience function to run performance benchmark
    
    Args:
        config_path: Path to privacy configuration
        iterations: Number of iterations per test
        
    Returns:
        Benchmark suite results
    """
    # Load configuration
    import yaml
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    privacy_config_data = config_data.get('privacy', {})
    privacy_config = PrivacyConfig.from_dict(privacy_config_data)
    
    # Run benchmark
    benchmark = PrivacyPerformanceBenchmark(privacy_config)
    results = await benchmark.run_full_benchmark(iterations)
    
    # Save results
    output_path = f"privacy_benchmark_{results.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    benchmark.save_results(results, output_path)
    
    return results


if __name__ == "__main__":
    # Run benchmark from command line
    import sys
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    print(f"Running Privacy Pipeline Performance Benchmark")
    print(f"Config: {config_path}")
    print(f"Iterations: {iterations}")
    print("=" * 50)
    
    results = asyncio.run(run_performance_benchmark(config_path, iterations))
    
    print("\nBenchmark completed successfully!")
    print(f"Results saved to privacy_benchmark_{results.timestamp.strftime('%Y%m%d_%H%M%S')}.json")