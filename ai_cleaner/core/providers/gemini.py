"""
Google Gemini AI provider implementation for image analysis and cleaning plan generation.
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import base64
from io import BytesIO

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold, GenerationConfig
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

from .base import (
    BaseAIProvider, ImageAnalysis, CleaningPlan, CleaningTask, AreaCondition,
    AnalysisConfidence, CleaningUrgency, TaskCategory,
    AIProviderError, AIProviderUnavailableError, AIProviderConfigError, AIProviderAnalysisError
)


logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider for image analysis and cleaning task generation."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Gemini provider.
        
        Args:
            config: Configuration dictionary with 'api_key' and optional 'model'
        """
        super().__init__("gemini", config)
        
        if not GEMINI_AVAILABLE:
            raise AIProviderConfigError("Gemini dependencies not available. Install google-generativeai package.")
        
        self.api_key = config.get('api_key')
        self.model_name = config.get('model', 'gemini-1.5-pro')
        self.max_retries = config.get('max_retries', 3)
        self.timeout_seconds = config.get('timeout_seconds', 120)
        
        self._model = None
        self._generation_config = None
        self._safety_settings = None
        
        if not self.api_key:
            raise AIProviderConfigError("Gemini API key is required")
    
    async def initialize(self) -> bool:
        """Initialize the Gemini provider."""
        try:
            # Configure Gemini
            genai.configure(api_key=self.api_key)
            
            # Create model instance
            self._model = genai.GenerativeModel(self.model_name)
            
            # Configure generation settings
            self._generation_config = GenerationConfig(
                temperature=0.3,  # Lower temperature for more consistent analysis
                top_p=0.8,
                top_k=40,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
            
            # Configure safety settings (be more permissive for cleaning analysis)
            self._safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Test the model with a simple request
            test_response = await self._test_model()
            if test_response:
                self._is_initialized = True
                self._clear_error()
                logger.info("Gemini provider initialized successfully")
                return True
            else:
                self._set_error("Model test failed during initialization")
                return False
        
        except Exception as e:
            error_msg = f"Failed to initialize Gemini provider: {e}"
            logger.error(error_msg)
            self._set_error(error_msg)
            return False
    
    async def _test_model(self) -> bool:
        """Test the model with a simple request."""
        try:
            prompt = "Respond with just the word 'ready' to confirm the model is working."
            response = await self._generate_response(prompt)
            return response and 'ready' in response.lower()
        except Exception as e:
            logger.warning(f"Model test failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Gemini provider."""
        health = {
            'status': 'healthy',
            'provider': 'gemini',
            'initialized': self._is_initialized,
            'available': self.is_available(),
            'model': self.model_name,
            'last_error': self._last_error,
            'test_response_time_ms': None
        }
        
        if not self._is_initialized:
            health['status'] = 'uninitialized'
            return health
        
        # Test response time
        start_time = datetime.now()
        try:
            test_success = await self._test_model()
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            health['test_response_time_ms'] = int(response_time)
            
            if not test_success:
                health['status'] = 'degraded'
                health['last_error'] = 'Model test failed'
        
        except Exception as e:
            health['status'] = 'unhealthy'
            health['last_error'] = str(e)
        
        return health
    
    def is_available(self) -> bool:
        """Check if Gemini provider is available."""
        return GEMINI_AVAILABLE and self._is_initialized and self._model is not None
    
    async def analyze_image(
        self, 
        image_data: bytes, 
        zone_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ImageAnalysis:
        """Analyze image for cleanliness using Gemini Vision."""
        if not self.is_available():
            raise AIProviderUnavailableError("Gemini provider is not available", self.name)
        
        start_time = datetime.now()
        
        try:
            # Prepare the image
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(zone_id, context)
            
            # Create the input for Gemini
            contents = [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",  # Assume JPEG, Gemini handles various formats
                                "data": image_b64
                            }
                        }
                    ]
                }
            ]
            
            # Generate response
            response_text = await self._generate_response_with_image(contents)
            
            # Parse response
            analysis = self._parse_analysis_response(response_text, zone_id)
            
            # Set processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            analysis.processing_time_seconds = processing_time
            
            logger.info(f"Image analysis completed in {processing_time:.2f}s for zone {zone_id}")
            return analysis
        
        except Exception as e:
            error_msg = f"Failed to analyze image: {e}"
            logger.error(error_msg)
            raise AIProviderAnalysisError(error_msg, self.name, e)
    
    def _create_analysis_prompt(self, zone_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """Create the analysis prompt for Gemini."""
        base_prompt = """
You are an expert home cleaning analyst. Analyze this image and assess the cleanliness and organization of the space. 

Provide your analysis in the following JSON format:

{
  "overall_cleanliness_score": 0.85,
  "confidence": "high",
  "summary": "Brief one-sentence summary of the overall condition",
  "detailed_analysis": "Detailed paragraph describing what you observe",
  "areas_assessed": [
    {
      "area_name": "Kitchen Counter",
      "cleanliness_score": 0.7,
      "confidence": "high",
      "issues_detected": ["Water stains", "Crumbs visible"],
      "recommended_actions": ["Wipe down surfaces", "Clear items"]
    }
  ],
  "suggested_tasks": [
    {
      "title": "Wipe Kitchen Counters",
      "description": "Clean and sanitize all counter surfaces",
      "category": "sanitizing",
      "urgency": 2,
      "estimated_minutes": 10,
      "tools_needed": ["All-purpose cleaner", "Microfiber cloth"]
    }
  ]
}

Guidelines:
- cleanliness_score: 0.0 = very dirty, 1.0 = spotless
- confidence: "low", "medium", "high", "very_high"
- category: "dusting", "vacuuming", "mopping", "organizing", "sanitizing", "deep_cleaning", "maintenance", "inspection"
- urgency: 1 = low, 2 = medium, 3 = high, 4 = critical
- Be specific about issues and actionable in recommendations
- Focus on cleanliness, organization, and hygiene
- Estimate realistic time requirements
"""
        
        if zone_id:
            base_prompt += f"\n\nThis image is from the {zone_id} area. Consider this context in your analysis."
        
        if context:
            if context.get('previous_score'):
                base_prompt += f"\n\nPrevious cleanliness score for comparison: {context['previous_score']}"
            if context.get('time_since_last_clean'):
                base_prompt += f"\n\nTime since last cleaning: {context['time_since_last_clean']}"
        
        return base_prompt
    
    async def _generate_response_with_image(self, contents: List[Dict]) -> str:
        """Generate response from Gemini with image input."""
        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    self._model.generate_content_async(
                        contents,
                        generation_config=self._generation_config,
                        safety_settings=self._safety_settings
                    ),
                    timeout=self.timeout_seconds
                )
                
                if response.text:
                    return response.text.strip()
                else:
                    raise AIProviderAnalysisError("Empty response from Gemini")
            
            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Gemini request timed out, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise AIProviderAnalysisError("Request timed out after all retries")
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Gemini request failed: {e}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise AIProviderAnalysisError(f"Request failed after all retries: {e}")
    
    async def _generate_response(self, prompt: str) -> str:
        """Generate text response from Gemini."""
        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    self._model.generate_content_async(
                        prompt,
                        generation_config=self._generation_config,
                        safety_settings=self._safety_settings
                    ),
                    timeout=self.timeout_seconds
                )
                
                if response.text:
                    return response.text.strip()
                else:
                    raise AIProviderAnalysisError("Empty response from Gemini")
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Gemini request failed: {e}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise
    
    def _parse_analysis_response(self, response_text: str, zone_id: Optional[str] = None) -> ImageAnalysis:
        """Parse Gemini response into ImageAnalysis object."""
        try:
            # Clean up the response text (remove markdown code blocks if present)
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            data = json.loads(clean_text)
            
            # Parse areas assessed
            areas_assessed = []
            for area_data in data.get('areas_assessed', []):
                confidence_str = area_data.get('confidence', 'medium').lower()
                confidence = self._parse_confidence(confidence_str)
                
                area = AreaCondition(
                    area_name=area_data.get('area_name', 'Unknown Area'),
                    cleanliness_score=float(area_data.get('cleanliness_score', 0.5)),
                    confidence=confidence,
                    issues_detected=area_data.get('issues_detected', []),
                    recommended_actions=area_data.get('recommended_actions', [])
                )
                areas_assessed.append(area)
            
            # Parse suggested tasks
            suggested_tasks = []
            for task_data in data.get('suggested_tasks', []):
                task_id = str(uuid.uuid4())
                
                # Parse category
                category_str = task_data.get('category', 'sanitizing').lower()
                category = self._parse_category(category_str)
                
                # Parse urgency
                urgency_val = int(task_data.get('urgency', 2))
                urgency = CleaningUrgency(max(1, min(4, urgency_val)))
                
                task = CleaningTask(
                    id=task_id,
                    title=task_data.get('title', 'Cleaning Task'),
                    description=task_data.get('description', ''),
                    category=category,
                    urgency=urgency,
                    estimated_minutes=int(task_data.get('estimated_minutes', 15)),
                    zone_id=zone_id,
                    tools_needed=task_data.get('tools_needed', []),
                    prerequisites=task_data.get('prerequisites', [])
                )
                suggested_tasks.append(task)
            
            # Parse confidence
            confidence_str = data.get('confidence', 'medium').lower()
            confidence = self._parse_confidence(confidence_str)
            
            # Create analysis object
            analysis = ImageAnalysis(
                zone_id=zone_id,
                overall_cleanliness_score=float(data.get('overall_cleanliness_score', 0.5)),
                confidence=confidence,
                summary=data.get('summary', 'Analysis completed'),
                detailed_analysis=data.get('detailed_analysis', 'No detailed analysis provided'),
                areas_assessed=areas_assessed,
                suggested_tasks=suggested_tasks
            )
            
            return analysis
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            return self._create_fallback_analysis(zone_id, f"JSON parsing failed: {e}")
        
        except Exception as e:
            logger.error(f"Failed to parse analysis response: {e}")
            return self._create_fallback_analysis(zone_id, f"Response parsing failed: {e}")
    
    def _parse_confidence(self, confidence_str: str) -> AnalysisConfidence:
        """Parse confidence string to enum."""
        confidence_map = {
            'low': AnalysisConfidence.LOW,
            'medium': AnalysisConfidence.MEDIUM,
            'high': AnalysisConfidence.HIGH,
            'very_high': AnalysisConfidence.VERY_HIGH
        }
        return confidence_map.get(confidence_str, AnalysisConfidence.MEDIUM)
    
    def _parse_category(self, category_str: str) -> TaskCategory:
        """Parse category string to enum."""
        category_map = {
            'dusting': TaskCategory.DUSTING,
            'vacuuming': TaskCategory.VACUUMING,
            'mopping': TaskCategory.MOPPING,
            'organizing': TaskCategory.ORGANIZING,
            'sanitizing': TaskCategory.SANITIZING,
            'deep_cleaning': TaskCategory.DEEP_CLEANING,
            'maintenance': TaskCategory.MAINTENANCE,
            'inspection': TaskCategory.INSPECTION
        }
        return category_map.get(category_str, TaskCategory.SANITIZING)
    
    def _create_fallback_analysis(self, zone_id: Optional[str], error: str) -> ImageAnalysis:
        """Create fallback analysis when parsing fails."""
        return ImageAnalysis(
            zone_id=zone_id,
            overall_cleanliness_score=0.5,
            confidence=AnalysisConfidence.LOW,
            summary="Analysis parsing failed, manual review recommended",
            detailed_analysis=f"Failed to parse AI response: {error}",
            areas_assessed=[],
            suggested_tasks=[
                CleaningTask(
                    id=str(uuid.uuid4()),
                    title="Manual Inspection Required",
                    description="AI analysis failed, manual inspection needed",
                    category=TaskCategory.INSPECTION,
                    urgency=CleaningUrgency.MEDIUM,
                    estimated_minutes=5,
                    zone_id=zone_id
                )
            ]
        )
    
    async def create_cleaning_plan(
        self, 
        analysis: ImageAnalysis,
        constraints: Optional[Dict[str, Any]] = None
    ) -> CleaningPlan:
        """Create cleaning plan from analysis (uses tasks from analysis)."""
        plan_id = f"gemini_plan_{datetime.now().isoformat()}"
        
        # Filter and prioritize tasks based on constraints
        filtered_tasks = analysis.suggested_tasks.copy()
        
        if constraints:
            max_time = constraints.get('max_time_minutes')
            if max_time:
                # Sort by urgency and filter by time
                filtered_tasks = sorted(filtered_tasks, key=lambda t: t.urgency.value, reverse=True)
                total_time = 0
                time_filtered_tasks = []
                
                for task in filtered_tasks:
                    if total_time + task.estimated_minutes <= max_time:
                        time_filtered_tasks.append(task)
                        total_time += task.estimated_minutes
                
                filtered_tasks = time_filtered_tasks
            
            # Filter by available tools
            available_tools = constraints.get('available_tools', [])
            if available_tools:
                tool_filtered_tasks = []
                for task in filtered_tasks:
                    task_tools = set(task.tools_needed or [])
                    available_tools_set = set(available_tools)
                    if not task_tools or task_tools.issubset(available_tools_set):
                        tool_filtered_tasks.append(task)
                filtered_tasks = tool_filtered_tasks
        
        # Calculate priority score (lower cleanliness = higher priority)
        priority_score = 1.0 - analysis.overall_cleanliness_score
        
        # Set expiration time (plans expire in 24 hours)
        expires_at = datetime.now() + timedelta(hours=24)
        
        return CleaningPlan(
            plan_id=plan_id,
            zone_id=analysis.zone_id,
            tasks=filtered_tasks,
            priority_score=priority_score,
            expires_at=expires_at,
            source_analysis=f"Gemini analysis at {analysis.analysis_timestamp}"
        )
    
    async def refine_analysis(
        self,
        previous_analysis: ImageAnalysis,
        new_image_data: bytes,
        progress_context: Optional[Dict[str, Any]] = None
    ) -> ImageAnalysis:
        """Refine previous analysis with new image and progress context."""
        # Create context for refinement
        context = {
            'previous_score': previous_analysis.overall_cleanliness_score,
            'previous_summary': previous_analysis.summary,
        }
        
        if progress_context:
            context.update(progress_context)
            if 'completed_tasks' in progress_context:
                context['completed_tasks_count'] = len(progress_context['completed_tasks'])
        
        # Perform new analysis with context
        new_analysis = await self.analyze_image(
            new_image_data, 
            previous_analysis.zone_id,
            context
        )
        
        # Calculate improvement score
        improvement = new_analysis.overall_cleanliness_score - previous_analysis.overall_cleanliness_score
        
        # Add improvement context to detailed analysis
        improvement_text = ""
        if improvement > 0.1:
            improvement_text = f" Significant improvement detected (+{improvement:.2f} cleanliness score)."
        elif improvement > 0.05:
            improvement_text = f" Moderate improvement detected (+{improvement:.2f} cleanliness score)."
        elif improvement < -0.05:
            improvement_text = f" Condition has declined ({improvement:.2f} cleanliness score)."
        else:
            improvement_text = " Minimal change in condition."
        
        new_analysis.detailed_analysis += improvement_text
        
        return new_analysis