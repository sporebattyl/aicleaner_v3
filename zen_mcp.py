#!/usr/bin/env python3
"""
Unified AI Provider Manager with Configuration System
Enhanced with intelligent quota cycling, thinking mode, and fallback support

Supports new unified configuration format with environment variable resolution,
configuration migration, and multi-provider support.

Available globally across all Claude sessions regardless of working directory.
"""

import asyncio
import json
import os
import time
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import aiohttp
import numpy as np

# Privacy pipeline imports
try:
    from addons.aicleaner_v3.privacy import PrivacyPipeline, PrivacyConfig
    PRIVACY_AVAILABLE = True
except ImportError:
    PRIVACY_AVAILABLE = False


@dataclass
class ProviderConfig:
    """Configuration for an AI provider"""
    provider: str
    enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: Dict[str, str] = field(default_factory=dict)
    timeout: int = 90
    priority: int = 1
    options: Dict[str, Any] = field(default_factory=dict)


class ModelType(Enum):
    """Types of AI models"""
    TEXT = "text"
    VISION = "vision"
    CODE = "code"


class AIProviderManager:
    def __init__(self, config_path: str = "config.yaml", api_keys: list = None, primary_api_key: str = None):
        """Initialize AI Provider Manager with unified configuration system"""
        self.config_path = Path(config_path)
        self.logger = logging.getLogger("ai_provider_manager")
        
        # Provider configurations
        self.provider_configs: List[ProviderConfig] = []
        
        # Legacy support for backward compatibility
        self.legacy_api_keys = None
        if api_keys:
            self.legacy_api_keys = api_keys
        elif primary_api_key:
            self.legacy_api_keys = [primary_api_key]
        else:
            # Default keys if none provided
            self.legacy_api_keys = [
                "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo",
                "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro", 
                "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc"
            ]
        
        # Configuration data
        self.config_data = {}
        
        # Privacy pipeline
        self.privacy_pipeline: Optional['PrivacyPipeline'] = None
        self.privacy_settings = {}
        
        # Load configuration
        self._migrate_config_if_needed()
        self._load_provider_configs()
        self._initialize_privacy_pipeline()
        
        # Model priority list with quota tracking per API key (legacy support)
        self.model_templates = [
            {
                "name": "gemini-2.5-pro",
                "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent",
                "daily_limit": 100,
                "rpm_limit": 5,
                "tpm_limit": 250000
            },
            {
                "name": "gemini-2.5-flash",
                "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                "daily_limit": 250,
                "rpm_limit": 10,
                "tpm_limit": 250000
            },
            {
                "name": "gemini-2.5-flash-lite-preview-06-17",
                "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite-preview-06-17:generateContent",
                "daily_limit": 1000,
                "rpm_limit": 15,
                "tpm_limit": 250000
            }
        ]
        
        # Create model instances for legacy mode
        self.models = {}
        if self.legacy_api_keys:
            for key_idx, api_key in enumerate(self.legacy_api_keys):
                self.models[api_key] = []
                for template in self.model_templates:
                    model_instance = {
                        **template,
                        "api_key": api_key,
                        "api_key_index": key_idx,
                        "request_count": 0,
                        "last_request_time": 0,
                        "daily_reset_time": time.time()
                    }
                    self.models[api_key].append(model_instance)
    
    def _load_provider_configs(self):
        """Load provider configurations from unified config file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config_data = yaml.safe_load(f) or {}
                
                # Load ai_providers array
                ai_providers = self.config_data.get("ai_providers", [])
                for provider_config in ai_providers:
                    # Resolve environment variables in API key
                    api_key = provider_config.get("api_key", "")
                    if api_key.startswith("env(") and api_key.endswith(")"):
                        env_var = api_key[4:-1]  # Extract variable name
                        api_key = os.getenv(env_var, "")
                    
                    config = ProviderConfig(
                        provider=provider_config["provider"],
                        enabled=provider_config.get("enabled", True),
                        api_key=api_key,
                        base_url=provider_config.get("base_url"),
                        models=provider_config.get("models", {}),
                        timeout=provider_config.get("timeout", 90),
                        priority=provider_config.get("priority", len(self.provider_configs) + 1),
                        options=provider_config.get("options", {})
                    )
                    self.provider_configs.append(config)
                    
                self.logger.info(f"Loaded {len(self.provider_configs)} provider configurations")
                
            else:
                self.logger.warning(f"Configuration file {self.config_path} not found, using legacy mode")
                
        except Exception as e:
            self.logger.error(f"Error loading provider configs: {e}")
    
    def _save_config(self):
        """Save current configuration to YAML file"""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert provider configs to dict format
            ai_providers = []
            for config in self.provider_configs:
                provider_dict = {
                    "provider": config.provider,
                    "enabled": config.enabled,
                    "timeout": config.timeout,
                    "priority": config.priority
                }
                
                if config.api_key:
                    provider_dict["api_key"] = config.api_key
                if config.base_url:
                    provider_dict["base_url"] = config.base_url
                if config.models:
                    provider_dict["models"] = config.models
                if config.options:
                    provider_dict["options"] = config.options
                    
                ai_providers.append(provider_dict)
            
            # Update config data
            self.config_data["ai_providers"] = ai_providers
            
            # Write to file
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False, indent=2)
                
            self.logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
    
    def _migrate_config_if_needed(self):
        """Migrate legacy configuration to new unified format if needed"""
        try:
            # Check if migration is needed
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    existing_config = yaml.safe_load(f) or {}
                
                # Check if already using new format
                if "ai_providers" in existing_config:
                    self.logger.info("Configuration already in new unified format")
                    return
                
                # Check for legacy format
                if "providers" in existing_config or "local_llm" in existing_config:
                    self.logger.info("Migrating legacy configuration to unified format")
                    self._perform_config_migration(existing_config)
                    return
            
            # Create default configuration if none exists
            if not self.config_path.exists():
                self.logger.info("Creating default unified configuration")
                self._create_default_config()
                
        except Exception as e:
            self.logger.error(f"Error during configuration migration: {e}")
    
    def _perform_config_migration(self, legacy_config: Dict[str, Any]):
        """Perform actual configuration migration"""
        try:
            # Create backup
            backup_path = self.config_path.with_suffix('.yaml.backup')
            with open(backup_path, 'w') as f:
                yaml.dump(legacy_config, f)
            self.logger.info(f"Legacy configuration backed up to {backup_path}")
            
            # Initialize new config structure
            new_config = {
                "ai_providers": [],
                "migrated_from_legacy": True,
                "migration_date": datetime.now().isoformat()
            }
            
            # Migrate legacy providers section
            legacy_providers = legacy_config.get("providers", {})
            for provider_name, provider_config in legacy_providers.items():
                migrated_provider = {
                    "provider": provider_name,
                    "enabled": provider_config.get("enabled", True),
                    "timeout": provider_config.get("timeout_seconds", 90),
                    "priority": provider_config.get("priority", 1)
                }
                
                # Migrate API key
                if "api_key" in provider_config:
                    migrated_provider["api_key"] = provider_config["api_key"]
                
                # Migrate base URL
                if "base_url" in provider_config:
                    migrated_provider["base_url"] = provider_config["base_url"]
                
                # Migrate model configuration
                if "model_name" in provider_config:
                    migrated_provider["models"] = {
                        "text": provider_config["model_name"],
                        "vision": provider_config["model_name"],
                        "code": provider_config["model_name"]
                    }
                
                new_config["ai_providers"].append(migrated_provider)
            
            # Migrate local_llm section to Ollama provider
            if "local_llm" in legacy_config:
                local_llm = legacy_config["local_llm"]
                if local_llm.get("enabled", False):
                    ollama_provider = {
                        "provider": "ollama",
                        "enabled": True,
                        "base_url": local_llm.get("base_url", "http://localhost:11434"),
                        "models": {
                            "text": local_llm.get("model", "llama3:latest"),
                            "vision": local_llm.get("vision_model", "llava:latest"),
                            "code": local_llm.get("code_model", "codellama:latest")
                        },
                        "timeout": local_llm.get("timeout", 120),
                        "priority": 999  # Lower priority than cloud providers
                    }
                    new_config["ai_providers"].append(ollama_provider)
            
            # Save migrated configuration
            with open(self.config_path, 'w') as f:
                yaml.dump(new_config, f, default_flow_style=False, indent=2)
            
            self.logger.info("Configuration migration completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error performing configuration migration: {e}")
            raise
    
    def _initialize_privacy_pipeline(self):
        """Initialize privacy pipeline if enabled and available"""
        try:
            if not PRIVACY_AVAILABLE:
                self.logger.debug("Privacy pipeline not available - skipping initialization")
                return
            
            # Load privacy settings from configuration
            self.privacy_settings = self.config_data.get("privacy", {})
            
            if not self.privacy_settings.get("enabled", False):
                self.logger.info("Privacy pipeline disabled in configuration")
                return
            
            # Create privacy configuration
            privacy_config = PrivacyConfig.from_dict(self.privacy_settings)
            
            # Initialize privacy pipeline
            self.privacy_pipeline = PrivacyPipeline(privacy_config)
            
            # Schedule async initialization
            asyncio.create_task(self._async_init_privacy_pipeline())
            
            self.logger.info("Privacy pipeline initialization scheduled")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize privacy pipeline: {e}")
            self.privacy_pipeline = None
    
    async def _async_init_privacy_pipeline(self):
        """Asynchronously initialize privacy pipeline components"""
        try:
            if self.privacy_pipeline:
                if await self.privacy_pipeline.initialize():
                    self.logger.info("Privacy pipeline successfully initialized")
                else:
                    self.logger.error("Privacy pipeline initialization failed")
                    self.privacy_pipeline = None
        except Exception as e:
            self.logger.error(f"Error during async privacy pipeline initialization: {e}")
            self.privacy_pipeline = None
    
    def _create_default_config(self):
        """Create default unified configuration"""
        default_config = {
            "ai_providers": [
                {
                    "provider": "ollama",
                    "enabled": True,
                    "base_url": "http://localhost:11434",
                    "models": {
                        "text": "llama3:latest",
                        "vision": "llava:latest",
                        "code": "codellama:latest"
                    },
                    "timeout": 120,
                    "priority": 1
                },
                {
                    "provider": "openai",
                    "enabled": False,
                    "api_key": "env(OPENAI_API_KEY)",
                    "models": {
                        "text": "gpt-4o",
                        "vision": "gpt-4o",
                        "code": "gpt-4o"
                    },
                    "timeout": 90,
                    "priority": 2
                },
                {
                    "provider": "google",
                    "enabled": True,
                    "api_key": "env(GEMINI_API_KEY)",
                    "models": {
                        "text": "gemini-2.5-pro",
                        "vision": "gemini-2.5-pro",
                        "code": "gemini-2.5-flash"
                    },
                    "timeout": 90,
                    "priority": 3
                }
            ],
            "created_date": datetime.now().isoformat()
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        
        self.logger.info(f"Default configuration created at {self.config_path}")
    
    def get_provider_for_model_type(self, model_type: ModelType) -> Optional[ProviderConfig]:
        """Get the best provider for a specific model type (text, vision, code)"""
        available_providers = [p for p in self.provider_configs if p.enabled]
        
        if not available_providers:
            return None
        
        # Sort by priority (lower number = higher priority)
        available_providers.sort(key=lambda p: p.priority)
        
        # Find first provider that supports the model type
        for provider in available_providers:
            if model_type.value in provider.models:
                return provider
        
        # Fallback to first available provider
        return available_providers[0] if available_providers else None
    
    def get_model_for_type(self, model_type: ModelType, provider_name: str = None) -> Optional[str]:
        """Get model name for specific type from provider"""
        if provider_name:
            # Get specific provider
            provider = next((p for p in self.provider_configs if p.provider == provider_name), None)
            if provider and provider.enabled:
                return provider.models.get(model_type.value)
        else:
            # Get best provider for model type
            provider = self.get_provider_for_model_type(model_type)
            if provider:
                return provider.models.get(model_type.value)
        
        return None
    
    async def collaborate_with_gemini(self, prompt: str, context_files: List[str] = None, image_data=None) -> Dict[str, Any]:
        """Collaborate with Gemini using unified configuration or legacy fallback"""
        
        # Apply privacy processing to image data if available
        processed_image_data = image_data
        privacy_metadata = {}
        
        if image_data is not None and self.privacy_pipeline:
            try:
                self.logger.info("Applying privacy redaction pipeline...")
                
                # Convert image_data to numpy array if needed
                if isinstance(image_data, (str, bytes)):
                    # Handle different image data formats
                    import cv2
                    import base64
                    
                    if isinstance(image_data, str) and os.path.exists(image_data):
                        # Image file path
                        image_array = cv2.imread(image_data)
                    elif isinstance(image_data, str):
                        # Base64 encoded image
                        image_bytes = base64.b64decode(image_data)
                        nparr = np.frombuffer(image_bytes, np.uint8)
                        image_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    else:
                        # Raw bytes
                        nparr = np.frombuffer(image_data, np.uint8)
                        image_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                else:
                    # Assume numpy array
                    image_array = image_data
                
                # Process through privacy pipeline
                privacy_result = await self.privacy_pipeline.process_image(image_array)
                
                if privacy_result["status"] == "success":
                    processed_image_data = privacy_result["anonymized_image"]
                    privacy_metadata = {
                        "privacy_applied": True,
                        "regions_processed": privacy_result["regions_processed"],
                        "processing_time": privacy_result["processing_time"],
                        "privacy_level": privacy_result["privacy_level"]
                    }
                    self.logger.info(f"Privacy redaction complete - {privacy_result['regions_processed']} regions processed")
                else:
                    self.logger.warning(f"Privacy processing failed: {privacy_result.get('metadata', {}).get('error', 'Unknown error')}")
                    privacy_metadata = {"privacy_applied": False, "error": "Privacy processing failed"}
                    
            except Exception as e:
                self.logger.error(f"Privacy pipeline error: {e}")
                privacy_metadata = {"privacy_applied": False, "error": str(e)}
        elif image_data is not None:
            self.logger.debug("Privacy pipeline not available or disabled")
            privacy_metadata = {"privacy_applied": False, "reason": "Pipeline not available"}
        
        # Try new unified configuration first
        gemini_provider = self.get_provider_for_model_type(ModelType.TEXT)
        if gemini_provider and gemini_provider.provider == "google" and gemini_provider.api_key:
            result = await self._collaborate_with_unified_config(prompt, gemini_provider, context_files, processed_image_data)
            result["privacy_metadata"] = privacy_metadata
            return result
        
        # Fallback to legacy mode if available
        if self.legacy_api_keys and hasattr(self, 'models'):
            result = await self._collaborate_with_legacy_models(prompt, context_files, processed_image_data)
            result["privacy_metadata"] = privacy_metadata
            return result
        
        return {
            "success": False,
            "error": "No Gemini/Google provider configured or available",
            "collaboration_established": False,
            "privacy_metadata": privacy_metadata
        }
    
    async def _collaborate_with_unified_config(self, prompt: str, provider: ProviderConfig, context_files: List[str] = None) -> Dict[str, Any]:
        """Collaborate using unified configuration format"""
        
        # Prepare the collaboration prompt
        collaboration_prompt = f"""
