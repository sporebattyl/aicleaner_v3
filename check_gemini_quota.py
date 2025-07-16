#!/usr/bin/env python3
"""
Check Gemini Quota Status
"""

import asyncio
from zen_gemini_client import ZenGeminiClient

async def check_quota():
    """Check current quota status"""
    
    client = ZenGeminiClient()
    
    # Get quota status
    status = client.get_quota_status()
    
    print("GEMINI QUOTA STATUS:")
    print("=" * 50)
    print(f"Total API Keys: {status['total_api_keys']}")
    print(f"Recommended Model: {status['recommended_model']}")
    print(f"Recommended API Key: {status['recommended_api_key']}")
    print()
    
    for api_key, models in status['quota_status'].items():
        print(f"{api_key}:")
        for model_name, model_status in models.items():
            print(f"  {model_name}:")
            print(f"    Used: {model_status['daily_used']}/{model_status['daily_limit']}")
            print(f"    Remaining: {model_status['daily_remaining']}")
            print(f"    RPM Limit: {model_status['rpm_limit']}")
            print(f"    Can Use Now: {model_status['can_use_now']}")
            print(f"    Time Since Last: {model_status['time_since_last_request']}")
            print()

if __name__ == "__main__":
    asyncio.run(check_quota())