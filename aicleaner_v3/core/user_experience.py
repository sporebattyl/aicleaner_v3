"""
User Experience Enhancement Module for AICleaner Phase 3B
Provides intelligent user interface improvements, adaptive behavior,
and personalized experiences
"""
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics


class UserPreference(Enum):
    """User preference categories"""
    NOTIFICATION_FREQUENCY = "notification_frequency"
    CLEANING_SCHEDULE = "cleaning_schedule"
    PRIVACY_LEVEL = "privacy_level"
    AUTOMATION_LEVEL = "automation_level"
    INTERFACE_COMPLEXITY = "interface_complexity"


class ExperienceLevel(Enum):
    """User experience levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class InteractionType(Enum):
    """Types of user interactions"""
    TASK_COMPLETION = "task_completion"
    CONFIGURATION_CHANGE = "configuration_change"
    FEEDBACK_PROVIDED = "feedback_provided"
    ERROR_ENCOUNTERED = "error_encountered"
    FEATURE_USAGE = "feature_usage"


@dataclass
class UserInteraction:
    """User interaction record"""
    timestamp: str
    interaction_type: InteractionType
    component: str
    action: str
    success: bool
    duration_seconds: float
    context: Dict[str, Any]
    satisfaction_score: Optional[float] = None


@dataclass
class UserProfile:
    """User profile with preferences and behavior patterns"""
    user_id: str
    experience_level: ExperienceLevel
    preferences: Dict[UserPreference, Any]
    interaction_history: List[UserInteraction]
    learning_progress: Dict[str, float]
    satisfaction_scores: List[float]
    created_at: str
    last_updated: str


@dataclass
class AdaptiveRecommendation:
    """Adaptive recommendation for user experience"""
    recommendation_id: str
    category: str
    title: str
    description: str
    confidence: float
    impact_score: float
    implementation_effort: str
    user_benefit: str
    suggested_action: Dict[str, Any]


class UserExperienceEngine:
    """
    User Experience Enhancement Engine
    
    Features:
    - Adaptive user interface based on behavior patterns
    - Personalized recommendations and suggestions
    - Learning progress tracking
    - Satisfaction monitoring and improvement
    - Intelligent automation adjustments
    - Context-aware assistance
    """
    
    def __init__(self, data_path: str = "/data/user_experience"):
        """
        Initialize user experience engine
        
        Args:
            data_path: Path to store user experience data
        """
        self.data_path = data_path
        self.logger = logging.getLogger(__name__)
        
        # User profiles and interactions
        self.user_profiles = {}
        self.interaction_patterns = defaultdict(list)
        self.satisfaction_trends = defaultdict(deque)
        
        # Adaptive recommendations
        self.recommendations = []
        self.recommendation_feedback = {}
        
        # Learning algorithms
        self.behavior_models = {}
        self.preference_predictors = {}
        
        # Load existing data
        self._load_user_data()
        
        self.logger.info("User Experience Engine initialized")
    
    def _load_user_data(self):
        """Load existing user experience data"""
        import os
        
        os.makedirs(self.data_path, exist_ok=True)
        
        profiles_file = os.path.join(self.data_path, "user_profiles.json")
        if os.path.exists(profiles_file):
            try:
                with open(profiles_file, 'r') as f:
                    data = json.load(f)
                    for user_id, profile_data in data.items():
                        # Convert interaction history
                        interactions = []
                        for interaction_data in profile_data.get('interaction_history', []):
                            interaction_data['interaction_type'] = InteractionType(interaction_data['interaction_type'])
                            interactions.append(UserInteraction(**interaction_data))
                        
                        profile_data['interaction_history'] = interactions
                        profile_data['experience_level'] = ExperienceLevel(profile_data['experience_level'])
                        
                        # Convert preferences
                        preferences = {}
                        for pref_key, pref_value in profile_data.get('preferences', {}).items():
                            preferences[UserPreference(pref_key)] = pref_value
                        profile_data['preferences'] = preferences
                        
                        self.user_profiles[user_id] = UserProfile(**profile_data)
                
                self.logger.info(f"Loaded {len(self.user_profiles)} user profiles")
            except Exception as e:
                self.logger.error(f"Failed to load user profiles: {e}")
    
    def _save_user_data(self):
        """Save user experience data"""
        profiles_file = os.path.join(self.data_path, "user_profiles.json")
        
        try:
            # Convert profiles to serializable format
            serializable_profiles = {}
            for user_id, profile in self.user_profiles.items():
                profile_dict = asdict(profile)
                
                # Convert enums to strings
                profile_dict['experience_level'] = profile.experience_level.value
                
                # Convert preferences
                preferences = {}
                for pref_key, pref_value in profile.preferences.items():
                    preferences[pref_key.value] = pref_value
                profile_dict['preferences'] = preferences
                
                # Convert interaction history
                interactions = []
                for interaction in profile.interaction_history:
                    interaction_dict = asdict(interaction)
                    interaction_dict['interaction_type'] = interaction.interaction_type.value
                    interactions.append(interaction_dict)
                profile_dict['interaction_history'] = interactions
                
                serializable_profiles[user_id] = profile_dict
            
            with open(profiles_file, 'w') as f:
                json.dump(serializable_profiles, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save user profiles: {e}")
    
    def create_user_profile(self, user_id: str, initial_preferences: Optional[Dict] = None) -> UserProfile:
        """Create a new user profile"""
        default_preferences = {
            UserPreference.NOTIFICATION_FREQUENCY: "moderate",
            UserPreference.CLEANING_SCHEDULE: "adaptive",
            UserPreference.PRIVACY_LEVEL: "standard",
            UserPreference.AUTOMATION_LEVEL: "balanced",
            UserPreference.INTERFACE_COMPLEXITY: "simple"
        }
        
        if initial_preferences:
            default_preferences.update(initial_preferences)
        
        profile = UserProfile(
            user_id=user_id,
            experience_level=ExperienceLevel.BEGINNER,
            preferences=default_preferences,
            interaction_history=[],
            learning_progress={},
            satisfaction_scores=[],
            created_at=datetime.now(timezone.utc).isoformat(),
            last_updated=datetime.now(timezone.utc).isoformat()
        )
        
        self.user_profiles[user_id] = profile
        self._save_user_data()
        
        self.logger.info(f"Created user profile for {user_id}")
        return profile
    
    def record_interaction(self, user_id: str, interaction: UserInteraction):
        """Record a user interaction"""
        if user_id not in self.user_profiles:
            self.create_user_profile(user_id)
        
        profile = self.user_profiles[user_id]
        profile.interaction_history.append(interaction)
        profile.last_updated = datetime.now(timezone.utc).isoformat()
        
        # Limit interaction history size
        if len(profile.interaction_history) > 1000:
            profile.interaction_history = profile.interaction_history[-1000:]
        
        # Update interaction patterns
        pattern_key = f"{interaction.component}.{interaction.action}"
        self.interaction_patterns[pattern_key].append({
            'user_id': user_id,
            'timestamp': interaction.timestamp,
            'success': interaction.success,
            'duration': interaction.duration_seconds
        })
        
        # Update satisfaction trends
        if interaction.satisfaction_score is not None:
            self.satisfaction_trends[user_id].append(interaction.satisfaction_score)
            if len(self.satisfaction_trends[user_id]) > 100:
                self.satisfaction_trends[user_id].popleft()
        
        # Update experience level based on interactions
        self._update_experience_level(user_id)
        
        # Generate adaptive recommendations
        self._generate_adaptive_recommendations(user_id)
        
        self._save_user_data()
    
    def _update_experience_level(self, user_id: str):
        """Update user experience level based on interaction history"""
        profile = self.user_profiles[user_id]
        
        # Calculate experience metrics
        total_interactions = len(profile.interaction_history)
        successful_interactions = sum(1 for i in profile.interaction_history if i.success)
        success_rate = successful_interactions / total_interactions if total_interactions > 0 else 0
        
        # Count unique features used
        unique_features = len(set(f"{i.component}.{i.action}" for i in profile.interaction_history))
        
        # Calculate average satisfaction
        avg_satisfaction = statistics.mean(profile.satisfaction_scores) if profile.satisfaction_scores else 0
        
        # Determine experience level
        if total_interactions >= 100 and success_rate >= 0.9 and unique_features >= 20 and avg_satisfaction >= 4.0:
            new_level = ExperienceLevel.EXPERT
        elif total_interactions >= 50 and success_rate >= 0.8 and unique_features >= 15:
            new_level = ExperienceLevel.ADVANCED
        elif total_interactions >= 20 and success_rate >= 0.7 and unique_features >= 10:
            new_level = ExperienceLevel.INTERMEDIATE
        else:
            new_level = ExperienceLevel.BEGINNER
        
        if new_level != profile.experience_level:
            old_level = profile.experience_level
            profile.experience_level = new_level
            self.logger.info(f"User {user_id} experience level updated: {old_level.value} -> {new_level.value}")
    
    def _generate_adaptive_recommendations(self, user_id: str):
        """Generate adaptive recommendations for user"""
        profile = self.user_profiles[user_id]
        
        # Analyze recent interactions for patterns
        recent_interactions = profile.interaction_history[-50:]  # Last 50 interactions
        
        # Identify pain points
        failed_interactions = [i for i in recent_interactions if not i.success]
        slow_interactions = [i for i in recent_interactions if i.duration_seconds > 10]
        
        recommendations = []
        
        # Recommendation: Simplify interface for beginners
        if profile.experience_level == ExperienceLevel.BEGINNER and len(failed_interactions) > 5:
            recommendations.append(AdaptiveRecommendation(
                recommendation_id=f"simplify_ui_{user_id}_{int(time.time())}",
                category="interface",
                title="Simplify Interface",
                description="Switch to simplified interface mode to reduce complexity",
                confidence=0.8,
                impact_score=0.7,
                implementation_effort="low",
                user_benefit="Easier navigation and reduced errors",
                suggested_action={
                    "action": "update_preference",
                    "preference": UserPreference.INTERFACE_COMPLEXITY.value,
                    "value": "simple"
                }
            ))
        
        # Recommendation: Increase automation for experienced users
        if profile.experience_level in [ExperienceLevel.ADVANCED, ExperienceLevel.EXPERT]:
            manual_tasks = [i for i in recent_interactions if "manual" in i.action.lower()]
            if len(manual_tasks) > 10:
                recommendations.append(AdaptiveRecommendation(
                    recommendation_id=f"increase_automation_{user_id}_{int(time.time())}",
                    category="automation",
                    title="Increase Automation",
                    description="Enable more automated features to save time",
                    confidence=0.9,
                    impact_score=0.8,
                    implementation_effort="medium",
                    user_benefit="Reduced manual work and increased efficiency",
                    suggested_action={
                        "action": "update_preference",
                        "preference": UserPreference.AUTOMATION_LEVEL.value,
                        "value": "high"
                    }
                ))
        
        # Recommendation: Adjust notification frequency
        notification_interactions = [i for i in recent_interactions if "notification" in i.action.lower()]
        if len(notification_interactions) > 0:
            avg_satisfaction = statistics.mean([i.satisfaction_score for i in notification_interactions if i.satisfaction_score])
            if avg_satisfaction < 3.0:
                recommendations.append(AdaptiveRecommendation(
                    recommendation_id=f"adjust_notifications_{user_id}_{int(time.time())}",
                    category="notifications",
                    title="Adjust Notification Frequency",
                    description="Reduce notification frequency based on your interaction patterns",
                    confidence=0.7,
                    impact_score=0.6,
                    implementation_effort="low",
                    user_benefit="Less interruption and better focus",
                    suggested_action={
                        "action": "update_preference",
                        "preference": UserPreference.NOTIFICATION_FREQUENCY.value,
                        "value": "low"
                    }
                ))
        
        # Store recommendations
        self.recommendations.extend(recommendations)
        
        # Limit recommendations history
        if len(self.recommendations) > 100:
            self.recommendations = self.recommendations[-100:]
    
    def get_personalized_interface_config(self, user_id: str) -> Dict[str, Any]:
        """Get personalized interface configuration for user"""
        if user_id not in self.user_profiles:
            return self._get_default_interface_config()
        
        profile = self.user_profiles[user_id]
        
        config = {
            "complexity_level": profile.preferences.get(UserPreference.INTERFACE_COMPLEXITY, "simple"),
            "automation_level": profile.preferences.get(UserPreference.AUTOMATION_LEVEL, "balanced"),
            "notification_frequency": profile.preferences.get(UserPreference.NOTIFICATION_FREQUENCY, "moderate"),
            "privacy_level": profile.preferences.get(UserPreference.PRIVACY_LEVEL, "standard"),
            "experience_level": profile.experience_level.value,
            "show_advanced_features": profile.experience_level in [ExperienceLevel.ADVANCED, ExperienceLevel.EXPERT],
            "enable_tooltips": profile.experience_level == ExperienceLevel.BEGINNER,
            "compact_view": profile.experience_level == ExperienceLevel.EXPERT,
            "auto_suggestions": True,
            "contextual_help": profile.experience_level in [ExperienceLevel.BEGINNER, ExperienceLevel.INTERMEDIATE]
        }
        
        return config
    
    def _get_default_interface_config(self) -> Dict[str, Any]:
        """Get default interface configuration"""
        return {
            "complexity_level": "simple",
            "automation_level": "balanced",
            "notification_frequency": "moderate",
            "privacy_level": "standard",
            "experience_level": "beginner",
            "show_advanced_features": False,
            "enable_tooltips": True,
            "compact_view": False,
            "auto_suggestions": True,
            "contextual_help": True
        }
    
    def get_user_recommendations(self, user_id: str) -> List[AdaptiveRecommendation]:
        """Get recommendations for a specific user"""
        user_recommendations = [
            rec for rec in self.recommendations
            if user_id in rec.recommendation_id
        ]
        
        # Sort by confidence and impact
        user_recommendations.sort(key=lambda r: r.confidence * r.impact_score, reverse=True)
        
        return user_recommendations[:5]  # Return top 5 recommendations
    
    def provide_recommendation_feedback(self, recommendation_id: str, 
                                      accepted: bool, satisfaction: float):
        """Provide feedback on a recommendation"""
        self.recommendation_feedback[recommendation_id] = {
            'accepted': accepted,
            'satisfaction': satisfaction,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.logger.info(f"Recommendation feedback: {recommendation_id} - accepted: {accepted}, satisfaction: {satisfaction}")
    
    def get_user_experience_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user experience summary"""
        if user_id not in self.user_profiles:
            return {"error": "User profile not found"}
        
        profile = self.user_profiles[user_id]
        
        # Calculate metrics
        total_interactions = len(profile.interaction_history)
        successful_interactions = sum(1 for i in profile.interaction_history if i.success)
        success_rate = successful_interactions / total_interactions if total_interactions > 0 else 0
        
        avg_satisfaction = statistics.mean(profile.satisfaction_scores) if profile.satisfaction_scores else 0
        
        recent_satisfaction = statistics.mean(
            list(self.satisfaction_trends[user_id])[-10:]
        ) if self.satisfaction_trends[user_id] else 0
        
        return {
            'user_id': user_id,
            'experience_level': profile.experience_level.value,
            'total_interactions': total_interactions,
            'success_rate': success_rate,
            'average_satisfaction': avg_satisfaction,
            'recent_satisfaction': recent_satisfaction,
            'preferences': {pref.value: value for pref, value in profile.preferences.items()},
            'recommendations_count': len(self.get_user_recommendations(user_id)),
            'learning_progress': profile.learning_progress,
            'interface_config': self.get_personalized_interface_config(user_id),
            'created_at': profile.created_at,
            'last_updated': profile.last_updated
        }
