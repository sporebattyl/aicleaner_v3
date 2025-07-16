#!/usr/bin/env python3
"""
Request Gemini Review of 6-Section Implementation
"""

import asyncio
from zen_mcp import zen_collaborate

async def review_6section_implementation():
    """Have Gemini review the 6-section implementation and reach consensus"""
    
    print("=== GEMINI REVIEW OF 6-SECTION IMPLEMENTATION ===")
    
    # Read the 6-section implementation
    with open("X:/aicleaner_v3/phase1b_6section_implementation.md", "r", encoding="utf-8") as f:
        implementation_content = f.read()
    
    review_request = f"""
GEMINI REVIEW - 6-SECTION IMPLEMENTATION CONSENSUS

Gemini, I've implemented the 6-section pattern for Phase 1B based on our consensus. Please review this implementation and let me know if you agree or if we need to iterate.

MY 6-SECTION IMPLEMENTATION:
{implementation_content}

CONSENSUS QUESTIONS:
1. Does this implementation correctly apply the 6-section pattern we agreed on?
2. Is the content specific and actionable for Phase 1B configuration migration?
3. Are all sections comprehensive and production-ready?
4. Does this achieve the 100/100 readiness standard we established?
5. Should we apply this exact pattern to all remaining 13 prompts?

REVIEW CRITERIA:
- Technical accuracy for configuration migration scenarios
- Completeness of each of the 6 sections
- Actionability and specificity of guidance
- Home Assistant addon compliance
- Production readiness standards

Please provide your detailed review and consensus recommendation. If you agree, we'll proceed to apply this pattern to all remaining prompts. If not, let's collaborate to refine it until we reach consensus.
"""
    
    result = await zen_collaborate(review_request)
    
    if result.get("success"):
        print(f"[SUCCESS] 6-section implementation review completed")
        return result["response"]
    else:
        print(f"[ERROR] 6-section review failed: {result.get('error')}")
        return None

async def main():
    """Main execution"""
    review_result = await review_6section_implementation()
    
    if review_result:
        print("\n" + "="*80)
        print("GEMINI'S 6-SECTION IMPLEMENTATION REVIEW")
        print("="*80)
        
        clean_review = ''.join(char if ord(char) < 128 else '?' for char in review_result)
        print(clean_review)
        print("="*80)
        
        print(f"\n[SUCCESS] 6-section implementation review completed - ready for consensus decision")
        
    else:
        print("[ERROR] Failed to get 6-section implementation review")

if __name__ == "__main__":
    asyncio.run(main())