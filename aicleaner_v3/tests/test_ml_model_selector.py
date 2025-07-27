"""
Tests for ML-Based Model Selection System
"""

import pytest
import json
import os
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock

from ai.providers.ml_model_selector import (
    MLModelSelector,
    FeatureExtractor,
    ModelPerformanceTracker,
    UCB1Algorithm,
    RequestCategory,
    ComplexityLevel,
    ModelMetrics,
    RequestFeatures
)


class TestRequestFeatures:
    """Test RequestFeatures class"""
    
    def test_request_features_initialization(self):
        """Test RequestFeatures initialization"""
        features = RequestFeatures(
            category=RequestCategory.CODE,
            complexity=ComplexityLevel.COMPLEX,
            prompt_length=100,
            has_code=True,
            has_image=False
        )
        
        assert features.category == RequestCategory.CODE
        assert features.complexity == ComplexityLevel.COMPLEX
        assert features.prompt_length == 100
        assert features.has_code is True
        assert features.has_image is False
    
    def test_get_key(self):
        """Test feature key generation"""
        features = RequestFeatures(
            category=RequestCategory.CODE,
            complexity=ComplexityLevel.COMPLEX,
            prompt_length=100,
            has_code=True,
            has_image=False
        )
        
        key = features.get_key()
        assert key == "code_complex"


class TestModelMetrics:
    """Test ModelMetrics class"""
    
    def test_model_metrics_initialization(self):
        """Test ModelMetrics initialization"""
        metrics = ModelMetrics()
        
        assert metrics.pulls == 0
        assert metrics.successes == 0
        assert metrics.total_response_time == 0.0
        assert metrics.total_cost == 0.0
        assert metrics.success_rate == 0.0
        assert metrics.avg_response_time == 0.0
        assert metrics.avg_cost == 0.0
    
    def test_update_success(self):
        """Test metrics update with successful request"""
        metrics = ModelMetrics()
        
        metrics.update(success=True, response_time=2.0, cost=0.05)
        
        assert metrics.pulls == 1
        assert metrics.successes == 1
        assert metrics.total_response_time == 2.0
        assert metrics.total_cost == 0.05
        assert metrics.success_rate == 1.0
        assert metrics.avg_response_time == 2.0
        assert metrics.avg_cost == 0.05
    
    def test_update_failure(self):
        """Test metrics update with failed request"""
        metrics = ModelMetrics()
        
        metrics.update(success=False, response_time=5.0, cost=0.0)
        
        assert metrics.pulls == 1
        assert metrics.successes == 0
        assert metrics.total_response_time == 0.0  # No response time added for failures
        assert metrics.total_cost == 0.0
        assert metrics.success_rate == 0.0
        assert metrics.avg_response_time == 0.0
        assert metrics.avg_cost == 0.0
    
    def test_mixed_updates(self):
        """Test metrics with mixed success/failure updates"""
        metrics = ModelMetrics()
        
        # Add successful request
        metrics.update(success=True, response_time=2.0, cost=0.05)
        # Add failed request
        metrics.update(success=False, response_time=10.0, cost=0.02)
        # Add another successful request
        metrics.update(success=True, response_time=3.0, cost=0.07)
        
        assert metrics.pulls == 3
        assert metrics.successes == 2
        assert metrics.total_response_time == 5.0  # Only successful requests
        assert metrics.total_cost == 0.14
        assert metrics.success_rate == 2/3
        assert metrics.avg_response_time == 2.5
        assert metrics.avg_cost == 0.14/3


