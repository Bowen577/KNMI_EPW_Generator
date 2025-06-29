"""
Utility functions for KNMI EPW Generator.

This module contains common utility functions used across the package.
"""

import os
import hashlib
import json
import pickle
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union, Tuple
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def calculate_file_hash(file_path: Union[str, Path], algorithm: str = 'md5') -> str:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm ('md5', 'sha1', 'sha256')
        
    Returns:
        Hex digest of file hash
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float with default fallback.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        if value is None or value == '' or str(value).strip() == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int with default fallback.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        if value is None or value == '' or str(value).strip() == '':
            return default
        return int(float(value))  # Convert through float to handle strings like "123.0"
    except (ValueError, TypeError):
        return default


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get comprehensive file information.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with file information
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {"exists": False}
    
    stat = file_path.stat()
    
    return {
        "exists": True,
        "size": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "modified": stat.st_mtime,
        "is_file": file_path.is_file(),
        "is_dir": file_path.is_dir(),
        "name": file_path.name,
        "stem": file_path.stem,
        "suffix": file_path.suffix,
        "parent": str(file_path.parent)
    }


def validate_year(year: int) -> bool:
    """
    Validate if year is reasonable for weather data.
    
    Args:
        year: Year to validate
        
    Returns:
        True if year is valid
    """
    current_year = 2024  # Update as needed
    return 1950 <= year <= current_year + 1


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    Validate geographic coordinates.
    
    Args:
        latitude: Latitude in degrees
        longitude: Longitude in degrees
        
    Returns:
        True if coordinates are valid
    """
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def create_cache_key(*args) -> str:
    """
    Create a cache key from arguments.
    
    Args:
        *args: Arguments to create key from
        
    Returns:
        Cache key string
    """
    key_data = json.dumps(args, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def cleanup_temp_files(directory: Union[str, Path], pattern: str = "*.tmp", 
                      max_age_hours: int = 24):
    """
    Clean up temporary files older than specified age.
    
    Args:
        directory: Directory to clean
        pattern: File pattern to match
        max_age_hours: Maximum age in hours
    """
    import time
    
    directory = Path(directory)
    if not directory.exists():
        return
    
    cutoff_time = time.time() - (max_age_hours * 3600)
    
    for file_path in directory.glob(pattern):
        try:
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                logger.debug(f"Removed temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temp file {file_path}: {e}")


def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                      backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """
    Decorator to retry function on exception.
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")
                        raise last_exception
            
            return None
        return wrapper
    return decorator


def progress_callback(current: int, total: int, prefix: str = "Progress"):
    """
    Simple progress callback function.
    
    Args:
        current: Current progress
        total: Total items
        prefix: Progress message prefix
    """
    if total > 0:
        percent = (current / total) * 100
        print(f"\r{prefix}: {current}/{total} ({percent:.1f}%)", end="", flush=True)
        if current == total:
            print()  # New line when complete


