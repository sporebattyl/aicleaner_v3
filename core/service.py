"""
AICleaner v3 Core Service
Simple FastAPI service implementing power-user focused AI automation
"""
import secrets
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config_loader import ConfigurationLoader  # Import the class directly
from .config_bridge import ConfigBridge  # Import the new ConfigBridge
from .mqtt_service import MQTTService  # Import MQTT service
from .ai_provider import AIService
from .metrics_manager import MetricsManager
from .service_registry import ServiceRegistry, ReloadContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
ai_service: Optional[AIService] = None
mqtt_service: Optional[MQTTService] = None  # New: MQTT Service instance
metrics_manager: Optional[MetricsManager] = None
service_registry: Optional[ServiceRegistry] = None
config_loader_instance: Optional[ConfigurationLoader] = None  # Instance reference
service_metrics = {
    'start_time': time.time(),
    'total_requests': 0,
    'total_errors': 0,
    'provider_requests': {},
    'provider_errors': {},
    'provider_response_times': {},
    'provider_tokens': {},
    'provider_costs': {},
    'total_response_time': 0.0
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global ai_service, metrics_manager, service_registry, mqtt_service, config_loader_instance
    
    # Startup
    logger.info("Starting AICleaner v3 Core Service")
    
    try:
        # Initialize ConfigLoader with the container's config directory
        # This will load config.default.yaml and config.user.yaml from /config/
        config_loader_instance = ConfigurationLoader(config_dir="/config")

        # Initialize ConfigBridge to load options.json from /data/
        config_bridge = ConfigBridge(options_file_path=Path("/data/options.json"))
        addon_options_config = config_bridge.load_addon_options()

        # Initialize Service Registry
        service_registry = ServiceRegistry()

        # Set service registry in config loader
        config_loader_instance.set_service_registry(service_registry)

        # Load initial configuration, merging with addon options
        # This will trigger a reload through the service registry
        reload_context = await config_loader_instance.reload_configuration(new_config_data=addon_options_config)
        if reload_context.status != "completed":
            logger.error(f"Initial configuration load failed: {reload_context.errors}")
            raise ValueError(f"Initial configuration load failed: {'; '.join(reload_context.errors)}")

        config = config_loader_instance.load_configuration()  # Get the now-loaded config
        is_valid, errors = config_loader_instance.validate_configuration()
        if not is_valid:
            logger.error(f"Configuration validation failed: {errors}")
            raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
        
        # Initialize AI service
        ai_service = AIService(config_loader_instance)
        
        # Initialize Metrics Manager
        metrics_manager = MetricsManager(config)
        await metrics_manager.start_background_task()

        # Initialize MQTT Service
        mqtt_config = config_loader_instance.get_mqtt_config()
        mqtt_service = MQTTService(mqtt_config)
        await mqtt_service.connect()

        # Register services with the registry
        service_registry.register_service("config_loader", config_loader_instance)
        service_registry.register_service("ai_service", ai_service, dependencies=["config_loader"])
        service_registry.register_service("mqtt_service", mqtt_service, dependencies=["config_loader"])
        # metrics_manager doesn't implement Reloadable yet, could be added later
        
        logger.info("Core service initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize core service: {e}")
        raise
    
    yield
    
    # Shutdown
    if mqtt_service:
        await mqtt_service.disconnect()
    if metrics_manager:
        await metrics_manager.stop_background_task()
    
    logger.info("Shutting down AICleaner v3 Core Service")


# Create FastAPI app
app = FastAPI(
    title="AICleaner v3 Core Service",
    version="1.0.0",
    description="A simplified, power-user-focused API for AI inference, configuration, and monitoring.",
    lifespan=lifespan
)

# Add CORS middleware for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="The input text for the AI model")
    provider: Optional[str] = Field(None, description="AI provider to use (overrides default)")
    model: Optional[str] = Field(None, description="Specific model within the provider")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Controls randomness")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192, description="Maximum tokens to generate")
    provider_params: Optional[Dict[str, Any]] = Field(None, description="Provider-specific parameters")


class GenerateResponse(BaseModel):
    text: str = Field(..., description="The generated text")
    model: str = Field(..., description="The model used for generation")
    provider: str = Field(..., description="The provider used")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")
    cost: Dict[str, float] = Field(..., description="Cost information")
    response_time_ms: float = Field(..., description="Response time in milliseconds")


class StatusResponse(BaseModel):
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    providers: Dict[str, Dict[str, Any]] = Field(..., description="Provider status")
    mqtt: Dict[str, Any] = Field(..., description="MQTT status")


class MetricsResponse(BaseModel):
    uptime_seconds: float = Field(..., description="Service uptime")
    total_requests: int = Field(..., description="Total requests processed")
    requests_per_minute: float = Field(..., description="Requests per minute")
    average_response_time_ms: float = Field(..., description="Average response time")
    error_rate: float = Field(..., description="Percentage of failed requests")
    providers: Dict[str, Dict[str, Any]] = Field(..., description="Provider-specific metrics")
    costs: Dict[str, float] = Field(..., description="Cost breakdown")


class MqttDevice(BaseModel):
    id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="User-friendly device name")
    source: str = Field(..., description="How this device was configured")
    status: str = Field(..., description="Device status")
    topics: Dict[str, List[str]] = Field(..., description="Subscribe and publish topics")
    last_seen: Optional[str] = Field(None, description="Last seen timestamp")


