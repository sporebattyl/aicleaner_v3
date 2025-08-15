import asyncio
import aiohttp
import time
import logging
import base64
from typing import Dict, Any, Optional
from .base_provider import (
    LLMProvider, 
    AnalysisResult, 
    ProviderHealth,
    ProviderStatus,
    ProviderCapabilities, 
    PrivacyLevel
)

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'gemini-1.5-flash')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_retries = config.get('max_retries', 3)
        self.timeout = config.get('timeout', 30)
        
    async def initialize(self) -> bool:
        """Initialize the Gemini provider."""
        if not self.api_key:
            logger.error("Gemini API key not provided")
            return False
            
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        
        # Test connectivity
        health = await self.health_check()
        return health.status != ProviderStatus.OFFLINE
        
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.session:
            await self.session.close()
            
    def get_capabilities(self) -> ProviderCapabilities:
        """Return Gemini provider capabilities."""
        return ProviderCapabilities(
            supported_privacy_levels=[PrivacyLevel.FAST, PrivacyLevel.HYBRID],
            max_image_size_mb=20.0,
            supports_batch_processing=False,
            max_concurrent_requests=10,
            estimated_cost_per_request=0.002  # Approximate cost in USD
        )
        
    async def health_check(self) -> ProviderHealth:
        """Check Gemini API health."""
        start_time = time.time()
        
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            
            async with self.session.get(url) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    return ProviderHealth(
                        status=ProviderStatus.HEALTHY,
                        response_time_ms=response_time,
                        error_rate=0.0,
                        last_check=time.time()
                    )
                else:
                    error_msg = f"HTTP {response.status}: {await response.text()}"
                    return ProviderHealth(
                        status=ProviderStatus.UNHEALTHY,
                        response_time_ms=response_time,
                        error_rate=1.0,
                        last_check=time.time(),
                        error_message=error_msg
                    )
                    
        except Exception as e:
            return ProviderHealth(
                status=ProviderStatus.OFFLINE,
                response_time_ms=0.0,
                error_rate=1.0,
                last_check=time.time(),
                error_message=str(e)
            )
            
    async def analyze(self, image_data: bytes, prompt: str, privacy_level: PrivacyLevel) -> AnalysisResult:
        """Analyze image using Gemini API."""
        start_time = time.time()
        
        try:
            # For HYBRID privacy level, we could extract metadata locally first
            # For now, implementing FAST mode (direct image to API)
            if privacy_level == PrivacyLevel.PRIVATE:
                raise ValueError("Private privacy level not supported by GeminiProvider")
                
            # Encode image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Build the analysis prompt
            analysis_prompt = self._build_analysis_prompt(prompt)
            
            # Prepare API request
            url = f"{self.base_url}/models/{self.model}:generateContent"
            headers = {
                'Content-Type': 'application/json'
            }
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": analysis_prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",  # Assume JPEG for now
                                "data": image_b64
                            }
                        }
                    ]
                }]
            }
            
            # Make request with retries
            for attempt in range(self.max_retries):
                try:
                    async with self.session.post(
                        f"{url}?key={self.api_key}", 
                        json=payload, 
                        headers=headers
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            return self._parse_response(result, time.time() - start_time)
                        else:
                            error_text = await response.text()
                            if attempt == self.max_retries - 1:
                                raise Exception(f"API error: {response.status} - {error_text}")
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            
                except asyncio.TimeoutError:
                    if attempt == self.max_retries - 1:
                        raise Exception("Request timeout")
                    await asyncio.sleep(2 ** attempt)
                    
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return AnalysisResult(
                action="keep",  # Conservative default
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                metadata={"error": str(e)},
                processing_time=time.time() - start_time
            )
            
    def _build_analysis_prompt(self, base_prompt: str) -> str:
        """Build the complete analysis prompt."""
        return f"""
You are an AI assistant helping to clean up a photo collection. Analyze this image and determine if it should be kept or deleted.

{base_prompt}

Respond in this exact JSON format:
{{
    "action": "keep" or "delete",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation of your decision",
    "metadata": {{
        "detected_objects": ["list", "of", "objects"],
        "image_quality": "poor|fair|good|excellent",
        "contains_people": true/false,
        "is_duplicate": true/false
    }}
}}
        """.strip()
        
    def _parse_response(self, response: Dict[str, Any], processing_time: float) -> AnalysisResult:
        """Parse Gemini API response into AnalysisResult."""
        try:
            # Extract text from response
            candidates = response.get('candidates', [])
            if not candidates:
                raise ValueError("No candidates in response")
                
            content = candidates[0].get('content', {})
            parts = content.get('parts', [])
            if not parts:
                raise ValueError("No parts in response content")
                
            text_response = parts[0].get('text', '')
            
            # Try to parse as JSON
            import json
            # Extract JSON from response (might have extra text)
            json_start = text_response.find('{')
            json_end = text_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
                
            json_str = text_response[json_start:json_end]
            parsed = json.loads(json_str)
            
            return AnalysisResult(
                action=parsed.get('action', 'keep'),
                confidence=float(parsed.get('confidence', 0.5)),
                reasoning=parsed.get('reasoning', 'No reasoning provided'),
                metadata=parsed.get('metadata', {}),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return AnalysisResult(
                action="keep",
                confidence=0.0,
                reasoning=f"Response parsing failed: {str(e)}",
                metadata={"raw_response": str(response)},
                processing_time=processing_time
            )