#!/usr/bin/env python3
"""
Simple Zen MCP Client for Gemini Collaboration
Enables direct collaboration with Gemini for AICleaner v3 prompt review
"""

import asyncio
import json
import os
import time
from typing import Dict, Any, List
import aiohttp

class ZenGeminiClient:
    def __init__(self, api_keys: list = None, primary_api_key: str = None):
        # Support both single key (backward compatibility) and multiple keys
        if api_keys:
            self.api_keys = api_keys
        elif primary_api_key:
            self.api_keys = [primary_api_key]
        else:
            # Default keys if none provided
            self.api_keys = [
                "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo",
                "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro", 
                "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc"
            ]
        
        # Model priority list with quota tracking per API key
        self.model_templates = [
            {
                "name": "gemini-2.5-pro",
                "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent",
                "daily_limit": 100,
                "rpm_limit": 5,
                "tpm_limit": 250000
            },
            {
                "name": "gemini-2.5-flash",
                "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                "daily_limit": 250,
                "rpm_limit": 10,
                "tpm_limit": 250000
            },
            {
                "name": "gemini-2.5-flash-lite-preview-06-17",
                "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite-preview-06-17:generateContent",
                "daily_limit": 1000,
                "rpm_limit": 15,
                "tpm_limit": 250000
            }
        ]
        
        # Create model instances for each API key
        self.models = {}
        for key_idx, api_key in enumerate(self.api_keys):
            self.models[api_key] = []
            for template in self.model_templates:
                model_instance = {
                    **template,
                    "api_key": api_key,
                    "api_key_index": key_idx,
                    "request_count": 0,
                    "last_request_time": 0,
                    "daily_reset_time": time.time()
                }
                self.models[api_key].append(model_instance)
    
    def _reset_daily_counters_if_needed(self):
        """Reset daily counters if 24 hours have passed"""
        current_time = time.time()
        for api_key in self.models:
            for model in self.models[api_key]:
                if current_time - model["daily_reset_time"] >= 86400:  # 24 hours
                    model["request_count"] = 0
                    model["daily_reset_time"] = current_time
    
    def _can_use_model(self, model: Dict[str, Any]) -> bool:
        """Check if we can use this model based on rate limits and quotas"""
        current_time = time.time()
        
        # Check daily limit
        if model["request_count"] >= model["daily_limit"]:
            return False
        
        # Check rate limit (RPM)
        time_since_last = current_time - model["last_request_time"]
        min_interval = 60 / model["rpm_limit"]  # seconds between requests
        if time_since_last < min_interval:
            return False
        
        return True
    
    def _select_best_available_model(self) -> Dict[str, Any]:
        """Select the best available model based on priority and limits"""
        self._reset_daily_counters_if_needed()
        
        # Try models by priority (Pro -> Flash -> Flash-Lite), cycling through API keys
        for model_idx in range(len(self.model_templates)):
            for api_key in self.api_keys:
                model = self.models[api_key][model_idx]
                if self._can_use_model(model):
                    return model
        
        # If no models available, return the last one (Flash-Lite with first API key)
        return self.models[self.api_keys[0]][-1]
    
    def _update_model_usage(self, model: Dict[str, Any]):
        """Update usage counters for the model"""
        model["request_count"] += 1
        model["last_request_time"] = time.time()
        
    async def collaborate_with_gemini(self, prompt: str, context_files: List[str] = None) -> Dict[str, Any]:
        """Collaborate with Gemini on prompt review and analysis with fallback models"""
        
        # Prepare the collaboration prompt
        collaboration_prompt = f"""
You are Gemini, collaborating with Claude through a zen MCP connection to review AICleaner v3 implementation prompts.

COLLABORATION CONTEXT:
Claude has created 15 comprehensive implementation prompts for the AICleaner v3 Home Assistant addon improvement project. These prompts include TDD principles, AAA testing, component-based design, MCP server integration, GitHub rollback procedures, and iterative collaborative review processes.

YOUR ROLE:
Provide expert review and collaborative analysis to help Claude refine these prompts to perfection.

PROMPT REVIEW REQUEST:
{prompt}

DETAILED ANALYSIS NEEDED:
1. **Implementation Readiness**: Are these prompts actionable and complete for successful implementation?
2. **Quality Integration**: How well are TDD/AAA/Component design principles integrated?
3. **MCP Server Usage**: Is the MCP server integration (WebFetch, zen, GitHub, Task) well-designed?
4. **Collaborative Process**: Will the iterative Claude-Gemini review cycles produce high-quality results?
5. **Risk Management**: Are rollback procedures and GitHub MCP integration sufficient?
6. **HA Compliance**: Do prompts properly address Home Assistant addon standards?
7. **Completeness**: Any gaps or missing elements?
8. **Production Readiness**: Will following these prompts result in a certifiable HA addon?

COLLABORATION OUTPUT FORMAT:
Provide specific, actionable feedback with:
- Strengths identified
- Areas for improvement
- Specific recommendations
- Consensus on readiness level (1-100)
- Final verdict on implementation readiness

Your expertise will help ensure these prompts lead to a production-ready, certifiable Home Assistant addon.
"""

        headers = {
            "Content-Type": "application/json",
        }
        
        # Try models in priority order: Pro->Flash->Flash-Lite, cycling through API keys
        for model_idx in range(len(self.model_templates)):
            for api_key in self.api_keys:
                attempt_model = self.models[api_key][model_idx]
                if not self._can_use_model(attempt_model):
                    continue
                
                # Configure thinking mode based on model capabilities
                generation_config = {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 8192
                }
                
                # Add thinking configuration for Gemini 2.5 models
                if "2.5-pro" in attempt_model["name"]:
                    # Pro: Dynamic thinking, most flexible
                    generation_config["thinkingConfig"] = {
                        "thinkingBudget": -1,  # Dynamic allocation
                        "includeThoughts": True
                    }
                elif "2.5-flash" in attempt_model["name"] and "lite" not in attempt_model["name"]:
                    # Flash: Medium complexity thinking for collaborative review
                    generation_config["thinkingConfig"] = {
                        "thinkingBudget": 12288,  # Half of max for complex analysis
                        "includeThoughts": True
                    }
                elif "flash-lite" in attempt_model["name"]:
                    # Flash-Lite: Minimal thinking for resource efficiency
                    generation_config["thinkingConfig"] = {
                        "thinkingBudget": 2048,  # Conservative for fallback model
                        "includeThoughts": True
                    }
                
                payload = {
                    "contents": [{
                        "parts": [{"text": collaboration_prompt}]
                    }],
                    "generationConfig": generation_config
                }
                    
                try:
                    async with aiohttp.ClientSession() as session:
                        url = f"{attempt_model['url']}?key={attempt_model['api_key']}"
                        async with session.post(url, headers=headers, json=payload) as response:
                            if response.status == 200:
                                data = await response.json()
                                self._update_model_usage(attempt_model)
                                
                                # Extract response and thinking data
                                candidate = data["candidates"][0]
                                response_text = candidate["content"]["parts"][0]["text"]
                                
                                # Extract thinking data if available
                                thinking_data = {}
                                thinking_config = generation_config.get("thinkingConfig", {})
                                if "thoughts" in candidate:
                                    thinking_data = {
                                        "thinking_available": True,
                                        "thinking_summary": candidate["thoughts"].get("thoughtSummary", ""),
                                        "thinking_budget_used": thinking_config.get("thinkingBudget", "none")
                                    }
                                else:
                                    thinking_data = {
                                        "thinking_available": False,
                                        "thinking_budget_configured": thinking_config.get("thinkingBudget", "none")
                                    }
                                
                                return {
                                    "success": True,
                                    "response": response_text,
                                    "collaboration_established": True,
                                    "model_used": attempt_model["name"],
                                    "api_key_used": f"api_key_{attempt_model['api_key_index'] + 1}",
                                    "thinking": thinking_data,
                                    "quota_status": {
                                        "daily_used": attempt_model["request_count"],
                                        "daily_limit": attempt_model["daily_limit"]
                                    }
                                }
                            elif response.status == 429:  # Rate limit
                                error_text = await response.text()
                                print(f"Rate limited on {attempt_model['name']} (API key {attempt_model['api_key_index'] + 1}), trying next...")
                                continue
                            else:
                                error_text = await response.text()
                                print(f"Error with {attempt_model['name']} (API key {attempt_model['api_key_index'] + 1}): {response.status}, trying next...")
                                continue
                except Exception as e:
                    print(f"Connection error with {attempt_model['name']} (API key {attempt_model['api_key_index'] + 1}): {str(e)}, trying next...")
                    continue
        
        # If all models failed, return error
        quota_summary = {}
        for api_key in self.models:
            key_name = f"api_key_{self.api_keys.index(api_key) + 1}"
            quota_summary[key_name] = {}
            for model in self.models[api_key]:
                quota_summary[key_name][model["name"]] = {
                    "daily_used": model["request_count"],
                    "daily_limit": model["daily_limit"],
                    "can_use": self._can_use_model(model)
                }
        
        return {
            "success": False,
            "error": f"All models across {len(self.api_keys)} API keys exhausted or rate limited. Please wait before retrying.",
            "collaboration_established": False,
            "quota_status": quota_summary
        }
    
    def get_quota_status(self) -> Dict[str, Any]:
        """Get current quota status for all models across all API keys"""
        self._reset_daily_counters_if_needed()
        
        quota_status = {}
        for api_key in self.models:
            key_name = f"api_key_{self.api_keys.index(api_key) + 1}"
            quota_status[key_name] = {}
            
            for model in self.models[api_key]:
                model_key = f"{model['name']}"
                quota_status[key_name][model_key] = {
                    "daily_used": model["request_count"],
                    "daily_limit": model["daily_limit"],
                    "daily_remaining": model["daily_limit"] - model["request_count"],
                    "rpm_limit": model["rpm_limit"],
                    "can_use_now": self._can_use_model(model),
                    "time_since_last_request": time.time() - model["last_request_time"] if model["last_request_time"] > 0 else "never"
                }
        
        best_model = self._select_best_available_model()
        return {
            "quota_status": quota_status,
            "recommended_model": best_model["name"],
            "recommended_api_key": f"api_key_{best_model['api_key_index'] + 1}",
            "total_api_keys": len(self.api_keys)
        }

async def test_gemini_collaboration():
    """Test the Gemini collaboration setup"""
    # Use default API keys or environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        client = ZenGeminiClient(primary_api_key=api_key)
    else:
        # Use default multiple API keys
        client = ZenGeminiClient()
    
    test_prompt = """
TEST COLLABORATION REQUEST:

Please confirm you can collaborate with Claude on reviewing the AICleaner v3 implementation prompts. 

The prompts include:
- 15 comprehensive phase implementation guides
- TDD/AAA/Component design principles
- MCP server integration requirements
- GitHub rollback procedures
- Iterative collaborative review processes

Respond with:
1. Confirmation you understand the collaboration context
2. Your assessment approach for prompt review
3. Readiness to provide detailed feedback
4. Any questions about the collaboration process

This is a test to establish our collaboration connection before the full prompt review.
"""
    
    result = await client.collaborate_with_gemini(test_prompt)
    return result

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_gemini_collaboration())
    print("=== ZEN GEMINI COLLABORATION TEST ===")
    print(json.dumps(result, indent=2))