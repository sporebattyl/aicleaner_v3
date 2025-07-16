#!/usr/bin/env python3
"""
Gemini Collaboration Script for AICleaner v3 Phase Implementations
Uses 3 API keys with Pro 2.5 preference and Flash fallback
"""

import google.generativeai as genai
import json
import sys
import time
from typing import Dict, Any, List

# API Keys for cycling
API_KEYS = [
    "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo",  # Key 1
    "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc",  # Key 2  
    "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro"   # Key 3
]

MODELS = [
    "gemini-2.0-flash-exp",  # Latest experimental model
    "gemini-1.5-pro",       # Pro model
    "gemini-1.5-flash"      # Flash model
]

current_key_index = 0
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
            
            time.sleep(2)  # Wait before retry
    
    raise Exception("All collaboration attempts failed")

def main():
    """Main collaboration function."""
    if len(sys.argv) < 2:
        print("Usage: python gemini_collaboration.py <phase_name>")
        print("Example: python gemini_collaboration.py 'Phase 3A: Device Detection'")
        sys.exit(1)
    
    phase_name = sys.argv[1]
    
    # Read the prompt file for the phase
    phase_file_map = {
        "Phase 3A": "07_PHASE_3A_DEVICE_DETECTION_100.md",
        "Phase 3B": "08_PHASE_3B_ZONE_CONFIGURATION_100.md", 
        "Phase 3C": "09_PHASE_3C_SECURITY_AUDIT_100.md",
        "Phase 4A": "10_PHASE_4A_HA_INTEGRATION_100.md",
        "Phase 4B": "11_PHASE_4B_MQTT_DISCOVERY_100.md",
        "Phase 4C": "12_PHASE_4C_USER_INTERFACE_100.md",
        "Phase 5A": "13_PHASE_5A_PERFORMANCE_OPTIMIZATION_100.md",
        "Phase 5B": "14_PHASE_5B_RESOURCE_MANAGEMENT_100.md",
        "Phase 5C": "15_PHASE_5C_PRODUCTION_DEPLOYMENT_100.md"
    }
    
    if phase_name not in phase_file_map:
        print(f"Unknown phase: {phase_name}")
        print(f"Available phases: {list(phase_file_map.keys())}")
        sys.exit(1)
    
    prompt_file = f"finalized prompts/{phase_file_map[phase_name]}"
    
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            phase_requirements = f.read()
    except FileNotFoundError:
        print(f"Prompt file not found: {prompt_file}")
        sys.exit(1)
    
    # Create collaboration prompt
    collaboration_prompt = f"""
You are Gemini, collaborating with Claude to implement {phase_name} for AICleaner v3.

COLLABORATION CONTEXT:
Claude has successfully implemented Phases 1A-2C:
- Phase 1A: Configuration Schema Consolidation ✅
- Phase 1B: AI Provider Integration ✅  
- Phase 1C: Configuration Testing ✅
- Phase 2A: AI Model Optimization ✅
- Phase 2B: Response Quality Enhancement ✅
- Phase 2C: AI Performance Monitoring ✅

CURRENT TASK: {phase_name}

PHASE REQUIREMENTS:
{phase_requirements}

COLLABORATION WORKFLOW:
1. Analyze the phase requirements thoroughly
2. Create a comprehensive implementation plan
3. Generate code diffs for ALL required files
4. Provide clear explanations for design decisions
5. Ensure integration with existing phases

YOUR RESPONSE MUST INCLUDE:
1. **IMPLEMENTATION PLAN** - Detailed plan with file structure
2. **CODE DIFFS** - Complete diffs for all files to create/modify  
3. **INTEGRATION NOTES** - How this integrates with previous phases
4. **TESTING STRATEGY** - Test cases and validation approach
5. **DOCUMENTATION** - User and developer documentation

IMPORTANT REQUIREMENTS:
- Follow the 100/100 readiness specifications exactly
- Use existing codebase structure: X:\\aicleaner_v3\\addons\\aicleaner_v3\\
- Build upon previous phases (import and use existing components)
- Follow AAA testing pattern established in Phase 1C
- Implement all 6-section framework requirements
- Ensure Home Assistant addon compliance

Please provide a complete implementation with all files and detailed explanations.
"""

    print(f"Collaborating with Gemini on {phase_name}...")
    print("=" * 80)
    
    try:
        response = collaborate_with_gemini(collaboration_prompt)
        
        # Save response to file
        output_file = f"gemini_response_{phase_name.lower().replace(' ', '_').replace(':', '')}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response)
        
        print(f"Gemini collaboration complete! Response saved to: {output_file}")
        print("=" * 80)
        print(response)
        
        return response
        
    except Exception as e:
        print(f"Collaboration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()