class MqttDevicesResponse(BaseModel):
    discovered: List[MqttDevice] = Field(..., description="Auto-discovered devices")
    explicit: List[MqttDevice] = Field(..., description="Explicitly configured devices")
    total_count: int = Field(..., description="Total device count")


class ConfigResponse(BaseModel):
    ai_provider: str = Field(..., description="Default AI provider")
    providers: Dict[str, Dict[str, Any]] = Field(..., description="Provider configurations")
    mqtt: Dict[str, Any] = Field(..., description="MQTT configuration")
    performance: Dict[str, Any] = Field(..., description="Performance settings")


class ConfigRequest(BaseModel):
    ai_provider: Optional[str] = Field(None, description="Default AI provider")
    api_keys: Optional[Dict[str, str]] = Field(None, description="API keys for providers")
    mqtt: Optional[Dict[str, Any]] = Field(None, description="MQTT configuration")
    performance: Optional[Dict[str, Any]] = Field(None, description="Performance settings")


class ErrorResponse(BaseModel):
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# --- Middleware ---

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect basic metrics for all requests"""
    global service_metrics
    
    start_time = time.time()
    service_metrics['total_requests'] += 1
    
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        service_metrics['total_errors'] += 1
        raise
    finally:
        # Could add more detailed metrics here
        pass


# --- Security Helpers ---

def validate_api_key(key: str) -> bool:
    """
    Validates the API key format.
    Requires a minimum length to discourage weak keys.
    """
    return len(key) >= 32


def _deep_merge_config(source: Dict, destination: Dict) -> Dict:
    """
    Recursively merges two dictionaries.
    'source' is merged into 'destination'.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # Get node or create one
            node = destination.setdefault(key, {})
            _deep_merge_config(value, node)
        else:
            destination[key] = value
    return destination