class TestFeatureExtractor:
    """Test FeatureExtractor class"""
    
    def test_feature_extractor_initialization(self):
        """Test FeatureExtractor initialization"""
        extractor = FeatureExtractor()
        
        assert extractor.code_patterns is not None
        assert extractor.analysis_keywords is not None
        assert extractor.creative_keywords is not None
        assert extractor.summarization_keywords is not None
        assert extractor.translation_keywords is not None
    
    def test_detect_code_python(self):
        """Test code detection for Python"""
        extractor = FeatureExtractor()
        
        python_code = "def hello_world():\n    print('Hello, World!')"
        assert extractor._detect_code(python_code) is True
        
        import_code = "import pandas as pd\nimport numpy as np"
        assert extractor._detect_code(import_code) is True
    
    def test_detect_code_javascript(self):
        """Test code detection for JavaScript"""
        extractor = FeatureExtractor()
        
        js_code = "function calculateSum(a, b) { return a + b; }"
        assert extractor._detect_code(js_code) is True
    
    def test_detect_code_html(self):
        """Test code detection for HTML"""
        extractor = FeatureExtractor()
        
        html_code = "<div class='container'><p>Hello World</p></div>"
        assert extractor._detect_code(html_code) is True
    
    def test_detect_code_negative(self):
        """Test code detection returns False for non-code"""
        extractor = FeatureExtractor()
        
        text = "This is just regular text about programming concepts"
        assert extractor._detect_code(text) is False
    
    def test_detect_category_code(self):
        """Test category detection for code"""
        extractor = FeatureExtractor()
        
        code_prompt = "def fibonacci(n):\n    if n <= 1:\n        return n"
        category = extractor._detect_category(code_prompt)
        assert category == RequestCategory.CODE
    
    def test_detect_category_summarization(self):
        """Test category detection for summarization"""
        extractor = FeatureExtractor()
        
        summary_prompt = "Please summarize the following article about AI"
        category = extractor._detect_category(summary_prompt)
        assert category == RequestCategory.SUMMARIZATION
    
    def test_detect_category_analysis(self):
        """Test category detection for analysis"""
        extractor = FeatureExtractor()
        
        analysis_prompt = "Analyze the performance of this algorithm"
        category = extractor._detect_category(analysis_prompt)
        assert category == RequestCategory.ANALYSIS
    
    def test_detect_category_creative(self):
        """Test category detection for creative tasks"""
        extractor = FeatureExtractor()
        
        creative_prompt = "Write a creative story about a robot"
        category = extractor._detect_category(creative_prompt)
        assert category == RequestCategory.CREATIVE
    
    def test_detect_category_question_answer(self):
        """Test category detection for Q&A"""
        extractor = FeatureExtractor()
        
        question_prompt = "What is the capital of France?"
        category = extractor._detect_category(question_prompt)
        assert category == RequestCategory.QUESTION_ANSWER
    
    def test_detect_category_generic(self):
        """Test category detection defaults to generic"""
        extractor = FeatureExtractor()
        
        generic_prompt = "Tell me about the weather today"
        category = extractor._detect_category(generic_prompt)
        assert category == RequestCategory.GENERIC
    
    def test_assess_complexity_simple(self):
        """Test complexity assessment for simple requests"""
        extractor = FeatureExtractor()
        
        simple_prompt = "Hello"
        complexity = extractor._assess_complexity(simple_prompt, 1, False, False)
        assert complexity == ComplexityLevel.SIMPLE
    
    def test_assess_complexity_medium(self):
        """Test complexity assessment for medium requests"""
        extractor = FeatureExtractor()
        
        medium_prompt = "Explain how machine learning works in simple terms"
        complexity = extractor._assess_complexity(medium_prompt, 10, False, False)
        assert complexity == ComplexityLevel.MEDIUM
    
    def test_assess_complexity_complex(self):
        """Test complexity assessment for complex requests"""
        extractor = FeatureExtractor()
        
        complex_prompt = "Implement a distributed algorithm for optimization with detailed architecture"
        complexity = extractor._assess_complexity(complex_prompt, 100, True, True)
        assert complexity == ComplexityLevel.COMPLEX
    
    def test_extract_features_basic(self):
        """Test basic feature extraction"""
        extractor = FeatureExtractor()
        
        prompt = "def hello():\n    print('Hello, World!')"
        features = extractor.extract_features(prompt)
        
        assert features.category == RequestCategory.CODE
        assert features.has_code is True
        assert features.has_image is False
        assert features.prompt_length > 0
    
    def test_extract_features_with_image(self):
        """Test feature extraction with image"""
        extractor = FeatureExtractor()
        
        prompt = "Analyze this image"
        features = extractor.extract_features(prompt, image_path="/path/to/image.jpg")
        
        assert features.has_image is True
        assert features.category == RequestCategory.ANALYSIS
    
    def test_extract_features_error_handling(self):
        """Test feature extraction error handling"""
        extractor = FeatureExtractor()
        
        # Mock an error in category detection
        with patch.object(extractor, '_detect_category', side_effect=Exception("Test error")):
            features = extractor.extract_features("test prompt")
            
            # Should return default values
            assert features.category == RequestCategory.GENERIC
            assert features.complexity == ComplexityLevel.MEDIUM


