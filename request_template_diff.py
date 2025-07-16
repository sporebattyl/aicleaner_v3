#!/usr/bin/env python3
"""
Request Template Enhancement Diff from Gemini - Step by Step Approach
"""

import asyncio
from zen_mcp import zen_collaborate

async def request_template_enhancement_diff():
    """Request the enhanced template diff from Gemini"""
    
    print("=== REQUESTING TEMPLATE ENHANCEMENT DIFF FROM GEMINI ===")
    
    template_diff_request = """
TEMPLATE ENHANCEMENT DIFF REQUEST - STEP 1

Gemini, let's start with the core template enhancement. Based on our consensus to go from 95/100 to 98/100 readiness, please provide a detailed diff for the enhanced template.

**CURRENT TEMPLATE:** `ENHANCED_CONSENSUS_TEMPLATE_90PLUS.md`

**CONSENSUS ENHANCEMENTS NEEDED:**
1. **Dependency & Data Contracts** section
2. **Success Metrics & Performance Baselines** section  
3. **Continuous Security Considerations** section (not just in audit phase)
4. **Developer Experience & Maintainability** focus

**DIFF REQUEST:**
Please provide a detailed diff showing exactly what to add/modify in the current template:

```diff
--- ENHANCED_CONSENSUS_TEMPLATE_90PLUS.md (current)
+++ ENHANCED_CONSENSUS_TEMPLATE_98PLUS.md (proposed)
```

**REQUIREMENTS:**
- Show exact line additions/modifications
- Maintain all existing 95/100 features
- Add the 4 consensus enhancements above
- Keep the template practical and implementable
- Preserve developer empowerment balance

**FORMAT:**
Please provide the diff in standard diff format with clear sections showing:
- What content to add
- Where to add it in the template structure
- Any modifications to existing sections

Focus only on the template enhancement - we'll handle individual prompt applications separately.
"""
    
    result = await zen_collaborate(template_diff_request)
    
    if result.get("success"):
        print(f"[SUCCESS] Template diff received from {result['model_used']} on {result['api_key_used']}")
        return result["response"]
    else:
        print(f"[ERROR] Template diff request failed: {result.get('error')}")
        return None

async def main():
    """Main execution"""
    print("Requesting template enhancement diff from Gemini...")
    
    template_diff = await request_template_enhancement_diff()
    
    if template_diff:
        print("\n" + "="*80)
        print("GEMINI'S TEMPLATE ENHANCEMENT DIFF")
        print("="*80)
        
        # Clean output for display
        clean_diff = ''.join(char if ord(char) < 128 else '?' for char in template_diff)
        print(clean_diff)
        print("="*80)
        
        print("\n[SUCCESS] Template diff received!")
        print("Please review the proposed changes and let me know if you'd like to:")
        print("1. Implement this template enhancement")
        print("2. Request modifications to the diff")
        print("3. Proceed to Phase 0 prompt creation")
        print("4. Get sample prompt enhancement diff")
        
    else:
        print("[ERROR] Failed to get template diff from Gemini")

if __name__ == "__main__":
    asyncio.run(main())