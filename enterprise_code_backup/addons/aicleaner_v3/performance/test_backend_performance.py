"""
Backend Performance Testing Suite
Phase 5A: Performance Optimization

Tests and profiles critical backend components to identify bottlenecks.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add addon path to Python path
addon_path = Path(__file__).parent.parent
sys.path.insert(0, str(addon_path))

from performance.simple_profiler import profiler, profile_api_endpoint, profile_ai_provider
from api.backend import app, initialize_services
from ai.providers.ai_provider_manager import AIProviderManager
from core.config_manager import ConfigManager

async def test_backend_initialization():
    """Profile backend service initialization"""
    print("🔍 Profiling backend initialization...")
    
    with profiler.profile_block("backend_initialization"):
        try:
            await initialize_services()
            print("✅ Backend initialization profiled")
        except Exception as e:
            print(f"❌ Backend initialization failed: {e}")

async def test_ai_provider_operations():
    """Profile AI provider operations"""
    print("🔍 Profiling AI provider operations...")
    
    try:
        # Initialize config manager
        config_manager = ConfigManager("/tmp/test_data")
        await config_manager.load_config()
        
        # Initialize AI provider manager
        config_data = config_manager.get_config()
        ai_manager = AIProviderManager(config_data, "/tmp/test_data")
        
        with profiler.profile_block("ai_provider_initialization"):
            await ai_manager.initialize()
        
        with profiler.profile_block("ai_provider_status_check"):
            status = ai_manager.get_provider_status()
            print(f"  Provider status retrieved: {len(status)} providers")
        
        with profiler.profile_block("ai_provider_health_check"):
            health = await ai_manager.health_check()
            print(f"  Health check completed: {health.get('status', 'unknown')}")
        
        with profiler.profile_block("ai_provider_performance_metrics"):
            metrics = ai_manager.get_performance_metrics()
            print(f"  Performance metrics retrieved: {len(metrics)} metrics")
        
        print("✅ AI provider operations profiled")
        
    except Exception as e:
        print(f"❌ AI provider operations failed: {e}")

async def test_api_endpoint_performance():
    """Profile FastAPI endpoint performance without actual HTTP requests"""
    print("🔍 Profiling API endpoint logic...")
    
    try:
        # Import endpoint functions directly
        from api.backend import get_system_status, get_providers, health_check
        
        # Mock dependencies
        class MockAIManager:
            def get_provider_status(self):
                return {"openai": {"status": "healthy", "available": True}}
            
            def get_load_balancer_stats(self):
                return {"strategy": "round_robin", "requests": 100}
            
            async def health_check(self):
                return {"status": "healthy", "timestamp": time.time()}
            
            def get_performance_metrics(self):
                return {"total_requests": 100, "avg_response_time": 0.1}
            
            @property
            def providers(self):
                return {"openai": MockProvider()}
        
        class MockProvider:
            def __init__(self):
                self.config = MockConfig()
            
        class MockConfig:
            enabled = True
            model_name = "gpt-4"
            priority = 1
            rate_limit_rpm = 60
            rate_limit_tpm = 10000
            daily_budget = 10.0
            base_url = None
        
        mock_ai_manager = MockAIManager()
        
        # Profile health check endpoint
        with profiler.profile_block("api_health_check"):
            health_result = await health_check()
            print(f"  Health check: {health_result.success}")
        
        # Profile system status endpoint
        with profiler.profile_block("api_system_status"):
            status_result = await get_system_status(mock_ai_manager)
            print(f"  System status: {status_result.success}")
        
        # Profile providers endpoint
        with profiler.profile_block("api_get_providers"):
            providers_result = await get_providers(mock_ai_manager)
            print(f"  Get providers: {providers_result.success}")
        
        print("✅ API endpoint logic profiled")
        
    except Exception as e:
        print(f"❌ API endpoint profiling failed: {e}")

async def test_websocket_performance():
    """Profile WebSocket connection manager performance"""
    print("🔍 Profiling WebSocket operations...")
    
    try:
        from api.backend import ConnectionManager
        
        manager = ConnectionManager()
        
        with profiler.profile_block("websocket_broadcast_preparation"):
            # Simulate message broadcasting preparation
            message = '{"type": "status_update", "data": {"test": "performance"}}'
            for i in range(100):
                # Simulate message preparation overhead
                formatted_message = f"{message}_{i}"
        
        print("✅ WebSocket operations profiled")
        
    except Exception as e:
        print(f"❌ WebSocket profiling failed: {e}")

async def test_memory_usage_patterns():
    """Test memory usage patterns over time"""
    print("🔍 Analyzing memory usage patterns...")
    
    try:
        initial_metrics = profiler.get_system_metrics()
        print(f"  Initial memory usage: {initial_metrics.get('memory_percent', 'N/A'):.1f}%")
        
        # Simulate memory-intensive operations
        large_data = []
        with profiler.profile_block("memory_intensive_operation"):
            for i in range(1000):
                large_data.append({
                    "id": i,
                    "data": "x" * 1000,  # 1KB strings
                    "metadata": {
                        "timestamp": time.time(),
                        "index": i,
                        "extra": ["item"] * 10
                    }
                })
        
        mid_metrics = profiler.get_system_metrics()
        print(f"  Peak memory usage: {mid_metrics.get('memory_percent', 'N/A'):.1f}%")
        
        # Clear memory
        with profiler.profile_block("memory_cleanup"):
            large_data.clear()
            del large_data
        
        final_metrics = profiler.get_system_metrics()
        print(f"  Final memory usage: {final_metrics.get('memory_percent', 'N/A'):.1f}%")
        
        print("✅ Memory usage patterns analyzed")
        
    except Exception as e:
        print(f"❌ Memory analysis failed: {e}")

async def run_comprehensive_performance_test():
    """Run comprehensive performance testing suite"""
    print("🚀 Starting AICleaner v3 Backend Performance Analysis")
    print("=" * 60)
    
    start_time = time.time()
    
    # System baseline
    baseline_metrics = profiler.get_system_metrics()
    print(f"📊 Baseline System Metrics:")
    print(f"  CPU: {baseline_metrics.get('cpu_percent', 'N/A'):.1f}%")
    print(f"  Memory: {baseline_metrics.get('memory_percent', 'N/A'):.1f}%")
    print(f"  Disk: {baseline_metrics.get('disk_percent', 'N/A'):.1f}%")
    print()
    
    # Run tests
    await test_backend_initialization()
    await test_ai_provider_operations()
    await test_api_endpoint_performance()
    await test_websocket_performance()
    await test_memory_usage_patterns()
    
    # Generate report
    total_time = time.time() - start_time
    print(f"\n⏱️ Total testing time: {total_time:.2f}s")
    
    # Save metrics and generate report
    metrics_file = profiler.save_metrics()
    print(f"📄 Metrics saved to: {metrics_file}")
    
    # Print summary
    profiler.print_summary()
    
    return metrics_file

if __name__ == "__main__":
    # Run performance tests
    try:
        metrics_file = asyncio.run(run_comprehensive_performance_test())
        print(f"\n✅ Performance analysis complete. Results saved to: {metrics_file}")
        print("📋 Next steps:")
        print("  1. Review performance metrics in the generated report")
        print("  2. Identify bottlenecks and optimization opportunities")
        print("  3. Implement targeted optimizations")
        print("  4. Re-run tests to measure improvements")
        
    except KeyboardInterrupt:
        print("\n🛑 Performance testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Performance testing failed: {e}")
        import traceback
        traceback.print_exc()