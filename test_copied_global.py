#!/usr/bin/env python3
"""
Test the copied global zen MCP client
"""

import asyncio

# Import from the copied global client
from zen_global import ZenGeminiClient, zen_collaborate, zen_quota_status

async def test_copied_global():
    """Test the copied global zen MCP functionality"""
    
    print("=== TESTING COPIED GLOBAL ZEN MCP ===")
    
    # Test quota status
    print("\n=== QUOTA STATUS ===")
    status = zen_quota_status()
    print(f"Recommended: {status['recommended_model']} on {status['recommended_api_key']}")
    print(f"Total API keys: {status['total_api_keys']}")
    
    # Show capacity summary
    total_remaining = {"pro": 0, "flash": 0, "lite": 0}
    for key_name, models in status['quota_status'].items():
        for model_name, info in models.items():
            if "pro" in model_name:
                total_remaining["pro"] += info['daily_remaining']
            elif "flash" in model_name and "lite" not in model_name:
                total_remaining["flash"] += info['daily_remaining']
            elif "lite" in model_name:
                total_remaining["lite"] += info['daily_remaining']
    
    print(f"Remaining capacity today:")
    print(f"  Pro: {total_remaining['pro']}/300")
    print(f"  Flash: {total_remaining['flash']}/750") 
    print(f"  Flash-Lite: {total_remaining['lite']}/3000")
    
    # Test collaboration
    print(f"\n=== TESTING COLLABORATION ===")
    
    test_prompt = """
GLOBAL ZEN MCP VALIDATION

Gemini, this is a validation test of our globally installed multi-API key zen MCP system.

System Features:
- Permanently installed at /c/Users/dmjtx/.claude/zen_mcp_global/
- 3 API keys with 4,050 total daily capacity
- Intelligent model fallback (Pro → Flash → Flash-Lite)
- Thinking mode optimization per model
- Available across all Claude sessions regardless of directory

Please confirm:
1. Which model and API key are responding
2. Verification that the global installation is working
3. Assessment of this approach for high-volume collaborative work
4. Readiness for complex project analysis (like AICleaner v3)

Keep response concise for this validation test.
"""
    
    result = await zen_collaborate(test_prompt)
    
    if result.get("success"):
        print(f"SUCCESS!")
        print(f"Model: {result['model_used']}")
        print(f"API Key: {result['api_key_used']}")
        print(f"Thinking: {result['thinking']['thinking_available']}")
        print(f"Quota: {result['quota_status']['daily_used']}/{result['quota_status']['daily_limit']}")
        
        print(f"\n=== GEMINI'S VALIDATION RESPONSE ===")
        print("=" * 60)
        clean_text = ''.join(char if ord(char) < 128 else '?' for char in result["response"])
        print(clean_text)
        print("=" * 60)
        
        print(f"\n[SUCCESS] Global zen MCP is working perfectly!")
        print(f"Ready for use in any future Claude session.")
        
    else:
        print(f"[ERROR] Collaboration failed: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_copied_global())