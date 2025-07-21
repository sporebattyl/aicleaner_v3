"""
AI Provider System for AICleaner v3
Phase 2A: AI Model Provider Optimization

This module provides a comprehensive AI provider system with:
- Multi-provider support (OpenAI, Anthropic, Google, Ollama)
- Credential management and API key rotation
- Rate limiting and quota management
- Health monitoring and automated failover
- Performance optimization and caching
- Structured logging and error handling
"""

from .ai_provider_manager import AIProviderManager
from .base_provider import BaseAIProvider, AIProviderStatus, AIProviderError
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .ollama_provider import OllamaProvider
from .credential_manager import CredentialManager
from .rate_limiter import RateLimiter
from .health_monitor import HealthMonitor

__all__ = [
    'AIProviderManager',
    'BaseAIProvider',
    'AIProviderStatus',
    'AIProviderError',
    'OpenAIProvider',
    'AnthropicProvider',
    'GoogleProvider',
    'OllamaProvider',
    'CredentialManager',
    'RateLimiter',
    'HealthMonitor',
]