class SimpleCache:
    """Simple in-memory cache with optional file persistence."""

    def __init__(self, cache_file: Optional[Union[str, Path]] = None):
        """
        Initialize cache.

        Args:
            cache_file: Optional file to persist cache to
        """
        self.cache = {}
        self.cache_file = Path(cache_file) if cache_file else None
        self._load_cache()

    def _load_cache(self):
        """Load cache from file if it exists."""
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.debug(f"Loaded cache from {self.cache_file}")
            except Exception as e:
                logger.warning(f"Failed to load cache from {self.cache_file}: {e}")
                self.cache = {}

    def _save_cache(self):
        """Save cache to file."""
        if self.cache_file:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, 'w') as f:
                    json.dump(self.cache, f, indent=2)
                logger.debug(f"Saved cache to {self.cache_file}")
            except Exception as e:
                logger.warning(f"Failed to save cache to {self.cache_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        return self.cache.get(key, default)

    def set(self, key: str, value: Any):
        """Set value in cache."""
        self.cache[key] = value
        self._save_cache()

    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self._save_cache()

    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self.cache


class IntelligentCache:
    """
    Intelligent caching system with TTL, size limits, and data integrity checks.
    Supports both in-memory and disk-based caching for different data types.
    """

    def __init__(self, cache_dir: Union[str, Path], max_size_mb: int = 1000,
                 default_ttl: int = 86400):
        """
        Initialize intelligent cache.

        Args:
            cache_dir: Directory for cache storage
            max_size_mb: Maximum cache size in MB
            default_ttl: Default time-to-live in seconds (24 hours)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl

        # In-memory metadata cache
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Load cache metadata."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
        return {}

    def _save_metadata(self):
        """Save cache metadata."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache metadata: {e}")

    def _get_cache_path(self, key: str, data_type: str = "pickle") -> Path:
        """Get cache file path for a key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        extension = {"pickle": ".pkl", "csv": ".csv", "json": ".json"}
        return self.cache_dir / f"{safe_key}{extension.get(data_type, '.pkl')}"

    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if key not in self.metadata:
            return True

        created_time = self.metadata[key].get('created_time', 0)
        ttl = self.metadata[key].get('ttl', self.default_ttl)
        return time.time() - created_time > ttl

    def _verify_integrity(self, key: str, file_path: Path) -> bool:
        """Verify cache file integrity using checksum."""
        if key not in self.metadata or not file_path.exists():
            return False

        expected_hash = self.metadata[key].get('checksum')
        if not expected_hash:
            return False

        actual_hash = calculate_file_hash(file_path)
        return actual_hash == expected_hash

    def _cleanup_expired(self):
        """Remove expired cache entries."""
        expired_keys = []
        for key in list(self.metadata.keys()):
            if self._is_expired(key):
                expired_keys.append(key)
                cache_path = self._get_cache_path(key, self.metadata[key].get('data_type', 'pickle'))
                try:
                    if cache_path.exists():
                        cache_path.unlink()
                    del self.metadata[key]
                except Exception as e:
                    logger.warning(f"Failed to remove expired cache entry {key}: {e}")

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            self._save_metadata()

    def _enforce_size_limit(self):
        """Enforce cache size limit by removing oldest entries."""
        total_size = sum(
            self._get_cache_path(key, meta.get('data_type', 'pickle')).stat().st_size
            for key, meta in self.metadata.items()
            if self._get_cache_path(key, meta.get('data_type', 'pickle')).exists()
        )

        if total_size <= self.max_size_bytes:
            return

        # Sort by access time (LRU eviction)
        sorted_entries = sorted(
            self.metadata.items(),
            key=lambda x: x[1].get('last_access', 0)
        )

        removed_count = 0
        for key, meta in sorted_entries:
            if total_size <= self.max_size_bytes:
                break

            cache_path = self._get_cache_path(key, meta.get('data_type', 'pickle'))
            try:
                if cache_path.exists():
                    file_size = cache_path.stat().st_size
                    cache_path.unlink()
                    total_size -= file_size
                    removed_count += 1
                del self.metadata[key]
            except Exception as e:
                logger.warning(f"Failed to remove cache entry {key}: {e}")

        if removed_count > 0:
            logger.info(f"Removed {removed_count} cache entries to enforce size limit")
            self._save_metadata()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        if self._is_expired(key):
            return default

        data_type = self.metadata.get(key, {}).get('data_type', 'pickle')
        cache_path = self._get_cache_path(key, data_type)

        if not cache_path.exists():
            return default

        if not self._verify_integrity(key, cache_path):
            logger.warning(f"Cache integrity check failed for key: {key}")
            return default

        try:
            # Update access time
            self.metadata[key]['last_access'] = time.time()
            self._save_metadata()

            # Load data based on type
            if data_type == "pickle":
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            elif data_type == "csv":
                return pd.read_csv(cache_path, index_col=0, parse_dates=True)
            elif data_type == "json":
                with open(cache_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Unknown data type for cache key {key}: {data_type}")
                return default

        except Exception as e:
            logger.warning(f"Failed to load cache entry {key}: {e}")
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            data_type: str = "auto"):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            data_type: Data type ("auto", "pickle", "csv", "json")
        """
        if ttl is None:
            ttl = self.default_ttl

        # Auto-detect data type
        if data_type == "auto":
            if isinstance(value, pd.DataFrame):
                data_type = "csv"
            elif isinstance(value, (dict, list)):
                data_type = "json"
            else:
                data_type = "pickle"

        cache_path = self._get_cache_path(key, data_type)

        try:
            # Save data based on type
            if data_type == "pickle":
                with open(cache_path, 'wb') as f:
                    pickle.dump(value, f)
            elif data_type == "csv":
                value.to_csv(cache_path)
            elif data_type == "json":
                with open(cache_path, 'w') as f:
                    json.dump(value, f, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")

            # Update metadata
            checksum = calculate_file_hash(cache_path)
            self.metadata[key] = {
                'created_time': time.time(),
                'last_access': time.time(),
                'ttl': ttl,
                'data_type': data_type,
                'checksum': checksum,
                'size': cache_path.stat().st_size
            }

            self._save_metadata()

            # Cleanup and enforce limits
            self._cleanup_expired()
            self._enforce_size_limit()

            logger.debug(f"Cached {key} ({data_type}, {format_file_size(cache_path.stat().st_size)})")

        except Exception as e:
            logger.error(f"Failed to cache {key}: {e}")

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return not self._is_expired(key) and self._get_cache_path(key).exists()

    def delete(self, key: str):
        """Delete cache entry."""
        if key in self.metadata:
            cache_path = self._get_cache_path(key, self.metadata[key].get('data_type', 'pickle'))
            try:
                if cache_path.exists():
                    cache_path.unlink()
                del self.metadata[key]
                self._save_metadata()
                logger.debug(f"Deleted cache entry: {key}")
            except Exception as e:
                logger.warning(f"Failed to delete cache entry {key}: {e}")

    def clear(self):
        """Clear all cache entries."""
        try:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            for cache_file in self.cache_dir.glob("*.csv"):
                cache_file.unlink()
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()

            self.metadata.clear()
            self._save_metadata()
            logger.info("Cleared all cache entries")

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.metadata)
        total_size = sum(
            self._get_cache_path(key, meta.get('data_type', 'pickle')).stat().st_size
            for key, meta in self.metadata.items()
            if self._get_cache_path(key, meta.get('data_type', 'pickle')).exists()
        )

        expired_count = sum(1 for key in self.metadata if self._is_expired(key))

        return {
            'total_entries': total_entries,
            'expired_entries': expired_count,
            'valid_entries': total_entries - expired_count,
            'total_size_bytes': total_size,
            'total_size_formatted': format_file_size(total_size),
            'max_size_bytes': self.max_size_bytes,
            'max_size_formatted': format_file_size(self.max_size_bytes),
            'usage_percentage': (total_size / self.max_size_bytes) * 100
        }
