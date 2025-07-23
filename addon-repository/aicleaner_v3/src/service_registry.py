"""
Service Registry for AICleaner v3 Hot-Reload System
Implements two-phase commit protocol for safe configuration updates
"""

import abc
import asyncio
import collections
import logging
from typing import Dict, List, Optional, Set, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

class Reloadable(abc.ABC):
    """
    Abstract Base Class for services that can be hot-reloaded.
    Defines the interface for two-phase configuration updates.
    """
    @abc.abstractmethod
    async def validate_config(self, new_config: Dict) -> Tuple[bool, Optional[str]]:
        """
        Phase 1: Validate the new configuration without applying it.
        Returns (True, None) if valid, or (False, error_message) if invalid.
        """
        pass

    @abc.abstractmethod
    async def reload_config(self, new_config: Dict):
        """
        Phase 2: Apply the new configuration. This method is called only if
        all services successfully passed the validation phase.
        """
        pass

class ReloadContext:
    """
    Manages the state of a configuration reload operation.
    """
    def __init__(self, version: int, status: str = "pending", errors: Optional[List[str]] = None):
        self.version = version
        self.status = status  # e.g., "pending", "validating", "applying", "completed", "failed"
        self.errors = errors if errors is not None else []
        self.start_time = asyncio.get_event_loop().time() # Use loop time for consistency

    def add_error(self, error_message: str):
        self.errors.append(error_message)
        self.status = "failed"

    def set_status(self, status: str):
        self.status = status

    def __repr__(self):
        return f"ReloadContext(version={self.version}, status='{self.status}', errors={self.errors})"

T = TypeVar('T', bound=Reloadable)

