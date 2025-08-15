"""
Base Provider Interface for AICleaner V3
Enhanced with visual annotation support and health monitoring
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any
import asyncio

class ProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class ProviderCapability(Enum):
    VISION = "vision"
    TEXT = "text"
    VISUAL_GROUNDING = "visual_grounding"
    OBJECT_DETECTION = "object_detection"

@dataclass
class BoundingBox:
    """Represents a rectangular region in an image"""
    x1: int  # Top-left x coordinate
    y1: int  # Top-left y coordinate  
    x2: int  # Bottom-right x coordinate
    y2: int  # Bottom-right y coordinate
    
    @property
    def width(self) -> int:
        return self.x2 - self.x1
    
    @property 
    def height(self) -> int:
        return self.y2 - self.y1
    
    @property
    def center(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

@dataclass
class Task:
    """Represents a single cleaning task with optional visual annotation"""
    description: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    estimated_duration: Optional[str] = None  # e.g. "5 minutes"
    annotation: Optional[BoundingBox] = None
    confidence: Optional[float] = None  # 0.0-1.0

@dataclass
class ProviderHealth:
    """Health status of an LLM provider"""
    status: ProviderStatus
    response_time: Optional[float] = None  # milliseconds
    error_message: Optional[str] = None
    resource_usage: Optional[Dict[str, float]] = None  # CPU, memory, etc.
    last_checked: Optional[str] = None  # ISO timestamp

@dataclass
class AnalysisResult:
    """Result from analyzing an image"""
    tasks: List[Task]
    annotated_image: Optional[bytes] = None
    processing_time: Optional[float] = None  # seconds
    model_used: Optional[str] = None
    confidence_score: Optional[float] = None  # Overall confidence

class LLMProvider(ABC):
    """Abstract base class for all LLM providers"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self._capabilities: Optional[List[ProviderCapability]] = None
    
    @abstractmethod
    async def analyze(self, image: bytes, prompt: str, **kwargs) -> AnalysisResult:
        """
        Analyze an image and return structured tasks with optional annotations
        
        Args:
            image: Raw image bytes
            prompt: Analysis prompt/instructions
            **kwargs: Provider-specific options
            
        Returns:
            AnalysisResult with tasks and optional visual annotations
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """
        Check the health and availability of this provider
        
        Returns:
            ProviderHealth with current status and metrics
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        """
        Get the capabilities supported by this provider
        
        Returns:
            List of supported capabilities
        """
        pass
    
    async def test_connection(self) -> bool:
        """
        Quick test to verify provider connectivity
        
        Returns:
            True if provider is accessible, False otherwise
        """
        try:
            health = await self.health_check()
            return health.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]
        except Exception:
            return False
    
    @property
    def supports_visual_grounding(self) -> bool:
        """Check if provider supports returning bounding boxes"""
        return ProviderCapability.VISUAL_GROUNDING in self.get_capabilities()
    
    @property
    def supports_vision(self) -> bool:
        """Check if provider can analyze images"""
        return ProviderCapability.VISION in self.get_capabilities()

class ProviderRegistry:
    """Registry for managing multiple LLM providers"""
    
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
    
    def register(self, provider: LLMProvider) -> None:
        """Register a new provider"""
        self._providers[provider.name] = provider
    
    def get_provider(self, name: str) -> Optional[LLMProvider]:
        """Get a provider by name"""
        return self._providers.get(name)
    
    def get_all_providers(self) -> List[LLMProvider]:
        """Get all registered providers"""
        return list(self._providers.values())
    
    async def get_healthy_providers(self) -> List[LLMProvider]:
        """Get all providers that are currently healthy"""
        healthy = []
        for provider in self._providers.values():
            try:
                if await provider.test_connection():
                    healthy.append(provider)
            except Exception:
                continue
        return healthy
    
    def get_providers_by_capability(self, capability: ProviderCapability) -> List[LLMProvider]:
        """Get all providers that support a specific capability"""
        return [
            provider for provider in self._providers.values()
            if capability in provider.get_capabilities()
        ]