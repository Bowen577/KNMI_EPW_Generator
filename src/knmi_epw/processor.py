"""
Data processing module for KNMI EPW Generator.

This module handles processing and validation of KNMI weather data,
including parsing, unit conversions, and quality checks.
"""

import pandas as pd
import numpy as np
import pvlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Iterator, Generator
import logging
from datetime import datetime
import gc
import psutil
from tqdm import tqdm

from .config import Config
from .station_manager import WeatherStation
from .utils import SimpleCache, IntelligentCache, calculate_file_hash

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Exception raised when data validation fails."""
    pass


class MemoryMonitor:
    """Monitor memory usage during data processing."""

    def __init__(self):
        self.process = psutil.Process()
        self.peak_memory = 0

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, memory_mb)
        return memory_mb

    def log_memory_usage(self, context: str = ""):
        """Log current memory usage."""
        memory_mb = self.get_memory_usage()
        logger.debug(f"Memory usage {context}: {memory_mb:.1f} MB (peak: {self.peak_memory:.1f} MB)")

    def force_garbage_collection(self):
        """Force garbage collection to free memory."""
        gc.collect()
        self.log_memory_usage("after GC")


class DataProcessor:
    """Processes KNMI weather data for EPW generation."""
    
    def __init__(self, config: Config):
        """
        Initialize data processor.

        Args:
            config: Configuration object
        """
        self.config = config
        self._memory_monitor = MemoryMonitor()

        # Initialize intelligent cache if enabled
        if config.processing.cache_enabled:
            cache_dir = Path(config.paths.data_dir) / "cache" / "processed_data"
            self.cache = IntelligentCache(cache_dir, max_size_mb=1000, default_ttl=7*24*3600)  # 7 days TTL
        else:
            self.cache = None
        
        # Unit conversion factors for KNMI data
        self.unit_conversions = {
            'ghi': 10000 / 3600,  # J/cm2 to W/m2
            'DD': 1,              # Wind direction (degrees)
            'FH': 0.1,            # Wind speed (0.1 m/s to m/s)
            'T': 0.1,             # Temperature (0.1 °C to °C)
            'TD': 0.1,            # Dew point temperature (0.1 °C to °C)
            'DR': 0.1,            # Precipitation duration (0.1 h to h)
            'RH': 0.1,            # Precipitation amount (0.1 mm to mm)
            'P': 10,              # Pressure (0.1 hPa to Pa)
            'VV': 0.1,            # Visibility (units to km)
            'N': 10 / 9,          # Cloud cover (octas to tenths)
            'U': 1,               # Relative humidity (%)
            'R': 1,               # Rain indicator
            'solar_zenith': 1     # Solar zenith angle (degrees)
        }
        
        # EPW column mapping
        self.epw_column_mapping = {
            'ghi': 13,    # Global horizontal irradiance
            'dni': 14,    # Direct normal irradiance
            'dhi': 15,    # Diffuse horizontal irradiance
            'DD': 20,     # Wind direction
            'FH': 21,     # Wind speed
            'T': 6,       # Dry bulb temperature
            'TD': 7,      # Dew point temperature
            'DR': 34,     # Precipitation duration
            'RH': 33,     # Precipitation amount
            'P': 9,       # Atmospheric pressure
            'VV': 24,     # Visibility
            'N': 23,      # Total sky cover
            'U': 8,       # Relative humidity
            'R': 26       # Present weather observation
        }
    
    def read_knmi_data(self, file_path: str, start_time: Optional[str] = None, 
                      end_time: Optional[str] = None) -> pd.DataFrame:
        """
        Read and parse KNMI data file.
        
        Args:
            file_path: Path to KNMI data file
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            Processed DataFrame with datetime index
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"KNMI data file not found: {file_path}")
        
        try:
            # Read CSV with proper handling of KNMI format
            df = pd.read_csv(file_path, sep=',', skiprows=self.config.processing.skiprows)
            
            # Clean column names
            df.columns = [col.strip() for col in df.columns]
            
            # Convert date/time columns to strings for processing
            df['YYYYMMDD'] = df['YYYYMMDD'].astype(str)
            df['HH'] = df['HH'].astype(str)
            
            # Process datetime
            df = self._process_datetime(df)
            
            # Set datetime index
            df.set_index('Datetime', inplace=True)
            df.index = pd.DatetimeIndex(df.index)
            
            # Apply time filtering if specified
            if start_time and end_time:
                df = df[start_time:end_time]
            
            logger.info(f"Loaded KNMI data: {len(df)} records from {file_path}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to read KNMI data from {file_path}: {e}")
            raise DataValidationError(f"KNMI data reading failed: {e}")
    
    def _process_datetime(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process KNMI datetime format to standard datetime."""
        processed_dates = []
        processed_hours = []
        
        for i, (date_str, hour_str) in enumerate(zip(df['YYYYMMDD'], df['HH'])):
            try:
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                hour = int(hour_str)
                
                # Handle leap year
                is_leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                days_in_month = {
                    1: 31, 2: 29 if is_leap else 28, 3: 31, 4: 30,
                    5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
                }
                
                # Handle hour 24 (next day at 00:00)
                if hour == 24:
                    hour = 0
                    day += 1
                    if day > days_in_month[month]:
                        day = 1
                        month += 1
                        if month > 12:
                            month = 1
                            year += 1
                
                processed_dates.append(f"{year:04d}-{month:02d}-{day:02d}")
                processed_hours.append(f"{hour:02d}:00:00")
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid datetime at row {i}: {date_str} {hour_str} - {e}")
                processed_dates.append(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}")
                processed_hours.append(f"{hour_str.zfill(2)}:00:00")
        
        # Create datetime column
        df['Datetime'] = [f"{date} {time}" for date, time in zip(processed_dates, processed_hours)]
        
        # Remove original date/time columns
        df.drop(['YYYYMMDD', 'HH'], axis=1, inplace=True)
        
        return df
    
    def process_weather_data(self, knmi_data: pd.DataFrame, station: WeatherStation,
                           year: int) -> pd.DataFrame:
        """
        Process KNMI weather data for EPW generation.

        Args:
            knmi_data: Raw KNMI data DataFrame
            station: Weather station information
            year: Year being processed

        Returns:
            Processed DataFrame ready for EPW generation
        """
        # Check cache first
        cache_key = f"processed_weather_{station.station_id}_{year}"
        if self.cache and self.cache.has(cache_key):
            logger.info(f"Loading processed weather data from cache for station {station.station_id} year {year}")
            cached_data = self.cache.get(cache_key)
            if cached_data is not None and len(cached_data) > 0:
                logger.info(f"Loaded {len(cached_data)} processed weather records from cache")
                return cached_data

        logger.info(f"Processing weather data for station {station.station_id} year {year}")

        try:
            # Create a copy to avoid modifying original data
            data = knmi_data.copy()
            
            # Handle leap year - remove Feb 29 if present
            if year % 4 == 0:
                try:
                    feb29_range = pd.date_range(
                        f'{year}-02-29 00:00:00', 
                        f'{year}-02-29 23:00:00', 
                        freq='H'
                    )
                    data = data.drop(feb29_range, errors='ignore')
                except Exception as e:
                    logger.warning(f"Could not remove Feb 29 data: {e}")
            
            # Calculate solar position
            times = data.index
            solpos = pvlib.solarposition.get_solarposition(
                times, station.latitude, station.longitude
            )
            data['solar_zenith'] = solpos['apparent_zenith']
            
            # Extract and clean weather variables
            weather_vars = self._extract_weather_variables(data)
            
            # Apply unit conversions
            weather_vars = self._apply_unit_conversions(weather_vars)
            
            # Calculate solar radiation components
            weather_vars = self._calculate_solar_radiation(weather_vars, times)
            
            # Apply data quality fixes
            weather_vars = self._apply_data_quality_fixes(weather_vars)
            
            # Fill missing values with appropriate defaults
            weather_vars = self._fill_missing_values(weather_vars)

            # Cache the processed data
            if self.cache:
                self.cache.set(cache_key, weather_vars, data_type="csv")
                logger.debug(f"Cached processed weather data for station {station.station_id} year {year}")

            logger.info(f"Successfully processed {len(weather_vars)} weather records")
            return weather_vars
            
        except Exception as e:
            logger.error(f"Weather data processing failed: {e}")
            raise DataValidationError(f"Weather data processing failed: {e}")
    
    def _extract_weather_variables(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract relevant weather variables from KNMI data."""
        variables = ['DD', 'FH', 'T', 'TD', 'DR', 'RH', 'P', 'VV', 'N', 'U', 'R', 'Q']
        
        # Check if solar zenith was already added
        if 'solar_zenith' in data.columns:
            variables.append('solar_zenith')
        
        # Extract available variables
        available_vars = [var for var in variables if var in data.columns]
        extracted = data[available_vars].copy()
        
        # Rename Q to ghi for consistency
        if 'Q' in extracted.columns:
            extracted['ghi'] = extracted['Q']
            extracted.drop('Q', axis=1, inplace=True)
        
        return extracted
    
    def _apply_unit_conversions(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply unit conversions to KNMI data."""
        converted = data.copy()
        
        # Replace empty strings and spaces with NaN
        converted = converted.replace(['', '     ', '    ', '   ', '  ', ' '], np.nan)
        
        # Convert to numeric
        for col in converted.columns:
            converted[col] = pd.to_numeric(converted[col], errors='coerce')
        
        # Apply unit conversions
        for col in converted.columns:
            if col in self.unit_conversions:
                converted[col] *= self.unit_conversions[col]
        
        return converted
    
    def _calculate_solar_radiation(self, data: pd.DataFrame, times: pd.DatetimeIndex) -> pd.DataFrame:
        """Calculate direct and diffuse solar radiation components."""
        if 'ghi' not in data.columns or 'solar_zenith' not in data.columns:
            logger.warning("Cannot calculate solar radiation: missing GHI or solar zenith data")
            return data
        
        try:
            # Calculate DNI using DIRINT model
            data['dni'] = pvlib.irradiance.dirint(
                data['ghi'], data['solar_zenith'], times
            )
            
            # Calculate DHI
            data['dhi'] = (data['ghi'] - 
                          data['dni'] * pvlib.tools.cosd(data['solar_zenith']))
            
            # Remove solar zenith as it's no longer needed
            data.drop('solar_zenith', axis=1, inplace=True)
            
        except Exception as e:
            logger.warning(f"Solar radiation calculation failed: {e}")
            # Set default values if calculation fails
            data['dni'] = 0
            data['dhi'] = data.get('ghi', 0)
        
        return data
    
    def _apply_data_quality_fixes(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply data quality fixes and corrections."""
        fixed = data.copy()
        
        # Fix cloud cover (round to nearest integer)
        if 'N' in fixed.columns:
            fixed['N'] = fixed['N'].round()
        
        # Fix rain indicator (0 -> 9, 1 -> 0 for EPW format)
        if 'R' in fixed.columns:
            rain_mask = fixed['R'] == 0
            no_rain_mask = fixed['R'] == 1
            fixed.loc[rain_mask, 'R'] = 9
            fixed.loc[no_rain_mask, 'R'] = 0
        
        # Fix wind direction (360 -> 0)
        if 'DD' in fixed.columns:
            fixed.loc[fixed['DD'] == 360, 'DD'] = 0
        
        return fixed
    
    def _fill_missing_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fill missing values with EPW-appropriate defaults."""
        defaults = {
            'DD': 999,      # Wind direction missing
            'FH': 999,      # Wind speed missing
            'T': 99.9,      # Temperature missing
            'TD': 99.9,     # Dew point missing
            'DR': 0,        # No precipitation duration
            'RH': 0,        # No precipitation
            'P': 999999,    # Pressure missing
            'VV': 9999,     # Visibility missing
            'N': 99,        # Cloud cover missing
            'U': 999,       # Humidity missing
            'R': 9,         # Weather observation missing
            'ghi': 0,       # No solar radiation
            'dni': 0,       # No direct radiation
            'dhi': 0        # No diffuse radiation
        }
        
        filled = data.copy()
        for col, default_val in defaults.items():
            if col in filled.columns:
                filled[col].fillna(default_val, inplace=True)
        
        return filled

    def validate_processed_data(self, data: pd.DataFrame) -> bool:
        """
        Validate processed weather data for quality and completeness.

        Args:
            data: Processed weather DataFrame

        Returns:
            True if data passes validation
        """
        try:
            # Check if DataFrame is not empty
            if data.empty:
                logger.error("Data validation failed: DataFrame is empty")
                return False

            # Check for required columns
            required_cols = ['T', 'U', 'P', 'ghi']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                logger.error(f"Data validation failed: Missing required columns: {missing_cols}")
                return False

            # Check for reasonable value ranges
            validations = [
                ('T', -50, 60, "Temperature"),
                ('U', 0, 100, "Relative humidity"),
                ('P', 80000, 110000, "Pressure"),
                ('ghi', 0, 1500, "Global horizontal irradiance"),
                ('FH', 0, 100, "Wind speed")
            ]

            for col, min_val, max_val, desc in validations:
                if col in data.columns:
                    out_of_range = ((data[col] < min_val) | (data[col] > max_val)).sum()
                    if out_of_range > len(data) * 0.1:  # More than 10% out of range
                        logger.warning(f"{desc} has {out_of_range} values out of range [{min_val}, {max_val}]")

            # Check temporal continuity
            if len(data) < 8760:  # Less than a full year
                logger.warning(f"Data validation: Only {len(data)} hours of data (expected ~8760)")

            logger.info("Data validation passed")
            return True

        except Exception as e:
            logger.error(f"Data validation failed with error: {e}")
            return False

    def read_knmi_data_chunked(self, file_path: str, chunk_size: int = None,
                              start_time: Optional[str] = None,
                              end_time: Optional[str] = None) -> Iterator[pd.DataFrame]:
        """
        Read KNMI data file in chunks for memory-efficient processing.

        Args:
            file_path: Path to KNMI data file
            chunk_size: Size of chunks to read
            start_time: Optional start time filter
            end_time: Optional end time filter

        Yields:
            Chunks of processed DataFrame
        """
        if chunk_size is None:
            chunk_size = self.config.processing.chunk_size

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"KNMI data file not found: {file_path}")

        self._memory_monitor.log_memory_usage("before chunked reading")

        try:
            # Read file in chunks
            chunk_reader = pd.read_csv(
                file_path,
                sep=',',
                skiprows=self.config.processing.skiprows,
                chunksize=chunk_size
            )

            for chunk_idx, chunk in enumerate(chunk_reader):
                try:
                    # Clean column names
                    chunk.columns = [col.strip() for col in chunk.columns]

                    # Convert date/time columns to strings for processing
                    chunk['YYYYMMDD'] = chunk['YYYYMMDD'].astype(str)
                    chunk['HH'] = chunk['HH'].astype(str)

                    # Process datetime
                    chunk = self._process_datetime(chunk)

                    # Set datetime index
                    chunk.set_index('Datetime', inplace=True)
                    chunk.index = pd.DatetimeIndex(chunk.index)

                    # Apply time filtering if specified
                    if start_time and end_time:
                        chunk = chunk[start_time:end_time]

                    # Skip empty chunks
                    if len(chunk) == 0:
                        continue

                    logger.debug(f"Processed chunk {chunk_idx + 1}: {len(chunk)} records")
                    self._memory_monitor.log_memory_usage(f"after chunk {chunk_idx + 1}")

                    yield chunk

                    # Force garbage collection periodically
                    if chunk_idx % 10 == 0:
                        self._memory_monitor.force_garbage_collection()

                except Exception as e:
                    logger.warning(f"Error processing chunk {chunk_idx + 1}: {e}")
                    continue

            logger.info(f"Completed chunked reading of {file_path}")

        except Exception as e:
            logger.error(f"Failed to read KNMI data from {file_path} in chunks: {e}")
            raise DataValidationError(f"Chunked KNMI data reading failed: {e}")

    def process_weather_data_streaming(self, file_path: str, station: WeatherStation,
                                     year: int, chunk_size: int = None) -> pd.DataFrame:
        """
        Process KNMI weather data using streaming approach for memory efficiency.

        Args:
            file_path: Path to KNMI data file
            station: Weather station information
            year: Year being processed
            chunk_size: Size of chunks for processing

        Returns:
            Processed DataFrame ready for EPW generation
        """
        logger.info(f"Processing weather data (streaming) for station {station.station_id} year {year}")

        if chunk_size is None:
            chunk_size = self.config.processing.chunk_size

        self._memory_monitor.log_memory_usage("before streaming processing")

        try:
            processed_chunks = []
            total_records = 0

            # Process data in chunks
            with tqdm(desc="Processing chunks", unit="chunk") as pbar:
                for chunk in self.read_knmi_data_chunked(file_path, chunk_size):
                    # Handle leap year - remove Feb 29 if present
                    if year % 4 == 0:
                        try:
                            feb29_range = pd.date_range(
                                f'{year}-02-29 00:00:00',
                                f'{year}-02-29 23:00:00',
                                freq='H'
                            )
                            chunk = chunk.drop(feb29_range, errors='ignore')
                        except Exception as e:
                            logger.warning(f"Could not remove Feb 29 data from chunk: {e}")

                    if len(chunk) == 0:
                        continue

                    # Calculate solar position for this chunk
                    times = chunk.index
                    solpos = pvlib.solarposition.get_solarposition(
                        times, station.latitude, station.longitude
                    )
                    chunk['solar_zenith'] = solpos['apparent_zenith']

                    # Extract and clean weather variables
                    weather_vars = self._extract_weather_variables(chunk)

                    # Apply unit conversions
                    weather_vars = self._apply_unit_conversions(weather_vars)

                    # Calculate solar radiation components
                    weather_vars = self._calculate_solar_radiation(weather_vars, times)

                    # Apply data quality fixes
                    weather_vars = self._apply_data_quality_fixes(weather_vars)

                    # Fill missing values with appropriate defaults
                    weather_vars = self._fill_missing_values(weather_vars)

                    processed_chunks.append(weather_vars)
                    total_records += len(weather_vars)

                    pbar.update(1)
                    pbar.set_postfix_str(f"{total_records} records")

                    # Memory management
                    del chunk, weather_vars, solpos
                    if len(processed_chunks) % 5 == 0:
                        self._memory_monitor.force_garbage_collection()

            # Combine all processed chunks
            logger.info("Combining processed chunks...")
            self._memory_monitor.log_memory_usage("before combining chunks")

            if not processed_chunks:
                raise DataValidationError("No data chunks were successfully processed")

            final_data = pd.concat(processed_chunks, ignore_index=False)
            final_data = final_data.sort_index()

            # Clean up
            del processed_chunks
            self._memory_monitor.force_garbage_collection()

            logger.info(f"Successfully processed {len(final_data)} weather records (streaming)")
            self._memory_monitor.log_memory_usage("after streaming processing")

            return final_data

        except Exception as e:
            logger.error(f"Streaming weather data processing failed: {e}")
            raise DataValidationError(f"Streaming weather data processing failed: {e}")
