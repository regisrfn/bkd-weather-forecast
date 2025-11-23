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
    
    Emits START and END logs for each span with duration measurement.
    Simple and clear approach without context management complexity.
    
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
            
            # Get logger
            logger = None
            try:
                from aws_lambda_powertools import Logger
                logger = Logger(child=True)
            except Exception:
                pass
            
            # Emit START log
            if logger:
                try:
                    logger.info(
                        f"Span started: {span_name}",
                        extra={
                            "span_name": span_name,
                            "trace_id": trace_id,
                            "span_event": "start"
                        }
                    )
                except Exception:
                    pass
            
            # Start timing
            start_time = time.time()
            
            # Execute function
            error_occurred = False
            error_message = None
            try:
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                error_occurred = True
                error_message = str(e)
                raise
                
            finally:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Emit END log with duration
                if logger:
                    try:
                        status = "failed" if error_occurred else "completed"
                        log_data = {
                            "span_name": span_name,
                            "trace_id": trace_id,
                            "span_event": "end",
                            "span_duration_ms": duration_ms,
                            "status": status
                        }
                        
                        if error_occurred and error_message:
                            log_data["error_message"] = error_message
                        
                        logger.info(
                            f"Span {status}: {span_name} ({duration_ms:.2f}ms)",
                            extra=log_data
                        )
                    except Exception:
                        pass
        
        return wrapper
    return decorator


# Note: Each span emits two logs:
# 1. START log: {"span_event": "start", "span_name": "...", "trace_id": "..."}
# 2. END log: {"span_event": "end", "span_name": "...", "trace_id": "...", "span_duration_ms": 123.45, "status": "completed|failed"}
#
# This simple approach avoids context management complexity and provides clear visibility
# of span lifecycle and performance metrics.
