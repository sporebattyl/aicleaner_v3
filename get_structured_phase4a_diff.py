#!/usr/bin/env python3
"""
Get Structured Phase 4A Diff from Gemini - Section by Section
"""

import asyncio
import json
from zen_gemini_client import ZenGeminiClient

async def get_structured_diff():
    """Get Phase 4A diff in structured sections"""
    
    client = ZenGeminiClient()
    
    # Request structured diff creation
    structured_request = """
# GEMINI: Create Structured Phase 4A Diff

Please create the comprehensive diff for Phase 4A: Home Assistant Integration Improvement following the exact 6-section 100/100 pattern structure.

## REQUIREMENTS

Create a diff that adds the 6-section enhancement framework to the base Phase 4A content. Format as additions (+) to the existing prompt.

## STRUCTURE NEEDED

```
## 6-Section 100/100 Enhancement Framework

### 1. User-Facing Error Reporting Strategy
+ [HA integration specific error handling]

### 2. Structured Logging Strategy  
+ [HA service logs integration]

### 3. Enhanced Security Considerations
+ [HA security compliance details]

### 4. Success Metrics & Performance Baselines
+ [HA integration metrics and KPIs]

### 5. Developer Experience & Maintainability
+ [HA addon development workflow]

### 6. Documentation Strategy (User & Developer)
+ [HA certification documentation]
```

## SPECIFIC HA FOCUS

Each section should address:
- HA Supervisor API integration
- HA entity registration and management
- HA service calls and automation
- HA config_flow implementation
- HA MQTT discovery protocols
- HA security and compliance requirements

Please provide the complete 6-section addition that transforms Phase 4A into a 100/100 quality HA integration improvement prompt.
"""

    print("REQUESTING: Structured Phase 4A 6-section diff...")
    print()
    
    # Request the collaboration
    result = await client.collaborate_with_gemini(structured_request)
    
    if result["success"]:
        print("SUCCESS: Structured diff received!")
        print(f"Model: {result['model_used']}")
        print(f"Quota: {result['quota_status']['daily_used']}/{result['quota_status']['daily_limit']}")
        print()
        print("=" * 80)
        print("STRUCTURED PHASE 4A DIFF:")
        print("=" * 80)
        print(result["response"])
        print("=" * 80)
        
        # Save the structured response
        with open("X:\\aicleaner_v3\\phase4a_structured_diff.md", "w", encoding="utf-8") as f:
            f.write("# Phase 4A: Home Assistant Integration - Structured 6-Section Diff\n\n")
            f.write(f"**Model**: {result['model_used']}\n")
            f.write(f"**Quota**: {result['quota_status']['daily_used']}/{result['quota_status']['daily_limit']}\n\n")
            f.write(result["response"])
        
        print(f"Saved to: X:\\aicleaner_v3\\phase4a_structured_diff.md")
        
    else:
        print("ERROR: Failed to get structured diff")
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(get_structured_diff())