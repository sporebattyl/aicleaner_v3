from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio


class PrivacyLevel(Enum):
    FAST = "fast"  # Raw images to API (speed priority)
    HYBRID = "hybrid"  # Local metadata -> API (balanced)
    PRIVATE = "private"  # Everything local (maximum privacy)


class ProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class AnalysisResult:
    action: str  # "keep" or "delete"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    metadata: Dict[str, Any]
    processing_time: float


@dataclass
class ProviderCapabilities:
    supported_privacy_levels: list[PrivacyLevel]
    max_image_size_mb: float
    supports_batch_processing: bool
    max_concurrent_requests: int
    estimated_cost_per_request: Optional[float] = None


@dataclass
class ProviderHealth:
    status: ProviderStatus
    response_time_ms: float
    error_rate: float  # 0.0 to 1.0
    last_check: float  # timestamp
    error_message: Optional[str] = None


class LLMProvider(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
        
    @abstractmethod
    async def analyze(self, image_data: bytes, prompt: str, privacy_level: PrivacyLevel) -> AnalysisResult:
        """Analyze an image and determine if it should be kept or deleted."""
        pass
        
    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check provider health and availability."""
        pass
        
    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities and limitations."""
        pass
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider. Return True if successful."""
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources before shutdown."""
        pass
        
    async def supports_privacy_level(self, privacy_level: PrivacyLevel) -> bool:
        """Check if provider supports the specified privacy level."""
        capabilities = self.get_capabilities()
        return privacy_level in capabilities.supported_privacy_levels