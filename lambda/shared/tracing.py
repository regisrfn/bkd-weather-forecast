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

import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Optional, Callable, Any

# Thread-safe trace_id storage
_trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)

# Thread-safe span stack for nested spans
_span_stack_var: ContextVar[list] = ContextVar('span_stack', default=None)


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
    
    Emits START/END marker logs for span boundaries (not persisted to DynamoDB).
    Adds span_name and trace_id context to all application logs within the span.
    
    Args:
        span_name: Name of the span/operation (e.g., "api_get_neighbors", "db_query")
        level: Log level (default: INFO)
    
    Example:
        @trace_operation("calculate_distance")
        def calculate_distance(lat1, lon1, lat2, lon2):
            logger.info("Calculating distance")  # Will have span_name in context
            return math.sqrt((lat2-lat1)**2 + (lon2-lon1)**2)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import time
            from datetime import datetime
            
            # Get or generate trace_id
            trace_id = get_trace_id()
            
            # Get global logger instance
            logger = None
            try:
                from aws_lambda_powertools import Logger
                logger = Logger()
            except Exception:
                pass
            
            # Get or initialize span stack
            span_stack = _span_stack_var.get()
            if span_stack is None:
                span_stack = []
                _span_stack_var.set(span_stack)
            
            # Save current span_name to stack (for nested decorators)
            previous_span_name = None
            if logger:
                try:
                    current_keys = getattr(logger, '_keys', {})
                    previous_span_name = current_keys.get('span_name')
                except Exception:
                    pass
            
            # Push current span to stack
            span_stack.append(span_name)
            
            # Add span context to all subsequent logs
            if logger:
                try:
                    logger.append_keys(span_name=span_name, trace_id=trace_id)
                except Exception:
                    pass
            
            # Emit START marker log (will be filtered by ingestor, not saved to DynamoDB)
            start_time = time.time()
            if logger:
                try:
                    logger.info(
                        f"[SPAN_START] {span_name}",
                        extra={
                            "span_marker": True,
                            "span_event": "start",
                            "span_name": span_name,
                            "trace_id": trace_id
                        }
                    )
                except Exception:
                    pass
            
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
                
                # Add duration to logger context for application logs
                if logger:
                    try:
                        logger.append_keys(span_duration_ms=duration_ms)
                    except Exception:
                        pass
                
                # Emit END marker log (will be filtered by ingestor, not saved to DynamoDB)
                if logger:
                    try:
                        status = "failed" if error_occurred else "completed"
                        extra_data = {
                            "span_marker": True,
                            "span_event": "end",
                            "span_name": span_name,
                            "trace_id": trace_id,
                            "span_duration_ms": duration_ms,
                            "status": status
                        }
                        if error_occurred and error_message:
                            extra_data["error_message"] = error_message
                        
                        logger.info(
                            f"[SPAN_END] {span_name} ({duration_ms:.2f}ms) [{status}]",
                            extra=extra_data
                        )
                    except Exception:
                        pass
                
                # Pop current span from stack
                span_stack = _span_stack_var.get()
                if span_stack and span_stack[-1] == span_name:
                    span_stack.pop()
                
                # Clean up span context and restore parent span_name
                if logger:
                    try:
                        logger.remove_keys(['span_name', 'span_duration_ms'])
                        
                        # Restore parent span_name from stack if exists
                        if span_stack:
                            parent_span_name = span_stack[-1]
                            logger.append_keys(span_name=parent_span_name)
                        elif previous_span_name:
                            # Fallback: restore from saved previous_span_name
                            logger.append_keys(span_name=previous_span_name)
                    except Exception:
                        pass
        
        return wrapper
    return decorator


# Note: Span marker logs ([SPAN_START] and [SPAN_END]) are emitted to CloudWatch
# for debugging and duration calculation, but are filtered by the ingestor and
# NOT saved to DynamoDB (identified by span_marker=True in extra metadata).
# This provides accurate span timing without polluting the persisted log data.
