import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
import hashlib

from ..config.loader import ConfigurationLoader
from ..config.schema import AICleanerConfig, ProviderType
from ..providers.base_provider import (
    LLMProvider, 
    AnalysisResult, 
    ProviderHealth, 
    ProviderStatus, 
    PrivacyLevel
)
from ..providers.gemini_provider import GeminiProvider
from .health import HealthMonitor

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics for image processing session."""
    total_images: int = 0
    processed_images: int = 0
    kept_images: int = 0
    deleted_images: int = 0
    failed_images: int = 0
    total_processing_time: float = 0.0
    start_time: float = field(default_factory=time.time)
    
    @property
    def completion_rate(self) -> float:
        return self.processed_images / max(self.total_images, 1)
    
    @property
    def average_processing_time(self) -> float:
        return self.total_processing_time / max(self.processed_images, 1)
    
    @property
    def deletion_rate(self) -> float:
        return self.deleted_images / max(self.processed_images, 1)


@dataclass
class ImageProcessingTask:
    """Represents a single image processing task."""
    file_path: Path
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        self.file_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """Calculate SHA-256 hash of the image file."""
        try:
            with open(self.file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]  # First 16 chars
        except Exception:
            return f"error_{int(time.time())}"


class ProviderRegistry:
    """Registry for managing LLM providers with health monitoring."""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.health_status: Dict[str, ProviderHealth] = {}
        self.failure_counts: Dict[str, int] = {}
        self.last_health_check: Dict[str, float] = {}
        
    def register_provider(self, provider_type: str, provider: LLMProvider) -> None:
        """Register a provider in the registry."""
        self.providers[provider_type] = provider
        self.failure_counts[provider_type] = 0
        logger.info(f"Registered provider: {provider_type}")
        
    async def initialize_providers(self) -> List[str]:
        """Initialize all registered providers and return list of successful ones."""
        successful_providers = []
        
        for provider_type, provider in self.providers.items():
            try:
                logger.info(f"Initializing provider: {provider_type}")
                success = await provider.initialize()
                if success:
                    successful_providers.append(provider_type)
                    logger.info(f"Provider {provider_type} initialized successfully")
                else:
                    logger.error(f"Provider {provider_type} initialization failed")
                    
            except Exception as e:
                logger.error(f"Provider {provider_type} initialization error: {e}")
                
        return successful_providers
    
    async def health_check_all(self, config: AICleanerConfig) -> Dict[str, ProviderHealth]:
        """Perform health checks on all providers."""
        results = {}
        
        for provider_type, provider in self.providers.items():
            try:
                health = await provider.health_check()
                self.health_status[provider_type] = health
                self.last_health_check[provider_type] = time.time()
                
                # Update failure count based on health status
                if health.status in [ProviderStatus.UNHEALTHY, ProviderStatus.OFFLINE]:
                    self.failure_counts[provider_type] += 1
                else:
                    self.failure_counts[provider_type] = 0
                    
                results[provider_type] = health
                logger.debug(f"Health check {provider_type}: {health.status.value}")
                
            except Exception as e:
                logger.error(f"Health check failed for {provider_type}: {e}")
                error_health = ProviderHealth(
                    status=ProviderStatus.OFFLINE,
                    response_time_ms=0.0,
                    error_rate=1.0,
                    last_check=time.time(),
                    error_message=str(e)
                )
                self.health_status[provider_type] = error_health
                self.failure_counts[provider_type] += 1
                results[provider_type] = error_health
                
        return results
    
    def get_healthy_providers(self, config: AICleanerConfig) -> List[str]:
        """Get list of healthy providers in priority order."""
        healthy = []
        
        for provider_type in config.provider_priority:
            provider_key = provider_type.value
            
            # Check if provider is registered
            if provider_key not in self.providers:
                continue
                
            # Check failure count
            if self.failure_counts.get(provider_key, 0) >= config.health.max_failures:
                logger.debug(f"Provider {provider_key} exceeded max failures")
                continue
                
            # Check health status
            health = self.health_status.get(provider_key)
            if health and health.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]:
                healthy.append(provider_key)
                
        return healthy
    
    def get_provider(self, provider_type: str) -> Optional[LLMProvider]:
        """Get provider instance by type."""
        return self.providers.get(provider_type)
    
    async def cleanup_all(self) -> None:
        """Clean up all providers."""
        for provider_type, provider in self.providers.items():
            try:
                await provider.cleanup()
                logger.info(f"Cleaned up provider: {provider_type}")
            except Exception as e:
                logger.error(f"Cleanup failed for {provider_type}: {e}")


class AICleanerOrchestrator:
    """Core orchestrator for AI Cleaner with provider management and health monitoring."""
    
    def __init__(self, config_loader: Optional[ConfigurationLoader] = None):
        self.config_loader = config_loader or ConfigurationLoader()
        self.config: Optional[AICleanerConfig] = None
        self.provider_registry = ProviderRegistry()
        self.health_monitor: Optional[HealthMonitor] = None
        self.stats = ProcessingStats()
        self._shutdown_event = asyncio.Event()
        self._processing_semaphore: Optional[asyncio.Semaphore] = None
        
    async def initialize(self, config_path: Optional[str] = None) -> bool:
        """Initialize the orchestrator with configuration and providers."""
        try:
            # Load configuration
            self.config = await self.config_loader.load_config(config_path)
            logger.info("Configuration loaded successfully")
            
            # Set up processing semaphore based on batch size
            self._processing_semaphore = asyncio.Semaphore(self.config.processing.batch_size)
            
            # Initialize health monitor
            self.health_monitor = HealthMonitor(self.config)
            
            # Register providers based on configuration
            await self._register_providers()
            
            # Initialize providers
            successful_providers = await self.provider_registry.initialize_providers()
            if not successful_providers:
                logger.error("No providers initialized successfully")
                return False
                
            logger.info(f"Initialized providers: {successful_providers}")
            
            # Start comprehensive health monitoring
            await self._start_health_monitoring()
            
            logger.info("Orchestrator initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Orchestrator initialization failed: {e}")
            return False
    
    async def _register_providers(self) -> None:
        """Register providers based on configuration."""
        # Register Gemini provider if configured
        if self.config.gemini and ProviderType.GEMINI in self.config.provider_priority:
            gemini_config = {
                'api_key': self.config.gemini.api_key,
                'model': self.config.gemini.model,
                'max_retries': self.config.gemini.max_retries,
                'timeout': self.config.gemini.timeout
            }
            gemini_provider = GeminiProvider(gemini_config)
            self.provider_registry.register_provider("gemini", gemini_provider)
            # Also register with health monitor for comprehensive tracking
            self.health_monitor.register_provider("gemini", gemini_provider)
        
        # TODO: Register Ollama provider when implemented
        # if self.config.ollama and ProviderType.OLLAMA in self.config.provider_priority:
        #     ollama_config = {...}
        #     ollama_provider = OllamaProvider(ollama_config)
        #     self.provider_registry.register_provider("ollama", ollama_provider)
    
    async def _start_health_monitoring(self) -> None:
        """Start comprehensive health monitoring system."""
        if self.health_monitor:
            await self.health_monitor.start_monitoring(self.provider_registry)
            logger.info("Comprehensive health monitoring started")
    
    async def process_images(self, image_paths: List[Path], 
                           progress_callback: Optional[callable] = None) -> ProcessingStats:
        """Process a batch of images with provider failover and health monitoring."""
        
        # Initialize statistics
        self.stats = ProcessingStats()
        self.stats.total_images = len(image_paths)
        self.stats.start_time = time.time()
        
        logger.info(f"Starting processing of {len(image_paths)} images")
        
        # Create processing tasks
        tasks = [
            ImageProcessingTask(path, priority=i) 
            for i, path in enumerate(image_paths)
        ]
        
        # Process images with controlled concurrency
        semaphore = asyncio.Semaphore(self.config.processing.batch_size)
        processing_tasks = [
            self._process_single_image(task, semaphore, progress_callback)
            for task in tasks
        ]
        
        # Wait for all processing to complete
        results = await asyncio.gather(*processing_tasks, return_exceptions=True)
        
        # Update final statistics
        self.stats.total_processing_time = time.time() - self.stats.start_time
        
        logger.info(f"Processing complete. Processed: {self.stats.processed_images}, "
                   f"Kept: {self.stats.kept_images}, Deleted: {self.stats.deleted_images}, "
                   f"Failed: {self.stats.failed_images}")
        
        return self.stats
    
    async def _process_single_image(self, task: ImageProcessingTask, 
                                  semaphore: asyncio.Semaphore,
                                  progress_callback: Optional[callable] = None) -> Optional[AnalysisResult]:
        """Process a single image with provider failover."""
        
        async with semaphore:
            start_time = time.time()
            
            try:
                # Validate image file
                if not self._validate_image_file(task.file_path):
                    self.stats.failed_images += 1
                    logger.warning(f"Invalid image file: {task.file_path}")
                    return None
                
                # Load image data
                image_data = await self._load_image_data(task.file_path)
                if not image_data:
                    self.stats.failed_images += 1
                    return None
                
                # Get analysis result with provider failover
                result = await self._analyze_with_failover(image_data, task)
                
                # Update statistics
                processing_time = time.time() - start_time
                self.stats.processed_images += 1
                self.stats.total_processing_time += processing_time
                
                if result.action == "delete":
                    self.stats.deleted_images += 1
                else:
                    self.stats.kept_images += 1
                
                # Report progress
                if progress_callback:
                    await progress_callback(task.file_path, result, self.stats)
                
                logger.debug(f"Processed {task.file_path}: {result.action} "
                           f"(confidence: {result.confidence:.2f}, time: {processing_time:.2f}s)")
                
                return result
                
            except Exception as e:
                self.stats.failed_images += 1
                logger.error(f"Failed to process {task.file_path}: {e}")
                return None
    
    def _validate_image_file(self, file_path: Path) -> bool:
        """Validate image file format and size."""
        try:
            # Check if file exists
            if not file_path.exists():
                return False
            
            # Check file extension
            file_ext = file_path.suffix.lower().lstrip('.')
            if file_ext not in self.config.processing.supported_formats:
                logger.debug(f"Unsupported format: {file_ext}")
                return False
            
            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.config.processing.max_image_size_mb:
                logger.debug(f"File too large: {file_size_mb:.2f}MB > {self.config.processing.max_image_size_mb}MB")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating {file_path}: {e}")
            return False
    
    async def _load_image_data(self, file_path: Path) -> Optional[bytes]:
        """Load image data from file."""
        try:
            # Use asyncio to avoid blocking
            loop = asyncio.get_event_loop()
            image_data = await loop.run_in_executor(
                None, lambda: file_path.read_bytes()
            )
            return image_data
        except Exception as e:
            logger.error(f"Failed to load image {file_path}: {e}")
            return None
    
    async def _analyze_with_failover(self, image_data: bytes, task: ImageProcessingTask) -> AnalysisResult:
        """Analyze image with automatic provider failover."""
        
        # Get list of healthy providers in priority order from health monitor
        if self.health_monitor:
            healthy_providers = self.health_monitor.get_healthy_providers()
        else:
            # Fallback to registry method if health monitor not available
            healthy_providers = self.provider_registry.get_healthy_providers(self.config)
        
        if not healthy_providers:
            logger.error("No healthy providers available")
            return AnalysisResult(
                action="keep",  # Conservative default
                confidence=0.0,
                reasoning="No healthy providers available",
                metadata={"error": "no_providers"},
                processing_time=0.0
            )
        
        # Try each healthy provider in order
        for provider_type in healthy_providers:
            provider = self.provider_registry.get_provider(provider_type)
            if not provider:
                continue
                
            try:
                # Check if provider supports the configured privacy level
                if not await provider.supports_privacy_level(self.config.processing.privacy_level):
                    logger.debug(f"Provider {provider_type} doesn't support privacy level {self.config.processing.privacy_level}")
                    continue
                
                # Attempt analysis
                result = await provider.analyze(
                    image_data=image_data,
                    prompt=self.config.analysis_prompt,
                    privacy_level=self.config.processing.privacy_level
                )
                
                # Validate result
                if self._validate_analysis_result(result):
                    logger.debug(f"Successful analysis with provider: {provider_type}")
                    return result
                else:
                    logger.warning(f"Invalid result from provider {provider_type}")
                    
            except Exception as e:
                logger.error(f"Analysis failed with provider {provider_type}: {e}")
                # Provider will be marked unhealthy in next health check
                continue
        
        # All providers failed - return conservative default
        logger.error(f"All providers failed for image: {task.file_path}")
        return AnalysisResult(
            action="keep",  # Conservative default
            confidence=0.0,
            reasoning="All provider attempts failed",
            metadata={"error": "all_providers_failed", "retry_count": task.retry_count},
            processing_time=0.0
        )
    
    def _validate_analysis_result(self, result: AnalysisResult) -> bool:
        """Validate analysis result for basic sanity checks."""
        try:
            # Check required fields
            if not result.action or result.action not in ["keep", "delete"]:
                return False
            
            if not isinstance(result.confidence, (int, float)) or not (0.0 <= result.confidence <= 1.0):
                return False
            
            if not result.reasoning or not isinstance(result.reasoning, str):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def get_system_status(self) -> Dict[str, any]:
        """Get current system status and health information."""
        if not self.config:
            return {"status": "not_initialized"}
        
        # Get comprehensive system status from health monitor
        if self.health_monitor:
            system_summary = self.health_monitor.get_system_performance_summary()
            healthy_providers = self.health_monitor.get_healthy_providers()
            provider_health = {
                provider: {
                    "status": health.current_health.status.value,
                    "response_time_ms": health.current_health.response_time_ms,
                    "error_rate": health.current_health.error_rate,
                    "last_check": health.current_health.last_check,
                    "error_message": health.current_health.error_message,
                    "availability": health.get_availability(),
                    "circuit_state": health.circuit_state.value,
                    "degradation_trend": health.degradation_trend,
                    "improvement_trend": health.improvement_trend
                }
                for provider, health in self.health_monitor.get_all_provider_metrics().items()
            }
        else:
            # Fallback to basic health check
            health_status = await self.provider_registry.health_check_all(self.config)
            healthy_providers = self.provider_registry.get_healthy_providers(self.config)
            provider_health = {
                provider: {
                    "status": health.status.value,
                    "response_time_ms": health.response_time_ms,
                    "error_rate": health.error_rate,
                    "last_check": health.last_check,
                    "error_message": health.error_message
                }
                for provider, health in health_status.items()
            }
        
        return {
            "status": "healthy" if healthy_providers else "degraded",
            "initialized": True,
            "healthy_providers": healthy_providers,
            "provider_health": provider_health,
            "processing_stats": {
                "total_images": self.stats.total_images,
                "processed_images": self.stats.processed_images,
                "kept_images": self.stats.kept_images,
                "deleted_images": self.stats.deleted_images,
                "failed_images": self.stats.failed_images,
                "completion_rate": self.stats.completion_rate,
                "deletion_rate": self.stats.deletion_rate,
                "average_processing_time": self.stats.average_processing_time
            },
            "configuration": {
                "privacy_level": self.config.processing.privacy_level.value,
                "batch_size": self.config.processing.batch_size,
                "max_image_size_mb": self.config.processing.max_image_size_mb,
                "provider_priority": [p.value for p in self.config.provider_priority]
            }
        }
    
    async def update_configuration(self, new_config: Dict[str, any]) -> bool:
        """Update configuration dynamically."""
        try:
            # Create temporary config loader to validate new config
            temp_config = AICleanerConfig(**new_config)
            
            # Update current configuration
            self.config = temp_config
            
            # Update processing semaphore if batch size changed
            self._processing_semaphore = asyncio.Semaphore(self.config.processing.batch_size)
            
            logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Graceful shutdown of the orchestrator."""
        logger.info("Shutting down orchestrator...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Stop comprehensive health monitoring
        if self.health_monitor:
            await self.health_monitor.stop_monitoring()
        
        # Clean up providers
        await self.provider_registry.cleanup_all()
        
        logger.info("Orchestrator shutdown complete")
    
    async def get_health_status_for_ha(self) -> Dict[str, Any]:
        """Get health status formatted for Home Assistant integration."""
        if self.health_monitor:
            return self.health_monitor.get_health_status_for_ha()
        return {"state": "unknown", "attributes": {"error": "Health monitor not available"}}
    
    async def force_health_check(self) -> Dict[str, ProviderHealth]:
        """Force an immediate health check on all providers."""
        if self.health_monitor:
            return await self.health_monitor.force_health_check(self.provider_registry)
        # Fallback to basic health check
        return await self.provider_registry.health_check_all(self.config)
    
    def get_provider_metrics(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive metrics for a specific provider."""
        if self.health_monitor:
            metrics = self.health_monitor.get_provider_metrics(provider_name)
            return metrics.get_performance_summary() if metrics else None
        return None
    
    def reset_circuit_breaker(self, provider_name: str) -> bool:
        """Manually reset circuit breaker for a provider."""
        if self.health_monitor:
            return self.health_monitor.reset_circuit_breaker(provider_name)
        return False
    
    def export_health_history(self) -> Dict[str, Any]:
        """Export health history for analysis or backup."""
        if self.health_monitor:
            return self.health_monitor.export_health_history()
        return {"error": "Health monitor not available"}