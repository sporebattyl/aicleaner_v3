#!/usr/bin/env python3
"""
Request Specific Diff Format for Phase 1A
"""

import asyncio
from zen_mcp import zen_collaborate

async def request_specific_diff_format():
    """Request actual diff format from Gemini"""
    
    print("=== REQUESTING SPECIFIC DIFF FORMAT ===")
    
    specific_diff_request = """
SPECIFIC DIFF FORMAT REQUEST - PHASE 1A

Gemini, I need the actual diff format, not analysis. Please provide the exact diff syntax showing where to add the 4 enhancement sections to Phase 1A.

CURRENT STRUCTURE (Phase 1A has these sections):
1. Context & Objective
2. Implementation Requirements  
3. Implementation Validation Framework
4. Quality Assurance
5. Production Readiness Validation
6. Deliverables
7. Implementation Notes

ENHANCEMENT SECTIONS TO ADD:
- Dependency & Data Contracts (add after Technical Specifications)
- Continuous Security Considerations (add after existing Security Considerations)  
- Success Metrics & Performance Baselines (add after Performance Baseline)
- Developer Experience & Maintainability (add in Quality Assurance section)

FORMAT REQUIRED:
```diff
--- PHASE_1A_CONFIGURATION_CONSOLIDATION_ENHANCED.md
+++ PHASE_1A_CONFIGURATION_CONSOLIDATION_98PLUS.md
@@ -35,6 +35,12 @@
 - **Testing Strategy**: [Unit, integration, and system test requirements with AAA examples]

+### Dependency & Data Contracts
+- **Internal Dependencies**: [Configuration schema validation, backup systems, migration utilities]
+- **External Dependencies**: [Home Assistant core config, YAML parser, JSON schema validator]
+- **Data Contracts (Inputs)**: [Three source config files with defined schemas and validation rules]
+- **Data Contracts (Outputs)**: [Unified config.yaml with consolidated schema and validation]
+
 ### Security Considerations
```

Please provide the complete diff with exact line additions for all 4 enhancement sections.
"""
    
    result = await zen_collaborate(specific_diff_request)
    
    if result.get("success"):
        print(f"[SUCCESS] Specific diff format received")
        return result["response"]
    else:
        print(f"[ERROR] Specific diff request failed: {result.get('error')}")
        return None

async def main():
    """Main execution"""
    diff_content = await request_specific_diff_format()
    
    if diff_content:
        print("\n" + "="*80)
        print("GEMINI'S SPECIFIC DIFF FORMAT")
        print("="*80)
        
        clean_diff = ''.join(char if ord(char) < 128 else '?' for char in diff_content)
        print(clean_diff)
        print("="*80)
        
        # Save the specific diff
        with open("X:/aicleaner_v3/phase1a_specific.diff", "w", encoding="utf-8") as f:
            f.write(clean_diff)
        
        print(f"\n[SUCCESS] Specific diff saved - ready for review and implementation")
        
    else:
        print("[ERROR] Failed to get specific diff format")

if __name__ == "__main__":
    asyncio.run(main())