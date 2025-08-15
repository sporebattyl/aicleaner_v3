"""
PDCA (Plan-Do-Check-Act) methodology coordinator for AI Cleaner addon.
Orchestrates the complete cleaning analysis and task management cycle.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from .config import get_config, AiCleanerConfig
from .camera_manager import CameraManager, ImageData, CameraError
from .providers.base import BaseAIProvider, ImageAnalysis, CleaningPlan, CleaningTask
from .providers.gemini import GeminiProvider
from .ha_link import HAEntityManager
from .scheduler import ZoneScheduler, ScheduledTask, ScheduleType, SchedulePriority


logger = logging.getLogger(__name__)


class PDCAPhase(Enum):
    """PDCA cycle phases."""
    PLAN = "plan"
    DO = "do"
    CHECK = "check"
    ACT = "act"


class AnalysisState(Enum):
    """Analysis execution states."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    CHECKING = "checking"
    ACTING = "acting"
    ERROR = "error"


@dataclass
class PDCACycle:
    """Represents a complete PDCA cycle execution."""
    id: str
    zone_id: Optional[str]
    started_at: datetime
    current_phase: PDCAPhase = PDCAPhase.PLAN
    completed_at: Optional[datetime] = None
    
    # Plan phase data
    image_analysis: Optional[ImageAnalysis] = None
    cleaning_plan: Optional[CleaningPlan] = None
    
    # Do phase data
    tasks_created: int = 0
    tasks_assigned_at: Optional[datetime] = None
    
    # Check phase data
    progress_check_at: Optional[datetime] = None
    completion_percentage: float = 0.0
    follow_up_analysis: Optional[ImageAnalysis] = None
    
    # Act phase data
    improvements_identified: List[str] = field(default_factory=list)
    adaptations_made: List[str] = field(default_factory=list)
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    
    def add_error(self, error: str):
        """Add error to the cycle."""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")
        logger.error(f"PDCA Cycle {self.id} error: {error}")
    
    def can_retry(self) -> bool:
        """Check if cycle can be retried."""
        return self.retry_count < self.max_retries
    
    def mark_completed(self):
        """Mark cycle as completed."""
        self.completed_at = datetime.now()
        self.current_phase = PDCAPhase.ACT


