
"""
AICleaner v3 Web UI API Server
FastAPI-based REST API for web interface
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

logger = logging.getLogger(__name__)

# Data Models
class ConfigurationModel(BaseModel):
    ai: Optional[Dict[str, Any]] = {}
    mqtt: Optional[Dict[str, Any]] = {}
    zones: Optional[Dict[str, Any]] = {}
    devices: Optional[Dict[str, Any]] = {}

class DeviceModel(BaseModel):
    id: str
    name: str
    type: str
    online: bool = False
    controllable: bool = False
    capabilities: List[str] = []
    properties: Optional[Dict[str, Any]] = {}
    last_seen: Optional[str] = None

class ZoneModel(BaseModel):
    id: Optional[str] = None
    name: str
    description: str = ""
    active: bool = False
    devices: List[str] = []
    schedule: Optional[Dict[str, Any]] = {}

class MetricsModel(BaseModel):
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    active_zones: int = 0
    connected_devices: int = 0
    timestamp: str

class SecurityStatusModel(BaseModel):
    supervisor_token_valid: bool = False
    tls_enabled: bool = False
    mqtt_secured: bool = False
    last_security_check: str
    security_level: str = "unknown"  # low, medium, high
    threats_detected: int = 0
    security_events: List[Dict[str, Any]] = []

class MQTTStatusModel(BaseModel):
    connected: bool = False
    broker_address: str = ""
    broker_port: int = 1883
    tls_enabled: bool = False
    discovery_prefix: str = "homeassistant"
    discovered_entities: int = 0
    last_message_time: Optional[str] = None
    connection_uptime: Optional[str] = None

# API Server
class AiCleanerAPIServer:
    """AICleaner v3 Web UI API Server"""
    
    def __init__(self, addon_root: str):
        self.addon_root = Path(addon_root)
        self.app = FastAPI(title="AICleaner v3 API", version="3.0.0")
        self.websocket_connections: List[WebSocket] = []
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mount static files
        static_path = self.addon_root / "ui" / "dist"
        if static_path.exists():
            self.app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/api/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        @self.app.get("/api/config", response_model=ConfigurationModel)
        async def get_configuration():
            """Get current configuration"""
            try:
                config_file = self.addon_root / "config" / "aicleaner_config.json"
                if config_file.exists():
                    with open(config_file) as f:
                        config = json.load(f)
                    return ConfigurationModel(**config)
                else:
                    return ConfigurationModel()
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
                raise HTTPException(status_code=500, detail="Failed to load configuration")
        
        @self.app.post("/api/config")
        async def update_configuration(config: ConfigurationModel):
            """Update configuration"""
            try:
                config_file = self.addon_root / "config" / "aicleaner_config.json"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(config_file, 'w') as f:
                    json.dump(config.dict(), f, indent=2)
                
                # Broadcast configuration update
                await self._broadcast_websocket({
                    "type": "config_updated",
                    "payload": config.dict()
                })
                
                return {"status": "success", "message": "Configuration updated"}
            except Exception as e:
                logger.error(f"Failed to update configuration: {e}")
                raise HTTPException(status_code=500, detail="Failed to update configuration")
        
        @self.app.get("/api/devices", response_model=List[DeviceModel])
        async def get_devices():
            """Get device list"""
            # Mock device data - replace with actual device discovery
            devices = [
                DeviceModel(
                    id="vacuum_1",
                    name="Living Room Vacuum",
                    type="vacuum",
                    online=True,
                    controllable=True,
                    capabilities=["clean", "dock", "spot_clean"],
                    last_seen=datetime.now().isoformat()
                ),
                DeviceModel(
                    id="sensor_1", 
                    name="Kitchen Motion Sensor",
                    type="motion_sensor",
                    online=True,
                    controllable=False,
                    capabilities=["motion_detection"],
                    last_seen=datetime.now().isoformat()
                )
            ]
            return devices
        
        @self.app.post("/api/devices/{device_id}/control")
        async def control_device(device_id: str, action: Dict[str, Any]):
            """Control device"""
            try:
                # Implement device control logic
                logger.info(f"Controlling device {device_id} with action: {action}")
                
                # Broadcast device state update
                await self._broadcast_websocket({
                    "type": "device_updated",
                    "payload": {"device_id": device_id, "action": action}
                })
                
                return {"status": "success", "message": f"Device {device_id} controlled"}
            except Exception as e:
                logger.error(f"Failed to control device {device_id}: {e}")
                raise HTTPException(status_code=500, detail="Failed to control device")
        
        @self.app.get("/api/zones", response_model=List[ZoneModel])
        async def get_zones():
            """Get zone list"""
            # Mock zone data - replace with actual zone management
            zones = [
                ZoneModel(
                    id="zone_1",
                    name="Living Room",
                    description="Main living area cleaning zone",
                    active=True,
                    devices=["vacuum_1"],
                    schedule={"enabled": True, "start_time": "09:00", "end_time": "17:00"}
                ),
                ZoneModel(
                    id="zone_2",
                    name="Kitchen",
                    description="Kitchen cleaning zone",
                    active=False,
                    devices=["sensor_1"]
                )
            ]
            return zones
        
        @self.app.post("/api/zones", response_model=ZoneModel)
        async def create_zone(zone: ZoneModel):
            """Create new zone"""
            try:
                # Generate zone ID
                zone.id = f"zone_{datetime.now().timestamp()}"
                
                # Implement zone creation logic
                logger.info(f"Creating zone: {zone.name}")
                
                # Broadcast zone creation
                await self._broadcast_websocket({
                    "type": "zone_created",
                    "payload": zone.dict()
                })
                
                return zone
            except Exception as e:
                logger.error(f"Failed to create zone: {e}")
                raise HTTPException(status_code=500, detail="Failed to create zone")
        
        @self.app.put("/api/zones/{zone_id}")
        async def update_zone(zone_id: str, zone: ZoneModel):
            """Update zone"""
            try:
                zone.id = zone_id
                logger.info(f"Updating zone {zone_id}: {zone.name}")
                
                # Broadcast zone update
                await self._broadcast_websocket({
                    "type": "zone_updated",
                    "payload": zone.dict()
                })
                
                return {"status": "success", "message": f"Zone {zone_id} updated"}
            except Exception as e:
                logger.error(f"Failed to update zone {zone_id}: {e}")
                raise HTTPException(status_code=500, detail="Failed to update zone")
        
        @self.app.delete("/api/zones/{zone_id}")
        async def delete_zone(zone_id: str):
            """Delete zone"""
            try:
                logger.info(f"Deleting zone {zone_id}")
                
                # Broadcast zone deletion
                await self._broadcast_websocket({
                    "type": "zone_deleted",
                    "payload": {"zone_id": zone_id}
                })
                
                return {"status": "success", "message": f"Zone {zone_id} deleted"}
            except Exception as e:
                logger.error(f"Failed to delete zone {zone_id}: {e}")
                raise HTTPException(status_code=500, detail="Failed to delete zone")
        
        @self.app.get("/api/metrics", response_model=MetricsModel)
        async def get_metrics():
            """Get system metrics"""
            # Mock metrics - replace with actual system monitoring
            metrics = MetricsModel(
                cpu_usage=45.2,
                memory_usage=62.8,
                disk_usage=34.1,
                active_zones=2,
                connected_devices=3,
                timestamp=datetime.now().isoformat()
            )
            return metrics
        
        @self.app.get("/api/security", response_model=SecurityStatusModel)
        async def get_security_status():
            """Get security status"""
            try:
                # Import security validator to check status
                from ...integrations.security_validator import SecurityValidator
                
                security_validator = SecurityValidator()
                await security_validator.initialize()
                
                # Perform security checks
                current_time = datetime.now().isoformat()
                
                # Mock security data - replace with actual security monitoring
                security_status = SecurityStatusModel(
                    supervisor_token_valid=True,  # Would check actual token
                    tls_enabled=True,  # Would check MQTT TLS status
                    mqtt_secured=True,  # Combined security status
                    last_security_check=current_time,
                    security_level="high",
                    threats_detected=0,
                    security_events=[
                        {
                            "timestamp": current_time,
                            "type": "security_check",
                            "message": "Security validation completed successfully",
                            "level": "info"
                        }
                    ]
                )
                
                await security_validator.cleanup()
                return security_status
                
            except Exception as e:
                logger.error(f"Failed to get security status: {e}")
                # Return safe defaults on error
                return SecurityStatusModel(
                    supervisor_token_valid=False,
                    tls_enabled=False,
                    mqtt_secured=False,
                    last_security_check=datetime.now().isoformat(),
                    security_level="unknown",
                    threats_detected=0,
                    security_events=[
                        {
                            "timestamp": datetime.now().isoformat(),
                            "type": "error",
                            "message": f"Security check failed: {str(e)[:100]}",
                            "level": "error"
                        }
                    ]
                )
        
        @self.app.post("/api/security/validate-token")
        async def validate_supervisor_token(token_data: Dict[str, str]):
            """Validate supervisor token"""
            try:
                from ...integrations.security_validator import SecurityValidator
                
                token = token_data.get("token", "")
                if not token:
                    raise HTTPException(status_code=400, detail="Token is required")
                
                security_validator = SecurityValidator()
                await security_validator.initialize()
                
                is_valid = await security_validator.validate_supervisor_token(token)
                
                await security_validator.cleanup()
                
                return {
                    "valid": is_valid,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Token validation completed"
                }
                
            except Exception as e:
                logger.error(f"Token validation error: {e}")
                raise HTTPException(status_code=500, detail="Token validation failed")
        
        @self.app.get("/api/mqtt/status", response_model=MQTTStatusModel)
        async def get_mqtt_status():
            """Get MQTT connection status"""
            try:
                # Mock MQTT status - replace with actual MQTT discovery manager
                mqtt_status = MQTTStatusModel(
                    connected=True,
                    broker_address="localhost",
                    broker_port=1883,
                    tls_enabled=False,
                    discovery_prefix="homeassistant",
                    discovered_entities=15,
                    last_message_time=datetime.now().isoformat(),
                    connection_uptime="2h 30m"
                )
                return mqtt_status
                
            except Exception as e:
                logger.error(f"Failed to get MQTT status: {e}")
                return MQTTStatusModel(
                    connected=False,
                    last_message_time=None,
                    connection_uptime=None
                )
        
        @self.app.post("/api/mqtt/reconnect")
        async def reconnect_mqtt():
            """Reconnect MQTT client"""
            try:
                # Implement MQTT reconnection logic
                logger.info("MQTT reconnection requested")
                
                # Broadcast MQTT reconnection event
                await self._broadcast_websocket({
                    "type": "mqtt_reconnecting",
                    "payload": {"timestamp": datetime.now().isoformat()}
                })
                
                return {"status": "success", "message": "MQTT reconnection initiated"}
                
            except Exception as e:
                logger.error(f"MQTT reconnection failed: {e}")
                raise HTTPException(status_code=500, detail="MQTT reconnection failed")
        
        @self.app.get("/api/mqtt/entities")
        async def get_mqtt_entities():
            """Get MQTT discovered entities"""
            try:
                # Mock MQTT entities - replace with actual entity manager
                entities = [
                    {
                        "unique_id": "sensor_temperature_1",
                        "name": "Living Room Temperature",
                        "component": "sensor",
                        "state": "23.5°C",
                        "last_updated": datetime.now().isoformat(),
                        "zone": "living_room"
                    },
                    {
                        "unique_id": "binary_sensor_motion_1", 
                        "name": "Kitchen Motion",
                        "component": "binary_sensor",
                        "state": "off",
                        "last_updated": datetime.now().isoformat(),
                        "zone": "kitchen"
                    }
                ]
                return entities
                
            except Exception as e:
                logger.error(f"Failed to get MQTT entities: {e}")
                raise HTTPException(status_code=500, detail="Failed to get MQTT entities")
        
        @self.app.post("/api/config/validate")
        async def validate_configuration(config_data: Dict[str, Any]):
            """Validate configuration in real-time"""
            try:
                from ...utils.configuration_manager import ConfigurationManager
                
                config_manager = ConfigurationManager()
                is_valid = config_manager.validate_configuration(config_data)
                errors = config_manager.get_validation_errors()
                warnings = self._generate_configuration_warnings(config_data)
                security_impact = self._assess_security_impact(config_data)
                
                return {
                    "valid": is_valid,
                    "errors": self._format_validation_errors(errors),
                    "warnings": warnings,
                    "security_impact": security_impact,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Configuration validation failed: {e}")
                raise HTTPException(status_code=500, detail="Validation failed")
        
        @self.app.post("/api/config/save")  
        async def save_configuration(config_data: Dict[str, Any]):
            """Save configuration with validation and audit logging"""
            try:
                from ...utils.configuration_manager import ConfigurationManager
                from ...integrations.security_validator import SecurityValidator
                
                # Validate configuration first
                config_manager = ConfigurationManager()
                is_valid = config_manager.validate_configuration(config_data)
                
                if not is_valid:
                    errors = config_manager.get_validation_errors()
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid configuration: {'; '.join(errors)}"
                    )
                
                # Security validation
                security_validator = SecurityValidator()
                await security_validator.initialize()
                
                # Audit logging (simplified)
                logger.info(f"Configuration update request from {datetime.now().isoformat()}")
                
                # Save configuration (mock implementation)
                config_file = self.addon_root / "config" / "aicleaner_config.json"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(config_file, 'w') as f:
                    json.dump(config_data, f, indent=2)
                
                # Broadcast configuration update
                await self._broadcast_websocket({
                    "type": "config_updated",
                    "payload": {
                        "timestamp": datetime.now().isoformat(),
                        "sections_updated": list(config_data.keys())
                    }
                })
                
                await security_validator.cleanup()
                
                return {
                    "status": "success", 
                    "message": "Configuration saved successfully",
                    "timestamp": datetime.now().isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to save configuration: {e}")
                raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        @self.app.post("/api/mqtt/test-connection")
        async def test_mqtt_connection(mqtt_config: Dict[str, Any]):
            """Test MQTT connection with provided configuration"""
            try:
                # Mock MQTT connection test - replace with actual implementation
                broker_address = mqtt_config.get('broker_address', '')
                broker_port = mqtt_config.get('broker_port', 1883)
                use_tls = mqtt_config.get('use_tls', False)
                
                if not broker_address:
                    raise HTTPException(status_code=400, detail="Broker address is required")
                
                # Simulate connection test
                await asyncio.sleep(1)  # Simulate network delay
                
                # Mock test logic
                if broker_address == 'localhost' or broker_address.endswith('.local'):
                    return {
                        "success": True,
                        "message": f"Successfully connected to {broker_address}:{broker_port}",
                        "details": f"TLS: {'Enabled' if use_tls else 'Disabled'}, Latency: 15ms"
                    }
                else:
                    # Simulate occasional connection failures for demo
                    import random
                    if random.random() > 0.7:
                        raise Exception("Connection timeout")
                    
                    return {
                        "success": True,
                        "message": f"Successfully connected to {broker_address}:{broker_port}",
                        "details": f"TLS: {'Enabled' if use_tls else 'Disabled'}, Latency: 45ms"
                    }
                
            except Exception as e:
                logger.error(f"MQTT connection test failed: {e}")
                return {
                    "success": False,
                    "message": str(e),
                    "details": "Check broker address, port, and network connectivity"
                }
        
        @self.app.get("/api/security/permissions")
        async def get_security_permissions():
            """Get user security permissions"""
            try:
                # Mock permissions - replace with actual security check
                return {
                    "canEditConfig": True,
                    "canViewSecurity": True,
                    "canManageZones": True,
                    "canControlDevices": True,
                    "security_level": "high"
                }
                
            except Exception as e:
                logger.error(f"Failed to get permissions: {e}")
                raise HTTPException(status_code=500, detail="Failed to get permissions")
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Send periodic updates
                    await asyncio.sleep(5)
                    metrics = await get_metrics()
                    await websocket.send_json({
                        "type": "metrics",
                        "payload": metrics.dict()
                    })
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
    
    async def _broadcast_websocket(self, message: Dict[str, Any]):
        """Broadcast message to all WebSocket connections"""
        if self.websocket_connections:
            disconnected = []
            for websocket in self.websocket_connections:
                try:
                    await websocket.send_json(message)
                except:
                    disconnected.append(websocket)
            
            # Remove disconnected websockets
            for websocket in disconnected:
                self.websocket_connections.remove(websocket)
    
    def _format_validation_errors(self, errors: List[str]) -> Dict[str, str]:
        """Format validation errors into field-specific dictionary"""
        formatted_errors = {}
        for error in errors:
            if ':' in error:
                # Try to extract field name from error message
                parts = error.split(':', 1)
                field = parts[0].strip()
                message = parts[1].strip()
                formatted_errors[field] = message
            else:
                formatted_errors['general'] = error
        return formatted_errors
    
    def _generate_configuration_warnings(self, config_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate configuration warnings"""
        warnings = {}
        
        # MQTT warnings
        mqtt_config = config_data.get('mqtt', {})
        if mqtt_config:
            if not mqtt_config.get('use_tls', False):
                warnings['mqtt.security'] = 'TLS encryption is disabled - communication will be unencrypted'
            
            if not mqtt_config.get('username') and not mqtt_config.get('password'):
                warnings['mqtt.auth'] = 'No authentication configured - ensure broker allows anonymous connections'
            
            if mqtt_config.get('tls_insecure', False):
                warnings['mqtt.tls_insecure'] = 'Certificate verification is disabled - not recommended for production'
        
        # Security warnings
        security_config = config_data.get('security', {})
        if security_config:
            if not security_config.get('supervisor_token_valid', False):
                warnings['security.token'] = 'Supervisor token validation failed - some features may be unavailable'
        
        return warnings
    
    def _assess_security_impact(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess security impact of configuration changes"""
        impact = {
            'level': 'low',
            'changes': [],
            'recommendations': []
        }
        
        mqtt_config = config_data.get('mqtt', {})
        if mqtt_config:
            # Check TLS configuration changes
            if not mqtt_config.get('use_tls', False):
                impact['level'] = 'high'
                impact['changes'].append('MQTT TLS encryption disabled')
                impact['recommendations'].append('Enable TLS encryption for secure communication')
            
            # Check authentication
            if not mqtt_config.get('username'):
                if impact['level'] != 'high':
                    impact['level'] = 'medium'
                impact['changes'].append('MQTT authentication not configured')
                impact['recommendations'].append('Configure MQTT username and password')
            
            # Check insecure TLS
            if mqtt_config.get('tls_insecure', False):
                if impact['level'] not in ['high']:
                    impact['level'] = 'medium'
                impact['changes'].append('TLS certificate verification disabled')
                impact['recommendations'].append('Enable certificate verification for production use')
        
        return impact
    
    def start_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the API server"""
        logger.info(f"Starting AICleaner v3 API server on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)

if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    addon_root = Path(__file__).parent.parent
    server = AiCleanerAPIServer(str(addon_root))
    server.start_server()
