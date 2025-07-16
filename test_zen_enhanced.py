#!/usr/bin/env python3
"""
Test Enhanced Zen MCP Client with Model Fallback
"""

import asyncio
import os
from zen_gemini_client import ZenGeminiClient

async def test_enhanced_zen():
    """Test the enhanced zen client with quota management"""
    
    # Set API key directly for testing
    api_key = "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo"
    
    client = ZenGeminiClient(api_key)
    
    # Check quota status first
    print("=== CURRENT QUOTA STATUS ===")
    status = client.get_quota_status()
    print(f"Recommended model: {status['recommended_model']}")
    print("\nModel availability:")
    for model_name, info in status['quota_status'].items():
        print(f"  {model_name}:")
        print(f"    Daily: {info['daily_used']}/{info['daily_limit']} (remaining: {info['daily_remaining']})")
        print(f"    RPM limit: {info['rpm_limit']}")
        print(f"    Can use now: {info['can_use_now']}")
        print(f"    Time since last: {info['time_since_last_request']}")
        print()
    
    # Test collaboration
    print("=== TESTING COLLABORATION WITH FALLBACK ===")
    test_prompt = """
TEST COLLABORATION REQUEST:

Please confirm you can collaborate with Claude on reviewing the AICleaner v3 implementation prompts using the enhanced zen MCP client.

The enhanced client now features:
- Priority model selection: 2.5 Pro → 2.5 Flash → 2.5 Flash-Lite Preview
- Quota tracking: 100, 250, 1000 daily requests respectively  
- Rate limit respect: 5, 10, 15 RPM respectively
- Automatic fallback when limits reached

Respond with:
1. Confirmation of which model is responding
2. Your readiness to review prompts for 90+ implementation quality
3. Assessment of our collaborative framework

This tests our enhanced quota-aware collaboration system.
"""
    
    result = await client.collaborate_with_gemini(test_prompt)
    
    if result.get("success"):
        print(f"SUCCESS! Model used: {result.get('model_used', 'unknown')}")
        print(f"Quota after request: {result['quota_status']['daily_used']}/{result['quota_status']['daily_limit']}")
        print("\nGEMINI'S RESPONSE:")
        print("=" * 80)
        print(result["response"])
        print("=" * 80)
    else:
        print(f"FAILED: {result.get('error')}")
        if 'quota_status' in result:
            print("\nQuota status:")
            for model_name, info in result['quota_status'].items():
                print(f"  {model_name}: {info['daily_used']}/{info['daily_limit']} (can use: {info['can_use']})")
    
    # Final quota check
    print("\n=== FINAL QUOTA STATUS ===")
    final_status = client.get_quota_status()
    print(f"Recommended model after test: {final_status['recommended_model']}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_zen())