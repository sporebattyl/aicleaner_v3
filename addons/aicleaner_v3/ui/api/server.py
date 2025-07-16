
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
