#!/usr/bin/env python3
"""
Claude Feedback to Gemini for Phase 3B Complete Implementation
Using Gemini 2.5 Pro with API key cycling
"""

import google.generativeai as genai
import json
import sys
import time

# Your 3 API keys for cycling (Gemini 2.5 Pro preferred)
API_KEYS = [
    "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo",  # Key 1
    "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc",  # Key 2  
    "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro"   # Key 3
]

MODELS = [
    "gemini-1.5-pro-latest", # Gemini 2.5 Pro (preferred)
    "gemini-2.0-flash-exp",  # Latest experimental fallback
    "gemini-1.5-flash"       # Flash model fallback
]

current_key_index = 1  # Start with Key 2
current_model_index = 0  # Start with 2.5 Pro model

def get_next_gemini_client():
    """Get next Gemini client with API key cycling (2.5 Pro preferred)."""
    global current_key_index, current_model_index
    
    api_key = API_KEYS[current_key_index]
    model_name = MODELS[current_model_index]
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    print(f"Gemini using API Key {current_key_index + 1} with {model_name}")
    
    # Cycle to next key (prefer 2.5 Pro model)
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
            
            time.sleep(3)  # Longer wait between retries
    
    raise Exception("All Gemini attempts failed")

def main():
    # Read Gemini's previous response
    try:
        with open('gemini_phase_3b_implementation.md', 'r', encoding='utf-8') as f:
            gemini_initial_response = f.read()
    except FileNotFoundError:
        print("Gemini's initial response file not found")
        sys.exit(1)
    
    # Claude's collaboration feedback to Gemini
    claude_feedback_prompt = f"""
You are Gemini, continuing our collaboration on Phase 3B: Zone Configuration for AICleaner v3.

COLLABORATION STATUS:
Claude has reviewed your initial implementation and provides the following feedback:

YOUR PREVIOUS RESPONSE:
{gemini_initial_response}

CLAUDE'S REVIEW:
✅ EXCELLENT STRENGTHS:
1. Strong Architecture - Well-designed modular system with clear separation of concerns
2. Proper Integration - Correctly builds on Phases 1A, 2C, and 3A 
3. ML-Based Optimization - Good use of scikit-learn for adaptive zone management
4. HA Integration - Proper Home Assistant addon approach
5. 6-Section Framework - Addresses logging, error handling, security requirements

🔄 AREAS NEEDING COMPLETE IMPLEMENTATION:
1. **Incomplete Code Diffs** - You noted "Due to complexity, complete diffs cannot be provided" - Claude needs FULL implementation code
2. **Missing Models Definition** - The models.py file structure needs COMPLETE Zone and Device models
3. **Incomplete HA Integration** - Need SPECIFIC HA entity registration and API code  
4. **Test Suite Not Provided** - Need ACTUAL AAA pattern test implementations
5. **Missing Error Handling Details** - Need COMPLETE progressive error disclosure implementation
6. **Optimization Algorithm Details** - Need MORE SPECIFIC ML implementation for zone optimization

CLAUDE'S COLLABORATION REQUEST:
Claude agrees with your excellent architecture! However, Claude needs COMPLETE implementation details to proceed with consensus and implementation.

Please provide the FULL implementation with:

1. **COMPLETE Code Diffs** - Full implementations for ALL files (manager.py, config.py, optimization.py, monitoring.py, ha_integration.py, models.py, schemas.py, logger.py, utils.py)

2. **COMPLETE Models** - Full Zone, Device, and Rule data models with ALL attributes, methods, and properties

3. **DETAILED HA Integration** - Specific entity registration, management code, and HA API implementations

4. **COMPLETE Test Suite** - Full AAA pattern tests for ALL components with actual test implementations

5. **ML Algorithm Details** - Specific optimization algorithms with real data processing code

6. **COMPLETE Error Handling System** - Full progressive error disclosure implementation

RESPONSE FORMAT REQUIRED:
```
# PHASE 3B: COMPLETE IMPLEMENTATION - GEMINI RESPONSE TO CLAUDE

## COMPLETE FILE IMPLEMENTATIONS

### zones/manager.py
[COMPLETE FILE CODE - NOT SNIPPETS]

### zones/config.py  
[COMPLETE FILE CODE - NOT SNIPPETS]

### zones/optimization.py
[COMPLETE FILE CODE - NOT SNIPPETS]

### zones/monitoring.py
[COMPLETE FILE CODE - NOT SNIPPETS]

### zones/ha_integration.py
[COMPLETE FILE CODE - NOT SNIPPETS]

### zones/models.py
[COMPLETE FILE CODE - NOT SNIPPETS]

### zones/schemas.py
[COMPLETE FILE CODE - NOT SNIPPETS]

### zones/logger.py
[COMPLETE FILE CODE - NOT SNIPPETS]

### zones/utils.py
[COMPLETE FILE CODE - NOT SNIPPETS]

## COMPLETE TEST SUITE

### zones/tests/test_manager.py
[COMPLETE AAA PATTERN TESTS]

### zones/tests/test_config.py
[COMPLETE AAA PATTERN TESTS]

[ALL OTHER TEST FILES WITH COMPLETE IMPLEMENTATIONS]
```

SUCCESS CRITERIA FOR COLLABORATION:
- Zone creation accuracy >90%
- Automation rule effectiveness >90% 
- Performance optimization >30%
- Adaptation accuracy >85%
- Full 6-section framework compliance
- 100/100 readiness achievement
- COMPLETE code that Claude can implement immediately

Please provide the COMPLETE implementation that allows Claude to achieve consensus and proceed with implementation!
"""

    print("Sending Claude's feedback to Gemini for complete Phase 3B implementation")
    print("=" * 80)
    
    try:
        response = gemini_do_work(claude_feedback_prompt)
        
        # Save Gemini's complete implementation
        output_file = "gemini_phase_3b_complete_implementation.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response)
        
        print(f"Gemini complete implementation received! Saved to: {output_file}")
        print("=" * 80)
        print("GEMINI'S COMPLETE PHASE 3B IMPLEMENTATION:")
        print("=" * 80)
        print(response[:2000])  # Show first 2000 chars to avoid encoding issues
        print("\n[... Full implementation saved to file ...]")
        
        return response
        
    except Exception as e:
        print(f"Gemini collaboration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()