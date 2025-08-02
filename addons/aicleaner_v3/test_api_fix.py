#!/usr/bin/env python3
"""
Test script to verify the API fixes work
"""

import os
import sys
import asyncio
import logging
import aiohttp

# Add src directory to path
sys.path.insert(0, '/home/drewcifer/aicleaner_v3/addons/aicleaner_v3/src')

from web_ui_enhanced import EnhancedWebUI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockApp:
    """Mock app instance for testing"""
    def __init__(self):
        self.status = "test"
        self.enabled = True
        self.mqtt_client = None
        self.ai_response_count = 0
        self.last_ai_request = None

async def test_api_endpoints():
    """Test the web UI API endpoints"""
    
    # Create mock app and web UI
    mock_app = MockApp()
    web_ui = EnhancedWebUI(mock_app)
    
    # Check environment
    supervisor_token = os.getenv('SUPERVISOR_TOKEN')
    logger.info(f"SUPERVISOR_TOKEN available: {bool(supervisor_token)}")
    
    if not supervisor_token:
        logger.error("SUPERVISOR_TOKEN not available - this test needs to run inside the addon container")
        return False
    
    try:
        # Test the get_homeassistant_entities method directly
        logger.info("Testing Home Assistant API access...")
        entities = await web_ui.get_homeassistant_entities()
        logger.info(f"Successfully retrieved {len(entities)} entities from Home Assistant")
        
        # Count camera and todo entities
        cameras = [e for e in entities if e.get('entity_id', '').startswith('camera.')]
        todos = [e for e in entities if e.get('entity_id', '').startswith('todo.')]
        
        logger.info(f"Found {len(cameras)} cameras and {len(todos)} todo lists")
        
        # List the entities
        logger.info("Camera entities:")
        for camera in cameras[:5]:  # Show first 5
            logger.info(f"  - {camera.get('entity_id')} ({camera.get('attributes', {}).get('friendly_name', 'No name')})")
        
        logger.info("Todo list entities:")
        for todo in todos:
            logger.info(f"  - {todo.get('entity_id')} ({todo.get('attributes', {}).get('friendly_name', 'No name')})")
        
        logger.info("✅ API test successful!")
        return True
        
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_api_endpoints())
    if success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Tests failed!")
        sys.exit(1)