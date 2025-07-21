"""
Privacy-First Gamification System for AICleaner
Implements achievement system, progress tracking, and motivational features
with Home Assistant integration and privacy-preserving design
"""
import os
import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import statistics


class PrivacyLevel(Enum):
    """Privacy levels for gamification data"""
    MINIMAL = "minimal"  # Only basic stats
    STANDARD = "standard"  # Standard gamification features
    ENHANCED = "enhanced"  # Full features with privacy protection


class AchievementType(Enum):
    """Types of achievements"""
    TASK_COMPLETION = "task_completion"
    STREAK = "streak"
    EFFICIENCY = "efficiency"
    CONSISTENCY = "consistency"
    MILESTONE = "milestone"
    SPECIAL = "special"
    PRIVACY = "privacy"  # Privacy-related achievements


class AchievementRarity(Enum):
    """Achievement rarity levels"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class HAIntegrationType(Enum):
    """Home Assistant integration types"""
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    BUTTON = "button"
    NUMBER = "number"


@dataclass
class PrivacySettings:
    """Privacy settings for gamification"""
    privacy_level: PrivacyLevel = PrivacyLevel.STANDARD
    anonymize_zone_names: bool = True
    store_detailed_timestamps: bool = False
    share_with_ha: bool = True
    data_retention_days: int = 365


@dataclass
class HAEntity:
    """Home Assistant entity configuration"""
    entity_id: str
    name: str
    type: HAIntegrationType
    icon: str
    unit_of_measurement: Optional[str] = None
    device_class: Optional[str] = None
    state_class: Optional[str] = None


@dataclass
class Achievement:
    """Represents an achievement"""
    id: str
    title: str
    description: str
    icon: str
    type: AchievementType
    rarity: AchievementRarity
    points: int
    requirements: Dict[str, Any]
    unlocked: bool = False
    unlocked_date: Optional[str] = None
    progress: float = 0.0
    hidden: bool = False
    ha_entity: Optional[HAEntity] = None


@dataclass
class UserStats:
    """User statistics for gamification with privacy protection"""
    total_tasks_completed: int = 0
    total_zones_cleaned: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    total_points: int = 0
    level: int = 1
    experience: int = 0
    achievements_unlocked: int = 0
    efficiency_score: float = 0.0
    consistency_score: float = 0.0
    last_activity_date: Optional[str] = None
    join_date: str = ""
    privacy_score: int = 0  # Points for privacy-conscious behavior
    ha_entities_created: int = 0  # Track HA integration usage


@dataclass
class DailyChallenge:
    """Daily challenge for users"""
    id: str
    title: str
    description: str
    icon: str
    target: int
    current_progress: int
    points_reward: int
    date: str
    completed: bool = False
    challenge_type: str = "task_completion"


class GamificationSystem:
    """
    Privacy-First Gamification System for AICleaner with Home Assistant Integration

    Features:
    - Privacy-preserving achievement system with multiple types and rarities
    - Experience points and leveling system
    - Daily challenges and streaks
    - Progress tracking and statistics with local storage
    - Motivational features and rewards
    - Home Assistant entity integration
    - Privacy-conscious design with user controls
    """

    def __init__(self, data_path: str = "/data/gamification",
                 privacy_settings: Optional[PrivacySettings] = None,
                 ha_update_callback: Optional[Callable] = None):
        """
        Initialize privacy-first gamification system

        Args:
            data_path: Path to store gamification data
            privacy_settings: Privacy configuration
            ha_update_callback: Callback function for Home Assistant updates
        """
        self.data_path = data_path
        self.logger = logging.getLogger(__name__)
        self.privacy_settings = privacy_settings or PrivacySettings()
        self.ha_update_callback = ha_update_callback
        self.ha_entities = {}  # Track created HA entities

        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)

        # Load user data and achievements
        self.user_stats = self._load_user_stats()
        self.achievements = self._load_achievements()
        self.daily_challenges = self._load_daily_challenges()

        # Initialize achievement definitions
        self._initialize_achievements()

        # Initialize Home Assistant entities
        self._initialize_ha_entities()

        self.logger.info(f"Privacy-First Gamification system initialized with privacy level: {self.privacy_settings.privacy_level.value}")

    def _initialize_ha_entities(self):
        """Initialize Home Assistant entities for gamification tracking"""
        if not self.privacy_settings.share_with_ha:
            return

        # Define core gamification entities
        core_entities = [
            HAEntity(
                entity_id="sensor.aicleaner_level",
                name="AICleaner Level",
                type=HAIntegrationType.SENSOR,
                icon="mdi:star-outline",
                state_class="measurement"
            ),
            HAEntity(
                entity_id="sensor.aicleaner_experience",
                name="AICleaner Experience Points",
                type=HAIntegrationType.SENSOR,
                icon="mdi:trophy",
                unit_of_measurement="XP",
                state_class="total_increasing"
            ),
            HAEntity(
                entity_id="sensor.aicleaner_streak",
                name="AICleaner Cleaning Streak",
                type=HAIntegrationType.SENSOR,
                icon="mdi:fire",
                unit_of_measurement="days",
                state_class="measurement"
            ),
            HAEntity(
                entity_id="sensor.aicleaner_achievements",
                name="AICleaner Achievements Unlocked",
                type=HAIntegrationType.SENSOR,
                icon="mdi:medal",
                state_class="total_increasing"
            ),
            HAEntity(
                entity_id="binary_sensor.aicleaner_daily_challenge",
                name="AICleaner Daily Challenge Complete",
                type=HAIntegrationType.BINARY_SENSOR,
                icon="mdi:calendar-check",
                device_class="connectivity"
            )
        ]

        for entity in core_entities:
            self.ha_entities[entity.entity_id] = entity

        self.logger.info(f"Initialized {len(core_entities)} Home Assistant entities")

    def _update_ha_entity(self, entity_id: str, state: Any, attributes: Optional[Dict] = None):
        """Update a Home Assistant entity"""
        if not self.privacy_settings.share_with_ha or not self.ha_update_callback:
            return

        try:
            self.ha_update_callback(entity_id, state, attributes or {})
            self.logger.debug(f"Updated HA entity {entity_id} with state: {state}")
        except Exception as e:
            self.logger.error(f"Failed to update HA entity {entity_id}: {e}")

    def _load_user_stats(self) -> UserStats:
        """Load user statistics from file"""
        stats_file = os.path.join(self.data_path, "user_stats.json")
        
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r') as f:
                    data = json.load(f)
                return UserStats(**data)
            except Exception as e:
                self.logger.error(f"Error loading user stats: {e}")
        
        # Return default stats with current date
        return UserStats(join_date=datetime.now(timezone.utc).isoformat())
    
    def _save_user_stats(self):
        """Save user statistics to file"""
        stats_file = os.path.join(self.data_path, "user_stats.json")
        
        try:
            with open(stats_file, 'w') as f:
                json.dump(asdict(self.user_stats), f, indent=2)
            self.logger.debug("User stats saved")
        except Exception as e:
            self.logger.error(f"Error saving user stats: {e}")
    
    def _load_achievements(self) -> List[Achievement]:
        """Load achievements from file"""
        achievements_file = os.path.join(self.data_path, "achievements.json")
        
        if os.path.exists(achievements_file):
            try:
                with open(achievements_file, 'r') as f:
                    data = json.load(f)
                achievements = []
                for item in data:
                    # Convert enum strings back to enums
                    item['type'] = AchievementType(item['type'])
                    item['rarity'] = AchievementRarity(item['rarity'])
                    achievements.append(Achievement(**item))
                return achievements
            except Exception as e:
                self.logger.error(f"Error loading achievements: {e}")
        
        return []
    
    def _save_achievements(self):
        """Save achievements to file"""
        achievements_file = os.path.join(self.data_path, "achievements.json")
        
        try:
            # Convert achievements to serializable format
            data = []
            for achievement in self.achievements:
                achievement_dict = asdict(achievement)
                achievement_dict['type'] = achievement.type.value
                achievement_dict['rarity'] = achievement.rarity.value
                data.append(achievement_dict)
            
            with open(achievements_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug("Achievements saved")
        except Exception as e:
            self.logger.error(f"Error saving achievements: {e}")
    
    def _load_daily_challenges(self) -> List[DailyChallenge]:
        """Load daily challenges from file"""
        challenges_file = os.path.join(self.data_path, "daily_challenges.json")
        
        if os.path.exists(challenges_file):
            try:
                with open(challenges_file, 'r') as f:
                    data = json.load(f)
                return [DailyChallenge(**item) for item in data]
            except Exception as e:
                self.logger.error(f"Error loading daily challenges: {e}")
        
        return []
    
    def _save_daily_challenges(self):
        """Save daily challenges to file"""
        challenges_file = os.path.join(self.data_path, "daily_challenges.json")
        
        try:
            with open(challenges_file, 'w') as f:
                json.dump([asdict(challenge) for challenge in self.daily_challenges], f, indent=2)
            self.logger.debug("Daily challenges saved")
        except Exception as e:
            self.logger.error(f"Error saving daily challenges: {e}")
    
    def _initialize_achievements(self):
        """Initialize default achievements if none exist"""
        if self.achievements:
            return  # Achievements already exist
        
        default_achievements = [
            # Task Completion Achievements
            Achievement(
                id="first_task",
                title="Getting Started",
                description="Complete your first cleaning task",
                icon="mdi:star-outline",
                type=AchievementType.TASK_COMPLETION,
                rarity=AchievementRarity.COMMON,
                points=10,
                requirements={"tasks_completed": 1}
            ),
            Achievement(
                id="task_master_10",
                title="Task Master",
                description="Complete 10 cleaning tasks",
                icon="mdi:star",
                type=AchievementType.TASK_COMPLETION,
                rarity=AchievementRarity.UNCOMMON,
                points=50,
                requirements={"tasks_completed": 10}
            ),
            Achievement(
                id="task_legend_100",
                title="Cleaning Legend",
                description="Complete 100 cleaning tasks",
                icon="mdi:star-four-points",
                type=AchievementType.TASK_COMPLETION,
                rarity=AchievementRarity.RARE,
                points=200,
                requirements={"tasks_completed": 100}
            ),
            
            # Streak Achievements
            Achievement(
                id="streak_3",
                title="On a Roll",
                description="Maintain a 3-day cleaning streak",
                icon="mdi:fire",
                type=AchievementType.STREAK,
                rarity=AchievementRarity.COMMON,
                points=25,
                requirements={"streak_days": 3}
            ),
            Achievement(
                id="streak_7",
                title="Week Warrior",
                description="Maintain a 7-day cleaning streak",
                icon="mdi:fire",
                type=AchievementType.STREAK,
                rarity=AchievementRarity.UNCOMMON,
                points=75,
                requirements={"streak_days": 7}
            ),
            Achievement(
                id="streak_30",
                title="Consistency Champion",
                description="Maintain a 30-day cleaning streak",
                icon="mdi:fire",
                type=AchievementType.STREAK,
                rarity=AchievementRarity.EPIC,
                points=300,
                requirements={"streak_days": 30}
            ),
            
            # Efficiency Achievements
            Achievement(
                id="efficiency_master",
                title="Efficiency Master",
                description="Achieve 90% efficiency score",
                icon="mdi:speedometer",
                type=AchievementType.EFFICIENCY,
                rarity=AchievementRarity.RARE,
                points=150,
                requirements={"efficiency_score": 0.9}
            ),
            
            # Milestone Achievements
            Achievement(
                id="level_10",
                title="Rising Star",
                description="Reach level 10",
                icon="mdi:trophy-outline",
                type=AchievementType.MILESTONE,
                rarity=AchievementRarity.UNCOMMON,
                points=100,
                requirements={"level": 10}
            ),
            Achievement(
                id="level_25",
                title="Cleaning Expert",
                description="Reach level 25",
                icon="mdi:trophy",
                type=AchievementType.MILESTONE,
                rarity=AchievementRarity.RARE,
                points=250,
                requirements={"level": 25}
            ),
            
            # Special Achievements
            Achievement(
                id="early_bird",
                title="Early Bird",
                description="Complete tasks before 8 AM",
                icon="mdi:weather-sunrise",
                type=AchievementType.SPECIAL,
                rarity=AchievementRarity.UNCOMMON,
                points=50,
                requirements={"early_morning_tasks": 5}
            ),
            Achievement(
                id="night_owl",
                title="Night Owl",
                description="Complete tasks after 10 PM",
                icon="mdi:weather-night",
                type=AchievementType.SPECIAL,
                rarity=AchievementRarity.UNCOMMON,
                points=50,
                requirements={"late_night_tasks": 5}
            ),
            Achievement(
                id="perfectionist",
                title="Perfectionist",
                description="Complete 10 tasks with perfect scores",
                icon="mdi:diamond-stone",
                type=AchievementType.SPECIAL,
                rarity=AchievementRarity.EPIC,
                points=200,
                requirements={"perfect_tasks": 10},
                hidden=True
            ),

            # Privacy-related achievements
            Achievement(
                id="privacy_advocate",
                title="Privacy Advocate",
                description="Enable privacy-first settings",
                icon="mdi:shield-check",
                type=AchievementType.PRIVACY,
                rarity=AchievementRarity.UNCOMMON,
                points=50,
                requirements={"privacy_enabled": True}
            ),
            Achievement(
                id="local_hero",
                title="Local Hero",
                description="Complete 50 tasks with local processing only",
                icon="mdi:home-lock",
                type=AchievementType.PRIVACY,
                rarity=AchievementRarity.RARE,
                points=150,
                requirements={"local_tasks": 50}
            ),
            Achievement(
                id="data_minimalist",
                title="Data Minimalist",
                description="Use minimal data retention settings for 30 days",
                icon="mdi:database-minus",
                type=AchievementType.PRIVACY,
                rarity=AchievementRarity.EPIC,
                points=250,
                requirements={"minimal_data_days": 30}
            )
        ]
        
        self.achievements = default_achievements
        self._save_achievements()
        self.logger.info(f"Initialized {len(default_achievements)} default achievements")

    def record_task_completion(self, zone_name: str, task_description: str,
                             completion_time: datetime, task_score: float = 1.0):
        """
        Record a task completion and update gamification stats with HA integration

        Args:
            zone_name: Name of the zone (anonymized if privacy enabled)
            task_description: Description of the completed task
            completion_time: When the task was completed
            task_score: Quality score of the task (0.0-1.0)
        """
        # Anonymize zone name if privacy enabled
        display_zone = self._anonymize_zone_name(zone_name) if self.privacy_settings.anonymize_zone_names else zone_name

        # Update basic stats
        self.user_stats.total_tasks_completed += 1
        self.user_stats.last_activity_date = completion_time.isoformat()

        # Update streak
        old_streak = self.user_stats.current_streak
        self._update_streak(completion_time)
        streak_improved = self.user_stats.current_streak > old_streak

        # Award experience points
        base_points = 10
        quality_bonus = int(task_score * 10)
        streak_bonus = min(self.user_stats.current_streak * 2, 20)
        privacy_bonus = 5 if self.privacy_settings.privacy_level != PrivacyLevel.MINIMAL else 0
        total_points = base_points + quality_bonus + streak_bonus + privacy_bonus

        old_level = self.user_stats.level
        self._award_experience(total_points)
        level_up = self.user_stats.level > old_level

        # Check for achievements
        newly_unlocked = self._check_achievements(completion_time, task_score)

        # Update daily challenges
        challenge_completed = self._update_daily_challenges()

        # Update Home Assistant entities
        self._update_ha_entities_after_task(level_up, streak_improved, newly_unlocked, challenge_completed)

        # Save data
        self._save_user_stats()

        # Log with privacy protection
        if self.privacy_settings.store_detailed_timestamps:
            self.logger.debug(f"Task completion recorded: {display_zone} - {task_description}")
        else:
            self.logger.debug(f"Task completion recorded for zone: {display_zone}")

    def _anonymize_zone_name(self, zone_name: str) -> str:
        """Create anonymized zone identifier"""
        if not self.privacy_settings.anonymize_zone_names:
            return zone_name
        hash_object = hashlib.sha256(zone_name.encode())
        return f"Zone_{hash_object.hexdigest()[:6]}"

    def _update_ha_entities_after_task(self, level_up: bool, streak_improved: bool,
                                     newly_unlocked: List, challenge_completed: bool):
        """Update Home Assistant entities after task completion"""
        if not self.privacy_settings.share_with_ha:
            return

        # Update core stats
        self._update_ha_entity("sensor.aicleaner_level", self.user_stats.level, {
            "friendly_name": "AICleaner Level",
            "icon": "mdi:star-outline",
            "level_up": level_up
        })

        self._update_ha_entity("sensor.aicleaner_experience", self.user_stats.experience, {
            "friendly_name": "AICleaner Experience Points",
            "total_points": self.user_stats.total_points,
            "icon": "mdi:trophy"
        })

        self._update_ha_entity("sensor.aicleaner_streak", self.user_stats.current_streak, {
            "friendly_name": "AICleaner Cleaning Streak",
            "longest_streak": self.user_stats.longest_streak,
            "streak_improved": streak_improved,
            "icon": "mdi:fire" if self.user_stats.current_streak > 0 else "mdi:fire-off"
        })

        self._update_ha_entity("sensor.aicleaner_achievements", self.user_stats.achievements_unlocked, {
            "friendly_name": "AICleaner Achievements Unlocked",
            "newly_unlocked": len(newly_unlocked),
            "recent_achievements": [a.title for a in newly_unlocked[-3:]] if newly_unlocked else [],
            "icon": "mdi:medal"
        })

        self._update_ha_entity("binary_sensor.aicleaner_daily_challenge", challenge_completed, {
            "friendly_name": "AICleaner Daily Challenge Complete",
            "device_class": "connectivity",
            "icon": "mdi:calendar-check" if challenge_completed else "mdi:calendar-clock"
        })

    def _update_streak(self, completion_time: datetime):
        """Update the user's streak based on completion time"""
        if not self.user_stats.last_activity_date:
            self.user_stats.current_streak = 1
            return

        last_activity = datetime.fromisoformat(self.user_stats.last_activity_date.replace('Z', '+00:00'))
        days_since_last = (completion_time.date() - last_activity.date()).days

        if days_since_last == 0:
            # Same day, streak continues
            pass
        elif days_since_last == 1:
            # Next day, increment streak
            self.user_stats.current_streak += 1
            if self.user_stats.current_streak > self.user_stats.longest_streak:
                self.user_stats.longest_streak = self.user_stats.current_streak
        else:
            # Streak broken
            self.user_stats.current_streak = 1

    def _award_experience(self, points: int):
        """Award experience points and handle leveling up"""
        self.user_stats.experience += points
        self.user_stats.total_points += points

        # Calculate level (100 XP per level, with increasing requirements)
        required_xp = 0
        level = 1

        while required_xp <= self.user_stats.experience:
            level += 1
            required_xp += level * 100  # Increasing XP requirement per level

        old_level = self.user_stats.level
        self.user_stats.level = level - 1

        # Check for level-up achievements
        if self.user_stats.level > old_level:
            self.logger.info(f"User leveled up to level {self.user_stats.level}")
            self._check_level_achievements()

    def _check_achievements(self, completion_time: datetime, task_score: float):
        """Check and unlock achievements based on current stats"""
        newly_unlocked = []

        for achievement in self.achievements:
            if achievement.unlocked:
                continue

            # Update progress and check if unlocked
            progress = self._calculate_achievement_progress(achievement)
            achievement.progress = progress

            if progress >= 1.0:
                achievement.unlocked = True
                achievement.unlocked_date = completion_time.isoformat()
                self.user_stats.achievements_unlocked += 1
                self.user_stats.total_points += achievement.points
                newly_unlocked.append(achievement)

                self.logger.info(f"Achievement unlocked: {achievement.title}")

        if newly_unlocked:
            self._save_achievements()

        return newly_unlocked

    def _calculate_achievement_progress(self, achievement: Achievement) -> float:
        """Calculate progress towards an achievement"""
        requirements = achievement.requirements

        if achievement.type == AchievementType.TASK_COMPLETION:
            required = requirements.get('tasks_completed', 1)
            return min(1.0, self.user_stats.total_tasks_completed / required)

        elif achievement.type == AchievementType.STREAK:
            required = requirements.get('streak_days', 1)
            return min(1.0, self.user_stats.current_streak / required)

        elif achievement.type == AchievementType.EFFICIENCY:
            required = requirements.get('efficiency_score', 1.0)
            return min(1.0, self.user_stats.efficiency_score / required)

        elif achievement.type == AchievementType.MILESTONE:
            required = requirements.get('level', 1)
            return min(1.0, self.user_stats.level / required)

        elif achievement.type == AchievementType.SPECIAL:
            # Special achievements have custom logic
            if 'perfect_tasks' in requirements:
                # This would need to be tracked separately
                return 0.0  # Placeholder
            elif 'early_morning_tasks' in requirements:
                # This would need to be tracked separately
                return 0.0  # Placeholder
            elif 'late_night_tasks' in requirements:
                # This would need to be tracked separately
                return 0.0  # Placeholder

        return 0.0

    def _check_level_achievements(self):
        """Check for level-based achievements"""
        for achievement in self.achievements:
            if (achievement.type == AchievementType.MILESTONE and
                not achievement.unlocked and
                'level' in achievement.requirements):

                required_level = achievement.requirements['level']
                if self.user_stats.level >= required_level:
                    achievement.unlocked = True
                    achievement.unlocked_date = datetime.now(timezone.utc).isoformat()
                    achievement.progress = 1.0
                    self.user_stats.achievements_unlocked += 1
                    self.user_stats.total_points += achievement.points

                    self.logger.info(f"Level achievement unlocked: {achievement.title}")

    def _update_daily_challenges(self) -> bool:
        """Update progress on daily challenges and return if any completed"""
        today = datetime.now(timezone.utc).date().isoformat()
        challenge_completed = False

        # Create today's challenge if it doesn't exist
        if not any(challenge.date == today for challenge in self.daily_challenges):
            self._generate_daily_challenge(today)

        # Update progress on today's challenges
        for challenge in self.daily_challenges:
            if challenge.date == today and not challenge.completed:
                if challenge.challenge_type == "task_completion":
                    challenge.current_progress = min(challenge.target,
                                                   self.user_stats.total_tasks_completed)
                    if challenge.current_progress >= challenge.target:
                        challenge.completed = True
                        challenge_completed = True
                        self.user_stats.total_points += challenge.points_reward
                        self.logger.info(f"Daily challenge completed: {challenge.title}")

        # Clean up old challenges (keep last 7 days)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        self.daily_challenges = [c for c in self.daily_challenges if c.date >= cutoff_date]

        self._save_daily_challenges()
        return challenge_completed

    def _generate_daily_challenge(self, date: str):
        """Generate a daily challenge for the given date"""
        import random

        challenges = [
            {
                "title": "Daily Cleaner",
                "description": "Complete 3 cleaning tasks today",
                "icon": "mdi:broom",
                "target": 3,
                "points_reward": 30,
                "challenge_type": "task_completion"
            },
            {
                "title": "Zone Master",
                "description": "Clean 2 different zones today",
                "icon": "mdi:home-variant",
                "target": 2,
                "points_reward": 25,
                "challenge_type": "zone_completion"
            },
            {
                "title": "Speed Cleaner",
                "description": "Complete 5 tasks today",
                "icon": "mdi:timer",
                "target": 5,
                "points_reward": 50,
                "challenge_type": "task_completion"
            }
        ]

        challenge_template = random.choice(challenges)
        challenge = DailyChallenge(
            id=f"daily_{date}",
            date=date,
            current_progress=0,
            **challenge_template
        )

        self.daily_challenges.append(challenge)
        self.logger.info(f"Generated daily challenge: {challenge.title}")

    def get_user_stats(self) -> Dict[str, Any]:
        """Get current user statistics"""
        return asdict(self.user_stats)

    def get_achievements(self, include_locked: bool = True) -> List[Dict[str, Any]]:
        """
        Get achievements list

        Args:
            include_locked: Whether to include locked achievements

        Returns:
            List of achievements
        """
        achievements = []
        for achievement in self.achievements:
            if not include_locked and not achievement.unlocked and achievement.hidden:
                continue

            achievement_dict = asdict(achievement)
            achievement_dict['type'] = achievement.type.value
            achievement_dict['rarity'] = achievement.rarity.value
            achievements.append(achievement_dict)

        return achievements

    def get_daily_challenges(self) -> List[Dict[str, Any]]:
        """Get current daily challenges"""
        today = datetime.now(timezone.utc).date().isoformat()
        return [asdict(challenge) for challenge in self.daily_challenges
                if challenge.date == today]

    def get_leaderboard_data(self) -> Dict[str, Any]:
        """Get leaderboard data for the user"""
        # In a multi-user system, this would compare with other users
        # For now, return personal best data
        return {
            'current_level': self.user_stats.level,
            'total_points': self.user_stats.total_points,
            'achievements_count': self.user_stats.achievements_unlocked,
            'longest_streak': self.user_stats.longest_streak,
            'total_tasks': self.user_stats.total_tasks_completed,
            'efficiency_score': self.user_stats.efficiency_score,
            'rank': 1,  # Placeholder for single user
            'percentile': 100  # Placeholder for single user
        }

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get progress summary for dashboard"""
        # Calculate next level progress
        current_level_xp = sum(i * 100 for i in range(1, self.user_stats.level + 1))
        next_level_xp = current_level_xp + (self.user_stats.level + 1) * 100
        level_progress = (self.user_stats.experience - current_level_xp) / ((self.user_stats.level + 1) * 100)

        # Get recent achievements
        recent_achievements = [
            achievement for achievement in self.achievements
            if achievement.unlocked and achievement.unlocked_date
        ]
        recent_achievements.sort(key=lambda x: x.unlocked_date, reverse=True)
        recent_achievements = recent_achievements[:3]  # Last 3 achievements

        # Get active daily challenges
        daily_challenges = self.get_daily_challenges()

        return {
            'level': self.user_stats.level,
            'level_progress': min(1.0, max(0.0, level_progress)),
            'experience': self.user_stats.experience,
            'next_level_xp': next_level_xp,
            'total_points': self.user_stats.total_points,
            'current_streak': self.user_stats.current_streak,
            'achievements_unlocked': self.user_stats.achievements_unlocked,
            'total_achievements': len(self.achievements),
            'recent_achievements': [asdict(a) for a in recent_achievements],
            'daily_challenges': daily_challenges,
            'efficiency_score': self.user_stats.efficiency_score
        }

    def get_motivational_message(self) -> Dict[str, str]:
        """Get a motivational message based on current progress"""
        import random

        messages = {
            'streak': [
                f"🔥 Amazing! You're on a {self.user_stats.current_streak}-day streak!",
                f"🌟 Keep it up! {self.user_stats.current_streak} days of consistent cleaning!",
                f"💪 Unstoppable! {self.user_stats.current_streak} days and counting!"
            ],
            'level_up': [
                f"🎉 Congratulations! You've reached level {self.user_stats.level}!",
                f"⭐ Level {self.user_stats.level} achieved! You're becoming a cleaning master!",
                f"🏆 Welcome to level {self.user_stats.level}! Your dedication is paying off!"
            ],
            'achievement': [
                "🏅 New achievement unlocked! Check your achievements page!",
                "🎯 You've earned a new badge! Great work!",
                "✨ Achievement earned! You're making excellent progress!"
            ],
            'encouragement': [
                "🌈 Every small step counts towards a cleaner home!",
                "💫 You're doing great! Keep up the momentum!",
                "🌟 Your consistency is inspiring! One task at a time!",
                "🎯 Focus on progress, not perfection!",
                "💪 You've got this! Every clean space makes a difference!"
            ],
            'milestone': [
                f"🎊 Incredible! You've completed {self.user_stats.total_tasks_completed} tasks!",
                f"🏆 {self.user_stats.total_points} points earned! You're a cleaning champion!",
                f"⭐ {self.user_stats.achievements_unlocked} achievements unlocked! Amazing progress!"
            ]
        }

        # Choose message type based on current state
        if self.user_stats.current_streak >= 7:
            message_type = 'streak'
        elif self.user_stats.level >= 10:
            message_type = 'milestone'
        elif self.user_stats.achievements_unlocked > 0:
            message_type = 'achievement'
        else:
            message_type = 'encouragement'

        message = random.choice(messages[message_type])

        return {
            'message': message,
            'type': message_type,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def reset_daily_progress(self):
        """Reset daily progress (called at midnight)"""
        # This would be called by a scheduler
        today = datetime.now(timezone.utc).date().isoformat()

        # Generate new daily challenge
        if not any(challenge.date == today for challenge in self.daily_challenges):
            self._generate_daily_challenge(today)

        self.logger.info("Daily progress reset and new challenges generated")

    def export_gamification_data(self) -> Dict[str, Any]:
        """Export complete gamification data"""
        return {
            'user_stats': asdict(self.user_stats),
            'achievements': self.get_achievements(include_locked=True),
            'daily_challenges': [asdict(challenge) for challenge in self.daily_challenges],
            'leaderboard': self.get_leaderboard_data(),
            'progress_summary': self.get_progress_summary(),
            'motivational_message': self.get_motivational_message(),
            'system_info': {
                'total_achievements_available': len(self.achievements),
                'achievement_types': list(set(a.type.value for a in self.achievements)),
                'rarity_levels': list(set(a.rarity.value for a in self.achievements)),
                'data_path': self.data_path,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        }

    def update_privacy_settings(self, new_settings: PrivacySettings):
        """Update privacy settings and apply changes"""
        old_level = self.privacy_settings.privacy_level
        self.privacy_settings = new_settings

        # Award privacy achievement if privacy level increased
        if new_settings.privacy_level.value > old_level.value:
            self.user_stats.privacy_score += 25
            self._check_privacy_achievements()

        # Update HA integration based on new settings
        if new_settings.share_with_ha != (old_level != PrivacyLevel.MINIMAL):
            self._initialize_ha_entities()

        self.logger.info(f"Privacy settings updated to level: {new_settings.privacy_level.value}")

    def _check_privacy_achievements(self):
        """Check for privacy-related achievements"""
        for achievement in self.achievements:
            if achievement.type == AchievementType.PRIVACY and not achievement.unlocked:
                if achievement.id == "privacy_advocate" and self.privacy_settings.privacy_level != PrivacyLevel.MINIMAL:
                    achievement.unlocked = True
                    achievement.unlocked_date = datetime.now(timezone.utc).isoformat()
                    self.user_stats.achievements_unlocked += 1
                    self.user_stats.total_points += achievement.points
                    self.logger.info(f"Privacy achievement unlocked: {achievement.title}")

    def get_enhanced_motivational_message(self) -> Dict[str, Any]:
        """Get enhanced motivational message with personalization"""
        import random

        # Analyze user patterns for personalized messages
        time_of_day = datetime.now().hour
        is_weekend = datetime.now().weekday() >= 5
        streak = self.user_stats.current_streak
        level = self.user_stats.level

        # Personalized message categories
        if streak >= 7:
            category = "streak_master"
            messages = [
                f"🔥 Incredible! {streak} days of consistent cleaning! You're unstoppable!",
                f"⭐ {streak}-day streak! You've built an amazing habit!",
                f"🏆 {streak} days strong! Your dedication is truly inspiring!"
            ]
        elif level >= 20:
            category = "expert"
            messages = [
                f"🌟 Level {level} expert! Your cleaning mastery is evident!",
                f"💎 At level {level}, you're a true cleaning professional!",
                f"🎯 Level {level} achieved! Your skills are exceptional!"
            ]
        elif time_of_day < 9:
            category = "morning_motivation"
            messages = [
                "🌅 Good morning! Starting the day with cleaning sets a positive tone!",
                "☀️ Early bird! Morning cleaning gives you energy for the whole day!",
                "🌈 Fresh start! Your morning cleaning routine is building great habits!"
            ]
        elif time_of_day > 20:
            category = "evening_encouragement"
            messages = [
                "🌙 Evening cleaning! Ending the day organized feels so satisfying!",
                "✨ Night owl! Your dedication to cleanliness is admirable!",
                "🌟 Late-night cleaning! Tomorrow you'll wake up to a fresh space!"
            ]
        elif is_weekend:
            category = "weekend_warrior"
            messages = [
                "🎉 Weekend cleaning warrior! Making the most of your free time!",
                "🏠 Weekend vibes! Your home will thank you for this attention!",
                "💪 Weekend dedication! You're building lasting habits!"
            ]
        else:
            category = "general_encouragement"
            messages = [
                "🌟 Every task completed makes a difference!",
                "💫 Your consistency is building something beautiful!",
                "🎯 Progress over perfection - you're doing great!",
                "🌈 Small steps lead to big transformations!",
                "💪 Your cleaning journey is inspiring!"
            ]

        message = random.choice(messages)

        # Add achievement hints
        hints = []
        for achievement in self.achievements:
            if not achievement.unlocked and not achievement.hidden:
                progress = self._calculate_achievement_progress(achievement)
                if 0.7 <= progress < 1.0:
                    hints.append(f"Almost there! {achievement.title}: {int(progress * 100)}% complete")

        return {
            'message': message,
            'category': category,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'personalization': {
                'time_of_day': time_of_day,
                'is_weekend': is_weekend,
                'current_streak': streak,
                'current_level': level
            },
            'achievement_hints': hints[:2],  # Show max 2 hints
            'privacy_level': self.privacy_settings.privacy_level.value
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Get gamification system status with privacy information"""
        return {
            'user_stats_loaded': bool(self.user_stats),
            'achievements_loaded': len(self.achievements),
            'daily_challenges_active': len(self.get_daily_challenges()),
            'current_level': self.user_stats.level,
            'total_points': self.user_stats.total_points,
            'achievements_unlocked': self.user_stats.achievements_unlocked,
            'current_streak': self.user_stats.current_streak,
            'privacy_level': self.privacy_settings.privacy_level.value,
            'ha_integration_enabled': self.privacy_settings.share_with_ha,
            'ha_entities_count': len(self.ha_entities),
            'data_path': self.data_path,
            'system_health': 'healthy'
        }

    def get_privacy_dashboard(self) -> Dict[str, Any]:
        """Get privacy dashboard information"""
        return {
            'privacy_settings': asdict(self.privacy_settings),
            'data_summary': {
                'local_storage_only': True,
                'anonymized_zones': self.privacy_settings.anonymize_zone_names,
                'detailed_timestamps': self.privacy_settings.store_detailed_timestamps,
                'ha_integration': self.privacy_settings.share_with_ha
            },
            'privacy_achievements': [
                asdict(a) for a in self.achievements
                if a.type == AchievementType.PRIVACY
            ],
            'privacy_score': self.user_stats.privacy_score,
            'data_retention_days': self.privacy_settings.data_retention_days,
            'compliance': {
                'gdpr_ready': True,
                'local_processing': True,
                'user_control': True,
                'data_minimization': True
            }
        }
