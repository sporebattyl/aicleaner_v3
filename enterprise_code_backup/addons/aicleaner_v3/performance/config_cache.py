"""
Configuration Caching Layer
Phase 5A: Performance Optimization

Provides in-memory caching for configuration data to reduce file I/O.
"""

import os
import json
import time
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

class ConfigCache:
    """Thread-safe configuration cache with file watching and TTL"""
    
    def __init__(self, default_ttl: int = 600, max_cache_size: int = 100):
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, float] = {}
        self._file_timestamps: Dict[str, float] = {}
        self._cache_lock = asyncio.Lock()
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_size
        self._hit_count = 0
        self._miss_count = 0
        
    async def get_config(self, config_path: str, 
                        reload_interval: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get configuration from cache or load from file
        
        Args:
            config_path: Path to configuration file
            reload_interval: Override default TTL for this config
            
        Returns:
            Configuration dictionary or None if not found
        """
        cache_key = self._get_cache_key(config_path)
        ttl = reload_interval or self.default_ttl
        
        async with self._cache_lock:
            # Check if cached and not expired
            if (cache_key in self._cache and 
                self._cache_expiry[cache_key] > time.time() and
                not self._is_file_modified(config_path)):
                
                self._hit_count += 1
                return self._cache[cache_key]
            
            # Load from file
            config_data = await self._load_config_file(config_path)
            if config_data is not None:
                # Cache the loaded config
                await self._set_cache_entry(cache_key, config_data, ttl, config_path)
                self._miss_count += 1
                return config_data
            
            self._miss_count += 1
            return None
    
    async def set_config(self, config_path: str, config_data: Dict[str, Any],
                        ttl: Optional[int] = None) -> None:
        """
        Set configuration in cache and optionally save to file
        
        Args:
            config_path: Path to configuration file
            config_data: Configuration data to cache
            ttl: Time to live for cached data
        """
        cache_key = self._get_cache_key(config_path)
        ttl = ttl or self.default_ttl
        
        async with self._cache_lock:
            await self._set_cache_entry(cache_key, config_data, ttl, config_path)
    
    async def invalidate_config(self, config_path: str) -> bool:
        """
        Invalidate cached configuration
        
        Args:
            config_path: Path to configuration file to invalidate
            
        Returns:
            True if config was cached and invalidated
        """
        cache_key = self._get_cache_key(config_path)
        
        async with self._cache_lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                del self._cache_expiry[cache_key]
                if config_path in self._file_timestamps:
                    del self._file_timestamps[config_path]
                return True
            return False
    
    async def clear_cache(self) -> None:
        """Clear all cached configurations"""
        async with self._cache_lock:
            self._cache.clear()
            self._cache_expiry.clear()
            self._file_timestamps.clear()
            self._hit_count = 0
            self._miss_count = 0
    
    async def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = []
        
        async with self._cache_lock:
            for cache_key, expiry_time in self._cache_expiry.items():
                if expiry_time <= current_time:
                    expired_keys.append(cache_key)
            
            for cache_key in expired_keys:
                del self._cache[cache_key]
                del self._cache_expiry[cache_key]
                # Note: We keep file_timestamps for file modification checking
        
        return len(expired_keys)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self._cache),
            "max_size": self.max_cache_size,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            "cached_files": len(self._file_timestamps)
        }
    
    def _get_cache_key(self, config_path: str) -> str:
        """Generate cache key from config path"""
        return hashlib.md5(config_path.encode()).hexdigest()
    
    async def _load_config_file(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Load configuration from file"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                return None
            
            # Update file timestamp
            self._file_timestamps[config_path] = config_file.stat().st_mtime
            
            # Load based on file extension
            with open(config_file, 'r') as f:
                if config_path.endswith('.json'):
                    return json.load(f)
                elif config_path.endswith(('.yml', '.yaml')):
                    try:
                        import yaml
                        return yaml.safe_load(f)
                    except ImportError:
                        # Fallback to JSON if yaml not available
                        return json.load(f)
                else:
                    # Assume JSON format
                    return json.load(f)
                    
        except Exception as e:
            print(f"Error loading config file {config_path}: {e}")
            return None
    
    async def _set_cache_entry(self, cache_key: str, config_data: Dict[str, Any],
                             ttl: int, config_path: str) -> None:
        """Set cache entry with TTL"""
        # Implement simple LRU by removing oldest entry if at max size
        if len(self._cache) >= self.max_cache_size:
            oldest_key = min(self._cache_expiry.keys(), 
                           key=lambda k: self._cache_expiry[k])
            del self._cache[oldest_key]
            del self._cache_expiry[oldest_key]
        
        self._cache[cache_key] = config_data
        self._cache_expiry[cache_key] = time.time() + ttl
    
    def _is_file_modified(self, config_path: str) -> bool:
        """Check if configuration file has been modified since last load"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                return True
            
            current_mtime = config_file.stat().st_mtime
            cached_mtime = self._file_timestamps.get(config_path, 0)
            
            return current_mtime > cached_mtime
            
        except Exception:
            # If we can't check, assume it's modified
            return True

class ConfigManager:
    """Enhanced configuration manager with caching"""
    
    def __init__(self, config_cache: Optional[ConfigCache] = None):
        self.cache = config_cache or ConfigCache()
        self.watchers: Dict[str, bool] = {}
        
    async def get_config(self, config_path: str, 
                        reload_interval: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get configuration with caching
        
        Args:
            config_path: Path to configuration file
            reload_interval: Cache TTL override
            
        Returns:
            Configuration dictionary
        """
        return await self.cache.get_config(config_path, reload_interval)
    
    async def update_config(self, config_path: str, config_data: Dict[str, Any],
                          save_to_file: bool = True) -> bool:
        """
        Update configuration in cache and optionally save to file
        
        Args:
            config_path: Path to configuration file
            config_data: New configuration data
            save_to_file: Whether to save to file immediately
            
        Returns:
            True if successful
        """
        try:
            # Update cache
            await self.cache.set_config(config_path, config_data)
            
            # Save to file if requested
            if save_to_file:
                await self._save_config_file(config_path, config_data)
            
            return True
            
        except Exception as e:
            print(f"Error updating config {config_path}: {e}")
            return False
    
    async def reload_config(self, config_path: str) -> Optional[Dict[str, Any]]:
        """
        Force reload configuration from file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Reloaded configuration
        """
        # Invalidate cache first
        await self.cache.invalidate_config(config_path)
        
        # Load fresh from file
        return await self.cache.get_config(config_path)
    
    async def get_merged_config(self, config_paths: list[str]) -> Dict[str, Any]:
        """
        Get merged configuration from multiple sources
        
        Args:
            config_paths: List of configuration file paths
            
        Returns:
            Merged configuration dictionary
        """
        merged_config = {}
        
        for config_path in config_paths:
            config = await self.get_config(config_path)
            if config:
                # Deep merge configurations
                merged_config = self._deep_merge(merged_config, config)
        
        return merged_config
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in update.items():
            if (key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    async def _save_config_file(self, config_path: str, config_data: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w') as f:
                if config_path.endswith('.json'):
                    json.dump(config_data, f, indent=2)
                elif config_path.endswith(('.yml', '.yaml')):
                    try:
                        import yaml
                        yaml.dump(config_data, f, default_flow_style=False)
                    except ImportError:
                        # Fallback to JSON
                        json.dump(config_data, f, indent=2)
                else:
                    json.dump(config_data, f, indent=2)
                    
        except Exception as e:
            raise Exception(f"Failed to save config to {config_path}: {e}")

# Global instances
global_config_cache = ConfigCache(default_ttl=300, max_cache_size=50)
global_config_manager = ConfigManager(global_config_cache)

# Convenience functions
async def get_cached_config(config_path: str, reload_interval: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Get configuration using global cache"""
    return await global_config_manager.get_config(config_path, reload_interval)

async def update_cached_config(config_path: str, config_data: Dict[str, Any]) -> bool:
    """Update configuration using global cache"""
    return await global_config_manager.update_config(config_path, config_data)

async def get_config_cache_stats() -> Dict[str, Any]:
    """Get global configuration cache statistics"""
    return global_config_cache.get_cache_stats()

async def clear_config_cache() -> None:
    """Clear global configuration cache"""
    await global_config_cache.clear_cache()

# Cache maintenance task
async def config_cache_maintenance_task():
    """Background task for configuration cache maintenance"""
    while True:
        try:
            removed_count = await global_config_cache.cleanup_expired()
            if removed_count > 0:
                print(f"Config cache maintenance: removed {removed_count} expired entries")
            
            # Run maintenance every 10 minutes
            await asyncio.sleep(600)
            
        except Exception as e:
            print(f"Config cache maintenance error: {e}")
            await asyncio.sleep(60)  # Retry in 1 minute on error