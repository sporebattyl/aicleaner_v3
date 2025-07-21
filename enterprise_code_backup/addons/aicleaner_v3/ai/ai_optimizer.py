"""
AI Analysis Performance Optimizer for AICleaner
Implements batch processing and intelligent caching for Gemini API calls
"""
import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image
import google.generativeai as genai
from google.generativeai import GenerativeModel


class AIAnalysisOptimizer:
    """
    Optimized AI analysis with batch processing and intelligent caching
    
    Features:
    - Batch analysis: Combines 3 separate API calls into 1 optimized call
    - Response caching: Caches results based on image hash + prompt hash  
    - Smart model selection: Uses gemini-1.5-flash for better performance
    - Cache TTL: Configurable cache time-to-live
    """
    
    def __init__(self, api_key: str, cache_ttl: int = 300, model_name: str = 'gemini-1.5-flash'):
        """
        Initialize the AI optimizer

        Args:
            api_key: Gemini API key
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
            model_name: Gemini model to use (default: gemini-1.5-flash)
        """
        self.cache = {}
        self.cache_ttl = cache_ttl

        # Configure Gemini with user-selected model
        genai.configure(api_key=api_key)
        self.model = GenerativeModel(model_name)

        logging.info(f"AI Optimizer initialized with {model_name} model and {cache_ttl}s cache TTL")
    
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
                return entry['result']
            else:
                # Remove expired entry
                del self.cache[cache_key]
                logging.debug(f"Cache expired for key: {cache_key[:20]}...")
        return None
    
    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache analysis result with timestamp"""
        self.cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        logging.debug(f"Cached result for key: {cache_key[:20]}...")
    
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
        Perform optimized batch analysis combining all 3 analysis types
        
        Returns:
            Tuple of (analysis_result, was_cached)
        """
        try:
            # Generate cache key based on image and context
            image_hash = self._get_image_hash(image_path)
            context_data = {
                'zone_name': zone_name,
                'zone_purpose': zone_purpose,
                'active_tasks': [t.get('id', '') + t.get('description', '') for t in active_tasks],
                'ignore_rules': ignore_rules
            }
            context_hash = hashlib.md5(json.dumps(context_data, sort_keys=True).encode()).hexdigest()
            cache_key = f"batch_{image_hash}_{context_hash}"
            
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result, True
            
            # Create batch prompt
            prompt = self._create_batch_prompt(zone_name, zone_purpose, active_tasks, ignore_rules)
            
            # Perform batch analysis
            with Image.open(image_path) as img:
                response = self.model.generate_content([prompt, img])
                result_text = response.text
                
                # Parse JSON response
                try:
                    # Clean up response text (remove markdown formatting if present)
                    if result_text.startswith('```json'):
                        result_text = result_text.replace('```json', '').replace('```', '').strip()
                    elif result_text.startswith('```'):
                        result_text = result_text.replace('```', '').strip()
                    
                    result = json.loads(result_text)
                    
                    # Add metadata
                    result['analysis_metadata'] = {
                        'timestamp': datetime.now().isoformat(),
                        'zone_name': zone_name,
                        'model_used': 'gemini-1.5-flash',
                        'analysis_type': 'batch_optimized',
                        'cache_hit': False
                    }
                    
                    # Cache the result
                    self._cache_result(cache_key, result)
                    
                    logging.info(f"Batch analysis completed for zone {zone_name}")
                    return result, False
                    
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse batch analysis JSON: {e}")
                    logging.error(f"Raw response: {result_text[:200]}...")
                    return self._create_fallback_result(), False
                    
        except Exception as e:
            logging.error(f"Error in batch analysis: {e}")
            return self._create_fallback_result(), False
    
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
                'analysis_notes': 'Analysis failed, using fallback result'
            },
            'cleanliness_assessment': {
                'score': 5,
                'state': 'unknown',
                'observations': ['Analysis failed'],
                'recommendations': ['Retry analysis'],
                'improvement_areas': []
            },
            'analysis_metadata': {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'fallback',
                'cache_hit': False
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
    
    def clear_cache(self) -> None:
        """Clear all cached results"""
        self.cache.clear()
        logging.info("AI analysis cache cleared")
    
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