# --- Authentication Dependency ---
async def get_api_key_or_allow_local(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    FastAPI dependency to enforce API key authentication for non-local requests,
    or allow all requests if API key authentication is disabled.
    """
    config = config_loader_instance.get_service_config() if config_loader_instance else {}
    api_config = config.get('api', {})
    api_key_enabled = api_config.get('api_key_enabled', False)
    configured_api_key = api_config.get('api_key')
    
    if not api_key_enabled:
        return  # API key authentication is disabled, allow all requests
    
    # Allow local requests without API key
    if request.client and request.client.host in ["127.0.0.1", "localhost"]:
        return
    
    # Validate key presence and format
    if not configured_api_key or not validate_api_key(configured_api_key):
        logger.warning("API key authentication is enabled, but the configured key is missing or invalid (must be at least 32 characters).")
        # Block requests until a valid key is configured
        raise HTTPException(status_code=503, detail="Service unavailable due to security misconfiguration.")
    
    # Securely compare the provided key with the configured key
    if not x_api_key or not secrets.compare_digest(x_api_key, configured_api_key):
        raise HTTPException(
            status_code=401, 
            detail="Invalid or missing API Key. Please provide a valid 'X-API-Key' header."
        )


# --- API Endpoints ---

@app.post("/v1/generate", response_model=GenerateResponse)
async def generate_text(request: GenerateRequest):
    """Generate text using specified AI provider and model configuration."""
    global ai_service, service_metrics, metrics_manager
    
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI service not initialized")
    
    try:
        # Prepare parameters
        kwargs = {}
        if request.temperature is not None:
            kwargs['temperature'] = request.temperature
        if request.max_tokens is not None:
            kwargs['max_tokens'] = request.max_tokens
        if request.provider_params:
            kwargs.update(request.provider_params)
        
        # Generate response
        response = await ai_service.generate(
            prompt=request.prompt,
            provider=request.provider,
            model=request.model,
            **kwargs
        )
        
        # Update metrics
        provider_name = response.provider
        if provider_name not in service_metrics['provider_requests']:
            service_metrics['provider_requests'][provider_name] = 0
            service_metrics['provider_response_times'][provider_name] = 0.0
            service_metrics['provider_tokens'][provider_name] = 0
            service_metrics['provider_costs'][provider_name] = 0.0
        
        service_metrics['provider_requests'][provider_name] += 1
        service_metrics['provider_response_times'][provider_name] += response.response_time_ms
        service_metrics['provider_tokens'][provider_name] += response.usage.get('total_tokens', 0)
        service_metrics['provider_costs'][provider_name] += response.cost.get('amount', 0.0)
        service_metrics['total_response_time'] += response.response_time_ms
        
        # Add snapshot to MetricsManager
        if metrics_manager:
            # Recalculate current service metrics for the snapshot
            uptime = time.time() - service_metrics['start_time']
            requests_per_minute = (service_metrics['total_requests'] / (uptime / 60)) if uptime > 0 else 0
            error_rate = (service_metrics['total_errors'] / service_metrics['total_requests'] * 100) if service_metrics['total_requests'] > 0 else 0
            avg_response_time = (service_metrics['total_response_time'] / service_metrics['total_requests']) if service_metrics['total_requests'] > 0 else 0

            current_service_metrics = {
                'uptime_seconds': uptime,
                'total_requests': service_metrics['total_requests'],
                'total_errors': service_metrics['total_errors'],
                'requests_per_minute': requests_per_minute,
                'average_response_time_ms': avg_response_time,
                'error_rate': error_rate,
            }
            metrics_manager.add_snapshot(current_service_metrics, ai_responses=[response])
        
        return GenerateResponse(
            text=response.text,
            model=response.model,
            provider=response.provider,
            usage=response.usage,
            cost=response.cost,
            response_time_ms=response.response_time_ms
        )
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/status", response_model=StatusResponse)
async def get_status():
    """Provides comprehensive status including AI provider health."""
    global ai_service, service_metrics
    
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI service not initialized")
    
    try:
        # Get provider status
        providers = await ai_service.get_provider_status()
        
        # Get MQTT status
        mqtt_config = config_loader_instance.get_mqtt_config() if config_loader_instance else {}
        mqtt_status = {
            'connected': mqtt_service.is_connected() if mqtt_service else False,  # Check actual connection
            'broker': f"{mqtt_config.get('broker', {}).get('host', 'localhost')}:{mqtt_config.get('broker', {}).get('port', 1883)}",
            'discovered_devices': len(mqtt_service.get_discovered_devices()) if mqtt_service else 0  # Count actual devices
        }
        
        # Calculate uptime
        uptime = time.time() - service_metrics['start_time']
        
        # Determine overall status
        available_providers = sum(1 for p in providers.values() if p.get('available', False))
        status = "ok" if available_providers > 0 else "degraded"
        
        return StatusResponse(
            status=status,
            version="1.0.0",
            uptime_seconds=uptime,
            providers=providers,
            mqtt=mqtt_status
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Retrieves detailed performance data including costs and provider breakdowns."""
    global service_metrics, metrics_manager
    
    if not metrics_manager:
        raise HTTPException(status_code=500, detail="Metrics service not initialized")
    
    try:
        # Get metrics summary from MetricsManager
        metrics_summary = metrics_manager.get_metrics_summary()

        # Calculate uptime from service_metrics for consistency with /status
        uptime = time.time() - service_metrics['start_time']
        requests_per_minute = (metrics_summary.get('total_requests', 0) / (uptime / 60)) if uptime > 0 else 0

        return MetricsResponse(
            uptime_seconds=uptime,
            total_requests=metrics_summary.get('total_requests', 0),
            requests_per_minute=requests_per_minute,
            average_response_time_ms=metrics_summary.get('average_response_time_ms', 0),
            error_rate=metrics_summary.get('error_rate', 0),
            providers=metrics_summary.get('provider_stats', {}),
            costs={'total_usd': metrics_summary.get('total_cost_usd', 0.0),
                   'by_provider': {p: s.get('total_cost', 0.0) for p, s in metrics_summary.get('provider_stats', {}).items()}}
        )
        
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/mqtt/devices", response_model=MqttDevicesResponse)
async def get_mqtt_devices():
    """Returns discovered and explicitly configured MQTT devices."""
    try:
        # Get MQTT configuration from the instance
        mqtt_config = config_loader_instance.get_mqtt_config() if config_loader_instance else {}
        explicit_devices = mqtt_config.get('devices', [])
        
        # Convert explicit devices to MqttDevice format
        explicit_mqtt_devices = []
        for device in explicit_devices:
            mqtt_device = MqttDevice(
                id=device.get('unique_id', device.get('name', 'unknown')),
                name=device.get('name', 'Unknown Device'),
                source='explicit',
                status='unknown',  # Would check actual status
                topics={
                    'subscribe': [device.get('state_topic', '')],
                    'publish': [device.get('command_topic', '')]
                }
            )
            explicit_mqtt_devices.append(mqtt_device)
        
        # Discovered devices
        discovered_devices = []  # This will be populated by monitoring_system via MQTT discovery
        if mqtt_service:
            # Get discovered devices from MQTT service
            discovered_devices.extend(mqtt_service.get_discovered_devices())
        
        return MqttDevicesResponse(
            discovered=discovered_devices,
            explicit=explicit_mqtt_devices,
            total_count=len(discovered_devices) + len(explicit_mqtt_devices)
        )
        
    except Exception as e:
        logger.error(f"MQTT device listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/config", response_model=ConfigResponse)
async def get_configuration():
    """Retrieves current service configuration with redacted secrets."""
    try:
        config = config_loader_instance.load_configuration() if config_loader_instance else {}
        
        # Build provider info with redacted secrets
        providers = {}
        ai_providers = config.get('ai_providers', {})
        for name, provider_config in ai_providers.items():
            providers[name] = {
                'enabled': True,
                'api_key_configured': bool(provider_config.get('api_key')),
                'models': list(provider_config.get('models', {}).keys())
            }
        
        # MQTT config with redacted credentials
        mqtt_config = config.get('mqtt', {})
        mqtt = {
            'host': mqtt_config.get('broker', {}).get('host', 'localhost'),
            'port': mqtt_config.get('broker', {}).get('port', 1883),
            'auto_discover': mqtt_config.get('auto_discovery', {}).get('enabled', True),
            'discovery_prefix': mqtt_config.get('auto_discovery', {}).get('topic_prefix', 'homeassistant')
        }
        
        # Performance config
        performance_config = config.get('performance', {})
        performance = {
            'cache_enabled': performance_config.get('cache', {}).get('enabled', True),
            'metrics_retention_days': performance_config.get('metrics_retention_days', 30)
        }
        
        return ConfigResponse(
            ai_provider=config.get('general', {}).get('active_provider', 'ollama'),
            providers=providers,
            mqtt=mqtt,
            performance=performance
        )
        
    except Exception as e:
        logger.error(f"Configuration retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/v1/config", dependencies=[Depends(get_api_key_or_allow_local)])
async def update_configuration(request: ConfigRequest):
    """Updates the service configuration using hot-reload system."""
    global ai_service, service_registry
    
    if not service_registry:
        raise HTTPException(status_code=500, detail="Service registry not initialized")
    
    try:
        logger.info("Configuration update requested")
        
        # Get current user configuration
        import os
        import yaml
        from pathlib import Path
        
        user_config_file = Path("/home/drewcifer/aicleaner_v3/core/config.user.yaml")
        
        # Load existing user config if it exists
        current_user_config = {}
        if user_config_file.exists():
            import aiofiles
            async with aiofiles.open(user_config_file, 'r') as f:
                content = await f.read()
                current_user_config = yaml.safe_load(content) or {}
        
        # Build the update dictionary from the request
        update_data = {}
        if request.ai_provider:
            update_data['general'] = {'active_provider': request.ai_provider}
        if request.api_keys:
            update_data['ai_providers'] = {
                provider: {'api_key': api_key} for provider, api_key in request.api_keys.items()
            }
        if request.mqtt:
            update_data['mqtt'] = request.mqtt
        if request.performance:
            update_data['performance'] = request.performance
        
        # Deep merge the update into the current configuration
        updated_config = _deep_merge_config(update_data, current_user_config)

        # Write updated configuration to user config file
        async with aiofiles.open(user_config_file, 'w') as f:
            config_content = yaml.dump(updated_config, default_flow_style=False, indent=2)
            await f.write(config_content)
        
        # Initiate hot-reload using the new system
        reload_context = await config_loader_instance.reload_configuration()
        
        if reload_context.status == "completed":
            logger.info(f"Configuration hot-reload completed successfully (version {reload_context.version})")
            # Return updated configuration (redacted)
            return await get_configuration()
        else:
            logger.error(f"Configuration hot-reload failed: {reload_context.errors}")
            raise HTTPException(
                status_code=500, 
                detail=f"Configuration reload failed: {'; '.join(reload_context.errors)}"
            )
        
    except Exception as e:
        logger.error(f"Configuration update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/config/reload/status")
async def get_reload_status():
    """Get the status of the current or last configuration reload operation."""
    global service_registry
    
    if not service_registry:
        raise HTTPException(status_code=500, detail="Service registry not initialized")
    
    try:
        reload_context = service_registry.get_current_reload_context()
        is_reload_in_progress = service_registry.is_reload_in_progress()
        
        if reload_context:
            return {
                "reload_in_progress": is_reload_in_progress,
                "current_context": {
                    "version": reload_context.version,
                    "status": reload_context.status,
                    "errors": reload_context.errors,
                    "start_time": reload_context.start_time
                },
                "config_version": config_loader_instance.get_config_version() if config_loader_instance else 0
            }
        else:
            return {
                "reload_in_progress": is_reload_in_progress,
                "current_context": None,
                "config_version": config_loader_instance.get_config_version() if config_loader_instance else 0
            }
    
    except Exception as e:
        logger.error(f"Failed to get reload status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/config/reload", dependencies=[Depends(get_api_key_or_allow_local)])
async def trigger_config_reload():
    """Manually trigger a configuration reload from files."""
    global service_registry
    
    if not service_registry:
        raise HTTPException(status_code=500, detail="Service registry not initialized")
    
    try:
        logger.info("Manual configuration reload triggered")
        
        # Trigger reload from files (no new config data provided)
        reload_context = await config_loader_instance.reload_configuration()
        
        return {
            "status": "success" if reload_context.status == "completed" else "failed",
            "reload_context": {
                "version": reload_context.version,
                "status": reload_context.status,
                "errors": reload_context.errors
            }
        }
        
    except Exception as e:
        logger.error(f"Manual configuration reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/services/registry")
async def get_service_registry_status():
    """Get status of all registered services in the registry."""
    global service_registry
    
    if not service_registry:
        raise HTTPException(status_code=500, detail="Service registry not initialized")
    
    try:
        services = {}
        for service_name in ["config_loader", "ai_service"]:
            service = service_registry.get_service(service_name)
            if service:
                services[service_name] = {
                    "registered": True,
                    "type": type(service).__name__
                }
            else:
                services[service_name] = {
                    "registered": False,
                    "type": None
                }
        
        return {
            "status": "success",
            "services": services,
            "reload_in_progress": service_registry.is_reload_in_progress()
        }
        
    except Exception as e:
        logger.error(f"Failed to get service registry status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Error Handlers ---

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'code': exc.status_code,
            'message': exc.detail,
            'details': getattr(exc, 'details', None)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            'code': 500,
            'message': 'Internal server error',
            'details': {'type': type(exc).__name__}
        }
    )


