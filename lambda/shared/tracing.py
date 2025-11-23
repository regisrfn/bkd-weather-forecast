"""
Distributed Tracing Library - Flat Span Model
Copy this file to any application that needs observability tracing.

Usage:
    from shared.tracing import trace_operation, get_trace_id, set_trace_id
    
    @trace_operation("operation_name")
    def my_function():
        # Your code here
        pass
    
    # Manual trace_id propagation
    trace_id = get_trace_id()  # Get current trace_id
    set_trace_id(trace_id)     # Set trace_id in new context
"""

import json
import time
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Optional, Callable, Any
from datetime import datetime

# Thread-safe trace_id storage
_trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


def get_trace_id() -> str:
    """Get current trace_id or generate new one."""
    trace_id = _trace_id_var.get()
    if not trace_id:
        trace_id = str(uuid.uuid4())
        _trace_id_var.set(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """Set trace_id for current context."""
    _trace_id_var.set(trace_id)


def clear_trace_id() -> None:
    """Clear trace_id from context."""
    _trace_id_var.set(None)


def trace_operation(span_name: str, level: str = "INFO"):
    """
    Decorator to trace operation execution with flat span model.
    
    Adds span_name to logger context for all logs within the decorated function.
    
    Args:
        span_name: Name of the span/operation (e.g., "api_get_neighbors", "db_query")
        level: Log level (default: INFO)
    
    Example:
        @trace_operation("calculate_distance")
        def calculate_distance(lat1, lon1, lat2, lon2):
            return math.sqrt((lat2-lat1)**2 + (lon2-lon1)**2)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get or generate trace_id
            trace_id = get_trace_id()
            
            # Add span_name to logger context (Powertools)
            try:
                from aws_lambda_powertools import Logger
                logger = Logger(child=True)
                logger.append_keys(span_name=span_name)
            except Exception:
                # Fallback if logger not available
                pass
            
            # Execute function
            try:
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                # Re-raise exception preserving stack trace
                raise
        
        return wrapper
    return decorator


# Note: Span metrics (span_name, duration_ms, trace_id) should be added
# to your application logs using logger.append_keys() or similar.
# This avoids duplicate logs while preserving observability data.
