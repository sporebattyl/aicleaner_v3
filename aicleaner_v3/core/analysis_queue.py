import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from datetime import datetime, timezone

class AnalysisPriority(Enum):
    """Analysis priority enum."""
    MANUAL = 1
    HIGH_MESSINESS = 2
    SCHEDULED = 3
    RETRY = 4


class AnalysisRequest:
    """Represents an analysis request in the queue."""

    def __init__(self, analysis_id: str, zone_name: str, priority: AnalysisPriority,
                 analysis_func: Optional[Callable] = None, created_at: Optional[datetime] = None):
        self.analysis_id = analysis_id
        self.zone_name = zone_name
        self.priority = priority
        self.analysis_func = analysis_func
        self.created_at = created_at or datetime.now(timezone.utc)
        self.attempts = 0
        self.max_attempts = 3

    def __lt__(self, other):
        """Enable priority queue ordering by priority value."""
        if not isinstance(other, AnalysisRequest):
            return NotImplemented
        return self.priority.value < other.priority.value

class AnalysisQueueManager:
    """
    Manages the analysis queue and worker pool for zone analysis.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("analysis_queue_manager")

        self.queue = asyncio.PriorityQueue()
        self.global_semaphore = asyncio.Semaphore(
            config.get("max_concurrent_analyses", 2)
        )
        self.worker_count = config.get("analysis_workers", 2)
        self.workers = []
        self.running = False

    async def start(self):
        """Start the analysis queue manager and its workers."""
        self.logger.info("Starting analysis queue manager")
        self.running = True
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker_loop(i))
            self.workers.append(worker)
        self.logger.info(f"Started {self.worker_count} analysis workers.")

    async def stop(self):
        """Stop the analysis queue manager and its workers."""
        self.logger.info("Stopping analysis queue manager")
        self.running = False
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.logger.info("Analysis queue manager stopped.")

    async def queue_analysis(self, zone_name: str, priority: AnalysisPriority,
                           analysis_func: Optional[Callable] = None) -> str:
        """
        Add an analysis request to the queue.
        Returns a unique analysis ID.
        """
        # Generate unique analysis ID
        analysis_id = f"{zone_name}_{uuid.uuid4().hex[:8]}"

        # Create analysis request
        request = AnalysisRequest(
            analysis_id=analysis_id,
            zone_name=zone_name,
            priority=priority,
            analysis_func=analysis_func
        )

        # Add to priority queue (priority value, request)
        await self.queue.put((priority.value, request))

        self.logger.info(f"Queued analysis request {analysis_id} for zone {zone_name} with priority {priority.name}")

        return analysis_id

    async def _worker_loop(self, worker_id: int):
        """Worker loop to process analysis requests from the queue."""
        self.logger.info(f"Analysis worker {worker_id} started.")
        while self.running:
            try:
                priority_value, request = await self.queue.get()
                self.logger.info(f"Worker {worker_id} picked up request {request.analysis_id} for zone {request.zone_name} with priority {request.priority.name}.")

                # Acquire global semaphore for resource limiting
                async with self.global_semaphore:
                    try:
                        # Execute analysis function if provided
                        if request.analysis_func:
                            await request.analysis_func(request.zone_name, request.analysis_id)
                        else:
                            # Placeholder for actual analysis processing
                            await asyncio.sleep(1)  # Simulate work

                        self.logger.info(f"Worker {worker_id} finished processing request {request.analysis_id} for zone {request.zone_name}.")
                    except Exception as analysis_error:
                        request.attempts += 1
                        self.logger.error(f"Analysis error in worker {worker_id} for request {request.analysis_id}: {analysis_error}")

                        # Retry if under max attempts
                        if request.attempts < request.max_attempts:
                            self.logger.info(f"Retrying request {request.analysis_id} (attempt {request.attempts + 1}/{request.max_attempts})")
                            await self.queue.put((AnalysisPriority.RETRY.value, request))
                        else:
                            self.logger.error(f"Request {request.analysis_id} failed after {request.max_attempts} attempts")

                self.queue.task_done()
            except asyncio.CancelledError:
                self.logger.info(f"Analysis worker {worker_id} cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Error in worker {worker_id}: {e}")
                await asyncio.sleep(5)  # Prevent busy-loop on error

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status for monitoring."""
        return {
            "queue_size": self.queue.qsize(),
            "worker_count": len(self.workers),
            "running": self.running,
            "max_concurrent": self.global_semaphore._value,
            "available_slots": self.global_semaphore._value
        }