class ServiceRegistry:
    """
    Manages the registration, dependency resolution, and hot-reloading
    of Reloadable services. Implements a two-phase commit protocol for reloads.
    """
    def __init__(self):
        self._services: Dict[str, Reloadable] = {}
        self._dependencies: Dict[str, List[str]] = collections.defaultdict(list)
        self._reverse_dependencies: Dict[str, List[str]] = collections.defaultdict(list)
        self._reload_lock = asyncio.Lock()
        self._current_reload_context: Optional[ReloadContext] = None
        self._request_queue_active = False # Flag to indicate if requests should be queued

    def register_service(self, name: str, service: Reloadable, dependencies: Optional[List[str]] = None):
        """
        Registers a service with the registry.
        :param name: Unique name of the service.
        :param service: An instance of a class implementing Reloadable.
        :param dependencies: List of service names that this service depends on.
        """
        if not isinstance(service, Reloadable):
            raise TypeError(f"Service '{name}' must implement the Reloadable ABC.")
        if name in self._services:
            logger.warning(f"Service '{name}' already registered. Overwriting.")

        self._services[name] = service
        if dependencies:
            self._dependencies[name].extend(dependencies)
            for dep in dependencies:
                self._reverse_dependencies[dep].append(name)
        logger.info(f"Service '{name}' registered with dependencies: {dependencies}")

    def get_service(self, name: str) -> Optional[Reloadable]:
        """Retrieves a registered service by its name."""
        return self._services.get(name)

    async def _topological_sort(self) -> Optional[List[str]]:
        """
        Performs a topological sort of services based on their dependencies.
        Returns a list of service names in reload order, or None if a cycle is detected.
        """
        in_degree = {name: 0 for name in self._services}
        graph = collections.defaultdict(list)

        for service_name, deps in self._dependencies.items():
            for dep in deps:
                if dep not in self._services:
                    logger.error(f"Dependency '{dep}' for service '{service_name}' not registered.")
                    return None # Unregistered dependency, cannot sort
                graph[dep].append(service_name)
                in_degree[service_name] += 1

        queue = collections.deque([name for name, degree in in_degree.items() if degree == 0])
        sorted_services = []

        while queue:
            service_name = queue.popleft()
            sorted_services.append(service_name)

            for neighbor in graph[service_name]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_services) != len(self._services):
            logger.error("Dependency cycle detected or some services are unreachable.")
            # Identify the cycle for better error reporting
            remaining_nodes = {name for name, degree in in_degree.items() if degree > 0}
            logger.error(f"Services involved in cycle/unreachable: {remaining_nodes}")
            return None
        return sorted_services

    async def initiate_reload(self, new_config: Dict, new_version: int) -> ReloadContext:
        """
        Initiates a two-phase commit for hot-reloading services with a new configuration.
        :param new_config: The new configuration dictionary.
        :param new_version: The new configuration version.
        :return: A ReloadContext object detailing the outcome.
        """
        async with self._reload_lock:
            if self._current_reload_context and self._current_reload_context.status not in ["completed", "failed"]:
                logger.warning("Another reload is already in progress. Aborting current request.")
                # Return a context indicating the ongoing reload
                return ReloadContext(new_version, "aborted", ["Another reload is already in progress."])

            self._current_reload_context = ReloadContext(new_version, "validating")
            logger.info(f"Initiating configuration reload for version {new_version}...")

            # 1. Get topological order
            reload_order = await self._topological_sort()
            if reload_order is None:
                error_msg = "Failed to determine service reload order due to dependency issues."
                self._current_reload_context.add_error(error_msg)
                logger.error(error_msg)
                return self._current_reload_context

            # 2. Phase 1: Validation (Fast/Full - though here just one validation)
            logger.info("Phase 1: Validating new configuration across services...")
            validation_results = {}
            for service_name in reload_order:
                service = self._services[service_name]
                try:
                    is_valid, error_msg = await service.validate_config(new_config)
                    validation_results[service_name] = (is_valid, error_msg)
                    if not is_valid:
                        self._current_reload_context.add_error(
                            f"Service '{service_name}' validation failed: {error_msg}"
                        )
                        logger.error(f"Validation failed for '{service_name}': {error_msg}")
                        # If validation fails, we stop and prepare for rollback
                        await self._rollback_reload(reload_order, validation_results)
                        return self._current_reload_context
                except Exception as e:
                    self._current_reload_context.add_error(
                        f"Exception during validation for '{service_name}': {e}"
                    )
                    logger.exception(f"Exception during validation for '{service_name}'")
                    await self._rollback_reload(reload_order, validation_results)
                    return self._current_reload_context

            logger.info("All services passed configuration validation.")
            self._current_reload_context.set_status("applying")

            # 3. Phase 2: Apply Configuration
            logger.info("Phase 2: Applying new configuration to services...")
            self._request_queue_active = True # Activate request queuing
            try:
                for service_name in reload_order:
                    service = self._services[service_name]
                    await service.reload_config(new_config)
                    logger.info(f"Service '{service_name}' reloaded successfully.")
                self._current_reload_context.set_status("completed")
                logger.info(f"Configuration reload for version {new_version} completed successfully.")
            except Exception as e:
                self._current_reload_context.add_error(f"Exception during config application: {e}")
                logger.exception("Exception during configuration application phase.")
                await self._rollback_reload(reload_order, validation_results) # Attempt rollback on failure
            finally:
                self._request_queue_active = False # Deactivate request queuing

            return self._current_reload_context

    async def _rollback_reload(self, reload_order: List[str], validation_results: Dict[str, Tuple[bool, Optional[str]]]):
        """
        Rolls back services to their previous state if the reload fails.
        This is a simplified rollback; in a real system, you'd need to store
        the old config for each service and re-apply it. For this exercise,
        we just log the failure.
        """
        logger.error("Reload failed. Attempting to rollback (logging only, no actual state restoration).")
        self._current_reload_context.set_status("failed")
        # In a real scenario, you would iterate through services that *were* modified
        # and revert their state using previously stored configurations.
        # For this implementation, we're just marking the context as failed.
        for service_name in reload_order:
            if service_name in validation_results and validation_results[service_name][0]:
                # This service passed validation, so it might have been partially reloaded
                # In a real system, you'd call a specific rollback method on the service
                logger.warning(f"Service '{service_name}' might be in an inconsistent state. Manual intervention may be required.")
        logger.error("Rollback procedure completed (conceptual). System may be in an inconsistent state.")

    def is_reload_in_progress(self) -> bool:
        """Checks if a configuration reload is currently active."""
        return self._reload_lock.locked() or self._request_queue_active

    def should_queue_requests(self) -> bool:
        """Indicates if incoming requests should be queued due to an active reload."""
        return self._request_queue_active

    def get_current_reload_context(self) -> Optional[ReloadContext]:
        """Returns the current or last reload context."""
        return self._current_reload_context