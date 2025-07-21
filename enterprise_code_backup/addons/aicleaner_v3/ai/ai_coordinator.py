# ai/ai_coordinator.py

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from .multi_model_ai import MultiModelAIOptimizer
from .predictive_analytics import PredictiveAnalytics
from .scene_understanding import AdvancedSceneUnderstanding

try:
    from core.local_model_manager import LocalModelManager
    from core.performance_tuner import PerformanceTuner
    from core.optimization_profiles import OptimizationProfileManager
    from core.system_monitor import SystemMonitor
    from core.performance_benchmarks import PerformanceBenchmarks
    PERFORMANCE_OPTIMIZATION_AVAILABLE = True
except ImportError:
    # Fallback for different import contexts
    try:
        from ..core.local_model_manager import LocalModelManager
        from ..core.performance_tuner import PerformanceTuner
        from ..core.optimization_profiles import OptimizationProfileManager
        from ..core.system_monitor import SystemMonitor
        from ..core.performance_benchmarks import PerformanceBenchmarks
        PERFORMANCE_OPTIMIZATION_AVAILABLE = True
    except ImportError:
        # Create dummy classes if imports fail
        PERFORMANCE_OPTIMIZATION_AVAILABLE = False

        class LocalModelManager:
            def __init__(self, config):
                pass
            async def initialize(self):
                return False

        class PerformanceTuner:
            def __init__(self, config, data_path="/data"):
                pass
            async def start_auto_tuning(self):
                pass

        class OptimizationProfileManager:
            def __init__(self, data_path="/data"):
                pass
            def recommend_profile(self, system_info):
                return None

        class SystemMonitor:
            def __init__(self, config, data_path="/data"):
                pass
            async def start_monitoring(self, interval=30):
                pass
            async def get_system_status(self):
                return None

        class PerformanceBenchmarks:
            def __init__(self, data_path="/data"):
                pass

