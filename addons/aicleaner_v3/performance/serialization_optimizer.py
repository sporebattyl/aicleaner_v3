"""
Data Serialization Optimization
Phase 5A: Performance Optimization

Optimizes JSON serialization/deserialization using orjson for better performance.
"""

import json
import logging
import time
from typing import Any, Dict, Union, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

# Try to import orjson for better performance
try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SerializationMetrics:
    """Serialization performance metrics"""
    total_serializations: int = 0
    total_deserializations: int = 0
    total_serialize_time: float = 0.0
    total_deserialize_time: float = 0.0
    average_serialize_time: float = 0.0
    average_deserialize_time: float = 0.0
    total_data_size: int = 0
    orjson_used: bool = False


class SerializationOptimizer:
    """
    Optimizes JSON serialization/deserialization for better performance.
    
    Features:
    - Uses orjson when available for 2-3x better performance
    - Fallback to standard json module
    - Performance metrics tracking
    - Custom serializers for common data types
    - Compression for large payloads
    """
    
    def __init__(self, 
                 use_orjson: bool = True,
                 compression_threshold: int = 1024,
                 enable_metrics: bool = True):
        """
        Initialize serialization optimizer.
        
        Args:
            use_orjson: Use orjson if available
            compression_threshold: Compress data larger than this size
            enable_metrics: Enable performance metrics tracking
        """
        self.use_orjson = use_orjson and ORJSON_AVAILABLE
        self.compression_threshold = compression_threshold
        self.enable_metrics = enable_metrics
        
        # Metrics
        self.metrics = SerializationMetrics()
        self.metrics.orjson_used = self.use_orjson
        
        # Custom serializers
        self._custom_serializers: Dict[type, callable] = {}
        self._custom_deserializers: Dict[str, callable] = {}
        
        # Register default serializers
        self._register_default_serializers()
        
        logger.info(f"Serialization optimizer initialized (orjson: {self.use_orjson})")
    
    def _register_default_serializers(self) -> None:
        """Register default custom serializers."""
        # DateTime serializer
        self.register_serializer(datetime, lambda dt: {
            "__type": "datetime",
            "value": dt.isoformat()
        })
        
        self.register_deserializer("datetime", lambda data: 
            datetime.fromisoformat(data["value"])
        )
    
    def register_serializer(self, data_type: type, serializer: callable) -> None:
        """
        Register custom serializer for a data type.
        
        Args:
            data_type: Type to serialize
            serializer: Function to serialize the type
        """
        self._custom_serializers[data_type] = serializer
        logger.debug(f"Registered custom serializer for {data_type.__name__}")
    
    def register_deserializer(self, type_name: str, deserializer: callable) -> None:
        """
        Register custom deserializer for a type.
        
        Args:
            type_name: Type name identifier
            deserializer: Function to deserialize the type
        """
        self._custom_deserializers[type_name] = deserializer
        logger.debug(f"Registered custom deserializer for {type_name}")
    
    def serialize(self, data: Any, compress: bool = False) -> Union[str, bytes]:
        """
        Serialize data to JSON with optimizations.
        
        Args:
            data: Data to serialize
            compress: Force compression regardless of size
            
        Returns:
            Serialized data as string or bytes
        """
        start_time = time.perf_counter()
        
        try:
            # Preprocess data with custom serializers
            processed_data = self._preprocess_for_serialization(data)
            
            if self.use_orjson:
                # Use orjson for better performance
                result = orjson.dumps(
                    processed_data,
                    option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY
                )
                # orjson returns bytes, convert to string if needed
                if not compress:
                    result = result.decode('utf-8')
            else:
                # Fallback to standard json
                result = json.dumps(processed_data, default=self._json_serializer, ensure_ascii=False)
                if compress:
                    result = result.encode('utf-8')
            
            # Apply compression if needed
            if compress or (isinstance(result, (str, bytes)) and len(result) > self.compression_threshold):
                result = self._compress_data(result)
            
            # Update metrics
            if self.enable_metrics:
                serialize_time = time.perf_counter() - start_time
                self.metrics.total_serializations += 1
                self.metrics.total_serialize_time += serialize_time
                self.metrics.average_serialize_time = (
                    self.metrics.total_serialize_time / self.metrics.total_serializations
                )
                self.metrics.total_data_size += len(result) if isinstance(result, (str, bytes)) else 0
            
            return result
            
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            raise
    
    def deserialize(self, data: Union[str, bytes], decompress: bool = False) -> Any:
        """
        Deserialize JSON data with optimizations.
        
        Args:
            data: Serialized data
            decompress: Data is compressed
            
        Returns:
            Deserialized data
        """
        start_time = time.perf_counter()
        
        try:
            # Decompress if needed
            if decompress or self._is_compressed(data):
                data = self._decompress_data(data)
            
            if self.use_orjson:
                # Use orjson for better performance
                if isinstance(data, str):
                    data = data.encode('utf-8')
                result = orjson.loads(data)
            else:
                # Fallback to standard json
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                result = json.loads(data)
            
            # Postprocess data with custom deserializers
            result = self._postprocess_from_serialization(result)
            
            # Update metrics
            if self.enable_metrics:
                deserialize_time = time.perf_counter() - start_time
                self.metrics.total_deserializations += 1
                self.metrics.total_deserialize_time += deserialize_time
                self.metrics.average_deserialize_time = (
                    self.metrics.total_deserialize_time / self.metrics.total_deserializations
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            raise
    
    async def serialize_async(self, data: Any, compress: bool = False) -> Union[str, bytes]:
        """
        Asynchronous serialization for large data.
        
        Args:
            data: Data to serialize
            compress: Force compression
            
        Returns:
            Serialized data
        """
        # For very large data, run in thread pool to avoid blocking
        if self._estimate_size(data) > 10000:  # 10KB threshold
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.serialize, data, compress)
        else:
            return self.serialize(data, compress)
    
    async def deserialize_async(self, data: Union[str, bytes], decompress: bool = False) -> Any:
        """
        Asynchronous deserialization for large data.
        
        Args:
            data: Serialized data
            decompress: Data is compressed
            
        Returns:
            Deserialized data
        """
        # For very large data, run in thread pool to avoid blocking
        if len(data) > 10000:  # 10KB threshold
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.deserialize, data, decompress)
        else:
            return self.deserialize(data, decompress)
    
    def _preprocess_for_serialization(self, data: Any) -> Any:
        """Preprocess data using custom serializers."""
        if type(data) in self._custom_serializers:
            return self._custom_serializers[type(data)](data)
        elif isinstance(data, dict):
            return {k: self._preprocess_for_serialization(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._preprocess_for_serialization(item) for item in data]
        else:
            return data
    
    def _postprocess_from_serialization(self, data: Any) -> Any:
        """Postprocess data using custom deserializers."""
        if isinstance(data, dict):
            # Check if this is a custom serialized object
            if "__type" in data and data["__type"] in self._custom_deserializers:
                return self._custom_deserializers[data["__type"]](data)
            else:
                return {k: self._postprocess_from_serialization(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._postprocess_from_serialization(item) for item in data]
        else:
            return data
    
    def _json_serializer(self, obj: Any) -> Any:
        """Default JSON serializer for unsupported types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    def _compress_data(self, data: Union[str, bytes]) -> bytes:
        """Compress data using gzip."""
        import gzip
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return gzip.compress(data)
    
    def _decompress_data(self, data: bytes) -> str:
        """Decompress gzipped data."""
        import gzip
        
        try:
            return gzip.decompress(data).decode('utf-8')
        except Exception:
            # If decompression fails, assume it's not compressed
            if isinstance(data, bytes):
                return data.decode('utf-8')
            return data
    
    def _is_compressed(self, data: Union[str, bytes]) -> bool:
        """Check if data is gzip compressed."""
        if isinstance(data, bytes) and len(data) >= 2:
            return data[:2] == b'\x1f\x8b'  # gzip magic number
        return False
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate the size of data object."""
        try:
            import sys
            return sys.getsizeof(data)
        except Exception:
            return 1000  # Default estimate
    
    def get_metrics(self) -> SerializationMetrics:
        """Get serialization metrics."""
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        orjson_used = self.metrics.orjson_used
        self.metrics = SerializationMetrics()
        self.metrics.orjson_used = orjson_used
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get detailed performance report."""
        return {
            "orjson_available": ORJSON_AVAILABLE,
            "orjson_used": self.use_orjson,
            "compression_threshold": self.compression_threshold,
            "metrics": {
                "total_serializations": self.metrics.total_serializations,
                "total_deserializations": self.metrics.total_deserializations,
                "average_serialize_time_ms": self.metrics.average_serialize_time * 1000,
                "average_deserialize_time_ms": self.metrics.average_deserialize_time * 1000,
                "total_data_size_mb": self.metrics.total_data_size / (1024 * 1024),
                "serializations_per_second": (
                    self.metrics.total_serializations / max(0.001, self.metrics.total_serialize_time)
                    if self.metrics.total_serialize_time > 0 else 0
                ),
                "deserializations_per_second": (
                    self.metrics.total_deserializations / max(0.001, self.metrics.total_deserialize_time)
                    if self.metrics.total_deserialize_time > 0 else 0
                )
            },
            "custom_serializers": len(self._custom_serializers),
            "custom_deserializers": len(self._custom_deserializers)
        }


# Global serializer instance
_serialization_optimizer: Optional[SerializationOptimizer] = None


def get_serialization_optimizer(
    use_orjson: bool = True,
    compression_threshold: int = 1024,
    enable_metrics: bool = True
) -> SerializationOptimizer:
    """
    Get global serialization optimizer instance.
    
    Args:
        use_orjson: Use orjson if available
        compression_threshold: Compress data larger than this size
        enable_metrics: Enable performance metrics tracking
        
    Returns:
        SerializationOptimizer instance
    """
    global _serialization_optimizer
    
    if _serialization_optimizer is None:
        _serialization_optimizer = SerializationOptimizer(
            use_orjson=use_orjson,
            compression_threshold=compression_threshold,
            enable_metrics=enable_metrics
        )
    
    return _serialization_optimizer


# Convenience functions
def fast_json_dumps(data: Any, compress: bool = False) -> Union[str, bytes]:
    """Fast JSON serialization using optimizations."""
    optimizer = get_serialization_optimizer()
    return optimizer.serialize(data, compress=compress)


def fast_json_loads(data: Union[str, bytes], decompress: bool = False) -> Any:
    """Fast JSON deserialization using optimizations."""
    optimizer = get_serialization_optimizer()
    return optimizer.deserialize(data, decompress=decompress)


async def fast_json_dumps_async(data: Any, compress: bool = False) -> Union[str, bytes]:
    """Async fast JSON serialization."""
    optimizer = get_serialization_optimizer()
    return await optimizer.serialize_async(data, compress=compress)


async def fast_json_loads_async(data: Union[str, bytes], decompress: bool = False) -> Any:
    """Async fast JSON deserialization."""
    optimizer = get_serialization_optimizer()
    return await optimizer.deserialize_async(data, decompress=decompress)


def optimize_json_calls():
    """
    Decorator to automatically optimize json.dumps/loads calls in a function.
    
    This replaces standard json calls with optimized versions.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Temporarily replace json functions
            original_dumps = json.dumps
            original_loads = json.loads
            
            try:
                json.dumps = fast_json_dumps
                json.loads = fast_json_loads
                return func(*args, **kwargs)
            finally:
                # Restore original functions
                json.dumps = original_dumps
                json.loads = original_loads
        
        return wrapper
    return decorator