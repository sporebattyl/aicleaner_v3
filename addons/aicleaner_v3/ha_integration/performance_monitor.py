"""Monitors and reports performance metrics for the AICleaner v3 addon."""
import logging
import time
from functools import wraps

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class PerformanceMonitor:
    """Tracks performance of key operations and integrates with HA event bus."""

    def __init__(self, hass: HomeAssistant, domain: str):
        self.hass = hass
        self.domain = domain

    def fire_performance_event(self, operation: str, duration: float):
        """Fire a custom event with performance data."""
        event_data = {
            "operation": operation,
            "duration_ms": round(duration * 1000, 2),
        }
        self.hass.bus.async_fire(f"{self.domain}_performance", event_data)
        _LOGGER.debug(f"Performance event fired: {event_data}")

    def measure_performance(self, operation_name: str):
        """A decorator to measure the execution time of a function."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                result = await func(*args, **kwargs)
                end_time = time.perf_counter()
                duration = end_time - start_time
                self.fire_performance_event(operation_name, duration)
                return result
            return wrapper
        return decorator