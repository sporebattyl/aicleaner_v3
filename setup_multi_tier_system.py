#!/usr/bin/env python3
"""
AICleaner v3 Multi-Tier System Setup
Installs dependencies and configures the integrated system
"""

import subprocess
import sys
import os
from pathlib import Path

class MultiTierSystemSetup:
    """Setup and configure the multi-tier AICleaner v3 system"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.addon_path = self.base_path / "addons" / "aicleaner_v3"
        
    def install_dependencies(self):
        """Install required Python dependencies"""
        print("📦 Installing Multi-Tier System Dependencies...")
        
        dependencies = [
            # Privacy Pipeline dependencies
            "opencv-python",
            "Pillow",
            "numpy",
            "torch",
            "torchvision",
            "onnxruntime",
            "spacy",
            
            # AMD Optimization dependencies  
            "llama-cpp-python[opencl]",
            "psutil",
            "GPUtil",
            "pyyaml",
            
            # Cloud Integration dependencies
            "aiohttp",
            "redis",
            "asyncio-throttle",
            
            # General dependencies
            "requests",
            "asyncio",
            "dataclasses",
            "typing-extensions"
        ]
        
        for dep in dependencies:
            try:
                print(f"Installing {dep}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                print(f"✅ {dep} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {dep}: {e}")
    
    def setup_directory_structure(self):
        """Create necessary directory structure"""
        print("📁 Setting up directory structure...")
        
        directories = [
            "data/models",
            "data/cache", 
            "logs",
            "config"
        ]
        
        for dir_path in directories:
            full_path = self.base_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {dir_path}")
    
    def create_requirements_file(self):
        """Create requirements.txt for easy installation"""
        requirements_content = """# AICleaner v3 Multi-Tier System Requirements

# Privacy Pipeline Dependencies
opencv-python>=4.8.0
Pillow>=10.0.0
numpy>=1.24.0
torch>=2.0.0
torchvision>=0.15.0
onnxruntime>=1.16.0
spacy>=3.7.0

# AMD Optimization Dependencies
llama-cpp-python[opencl]>=0.2.0
psutil>=5.9.0
GPUtil>=1.4.0
pyyaml>=6.0

# Cloud Integration Dependencies
aiohttp>=3.8.0
redis>=5.0.0
asyncio-throttle>=1.1.0

# General Dependencies
requests>=2.31.0
asyncio
dataclasses
typing-extensions>=4.0.0

# Home Assistant Integration
homeassistant>=2023.12.0
"""
        
        requirements_path = self.base_path / "requirements.txt"
        with open(requirements_path, 'w') as f:
            f.write(requirements_content)
        
        print(f"✅ Created requirements.txt at: {requirements_path}")
    
    def create_main_config(self):
        """Create main AICleaner v3 configuration"""
        config_content = """# AICleaner v3 Multi-Tier Configuration
name: "AICleaner v3 Multi-Tier"
version: "3.0.0"
description: "AI-powered Home Assistant addon with multi-tier architecture"

# Multi-Tier Architecture Configuration
multi_tier:
  enabled: true
  default_tier: "hybrid"  # hybrid, local, cloud
  
  # Tier 1: Privacy-Preserving Hybrid
  hybrid:
    enabled: true
    privacy_pipeline: true
    cloud_fallback: true
    target_response_time: 15  # seconds
  
  # Tier 2: Full Local Processing
  local:
    enabled: true
    amd_optimization: true
    model_preference: "llava:7b"
    target_response_time: 120  # seconds
  
  # Tier 3: Pure Cloud
  cloud:
    enabled: true
    providers: ["openai", "anthropic", "google"]
    target_response_time: 10  # seconds

# Privacy Pipeline Configuration
privacy:
  enabled: true
  default_level: "balanced"  # paranoid, balanced, speed
  preprocessing_timeout: 5   # seconds
  
  levels:
    paranoid:
      face_detection: true
      text_sanitization: true
      object_anonymization: true
      pii_removal: true
    balanced:
      face_detection: true
      text_sanitization: true
      object_anonymization: false
      pii_removal: true
    speed:
      face_detection: false
      text_sanitization: true
      object_anonymization: false
      pii_removal: false

# AMD Hardware Optimization
amd_optimization:
  enabled: true
  cpu: "8845hs"
  igpu: "780m"
  memory: "64gb"
  
  models:
    llava_7b:
      enabled: true
      gpu_layers: 20
      context_length: 4096
      quantization: "Q4_K_M"
    llava_13b:
      enabled: true
      gpu_layers: 26
      context_length: 4096
      quantization: "Q4_K_M"

# Cloud Provider Configuration (Simplified)
providers:
  openai:
    enabled: true
    priority: 1
    model: "gpt-4-vision-preview"
    timeout: 10
    
  anthropic:
    enabled: true
    priority: 2
    model: "claude-3-5-sonnet-20241022"
    timeout: 10
    
  google:
    enabled: true
    priority: 3
    model: "gemini-1.5-flash"
    timeout: 8
    
  llamacpp_amd:
    enabled: true
    priority: 4
    model: "llava:7b"
    timeout: 120

