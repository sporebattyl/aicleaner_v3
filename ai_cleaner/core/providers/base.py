"""
Abstract base class for AI providers in the AI Cleaner addon.
Defines the interface for vision analysis and cleaning plan generation.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum


class AnalysisConfidence(Enum):
    """Confidence levels for AI analysis."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class CleaningUrgency(Enum):
    """Urgency levels for cleaning tasks."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskCategory(Enum):
    """Categories for cleaning tasks."""
    DUSTING = "dusting"
    VACUUMING = "vacuuming"
    MOPPING = "mopping"
    ORGANIZING = "organizing"
    SANITIZING = "sanitizing"
    DEEP_CLEANING = "deep_cleaning"
    MAINTENANCE = "maintenance"
    INSPECTION = "inspection"


@dataclass
class CleaningTask:
    """Individual cleaning task with metadata."""
    id: str
    title: str
    description: str
    category: TaskCategory
    urgency: CleaningUrgency
    estimated_minutes: int
    zone_id: Optional[str] = None
    tools_needed: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set default values after initialization."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.tools_needed is None:
            self.tools_needed = []
        if self.prerequisites is None:
            self.prerequisites = []


@dataclass
class AreaCondition:
    """Condition assessment for a specific area."""
    area_name: str
    cleanliness_score: float  # 0.0 = very dirty, 1.0 = very clean
    confidence: AnalysisConfidence
    issues_detected: List[str]
    recommended_actions: List[str]
    last_assessed: Optional[datetime] = None
    
    def __post_init__(self):
        """Set default values after initialization."""
        if self.last_assessed is None:
            self.last_assessed = datetime.now()


@dataclass
class ImageAnalysis:
    """Complete image analysis result."""
    zone_id: Optional[str]
    overall_cleanliness_score: float  # 0.0 = very dirty, 1.0 = very clean
    confidence: AnalysisConfidence
    summary: str
    detailed_analysis: str
    areas_assessed: List[AreaCondition]
    suggested_tasks: List[CleaningTask]
    analysis_timestamp: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    
    def __post_init__(self):
        """Set default values after initialization."""
        if self.analysis_timestamp is None:
            self.analysis_timestamp = datetime.now()


@dataclass
class CleaningPlan:
    """Comprehensive cleaning plan with prioritized tasks."""
    plan_id: str
    zone_id: Optional[str]
    tasks: List[CleaningTask]
    estimated_total_minutes: int
    priority_score: float  # Higher scores indicate more urgent plans
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    source_analysis: Optional[str] = None  # Reference to source analysis
    
    def __post_init__(self):
        """Set default values after initialization."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.tasks:
            self.estimated_total_minutes = 0
        else:
            self.estimated_total_minutes = sum(task.estimated_minutes for task in self.tasks)


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers.
    
    All AI providers must implement this interface to ensure consistent
    behavior across different AI services (Gemini, Ollama, etc.).
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize the AI provider.
        
        Args:
            name: Provider name (e.g., "gemini", "ollama")
            config: Provider-specific configuration
        """
        self.name = name
        self.config = config
        self._is_initialized = False
        self._last_error: Optional[str] = None
    
    @property
    def is_initialized(self) -> bool:
        """Check if provider is properly initialized."""
        return self._is_initialized
    
    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the AI provider.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the AI provider.
        
        Returns:
            Dictionary containing health status and metrics
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the AI provider is currently available.
        
        Returns:
            True if provider is available for requests
        """
        pass
    
    @abstractmethod
    async def analyze_image(
        self, 
        image_data: bytes, 
        zone_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ImageAnalysis:
        """
        Analyze image for cleanliness and generate assessment.
        
        Args:
            image_data: Image data as bytes
            zone_id: Optional zone identifier for context
            context: Optional additional context (previous analyses, etc.)
            
        Returns:
            ImageAnalysis object with detailed assessment
            
        Raises:
            AIProviderError: If analysis fails
        """
        pass
    
    @abstractmethod
    async def create_cleaning_plan(
        self, 
        analysis: ImageAnalysis,
        constraints: Optional[Dict[str, Any]] = None
    ) -> CleaningPlan:
        """
        Create a structured cleaning plan based on image analysis.
        
        Args:
            analysis: ImageAnalysis result from analyze_image
            constraints: Optional constraints (time limits, available tools, etc.)
            
        Returns:
            CleaningPlan with prioritized tasks
            
        Raises:
            AIProviderError: If plan creation fails
        """
        pass
    
    @abstractmethod
    async def refine_analysis(
        self,
        previous_analysis: ImageAnalysis,
        new_image_data: bytes,
        progress_context: Optional[Dict[str, Any]] = None
    ) -> ImageAnalysis:
        """
        Refine previous analysis with new image data and context.
        
        Args:
            previous_analysis: Previous ImageAnalysis result
            new_image_data: New image data as bytes
            progress_context: Context about completed tasks, time elapsed, etc.
            
        Returns:
            Updated ImageAnalysis with progress assessment
            
        Raises:
            AIProviderError: If refinement fails
        """
        pass
    
    async def batch_analyze_images(
        self,
        images: List[Tuple[bytes, Optional[str]]],  # (image_data, zone_id)
        context: Optional[Dict[str, Any]] = None
    ) -> List[ImageAnalysis]:
        """
        Analyze multiple images in batch (default implementation processes sequentially).
        
        Args:
            images: List of (image_data, zone_id) tuples
            context: Optional shared context for all analyses
            
        Returns:
            List of ImageAnalysis results
        """
        results = []
        for image_data, zone_id in images:
            try:
                analysis = await self.analyze_image(image_data, zone_id, context)
                results.append(analysis)
            except Exception as e:
                # Create error analysis
                error_analysis = ImageAnalysis(
                    zone_id=zone_id,
                    overall_cleanliness_score=0.5,  # Neutral score on error
                    confidence=AnalysisConfidence.LOW,
                    summary=f"Analysis failed: {str(e)}",
                    detailed_analysis=f"Error occurred during image analysis: {str(e)}",
                    areas_assessed=[],
                    suggested_tasks=[]
                )
                results.append(error_analysis)
        
        return results
    
    async def create_comprehensive_plan(
        self,
        analyses: List[ImageAnalysis],
        constraints: Optional[Dict[str, Any]] = None
    ) -> CleaningPlan:
        """
        Create comprehensive cleaning plan from multiple analyses.
        
        Args:
            analyses: List of ImageAnalysis results
            constraints: Optional constraints for the plan
            
        Returns:
            Comprehensive CleaningPlan combining all analyses
        """
        if not analyses:
            return CleaningPlan(
                plan_id=f"empty_plan_{datetime.now().isoformat()}",
                zone_id=None,
                tasks=[],
                priority_score=0.0
            )
        
        # Merge all suggested tasks
        all_tasks = []
        total_score = 0.0
        
        for analysis in analyses:
            all_tasks.extend(analysis.suggested_tasks)
            total_score += analysis.overall_cleanliness_score
        
        # Calculate average cleanliness score (lower = higher priority)
        avg_cleanliness = total_score / len(analyses) if analyses else 0.5
        priority_score = 1.0 - avg_cleanliness  # Invert for priority
        
        # Remove duplicate tasks and sort by urgency
        unique_tasks = []
        task_titles = set()
        
        for task in sorted(all_tasks, key=lambda t: t.urgency.value, reverse=True):
            if task.title not in task_titles:
                unique_tasks.append(task)
                task_titles.add(task.title)
        
        # Create comprehensive plan
        plan_id = f"comprehensive_plan_{datetime.now().isoformat()}"
        
        return CleaningPlan(
            plan_id=plan_id,
            zone_id=None,  # Multi-zone plan
            tasks=unique_tasks,
            priority_score=priority_score,
            source_analysis=f"Combined from {len(analyses)} analyses"
        )
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider.
        
        Returns:
            Dictionary with provider information
        """
        return {
            'name': self.name,
            'initialized': self._is_initialized,
            'available': self.is_available(),
            'last_error': self._last_error,
            'config_keys': list(self.config.keys()) if self.config else []
        }
    
    def _set_error(self, error: str):
        """Set the last error message."""
        self._last_error = error
    
    def _clear_error(self):
        """Clear the last error message."""
        self._last_error = None


class AIProviderError(Exception):
    """Base exception for AI provider errors."""
    
    def __init__(self, message: str, provider_name: Optional[str] = None, original_error: Optional[Exception] = None):
        """
        Initialize AI provider error.
        
        Args:
            message: Error message
            provider_name: Name of the provider that caused the error
            original_error: Original exception that was caught
        """
        self.provider_name = provider_name
        self.original_error = original_error
        super().__init__(message)


class AIProviderUnavailableError(AIProviderError):
    """Raised when AI provider is temporarily unavailable."""
    pass


class AIProviderConfigError(AIProviderError):
    """Raised when AI provider configuration is invalid."""
    pass


class AIProviderAnalysisError(AIProviderError):
    """Raised when image analysis fails."""
    pass


class AIProviderPlanningError(AIProviderError):
    """Raised when cleaning plan creation fails."""
    pass