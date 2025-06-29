"""
Structured logging configuration for KNMI EPW Generator.

This module provides comprehensive logging functionality with configurable
levels, formats, and output destinations for debugging and monitoring.
"""

import logging
import logging.handlers
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import traceback

from .exceptions import KNMIEPWError


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging with JSON output support.
    
    Provides both human-readable and machine-readable log formats
    with comprehensive context information.
    """
    
    def __init__(self, format_type: str = "human", include_extra: bool = True):
        """
        Initialize structured formatter.
        
        Args:
            format_type: Format type ("human", "json", "detailed")
            include_extra: Whether to include extra context fields
        """
        self.format_type = format_type
        self.include_extra = include_extra
        
        # Define format strings
        if format_type == "human":
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        elif format_type == "detailed":
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        else:  # json
            fmt = None
        
        super().__init__(fmt, datefmt="%Y-%m-%d %H:%M:%S")
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record according to configured format type."""
        if self.format_type == "json":
            return self._format_json(record)
        else:
            return self._format_human(record)
    
    def _format_json(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {
                k: v for k, v in record.__dict__.items()
                if k not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info'
                }
            }
            if extra_fields:
                log_data["extra"] = extra_fields
        
        return json.dumps(log_data, default=str)
    
    def _format_human(self, record: logging.LogRecord) -> str:
        """Format log record for human readability."""
        formatted = super().format(record)
        
        # Add extra context if available
        if hasattr(record, 'station_id'):
            formatted += f" [Station: {record.station_id}]"
        if hasattr(record, 'year'):
            formatted += f" [Year: {record.year}]"
        if hasattr(record, 'processing_time'):
            formatted += f" [Time: {record.processing_time:.2f}s]"
        if hasattr(record, 'memory_usage'):
            formatted += f" [Memory: {record.memory_usage:.1f}MB]"
        
        return formatted


class PerformanceFilter(logging.Filter):
    """Filter for performance-related log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter performance-related records."""
        performance_keywords = [
            'processing_time', 'memory_usage', 'cache_hit', 'cache_miss',
            'download_speed', 'throughput', 'parallel', 'streaming'
        ]
        
        message = record.getMessage().lower()
        return any(keyword in message for keyword in performance_keywords)


class ErrorFilter(logging.Filter):
    """Filter for error and warning records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter error and warning records."""
        return record.levelno >= logging.WARNING


class ContextLogger:
    """
    Context-aware logger that automatically includes relevant context information.
    
    Provides structured logging with automatic context injection for
    station IDs, years, processing stages, and performance metrics.
    """
    
    def __init__(self, name: str):
        """
        Initialize context logger.
        
        Args:
            name: Logger name (typically module name)
        """
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """Set context information for subsequent log messages."""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context information."""
        self.context.clear()
    
    def _log_with_context(self, level: int, message: str, *args, **kwargs):
        """Log message with automatic context injection."""
        # Merge context with any extra kwargs
        extra = kwargs.get('extra', {})
        extra.update(self.context)
        kwargs['extra'] = extra
        
        self.logger.log(level, message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception with context and traceback."""
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, message, *args, **kwargs)


def setup_logging(
    level: Union[str, int] = logging.INFO,
    format_type: str = "human",
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_performance_logging: bool = True,
    enable_error_file: bool = True
) -> Dict[str, logging.Handler]:
    """
    Setup comprehensive logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("human", "json", "detailed")
        log_file: Optional log file path
        max_file_size: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        enable_performance_logging: Whether to enable performance logging
        enable_error_file: Whether to create separate error log file
        
    Returns:
        Dictionary of configured handlers
    """
    # Convert string level to integer
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root logger level
    root_logger.setLevel(level)
    
    handlers = {}
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(StructuredFormatter(format_type))
    root_logger.addHandler(console_handler)
    handlers['console'] = console_handler
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(StructuredFormatter("detailed"))
        root_logger.addHandler(file_handler)
        handlers['file'] = file_handler
    
    # Performance log handler
    if enable_performance_logging and log_file:
        perf_log_file = log_path.parent / f"{log_path.stem}_performance{log_path.suffix}"
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(StructuredFormatter("json"))
        perf_handler.addFilter(PerformanceFilter())
        root_logger.addHandler(perf_handler)
        handlers['performance'] = perf_handler
    
    # Error log handler
    if enable_error_file and log_file:
        error_log_file = log_path.parent / f"{log_path.stem}_errors{log_path.suffix}"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(StructuredFormatter("json"))
        error_handler.addFilter(ErrorFilter())
        root_logger.addHandler(error_handler)
        handlers['error'] = error_handler
    
    # Set specific logger levels
    logging.getLogger('knmi_epw').setLevel(level)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    return handlers


def get_logger(name: str) -> ContextLogger:
    """
    Get a context-aware logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        ContextLogger instance
    """
    return ContextLogger(name)


def log_performance_metrics(
    operation: str,
    duration: float,
    memory_usage: Optional[float] = None,
    records_processed: Optional[int] = None,
    cache_hits: Optional[int] = None,
    cache_misses: Optional[int] = None,
    **kwargs
):
    """
    Log performance metrics in a structured format.
    
    Args:
        operation: Name of the operation
        duration: Operation duration in seconds
        memory_usage: Peak memory usage in MB
        records_processed: Number of records processed
        cache_hits: Number of cache hits
        cache_misses: Number of cache misses
        **kwargs: Additional metrics
    """
    logger = get_logger('knmi_epw.performance')
    
    metrics = {
        'operation': operation,
        'duration': duration,
        'throughput': records_processed / duration if records_processed and duration > 0 else None,
    }
    
    if memory_usage is not None:
        metrics['memory_usage'] = memory_usage
    if records_processed is not None:
        metrics['records_processed'] = records_processed
    if cache_hits is not None:
        metrics['cache_hits'] = cache_hits
    if cache_misses is not None:
        metrics['cache_misses'] = cache_misses
        if cache_hits is not None:
            total_requests = cache_hits + cache_misses
            metrics['cache_hit_rate'] = cache_hits / total_requests if total_requests > 0 else 0
    
    metrics.update(kwargs)
    
    logger.info(f"Performance metrics for {operation}", extra=metrics)


def log_exception(exception: Exception, context: Optional[Dict[str, Any]] = None):
    """
    Log exception with comprehensive context information.
    
    Args:
        exception: Exception to log
        context: Additional context information
    """
    logger = get_logger('knmi_epw.errors')
    
    extra = {'exception_type': type(exception).__name__}
    if context:
        extra.update(context)
    
    if isinstance(exception, KNMIEPWError):
        # Log our custom exceptions with full context
        extra.update(exception.to_dict())
        logger.error(f"KNMI EPW Error: {exception.message}", extra=extra)
    else:
        # Log unexpected exceptions
        logger.exception(f"Unexpected error: {str(exception)}", extra=extra)


class LoggingContext:
    """Context manager for automatic logging context management."""
    
    def __init__(self, logger: ContextLogger, **context):
        """
        Initialize logging context.
        
        Args:
            logger: ContextLogger instance
            **context: Context key-value pairs
        """
        self.logger = logger
        self.context = context
        self.previous_context = {}
    
    def __enter__(self):
        """Enter context and set logging context."""
        self.previous_context = self.logger.context.copy()
        self.logger.set_context(**self.context)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore previous logging context."""
        self.logger.context = self.previous_context
        
        # Log any exceptions that occurred
        if exc_type and exc_val:
            log_exception(exc_val, self.context)
