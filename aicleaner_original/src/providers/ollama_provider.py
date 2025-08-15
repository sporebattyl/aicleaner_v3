"""
Ollama Provider for AICleaner V3
Connects to external user-managed Ollama instance for local LLM processing
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

class OllamaProvider(LLMProvider):
    """
    External Ollama instance provider for local LLM processing
    Connects to user-managed Ollama server for maximum privacy
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
        # External Ollama configuration
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 11434)
        self.base_url = f"http://{self.host}:{self.port}"
        
        # Model configuration
        self.vision_model = config.get('vision_model', 'llava:13b')
        self.text_model = config.get('text_model', 'mistral:7b')
        self.timeout = config.get('timeout', 120)  # Longer timeout for local processing
        self.max_retries = config.get('max_retries', 2)  # Fewer retries for local
        
        # Resource monitoring
        self.max_cpu_percent = config.get('max_cpu_percent', 80)
        self.max_memory_gb = config.get('max_memory_gb', 8)
        
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Cache model info
        self._available_models: Optional[List[str]] = None
        self._model_capabilities: Dict[str, List[ProviderCapability]] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with longer timeout for local processing"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def analyze(self, image: bytes, prompt: str, **kwargs) -> AnalysisResult:
        """
        Analyze image using local Ollama vision model
        
        Args:
            image: Image bytes to analyze
            prompt: Analysis prompt
            **kwargs: Additional options (temperature, etc.)
            
        Returns:
            AnalysisResult with tasks and potential bounding boxes
        """
        start_time = time.time()
        
        try:
            # Check if we should use vision or text model
            model_to_use = self.vision_model if image and len(image) > 0 else self.text_model
            
            # Verify model availability
            if not await self._is_model_available(model_to_use):
                raise ValueError(f"Model {model_to_use} is not available on Ollama instance")
            
            # Create enhanced prompt for local model
            enhanced_prompt = self._create_local_analysis_prompt(prompt)
            
            # Make request to Ollama
            if image and len(image) > 0:
                response_data = await self._make_vision_request(image, enhanced_prompt, model_to_use, **kwargs)
            else:
                response_data = await self._make_text_request(enhanced_prompt, model_to_use, **kwargs)
            
            # Parse response into structured result
            result = await self._parse_ollama_response(response_data, image)
            
            result.processing_time = time.time() - start_time
            result.model_used = model_to_use
            
            self.logger.info(f"Local analysis completed in {result.processing_time:.2f}s, found {len(result.tasks)} tasks")
            return result
            
        except Exception as e:
            self.logger.error(f"Ollama analysis failed: {e}")
            return AnalysisResult(
                tasks=[],
                processing_time=time.time() - start_time,
                model_used=f"{self.vision_model} (failed)"
            )
    
    def _create_local_analysis_prompt(self, base_prompt: str) -> str:
        """Create prompt optimized for local models"""
        return f"""{base_prompt}

You are analyzing an image for cleaning tasks. Please identify specific areas that need cleaning and provide detailed, actionable tasks.

Response format (JSON):
{{
  "tasks": [
    {{
      "description": "Specific cleaning task",
      "priority": 1,
      "confidence": 0.9,
      "estimated_duration": "5 minutes"
    }}
  ],
  "scene_description": "What you see in the image"
}}

Instructions:
- Priority: 1=High (urgent/visible mess), 2=Medium (regular maintenance), 3=Low (minor touch-up)
- Be specific: "wipe coffee spill on counter" not just "clean counter"
- Only identify actual cleaning tasks, not organizing or maintenance
- Estimate realistic duration for each task
- Focus on visible mess, stains, clutter that needs cleaning

Respond with valid JSON only."""
    
    async def _make_vision_request(self, image: bytes, prompt: str, model: str, **kwargs) -> Dict[str, Any]:
        """Make vision request to Ollama API"""
        session = await self._get_session()
        
        # Encode image to base64
        image_b64 = base64.b64encode(image).decode('utf-8')
        
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": kwargs.get('temperature', 0.1),
                "top_p": kwargs.get('top_p', 0.9),
                "num_predict": kwargs.get('max_tokens', 1024)
            }
        }
        
        return await self._execute_ollama_request(session, url, payload)
    
    async def _make_text_request(self, prompt: str, model: str, **kwargs) -> Dict[str, Any]:
        """Make text-only request to Ollama API"""
        session = await self._get_session()
        
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get('temperature', 0.1),
                "top_p": kwargs.get('top_p', 0.9),
                "num_predict": kwargs.get('max_tokens', 1024)
            }
        }
        
        return await self._execute_ollama_request(session, url, payload)
    
    async def _execute_ollama_request(self, session: aiohttp.ClientSession, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute request to Ollama with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Making Ollama request to {self.host}:{self.port} (attempt {attempt + 1})")
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error {response.status}: {error_text}")
                        
            except asyncio.TimeoutError:
                last_exception = Exception(f"Request timeout after {self.timeout}s")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)
                    continue
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
        
        raise last_exception or Exception("All Ollama request attempts failed")
    
    async def _parse_ollama_response(self, response_data: Dict[str, Any], original_image: bytes) -> AnalysisResult:
        """Parse Ollama response into structured result"""
        try:
            response_text = response_data.get('response', '')
            if not response_text:
                raise ValueError("No response text from Ollama")
            
            self.logger.debug(f"Ollama response: {response_text[:200]}...")
            
            # Try to parse as JSON first
            try:
                # Clean up response text
                json_text = response_text.strip()
                if json_text.startswith('```json'):
                    json_text = json_text[7:]
                if json_text.endswith('```'):
                    json_text = json_text[:-3]
                json_text = json_text.strip()
                
                data = json.loads(json_text)
                
                # Parse tasks from JSON
                tasks = []
                for task_data in data.get('tasks', []):
                    task = await self._create_task_from_json(task_data)
                    if task:
                        tasks.append(task)
                
                return AnalysisResult(
                    tasks=tasks,
                    confidence_score=0.8,  # Local models get good confidence score
                    processing_time=0.0
                )
                
            except json.JSONDecodeError:
                # Fallback to text parsing
                return await self._parse_ollama_text_response(response_text)
                
        except Exception as e:
            self.logger.error(f"Failed to parse Ollama response: {e}")
            return AnalysisResult(tasks=[])
    
    async def _create_task_from_json(self, task_data: Dict[str, Any]) -> Optional[Task]:
        """Create Task object from JSON data"""
        try:
            description = task_data.get('description', '').strip()
            if not description:
                return None
            
            # Note: Local models typically don't provide bounding boxes
            # This would require specialized training or post-processing
            return Task(
                description=description,
                priority=task_data.get('priority', 2),
                estimated_duration=task_data.get('estimated_duration'),
                annotation=None,  # Local models don't typically provide coordinates
                confidence=task_data.get('confidence', 0.8)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create task from data {task_data}: {e}")
            return None
    
    async def _parse_ollama_text_response(self, text: str) -> AnalysisResult:
        """Parse free-form text response from Ollama"""
        tasks = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for cleaning tasks
            if any(keyword in line.lower() for keyword in [
                'clean', 'wipe', 'wash', 'vacuum', 'dust', 'scrub', 'mop', 'sweep'
            ]):
                # Remove common prefixes
                for prefix in ['- ', '* ', '• ', '1. ', '2. ', '3. ', '4. ', '5. ']:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                        break
                
                if len(line) > 10:  # Reasonable minimum length
                    task = Task(
                        description=line,
                        priority=2,
                        confidence=0.7  # Good confidence for local processing
                    )
                    tasks.append(task)
        
        return AnalysisResult(
            tasks=tasks,
            confidence_score=0.7
        )
    
    async def health_check(self) -> ProviderHealth:
        """Check Ollama instance health and resource usage"""
        start_time = time.time()
        
        try:
            session = await self._get_session()
            
            # Check if Ollama is running
            url = f"{self.base_url}/api/tags"
            
            async with session.get(url) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    models = data.get('models', [])
                    
                    # Check if required models are available
                    model_names = [model['name'] for model in models]
                    has_vision = any(self.vision_model.split(':')[0] in name for name in model_names)
                    has_text = any(self.text_model.split(':')[0] in name for name in model_names)
                    
                    # Get system resources if available
                    resource_usage = await self._get_system_resources()
                    
                    # Determine health status
                    if has_vision and has_text:
                        status = ProviderStatus.HEALTHY
                        message = f"All models available: {len(models)} total"
                    elif has_vision or has_text:
                        status = ProviderStatus.DEGRADED
                        message = f"Some models missing (have {len(models)} models)"
                    else:
                        status = ProviderStatus.UNHEALTHY
                        message = f"Required models not found (have {len(models)} models)"
                    
                    # Check resource usage
                    if resource_usage:
                        cpu_usage = resource_usage.get('cpu_percent', 0)
                        memory_gb = resource_usage.get('memory_gb', 0)
                        
                        if cpu_usage > self.max_cpu_percent or memory_gb > self.max_memory_gb:
                            status = ProviderStatus.DEGRADED
                            message += f" (High resource usage: CPU {cpu_usage:.1f}%, Memory {memory_gb:.1f}GB)"
                    
                    return ProviderHealth(
                        status=status,
                        response_time=response_time,
                        error_message=message if status != ProviderStatus.HEALTHY else None,
                        resource_usage=resource_usage,
                        last_checked=datetime.now().isoformat()
                    )
                else:
                    error_text = await response.text()
                    return ProviderHealth(
                        status=ProviderStatus.UNHEALTHY,
                        response_time=response_time,
                        error_message=f"Ollama not responding: HTTP {response.status}",
                        last_checked=datetime.now().isoformat()
                    )
                    
        except aiohttp.ClientConnectorError:
            return ProviderHealth(
                status=ProviderStatus.UNHEALTHY,
                response_time=(time.time() - start_time) * 1000,
                error_message=f"Cannot connect to Ollama at {self.host}:{self.port}",
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
    
    async def _get_system_resources(self) -> Optional[Dict[str, float]]:
        """Get system resource usage (if available)"""
        try:
            import psutil
            
            # Get CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_gb = (memory.total - memory.available) / (1024**3)
            
            return {
                'cpu_percent': cpu_percent,
                'memory_gb': memory_gb,
                'memory_percent': memory.percent
            }
        except ImportError:
            # psutil not available
            return None
        except Exception:
            return None
    
    async def _is_model_available(self, model_name: str) -> bool:
        """Check if specific model is available"""
        try:
            if self._available_models is None:
                await self._refresh_model_list()
            
            # Check if model (with or without tag) is available
            model_base = model_name.split(':')[0]
            return any(model_base in available for available in (self._available_models or []))
        except Exception:
            return False
    
    async def _refresh_model_list(self) -> None:
        """Refresh the list of available models"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/api/tags"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get('models', [])
                    self._available_models = [model['name'] for model in models]
                else:
                    self._available_models = []
        except Exception:
            self._available_models = []
    
    def get_capabilities(self) -> List[ProviderCapability]:
        """Get supported capabilities"""
        capabilities = [ProviderCapability.TEXT]
        
        # Check if vision model is configured
        if self.vision_model and 'llava' in self.vision_model.lower():
            capabilities.append(ProviderCapability.VISION)
        
        # Local models typically don't support advanced visual grounding
        # This would require specialized training or post-processing
        
        return capabilities
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull/download a model to the Ollama instance"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/api/pull"
            
            payload = {"name": model_name}
            
            self.logger.info(f"Pulling model {model_name} (this may take a while)...")
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    # Stream the response to show progress
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                if 'status' in data:
                                    self.logger.info(f"Pull progress: {data['status']}")
                            except json.JSONDecodeError:
                                pass
                    
                    # Refresh model list
                    await self._refresh_model_list()
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Failed to pull model {model_name}: {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    async def close(self) -> None:
        """Clean up resources"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

class OllamaProviderFactory:
    """Factory for creating Ollama provider instances"""
    
    @staticmethod
    def create_provider(config: Dict[str, Any]) -> OllamaProvider:
        """
        Create an Ollama provider instance
        
        Args:
            config: Configuration dictionary containing:
                - host: Ollama server host (default: localhost)
                - port: Ollama server port (default: 11434)  
                - vision_model: Vision model name (default: llava:13b)
                - text_model: Text model name (default: mistral:7b)
                - timeout: Request timeout (default: 120)
                - max_cpu_percent: CPU usage threshold (default: 80)
                - max_memory_gb: Memory usage threshold (default: 8)
                
        Returns:
            Configured OllamaProvider instance
        """
        name = config.get('name', 'ollama')
        return OllamaProvider(name, config)
    
    @staticmethod
    async def create_and_verify(config: Dict[str, Any]) -> Optional[OllamaProvider]:
        """Create provider and verify it's working"""
        provider = OllamaProviderFactory.create_provider(config)
        
        # Test connectivity
        health = await provider.health_check()
        if health.status == ProviderStatus.UNHEALTHY:
            provider.logger.error(f"Ollama provider unhealthy: {health.error_message}")
            await provider.close()
            return None
        
        return provider