class TestModelPerformanceTracker:
    """Test ModelPerformanceTracker class"""
    
    def test_model_performance_tracker_initialization(self):
        """Test ModelPerformanceTracker initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            tracker = ModelPerformanceTracker("test_provider", data_path)
            
            assert tracker.provider_name == "test_provider"
            assert tracker.data_path == data_path
            assert isinstance(tracker.metrics, dict)
    
    def test_get_metrics_new_model(self):
        """Test getting metrics for a new model"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            tracker = ModelPerformanceTracker("test_provider", data_path)
            
            metrics = tracker.get_metrics("new_model", "generic_simple")
            
            assert isinstance(metrics, ModelMetrics)
            assert metrics.pulls == 0
            assert metrics.successes == 0
    
    def test_update_metrics(self):
        """Test updating metrics"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            tracker = ModelPerformanceTracker("test_provider", data_path)
            
            # Update metrics
            tracker.update_metrics("test_model", "generic_simple", True, 2.0, 0.05)
            
            # Check metrics were updated
            metrics = tracker.get_metrics("test_model", "generic_simple")
            assert metrics.pulls == 1
            assert metrics.successes == 1
            assert metrics.total_response_time == 2.0
            assert metrics.total_cost == 0.05
    
    def test_save_and_load_performance_data(self):
        """Test saving and loading performance data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            
            # Create tracker and add data
            tracker1 = ModelPerformanceTracker("test_provider", data_path)
            tracker1.update_metrics("model1", "generic_simple", True, 2.0, 0.05)
            tracker1.update_metrics("model1", "code_complex", False, 5.0, 0.02)
            
            # Create new tracker and verify data loaded
            tracker2 = ModelPerformanceTracker("test_provider", data_path)
            
            metrics1 = tracker2.get_metrics("model1", "generic_simple")
            assert metrics1.pulls == 1
            assert metrics1.successes == 1
            
            metrics2 = tracker2.get_metrics("model1", "code_complex")
            assert metrics2.pulls == 1
            assert metrics2.successes == 0


class TestUCB1Algorithm:
    """Test UCB1Algorithm class"""
    
    def test_ucb1_algorithm_initialization(self):
        """Test UCB1Algorithm initialization"""
        algorithm = UCB1Algorithm()
        
        assert algorithm.confidence_level == 2.0
    
    def test_calculate_ucb1_score_untested(self):
        """Test UCB1 score for untested model"""
        algorithm = UCB1Algorithm()
        metrics = ModelMetrics()
        
        score = algorithm.calculate_ucb1_score(metrics, 10)
        
        assert score == float('inf')  # Untested models should be tried first
    
    def test_calculate_ucb1_score_tested(self):
        """Test UCB1 score for tested model"""
        algorithm = UCB1Algorithm()
        metrics = ModelMetrics()
        
        # Add some test data
        metrics.update(True, 2.0, 0.05)
        metrics.update(True, 3.0, 0.06)
        metrics.update(False, 10.0, 0.0)
        
        score = algorithm.calculate_ucb1_score(metrics, 10)
        
        assert isinstance(score, float)
        assert score > 0
    
    def test_calculate_reward(self):
        """Test reward calculation"""
        algorithm = UCB1Algorithm()
        metrics = ModelMetrics()
        
        # Perfect performance
        metrics.update(True, 1.0, 0.01)
        reward = algorithm._calculate_reward(metrics)
        
        assert reward > 0.8  # Should be high for good performance
        
        # Poor performance
        metrics_poor = ModelMetrics()
        metrics_poor.update(False, 10.0, 0.20)
        reward_poor = algorithm._calculate_reward(metrics_poor)
        
        assert reward_poor < reward  # Should be lower for poor performance


