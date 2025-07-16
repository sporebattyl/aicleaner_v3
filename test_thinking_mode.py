#!/usr/bin/env python3
"""
Test Thinking Mode Integration for Enhanced Zen MCP Client
"""

import asyncio
from zen_gemini_client import ZenGeminiClient

async def test_thinking_mode():
    """Test thinking mode across different models"""
    
    api_key = "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo"
    client = ZenGeminiClient(api_key)
    
    print("=== TESTING THINKING MODE INTEGRATION ===")
    
    # Complex collaborative review prompt that benefits from thinking
    thinking_test_prompt = """
COMPLEX COLLABORATIVE ANALYSIS - THINKING MODE TEST

Gemini, please analyze this complex AICleaner v3 implementation scenario using your thinking capabilities:

SCENARIO: 
We need to design a configuration consolidation system that:
1. Merges 3 separate config files with potential conflicts
2. Provides backward compatibility with existing user configs  
3. Implements TDD with AAA pattern for all validation logic
4. Ensures Home Assistant addon certification compliance
5. Handles rollback scenarios for failed migrations

COMPLEX ANALYSIS REQUIRED:
1. **Architecture Decision**: Should we use a single unified schema or maintain separate schemas with a coordination layer?
2. **Risk Assessment**: What are the highest-risk failure scenarios and how do we mitigate them?
3. **Testing Strategy**: How do we structure AAA tests for migration logic that involves file system operations?
4. **HA Compliance**: Which specific HA addon requirements are most likely to be missed during configuration consolidation?
5. **Component Design**: How do we design interfaces that are stable across config schema evolution?

Please use your thinking capabilities to:
- Reason through the architectural trade-offs systematically
- Identify potential edge cases and failure modes
- Provide a comprehensive, well-reasoned recommendation

This is a test of collaborative thinking for complex technical decision-making.
"""
    
    result = await client.collaborate_with_gemini(thinking_test_prompt)
    
    if result.get("success"):
        print(f"SUCCESS! Model used: {result['model_used']}")
        print(f"Quota status: {result['quota_status']['daily_used']}/{result['quota_status']['daily_limit']}")
        
        # Display thinking information
        thinking = result.get("thinking", {})
        if thinking.get("thinking_available"):
            print(f"\n=== THINKING MODE ACTIVE ===")
            print(f"Thinking budget: {thinking['thinking_budget_used']}")
            if thinking.get("thinking_summary"):
                print(f"Thinking summary: {thinking['thinking_summary'][:200]}...")
        else:
            print(f"\n=== THINKING MODE: {thinking} ===")
        
        print(f"\n=== GEMINI'S ANALYSIS (with thinking) ===")
        print("=" * 80)
        # Handle encoding for display
        response_text = result["response"]
        clean_text = ''.join(char if ord(char) < 128 else '?' for char in response_text)
        print(clean_text)
        print("=" * 80)
        
    else:
        print(f"FAILED: {result.get('error')}")
        if 'quota_status' in result:
            print("Quota status:")
            for model_name, info in result['quota_status'].items():
                print(f"  {model_name}: {info}")

if __name__ == "__main__":
    asyncio.run(test_thinking_mode())