"""
Test suite for Local LLM Integration
Following TDD and AAA (Arrange, Act, Assert) principles

This test suite comprehensively tests the local LLM integration functionality
including Ollama client, model routing, fallback mechanisms, and performance.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json

from integrations.ollama_client import OllamaClient
from ai.ai_coordinator import AICoordinator
from core.local_model_manager import LocalModelManager, ModelStatus, ModelInfo
from ai.multi_model_ai import MultiModelAIOptimizer


class TestOllamaClient:
    """Test suite for OllamaClient class"""

    @pytest.fixture
    def mock_config(self) -> dict:
        """Arrange: Mock configuration for Ollama client"""
        return {
            "local_llm": {
                "enabled": True,
                "ollama_host": "localhost:11434",
                "preferred_models": {
                    "vision": "llava:13b",
                    "text": "mistral:7b",
                    "task_generation": "mistral:7b",
                    "fallback": "gemini"
                },
                "resource_limits": {
                    "max_cpu_usage": 80,
                    "max_memory_usage": 4096
                },
                "performance_tuning": {
                    "quantization_level": 4,
                    "batch_size": 1,
                    "timeout_seconds": 120
                },
                "auto_download": True,
                "max_concurrent": 1
            }
        }

    @pytest.fixture
    def ollama_client(self, mock_config) -> OllamaClient:
        """Arrange: Create OllamaClient instance"""
        return OllamaClient(mock_config)

    @pytest.mark.skip(reason="Requires actual ollama package for Client/AsyncClient creation")
    @pytest.mark.asyncio
    async def test_ollama_client_initialization_success(self, ollama_client):
        """Test successful Ollama client initialization"""
        # Arrange
        with patch('integrations.ollama_client.OLLAMA_AVAILABLE', True):
            # Mock the clients directly on the instance to avoid import issues
            mock_client_instance = Mock()
            mock_client_instance.list.return_value = {'models': []}
            ollama_client.client = mock_client_instance

            mock_async_client_instance = Mock()
            ollama_client.async_client = mock_async_client_instance

            # Mock the initialization steps
            with patch.object(ollama_client, '_check_server_health', return_value=True), \
                 patch.object(ollama_client, '_update_available_models'), \
                 patch.object(ollama_client, '_ensure_preferred_models'):

                # Act
                result = await ollama_client.initialize()

                # Assert
                assert result is True
                assert ollama_client.client is not None
                assert ollama_client.async_client is not None

    @pytest.mark.asyncio
    async def test_ollama_client_initialization_failure_no_package(self, ollama_client):
        """Test Ollama client initialization failure when package not available"""
        # Arrange
        with patch('integrations.ollama_client.OLLAMA_AVAILABLE', False):

            # Act
            result = await ollama_client.initialize()

            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_analyze_image_local_success(self, ollama_client):
        """Test successful local image analysis"""
        # Arrange
        mock_async_client = AsyncMock()
        ollama_client.async_client = mock_async_client
        
        mock_response = {
            'message': {
                'content': 'The kitchen appears clean with some dishes on the counter that need washing.'
            }
        }
        mock_async_client.chat.return_value = mock_response
        
        with patch.object(ollama_client, 'check_model_availability', return_value=True), \
             patch.object(ollama_client, '_read_image_file', return_value=b'fake_image_data'):

            # Act
            result = await ollama_client.analyze_image_local(
                image_path="test_image.jpg",
                model="llava:13b"
            )

            # Assert
            assert result is not None
            assert result["text"] == mock_response['message']['content']
            assert result["model"] == "llava:13b"
            assert result["provider"] == "ollama"
            assert "confidence" in result
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_analyze_image_local_model_unavailable(self, ollama_client):
        """Test image analysis when model is unavailable"""
        # Arrange
        ollama_client.async_client = AsyncMock()  # Initialize client first
        ollama_client.auto_download = False  # Disable auto-download for this test
        with patch.object(ollama_client, 'check_model_availability', return_value=False):

            # Act & Assert
            with pytest.raises(Exception, match="Model llava:13b not available"):
                await ollama_client.analyze_image_local(
                    image_path="test_image.jpg",
                    model="llava:13b"
                )

    @pytest.mark.asyncio
    async def test_generate_tasks_local_success(self, ollama_client):
        """Test successful local task generation"""
        # Arrange
        mock_async_client = AsyncMock()
        ollama_client.async_client = mock_async_client
        
        mock_response = {
            'message': {
                'content': '''[
                    {"task": "Wash dishes on counter", "priority": "high", "category": "hygiene", "estimated_time": 15},
                    {"task": "Wipe down countertops", "priority": "medium", "category": "hygiene", "estimated_time": 5}
                ]'''
            }
        }
        mock_async_client.chat.return_value = mock_response
        
        with patch.object(ollama_client, 'check_model_availability', return_value=True):

            # Act
            result = await ollama_client.generate_tasks_local(
                analysis="Kitchen needs cleaning",
                context={"zone_name": "Kitchen", "zone_purpose": "cooking"}
            )

            # Assert
            assert len(result) == 2
            assert result[0]["task"] == "Wash dishes on counter"
            assert result[0]["priority"] == "high"
            assert result[1]["task"] == "Wipe down countertops"

    @pytest.mark.asyncio
    async def test_check_model_availability_success(self, ollama_client):
        """Test successful model availability check"""
        # Arrange
        ollama_client.client = Mock()  # Initialize client first
        ollama_client._available_models = {"llava:13b", "mistral:7b"}

        # Act
        result = await ollama_client.check_model_availability("llava:13b")

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_download_model_success(self, ollama_client):
        """Test successful model download"""
        # Arrange
        mock_client = Mock()
        ollama_client.client = mock_client
        ollama_client.auto_download = True
        
        with patch.object(ollama_client, '_update_available_models') as mock_update:
            ollama_client._available_models = set()
            mock_update.side_effect = lambda: ollama_client._available_models.add("llava:13b")

            # Act
            result = await ollama_client.download_model("llava:13b")

            # Assert
            assert result is True
            mock_client.pull.assert_called_once_with("llava:13b")


class TestAICoordinatorLocalLLM:
    """Test suite for AI Coordinator local LLM integration"""

    @pytest.fixture
    def mock_config(self) -> dict:
        """Arrange: Mock configuration with local LLM enabled"""
        return {
            "ai_enhancements": {
                "local_llm": {
                    "enabled": True,
                    "preferred_models": {
                        "vision": "llava:13b",
                        "text": "mistral:7b"
                    },
                    "min_confidence": 0.6
                },
                "advanced_scene_understanding": True,
                "predictive_analytics": True
            }
        }

    @pytest.fixture
    def mock_multi_model_ai(self) -> Mock:
        """Arrange: Mock MultiModelAIOptimizer"""
        mock = Mock(spec=MultiModelAIOptimizer)
        mock.analyze_batch_optimized = AsyncMock()
        return mock

    @pytest.fixture
    def mock_local_model_manager(self) -> Mock:
        """Arrange: Mock LocalModelManager"""
        mock = Mock(spec=LocalModelManager)
        mock.initialize = AsyncMock(return_value=True)
        mock.ensure_model_loaded = AsyncMock(return_value=True)
        mock.analyze_image_with_model = AsyncMock()
        mock.generate_tasks_with_model = AsyncMock()
        mock.get_resource_metrics = AsyncMock()
        mock.get_performance_stats = AsyncMock()
        return mock

    @pytest.fixture
    def ai_coordinator(self, mock_config, mock_multi_model_ai, mock_local_model_manager) -> AICoordinator:
        """Arrange: Create AICoordinator with mocked dependencies"""
        return AICoordinator(
            config=mock_config,
            multi_model_ai=mock_multi_model_ai,
            local_model_manager=mock_local_model_manager
        )

    @pytest.mark.asyncio
    async def test_ai_coordinator_initialization_with_local_llm(self, ai_coordinator, mock_local_model_manager):
        """Test AI Coordinator initialization with local LLM enabled"""
        # Act
        await ai_coordinator.initialize()

        # Assert
        mock_local_model_manager.initialize.assert_called_once()
        assert ai_coordinator._local_llm_initialized is True

    @pytest.mark.asyncio
    async def test_select_and_route_model_local_available(self, ai_coordinator, mock_local_model_manager):
        """Test model routing when local model is available"""
        # Arrange
        ai_coordinator._local_llm_initialized = True
        mock_local_model_manager.ensure_model_loaded.return_value = True

        # Act
        model_name, provider = await ai_coordinator._select_and_route_model("scheduled", "image_analysis")

        # Assert
        assert provider == "local"
        assert model_name == "llava:13b"

    @pytest.mark.asyncio
    async def test_select_and_route_model_fallback_to_cloud(self, ai_coordinator, mock_local_model_manager):
        """Test model routing fallback to cloud when local unavailable"""
        # Arrange
        ai_coordinator._local_llm_initialized = False

        # Act
        model_name, provider = await ai_coordinator._select_and_route_model("manual", "image_analysis")

        # Assert
        assert provider == "cloud"
        assert model_name in ["gemini-pro", "claude-sonnet", "gemini-flash"]

    @pytest.mark.asyncio
    async def test_analyze_with_local_model_success(self, ai_coordinator, mock_local_model_manager):
        """Test successful analysis with local model"""
        # Arrange
        mock_local_analysis = {
            "text": "Kitchen is moderately clean with some dishes to wash",
            "confidence": 0.8,
            "timestamp": 1234567890,
            "analysis_time": 2.5
        }
        mock_local_model_manager.analyze_image_with_model.return_value = mock_local_analysis

        mock_local_tasks = [
            {"task": "Wash dishes", "priority": "high", "category": "hygiene", "estimated_time": 15}
        ]
        mock_local_model_manager.generate_tasks_with_model.return_value = mock_local_tasks

        # Act
        result, was_cached = await ai_coordinator._analyze_with_local_model(
            image_path="test.jpg",
            zone_name="Kitchen",
            zone_purpose="cooking",
            active_tasks=[],
            ignore_rules=[],
            model_name="llava:13b"
        )

        # Assert
        assert result is not None
        assert was_cached is False
        assert result["analysis_summary"] == mock_local_analysis["text"]
        assert result["new_tasks"] == mock_local_tasks
        assert result["analysis_metadata"]["provider"] == "ollama"

    @pytest.mark.asyncio
    async def test_analyze_with_local_model_low_confidence_fallback(self, ai_coordinator, mock_local_model_manager, mock_multi_model_ai):
        """Test fallback to cloud when local model confidence is low"""
        # Arrange
        mock_local_analysis = {
            "text": "Unclear analysis",
            "confidence": 0.3,  # Below threshold
            "timestamp": 1234567890
        }
        mock_local_model_manager.analyze_image_with_model.return_value = mock_local_analysis

        mock_cloud_result = {"analysis_summary": "Cloud analysis result"}
        mock_multi_model_ai.analyze_batch_optimized.return_value = (mock_cloud_result, False)

        # Act
        result, was_cached = await ai_coordinator._analyze_with_local_model(
            image_path="test.jpg",
            zone_name="Kitchen",
            zone_purpose="cooking",
            active_tasks=[],
            ignore_rules=[],
            model_name="llava:13b"
        )

        # Assert
        assert result == mock_cloud_result
        mock_multi_model_ai.analyze_batch_optimized.assert_called_once()


class TestLocalModelManager:
    """Test suite for LocalModelManager class"""

    @pytest.fixture
    def mock_config(self) -> dict:
        """Arrange: Mock configuration for LocalModelManager"""
        return {
            "local_llm": {
                "ollama_host": "localhost:11434",
                "resource_limits": {
                    "max_cpu_usage": 80,
                    "max_memory_usage": 4096
                },
                "performance_tuning": {
                    "auto_unload_minutes": 30,
                    "max_loaded_models": 2,
                    "health_check_interval": 300
                }
            }
        }

    @pytest.fixture
    def model_manager(self, mock_config) -> LocalModelManager:
        """Arrange: Create LocalModelManager instance"""
        return LocalModelManager(mock_config)

    @pytest.mark.asyncio
    async def test_model_manager_initialization_success(self, model_manager):
        """Test successful model manager initialization"""
        # Arrange
        with patch('core.local_model_manager.OLLAMA_AVAILABLE', True):
            # Mock the OllamaClient initialization
            mock_ollama_client = Mock()
            mock_ollama_client.initialize = AsyncMock(return_value=True)
            mock_ollama_client._available_models = {'llava:13b', 'mistral:7b'}
            model_manager.ollama_client = mock_ollama_client

            # Mock the initialization steps
            with patch.object(model_manager, '_start_background_tasks'):

                # Act
                result = await model_manager.initialize()

                # Assert
                assert result is True
                assert len(model_manager.models) == 2
                assert 'llava:13b' in model_manager.models
                assert 'mistral:7b' in model_manager.models

    @pytest.mark.asyncio
    async def test_ensure_model_loaded_success(self, model_manager):
        """Test successful model loading"""
        # Arrange
        model_manager.ollama_client = Mock()
        model_manager.ollama_client.generate.return_value = {"response": "test"}
        model_manager.models['test_model'] = ModelInfo(name='test_model')
        
        with patch.object(model_manager, '_check_resource_constraints', return_value=True):

            # Act
            result = await model_manager.ensure_model_loaded('test_model')

            # Assert
            assert result is True
            assert 'test_model' in model_manager.loaded_models
            assert model_manager.models['test_model'].status == ModelStatus.LOADED

    @pytest.mark.asyncio
    async def test_unload_model_success(self, model_manager):
        """Test successful model unloading"""
        # Arrange
        model_manager.loaded_models.add('test_model')
        model_manager.models['test_model'] = ModelInfo(name='test_model', status=ModelStatus.LOADED)

        # Act
        result = await model_manager.unload_model('test_model')

        # Assert
        assert result is True
        assert 'test_model' not in model_manager.loaded_models
        assert model_manager.models['test_model'].status == ModelStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_get_performance_stats(self, model_manager):
        """Test performance statistics retrieval"""
        # Arrange
        model_manager.models['test_model'] = ModelInfo(
            name='test_model',
            success_count=10,
            error_count=2
        )
        model_manager.loaded_models.add('test_model')

        # Act
        stats = await model_manager.get_performance_stats()

        # Assert
        assert 'models' in stats
        assert 'system' in stats
        assert 'test_model' in stats['models']
        assert stats['models']['test_model']['success_rate'] == 10/12
        assert stats['system']['loaded_models'] == 1


class TestLocalLLMFallbackReliability:
    """Test suite for local LLM fallback reliability"""

    @pytest.mark.asyncio
    async def test_ollama_server_down_fallback(self):
        """Test fallback when Ollama server is down"""
        # Arrange
        config = {"local_llm": {"enabled": True}}
        ollama_client = OllamaClient(config)

        with patch('integrations.ollama_client.OLLAMA_AVAILABLE', True):
            # Mock the health check to fail
            with patch.object(ollama_client, '_check_server_health', side_effect=Exception("Connection refused")):

                # Act
                result = await ollama_client.initialize()

                # Assert
                assert result is False

    @pytest.fixture
    def mock_config(self) -> dict:
        """Arrange: Mock configuration for fallback tests"""
        return {
            "local_llm": {
                "enabled": True,
                "performance_tuning": {"timeout_seconds": 1}
            }
        }

    @pytest.mark.asyncio
    async def test_model_inference_timeout_fallback(self, mock_config):
        """Test fallback when model inference times out"""
        # Arrange
        ollama_client = OllamaClient(mock_config)
        ollama_client.async_client = AsyncMock()
        ollama_client.async_client.chat.side_effect = asyncio.TimeoutError()
        
        with patch.object(ollama_client, 'check_model_availability', return_value=True), \
             patch.object(ollama_client, '_read_image_file', return_value=b'fake_data'):

            # Act & Assert
            with pytest.raises(Exception, match="Analysis timeout"):
                await ollama_client.analyze_image_local("test.jpg")

    @pytest.mark.asyncio
    async def test_end_to_end_local_to_cloud_fallback(self):
        """Test end-to-end fallback from local to cloud analysis"""
        # Arrange
        config = {
            "ai_enhancements": {
                "local_llm": {"enabled": True, "min_confidence": 0.8},
                "advanced_scene_understanding": True,
                "predictive_analytics": True
            }
        }
        
        mock_multi_model_ai = Mock(spec=MultiModelAIOptimizer)
        mock_multi_model_ai.analyze_batch_optimized = AsyncMock(
            return_value=({"analysis_summary": "Cloud analysis"}, False)
        )
        
        mock_local_model_manager = Mock(spec=LocalModelManager)
        mock_local_model_manager.initialize = AsyncMock(return_value=False)  # Local fails

        ai_coordinator = AICoordinator(
            config=config,
            multi_model_ai=mock_multi_model_ai,
            local_model_manager=mock_local_model_manager
        )

        # Act
        await ai_coordinator.initialize()
        model_name, provider = await ai_coordinator._select_and_route_model("manual", "image_analysis")

        # Assert
        assert provider == "cloud"
        assert ai_coordinator._local_llm_initialized is False


class TestLocalModelManagerIntegration:
    """Test suite for LocalModelManager integration with AICoordinator"""

    @pytest.fixture
    def mock_config(self) -> dict:
        """Arrange: Mock configuration for integration tests"""
        return {
            "ai_enhancements": {
                "local_llm": {
                    "enabled": True,
                    "preferred_models": {
                        "vision": "llava:13b",
                        "text": "mistral:7b",
                        "task_generation": "mistral:7b"
                    },
                    "min_confidence": 0.6
                }
            }
        }

    @pytest.fixture
    def mock_multi_model_ai(self) -> Mock:
        """Arrange: Mock MultiModelAIOptimizer"""
        mock = Mock(spec=MultiModelAIOptimizer)
        mock.analyze_batch_optimized = AsyncMock()
        return mock

    @pytest.fixture
    def mock_local_model_manager(self) -> Mock:
        """Arrange: Mock LocalModelManager with full integration"""
        mock = Mock(spec=LocalModelManager)
        mock.initialize = AsyncMock(return_value=True)
        mock.ensure_model_loaded = AsyncMock(return_value=True)
        mock.analyze_image_with_model = AsyncMock()
        mock.generate_tasks_with_model = AsyncMock()
        mock.get_resource_metrics = AsyncMock()
        mock.get_performance_stats = AsyncMock()
        return mock

    @pytest.fixture
    def ai_coordinator(self, mock_config, mock_multi_model_ai, mock_local_model_manager) -> AICoordinator:
        """Arrange: Create AICoordinator with LocalModelManager integration"""
        return AICoordinator(
            config=mock_config,
            multi_model_ai=mock_multi_model_ai,
            local_model_manager=mock_local_model_manager
        )

    @pytest.mark.asyncio
    async def test_ai_coordinator_delegates_to_local_model_manager(self, ai_coordinator, mock_local_model_manager):
        """Test that AICoordinator properly delegates to LocalModelManager"""
        # Arrange
        ai_coordinator._local_llm_initialized = True

        mock_analysis = {
            "text": "Test analysis",
            "confidence": 0.8,
            "timestamp": time.time()
        }
        mock_local_model_manager.analyze_image_with_model.return_value = mock_analysis

        mock_tasks = [{"task": "Test task", "priority": "medium"}]
        mock_local_model_manager.generate_tasks_with_model.return_value = mock_tasks

        # Act
        result, was_cached = await ai_coordinator._analyze_with_local_model(
            image_path="test.jpg",
            zone_name="TestZone",
            zone_purpose="testing",
            active_tasks=[],
            ignore_rules=[],
            model_name="llava:13b"
        )

        # Assert
        mock_local_model_manager.analyze_image_with_model.assert_called_once_with(
            model_name="llava:13b",
            image_path="test.jpg"
        )
        mock_local_model_manager.generate_tasks_with_model.assert_called_once()
        assert result["analysis_summary"] == "Test analysis"
        assert result["new_tasks"] == mock_tasks

    @pytest.mark.asyncio
    async def test_model_lifecycle_management_integration(self, ai_coordinator, mock_local_model_manager):
        """Test model lifecycle management through LocalModelManager"""
        # Arrange
        ai_coordinator._local_llm_initialized = True

        # Act
        model_name, provider = await ai_coordinator._select_and_route_model("scheduled", "image_analysis")

        # Assert
        assert provider == "local"
        assert model_name == "llava:13b"
        mock_local_model_manager.ensure_model_loaded.assert_called_once_with("llava:13b")

    @pytest.mark.asyncio
    async def test_resource_constraint_handling_integration(self, ai_coordinator, mock_local_model_manager):
        """Test resource constraint handling through LocalModelManager"""
        # Arrange
        ai_coordinator._local_llm_initialized = True
        mock_local_model_manager.ensure_model_loaded.return_value = False  # Resource constraints

        # Act
        model_name, provider = await ai_coordinator._select_and_route_model("manual", "image_analysis")

        # Assert
        assert provider == "cloud"  # Should fallback to cloud
        mock_local_model_manager.ensure_model_loaded.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_metrics_integration(self, ai_coordinator, mock_local_model_manager):
        """Test that performance metrics are accessible through LocalModelManager"""
        # Arrange
        mock_stats = {
            "models": {
                "llava:13b": {
                    "success_rate": 0.95,
                    "total_requests": 100,
                    "last_used": "2024-01-01T00:00:00"
                }
            },
            "system": {
                "loaded_models": 2,
                "total_models": 5
            }
        }
        mock_local_model_manager.get_performance_stats.return_value = mock_stats

        # Act
        stats = await ai_coordinator.local_model_manager.get_performance_stats()

        # Assert
        assert stats == mock_stats
        assert stats["models"]["llava:13b"]["success_rate"] == 0.95


class TestEndToEndIntegration:
    """Test suite for end-to-end integration from ZoneManager to LocalModelManager"""

    @pytest.mark.asyncio
    async def test_full_analysis_pipeline_with_local_manager(self):
        """Test complete workflow: ZoneManager → AICoordinator → LocalModelManager → OllamaClient"""
        # Arrange
        config = {
            "ai_enhancements": {
                "local_llm": {
                    "enabled": True,
                    "preferred_models": {
                        "vision": "llava:13b",
                        "task_generation": "mistral:7b"
                    },
                    "min_confidence": 0.6
                }
            }
        }

        # Mock the entire chain
        mock_multi_model_ai = Mock(spec=MultiModelAIOptimizer)
        mock_local_model_manager = Mock(spec=LocalModelManager)
        mock_local_model_manager.initialize = AsyncMock(return_value=True)
        mock_local_model_manager.ensure_model_loaded = AsyncMock(return_value=True)

        # Mock successful local analysis
        mock_analysis = {
            "text": "Kitchen needs cleaning - dishes on counter",
            "confidence": 0.8,
            "timestamp": time.time(),
            "analysis_time": 2.5
        }
        mock_local_model_manager.analyze_image_with_model = AsyncMock(return_value=mock_analysis)

        mock_tasks = [
            {"task": "Wash dishes on counter", "priority": "high", "category": "hygiene", "estimated_time": 15}
        ]
        mock_local_model_manager.generate_tasks_with_model = AsyncMock(return_value=mock_tasks)

        # Create AICoordinator with mocked dependencies
        ai_coordinator = AICoordinator(
            config=config,
            multi_model_ai=mock_multi_model_ai,
            local_model_manager=mock_local_model_manager
        )

        # Act
        await ai_coordinator.initialize()

        # Simulate the full analysis workflow
        result = await ai_coordinator.analyze_zone(
            zone_name="Kitchen",
            image_path="test_kitchen.jpg",
            priority="scheduled",
            zone_purpose="cooking",
            active_tasks=[],
            ignore_rules=[]
        )

        # Assert
        assert ai_coordinator._local_llm_initialized is True
        mock_local_model_manager.initialize.assert_called_once()
        mock_local_model_manager.analyze_image_with_model.assert_called_once()
        mock_local_model_manager.generate_tasks_with_model.assert_called_once()

        assert result is not None
        assert result["analysis_summary"] == mock_analysis["text"]
        # The tasks go through enhancement processing, so check the core assessment
        assert result["core_assessment"]["new_tasks"] == mock_tasks

    @pytest.mark.asyncio
    async def test_resource_monitoring_integration(self):
        """Test background monitoring tasks work with full integration"""
        # Arrange
        config = {
            "ai_enhancements": {
                "local_llm": {
                    "enabled": True,
                    "resource_limits": {
                        "max_cpu_usage": 80,
                        "max_memory_usage": 4096
                    }
                }
            }
        }

        mock_multi_model_ai = Mock(spec=MultiModelAIOptimizer)
        mock_local_model_manager = Mock(spec=LocalModelManager)
        mock_local_model_manager.initialize = AsyncMock(return_value=True)

        # Mock resource metrics
        mock_metrics = {
            "cpu_percent": 45.0,
            "memory_percent": 60.0,
            "memory_used_mb": 2048.0,
            "memory_available_mb": 2048.0,
            "timestamp": datetime.now()
        }
        mock_local_model_manager.get_resource_metrics = AsyncMock(return_value=mock_metrics)

        ai_coordinator = AICoordinator(
            config=config,
            multi_model_ai=mock_multi_model_ai,
            local_model_manager=mock_local_model_manager
        )

        # Act
        await ai_coordinator.initialize()
        metrics = await ai_coordinator.local_model_manager.get_resource_metrics()

        # Assert
        assert metrics["cpu_percent"] == 45.0
        assert metrics["memory_used_mb"] == 2048.0
        mock_local_model_manager.get_resource_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_switching_performance(self):
        """Test switching between models under resource constraints"""
        # Arrange
        config = {
            "ai_enhancements": {
                "local_llm": {
                    "enabled": True,
                    "preferred_models": {
                        "vision": "llava:13b",
                        "text": "mistral:7b",
                        "fallback": "gemini"
                    }
                }
            }
        }

        mock_multi_model_ai = Mock(spec=MultiModelAIOptimizer)
        mock_local_model_manager = Mock(spec=LocalModelManager)
        mock_local_model_manager.initialize = AsyncMock(return_value=True)

        # First call succeeds (model available)
        # Second call fails (resource constraints)
        mock_local_model_manager.ensure_model_loaded = AsyncMock(side_effect=[True, False])

        ai_coordinator = AICoordinator(
            config=config,
            multi_model_ai=mock_multi_model_ai,
            local_model_manager=mock_local_model_manager
        )

        await ai_coordinator.initialize()

        # Act - First call should use local
        model1, provider1 = await ai_coordinator._select_and_route_model("scheduled", "image_analysis")

        # Act - Second call should fallback to cloud due to resource constraints
        model2, provider2 = await ai_coordinator._select_and_route_model("scheduled", "image_analysis")

        # Assert
        assert provider1 == "local"
        assert model1 == "llava:13b"

        assert provider2 == "cloud"
        assert model2 == "gemini-flash"  # Should fallback to cloud model

        # Verify ensure_model_loaded was called twice
        assert mock_local_model_manager.ensure_model_loaded.call_count == 2

    @pytest.mark.asyncio
    async def test_fallback_reliability_under_failure_conditions(self):
        """Test system reliability when local models fail at various points"""
        # Arrange
        config = {
            "ai_enhancements": {
                "local_llm": {
                    "enabled": True,
                    "preferred_models": {
                        "vision": "llava:13b",
                        "fallback": "gemini"
                    },
                    "min_confidence": 0.7
                }
            }
        }

        mock_multi_model_ai = Mock(spec=MultiModelAIOptimizer)
        mock_cloud_result = {"analysis_summary": "Cloud fallback analysis"}
        mock_multi_model_ai.analyze_batch_optimized = AsyncMock(return_value=(mock_cloud_result, False))

        mock_local_model_manager = Mock(spec=LocalModelManager)
        mock_local_model_manager.initialize = AsyncMock(return_value=True)
        mock_local_model_manager.ensure_model_loaded = AsyncMock(return_value=True)

        # Mock low confidence analysis that should trigger fallback
        mock_low_confidence_analysis = {
            "text": "Unclear image analysis",
            "confidence": 0.4,  # Below threshold
            "timestamp": time.time()
        }
        mock_local_model_manager.analyze_image_with_model = AsyncMock(return_value=mock_low_confidence_analysis)

        ai_coordinator = AICoordinator(
            config=config,
            multi_model_ai=mock_multi_model_ai,
            local_model_manager=mock_local_model_manager
        )

        await ai_coordinator.initialize()

        # Act - Should fallback to cloud due to low confidence
        result, was_cached = await ai_coordinator._analyze_with_local_model(
            image_path="unclear_image.jpg",
            zone_name="TestZone",
            zone_purpose="testing",
            active_tasks=[],
            ignore_rules=[],
            model_name="llava:13b"
        )

        # Assert
        assert result == mock_cloud_result
        mock_local_model_manager.analyze_image_with_model.assert_called_once()
        mock_multi_model_ai.analyze_batch_optimized.assert_called_once()  # Fallback was triggered
