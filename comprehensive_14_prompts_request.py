#!/usr/bin/env python3
"""
Comprehensive Request for Gemini to Create 14 Prompt Enhancement Diffs
"""

import asyncio
from zen_mcp import zen_collaborate

async def request_comprehensive_14_prompts():
    """Request Gemini to create specific diffs for all 14 remaining prompts"""
    
    print("=== COMPREHENSIVE 14 PROMPTS ENHANCEMENT REQUEST ===")
    
    # Read the master template and Phase 1A for reference
    with open("X:/aicleaner_v3/docs/prompts/MASTER_TEMPLATE_100.md", "r", encoding="utf-8") as f:
        master_template = f.read()
    
    with open("X:/aicleaner_v3/docs/prompts/PHASE_1A_CONFIGURATION_CONSOLIDATION_99PLUS.md", "r", encoding="utf-8") as f:
        phase1a_example = f.read()
    
    comprehensive_request = f"""
COMPREHENSIVE 14 PROMPTS ENHANCEMENT - APPLY 100/100 PATTERN

Gemini, I need you to create specific enhancement diffs for each of the 14 remaining prompts using our validated 100/100 pattern.

MASTER TEMPLATE REFERENCE:
{master_template}

PROVEN 100/100 EXAMPLE (Phase 1A):
{phase1a_example}

TASK: Create detailed enhancement diffs for these 14 prompts:

1. **Phase 1B: Configuration Migration & Validation**
2. **Phase 1C: Configuration Testing & Quality Assurance**  
3. **Phase 2A: AI Model Provider Optimization**
4. **Phase 2B: Response Quality Enhancement**
5. **Phase 2C: AI Performance Monitoring**
6. **Phase 3A: Device Detection Enhancement**
7. **Phase 3B: Zone Configuration Optimization**
8. **Phase 3C: Security Audit & Hardening**
9. **Phase 4A: Home Assistant Integration Improvement**
10. **Phase 4B: MQTT Discovery Enhancement**
11. **Phase 4C: User Interface Improvements**
12. **Phase 5A: Performance Optimization**
13. **Phase 5B: Resource Management**
14. **Phase 5C: Production Deployment**

REQUIRED OUTPUT FORMAT:
For each prompt, provide a structured diff showing exactly what sections to add. Use this format:

```
=== PHASE_1B_CONFIGURATION_MIGRATION_ENHANCEMENT.diff ===

### Key Additions Required:

1. **User-Facing Error Reporting Strategy**
   - Error Classification: [specific to migration scenarios]
   - Progressive Error Disclosure: [migration-specific guidance]
   - Recovery Guidance: [migration rollback procedures]
   - Error Prevention: [pre-migration validation]

2. **Structured Logging Strategy**
   - Log Levels: [DEBUG, INFO, WARN, ERROR, CRITICAL for migration]
   - Log Format Standards: [migration-specific JSON logging]
   - Contextual Information: [migration progress, version details]
   - Integration Requirements: [HA logging compatibility]

3. **Enhanced Security Considerations**
   - Continuous Security: [migration security threats]
   - Secure Coding Practices: [migration data protection]
   - Dependency Vulnerability Scans: [migration tool security]

4. **Success Metrics & Performance Baselines**
   - KPIs: [migration completion rates, success metrics]
   - Performance Baselines: [migration speed, memory usage]
   - Benchmarking Strategy: [before/after validation]

5. **Developer Experience & Maintainability**
   - Code Readability: [migration documentation standards]
   - Testability: [migration test frameworks]
   - Configuration Simplicity: [user-friendly migration process]
   - Extensibility: [future migration compatibility]

### Specific Implementation Notes:
[Phase 1B specific guidance for configuration migration and validation]
```

Continue this pattern for ALL 14 phases, customizing each section to the specific phase requirements.

CRITICAL REQUIREMENTS:
1. Each enhancement must be specific to that phase's domain
2. Include all 5 key sections from the 100/100 pattern
3. Provide actionable, specific guidance for each phase
4. Ensure Home Assistant addon compliance
5. Include TDD/AAA pattern integration
6. Add MCP server usage requirements
7. Include rollback and recovery procedures

Please provide comprehensive diffs for all 14 phases.
"""
    
    result = await zen_collaborate(comprehensive_request)
    
    if result.get("success"):
        print(f"[SUCCESS] Comprehensive 14 prompts enhancement completed")
        return result["response"]
    else:
        print(f"[ERROR] Comprehensive enhancement request failed: {result.get('error')}")
        return None

async def main():
    """Main execution"""
    enhancement_diffs = await request_comprehensive_14_prompts()
    
    if enhancement_diffs:
        print("\n" + "="*80)
        print("GEMINI'S COMPREHENSIVE 14 PROMPTS ENHANCEMENT DIFFS")
        print("="*80)
        
        clean_diffs = ''.join(char if ord(char) < 128 else '?' for char in enhancement_diffs)
        print(clean_diffs)
        print("="*80)
        
        # Save the comprehensive enhancement diffs
        with open("X:/aicleaner_v3/comprehensive_14_prompts_diffs.md", "w", encoding="utf-8") as f:
            f.write(clean_diffs)
        
        print(f"\n[SUCCESS] Comprehensive 14 prompts enhancement diffs received - ready for review")
        
    else:
        print("[ERROR] Failed to get comprehensive enhancement diffs")

if __name__ == "__main__":
    asyncio.run(main())