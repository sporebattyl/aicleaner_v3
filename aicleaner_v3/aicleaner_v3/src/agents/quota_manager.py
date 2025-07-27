#!/usr/bin/env python3
"""
Gemini API Quota Manager
Handles intelligent API key cycling and quota optimization for Claude-Gemini collaboration
"""

import time
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ModelType(Enum):
    """Gemini model types with their characteristics"""
    PRO = "gemini-2.5-pro"
    FLASH = "gemini-2.5-flash"


@dataclass
class ApiKeyStatus:
    """Track status and quota usage for a single API key"""
    key_id: str
    api_key: str
    requests_today: int = 0
    requests_this_minute: int = 0
    last_request_time: float = 0
    last_minute_reset: float = field(default_factory=time.time)
    last_daily_reset: float = field(default_factory=time.time)
    is_available: bool = True
    error_count: int = 0
    
    @property
    def daily_remaining(self) -> int:
        """Get remaining daily quota"""
        return max(0, 250 - self.requests_today)
    
    @property
    def minute_remaining(self) -> int:
        """Get remaining per-minute quota"""
        return max(0, 10 - self.requests_this_minute)
    
    def reset_minute_counter(self):
        """Reset per-minute counter if enough time has passed"""
        current_time = time.time()
        if current_time - self.last_minute_reset >= 60:
            self.requests_this_minute = 0
            self.last_minute_reset = current_time
    
    def reset_daily_counter(self):
        """Reset daily counter if new day"""
        current_time = time.time()
        if current_time - self.last_daily_reset >= 86400:  # 24 hours
            self.requests_today = 0
            self.last_daily_reset = current_time
    
    def can_make_request(self) -> bool:
        """Check if key can make a request right now"""
        self.reset_minute_counter()
        self.reset_daily_counter()
        return (
            self.is_available 
            and self.daily_remaining > 0 
            and self.minute_remaining > 0
        )
    
    def record_request(self):
        """Record that a request was made with this key"""
        self.requests_today += 1
        self.requests_this_minute += 1
        self.last_request_time = time.time()
    
    def record_error(self):
        """Record an error with this key"""
        self.error_count += 1
        if self.error_count >= 5:  # Disable key after 5 errors
            self.is_available = False


class QuotaManager:
    """Manages quota and API key cycling for Gemini collaboration"""
    
    def __init__(self):
        self.api_keys: List[ApiKeyStatus] = []
        self.current_key_index = 0
        self.initialize_keys()
    
    def initialize_keys(self):
        """Initialize API keys from environment variables"""
        key_names = ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4"]
        
        for i, key_name in enumerate(key_names, 1):
            api_key = os.getenv(key_name)
            if api_key and api_key.strip():
                status = ApiKeyStatus(
                    key_id=f"key_{i}",
                    api_key=api_key.strip()
                )
                self.api_keys.append(status)
        
        if not self.api_keys:
            raise ValueError("No valid Gemini API keys found in environment variables")
    
    def get_optimal_key(self, model_type: ModelType = ModelType.FLASH) -> Optional[ApiKeyStatus]:
        """Get the optimal API key for a request"""
        
        # First pass: find keys with good quota
        for key in self.api_keys:
            if key.can_make_request() and key.daily_remaining > 10:
                return key
        
        # Second pass: find any available key
        for key in self.api_keys:
            if key.can_make_request():
                return key
        
        # No keys available
        return None
    
    def cycle_to_next_key(self) -> Optional[ApiKeyStatus]:
        """Cycle to the next available key"""
        start_index = self.current_key_index
        
        while True:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            key = self.api_keys[self.current_key_index]
            
            if key.can_make_request():
                return key
            
            # If we've cycled through all keys, return None
            if self.current_key_index == start_index:
                return None
    
    def select_model(self, task_complexity: str, quota_remaining: int) -> ModelType:
        """Intelligently select Gemini model based on task and quota"""
        
        if task_complexity == "high" and quota_remaining > 50:
            return ModelType.PRO
        elif task_complexity == "medium" and quota_remaining > 20:
            return ModelType.PRO
        else:
            return ModelType.FLASH
    
    def get_quota_status(self) -> Dict[str, Any]:
        """Get comprehensive quota status across all keys"""
        total_daily_remaining = sum(key.daily_remaining for key in self.api_keys)
        total_minute_remaining = sum(key.minute_remaining for key in self.api_keys)
        available_keys = len([key for key in self.api_keys if key.is_available])
        
        return {
            "total_daily_remaining": total_daily_remaining,
            "total_minute_remaining": total_minute_remaining,
            "available_keys": available_keys,
            "total_keys": len(self.api_keys),
            "key_details": [
                {
                    "key_id": key.key_id,
                    "daily_remaining": key.daily_remaining,
                    "minute_remaining": key.minute_remaining,
                    "is_available": key.is_available,
                    "error_count": key.error_count
                }
                for key in self.api_keys
            ]
        }
    
    def make_request(self, request_type: str, complexity: str = "medium") -> Dict[str, Any]:
        """Coordinate making a request with optimal key and model selection"""
        
        # Get quota status
        status = self.get_quota_status()
        
        # Select optimal key
        key = self.get_optimal_key()
        if not key:
            return {
                "success": False,
                "error": "No API keys available (quota exhausted)",
                "fallback": "claude_only_mode",
                "status": status
            }
        
        # Select optimal model
        model = self.select_model(complexity, status["total_daily_remaining"])
        
        # Record the request
        key.record_request()
        
        return {
            "success": True,
            "key_id": key.key_id,
            "api_key": key.api_key,
            "model": model.value,
            "quota_used": {
                "daily": 1,
                "minute": 1
            },
            "status": self.get_quota_status()
        }
    
    def handle_request_error(self, key_id: str, error_type: str):
        """Handle errors for specific API key"""
        for key in self.api_keys:
            if key.key_id == key_id:
                key.record_error()
                if error_type == "quota_exceeded":
                    # Temporarily disable this key
                    key.is_available = False
                break
    
    def get_batch_strategy(self, num_requests: int) -> Dict[str, Any]:
        """Get optimal batching strategy for multiple requests"""
        status = self.get_quota_status()
        
        if status["total_minute_remaining"] >= num_requests:
            return {
                "strategy": "immediate",
                "batch_size": num_requests,
                "estimated_time": "< 1 minute"
            }
        elif status["total_daily_remaining"] >= num_requests:
            return {
                "strategy": "throttled",
                "batch_size": min(status["total_minute_remaining"], 5),
                "estimated_time": f"{(num_requests / 5)} minutes"
            }
        else:
            return {
                "strategy": "partial",
                "batch_size": status["total_daily_remaining"],
                "estimated_time": "Limited by daily quota",
                "fallback": "claude_mode_for_remaining"
            }


# Example usage and testing
if __name__ == "__main__":
    # Initialize quota manager
    try:
        manager = QuotaManager()
        print("✓ Quota Manager initialized successfully")
        
        # Show initial status
        status = manager.get_quota_status()
        print(f"Total quota: {status['total_daily_remaining']}/1000 daily, {status['available_keys']}/{status['total_keys']} keys available")
        
        # Test request coordination
        result = manager.make_request("analysis", "high")
        if result["success"]:
            print(f"✓ Request coordinated: Key {result['key_id']}, Model {result['model']}")
        else:
            print(f"✗ Request failed: {result['error']}")
            
    except ValueError as e:
        print(f"✗ Initialization failed: {e}")
        print("Make sure GEMINI_API_KEY_1 through GEMINI_API_KEY_4 are set in environment")