import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from PIL import Image
from .state_manager import AnalysisState
from rules.ignore_rules_manager import IgnoreRulesManager
from notifications.notification_engine import NotificationEngine
from ai.multi_model_ai import MultiModelAIOptimizer
from ai.predictive_analytics import PredictiveAnalytics
from ai.scene_understanding import AdvancedSceneUnderstanding
from ai.ai_coordinator import AICoordinator
from core.local_model_manager import LocalModelManager
from dataclasses import asdict

class ZoneManager:
    """
    Manages an individual zone's analysis, task processing, and state updates.
    This class encapsulates the logic previously found in the monolithic Zone class.
    """
    def __init__(self, zone_config: Dict[str, Any], ha_client, state_manager,
                 multi_model_ai_optimizer, config: Dict[str, Any] = None):
        self.name = zone_config['name']
        self.camera_entity = zone_config['camera_entity']
        self.todo_list_entity = zone_config['todo_list_entity']
        self.update_frequency = zone_config.get('update_frequency', 300)  # Default 5 minutes
        self.icon = zone_config.get('icon', 'mdi:home')
        self.purpose = zone_config.get('purpose', 'Keep tidy and clean')
        self.notifications_enabled = zone_config.get('notifications_enabled', False)
        self.notification_service = zone_config.get('notification_service', '')
        self.notification_personality = zone_config.get('notification_personality', 'default')
        self.notify_on_create = zone_config.get('notify_on_create', False)
        self.notify_on_complete = zone_config.get('notify_on_complete', False)
        self.ha_client = ha_client
        self.state_manager = state_manager
        self.multi_model_ai_optimizer = multi_model_ai_optimizer

        self.logger = logging.getLogger(f"zone_manager.{self.name}")

        # Initialize AI Coordinator for orchestrated analysis
        if config is None:
            config = {}
        self.ai_coordinator = AICoordinator(
            config=config,
            multi_model_ai=multi_model_ai_optimizer,
            predictive_analytics=PredictiveAnalytics(),
            scene_understanding=AdvancedSceneUnderstanding(),
            local_model_manager=LocalModelManager(config)
        )

        # Flag to track if AI Coordinator is initialized
        self._ai_coordinator_initialized = False

        # Initialize component-based notification engine
        notification_config = {
            'notification_personality': self.notification_personality,
            'notification_service': self.notification_service,
            'webhook_url': zone_config.get('webhook_url'),
            'timeout': zone_config.get('notification_timeout', 10),
            'retry_count': zone_config.get('notification_retry_count', 3)
        }
        self.notification_engine = NotificationEngine(notification_config, ha_client)

        # Initialize component-based ignore rules manager
        self.ignore_rules_manager = IgnoreRulesManager(self.name)
        self.ignore_rules_manager.load_rules() # Load existing ignore rules

        self.last_analysis_time = None # For UI display

    async def initialize_ai_coordinator(self):
        """Initialize the AI Coordinator if not already done."""
        if not self._ai_coordinator_initialized:
            try:
                await self.ai_coordinator.initialize()
                self._ai_coordinator_initialized = True
                self.logger.info(f"AI Coordinator initialized for zone {self.name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize AI Coordinator for zone {self.name}: {e}")

    async def analyze_image_batch_optimized(self, image_path: str, priority: str = "scheduled") -> Optional[Dict[str, Any]]:
        """
        Performs orchestrated AI analysis using the AI Coordinator.
        Combines core analysis, scene understanding, and predictive insights.
        """
        if not image_path or not os.path.exists(image_path):
            self.logger.error(f"Invalid image path provided: {image_path}")
            return None

        try:
            # Ensure AI Coordinator is initialized
            await self.initialize_ai_coordinator()

            active_tasks = await self.state_manager.get_active_tasks(self.name)
            ignore_rules = self.ignore_rules_manager.get_rules()

            # Use AI Coordinator for orchestrated analysis
            analysis_result = await self.ai_coordinator.analyze_zone(
                zone_name=self.name,
                image_path=image_path,
                priority=priority,
                zone_purpose=self.purpose,
                active_tasks=active_tasks,
                ignore_rules=ignore_rules
            )

            if analysis_result and not analysis_result.get("error", False):
                was_cached = analysis_result.get("was_cached", False)
                self.logger.info(f"Orchestrated AI analysis for zone {self.name} completed. Cached: {was_cached}")
                return analysis_result
            else:
                error_msg = analysis_result.get("error_message", "Unknown error") if analysis_result else "No result"
                self.logger.warning(f"Orchestrated AI analysis for zone {self.name} failed: {error_msg}")
                return None

        except Exception as e:
            self.logger.error(f"Error in orchestrated analysis for zone {self.name}: {e}")
            return None

    async def process_batch_analysis_results(self, batch_result: Dict[str, Any], analysis_id: str) -> Dict[str, Any]:
        """
        Process the results from AI Coordinator orchestrated analysis and update zone state accordingly.
        Works with the new AI Coordinator output format.
        """
        if not batch_result:
            return {'processed': False, 'error': 'No batch result provided'}

        summary = {
            'processed': True,
            'completed_tasks_count': 0,
            'new_tasks_count': 0,
            'cleanliness_score': None,
            'cache_hit': batch_result.get('was_cached', False),
            'scene_context_summary': {},
            'predictive_insights': [],
            'contextual_insights': []
        }

        try:
            # Extract scene understanding data (already processed by AI Coordinator)
            scene_understanding_data = batch_result.get('scene_understanding', {})
            if scene_understanding_data:
                summary['scene_context_summary'] = scene_understanding_data.get('scene_context', {})
                summary['contextual_insights'] = scene_understanding_data.get('contextual_insights', [])
                self.logger.info(f"Scene understanding data available for zone {self.name}")

            # Extract predictive insights (already processed by AI Coordinator)
            predictive_insights = batch_result.get('predictive_insights', {})
            if predictive_insights:
                summary['predictive_insights'] = predictive_insights
                self.logger.info(f"Predictive insights available for zone {self.name}")

            # Process completed tasks from core assessment
            core_assessment = batch_result.get('core_assessment', {})
            completed_tasks = batch_result.get('completed_tasks', [])

            if completed_tasks:
                # Extract task IDs if they exist, otherwise use the task descriptions
                completed_task_ids = []
                for task in completed_tasks:
                    if isinstance(task, dict) and 'task_ids' in task:
                        completed_task_ids.extend(task['task_ids'])
                    elif isinstance(task, dict) and 'id' in task:
                        completed_task_ids.append(task['id'])

                if completed_task_ids:
                    await self._process_completed_tasks(completed_task_ids, analysis_id)
                    summary['completed_tasks_count'] = len(completed_task_ids)
                    self.logger.info(f"Processed {len(completed_task_ids)} completed tasks in zone {self.name}")

                    # Record completed tasks for predictive analytics
                    for task_id in completed_task_ids:
                        task = await self.state_manager.get_task(task_id)
                        if task:
                            self.ai_coordinator.predictive_analytics.record_task_completion(
                                zone_name=self.name,
                                task_description=task['description'],
                                completion_time=datetime.now(timezone.utc),
                                task_priority=task.get('priority', 5)
                            )
                            self.logger.debug(f"Recorded completed task '{task['description']}' for predictive analytics.")

            # Process new tasks (enhanced by AI Coordinator)
            generated_tasks = batch_result.get('generated_tasks', [])

            if generated_tasks:
                # Tasks are already enhanced by the AI Coordinator with scene understanding
                await self._process_new_tasks(generated_tasks, analysis_id)
                summary['new_tasks_count'] = len(generated_tasks)
                self.logger.info(f"Processed {len(generated_tasks)} enhanced tasks in zone {self.name}.")

            # Process cleanliness assessment from core assessment
            cleanliness_score = batch_result.get('cleanliness_score', 0)
            if cleanliness_score > 0:
                cleanliness_data = {
                    'score': cleanliness_score,
                    'timestamp': batch_result.get('timestamp'),
                    'analysis_summary': batch_result.get('analysis_summary', ''),
                    'ai_coordinator_version': batch_result.get('ai_coordinator_version', '1.0')
                }
                await self.state_manager.add_cleanliness_entry(self.name, cleanliness_data)
                summary['cleanliness_score'] = cleanliness_score
                self.logger.info(f"Updated cleanliness score for zone {self.name}: {cleanliness_score}/10")

            return summary
        except Exception as e:
            self.logger.error(f"Error processing AI Coordinator analysis results for zone {self.name}: {e}")
            return {'processed': False, 'error': str(e)}

    async def _process_completed_tasks(self, completed_task_ids: List[str], analysis_id: str):
        """Process completed tasks: update state, HA todo list, and send notifications"""
        for task_id in completed_task_ids:
            task = await self.state_manager.get_task(task_id)
            if not task:
                self.logger.warning(f"Completed task ID {task_id} not found in state for zone {self.name}")
                continue
            await self.state_manager.update_task_status(task_id, 'completed', {'analysis_id': analysis_id})
            try:
                await self.ha_client.update_todo_item(
                    entity_id=self.todo_list_entity,
                    item=task['description'],
                    status='completed'
                )
            except Exception as e:
                self.logger.error(f"Error updating HA todo item for completed task in zone {self.name}: {e}")
            if self.notify_on_complete:
                self.notification_engine.send_task_notification({
                    'zone': self.name,
                    'description': task['description'],
                    'status': 'completed'
                })

    async def _process_new_tasks(self, new_tasks: List[Dict[str, Any]], analysis_id: str):
        """Process new tasks: update state, HA todo list, and send notifications.
        Filters out tasks that match ignore rules."""
        for task_data in new_tasks:
            task_description = task_data['description']
            if self.ignore_rules_manager.should_ignore_task(task_description):
                self.logger.info(f"Ignoring task in zone {self.name} due to ignore rules: {task_description}")
                continue
            task_id = str(uuid.uuid4()) # Generate unique ID for the task
            new_task = {
                'id': task_id,
                'description': task_description,
                'status': 'active',
                'created_at': task_data.get('generated_at', datetime.now(timezone.utc).isoformat()),
                'priority': task_data.get('priority', 5),
                'context_aware': task_data.get('context_aware', False)
            }
            await self.state_manager.record_task(
                task_id,
                self.name,
                task_description,
                {'analysis_id': analysis_id, 'priority': new_task['priority']}
            )
            try:
                await self.ha_client.add_todo_item(
                    entity_id=self.todo_list_entity,
                    item=task_description
                )
            except Exception as e:
                self.logger.error(f"Error adding HA todo item for new task in zone {self.name}: {e}")
            if self.notify_on_create:
                self.notification_engine.send_task_notification({
                    'zone': self.name,
                    'description': task_description,
                    'status': 'created',
                    'priority': new_task['priority']
                })

    def _parse_gemini_batch_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parses the comprehensive JSON response from Gemini for batch analysis.
        """
        try:
            cleaned_text = response_text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_text)
            # Validate top-level keys
            if not all(k in data for k in ["completed_tasks", "new_tasks", "cleanliness_assessment"]):
                self.logger.error("Batch response missing required top-level keys.")
                return None
            # Validate completed_tasks format
            if not isinstance(data["completed_tasks"], list):
                self.logger.warning("completed_tasks is not a list.")
                data["completed_tasks"] = []
            data["completed_tasks"] = {"task_ids": [str(t) for t in data["completed_tasks"]]} # Ensure string IDs
            # Validate new_tasks format
            if not isinstance(data["new_tasks"], list):
                self.logger.warning("new_tasks is not a list.")
                data["new_tasks"] = []
            # Add dummy priority and generated_at for now, will be calculated later if needed
            data["new_tasks"] = {"tasks": [{"description": str(t), "priority": 5, "generated_at": datetime.now(timezone.utc).isoformat()} for t in data["new_tasks"]]}            # Validate cleanliness_assessment format
            cleanliness = data["cleanliness_assessment"]
            if not isinstance(cleanliness, dict) or "score" not in cleanliness:
                self.logger.warning("cleanliness_assessment is not valid.")
                data["cleanliness_assessment"] = {"score": None, "state": "unknown", "observations": [], "recommendations": []}
            else:
                cleanliness["state"] = self._get_cleanliness_state_label(cleanliness.get("score"))
            self.logger.info("Successfully parsed Gemini batch response.")
            return data
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decoding error in Gemini batch response: {e}. Raw: {response_text}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing Gemini batch response: {e}. Raw: {response_text}")
            return None

    def _get_cleanliness_state_label(self, score: Optional[float]) -> str:
        """
        Converts numerical cleanliness score to descriptive label.
        """
        if score is None:
            return "unknown"
        if score >= 9:
            return "Excellent"
        elif score >= 7:
            return "Good"
        elif score >= 5:
            return "Fair"
        elif score >= 3:
            return "Poor"
        else:
            return "Needs Attention"

    async def update_ha_sensor(self):
        """
        Updates Home Assistant sensor with current zone data via REST API.
        """
        try:
            sensor_data = await self.get_sensor_data()
            sensor_entity = f"sensor.aicleaner_{self.sanitize_entity_name(self.name)}_tasks"
            state = sensor_data['state']
            attributes = sensor_data['attributes']
            await self.ha_client.update_sensor(sensor_entity, state, attributes)
            self.logger.info(f"Updated HA sensor for zone {self.name}: {state} active tasks")
        except Exception as e:
            self.logger.error(f"Error updating HA sensor for zone {self.name}: {e}")

    async def get_sensor_data(self) -> Dict[str, Any]:
        """
        Gets sensor data for this zone to send to Home Assistant.
        Combines tasks from AICleaner's internal state AND Home Assistant to-do list.
        """
        internal_tasks = await self.state_manager.get_all_tasks(self.name)
        internal_active = [task for task in internal_tasks if task.get('status') == 'active']
        internal_completed = [task for task in internal_tasks if task.get('status') == 'completed']

        ha_todo_items = await self.ha_client.get_todo_list_items(self.todo_list_entity)
        ha_active_tasks = [item for item in ha_todo_items if item.get('status') == 'needs_action']
        ha_completed_tasks = [item for item in ha_todo_items if item.get('status') == 'completed']

        total_active_count = len(internal_active) + len(ha_active_tasks)
        total_completed_count = len(internal_completed) + len(ha_completed_tasks)

        # Placeholder for performance metrics - will be implemented in PerformanceMonitor
        performance_metrics = {
            'completion_rate': 0,
            'average_completion_time': 0,
            'task_creation_rate': 0,
            'efficiency_score': 0,
            'total_tasks': total_active_count + total_completed_count,
            'completed_tasks': total_completed_count,
            'active_tasks': total_active_count
        }

        combined_completion_rate = 0
        if (total_active_count + total_completed_count) > 0:
            combined_completion_rate = round((total_completed_count / (total_active_count + total_completed_count)) * 100, 1)

        last_analysis = None
        if self.last_analysis_time:
            last_analysis = self.last_analysis_time.isoformat()

        task_details = []
        for task in internal_active[:5]:
            task_details.append({
                'id': task.get('id'),
                'description': task.get('description'),
                'priority': task.get('priority', 'normal'),
                'created_at': task.get('created_at'),
                'status': 'active',
                'source': 'aicleaner'
            })

        remaining_slots = 10 - len(task_details)
        for item in ha_active_tasks[:remaining_slots]:
            task_details.append({
                'id': item.get('uid', item.get('summary', '')),
                'description': item.get('summary', ''),
                'priority': 'normal',
                'created_at': None,
                'status': 'active',
                'source': 'home_assistant'
            })

        displayed_active_count = min(total_active_count, 10)

        return {
            'state': displayed_active_count,
            'attributes': {
                'zone_name': self.name,
                'display_name': self.name.replace('_', ' ').title(),
                'purpose': self.purpose,
                'total_tasks': total_active_count + total_completed_count,
                'active_tasks': displayed_active_count,
                'total_active_tasks': total_active_count,
                'completed_tasks': total_completed_count,
                'completion_rate': combined_completion_rate,
                'efficiency_score': performance_metrics.get('efficiency_score', 0),
                'average_completion_time': performance_metrics.get('average_completion_time', 0),
                'last_analysis': last_analysis,
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'camera_entity': self.camera_entity,
                'todo_list_entity': self.todo_list_entity,
                'update_frequency': self.update_frequency,
                'tasks': task_details,
                'ignore_rules': self.ignore_rules_manager.get_rules(),
                'notifications_enabled': self.notifications_enabled,
                'notification_personality': self.notification_personality,
                'unit_of_measurement': 'tasks',
                'friendly_name': f"{self.name} Tasks",
                'icon': 'mdi:format-list-checks',
                'device_class': 'aicleaner_zone'
            }
        }

    def sanitize_entity_name(self, name: str) -> str:
        """
        Sanitizes zone names for Home Assistant entity IDs.
        """
        sanitized = name.lower()
        sanitized = re.sub(r"[^\w\s-]", "_", sanitized)
        sanitized = re.sub(r"[\s-]+", "_", sanitized)
        sanitized = re.sub(r"_+", "_", sanitized)
        sanitized = sanitized.strip("_")
        return sanitized
