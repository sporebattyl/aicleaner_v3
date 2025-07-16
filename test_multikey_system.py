#!/usr/bin/env python3
"""
Test Multi-API Key System with Enhanced Zen MCP Client
"""

import asyncio
from zen_gemini_client import ZenGeminiClient

async def test_multikey_system():
    """Test the multi-API key fallback system"""
    
    # Initialize with multiple API keys
    api_keys = [
        "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo",  # Key 1
        "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro",  # Key 2 
        "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc"   # Key 3
    ]
    
    client = ZenGeminiClient(api_keys=api_keys)
    
    print("=== MULTI-API KEY SYSTEM TEST ===")
    print(f"Total API keys: {len(api_keys)}")
    
    # Check initial quota status across all keys
    print("\n=== INITIAL QUOTA STATUS ===")
    status = client.get_quota_status()
    print(f"Recommended: {status['recommended_model']} on {status['recommended_api_key']}")
    print(f"Total API keys managed: {status['total_api_keys']}")
    
    for key_name, models in status['quota_status'].items():
        print(f"\n{key_name}:")
        for model_name, info in models.items():
            print(f"  {model_name}: {info['daily_used']}/{info['daily_limit']} used (can use: {info['can_use_now']})")
    
    # Test collaborative analysis
    print(f"\n=== TESTING MULTI-KEY COLLABORATION ===")
    
    multikey_test_prompt = """
MULTI-API KEY COLLABORATION TEST

Gemini, this is a test of our enhanced multi-API key zen MCP system with these capabilities:

**SYSTEM FEATURES:**
- 3 API keys with identical quotas (100/250/1000 daily requests)
- Model priority: 2.5 Pro → 2.5 Flash → 2.5 Flash-Lite Preview
- Key cycling: Try all keys for Pro before falling back to Flash
- Thinking mode: Dynamic/12288/2048 tokens respectively
- Intelligent fallback: Maximizes available quota across all keys

**WORKFLOW:**
1. Start with 2.5 Pro on API Key 1
2. If Key 1 exhausted, try 2.5 Pro on Key 2, then Key 3
3. Once all Pro quota exhausted, move to 2.5 Flash on Key 1
4. Continue cycling through keys and models as needed

**TEST OBJECTIVES:**
Please confirm:
1. Which API key and model are responding to this request
2. Assessment of this multi-key quota management approach
3. Recommendations for optimizing collaborative workflow
4. Validation that this maximizes our 300 Pro + 750 Flash + 3000 Flash-Lite total capacity

This tests our enhanced quota utilization for high-volume AICleaner v3 prompt development.
"""
    
    result = await client.collaborate_with_gemini(multikey_test_prompt)
    
    if result.get("success"):
        print(f"SUCCESS!")
        print(f"Model used: {result['model_used']}")
        print(f"API key used: {result['api_key_used']}")
        print(f"Quota after request: {result['quota_status']['daily_used']}/{result['quota_status']['daily_limit']}")
        
        # Display thinking information
        thinking = result.get("thinking", {})
        if thinking.get("thinking_available"):
            print(f"Thinking mode: Active (budget: {thinking['thinking_budget_used']})")
        else:
            print(f"Thinking mode: {thinking}")
        
        print(f"\n=== GEMINI'S MULTI-KEY ANALYSIS ===")
        print("=" * 80)
        # Handle encoding for display
        response_text = result["response"]
        clean_text = ''.join(char if ord(char) < 128 else '?' for char in response_text)
        print(clean_text)
        print("=" * 80)
        
    else:
        print(f"FAILED: {result.get('error')}")
        if 'quota_status' in result:
            print("\nQuota status across all keys:")
            for key_name, models in result['quota_status'].items():
                print(f"  {key_name}:")
                for model_name, info in models.items():
                    print(f"    {model_name}: {info['daily_used']}/{info['daily_limit']} (can use: {info['can_use']})")
    
    # Final quota check
    print(f"\n=== FINAL QUOTA STATUS ===")
    final_status = client.get_quota_status()
    print(f"Next recommended: {final_status['recommended_model']} on {final_status['recommended_api_key']}")
    
    # Show usage summary
    total_usage = {"pro": 0, "flash": 0, "lite": 0}
    for key_name, models in final_status['quota_status'].items():
        for model_name, info in models.items():
            if "pro" in model_name:
                total_usage["pro"] += info['daily_used']
            elif "flash" in model_name and "lite" not in model_name:
                total_usage["flash"] += info['daily_used']
            elif "lite" in model_name:
                total_usage["lite"] += info['daily_used']
    
    print(f"\nTotal usage across all keys:")
    print(f"  Pro: {total_usage['pro']}/300 total capacity")
    print(f"  Flash: {total_usage['flash']}/750 total capacity") 
    print(f"  Flash-Lite: {total_usage['lite']}/3000 total capacity")

if __name__ == "__main__":
    asyncio.run(test_multikey_system())