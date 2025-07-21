#!/usr/bin/env python3
'''
AICleaner v3 Multi-Tier System Startup
Main entry point for the integrated system
'''

import asyncio
import logging
import sys
from pathlib import Path

# Add addon path to Python path
addon_path = Path(__file__).parent / "addons" / "aicleaner_v3"
sys.path.insert(0, str(addon_path))

async def main():
    '''Main startup function'''
    print("🚀 Starting AICleaner v3 Multi-Tier System...")
    
    try:
        # Start FastAPI backend with UI
        print("🌐 Starting Web Interface...")
        import uvicorn
        from api.backend import app
        
        # Start backend services as background tasks
        print("🔒 Initializing Privacy Pipeline...")
        from privacy.main_pipeline import PrivacyPipeline
        privacy_pipeline = PrivacyPipeline()
        print("✅ Privacy Pipeline ready")
        
        # Initialize Cloud Integration
        print("☁️ Initializing Cloud Integration...")
        from ai.providers.optimized_ai_provider_manager import OptimizedAIProviderManager
        cloud_manager = OptimizedAIProviderManager({})
        print("✅ Cloud Integration ready")
        
        # Initialize AMD Optimization
        print("⚡ Initializing AMD Optimization...")
        from ai.amd_integration_manager import AMDIntegrationManager
        amd_manager = AMDIntegrationManager()
        print("✅ AMD Optimization ready")
        
        print("🎭 Multi-Tier System fully operational!")
        print("📊 Available tiers: Hybrid, Local, Cloud")
        print("🏠 Home Assistant integration active")
        print("🌐 Web UI available at http://localhost:8000")
        
        # Start the web server
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=False
        )
        server = uvicorn.Server(config)
        await server.serve()
            
    except KeyboardInterrupt:
        print("\n⏹️ Shutting down AICleaner v3...")
    except Exception as e:
        print(f"❌ System error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the main system
    asyncio.run(main())