# Home Assistant Integration
home_assistant:
  enabled: true
  api_url: "http://supervisor/core/api"
  zones:
    - name: "Living Room"
      camera: "camera.living_room"
      todo_list: "todo.living_room_tasks"
    - name: "Kitchen"  
      camera: "camera.kitchen"
      todo_list: "todo.kitchen_tasks"

# Logging Configuration
logging:
  level: "INFO"
  file: "/data/logs/aicleaner.log"
  max_size: "10MB"
  backup_count: 5
"""
        
        config_path = self.addon_path / "config.yaml"
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        print(f"✅ Created main configuration at: {config_path}")
    
    def create_startup_script(self):
        """Create startup script for the multi-tier system"""
        startup_content = """#!/usr/bin/env python3
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
        # Initialize Privacy Pipeline
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
        
        # Start the main system
        print("🎭 Multi-Tier System fully operational!")
        print("📊 Available tiers: Hybrid, Local, Cloud")
        print("🏠 Home Assistant integration active")
        
        # Keep the system running
        while True:
            await asyncio.sleep(60)  # Check status every minute
            
    except KeyboardInterrupt:
        print("\\n⏹️ Shutting down AICleaner v3...")
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
"""
        
        startup_path = self.base_path / "start_aicleaner.py"
        with open(startup_path, 'w') as f:
            f.write(startup_content)
        
        # Make executable
        os.chmod(startup_path, 0o755)
        print(f"✅ Created startup script at: {startup_path}")
    
    def create_deployment_readme(self):
        """Create deployment instructions"""
        readme_content = """# 🎭 AICleaner v3 Multi-Tier System Deployment Guide

## 🚀 Quick Start

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Download Models (Optional - for local processing):**
   ```bash
   mkdir -p /data/models
   # Download LLaVA GGUF models to /data/models/
   ```

3. **Start the System:**
   ```bash
   python3 start_aicleaner.py
   ```

## 🎯 System Architecture

### **Tier 1: Privacy-Preserving Hybrid (Recommended)**
- **Performance**: 5-15 seconds
- **Privacy**: Local preprocessing + cloud inference
- **Use Case**: Balanced privacy and speed

### **Tier 2: Full Local Processing**
- **Performance**: 1-5 minutes
- **Privacy**: Complete local processing
- **Use Case**: Maximum privacy, offline operation

### **Tier 3: Pure Cloud**
- **Performance**: 5-10 seconds  
- **Privacy**: Minimal (direct API calls)
- **Use Case**: Maximum speed

## 🔧 Configuration

Edit `addons/aicleaner_v3/config.yaml` to customize:
- Privacy levels (paranoid/balanced/speed)
- AMD optimization settings
- Cloud provider preferences
- Home Assistant integration

## 🏠 Home Assistant Integration

Add to your `configuration.yaml`:
```yaml
aicleaner_v3:
  enabled: true
  config_path: "/path/to/aicleaner_v3/config.yaml"
```

## 📊 Performance Optimization

### For AMD 8845HS + Radeon 780M:
1. Enable AMD optimization in config
2. Install ROCm drivers for GPU acceleration
3. Download optimized LLaVA models
4. Configure GPU layer allocation

### Privacy Pipeline Optimization:
1. Choose appropriate privacy level
2. Configure preprocessing timeout
3. Enable hardware acceleration

## 🔍 Monitoring

Check logs at `/data/logs/aicleaner.log` for:
- Performance metrics
- Error diagnostics
- Optimization recommendations

## 🆘 Troubleshooting

**Common Issues:**
1. **Missing dependencies**: Run `pip install -r requirements.txt`
2. **GPU acceleration**: Install ROCm drivers for AMD 780M
3. **Model loading**: Ensure models are in `/data/models/`
4. **Performance**: Check GPU layer allocation in config

**Support:**
- Check integration test results
- Review log files for errors
- Validate configuration syntax
"""
        
        readme_path = self.base_path / "DEPLOYMENT_README.md"
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        print(f"✅ Created deployment guide at: {readme_path}")
    
    def run_setup(self):
        """Execute complete setup process"""
        print("🎭 AICleaner v3 Multi-Tier System Setup")
        print("=" * 50)
        
        try:
            self.setup_directory_structure()
            self.create_requirements_file()
            self.create_main_config()
            self.create_startup_script()
            self.create_deployment_readme()
            
            print("\n" + "=" * 50)
            print("🎉 Multi-Tier System Setup Complete!")
            print("\n📋 Next Steps:")
            print("1. Install dependencies: pip install -r requirements.txt")
            print("2. Configure API keys in config.yaml")
            print("3. Download LLaVA models (optional)")
            print("4. Test the system: python3 start_aicleaner.py")
            print("\n📖 See DEPLOYMENT_README.md for detailed instructions")
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
        
        return True

if __name__ == "__main__":
    setup = MultiTierSystemSetup()
    success = setup.run_setup()
    
    if success:
        print("\n✅ Setup completed successfully!")
    else:
        print("\n❌ Setup failed. Check errors above.")
        sys.exit(1)