# --- Health Check ---

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}


# --- Provider Management Endpoints ---

@app.post("/v1/providers/switch", dependencies=[Depends(get_api_key_or_allow_local)])
async def switch_provider(request: Dict[str, str]):
    """Manually switch to a different AI provider"""
    global ai_service
    
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI service not initialized")
    
    provider_name = request.get('provider')
    if not provider_name:
        raise HTTPException(status_code=400, detail="Provider name required")
    
    try:
        # Validate provider exists and is available
        config = config_loader_instance.load_configuration() if config_loader_instance else {}
        ai_providers = config.get('ai_providers', {})
        
        if provider_name not in ai_providers:
            available_providers = list(ai_providers.keys())
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown provider '{provider_name}'. Available: {available_providers}"
            )
        
        # Check if provider is available
        if not ai_service.provider_registry.is_provider_available(provider_name):
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{provider_name}' is currently unavailable (circuit breaker open)"
            )
        
        # Update active provider in config and persist the change
        logger.info(f"Manually switching to provider: {provider_name}")
        previous_provider = config.get('general', {}).get('active_provider', 'unknown')
        
        # Load and update user configuration
        import os
        import yaml
        from pathlib import Path
        
        user_config_file = Path("/home/drewcifer/aicleaner_v3/core/config.user.yaml")
        
        # Load existing user config if it exists
        current_user_config = {}
        if user_config_file.exists():
            async with aiofiles.open(user_config_file, 'r') as f:
                content = await f.read()
                current_user_config = yaml.safe_load(content) or {}
        
        # Deep merge the provider switch into the current configuration
        update_data = {'general': {'active_provider': provider_name}}
        updated_config = _deep_merge_config(update_data, current_user_config)
        
        # Write updated configuration to user config file
        async with aiofiles.open(user_config_file, 'w') as f:
            config_content = yaml.dump(updated_config, default_flow_style=False, indent=2)
            await f.write(config_content)
        
        # Trigger hot-reload to apply the change
        if service_registry:
            reload_context = await config_loader_instance.reload_configuration()
            if reload_context.success:
                # Update ai_service with new active provider
                new_config = config_loader_instance.load_configuration()
                ai_service.config_loader = config_loader_instance
                logger.info(f"Successfully switched to provider: {provider_name}")
            else:
                logger.error(f"Hot-reload failed after provider switch: {reload_context.errors}")
                raise HTTPException(status_code=500, detail=f"Failed to apply provider switch: {reload_context.errors}")
        
        return {
            "status": "success",
            "message": f"Switched to provider: {provider_name}",
            "previous_provider": previous_provider,
            "new_provider": provider_name,
            "reloaded": True
        }
        
    except Exception as e:
        logger.error(f"Provider switch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/providers/status")
