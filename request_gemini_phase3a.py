#!/usr/bin/env python3
"""
Request Gemini to Create Phase 3A via gemini-mcp-tool with diff approach
"""

import asyncio
from zen_mcp import zen_collaborate

async def request_gemini_phase3a_diff():
    """Ask Gemini to create Phase 3A Device Detection Enhancement with diff format"""
    
    print("=== REQUESTING GEMINI TO CREATE PHASE 3A WITH DIFF ===")
    
    # Show Gemini our successful pattern from previous phases
    with open("X:/aicleaner_v3/docs/prompts/PHASE_2B_RESPONSE_QUALITY_100.md", "r", encoding="utf-8") as f:
        phase2b_example = f.read()[:1500]  # Sample for pattern reference
    
    phase3a_request = f"""
GEMINI - PHASE 3A DEVICE DETECTION ENHANCEMENT REQUEST

Gemini, please create Phase 3A: Device Detection Enhancement using our validated 6-section 100/100 pattern. Provide your response as a complete diff that I can review and implement.

VALIDATED PATTERN REFERENCE (Phase 2B excerpt):
{phase2b_example}

PHASE 3A FOCUS: Device Detection Enhancement
- Smart device discovery and identification
- Device capability detection and classification  
- Device state monitoring and tracking
- Device compatibility and integration assessment
- Automated device onboarding and configuration

REQUIRED FORMAT - Complete diff ready for implementation:

```diff
--- /dev/null
+++ X:/aicleaner_v3/docs/prompts/PHASE_3A_DEVICE_DETECTION_100.md
@@ -0,0 +1,XXX @@
+# Phase 3A: Device Detection Enhancement - 6-Section 100/100 Enhancement
+
+## Core Implementation Requirements
+
+### Core Tasks
+1. **Smart Device Discovery System**
+   - **Action**: [Specific device detection and discovery actions]
+   - **Details**: [Detailed device detection requirements]  
+   - **Validation**: [Device detection validation criteria]
+
+[Continue with complete 6-section implementation...]
```

Please provide the complete, detailed Phase 3A prompt following our validated pattern, formatted as a diff ready for implementation. Include all 6 sections with device detection-specific content.
"""
    
    result = await zen_collaborate(phase3a_request)
    
    if result.get("success"):
        print(f"[SUCCESS] Gemini Phase 3A diff received")
        return result["response"]
    else:
        print(f"[ERROR] Gemini Phase 3A request failed: {result.get('error')}")
        return None

async def main():
    """Main execution"""
    gemini_diff = await request_gemini_phase3a_diff()
    
    if gemini_diff:
        print("\n" + "="*80)
        print("GEMINI'S PHASE 3A DIFF")
        print("="*80)
        
        clean_diff = ''.join(char if ord(char) < 128 else '?' for char in gemini_diff)
        print(clean_diff)
        print("="*80)
        
        # Save Gemini's diff
        with open("X:/aicleaner_v3/gemini_phase3a_diff.md", "w", encoding="utf-8") as f:
            f.write(clean_diff)
        
        print(f"\n[SUCCESS] Gemini's Phase 3A diff saved - ready for review and consensus")
        
    else:
        print("[ERROR] Failed to get Gemini's Phase 3A diff")

if __name__ == "__main__":
    asyncio.run(main())