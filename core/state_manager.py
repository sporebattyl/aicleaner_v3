"""
State manager for AI Cleaner addon.
Handles state persistence and tracking.
"""
import os
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from typing import Dict, Any, List, Optional

class AnalysisState(Enum):
    """Analysis state enum."""
    IMAGE_CAPTURED = auto()
    LOCAL_ANALYSIS_COMPLETE = auto()
    GEMINI_API_CALL_INITIATED = auto()
    GEMINI_API_CALL_SUCCESS = auto()
    TASK_GENERATION_COMPLETE = auto()
    HA_TODO_CREATION_INITIATED = auto()
    HA_TODO_CREATION_SUCCESS = auto()
    NOTIFICATIONS_SENT = auto()
    CYCLE_COMPLETE = auto()

class StateManager:
    """
    State manager.
    
    Features:
    - File-based state persistence
    - Analysis state tracking
    - API call tracking
    - Cost estimation
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the state manager.
        
        Args:
            config: Configuration
        """
        self.config = config
        self.logger = logging.getLogger("state_manager")
        
        # State file path
        self.state_file = config.get("state_file", "/data/aicleaner_state.json")
        
        # State data
        self.state = {
            "analyses": {},
            "api_calls": [],
            "tasks": [],
            "zones": {}
        }
        
        # Lock for state access
        self.lock = asyncio.Lock()
        
    async def initialize(self):
        """
        Initialize the state manager.
        
        This method should be called after the StateManager is instantiated
        to load the persistent state from disk.
        """
        self.logger.info("Initializing state manager")
        
        # Load state from file
        await self.load_state()
        
    async def load_state(self):
        """Load state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    self.state = json.load(f)
                    
                self.logger.info(f"Loaded state from {self.state_file}")
            else:
                self.logger.info(f"State file {self.state_file} not found, using default state")
                
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
            
    async def save_state(self):
        """
        Save state to file.
        
        This method ensures that the current state is written to the
        configured state file, making it persistent across restarts.
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            # Save state
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
                
            self.logger.debug(f"Saved state to {self.state_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
            
    async def update_analysis_state(self, analysis_id: str, state: AnalysisState, metadata: Dict[str, Any] = None):
        """
        Update analysis state.
        
        Args:
            analysis_id: Analysis ID
            state: Analysis state
            metadata: Additional metadata
        """
        async with self.lock:
            # Get current timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Get or create analysis entry
            if analysis_id not in self.state["analyses"]:
                self.state["analyses"][analysis_id] = {
                    "id": analysis_id,
                    "created_at": timestamp,
                    "states": []
                }
                
            # Add state
            state_entry = {
                "state": state.name,
                "timestamp": timestamp
            }
            
            # Add metadata
            if metadata:
                state_entry["metadata"] = metadata
                
            # Add to states
            self.state["analyses"][analysis_id]["states"].append(state_entry)
            
            # Update current state
            self.state["analyses"][analysis_id]["current_state"] = state.name
            
            # Save state
            await self.save_state()
            
    async def record_api_call(self, model: str, tokens: int, cost: float, metadata: Dict[str, Any] = None):
        """
        Record API call.
        
        Args:
            model: Model name
            tokens: Token count
            cost: Cost
            metadata: Additional metadata
        """
        async with self.lock:
            # Get current timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Create API call entry
            api_call = {
                "model": model,
                "tokens": tokens,
                "cost": cost,
                "timestamp": timestamp
            }
            
            # Add metadata
            if metadata:
                api_call["metadata"] = metadata
                
            # Add to API calls
            self.state["api_calls"].append(api_call)
            
            # Save state
            await self.save_state()
            
    async def record_task(self, task_id: str, zone_name: str, description: str, metadata: Dict[str, Any] = None):
        """
        Record task.
        
        Args:
            task_id: Task ID
            zone_name: Zone name
            description: Task description
            metadata: Additional metadata
        """
        async with self.lock:
            # Get current timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Create task entry
            task = {
                "id": task_id,
                "zone_name": zone_name,
                "description": description,
                "created_at": timestamp,
                "status": "active"
            }
            
            # Add metadata
            if metadata:
                task["metadata"] = metadata
                
            # Add to tasks
            self.state["tasks"].append(task)
            
            # Save state
            await self.save_state()
            
    async def update_task_status(self, task_id: str, status: str, metadata: Dict[str, Any] = None):
        """
        Update task status.
        
        Args:
            task_id: Task ID
            status: Task status
            metadata: Additional metadata
        """
        async with self.lock:
            # Find task
            for task in self.state["tasks"]:
                if task["id"] == task_id:
                    # Update status
                    task["status"] = status
                    
                    # Add completed_at timestamp if completed
                    if status == "completed":
                        task["completed_at"] = datetime.now(timezone.utc).isoformat()
                        
                    # Add metadata
                    if metadata:
                        if "metadata" not in task:
                            task["metadata"] = {}
                            
                        task["metadata"].update(metadata)
                        
                    # Save state
                    await self.save_state()
                    
                    return
                    
            self.logger.warning(f"Task {task_id} not found")

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single task by its ID.

        Args:
            task_id: The ID of the task to retrieve.

        Returns:
            The task dictionary if found, otherwise None.
        """
        async with self.lock:
            for task in self.state["tasks"]:
                if task["id"] == task_id:
                    return task
            return None

    async def get_all_tasks(self, zone_name: str = None) -> List[Dict[str, Any]]:
        """
        Get all tasks, optionally filtered by zone name.

        Args:
            zone_name: Optional. The name of the zone to filter tasks by.

        Returns:
            A list of task dictionaries.
        """
        async with self.lock:
            if zone_name:
                return [task for task in self.state["tasks"] if task.get("zone_name") == zone_name]
            return self.state["tasks"]
            
    async def get_api_calls_today(self) -> int:
        """
        Get API calls today.
        
        Returns:
            API call count
        """
        async with self.lock:
            # Get today's date
            today = datetime.now(timezone.utc).date()
            
            # Count API calls today
            count = 0
            
            for api_call in self.state["api_calls"]:
                # Parse timestamp
                timestamp = datetime.fromisoformat(api_call["timestamp"])
                
                # Check if today
                if timestamp.date() == today:
                    count += 1
                    
            return count
            
    async def get_cost_estimate_today(self) -> float:
        """
        Get cost estimate today.
        
        Returns:
            Cost estimate
        """
        async with self.lock:
            # Get today's date
            today = datetime.now(timezone.utc).date()
            
            # Sum costs today
            cost = 0.0
            
            for api_call in self.state["api_calls"]:
                # Parse timestamp
                timestamp = datetime.fromisoformat(api_call["timestamp"])
                
                # Check if today
                if timestamp.date() == today:
                    cost += api_call.get("cost", 0.0)
                    
            return cost
            
    async def get_analysis_duration_stats(self) -> Dict[str, float]:
        """
        Get analysis duration stats.
        
        Returns:
            Analysis duration stats
        """
        async with self.lock:
            durations = []
            
            for analysis_id, analysis in self.state["analyses"].items():
                states = analysis.get("states", [])
                
                if len(states) >= 2:
                    # Get first and last state
                    first_state = states[0]
                    last_state = states[-1]
                    
                    # Parse timestamps
                    first_timestamp = datetime.fromisoformat(first_state["timestamp"])
                    last_timestamp = datetime.fromisoformat(last_state["timestamp"])
                    
                    # Calculate duration
                    duration = (last_timestamp - first_timestamp).total_seconds()
                    
                    durations.append(duration)
                    
            # Calculate stats
            if durations:
                return {
                    "average": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "count": len(durations)
                }
            else:
                return {
                    "average": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "count": 0
                }
                
    async def get_active_tasks(self, zone_name: str = None) -> List[Dict[str, Any]]:
        """
        Get active tasks.
        
        Args:
            zone_name: Zone name filter
            
        Returns:
            Active tasks
        """
        async with self.lock:
            # Filter active tasks
            active_tasks = [task for task in self.state["tasks"] if task.get("status") == "active"]
            
            # Filter by zone if specified
            if zone_name:
                active_tasks = [task for task in active_tasks if task.get("zone_name") == zone_name]
                
            return active_tasks
            
    async def get_zone_state(self, zone_name: str) -> Dict[str, Any]:
        """
        Get zone state.
        
        Args:
            zone_name: Zone name
            
        Returns:
            Zone state
        """
        async with self.lock:
            # Get or create zone state
            if zone_name not in self.state["zones"]:
                self.state["zones"][zone_name] = {
                    "name": zone_name,
                    "last_analysis": None,
                    "cleanliness_score": None,
                    "active_tasks": 0,
                    "cleanliness_history": []
                }
                
            # Update active task count
            active_tasks = await self.get_active_tasks(zone_name)
            self.state["zones"][zone_name]["active_tasks"] = len(active_tasks)
            
            return self.state["zones"][zone_name]
            
    async def update_zone_state(self, zone_name: str, updates: Dict[str, Any]):
        """
        Update zone state.
        
        Args:
            zone_name: Zone name
            updates: State updates
        """
        async with self.lock:
            # Get or create zone state
            zone_state = await self.get_zone_state(zone_name)
            
            # Update state
            zone_state.update(updates)
            
            # Save state
            await self.save_state()

    async def add_cleanliness_entry(self, zone_name: str, cleanliness_data: Dict[str, Any]):
        """
        Adds a cleanliness assessment entry to the zone's history.

        Args:
            zone_name: The name of the zone.
            cleanliness_data: Dictionary containing cleanliness assessment details.
        """
        async with self.lock:
            zone_state = await self.get_zone_state(zone_name)
            if 'cleanliness_history' not in zone_state:
                zone_state['cleanliness_history'] = []

            # Add timestamp if not present
            if 'timestamp' not in cleanliness_data:
                cleanliness_data['timestamp'] = datetime.now(timezone.utc).isoformat()

            zone_state['cleanliness_history'].append(cleanliness_data)
            # Keep only the last 10 cleanliness records
            zone_state['cleanliness_history'] = zone_state['cleanliness_history'][-10:]
            await self.save_state()

    async def get_cleanliness_history(self, zone_name: str) -> List[Dict[str, Any]]:
        """
        Retrieves the cleanliness history for a given zone.

        Args:
            zone_name: The name of the zone.

        Returns:
            A list of cleanliness assessment entries.
        """
        async with self.lock:
            zone_state = await self.get_zone_state(zone_name)
            return zone_state.get('cleanliness_history', [])

    async def shutdown(self):
        """
        Performs any necessary cleanup before shutdown.
        """
        self.logger.info("Shutting down state manager.")
        await self.save_state()