"""
Comprehensive data validation module for KNMI EPW Generator.

This module provides validation functions for all types of data used in the
KNMI EPW Generator, including configuration, weather data, station information,
and output files.
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, date
import logging

from .exceptions import (
    ValidationError, 
    DataValidationError, 
    ConfigurationError,
    StationError
)

logger = logging.getLogger(__name__)


class ValidationResult:
    """Container for validation results with detailed information."""
    
    def __init__(self, is_valid: bool = True, errors: Optional[List[str]] = None, 
                 warnings: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None):
        """
        Initialize validation result.
        
        Args:
            is_valid: Whether validation passed
            errors: List of error messages
            warnings: List of warning messages
            context: Additional context information
        """
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.context = context or {}
    
    def add_error(self, message: str, **context):
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False
        self.context.update(context)
    
    def add_warning(self, message: str, **context):
        """Add a warning message."""
        self.warnings.append(message)
        self.context.update(context)
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.context.update(other.context)
        if not other.is_valid:
            self.is_valid = False
    
    def __bool__(self):
        """Return True if validation passed."""
        return self.is_valid
    
    def __str__(self):
        """Return string representation of validation result."""
        if self.is_valid:
            status = "VALID"
        else:
            status = "INVALID"
        
        parts = [f"Validation: {status}"]
        
        if self.errors:
            parts.append(f"Errors: {len(self.errors)}")
        if self.warnings:
            parts.append(f"Warnings: {len(self.warnings)}")
        
        return " | ".join(parts)


class ConfigurationValidator:
    """Validator for configuration data."""
    
    @staticmethod
    def validate_paths(paths_config) -> ValidationResult:
        """Validate paths configuration."""
        result = ValidationResult()
        
        # Required path attributes
        required_attrs = ['data_dir', 'knmi_dir', 'knmi_zip_dir', 'epw_output_dir']
        
        for attr in required_attrs:
            if not hasattr(paths_config, attr):
                result.add_error(f"Missing required path attribute: {attr}")
                continue
            
            path_value = getattr(paths_config, attr)
            if not path_value:
                result.add_error(f"Empty path value for: {attr}")
                continue
            
            # Check if path is valid string
            if not isinstance(path_value, str):
                result.add_error(f"Path must be string, got {type(path_value).__name__}: {attr}")
        
        # Validate file paths exist (for required files)
        file_attrs = ['station_info_file', 'epw_template_file']
        for attr in file_attrs:
            if hasattr(paths_config, attr):
                file_path = getattr(paths_config, attr)
                if file_path and not Path(file_path).exists():
                    result.add_warning(f"File does not exist: {file_path} ({attr})")
        
        return result
    
    @staticmethod
    def validate_urls(urls_config) -> ValidationResult:
        """Validate URLs configuration."""
        result = ValidationResult()
        
        # Validate base URL
        if hasattr(urls_config, 'base_url'):
            base_url = urls_config.base_url
            if not base_url:
                result.add_error("Base URL cannot be empty")
            elif not isinstance(base_url, str):
                result.add_error(f"Base URL must be string, got {type(base_url).__name__}")
            elif not (base_url.startswith('http://') or base_url.startswith('https://')):
                result.add_warning(f"Base URL should start with http:// or https://: {base_url}")
        
        # Validate link pattern
        if hasattr(urls_config, 'link_pattern'):
            pattern = urls_config.link_pattern
            if pattern:
                try:
                    re.compile(pattern)
                except re.error as e:
                    result.add_error(f"Invalid regex pattern: {pattern} - {e}")
        
        return result
    
    @staticmethod
    def validate_processing(processing_config) -> ValidationResult:
        """Validate processing configuration."""
        result = ValidationResult()
        
        # Validate numeric parameters
        numeric_params = {
            'local_time_shift': (-12, 12),
            'skiprows': (0, 100),
            'epw_skiprows': (0, 50),
            'coerce_year': (1900, 2100),
            'max_workers': (1, 32),
            'chunk_size': (100, 1000000)
        }
        
        for param, (min_val, max_val) in numeric_params.items():
            if hasattr(processing_config, param):
                value = getattr(processing_config, param)
                if not isinstance(value, (int, float)):
                    result.add_error(f"{param} must be numeric, got {type(value).__name__}")
                elif not (min_val <= value <= max_val):
                    result.add_error(f"{param} must be between {min_val} and {max_val}, got {value}")
        
        # Validate boolean parameters
        boolean_params = ['cache_enabled']
        for param in boolean_params:
            if hasattr(processing_config, param):
                value = getattr(processing_config, param)
                if not isinstance(value, bool):
                    result.add_error(f"{param} must be boolean, got {type(value).__name__}")
        
        return result


class WeatherDataValidator:
    """Validator for weather data."""
    
    @staticmethod
    def validate_knmi_data(data: pd.DataFrame) -> ValidationResult:
        """Validate KNMI weather data format and content."""
        result = ValidationResult()
        
        if data.empty:
            result.add_error("Weather data is empty")
            return result
        
        # Required columns for KNMI data
        required_columns = ['YYYYMMDD', 'HH']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            result.add_error(f"Missing required columns: {missing_columns}")
        
        # Validate date format
        if 'YYYYMMDD' in data.columns:
            try:
                # Check if dates are valid
                date_strings = data['YYYYMMDD'].astype(str)
                for date_str in date_strings.head(10):  # Check first 10
                    if len(date_str) != 8:
                        result.add_error(f"Invalid date format: {date_str} (should be YYYYMMDD)")
                        break
                    try:
                        datetime.strptime(date_str, '%Y%m%d')
                    except ValueError:
                        result.add_error(f"Invalid date: {date_str}")
                        break
            except Exception as e:
                result.add_error(f"Error validating dates: {e}")
        
        # Validate hour format
        if 'HH' in data.columns:
            hours = data['HH']
            invalid_hours = hours[(hours < 1) | (hours > 24)]
            if len(invalid_hours) > 0:
                result.add_error(f"Invalid hours found (must be 1-24): {invalid_hours.head().tolist()}")
        
        # Check for reasonable data ranges
        data_ranges = {
            'T': (-500, 500),      # Temperature (0.1°C)
            'TD': (-500, 500),     # Dew point (0.1°C)
            'P': (9000, 11000),    # Pressure (0.1 hPa)
            'U': (0, 100),         # Humidity (%)
            'DD': (0, 360),        # Wind direction (degrees)
            'FH': (0, 1000),       # Wind speed (0.1 m/s)
            'Q': (0, 5000),        # Global radiation (J/cm²)
            'RH': (0, 1000),       # Precipitation (0.1 mm)
        }
        
        for column, (min_val, max_val) in data_ranges.items():
            if column in data.columns:
                col_data = pd.to_numeric(data[column], errors='coerce')
                out_of_range = col_data[(col_data < min_val) | (col_data > max_val)]
                if len(out_of_range) > 0:
                    result.add_warning(f"Values out of expected range for {column}: "
                                     f"{len(out_of_range)} values outside [{min_val}, {max_val}]")
        
        # Check for missing data
        total_records = len(data)
        for column in data.columns:
            missing_count = data[column].isna().sum()
            missing_percent = (missing_count / total_records) * 100
            
            if missing_percent > 50:
                result.add_error(f"Too much missing data in {column}: {missing_percent:.1f}%")
            elif missing_percent > 10:
                result.add_warning(f"Significant missing data in {column}: {missing_percent:.1f}%")
        
        # Check data continuity (for hourly data)
        if 'YYYYMMDD' in data.columns and 'HH' in data.columns:
            try:
                # Create datetime index
                datetime_strings = data['YYYYMMDD'].astype(str) + data['HH'].astype(str).str.zfill(2)
                datetimes = pd.to_datetime(datetime_strings, format='%Y%m%d%H', errors='coerce')
                
                # Check for gaps
                if len(datetimes.dropna()) > 1:
                    time_diffs = datetimes.dropna().diff().dropna()
                    expected_diff = pd.Timedelta(hours=1)
                    gaps = time_diffs[time_diffs > expected_diff]
                    
                    if len(gaps) > 0:
                        result.add_warning(f"Found {len(gaps)} time gaps in data")
            except Exception as e:
                result.add_warning(f"Could not validate data continuity: {e}")
        
        return result
    
    @staticmethod
    def validate_processed_weather_data(data: pd.DataFrame) -> ValidationResult:
        """Validate processed weather data ready for EPW generation."""
        result = ValidationResult()
        
        if data.empty:
            result.add_error("Processed weather data is empty")
            return result
        
        # Expected columns for EPW generation
        expected_columns = [
            'dry_bulb_temperature', 'dew_point_temperature', 'relative_humidity',
            'atmospheric_pressure', 'global_horizontal_radiation', 'direct_normal_radiation',
            'diffuse_horizontal_radiation', 'wind_direction', 'wind_speed'
        ]
        
        missing_columns = [col for col in expected_columns if col not in data.columns]
        if missing_columns:
            result.add_error(f"Missing required processed columns: {missing_columns}")
        
        # Validate data ranges for EPW format
        epw_ranges = {
            'dry_bulb_temperature': (-70, 70),      # °C
            'dew_point_temperature': (-70, 70),     # °C
            'relative_humidity': (0, 100),          # %
            'atmospheric_pressure': (31000, 120000), # Pa
            'global_horizontal_radiation': (0, 1500), # W/m²
            'wind_direction': (0, 360),             # degrees
            'wind_speed': (0, 40),                  # m/s
        }
        
        for column, (min_val, max_val) in epw_ranges.items():
            if column in data.columns:
                col_data = data[column]
                out_of_range = col_data[(col_data < min_val) | (col_data > max_val)]
                if len(out_of_range) > 0:
                    result.add_warning(f"EPW values out of range for {column}: "
                                     f"{len(out_of_range)} values outside [{min_val}, {max_val}]")
        
        # Check for required number of records (8760 for full year)
        expected_records = 8760  # 365 * 24
        if len(data) != expected_records:
            if len(data) == 8784:  # Leap year
                result.add_warning("Data appears to be from leap year (8784 records)")
            else:
                result.add_error(f"Expected {expected_records} records for full year, got {len(data)}")
        
        # Check datetime index
        if not isinstance(data.index, pd.DatetimeIndex):
            result.add_error("Processed data must have DatetimeIndex")
        else:
            # Check for duplicates
            duplicates = data.index.duplicated().sum()
            if duplicates > 0:
                result.add_error(f"Found {duplicates} duplicate timestamps")
            
            # Check for proper hourly frequency
            if len(data) > 1:
                freq_check = pd.infer_freq(data.index)
                if freq_check != 'H':
                    result.add_warning(f"Data frequency may not be hourly: {freq_check}")
        
        return result


class StationDataValidator:
    """Validator for weather station data."""
    
    @staticmethod
    def validate_station_info(station_data: Dict[str, Any]) -> ValidationResult:
        """Validate weather station information."""
        result = ValidationResult()
        
        # Required fields
        required_fields = ['station_id', 'name', 'abbreviation', 'latitude', 'longitude']
        for field in required_fields:
            if field not in station_data:
                result.add_error(f"Missing required field: {field}")
        
        # Validate station ID
        if 'station_id' in station_data:
            station_id = station_data['station_id']
            if not isinstance(station_id, str):
                result.add_error(f"Station ID must be string, got {type(station_id).__name__}")
            elif not station_id.isdigit():
                result.add_error(f"Station ID must be numeric string: {station_id}")
            elif len(station_id) != 3:
                result.add_error(f"Station ID must be 3 digits: {station_id}")
        
        # Validate coordinates
        if 'latitude' in station_data:
            lat = station_data['latitude']
            if not isinstance(lat, (int, float)):
                result.add_error(f"Latitude must be numeric, got {type(lat).__name__}")
            elif not (-90 <= lat <= 90):
                result.add_error(f"Latitude must be between -90 and 90: {lat}")
        
        if 'longitude' in station_data:
            lon = station_data['longitude']
            if not isinstance(lon, (int, float)):
                result.add_error(f"Longitude must be numeric, got {type(lon).__name__}")
            elif not (-180 <= lon <= 180):
                result.add_error(f"Longitude must be between -180 and 180: {lon}")
        
        # Validate name and abbreviation
        if 'name' in station_data:
            name = station_data['name']
            if not isinstance(name, str):
                result.add_error(f"Station name must be string, got {type(name).__name__}")
            elif not name.strip():
                result.add_error("Station name cannot be empty")
        
        if 'abbreviation' in station_data:
            abbr = station_data['abbreviation']
            if not isinstance(abbr, str):
                result.add_error(f"Station abbreviation must be string, got {type(abbr).__name__}")
            elif not abbr.strip():
                result.add_error("Station abbreviation cannot be empty")
            elif len(abbr) > 5:
                result.add_warning(f"Station abbreviation is long: {abbr}")
        
        return result
    
    @staticmethod
    def validate_station_csv(csv_path: Union[str, Path]) -> ValidationResult:
        """Validate station CSV file format."""
        result = ValidationResult()
        csv_path = Path(csv_path)
        
        if not csv_path.exists():
            result.add_error(f"Station CSV file does not exist: {csv_path}")
            return result
        
        try:
            # Read CSV file
            with open(csv_path, 'r') as f:
                lines = f.readlines()
            
            if len(lines) < 5:
                result.add_error("Station CSV file must have at least 5 lines")
                return result
            
            # Parse station data
            station_ids = lines[0].strip().split(',')
            names = lines[1].strip().split(',')
            abbreviations = lines[2].strip().split(',')
            latitudes = lines[3].strip().split(',')
            longitudes = lines[4].strip().split(',')
            
            # Check consistency
            lengths = [len(station_ids), len(names), len(abbreviations), 
                      len(latitudes), len(longitudes)]
            if len(set(lengths)) > 1:
                result.add_error(f"Inconsistent number of columns: {lengths}")
            
            # Validate each station
            for i, station_id in enumerate(station_ids):
                if i < len(names) and i < len(abbreviations) and i < len(latitudes) and i < len(longitudes):
                    station_data = {
                        'station_id': station_id.strip(),
                        'name': names[i].strip(),
                        'abbreviation': abbreviations[i].strip(),
                        'latitude': float(latitudes[i].strip()) if latitudes[i].strip() else None,
                        'longitude': float(longitudes[i].strip()) if longitudes[i].strip() else None,
                    }
                    
                    station_result = StationDataValidator.validate_station_info(station_data)
                    if not station_result.is_valid:
                        result.add_error(f"Station {station_id} validation failed: {station_result.errors}")
        
        except Exception as e:
            result.add_error(f"Error reading station CSV file: {e}")
        
        return result


class EPWFileValidator:
    """Validator for EPW files."""
    
    @staticmethod
    def validate_epw_file(epw_path: Union[str, Path]) -> ValidationResult:
        """Validate EPW file format and content."""
        result = ValidationResult()
        epw_path = Path(epw_path)
        
        if not epw_path.exists():
            result.add_error(f"EPW file does not exist: {epw_path}")
            return result
        
        try:
            with open(epw_path, 'r') as f:
                lines = f.readlines()
            
            if len(lines) < 8:
                result.add_error("EPW file must have at least 8 header lines")
                return result
            
            # Validate header lines
            header_keywords = ['LOCATION', 'DESIGN CONDITIONS', 'TYPICAL/EXTREME PERIODS',
                             'GROUND TEMPERATURES', 'HOLIDAYS/DAYLIGHT SAVINGS',
                             'COMMENTS 1', 'COMMENTS 2', 'DATA PERIODS']
            
            for i, keyword in enumerate(header_keywords):
                if i < len(lines) and not lines[i].startswith(keyword):
                    result.add_warning(f"Expected '{keyword}' in line {i+1}, got: {lines[i][:50]}")
            
            # Count data lines
            data_lines = lines[8:]  # Skip header
            if len(data_lines) != 8760:
                if len(data_lines) == 8784:
                    result.add_warning("EPW file has leap year data (8784 records)")
                else:
                    result.add_error(f"Expected 8760 data lines, got {len(data_lines)}")
            
            # Validate sample data lines
            for i, line in enumerate(data_lines[:10]):  # Check first 10 data lines
                fields = line.strip().split(',')
                if len(fields) < 35:  # EPW format has 35 fields
                    result.add_error(f"Data line {i+9} has insufficient fields: {len(fields)}")
                
                # Validate year, month, day, hour
                try:
                    year, month, day, hour = int(fields[0]), int(fields[1]), int(fields[2]), int(fields[3])
                    if not (1 <= month <= 12):
                        result.add_error(f"Invalid month in line {i+9}: {month}")
                    if not (1 <= day <= 31):
                        result.add_error(f"Invalid day in line {i+9}: {day}")
                    if not (1 <= hour <= 24):
                        result.add_error(f"Invalid hour in line {i+9}: {hour}")
                except (ValueError, IndexError):
                    result.add_error(f"Invalid date/time format in line {i+9}")
        
        except Exception as e:
            result.add_error(f"Error reading EPW file: {e}")
        
        return result


def validate_year(year: Union[int, str]) -> ValidationResult:
    """Validate year parameter."""
    result = ValidationResult()
    
    try:
        year_int = int(year)
        current_year = datetime.now().year
        
        if year_int < 1950:
            result.add_error(f"Year too old: {year_int} (minimum: 1950)")
        elif year_int > current_year + 1:
            result.add_error(f"Year too far in future: {year_int} (maximum: {current_year + 1})")
        
    except (ValueError, TypeError):
        result.add_error(f"Invalid year format: {year}")
    
    return result


def validate_file_path(file_path: Union[str, Path], must_exist: bool = True,
                      must_be_readable: bool = True, must_be_writable: bool = False) -> ValidationResult:
    """Validate file path with various requirements."""
    result = ValidationResult()
    
    try:
        path = Path(file_path)
        
        if must_exist and not path.exists():
            result.add_error(f"File does not exist: {file_path}")
        
        if path.exists():
            if must_be_readable and not os.access(path, os.R_OK):
                result.add_error(f"File is not readable: {file_path}")
            
            if must_be_writable and not os.access(path, os.W_OK):
                result.add_error(f"File is not writable: {file_path}")
            
            if path.is_dir():
                result.add_error(f"Path is a directory, not a file: {file_path}")
        
        # Check parent directory exists and is writable (for new files)
        if not path.exists() and must_be_writable:
            parent = path.parent
            if not parent.exists():
                result.add_error(f"Parent directory does not exist: {parent}")
            elif not os.access(parent, os.W_OK):
                result.add_error(f"Parent directory is not writable: {parent}")
    
    except Exception as e:
        result.add_error(f"Error validating file path: {e}")
    
    return result
