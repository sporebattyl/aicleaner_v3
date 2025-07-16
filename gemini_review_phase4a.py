#!/usr/bin/env python3
"""
Ask Gemini to Review Phase 4A Implementation via MCP Tool
"""

import asyncio
from zen_mcp import zen_collaborate

async def gemini_review_phase4a():
    """Have Gemini review the Phase 4A implementation and collaborate on improvements"""
    
    print("=== GEMINI REVIEW OF PHASE 4A IMPLEMENTATION ===")
    
    # Read the Phase 4A implementation
    with open("X:/aicleaner_v3/docs/prompts/PHASE_4A_HA_INTEGRATION_100.md", "r", encoding="utf-8") as f:
        phase4a_content = f.read()
    
    review_request = f"""
GEMINI REVIEW - PHASE 4A HOME ASSISTANT INTEGRATION IMPLEMENTATION

Gemini, I've created the Phase 4A: Home Assistant Integration Improvement using our validated 6-section 100/100 pattern. Please review this implementation and collaborate with me on any improvements.

MY PHASE 4A IMPLEMENTATION:
{phase4a_content}

COLLABORATION QUESTIONS:
1. Does this implementation correctly apply our 6-section pattern to HA integration?
2. Is the HA-specific content comprehensive and technically accurate?
3. Are the HA Supervisor integration, service calls, entity management, and config flow properly covered?
4. Does this meet HA addon certification requirements and Quality Scale standards?
5. Any specific improvements or additions needed for HA integration excellence?

REVIEW CRITERIA:
- Technical accuracy for HA integration scenarios
- Completeness of HA-specific requirements (Supervisor API, entity registry, config flow)
- HA certification and Quality Scale compliance
- Developer experience for HA addon development
- Production readiness for HA addon store submission

Please provide your detailed review and specific recommendations for improvements. If you agree it's excellent, we can proceed. If not, let's collaborate to refine it until we reach consensus on the best HA integration approach.
"""
    
    result = await zen_collaborate(review_request)
    
    if result.get("success"):
        print(f"[SUCCESS] Gemini review of Phase 4A completed")
        return result["response"]
    else:
        print(f"[ERROR] Gemini review failed: {result.get('error')}")
        return None

async def main():
    """Main execution"""
    review_result = await gemini_review_phase4a()
    
    if review_result:
        print("\n" + "="*80)
        print("GEMINI'S PHASE 4A REVIEW AND RECOMMENDATIONS")
        print("="*80)
        
        clean_review = ''.join(char if ord(char) < 128 else '?' for char in review_result)
        print(clean_review)
        print("="*80)
        
        # Save Gemini's review
        with open("X:/aicleaner_v3/gemini_phase4a_review.md", "w", encoding="utf-8") as f:
            f.write(clean_review)
        
        print(f"\n[SUCCESS] Gemini's Phase 4A review completed - ready for consensus decision")
        
    else:
        print("[ERROR] Failed to get Gemini's Phase 4A review")

if __name__ == "__main__":
    asyncio.run(main())