#!/usr/bin/env python3
"""
AICleaner V3 Web UI Module
Provides the web interface for the Home Assistant addon
"""

import os
import json
import logging
import aiohttp
from datetime import datetime
from aiohttp import web, web_request
from typing import Dict, Any, List
from validation import InputValidator, ValidationError
from error_handler import ErrorHandler, NotificationManager, AICleaenerError, ErrorCategory, ErrorSeverity, error_handler
from config_validator import ConfigValidator

logger = logging.getLogger(__name__)

class WebUI:
    """Web UI handler for AICleaner addon"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.web_app = web.Application()
        self.notification_manager = NotificationManager()
        self.error_handler = ErrorHandler(self.notification_manager)
        self.config_validator = ConfigValidator()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup web routes"""
        self.web_app.router.add_get('/', self.index)
        self.web_app.router.add_get('/api/status', self.api_status)
        self.web_app.router.add_post('/api/test_generation', self.api_test_generation)
        self.web_app.router.add_get('/api/config', self.api_config)
        self.web_app.router.add_get('/api/entities', self.api_entities)
        self.web_app.router.add_get('/api/zones', self.api_zones)
        self.web_app.router.add_post('/api/zones', self.api_save_zones)
        self.web_app.router.add_get('/api/health', self.api_health)
        self.web_app.router.add_get('/api/errors', self.api_errors)
        self.web_app.router.add_get('/api/notifications', self.api_notifications)
        self.web_app.router.add_get('/api/validate_config', self.api_validate_config)
    
    async def index(self, request: web_request.Request):
        """Serve main page"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Cleaner v3</title>
    <style>
        body {
            font-family: system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 800px;
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
        .zone-form {
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 16px;
            margin: 16px 0;
            background: #fff;
        }
        .form-row {
            display: flex;
            gap: 16px;
            margin: 12px 0;
            align-items: center;
        }
        .form-group {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        .form-group label {
            font-weight: bold;
            margin-bottom: 4px;
            font-size: 14px;
        }
        .form-group input, .form-group select, .form-group textarea {
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
        }
        .form-group textarea {
            min-height: 60px;
            resize: vertical;
        }
        .zone-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #eee;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }
        .btn-danger:hover { background: #c82333; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Cleaner v3</h1>
            <p>Home Assistant Add-on for AI-powered content generation</p>
        </div>
        
        <div class="status-card">
            <h3>System Status</h3>
            <div id="status-content">
                <div>Loading status...</div>
            </div>
        </div>
        
        <div class="status-card">
            <h3>Actions</h3>
            <button class="btn" onclick="testGeneration()">Test AI Generation</button>
            <button class="btn" onclick="refreshStatus()">Refresh Status</button>
            <button class="btn" onclick="showConfig()">Show Configuration</button>
            <button class="btn" onclick="showZoneConfig()">Configure Zones</button>
            <button class="btn" onclick="validateConfiguration()">Validate Configuration</button>
        </div>
        
        <div class="status-card" id="config-section" style="display: none;">
            <h3>Configuration</h3>
            <div id="config-content"></div>
        </div>
        
        <div class="status-card" id="zone-config-section" style="display: none;">
            <h3>Zone Configuration</h3>
            <div id="zone-config-content">
                <div id="zones-list"></div>
                <button class="btn" onclick="addZone()">Add New Zone</button>
                <button class="btn" onclick="saveZones()">Save Zones</button>
            </div>
        </div>
        
        <div class="log-output" id="log-output" style="display: none;">
            <h4>Action Log</h4>
            <div id="log-content"></div>
        </div>
    </div>

    <script>
        let logVisible = false;
        
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
                    <span>Core Service:</span>
                    <span><span class="status-indicator status-${status.core_service_health ? 'connected' : 'error'}"></span>${status.core_service_health ? 'Available' : 'Unavailable'}</span>
                </div>
                <div class="config-item">
                    <span>AI Requests:</span>
                    <span>${status.ai_response_count}</span>
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
        
        // Zone configuration variables
        let availableEntities = { cameras: [], todo_lists: [] };
        let currentZones = [];
        
        async function showZoneConfig() {
            try {
                // Fetch available entities
                const entitiesResponse = await fetch('/api/entities');
                const entitiesData = await entitiesResponse.json();
                availableEntities = entitiesData;
                
                // Fetch current zones
                const zonesResponse = await fetch('/api/zones');
                const zonesData = await zonesResponse.json();
                currentZones = zonesData.zones || [];
                
                const zoneSection = document.getElementById('zone-config-section');
                zoneSection.style.display = zoneSection.style.display === 'none' ? 'block' : 'none';
                
                if (zoneSection.style.display === 'block') {
                    renderZones();
                }
                
            } catch (error) {
                logMessage('Error loading zone configuration: ' + error.message);
            }
        }
        
        function renderZones() {
            const zonesList = document.getElementById('zones-list');
            zonesList.innerHTML = '';
            
            currentZones.forEach((zone, index) => {
                const zoneDiv = document.createElement('div');
                zoneDiv.className = 'zone-form';
                zoneDiv.innerHTML = createZoneFormHTML(zone, index);
                zonesList.appendChild(zoneDiv);
            });
        }
        
        function createZoneFormHTML(zone, index) {
            const cameraOptions = availableEntities.cameras.map(cam => 
                `<option value="${cam.entity_id}" ${zone.camera_entity === cam.entity_id ? 'selected' : ''}>${cam.friendly_name}</option>`
            ).join('');
            
            const todoOptions = availableEntities.todo_lists.map(todo => 
                `<option value="${todo.entity_id}" ${zone.todo_list_entity === todo.entity_id ? 'selected' : ''}>${todo.friendly_name}</option>`
            ).join('');
            
            const ignoreRulesText = zone.ignore_rules ? zone.ignore_rules.join('\\n') : '';
            
            return `
                <div class="zone-header">
                    <h4>Zone ${index + 1}</h4>
                    <button class="btn-danger" onclick="removeZone(${index})">Remove</button>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Zone Name</label>
                        <input type="text" value="${zone.name || ''}" onchange="updateZone(${index}, 'name', this.value)">
                    </div>
                    <div class="form-group">
                        <label>Purpose</label>
                        <input type="text" value="${zone.purpose || ''}" onchange="updateZone(${index}, 'purpose', this.value)">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Camera Entity</label>
                        <select onchange="updateZone(${index}, 'camera_entity', this.value)">
                            <option value="">Select Camera</option>
                            ${cameraOptions}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Todo List Entity</label>
                        <select onchange="updateZone(${index}, 'todo_list_entity', this.value)">
                            <option value="">Select Todo List</option>
                            ${todoOptions}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Check Interval (minutes)</label>
                        <input type="number" value="${zone.interval_minutes || 60}" min="1" max="1440" onchange="updateZone(${index}, 'interval_minutes', parseInt(this.value))">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Ignore Rules (one per line)</label>
                        <textarea onchange="updateZone(${index}, 'ignore_rules', this.value.split('\\n').filter(r => r.trim()))">${ignoreRulesText}</textarea>
                    </div>
                </div>
            `;
        }
        
        function addZone() {
            const newZone = {
                name: 'New Zone',
                camera_entity: '',
                todo_list_entity: '',
                purpose: '',
                interval_minutes: 60,
                ignore_rules: []
            };
            currentZones.push(newZone);
            renderZones();
            logMessage('Added new zone');
        }
        
        function removeZone(index) {
            if (confirm('Are you sure you want to remove this zone?')) {
                currentZones.splice(index, 1);
                renderZones();
                logMessage('Removed zone');
            }
        }
        
        function updateZone(index, field, value) {
            currentZones[index][field] = value;
            logMessage(`Updated zone ${index + 1}: ${field} = ${value}`);
        }
        
        async function saveZones() {
            try {
                const response = await fetch('/api/zones', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ zones: currentZones })
                });
                
                const result = await response.json();
                if (result.success) {
                    logMessage('✅ Zones saved successfully');
                } else {
                    logMessage('❌ Failed to save zones: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                logMessage('❌ Error saving zones: ' + error.message);
            }
        }
        
        async function validateConfiguration() {
            logMessage('Validating addon configuration...');
            try {
                const response = await fetch('/api/validate_config');
                const data = await response.json();
                
                if (data.overall_status === 'valid') {
                    logMessage('✅ Configuration validation passed');
                } else if (data.overall_status === 'warnings') {
                    logMessage('⚠️ Configuration validation passed with warnings');
                    
                    // Show warnings
                    for (const [category, validation] of Object.entries(data.validations)) {
                        if (validation.warnings && validation.warnings.length > 0) {
                            validation.warnings.forEach(warning => {
                                logMessage(`⚠️ ${category}: ${warning}`);
                            });
                        }
                        if (validation.recommendations && validation.recommendations.length > 0) {
                            validation.recommendations.forEach(rec => {
                                logMessage(`💡 ${category}: ${rec}`);
                            });
                        }
                    }
                } else if (data.overall_status === 'invalid') {
                    logMessage('❌ Configuration validation failed');
                    
                    // Show errors
                    for (const [category, validation] of Object.entries(data.validations)) {
                        if (validation.errors && validation.errors.length > 0) {
                            validation.errors.forEach(error => {
                                logMessage(`❌ ${category}: ${error}`);
                            });
                        }
                        if (validation.error) {
                            logMessage(`❌ ${category}: ${validation.error}`);
                        }
                    }
                } else {
                    logMessage(`❌ Configuration validation error: ${data.error || 'Unknown error'}`);
                }
                
            } catch (error) {
                logMessage('❌ Error validating configuration: ' + error.message);
            }
        }
        
        // Auto-refresh status every 10 seconds
        refreshStatus();
        setInterval(refreshStatus, 10000);
    </script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
    async def api_status(self, request: web_request.Request):
        """API endpoint for status information"""
        try:
            status_data = {
                'status': self.app.status,
                'enabled': self.app.enabled,
                'mqtt_connected': self.app.mqtt_client and self.app.mqtt_client.is_connected(),
                'core_service_health': await self.app.check_core_service_health(),
                'ai_response_count': self.app.ai_response_count,
                'last_ai_request': self.app.last_ai_request,
                'device_id': os.getenv('DEVICE_ID', 'aicleaner_v3'),
                'version': 'dev-0.1.0'
            }
            return web.json_response(status_data)
        except Exception as e:
            logger.error(f"Error in api_status: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_test_generation(self, request: web_request.Request):
        """API endpoint to test AI generation"""
        try:
            result = await self.app.call_core_service('/v1/generate', {
                'prompt': 'Hello! This is a test from the AI Cleaner addon.',
                'max_tokens': 50
            })
            
            if result:
                return web.json_response({
                    'success': True,
                    'result': result
                })
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Core service call failed'
                })
        except Exception as e:
            logger.error(f"Error in api_test_generation: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def api_config(self, request: web_request.Request):
        """API endpoint to get configuration"""
        try:
            config_data = {
                'mqtt_host': os.getenv('MQTT_HOST', 'localhost'),
                'mqtt_port': os.getenv('MQTT_PORT', '1883'),
                'core_service_url': os.getenv('CORE_SERVICE_URL', 'http://localhost:8000'),
                'device_id': os.getenv('DEVICE_ID', 'aicleaner_v3'),
                'log_level': os.getenv('LOG_LEVEL', 'info'),
                'debug_mode': os.getenv('DEBUG_MODE', 'true')
            }
            return web.json_response(config_data)
        except Exception as e:
            logger.error(f"Error in api_config: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_entities(self, request: web_request.Request):
        """API endpoint to get Home Assistant entities for dropdowns"""
        try:
            entities = await self.fetch_ha_entities()
            return web.json_response({
                'cameras': entities.get('cameras', []),
                'todo_lists': entities.get('todo_lists', []),
                'success': True
            })
        except Exception as e:
            logger.error(f"Error fetching entities: {e}")
            return web.json_response({
                'cameras': [],
                'todo_lists': [],
                'success': False,
                'error': str(e)
            })
    
    async def api_zones(self, request: web_request.Request):
        """API endpoint to get current zone configuration"""
        try:
            zones_file = '/data/zones.json'
            if os.path.exists(zones_file):
                with open(zones_file, 'r') as f:
                    zones = json.load(f)
            else:
                zones = []
            
            return web.json_response({
                'zones': zones,
                'success': True
            })
        except Exception as e:
            logger.error(f"Error loading zones: {e}")
            return web.json_response({
                'zones': [],
                'success': False,
                'error': str(e)
            })
    
    @error_handler(category=ErrorCategory.CONFIGURATION, severity=ErrorSeverity.MEDIUM)
    async def api_save_zones(self, request: web_request.Request):
        """API endpoint to save zone configuration with validation"""
        try:
            # Parse and validate request data
            try:
                data = await request.json()
            except json.JSONDecodeError as e:
                raise AICleaenerError(
                    "Invalid JSON in request body",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.LOW,
                    user_message="Invalid configuration data format"
                )
            
            if not isinstance(data, dict):
                raise AICleaenerError(
                    "Request data must be a JSON object",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.LOW
                )
            
            zones_data = data.get('zones', [])
            
            # Comprehensive validation
            try:
                validated_zones = InputValidator.validate_zones_list(zones_data)
                logger.info(f"Validated {len(validated_zones)} zones successfully")
            except ValidationError as e:
                raise AICleaenerError(
                    f"Zone validation failed: {str(e)}",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.LOW,
                    user_message=str(e)
                )
            
            # Save validated zones
            zones_file = '/data/zones.json'
            try:
                # Create backup of existing config
                if os.path.exists(zones_file):
                    backup_file = f"{zones_file}.backup"
                    with open(zones_file, 'r') as src, open(backup_file, 'w') as dst:
                        dst.write(src.read())
                
                # Save new configuration
                with open(zones_file, 'w') as f:
                    json.dump(validated_zones, f, indent=2)
                    
                logger.info(f"Saved {len(validated_zones)} validated zones to configuration")
                
            except IOError as e:
                raise AICleaenerError(
                    f"Failed to save zones configuration: {str(e)}",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.HIGH,
                    user_message="Unable to save configuration. Check file permissions."
                )
            
            # Update dashboard automatically
            dashboard_success = False
            dashboard_error = None
            
            try:
                dashboard_success = await self.app.dashboard_manager.setup_dashboard(validated_zones)
                if dashboard_success:
                    logger.info("Dashboard updated automatically after zone save")
                    
                    # Send success notification
                    await self.notification_manager.send_notification(
                        title="Configuration Updated",
                        message=f"Successfully saved {len(validated_zones)} zones and updated dashboard",
                        severity=ErrorSeverity.LOW
                    )
                else:
                    logger.warning("Dashboard update failed after zone save")
                    dashboard_error = "Dashboard update failed"
                    
            except Exception as dashboard_err:
                dashboard_error = str(dashboard_err)
                logger.error(f"Error updating dashboard: {dashboard_err}")
                
                # Don't fail the entire operation, just warn
                await self.notification_manager.send_notification(
                    title="Dashboard Update Failed", 
                    message="Zones saved successfully, but dashboard update failed. Check logs for details.",
                    severity=ErrorSeverity.MEDIUM
                )
            
            response_data = {
                'success': True,
                'message': f'Saved {len(validated_zones)} zones successfully',
                'dashboard_updated': dashboard_success,
                'zones_count': len(validated_zones),
                'validation_passed': True
            }
            
            if dashboard_error:
                response_data['dashboard_error'] = dashboard_error
            
            return web.json_response(response_data)
            
        except AICleaenerError:
            # Re-raise AICleaner errors to be handled by decorator
            raise
        except Exception as e:
            # Convert unexpected errors to AICleaner errors
            raise AICleaenerError(
                f"Unexpected error saving zones: {str(e)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                user_message="An unexpected error occurred while saving zones"
            )
    
    @error_handler(category=ErrorCategory.API, severity=ErrorSeverity.MEDIUM)
    async def fetch_ha_entities(self) -> Dict[str, List[Dict]]:
        """Fetch available entities from Home Assistant API with error handling"""
        try:
            hassio_token = os.getenv('HASSIO_TOKEN')
            if not hassio_token:
                logger.warning("HASSIO_TOKEN not available, using mock entities")
                raise AICleaenerError(
                    "HASSIO_TOKEN not configured",
                    category=ErrorCategory.CONFIGURATION,
                    severity=ErrorSeverity.MEDIUM,
                    user_message="Home Assistant API token not available. Using sample data."
                )
            
            headers = {
                'Authorization': f'Bearer {hassio_token}',
                'Content-Type': 'application/json'
            }
            
            # Try to get entities from Home Assistant API
            ha_url = os.getenv('HA_URL', 'http://supervisor/core')
            api_url = f"{ha_url}/api/states"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(api_url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            states = await response.json()
                            entities = self.parse_entities_from_states(states)
                            logger.info(f"Successfully fetched {len(entities.get('cameras', []))} cameras and {len(entities.get('todo_lists', []))} todo lists")
                            return entities
                        elif response.status == 401:
                            raise AICleaenerError(
                                f"Unauthorized access to Home Assistant API (status {response.status})",
                                category=ErrorCategory.PERMISSION,
                                severity=ErrorSeverity.HIGH,
                                user_message="Authentication failed. Check addon permissions."
                            )
                        else:
                            raise AICleaenerError(
                                f"Home Assistant API error (status {response.status})",
                                category=ErrorCategory.API,
                                severity=ErrorSeverity.MEDIUM,
                                user_message="Unable to fetch entities from Home Assistant."
                            )
                except aiohttp.ClientTimeout:
                    raise AICleaenerError(
                        "Timeout connecting to Home Assistant API",
                        category=ErrorCategory.NETWORK,
                        severity=ErrorSeverity.MEDIUM,
                        user_message="Connection timeout. Check network connectivity."
                    )
                except aiohttp.ClientError as e:
                    raise AICleaenerError(
                        f"Network error connecting to Home Assistant API: {str(e)}",
                        category=ErrorCategory.NETWORK,
                        severity=ErrorSeverity.MEDIUM,
                        user_message="Network error. Check connectivity and try again."
                    )
            
        except AICleaenerError:
            # For known errors, return mock entities and let error handler log/notify
            return self.get_mock_entities()
        except Exception as e:
            # For unexpected errors, wrap and re-raise
            raise AICleaenerError(
                f"Unexpected error fetching entities: {str(e)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                user_message="An unexpected error occurred while fetching entities."
            )
    
    def parse_entities_from_states(self, states: List[Dict]) -> Dict[str, List[Dict]]:
        """Parse entities from Home Assistant states"""
        cameras = []
        todo_lists = []
        
        for state in states:
            entity_id = state.get('entity_id', '')
            attributes = state.get('attributes', {})
            friendly_name = attributes.get('friendly_name', entity_id)
            
            if entity_id.startswith('camera.'):
                cameras.append({
                    'entity_id': entity_id,
                    'friendly_name': friendly_name,
                    'state': state.get('state', 'unknown')
                })
            elif entity_id.startswith('todo.'):
                todo_lists.append({
                    'entity_id': entity_id,
                    'friendly_name': friendly_name,
                    'state': state.get('state', 'unknown')
                })
        
        return {
            'cameras': cameras,
            'todo_lists': todo_lists
        }
    
    def get_mock_entities(self) -> Dict[str, List[Dict]]:
        """Return mock entities for testing when HA API is unavailable"""
        return {
            'cameras': [
                {'entity_id': 'camera.living_room', 'friendly_name': 'Living Room Camera', 'state': 'idle'},
                {'entity_id': 'camera.kitchen', 'friendly_name': 'Kitchen Camera', 'state': 'idle'},
                {'entity_id': 'camera.bedroom', 'friendly_name': 'Bedroom Camera', 'state': 'idle'},
                {'entity_id': 'camera.front_door', 'friendly_name': 'Front Door Camera', 'state': 'idle'}
            ],
            'todo_lists': [
                {'entity_id': 'todo.living_room', 'friendly_name': 'Living Room Tasks', 'state': '3'},
                {'entity_id': 'todo.kitchen', 'friendly_name': 'Kitchen Tasks', 'state': '1'},
                {'entity_id': 'todo.bedroom', 'friendly_name': 'Bedroom Tasks', 'state': '0'},
                {'entity_id': 'todo.household', 'friendly_name': 'Household Tasks', 'state': '5'}
            ]
        }
    
    async def api_health(self, request: web_request.Request):
        """API endpoint for system health monitoring"""
        try:
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'components': {
                    'addon': {
                        'status': self.app.status,
                        'enabled': self.app.enabled
                    },
                    'mqtt': {
                        'connected': self.app.mqtt_client and self.app.mqtt_client.is_connected()
                    },
                    'core_service': {
                        'available': await self.app.check_core_service_health()
                    },
                    'error_handler': {
                        'active': self.error_handler is not None,
                        'stats': self.error_handler.get_error_stats() if self.error_handler else None
                    }
                },
                'metrics': {
                    'ai_requests': self.app.ai_response_count,
                    'last_request': self.app.last_ai_request
                }
            }
            
            # Determine overall health
            unhealthy_components = []
            if not health_data['components']['mqtt']['connected']:
                unhealthy_components.append('mqtt')
            if not health_data['components']['core_service']['available']:
                unhealthy_components.append('core_service')
            
            if len(unhealthy_components) > 0:
                health_data['status'] = 'degraded' if len(unhealthy_components) == 1 else 'unhealthy'
                health_data['issues'] = unhealthy_components
            
            return web.json_response(health_data)
            
        except Exception as e:
            logger.error(f"Error in api_health: {e}")
            return web.json_response({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, status=500)
    
    async def api_errors(self, request: web_request.Request):
        """API endpoint for recent error information"""
        try:
            limit = int(request.query.get('limit', 20))
            limit = min(limit, 100)  # Cap at 100
            
            error_data = {
                'errors': [],
                'stats': {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if self.error_handler:
                error_data['stats'] = self.error_handler.get_error_stats()
                
                # Try to read recent errors from file
                try:
                    error_log_file = '/data/error_log.json'
                    if os.path.exists(error_log_file):
                        with open(error_log_file, 'r') as f:
                            all_errors = json.load(f)
                            error_data['errors'] = all_errors[-limit:] if all_errors else []
                except Exception as e:
                    logger.warning(f"Could not read error log file: {e}")
            
            return web.json_response(error_data)
            
        except Exception as e:
            logger.error(f"Error in api_errors: {e}")
            return web.json_response({
                'errors': [],
                'stats': {},
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, status=500)
    
    async def api_notifications(self, request: web_request.Request):
        """API endpoint for recent notification history"""
        try:
            limit = int(request.query.get('limit', 10))
            limit = min(limit, 50)  # Cap at 50
            
            notification_data = {
                'notifications': [],
                'count': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if self.notification_manager:
                notifications = self.notification_manager.get_recent_notifications(limit)
                notification_data['notifications'] = notifications
                notification_data['count'] = len(notifications)
            
            return web.json_response(notification_data)
            
        except Exception as e:
            logger.error(f"Error in api_notifications: {e}")
            return web.json_response({
                'notifications': [],
                'count': 0,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, status=500)
    
    async def api_validate_config(self, request: web_request.Request):
        """API endpoint for comprehensive configuration validation"""
        try:
            validation_report = self.config_validator.perform_comprehensive_validation()
            
            # Add current addon options validation if available
            if hasattr(self.app, 'config') and self.app.config:
                try:
                    validated_options = self.config_validator.validate_addon_options(self.app.config)
                    validation_report['validations']['addon_options'] = {
                        'valid': True,
                        'validated_options': validated_options
                    }
                except ValidationError as e:
                    validation_report['validations']['addon_options'] = {
                        'valid': False,
                        'error': str(e)
                    }
                    if validation_report['overall_status'] == 'valid':
                        validation_report['overall_status'] = 'invalid'
            
            return web.json_response(validation_report)
            
        except Exception as e:
            logger.error(f"Error in api_validate_config: {e}")
            return web.json_response({
                'overall_status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, status=500)