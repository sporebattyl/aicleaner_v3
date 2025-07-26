#!/usr/bin/env python3
"""
Simple test script to verify the addon environment
"""

import os
import sys
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=== AICleaner V3 Simple Test ===")
    
    # Check environment
    logger.info("Checking environment variables...")
    env_vars = ['MQTT_HOST', 'CORE_SERVICE_URL', 'LOG_LEVEL']
    for var in env_vars:
        value = os.getenv(var, "NOT_SET")
        logger.info(f"{var}: {value}")
    
    # Check directories
    logger.info("Checking directories...")
    dirs = ['/data', '/app', '/app/src', '/config']
    for dir_path in dirs:
        exists = os.path.exists(dir_path)
        logger.info(f"{dir_path}: {'EXISTS' if exists else 'MISSING'}")
    
    # Load options.json if available
    options_file = '/data/options.json'
    if os.path.exists(options_file):
        try:
            with open(options_file, 'r') as f:
                options = json.load(f)
            logger.info(f"Options loaded: {options}")
        except Exception as e:
            logger.error(f"Error loading options: {e}")
    else:
        logger.warning("No options.json found")
    
    # Test basic functionality
    logger.info("Testing basic Python imports...")
    try:
        import aiohttp
        import paho.mqtt.client as mqtt
        logger.info("✓ Required imports successful")
    except ImportError as e:
        logger.error(f"✗ Import error: {e}")
        return False
    
    logger.info("✓ Simple test completed successfully!")
    
    # Keep running for 30 seconds
    logger.info("Keeping addon running for 30 seconds...")
    import time
    for i in range(30):
        time.sleep(1)
        if i % 10 == 0:
            logger.info(f"Still running... {30-i} seconds remaining")
    
    logger.info("Test completed.")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)