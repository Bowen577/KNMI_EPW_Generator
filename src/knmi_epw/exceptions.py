"""
Comprehensive exception handling for KNMI EPW Generator.

This module defines all custom exceptions used throughout the package,
providing clear error messages and context for debugging and error recovery.
"""

from typing import Optional, Dict, Any, List
import traceback
from pathlib import Path


class KNMIEPWError(Exception):
    """
    Base exception class for all KNMI EPW Generator errors.
    
    Provides common functionality for error handling, logging, and recovery.
    """
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None, 
                 suggestions: Optional[List[str]] = None):
        """
        Initialize base exception.
        
        Args:
            message: Human-readable error message
            error_code: Unique error code for programmatic handling
            context: Additional context information for debugging
            suggestions: List of suggested solutions or next steps
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.suggestions = suggestions or []
        self.traceback_info = traceback.format_exc()
    
    def __str__(self) -> str:
        """Return formatted error message."""
        parts = [f"[{self.error_code}] {self.message}"]
        
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")
        
        if self.suggestions:
            suggestions_str = "; ".join(self.suggestions)
            parts.append(f"Suggestions: {suggestions_str}")
        
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'context': self.context,
            'suggestions': self.suggestions,
            'traceback': self.traceback_info
        }


class ConfigurationError(KNMIEPWError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_file: Optional[str] = None, 
                 invalid_keys: Optional[List[str]] = None):
        context = {}
        if config_file:
            context['config_file'] = config_file
        if invalid_keys:
            context['invalid_keys'] = invalid_keys
        
        suggestions = [
            "Check configuration file syntax and format",
            "Verify all required configuration keys are present",
            "Use Config.from_file() to load configuration",
            "Run with --help to see configuration options"
        ]
        
        super().__init__(message, "CONFIG_ERROR", context, suggestions)


class StationError(KNMIEPWError):
    """Raised when weather station operations fail."""
    
    def __init__(self, message: str, station_id: Optional[str] = None, 
                 operation: Optional[str] = None):
        context = {}
        if station_id:
            context['station_id'] = station_id
        if operation:
            context['operation'] = operation
        
        suggestions = [
            "Use 'knmi-epw stations --list' to see available stations",
            "Verify station ID is correct and exists",
            "Check station information file is accessible",
            "Try with a different station ID"
        ]
        
        super().__init__(message, "STATION_ERROR", context, suggestions)


class DownloadError(KNMIEPWError):
    """Raised when data download operations fail."""
    
    def __init__(self, message: str, url: Optional[str] = None, 
                 station_id: Optional[str] = None, year: Optional[int] = None,
                 http_status: Optional[int] = None):
        context = {}
        if url:
            context['url'] = url
        if station_id:
            context['station_id'] = station_id
        if year:
            context['year'] = year
        if http_status:
            context['http_status'] = http_status
        
        suggestions = [
            "Check internet connection",
            "Verify KNMI website is accessible",
            "Try again later if server is temporarily unavailable",
            "Use --force-download to retry failed downloads",
            "Check if data exists for the specified year"
        ]
        
        super().__init__(message, "DOWNLOAD_ERROR", context, suggestions)


class DataValidationError(KNMIEPWError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None,
                 validation_type: Optional[str] = None, 
                 expected_format: Optional[str] = None):
        context = {}
        if file_path:
            context['file_path'] = file_path
        if validation_type:
            context['validation_type'] = validation_type
        if expected_format:
            context['expected_format'] = expected_format
        
        suggestions = [
            "Check if input file is corrupted or incomplete",
            "Verify file format matches expected KNMI format",
            "Try re-downloading the data file",
            "Use --force-download to get fresh data",
            "Check file permissions and accessibility"
        ]
        
        super().__init__(message, "VALIDATION_ERROR", context, suggestions)


class ProcessingError(KNMIEPWError):
    """Raised when data processing operations fail."""
    
    def __init__(self, message: str, station_id: Optional[str] = None,
                 year: Optional[int] = None, processing_stage: Optional[str] = None,
                 data_records: Optional[int] = None):
        context = {}
        if station_id:
            context['station_id'] = station_id
        if year:
            context['year'] = year
        if processing_stage:
            context['processing_stage'] = processing_stage
        if data_records:
            context['data_records'] = data_records
        
        suggestions = [
            "Check if input data is complete and valid",
            "Try using streaming processing for large datasets",
            "Verify sufficient memory is available",
            "Use --sequential processing if parallel processing fails",
            "Check log files for detailed error information"
        ]
        
        super().__init__(message, "PROCESSING_ERROR", context, suggestions)


class EPWGenerationError(KNMIEPWError):
    """Raised when EPW file generation fails."""
    
    def __init__(self, message: str, output_path: Optional[str] = None,
                 station_id: Optional[str] = None, year: Optional[int] = None,
                 template_file: Optional[str] = None):
        context = {}
        if output_path:
            context['output_path'] = output_path
        if station_id:
            context['station_id'] = station_id
        if year:
            context['year'] = year
        if template_file:
            context['template_file'] = template_file
        
        suggestions = [
            "Check if output directory is writable",
            "Verify EPW template file exists and is valid",
            "Ensure sufficient disk space is available",
            "Check file permissions for output directory",
            "Try with a different output path"
        ]
        
        super().__init__(message, "EPW_ERROR", context, suggestions)


class CacheError(KNMIEPWError):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str, cache_key: Optional[str] = None,
                 cache_dir: Optional[str] = None, operation: Optional[str] = None):
        context = {}
        if cache_key:
            context['cache_key'] = cache_key
        if cache_dir:
            context['cache_dir'] = cache_dir
        if operation:
            context['operation'] = operation
        
        suggestions = [
            "Check if cache directory is writable",
            "Verify sufficient disk space for cache",
            "Try clearing cache with --disable-cache",
            "Check file permissions for cache directory",
            "Use cache.clear() to reset cache state"
        ]
        
        super().__init__(message, "CACHE_ERROR", context, suggestions)


class ResourceError(KNMIEPWError):
    """Raised when system resource constraints are encountered."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None,
                 current_usage: Optional[str] = None, limit: Optional[str] = None):
        context = {}
        if resource_type:
            context['resource_type'] = resource_type
        if current_usage:
            context['current_usage'] = current_usage
        if limit:
            context['limit'] = limit
        
        suggestions = [
            "Reduce number of parallel workers",
            "Enable streaming processing to reduce memory usage",
            "Close other applications to free resources",
            "Use --sequential processing for resource-constrained systems",
            "Increase system memory or disk space"
        ]
        
        super().__init__(message, "RESOURCE_ERROR", context, suggestions)


