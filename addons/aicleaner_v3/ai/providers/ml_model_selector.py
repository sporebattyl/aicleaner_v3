"""
ML-Based Model Selection for AI Providers
Phase 5A: ML-Based Model Selection Implementation

Intelligent model selection using Multi-Armed Bandit (UCB1) algorithm optimized for
single-user Home Assistant addon with limited data and lightweight computation.
"""

import json
import logging
import math
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re

from utils.unified_logger import get_logger
from monitoring.system_monitor import get_system_monitor

logger = get_logger(__name__)

# Configuration constants
UCB1_CONFIDENCE_LEVEL = 2.0  # Higher values favor exploration
WARMUP_REQUESTS_PER_CATEGORY = 5  # Number of requests to cycle through models during warmup
MIN_PULLS_FOR_RECOMMENDATION = 3  # Minimum pulls before using UCB1 scores
PERFORMANCE_FILE_PATH = "/data/model_performance.json"  # Persistent storage
FEATURE_EXTRACTION_TIMEOUT = 0.1  # Max time for feature extraction in seconds

class RequestCategory(Enum):
    """Request categories for model selection"""
    GENERIC = "generic"
    CODE = "code"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    QUESTION_ANSWER = "question_answer"

class ComplexityLevel(Enum):
    """Request complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

@dataclass
class ModelMetrics:
    """Performance metrics for a model in a specific category"""
    pulls: int = 0
    successes: int = 0
    total_response_time: float = 0.0
    total_cost: float = 0.0
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        return self.successes / max(1, self.pulls)
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        return self.total_response_time / max(1, self.successes)
    
    @property
    def avg_cost(self) -> float:
        """Calculate average cost"""
        return self.total_cost / max(1, self.pulls)
    
    def update(self, success: bool, response_time: float, cost: float):
        """Update metrics with new data"""
        self.pulls += 1
        if success:
            self.successes += 1
            self.total_response_time += response_time
        self.total_cost += cost
        self.last_used = datetime.now().isoformat()

@dataclass
class RequestFeatures:
    """Extracted features from a request"""
    category: RequestCategory
    complexity: ComplexityLevel
    prompt_length: int
    has_code: bool
    has_image: bool
    language_detected: Optional[str] = None
    
    def get_key(self) -> str:
        """Get unique key for this feature combination"""
        return f"{self.category.value}_{self.complexity.value}"

class FeatureExtractor:
    """Extract features from AI requests for model selection"""
    
    def __init__(self):
        self.code_patterns = [
            r'```[\w]*\n',  # Code blocks
            r'def\s+\w+\s*\(',  # Function definitions
            r'class\s+\w+\s*[\(:]',  # Class definitions
            r'import\s+\w+',  # Import statements
            r'from\s+\w+\s+import',  # From imports
            r'<\w+[^>]*>',  # HTML tags
            r'SELECT\s+.*\s+FROM\s+',  # SQL queries
            r'function\s+\w+\s*\(',  # JavaScript functions
        ]
        
        self.analysis_keywords = [
            'analyze', 'analysis', 'examine', 'review', 'evaluate',
            'assess', 'investigate', 'study', 'research', 'compare'
        ]
        
        self.creative_keywords = [
            'create', 'generate', 'write', 'compose', 'design',
            'invent', 'imagine', 'story', 'poem', 'creative'
        ]
        
        self.summarization_keywords = [
            'summarize', 'summary', 'brief', 'tl;dr', 'overview',
            'recap', 'outline', 'digest', 'abstract'
        ]
        
        self.translation_keywords = [
            'translate', 'translation', 'convert', 'language',
            'français', 'español', 'deutsch', 'italiano', 'português',
            'русский', '中文', '日本語', '한국어'
        ]
    
    def extract_features(self, prompt: str, image_path: Optional[str] = None, 
                        image_data: Optional[bytes] = None) -> RequestFeatures:
        """Extract features from request for model selection"""
        try:
            start_time = time.time()
            
            # Basic features
            prompt_length = len(prompt.split())
            has_code = self._detect_code(prompt)
            has_image = bool(image_path or image_data)
            
            # Category detection
            category = self._detect_category(prompt)
            
            # Complexity assessment
            complexity = self._assess_complexity(prompt, prompt_length, has_code, has_image)
            
            # Language detection (simple heuristic)
            language_detected = self._detect_language(prompt)
            
            # Ensure we don't exceed timeout
            if time.time() - start_time > FEATURE_EXTRACTION_TIMEOUT:
                logger.warning("Feature extraction timeout, using defaults")
                return RequestFeatures(
                    category=RequestCategory.GENERIC,
                    complexity=ComplexityLevel.MEDIUM,
                    prompt_length=prompt_length,
                    has_code=has_code,
                    has_image=has_image
                )
            
            return RequestFeatures(
                category=category,
                complexity=complexity,
                prompt_length=prompt_length,
                has_code=has_code,
                has_image=has_image,
                language_detected=language_detected
            )
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return RequestFeatures(
                category=RequestCategory.GENERIC,
                complexity=ComplexityLevel.MEDIUM,
                prompt_length=len(prompt.split()),
                has_code=False,
                has_image=bool(image_path or image_data)
            )
    
    def _detect_code(self, prompt: str) -> bool:
        """Detect if prompt contains code"""
        for pattern in self.code_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                return True
        return False
    
    def _detect_category(self, prompt: str) -> RequestCategory:
        """Detect request category based on keywords"""
        prompt_lower = prompt.lower()
        
        # Check for code
        if self._detect_code(prompt):
            return RequestCategory.CODE
        
        # Check for summarization
        if any(keyword in prompt_lower for keyword in self.summarization_keywords):
            return RequestCategory.SUMMARIZATION
        
        # Check for translation
        if any(keyword in prompt_lower for keyword in self.translation_keywords):
            return RequestCategory.TRANSLATION
        
        # Check for analysis
        if any(keyword in prompt_lower for keyword in self.analysis_keywords):
            return RequestCategory.ANALYSIS
        
        # Check for creative
        if any(keyword in prompt_lower for keyword in self.creative_keywords):
            return RequestCategory.CREATIVE
        
        # Check for question/answer patterns
        if prompt.strip().endswith('?') or prompt_lower.startswith(('what', 'how', 'why', 'when', 'where', 'who')):
            return RequestCategory.QUESTION_ANSWER
        
        return RequestCategory.GENERIC
    
    def _assess_complexity(self, prompt: str, prompt_length: int, has_code: bool, has_image: bool) -> ComplexityLevel:
        """Assess request complexity"""
        complexity_score = 0
        
        # Length-based complexity
        if prompt_length > 200:
            complexity_score += 2
        elif prompt_length > 50:
            complexity_score += 1
        
        # Code adds complexity
        if has_code:
            complexity_score += 2
        
        # Images add complexity
        if has_image:
            complexity_score += 1
        
        # Multi-step instructions
        if len(re.findall(r'\d+\.\s', prompt)) > 3:
            complexity_score += 1
        
        # Technical terms
        technical_terms = ['algorithm', 'optimization', 'implementation', 'architecture', 'performance']
        if any(term in prompt.lower() for term in technical_terms):
            complexity_score += 1
        
        if complexity_score >= 4:
            return ComplexityLevel.COMPLEX
        elif complexity_score >= 2:
            return ComplexityLevel.MEDIUM
        else:
            return ComplexityLevel.SIMPLE
    
    def _detect_language(self, prompt: str) -> Optional[str]:
        """Simple language detection based on common words"""
        language_indicators = {
            'spanish': ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'por'],
            'french': ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir', 'que', 'pour', 'dans'],
            'german': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich', 'des', 'auf'],
            'italian': ['il', 'di', 'che', 'e', 'la', 'per', 'in', 'un', 'è', 'con', 'da', 'su', 'sono'],
            'portuguese': ['de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não']
        }
        
        words = prompt.lower().split()[:20]  # Check first 20 words
        
        for language, indicators in language_indicators.items():
            matches = sum(1 for word in words if word in indicators)
            if matches >= 3:  # Threshold for detection
                return language
        
        return None

class ModelPerformanceTracker:
    """Track and persist model performance data"""
    
    def __init__(self, provider_name: str, data_path: str = PERFORMANCE_FILE_PATH):
        self.provider_name = provider_name
        self.data_path = data_path
        self.metrics: Dict[str, Dict[str, ModelMetrics]] = {}
        self.system_monitor = get_system_monitor()
        
        # Load existing data
        self._load_performance_data()
    
    def _load_performance_data(self):
        """Load performance data from file"""
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                
                provider_data = data.get(self.provider_name, {})
                
                # Convert loaded data to ModelMetrics objects
                for model_name, categories in provider_data.items():
                    if model_name not in self.metrics:
                        self.metrics[model_name] = {}
                    
                    for category, metrics_data in categories.items():
                        self.metrics[model_name][category] = ModelMetrics(
                            pulls=metrics_data.get('pulls', 0),
                            successes=metrics_data.get('successes', 0),
                            total_response_time=metrics_data.get('total_response_time', 0.0),
                            total_cost=metrics_data.get('total_cost', 0.0),
                            last_used=metrics_data.get('last_used', datetime.now().isoformat())
                        )
                
                logger.info(f"Loaded performance data for {self.provider_name}: {len(self.metrics)} models")
            else:
                logger.info(f"No existing performance data found for {self.provider_name}")
                
        except Exception as e:
            logger.error(f"Failed to load performance data: {e}")
            self.metrics = {}
    
    def _save_performance_data(self):
        """Save performance data to file"""
        try:
            # Load existing data
            data = {}
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
            
            # Convert ModelMetrics to dict for serialization
            provider_data = {}
            for model_name, categories in self.metrics.items():
                provider_data[model_name] = {}
                for category, metrics in categories.items():
                    provider_data[model_name][category] = {
                        'pulls': metrics.pulls,
                        'successes': metrics.successes,
                        'total_response_time': metrics.total_response_time,
                        'total_cost': metrics.total_cost,
                        'last_used': metrics.last_used
                    }
            
            data[self.provider_name] = provider_data
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            
            # Save to file
            with open(self.data_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved performance data for {self.provider_name}")
            
        except Exception as e:
            logger.error(f"Failed to save performance data: {e}")
    
    def get_metrics(self, model_name: str, category: str) -> ModelMetrics:
        """Get metrics for a model in a specific category"""
        if model_name not in self.metrics:
            self.metrics[model_name] = {}
        
        if category not in self.metrics[model_name]:
            self.metrics[model_name][category] = ModelMetrics()
        
        return self.metrics[model_name][category]
    
    def update_metrics(self, model_name: str, category: str, success: bool, 
                      response_time: float, cost: float):
        """Update metrics for a model"""
        metrics = self.get_metrics(model_name, category)
        metrics.update(success, response_time, cost)
        
        # Save periodically (every 5 updates)
        if metrics.pulls % 5 == 0:
            self._save_performance_data()
    
    def get_all_metrics(self) -> Dict[str, Dict[str, ModelMetrics]]:
        """Get all metrics for this provider"""
        return self.metrics
    
    def cleanup_old_data(self, days_old: int = 30):
        """Remove old performance data"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for model_name in list(self.metrics.keys()):
            for category in list(self.metrics[model_name].keys()):
                metrics = self.metrics[model_name][category]
                last_used = datetime.fromisoformat(metrics.last_used)
                
                if last_used < cutoff_date:
                    del self.metrics[model_name][category]
                    logger.info(f"Removed old metrics for {model_name}/{category}")
        
        self._save_performance_data()

