"""
FastAPI Backend for AICleaner v3 Web Interface
Phase 4C: User Interface Implementation

Provides REST API endpoints for the web-based management interface.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Performance optimization - Phase 5A
from performance.serialization_optimizer import fast_json_dumps, fast_json_loads

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

from performance.api_cache import (
    api_response_cache, cache_clear, cache_ai_provider_status, 
    cache_system_config, get_cache_statistics, cache_maintenance_task
)

from ai.providers.ai_provider_manager import AIProviderManager
from ai.providers.load_balancer import LoadBalancingStrategy
from core.config_manager import ConfigManager
from utils.unified_logger import get_logger
from monitoring.system_monitor import get_system_monitor

# Home Assistant Integration
from ha_integration.ha_client import HAClient
from ha_integration.entity_manager import EntityManager
from ha_integration.service_handler import ServiceHandler
from ha_integration.ingress_middleware import IngressMiddleware
from ha_integration.config_schema import HAIntegrationConfig
from ha_integration.ha_adapter import HomeAssistantAdapter

# Core Systems Integration
from core.aicleaner_core import AICleanerCore

# MQTT Integration - Phase 4B
from mqtt.adapter import MQTTAdapter
from mqtt.config import MQTTConfig

logger = get_logger(__name__)

# Security (optional for single-user, but good practice)
security = HTTPBearer(auto_error=False)

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

# Pydantic models for API requests/responses
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ProviderConfig(BaseModel):
    name: str
    enabled: bool
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    priority: int = 1
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 10000
    daily_budget: float = 10.0
    base_url: Optional[str] = None

class StrategyConfig(BaseModel):
    load_balancing_strategy: str
    cost_optimization_tiers: Optional[Dict[str, List[str]]] = None

class LogQuery(BaseModel):
    level: Optional[str] = None
    provider: Optional[str] = None
    limit: int = 100
    search: Optional[str] = None

# Global instances
manager = ConnectionManager()
ai_provider_manager: Optional[AIProviderManager] = None
config_manager: Optional[ConfigManager] = None
system_monitor = get_system_monitor()

# Home Assistant Integration instances
ha_client: Optional[HAClient] = None
entity_manager: Optional[EntityManager] = None
service_handler: Optional[ServiceHandler] = None
ha_adapter: Optional[HomeAssistantAdapter] = None

# Core System instances
aicleaner_core: Optional[AICleanerCore] = None

# FastAPI app
app = FastAPI(
    title="AICleaner v3 Management API",
    description="REST API for managing AICleaner v3 Home Assistant addon",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Home Assistant ingress middleware (must be after CORS)
# This will be initialized during startup when HA config is available
def add_ingress_middleware():
    """Add ingress middleware if HA integration is enabled"""
    if ha_client and ha_client.config:
        app.add_middleware(IngressMiddleware, ha_config=ha_client.config)

# Initialize global instances
async def initialize_services():
    """Initialize AI provider manager, config manager, and HA integration"""
    global ai_provider_manager, config_manager, ha_client, entity_manager, service_handler, ha_adapter, aicleaner_core
    
    try:
        # Initialize config manager
        config_manager = ConfigManager("/data")
        await config_manager.load_config()
        
        # Initialize AI provider manager
        config_data = config_manager.get_config()
        ai_provider_manager = AIProviderManager(config_data, "/data")
        await ai_provider_manager.initialize()
        
        # Initialize Home Assistant adapter (standalone mode - no hass object)
        ha_adapter = HomeAssistantAdapter(hass=None)
        logger.info("Home Assistant adapter initialized in standalone mode")
        
        # Initialize MQTT adapter if enabled - Phase 4B
        mqtt_adapter = None
        mqtt_config_data = config_data.get("mqtt", {})
        if mqtt_config_data.get("enabled", True):
            try:
                mqtt_config = MQTTConfig(**mqtt_config_data)
                mqtt_adapter = MQTTAdapter(mqtt_config, mock_mode=True)  # Use mock mode for testing
                logger.info("MQTT adapter initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize MQTT adapter: {e}")
                mqtt_adapter = None
        else:
            logger.info("MQTT integration disabled in configuration")
        
        # Initialize AICleaner core system
        try:
            aicleaner_core = AICleanerCore(
                config_data=config_data,
                ha_adapter=ha_adapter,
                ai_provider_manager=ai_provider_manager,
                mqtt_adapter=mqtt_adapter
            )
            await aicleaner_core.start()
            logger.info("AICleaner Core initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AICleaner Core: {e}")
            # Don't fail entire startup if core system can't initialize
            aicleaner_core = None
        
        # Initialize Home Assistant integration if enabled
        ha_config = config_data.get("ha", {})
        if ha_config.get("enabled", True):
            try:
                # Parse HA configuration
                ha_integration_config = HAIntegrationConfig(**ha_config)
                
                # Initialize HA client
                ha_client = HAClient(ha_integration_config)
                
                # Initialize entity manager
                entity_manager = EntityManager(ha_client, ha_integration_config)
                
                # Initialize service handler with AICleaner core
                service_handler = ServiceHandler(
                    ha_client=ha_client,
                    config=ha_integration_config,
                    aicleaner_core=aicleaner_core
                )
                
                # Connect to Home Assistant
                await ha_client.connect()
                
                # Register default entities
                await entity_manager.initialize_default_entities()
                
                # Register services
                await service_handler.register_default_services()
                
                logger.info("Home Assistant integration initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize HA integration: {e}")
                # Don't fail the entire startup if HA integration fails
                ha_client = None
                entity_manager = None
                service_handler = None
        else:
            logger.info("Home Assistant integration disabled in configuration")
        
        logger.info("Backend services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize backend services: {e}")
        raise

# Dependency to get AI provider manager
async def get_ai_provider_manager() -> AIProviderManager:
    if ai_provider_manager is None:
        raise HTTPException(status_code=503, detail="AI Provider Manager not initialized")
    return ai_provider_manager

# Dependency to get config manager
async def get_config_manager() -> ConfigManager:
    if config_manager is None:
        raise HTTPException(status_code=503, detail="Config Manager not initialized")
    return config_manager

# Health check endpoint
@app.get("/api/health")
@api_response_cache(ttl=30)  # Cache health status for 30 seconds
async def health_check(request: Request):
    """Health check endpoint with caching"""
    return APIResponse(
        success=True,
        message="Service is healthy",
        data={
            "uptime": time.time(),
            "ai_providers_initialized": ai_provider_manager is not None,
            "config_manager_initialized": config_manager is not None
        }
    )

# System status endpoints
@app.get("/api/status")
@cache_ai_provider_status(ttl=60)  # Cache system status for 1 minute
async def get_system_status(
    request: Request,
    ai_mgr: AIProviderManager = Depends(get_ai_provider_manager)
):
    """Get overall system status"""
    try:
        # Get provider status
        provider_status = ai_mgr.get_provider_status()
        
        # Get load balancer stats
        load_balancer_stats = ai_mgr.get_load_balancer_stats()
        
        # Get system health
        health_report = await ai_mgr.health_check()
        
        # Get performance metrics
        performance_metrics = ai_mgr.get_performance_metrics()
        
        return APIResponse(
            success=True,
            message="System status retrieved successfully",
            data={
                "providers": provider_status,
                "load_balancer": load_balancer_stats,
                "health": health_report,
                "performance": performance_metrics,
                "system_info": {
                    "total_providers": len(ai_mgr.providers),
                    "active_providers": len([p for p in provider_status.values() if p.get("available", False)]),
                    "current_strategy": load_balancer_stats.get("strategy", "unknown")
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Provider management endpoints
@app.get("/api/providers")
@cache_ai_provider_status(ttl=120)  # Cache providers for 2 minutes
async def get_providers(
    request: Request,
    ai_mgr: AIProviderManager = Depends(get_ai_provider_manager)
):
    """Get all AI providers"""
    try:
        provider_status = ai_mgr.get_provider_status()
        
        providers = []
        for name, status in provider_status.items():
            provider = ai_mgr.providers.get(name)
            if provider:
                providers.append({
                    "name": name,
                    "enabled": provider.config.enabled,
                    "status": status["status"],
                    "health": status["health"],
                    "available": status["available"],
                    "active_requests": status["active_requests"],
                    "metrics": status["metrics"],
                    "load_balancer_stats": status.get("load_balancer_stats", {}),
                    "ml_model_stats": status.get("ml_model_stats", {}),
                    "config": {
                        "model_name": provider.config.model_name,
                        "priority": provider.config.priority,
                        "rate_limit_rpm": provider.config.rate_limit_rpm,
                        "rate_limit_tpm": provider.config.rate_limit_tpm,
                        "daily_budget": provider.config.daily_budget,
                        "base_url": provider.config.base_url
                    }
                })
        
        return APIResponse(
            success=True,
            message="Providers retrieved successfully",
            data={"providers": providers}
        )
        
    except Exception as e:
        logger.error(f"Error getting providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/providers/{provider_name}")
async def get_provider_details(
    provider_name: str,
    ai_mgr: AIProviderManager = Depends(get_ai_provider_manager)
):
    """Get detailed information about a specific provider"""
    try:
        if provider_name not in ai_mgr.providers:
            raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")
        
        provider = ai_mgr.providers[provider_name]
        provider_status = ai_mgr.get_provider_status()
        
        status = provider_status.get(provider_name, {})
        
        return APIResponse(
            success=True,
            message=f"Provider '{provider_name}' details retrieved successfully",
            data={
                "name": provider_name,
                "config": provider.config.__dict__,
                "status": status,
                "cost_stats": provider.get_cost_stats(),
                "capabilities": provider.capabilities
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting provider details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Strategy management endpoints
@app.get("/api/strategy")
async def get_current_strategy(
    ai_mgr: AIProviderManager = Depends(get_ai_provider_manager)
):
    """Get current load balancing and ML model selection strategy"""
    try:
        load_balancer_stats = ai_mgr.get_load_balancer_stats()
        
        return APIResponse(
            success=True,
            message="Strategy configuration retrieved successfully",
            data={
                "load_balancing_strategy": load_balancer_stats.get("strategy", "unknown"),
                "cost_optimization_tiers": load_balancer_stats.get("cost_tiers", {}),
                "available_strategies": [strategy.value for strategy in LoadBalancingStrategy]
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategy")
async def update_strategy(
    strategy_config: StrategyConfig,
    ai_mgr: AIProviderManager = Depends(get_ai_provider_manager),
    config_mgr: ConfigManager = Depends(get_config_manager)
):
    """Update load balancing strategy"""
    try:
        # Validate strategy
        try:
            new_strategy = LoadBalancingStrategy(strategy_config.load_balancing_strategy)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid strategy: {strategy_config.load_balancing_strategy}"
            )
        
        # Update load balancer strategy
        ai_mgr.load_balancer.set_strategy(new_strategy)
        
        # Update cost tiers if provided
        if strategy_config.cost_optimization_tiers:
            ai_mgr.load_balancer.update_cost_tiers(strategy_config.cost_optimization_tiers)
        
        # Update configuration
        config_data = config_mgr.get_config()
        if "ai_provider_manager" not in config_data:
            config_data["ai_provider_manager"] = {}
        
        config_data["ai_provider_manager"]["selection_strategy"] = strategy_config.load_balancing_strategy
        if strategy_config.cost_optimization_tiers:
            config_data["ai_provider_manager"]["cost_optimization_tiers"] = strategy_config.cost_optimization_tiers
        
        await config_mgr.save_config(config_data)
        
        # Broadcast update to WebSocket clients
        await manager.broadcast(fast_json_dumps({
            "type": "strategy_updated",
            "data": {
                "strategy": strategy_config.load_balancing_strategy,
                "cost_tiers": strategy_config.cost_optimization_tiers
            }
        }))
        
        return APIResponse(
            success=True,
            message="Strategy updated successfully",
            data={
                "new_strategy": strategy_config.load_balancing_strategy,
                "cost_tiers": strategy_config.cost_optimization_tiers
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ML model statistics endpoint
@app.get("/api/ml_stats")
async def get_ml_stats(
    ai_mgr: AIProviderManager = Depends(get_ai_provider_manager)
):
    """Get ML model selection statistics"""
    try:
        ml_stats = {}
        
        for provider_name, provider in ai_mgr.providers.items():
            provider_ml_stats = provider.get_ml_model_stats()
            if provider_ml_stats:
                ml_stats[provider_name] = provider_ml_stats
        
        return APIResponse(
            success=True,
            message="ML statistics retrieved successfully",
            data=ml_stats
        )
        
    except Exception as e:
        logger.error(f"Error getting ML stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Log viewing endpoint
@app.post("/api/logs")
async def get_logs(
    query: LogQuery,
    config_mgr: ConfigManager = Depends(get_config_manager)
):
    """Get system logs with filtering"""
    try:
        # This is a simplified implementation
        # In a full implementation, you'd integrate with your unified logging system
        
        # For now, return a mock response
        logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "provider": "openai",
                "message": "Request processed successfully",
                "details": {"response_time": 2.1, "cost": 0.05}
            },
            {
                "timestamp": datetime.now().isoformat(),
                "level": "DEBUG",
                "provider": "load_balancer",
                "message": "Selected provider: openai",
                "details": {"strategy": "weighted_round_robin"}
            }
        ]
        
        # Apply filters
        if query.level:
            logs = [log for log in logs if log["level"] == query.level.upper()]
        
        if query.provider:
            logs = [log for log in logs if log["provider"] == query.provider]
        
        if query.search:
            logs = [log for log in logs if query.search.lower() in log["message"].lower()]
        
        # Apply limit
        logs = logs[:query.limit]
        
        return APIResponse(
            success=True,
            message="Logs retrieved successfully",
            data={"logs": logs}
        )
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Handle different message types
            message = fast_json_loads(data)
            message_type = message.get("type")
            
            if message_type == "ping":
                await websocket.send_text(fast_json_dumps({"type": "pong"}))
            elif message_type == "subscribe":
                # Handle subscription to specific event types
                await websocket.send_text(fast_json_dumps({
                    "type": "subscription_confirmed",
                    "data": {"subscribed_to": message.get("events", [])}
                }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Background task to send periodic updates
async def send_periodic_updates():
    """Send periodic system updates to WebSocket clients"""
    while True:
        try:
            if ai_provider_manager and len(manager.active_connections) > 0:
                # Get current status
                provider_status = ai_provider_manager.get_provider_status()
                
                # Get HA status if available
                ha_status = None
                if ha_client:
                    ha_status = {
                        "connected": ha_client.connected,
                        "entities": len(entity_manager.registered_entities) if entity_manager else 0,
                        "services": len(service_handler.registered_services) if service_handler else 0
                    }
                
                # Send update
                await manager.broadcast(fast_json_dumps({
                    "type": "status_update",
                    "data": {
                        "providers": provider_status,
                        "ha_integration": ha_status,
                        "timestamp": datetime.now().isoformat()
                    }
                }))
            
            await asyncio.sleep(10)  # Update every 10 seconds
            
        except Exception as e:
            logger.error(f"Error sending periodic updates: {e}")
            await asyncio.sleep(30)  # Wait longer on error

# Cache statistics endpoint
@app.get("/api/cache/stats")
async def get_cache_stats(request: Request):
    """Get cache performance statistics"""
    try:
        stats = await get_cache_statistics()
        return APIResponse(
            success=True,
            message="Cache statistics retrieved successfully",
            data=stats
        )
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/clear")
@cache_clear()
async def clear_cache(request: Request):
    """Clear all cached data"""
    try:
        return APIResponse(
            success=True,
            message="Cache cleared successfully",
            data={"timestamp": datetime.now().isoformat()}
        )
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        await initialize_services()
        
        # Add ingress middleware after HA initialization
        add_ingress_middleware()
        
        # Start background tasks
        asyncio.create_task(send_periodic_updates())
        asyncio.create_task(cache_maintenance_task())  # Start cache maintenance
        
        logger.info("AICleaner v3 API backend started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        raise

# Shutdown event for HA cleanup
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        if ha_client:
            await ha_client.disconnect()
            logger.info("Home Assistant client disconnected")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# AICleaner Core endpoints
@app.get("/api/core/status")
@api_response_cache(ttl=30)  # Cache core status for 30 seconds
async def get_core_status(request: Request):
    """Get AICleaner core system status"""
    try:
        if not aicleaner_core:
            return APIResponse(
                success=False,
                message="AICleaner core not initialized",
                data={"status": "disabled"}
            )
        
        status = aicleaner_core.get_system_status()
        
        return APIResponse(
            success=True,
            message="Core system status retrieved successfully",
            data=status
        )
        
    except Exception as e:
        logger.error(f"Error getting core status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/core/zones")
async def get_zones():
    """Get all configured zones"""
    try:
        if not aicleaner_core:
            raise HTTPException(status_code=503, detail="AICleaner core not available")
        
        zones = aicleaner_core.list_zones()
        
        return APIResponse(
            success=True,
            message="Zones retrieved successfully",
            data={"zones": zones}
        )
        
    except Exception as e:
        logger.error(f"Error getting zones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/core/clean")
async def start_cleaning(cleaning_request: Dict[str, Any]):
    """Start cleaning operation"""
    try:
        if not aicleaner_core:
            raise HTTPException(status_code=503, detail="AICleaner core not available")
        
        zone_id = cleaning_request.get("zone_id")
        cleaning_mode = cleaning_request.get("cleaning_mode", "normal")
        duration = cleaning_request.get("duration")
        
        if zone_id:
            result = await aicleaner_core.clean_zone_by_id(zone_id, cleaning_mode, duration)
        else:
            result = await aicleaner_core.clean_all_zones(cleaning_mode)
        
        return APIResponse(
            success=result.get("status") == "success",
            message=result.get("message", "Cleaning operation completed"),
            data=result
        )
        
    except Exception as e:
        logger.error(f"Error starting cleaning: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/core/stop")
async def stop_cleaning(stop_request: Dict[str, Any]):
    """Stop cleaning operation"""
    try:
        if not aicleaner_core:
            raise HTTPException(status_code=503, detail="AICleaner core not available")
        
        zone_id = stop_request.get("zone_id")
        result = await aicleaner_core.stop_cleaning(zone_id)
        
        return APIResponse(
            success=result.get("status") == "success",
            message=result.get("message", "Stop operation completed"),
            data=result
        )
        
    except Exception as e:
        logger.error(f"Error stopping cleaning: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Home Assistant integration endpoints
@app.get("/api/ha/status")
@api_response_cache(ttl=30)  # Cache HA status for 30 seconds
async def get_ha_status(request: Request):
    """Get Home Assistant integration status"""
    try:
        if not ha_client:
            return APIResponse(
                success=False,
                message="Home Assistant integration not initialized",
                data={"status": "disabled"}
            )
        
        status = {
            "connected": ha_client.connected,
            "status": "connected" if ha_client.connected else "disconnected",
            "entities_registered": len(entity_manager.registered_entities) if entity_manager else 0,
            "services_registered": len(service_handler.registered_services) if service_handler else 0,
            "config": {
                "websocket_url": ha_client.config.websocket_url,
                "entity_prefix": ha_client.config.entity_prefix,
                "device_name": ha_client.config.device_name,
                "service_domain": ha_client.config.service_domain
            }
        }
        
        return APIResponse(
            success=True,
            message="HA integration status retrieved successfully",
            data=status
        )
        
    except Exception as e:
        logger.error(f"Error getting HA status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ha/entities")
async def get_ha_entities():
    """Get registered Home Assistant entities"""
    try:
        if not entity_manager:
            raise HTTPException(status_code=503, detail="HA entity manager not available")
        
        entities = entity_manager.get_registered_entities()
        
        return APIResponse(
            success=True,
            message="HA entities retrieved successfully",
            data={"entities": entities}
        )
        
    except Exception as e:
        logger.error(f"Error getting HA entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ha/services")
async def get_ha_services():
    """Get registered Home Assistant services"""
    try:
        if not service_handler:
            raise HTTPException(status_code=503, detail="HA service handler not available")
        
        services = service_handler.get_registered_services()
        
        return APIResponse(
            success=True,
            message="HA services retrieved successfully",
            data={"services": services}
        )
        
    except Exception as e:
        logger.error(f"Error getting HA services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Static file serving for frontend
app.mount("/", StaticFiles(directory="ui/dist", html=True), name="static")

# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "api.backend:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )