#!/usr/bin/env python3
"""
Have Gemini Review Phase 1A Diff and Reach Consensus
"""

import asyncio
from zen_mcp import zen_collaborate

async def review_phase1a_diff():
    """Have Gemini review the Phase 1A diff for issues and consensus"""
    
    print("=== GEMINI REVIEW OF PHASE 1A DIFF ===")
    
    # Read the diff file
    with open("X:/aicleaner_v3/phase1a_98plus_enhancement.diff", "r", encoding="utf-8") as f:
        diff_content = f.read()
    
    review_request = f"""
PHASE 1A DIFF REVIEW AND CONSENSUS

Gemini, please review this specific diff I created to enhance Phase 1A from 92/100 to 98/100 readiness. I need your expert analysis and consensus.

DIFF TO REVIEW:
{diff_content}

REVIEW OBJECTIVES:
1. **Technical Accuracy**: Are the additions technically sound for configuration consolidation?
2. **Content Quality**: Is the content practical and implementable?
3. **Placement Logic**: Are the new sections in the right locations?
4. **Completeness**: Do these additions achieve 98/100 readiness?
5. **HA Compliance**: Are the additions appropriate for Home Assistant addon development?

SPECIFIC REVIEW POINTS:
- **Dependency & Data Contracts**: Are the dependencies and contracts realistic for config consolidation?
- **Continuous Security**: Are the threat models and practices appropriate?
- **Success Metrics**: Are the KPIs and baselines measurable and achievable?
- **Developer Experience**: Do the maintainability aspects improve the prompt?

CONSENSUS QUESTIONS:
1. Do you agree this diff transforms Phase 1A to 98/100 readiness?
2. Are there any technical issues or improvements needed?
3. Should any content be modified or repositioned?
4. Is this ready for implementation or does it need refinement?

Please provide your detailed review and final consensus recommendation.
"""
    
    result = await zen_collaborate(review_request)
    
    if result.get("success"):
        print(f"[SUCCESS] Gemini review completed using {result['model_used']} on {result['api_key_used']}")
        return result["response"]
    else:
        print(f"[ERROR] Gemini review failed: {result.get('error')}")
        return None

async def main():
    """Main execution"""
    review_result = await review_phase1a_diff()
    
    if review_result:
        print("\n" + "="*80)
        print("GEMINI'S DIFF REVIEW AND CONSENSUS")
        print("="*80)
        
        clean_review = ''.join(char if ord(char) < 128 else '?' for char in review_result)
        print(clean_review)
        print("="*80)
        
        print(f"\n[SUCCESS] Gemini review completed - ready for consensus decision")
        
    else:
        print("[ERROR] Failed to get Gemini review")

if __name__ == "__main__":
    asyncio.run(main())