You are Gemini, collaborating with Claude through a zen MCP connection to review AICleaner v3 implementation prompts.

COLLABORATION CONTEXT:
Claude has created comprehensive implementation prompts for the AICleaner v3 Home Assistant addon improvement project. These prompts include TDD principles, AAA testing, component-based design, MCP server integration, GitHub rollback procedures, and iterative collaborative review processes.

YOUR ROLE:
Provide expert review and collaborative analysis to help Claude refine these prompts to perfection.

PROMPT REVIEW REQUEST:
{prompt}

DETAILED ANALYSIS NEEDED:
1. **Implementation Readiness**: Are these prompts actionable and complete for successful implementation?
2. **Quality Integration**: How well are TDD/AAA/Component design principles integrated?
3. **MCP Server Usage**: Is the MCP server integration (WebFetch, zen, GitHub, Task) well-designed?
4. **Collaborative Process**: Will the iterative Claude-Gemini review cycles produce high-quality results?
5. **Risk Management**: Are rollback procedures and GitHub MCP integration sufficient?
6. **HA Compliance**: Do prompts properly address Home Assistant addon standards?
7. **Completeness**: Any gaps or missing elements?
8. **Production Readiness**: Will following these prompts result in a certifiable HA addon?

COLLABORATION OUTPUT FORMAT:
Provide specific, actionable feedback with:
- Strengths identified
- Areas for improvement
- Specific recommendations
- Consensus on readiness level (1-100)
- Final verdict on implementation readiness

