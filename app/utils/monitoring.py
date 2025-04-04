import time
from functools import wraps
from typing import Dict, Any, Optional, Callable
import psutil
import logging
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge

# Initialize metrics
PROCESSING_TIME = Histogram(
    'statement_processing_seconds',
    'Time spent processing statements',
    ['format', 'status']
)

PROCESSED_STATEMENTS = Counter(
    'processed_statements_total',
    'Total number of processed statements',
    ['format', 'status']
)

ERROR_COUNT = Counter(
    'processing_errors_total',
    'Total number of processing errors',
    ['error_type']
)

MEMORY_USAGE = Gauge(
    'statement_processor_memory_bytes',
    'Memory usage of the statement processor'
)

class PerformanceMonitor:
    """Monitors and records performance metrics."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def monitor_performance(self, operation: str):
        """Decorator to monitor function performance."""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss
                
                try:
                    result = func(*args, **kwargs)
                    status = "success"
                except Exception as e:
                    status = "error"
                    ERROR_COUNT.labels(error_type=type(e).__name__).inc()
                    raise
                finally:
                    duration = time.time() - start_time
                    memory_used = psutil.Process().memory_info().rss - start_memory
                    
                    # Record metrics
                    PROCESSING_TIME.labels(
                        format=kwargs.get('file_format', 'unknown'),
                        status=status
                    ).observe(duration)
                    
                    MEMORY_USAGE.set(psutil.Process().memory_info().rss)
                    
                    # Log performance data
                    self.logger.info(
                        f"Performance metrics for {operation}: "
                        f"duration={duration:.2f}s, "
                        f"memory_used={memory_used/1024/1024:.2f}MB"
                    )
                
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def record_metric(metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a custom metric."""
        if labels is None:
            labels = {}
        
        if metric_name == "processing_time":
            PROCESSING_TIME.labels(**labels).observe(value)
        elif metric_name == "memory_usage":
            MEMORY_USAGE.set(value)
    
    def get_performance_report(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate performance report for a time period."""
        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "metrics": {
                "total_processed": {
                    "pdf": int(PROCESSED_STATEMENTS.labels(format="PDF", status="success")._value.get()),
                    "csv": int(PROCESSED_STATEMENTS.labels(format="CSV", status="success")._value.get()),
                    "image": int(PROCESSED_STATEMENTS.labels(format="IMAGE", status="success")._value.get())
                },
                "errors": {
                    "total": sum(ERROR_COUNT.values()),
                    "by_type": {
                        k: v for k, v in ERROR_COUNT._metrics.items()
                    }
                },
                "processing_time": {
                    "avg": PROCESSING_TIME.labels(format="PDF", status="success")._sum.get() / 
                           max(PROCESSING_TIME.labels(format="PDF", status="success")._count.get(), 1)
                },
                "memory": {
                    "current": MEMORY_USAGE._value.get() / 1024 / 1024  # MB
                }
            }
        }

# Create global monitor instance
monitor = PerformanceMonitor()

# Example usage:
# @monitor.monitor_performance("statement_processing")
# def process_statement(statement_id: int, **kwargs):
#     pass