class UCB1Algorithm:
    """Upper Confidence Bound algorithm for model selection"""
    
    def __init__(self, confidence_level: float = UCB1_CONFIDENCE_LEVEL):
        self.confidence_level = confidence_level
    
    def calculate_ucb1_score(self, metrics: ModelMetrics, total_pulls: int) -> float:
        """Calculate UCB1 score for a model"""
        if metrics.pulls == 0:
            return float('inf')  # Ensure untested models are tried first
        
        if total_pulls <= 0:
            return metrics.success_rate
        
        # UCB1 formula: average_reward + confidence_bound
        # Reward is a combination of success rate and inverse of response time
        avg_reward = self._calculate_reward(metrics)
        confidence_bound = self.confidence_level * math.sqrt(
            math.log(total_pulls) / metrics.pulls
        )
        
        return avg_reward + confidence_bound
    
    def _calculate_reward(self, metrics: ModelMetrics) -> float:
        """Calculate reward for a model based on multiple factors"""
        if metrics.successes == 0:
            return 0.0
        
        # Base reward is success rate
        success_reward = metrics.success_rate
        
        # Penalize slow response times (normalize assuming 10s max)
        time_penalty = min(metrics.avg_response_time / 10.0, 1.0)
        time_reward = max(0.0, 1.0 - time_penalty)
        
        # Penalize high costs (normalize assuming $0.10 max per request)
        cost_penalty = min(metrics.avg_cost / 0.10, 1.0)
        cost_reward = max(0.0, 1.0 - cost_penalty)
        
        # Combined reward with weights
        combined_reward = (
            0.5 * success_reward +    # 50% success rate
            0.3 * time_reward +       # 30% response time
            0.2 * cost_reward         # 20% cost
        )
        
        return combined_reward