Your expertise will help ensure these prompts lead to a production-ready, certifiable Home Assistant addon.
"""
        
        # Get model for text generation
        model_name = provider.models.get(ModelType.TEXT.value, "gemini-2.5-pro")
        
        headers = {
            "Content-Type": "application/json",
        }
        
        # Configure generation based on model
        generation_config = {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192
        }
        
        # Add thinking configuration for Gemini 2.5 models
        if "2.5-pro" in model_name:
            generation_config["thinkingConfig"] = {
                "thinkingBudget": -1,  # Dynamic allocation
                "includeThoughts": True
            }
        elif "2.5-flash" in model_name:
            generation_config["thinkingConfig"] = {
                "thinkingBudget": 12288,  # Half of max for complex analysis
                "includeThoughts": True
            }
        
        payload = {
            "contents": [{
                "parts": [{"text": collaboration_prompt}]
            }],
            "generationConfig": generation_config
        }
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={provider.api_key}"
            
            timeout = aiohttp.ClientTimeout(total=provider.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract response and thinking data
                        candidate = data["candidates"][0]
                        response_text = candidate["content"]["parts"][0]["text"]
                        
                        # Extract thinking data if available
                        thinking_data = {}
                        thinking_config = generation_config.get("thinkingConfig", {})
                        if "thoughts" in candidate:
                            thinking_data = {
                                "thinking_available": True,
                                "thinking_summary": candidate["thoughts"].get("thoughtSummary", ""),
                                "thinking_budget_used": thinking_config.get("thinkingBudget", "none")
                            }
                        else:
                            thinking_data = {
                                "thinking_available": False,
                                "thinking_budget_configured": thinking_config.get("thinkingBudget", "none")
                            }
                        
                        return {
                            "success": True,
                            "response": response_text,
                            "collaboration_established": True,
                            "model_used": model_name,
                            "provider_used": provider.provider,
                            "configuration_mode": "unified",
                            "thinking": thinking_data
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}",
                            "collaboration_established": False
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection error: {str(e)}",
                "collaboration_established": False
            }
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers (unified and legacy)"""
        status = {
            "configuration_mode": "unified" if self.provider_configs else "legacy",
            "unified_providers": {},
            "legacy_quota": {}
        }
        
        # Unified provider status
        for provider in self.provider_configs:
            status["unified_providers"][provider.provider] = {
                "enabled": provider.enabled,
                "has_api_key": bool(provider.api_key),
                "models_configured": list(provider.models.keys()),
                "priority": provider.priority,
                "timeout": provider.timeout
            }
        
        # Legacy quota status if available
        if hasattr(self, 'models') and self.legacy_api_keys:
            status["legacy_quota"] = self.get_quota_status()
        
        return status
    
    def _reset_daily_counters_if_needed(self):
        """Reset daily counters if 24 hours have passed"""
        if not hasattr(self, 'models'):
            return
            
        current_time = time.time()
        for api_key in self.models:
            for model in self.models[api_key]:
                if current_time - model["daily_reset_time"] >= 86400:  # 24 hours
                    model["request_count"] = 0
                    model["daily_reset_time"] = current_time
    
    def _can_use_model(self, model: Dict[str, Any]) -> bool:
        """Check if we can use this model based on rate limits and quotas"""
        current_time = time.time()
        
        # Check daily limit
        if model["request_count"] >= model["daily_limit"]:
            return False
        
        # Check rate limit (RPM)
        time_since_last = current_time - model["last_request_time"]
        min_interval = 60 / model["rpm_limit"]  # seconds between requests
        if time_since_last < min_interval:
            return False
        
        return True
    
    def _select_best_available_model(self) -> Dict[str, Any]:
        """Select the best available model based on priority and limits"""
        if not hasattr(self, 'models'):
            return {}
            
        self._reset_daily_counters_if_needed()
        
        # Try models by priority (Pro -> Flash -> Flash-Lite), cycling through API keys
        for model_idx in range(len(self.model_templates)):
            for api_key in self.legacy_api_keys:
                model = self.models[api_key][model_idx]
                if self._can_use_model(model):
                    return model
        
        # If no models available, return the last one (Flash-Lite with first API key)
        return self.models[self.legacy_api_keys[0]][-1]
    
    def _update_model_usage(self, model: Dict[str, Any]):
        """Update usage counters for the model"""
        model["request_count"] += 1
        model["last_request_time"] = time.time()
    
    def get_quota_status(self) -> Dict[str, Any]:
        """Get current quota status for all models across all API keys"""
        if not hasattr(self, 'models'):
            return {"error": "No legacy models configured"}
            
        self._reset_daily_counters_if_needed()
        
        quota_status = {}
        for api_key in self.models:
            key_name = f"api_key_{self.legacy_api_keys.index(api_key) + 1}"
            quota_status[key_name] = {}
            
            for model in self.models[api_key]:
                model_key = f"{model['name']}"
                quota_status[key_name][model_key] = {
                    "daily_used": model["request_count"],
                    "daily_limit": model["daily_limit"],
                    "daily_remaining": model["daily_limit"] - model["request_count"],
                    "rpm_limit": model["rpm_limit"],
                    "can_use_now": self._can_use_model(model),
                    "time_since_last_request": time.time() - model["last_request_time"] if model["last_request_time"] > 0 else "never"
                }
        
        best_model = self._select_best_available_model()
        return {
            "quota_status": quota_status,
            "recommended_model": best_model.get("name", "none"),
            "recommended_api_key": f"api_key_{best_model.get('api_key_index', 0) + 1}",
            "total_api_keys": len(self.legacy_api_keys)
        }


