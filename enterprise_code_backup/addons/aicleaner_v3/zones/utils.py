"""
Phase 3B: Zone Configuration Utilities
Helper functions and decorators for zone management.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Optional, Tuple, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def retry(exceptions: Tuple[Exception, ...] = (Exception,), tries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry decorator for async functions with exponential backoff.
    
    Args:
        exceptions: Tuple of exceptions to catch and retry on
        tries: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(tries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == tries - 1:  # Last attempt
                        logger.error(f"Function {func.__name__} failed after {tries} attempts: {e}")
                        raise e
                    
                    logger.warning(f"Function {func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            # This should never be reached, but just in case
            raise last_exception
            
        return wrapper
    return decorator


def timing(func: Callable) -> Callable:
    """
    Decorator to measure and log execution time of async functions.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            logger.debug(f"Function {func.__name__} executed in {execution_time:.2f}ms")
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Function {func.__name__} failed after {execution_time:.2f}ms: {e}")
            raise
            
    return wrapper


def validate_zone_id(zone_id: str) -> bool:
    """
    Validate zone ID format.
    
    Args:
        zone_id: Zone identifier to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not zone_id or not isinstance(zone_id, str):
        return False
    
    # Zone ID should be 3-50 characters, alphanumeric with underscores and hyphens
    if len(zone_id) < 3 or len(zone_id) > 50:
        return False
    
    # Check character validity
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
    return all(c in allowed_chars for c in zone_id)


def validate_device_id(device_id: str) -> bool:
    """
    Validate device ID format.
    
    Args:
        device_id: Device identifier to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not device_id or not isinstance(device_id, str):
        return False
    
    # Device ID should be 3-100 characters
    if len(device_id) < 3 or len(device_id) > 100:
        return False
    
    # Allow more flexible format for device IDs (could include dots, colons)
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.:')
    return all(c in allowed_chars for c in device_id)


def sanitize_name(name: str, max_length: int = 100) -> str:
    """
    Sanitize user-provided names for zones, devices, and rules.
    
    Args:
        name: Name to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized name
    """
    if not name or not isinstance(name, str):
        return "Unnamed"
    
    # Remove leading/trailing whitespace
    name = name.strip()
    
    # Truncate if too long
    if len(name) > max_length:
        name = name[:max_length].strip()
    
    # If empty after processing, provide default
    if not name:
        return "Unnamed"
    
    return name


def parse_schedule_expression(schedule: str) -> Optional[dict]:
    """
    Parse cron-like schedule expression.
    
    Args:
        schedule: Schedule expression (simplified cron format)
        
    Returns:
        Parsed schedule dictionary or None if invalid
    """
    if not schedule or not isinstance(schedule, str):
        return None
    
    # Simplified parsing - in production would use proper cron library
    schedule = schedule.strip()
    
    # Handle common expressions
    common_schedules = {
        '@hourly': {'minute': 0},
        '@daily': {'hour': 0, 'minute': 0},
        '@weekly': {'day_of_week': 0, 'hour': 0, 'minute': 0},
        '@monthly': {'day': 1, 'hour': 0, 'minute': 0}
    }
    
    if schedule in common_schedules:
        return common_schedules[schedule]
    
    # Basic cron parsing (minute hour day month day_of_week)
    parts = schedule.split()
    if len(parts) != 5:
        return None
    
    try:
        return {
            'minute': int(parts[0]) if parts[0] != '*' else None,
            'hour': int(parts[1]) if parts[1] != '*' else None,
            'day': int(parts[2]) if parts[2] != '*' else None,
            'month': int(parts[3]) if parts[3] != '*' else None,
            'day_of_week': int(parts[4]) if parts[4] != '*' else None
        }
    except ValueError:
        return None


