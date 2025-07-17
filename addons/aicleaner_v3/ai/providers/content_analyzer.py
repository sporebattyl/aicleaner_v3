"""
Intelligent Content Analyzer
Cloud Integration Optimization - Phase 2

Advanced content analysis system for granular content type detection,
preprocessing integration, and intelligent routing optimization.
"""

import asyncio
import base64
import hashlib
import json
import logging
import mimetypes
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import time

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

from .enhanced_config import ContentType, ProcessingPriority


@dataclass
class ContentAnalysisResult:
    """Result of content analysis"""
    content_type: ContentType
    primary_type: str                          # "text", "image", "audio", etc.
    secondary_types: List[str] = field(default_factory=list)
    confidence: float = 1.0                    # 0-1 confidence in classification
    size_estimate: int = 0                     # Size in tokens/pixels/bytes
    complexity_score: float = 0.5              # 0-1 complexity assessment
    privacy_sensitive: bool = False            # Contains sensitive information
    processing_hints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrivacyAnalysis:
    """Privacy analysis results"""
    contains_pii: bool = False                 # Personal Identifiable Information
    contains_sensitive_data: bool = False      # Sensitive business data
    privacy_risk_score: float = 0.0           # 0-1 risk score
    detected_entities: List[str] = field(default_factory=list)
    redaction_suggestions: List[str] = field(default_factory=list)


class ContentComplexity(Enum):
    """Content complexity levels for processing optimization"""
    SIMPLE = "simple"           # Basic text, simple images
    MODERATE = "moderate"       # Structured content, code
    COMPLEX = "complex"         # Multimodal, large documents
    ENTERPRISE = "enterprise"   # Complex business documents


