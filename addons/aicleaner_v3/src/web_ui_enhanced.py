#!/usr/bin/env python3
"""
AICleaner V3 Enhanced Web UI Module
Provides entity selection capabilities for configuration
"""

import os
import json
import logging
import aiohttp
import asyncio
from datetime import datetime
from aiohttp import web, web_request
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class EnhancedWebUI:
    """Enhanced Web UI handler for AICleaner addon with entity selection"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.web_app = web.Application(middlewares=[self.json_error_middleware])
        self.http_session = None
        self.setup_routes()
    
    @web.middleware
    async def json_error_middleware(self, request, handler):
        """Middleware to ensure API endpoints always return JSON, never HTML errors"""
        try:
            response = await handler(request)
            
            # For API routes, validate that the response is actually JSON
            if request.path.startswith('/api/'):
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('application/json'):
                    logger.warning(f"[WEB_UI] API endpoint {request.path} returned non-JSON content-type: {content_type}")
                    
                    # Try to read and validate the response body
                    try:
                        if hasattr(response, 'text'):
                            body = await response.text()
                        else:
                            body = str(response.body) if response.body else ''
                        
                        # Check if body looks like JSON
                        import json
                        if body:
                            json.loads(body)  # Will raise if not valid JSON
                            logger.info(f"[WEB_UI] Response body is valid JSON despite content-type")
                        else:
                            logger.warning(f"[WEB_UI] Empty response body for {request.path}")
                            
                    except (json.JSONDecodeError, AttributeError, UnicodeDecodeError) as parse_error:
                        logger.error(f"[WEB_UI] Invalid JSON response from {request.path}: {parse_error}")
                        # Return a safe JSON error response
                        return web.json_response({
                            'success': False,
                            'error': 'Invalid JSON response generated',
                            'path': request.path,
                            'original_content_type': content_type
                        }, status=500)
            
            return response
            
        except Exception as e:
            # Only apply JSON error handling to API routes
            if request.path.startswith('/api/'):
                logger.error(f"[WEB_UI] API endpoint error on {request.path}: {type(e).__name__}: {e}")
                
                # Create safe error response with comprehensive error info
                error_response = {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'path': request.path,
                    'method': request.method
                }
                
                # Ensure error response can be JSON serialized
                try:
                    import json
                    json.dumps(error_response)
                    return web.json_response(error_response, status=500)
                except (TypeError, ValueError) as json_error:
                    logger.error(f"[WEB_UI] Error response serialization failed: {json_error}")
                    # Ultra-safe fallback
                    return web.json_response({
                        'success': False,
                        'error': 'Serialization error in error handler',
                        'path': request.path
                    }, status=500)
            else:
                # For non-API routes, let the exception bubble up normally
                raise
    
    def setup_routes(self):
        """Setup web routes"""
        self.web_app.router.add_get('/', self.index)
        self.web_app.router.add_get('/api/status', self.api_status)
        self.web_app.router.add_post('/api/test_generation', self.api_test_generation)
        self.web_app.router.add_get('/api/config', self.api_config)
        self.web_app.router.add_put('/api/config', self.api_update_config)
        self.web_app.router.add_get('/api/entities', self.api_entities)
    
    async def get_http_session(self):
        """Get or create HTTP session for HA API calls"""
        if self.http_session is None or self.http_session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.http_session = aiohttp.ClientSession(timeout=timeout)
        return self.http_session
    
    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
    
    def load_addon_options(self) -> Dict[str, Any]:
        """Load current addon options from /data/options.json"""
        options_file = '/data/options.json'
        if os.path.exists(options_file):
            try:
                with open(options_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading options.json: {e}")
        return {}
    
    def save_addon_options(self, options: Dict[str, Any]) -> bool:
        """Save addon options to /data/options.json"""
        options_file = '/data/options.json'
        try:
            with open(options_file, 'w') as f:
                json.dump(options, f, indent=2)
            logger.info("Options saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving options.json: {e}")
            return False
    
    async def index(self, request: web_request.Request):
        """Serve enhanced main page with entity selection"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Cleaner v3 - Enhanced Configuration</title>
    <style>
        body {
            font-family: system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            border-bottom: 1px solid #eee;
            padding-bottom: 16px;
            margin-bottom: 24px;
        }
        .status-card {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 16px;
            margin: 16px 0;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-connected { background: #28a745; }
        .status-error { background: #dc3545; }
        .status-warning { background: #ffc107; }
        .btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 4px;
        }
        .btn:hover { background: #0056b3; }
        .btn:disabled { background: #6c757d; cursor: not-allowed; }
        .btn-success {
            background: #28a745;
        }
        .btn-success:hover { background: #218838; }
        .config-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .config-item:last-child { border-bottom: none; }
        .log-output {
            background: #2d3748;
            color: #e2e8f0;
            padding: 16px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            max-height: 300px;
            overflow-y: auto;
            margin-top: 16px;
        }
        .form-group {
            margin: 16px 0;
        }
        .form-group label {
            display: block;
            font-weight: bold;
            margin-bottom: 6px;
        }
        .form-group select, .form-group input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
        }
        .entity-config {
            background: #fff;
            border: 2px solid #007bff;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .entity-status {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-left: 8px;
        }
        .entity-valid { background: #d4edda; color: #155724; }
        .entity-invalid { background: #f8d7da; color: #721c24; }
        .validation-message {
            margin-top: 8px;
            padding: 8px;
            border-radius: 4px;
            font-size: 14px;
        }
        .validation-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .validation-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Cleaner v3 - Enhanced Configuration</h1>
            <p>Configure your AICleaner addon with proper entity selection</p>
        </div>
        
        <div class="status-card">
            <h3>System Status</h3>
            <div id="status-content">
                <div>Loading status...</div>
            </div>
        </div>
        
        <div class="entity-config">
            <h3>Entity Configuration</h3>
            <p>Select the camera and todo list entities for Rowan's room:</p>
            
            <div class="form-group">
                <label for="default_camera">Default Camera Entity:</label>
                <select id="default_camera" onchange="validateEntity('camera', this.value)">
                    <option value="">Select a camera...</option>
                </select>
                <span id="camera_status" class="entity-status"></span>
                <div id="camera_validation" class="validation-message" style="display: none;"></div>
            </div>
            
            <div class="form-group">
                <label for="default_todo_list">Default Todo List Entity:</label>
                <select id="default_todo_list" onchange="validateEntity('todo', this.value)">
                    <option value="">Select a todo list...</option>
                </select>
                <span id="todo_status" class="entity-status"></span>
                <div id="todo_validation" class="validation-message" style="display: none;"></div>
            </div>
            
            <button class="btn btn-success" onclick="saveConfiguration()" id="save_btn" disabled>
                Save Configuration
            </button>
        </div>
        
        <div class="status-card">
            <h3>Actions</h3>
            <button class="btn" onclick="testGeneration()">Test AI Generation</button>
            <button class="btn" onclick="refreshStatus()">Refresh Status</button>
            <button class="btn" onclick="loadEntities()">Reload Entities</button>
            <button class="btn" onclick="showConfig()">Show Current Config</button>
        </div>
        
        <div class="status-card" id="config-section" style="display: none;">
            <h3>Current Configuration</h3>
            <div id="config-content"></div>
        </div>
        
        <div class="log-output" id="log-output" style="display: none;">
            <h4>Action Log</h4>
            <div id="log-content"></div>
        </div>
    </div>

    <script>
        let logVisible = false;
        let availableEntities = { cameras: [], todo_lists: [] };
        let validEntities = { camera: false, todo: false };
        
        async function refreshStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateStatusDisplay(data);
            } catch (error) {
                logMessage('Error fetching status: ' + error.message);
            }
        }
        
        function updateStatusDisplay(status) {
            const content = document.getElementById('status-content');
            content.innerHTML = `
                <div class="config-item">
                    <span>Addon Status:</span>
                    <span><span class="status-indicator status-${getStatusClass(status.status)}"></span>${status.status}</span>
                </div>
                <div class="config-item">
                    <span>MQTT Connection:</span>
                    <span><span class="status-indicator status-${status.mqtt_connected ? 'connected' : 'error'}"></span>${status.mqtt_connected ? 'Connected' : 'Disconnected'}</span>
                </div>
                <div class="config-item">
                    <span>AI Requests:</span>
                    <span>${status.ai_response_count || 0}</span>
                </div>
                <div class="config-item">
                    <span>Last Request:</span>
                    <span>${status.last_ai_request || 'Never'}</span>
                </div>
            `;
        }
        
        function getStatusClass(status) {
            if (status === 'connected' || status === 'idle') return 'connected';
            if (status === 'error') return 'error';
            return 'warning';
        }
        
        async function loadEntities() {
            logMessage('Loading available entities...');
            try {
                const response = await fetch('/api/entities');
                const data = await response.json();
                
                if (data.success) {
                    availableEntities = data;
                    populateEntityDropdowns();
                    logMessage(`✅ Loaded ${data.cameras.length} cameras and ${data.todo_lists.length} todo lists`);
                } else {
                    logMessage('❌ Failed to load entities: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                logMessage('❌ Error loading entities: ' + error.message);
            }
        }
        
        function populateEntityDropdowns() {
            const cameraSelect = document.getElementById('default_camera');
            const todoSelect = document.getElementById('default_todo_list');
            
            // Clear existing options except the first
            cameraSelect.innerHTML = '<option value="">Select a camera...</option>';
            todoSelect.innerHTML = '<option value="">Select a todo list...</option>';
            
            // Populate cameras
            availableEntities.cameras.forEach(camera => {
                const option = document.createElement('option');
                option.value = camera.entity_id;
                option.textContent = `${camera.friendly_name} (${camera.entity_id})`;
                cameraSelect.appendChild(option);
            });
            
            // Populate todo lists
            availableEntities.todo_lists.forEach(todo => {
                const option = document.createElement('option');
                option.value = todo.entity_id;
                option.textContent = `${todo.friendly_name} (${todo.entity_id})`;
                todoSelect.appendChild(option);
            });
            
            // Load current configuration and select values
            loadCurrentConfiguration();
        }
        
        async function loadCurrentConfiguration() {
            try {
                const response = await fetch('/api/config');
                const data = await response.json();
                
                if (data.default_camera) {
                    document.getElementById('default_camera').value = data.default_camera;
                    validateEntity('camera', data.default_camera);
                }
                
                if (data.default_todo_list) {
                    document.getElementById('default_todo_list').value = data.default_todo_list;
                    validateEntity('todo', data.default_todo_list);
                }
                
            } catch (error) {
                logMessage('Error loading current configuration: ' + error.message);
            }
        }
        
        function validateEntity(type, entityId) {
            const statusElement = document.getElementById(type + '_status');
            const validationElement = document.getElementById(type + '_validation');
            
            if (!entityId) {
                statusElement.textContent = '';
                statusElement.className = 'entity-status';
                validationElement.style.display = 'none';
                validEntities[type] = false;
                updateSaveButton();
                return;
            }
            
            // Check if entity exists in available entities
            const entities = type === 'camera' ? availableEntities.cameras : availableEntities.todo_lists;
            const found = entities.find(e => e.entity_id === entityId);
            
            if (found) {
                statusElement.textContent = '✅ Valid';
                statusElement.className = 'entity-status entity-valid';
                validationElement.innerHTML = `Entity found: ${found.friendly_name}`;
                validationElement.className = 'validation-message validation-success';
                validationElement.style.display = 'block';
                validEntities[type] = true;
            } else {
                statusElement.textContent = '❌ Invalid';
                statusElement.className = 'entity-status entity-invalid';
                validationElement.innerHTML = `Entity "${entityId}" not found in Home Assistant`;
                validationElement.className = 'validation-message validation-error';
                validationElement.style.display = 'block';
                validEntities[type] = false;
            }
            
            updateSaveButton();
        }
        
        function updateSaveButton() {
            const saveBtn = document.getElementById('save_btn');
            const hasValidCamera = validEntities.camera;
            const hasValidTodo = validEntities.todo;
            
            if (hasValidCamera && hasValidTodo) {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save Configuration';
            } else {
                saveBtn.disabled = true;
                const missing = [];
                if (!hasValidCamera) missing.push('camera');
                if (!hasValidTodo) missing.push('todo list');
                saveBtn.textContent = `Select valid ${missing.join(' and ')} first`;
            }
        }
        
        async function saveConfiguration() {
            const cameraValue = document.getElementById('default_camera').value;
            const todoValue = document.getElementById('default_todo_list').value;
            
            if (!validEntities.camera || !validEntities.todo) {
                logMessage('❌ Cannot save: Invalid entities selected');
                return;
            }
            
            logMessage('Saving configuration...');
            
            try {
                const response = await fetch('/api/config', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        default_camera: cameraValue,
                        default_todo_list: todoValue
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    logMessage('✅ Configuration saved successfully!');
                    logMessage(`Camera: ${cameraValue}`);
                    logMessage(`Todo List: ${todoValue}`);
                    
                    // Refresh status to show updated configuration
                    setTimeout(refreshStatus, 1000);
                } else {
                    logMessage('❌ Failed to save configuration: ' + (result.error || 'Unknown error'));
                }
                
            } catch (error) {
                logMessage('❌ Error saving configuration: ' + error.message);
            }
        }
        
        async function testGeneration() {
            logMessage('Testing AI generation...');
            try {
                const response = await fetch('/api/test_generation', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    logMessage('✅ AI generation test successful');
                    refreshStatus();
                } else {
                    logMessage('❌ AI generation test failed: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                logMessage('❌ Error testing generation: ' + error.message);
            }
        }
        
        async function showConfig() {
            try {
                const response = await fetch('/api/config');
                const data = await response.json();
                const configContent = document.getElementById('config-content');
                const configSection = document.getElementById('config-section');
                
                configContent.innerHTML = Object.entries(data)
                    .map(([key, value]) => `
                        <div class="config-item">
                            <span><strong>${key}:</strong></span>
                            <span>${typeof value === 'string' && key.includes('password') ? '***' : JSON.stringify(value)}</span>
                        </div>
                    `).join('');
                
                configSection.style.display = configSection.style.display === 'none' ? 'block' : 'none';
            } catch (error) {
                logMessage('Error loading configuration: ' + error.message);
            }
        }
        
        function logMessage(message) {
            const logOutput = document.getElementById('log-output');
            const logContent = document.getElementById('log-content');
            
            if (!logVisible) {
                logOutput.style.display = 'block';
                logVisible = true;
            }
            
            const timestamp = new Date().toLocaleTimeString();
            logContent.innerHTML += `<div>[${timestamp}] ${message}</div>`;
            logContent.scrollTop = logContent.scrollHeight;
        }
        
        // Initialize the interface
        refreshStatus();
        loadEntities();
        setInterval(refreshStatus, 10000);
    </script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
    async def api_status(self, request: web_request.Request):
        """Enhanced API endpoint for status information"""
        try:
            status_data = {
                'status': getattr(self.app, 'status', 'unknown'),
                'enabled': getattr(self.app, 'enabled', True),
                'mqtt_connected': getattr(self.app, 'mqtt_client', None) is not None,
                'ai_response_count': getattr(self.app, 'ai_response_count', 0),
                'last_ai_request': getattr(self.app, 'last_ai_request', None),
                'device_id': os.getenv('DEVICE_ID', 'aicleaner_v3'),
                'version': 'enhanced-1.0.0',
                'supervisor_token_available': bool(os.getenv('SUPERVISOR_TOKEN'))
            }
            return web.json_response(status_data)
        except Exception as e:
            # Always return JSON response
            return web.json_response({'error': str(e), 'success': False}, status=500)
    
    async def api_test_generation(self, request: web_request.Request):
        """API endpoint to test AI generation with enhanced HA API testing"""
        try:
            # Test HA API connectivity with better error handling
            supervisor_token = os.getenv('SUPERVISOR_TOKEN')
            ha_accessible = False
            ha_error = None
            
            if supervisor_token:
                try:
                    session = await self.get_http_session()
                    headers = {'Authorization': f'Bearer {supervisor_token}'}
                    async with session.get('http://supervisor/core/api/config', headers=headers) as response:
                        ha_accessible = response.status == 200
                        if not ha_accessible:
                            ha_error = f"HTTP {response.status}: {await response.text()}"
                except Exception as e:
                    ha_error = str(e)
            else:
                ha_error = "SUPERVISOR_TOKEN not available"
            
            return web.json_response({
                'success': True,
                'result': 'Enhanced UI test completed',
                'ha_api_accessible': ha_accessible,
                'ha_error': ha_error,
                'supervisor_token_available': bool(supervisor_token),
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error in api_test_generation: {e}")
            return web.json_response({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    async def api_config(self, request: web_request.Request):
        """Enhanced API endpoint to get configuration including addon options"""
        try:
            # Load addon options
            addon_options = self.load_addon_options()
            
            # Merge with environment variables
            config_data = {
                'mqtt_host': os.getenv('MQTT_HOST', addon_options.get('mqtt_host', 'localhost')),
                'mqtt_port': os.getenv('MQTT_PORT', str(addon_options.get('mqtt_port', 1883))),
                'device_id': os.getenv('DEVICE_ID', 'aicleaner_v3'),
                'log_level': os.getenv('LOG_LEVEL', addon_options.get('log_level', 'info')),
                'debug_mode': os.getenv('DEBUG_MODE', str(addon_options.get('debug_mode', False))),
                'default_camera': addon_options.get('default_camera', ''),
                'default_todo_list': addon_options.get('default_todo_list', ''),
                'success': True
            }
            return web.json_response(config_data)
        except Exception as e:
            logger.error(f"Error in api_config: {e}")
            # Always return JSON response
            return web.json_response({'error': str(e), 'success': False}, status=500)
    
    async def api_update_config(self, request: web_request.Request):
        """API endpoint to update configuration"""
        try:
            data = await request.json()
            
            # Load current options
            current_options = self.load_addon_options()
            
            # Update with new values
            if 'default_camera' in data:
                current_options['default_camera'] = data['default_camera']
            if 'default_todo_list' in data:
                current_options['default_todo_list'] = data['default_todo_list']
            
            # Save updated options
            if self.save_addon_options(current_options):
                return web.json_response({
                    'success': True,
                    'message': 'Configuration updated successfully',
                    'updated_fields': list(data.keys())
                })
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Failed to save configuration'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error in api_update_config: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    async def get_homeassistant_entities(self) -> Dict[str, Any]:
        """Query Home Assistant API for all entities with enhanced error handling"""
        supervisor_token = os.getenv('SUPERVISOR_TOKEN')
        if not supervisor_token:
            raise Exception("SUPERVISOR_TOKEN not available - ensure hassio_api: true in config.yaml")
        
        headers = {
            'Authorization': f'Bearer {supervisor_token}',
            'Content-Type': 'application/json'
        }
        
        session = await self.get_http_session()
        
        try:
            async with session.get('http://supervisor/core/api/states', headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 401:
                    raise Exception("HA API authentication failed - invalid SUPERVISOR_TOKEN")
                elif response.status == 403:
                    raise Exception("HA API access forbidden - check hassio_api permissions")
                else:
                    error_text = await response.text()
                    raise Exception(f"HA API call failed: HTTP {response.status} - {error_text}")
        except aiohttp.ClientConnectorError as e:
            raise Exception(f"Cannot connect to Home Assistant API: {e}")
        except aiohttp.ServerTimeoutError as e:
            raise Exception(f"Home Assistant API timeout: {e}")
        except asyncio.TimeoutError as e:
            raise Exception(f"Home Assistant API request timeout: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from Home Assistant API: {e}")
    
    async def api_entities(self, request: web_request.Request):
        """API endpoint to get Home Assistant entities with real HA API calls"""
        try:
            logger.info("[WEB_UI] Starting entity fetch from Home Assistant API")
            
            # Get all entities from Home Assistant
            all_entities = await self.get_homeassistant_entities()
            
            if not isinstance(all_entities, list):
                logger.error(f"[WEB_UI] Invalid entity data type: {type(all_entities)}")
                return web.json_response({
                    'cameras': [],
                    'todo_lists': [],
                    'success': False,
                    'error': 'Invalid entity data format from Home Assistant API',
                    'total_entities': 0
                }, status=500)
            
            logger.info(f"[WEB_UI] Retrieved {len(all_entities)} entities from HA API")
            
            # Filter for cameras and todo lists
            cameras = []
            todo_lists = []
            
            for entity in all_entities:
                try:
                    entity_id = entity.get('entity_id', '')
                    if not entity_id:
                        continue
                        
                    domain = entity_id.split('.')[0] if '.' in entity_id else ''
                    
                    if domain == 'camera':
                        cameras.append({
                            'entity_id': entity_id,
                            'friendly_name': entity.get('attributes', {}).get('friendly_name', entity_id),
                            'state': entity.get('state', 'unknown')
                        })
                    elif domain == 'todo':
                        todo_lists.append({
                            'entity_id': entity_id,
                            'friendly_name': entity.get('attributes', {}).get('friendly_name', entity_id),
                            'state': entity.get('state', 'unknown')
                        })
                except Exception as entity_error:
                    logger.warning(f"[WEB_UI] Error processing entity {entity.get('entity_id', 'unknown')}: {entity_error}")
                    continue
            
            logger.info(f"[WEB_UI] Filtered entities: {len(cameras)} cameras, {len(todo_lists)} todo lists")
            
            # Ensure we always return valid JSON structure
            response_data = {
                'cameras': cameras,
                'todo_lists': todo_lists,
                'success': True,
                'total_entities': len(all_entities),
                'filtered_count': {
                    'cameras': len(cameras),
                    'todo_lists': len(todo_lists)
                }
            }
            
            # Validate response can be JSON serialized
            try:
                import json
                json.dumps(response_data)
            except (TypeError, ValueError) as json_error:
                logger.error(f"[WEB_UI] Response data is not JSON serializable: {json_error}")
                return web.json_response({
                    'cameras': [],
                    'todo_lists': [],
                    'success': False,
                    'error': 'Response data serialization error',
                    'total_entities': 0
                }, status=500)
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"[WEB_UI] Critical error in api_entities: {type(e).__name__}: {e}")
            # Always return properly formatted JSON, never let exceptions create HTML responses
            error_response = {
                'cameras': [],
                'todo_lists': [],
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'total_entities': 0
            }
            
            # Ensure error response is JSON serializable
            try:
                import json
                json.dumps(error_response)
                return web.json_response(error_response, status=500)
            except Exception as json_error:
                logger.error(f"[WEB_UI] Even error response failed JSON serialization: {json_error}")
                # Last resort - return minimal safe JSON
                return web.json_response({
                    'success': False,
                    'error': 'Critical JSON serialization error',
                    'cameras': [],
                    'todo_lists': [],
                    'total_entities': 0
                }, status=500)

    async def start_server(self, host='0.0.0.0', port=8080):
        """Start the enhanced web server"""
        logger.info(f"Starting enhanced web UI server on {host}:{port}")
        runner = web.AppRunner(self.web_app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info("Enhanced web UI server started successfully")
    
    async def shutdown(self):
        """Cleanup resources on shutdown"""
        await self.cleanup_session()
        logger.info("Enhanced web UI resources cleaned up")