#!/usr/bin/env python3
"""
Claude's Analysis of Gemini's Recommendations
Critical evaluation before implementation
"""

import asyncio
from zen_gemini_client import ZenGeminiClient
import os

async def claude_analysis_of_gemini_recommendations():
    """Claude's critical analysis of Gemini's recommendations"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not found"}
    
    client = ZenGeminiClient(api_key)
    
    claude_analysis = """
CLAUDE'S CRITICAL ANALYSIS OF GEMINI'S RECOMMENDATIONS

After reviewing your recommendations, I have some concerns and disagreements that we should discuss:

**AREAS WHERE I AGREE (✅):**

1. **Test Type Specification**: Yes, specifying unit/integration/system test types is valuable
2. **AAA Code Examples**: Concrete examples would indeed help implementation
3. **Review Checklists**: Structured checklists would improve consistency
4. **HA Compliance Pitfalls**: Proactive addressing of common issues makes sense

**AREAS WHERE I DISAGREE OR HAVE CONCERNS (⚠️):**

1. **Over-Specification Risk**: Your recommendation to add detailed code examples in prompts might lead to:
   - Micromanagement rather than empowering developer creativity
   - Prompts becoming too rigid and prescriptive
   - Loss of flexibility for different implementation approaches
   
   **My Concern**: We risk turning implementation guidance into step-by-step tutorials, which could stifle innovative solutions.

2. **MCP Server Justification**: While explaining WHY to use servers is good, your examples seem verbose:
   - "Use WebFetch to retrieve the latest HA addon config schema because this schema is subject to change..."
   - This level of explanation might clutter the prompts without adding real value
   
   **My Concern**: We might be over-explaining obvious choices and making prompts unnecessarily long.

3. **Zen Collaboration Specificity**: Your suggestion for specific zen prompts like:
   - "Gemini, using zen, analyze the proposed AI provider switching logic..."
   - This feels like pre-scripting conversations rather than allowing natural collaboration
   
   **My Concern**: Over-scripted collaboration might reduce the organic, creative problem-solving we want.

4. **Risk Management Detail Level**: You want very specific rollback procedures:
   - "1. Run git revert <commit-hash> 2. Run git push origin..."
   - This level of Git tutorial detail might not belong in implementation prompts
   
   **My Concern**: We might be confusing implementation guidance with basic tool training.

**QUESTIONS FOR COLLABORATIVE DISCUSSION:**

1. **Balance Question**: How do we provide helpful guidance without becoming overly prescriptive?

2. **Target Audience**: Are we designing these prompts for senior developers who need strategic guidance, or junior developers who need step-by-step tutorials?

3. **Prompt Length**: At what point do detailed examples and explanations make prompts too long and unwieldy?

4. **Flexibility vs Structure**: How do we maintain implementation flexibility while providing sufficient structure?

**MY COUNTER-PROPOSALS:**

1. **Selective Examples**: Add examples only where truly needed (complex schemas, not basic Git commands)
2. **Concise Justification**: Brief MCP server rationale without verbose explanations  
3. **Natural Collaboration**: Keep zen prompts open-ended to encourage creative problem-solving
4. **Reference Links**: Point to external resources for basic tool usage rather than embedding tutorials

**COLLABORATIVE REQUEST:**

Before I implement your recommendations, let's discuss these concerns and reach consensus on:
- Which recommendations to implement as-is
- Which need modification to balance detail with flexibility
- Which might be better addressed through external references

What are your thoughts on my concerns? How can we refine your recommendations to achieve the right balance?
"""

    result = await client.collaborate_with_gemini(claude_analysis)
    return result

if __name__ == "__main__":
    print("=== CLAUDE'S ANALYSIS & COLLABORATIVE DISCUSSION ===")
    result = asyncio.run(claude_analysis_of_gemini_recommendations())
    
    if result.get("success"):
        print("\nGEMINI'S RESPONSE TO CLAUDE'S CONCERNS:")
        print("=" * 80)
        print(result["response"].encode('utf-8', errors='replace').decode('utf-8'))
        print("=" * 80)
    else:
        print(f"\nCOLLABORATION ERROR: {result.get('error')}")