class MLModelSelector:
    """ML-based model selector using Multi-Armed Bandit approach"""
    
    def __init__(self, provider_name: str, models: List[str], default_model: str,
                 data_path: str = PERFORMANCE_FILE_PATH):
        self.provider_name = provider_name
        self.models = models
        self.default_model = default_model
        
        # Initialize components
        self.feature_extractor = FeatureExtractor()
        self.performance_tracker = ModelPerformanceTracker(provider_name, data_path)
        self.ucb1_algorithm = UCB1Algorithm()
        
        # Warmup tracking
        self.warmup_counters: Dict[str, int] = {}
        self.warmup_model_cycle: Dict[str, int] = {}
        
        logger.info(f"ML Model Selector initialized for {provider_name} with models: {models}")
    
    def recommend_model(self, prompt: str, image_path: Optional[str] = None,
                       image_data: Optional[bytes] = None) -> str:
        """Recommend the best model for the given request"""
        try:
            # Extract features
            features = self.feature_extractor.extract_features(prompt, image_path, image_data)
            category_key = features.get_key()
            
            # Check if we're in warmup phase
            if self._is_warmup_phase(category_key):
                return self._warmup_selection(category_key)
            
            # Use UCB1 algorithm for model selection
            return self._ucb1_selection(category_key)
            
        except Exception as e:
            logger.error(f"Model recommendation failed: {e}")
            return self.default_model
    
    def update_performance(self, model_name: str, prompt: str, success: bool,
                          response_time: float, cost: float,
                          image_path: Optional[str] = None, image_data: Optional[bytes] = None):
        """Update performance metrics after request completion"""
        try:
            # Extract features to get category
            features = self.feature_extractor.extract_features(prompt, image_path, image_data)
            category_key = features.get_key()
            
            # Update metrics
            self.performance_tracker.update_metrics(
                model_name, category_key, success, response_time, cost
            )
            
            logger.debug(f"Updated performance for {model_name}/{category_key}: "
                        f"success={success}, time={response_time:.2f}s, cost=${cost:.4f}")
            
        except Exception as e:
            logger.error(f"Performance update failed: {e}")
    
    def _is_warmup_phase(self, category_key: str) -> bool:
        """Check if we're still in warmup phase for this category"""
        if category_key not in self.warmup_counters:
            self.warmup_counters[category_key] = 0
            self.warmup_model_cycle[category_key] = 0
        
        # Calculate total pulls for this category across all models
        total_pulls = sum(
            self.performance_tracker.get_metrics(model, category_key).pulls
            for model in self.models
        )
        
        # Warmup if we haven't reached minimum pulls per model
        min_pulls_needed = len(self.models) * WARMUP_REQUESTS_PER_CATEGORY
        return total_pulls < min_pulls_needed
    
    def _warmup_selection(self, category_key: str) -> str:
        """Select model during warmup phase (round-robin)"""
        cycle_position = self.warmup_model_cycle[category_key]
        model_index = cycle_position % len(self.models)
        selected_model = self.models[model_index]
        
        self.warmup_counters[category_key] += 1
        self.warmup_model_cycle[category_key] = (cycle_position + 1) % len(self.models)
        
        logger.debug(f"Warmup selection for {category_key}: {selected_model} (cycle: {cycle_position})")
        return selected_model
    
    def _ucb1_selection(self, category_key: str) -> str:
        """Select model using UCB1 algorithm"""
        # Calculate total pulls for this category
        total_pulls = sum(
            self.performance_tracker.get_metrics(model, category_key).pulls
            for model in self.models
        )
        
        if total_pulls == 0:
            return self.default_model
        
        # Calculate UCB1 scores for each model
        ucb1_scores = {}
        for model in self.models:
            metrics = self.performance_tracker.get_metrics(model, category_key)
            ucb1_scores[model] = self.ucb1_algorithm.calculate_ucb1_score(metrics, total_pulls)
        
        # Select model with highest UCB1 score
        selected_model = max(ucb1_scores, key=ucb1_scores.get)
        
        logger.debug(f"UCB1 selection for {category_key}: {selected_model} "
                    f"(score: {ucb1_scores[selected_model]:.3f})")
        
        return selected_model
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics for all models"""
        stats = {
            "provider": self.provider_name,
            "models": self.models,
            "default_model": self.default_model,
            "warmup_status": {},
            "model_performance": {}
        }
        
        # Warmup status
        for category_key, counter in self.warmup_counters.items():
            total_pulls = sum(
                self.performance_tracker.get_metrics(model, category_key).pulls
                for model in self.models
            )
            min_pulls_needed = len(self.models) * WARMUP_REQUESTS_PER_CATEGORY
            stats["warmup_status"][category_key] = {
                "is_warmup": total_pulls < min_pulls_needed,
                "total_pulls": total_pulls,
                "needed_pulls": min_pulls_needed
            }
        
        # Model performance
        for model in self.models:
            model_data = {}
            for category_key in self.warmup_counters.keys():
                metrics = self.performance_tracker.get_metrics(model, category_key)
                model_data[category_key] = {
                    "pulls": metrics.pulls,
                    "success_rate": round(metrics.success_rate, 3),
                    "avg_response_time": round(metrics.avg_response_time, 3),
                    "avg_cost": round(metrics.avg_cost, 4)
                }
            stats["model_performance"][model] = model_data
        
        return stats
    
    def cleanup_old_data(self, days_old: int = 30):
        """Clean up old performance data"""
        self.performance_tracker.cleanup_old_data(days_old)