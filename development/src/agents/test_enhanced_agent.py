#!/usr/bin/env python3
"""
Test Suite for Enhanced Gemini Collaboration Agent
Validates quota management, error recovery, and intelligent model selection
"""

import os
import time
from unittest.mock import patch, MagicMock
from quota_manager import QuotaManager, ApiKeyStatus, ModelType
from enhanced_gemini_wrapper import EnhancedGeminiWrapper, GeminiCollaborationError


class TestQuotaManager:
    """Test suite for QuotaManager functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Mock environment variables
        self.mock_env = {
            "GEMINI_API_KEY_1": "test_key_1",
            "GEMINI_API_KEY_2": "test_key_2", 
            "GEMINI_API_KEY_3": "test_key_3",
            "GEMINI_API_KEY_4": "test_key_4"
        }
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1", "GEMINI_API_KEY_2": "test_key_2"})
    def test_quota_manager_initialization(self):
        """Test that QuotaManager initializes correctly with API keys"""
        manager = QuotaManager()
        
        assert len(manager.api_keys) == 2
        assert manager.api_keys[0].key_id == "key_1"
        assert manager.api_keys[1].key_id == "key_2"
        assert all(key.is_available for key in manager.api_keys)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_quota_manager_no_keys(self):
        """Test that QuotaManager raises error when no API keys available"""
        try:
            QuotaManager()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "No valid Gemini API keys found" in str(e)
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_model_selection_logic(self):
        """Test intelligent model selection based on complexity and quota"""
        manager = QuotaManager()
        
        # High complexity with good quota should use PRO
        model = manager.select_model("high", 100)
        assert model == ModelType.PRO
        
        # High complexity with low quota should use FLASH
        model = manager.select_model("high", 10)
        assert model == ModelType.FLASH
        
        # Medium complexity with good quota should use PRO
        model = manager.select_model("medium", 50)
        assert model == ModelType.PRO
        
        # Low complexity should always use FLASH
        model = manager.select_model("low", 100)
        assert model == ModelType.FLASH
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_quota_tracking(self):
        """Test quota tracking and reset functionality"""
        manager = QuotaManager()
        key = manager.api_keys[0]
        
        # Initial state
        assert key.daily_remaining == 250
        assert key.minute_remaining == 10
        
        # Record some requests
        for _ in range(5):
            key.record_request()
        
        assert key.daily_remaining == 245
        assert key.minute_remaining == 5
        
        # Test minute reset
        key.last_minute_reset = time.time() - 61  # Simulate 61 seconds ago
        key.reset_minute_counter()
        assert key.minute_remaining == 10
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1", "GEMINI_API_KEY_2": "test_key_2"})
    def test_key_cycling(self):
        """Test intelligent key cycling"""
        manager = QuotaManager()
        
        # Exhaust first key's minute quota
        first_key = manager.api_keys[0]
        for _ in range(10):
            first_key.record_request()
        
        # Should select second key
        optimal_key = manager.get_optimal_key()
        assert optimal_key.key_id == "key_2"
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_batch_strategy(self):
        """Test batch strategy calculation"""
        manager = QuotaManager()
        
        # Test immediate strategy
        strategy = manager.get_batch_strategy(5)
        assert strategy["strategy"] == "immediate"
        assert strategy["batch_size"] == 5
        
        # Test throttled strategy
        strategy = manager.get_batch_strategy(50)
        assert strategy["strategy"] == "throttled"
        
        # Exhaust daily quota and test partial strategy
        key = manager.api_keys[0]
        key.requests_today = 250
        strategy = manager.get_batch_strategy(10)
        assert strategy["strategy"] == "partial"


class TestEnhancedGeminiWrapper:
    """Test suite for EnhancedGeminiWrapper functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.mock_env = {
            "GEMINI_API_KEY_1": "test_key_1",
            "GEMINI_API_KEY_2": "test_key_2"
        }
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_wrapper_initialization(self):
        """Test that wrapper initializes correctly"""
        wrapper = EnhancedGeminiWrapper()
        
        assert wrapper.quota_manager is not None
        assert wrapper.fallback_mode is False
        assert len(wrapper.request_history) == 0
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_claude_only_response(self):
        """Test Claude-only fallback response generation"""
        wrapper = EnhancedGeminiWrapper()
        
        response = wrapper._claude_only_response(
            "Test prompt", 
            "Testing fallback mode"
        )
        
        assert response["success"] is True
        assert response["source"] == "claude_fallback"
        assert "CLAUDE-ONLY MODE ACTIVE" in response["response"]
        assert "Testing fallback mode" in response["response"]
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_fallback_mode_activation(self):
        """Test that fallback mode activates correctly"""
        wrapper = EnhancedGeminiWrapper()
        
        # Force quota exhaustion
        wrapper.quota_manager.api_keys[0].requests_today = 250
        
        response = wrapper.chat_with_gemini("Test prompt", "medium")
        
        assert wrapper.fallback_mode is True
        assert response["source"] == "claude_fallback"
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_error_handling(self):
        """Test error handling and recovery mechanisms"""
        wrapper = EnhancedGeminiWrapper()
        
        # Mock a quota exceeded error
        with patch.object(wrapper, '_execute_gemini_request', side_effect=GeminiCollaborationError("Quota exceeded")):
            response = wrapper.chat_with_gemini("Test prompt", "high", max_retries=1)
            
            assert wrapper.fallback_mode is True
            assert response["source"] == "claude_fallback"
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_request_history_tracking(self):
        """Test that request history is tracked correctly"""
        wrapper = EnhancedGeminiWrapper()
        
        # Force Claude-only mode to test history tracking
        wrapper.fallback_mode = True
        
        response = wrapper.chat_with_gemini("Test prompt", "medium")
        
        assert len(wrapper.request_history) == 1
        record = wrapper.request_history[0]
        assert record["prompt_length"] == len("Test prompt")
        assert record["response_success"] is True
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_status_reporting(self):
        """Test comprehensive status reporting"""
        wrapper = EnhancedGeminiWrapper()
        
        status = wrapper.get_status()
        
        assert "fallback_mode" in status
        assert "quota_status" in status
        assert "request_history_length" in status
        assert "performance_metrics" in status
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_fallback_mode_reset(self):
        """Test that fallback mode can be reset"""
        wrapper = EnhancedGeminiWrapper()
        
        # Activate fallback mode
        wrapper.fallback_mode = True
        assert wrapper.fallback_mode is True
        
        # Reset fallback mode
        wrapper.reset_fallback_mode()
        assert wrapper.fallback_mode is False


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios"""
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1", "GEMINI_API_KEY_2": "test_key_2"})
    def test_complete_workflow_simulation(self):
        """Test complete Claude-Gemini collaboration workflow"""
        wrapper = EnhancedGeminiWrapper()
        
        # Simulate 7-step workflow
        steps = [
            ("Consult", "high"),
            ("Analyze", "medium"),
            ("Refine", "medium"),
            ("Generate", "high"),
            ("Review", "low"),
            ("Implement", "medium"),
            ("Validate", "low")
        ]
        
        for step_name, complexity in steps:
            response = wrapper.chat_with_gemini(
                f"Step {step_name}: Complex system refactoring task",
                complexity
            )
            
            assert response["success"] is True
            assert len(response["response"]) > 0
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"})
    def test_quota_exhaustion_graceful_degradation(self):
        """Test graceful degradation when quota is exhausted"""
        wrapper = EnhancedGeminiWrapper()
        
        # Exhaust quota
        wrapper.quota_manager.api_keys[0].requests_today = 250
        
        # Should still work in Claude-only mode
        response = wrapper.chat_with_gemini("Test prompt after quota exhaustion")
        
        assert response["success"] is True
        assert response["source"] == "claude_fallback"
        assert wrapper.fallback_mode is True
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1", "GEMINI_API_KEY_2": "test_key_2"})
    def test_high_volume_request_handling(self):
        """Test handling of high-volume requests with intelligent batching"""
        wrapper = EnhancedGeminiWrapper()
        
        # Simulate high-volume usage
        responses = []
        for i in range(20):
            response = wrapper.chat_with_gemini(
                f"Request {i+1}: Analysis task",
                "medium" if i % 2 == 0 else "low"
            )
            responses.append(response)
        
        # Should handle all requests either via Gemini or Claude fallback
        assert all(r["success"] for r in responses)
        
        # Should show intelligent key usage
        status = wrapper.get_status()
        assert status["request_history_length"] == 20


def run_tests():
    """Run all tests manually without pytest"""
    
    print("🧪 Running Enhanced Gemini Agent Tests...\n")
    
    # Test QuotaManager
    print("📊 Testing QuotaManager...")
    try:
        with patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"}):
            manager = QuotaManager()
            print("✓ QuotaManager initialization")
            
            model = manager.select_model("high", 100)
            assert model == ModelType.PRO
            print("✓ Model selection logic")
            
            status = manager.get_quota_status()
            assert status["available_keys"] == 1
            print("✓ Quota status reporting")
            
    except Exception as e:
        print(f"✗ QuotaManager test failed: {e}")
    
    # Test EnhancedGeminiWrapper
    print("\n🤖 Testing EnhancedGeminiWrapper...")
    try:
        with patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"}):
            wrapper = EnhancedGeminiWrapper()
            print("✓ Wrapper initialization")
            
            # Test Claude-only response
            response = wrapper._claude_only_response("Test", "Test reason")
            assert response["success"] is True
            print("✓ Claude-only response generation")
            
            # Test fallback activation
            wrapper.quota_manager.api_keys[0].requests_today = 250
            response = wrapper.chat_with_gemini("Test prompt")
            assert wrapper.fallback_mode is True
            print("✓ Fallback mode activation")
            
            # Test status reporting
            status = wrapper.get_status()
            assert "fallback_mode" in status
            print("✓ Status reporting")
            
    except Exception as e:
        print(f"✗ EnhancedGeminiWrapper test failed: {e}")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    run_tests()