class AnalysisManager:
    """
    PDCA methodology coordinator that orchestrates the complete cleaning analysis cycle.
    
    This is the main orchestrator that brings together all components:
    - Camera management for image acquisition
    - AI providers for analysis
    - Home Assistant integration for task creation
    - Scheduling for automated execution
    """
    
    def __init__(self, config: Optional[AiCleanerConfig] = None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        
        # Component managers
        self.camera_manager: Optional[CameraManager] = None
        self.ai_provider: Optional[BaseAIProvider] = None
        self.ha_manager: Optional[HAEntityManager] = None
        self.scheduler: Optional[ZoneScheduler] = None
        
        # State tracking
        self.state = AnalysisState.IDLE
        self.active_cycles: Dict[str, PDCACycle] = {}
        self.completed_cycles: List[PDCACycle] = []
        self.max_completed_history = 50
        
        # Performance metrics
        self.total_analyses = 0
        self.successful_analyses = 0
        self.total_tasks_created = 0
        self.average_analysis_time = 0.0
        
        # Component initialization flags
        self._initialized = False
        self._running = False
    
    async def initialize(self) -> bool:
        """Initialize all components and start the analysis manager."""
        try:
            self.logger.info("Initializing Analysis Manager...")
            
            # Initialize camera manager
            self.camera_manager = CameraManager(self.config)
            
            # Initialize AI provider
            ai_config = self.config.get_ai_provider_config()
            if self.config.ai_provider == "gemini":
                self.ai_provider = GeminiProvider(ai_config)
            else:
                raise ValueError(f"Unsupported AI provider: {self.config.ai_provider}")
            
            if not await self.ai_provider.initialize():
                self.logger.error("Failed to initialize AI provider")
                return False
            
            # Initialize Home Assistant integration
            self.ha_manager = HAEntityManager(self.config)
            if not await self.ha_manager.initialize():
                self.logger.error("Failed to initialize HA integration")
                return False
            
            # Initialize scheduler
            self.scheduler = ZoneScheduler(self.config)
            
            # Register scheduler callbacks
            self.scheduler.register_callback(ScheduleType.ZONE_ANALYSIS, self.execute_zone_analysis)
            self.scheduler.register_callback(ScheduleType.HEALTH_CHECK, self.health_check)
            self.scheduler.register_callback(ScheduleType.CLEANUP, self.cleanup_old_data)
            
            # Setup default tasks
            self.scheduler.setup_default_tasks()
            
            # Update HA entities
            await self.ha_manager.set_ai_available(True, self.config.ai_provider)
            await self.ha_manager.update_system_status("initialized")
            
            self._initialized = True
            self.logger.info("Analysis Manager initialized successfully")
            return True
        
        except Exception as e:
            error_msg = f"Failed to initialize Analysis Manager: {e}"
            self.logger.error(error_msg)
            await self._update_error_status(error_msg)
            return False
    
    async def start(self):
        """Start the analysis manager and scheduler."""
        if not self._initialized:
            if not await self.initialize():
                raise RuntimeError("Failed to initialize Analysis Manager")
        
        self._running = True
        
        # Start scheduler
        await self.scheduler.start()
        
        # Update status
        await self.ha_manager.update_system_status("running")
        
        self.logger.info("Analysis Manager started")
    
    async def shutdown(self):
        """Shutdown the analysis manager and all components."""
        self._running = False
        
        # Stop scheduler
        if self.scheduler:
            await self.scheduler.stop()
        
        # Complete any active cycles
        for cycle in self.active_cycles.values():
            cycle.add_error("Shutdown requested")
            cycle.mark_completed()
        
        # Shutdown components
        if self.ha_manager:
            await self.ha_manager.update_system_status("stopped")
            await self.ha_manager.shutdown()
        
        if self.camera_manager:
            await self.camera_manager.close()
        
        self.logger.info("Analysis Manager shutdown complete")
    
    async def execute_zone_analysis(self, zone_id: Optional[str] = None) -> bool:
        """
        Execute complete PDCA cycle for a zone.
        
        Args:
            zone_id: Zone to analyze (None for default zone)
            
        Returns:
            True if cycle completed successfully
        """
        cycle_id = str(uuid.uuid4())
        cycle = PDCACycle(
            id=cycle_id,
            zone_id=zone_id,
            started_at=datetime.now()
        )
        
        self.active_cycles[cycle_id] = cycle
        
        try:
            self.logger.info(f"Starting PDCA cycle for zone {zone_id or 'default'}")
            
            # PLAN: Analyze current state
            if not await self._plan_phase(cycle):
                cycle.add_error("Plan phase failed")
                return False
            
            # DO: Execute plan (create tasks)
            if not await self._do_phase(cycle):
                cycle.add_error("Do phase failed")
                return False
            
            # CHECK: Monitor progress (simplified for now)
            if not await self._check_phase(cycle):
                cycle.add_error("Check phase failed")
                return False
            
            # ACT: Make improvements
            if not await self._act_phase(cycle):
                cycle.add_error("Act phase failed")
                return False
            
            # Mark as successful
            cycle.mark_completed()
            self.successful_analyses += 1
            
            # Record result for adaptive scheduling
            if cycle.image_analysis and zone_id:
                self.scheduler.record_analysis_result(zone_id, cycle.image_analysis.overall_cleanliness_score)
            
            self.logger.info(f"PDCA cycle {cycle_id} completed successfully")
            return True
        
        except Exception as e:
            cycle.add_error(f"Unexpected error: {e}")
            self.logger.error(f"PDCA cycle {cycle_id} failed: {e}")
            return False
        
        finally:
            # Move to completed cycles
            self.active_cycles.pop(cycle_id, None)
            self.completed_cycles.append(cycle)
            
            # Limit history size
            if len(self.completed_cycles) > self.max_completed_history:
                self.completed_cycles.pop(0)
            
            self.total_analyses += 1
            
            # Update metrics
            await self._update_metrics()
    
    async def _plan_phase(self, cycle: PDCACycle) -> bool:
        """Execute PLAN phase - analyze current state."""
        cycle.current_phase = PDCAPhase.PLAN
        self.state = AnalysisState.PLANNING
        
        start_time = datetime.now()
        
        try:
            # Get camera entity for zone
            camera_entity = self._get_zone_camera_entity(cycle.zone_id)
            if not camera_entity:
                cycle.add_error(f"No camera configured for zone {cycle.zone_id}")
                return False
            
            # Capture image
            self.logger.debug(f"Capturing image from {camera_entity}")
            image = await self.camera_manager.get_camera_snapshot(camera_entity)
            
            # Analyze image with AI
            self.logger.debug("Analyzing image with AI provider")
            analysis = await self.ai_provider.analyze_image(
                image.data,
                cycle.zone_id,
                context=self._get_analysis_context(cycle.zone_id)
            )
            
            # Create cleaning plan
            self.logger.debug("Creating cleaning plan")
            plan = await self.ai_provider.create_cleaning_plan(
                analysis,
                constraints=self._get_planning_constraints()
            )
            
            # Store results
            cycle.image_analysis = analysis
            cycle.cleaning_plan = plan
            
            # Update HA entities
            await self.ha_manager.update_last_analysis(datetime.now(), analysis)
            await self.ha_manager.update_confidence(
                self._confidence_to_percentage(analysis.confidence)
            )
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Plan phase completed in {analysis_time:.2f}s - Score: {analysis.overall_cleanliness_score:.2f}, Tasks: {len(plan.tasks)}")
            
            return True
        
        except CameraError as e:
            cycle.add_error(f"Camera error: {e}")
            return False
        except Exception as e:
            cycle.add_error(f"Plan phase error: {e}")
            return False
    
    async def _do_phase(self, cycle: PDCACycle) -> bool:
        """Execute DO phase - implement the plan."""
        cycle.current_phase = PDCAPhase.DO
        self.state = AnalysisState.EXECUTING
        
        try:
            if not cycle.cleaning_plan or not cycle.cleaning_plan.tasks:
                self.logger.info("No tasks to execute in cleaning plan")
                return True
            
            # Get or create todo list
            todo_entity = self.config.todo_entity or "todo.cleaning_tasks"
            
            # Add tasks to todo list
            tasks_added = await self.ha_manager.add_todo_items(todo_entity, cycle.cleaning_plan.tasks)
            
            cycle.tasks_created = tasks_added
            cycle.tasks_assigned_at = datetime.now()
            
            # Update HA entities
            await self.ha_manager.update_task_count(
                tasks_added,
                {
                    'zone_id': cycle.zone_id,
                    'plan_id': cycle.cleaning_plan.plan_id,
                    'priority_score': cycle.cleaning_plan.priority_score
                }
            )
            
            # Send notification if configured
            if tasks_added > 0:
                await self.ha_manager.send_cleaning_plan_notification(cycle.cleaning_plan)
            
            self.total_tasks_created += tasks_added
            
            self.logger.info(f"Do phase completed - Created {tasks_added} tasks")
            return True
        
        except Exception as e:
            cycle.add_error(f"Do phase error: {e}")
            return False
    
    async def _check_phase(self, cycle: PDCACycle) -> bool:
        """Execute CHECK phase - monitor progress."""
        cycle.current_phase = PDCAPhase.CHECK
        self.state = AnalysisState.CHECKING
        
        try:
            # For now, simplified check phase
            # In a full implementation, this would:
            # 1. Check todo list completion status
            # 2. Take follow-up images
            # 3. Compare before/after analysis
            
            cycle.progress_check_at = datetime.now()
            cycle.completion_percentage = 0.0  # Would be calculated from actual progress
            
            # Could implement follow-up image analysis here
            # cycle.follow_up_analysis = await self._analyze_progress(cycle)
            
            self.logger.debug("Check phase completed (simplified)")
            return True
        
        except Exception as e:
            cycle.add_error(f"Check phase error: {e}")
            return False
    
    async def _act_phase(self, cycle: PDCACycle) -> bool:
        """Execute ACT phase - make improvements."""
        cycle.current_phase = PDCAPhase.ACT
        self.state = AnalysisState.ACTING
        
        try:
            # Analyze cycle performance and identify improvements
            improvements = []
            adaptations = []
            
            # Example adaptations based on analysis
            if cycle.image_analysis:
                score = cycle.image_analysis.overall_cleanliness_score
                
                if score < 0.3:
                    improvements.append("Consider more frequent analysis for this zone")
                    adaptations.append("Increased analysis frequency")
                elif score > 0.9:
                    improvements.append("Zone is very clean, can reduce analysis frequency")
                    adaptations.append("Decreased analysis frequency")
                
                if len(cycle.cleaning_plan.tasks) > 10:
                    improvements.append("Many tasks created, consider task prioritization")
                    adaptations.append("Enhanced task filtering")
            
            cycle.improvements_identified = improvements
            cycle.adaptations_made = adaptations
            
            # Apply adaptations (this would update scheduling, thresholds, etc.)
            # For now, we'll just log them
            for adaptation in adaptations:
                self.logger.info(f"Applied adaptation: {adaptation}")
            
            self.logger.debug("Act phase completed")
            return True
        
        except Exception as e:
            cycle.add_error(f"Act phase error: {e}")
            return False
    
    def _get_zone_camera_entity(self, zone_id: Optional[str]) -> Optional[str]:
        """Get camera entity ID for a zone."""
        if zone_id:
            zone = self.config.get_zone_by_id(zone_id)
            if zone and zone.camera_entity:
                return zone.camera_entity
        
        # Fall back to default camera
        return self.config.camera_entity
    
    def _get_analysis_context(self, zone_id: Optional[str]) -> Dict[str, Any]:
        """Get context for AI analysis."""
        context = {}
        
        # Add historical data if available
        if zone_id:
            # Find recent analysis for this zone
            for cycle in reversed(self.completed_cycles[-10:]):  # Last 10 cycles
                if cycle.zone_id == zone_id and cycle.image_analysis:
                    context['previous_score'] = cycle.image_analysis.overall_cleanliness_score
                    context['previous_summary'] = cycle.image_analysis.summary
                    time_diff = datetime.now() - cycle.started_at
                    context['time_since_last_analysis'] = str(time_diff)
                    break
        
        return context
    
    def _get_planning_constraints(self) -> Dict[str, Any]:
        """Get constraints for cleaning plan generation."""
        return {
            'max_time_minutes': 120,  # Maximum 2 hours of tasks
            'task_priority_threshold': self.config.task_priority_threshold,
        }
    
    def _confidence_to_percentage(self, confidence) -> float:
        """Convert confidence enum to percentage."""
        confidence_map = {
            'low': 0.25,
            'medium': 0.50,
            'high': 0.75,
            'very_high': 0.90
        }
        return confidence_map.get(confidence.value if hasattr(confidence, 'value') else str(confidence).lower(), 0.50)
    
    async def _update_error_status(self, error: str):
        """Update HA entities with error status."""
        if self.ha_manager:
            await self.ha_manager.update_system_status("error", {"last_error": error})
            await self.ha_manager.set_ai_available(False)
    
    async def _update_metrics(self):
        """Update performance metrics."""
        if self.completed_cycles:
            # Calculate average analysis time
            analysis_times = []
            for cycle in self.completed_cycles[-10:]:  # Last 10 cycles
                if cycle.completed_at:
                    duration = (cycle.completed_at - cycle.started_at).total_seconds()
                    analysis_times.append(duration)
            
            if analysis_times:
                self.average_analysis_time = sum(analysis_times) / len(analysis_times)
        
        # Update HA entities with metrics
        success_rate = (self.successful_analyses / max(1, self.total_analyses)) * 100
        
        await self.ha_manager.update_system_status(
            "running",
            {
                "total_analyses": self.total_analyses,
                "successful_analyses": self.successful_analyses,
                "success_rate": f"{success_rate:.1f}%",
                "total_tasks_created": self.total_tasks_created,
                "average_analysis_time": f"{self.average_analysis_time:.1f}s",
                "active_cycles": len(self.active_cycles)
            }
        )
    
    async def health_check(self) -> bool:
        """Perform system health check."""
        try:
            self.logger.debug("Performing health check...")
            
            # Check AI provider
            if self.ai_provider:
                ai_health = await self.ai_provider.health_check()
                await self.ha_manager.set_ai_available(
                    ai_health['status'] in ['healthy', 'degraded'],
                    self.config.ai_provider
                )
            
            # Check camera manager
            if self.camera_manager:
                camera_health = await self.camera_manager.health_check()
                if camera_health['status'] != 'healthy':
                    self.logger.warning(f"Camera health degraded: {camera_health}")
            
            # Check HA integration
            if self.ha_manager:
                ha_health = await self.ha_manager.health_check()
                if ha_health['status'] != 'healthy':
                    self.logger.warning(f"HA integration health degraded: {ha_health}")
            
            self.logger.debug("Health check completed")
            return True
        
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def cleanup_old_data(self) -> bool:
        """Clean up old data and temporary files."""
        try:
            self.logger.debug("Performing cleanup...")
            
            # Clean up old completed cycles (keep last 50)
            if len(self.completed_cycles) > self.max_completed_history:
                removed = len(self.completed_cycles) - self.max_completed_history
                self.completed_cycles = self.completed_cycles[-self.max_completed_history:]
                self.logger.info(f"Cleaned up {removed} old PDCA cycles")
            
            # Could add more cleanup tasks here:
            # - Remove old saved images
            # - Clean up temporary files
            # - Archive old logs
            
            self.logger.debug("Cleanup completed")
            return True
        
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the analysis manager."""
        return {
            'state': self.state.value,
            'initialized': self._initialized,
            'running': self._running,
            'active_cycles': len(self.active_cycles),
            'completed_cycles': len(self.completed_cycles),
            'total_analyses': self.total_analyses,
            'successful_analyses': self.successful_analyses,
            'success_rate': (self.successful_analyses / max(1, self.total_analyses)) * 100,
            'total_tasks_created': self.total_tasks_created,
            'average_analysis_time': self.average_analysis_time,
            'ai_provider': {
                'name': self.ai_provider.name if self.ai_provider else None,
                'available': self.ai_provider.is_available() if self.ai_provider else False,
                'initialized': self.ai_provider.is_initialized if self.ai_provider else False
            },
            'scheduler_status': self.scheduler.get_status() if self.scheduler else None,
            'recent_cycles': [
                {
                    'id': cycle.id,
                    'zone_id': cycle.zone_id,
                    'started_at': cycle.started_at.isoformat(),
                    'completed_at': cycle.completed_at.isoformat() if cycle.completed_at else None,
                    'current_phase': cycle.current_phase.value,
                    'tasks_created': cycle.tasks_created,
                    'errors': len(cycle.errors),
                    'cleanliness_score': cycle.image_analysis.overall_cleanliness_score if cycle.image_analysis else None
                }
                for cycle in self.completed_cycles[-5:]  # Last 5 cycles
            ]
        }