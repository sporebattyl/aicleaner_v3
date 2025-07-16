"""
Object Database for AI Cleaner v3

This module provides a comprehensive database of household objects with their
cleaning characteristics, priorities, and contextual information. This data
is used by the scene understanding system to generate more intelligent and
prioritized cleaning tasks.

Key Features:
- Object cleaning frequency recommendations
- Safety and hygiene priority levels
- Room-specific context and handling
- Typical cleanup time estimates
- Seasonal considerations
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import json
import logging


class SafetyLevel(Enum):
    """Safety levels for objects"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HygieneImpact(Enum):
    """Hygiene impact levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CleaningFrequency(Enum):
    """Recommended cleaning frequencies"""
    IMMEDIATE = "immediate"      # Needs immediate attention
    DAILY = "daily"             # Should be cleaned daily
    WEEKLY = "weekly"           # Weekly cleaning sufficient
    MONTHLY = "monthly"         # Monthly cleaning sufficient
    SEASONAL = "seasonal"       # Seasonal cleaning


class ObjectDatabase:
    """
    Comprehensive database of household objects with cleaning characteristics
    
    This database provides detailed information about household objects to help
    the AI system generate more intelligent and prioritized cleaning tasks.
    """
    
    def __init__(self):
        """Initialize the object database"""
        self.logger = logging.getLogger(__name__)
        self._objects = self._initialize_object_database()
    
    def _initialize_object_database(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize the comprehensive object database
        
        Returns:
            Dictionary mapping object names to their characteristics
        """
        return {
            # Kitchen Objects
            "dishes": {
                "priority_level": 8,
                "cleaning_frequency": CleaningFrequency.IMMEDIATE,
                "safety_level": SafetyLevel.MEDIUM,
                "hygiene_impact": HygieneImpact.HIGH,
                "typical_cleanup_time": 10,
                "categories": ["kitchen", "hygiene"],
                "room_specific_handling": {
                    "kitchen": "Clean and put away in dishwasher or cabinet",
                    "dining_room": "Collect and take to kitchen for cleaning"
                },
                "seasonal_considerations": {
                    "summer": "Extra attention to prevent bacterial growth",
                    "winter": "Standard cleaning protocol"
                }
            },
            "food": {
                "priority_level": 9,
                "cleaning_frequency": CleaningFrequency.IMMEDIATE,
                "safety_level": SafetyLevel.HIGH,
                "hygiene_impact": HygieneImpact.CRITICAL,
                "typical_cleanup_time": 5,
                "categories": ["kitchen", "hygiene", "perishable"],
                "room_specific_handling": {
                    "kitchen": "Store properly or dispose if spoiled",
                    "living_room": "Remove immediately to prevent pests"
                }
            },
            "cup": {
                "priority_level": 6,
                "cleaning_frequency": CleaningFrequency.DAILY,
                "safety_level": SafetyLevel.LOW,
                "hygiene_impact": HygieneImpact.MEDIUM,
                "typical_cleanup_time": 3,
                "categories": ["kitchen", "drinkware"],
                "room_specific_handling": {
                    "kitchen": "Rinse and put in dishwasher",
                    "living_room": "Take to kitchen for cleaning",
                    "bedroom": "Take to kitchen, check for spills"
                }
            },
            "plate": {
                "priority_level": 7,
                "cleaning_frequency": CleaningFrequency.IMMEDIATE,
                "safety_level": SafetyLevel.MEDIUM,
                "hygiene_impact": HygieneImpact.HIGH,
                "typical_cleanup_time": 5,
                "categories": ["kitchen", "tableware"],
                "room_specific_handling": {
                    "kitchen": "Scrape and load into dishwasher",
                    "dining_room": "Clear and take to kitchen"
                }
            },
            
            # Clothing and Textiles
            "clothes": {
                "priority_level": 4,
                "cleaning_frequency": CleaningFrequency.WEEKLY,
                "safety_level": SafetyLevel.LOW,
                "hygiene_impact": HygieneImpact.MEDIUM,
                "typical_cleanup_time": 8,
                "categories": ["clothing", "textile"],
                "room_specific_handling": {
                    "bedroom": "Fold and put in dresser or hang in closet",
                    "bathroom": "Check if clean or dirty, handle appropriately",
                    "living_room": "Fold and return to bedroom"
                }
            },
            "towel": {
                "priority_level": 5,
                "cleaning_frequency": CleaningFrequency.WEEKLY,
                "safety_level": SafetyLevel.LOW,
                "hygiene_impact": HygieneImpact.MEDIUM,
                "typical_cleanup_time": 3,
                "categories": ["bathroom", "textile"],
                "room_specific_handling": {
                    "bathroom": "Hang properly to dry or put in laundry",
                    "kitchen": "Replace with clean towel if used for cleaning"
                }
            },
            
            # Personal Items
            "book": {
                "priority_level": 2,
                "cleaning_frequency": CleaningFrequency.WEEKLY,
                "safety_level": SafetyLevel.LOW,
                "hygiene_impact": HygieneImpact.LOW,
                "typical_cleanup_time": 2,
                "categories": ["personal", "entertainment"],
                "room_specific_handling": {
                    "living_room": "Return to bookshelf or reading area",
                    "bedroom": "Place on nightstand or return to shelf",
                    "kitchen": "Remove to prevent damage from spills"
                }
            },
            "shoe": {
                "priority_level": 3,
                "cleaning_frequency": CleaningFrequency.WEEKLY,
                "safety_level": SafetyLevel.LOW,
                "hygiene_impact": HygieneImpact.MEDIUM,
                "typical_cleanup_time": 5,
                "categories": ["personal", "footwear"],
                "room_specific_handling": {
                    "entrance": "Organize in shoe rack or designated area",
                    "bedroom": "Return to closet or shoe storage",
                    "living_room": "Move to entrance area"
                }
            },
            
            # Paper and Office Items
            "paper": {
                "priority_level": 3,
                "cleaning_frequency": CleaningFrequency.WEEKLY,
                "safety_level": SafetyLevel.LOW,
                "hygiene_impact": HygieneImpact.LOW,
                "typical_cleanup_time": 3,
                "categories": ["office", "clutter"],
                "room_specific_handling": {
                    "office": "Sort, file, or recycle as appropriate",
                    "kitchen": "Remove to prevent clutter and fire hazard",
                    "living_room": "Organize or move to office area"
                }
            },
            "magazine": {
                "priority_level": 2,
                "cleaning_frequency": CleaningFrequency.MONTHLY,
                "safety_level": SafetyLevel.LOW,
                "hygiene_impact": HygieneImpact.LOW,
                "typical_cleanup_time": 2,
                "categories": ["entertainment", "reading"],
                "room_specific_handling": {
                    "living_room": "Stack neatly on coffee table or magazine rack",
                    "bathroom": "Keep dry, organize in basket"
                }
            },
            
            # Containers and Bottles
            "bottle": {
                "priority_level": 5,
                "cleaning_frequency": CleaningFrequency.DAILY,
                "safety_level": SafetyLevel.MEDIUM,
                "hygiene_impact": HygieneImpact.MEDIUM,
                "typical_cleanup_time": 3,
                "categories": ["container", "recyclable"],
                "room_specific_handling": {
                    "kitchen": "Rinse and recycle or refill if reusable",
                    "living_room": "Take to kitchen for proper disposal",
                    "bedroom": "Remove to prevent spills and pests"
                }
            },
            
            # Electronics
            "laptop": {
                "priority_level": 6,
                "cleaning_frequency": CleaningFrequency.WEEKLY,
                "safety_level": SafetyLevel.MEDIUM,
                "hygiene_impact": HygieneImpact.LOW,
                "typical_cleanup_time": 5,
                "categories": ["electronics", "valuable"],
                "room_specific_handling": {
                    "office": "Place on desk or in laptop stand",
                    "living_room": "Move to safe, stable surface",
                    "bedroom": "Ensure proper ventilation, avoid bed"
                }
            },
            
            # Cleaning and Maintenance
            "trash": {
                "priority_level": 9,
                "cleaning_frequency": CleaningFrequency.IMMEDIATE,
                "safety_level": SafetyLevel.HIGH,
                "hygiene_impact": HygieneImpact.CRITICAL,
                "typical_cleanup_time": 2,
                "categories": ["waste", "hygiene"],
                "room_specific_handling": {
                    "any": "Dispose of immediately in appropriate waste bin"
                }
            },
            
            # Toys and Games
            "toy": {
                "priority_level": 3,
                "cleaning_frequency": CleaningFrequency.DAILY,
                "safety_level": SafetyLevel.MEDIUM,
                "hygiene_impact": HygieneImpact.MEDIUM,
                "typical_cleanup_time": 5,
                "categories": ["toy", "child_item"],
                "room_specific_handling": {
                    "playroom": "Organize in toy bins or shelves",
                    "living_room": "Return to designated play area",
                    "bedroom": "Place in toy box or return to playroom"
                }
            }
        }
    
    def get_object_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive information about an object
        
        Args:
            object_name: Name of the object to look up
            
        Returns:
            Dictionary with object information or None if not found
        """
        # Normalize object name for lookup
        normalized_name = object_name.lower().strip()
        
        # Direct lookup
        if normalized_name in self._objects:
            return self._objects[normalized_name].copy()
        
        # Fuzzy matching for common variations
        for obj_name, obj_info in self._objects.items():
            if normalized_name in obj_name or obj_name in normalized_name:
                return obj_info.copy()
        
        # Check categories for partial matches
        for obj_name, obj_info in self._objects.items():
            if any(normalized_name in category for category in obj_info.get("categories", [])):
                return obj_info.copy()
        
        self.logger.debug(f"Object '{object_name}' not found in database")
        return None
    
    def get_objects_by_priority(self, min_priority: int = 1) -> List[str]:
        """
        Get objects with priority level >= min_priority
        
        Args:
            min_priority: Minimum priority level (1-10)
            
        Returns:
            List of object names sorted by priority (highest first)
        """
        filtered_objects = [
            (name, info["priority_level"])
            for name, info in self._objects.items()
            if info["priority_level"] >= min_priority
        ]
        
        # Sort by priority (highest first)
        filtered_objects.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in filtered_objects]
    
    def get_objects_by_frequency(self, frequency: CleaningFrequency) -> List[str]:
        """
        Get objects that require specific cleaning frequency
        
        Args:
            frequency: Cleaning frequency to filter by
            
        Returns:
            List of object names with the specified frequency
        """
        return [
            name for name, info in self._objects.items()
            if info["cleaning_frequency"] == frequency
        ]
    
    def get_high_priority_objects(self) -> List[str]:
        """
        Get objects that require immediate or high priority attention
        
        Returns:
            List of high-priority object names
        """
        return self.get_objects_by_priority(min_priority=7)
    
    def get_safety_critical_objects(self) -> List[str]:
        """
        Get objects with high safety concerns
        
        Returns:
            List of safety-critical object names
        """
        return [
            name for name, info in self._objects.items()
            if info["safety_level"] in [SafetyLevel.HIGH, SafetyLevel.CRITICAL]
        ]
    
    def get_hygiene_critical_objects(self) -> List[str]:
        """
        Get objects with high hygiene impact
        
        Returns:
            List of hygiene-critical object names
        """
        return [
            name for name, info in self._objects.items()
            if info["hygiene_impact"] in [HygieneImpact.HIGH, HygieneImpact.CRITICAL]
        ]
