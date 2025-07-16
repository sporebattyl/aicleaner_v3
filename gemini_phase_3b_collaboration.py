#!/usr/bin/env python3
"""
Gemini-Led Collaboration for Phase 3B: Zone Configuration
Uses Gemini CLI approach with 3 API keys as specified
"""

import google.generativeai as genai
import json
import sys
import time

# Your 3 API keys for cycling (Gemini Pro 2.5 preferred)
API_KEYS = [
    "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo",  # Key 1
    "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc",  # Key 2  
    "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro"   # Key 3
]

MODELS = [
    "gemini-2.0-flash-exp",  # Latest experimental 
    "gemini-1.5-pro-latest", # Latest Pro model (should be 2.5)
    "gemini-1.5-flash"       # Flash model fallback
]

current_key_index = 0
current_model_index = 1  # Start with 2.5 Pro model

def get_next_gemini_client():
    """Get next Gemini client with API key cycling (Pro 2.5 preferred)."""
    global current_key_index, current_model_index
    
    api_key = API_KEYS[current_key_index]
    model_name = MODELS[current_model_index]
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    print(f"Gemini using API Key {current_key_index + 1} with {model_name}")
    
    # Cycle to next key (prefer Pro model)
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    
    return model

def gemini_do_work(prompt: str, max_retries: int = 3) -> str:
    """Gemini does the work with API key cycling and model fallback."""
    global current_model_index
    
    for attempt in range(max_retries):
        try:
            model = get_next_gemini_client()
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            
            # Switch models on quota/limit errors
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                print("Switching to next model due to quota/limit")
                current_model_index = (current_model_index + 1) % len(MODELS)
            
            if attempt == max_retries - 1:
                raise e
            
            time.sleep(2)
    
    raise Exception("All Gemini attempts failed")

def main():
    # Read Phase 3B requirements
    try:
        with open('finalized prompts/08_PHASE_3B_ZONE_CONFIGURATION_100.md', 'r', encoding='utf-8') as f:
            phase_3b_requirements = f.read()
    except FileNotFoundError:
        print("Phase 3B prompt file not found")
        sys.exit(1)
    
    # Gemini-led collaboration prompt for Phase 3B
    gemini_lead_prompt = f"""
You are Gemini, leading the implementation of Phase 3B: Zone Configuration for AICleaner v3.

🎯 YOUR LEADERSHIP ROLE:
You will design, architect, and provide complete implementation diffs for this phase. Claude will review your work and collaborate with you until we reach consensus, then implement your agreed-upon solution.

📋 COMPLETED PHASES (Built by Claude based on our collaboration):
✅ Phase 1A: Configuration Consolidation - Unified config system
✅ Phase 1B: AI Provider Integration - Multi-provider AI with intelligent routing  
✅ Phase 1C: Configuration Testing - Comprehensive AAA testing framework
✅ Phase 2A: AI Model Optimization - Advanced optimization with caching
✅ Phase 2B: Response Quality Enhancement - Quality assessment & optimization
✅ Phase 2C: AI Performance Monitoring - Real-time monitoring & alerting
✅ Phase 3A: Device Detection - Multi-protocol discovery with HA integration

🏗️ CURRENT TASK: Phase 3B: Zone Configuration Optimization

PHASE 3B REQUIREMENTS:
{phase_3b_requirements}

🎯 YOUR IMPLEMENTATION MANDATE:
1. **Lead the Architecture** - Design the complete zone configuration system
2. **Provide Complete Diffs** - Give Claude all files to create/modify with exact code
3. **Build on Existing Phases** - Integrate with device detection (3A) and monitoring (2C)
4. **Follow 100/100 Standards** - Meet all 6-section framework requirements
5. **Ensure HA Compliance** - Full Home Assistant addon integration

📁 EXISTING CODEBASE STRUCTURE:
```
X:\\aicleaner_v3\\addons\\aicleaner_v3\\
├── core/                    # Config, schema, validation (Phase 1A-1C)
├── ai/                      # AI providers, optimization, quality, monitoring (Phase 1B, 2A-2C)
├── devices/                 # Device discovery system (Phase 3A)
└── zones/                   # 👈 NEW: Your zone system goes here
```

🔧 INTEGRATION REQUIREMENTS:
- **Use Phase 3A devices**: Import and build on DeviceInfo, DeviceDiscoveryManager
- **Use Phase 2C monitoring**: Integrate with AIPerformanceMonitor for zone metrics
- **Use Phase 1A config**: Build on ConfigSchema for zone configuration
- **Follow Phase 1C testing**: Use AAA pattern for all tests

💎 IMPLEMENTATION DELIVERABLES REQUIRED:
1. **Complete File Structure** - All files for zones/ directory
2. **Exact Code Diffs** - Ready-to-implement code for each file  
3. **Integration Code** - How to connect with existing phases
4. **HA Integration** - Zone integration with Home Assistant
5. **Test Suite** - Comprehensive tests following AAA pattern
6. **Documentation** - User and developer docs

🚀 RESPONSE FORMAT:
```
# PHASE 3B: ZONE CONFIGURATION - GEMINI IMPLEMENTATION

## 1. ARCHITECTURE OVERVIEW
[Your complete system design]

## 2. FILE STRUCTURE
[Complete directory/file layout]

## 3. IMPLEMENTATION DIFFS
[All code files with complete implementations]

## 4. INTEGRATION DETAILS  
[How this connects to existing phases]

## 5. HOME ASSISTANT INTEGRATION
[HA zone integration code]

## 6. TESTING FRAMEWORK
[Complete test suite with AAA pattern]

## 7. CONFIGURATION & SETUP
[How users configure and use zones]
```

🎯 SUCCESS CRITERIA:
- Zone creation accuracy >90%
- Automation rule effectiveness >90% 
- Performance optimization >30%
- Adaptation accuracy >85%
- Full 6-section framework compliance
- 100/100 readiness achievement

Begin implementation now. Lead this phase and provide Claude with everything needed for implementation!
"""

    print("Starting Gemini-led collaboration for Phase 3B: Zone Configuration")
    print("=" * 80)
    
    try:
        response = gemini_do_work(gemini_lead_prompt)
        
        # Save Gemini's implementation
        output_file = "gemini_phase_3b_implementation.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response)
        
        print(f"Gemini implementation complete! Saved to: {output_file}")
        print("=" * 80)
        print("GEMINI'S PHASE 3B IMPLEMENTATION:")
        print("=" * 80)
        print(response)
        
        return response
        
    except Exception as e:
        print(f"Gemini collaboration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()