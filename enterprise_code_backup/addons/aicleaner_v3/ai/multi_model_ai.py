"""
Multi-Model AI Support for AICleaner
Supports Gemini, Claude 3.5 Sonnet, and GPT-4V with intelligent fallback
"""
import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from PIL import Image
from abc import ABC, abstractmethod
from enum import Enum

# Import AI model libraries with fallbacks
try:
    import google.generativeai as genai
    from google.generativeai import GenerativeModel
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

try:
    import openai
    GPT_AVAILABLE = True
except ImportError:
    GPT_AVAILABLE = False


class AIModel(Enum):
    """Supported AI models"""
    GEMINI_FLASH = "gemini-1.5-flash"
    GEMINI_PRO = "gemini-1.5-pro"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    GPT_4V = "gpt-4-vision-preview"


class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def analyze_image(self, image_path: str, prompt: str) -> str:
        """Analyze image with given prompt"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available"""
        pass


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        super().__init__(api_key, model_name)
        if GEMINI_AVAILABLE:
            genai.configure(api_key=api_key)
            self.model = GenerativeModel(model_name)
        else:
            self.model = None
    
    def is_available(self) -> bool:
        return GEMINI_AVAILABLE and self.model is not None
    
    def analyze_image(self, image_path: str, prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError("Gemini provider not available")
        
        try:
            with Image.open(image_path) as img:
                response = self.model.generate_content([prompt, img])
                return response.text
        except Exception as e:
            self.logger.error(f"Gemini analysis failed: {e}")
            raise


class ClaudeProvider(BaseAIProvider):
    """Anthropic Claude AI provider"""
    
    def __init__(self, api_key: str, model_name: str = "claude-3-5-sonnet-20241022"):
        super().__init__(api_key, model_name)
        if CLAUDE_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = None
    
    def is_available(self) -> bool:
        return CLAUDE_AVAILABLE and self.client is not None
    
    def analyze_image(self, image_path: str, prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError("Claude provider not available")
        
        try:
            import base64
            
            # Convert image to base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Determine image format
            image_format = "jpeg"
            if image_path.lower().endswith('.png'):
                image_format = "png"
            
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": f"image/{image_format}",
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            self.logger.error(f"Claude analysis failed: {e}")
            raise


class GPTProvider(BaseAIProvider):
    """OpenAI GPT-4V provider"""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4-vision-preview"):
        super().__init__(api_key, model_name)
        if GPT_AVAILABLE:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            self.client = None
    
    def is_available(self) -> bool:
        return GPT_AVAILABLE and self.client is not None
    
    def analyze_image(self, image_path: str, prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError("GPT provider not available")
        
        try:
            import base64
            
            # Convert image to base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"GPT analysis failed: {e}")
            raise


class MultiModelAIOptimizer:
    """
    Multi-model AI optimizer with intelligent fallback and model selection
    
    Features:
    - Support for Gemini, Claude 3.5 Sonnet, and GPT-4V
    - Intelligent model selection based on availability and performance
    - Automatic fallback to alternative models on failure
    - Batch processing and caching (inherited from original optimizer)
    - Model performance tracking and optimization
    """
    
    def __init__(self, config: Dict[str, str], cache_ttl: int = 300,
                 preferred_models: List[AIModel] = None, ai_config: Dict[str, Any] = None):
        """
        Initialize multi-model AI optimizer

        Args:
            config: Dictionary with API keys for different models
                   e.g., {'gemini_api_key': 'key1', 'claude_api_key': 'key2', 'openai_api_key': 'key3'}
            cache_ttl: Cache time-to-live in seconds
            preferred_models: List of preferred models in order of preference
            ai_config: AI enhancements configuration dictionary
        """
        self.cache = {}
        self.cache_ttl = cache_ttl
        self.providers = {}
        self.model_performance = {}

        # Store AI configuration for feature toggles
        self.ai_config = ai_config or {}
        self.caching_config = self.ai_config.get("caching", {})
        self.multi_model_config = self.ai_config.get("multi_model_ai", {})
        
        # Set default preferred models if not specified
        if preferred_models is None:
            preferred_models = [AIModel.GEMINI_FLASH, AIModel.CLAUDE_SONNET, AIModel.GPT_4V]
        
        self.preferred_models = preferred_models
        
        # Initialize available providers
        self._initialize_providers(config)
        
        logging.info(f"Multi-model AI Optimizer initialized with {len(self.providers)} providers")
        logging.info(f"Available models: {list(self.providers.keys())}")
    
    def _initialize_providers(self, config: Dict[str, str]):
        """Initialize AI providers based on available API keys"""
        
        # Initialize Gemini
        if 'gemini_api_key' in config and config['gemini_api_key']:
            try:
                self.providers[AIModel.GEMINI_FLASH] = GeminiProvider(
                    config['gemini_api_key'], "gemini-1.5-flash"
                )
                self.providers[AIModel.GEMINI_PRO] = GeminiProvider(
                    config['gemini_api_key'], "gemini-1.5-pro"
                )
                logging.info("Gemini providers initialized")
            except Exception as e:
                logging.warning(f"Failed to initialize Gemini: {e}")
        
        # Initialize Claude
        if 'claude_api_key' in config and config['claude_api_key']:
            try:
                self.providers[AIModel.CLAUDE_SONNET] = ClaudeProvider(
                    config['claude_api_key']
                )
                logging.info("Claude provider initialized")
            except Exception as e:
                logging.warning(f"Failed to initialize Claude: {e}")
        
        # Initialize GPT-4V
        if 'openai_api_key' in config and config['openai_api_key']:
            try:
                self.providers[AIModel.GPT_4V] = GPTProvider(
                    config['openai_api_key']
                )
                logging.info("GPT-4V provider initialized")
            except Exception as e:
                logging.warning(f"Failed to initialize GPT-4V: {e}")
    
    def get_available_models(self) -> List[AIModel]:
        """Get list of available AI models"""
        return [model for model, provider in self.providers.items() 
                if provider.is_available()]
    
    def _select_best_model(self) -> Optional[AIModel]:
        """Select the best available model based on preferences and performance"""
        available_models = self.get_available_models()
        
        if not available_models:
            return None
        
        # First, try preferred models in order
        for model in self.preferred_models:
            if model in available_models:
                return model
        
        # If no preferred models available, use the first available
        return available_models[0]

    def _get_cache_key(self, image_path: str, prompt: str, model_name: str) -> str:
        """Generate a unique cache key for a request."""
        image_hash = self._get_image_hash(image_path)
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        return f"{model_name}_{image_hash}_{prompt_hash}"

    def _get_image_hash(self, image_path: str) -> str:
        """Generate MD5 hash for image content"""
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logging.error(f"Error generating image hash: {e}")
            return str(hash(image_path))  # Fallback to path hash

    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry or 'timestamp' not in cache_entry:
            return False

        try:
            cache_time = datetime.fromisoformat(cache_entry['timestamp'])
            return datetime.now() - cache_time < timedelta(seconds=self.cache_ttl)
        except Exception:
            return False

    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if valid"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if self._is_cache_valid(entry):
                logging.debug(f"Cache hit for key: {cache_key[:20]}...")
                return entry['raw_response'] # Return raw response
            else:
                # Remove expired entry
                del self.cache[cache_key]
                logging.debug(f"Cache expired for key: {cache_key[:20]}...")
        return None

    def _cache_result(self, cache_key: str, raw_response: str, model_used: AIModel,
                     intermediate_results: Dict[str, Any] = None) -> None:
        """Cache raw analysis response with timestamp, model info, and intermediate results"""
        cache_entry = {
            'raw_response': raw_response,
            'timestamp': datetime.now().isoformat(),
            'model_used': model_used.value
        }

        # Store intermediate results for faster reprocessing
        if intermediate_results:
            cache_entry['intermediate_results'] = intermediate_results

        self.cache[cache_key] = cache_entry
        logging.debug(f"Cached result for key: {cache_key[:20]}... using {model_used.value}")

    def _get_cached_intermediate_results(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached intermediate results if available"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if self._is_cache_valid(entry):
                return entry.get('intermediate_results')
        return None

    def _create_batch_prompt(self, zone_name: str, zone_purpose: str,
                           active_tasks: List[Dict], ignore_rules: List[str]) -> str:
        """
        Create optimized batch prompt for all 3 analysis types

        This combines completed tasks, new tasks, and cleanliness analysis
        into a single optimized prompt for better performance.
        """
        # Format active tasks for completion checking
        active_tasks_text = ""
        if active_tasks:
            active_tasks_text = "Active Tasks to Check for Completion:\n"
            for i, task in enumerate(active_tasks, 1):
                priority = task.get('priority', 'N/A')
                active_tasks_text += f"{i}. ID: {task.get('id', f'task_{i}')} - {task['description']} (Priority: {priority})\n"

        # Format ignore rules
        ignore_rules_text = ""
        if ignore_rules:
            ignore_rules_text = f"Ignore Rules (do not suggest tasks for these): {', '.join(ignore_rules)}\n"

        prompt = f"""Analyze this image of the {zone_name} and provide a comprehensive analysis.

Zone Purpose: {zone_purpose}

{active_tasks_text}

{ignore_rules_text}

Please provide a JSON response with the following structure:
{{
  "completed_tasks": {{
    "task_ids": ["task_id_1", "task_id_2"],
    "confidence_scores": {{"task_id_1": 0.95, "task_id_2": 0.87}},
    "reasoning": {{"task_id_1": "The countertop is now clean", "task_id_2": "Dishes are put away"}}
  }},
  "new_tasks": {{
    "tasks": [
      {{"description": "Wipe down surfaces", "priority": 7, "category": "cleaning"}},
      {{"description": "Organize items", "priority": 5, "category": "organization"}}
    ],
    "room_cleanliness_score": 6,
    "analysis_notes": "Room is moderately clean with some areas needing attention"
  }},
  "cleanliness_assessment": {{
    "score": 7,
    "state": "moderately_clean",
    "observations": ["Surfaces are mostly clean", "Some clutter visible"],
    "recommendations": ["Focus on organizing loose items", "Regular surface cleaning"],
    "improvement_areas": ["Kitchen counter", "Dining table"]
  }}
}}

Analysis Guidelines:
1. For completed tasks: Only mark tasks as completed if you can clearly see evidence in the image
2. For new tasks: Focus on specific, actionable items that are clearly visible and relevant to the zone purpose
3. For cleanliness: Provide an honest assessment with specific observations
4. Use confidence scores between 0.0-1.0 for completed tasks
5. Prioritize new tasks from 1-10 (10 = highest priority)

If no tasks are completed, use empty arrays. If the room is very clean, suggest minimal or no new tasks."""

        return prompt

    def analyze_batch_optimized(self, image_path: str, zone_name: str, zone_purpose: str,
                              active_tasks: List[Dict], ignore_rules: List[str]) -> Tuple[Dict, bool]:
        """
        Perform optimized batch analysis with multi-model support, fallback, and enhanced caching

        Returns:
            Tuple of (analysis_result, was_cached)
        """
        # Create batch prompt
        prompt = self._create_batch_prompt(zone_name, zone_purpose, active_tasks, ignore_rules)

        # Generate cache key for intermediate results
        image_hash = self._get_image_hash(image_path)
        context_data = {
            'zone_name': zone_name,
            'zone_purpose': zone_purpose,
            'active_tasks': [t.get('id', '') + t.get('description', '') for t in active_tasks],
            'ignore_rules': ignore_rules
        }
        context_hash = hashlib.md5(json.dumps(context_data, sort_keys=True).encode()).hexdigest()
        intermediate_cache_key = f"intermediate_{image_hash}_{context_hash}"

        # Check for cached intermediate results first (if enabled)
        if self.caching_config.get("intermediate_caching", True):
            cached_intermediate = self._get_cached_intermediate_results(intermediate_cache_key)
            if cached_intermediate:
                logging.debug("Using cached intermediate results for faster processing")
                # Reconstruct result from cached intermediate data
                result = self._reconstruct_from_intermediate(cached_intermediate, zone_name)
                return result, True

        # Try analysis with fallback
        result, was_cached = self._analyze_with_fallback(image_path, prompt)

        if result:
            # Extract and cache intermediate results for future use
            intermediate_results = self._extract_intermediate_results(result, image_path, zone_name)

            # Add metadata
            result['analysis_metadata'] = {
                'timestamp': datetime.now().isoformat(),
                'zone_name': zone_name,
                'analysis_type': 'multi_model_batch_optimized',
                'cache_hit': was_cached,
                'intermediate_cached': False,
                'available_models': [model.value for model in self.get_available_models()]
            }

            # Cache intermediate results separately for faster reprocessing (if enabled)
            if intermediate_results and not was_cached and self.caching_config.get("intermediate_caching", True):
                self._cache_intermediate_results(intermediate_cache_key, intermediate_results)

            logging.info(f"Multi-model batch analysis completed for zone {zone_name}")
            return result, was_cached
        else:
            return self._create_fallback_result(), False

    def _extract_intermediate_results(self, result: Dict, image_path: str, zone_name: str) -> Dict[str, Any]:
        """Extract intermediate results for caching"""
        try:
            intermediate = {
                'raw_response': result.get('raw_response', ''),
                'parsed_objects': result.get('detected_objects', []),
                'cleanliness_indicators': result.get('cleanliness_assessment', {}).get('observations', []),
                'task_categories': self._categorize_tasks(result.get('new_tasks', [])),
                'image_hash': self._get_image_hash(image_path),
                'zone_context': {
                    'zone_name': zone_name,
                    'analysis_timestamp': datetime.now().isoformat()
                }
            }
            return intermediate
        except Exception as e:
            logging.error(f"Error extracting intermediate results: {e}")
            return {}

    def _categorize_tasks(self, tasks: List[Dict]) -> Dict[str, List[str]]:
        """Categorize tasks by type for better caching"""
        categories = {
            'cleaning': [],
            'organizing': [],
            'maintenance': [],
            'other': []
        }

        for task in tasks:
            description = task.get('description', '').lower()
            if any(word in description for word in ['clean', 'wipe', 'sanitize', 'wash']):
                categories['cleaning'].append(task.get('description', ''))
            elif any(word in description for word in ['organize', 'arrange', 'sort', 'put away']):
                categories['organizing'].append(task.get('description', ''))
            elif any(word in description for word in ['fix', 'repair', 'replace', 'maintain']):
                categories['maintenance'].append(task.get('description', ''))
            else:
                categories['other'].append(task.get('description', ''))

        return categories

    def _cache_intermediate_results(self, cache_key: str, intermediate_results: Dict[str, Any]) -> None:
        """Cache intermediate results separately"""
        self.cache[cache_key] = {
            'intermediate_results': intermediate_results,
            'timestamp': datetime.now().isoformat(),
            'type': 'intermediate'
        }
        logging.debug(f"Cached intermediate results for key: {cache_key[:20]}...")

    def _reconstruct_from_intermediate(self, intermediate: Dict[str, Any], zone_name: str) -> Dict[str, Any]:
        """Reconstruct analysis result from cached intermediate data"""
        try:
            # Reconstruct the full result from intermediate data
            task_categories = intermediate.get('task_categories', {})
            all_tasks = []

            for category, tasks in task_categories.items():
                for task_desc in tasks:
                    all_tasks.append({
                        'description': task_desc,
                        'priority': 5,  # Default priority
                        'category': category,
                        'generated_at': datetime.now().isoformat()
                    })

            result = {
                'completed_tasks': [],  # Cannot determine from intermediate cache
                'new_tasks': all_tasks,
                'cleanliness_assessment': {
                    'score': 5,  # Default score, could be enhanced
                    'observations': intermediate.get('cleanliness_indicators', []),
                    'state': 'reconstructed_from_cache'
                },
                'raw_response': intermediate.get('raw_response', ''),
                'detected_objects': intermediate.get('parsed_objects', []),
                'analysis_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'zone_name': zone_name,
                    'analysis_type': 'reconstructed_from_intermediate',
                    'cache_hit': True,
                    'intermediate_cached': True,
                    'original_timestamp': intermediate.get('zone_context', {}).get('analysis_timestamp')
                }
            }

            return result

        except Exception as e:
            logging.error(f"Error reconstructing from intermediate cache: {e}")
            return {}

    def _analyze_with_fallback(self, image_path: str, prompt: str) -> Tuple[Optional[Dict], bool]:
        """
        Analyze image with automatic fallback to alternative models
        Returns a tuple of (result, was_cached)
        """
        available_models = self.get_available_models()

        if not available_models:
            logging.error("No AI models available for analysis")
            return None, False

        # Try models in order of preference
        for model in self.preferred_models:
            if model not in available_models:
                continue

            # Generate cache key
            cache_key = self._get_cache_key(image_path, prompt, model.value)

            # Check cache first
            cached_response = self._get_cached_result(cache_key)
            if cached_response:
                parsed_result = self._parse_response(cached_response, model)
                if parsed_result:
                    return parsed_result, True

            # Get retry configuration
            max_retries = self.multi_model_config.get("max_retries", 3)
            timeout_seconds = self.multi_model_config.get("timeout_seconds", 30)

            for retry_attempt in range(max_retries):
                try:
                    start_time = datetime.now()
                    provider = self.providers[model]

                    logging.info(f"Attempting analysis with {model.value} (attempt {retry_attempt + 1}/{max_retries})")
                    response_text = provider.analyze_image(image_path, prompt)

                    # Track performance
                    analysis_time = (datetime.now() - start_time).total_seconds()
                    self._track_model_performance(model, analysis_time, True)

                    # Cache the raw response
                    self._cache_result(cache_key, response_text, model)

                    # Parse JSON response
                    result = self._parse_response(response_text, model)
                    if result:
                        result['analysis_metadata'] = result.get('analysis_metadata', {})
                        result['analysis_metadata']['model_used'] = model.value
                        result['analysis_metadata']['analysis_time_seconds'] = analysis_time
                        result['analysis_metadata']['retry_attempt'] = retry_attempt + 1
                        return result, False

                except Exception as e:
                    # Track failure
                    analysis_time = (datetime.now() - start_time).total_seconds()
                    self._track_model_performance(model, analysis_time, False)

                    if retry_attempt < max_retries - 1:
                        logging.warning(f"Analysis failed with {model.value} (attempt {retry_attempt + 1}/{max_retries}): {e}. Retrying...")
                        continue
                    else:
                        logging.warning(f"Analysis failed with {model.value} after {max_retries} attempts: {e}")
                        break

        logging.error("All available models failed for analysis")
        return None, False

    def _parse_response(self, response_text: str, model: AIModel) -> Optional[Dict]:
        """Parse AI response text into structured result"""
        try:
            # Clean up response text (remove markdown formatting if present)
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()

            result = json.loads(response_text)
            return result

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse {model.value} response JSON: {e}")
            logging.error(f"Raw response: {response_text[:200]}...")
            return None

    def _track_model_performance(self, model: AIModel, analysis_time: float, success: bool):
        """Track model performance for optimization"""
        if model not in self.model_performance:
            self.model_performance[model] = {
                'total_calls': 0,
                'successful_calls': 0,
                'total_time': 0.0,
                'average_time': 0.0,
                'success_rate': 0.0
            }

        stats = self.model_performance[model]
        stats['total_calls'] += 1
        stats['total_time'] += analysis_time

        if success:
            stats['successful_calls'] += 1

        stats['average_time'] = stats['total_time'] / stats['total_calls']
        stats['success_rate'] = stats['successful_calls'] / stats['total_calls']

    def _create_fallback_result(self) -> Dict:
        """Create fallback result structure when analysis fails"""
        return {
            'completed_tasks': {
                'task_ids': [],
                'confidence_scores': {},
                'reasoning': {}
            },
            'new_tasks': {
                'tasks': [],
                'room_cleanliness_score': 5,
                'analysis_notes': 'Multi-model analysis failed, using fallback result'
            },
            'cleanliness_assessment': {
                'score': 5,
                'state': 'unknown',
                'observations': ['Multi-model analysis failed'],
                'recommendations': ['Retry analysis', 'Check AI model availability'],
                'improvement_areas': []
            },
            'analysis_metadata': {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'fallback',
                'cache_hit': False,
                'model_used': 'fallback'
            }
        }

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        total_entries = len(self.cache)
        valid_entries = sum(1 for entry in self.cache.values() if self._is_cache_valid(entry))

        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': total_entries - valid_entries,
            'cache_ttl_seconds': self.cache_ttl
        }

    def get_model_performance_stats(self) -> Dict:
        """Get performance statistics for all models"""
        return {
            model.value: stats.copy()
            for model, stats in self.model_performance.items()
        }

    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        return {
            'available_models': [model.value for model in self.get_available_models()],
            'preferred_models': [model.value for model in self.preferred_models],
            'cache_stats': self.get_cache_stats(),
            'model_performance': self.get_model_performance_stats(),
            'providers_initialized': len(self.providers),
            'system_health': 'healthy' if self.get_available_models() else 'degraded'
        }

    def clear_cache(self) -> None:
        """Clear all cached results"""
        self.cache.clear()
        logging.info("Multi-model AI analysis cache cleared")

    def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries and return count removed"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if not self._is_cache_valid(entry)
        ]

        for key in expired_keys:
            del self.cache[key]

        logging.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        return len(expired_keys)

    def set_preferred_models(self, models: List[AIModel]) -> None:
        """Update preferred model order"""
        available_models = self.get_available_models()
        valid_models = [model for model in models if model in available_models]

        if not valid_models:
            logging.warning("No valid models in preferred list, keeping current preferences")
            return

        self.preferred_models = valid_models
        logging.info(f"Updated preferred models: {[m.value for m in valid_models]}")

    def optimize_model_selection(self) -> None:
        """Optimize model selection based on performance statistics"""
        if not self.model_performance:
            return

        # Sort models by success rate and average time
        available_models = self.get_available_models()
        model_scores = []

        for model in available_models:
            if model in self.model_performance:
                stats = self.model_performance[model]
                # Score based on success rate (70%) and speed (30%)
                score = (stats['success_rate'] * 0.7) + ((1.0 / max(stats['average_time'], 0.1)) * 0.3)
                model_scores.append((model, score))

        if model_scores:
            # Sort by score (highest first)
            model_scores.sort(key=lambda x: x[1], reverse=True)
            optimized_order = [model for model, score in model_scores]

            logging.info(f"Optimized model order based on performance: {[m.value for m in optimized_order]}")
            self.preferred_models = optimized_order
