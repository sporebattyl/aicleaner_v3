"""
Advanced Scene Understanding for AICleaner
Provides enhanced context awareness with room type detection, object recognition, and seasonal adjustments
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import re

from ai.object_database_cache import ObjectDatabaseCache
from ai.object_database import SafetyLevel, HygieneImpact, CleaningFrequency


class RoomType(Enum):
    """Types of rooms with specific cleaning contexts"""
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    BEDROOM = "bedroom"
    LIVING_ROOM = "living_room"
    DINING_ROOM = "dining_room"
    OFFICE = "office"
    LAUNDRY_ROOM = "laundry_room"
    GARAGE = "garage"
    BASEMENT = "basement"
    ATTIC = "attic"
    HALLWAY = "hallway"
    CLOSET = "closet"
    PANTRY = "pantry"
    UNKNOWN = "unknown"


class Season(Enum):
    """Seasons for seasonal adjustments"""
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"


class TimeOfDay(Enum):
    """Time periods for context-aware analysis"""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


@dataclass
class SceneContext:
    """Represents the context of a scene for enhanced analysis"""
    room_type: RoomType
    detected_objects: List[str]
    lighting_condition: str
    time_of_day: TimeOfDay
    season: Season
    weather_context: Optional[str] = None
    occupancy_level: str = "unknown"  # "empty", "low", "medium", "high"
    cleanliness_indicators: List[str] = None
    
    def __post_init__(self):
        if self.cleanliness_indicators is None:
            self.cleanliness_indicators = []


@dataclass
class ContextualInsight:
    """Represents a contextual insight about the scene"""
    insight_type: str
    description: str
    confidence: float
    room_specific: bool
    seasonal_relevance: bool
    time_sensitive: bool
    supporting_evidence: List[str]


class AdvancedSceneUnderstanding:
    """
    Advanced scene understanding system for AICleaner
    
    Features:
    - Room type detection and classification
    - Object recognition and context analysis
    - Seasonal cleaning adjustments
    - Time-of-day context awareness
    - Occupancy and usage pattern detection
    - Context-aware task prioritization
    """
    
    def __init__(self, data_path: str = "/data/scene_context"):
        """
        Initialize advanced scene understanding system
        
        Args:
            data_path: Path to store scene context data
        """
        self.data_path = data_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Load room type patterns and object databases
        self.room_patterns = self._load_room_patterns()
        self.object_database = self._load_object_database()
        self.seasonal_adjustments = self._load_seasonal_adjustments()

        # Initialize object database cache for enhanced task generation
        self.object_db_cache = ObjectDatabaseCache(max_size=500, ttl_seconds=1800)  # 30 minutes TTL

        self.logger.info("Advanced Scene Understanding system initialized with object database cache")
    
    def _load_room_patterns(self) -> Dict[RoomType, Dict[str, List[str]]]:
        """Load room type detection patterns"""
        return {
            RoomType.KITCHEN: {
                'objects': ['stove', 'oven', 'refrigerator', 'sink', 'dishwasher', 'microwave', 
                           'counter', 'cabinet', 'cutting board', 'pot', 'pan', 'dishes'],
                'keywords': ['kitchen', 'cook', 'food', 'meal', 'dining', 'eat'],
                'surfaces': ['countertop', 'stovetop', 'backsplash', 'island']
            },
            RoomType.BATHROOM: {
                'objects': ['toilet', 'sink', 'shower', 'bathtub', 'mirror', 'towel', 
                           'toothbrush', 'soap', 'shampoo', 'toilet paper'],
                'keywords': ['bathroom', 'bath', 'shower', 'toilet', 'wash'],
                'surfaces': ['floor', 'walls', 'mirror', 'fixtures']
            },
            RoomType.BEDROOM: {
                'objects': ['bed', 'pillow', 'blanket', 'dresser', 'nightstand', 'lamp', 
                           'closet', 'clothes', 'mattress'],
                'keywords': ['bedroom', 'sleep', 'bed', 'rest', 'night'],
                'surfaces': ['floor', 'bed', 'furniture']
            },
            RoomType.LIVING_ROOM: {
                'objects': ['sofa', 'couch', 'tv', 'coffee table', 'chair', 'cushion', 
                           'remote', 'book', 'magazine', 'lamp'],
                'keywords': ['living', 'family', 'lounge', 'relax', 'tv'],
                'surfaces': ['floor', 'furniture', 'tables']
            },
            RoomType.OFFICE: {
                'objects': ['desk', 'computer', 'chair', 'monitor', 'keyboard', 'mouse', 
                           'papers', 'books', 'printer', 'phone'],
                'keywords': ['office', 'work', 'study', 'desk', 'computer'],
                'surfaces': ['desk', 'floor', 'shelves']
            },
            RoomType.LAUNDRY_ROOM: {
                'objects': ['washer', 'dryer', 'laundry basket', 'detergent', 'clothes', 
                           'iron', 'ironing board'],
                'keywords': ['laundry', 'wash', 'dry', 'clean clothes'],
                'surfaces': ['floor', 'machines', 'folding area']
            }
        }
    
    def _load_object_database(self) -> Dict[str, Dict[str, Any]]:
        """Load object database with cleaning context"""
        return {
            'kitchen_appliances': {
                'objects': ['stove', 'oven', 'refrigerator', 'dishwasher', 'microwave'],
                'cleaning_frequency': 'weekly',
                'priority_level': 'high',
                'seasonal_factors': ['holiday_cooking', 'summer_usage']
            },
            'bathroom_fixtures': {
                'objects': ['toilet', 'sink', 'shower', 'bathtub'],
                'cleaning_frequency': 'daily',
                'priority_level': 'high',
                'seasonal_factors': ['humidity', 'mold_risk']
            },
            'furniture': {
                'objects': ['sofa', 'chair', 'table', 'desk', 'bed'],
                'cleaning_frequency': 'weekly',
                'priority_level': 'medium',
                'seasonal_factors': ['dust_accumulation', 'pet_hair']
            },
            'electronics': {
                'objects': ['tv', 'computer', 'monitor', 'phone'],
                'cleaning_frequency': 'weekly',
                'priority_level': 'low',
                'seasonal_factors': ['dust', 'static']
            }
        }
    
    def _load_seasonal_adjustments(self) -> Dict[Season, Dict[str, Any]]:
        """Load seasonal cleaning adjustments"""
        return {
            Season.SPRING: {
                'focus_areas': ['deep_cleaning', 'decluttering', 'window_cleaning'],
                'priority_boost': ['organization', 'outdoor_prep'],
                'frequency_multiplier': 1.3,
                'special_tasks': ['spring_cleaning', 'allergen_removal', 'fresh_air']
            },
            Season.SUMMER: {
                'focus_areas': ['cooling_systems', 'outdoor_spaces', 'humidity_control'],
                'priority_boost': ['air_conditioning', 'ventilation'],
                'frequency_multiplier': 1.1,
                'special_tasks': ['ac_maintenance', 'outdoor_cleaning', 'pest_control']
            },
            Season.FALL: {
                'focus_areas': ['heating_prep', 'leaf_management', 'weatherproofing'],
                'priority_boost': ['heating_systems', 'insulation'],
                'frequency_multiplier': 1.2,
                'special_tasks': ['heating_check', 'gutter_cleaning', 'winterization']
            },
            Season.WINTER: {
                'focus_areas': ['indoor_air_quality', 'heating_efficiency', 'moisture_control'],
                'priority_boost': ['heating', 'humidity_control'],
                'frequency_multiplier': 0.9,
                'special_tasks': ['humidifier_maintenance', 'draft_sealing', 'indoor_plants']
            }
        }
    
    def detect_room_type(self, zone_name: str, zone_purpose: str, detected_objects: List[str]) -> RoomType:
        """
        Detect room type based on zone information and detected objects
        
        Args:
            zone_name: Name of the zone
            zone_purpose: Purpose description of the zone
            detected_objects: List of objects detected in the scene
            
        Returns:
            Detected room type
        """
        # Normalize inputs
        zone_name_lower = zone_name.lower()
        zone_purpose_lower = zone_purpose.lower()
        detected_objects_lower = [obj.lower() for obj in detected_objects]
        
        # Score each room type
        room_scores = {}
        
        for room_type, patterns in self.room_patterns.items():
            score = 0
            
            # Check zone name and purpose for keywords
            for keyword in patterns['keywords']:
                if keyword in zone_name_lower:
                    score += 3
                if keyword in zone_purpose_lower:
                    score += 2
            
            # Check detected objects
            for obj in patterns['objects']:
                if obj in detected_objects_lower:
                    score += 1
            
            room_scores[room_type] = score
        
        # Return the highest scoring room type
        if room_scores:
            best_room = max(room_scores, key=room_scores.get)
            if room_scores[best_room] > 0:
                return best_room
        
        return RoomType.UNKNOWN
    
    def get_current_season(self) -> Season:
        """Get current season based on date"""
        now = datetime.now()
        month = now.month
        
        if month in [3, 4, 5]:
            return Season.SPRING
        elif month in [6, 7, 8]:
            return Season.SUMMER
        elif month in [9, 10, 11]:
            return Season.FALL
        else:
            return Season.WINTER
    
    def get_time_of_day(self) -> TimeOfDay:
        """Get current time of day context"""
        now = datetime.now()
        hour = now.hour
        
        if 5 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 22:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.NIGHT
    
    def extract_objects_from_analysis(self, ai_response: str) -> List[str]:
        """
        Extract object mentions from AI analysis response
        
        Args:
            ai_response: AI analysis response text
            
        Returns:
            List of detected objects
        """
        objects = set()
        
        # Common object patterns to look for
        object_patterns = [
            r'\b(counter|countertop|surface|table|desk|floor|wall|ceiling)\b',
            r'\b(stove|oven|refrigerator|sink|dishwasher|microwave|cabinet)\b',
            r'\b(toilet|shower|bathtub|mirror|towel)\b',
            r'\b(bed|pillow|blanket|dresser|nightstand|closet)\b',
            r'\b(sofa|couch|chair|tv|coffee table|lamp)\b',
            r'\b(computer|monitor|keyboard|mouse|printer|phone)\b',
            r'\b(washer|dryer|laundry|clothes|iron)\b'
        ]
        
        for pattern in object_patterns:
            matches = re.findall(pattern, ai_response.lower())
            objects.update(matches)
        
        return list(objects)
    
    def analyze_scene_context(self, zone_name: str, zone_purpose: str,
                            ai_response: str, enable_seasonal_adjustments: bool = True,
                            enable_time_context: bool = True) -> SceneContext:
        """
        Analyze scene context from zone information and AI response

        Args:
            zone_name: Name of the zone
            zone_purpose: Purpose of the zone
            ai_response: AI analysis response
            enable_seasonal_adjustments: Whether to include seasonal context
            enable_time_context: Whether to include time-of-day context

        Returns:
            Scene context analysis
        """
        # Extract objects from AI response
        detected_objects = self.extract_objects_from_analysis(ai_response)
        
        # Detect room type
        room_type = self.detect_room_type(zone_name, zone_purpose, detected_objects)
        
        # Get temporal context based on configuration
        current_season = self.get_current_season() if enable_seasonal_adjustments else Season.SPRING
        current_time = self.get_time_of_day() if enable_time_context else TimeOfDay.AFTERNOON
        
        # Analyze lighting and cleanliness indicators
        lighting_condition = self._analyze_lighting(ai_response)
        cleanliness_indicators = self._extract_cleanliness_indicators(ai_response)
        
        return SceneContext(
            room_type=room_type,
            detected_objects=detected_objects,
            lighting_condition=lighting_condition,
            time_of_day=current_time,
            season=current_season,
            cleanliness_indicators=cleanliness_indicators
        )

    def get_detailed_scene_context(self, zone_name: str, zone_purpose: str, ai_response: str,
                                 max_objects: int = 10, confidence_threshold: float = 0.7,
                                 enable_seasonal_adjustments: bool = True,
                                 enable_time_context: bool = True) -> Dict[str, Any]:
        """
        Get detailed scene context for AI Coordinator integration.
        This method provides the interface expected by the AI Coordinator.

        Args:
            zone_name: Name of the zone
            zone_purpose: Purpose of the zone
            ai_response: Raw AI analysis response
            max_objects: Maximum number of objects to detect
            confidence_threshold: Confidence threshold for object detection
            enable_seasonal_adjustments: Whether to apply seasonal adjustments
            enable_time_context: Whether to include time-of-day context

        Returns:
            Dictionary with detailed scene context and generated tasks
        """
        try:
            # Get the scene context using existing method with configuration options
            scene_context = self.analyze_scene_context(
                zone_name, zone_purpose, ai_response,
                enable_seasonal_adjustments=enable_seasonal_adjustments,
                enable_time_context=enable_time_context
            )

            # Extract objects with locations from AI response using configuration limits
            objects_with_locations = self._extract_objects_with_locations(
                ai_response, max_objects, confidence_threshold
            )

            # Generate specific, actionable tasks based on detected objects and context
            generated_tasks = self._generate_granular_tasks(
                objects_with_locations, scene_context, ai_response,
                enable_seasonal_adjustments=enable_seasonal_adjustments
            )

            # Return structured data for AI Coordinator
            return {
                "scene_context": {
                    "room_type": scene_context.room_type.value,
                    "detected_objects": scene_context.detected_objects,
                    "lighting_condition": scene_context.lighting_condition,
                    "time_of_day": scene_context.time_of_day.value,
                    "season": scene_context.season.value,
                    "cleanliness_indicators": scene_context.cleanliness_indicators,
                    "occupancy_level": scene_context.occupancy_level
                },
                "objects": objects_with_locations,
                "generated_tasks": generated_tasks,
                "contextual_insights": [
                    insight.__dict__ if hasattr(insight, '__dict__') else insight
                    for insight in self.generate_contextual_insights(scene_context, {"ai_response": ai_response})
                ]
            }

        except Exception as e:
            self.logger.error(f"Error in get_detailed_scene_context: {e}")
            return {
                "scene_context": {},
                "objects": [],
                "generated_tasks": [],
                "contextual_insights": []
            }

    def _extract_objects_with_locations(self, ai_response: str, max_objects: int, confidence_threshold: float) -> List[Dict[str, Any]]:
        """
        Extract objects with their locations and counts from AI response.

        Args:
            ai_response: Raw AI analysis response

        Returns:
            List of objects with location and count information
        """
        objects_with_locations = []

        try:
            # Common patterns for object-location detection
            location_patterns = [
                r'(\d+)\s+([a-zA-Z\s]+?)\s+(?:on|in|near|under|beside|next to|by)\s+(?:the\s+)?([a-zA-Z\s]+)',
                r'([a-zA-Z\s]+?)\s+(?:on|in|near|under|beside|next to|by)\s+(?:the\s+)?([a-zA-Z\s]+)',
                r'(?:there (?:is|are))\s+(\d+)?\s*([a-zA-Z\s]+?)\s+(?:on|in|near|under|beside|next to|by)\s+(?:the\s+)?([a-zA-Z\s]+)',
            ]

            response_lower = ai_response.lower()

            for pattern in location_patterns:
                matches = re.findall(pattern, response_lower)
                for match in matches:
                    if len(match) == 3:
                        count_str, object_name, location = match
                        try:
                            count = int(count_str) if count_str.isdigit() else 1
                        except:
                            count = 1
                    else:
                        object_name, location = match
                        count = 1

                    # Clean up object name and location
                    object_name = object_name.strip()
                    location = location.strip()

                    if object_name and location and len(object_name) > 1 and len(location) > 1:
                        objects_with_locations.append({
                            "name": object_name,
                            "location": location,
                            "count": count,
                            "confidence": self._calculate_object_confidence(object_name, location, ai_response)
                        })

            # Filter by confidence threshold
            confident_objects = [obj for obj in objects_with_locations if obj["confidence"] >= confidence_threshold]

            # Remove duplicates while preserving order
            seen = set()
            unique_objects = []
            for obj in confident_objects:
                obj_key = (obj["name"], obj["location"])
                if obj_key not in seen:
                    seen.add(obj_key)
                    unique_objects.append(obj)

            return unique_objects[:max_objects]

        except Exception as e:
            self.logger.error(f"Error extracting objects with locations: {e}")
            return []

    def _calculate_object_confidence(self, object_name: str, location: str, ai_response: str) -> float:
        """
        Calculate confidence score for detected object-location pairs.

        Args:
            object_name: Name of the detected object
            location: Location where object was detected
            ai_response: Full AI response for context

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence

        # Boost confidence for common household objects
        common_objects = ['book', 'cup', 'plate', 'towel', 'shoe', 'clothes', 'paper', 'bottle']
        if any(obj in object_name.lower() for obj in common_objects):
            confidence += 0.2

        # Boost confidence for common locations
        common_locations = ['floor', 'table', 'counter', 'bed', 'chair', 'shelf', 'sink']
        if any(loc in location.lower() for loc in common_locations):
            confidence += 0.2

        # Boost confidence if object and location appear multiple times in response
        object_mentions = ai_response.lower().count(object_name.lower())
        location_mentions = ai_response.lower().count(location.lower())
        if object_mentions > 1:
            confidence += 0.1
        if location_mentions > 1:
            confidence += 0.1

        return min(confidence, 1.0)  # Cap at 1.0

    def _generate_granular_tasks(self, objects_with_locations: List[Dict],
                                scene_context: SceneContext, ai_response: str,
                                enable_seasonal_adjustments: bool = True) -> List[Dict]:
        """
        Generate specific, actionable tasks based on detected objects and context.
        Enhanced with object database integration and hybrid prioritization.

        Args:
            objects_with_locations: List of objects with location information
            scene_context: Scene context analysis
            ai_response: Raw AI response for additional context
            enable_seasonal_adjustments: Whether to apply seasonal adjustments

        Returns:
            List of task dictionaries with priority, urgency, and safety information
        """
        generated_tasks = []

        try:
            # Generate tasks based on objects with locations using object database
            for obj in objects_with_locations:
                object_name = obj["name"]
                location = obj["location"]
                count = obj["count"]
                confidence = obj.get("confidence", 0.7)

                # Get object information from database
                object_info = self.object_db_cache.get_object_info(object_name)

                # Generate enhanced task with object database integration
                task = self._create_enhanced_task(
                    object_name, location, count, confidence,
                    object_info, scene_context
                )

                if task:
                    generated_tasks.append(task)

            # Add context-based tasks from cleanliness indicators
            context_tasks = self._generate_context_based_tasks(scene_context, ai_response)
            generated_tasks.extend(context_tasks)

            # Add seasonal tasks if relevant and enabled
            if enable_seasonal_adjustments:
                seasonal_tasks = self._generate_seasonal_tasks(scene_context, ai_response)
                generated_tasks.extend(seasonal_tasks)

            # Apply hybrid prioritization (Safety/Hygiene → Aesthetics)
            prioritized_tasks = self._apply_hybrid_prioritization(generated_tasks)

            # Return top 8 tasks to avoid overwhelming
            return prioritized_tasks[:8]

        except Exception as e:
            self.logger.error(f"Error generating granular tasks: {e}")
            return []

    def _create_enhanced_task(self, object_name: str, location: str, count: int,
                            confidence: float, object_info: Optional[Dict],
                            scene_context: SceneContext) -> Optional[Dict]:
        """
        Create an enhanced task with object database information and hybrid prioritization

        Args:
            object_name: Name of the object
            location: Location where object was found
            count: Number of objects
            confidence: Detection confidence
            object_info: Object information from database
            scene_context: Scene context

        Returns:
            Enhanced task dictionary or None if task cannot be created
        """
        try:
            # Generate base task description
            if count > 1:
                base_description = f"the {count} {object_name}s from the {location}"
            else:
                base_description = f"the {object_name} from the {location}"

            # Get room-specific handling if available
            room_specific_action = "Pick up"
            if object_info and "room_specific_handling" in object_info:
                room_handling = object_info["room_specific_handling"]
                room_key = scene_context.room_type.value

                if room_key in room_handling:
                    # Extract action from room-specific handling
                    handling_text = room_handling[room_key]
                    if "clean and put away" in handling_text.lower():
                        room_specific_action = "Clean and put away"
                    elif "organize" in handling_text.lower():
                        room_specific_action = "Organize"
                    elif "hang" in handling_text.lower():
                        room_specific_action = "Hang"
                    elif "remove" in handling_text.lower():
                        room_specific_action = "Remove"
                    elif "store" in handling_text.lower():
                        room_specific_action = "Store"
                    elif "replace" in handling_text.lower():
                        room_specific_action = "Replace"

            task_description = f"{room_specific_action} {base_description}"

            # Calculate hybrid priority (Safety/Hygiene → Aesthetics)
            priority = self._calculate_hybrid_priority(object_info, scene_context, object_name)

            # Calculate urgency based on cleaning frequency
            urgency = self._calculate_urgency_from_frequency(object_info, scene_context)

            # Create enhanced task
            task = {
                "description": task_description,
                "priority": priority,
                "urgency": urgency,
                "object_type": object_name,
                "location": location,
                "count": count,
                "confidence": confidence,
                "estimated_time": object_info.get("typical_cleanup_time", 5) if object_info else 5,
                "safety_level": object_info.get("safety_level", SafetyLevel.LOW).value if object_info else "low",
                "hygiene_impact": object_info.get("hygiene_impact", HygieneImpact.LOW).value if object_info else "low",
                "cleaning_frequency": object_info.get("cleaning_frequency", CleaningFrequency.WEEKLY).value if object_info else "weekly"
            }

            return task

        except Exception as e:
            self.logger.error(f"Error creating enhanced task for {object_name}: {e}")
            return None

    def _calculate_hybrid_priority(self, object_info: Optional[Dict],
                                 scene_context: SceneContext, object_name: str) -> int:
        """
        Calculate priority using Gemini's hybrid approach: Safety/Hygiene → Aesthetics

        Args:
            object_info: Object information from database
            scene_context: Scene context
            object_name: Name of the object

        Returns:
            Priority score (1-10, higher is more urgent)
        """
        if not object_info:
            return 3  # Default priority for unknown objects

        base_priority = object_info.get("priority_level", 5)

        # Safety boost (highest priority)
        safety_level = object_info.get("safety_level", SafetyLevel.LOW)
        if safety_level == SafetyLevel.CRITICAL:
            base_priority += 4
        elif safety_level == SafetyLevel.HIGH:
            base_priority += 3
        elif safety_level == SafetyLevel.MEDIUM:
            base_priority += 1

        # Hygiene boost (second priority)
        hygiene_impact = object_info.get("hygiene_impact", HygieneImpact.LOW)
        if hygiene_impact == HygieneImpact.CRITICAL:
            base_priority += 3
        elif hygiene_impact == HygieneImpact.HIGH:
            base_priority += 2
        elif hygiene_impact == HygieneImpact.MEDIUM:
            base_priority += 1

        # Room-specific boosts
        if scene_context.room_type == RoomType.KITCHEN:
            if any(keyword in object_name.lower() for keyword in ['food', 'dish', 'plate']):
                base_priority += 2
        elif scene_context.room_type == RoomType.BATHROOM:
            if any(keyword in object_name.lower() for keyword in ['hygiene', 'toilet', 'towel']):
                base_priority += 2

        # Time-sensitive boosts
        if scene_context.time_of_day == TimeOfDay.EVENING:
            # Boost priority for items that should be cleaned before bed
            if any(keyword in object_name.lower() for keyword in ['dish', 'food', 'trash']):
                base_priority += 1

        return min(base_priority, 10)  # Cap at 10

    def _calculate_urgency_from_frequency(self, object_info: Optional[Dict],
                                        scene_context: SceneContext) -> int:
        """
        Calculate urgency based on cleaning frequency and context

        Args:
            object_info: Object information from database
            scene_context: Scene context

        Returns:
            Urgency score (1-10, higher is more urgent)
        """
        if not object_info:
            return 5  # Default urgency

        frequency = object_info.get("cleaning_frequency", CleaningFrequency.WEEKLY)

        # Base urgency from frequency
        urgency_map = {
            CleaningFrequency.IMMEDIATE: 10,
            CleaningFrequency.DAILY: 8,
            CleaningFrequency.WEEKLY: 5,
            CleaningFrequency.MONTHLY: 3,
            CleaningFrequency.SEASONAL: 2
        }

        base_urgency = urgency_map.get(frequency, 5)

        # Seasonal adjustments
        if scene_context.season == Season.SPRING:
            # Spring cleaning boost
            base_urgency += 1
        elif scene_context.season == Season.SUMMER:
            # Summer hygiene boost for food items
            if "food" in object_info.get("categories", []):
                base_urgency += 2

        return min(base_urgency, 10)  # Cap at 10

    def _analyze_lighting(self, ai_response: str) -> str:
        """Analyze lighting conditions from AI response"""
        response_lower = ai_response.lower()
        
        if any(word in response_lower for word in ['bright', 'well-lit', 'sunny', 'clear']):
            return "bright"
        elif any(word in response_lower for word in ['dim', 'dark', 'shadowy', 'poor lighting']):
            return "dim"
        elif any(word in response_lower for word in ['natural', 'daylight', 'window']):
            return "natural"
        else:
            return "normal"
    
    def _extract_cleanliness_indicators(self, ai_response: str) -> List[str]:
        """Extract cleanliness indicators from AI response"""
        indicators = []
        response_lower = ai_response.lower()
        
        # Positive indicators
        if any(word in response_lower for word in ['clean', 'tidy', 'organized', 'neat']):
            indicators.append("clean")
        
        # Negative indicators
        if any(word in response_lower for word in ['dirty', 'messy', 'cluttered', 'disorganized']):
            indicators.append("needs_cleaning")
        
        if any(word in response_lower for word in ['dust', 'dusty', 'grimy']):
            indicators.append("dusty")
        
        if any(word in response_lower for word in ['stain', 'spot', 'mark']):
            indicators.append("stained")
        
        if any(word in response_lower for word in ['clutter', 'scattered', 'items everywhere']):
            indicators.append("cluttered")
        
        return indicators

    def _generate_context_based_tasks(self, scene_context: SceneContext, ai_response: str) -> List[Dict]:
        """
        Generate tasks based on cleanliness indicators and room context

        Args:
            scene_context: Scene context analysis
            ai_response: Raw AI response

        Returns:
            List of context-based task dictionaries
        """
        context_tasks = []

        try:
            for indicator in scene_context.cleanliness_indicators:
                task = None

                if indicator == "dusty":
                    task = {
                        "description": f"Dust the surfaces in the {scene_context.room_type.value.replace('_', ' ')}",
                        "priority": 6,
                        "urgency": 5,
                        "object_type": "surfaces",
                        "location": scene_context.room_type.value,
                        "count": 1,
                        "confidence": 0.8,
                        "estimated_time": 15,
                        "safety_level": "low",
                        "hygiene_impact": "medium",
                        "cleaning_frequency": "weekly"
                    }
                elif indicator == "cluttered":
                    task = {
                        "description": f"Organize and declutter the {scene_context.room_type.value.replace('_', ' ')}",
                        "priority": 4,
                        "urgency": 6,
                        "object_type": "general",
                        "location": scene_context.room_type.value,
                        "count": 1,
                        "confidence": 0.8,
                        "estimated_time": 20,
                        "safety_level": "low",
                        "hygiene_impact": "low",
                        "cleaning_frequency": "weekly"
                    }
                elif indicator == "dirty":
                    task = {
                        "description": f"Clean the {scene_context.room_type.value.replace('_', ' ')} thoroughly",
                        "priority": 7,
                        "urgency": 8,
                        "object_type": "room",
                        "location": scene_context.room_type.value,
                        "count": 1,
                        "confidence": 0.9,
                        "estimated_time": 30,
                        "safety_level": "low",
                        "hygiene_impact": "high",
                        "cleaning_frequency": "weekly"
                    }

                if task:
                    context_tasks.append(task)

        except Exception as e:
            self.logger.error(f"Error generating context-based tasks: {e}")

        return context_tasks

    def _generate_seasonal_tasks(self, scene_context: SceneContext, ai_response: str) -> List[Dict]:
        """
        Generate seasonal maintenance tasks

        Args:
            scene_context: Scene context analysis
            ai_response: Raw AI response

        Returns:
            List of seasonal task dictionaries
        """
        seasonal_tasks = []

        try:
            seasonal_data = self.seasonal_adjustments.get(scene_context.season, {})
            for focus_area in seasonal_data.get('focus_areas', []):
                if focus_area in ai_response.lower():
                    task = {
                        "description": f"Seasonal maintenance: Address {focus_area} for {scene_context.season.value}",
                        "priority": 5,
                        "urgency": 4,
                        "object_type": "seasonal",
                        "location": focus_area,
                        "count": 1,
                        "confidence": 0.7,
                        "estimated_time": 25,
                        "safety_level": "low",
                        "hygiene_impact": "medium",
                        "cleaning_frequency": "seasonal"
                    }
                    seasonal_tasks.append(task)

        except Exception as e:
            self.logger.error(f"Error generating seasonal tasks: {e}")

        return seasonal_tasks

    def _apply_hybrid_prioritization(self, tasks: List[Dict]) -> List[Dict]:
        """
        Apply Gemini's hybrid prioritization: Safety/Hygiene → Aesthetics

        Args:
            tasks: List of task dictionaries

        Returns:
            List of tasks sorted by hybrid priority
        """
        try:
            def priority_key(task):
                # Primary sort: Safety level (critical safety issues first)
                safety_priority = {
                    "critical": 1000,
                    "high": 900,
                    "medium": 800,
                    "low": 700
                }.get(task.get("safety_level", "low"), 700)

                # Secondary sort: Hygiene impact
                hygiene_priority = {
                    "critical": 100,
                    "high": 90,
                    "medium": 80,
                    "low": 70
                }.get(task.get("hygiene_impact", "low"), 70)

                # Tertiary sort: Task priority and urgency
                task_priority = task.get("priority", 5) * 10
                task_urgency = task.get("urgency", 5)

                # Combined score (higher is more important)
                return safety_priority + hygiene_priority + task_priority + task_urgency

            # Sort tasks by hybrid priority (highest first)
            sorted_tasks = sorted(tasks, key=priority_key, reverse=True)

            self.logger.debug(f"Applied hybrid prioritization to {len(tasks)} tasks")
            return sorted_tasks

        except Exception as e:
            self.logger.error(f"Error applying hybrid prioritization: {e}")
            return tasks  # Return original order if sorting fails

    def generate_contextual_insights(self, scene_context: SceneContext,
                                   ai_analysis: Dict[str, Any]) -> List[ContextualInsight]:
        """
        Generate contextual insights based on scene understanding

        Args:
            scene_context: Scene context analysis
            ai_analysis: Original AI analysis results

        Returns:
            List of contextual insights
        """
        insights = []

        # Room-specific insights
        room_insights = self._generate_room_specific_insights(scene_context)
        insights.extend(room_insights)

        # Seasonal insights
        seasonal_insights = self._generate_seasonal_insights(scene_context)
        insights.extend(seasonal_insights)

        # Time-based insights
        time_insights = self._generate_time_based_insights(scene_context)
        insights.extend(time_insights)

        # Object-specific insights
        object_insights = self._generate_object_insights(scene_context)
        insights.extend(object_insights)

        return insights

    def _generate_room_specific_insights(self, context: SceneContext) -> List[ContextualInsight]:
        """Generate insights specific to the room type"""
        insights = []

        if context.room_type == RoomType.KITCHEN:
            if 'stained' in context.cleanliness_indicators:
                insights.append(ContextualInsight(
                    insight_type="room_specific",
                    description="Kitchen stains require immediate attention for food safety",
                    confidence=0.9,
                    room_specific=True,
                    seasonal_relevance=False,
                    time_sensitive=True,
                    supporting_evidence=["food safety", "hygiene requirements"]
                ))

            if context.time_of_day in [TimeOfDay.MORNING, TimeOfDay.EVENING]:
                insights.append(ContextualInsight(
                    insight_type="usage_pattern",
                    description="Peak kitchen usage time - prioritize quick cleaning tasks",
                    confidence=0.8,
                    room_specific=True,
                    seasonal_relevance=False,
                    time_sensitive=True,
                    supporting_evidence=["meal preparation times"]
                ))

        elif context.room_type == RoomType.BATHROOM:
            if 'needs_cleaning' in context.cleanliness_indicators:
                insights.append(ContextualInsight(
                    insight_type="hygiene_priority",
                    description="Bathroom cleanliness is critical for health and hygiene",
                    confidence=0.95,
                    room_specific=True,
                    seasonal_relevance=False,
                    time_sensitive=True,
                    supporting_evidence=["health requirements", "hygiene standards"]
                ))

        elif context.room_type == RoomType.BEDROOM:
            if context.time_of_day == TimeOfDay.MORNING:
                insights.append(ContextualInsight(
                    insight_type="daily_routine",
                    description="Morning is ideal time for bedroom organization",
                    confidence=0.7,
                    room_specific=True,
                    seasonal_relevance=False,
                    time_sensitive=True,
                    supporting_evidence=["daily routine optimization"]
                ))

        return insights

    def _generate_seasonal_insights(self, context: SceneContext) -> List[ContextualInsight]:
        """Generate seasonal cleaning insights"""
        insights = []

        seasonal_data = self.seasonal_adjustments[context.season]

        # Check if any detected objects need seasonal attention
        for focus_area in seasonal_data['focus_areas']:
            if any(focus_area in obj for obj in context.detected_objects):
                insights.append(ContextualInsight(
                    insight_type="seasonal_priority",
                    description=f"{context.season.value.title()} focus: {focus_area} requires attention",
                    confidence=0.8,
                    room_specific=False,
                    seasonal_relevance=True,
                    time_sensitive=False,
                    supporting_evidence=[f"{context.season.value} maintenance"]
                ))

        # Seasonal frequency adjustments
        if seasonal_data['frequency_multiplier'] > 1.0:
            insights.append(ContextualInsight(
                insight_type="frequency_adjustment",
                description=f"Increase cleaning frequency by {(seasonal_data['frequency_multiplier'] - 1) * 100:.0f}% for {context.season.value}",
                confidence=0.7,
                room_specific=False,
                seasonal_relevance=True,
                time_sensitive=False,
                supporting_evidence=[f"{context.season.value} requirements"]
            ))

        return insights

    def _generate_time_based_insights(self, context: SceneContext) -> List[ContextualInsight]:
        """Generate time-of-day based insights"""
        insights = []

        if context.time_of_day == TimeOfDay.MORNING:
            insights.append(ContextualInsight(
                insight_type="optimal_timing",
                description="Morning is optimal for quick tidying and organization tasks",
                confidence=0.7,
                room_specific=False,
                seasonal_relevance=False,
                time_sensitive=True,
                supporting_evidence=["energy levels", "daily routine"]
            ))

        elif context.time_of_day == TimeOfDay.EVENING:
            insights.append(ContextualInsight(
                insight_type="optimal_timing",
                description="Evening is good for deeper cleaning tasks and preparation for next day",
                confidence=0.6,
                room_specific=False,
                seasonal_relevance=False,
                time_sensitive=True,
                supporting_evidence=["available time", "next day preparation"]
            ))

        return insights

    def _generate_object_insights(self, context: SceneContext) -> List[ContextualInsight]:
        """Generate insights based on detected objects"""
        insights = []

        # Check object database for specific cleaning requirements
        for category, data in self.object_database.items():
            detected_category_objects = [obj for obj in context.detected_objects
                                       if obj in data['objects']]

            if detected_category_objects:
                if data['priority_level'] == 'high':
                    insights.append(ContextualInsight(
                        insight_type="object_priority",
                        description=f"High-priority objects detected: {', '.join(detected_category_objects)}",
                        confidence=0.8,
                        room_specific=True,
                        seasonal_relevance=False,
                        time_sensitive=True,
                        supporting_evidence=[f"{category} maintenance requirements"]
                    ))

        return insights

    def enhance_ai_prompt(self, base_prompt: str, scene_context: SceneContext) -> str:
        """
        Enhance AI prompt with contextual information

        Args:
            base_prompt: Original AI prompt
            scene_context: Scene context analysis

        Returns:
            Enhanced prompt with context
        """
        # Add room type context
        room_context = f"\nRoom Type: {scene_context.room_type.value.replace('_', ' ').title()}"

        # Add seasonal context
        seasonal_data = self.seasonal_adjustments[scene_context.season]
        seasonal_context = f"\nSeasonal Context ({scene_context.season.value.title()}): Focus on {', '.join(seasonal_data['focus_areas'])}"

        # Add time context
        time_context = f"\nTime Context: {scene_context.time_of_day.value.title()} - consider appropriate task timing"

        # Add detected objects context
        if scene_context.detected_objects:
            objects_context = f"\nDetected Objects: {', '.join(scene_context.detected_objects[:10])}"  # Limit to first 10
        else:
            objects_context = ""

        # Add lighting context
        lighting_context = f"\nLighting: {scene_context.lighting_condition}"

        # Combine all context
        enhanced_prompt = (
            base_prompt +
            room_context +
            seasonal_context +
            time_context +
            objects_context +
            lighting_context +
            "\n\nPlease consider this contextual information when analyzing the image and generating recommendations."
        )

        return enhanced_prompt

    def prioritize_tasks_with_context(self, tasks: List[Dict], scene_context: SceneContext) -> List[Dict]:
        """
        Prioritize tasks based on contextual understanding

        Args:
            tasks: List of tasks to prioritize
            scene_context: Scene context analysis

        Returns:
            Prioritized list of tasks
        """
        # Create a copy to avoid modifying original
        prioritized_tasks = [task.copy() for task in tasks]

        seasonal_data = self.seasonal_adjustments[scene_context.season]

        for task in prioritized_tasks:
            original_priority = task.get('priority', 5)
            context_boost = 0

            # Room-specific priority boosts
            if scene_context.room_type == RoomType.KITCHEN:
                if any(keyword in task.get('description', '').lower()
                      for keyword in ['clean', 'sanitize', 'food', 'counter']):
                    context_boost += 2

            elif scene_context.room_type == RoomType.BATHROOM:
                if any(keyword in task.get('description', '').lower()
                      for keyword in ['clean', 'sanitize', 'disinfect']):
                    context_boost += 3

            # Seasonal priority boosts
            for boost_area in seasonal_data['priority_boost']:
                if boost_area in task.get('description', '').lower():
                    context_boost += 1

            # Time-based adjustments
            if scene_context.time_of_day == TimeOfDay.MORNING:
                if any(keyword in task.get('description', '').lower()
                      for keyword in ['organize', 'tidy', 'quick']):
                    context_boost += 1

            # Apply frequency multiplier
            frequency_boost = (seasonal_data['frequency_multiplier'] - 1.0) * 2
            context_boost += frequency_boost

            # Update priority (cap at 10)
            task['priority'] = min(10, original_priority + context_boost)
            task['context_boost'] = context_boost
            task['original_priority'] = original_priority

        # Sort by priority (highest first)
        prioritized_tasks.sort(key=lambda x: x.get('priority', 5), reverse=True)

        return prioritized_tasks

    def get_context_summary(self, scene_context: SceneContext) -> Dict[str, Any]:
        """
        Get a summary of the scene context

        Args:
            scene_context: Scene context analysis

        Returns:
            Context summary dictionary
        """
        return {
            'room_type': scene_context.room_type.value,
            'season': scene_context.season.value,
            'time_of_day': scene_context.time_of_day.value,
            'lighting': scene_context.lighting_condition,
            'detected_objects_count': len(scene_context.detected_objects),
            'detected_objects': scene_context.detected_objects[:10],  # First 10 objects
            'cleanliness_indicators': scene_context.cleanliness_indicators,
            'seasonal_focus_areas': self.seasonal_adjustments[scene_context.season]['focus_areas'],
            'seasonal_frequency_multiplier': self.seasonal_adjustments[scene_context.season]['frequency_multiplier'],
            'context_timestamp': datetime.now(timezone.utc).isoformat()
        }
