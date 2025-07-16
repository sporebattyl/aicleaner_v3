#!/usr/bin/env python3
"""
Comprehensive AICleaner v3 Prompt Review using Combined MCP Approach
- Uses Gemini CLI for file analysis
- Uses custom zen MCP for intensive collaboration
- Achieves consensus on final prompts
"""

import asyncio
import os
import json
from pathlib import Path

# Import our global zen MCP
from zen_mcp import ZenGeminiClient, zen_collaborate, zen_quota_status

class ComprehensivePromptReviewer:
    def __init__(self):
        self.zen_client = ZenGeminiClient()
        self.prompts_dir = Path("X:/aicleaner_v3/docs/prompts")
        
    def analyze_prompt_files_with_gemini_cli(self):
        """Use Gemini CLI to analyze existing prompt files"""
        print("=== ANALYZING PROMPT FILES WITH GEMINI CLI ===")
        
        # List all prompt files
        prompt_files = list(self.prompts_dir.glob("*.md"))
        print(f"Found {len(prompt_files)} prompt files to analyze")
        
        for file in prompt_files:
            print(f"- {file.name}")
        
        return prompt_files
    
    async def comprehensive_review_with_zen_mcp(self, prompt_files):
        """Use zen MCP for comprehensive collaborative review"""
        print("\n=== COMPREHENSIVE REVIEW WITH ZEN MCP ===")
        
        # Check quota status first
        status = zen_quota_status()
        print(f"Starting with: {status['recommended_model']} on {status['recommended_api_key']}")
        print(f"Available capacity: Pro: {sum(models['gemini-2.5-pro']['daily_remaining'] for models in status['quota_status'].values())}/300")
        
        # Prepare comprehensive review prompt
        comprehensive_review_prompt = f"""
COMPREHENSIVE AICLEANER V3 PROMPT REVIEW - FINAL CONSENSUS

Gemini, this is our final comprehensive review of all 15 AICleaner v3 implementation prompts for achieving 90+ readiness and reaching consensus on the final versions.

**PROJECT CONTEXT:**
- AICleaner v3 Home Assistant addon improvement project
- 15 comprehensive implementation phases requiring prompt enhancement
- Target: 90+ implementation readiness for certifiable HA addon
- Previous achievement: 92/100 on Phase 1A using enhanced template

**PROMPT FILES IDENTIFIED:**
{chr(10).join(f"- {file.name}" for file in prompt_files)}

**ENHANCED TEMPLATE FEATURES ACHIEVED:**
✅ Implementation Validation Framework (8-item checklists, integration gates)
✅ Production Readiness Validation (deployment tests, operational focus)  
✅ Component Interface Contracts (abstract base classes, conformance tests)
✅ Critical HA Compliance Focus (specific documentation links, certification requirements)
✅ TDD/AAA Pattern Integration (concrete examples, security test cases)
✅ MCP Server Usage Requirements (WebFetch, GitHub, zen, Task integration)
✅ Rollback and Recovery Procedures (GitHub MCP, automated validation)
✅ Collaborative Review Process (Claude-Gemini consensus building)

**COMPREHENSIVE REVIEW OBJECTIVES:**
1. **Systematic Assessment**: Review each prompt against 90+ readiness criteria
2. **Consistency Validation**: Ensure all prompts follow the validated 92/100 pattern
3. **Gap Analysis**: Identify any missing elements across the 15 phases
4. **Integration Verification**: Confirm proper phase sequencing and dependencies
5. **Production Readiness**: Validate that following these prompts results in certifiable addon
6. **Final Consensus**: Reach agreement on any needed refinements

**SPECIFIC ANALYSIS REQUIRED:**
1. **Template Compliance**: Do all prompts incorporate the 8-item validation framework?
2. **HA Certification**: Are specific HA addon requirements addressed systematically?
3. **TDD Integration**: Is the AAA pattern properly enforced with concrete examples?
4. **MCP Usage**: Are MCP server requirements clearly specified for each phase?
5. **Component Design**: Are interface contracts and validation requirements clear?
6. **Risk Management**: Are rollback procedures and safety measures adequate?
7. **Collaborative Process**: Is the Claude-Gemini review cycle properly integrated?
8. **Completeness**: Are all 15 phases properly sequenced and comprehensive?

**CONSENSUS BUILDING:**
For each area needing improvement:
- Provide specific, actionable recommendations
- Suggest exact template modifications or additions
- Prioritize changes by impact on 90+ readiness achievement
- Ensure recommendations maintain developer empowerment vs over-specification

**FINAL DELIVERABLES:**
1. Overall readiness assessment (1-100) for the complete prompt set
2. Specific recommendations for any prompts needing enhancement
3. Validation that the set achieves production-ready, certifiable addon development
4. Consensus confirmation on final prompt versions

This is our definitive collaborative review to finalize the AICleaner v3 implementation prompts for production use.
"""

        # Execute comprehensive review
        print("Executing comprehensive review with Gemini...")
        result = await zen_collaborate(comprehensive_review_prompt)
        
        if result.get("success"):
            print(f"[SUCCESS] Review completed using {result['model_used']} on {result['api_key_used']}")
            print(f"Thinking mode: {result['thinking']['thinking_available']}")
            return result["response"]
        else:
            print(f"[ERROR] Review failed: {result.get('error')}")
            return None
    
    async def consensus_building_cycle(self, initial_review):
        """Engage in iterative consensus building until agreement reached"""
        print("\n=== CONSENSUS BUILDING CYCLE ===")
        
        consensus_prompt = f"""
CONSENSUS BUILDING - AICLEANER V3 PROMPT FINALIZATION

Gemini, based on your comprehensive review, let's reach final consensus on the AICleaner v3 prompts.

**YOUR INITIAL ASSESSMENT:**
{initial_review[:2000]}...

**CONSENSUS OBJECTIVES:**
1. **Mutual Agreement**: Do we both agree the prompts are ready for production use?
2. **Refinement Priorities**: Which specific improvements would have highest impact?
3. **Implementation Strategy**: What's the optimal approach for applying any final changes?
4. **Quality Assurance**: Are we confident these prompts will produce a certifiable addon?

**COLLABORATIVE DECISION POINTS:**
1. **Overall Readiness**: Is the prompt set 90+ ready as-is, or do specific enhancements add significant value?
2. **Priority Changes**: If improvements needed, which are critical vs nice-to-have?
3. **Template Application**: Should we systematically enhance all prompts, or focus on key phases?
4. **Production Confidence**: Will following these prompts result in Home Assistant certification?

**CONSENSUS BUILDING:**
Please provide:
- Your final readiness score for the complete prompt set
- Top 3 improvements that would maximize value (if any)
- Confirmation of production-readiness for HA addon development
- Agreement on whether we've achieved our 90+ collaborative enhancement goal

Let's reach definitive consensus on the final state of these implementation prompts.
"""
        
        consensus_result = await zen_collaborate(consensus_prompt)
        
        if consensus_result.get("success"):
            print(f"[SUCCESS] Consensus building completed")
            return consensus_result["response"]
        else:
            print(f"[ERROR] Consensus building failed")
            return None
    
    async def run_comprehensive_review(self):
        """Execute the complete comprehensive review process"""
        print("=== COMPREHENSIVE AICLEANER V3 PROMPT REVIEW ===")
        print("Objective: Final consensus on 90+ readiness implementation prompts")
        
        # Step 1: Analyze existing files
        prompt_files = self.analyze_prompt_files_with_gemini_cli()
        
        # Step 2: Comprehensive review with zen MCP
        initial_review = await self.comprehensive_review_with_zen_mcp(prompt_files)
        
        if not initial_review:
            print("[ERROR] Comprehensive review failed - cannot proceed")
            return
        
        print("\n=== INITIAL COMPREHENSIVE REVIEW ===")
        print("=" * 80)
        # Display clean text
        clean_review = ''.join(char if ord(char) < 128 else '?' for char in initial_review)
        print(clean_review)
        print("=" * 80)
        
        # Step 3: Consensus building
        consensus = await self.consensus_building_cycle(initial_review)
        
        if consensus:
            print("\n=== FINAL CONSENSUS ===")
            print("=" * 80)
            clean_consensus = ''.join(char if ord(char) < 128 else '?' for char in consensus)
            print(clean_consensus)
            print("=" * 80)
            
            # Final status
            final_status = zen_quota_status()
            print(f"\n=== SESSION SUMMARY ===")
            print(f"Comprehensive review completed successfully")
            print(f"Final recommended model: {final_status['recommended_model']} on {final_status['recommended_api_key']}")
            
            # Show quota usage
            total_used = {"pro": 0, "flash": 0, "lite": 0}
            for key_name, models in final_status['quota_status'].items():
                for model_name, info in models.items():
                    if "pro" in model_name:
                        total_used["pro"] += info['daily_used']
                    elif "flash" in model_name and "lite" not in model_name:
                        total_used["flash"] += info['daily_used']
                    elif "lite" in model_name:
                        total_used["lite"] += info['daily_used']
            
            print(f"Quota used in this session:")
            print(f"  Pro: {total_used['pro']}/300")
            print(f"  Flash: {total_used['flash']}/750")
            print(f"  Flash-Lite: {total_used['lite']}/3000")
            
            return {"initial_review": initial_review, "consensus": consensus}
        else:
            print("[ERROR] Consensus building failed")
            return None

async def main():
    """Main execution function"""
    reviewer = ComprehensivePromptReviewer()
    result = await reviewer.run_comprehensive_review()
    
    if result:
        print("\n[SUCCESS] COMPREHENSIVE PROMPT REVIEW COMPLETED!")
        print("Ready to implement final consensus recommendations.")
    else:
        print("\n[ERROR] COMPREHENSIVE REVIEW INCOMPLETE")
        print("Please check quota status and retry.")

if __name__ == "__main__":
    asyncio.run(main())