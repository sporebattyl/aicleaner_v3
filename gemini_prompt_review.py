#!/usr/bin/env python3
"""
Comprehensive Gemini Review of AICleaner v3 Implementation Prompts
Facilitates collaborative review between Claude and Gemini
"""

import asyncio
import json
import os
from pathlib import Path
from zen_gemini_client import ZenGeminiClient

async def review_all_prompts():
    """Conduct comprehensive Gemini review of all AICleaner v3 prompts"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not found"}
    
    client = ZenGeminiClient(api_key)
    
    # List of all prompt files to review
    prompt_files = [
        "CONSENSUS_PROMPT_TEMPLATE.md",
        "PHASE_1A_CONFIGURATION_CONSOLIDATION.md",
        "PHASE_1B_REQUIREMENTS_RESOLUTION.md", 
        "PHASE_1C_INFRASTRUCTURE_VALIDATION.md",
        "PHASE_2A_AI_MODEL_OPTIMIZATION.md",
        "PHASE_2B_PERFORMANCE_MONITORING.md",
        "PHASE_2C_PREDICTIVE_ANALYTICS.md",
        "PHASE_2_5_AI_INTEGRATION_TESTING.md",
        "PHASE_3A_TESTING_FRAMEWORK.md",
        "PHASE_3B_CODE_QUALITY.md",
        "PHASE_3C_SECURITY_AUDIT.md",
        "PHASE_4A_HA_INTEGRATION.md",
        "PHASE_4B_PERFORMANCE_OPTIMIZATION.md",
        "PHASE_4C_DOCUMENTATION_DEPLOYMENT.md",
        "CERTIFICATION_COMPLIANCE_CHECKLIST.md"
    ]
    
    # Read all prompt files
    prompts_content = {}
    prompts_dir = Path("X:/aicleaner_v3/docs/prompts")
    
    for filename in prompt_files:
        file_path = prompts_dir / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                prompts_content[filename] = f.read()
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            prompts_content[filename] = f"ERROR: Could not read file - {e}"
    
    # Create comprehensive review prompt for Gemini
    review_prompt = f"""
COMPREHENSIVE AICLEANER V3 IMPLEMENTATION PROMPTS REVIEW

COLLABORATION CONTEXT:
You (Gemini) are collaborating with Claude through zen MCP to conduct the final comprehensive review of all 15 AICleaner v3 implementation prompts. This is the definitive quality assurance step before implementation begins.

PROMPT FILES CONTENT:
{json.dumps(prompts_content, indent=2)}

CRITICAL REVIEW CRITERIA:
Please provide detailed analysis on:

1. **Implementation Readiness (Weight: 25%)**
   - Are prompts actionable and complete for successful implementation?
   - Do they provide sufficient technical guidance without micromanaging?
   - Are success criteria measurable and achievable?

2. **Quality Assurance Integration (Weight: 20%)**
   - How effectively are TDD/AAA/Component design principles integrated?
   - Will the testing strategies ensure code quality?
   - Are quality gates properly defined?

3. **MCP Server Integration (Weight: 15%)**
   - Is WebFetch/WebSearch/zen/GitHub/Task usage well-designed?
   - Will MCP integration enhance implementation success?
   - Are rollback procedures using GitHub MCP sufficient?

4. **Collaborative Review Process (Weight: 15%)**
   - Will the iterative Claude-Gemini review cycles work effectively?
   - Are review criteria comprehensive enough?
   - Is consensus-building process well-defined?

5. **Home Assistant Compliance (Weight: 15%)**
   - Do prompts address current HA addon development standards?
   - Is certification compliance thoroughly covered?
   - Are security and performance requirements met?

6. **Risk Management (Weight: 10%)**
   - Are rollback procedures comprehensive?
   - Are phase dependencies properly managed?
   - Is error handling sufficiently addressed?

ANALYSIS OUTPUT REQUIRED:
For each criterion, provide:
- **Score (1-100)**: Numerical assessment
- **Strengths**: Specific positive elements identified
- **Weaknesses**: Areas needing improvement
- **Recommendations**: Actionable suggestions for enhancement

OVERALL ASSESSMENT:
- **Total Score**: Weighted average of all criteria
- **Implementation Readiness**: Ready/Needs Work/Major Issues
- **Key Improvements**: Top 3-5 critical enhancements needed
- **Final Consensus**: Your definitive verdict on readiness

COLLABORATIVE DECISION:
Based on your expert analysis, should we:
1. **PROCEED** with implementation using current prompts
2. **REFINE** specific prompts based on your recommendations  
3. **MAJOR REVISION** needed before implementation

Provide your comprehensive analysis with specific, actionable feedback for Claude to achieve perfect implementation prompts.
"""

    # Get Gemini's comprehensive review
    result = await client.collaborate_with_gemini(review_prompt)
    return result

if __name__ == "__main__":
    print("=== COMPREHENSIVE GEMINI REVIEW OF AICLEANER V3 PROMPTS ===")
    result = asyncio.run(review_all_prompts())
    
    if result.get("success"):
        print("\nGEMINI COLLABORATIVE REVIEW:")
        print("=" * 80)
        print(result["response"])
        print("=" * 80)
    else:
        print(f"\nCOLLABORATION ERROR: {result.get('error')}")