# Legacy Gemini Client for backward compatibility
class ZenGeminiClient:
    """Legacy Gemini client wrapper for backward compatibility"""
    
    def __init__(self, api_keys: list = None, primary_api_key: str = None):
        self.provider_manager = AIProviderManager(api_keys=api_keys, primary_api_key=primary_api_key)
    
    async def collaborate_with_gemini(self, prompt: str, context_files: List[str] = None) -> Dict[str, Any]:
        """Legacy method - delegates to provider manager's Gemini collaboration"""
        return await self.provider_manager.collaborate_with_gemini(prompt, context_files)
    
    def get_quota_status(self) -> Dict[str, Any]:
        """Legacy method - delegates to provider manager's quota status"""
        return self.provider_manager.get_quota_status()


# Global convenience functions for easy access
async def zen_collaborate(prompt: str, api_keys: list = None, config_path: str = "config.yaml") -> Dict[str, Any]:
    """Quick collaboration function using global zen MCP client"""
    if api_keys:
        # Legacy mode
        client = ZenGeminiClient(api_keys=api_keys)
        return await client.collaborate_with_gemini(prompt)
    else:
        # New unified configuration mode
        manager = AIProviderManager(config_path=config_path)
        return await manager.collaborate_with_gemini(prompt)


def zen_quota_status(api_keys: list = None, config_path: str = "config.yaml") -> Dict[str, Any]:
    """Quick quota check function using global zen MCP client"""
    if api_keys:
        # Legacy mode
        client = ZenGeminiClient(api_keys=api_keys)
        return client.get_quota_status()
    else:
        # New unified configuration mode
        manager = AIProviderManager(config_path=config_path)
        return manager.get_provider_status()


