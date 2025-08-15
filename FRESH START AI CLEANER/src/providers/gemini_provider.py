"""
Gemini Provider for AICleaner V3
Enhanced with visual grounding capabilities for bounding box annotations
"""

import asyncio
import base64
import json
import time
from typing import Dict, Any, List, Optional, Tuple
import aiohttp
import logging
from datetime import datetime

from .base_provider import (
    LLMProvider, AnalysisResult, Task, BoundingBox, 
    ProviderHealth, ProviderStatus, ProviderCapability
)

class GeminiProvider(LLMProvider):
    """
    Google Gemini API provider with visual grounding support
    Supports both Gemini Pro and Gemini Pro Vision models
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'gemini-pro-vision')
        self.base_url = config.get('base_url', 'https://generativelanguage.googleapis.com/v1beta')
        self.max_retries = config.get('max_retries', 3)
        self.timeout = config.get('timeout', 30)
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        if not self.api_key:
            raise ValueError("Gemini API key is required")
        
        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def analyze(self, image: bytes, prompt: str, **kwargs) -> AnalysisResult:
        """
        Analyze image using Gemini Vision API with visual grounding
        
        Args:
            image: Image bytes to analyze
            prompt: Analysis prompt
            **kwargs: Additional options (temperature, max_tokens, etc.)
            
        Returns:
            AnalysisResult with tasks and bounding box annotations
        """
        start_time = time.time()
        
        try:
            # Prepare the request
            enhanced_prompt = self._create_analysis_prompt(prompt)
            
            # Handle metadata-only requests (empty image bytes)
            if not image or len(image) == 0:
                return await self._analyze_metadata_only(enhanced_prompt, **kwargs)
            
            # Make API request with retries
            response_data = await self._make_api_request(image, enhanced_prompt, **kwargs)
            
            # Parse response into structured result
            result = await self._parse_gemini_response(response_data, image)
            
            result.processing_time = time.time() - start_time
            result.model_used = self.model
            
            self.logger.info(f"Analysis completed in {result.processing_time:.2f}s, found {len(result.tasks)} tasks")
            return result
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return AnalysisResult(
                tasks=[],
                processing_time=time.time() - start_time,
                model_used=self.model
            )
    
    async def _analyze_metadata_only(self, prompt: str, **kwargs) -> AnalysisResult:
        """Handle metadata-only analysis for privacy level 3"""
        try:
            session = await self._get_session()
            
            # Use text-only model for metadata analysis
            url = f"{self.base_url}/models/gemini-pro:generateContent?key={self.api_key}"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return await self._parse_text_response(data)
                else:
                    error_text = await response.text()
                    raise Exception(f"Gemini API error {response.status}: {error_text}")
                    
        except Exception as e:
            self.logger.error(f"Metadata analysis failed: {e}")
            return AnalysisResult(tasks=[])
    
    def _create_analysis_prompt(self, base_prompt: str) -> str:
        """Create enhanced prompt for visual grounding"""
        return f"""{base_prompt}

Please analyze this image for cleaning tasks and provide your response in this exact JSON format:

{{
  "tasks": [
    {{
      "description": "Specific cleaning task description",
      "priority": 1,
      "confidence": 0.9,
      "estimated_duration": "5 minutes",
      "bounding_box": {{
        "x1": 100,
        "y1": 150,
        "x2": 300,
        "y2": 400
      }}
    }}
  ],
  "overall_confidence": 0.85,
  "scene_description": "Brief description of what you see"
}}

IMPORTANT INSTRUCTIONS:
1. Priority: 1=High, 2=Medium, 3=Low
2. Confidence: 0.0 to 1.0 (how certain you are about this task)
3. Bounding box: Coordinates of the area that needs attention (x1,y1 = top-left, x2,y2 = bottom-right)
4. Be specific in descriptions: instead of "clean counter" say "wipe coffee spill on kitchen counter"
5. Only identify actual cleaning tasks, not maintenance or organization
6. Estimate realistic time duration for each task
7. Provide bounding boxes for all tasks when possible

