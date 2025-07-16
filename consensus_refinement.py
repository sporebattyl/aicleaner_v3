#!/usr/bin/env python3
"""
Claude-Gemini Consensus Building for Final Recommendations
"""

import asyncio
from zen_gemini_client import ZenGeminiClient
import os

async def reach_final_consensus():
    """Continue collaboration to reach final consensus"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    client = ZenGeminiClient(api_key)
    
    claude_consensus_response = """
CLAUDE'S CONSENSUS RESPONSE

Excellent! I'm much more aligned with your revised recommendations. You've addressed my core concerns effectively. Let me respond to your revisions:

**AREAS WHERE WE NOW HAVE CONSENSUS (✅):**

1. **Selective Examples**: Your approach of targeting complex interactions (like async MCP responses) rather than basic code is perfect. This provides value without micromanagement.

2. **Concise MCP Justification**: Your revised format focusing on benefits is ideal. "This ensures latest schema, simplifying updates" is much better than verbose explanations.

3. **Zen as Collaborative Framework**: Framing zen as general collaboration for "complex design decisions, performance analysis" is exactly right. No pre-scripted conversations.

4. **External Resource Links**: Linking to Git documentation instead of embedding tutorials keeps prompts focused on implementation strategy.

**MINOR REFINEMENTS NEEDED:**

1. **Review Checklist Scope**: Your checklist idea is excellent, but let's ensure they're focused on phase-specific outcomes rather than general development practices.

2. **Example Selection Criteria**: Let's be very selective - only include examples for:
   - Complex async patterns (MCP interactions)
   - HA-specific integration patterns
   - Non-obvious test scenarios

3. **Target Audience Clarity**: I agree on "senior developer" focus, but let's add a brief note in the template about skill level expectations.

**FINAL CONSENSUS PROPOSAL:**

Based on our discussion, here's what I propose we implement:

**IMPLEMENT THESE REFINEMENTS:**
1. ✅ Add targeted examples for complex MCP async patterns only
2. ✅ Include concise, benefit-focused MCP server justifications  
3. ✅ Add phase-specific review checklists (5-7 items max)
4. ✅ Frame zen as collaborative problem-solving framework
5. ✅ Link to external resources for basic tooling
6. ✅ Specify test types (unit/integration/system) where helpful
7. ✅ Add brief HA compliance pitfall warnings

**DO NOT IMPLEMENT:**
- ❌ Detailed step-by-step code examples
- ❌ Verbose MCP server explanations
- ❌ Pre-scripted zen conversation prompts
- ❌ Embedded Git/tool tutorials

**VALIDATION APPROACH:**

You suggested a dry-run with one prompt. I propose we:
1. Apply our agreed refinements to **Phase 1A (Configuration Consolidation)** 
2. Review the refined version together
3. If we both approve, apply the same refinement pattern to all 15 prompts

**QUESTIONS FOR FINAL ALIGNMENT:**

1. **Review Checklist Length**: Do you agree on 5-7 items max per phase to keep them actionable?

2. **Example Placement**: Should complex examples go in "Implementation Notes" or "Technical Specifications"?

3. **HA Pitfall Format**: Brief bullet points in "Technical Guidelines" or separate "HA Compliance Notes" section?

4. **Ready to Proceed**: If you agree with this consensus, should we implement the refinements on Phase 1A as our validation test?

Your revised approach perfectly balances guidance with flexibility. I believe these refinements will create prompts that empower senior developers while providing the structure needed for consistent, high-quality implementation.

Are we aligned on this final approach?
"""

    result = await client.collaborate_with_gemini(claude_consensus_response)
    return result

if __name__ == "__main__":
    print("=== CLAUDE-GEMINI CONSENSUS BUILDING ===")
    result = asyncio.run(reach_final_consensus())
    
    if result.get("success"):
        print("\nGEMINI'S FINAL CONSENSUS RESPONSE:")
        print("=" * 80)
        print(result["response"].encode('utf-8', errors='replace').decode('utf-8'))
        print("=" * 80)
    else:
        print(f"\nCOLLABORATION ERROR: {result.get('error')}")