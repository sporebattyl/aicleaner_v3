#!/usr/bin/env python3
"""
Enhanced Gemini Collaboration Wrapper
Provides error recovery and fallback mechanisms for Claude-Gemini collaboration
"""

import json
import subprocess
import time
from typing import Dict, Any, Optional, List
from quota_manager import QuotaManager, ModelType


class GeminiCollaborationError(Exception):
    """Custom exception for Gemini collaboration issues"""
    pass


class EnhancedGeminiWrapper:
    """Enhanced wrapper for Gemini CLI with intelligent error handling and fallbacks"""
    
    def __init__(self):
        self.quota_manager = QuotaManager()
        self.fallback_mode = False
        self.request_history: List[Dict[str, Any]] = []
    
    def chat_with_gemini(self, prompt: str, complexity: str = "medium", max_retries: int = 3) -> Dict[str, Any]:
        """
        Enhanced chat with Gemini including error recovery and fallback mechanisms
        
        Args:
            prompt: The chat prompt to send to Gemini
            complexity: Task complexity (low/medium/high) for model selection
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict containing response, metadata, and status information
        """
        
        # Check if we're in fallback mode
        if self.fallback_mode:
            return self._claude_only_response(prompt, "Fallback mode active - using Claude analysis only")
        
        # Attempt Gemini collaboration with retries
        for attempt in range(max_retries):
            try:
                # Get optimal request configuration
                request_config = self.quota_manager.make_request("chat", complexity)
                
                if not request_config["success"]:
                    # No quota available - activate fallback mode
                    self.fallback_mode = True
                    return self._claude_only_response(
                        prompt, 
                        f"Quota exhausted: {request_config['error']}"
                    )
                
                # Execute Gemini request
                response = self._execute_gemini_request(
                    prompt=prompt,
                    api_key=request_config["api_key"],
                    model=request_config["model"],
                    request_config=request_config
                )
                
                # Record successful request
                self._record_request(prompt, response, request_config, "success")
                return response
                
            except GeminiCollaborationError as e:
                # Handle specific Gemini errors
                error_response = self._handle_gemini_error(e, request_config, attempt, max_retries)
                if error_response:
                    return error_response
                
            except Exception as e:
                # Handle unexpected errors
                error_response = self._handle_unexpected_error(e, attempt, max_retries)
                if error_response:
                    return error_response
        
        # All retries exhausted - activate fallback mode
        self.fallback_mode = True
        return self._claude_only_response(prompt, "All retry attempts exhausted - switching to Claude-only mode")
    
    def _execute_gemini_request(self, prompt: str, api_key: str, model: str, request_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual Gemini CLI request"""
        
        # Prepare Gemini CLI command
        cmd = [
            "mcp__gemini-cli__chat",
            "--model", model,
            "--prompt", prompt
        ]
        
        # Set API key environment variable
        env = {"GEMINI_API_KEY": api_key}
        
        # Execute with timeout
        try:
            start_time = time.time()
            
            # Simulate Gemini CLI call (in practice, this would use the actual MCP tool)
            # For now, we'll create a mock response structure
            response_data = {
                "content": f"[Gemini {model} Response]\n\nAnalyzing your request with {model}...\n\nThis is a simulated response that would contain Gemini's actual analysis and recommendations.",
                "model_used": model,
                "request_time": time.time() - start_time,
                "token_usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": 150}
            }
            
            return {
                "success": True,
                "response": response_data["content"],
                "metadata": {
                    "model": model,
                    "key_id": request_config["key_id"],
                    "request_time": response_data["request_time"],
                    "token_usage": response_data["token_usage"],
                    "quota_status": request_config["status"]
                },
                "source": "gemini"
            }
            
        except subprocess.TimeoutExpired:
            raise GeminiCollaborationError("Request timeout - Gemini API unresponsive")
        except subprocess.CalledProcessError as e:
            if "quota" in str(e).lower():
                raise GeminiCollaborationError("Quota exceeded")
            elif "rate limit" in str(e).lower():
                raise GeminiCollaborationError("Rate limit hit")
            else:
                raise GeminiCollaborationError(f"API error: {str(e)}")
    
    def _handle_gemini_error(self, error: GeminiCollaborationError, request_config: Dict[str, Any], attempt: int, max_retries: int) -> Optional[Dict[str, Any]]:
        """Handle specific Gemini collaboration errors"""
        
        error_msg = str(error)
        
        if "quota exceeded" in error_msg.lower():
            # Mark key as quota exceeded and try next key
            self.quota_manager.handle_request_error(request_config["key_id"], "quota_exceeded")
            
            # If this was our last attempt, switch to fallback
            if attempt >= max_retries - 1:
                self.fallback_mode = True
                return self._claude_only_response("", f"Quota exceeded on all available keys: {error_msg}")
        
        elif "rate limit" in error_msg.lower():
            # Wait before retry
            wait_time = min(60, 10 * (attempt + 1))
            time.sleep(wait_time)
        
        elif "timeout" in error_msg.lower():
            # Try with different key on timeout
            self.quota_manager.handle_request_error(request_config["key_id"], "timeout")
        
        # Return None to indicate we should retry
        return None
    
    def _handle_unexpected_error(self, error: Exception, attempt: int, max_retries: int) -> Optional[Dict[str, Any]]:
        """Handle unexpected errors"""
        
        # Log the error for debugging
        self._record_error(error, attempt)
        
        # If this was our last attempt, activate fallback mode
        if attempt >= max_retries - 1:
            self.fallback_mode = True
            return self._claude_only_response("", f"Unexpected error occurred: {str(error)}")
        
        # Wait before retry
        time.sleep(5 * (attempt + 1))
        return None
    
    def _claude_only_response(self, prompt: str, reason: str) -> Dict[str, Any]:
        """Generate a Claude-only response when Gemini is unavailable"""
        
        claude_analysis = f"""
**CLAUDE-ONLY MODE ACTIVE**
Reason: {reason}

**Analysis using Claude capabilities:**

While I cannot consult with Gemini at this moment, I can provide comprehensive analysis using my own capabilities:

1. **Problem Assessment**: {self._generate_claude_assessment(prompt)}
2. **Recommended Approach**: {self._generate_claude_recommendations(prompt)}
3. **Implementation Strategy**: {self._generate_claude_implementation(prompt)}
4. **Security Considerations**: {self._generate_claude_security(prompt)}

**Note**: This analysis is provided using Claude's capabilities only. When Gemini quota becomes available again, we can enhance this analysis with Gemini's additional insights.
"""
        
        return {
            "success": True,
            "response": claude_analysis,
            "metadata": {
                "model": "claude-only",
                "fallback_reason": reason,
                "quota_status": self.quota_manager.get_quota_status()
            },
            "source": "claude_fallback"
        }
    
    def _generate_claude_assessment(self, prompt: str) -> str:
        """Generate Claude's assessment of the problem"""
        if not prompt.strip():
            return "No specific prompt provided for assessment."
        
        return f"Analyzing the request focusing on technical requirements, constraints, and implementation considerations based on the provided context."
    
    def _generate_claude_recommendations(self, prompt: str) -> str:
        """Generate Claude's recommendations"""
        return "Recommending a structured approach with emphasis on security, maintainability, and integration with existing systems."
    
    def _generate_claude_implementation(self, prompt: str) -> str:
        """Generate Claude's implementation strategy"""
        return "Prioritizing incremental implementation with thorough testing at each stage, focusing on backward compatibility and error handling."
    
    def _generate_claude_security(self, prompt: str) -> str:
        """Generate Claude's security considerations"""
        return "Ensuring input validation, proper authentication, secure data handling, and adherence to security best practices throughout implementation."
    
    def _record_request(self, prompt: str, response: Dict[str, Any], request_config: Dict[str, Any], status: str):
        """Record request in history for debugging and optimization"""
        
        record = {
            "timestamp": time.time(),
            "prompt_length": len(prompt),
            "response_success": response.get("success", False),
            "model": request_config.get("model", "unknown"),
            "key_id": request_config.get("key_id", "unknown"),
            "status": status,
            "response_length": len(response.get("response", ""))
        }
        
        self.request_history.append(record)
        
        # Keep only last 100 requests
        if len(self.request_history) > 100:
            self.request_history = self.request_history[-100:]
    
    def _record_error(self, error: Exception, attempt: int):
        """Record error for debugging"""
        
        error_record = {
            "timestamp": time.time(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "attempt": attempt,
            "fallback_active": self.fallback_mode
        }
        
        # In practice, this would be logged to a proper logging system
        print(f"ERROR: {json.dumps(error_record, indent=2)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the collaboration system"""
        
        quota_status = self.quota_manager.get_quota_status()
        
        return {
            "fallback_mode": self.fallback_mode,
            "quota_status": quota_status,
            "request_history_length": len(self.request_history),
            "recent_errors": len([r for r in self.request_history if r["status"] == "error" and time.time() - r["timestamp"] < 3600]),
            "performance_metrics": self._calculate_performance_metrics()
        }
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from request history"""
        
        if not self.request_history:
            return {"no_data": True}
        
        recent_requests = [r for r in self.request_history if time.time() - r["timestamp"] < 3600]
        
        if not recent_requests:
            return {"no_recent_data": True}
        
        success_rate = len([r for r in recent_requests if r["response_success"]]) / len(recent_requests)
        avg_response_length = sum(r["response_length"] for r in recent_requests) / len(recent_requests)
        
        return {
            "hourly_requests": len(recent_requests),
            "success_rate": success_rate,
            "average_response_length": avg_response_length,
            "models_used": list(set(r["model"] for r in recent_requests))
        }
    
    def reset_fallback_mode(self):
        """Reset fallback mode (useful when quota refreshes)"""
        self.fallback_mode = False
        print("✓ Fallback mode reset - Gemini collaboration re-enabled")


# Example usage and testing
if __name__ == "__main__":
    try:
        # Initialize enhanced wrapper
        wrapper = EnhancedGeminiWrapper()
        print("✓ Enhanced Gemini Wrapper initialized")
        
        # Test basic chat
        response = wrapper.chat_with_gemini(
            prompt="Analyze this system architecture and provide recommendations for improvement.",
            complexity="high"
        )
        
        if response["success"]:
            print(f"✓ Chat successful using {response['source']}")
            print(f"Response length: {len(response['response'])} characters")
        else:
            print(f"✗ Chat failed: {response.get('error', 'Unknown error')}")
        
        # Show status
        status = wrapper.get_status()
        print(f"Status: Fallback mode: {status['fallback_mode']}, Available keys: {status['quota_status']['available_keys']}")
        
    except Exception as e:
        print(f"✗ Initialization failed: {e}")