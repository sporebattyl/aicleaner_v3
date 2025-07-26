"""AICleaner Data Update Coordinator"""
import logging
from datetime import timedelta, datetime, timezone
from typing import Dict, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import AiCleanerApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

MIN_UPDATE_INTERVAL = timedelta(seconds=30)
MAX_UPDATE_INTERVAL = timedelta(minutes=15)
TRANSIENT_ERROR_THRESHOLD = 3
CACHE_TTL = timedelta(minutes=5)


class AiCleanerCoordinator(DataUpdateCoordinator):
    """Class to manage fetching AICleaner data."""
    
    def __init__(self, hass: HomeAssistant, api_client: AiCleanerApiClient):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=MIN_UPDATE_INTERVAL,
        )
        self.api_client = api_client
        self._transient_error_count = 0
        self._last_successful_update: datetime | None = None
    
    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from AICleaner core service."""
        try:
            status_data = await self.api_client.get_status()
            
            # Successful update, reset error counters and polling interval
            self._transient_error_count = 0
            self.update_interval = MIN_UPDATE_INTERVAL
            self._last_successful_update = datetime.now(timezone.utc)
            _LOGGER.debug("Successfully fetched data, polling interval reset.")
            
            # Return a structured and consistent data object
            return {
                "status": status_data.get("status", "unknown"),
                "version": status_data.get("version", "unknown"),
                "uptime_seconds": status_data.get("uptime_seconds", 0),
                "providers": status_data.get("providers", {}),
                "mqtt": status_data.get("mqtt", {}),
                "last_successful_update": self._last_successful_update,
            }
        
        except Exception as err:
            # Classify error and adjust polling frequency
            error_message = f"Error communicating with AICleaner core: {err}"
            
            # Check if the error is persistent (e.g., auth error)
            if "401" in str(err) or "auth" in str(err).lower():
                self.update_interval = MAX_UPDATE_INTERVAL
                _LOGGER.error(f"Persistent authentication error. Polling interval increased to {MAX_UPDATE_INTERVAL.seconds}s.")
            else:
                # Treat as a transient error
                self._transient_error_count += 1
                new_interval_seconds = min(
                    MIN_UPDATE_INTERVAL.seconds * (2 ** self._transient_error_count),
                    MAX_UPDATE_INTERVAL.seconds
                )
                self.update_interval = timedelta(seconds=new_interval_seconds)
                _LOGGER.warning(
                    f"Transient error count: {self._transient_error_count}. "
                    f"Polling interval increased to {self.update_interval.seconds}s."
                )
            
            # If we have recent, valid data, return it to avoid UI failure
            if self.data and self._last_successful_update:
                time_since_last_success = datetime.now(timezone.utc) - self._last_successful_update
                if time_since_last_success <= CACHE_TTL:
                    _LOGGER.warning(
                        f"{error_message} - Serving stale data from last successful update "
                        f"({time_since_last_success.seconds}s ago)."
                    )
                    return self.data
            
            # If no recent data is available, raise UpdateFailed
            _LOGGER.error(f"No valid cached data available. Failing update. Details: {error_message}")
            raise UpdateFailed(error_message)
