#!/usr/bin/env python3
"""
Request Comprehensive Prompt Diffs from Gemini
Then have Claude review the proposed changes
"""

import asyncio
from zen_mcp import zen_collaborate

async def request_comprehensive_diffs():
    """Ask Gemini to create detailed diffs for all prompts"""
    
    print("=== REQUESTING COMPREHENSIVE PROMPT DIFFS FROM GEMINI ===")
    
    diff_request_prompt = """
COMPREHENSIVE PROMPT DIFF GENERATION REQUEST

Gemini, based on our consensus to enhance the AICleaner v3 prompts from 95/100 to 98/100 readiness, please create detailed diffs for all necessary changes.

**CONSENSUS REFINEMENTS TO IMPLEMENT:**

1. **Enhanced Template v3.1** with:
   - Dependency & Data Contracts section
   - Success Metrics & Performance Baselines section  
   - Continuous Security Considerations section
   - Developer Experience & Maintainability focus

2. **Security Integration** throughout (not just in audit phase)

3. **Phase 0: Architecture & Dependency Map** (new prompt)

**DIFF GENERATION REQUEST:**

Please provide comprehensive diffs in the following format:

**TEMPLATE ENHANCEMENT DIFF:**
```diff
--- ENHANCED_CONSENSUS_TEMPLATE_90PLUS.md (current)
+++ ENHANCED_CONSENSUS_TEMPLATE_98PLUS.md (proposed)
@@ -XX,X +XX,X @@
- [current content]
+ [enhanced content with new sections]
```

**SAMPLE PROMPT ENHANCEMENT DIFF:**
Show detailed diff for Phase 1A as an example of how to apply the template:
```diff
--- PHASE_1A_CONFIGURATION_CONSOLIDATION_ENHANCED.md (current)  
+++ PHASE_1A_CONFIGURATION_CONSOLIDATION_ENHANCED_V31.md (proposed)
@@ -XX,X +XX,X @@
- [current sections]
+ [enhanced sections with dependency contracts, metrics, security]
```

**NEW PHASE 0 PROMPT:**
Complete content for the new Phase 0: Architecture & Dependency Map prompt.

**SYSTEMATIC APPLICATION GUIDE:**
Brief instructions for applying these changes to all 15 prompts systematically.

**SPECIFIC REQUIREMENTS:**
- Show exact additions/modifications needed
- Maintain all existing 95/100 features while adding 98/100 enhancements
- Ensure changes are implementable and maintainable
- Focus on practical, actionable improvements
- Keep developer empowerment vs specification balance

Please provide the complete diff package that Claude can review and implement to achieve our 98/100 consensus target.
"""
    
    print("Requesting comprehensive diffs from Gemini...")
    result = await zen_collaborate(diff_request_prompt)
    
    if result.get("success"):
        print(f"[SUCCESS] Diff request completed using {result['model_used']} on {result['api_key_used']}")
        return result["response"]
    else:
        print(f"[ERROR] Diff request failed: {result.get('error')}")
        return None

async def send_diffs_to_claude_for_review(gemini_diffs):
    """Have Claude review Gemini's proposed diffs"""
    
    print("\n=== CLAUDE REVIEW OF GEMINI'S PROPOSED DIFFS ===")
    
    claude_review_prompt = f"""
CLAUDE REVIEW OF GEMINI'S COMPREHENSIVE PROMPT DIFFS

Gemini has provided comprehensive diffs to enhance our AICleaner v3 prompts from 95/100 to 98/100 readiness. Please review these proposed changes.

**GEMINI'S DIFF PACKAGE:**
{gemini_diffs}

**CLAUDE REVIEW OBJECTIVES:**
1. **Technical Accuracy**: Are the proposed changes technically sound and implementable?
2. **Consensus Alignment**: Do the diffs accurately reflect our agreed 98/100 enhancements?
3. **Implementation Feasibility**: Can these changes be systematically applied to all prompts?
4. **Quality Preservation**: Do the changes maintain existing 95/100 strengths while adding value?
5. **Developer Experience**: Will these changes improve or complicate the developer workflow?

**SPECIFIC REVIEW POINTS:**
- Template v3.1 enhancements: Are the new sections well-designed and practical?
- Security integration: Is the continuous security approach effective?
- Phase 0 prompt: Does it provide the architectural foundation needed?
- Diff quality: Are the changes clear, complete, and ready for implementation?
- Systematic application: Is the guidance sufficient for enhancing all 15 prompts?

**CLAUDE FEEDBACK REQUIRED:**
1. **Overall Assessment**: Do you agree with Gemini's proposed changes?
2. **Specific Concerns**: Any technical issues or improvement suggestions?
3. **Implementation Readiness**: Are the diffs ready for systematic application?
4. **Consensus Confirmation**: Do these changes achieve our 98/100 target?
5. **Next Steps**: What's the optimal approach for implementing these enhancements?

Please provide your detailed review and recommendations for proceeding with these prompt enhancements.
"""
    
    print("Having Claude review Gemini's proposed diffs...")
    result = await zen_collaborate(claude_review_prompt)
    
    if result.get("success"):
        print(f"[SUCCESS] Claude review completed using {result['model_used']} on {result['api_key_used']}")
        return result["response"]
    else:
        print(f"[ERROR] Claude review failed: {result.get('error')}")
        return None

async def collaborative_diff_review():
    """Execute the complete collaborative diff review process"""
    
    print("=== COLLABORATIVE PROMPT DIFF REVIEW PROCESS ===")
    print("Step 1: Request comprehensive diffs from Gemini")
    print("Step 2: Have Claude review the proposed changes")
    print("Step 3: Reach consensus on implementation approach\n")
    
    # Step 1: Get diffs from Gemini
    gemini_diffs = await request_comprehensive_diffs()
    
    if not gemini_diffs:
        print("[ERROR] Failed to get diffs from Gemini")
        return None
    
    print("\n" + "="*80)
    print("GEMINI'S COMPREHENSIVE PROMPT DIFFS")
    print("="*80)
    # Display clean text
    clean_diffs = ''.join(char if ord(char) < 128 else '?' for char in gemini_diffs)
    print(clean_diffs)
    print("="*80)
    
    # Step 2: Have Claude review the diffs
    claude_review = await send_diffs_to_claude_for_review(gemini_diffs)
    
    if claude_review:
        print("\n" + "="*80)
        print("CLAUDE'S REVIEW OF GEMINI'S DIFFS")
        print("="*80)
        clean_review = ''.join(char if ord(char) < 128 else '?' for char in claude_review)
        print(clean_review)
        print("="*80)
        
        return {
            "gemini_diffs": gemini_diffs,
            "claude_review": claude_review
        }
    else:
        print("[ERROR] Claude review failed")
        return None

if __name__ == "__main__":
    print("Starting collaborative diff review process...")
    result = asyncio.run(collaborative_diff_review())
    
    if result:
        print("\n[SUCCESS] COLLABORATIVE DIFF REVIEW COMPLETED!")
        print("Ready to implement the consensus enhancements.")
    else:
        print("\n[ERROR] COLLABORATIVE DIFF REVIEW FAILED")
        print("Please check the process and retry.")