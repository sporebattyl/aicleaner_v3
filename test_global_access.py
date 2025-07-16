#!/usr/bin/env python3
"""
Test Global Zen MCP Access from Current Directory
"""

import sys
import os

# Test accessing global zen MCP client
global_path = '/c/Users/dmjtx/.claude/zen_mcp_global'
print(f"Testing access to global zen MCP at: {global_path}")

# Add to Python path
if global_path not in sys.path:
    sys.path.append(global_path)
    print(f"[OK] Added {global_path} to Python path")

try:
    # Test import
    from zen_gemini_client import ZenGeminiClient, zen_quota_status
    print("[OK] Successfully imported global zen MCP client!")
    
    # Test client creation
    client = ZenGeminiClient()
    print(f"[OK] Created client with {len(client.api_keys)} API keys")
    
    # Test quota status
    status = zen_quota_status()
    print(f"[OK] Quota status check successful")
    print(f"Recommended: {status['recommended_model']} on {status['recommended_api_key']}")
    print(f"Total capacity: {status['total_api_keys']} API keys")
    
    print("\n[SUCCESS] GLOBAL ZEN MCP ACCESS CONFIRMED!")
    print("You can now use this from any session with:")
    print("```python")
    print("import sys")
    print("sys.path.append('/c/Users/dmjtx/.claude/zen_mcp_global')")
    print("from zen_gemini_client import zen_collaborate, zen_quota_status")
    print("```")
    
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    print("Global zen MCP may not be accessible from this location")
    
except Exception as e:
    print(f"[ERROR] Error: {e}")

print(f"\nCurrent working directory: {os.getcwd()}")
print(f"Python path includes: {[p for p in sys.path if 'zen' in p]}")