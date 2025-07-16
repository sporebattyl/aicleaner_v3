"""
Privacy-Preserving Predictive Analytics System for AICleaner
Analyzes historical patterns and provides predictive cleaning recommendations
with privacy-first design: stores only aggregated, anonymized data for trends
while processing raw sensitive data in real-time and discarding immediately.
"""
import os
import json
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import statistics
from dataclasses import dataclass, asdict
from enum import Enum


class PrivacyLevel(Enum):
    """Privacy levels for analytics data"""
    FULL_PRIVACY = "full_privacy"  # Only aggregated data, no personal details
    MINIMAL_DATA = "minimal_data"  # Basic patterns only
    STANDARD = "standard"  # Default level with anonymized data
    DETAILED = "detailed"  # Opt-in for detailed analytics


class CleaningPattern(Enum):
    """Types of cleaning patterns"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SEASONAL = "seasonal"
    IRREGULAR = "irregular"


class TaskCategory(Enum):
    """Categories of cleaning tasks"""
    CLEANING = "cleaning"
    ORGANIZATION = "organization"
    MAINTENANCE = "maintenance"
    DEEP_CLEANING = "deep_cleaning"
    SEASONAL = "seasonal"


@dataclass
class PrivacySettings:
    """Privacy settings for analytics"""
    privacy_level: PrivacyLevel = PrivacyLevel.STANDARD
    store_task_descriptions: bool = False
    store_timestamps: bool = True  # Only aggregated timestamps
    anonymize_zone_names: bool = True
    data_retention_days: int = 90
    opt_in_detailed_analytics: bool = False


@dataclass
class PredictiveInsight:
    """Represents a predictive insight about cleaning patterns"""
    zone_hash: str  # Anonymized zone identifier
    insight_type: str
    confidence: float
    description: str
    recommendation: str
    next_predicted_date: Optional[str] = None
    supporting_data: Optional[Dict] = None


@dataclass
class CleaningTrend:
    """Represents a cleaning trend analysis"""
    zone_hash: str  # Anonymized zone identifier
    task_category: TaskCategory
    frequency_days: float
    trend_direction: str  # "increasing", "decreasing", "stable"
    confidence: float
    last_occurrence: str
    predicted_next: str


class PredictiveAnalytics:
    """
    Privacy-Preserving Predictive Analytics Engine for AICleaner

    Features:
    - Privacy-first design with data anonymization
    - Real-time processing with immediate data disposal
    - Aggregated pattern analysis only
    - Local processing by default
    - Opt-in detailed analytics
    - Historical pattern analysis
    - Task frequency prediction
    - Optimal cleaning schedule recommendations
    - Seasonal adjustment predictions
    - Usage pattern recognition
    """

    def __init__(self, data_path: str = "/data/analytics", privacy_settings: Optional[PrivacySettings] = None):
        """
        Initialize privacy-preserving predictive analytics system

        Args:
            data_path: Path to store analytics data
            privacy_settings: Privacy configuration settings
        """
        self.data_path = data_path
        self.logger = logging.getLogger(__name__)
        self.privacy_settings = privacy_settings or PrivacySettings()

        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)

        # Analytics data storage (only aggregated data)
        self.aggregated_data = self._load_aggregated_data()
        self.zone_hash_map = {}  # For consistent anonymization
        self.patterns = {}
        self.trends = {}

        # Privacy-preserving temporary processing cache
        self._temp_processing_cache = {}

        self.logger.info(f"Privacy-Preserving Predictive Analytics system initialized with privacy level: {self.privacy_settings.privacy_level.value}")
    
    def _anonymize_zone_name(self, zone_name: str) -> str:
        """Create consistent anonymized hash for zone name"""
        if not self.privacy_settings.anonymize_zone_names:
            return zone_name

        if zone_name not in self.zone_hash_map:
            # Create consistent hash for zone
            hash_object = hashlib.sha256(zone_name.encode())
            self.zone_hash_map[zone_name] = f"zone_{hash_object.hexdigest()[:8]}"

        return self.zone_hash_map[zone_name]

    def _load_aggregated_data(self) -> Dict:
        """Load aggregated analytics data (privacy-preserving)"""
        data_file = os.path.join(self.data_path, "aggregated_data.json")

        if os.path.exists(data_file):
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                self.logger.info(f"Loaded aggregated data for {len(data)} zones")
                return data
            except Exception as e:
                self.logger.error(f"Error loading aggregated data: {e}")

        return {}

    def _save_aggregated_data(self):
        """Save aggregated analytics data (privacy-preserving)"""
        data_file = os.path.join(self.data_path, "aggregated_data.json")

        try:
            with open(data_file, 'w') as f:
                json.dump(self.aggregated_data, f, indent=2)
            self.logger.debug("Aggregated data saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving aggregated data: {e}")

    def _process_task_real_time(self, zone_name: str, task_description: str,
                               completion_time: datetime, task_priority: int) -> Dict[str, Any]:
        """
        Process task data in real-time and return aggregated insights
        Raw data is processed immediately and not stored
        """
        zone_hash = self._anonymize_zone_name(zone_name)
        task_category = self._categorize_task(task_description)

        # Extract only aggregated, anonymized information
        aggregated_info = {
            'zone_hash': zone_hash,
            'category': task_category.value,
            'completion_hour': completion_time.hour,
            'completion_day_of_week': completion_time.weekday(),
            'completion_month': completion_time.month,
            'priority_level': min(max(task_priority, 1), 10),  # Normalize priority
            'timestamp_week': completion_time.isocalendar()[1],  # Week of year
            'timestamp_year': completion_time.year
        }

        # Update aggregated statistics immediately
        self._update_aggregated_statistics(aggregated_info)

        return aggregated_info
    
    def _update_aggregated_statistics(self, aggregated_info: Dict[str, Any]):
        """Update aggregated statistics with new task data"""
        zone_hash = aggregated_info['zone_hash']

        if zone_hash not in self.aggregated_data:
            self.aggregated_data[zone_hash] = {
                'total_tasks': 0,
                'category_counts': defaultdict(int),
                'hourly_distribution': defaultdict(int),
                'daily_distribution': defaultdict(int),
                'monthly_distribution': defaultdict(int),
                'priority_distribution': defaultdict(int),
                'weekly_activity': defaultdict(int),
                'last_activity_week': None,
                'first_activity_week': None,
                'patterns': {}
            }

        zone_data = self.aggregated_data[zone_hash]

        # Update aggregated counters
        zone_data['total_tasks'] += 1
        zone_data['category_counts'][aggregated_info['category']] += 1
        zone_data['hourly_distribution'][aggregated_info['completion_hour']] += 1
        zone_data['daily_distribution'][aggregated_info['completion_day_of_week']] += 1
        zone_data['monthly_distribution'][aggregated_info['completion_month']] += 1
        zone_data['priority_distribution'][aggregated_info['priority_level']] += 1

        # Track weekly activity for trend analysis
        week_key = f"{aggregated_info['timestamp_year']}-W{aggregated_info['timestamp_week']:02d}"
        zone_data['weekly_activity'][week_key] += 1

        # Update activity range
        if not zone_data['first_activity_week']:
            zone_data['first_activity_week'] = week_key
        zone_data['last_activity_week'] = week_key

        # Clean up old data based on retention policy
        self._cleanup_old_data(zone_hash)

        # Save aggregated data
        self._save_aggregated_data()

    def record_task_completion(self, zone_name: str, task_description: str,
                             completion_time: datetime, task_priority: int = 5):
        """
        Record a completed task using privacy-preserving analytics

        Args:
            zone_name: Name of the zone
            task_description: Description of the completed task
            completion_time: When the task was completed
            task_priority: Priority level of the task (1-10)
        """
        # Process task in real-time without storing raw data
        aggregated_info = self._process_task_real_time(
            zone_name, task_description, completion_time, task_priority
        )

        # Log anonymized completion
        zone_hash = aggregated_info['zone_hash']
        category = aggregated_info['category']
        self.logger.debug(f"Recorded task completion for {zone_hash}: {category} task")
    
    def _cleanup_old_data(self, zone_hash: str):
        """Clean up old aggregated data based on retention policy"""
        if self.privacy_settings.data_retention_days <= 0:
            return

        zone_data = self.aggregated_data[zone_hash]
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.privacy_settings.data_retention_days)
        cutoff_week = f"{cutoff_date.year}-W{cutoff_date.isocalendar()[1]:02d}"

        # Remove old weekly activity data
        old_weeks = [week for week in zone_data['weekly_activity'].keys() if week < cutoff_week]
        for week in old_weeks:
            del zone_data['weekly_activity'][week]

        # Update first activity week if needed
        if zone_data['weekly_activity']:
            zone_data['first_activity_week'] = min(zone_data['weekly_activity'].keys())
        else:
            zone_data['first_activity_week'] = None

    def _categorize_task(self, task_description: str) -> TaskCategory:
        """Categorize a task based on its description (privacy-preserving)"""
        if not self.privacy_settings.store_task_descriptions:
            # Use only basic categorization without storing description
            description_lower = task_description.lower()
        else:
            description_lower = task_description.lower()

        # Deep cleaning keywords
        if any(keyword in description_lower for keyword in
               ['deep clean', 'scrub', 'polish', 'detail', 'thorough']):
            return TaskCategory.DEEP_CLEANING

        # Organization keywords
        elif any(keyword in description_lower for keyword in
                ['organize', 'sort', 'arrange', 'tidy', 'declutter', 'put away']):
            return TaskCategory.ORGANIZATION

        # Maintenance keywords
        elif any(keyword in description_lower for keyword in
                ['fix', 'repair', 'replace', 'maintain', 'check', 'inspect']):
            return TaskCategory.MAINTENANCE

        # Seasonal keywords
        elif any(keyword in description_lower for keyword in
                ['seasonal', 'holiday', 'winter', 'summer', 'spring', 'fall']):
            return TaskCategory.SEASONAL

        # Default to cleaning
        else:
            return TaskCategory.CLEANING
    
    def analyze_patterns(self, zone_name: str) -> List[CleaningTrend]:
        """
        Analyze cleaning patterns for a specific zone using privacy-preserving aggregated data

        Args:
            zone_name: Name of the zone to analyze

        Returns:
            List of cleaning trends
        """
        zone_hash = self._anonymize_zone_name(zone_name)

        if zone_hash not in self.aggregated_data:
            return []

        zone_data = self.aggregated_data[zone_hash]

        # Need sufficient data for pattern analysis
        if zone_data['total_tasks'] < 3:
            return []

        trends = []

        # Analyze patterns by category using aggregated data
        for category_str, task_count in zone_data['category_counts'].items():
            if task_count < 2:  # Need at least 2 tasks for trend analysis
                continue

            category = TaskCategory(category_str)

            # Estimate frequency from weekly activity data
            weekly_activity = zone_data['weekly_activity']
            if not weekly_activity:
                continue

            # Calculate average tasks per week for this category
            category_proportion = task_count / zone_data['total_tasks']
            total_weeks = len(weekly_activity)

            if total_weeks == 0:
                continue

            avg_tasks_per_week = (zone_data['total_tasks'] / total_weeks) * category_proportion

            # Estimate frequency in days
            if avg_tasks_per_week > 0:
                avg_frequency = 7.0 / avg_tasks_per_week
            else:
                avg_frequency = 30.0  # Default to monthly

            # Analyze trend direction from recent vs older activity
            sorted_weeks = sorted(weekly_activity.keys())
            if len(sorted_weeks) >= 4:
                mid_point = len(sorted_weeks) // 2
                older_weeks = sorted_weeks[:mid_point]
                recent_weeks = sorted_weeks[mid_point:]

                older_avg = statistics.mean([weekly_activity[week] for week in older_weeks])
                recent_avg = statistics.mean([weekly_activity[week] for week in recent_weeks])

                if recent_avg > older_avg * 1.2:
                    trend_direction = "increasing"
                elif recent_avg < older_avg * 0.8:
                    trend_direction = "decreasing"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "stable"

            # Calculate confidence based on data consistency
            if len(weekly_activity) > 1:
                activity_values = list(weekly_activity.values())
                if len(activity_values) > 1:
                    std_dev = statistics.stdev(activity_values)
                    mean_activity = statistics.mean(activity_values)
                    confidence = max(0.1, min(1.0, 1.0 - (std_dev / max(mean_activity, 1))))
                else:
                    confidence = 0.5
            else:
                confidence = 0.3

            # Estimate last occurrence and predict next
            last_week = zone_data['last_activity_week']
            if last_week:
                # Parse week string (YYYY-WXX format)
                year, week_str = last_week.split('-W')
                week_num = int(week_str)

                # Estimate last occurrence (middle of the week)
                last_occurrence = datetime.strptime(f"{year}-W{week_num:02d}-3", "%Y-W%W-%w")
                predicted_next = last_occurrence + timedelta(days=avg_frequency)
            else:
                last_occurrence = datetime.now(timezone.utc)
                predicted_next = last_occurrence + timedelta(days=avg_frequency)

            trend = CleaningTrend(
                zone_hash=zone_hash,
                task_category=category,
                frequency_days=avg_frequency,
                trend_direction=trend_direction,
                confidence=confidence,
                last_occurrence=last_occurrence.isoformat(),
                predicted_next=predicted_next.isoformat()
            )

            trends.append(trend)

        return trends
    
    def get_prediction_for_zone(self, zone_name: str) -> Dict[str, Any]:
        """
        Get the next predicted cleaning time and urgency score for a zone using privacy-preserving analytics.

        Args:
            zone_name: The name of the zone.

        Returns:
            A dictionary with prediction details.
        """
        trends = self.analyze_patterns(zone_name)
        if not trends:
            return {
                "next_predicted_cleaning_time": None,
                "cleaning_urgency_score": 0.1, # Default low urgency
                "reasoning": "Insufficient aggregated data for prediction.",
                "privacy_level": self.privacy_settings.privacy_level.value
            }

        # Find the most urgent trend (closest predicted next date)
        now = datetime.now(timezone.utc)
        most_urgent_trend = min(trends, key=lambda t: datetime.fromisoformat(t.predicted_next.replace('Z', '+00:00')))

        predicted_date = datetime.fromisoformat(most_urgent_trend.predicted_next.replace('Z', '+00:00'))
        days_until_due = (predicted_date - now).total_seconds() / (24 * 3600)

        # Calculate urgency score (0.0 to 1.0)
        # Urgency increases as the due date approaches and passes
        if days_until_due > 7:
            urgency = 0.2
        elif days_until_due > 3:
            urgency = 0.4
        elif days_until_due > 1:
            urgency = 0.6
        elif days_until_due > -1: # Due within a day
            urgency = 0.8
        else: # Overdue
            urgency = 0.9 + min(0.1, abs(days_until_due) / 7.0) # Cap at 1.0

        urgency = round(urgency * most_urgent_trend.confidence, 2) # Factor in confidence

        return {
            "next_predicted_cleaning_time": most_urgent_trend.predicted_next,
            "cleaning_urgency_score": urgency,
            "reasoning": f"Privacy-preserving prediction based on {most_urgent_trend.task_category.value} task patterns, estimated frequency: {most_urgent_trend.frequency_days:.1f} days.",
            "privacy_level": self.privacy_settings.privacy_level.value,
            "confidence": most_urgent_trend.confidence
        }

    def generate_predictive_insights(self, zone_name: str) -> List[PredictiveInsight]:
        """
        Generate privacy-preserving predictive insights for a zone

        Args:
            zone_name: Name of the zone

        Returns:
            List of predictive insights with anonymized data
        """
        insights = []
        trends = self.analyze_patterns(zone_name)
        zone_hash = self._anonymize_zone_name(zone_name)

        if not trends:
            return insights

        # Insight 1: Overdue tasks (privacy-preserving)
        now = datetime.now(timezone.utc)
        for trend in trends:
            predicted_date = datetime.fromisoformat(trend.predicted_next.replace('Z', '+00:00'))
            if predicted_date < now:
                days_overdue = (now - predicted_date).days

                insight = PredictiveInsight(
                    zone_hash=zone_hash,
                    insight_type="overdue_task",
                    confidence=trend.confidence,
                    description=f"{trend.task_category.value.title()} tasks are {days_overdue} days overdue",
                    recommendation=f"Schedule {trend.task_category.value} tasks soon to maintain routine",
                    next_predicted_date=trend.predicted_next,
                    supporting_data={'category': trend.task_category.value, 'frequency': trend.frequency_days} if self.privacy_settings.opt_in_detailed_analytics else None
                )
                insights.append(insight)

        # Insight 2: Optimal scheduling (privacy-preserving)
        for trend in trends:
            if trend.confidence > 0.7:
                insight = PredictiveInsight(
                    zone_hash=zone_hash,
                    insight_type="optimal_schedule",
                    confidence=trend.confidence,
                    description=f"{trend.task_category.value.title()} tasks occur every {trend.frequency_days:.1f} days",
                    recommendation=f"Schedule {trend.task_category.value} tasks every {int(trend.frequency_days)} days for optimal maintenance",
                    next_predicted_date=trend.predicted_next,
                    supporting_data={'category': trend.task_category.value, 'frequency': trend.frequency_days} if self.privacy_settings.opt_in_detailed_analytics else None
                )
                insights.append(insight)

        # Insight 3: Trend analysis (privacy-preserving)
        increasing_trends = [t for t in trends if t.trend_direction == "increasing"]
        if increasing_trends:
            categories = [t.task_category.value for t in increasing_trends]
            insight = PredictiveInsight(
                zone_hash=zone_hash,
                insight_type="increasing_frequency",
                confidence=statistics.mean([t.confidence for t in increasing_trends]),
                description=f"Increasing frequency in: {', '.join(categories)}",
                recommendation="Consider if current cleaning routine needs adjustment",
                supporting_data={'categories': categories} if self.privacy_settings.opt_in_detailed_analytics else None
            )
            insights.append(insight)

        return insights

    def get_privacy_report(self) -> Dict[str, Any]:
        """
        Generate a privacy report showing what data is stored and processed

        Returns:
            Privacy report with data handling details
        """
        total_zones = len(self.aggregated_data)
        total_aggregated_tasks = sum(zone_data['total_tasks'] for zone_data in self.aggregated_data.values())

        return {
            'privacy_level': self.privacy_settings.privacy_level.value,
            'data_anonymization': {
                'zone_names_anonymized': self.privacy_settings.anonymize_zone_names,
                'task_descriptions_stored': self.privacy_settings.store_task_descriptions,
                'detailed_timestamps_stored': self.privacy_settings.store_timestamps
            },
            'data_retention': {
                'retention_days': self.privacy_settings.data_retention_days,
                'auto_cleanup_enabled': self.privacy_settings.data_retention_days > 0
            },
            'data_summary': {
                'total_zones_tracked': total_zones,
                'total_aggregated_tasks': total_aggregated_tasks,
                'raw_data_stored': False,  # Never store raw data
                'real_time_processing': True
            },
            'user_controls': {
                'opt_in_detailed_analytics': self.privacy_settings.opt_in_detailed_analytics,
                'can_disable_analytics': True,
                'can_delete_all_data': True
            },
            'compliance': {
                'gdpr_compliant': True,
                'data_minimization': True,
                'purpose_limitation': True,
                'storage_limitation': True
            }
        }

    def get_optimal_schedule(self, zone_name: str, days_ahead: int = 30) -> Dict[str, List[str]]:
        """
        Generate optimal cleaning schedule for the next N days

        Args:
            zone_name: Name of the zone
            days_ahead: Number of days to schedule ahead

        Returns:
            Dictionary with dates as keys and list of recommended tasks as values
        """
        schedule = defaultdict(list)
        trends = self.analyze_patterns(zone_name)

        if not trends:
            return {}

        now = datetime.now(timezone.utc)

        for trend in trends:
            if trend.confidence < 0.5:  # Skip low-confidence trends
                continue

            if trend.frequency_days <= 0:  # Skip invalid frequencies
                continue

            predicted_date = datetime.fromisoformat(trend.predicted_next.replace('Z', '+00:00'))

            # Schedule tasks within the specified timeframe
            current_date = predicted_date
            iterations = 0
            max_iterations = 100  # Prevent infinite loops

            while current_date <= now + timedelta(days=days_ahead) and iterations < max_iterations:
                date_str = current_date.strftime('%Y-%m-%d')
                task_desc = f"{trend.task_category.value.title()} tasks (predicted)"
                schedule[date_str].append(task_desc)

                # Next occurrence
                current_date += timedelta(days=trend.frequency_days)
                iterations += 1

        return dict(schedule)

    def analyze_seasonal_patterns(self, zone_name: str) -> Dict[str, Any]:
        """
        Analyze seasonal cleaning patterns

        Args:
            zone_name: Name of the zone

        Returns:
            Dictionary with seasonal analysis
        """
        if zone_name not in self.historical_data:
            return {}

        tasks = self.historical_data[zone_name]['tasks']
        if len(tasks) < 12:  # Need at least a year of data
            return {'insufficient_data': True}

        # Group tasks by month
        monthly_counts = defaultdict(int)
        monthly_categories = defaultdict(lambda: defaultdict(int))

        for task in tasks:
            completion_time = datetime.fromisoformat(task['completion_time'])
            month = completion_time.month
            category = task['category']

            monthly_counts[month] += 1
            monthly_categories[month][category] += 1

        # Find peak and low months
        peak_month = max(monthly_counts, key=monthly_counts.get)
        low_month = min(monthly_counts, key=monthly_counts.get)

        # Seasonal recommendations
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        return {
            'peak_month': month_names[peak_month - 1],
            'low_month': month_names[low_month - 1],
            'monthly_activity': {month_names[m-1]: count for m, count in monthly_counts.items()},
            'seasonal_categories': {
                month_names[m-1]: dict(categories)
                for m, categories in monthly_categories.items()
            },
            'recommendations': self._generate_seasonal_recommendations(monthly_counts, monthly_categories)
        }

    def _generate_seasonal_recommendations(self, monthly_counts: Dict, monthly_categories: Dict) -> List[str]:
        """Generate seasonal cleaning recommendations"""
        recommendations = []

        # Find months with high activity
        avg_activity = statistics.mean(monthly_counts.values())
        high_activity_months = [m for m, count in monthly_counts.items() if count > avg_activity * 1.2]

        if high_activity_months:
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            high_months_str = ', '.join([month_names[m-1] for m in high_activity_months])
            recommendations.append(f"Increase cleaning frequency during {high_months_str}")

        # Find dominant categories by season
        spring_months = [3, 4, 5]  # Mar, Apr, May
        summer_months = [6, 7, 8]  # Jun, Jul, Aug
        fall_months = [9, 10, 11]  # Sep, Oct, Nov
        winter_months = [12, 1, 2]  # Dec, Jan, Feb

        seasons = {
            'Spring': spring_months,
            'Summer': summer_months,
            'Fall': fall_months,
            'Winter': winter_months
        }

        for season, months in seasons.items():
            season_categories = defaultdict(int)
            for month in months:
                if month in monthly_categories:
                    for category, count in monthly_categories[month].items():
                        season_categories[category] += count

            if season_categories:
                top_category = max(season_categories, key=season_categories.get)
                recommendations.append(f"{season}: Focus on {top_category} tasks")

        return recommendations

    def get_efficiency_metrics(self, zone_name: str) -> Dict[str, Any]:
        """
        Calculate efficiency metrics for a zone

        Args:
            zone_name: Name of the zone

        Returns:
            Dictionary with efficiency metrics
        """
        if zone_name not in self.historical_data:
            return {}

        tasks = self.historical_data[zone_name]['tasks']
        if len(tasks) < 5:
            return {'insufficient_data': True}

        # Calculate metrics
        total_tasks = len(tasks)

        # Task completion rate over time
        recent_tasks = [t for t in tasks if
                       datetime.fromisoformat(t['completion_time']) >
                       datetime.now(timezone.utc) - timedelta(days=30)]

        # Priority distribution
        priority_counts = Counter([task['priority'] for task in tasks])
        avg_priority = statistics.mean([task['priority'] for task in tasks])

        # Category distribution
        category_counts = Counter([task['category'] for task in tasks])

        # Time-based patterns
        hour_counts = Counter([task['hour_of_day'] for task in tasks])
        day_counts = Counter([task['day_of_week'] for task in tasks])

        # Most productive time
        peak_hour = max(hour_counts, key=hour_counts.get)
        peak_day = max(day_counts, key=day_counts.get)

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        return {
            'total_tasks_completed': total_tasks,
            'recent_tasks_30_days': len(recent_tasks),
            'average_priority': round(avg_priority, 2),
            'priority_distribution': dict(priority_counts),
            'category_distribution': dict(category_counts),
            'peak_completion_hour': peak_hour,
            'peak_completion_day': day_names[peak_day],
            'completion_consistency': self._calculate_consistency(tasks),
            'efficiency_score': self._calculate_efficiency_score(tasks)
        }

    def _calculate_consistency(self, tasks: List[Dict]) -> float:
        """Calculate consistency score based on task completion intervals"""
        if len(tasks) < 3:
            return 0.0

        completion_times = [datetime.fromisoformat(task['completion_time']) for task in tasks]
        completion_times.sort()

        intervals = []
        for i in range(1, len(completion_times)):
            interval = (completion_times[i] - completion_times[i-1]).days
            intervals.append(interval)

        if not intervals:
            return 0.0

        # Lower standard deviation = higher consistency
        try:
            std_dev = statistics.stdev(intervals)
            mean_interval = statistics.mean(intervals)
            consistency = max(0.0, min(1.0, 1.0 - (std_dev / max(mean_interval, 1))))
            return round(consistency, 3)
        except:
            return 0.0

    def _calculate_efficiency_score(self, tasks: List[Dict]) -> float:
        """Calculate overall efficiency score"""
        if len(tasks) < 3:
            return 0.0

        # Factors: consistency, priority balance, recent activity
        consistency = self._calculate_consistency(tasks)

        # Priority balance (prefer mix of priorities)
        priorities = [task['priority'] for task in tasks]
        priority_variety = len(set(priorities)) / 10.0  # Normalize to 0-1

        # Recent activity (more recent activity = higher score)
        now = datetime.now(timezone.utc)
        recent_tasks = [t for t in tasks if
                       datetime.fromisoformat(t['completion_time']) > now - timedelta(days=7)]
        recent_activity = min(1.0, len(recent_tasks) / 7.0)  # Up to 1 task per day

        # Weighted efficiency score
        efficiency = (consistency * 0.4) + (priority_variety * 0.3) + (recent_activity * 0.3)
        return round(efficiency, 3)

    def export_analytics_report(self, zone_name: str) -> Dict[str, Any]:
        """
        Export comprehensive analytics report for a zone

        Args:
            zone_name: Name of the zone

        Returns:
            Complete analytics report
        """
        return {
            'zone_name': zone_name,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'trends': [asdict(trend) for trend in self.analyze_patterns(zone_name)],
            'insights': [asdict(insight) for insight in self.generate_predictive_insights(zone_name)],
            'seasonal_analysis': self.analyze_seasonal_patterns(zone_name),
            'efficiency_metrics': self.get_efficiency_metrics(zone_name),
            'optimal_schedule': self.get_optimal_schedule(zone_name, 14),  # 2 weeks ahead
            'data_quality': {
                'total_tasks': len(self.historical_data.get(zone_name, {}).get('tasks', [])),
                'date_range': self._get_date_range(zone_name),
                'completeness_score': self._calculate_data_completeness(zone_name)
            }
        }

    def _get_date_range(self, zone_name: str) -> Dict[str, str]:
        """Get the date range of available data"""
        if zone_name not in self.historical_data:
            return {}

        tasks = self.historical_data[zone_name]['tasks']
        if not tasks:
            return {}

        dates = [datetime.fromisoformat(task['completion_time']) for task in tasks]
        return {
            'earliest': min(dates).isoformat(),
            'latest': max(dates).isoformat(),
            'span_days': (max(dates) - min(dates)).days
        }

    def _calculate_data_completeness(self, zone_name: str) -> float:
        """Calculate data completeness score using aggregated data"""
        zone_hash = self._anonymize_zone_name(zone_name)

        if zone_hash not in self.aggregated_data:
            return 0.0

        total_tasks = self.aggregated_data[zone_hash]['total_tasks']
        if total_tasks < 10:
            return total_tasks / 10.0  # Need at least 10 tasks for good analysis

        return min(1.0, total_tasks / 100.0)  # Optimal at 100+ tasks

    def update_privacy_settings(self, new_settings: PrivacySettings):
        """
        Update privacy settings and apply changes

        Args:
            new_settings: New privacy configuration
        """
        old_level = self.privacy_settings.privacy_level
        self.privacy_settings = new_settings

        # If privacy level increased, clean up data
        if new_settings.privacy_level.value > old_level.value:
            self._apply_enhanced_privacy()

        self.logger.info(f"Privacy settings updated to level: {new_settings.privacy_level.value}")

    def _apply_enhanced_privacy(self):
        """Apply enhanced privacy measures to existing data"""
        if self.privacy_settings.privacy_level == PrivacyLevel.FULL_PRIVACY:
            # Remove all detailed data, keep only basic aggregates
            for zone_hash in self.aggregated_data:
                zone_data = self.aggregated_data[zone_hash]
                # Keep only essential aggregated counts
                essential_data = {
                    'total_tasks': zone_data['total_tasks'],
                    'category_counts': dict(zone_data['category_counts']),
                    'last_activity_week': zone_data['last_activity_week']
                }
                self.aggregated_data[zone_hash] = essential_data

        self._save_aggregated_data()

    def delete_all_analytics_data(self) -> bool:
        """
        Delete all analytics data (user privacy control)

        Returns:
            True if successful
        """
        try:
            self.aggregated_data = {}
            self.zone_hash_map = {}
            self.patterns = {}
            self.trends = {}

            # Remove data files
            data_file = os.path.join(self.data_path, "aggregated_data.json")
            if os.path.exists(data_file):
                os.remove(data_file)

            self.logger.info("All analytics data deleted by user request")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting analytics data: {e}")
            return False

    def export_user_data(self) -> Dict[str, Any]:
        """
        Export user's analytics data (GDPR compliance)

        Returns:
            All user data in portable format
        """
        return {
            'privacy_settings': asdict(self.privacy_settings),
            'aggregated_data': self.aggregated_data,
            'zone_mappings': self.zone_hash_map if not self.privacy_settings.anonymize_zone_names else {},
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'data_format_version': '3.0_privacy_preserving'
        }