async def get_providers_status():
    """Get comprehensive provider status including health and performance"""
    global ai_service
    
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI service not initialized")
    
    try:
        # Get basic provider status
        provider_status = await ai_service.get_provider_status()
        
        # Get registry status (circuit breaker, performance)
        registry_status = ai_service.get_provider_registry_status()
        
        # Merge the data
        combined_status = {}
        for provider_name in provider_status.keys():
            combined_status[provider_name] = {
                **provider_status[provider_name],
                **registry_status.get(provider_name, {})
            }
        
        # Add any providers that are only in registry
        for provider_name in registry_status.keys():
            if provider_name not in combined_status:
                combined_status[provider_name] = registry_status[provider_name]
        
        return {
            "status": "success",
            "providers": combined_status,
            "total_providers": len(combined_status),
            "available_providers": len([p for p in combined_status.values() if p.get('available', False)])
        }
        
    except Exception as e:
        logger.error(f"Provider status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/providers/performance")
async def get_providers_performance():
    """Get detailed performance metrics for all providers"""
    global ai_service
    
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI service not initialized")
    
    try:
        registry_status = ai_service.get_provider_registry_status()
        
        performance_data = {}
        for provider_name, status in registry_status.items():
            performance_data[provider_name] = {
                'health_status': status.get('health_status'),
                'performance_score': status.get('performance_score', 0.0),
                'failure_count': status.get('failure_count', 0),
                'available': status.get('available', False)
            }
        
        return {
            "status": "success", 
            "performance_data": performance_data
        }
        
    except Exception as e:
        logger.error(f"Performance data retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/providers/recover", dependencies=[Depends(get_api_key_or_allow_local)])
async def recover_provider(request: Dict[str, str]):
    """Force recovery of a provider (reset circuit breaker)"""
    global ai_service
    
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI service not initialized")
    
    provider_name = request.get('provider')
    if not provider_name:
        raise HTTPException(status_code=400, detail="Provider name required")
    
    try:
        # Enable the provider (resets circuit breaker)
        ai_service.enable_provider(provider_name)
        
        logger.info(f"Manually recovered provider: {provider_name}")
        
        return {
            "status": "success",
            "message": f"Provider '{provider_name}' has been recovered",
            "provider": provider_name
        }
        
    except Exception as e:
        logger.error(f"Provider recovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Main ---

if __name__ == "__main__":
    import uvicorn
    
    # Get service configuration
    service_config = config_loader_instance.get_service_config() if config_loader_instance else {}
    api_config = service_config.get('api', {})
    
    host = api_config.get('host', '0.0.0.0')
    port = api_config.get('port', 8000)
    
    logger.info(f"Starting AICleaner v3 Core Service on {host}:{port}")
    
    uvicorn.run(
        "core.service:app",
        host=host,
        port=port,
        reload=False,  # Set to True for development
        log_level="info"
    )