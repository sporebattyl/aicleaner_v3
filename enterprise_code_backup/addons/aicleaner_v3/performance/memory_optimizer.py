"""
Memory-Efficient Data Processing
Phase 5A: Performance Optimization

Provides memory-optimized data structures and processing patterns.
"""

import sys
from typing import Iterator, List, Dict, Any, Generator, Optional, Callable
from itertools import islice
import gc

class MemoryOptimizer:
    """Memory optimization utilities for large data processing"""
    
    @staticmethod
    def chunked_iterator(iterable: Iterator, chunk_size: int) -> Generator[List[Any], None, None]:
        """
        Break an iterable into chunks of specified size
        
        Args:
            iterable: Input iterable
            chunk_size: Size of each chunk
            
        Yields:
            Lists of items up to chunk_size
        """
        iterator = iter(iterable)
        while True:
            chunk = list(islice(iterator, chunk_size))
            if not chunk:
                break
            yield chunk
    
    @staticmethod
    def memory_efficient_filter(data: Iterator[Any], 
                              predicate: Callable[[Any], bool]) -> Generator[Any, None, None]:
        """
        Memory-efficient filtering using generators
        
        Args:
            data: Input data iterator
            predicate: Function to test each item
            
        Yields:
            Items that pass the predicate test
        """
        for item in data:
            if predicate(item):
                yield item
    
    @staticmethod
    def memory_efficient_map(data: Iterator[Any], 
                           func: Callable[[Any], Any]) -> Generator[Any, None, None]:
        """
        Memory-efficient mapping using generators
        
        Args:
            data: Input data iterator
            func: Function to apply to each item
            
        Yields:
            Transformed items
        """
        for item in data:
            yield func(item)
    
    @staticmethod
    def batch_process_generator(data: Iterator[Any], 
                              processor: Callable[[List[Any]], List[Any]],
                              batch_size: int = 1000) -> Generator[Any, None, None]:
        """
        Process data in batches to control memory usage
        
        Args:
            data: Input data iterator
            processor: Function to process each batch
            batch_size: Size of each processing batch
            
        Yields:
            Processed items
        """
        for batch in MemoryOptimizer.chunked_iterator(data, batch_size):
            processed_batch = processor(batch)
            for item in processed_batch:
                yield item
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Get current memory usage statistics"""
        try:
            import resource
            memory_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # Convert to MB (Linux reports in KB)
            memory_mb = memory_kb / 1024
            
            return {
                "memory_mb": memory_mb,
                "objects_count": len(gc.get_objects()),
                "garbage_count": len(gc.garbage)
            }
        except:
            return {"memory_mb": 0, "objects_count": 0, "garbage_count": 0}
    
    @staticmethod
    def force_garbage_collection() -> Dict[str, int]:
        """Force garbage collection and return statistics"""
        collected = gc.collect()
        return {
            "collected_objects": collected,
            "remaining_objects": len(gc.get_objects()),
            "garbage_objects": len(gc.garbage)
        }

class EntityDataProcessor:
    """Memory-efficient processing for Home Assistant entity data"""
    
    def __init__(self, max_batch_size: int = 1000):
        self.max_batch_size = max_batch_size
        self.memory_optimizer = MemoryOptimizer()
    
    def process_entity_states(self, entities: Iterator[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
        """
        Process entity states efficiently using generators
        
        Args:
            entities: Iterator of entity state dictionaries
            
        Yields:
            Processed entity states
        """
        def process_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
            """Process a single entity state"""
            return {
                "entity_id": entity.get("entity_id"),
                "state": entity.get("state"),
                "last_changed": entity.get("last_changed"),
                "attributes": {
                    k: v for k, v in entity.get("attributes", {}).items()
                    if k in ["friendly_name", "unit_of_measurement", "device_class"]
                },
                "processed_at": entity.get("last_updated")
            }
        
        # Use memory-efficient mapping
        return self.memory_optimizer.memory_efficient_map(entities, process_entity)
    
    def aggregate_sensor_data(self, sensor_data: Iterator[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate sensor data efficiently with minimal memory usage
        
        Args:
            sensor_data: Iterator of sensor data points
            
        Returns:
            Aggregated statistics
        """
        count = 0
        total = 0.0
        min_value = float('inf')
        max_value = float('-inf')
        
        # Process data one item at a time
        for data_point in sensor_data:
            try:
                value = float(data_point.get("value", 0))
                count += 1
                total += value
                min_value = min(min_value, value)
                max_value = max(max_value, value)
            except (ValueError, TypeError):
                continue
        
        if count == 0:
            return {"count": 0, "average": 0, "min": 0, "max": 0}
        
        return {
            "count": count,
            "average": total / count,
            "min": min_value if min_value != float('inf') else 0,
            "max": max_value if max_value != float('-inf') else 0,
            "total": total
        }
    
    def filter_entities_by_domain(self, entities: Iterator[Dict[str, Any]], 
                                 domain: str) -> Generator[Dict[str, Any], None, None]:
        """
        Filter entities by domain efficiently
        
        Args:
            entities: Iterator of entity dictionaries
            domain: Domain to filter by (e.g., 'sensor', 'switch')
            
        Yields:
            Filtered entities
        """
        def domain_filter(entity: Dict[str, Any]) -> bool:
            entity_id = entity.get("entity_id", "")
            return entity_id.startswith(f"{domain}.")
        
        return self.memory_optimizer.memory_efficient_filter(entities, domain_filter)