def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calculate Euclidean distance between two coordinates.
    
    Args:
        coord1: First coordinate (x, y)
        coord2: Second coordinate (x, y)
        
    Returns:
        Distance between coordinates
    """
    import math
    
    x1, y1 = coord1
    x2, y2 = coord2
    
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def group_devices_by_proximity(devices: list, max_distance: float = 5.0) -> list:
    """
    Group devices by physical proximity.
    
    Args:
        devices: List of devices with location coordinates
        max_distance: Maximum distance for grouping
        
    Returns:
        List of device groups
    """
    if not devices:
        return []
    
    groups = []
    ungrouped_devices = devices.copy()
    
    while ungrouped_devices:
        # Start new group with first ungrouped device
        current_group = [ungrouped_devices.pop(0)]
        
        # Find all devices within max_distance of any device in current group
        i = 0
        while i < len(ungrouped_devices):
            device = ungrouped_devices[i]
            
            # Check if device is close to any device in current group
            should_add = False
            for group_device in current_group:
                if (hasattr(device, 'coordinates') and hasattr(group_device, 'coordinates') and
                    device.coordinates and group_device.coordinates):
                    
                    distance = calculate_distance(device.coordinates, group_device.coordinates)
                    if distance <= max_distance:
                        should_add = True
                        break
            
            if should_add:
                current_group.append(ungrouped_devices.pop(i))
            else:
                i += 1
        
        groups.append(current_group)
    
    return groups


def normalize_score(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    Normalize a score to a specific range.
    
    Args:
        value: Value to normalize
        min_val: Minimum value of range
        max_val: Maximum value of range
        
    Returns:
        Normalized value
    """
    if value < min_val:
        return min_val
    elif value > max_val:
        return max_val
    else:
        return value


def calculate_weighted_average(values: list, weights: Optional[list] = None) -> float:
    """
    Calculate weighted average of values.
    
    Args:
        values: List of values
        weights: List of weights (equal weights if None)
        
    Returns:
        Weighted average
    """
    if not values:
        return 0.0
    
    if weights is None:
        weights = [1.0] * len(values)
    
    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")
    
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    total_weight = sum(weights)
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def exponential_moving_average(current_value: float, new_value: float, alpha: float = 0.1) -> float:
    """
    Calculate exponential moving average.
    
    Args:
        current_value: Current EMA value
        new_value: New value to incorporate
        alpha: Smoothing factor (0-1)
        
    Returns:
        Updated EMA value
    """
    return alpha * new_value + (1 - alpha) * current_value


def is_time_in_range(start_time: str, end_time: str, current_time: Optional[datetime] = None) -> bool:
    """
    Check if current time is within specified range.
    
    Args:
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
        current_time: Current time (uses now() if None)
        
    Returns:
        True if current time is in range
    """
    if current_time is None:
        current_time = datetime.now()
    
    try:
        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))
        
        current_minutes = current_time.hour * 60 + current_time.minute
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        
        if start_minutes <= end_minutes:
            # Same day range
            return start_minutes <= current_minutes <= end_minutes
        else:
            # Overnight range
            return current_minutes >= start_minutes or current_minutes <= end_minutes
            
    except (ValueError, IndexError):
        return False


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        Division result or default
    """
    return numerator / denominator if denominator != 0 else default


def deep_merge_dict(dict1: dict, dict2: dict) -> dict:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_calls: int, time_window: float):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Acquire permission to make a call.
        
        Returns:
            True if call is allowed, False if rate limited
        """
        async with self.lock:
            now = time.time()
            
            # Remove old calls outside time window
            self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
            
            # Check if we can make a new call
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            else:
                return False
    
    async def wait_until_available(self) -> None:
        """Wait until a call slot becomes available."""
        while True:
            if await self.acquire():
                return
            await asyncio.sleep(0.1)


# Example usage and testing
if __name__ == "__main__":
    async def test_utilities():
        """Test utility functions."""
        
        # Test retry decorator
        @retry(tries=3, delay=0.1)
        async def flaky_function(should_fail=True):
            if should_fail:
                raise ValueError("Test error")
            return "Success"
        
        # Test timing decorator
        @timing
        async def timed_function():
            await asyncio.sleep(0.1)
            return "Completed"
        
        print("Testing utilities...")
        
        # Test validation
        assert validate_zone_id("living_room_1") == True
        assert validate_zone_id("") == False
        assert validate_device_id("light.living_room") == True
        
        # Test sanitization
        assert sanitize_name("  Living Room  ") == "Living Room"
        assert sanitize_name("") == "Unnamed"
        
        # Test schedule parsing
        schedule = parse_schedule_expression("0 8 * * *")
        assert schedule == {'minute': 0, 'hour': 8, 'day': None, 'month': None, 'day_of_week': None}
        
        # Test time range
        assert is_time_in_range("09:00", "17:00", datetime.now().replace(hour=12, minute=0)) == True
        
        # Test rate limiter
        limiter = RateLimiter(max_calls=2, time_window=1.0)
        assert await limiter.acquire() == True
        assert await limiter.acquire() == True
        assert await limiter.acquire() == False
        
        print("All utility tests passed!")
    
    # Run tests
    asyncio.run(test_utilities())