class TestMLModelSelector:
    """Test MLModelSelector class"""
    
    def test_ml_model_selector_initialization(self):
        """Test MLModelSelector initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            selector = MLModelSelector(
                provider_name="test_provider",
                models=["model1", "model2", "model3"],
                default_model="model1",
                data_path=data_path
            )
            
            assert selector.provider_name == "test_provider"
            assert selector.models == ["model1", "model2", "model3"]
            assert selector.default_model == "model1"
            assert selector.feature_extractor is not None
            assert selector.performance_tracker is not None
            assert selector.ucb1_algorithm is not None
    
    def test_recommend_model_warmup(self):
        """Test model recommendation during warmup phase"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            selector = MLModelSelector(
                provider_name="test_provider",
                models=["model1", "model2", "model3"],
                default_model="model1",
                data_path=data_path
            )
            
            # During warmup, should cycle through models
            recommendations = []
            for i in range(6):
                model = selector.recommend_model("Test prompt")
                recommendations.append(model)
            
            # Should have tried different models
            assert len(set(recommendations)) > 1
    
    def test_recommend_model_ucb1(self):
        """Test model recommendation using UCB1"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            selector = MLModelSelector(
                provider_name="test_provider",
                models=["model1", "model2"],
                default_model="model1",
                data_path=data_path
            )
            
            # Add enough data to exit warmup
            for i in range(20):
                model = selector.recommend_model("Test prompt")
                selector.update_performance(model, "Test prompt", True, 2.0, 0.05)
            
            # Make model1 perform better
            for i in range(10):
                selector.update_performance("model1", "Test prompt", True, 1.0, 0.03)
            
            # Make model2 perform worse
            for i in range(10):
                selector.update_performance("model2", "Test prompt", False, 5.0, 0.08)
            
            # Should now prefer model1
            recommendations = []
            for i in range(10):
                model = selector.recommend_model("Test prompt")
                recommendations.append(model)
            
            # Should mostly recommend model1
            model1_count = recommendations.count("model1")
            assert model1_count > 5
    
    def test_update_performance(self):
        """Test performance update"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            selector = MLModelSelector(
                provider_name="test_provider",
                models=["model1", "model2"],
                default_model="model1",
                data_path=data_path
            )
            
            # Update performance
            selector.update_performance("model1", "Test prompt", True, 2.0, 0.05)
            
            # Check that metrics were updated
            metrics = selector.performance_tracker.get_metrics("model1", "generic_simple")
            assert metrics.pulls == 1
            assert metrics.successes == 1
    
    def test_recommend_model_error_handling(self):
        """Test error handling in model recommendation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            selector = MLModelSelector(
                provider_name="test_provider",
                models=["model1", "model2"],
                default_model="model1",
                data_path=data_path
            )
            
            # Mock an error in feature extraction
            with patch.object(selector.feature_extractor, 'extract_features', side_effect=Exception("Test error")):
                model = selector.recommend_model("Test prompt")
                
                # Should return default model
                assert model == "model1"
    
    def test_get_model_stats(self):
        """Test getting model statistics"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            selector = MLModelSelector(
                provider_name="test_provider",
                models=["model1", "model2"],
                default_model="model1",
                data_path=data_path
            )
            
            # Add some performance data
            selector.update_performance("model1", "Test prompt", True, 2.0, 0.05)
            selector.update_performance("model2", "Test prompt", False, 5.0, 0.08)
            
            stats = selector.get_model_stats()
            
            assert stats["provider"] == "test_provider"
            assert stats["models"] == ["model1", "model2"]
            assert stats["default_model"] == "model1"
            assert "warmup_status" in stats
            assert "model_performance" in stats
    
    def test_different_request_categories(self):
        """Test model selection for different request categories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            selector = MLModelSelector(
                provider_name="test_provider",
                models=["model1", "model2"],
                default_model="model1",
                data_path=data_path
            )
            
            # Test different prompt types
            code_prompt = "def hello():\n    print('Hello, World!')"
            summary_prompt = "Please summarize this article"
            question_prompt = "What is the capital of France?"
            
            # Should handle different categories
            code_model = selector.recommend_model(code_prompt)
            summary_model = selector.recommend_model(summary_prompt)
            question_model = selector.recommend_model(question_prompt)
            
            assert code_model in ["model1", "model2"]
            assert summary_model in ["model1", "model2"]
            assert question_model in ["model1", "model2"]
    
    def test_image_requests(self):
        """Test model selection for image requests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            selector = MLModelSelector(
                provider_name="test_provider",
                models=["model1", "model2"],
                default_model="model1",
                data_path=data_path
            )
            
            # Test image request
            model = selector.recommend_model("Analyze this image", image_path="/path/to/image.jpg")
            
            assert model in ["model1", "model2"]
            
            # Update performance for image request
            selector.update_performance(model, "Analyze this image", True, 3.0, 0.10, 
                                      image_path="/path/to/image.jpg")
            
            # Should have updated metrics for the analysis category
            stats = selector.get_model_stats()
            assert "analysis_medium" in stats["model_performance"][model]


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    def test_home_assistant_addon_scenario(self):
        """Test typical Home Assistant addon usage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            
            # Create selector for OpenAI provider
            selector = MLModelSelector(
                provider_name="openai",
                models=["gpt-4o", "gpt-4o-mini"],
                default_model="gpt-4o-mini",
                data_path=data_path
            )
            
            # Simulate typical HA addon requests
            requests = [
                ("Clean the kitchen", True, 2.0, 0.02),
                ("Analyze camera image", True, 3.0, 0.05),
                ("def automate_lights():\n    pass", True, 4.0, 0.08),
                ("Summarize today's events", True, 2.5, 0.03),
                ("What's the weather like?", True, 1.5, 0.01)
            ]
            
            # Process requests
            for prompt, success, response_time, cost in requests:
                model = selector.recommend_model(prompt)
                selector.update_performance(model, prompt, success, response_time, cost)
            
            # Check that system learned from requests
            stats = selector.get_model_stats()
            assert len(stats["model_performance"]) == 2
            assert "openai" == stats["provider"]
    
    def test_model_learning_adaptation(self):
        """Test that the system adapts to changing model performance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            
            selector = MLModelSelector(
                provider_name="test_provider",
                models=["fast_model", "slow_model"],
                default_model="fast_model",
                data_path=data_path
            )
            
            # Initially, make fast_model perform well
            for i in range(20):
                model = selector.recommend_model("Test prompt")
                if model == "fast_model":
                    selector.update_performance(model, "Test prompt", True, 1.0, 0.02)
                else:
                    selector.update_performance(model, "Test prompt", True, 5.0, 0.08)
            
            # Count recommendations before change
            fast_count_before = 0
            for i in range(10):
                model = selector.recommend_model("Test prompt")
                if model == "fast_model":
                    fast_count_before += 1
            
            # Now make slow_model perform better
            for i in range(30):
                selector.update_performance("slow_model", "Test prompt", True, 0.5, 0.01)
                selector.update_performance("fast_model", "Test prompt", False, 10.0, 0.10)
            
            # Count recommendations after change
            fast_count_after = 0
            for i in range(10):
                model = selector.recommend_model("Test prompt")
                if model == "fast_model":
                    fast_count_after += 1
            
            # Should adapt to new performance characteristics
            assert fast_count_after < fast_count_before
    
    def test_cold_start_behavior(self):
        """Test behavior when starting with no historical data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "performance.json")
            
            selector = MLModelSelector(
                provider_name="new_provider",
                models=["model_a", "model_b", "model_c"],
                default_model="model_a",
                data_path=data_path
            )
            
            # Should handle cold start gracefully
            model = selector.recommend_model("First request ever")
            assert model in ["model_a", "model_b", "model_c"]
            
            # Should cycle through models during warmup
            models_tried = set()
            for i in range(15):
                model = selector.recommend_model("Test prompt")
                models_tried.add(model)
                selector.update_performance(model, "Test prompt", True, 2.0, 0.05)
            
            # Should have tried all models
            assert len(models_tried) == 3