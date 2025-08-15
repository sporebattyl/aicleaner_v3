"""
AI provider implementations for image analysis and cleaning plan generation.
"""

from .base import (
    BaseAIProvider,
    ImageAnalysis,
    CleaningPlan,
    CleaningTask,
    AreaCondition,
    AnalysisConfidence,
    CleaningUrgency,
    TaskCategory,
    AIProviderError,
    AIProviderUnavailableError,
    AIProviderConfigError,
    AIProviderAnalysisError,
    AIProviderPlanningError
)

from .gemini import GeminiProvider

__all__ = [
    # Base classes and data structures
    'BaseAIProvider',
    'ImageAnalysis',
    'CleaningPlan',
    'CleaningTask',
    'AreaCondition',
    'AnalysisConfidence',
    'CleaningUrgency',
    'TaskCategory',
    
    # Exceptions
    'AIProviderError',
    'AIProviderUnavailableError',
    'AIProviderConfigError',
    'AIProviderAnalysisError',
    'AIProviderPlanningError',
    
    # Provider implementations
    'GeminiProvider',
]

# Provider factory function
def create_provider(provider_name: str, config: dict) -> BaseAIProvider:
    """
    Create an AI provider instance.
    
    Args:
        provider_name: Name of the provider ('gemini', 'ollama')
        config: Provider configuration
        
    Returns:
        BaseAIProvider instance
        
    Raises:
        ValueError: If provider name is not supported
    """
    if provider_name.lower() == 'gemini':
        return GeminiProvider(config)
    elif provider_name.lower() == 'ollama':
        # Import OllamaProvider when implemented
        raise NotImplementedError("Ollama provider not yet implemented")
    else:
        raise ValueError(f"Unsupported AI provider: {provider_name}")

__version__ = "1.0.0"