Respond ONLY with valid JSON, no other text."""
    
    async def _make_api_request(self, image: bytes, prompt: str, **kwargs) -> Dict[str, Any]:
        """Make API request to Gemini with retry logic"""
        session = await self._get_session()
        
        # Encode image to base64
        image_b64 = base64.b64encode(image).decode('utf-8')
        
        # Prepare request
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": kwargs.get('temperature', 0.1),
                "maxOutputTokens": kwargs.get('max_tokens', 2048),
                "topP": kwargs.get('top_p', 0.8),
                "topK": kwargs.get('top_k', 40)
            }
        }
        
        # Retry logic
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Making Gemini API request (attempt {attempt + 1}/{self.max_retries})")
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:
                        # Rate limiting - wait and retry
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"API error {response.status}: {error_text}")
                        
            except asyncio.TimeoutError:
                last_exception = Exception(f"Request timeout after {self.timeout}s")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
        
        # All retries failed
        raise last_exception or Exception("All retry attempts failed")
    
    async def _parse_gemini_response(self, response_data: Dict[str, Any], original_image: bytes) -> AnalysisResult:
        """Parse Gemini API response into structured result"""
        try:
            # Extract text from Gemini response
            candidates = response_data.get('candidates', [])
            if not candidates:
                raise ValueError("No candidates in response")
            
            content = candidates[0].get('content', {})
            parts = content.get('parts', [])
            if not parts:
                raise ValueError("No parts in response content")
            
            text = parts[0].get('text', '')
            if not text:
                raise ValueError("No text in response")
            
            self.logger.debug(f"Gemini response text: {text[:200]}...")
            
            # Try to parse as JSON
            try:
                # Clean up the response text
                json_text = text.strip()
                if json_text.startswith('```json'):
                    json_text = json_text[7:]
                if json_text.endswith('```'):
                    json_text = json_text[:-3]
                json_text = json_text.strip()
                
                data = json.loads(json_text)
            except json.JSONDecodeError:
                # Fallback: try to extract tasks from free-form text
                return await self._parse_freeform_response(text, original_image)
            
            # Parse structured JSON response
            tasks = []
            for task_data in data.get('tasks', []):
                task = await self._create_task_from_json(task_data)
                if task:
                    tasks.append(task)
            
            return AnalysisResult(
                tasks=tasks,
                confidence_score=data.get('overall_confidence', 0.8),
                processing_time=0.0  # Will be set by caller
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse Gemini response: {e}")
            # Fallback to extracting basic tasks
            return await self._parse_freeform_response(
                str(response_data), 
                original_image
            )
    
    async def _create_task_from_json(self, task_data: Dict[str, Any]) -> Optional[Task]:
        """Create Task object from JSON data"""
        try:
            description = task_data.get('description', '').strip()
            if not description:
                return None
            
            # Parse bounding box if present
            bbox = None
            bbox_data = task_data.get('bounding_box')
            if bbox_data:
                try:
                    bbox = BoundingBox(
                        x1=int(bbox_data.get('x1', 0)),
                        y1=int(bbox_data.get('y1', 0)),
                        x2=int(bbox_data.get('x2', 0)),
                        y2=int(bbox_data.get('y2', 0))
                    )
                    
                    # Validate bounding box
                    if bbox.width <= 0 or bbox.height <= 0:
                        bbox = None
                except (ValueError, TypeError):
                    bbox = None
            
            return Task(
                description=description,
                priority=task_data.get('priority', 2),
                estimated_duration=task_data.get('estimated_duration'),
                annotation=bbox,
                confidence=task_data.get('confidence', 0.8)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create task from data {task_data}: {e}")
            return None
    
    async def _parse_freeform_response(self, text: str, original_image: bytes) -> AnalysisResult:
        """Parse free-form text response into tasks (fallback method)"""
        tasks = []
        
        # Simple heuristic parsing
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for task-like lines
            if any(keyword in line.lower() for keyword in ['clean', 'wipe', 'wash', 'vacuum', 'dust', 'organize']):
                # Remove common prefixes
                for prefix in ['- ', '* ', '1. ', '2. ', '3. ', '4. ', '5. ']:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                        break
                
                if len(line) > 5:  # Reasonable minimum length
                    task = Task(
                        description=line,
                        priority=2,  # Default medium priority
                        confidence=0.6  # Lower confidence for parsed text
                    )
                    tasks.append(task)
        
        return AnalysisResult(
            tasks=tasks,
            confidence_score=0.6  # Lower confidence for fallback parsing
        )
    
    async def _parse_text_response(self, response_data: Dict[str, Any]) -> AnalysisResult:
        """Parse text-only response for metadata analysis"""
        try:
            candidates = response_data.get('candidates', [])
            if candidates:
                content = candidates[0].get('content', {})
                parts = content.get('parts', [])
                if parts:
                    text = parts[0].get('text', '')
                    return await self._parse_freeform_response(text, b'')
            
            return AnalysisResult(tasks=[])
            
        except Exception as e:
            self.logger.error(f"Failed to parse text response: {e}")
            return AnalysisResult(tasks=[])
    
    async def health_check(self) -> ProviderHealth:
        """Check Gemini API health and connectivity"""
        start_time = time.time()
        
        try:
            session = await self._get_session()
            
            # Simple health check using models endpoint
            url = f"{self.base_url}/models?key={self.api_key}"
            
            async with session.get(url) as response:
                response_time = (time.time() - start_time) * 1000  # milliseconds
                
                if response.status == 200:
                    return ProviderHealth(
                        status=ProviderStatus.HEALTHY,
                        response_time=response_time,
                        last_checked=datetime.now().isoformat()
                    )
                elif response.status == 401:
                    return ProviderHealth(
                        status=ProviderStatus.UNHEALTHY,
                        response_time=response_time,
                        error_message="Invalid API key",
                        last_checked=datetime.now().isoformat()
                    )
                elif response.status == 429:
                    return ProviderHealth(
                        status=ProviderStatus.DEGRADED,
                        response_time=response_time,
                        error_message="Rate limited",
                        last_checked=datetime.now().isoformat()
                    )
                else:
                    error_text = await response.text()
                    return ProviderHealth(
                        status=ProviderStatus.UNHEALTHY,
                        response_time=response_time,
                        error_message=f"HTTP {response.status}: {error_text}",
                        last_checked=datetime.now().isoformat()
                    )
                    
        except asyncio.TimeoutError:
            return ProviderHealth(
                status=ProviderStatus.UNHEALTHY,
                response_time=(time.time() - start_time) * 1000,
                error_message="Health check timeout",
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return ProviderHealth(
                status=ProviderStatus.UNHEALTHY,
                response_time=(time.time() - start_time) * 1000,
                error_message=str(e),
                last_checked=datetime.now().isoformat()
            )
    
    def get_capabilities(self) -> List[ProviderCapability]:
        """Get supported capabilities"""
        return [
            ProviderCapability.VISION,
            ProviderCapability.TEXT,
            ProviderCapability.VISUAL_GROUNDING,  # Supports bounding boxes
            ProviderCapability.OBJECT_DETECTION
        ]
    
    async def close(self) -> None:
        """Clean up resources"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def __del__(self):
        """Ensure session cleanup on deletion"""
        if hasattr(self, '_session') and self._session and not self._session.closed:
            # Note: This is not ideal as we can't await in __del__
            # Better to call close() explicitly
            pass

class GeminiProviderFactory:
    """Factory for creating Gemini provider instances"""
    
    @staticmethod
    def create_provider(config: Dict[str, Any]) -> GeminiProvider:
        """
        Create a Gemini provider instance
        
        Args:
            config: Configuration dictionary containing:
                - api_key: Gemini API key (required)
                - model: Model name (default: gemini-pro-vision)
                - max_retries: Maximum retry attempts (default: 3)
                - timeout: Request timeout in seconds (default: 30)
                
        Returns:
            Configured GeminiProvider instance
        """
        name = config.get('name', 'gemini')
        return GeminiProvider(name, config)
    
    @staticmethod
    def create_multiple_providers(configs: List[Dict[str, Any]]) -> List[GeminiProvider]:
        """Create multiple Gemini provider instances (for API key rotation)"""
        providers = []
        for i, config in enumerate(configs):
            if 'name' not in config:
                config['name'] = f"gemini_{i+1}"
            providers.append(GeminiProviderFactory.create_provider(config))
        return providers