class ConfigDataProcessor:
    """Memory-efficient processing for configuration data"""
    
    def __init__(self):
        self.memory_optimizer = MemoryOptimizer()
    
    def merge_configs_efficiently(self, config_sources: Iterator[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple configuration sources efficiently
        
        Args:
            config_sources: Iterator of configuration dictionaries
            
        Returns:
            Merged configuration
        """
        merged_config = {}
        
        for config in config_sources:
            # Process config one at a time to minimize memory usage
            if isinstance(config, dict):
                for key, value in config.items():
                    if key in merged_config and isinstance(merged_config[key], dict) and isinstance(value, dict):
                        # Recursively merge dictionaries
                        merged_config[key].update(value)
                    else:
                        merged_config[key] = value
        
        return merged_config
    
    def validate_config_efficiently(self, config: Dict[str, Any], 
                                  validation_rules: Dict[str, Callable]) -> Generator[Dict[str, Any], None, None]:
        """
        Validate configuration efficiently using generators
        
        Args:
            config: Configuration to validate
            validation_rules: Dictionary of validation functions
            
        Yields:
            Validation results
        """
        for key, validator in validation_rules.items():
            if key in config:
                try:
                    is_valid = validator(config[key])
                    yield {
                        "key": key,
                        "valid": is_valid,
                        "value": config[key] if is_valid else None,
                        "error": None
                    }
                except Exception as e:
                    yield {
                        "key": key,
                        "valid": False,
                        "value": None,
                        "error": str(e)
                    }
            else:
                yield {
                    "key": key,
                    "valid": False,
                    "value": None,
                    "error": "Key not found in configuration"
                }

class LogDataProcessor:
    """Memory-efficient processing for log data"""
    
    def __init__(self, max_buffer_size: int = 10000):
        self.max_buffer_size = max_buffer_size
        self.memory_optimizer = MemoryOptimizer()
    
    def process_log_stream(self, log_entries: Iterator[str]) -> Generator[Dict[str, Any], None, None]:
        """
        Process log entries efficiently
        
        Args:
            log_entries: Iterator of log entry strings
            
        Yields:
            Parsed log entries
        """
        def parse_log_entry(entry: str) -> Dict[str, Any]:
            """Parse a single log entry"""
            parts = entry.strip().split(" - ", 3)
            if len(parts) >= 4:
                return {
                    "timestamp": parts[0],
                    "logger": parts[1],
                    "level": parts[2],
                    "message": parts[3],
                    "parsed": True
                }
            else:
                return {
                    "raw": entry,
                    "parsed": False
                }
        
        return self.memory_optimizer.memory_efficient_map(log_entries, parse_log_entry)
    
    def filter_log_level(self, log_entries: Iterator[Dict[str, Any]], 
                        level: str) -> Generator[Dict[str, Any], None, None]:
        """
        Filter log entries by level efficiently
        
        Args:
            log_entries: Iterator of parsed log entries
            level: Log level to filter by
            
        Yields:
            Filtered log entries
        """
        def level_filter(entry: Dict[str, Any]) -> bool:
            return entry.get("level", "").upper() == level.upper()
        
        return self.memory_optimizer.memory_efficient_filter(log_entries, level_filter)

# Global processors
entity_processor = EntityDataProcessor(max_batch_size=500)
config_processor = ConfigDataProcessor()
log_processor = LogDataProcessor(max_buffer_size=5000)

# Convenience functions
def process_entities_efficiently(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process entity list efficiently"""
    return list(entity_processor.process_entity_states(iter(entities)))

def aggregate_sensor_data_efficiently(sensor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate sensor data efficiently"""
    return entity_processor.aggregate_sensor_data(iter(sensor_data))

def merge_configurations_efficiently(configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge configuration list efficiently"""
    return config_processor.merge_configs_efficiently(iter(configs))

def get_memory_stats() -> Dict[str, Any]:
    """Get current memory statistics"""
    return MemoryOptimizer.get_memory_usage()

def cleanup_memory() -> Dict[str, int]:
    """Force memory cleanup and return stats"""
    return MemoryOptimizer.force_garbage_collection()