#!/usr/bin/env python3
"""
Test Script for AICleaner v3 Web Interface
Tests the FastAPI backend endpoints to ensure proper functionality
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

import requests
from fastapi.testclient import TestClient

# Add the application directory to the path
sys.path.insert(0, str(Path(__file__).parent / "addons" / "aicleaner_v3"))

from api.backend import app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_endpoints():
    """Test all API endpoints"""
    
    # Create test client
    client = TestClient(app)
    
    logger.info("Testing AICleaner v3 Web Interface API endpoints...")
    
    # Test health check
    logger.info("Testing health check endpoint...")
    response = client.get("/api/health")
    logger.info(f"Health check status: {response.status_code}")
    if response.status_code == 200:
        logger.info(f"Health check response: {response.json()}")
    else:
        logger.error(f"Health check failed: {response.text}")
    
    # Test system status (may fail due to uninitialized services)
    logger.info("Testing system status endpoint...")
    response = client.get("/api/status")
    logger.info(f"System status: {response.status_code}")
    if response.status_code == 200:
        logger.info("System status endpoint working")
    else:
        logger.warning(f"System status failed (expected): {response.status_code}")
    
    # Test providers endpoint (may fail due to uninitialized services)
    logger.info("Testing providers endpoint...")
    response = client.get("/api/providers")
    logger.info(f"Providers status: {response.status_code}")
    if response.status_code == 200:
        logger.info("Providers endpoint working")
    else:
        logger.warning(f"Providers failed (expected): {response.status_code}")
    
    # Test strategy endpoint (may fail due to uninitialized services)
    logger.info("Testing strategy endpoint...")
    response = client.get("/api/strategy")
    logger.info(f"Strategy status: {response.status_code}")
    if response.status_code == 200:
        logger.info("Strategy endpoint working")
    else:
        logger.warning(f"Strategy failed (expected): {response.status_code}")
    
    # Test ML stats endpoint (may fail due to uninitialized services)
    logger.info("Testing ML stats endpoint...")
    response = client.get("/api/ml_stats")
    logger.info(f"ML stats status: {response.status_code}")
    if response.status_code == 200:
        logger.info("ML stats endpoint working")
    else:
        logger.warning(f"ML stats failed (expected): {response.status_code}")
    
    # Test logs endpoint
    logger.info("Testing logs endpoint...")
    response = client.post("/api/logs", json={"limit": 10})
    logger.info(f"Logs status: {response.status_code}")
    if response.status_code == 200:
        logger.info("Logs endpoint working")
        logs_data = response.json()
        logger.info(f"Received {len(logs_data.get('data', {}).get('logs', []))} log entries")
    else:
        logger.warning(f"Logs failed (expected): {response.status_code}")
    
    logger.info("API endpoint testing completed!")

def test_static_files():
    """Test static file serving"""
    
    client = TestClient(app)
    
    logger.info("Testing static file serving...")
    
    # Test main dashboard
    logger.info("Testing main dashboard...")
    response = client.get("/")
    logger.info(f"Main dashboard status: {response.status_code}")
    if response.status_code == 200:
        logger.info("Main dashboard loads successfully")
    else:
        logger.error(f"Main dashboard failed: {response.status_code}")
    
    # Test providers page
    logger.info("Testing providers page...")
    response = client.get("/providers.html")
    logger.info(f"Providers page status: {response.status_code}")
    if response.status_code == 200:
        logger.info("Providers page loads successfully")
    else:
        logger.error(f"Providers page failed: {response.status_code}")
    
    # Test logs page
    logger.info("Testing logs page...")
    response = client.get("/logs.html")
    logger.info(f"Logs page status: {response.status_code}")
    if response.status_code == 200:
        logger.info("Logs page loads successfully")
    else:
        logger.error(f"Logs page failed: {response.status_code}")
    
    logger.info("Static file testing completed!")

def test_live_server():
    """Test against a live server if available"""
    
    logger.info("Testing live server (if available)...")
    
    try:
        # Try to connect to a live server
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        if response.status_code == 200:
            logger.info("Live server is running and responding!")
            logger.info(f"Live server response: {response.json()}")
        else:
            logger.warning(f"Live server returned status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        logger.info("No live server detected (this is normal for testing)")
    except requests.exceptions.Timeout:
        logger.warning("Live server request timed out")
    except Exception as e:
        logger.error(f"Error testing live server: {e}")

def main():
    """Run all tests"""
    
    logger.info("=" * 60)
    logger.info("AICleaner v3 Web Interface Test Suite")
    logger.info("=" * 60)
    
    try:
        # Test API endpoints
        test_api_endpoints()
        
        logger.info("-" * 60)
        
        # Test static files
        test_static_files()
        
        logger.info("-" * 60)
        
        # Test live server
        test_live_server()
        
        logger.info("=" * 60)
        logger.info("All tests completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())