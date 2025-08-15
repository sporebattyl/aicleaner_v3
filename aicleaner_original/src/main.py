"""
AICleaner V3 Main Application
PDCA-based orchestration with visual annotations and privacy spectrum
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

from core.orchestrator import PDCAOrchestrator, AnalysisRequest
from core.privacy_engine import PrivacyLevel
from config.loader import ConfigurationManager, ConfigValidationError
from config.schema import AICleanerConfig, GeminiConfig, OllamaConfig
from providers.gemini_provider import GeminiProvider, GeminiProviderFactory
from providers.ollama_provider import OllamaProvider, OllamaProviderFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/data/aicleaner.log') if Path('/data').exists() else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

class AICleanerApplication:
    """
    Main AICleaner V3 application with PDCA orchestration
    Manages the complete lifecycle and integration of all components
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config_manager = ConfigurationManager(config_path)
        self.config: Optional[AICleanerConfig] = None
        self.orchestrator: Optional[PDCAOrchestrator] = None
        
        # Component tracking
        self.providers: Dict[str, Any] = {}
        self.running = False
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self.startup_time: Optional[float] = None
        self.request_count = 0
        
        logger.info("AICleaner V3 Application initialized")
    
    async def initialize(self) -> None:
        """Initialize the application with full PDCA methodology"""
        logger.info("🚀 Starting AICleaner V3 initialization...")
        start_time = time.time()
        
        try:
            # PLAN: Load and validate configuration
            await self._pdca_plan_initialization()
            
            # DO: Initialize all components
            await self._pdca_do_initialization()
            
            # CHECK: Verify all components are working
            await self._pdca_check_initialization()
            
            # ACT: Finalize setup and log status
            await self._pdca_act_initialization()
            
            self.startup_time = time.time() - start_time
            logger.info(f"✅ AICleaner V3 initialized successfully in {self.startup_time:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise
    
    async def _pdca_plan_initialization(self) -> None:
        """PLAN: Load configuration and validate requirements"""
        logger.info("📋 PLAN: Loading configuration and validating requirements")
        
        # Load configuration
        try:
            self.config = self.config_manager.load_configuration()
        except ConfigValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        
        # Validate runtime requirements
        issues = self.config_manager.validate_runtime_requirements()
        if issues:
            for issue in issues:
                logger.warning(f"Configuration issue: {issue}")
            
            # Check if we have any working providers
            has_working_provider = False
            for name, provider_config in self.config.providers.items():
                if isinstance(provider_config, GeminiConfig):
                    if provider_config.api_key and provider_config.api_key != "your-gemini-api-key-here":
                        has_working_provider = True
                        break
                elif isinstance(provider_config, OllamaConfig):
                    # Assume Ollama could work (will check in DO phase)
                    has_working_provider = True
                    break
            
            if not has_working_provider:
                raise ConfigValidationError("No working providers configured")
        
        logger.info(f"✓ Configuration loaded with {len(self.config.providers)} providers")
    
    async def _pdca_do_initialization(self) -> None:
        """DO: Initialize all components and providers"""
        logger.info("🔧 DO: Initializing components and providers")
        
        # Initialize providers
        await self._initialize_providers()
        
        # Initialize orchestrator with providers
        await self._initialize_orchestrator()
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info("✓ All components initialized")
    
    async def _initialize_providers(self) -> None:
        """Initialize all configured providers"""
        logger.info("Initializing LLM providers...")
        
        for name, provider_config in self.config.providers.items():
            try:
                if isinstance(provider_config, GeminiConfig):
                    provider = GeminiProviderFactory.create_provider(provider_config.dict())
                    self.providers[name] = provider
                    logger.info(f"✓ Initialized Gemini provider: {name}")
                    
                elif isinstance(provider_config, OllamaConfig):
                    provider = await OllamaProviderFactory.create_and_verify(provider_config.dict())
                    if provider:
                        self.providers[name] = provider
                        logger.info(f"✓ Initialized Ollama provider: {name}")
                    else:
                        logger.warning(f"⚠️ Failed to initialize Ollama provider: {name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize provider {name}: {e}")
        
        if not self.providers:
            raise RuntimeError("No providers successfully initialized")
        
        logger.info(f"✓ Initialized {len(self.providers)} providers")
    
    async def _initialize_orchestrator(self) -> None:
        """Initialize the PDCA orchestrator"""
        logger.info("Initializing PDCA orchestrator...")
        
        orchestrator_config = {
            'privacy': self.config.privacy.dict(),
            'annotation': self.config.annotation.dict(),
            'system': self.config.system.dict()
        }
        
        self.orchestrator = PDCAOrchestrator(orchestrator_config)
        
        # Register all providers with orchestrator
        for name, provider in self.providers.items():
            self.orchestrator.register_provider(provider)
        
        logger.info("✓ PDCA orchestrator initialized with all providers")
    
    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def _pdca_check_initialization(self) -> None:
        """CHECK: Verify all components are working correctly"""
        logger.info("🔍 CHECK: Verifying component health")
        
        # Check provider health
        healthy_providers = 0
        for name, provider in self.providers.items():
            try:
                health = await provider.health_check()
                if health.status.value in ['healthy', 'degraded']:
                    healthy_providers += 1
                    logger.info(f"✓ Provider {name} is {health.status.value}")
                else:
                    logger.warning(f"⚠️ Provider {name} is unhealthy: {health.error_message}")
            except Exception as e:
                logger.error(f"❌ Health check failed for provider {name}: {e}")
        
        if healthy_providers == 0:
            raise RuntimeError("No healthy providers available")
        
        # Verify orchestrator
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        logger.info(f"✓ {healthy_providers}/{len(self.providers)} providers are healthy")
    
    async def _pdca_act_initialization(self) -> None:
        """ACT: Finalize initialization and log status"""
        logger.info("🎯 ACT: Finalizing initialization")
        
        # Log final status
        self._log_system_status()
        
        # Set running flag
        self.running = True
        
        logger.info("✅ Application ready to process requests")
    
    def _log_system_status(self) -> None:
        """Log comprehensive system status"""
        logger.info("=== AICleaner V3 Status ===")
        logger.info(f"Privacy Level: {self.config.privacy.default_level.value} ({self.config.get_privacy_description()})")
        logger.info(f"Primary Provider: {self.config.primary_provider}")
        logger.info(f"Fallback Providers: {', '.join(self.config.fallback_providers)}")
        logger.info(f"Debug Mode: {self.config.system.debug_mode}")
        logger.info(f"Visual Annotations: {self.config.annotation.enable_annotations}")
        logger.info(f"Auto Dashboard: {self.config.system.auto_dashboard}")
        logger.info("========================")
    
    async def analyze_image(
        self, 
        image_bytes: bytes, 
        prompt: str = "Analyze this image for cleaning tasks",
        privacy_level: Optional[PrivacyLevel] = None,
        preferred_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze an image for cleaning tasks using PDCA orchestration
        
        Args:
            image_bytes: Image data to analyze
            prompt: Analysis prompt
            privacy_level: Override default privacy level
            preferred_provider: Preferred provider name
            
        Returns:
            Dictionary containing tasks, annotations, and processing info
        """
        if not self.running or not self.orchestrator:
            raise RuntimeError("Application not initialized")
        
        self.request_count += 1
        start_time = time.time()
        
        logger.info(f"📸 Processing analysis request #{self.request_count}")
        
        # Use default privacy level if not specified
        if privacy_level is None:
            privacy_level = self.config.privacy.default_level
        
        # Create analysis request
        request = AnalysisRequest(
            image_bytes=image_bytes,
            prompt=prompt,
            privacy_level=privacy_level,
            preferred_provider=preferred_provider,
            metadata={
                'request_id': self.request_count,
                'timestamp': time.time()
            }
        )
        
        try:
            # Process through PDCA orchestrator
            result = await self.orchestrator.process_analysis_request(request)
            
            processing_time = time.time() - start_time
            
            logger.info(
                f"✅ Analysis completed in {processing_time:.2f}s: "
                f"{len(result.tasks)} tasks, provider: {result.provider_used}"
            )
            
            # Return comprehensive result
            return {
                'success': True,
                'request_id': self.request_count,
                'tasks': [
                    {
                        'description': task.description,
                        'priority': task.priority,
                        'confidence': task.confidence,
                        'estimated_duration': task.estimated_duration,
                        'annotation': {
                            'x1': task.annotation.x1,
                            'y1': task.annotation.y1,
                            'x2': task.annotation.x2,
                            'y2': task.annotation.y2
                        } if task.annotation else None
                    }
                    for task in result.tasks
                ],
                'annotated_image_base64': result.annotated_image.decode('base64') if result.annotated_image else None,
                'processing_summary': result.processing_summary,
                'privacy_level': privacy_level.value,
                'provider_used': result.provider_used,
                'fallback_used': result.fallback_used,
                'processing_time': result.total_processing_time
            }
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'request_id': self.request_count,
                'processing_time': time.time() - start_time
            }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information"""
        if not self.orchestrator:
            return {'status': 'not_initialized'}
        
        # Get provider health
        provider_health = {}
        for name, provider in self.providers.items():
            try:
                health = await provider.health_check()
                provider_health[name] = {
                    'status': health.status.value,
                    'response_time': health.response_time,
                    'error_message': health.error_message,
                    'last_checked': health.last_checked
                }
            except Exception as e:
                provider_health[name] = {
                    'status': 'error',
                    'error_message': str(e)
                }
        
        # Get performance metrics
        performance = self.orchestrator.get_performance_metrics()
        
        return {
            'status': 'healthy' if any(p['status'] in ['healthy', 'degraded'] for p in provider_health.values()) else 'unhealthy',
            'uptime': time.time() - self.startup_time if self.startup_time else 0,
            'requests_processed': self.request_count,
            'providers': provider_health,
            'performance': performance,
            'configuration': {
                'privacy_level': self.config.privacy.default_level.value,
                'primary_provider': self.config.primary_provider,
                'debug_mode': self.config.system.debug_mode
            }
        }
    
    async def run_forever(self) -> None:
        """Run the application until shutdown signal"""
        logger.info("🔄 Application running - waiting for shutdown signal...")
        
        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Graceful application shutdown"""
        logger.info("🛑 Starting graceful shutdown...")
        
        self.running = False
        
        # Shutdown orchestrator
        if self.orchestrator:
            await self.orchestrator.shutdown()
        
        # Close all providers
        for name, provider in self.providers.items():
            try:
                if hasattr(provider, 'close'):
                    await provider.close()
                logger.info(f"✓ Closed provider: {name}")
            except Exception as e:
                logger.error(f"Error closing provider {name}: {e}")
        
        logger.info("✅ Shutdown complete")

async def main():
    """Main application entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AICleaner V3 - AI-powered cleaning task analysis')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--validate-only', action='store_true', help='Validate configuration and exit')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Create and initialize application
    app = AICleanerApplication(args.config)
    
    try:
        await app.initialize()
        
        if args.validate_only:
            logger.info("✅ Configuration validation successful")
            return 0
        
        # Run application
        await app.run_forever()
        return 0
        
    except ConfigValidationError as e:
        logger.error(f"❌ Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        return 0
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))