class ValidationError(KNMIEPWError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, parameter: Optional[str] = None,
                 value: Optional[Any] = None, expected_type: Optional[str] = None):
        context = {}
        if parameter:
            context['parameter'] = parameter
        if value is not None:
            context['value'] = str(value)
        if expected_type:
            context['expected_type'] = expected_type
        
        suggestions = [
            "Check parameter types and values",
            "Refer to API documentation for valid parameter ranges",
            "Use configuration validation before processing",
            "Check command-line argument syntax"
        ]
        
        super().__init__(message, "VALIDATION_ERROR", context, suggestions)


def handle_exception(func):
    """
    Decorator for graceful exception handling with logging.
    
    Converts unexpected exceptions into KNMIEPWError instances
    with appropriate context and suggestions.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KNMIEPWError:
            # Re-raise our custom exceptions as-is
            raise
        except FileNotFoundError as e:
            raise ValidationError(
                f"Required file not found: {e.filename}",
                parameter="file_path",
                value=e.filename,
                expected_type="existing file"
            ) from e
        except PermissionError as e:
            raise ResourceError(
                f"Permission denied: {e.filename}",
                resource_type="file_access",
                current_usage=str(e)
            ) from e
        except MemoryError as e:
            raise ResourceError(
                "Insufficient memory for operation",
                resource_type="memory",
                current_usage="exceeded"
            ) from e
        except Exception as e:
            # Convert unexpected exceptions to KNMIEPWError
            raise KNMIEPWError(
                f"Unexpected error in {func.__name__}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                context={'function': func.__name__, 'args': str(args)},
                suggestions=[
                    "Check input parameters and data",
                    "Enable debug logging for more information",
                    "Report this error if it persists"
                ]
            ) from e
    
    return wrapper


def validate_file_path(file_path: str, must_exist: bool = True, 
                      must_be_readable: bool = True) -> Path:
    """
    Validate file path with comprehensive error handling.
    
    Args:
        file_path: Path to validate
        must_exist: Whether file must exist
        must_be_readable: Whether file must be readable
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        path = Path(file_path)
        
        if must_exist and not path.exists():
            raise ValidationError(
                f"File does not exist: {file_path}",
                parameter="file_path",
                value=file_path,
                expected_type="existing file"
            )
        
        if must_be_readable and path.exists() and not path.is_file():
            raise ValidationError(
                f"Path is not a file: {file_path}",
                parameter="file_path",
                value=file_path,
                expected_type="regular file"
            )
        
        return path
        
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(
            f"Invalid file path: {file_path}",
            parameter="file_path",
            value=file_path
        ) from e


def validate_year(year: int) -> int:
    """
    Validate year parameter.
    
    Args:
        year: Year to validate
        
    Returns:
        Validated year
        
    Raises:
        ValidationError: If year is invalid
    """
    current_year = 2024  # Update as needed
    
    if not isinstance(year, int):
        raise ValidationError(
            f"Year must be an integer, got {type(year).__name__}",
            parameter="year",
            value=year,
            expected_type="integer"
        )
    
    if year < 1950 or year > current_year + 1:
        raise ValidationError(
            f"Year must be between 1950 and {current_year + 1}, got {year}",
            parameter="year",
            value=year,
            expected_type=f"integer between 1950 and {current_year + 1}"
        )
    
    return year


def validate_station_id(station_id: str) -> str:
    """
    Validate station ID format.
    
    Args:
        station_id: Station ID to validate
        
    Returns:
        Validated station ID
        
    Raises:
        ValidationError: If station ID is invalid
    """
    if not isinstance(station_id, str):
        raise ValidationError(
            f"Station ID must be a string, got {type(station_id).__name__}",
            parameter="station_id",
            value=station_id,
            expected_type="string"
        )
    
    if not station_id.isdigit() or len(station_id) != 3:
        raise ValidationError(
            f"Station ID must be a 3-digit string, got '{station_id}'",
            parameter="station_id",
            value=station_id,
            expected_type="3-digit string"
        )
    
    return station_id
