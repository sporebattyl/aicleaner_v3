#!/usr/bin/env python3
"""
Mock Home Assistant API for AICleaner v3 Testing
Simulates Home Assistant Core API for integration testing
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, request, jsonify, Response
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockHomeAssistantAPI:
    """Mock Home Assistant API server for testing"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.devices = {}
        self.entities = {}
        self.services = {}
        self.events = []
        self.running = True
        
        # Set up routes
        self.setup_routes()
        
    def setup_routes(self):
        """Set up API routes"""
        
        # Health check endpoint
        @self.app.route('/api/', methods=['GET'])
        def health_check():
            """Health check endpoint for Docker health checks"""
            return jsonify({
                "message": "Mock Home Assistant API",
                "version": "test-1.0.0",
                "timestamp": datetime.now().isoformat()
            })
        
        # API info endpoint
        @self.app.route('/api/discovery_info', methods=['GET'])
        def discovery_info():
            """Discovery info endpoint"""
            return jsonify({
                "base_url": "http://mock-ha-api:8123",
                "external_url": None,
                "internal_url": "http://mock-ha-api:8123",
                "requires_api_password": False,
                "version": "2024.1.0"
            })
        
        # States endpoint
        @self.app.route('/api/states', methods=['GET', 'POST'])
        def handle_states():
            """Handle entity states"""
            if request.method == 'GET':
                return jsonify(list(self.entities.values()))
            elif request.method == 'POST':
                # POST - create/update entity state
                data = request.get_json()
                if not data:
                    return jsonify({"error": "Invalid JSON"}), 400
                entity_id = data.get('entity_id')
                if entity_id:
                    self.entities[entity_id] = {
                        'entity_id': entity_id,
                        'state': data.get('state', 'unknown'),
                        'attributes': data.get('attributes', {}),
                        'last_changed': datetime.now().isoformat(),
                        'last_updated': datetime.now().isoformat()
                    }
                    logger.info(f"Updated entity: {entity_id}")
                    return jsonify(self.entities.get(entity_id, {}))
                return jsonify({"error": "entity_id missing"}), 400
        
        # Individual entity state
        @self.app.route('/api/states/<entity_id>', methods=['GET', 'POST'])
        def handle_entity_state(entity_id):
            """Handle individual entity state"""
            if request.method == 'GET':
                entity = self.entities.get(entity_id)
                if entity:
                    return jsonify(entity)
                else:
                    return jsonify({"error": "Entity not found"}), 404
            elif request.method == 'POST':
                # POST - update entity
                data = request.get_json()
                if not data:
                    return jsonify({"error": "Invalid JSON"}), 400
                self.entities[entity_id] = {
                    'entity_id': entity_id,
                    'state': data.get('state', 'unknown'),
                    'attributes': data.get('attributes', {}),
                    'last_changed': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
                logger.info(f"Updated entity: {entity_id}")
                return jsonify(self.entities[entity_id])
        
        # Services endpoint
        @self.app.route('/api/services', methods=['GET'])
        def list_services():
            """List available services"""
            return jsonify(self.services)
        
        # Call service endpoint
        @self.app.route('/api/services/<domain>/<service>', methods=['POST'])
        def call_service(domain, service):
            """Call a service"""
            data = request.get_json() or {}
            service_call = {
                'domain': domain,
                'service': service,
                'service_data': data.get('service_data', {}),
                'target': data.get('target', {}),
                'timestamp': datetime.now().isoformat()
            }
            
            # Log the service call
            logger.info(f"Service called: {domain}.{service}")
            logger.info(f"Service data: {service_call}")
            
            # Store service call for validation
            if domain not in self.services:
                self.services[domain] = {}
            if service not in self.services[domain]:
                self.services[domain][service] = []
            self.services[domain][service].append(service_call)
            
            return jsonify({"success": True, "service_call": service_call})
        
        # Events endpoint
        @self.app.route('/api/events', methods=['GET'])
        def list_events():
            """List events"""
            return jsonify(self.events[-100:])  # Last 100 events
        
        # Fire event endpoint
        @self.app.route('/api/events/<event_type>', methods=['POST'])
        def fire_event(event_type):
            """Fire an event"""
            data = request.get_json() or {}
            event = {
                'event_type': event_type,
                'data': data,
                'time_fired': datetime.now().isoformat()
            }
            self.events.append(event)
            logger.info(f"Event fired: {event_type}")
            return jsonify(event)
        
        # Config endpoint
        @self.app.route('/api/config', methods=['GET'])
        def get_config():
            """Get HA configuration"""
            return jsonify({
                "components": ["mqtt", "api", "automation", "script"],
                "config_dir": "/config",
                "elevation": 0,
                "internal_url": "http://mock-ha-api:8123",
                "external_url": None,
                "latitude": 40.7128,
                "longitude": -74.0060,
                "location_name": "Test Location",
                "time_zone": "America/New_York",
                "unit_system": {
                    "length": "mi",
                    "mass": "lb",
                    "temperature": "°F",
                    "volume": "gal"
                },
                "version": "2024.1.0",
                "whitelist_external_dirs": []
            })
        
        # Supervisor API endpoints (for add-on testing)
        @self.app.route('/api/supervisor/info', methods=['GET'])
        def supervisor_info():
            """Mock supervisor info"""
            return jsonify({
                "data": {
                    "version": "2024.01.0",
                    "arch": "amd64",
                    "machine": "qemux86-64",
                    "homeassistant": "2024.1.0",
                    "supervisor": "2024.01.0"
                }
            })
        
        # Log all requests for debugging
        @self.app.before_request
        def log_request():
            """Log all incoming requests"""
            logger.info(f"Request: {request.method} {request.path}")
            # Only try to get JSON for requests that might have it
            if request.method in ['POST', 'PUT', 'PATCH'] and request.content_type == 'application/json':
                try:
                    data = request.get_json(silent=True)
                    if data:
                        logger.info(f"Request data: {data}")
                except Exception:
                    pass
    
    def run(self, host='0.0.0.0', port=8123, debug=False):
        """Run the mock API server"""
        logger.info("Starting Mock Home Assistant API server...")
        logger.info(f"Server will be available at http://{host}:{port}")
        
        try:
            self.app.run(host=host, port=port, debug=debug, use_reloader=False)
        except Exception as e:
            logger.error(f"Error running server: {e}")
            sys.exit(1)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Install Flask dependency
    import subprocess
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask'], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Flask dependency installed")
    except subprocess.CalledProcessError:
        logger.warning("Could not install Flask - assuming it's already available")
    
    # Create and run the mock API
    api = MockHomeAssistantAPI()
    api.run()

if __name__ == '__main__':
    main()