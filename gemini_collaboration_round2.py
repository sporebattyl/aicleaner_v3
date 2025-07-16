#!/usr/bin/env python3
"""
Gemini Collaboration Round 2 - Phase 3A Refinements
Sends Claude's feedback and requests refined implementation
"""

import google.generativeai as genai
import json
import sys
import time

# API Keys for cycling
API_KEYS = [
    "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo",  # Key 1
    "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc",  # Key 2  
    "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro"   # Key 3
]

MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro", 
    "gemini-1.5-flash"
]

current_key_index = 1  # Start with key 2
current_model_index = 0

def get_next_client():
    """Get next Gemini client with API key cycling."""
    global current_key_index, current_model_index
    
    api_key = API_KEYS[current_key_index]
    model_name = MODELS[current_model_index]
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    print(f"Using API Key {current_key_index + 1} with model {model_name}")
    
    # Cycle to next key
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    
    return model

def collaborate_with_gemini(prompt: str, max_retries: int = 3) -> str:
    """Collaborate with Gemini using API key cycling and model fallback."""
    global current_model_index
    
    for attempt in range(max_retries):
        try:
            model = get_next_client()
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            
            # Try next model on error
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                print("Switching to next model due to quota/limit")
                current_model_index = (current_model_index + 1) % len(MODELS)
            
            if attempt == max_retries - 1:
                raise e
            
            time.sleep(2)
    
    raise Exception("All collaboration attempts failed")

def main():
    # Read Claude's feedback
    try:
        with open('claude_feedback_phase_3a.md', 'r', encoding='utf-8') as f:
            claude_feedback = f.read()
    except FileNotFoundError:
        print("Claude feedback file not found")
        sys.exit(1)
    
    # Read the original response
    try:
        with open('gemini_response_phase_3a.md', 'r', encoding='utf-8') as f:
            original_response = f.read()
    except FileNotFoundError:
        print("Original Gemini response not found")
        sys.exit(1)
    
    # Create refinement prompt
    refinement_prompt = f"""
You are Gemini, continuing collaboration with Claude on Phase 3A: Device Detection for AICleaner v3.

COLLABORATION STATUS:
Claude has reviewed your initial implementation and provided excellent feedback. Claude agrees with the overall architecture and approach but requests specific refinements.

CLAUDE'S FEEDBACK:
{claude_feedback}

YOUR ORIGINAL RESPONSE:
{original_response}

REFINEMENT REQUEST:
Please provide updated code diffs addressing Claude's collaboration points:

1. **Enhanced DeviceInfo Class** - Implement the complete dataclass with all metadata fields Claude specified
2. **Corrected Async/Await Patterns** - Fix any sync/async mixing issues in all modules  
3. **Phase 2C Integration** - Add actual integration with AIPerformanceMonitor from Phase 2C
4. **Complete HA Device Registry** - Implement actual device registry API calls, not placeholders
5. **Device Database Schema** - Provide complete JSON schema with example device signatures

COLLABORATION GOALS:
- Address each refinement point specifically
- Maintain the excellent modular architecture you designed
- Ensure proper integration with existing phases (1A, 1B, 2C)
- Provide complete, implementable code diffs
- Follow the 100/100 readiness specifications

RESPONSE FORMAT:
1. **ACKNOWLEDGMENT** - Confirm understanding of refinements needed
2. **REFINED CODE DIFFS** - Updated diffs addressing each collaboration point
3. **INTEGRATION DETAILS** - Specific integration code for Phase 2C monitoring
4. **DATABASE SCHEMA** - Complete JSON schema with examples
5. **IMPLEMENTATION NOTES** - Any additional considerations for Claude

Please provide the refined implementation that Claude can confidently implement.
"""

    print("Collaborating with Gemini on Phase 3A refinements...")
    print("=" * 80)
    
    try:
        response = collaborate_with_gemini(refinement_prompt)
        
        # Save response to file
        output_file = "gemini_response_phase_3a_refined.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response)
        
        print(f"Gemini refinement complete! Response saved to: {output_file}")
        print("=" * 80)
        print(response)
        
        return response
        
    except Exception as e:
        print(f"Collaboration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()