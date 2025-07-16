"""
Enhanced Error Handling Utilities for AICleaner
Provides robust error handling, recovery mechanisms, and debugging support
"""
import functools
import asyncio
import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass
from enum import Enum
import json


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """Error recovery strategies"""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    FAIL_FAST = "fail_fast"


@dataclass
class ErrorPolicy:
    """Error handling policy configuration"""
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 60.0
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    fallback_function: Optional[Callable] = None
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 300.0
    severity: ErrorSeverity = ErrorSeverity.MEDIUM


class CircuitBreaker:
    """Circuit breaker implementation for error handling"""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 300.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func: Callable, *args, **kwargs):
        """Call function with circuit breaker protection"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise e


class ErrorHandler:
    """Enhanced error handler with multiple recovery strategies"""
    
    def __init__(self):
        self.circuit_breakers = {}
        self.error_policies = {}
        self.logger = logging.getLogger(__name__)
    
    def register_policy(self, operation_name: str, policy: ErrorPolicy):
        """Register error handling policy for an operation"""
        self.error_policies[operation_name] = policy
        
        if policy.recovery_strategy == RecoveryStrategy.CIRCUIT_BREAKER:
            self.circuit_breakers[operation_name] = CircuitBreaker(
                policy.circuit_breaker_threshold,
                policy.circuit_breaker_timeout
            )
    
    def handle_error(self, operation_name: str):
        """Decorator for error handling with policies"""
        def decorator(func: Callable):
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._execute_with_policy(operation_name, func, *args, **kwargs)
            
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._execute_with_policy_async(operation_name, func, *args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def _execute_with_policy(self, operation_name: str, func: Callable, *args, **kwargs):
        """Execute function with error handling policy"""
        policy = self.error_policies.get(operation_name, ErrorPolicy())
        
        last_exception = None
        
        for attempt in range(policy.max_retries + 1):
            try:
                # Circuit breaker check
                if policy.recovery_strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                    circuit_breaker = self.circuit_breakers.get(operation_name)
                    if circuit_breaker:
                        return circuit_breaker.call(func, *args, **kwargs)
                
                # Normal execution
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                self.logger.warning(
                    f"Error in {operation_name} (attempt {attempt + 1}/{policy.max_retries + 1}): {e}"
                )
                
                # If this is the last attempt, handle according to strategy
                if attempt == policy.max_retries:
                    return self._handle_final_failure(operation_name, policy, e, *args, **kwargs)
                
                # Calculate retry delay with exponential backoff
                delay = min(
                    policy.retry_delay * (policy.backoff_multiplier ** attempt),
                    policy.max_delay
                )
                
                time.sleep(delay)
        
        # Should not reach here, but handle gracefully
        return self._handle_final_failure(operation_name, policy, last_exception, *args, **kwargs)
    
    async def _execute_with_policy_async(self, operation_name: str, func: Callable, *args, **kwargs):
        """Execute async function with error handling policy"""
        policy = self.error_policies.get(operation_name, ErrorPolicy())
        
        last_exception = None
        
        for attempt in range(policy.max_retries + 1):
            try:
                # Circuit breaker check
                if policy.recovery_strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                    circuit_breaker = self.circuit_breakers.get(operation_name)
                    if circuit_breaker:
                        return circuit_breaker.call(func, *args, **kwargs)
                
                # Normal execution
                return await func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                self.logger.warning(
                    f"Error in {operation_name} (attempt {attempt + 1}/{policy.max_retries + 1}): {e}"
                )
                
                # If this is the last attempt, handle according to strategy
                if attempt == policy.max_retries:
                    return await self._handle_final_failure_async(operation_name, policy, e, *args, **kwargs)
                
                # Calculate retry delay with exponential backoff
                delay = min(
                    policy.retry_delay * (policy.backoff_multiplier ** attempt),
                    policy.max_delay
                )
                
                await asyncio.sleep(delay)
        
        # Should not reach here, but handle gracefully
        return await self._handle_final_failure_async(operation_name, policy, last_exception, *args, **kwargs)
    
    def _handle_final_failure(self, operation_name: str, policy: ErrorPolicy, 
                            exception: Exception, *args, **kwargs):
        """Handle final failure according to recovery strategy"""
        if policy.recovery_strategy == RecoveryStrategy.FALLBACK and policy.fallback_function:
            try:
                self.logger.info(f"Using fallback for {operation_name}")
                return policy.fallback_function(*args, **kwargs)
            except Exception as fallback_error:
                self.logger.error(f"Fallback failed for {operation_name}: {fallback_error}")
        
        elif policy.recovery_strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            self.logger.warning(f"Graceful degradation for {operation_name}")
            return None  # Return None instead of raising
        
        elif policy.recovery_strategy == RecoveryStrategy.FAIL_FAST:
            self.logger.error(f"Fail fast for {operation_name}: {exception}")
            raise exception
        
        # Default: log and re-raise
        self.logger.error(f"Final failure for {operation_name}: {exception}")
        raise exception
    
    async def _handle_final_failure_async(self, operation_name: str, policy: ErrorPolicy, 
                                        exception: Exception, *args, **kwargs):
        """Handle final failure for async functions"""
        if policy.recovery_strategy == RecoveryStrategy.FALLBACK and policy.fallback_function:
            try:
                self.logger.info(f"Using fallback for {operation_name}")
                if asyncio.iscoroutinefunction(policy.fallback_function):
                    return await policy.fallback_function(*args, **kwargs)
                else:
                    return policy.fallback_function(*args, **kwargs)
            except Exception as fallback_error:
                self.logger.error(f"Fallback failed for {operation_name}: {fallback_error}")
        
        elif policy.recovery_strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            self.logger.warning(f"Graceful degradation for {operation_name}")
            return None  # Return None instead of raising
        
        elif policy.recovery_strategy == RecoveryStrategy.FAIL_FAST:
            self.logger.error(f"Fail fast for {operation_name}: {exception}")
            raise exception
        
        # Default: log and re-raise
        self.logger.error(f"Final failure for {operation_name}: {exception}")
        raise exception


def safe_execute(func: Callable, default_value: Any = None, 
                log_errors: bool = True) -> Any:
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        default_value: Value to return on error
        log_errors: Whether to log errors
        
    Returns:
        Function result or default value on error
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger = logging.getLogger(__name__)
            logger.error(f"Safe execution failed: {e}")
        return default_value


async def safe_execute_async(func: Callable, default_value: Any = None, 
                           log_errors: bool = True) -> Any:
    """
    Safely execute an async function with error handling
    
    Args:
        func: Async function to execute
        default_value: Value to return on error
        log_errors: Whether to log errors
        
    Returns:
        Function result or default value on error
    """
    try:
        return await func()
    except Exception as e:
        if log_errors:
            logger = logging.getLogger(__name__)
            logger.error(f"Safe async execution failed: {e}")
        return default_value


def timeout_handler(timeout_seconds: float):
    """Decorator to add timeout handling to functions"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger = logging.getLogger(__name__)
                logger.error(f"Function {func.__name__} timed out after {timeout_seconds} seconds")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we can't easily add timeout without threading
            # This is a placeholder for sync timeout implementation
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def exception_context(additional_context: Dict[str, Any] = None):
    """Decorator to add context to exceptions"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Add context to exception
                context = {
                    'function': func.__name__,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys()),
                    'timestamp': time.time()
                }
                
                if additional_context:
                    context.update(additional_context)
                
                # Add context as exception attribute
                e.context = context
                raise e
        
        return wrapper
    return decorator


# Global error handler instance
global_error_handler = ErrorHandler()