async def test_global_zen():
    """Test the global zen MCP setup with unified configuration"""
    print("=== GLOBAL ZEN MCP TEST ===")
    print("Testing unified configuration system with legacy fallback")
    
    # Test both configuration modes
    print("\n--- Testing Unified Configuration Mode ---")
    try:
        manager = AIProviderManager(config_path="config.yaml")
        status = manager.get_provider_status()
        print(f"Configuration mode: {status['configuration_mode']}")
        print(f"Unified providers: {list(status['unified_providers'].keys())}")
        
        # Test collaboration with unified config
        test_prompt = """
UNIFIED CONFIGURATION TEST

Gemini, this is a test of our new unified AI provider configuration system that supports:

NEW FEATURES:
- Unified ai_providers array configuration
- Environment variable resolution for API keys  
- Model type mapping (text, vision, code)
- Priority-based provider selection
- Configuration migration from legacy format
- Multi-provider support beyond just Gemini

CONFIGURATION STRUCTURE:
- YAML-based configuration with ai_providers array
- Each provider has models.text/vision/code definitions
- Environment variable support: env(GEMINI_API_KEY)
- Priority ordering and timeout configuration

Please confirm:
1. Which model and provider are responding
2. Verification that the unified configuration is working
3. Readiness for enhanced multi-provider AICleaner v3 development

This tests our new configuration management system.
"""
        
        result = await manager.collaborate_with_gemini(test_prompt)
        
        if result.get("success"):
            print(f"SUCCESS! Provider: {result.get('provider_used', 'unknown')}")
            print(f"Model: {result.get('model_used', 'unknown')}")
            print(f"Config Mode: {result.get('configuration_mode', 'unknown')}")
            print(f"Thinking: {result.get('thinking', {})}")
            print("\nGemini Response:")
            print("=" * 50)
            clean_text = ''.join(char if ord(char) < 128 else '?' for char in result["response"])
            print(clean_text[:500] + "..." if len(clean_text) > 500 else clean_text)
            print("=" * 50)
        else:
            print(f"UNIFIED MODE FAILED: {result.get('error')}")
            
            # Fallback to legacy mode test
            print("\n--- Testing Legacy Fallback Mode ---")
            legacy_status = zen_quota_status(api_keys=[
                "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo",
                "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro", 
                "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc"
            ])
            print(f"Legacy quota status: {legacy_status.get('recommended_model', 'none')}")
            
            legacy_result = await zen_collaborate(test_prompt, api_keys=[
                "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo",
                "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro", 
                "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc"
            ])
            
            if legacy_result.get("success"):
                print(f"LEGACY SUCCESS! Model: {legacy_result['model_used']} on {legacy_result.get('api_key_used', 'unknown')}")
                print(f"Thinking: {legacy_result['thinking']}")
            else:
                print(f"LEGACY ALSO FAILED: {legacy_result.get('error')}")
                
    except Exception as e:
        print(f"TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_global_zen())