class ContentAnalyzer:
    """
    Intelligent Content Analyzer for AI request optimization.
    
    Features:
    - Granular content type detection
    - Privacy-sensitive content identification
    - Processing complexity assessment
    - Size and cost estimation
    - Provider capability matching
    - Privacy Pipeline integration hints
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Content Analyzer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("content_analyzer")
        
        # Content detection patterns
        self.code_patterns = self._initialize_code_patterns()
        self.pii_patterns = self._initialize_pii_patterns()
        self.technical_patterns = self._initialize_technical_patterns()
        
        # Cache for analysis results
        self.analysis_cache: Dict[str, ContentAnalysisResult] = {}
        self.cache_ttl = self.config.get("cache_ttl", 3600)  # 1 hour
        
        # Privacy Pipeline integration
        self.privacy_pipeline_enabled = self.config.get("privacy_pipeline_enabled", True)
        
        self.logger.info("Content Analyzer initialized")
    
    def _initialize_code_patterns(self) -> Dict[str, List[str]]:
        """Initialize code detection patterns"""
        return {
            "python": [
                r"def\s+\w+\s*\(",
                r"import\s+\w+",
                r"from\s+\w+\s+import",
                r"class\s+\w+\s*:",
                r"if\s+__name__\s*==\s*['\"]__main__['\"]",
                r"print\s*\(",
                r"return\s+\w+"
            ],
            "javascript": [
                r"function\s+\w+\s*\(",
                r"const\s+\w+\s*=",
                r"let\s+\w+\s*=",
                r"var\s+\w+\s*=",
                r"=>\s*{",
                r"console\.log\s*\(",
                r"document\.\w+"
            ],
            "sql": [
                r"SELECT\s+.*FROM",
                r"INSERT\s+INTO",
                r"UPDATE\s+.*SET",
                r"DELETE\s+FROM",
                r"CREATE\s+TABLE",
                r"ALTER\s+TABLE",
                r"JOIN\s+\w+"
            ],
            "html_css": [
                r"<html>",
                r"<div\s+.*>",
                r"class\s*=\s*['\"]",
                r"{\s*\w+\s*:",
                r"@media\s+",
                r"#\w+\s*{"
            ],
            "yaml_json": [
                r"^\s*-\s+\w+:",
                r"^\s*\w+:\s*$",
                r'"\w+"\s*:\s*[{\[]',
                r"version:\s*['\"]?\d"
            ]
        }
    
    def _initialize_pii_patterns(self) -> List[Tuple[str, str]]:
        """Initialize PII detection patterns"""
        return [
            (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),                    # Social Security Number
            (r"\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b", "Credit Card"), # Credit Card
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email"),  # Email
            (r"\b\d{3}-\d{3}-\d{4}\b", "Phone"),                  # Phone Number
            (r"\b\d{5}(-\d{4})?\b", "ZIP Code"),                  # ZIP Code
            (r"\b[A-Z]{2}\d{6,8}\b", "Passport"),                 # Passport-like
            (r"\bAPI[_\s]?KEY[_\s]?[:=]\s*[A-Za-z0-9+/=]{20,}\b", "API Key"),  # API Keys
        ]
    
    def _initialize_technical_patterns(self) -> Dict[str, List[str]]:
        """Initialize technical content patterns"""
        return {
            "automation": [
                r"trigger\s+when",
                r"if\s+.*then",
                r"automation\s+rule",
                r"device\s+state",
                r"sensor\s+reading"
            ],
            "configuration": [
                r"config\s*:",
                r"settings\s*=",
                r"parameter\s*:",
                r"option\s*:",
                r"\.yaml$",
                r"\.json$",
                r"\.toml$"
            ],
            "security": [
                r"password",
                r"secret",
                r"token",
                r"credential",
                r"certificate",
                r"encrypt",
                r"decrypt",
                r"authentication"
            ],
            "home_assistant": [
                r"homeassistant:",
                r"entity_id:",
                r"service:",
                r"automation:",
                r"sensor:",
                r"binary_sensor:",
                r"switch:",
                r"light:"
            ]
        }
    
    async def analyze_content(
        self,
        content: str = "",
        image_path: Optional[str] = None,
        image_data: Optional[bytes] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ContentAnalysisResult:
        """
        Perform comprehensive content analysis.
        
        Args:
            content: Text content to analyze
            image_path: Path to image file
            image_data: Raw image data
            context: Additional context information
            
        Returns:
            Content analysis result
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(content, image_path, image_data, context)
        
        # Check cache
        if cache_key in self.analysis_cache:
            cached_result = self.analysis_cache[cache_key]
            self.logger.debug(f"Content analysis cache hit: {cache_key[:16]}...")
            return cached_result
        
        try:
            # Initialize result
            result = ContentAnalysisResult()
            
            # Analyze different content types
            if image_path or image_data:
                result = await self._analyze_image_content(result, image_path, image_data)
            
            if content:
                result = await self._analyze_text_content(result, content)
            
            # Determine primary content type
            result.content_type = self._determine_primary_content_type(result)
            
            # Calculate complexity score
            result.complexity_score = self._calculate_complexity_score(result, content, image_path, image_data)
            
            # Estimate processing size
            result.size_estimate = self._estimate_processing_size(content, image_path, image_data)
            
            # Privacy analysis
            if self.privacy_pipeline_enabled:
                privacy_analysis = await self._analyze_privacy_content(content)
                result.privacy_sensitive = privacy_analysis.contains_pii or privacy_analysis.contains_sensitive_data
                result.metadata["privacy_analysis"] = privacy_analysis.__dict__
            
            # Add processing hints
            result.processing_hints = self._generate_processing_hints(result, context)
            
            # Add metadata
            result.metadata.update({
                "analysis_time": time.time() - start_time,
                "analyzer_version": "1.0",
                "timestamp": time.time()
            })
            
            # Cache result
            self.analysis_cache[cache_key] = result
            
            # Log analysis
            self.logger.info(
                json.dumps({
                    "event": "content_analysis_complete",
                    "content_type": result.content_type.value,
                    "confidence": result.confidence,
                    "size_estimate": result.size_estimate,
                    "complexity_score": result.complexity_score,
                    "privacy_sensitive": result.privacy_sensitive,
                    "analysis_time": result.metadata["analysis_time"]
                })
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Content analysis failed: {e}")
            
            # Return default result
            return ContentAnalysisResult(
                content_type=ContentType.TEXT,
                primary_type="text",
                confidence=0.5,
                metadata={"error": str(e)}
            )
    
    async def _analyze_image_content(
        self,
        result: ContentAnalysisResult,
        image_path: Optional[str],
        image_data: Optional[bytes]
    ) -> ContentAnalysisResult:
        """Analyze image content"""
        try:
            if image_path:
                # File-based image analysis
                file_path = Path(image_path)
                if not file_path.exists():
                    raise FileNotFoundError(f"Image file not found: {image_path}")
                
                # Get file info
                file_size = file_path.stat().st_size
                mime_type, _ = mimetypes.guess_type(image_path)
                
                result.primary_type = "image"
                result.secondary_types.append("file")
                result.metadata.update({
                    "file_path": str(image_path),
                    "file_size": file_size,
                    "mime_type": mime_type
                })
                
                # PIL analysis if available
                if PIL_AVAILABLE:
                    try:
                        with Image.open(image_path) as img:
                            result.metadata.update({
                                "image_format": img.format,
                                "image_mode": img.mode,
                                "image_size": img.size,
                                "image_dimensions": f"{img.width}x{img.height}"
                            })
                            
                            # Estimate complexity based on image properties
                            total_pixels = img.width * img.height
                            if total_pixels > 2000000:  # >2MP
                                result.complexity_score += 0.3
                            elif total_pixels > 500000:  # >0.5MP
                                result.complexity_score += 0.2
                            else:
                                result.complexity_score += 0.1
                    except Exception as e:
                        self.logger.warning(f"PIL image analysis failed: {e}")
            
            elif image_data:
                # Raw image data analysis
                result.primary_type = "image"
                result.secondary_types.append("raw_data")
                result.metadata.update({
                    "data_size": len(image_data),
                    "data_type": "bytes"
                })
                
                # Basic complexity estimation based on size
                if len(image_data) > 1000000:  # >1MB
                    result.complexity_score += 0.3
                elif len(image_data) > 100000:  # >100KB
                    result.complexity_score += 0.2
                else:
                    result.complexity_score += 0.1
            
            result.confidence = 0.95  # High confidence for image detection
            
        except Exception as e:
            self.logger.error(f"Image analysis failed: {e}")
            result.metadata["image_analysis_error"] = str(e)
        
        return result
    
    async def _analyze_text_content(self, result: ContentAnalysisResult, content: str) -> ContentAnalysisResult:
        """Analyze text content"""
        try:
            content_lower = content.lower()
            
            # Basic text analysis
            word_count = len(content.split())
            line_count = len(content.splitlines())
            char_count = len(content)
            
            result.metadata.update({
                "word_count": word_count,
                "line_count": line_count,
                "char_count": char_count
            })
            
            # Initialize primary type
            if not result.primary_type:
                result.primary_type = "text"
            
            # Detect code content
            code_confidence = self._detect_code_content(content)
            if code_confidence > 0.7:
                result.secondary_types.append("code")
                result.complexity_score += 0.3
            
            # Detect structured data
            structured_confidence = self._detect_structured_data(content)
            if structured_confidence > 0.7:
                result.secondary_types.append("structured_data")
                result.complexity_score += 0.2
            
            # Detect technical content
            technical_categories = self._detect_technical_content(content)
            if technical_categories:
                result.secondary_types.extend(technical_categories)
                result.complexity_score += 0.1 * len(technical_categories)
            
            # Detect document-like content
            if word_count > 500 and line_count > 10:
                result.secondary_types.append("document")
                result.complexity_score += 0.2
            
            # Update confidence based on detection certainty
            detection_count = len(result.secondary_types)
            if detection_count > 0:
                result.confidence = min(0.95, 0.7 + (detection_count * 0.1))
            else:
                result.confidence = 0.8  # Default text confidence
            
        except Exception as e:
            self.logger.error(f"Text analysis failed: {e}")
            result.metadata["text_analysis_error"] = str(e)
        
        return result
    
    def _detect_code_content(self, content: str) -> float:
        """Detect if content contains code and return confidence score"""
        code_indicators = 0
        total_patterns = 0
        
        for language, patterns in self.code_patterns.items():
            for pattern in patterns:
                total_patterns += 1
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    code_indicators += 1
        
        return code_indicators / max(1, total_patterns) if total_patterns > 0 else 0.0
    
    def _detect_structured_data(self, content: str) -> float:
        """Detect structured data (JSON, YAML, XML) and return confidence"""
        structured_indicators = 0
        
        # JSON indicators
        if re.search(r'{\s*"[^"]+"\s*:', content):
            structured_indicators += 2
        if re.search(r'\[\s*{', content):
            structured_indicators += 1
        
        # YAML indicators
        if re.search(r'^\s*\w+:\s*\w+', content, re.MULTILINE):
            structured_indicators += 1
        if re.search(r'^\s*-\s+\w+', content, re.MULTILINE):
            structured_indicators += 1
        
        # XML indicators
        if re.search(r'<\w+[^>]*>', content):
            structured_indicators += 1
        
        return min(1.0, structured_indicators / 5.0)
    
    def _detect_technical_content(self, content: str) -> List[str]:
        """Detect technical content categories"""
        detected_categories = []
        
        for category, patterns in self.technical_patterns.items():
            matches = sum(1 for pattern in patterns if re.search(pattern, content, re.IGNORECASE))
            if matches >= 2:  # Require multiple matches for confidence
                detected_categories.append(category)
        
        return detected_categories
    
    def _determine_primary_content_type(self, result: ContentAnalysisResult) -> ContentType:
        """Determine primary content type based on analysis"""
        if result.primary_type == "image":
            if "text" in result.secondary_types:
                return ContentType.MULTIMODAL
            else:
                return ContentType.IMAGE
        
        if "code" in result.secondary_types:
            return ContentType.CODE
        
        if "structured_data" in result.secondary_types:
            return ContentType.STRUCTURED_DATA
        
        if "document" in result.secondary_types:
            return ContentType.DOCUMENT
        
        # Default to text
        return ContentType.TEXT
    
    def _calculate_complexity_score(
        self,
        result: ContentAnalysisResult,
        content: str,
        image_path: Optional[str],
        image_data: Optional[bytes]
    ) -> float:
        """Calculate overall complexity score (0-1)"""
        complexity = result.complexity_score
        
        # Add complexity based on content length
        if content:
            word_count = len(content.split())
            if word_count > 1000:
                complexity += 0.3
            elif word_count > 500:
                complexity += 0.2
            elif word_count > 100:
                complexity += 0.1
        
        # Add complexity for multimodal content
        if result.content_type == ContentType.MULTIMODAL:
            complexity += 0.4
        
        # Add complexity for multiple secondary types
        complexity += len(result.secondary_types) * 0.05
        
        return min(1.0, complexity)
    
    def _estimate_processing_size(
        self,
        content: str,
        image_path: Optional[str],
        image_data: Optional[bytes]
    ) -> int:
        """Estimate processing size in tokens/equivalent units"""
        size = 0
        
        # Text size estimation (4 chars per token average)
        if content:
            size += len(content) // 4
        
        # Image size estimation (vision models have different token costs)
        if image_path or image_data:
            if image_path and Path(image_path).exists():
                file_size = Path(image_path).stat().st_size
                # Rough estimation: 1MB image ≈ 1000 tokens for vision models
                size += file_size // 1000
            elif image_data:
                size += len(image_data) // 1000
        
        return max(1, size)  # Minimum 1 token
    
    async def _analyze_privacy_content(self, content: str) -> PrivacyAnalysis:
        """Analyze content for privacy-sensitive information"""
        analysis = PrivacyAnalysis()
        
        if not content:
            return analysis
        
        # PII detection
        for pattern, entity_type in self.pii_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                analysis.contains_pii = True
                analysis.detected_entities.append(entity_type)
                analysis.redaction_suggestions.append(f"Redact {entity_type}: {len(matches)} instances")
        
        # Sensitive data patterns
        sensitive_patterns = [
            r"password\s*[:=]\s*\S+",
            r"secret\s*[:=]\s*\S+",
            r"token\s*[:=]\s*\S+",
            r"private\s+key",
            r"confidential",
            r"proprietary"
        ]
        
        sensitive_matches = 0
        for pattern in sensitive_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                sensitive_matches += 1
        
        if sensitive_matches > 0:
            analysis.contains_sensitive_data = True
        
        # Calculate privacy risk score
        pii_weight = 0.7 if analysis.contains_pii else 0.0
        sensitive_weight = 0.5 if analysis.contains_sensitive_data else 0.0
        entity_weight = len(analysis.detected_entities) * 0.1
        
        analysis.privacy_risk_score = min(1.0, pii_weight + sensitive_weight + entity_weight)
        
        return analysis
    
    def _generate_processing_hints(
        self,
        result: ContentAnalysisResult,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate processing hints for provider optimization"""
        hints = {}
        
        # Content type specific hints
        if result.content_type == ContentType.CODE:
            hints["prefer_code_specialized"] = True
            hints["require_syntax_awareness"] = True
            
        elif result.content_type == ContentType.IMAGE:
            hints["require_vision_capability"] = True
            hints["prefer_vision_specialized"] = True
            
        elif result.content_type == ContentType.MULTIMODAL:
            hints["require_multimodal"] = True
            hints["high_complexity"] = True
            
        # Complexity hints
        if result.complexity_score > 0.8:
            hints["high_complexity"] = True
            hints["prefer_premium_models"] = True
        elif result.complexity_score < 0.3:
            hints["low_complexity"] = True
            hints["prefer_fast_models"] = True
        
        # Privacy hints
        if result.privacy_sensitive:
            hints["privacy_sensitive"] = True
            hints["require_privacy_pipeline"] = True
            hints["prefer_local_processing"] = True
        
        # Size hints
        if result.size_estimate > 2000:
            hints["large_content"] = True
            hints["prefer_high_token_limit"] = True
        
        # Context hints
        if context:
            priority = context.get("priority", ProcessingPriority.NORMAL)
            if priority == ProcessingPriority.CRITICAL:
                hints["critical_priority"] = True
                hints["prefer_reliable_providers"] = True
            elif priority == ProcessingPriority.BATCH:
                hints["batch_processing"] = True
                hints["prefer_cost_efficient"] = True
        
        return hints
    
    def _generate_cache_key(
        self,
        content: str,
        image_path: Optional[str],
        image_data: Optional[bytes],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for analysis result"""
        key_components = []
        
        if content:
            content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
            key_components.append(f"text:{content_hash}")
        
        if image_path:
            path_hash = hashlib.md5(str(image_path).encode()).hexdigest()[:16]
            key_components.append(f"path:{path_hash}")
        
        if image_data:
            data_hash = hashlib.md5(image_data).hexdigest()[:16]
            key_components.append(f"data:{data_hash}")
        
        if context:
            context_str = json.dumps(context, sort_keys=True)
            context_hash = hashlib.md5(context_str.encode()).hexdigest()[:16]
            key_components.append(f"ctx:{context_hash}")
        
        return "|".join(key_components)
    
    def clear_cache(self):
        """Clear analysis cache"""
        self.analysis_cache.clear()
        self.logger.info("Content analysis cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.analysis_cache),
            "cache_ttl": self.cache_ttl,
            "cache_keys": list(self.analysis_cache.keys())[:10]  # First 10 keys for debugging
        }
    
    def suggest_provider_requirements(self, result: ContentAnalysisResult) -> Dict[str, Any]:
        """Suggest provider requirements based on analysis"""
        requirements = {
            "required_capabilities": [],
            "preferred_capabilities": [],
            "performance_requirements": {},
            "cost_considerations": {}
        }
        
        # Required capabilities
        if result.content_type == ContentType.IMAGE:
            requirements["required_capabilities"].append("vision")
        elif result.content_type == ContentType.MULTIMODAL:
            requirements["required_capabilities"].extend(["vision", "multimodal"])
        
        # Performance requirements
        if result.complexity_score > 0.8:
            requirements["performance_requirements"]["min_quality_score"] = 0.9
            requirements["performance_requirements"]["prefer_premium"] = True
        
        if result.size_estimate > 2000:
            requirements["performance_requirements"]["min_token_limit"] = result.size_estimate * 1.2
        
        # Cost considerations
        if result.privacy_sensitive:
            requirements["cost_considerations"]["privacy_premium_acceptable"] = True
        
        if result.complexity_score < 0.3:
            requirements["cost_considerations"]["prefer_cost_efficient"] = True
        
        return requirements