class AICoordinator:
    """
    Orchestrates all AI components for a cohesive analysis pipeline.
    This is the single entry point for AI-related tasks.
    """
    def __init__(self, config: Dict[str, Any], multi_model_ai: MultiModelAIOptimizer,
                 predictive_analytics: PredictiveAnalytics = None,
                 scene_understanding: AdvancedSceneUnderstanding = None,
                 local_model_manager: LocalModelManager = None,
                 performance_tuner: PerformanceTuner = None,
                 optimization_profiles: OptimizationProfileManager = None,
                 system_monitor: SystemMonitor = None):
        """
        Initialize AI Coordinator with direct dependency injection.

        Args:
            config: Full configuration dictionary
            multi_model_ai: MultiModelAIOptimizer instance
            predictive_analytics: PredictiveAnalytics instance (optional, will create if None)
            scene_understanding: AdvancedSceneUnderstanding instance (optional, will create if None)
            local_model_manager: LocalModelManager instance (optional, will create if None)
            performance_tuner: PerformanceTuner instance (optional, will create if None)
            optimization_profiles: OptimizationProfileManager instance (optional, will create if None)
            system_monitor: SystemMonitor instance (optional, will create if None)
        """
        self.logger = logging.getLogger(__name__)
        self.config = config  # Store full config
        self.ai_config = config.get("ai_enhancements", {})  # Store AI enhancements config

        # Store AI components
        self.multi_model_ai = multi_model_ai
        self.predictive_analytics = predictive_analytics or PredictiveAnalytics()
        self.scene_understanding = scene_understanding or AdvancedSceneUnderstanding()
        self.local_model_manager = local_model_manager or LocalModelManager(config)

        # Performance optimization components
        if PERFORMANCE_OPTIMIZATION_AVAILABLE:
            self.performance_tuner = performance_tuner or PerformanceTuner(config)
            self.optimization_profiles = optimization_profiles or OptimizationProfileManager()
            self.system_monitor = system_monitor or SystemMonitor(config)
            self.performance_benchmarks = PerformanceBenchmarks()
        else:
            self.performance_tuner = None
            self.optimization_profiles = None
            self.system_monitor = None
            self.performance_benchmarks = None

        # Initialize local LLM client if enabled
        self._local_llm_initialized = False
        self._performance_optimization_enabled = PERFORMANCE_OPTIMIZATION_AVAILABLE and config.get("performance_optimization", {}).get("auto_tuning", {}).get("enabled", False)

        # Performance tracking
        self._analysis_count = 0
        self._total_analysis_time = 0.0
        self._last_optimization_check = 0

    async def initialize(self):
        """Initialize the AI Coordinator and its components."""
        try:
            # Initialize local model manager if enabled
            if self.ai_config.get("local_llm", {}).get("enabled", False):
                self.logger.info("Initializing local model manager")
                self._local_llm_initialized = await self.local_model_manager.initialize()
                if self._local_llm_initialized:
                    self.logger.info("Local model manager initialized successfully")
                else:
                    self.logger.warning("Local model manager initialization failed, will use cloud fallback")
            else:
                self.logger.info("Local LLM disabled in configuration")

            # Initialize performance optimization components
            if self._performance_optimization_enabled:
                await self._initialize_performance_optimization()

        except Exception as e:
            self.logger.error(f"Error initializing AI Coordinator: {e}")
            self._local_llm_initialized = False

    async def analyze_zone(self, zone_name: str, image_path: str, priority: str,
                          zone_purpose: str, active_tasks: List[Dict] = None,
                          ignore_rules: List[str] = None) -> Dict[str, Any]:
        """
        Performs a full, orchestrated analysis of a zone.

        Args:
            zone_name: The name of the zone to analyze.
            image_path: The path to the captured image.
            priority: The priority of the analysis request ('manual', 'scheduled', etc.).
            zone_purpose: The purpose/description of the zone.
            active_tasks: List of currently active tasks for the zone.
            ignore_rules: List of ignore rules for the zone.

        Returns:
            A comprehensive analysis result dictionary.
        """
        self.logger.info(f"Starting orchestrated AI analysis for zone: {zone_name}")

        # Initialize defaults
        if active_tasks is None:
            active_tasks = []
        if ignore_rules is None:
            ignore_rules = []

        try:
            # 1. Select and route to the best AI model (local or cloud)
            model_name, provider = await self._select_and_route_model(priority, "image_analysis")
            self.logger.debug(f"Selected model: {model_name} via {provider} for priority: {priority}")

            # 2. Get the core analysis using the selected provider
            if provider == "local" and self._local_llm_initialized:
                core_analysis_result, was_cached = await self._analyze_with_local_model(
                    image_path, zone_name, zone_purpose, active_tasks, ignore_rules, model_name
                )
            else:
                # Fallback to cloud analysis
                core_analysis_result, was_cached = await self.multi_model_ai.analyze_batch_optimized(
                    image_path, zone_name, zone_purpose, active_tasks, ignore_rules
                )

            if core_analysis_result is None:
                self.logger.error(f"Core analysis failed for zone: {zone_name}")
                return self._create_error_result("Core analysis failed")

            self.logger.debug(f"Core analysis completed (cached: {was_cached})")

            # 3. Enhance the analysis with scene understanding
            scene_details = await self._get_scene_understanding(
                zone_name, zone_purpose, core_analysis_result
            )

            # 4. Get predictive insights for this zone
            predictions = self._get_predictive_insights(zone_name)

            # 5. Generate enhanced tasks based on scene understanding
            enhanced_tasks = self._generate_enhanced_tasks(core_analysis_result, scene_details)

            # 6. Combine all insights into a final result
            final_result = self._compile_final_analysis(
                core_analysis_result, scene_details, predictions, enhanced_tasks, was_cached
            )

            self.logger.info(f"Completed orchestrated AI analysis for zone: {zone_name}")
            return final_result

        except Exception as e:
            self.logger.error(f"Error in orchestrated analysis for zone {zone_name}: {e}")
            return self._create_error_result(f"Analysis error: {str(e)}")

    async def _initialize_performance_optimization(self):
        """Initialize performance optimization components."""
        try:
            self.logger.info("Initializing performance optimization")

            # Detect system capabilities
            system_info = await self._detect_system_capabilities()

            # Recommend and apply optimization profile
            if self.optimization_profiles:
                recommended_profile = self.optimization_profiles.recommend_profile(system_info)
                if recommended_profile:
                    self.optimization_profiles.apply_profile(recommended_profile.profile_id)
                    self.logger.info(f"Applied optimization profile: {recommended_profile.name}")

            # Start performance tuner if enabled
            if self.performance_tuner:
                await self.performance_tuner.start_auto_tuning()
                self.logger.info("Performance auto-tuning started")

            # Initialize system monitoring
            if self.system_monitor:
                await self.system_monitor.start_monitoring()
                self.logger.info("System monitoring started")

        except Exception as e:
            self.logger.error(f"Error initializing performance optimization: {e}")

    async def _detect_system_capabilities(self) -> Dict[str, Any]:
        """Detect system capabilities for optimization profile selection."""
        try:
            import psutil

            # Get system information
            memory_gb = psutil.virtual_memory().total / (1024**3)
            cpu_cores = psutil.cpu_count()

            # Detect GPU
            has_gpu = False
            try:
                import torch
                has_gpu = torch.cuda.is_available()
            except ImportError:
                pass

            return {
                "memory_gb": memory_gb,
                "cpu_cores": cpu_cores,
                "has_gpu": has_gpu,
                "use_case": "interactive"  # Default use case
            }

        except Exception as e:
            self.logger.error(f"Error detecting system capabilities: {e}")
            return {
                "memory_gb": 4,
                "cpu_cores": 4,
                "has_gpu": False,
                "use_case": "interactive"
            }

    async def analyze_zone_with_optimization(self, zone_name: str, image_path: str, priority: str,
                                           zone_purpose: str, active_tasks: List[Dict] = None,
                                           ignore_rules: List[str] = None) -> Dict[str, Any]:
        """
        Enhanced zone analysis with performance optimization and monitoring.

        Args:
            zone_name: The name of the zone to analyze
            image_path: The path to the captured image
            priority: The priority of the analysis request
            zone_purpose: The purpose/description of the zone
            active_tasks: List of currently active tasks for the zone
            ignore_rules: List of ignore rules for the zone

        Returns:
            Comprehensive analysis result with performance metrics
        """
        import time

        start_time = time.time()

        try:
            # Track performance metrics
            if self.system_monitor:
                from core.production_monitor import PerformanceMetric
                self.system_monitor.record_performance(
                    PerformanceMetric.RESPONSE_TIME,
                    start_time,
                    "ai_coordinator",
                    "analyze_zone"
                )

            # Check if optimization is needed before analysis
            if self._performance_optimization_enabled:
                await self._check_and_optimize_performance()

            # Perform the analysis
            result = await self.analyze_zone(zone_name, image_path, priority, zone_purpose, active_tasks, ignore_rules)

            # Calculate analysis time
            analysis_time = time.time() - start_time

            # Update performance tracking
            self._analysis_count += 1
            self._total_analysis_time += analysis_time

            # Record performance metrics
            if self.system_monitor:
                from core.production_monitor import PerformanceMetric
                self.system_monitor.record_performance(
                    PerformanceMetric.RESPONSE_TIME,
                    analysis_time,
                    "ai_coordinator",
                    "analyze_zone"
                )

            # Add performance metadata to result
            if "metadata" not in result:
                result["metadata"] = {}

            result["metadata"]["performance"] = {
                "analysis_time_seconds": analysis_time,
                "optimization_enabled": self._performance_optimization_enabled,
                "total_analyses": self._analysis_count,
                "average_analysis_time": self._total_analysis_time / self._analysis_count
            }

            return result

        except Exception as e:
            analysis_time = time.time() - start_time

            # Record error metrics
            if self.system_monitor:
                self.system_monitor.capture_error(e, "ai_coordinator", "analyze_zone")

            self.logger.error(f"Error in optimized analysis for zone {zone_name}: {e}")
            return self._create_error_result(f"Optimized analysis error: {str(e)}")

    async def _check_and_optimize_performance(self):
        """Check performance and apply optimizations if needed."""
        try:
            import time

            current_time = time.time()

            # Check if it's time for optimization check (every 5 minutes)
            if current_time - self._last_optimization_check < 300:
                return

            self._last_optimization_check = current_time

            # Get performance recommendations from tuner
            if self.performance_tuner:
                recommendations = await self.performance_tuner.get_tuning_recommendations()

                if recommendations:
                    # Apply the best recommendation if confidence is high
                    best_recommendation = recommendations[0]
                    if best_recommendation.confidence > 0.8:
                        self.logger.info(f"Applying performance optimization: {best_recommendation.reasoning}")

                        # In a real implementation, this would apply the recommendation
                        # For now, just log it

        except Exception as e:
            self.logger.error(f"Error in performance optimization check: {e}")

    async def get_performance_status(self) -> Dict[str, Any]:
        """Get current performance status and metrics."""
        status = {
            "optimization_enabled": self._performance_optimization_enabled,
            "total_analyses": self._analysis_count,
            "average_analysis_time": self._total_analysis_time / self._analysis_count if self._analysis_count > 0 else 0,
            "components": {}
        }

        # Get status from performance components
        if self.performance_tuner:
            status["components"]["tuner"] = self.performance_tuner.get_tuning_status()

        if self.optimization_profiles:
            active_profile = self.optimization_profiles.get_active_profile()
            status["components"]["active_profile"] = active_profile.name if active_profile else None

        if self.system_monitor:
            system_status = await self.system_monitor.get_system_status()
            status["components"]["monitoring"] = {
                "overall_health": system_status.overall_health,
                "active_alerts": len(system_status.active_alerts) if system_status.active_alerts else 0,
                "performance_summary": system_status.performance_summary
            }

        return status

    async def run_performance_benchmark(self, benchmark_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Run performance benchmarks to evaluate current system performance.

        Args:
            benchmark_type: Type of benchmark to run (quick, comprehensive, load_test)

        Returns:
            Benchmark results
        """
        if not self.performance_benchmarks:
            return {"error": "Performance benchmarks not available"}

        try:
            self.logger.info(f"Running {benchmark_type} performance benchmark")

            if benchmark_type == "quick":
                # Quick latency test
                async def test_function():
                    return await self.analyze_zone("test_zone", "test_image.jpg", "manual", "test_purpose")

                result = await self.performance_benchmarks.benchmark_latency(
                    component="ai_coordinator",
                    operation="analyze_zone",
                    test_func=test_function,
                    iterations=3
                )

            elif benchmark_type == "load_test":
                # Load test
                async def load_test_function():
                    return await self.analyze_zone("test_zone", "test_image.jpg", "scheduled", "test_purpose")

                result = await self.performance_benchmarks.benchmark_load_test(
                    component="ai_coordinator",
                    operation="analyze_zone",
                    test_func=load_test_function,
                    concurrent_users=3,
                    duration_seconds=30
                )

            else:  # comprehensive
                # Run multiple benchmark types
                results = {}

                # Latency benchmark
                async def latency_test():
                    return await self.analyze_zone("test_zone", "test_image.jpg", "manual", "test_purpose")

                latency_result = await self.performance_benchmarks.benchmark_latency(
                    component="ai_coordinator",
                    operation="analyze_zone",
                    test_func=latency_test,
                    iterations=5
                )
                results["latency"] = latency_result

                # Throughput benchmark
                async def throughput_test():
                    return await self.analyze_zone("test_zone", "test_image.jpg", "scheduled", "test_purpose")

                throughput_result = await self.performance_benchmarks.benchmark_throughput(
                    component="ai_coordinator",
                    operation="analyze_zone",
                    test_func=throughput_test,
                    duration_seconds=60
                )
                results["throughput"] = throughput_result

                return results

            return {"status": "completed", "results": result}

        except Exception as e:
            self.logger.error(f"Error running performance benchmark: {e}")
            return {"status": "failed", "error": str(e)}

    def _select_model(self, priority: str) -> str:
        """Selects the appropriate cloud AI model based on priority and local_llm fallback configuration."""
        # Use local_llm.preferred_models.fallback as the base, with priority-specific overrides
        local_llm_config = self.ai_config.get("local_llm", {})
        fallback_model = local_llm_config.get("preferred_models", {}).get("fallback", "gemini-pro")

        # Map priority to specific cloud models if needed, otherwise use fallback
        priority_mapping = {
            "manual": "gemini-pro",      # For manual/detailed analysis
            "complex": "claude-sonnet",  # For complex scenes requiring reasoning
            "scheduled": "gemini-flash"  # For scheduled/routine analysis
        }

        return priority_mapping.get(priority, fallback_model)

    async def _select_and_route_model(self, priority: str, analysis_type: str) -> Tuple[str, str]:
        """
        Select and route to the best model (local or cloud) based on availability and criteria.

        Args:
            priority: Analysis priority ('manual', 'scheduled', 'complex')
            analysis_type: Type of analysis ('image_analysis', 'task_generation')

        Returns:
            Tuple of (model_name, provider) where provider is 'local' or 'cloud'
        """
        local_llm_config = self.ai_config.get("local_llm", {})

        # Check if local LLM is enabled and initialized
        if not local_llm_config.get("enabled", False) or not self._local_llm_initialized:
            self.logger.debug("Local LLM not available, using cloud")
            return self._select_model(priority), "cloud"

        # Check fallback preference - if user explicitly prefers cloud
        fallback_model = local_llm_config.get("preferred_models", {}).get("fallback", "")
        if fallback_model in ["gemini", "claude", "openai"]:
            # User has set cloud as fallback preference
            if priority == "manual":  # For manual analysis, prefer cloud for quality
                self.logger.debug("Manual analysis with cloud fallback preference")
                return self._select_model(priority), "cloud"

        # Determine local model based on analysis type
        preferred_models = local_llm_config.get("preferred_models", {})
        if analysis_type == "image_analysis":
            local_model = preferred_models.get("vision", "llava:13b")
        elif analysis_type == "task_generation":
            local_model = preferred_models.get("task_generation", "mistral:7b")
        else:
            local_model = preferred_models.get("text", "mistral:7b")

        # Check if local model is available and ensure it's loaded
        try:
            if await self.local_model_manager.ensure_model_loaded(local_model):
                self.logger.debug(f"Using local model {local_model}")
                return local_model, "local"
            else:
                self.logger.warning(f"Local model {local_model} not available, falling back to cloud")
                return self._select_model(priority), "cloud"
        except Exception as e:
            self.logger.error(f"Error ensuring local model availability: {e}")
            return self._select_model(priority), "cloud"

    async def _analyze_with_local_model(self, image_path: str, zone_name: str, zone_purpose: str,
                                      active_tasks: List[Dict], ignore_rules: List[str],
                                      model_name: str) -> Tuple[Dict[str, Any], bool]:
        """
        Perform analysis using local LLM with fallback to cloud on failure.

        Args:
            image_path: Path to image file
            zone_name: Name of the zone
            zone_purpose: Purpose of the zone
            active_tasks: List of active tasks
            ignore_rules: List of ignore rules
            model_name: Local model to use

        Returns:
            Tuple of (analysis_result, was_cached)
        """
        try:
            # Perform local image analysis through LocalModelManager
            local_analysis = await self.local_model_manager.analyze_image_with_model(
                model_name=model_name,
                image_path=image_path
            )

            # Check confidence score for fallback decision
            confidence = local_analysis.get("confidence", 0.0)
            min_confidence = self.ai_config.get("local_llm", {}).get("min_confidence", 0.6)

            if confidence < min_confidence:
                self.logger.warning(f"Local analysis confidence {confidence} below threshold {min_confidence}, falling back to cloud")
                return await self.multi_model_ai.analyze_batch_optimized(
                    image_path, zone_name, zone_purpose, active_tasks, ignore_rules
                )

            # Generate tasks using local model through LocalModelManager
            context = {
                "zone_name": zone_name,
                "zone_purpose": zone_purpose,
                "active_tasks": active_tasks,
                "ignore_rules": ignore_rules
            }

            # Determine task generation model
            task_model = self.ai_config.get("local_llm", {}).get("preferred_models", {}).get("task_generation", model_name)
            local_tasks = await self.local_model_manager.generate_tasks_with_model(
                model_name=task_model,
                analysis=local_analysis.get("text", ""),
                context=context
            )

            # Convert to expected format
            analysis_result = {
                "analysis_summary": local_analysis.get("text", ""),
                "cleanliness_score": self._extract_cleanliness_score(local_analysis.get("text", "")),
                "new_tasks": local_tasks,
                "completed_tasks": [],  # Local model doesn't handle task completion yet
                "analysis_metadata": {
                    "timestamp": local_analysis.get("timestamp"),
                    "model": local_analysis.get("model"),
                    "provider": "ollama",
                    "analysis_time": local_analysis.get("analysis_time", 0),
                    "confidence": confidence
                }
            }

            self.logger.info(f"Local analysis completed successfully with confidence {confidence}")
            return analysis_result, False  # Local analysis is never cached (for now)

        except Exception as e:
            self.logger.error(f"Local analysis failed: {e}, falling back to cloud")
            # Fallback to cloud analysis
            return await self.multi_model_ai.analyze_batch_optimized(
                image_path, zone_name, zone_purpose, active_tasks, ignore_rules
            )

    def _extract_cleanliness_score(self, analysis_text: str) -> int:
        """Extract a cleanliness score from analysis text."""
        # Simple heuristic to extract score from text
        # Look for patterns like "score: 7" or "cleanliness: 8/10"
        import re

        # Try to find explicit score mentions
        score_patterns = [
            r'score[:\s]+(\d+)',
            r'cleanliness[:\s]+(\d+)',
            r'rating[:\s]+(\d+)',
            r'(\d+)/10',
            r'(\d+)\s*out\s*of\s*10'
        ]

        for pattern in score_patterns:
            match = re.search(pattern, analysis_text.lower())
            if match:
                score = int(match.group(1))
                return max(1, min(10, score))  # Clamp to 1-10 range

        # Fallback: analyze sentiment
        negative_words = ['dirty', 'messy', 'cluttered', 'unclean', 'disorganized']
        positive_words = ['clean', 'tidy', 'organized', 'neat', 'spotless']

        negative_count = sum(1 for word in negative_words if word in analysis_text.lower())
        positive_count = sum(1 for word in positive_words if word in analysis_text.lower())

        if negative_count > positive_count:
            return 4  # Below average
        elif positive_count > negative_count:
            return 8  # Above average
        else:
            return 6  # Average

    async def _get_scene_understanding(self, zone_name: str, zone_purpose: str,
                                     core_analysis: Dict) -> Dict[str, Any]:
        """Get enhanced scene understanding from the core analysis."""
        # Use AI enhancements configuration
        scene_config = self.ai_config.get("scene_understanding_settings", {})

        # Check if advanced scene understanding is enabled
        if not self.ai_config.get("advanced_scene_understanding", True):
            self.logger.debug("Advanced scene understanding disabled by config")
            return {}

        try:
            # Extract AI response text for scene understanding
            ai_response = core_analysis.get("raw_response", "")
            if not ai_response:
                self.logger.warning("No raw response available for scene understanding")
                return {}

            # Apply configuration settings
            max_objects = scene_config.get("max_objects_detected", 10)
            confidence_threshold = scene_config.get("confidence_threshold", 0.7)
            enable_seasonal = scene_config.get("enable_seasonal_adjustments", True)
            enable_time_context = scene_config.get("enable_time_context", True)

            self.logger.debug(f"Scene understanding config: max_objects={max_objects}, "
                            f"confidence={confidence_threshold}, seasonal={enable_seasonal}")

            # Get detailed scene context with configuration parameters
            scene_context = self.scene_understanding.get_detailed_scene_context(
                zone_name, zone_purpose, ai_response,
                max_objects=max_objects,
                confidence_threshold=confidence_threshold,
                enable_seasonal_adjustments=enable_seasonal,
                enable_time_context=enable_time_context
            )

            return {
                "scene_context": scene_context.__dict__ if hasattr(scene_context, '__dict__') else scene_context,
                "contextual_insights": self.scene_understanding.generate_contextual_insights(scene_context)
            }

        except Exception as e:
            self.logger.error(f"Error in scene understanding: {e}")
            return {}

    def _get_predictive_insights(self, zone_name: str) -> Dict[str, Any]:
        """Get predictive insights for the zone."""
        # Check if predictive analytics is enabled
        predictive_enabled = self.ai_config.get("predictive_analytics", True)
        self.logger.debug(f"Predictive analytics enabled: {predictive_enabled}")

        if not predictive_enabled:
            self.logger.debug("Predictive analytics disabled by config")
            return {}

        try:
            predictive_config = self.ai_config.get("predictive_analytics_settings", {})

            # Apply configuration settings
            history_days = predictive_config.get("history_days", 30)
            prediction_horizon = predictive_config.get("prediction_horizon_hours", 24)
            min_data_points = predictive_config.get("min_data_points", 5)
            enable_urgency_scoring = predictive_config.get("enable_urgency_scoring", True)
            enable_pattern_detection = predictive_config.get("enable_pattern_detection", True)

            self.logger.debug(f"Predictive analytics config: history_days={history_days}, "
                            f"horizon={prediction_horizon}, urgency_scoring={enable_urgency_scoring}")

            return self.predictive_analytics.get_prediction_for_zone(
                zone_name,
                history_days=history_days,
                prediction_horizon_hours=prediction_horizon,
                min_data_points=min_data_points,
                enable_urgency_scoring=enable_urgency_scoring,
                enable_pattern_detection=enable_pattern_detection
            )

        except Exception as e:
            self.logger.error(f"Error getting predictive insights: {e}")
            return {}

    def _generate_enhanced_tasks(self, core_analysis: Dict, scene_details: Dict) -> List[Dict[str, Any]]:
        """Generate enhanced, specific tasks based on scene understanding."""
        try:
            enhanced_tasks = []

            # Get base tasks from core analysis
            base_tasks = core_analysis.get("new_tasks", [])

            # If scene understanding is available, enhance tasks with location and object details
            if scene_details and scene_details.get("scene_context"):
                scene_context = scene_details["scene_context"]
                detected_objects = scene_context.get("detected_objects", [])

                for task in base_tasks:
                    enhanced_task = task.copy()

                    # Add location context if available
                    if detected_objects:
                        enhanced_task["detected_objects"] = detected_objects
                        enhanced_task["enhanced"] = True

                    enhanced_tasks.append(enhanced_task)
            else:
                enhanced_tasks = base_tasks

            return enhanced_tasks

        except Exception as e:
            self.logger.error(f"Error generating enhanced tasks: {e}")
            return core_analysis.get("new_tasks", [])

    def _compile_final_analysis(self, core: Dict, scene: Dict, preds: Dict,
                              enhanced_tasks: List[Dict], was_cached: bool) -> Dict[str, Any]:
        """Combines all AI outputs into a single, comprehensive result."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "was_cached": was_cached,
            "core_assessment": core,
            "scene_understanding": scene,
            "predictive_insights": preds,
            "generated_tasks": enhanced_tasks,
            "completed_tasks": core.get("completed_tasks", []),
            "cleanliness_score": core.get("cleanliness_score", 0),
            "analysis_summary": core.get("analysis_summary", ""),
            "ai_coordinator_version": "1.0"
        }

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error result."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": True,
            "error_message": error_message,
            "core_assessment": {},
            "scene_understanding": {},
            "predictive_insights": {},
            "generated_tasks": [],
            "completed_tasks": [],
            "cleanliness_score": 0,
            "analysis_summary": f"Analysis failed: {error_message}",
            "ai_coordinator_version": "1.0"
        }
