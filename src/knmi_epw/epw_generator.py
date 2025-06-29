"""
EPW file generation module for KNMI EPW Generator.

This module handles the creation of EnergyPlus Weather (EPW) files
from processed KNMI weather data.
"""

import pandas as pd
import numpy as np
import pvlib
import copy
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from .config import Config
from .station_manager import WeatherStation
from .processor import DataProcessor

logger = logging.getLogger(__name__)


class EPWGenerationError(Exception):
    """Exception raised when EPW generation fails."""
    pass


class EPWGenerator:
    """Generates EPW files from processed weather data."""
    
    def __init__(self, config: Config, processor: DataProcessor):
        """
        Initialize EPW generator.
        
        Args:
            config: Configuration object
            processor: Data processor instance
        """
        self.config = config
        self.processor = processor
        
        # EPW column indices for weather data
        self.epw_columns = {
            'year': 0, 'month': 1, 'day': 2, 'hour': 3, 'minute': 4,
            'dry_bulb_temp': 6, 'dew_point_temp': 7, 'relative_humidity': 8,
            'atmospheric_pressure': 9, 'extraterrestrial_horizontal_radiation': 10,
            'extraterrestrial_direct_normal_radiation': 11, 'horizontal_infrared_radiation': 12,
            'global_horizontal_radiation': 13, 'direct_normal_radiation': 14,
            'diffuse_horizontal_radiation': 15, 'global_horizontal_illuminance': 16,
            'direct_normal_illuminance': 17, 'diffuse_horizontal_illuminance': 18,
            'zenith_luminance': 19, 'wind_direction': 20, 'wind_speed': 21,
            'total_sky_cover': 23, 'visibility': 24, 'ceiling_height': 25,
            'present_weather_observation': 26, 'present_weather_codes': 27,
            'precipitable_water': 28, 'aerosol_optical_depth': 29,
            'snow_depth': 30, 'days_since_last_snowfall': 31,
            'albedo': 32, 'liquid_precipitation_depth': 33,
            'liquid_precipitation_quantity': 34
        }
    
    def read_epw_template(self, template_path: str, coerce_year: int = 2021) -> tuple:
        """
        Read EPW template file for structure and metadata.
        
        Args:
            template_path: Path to template EPW file
            coerce_year: Year to coerce the template data to
            
        Returns:
            Tuple of (epw_dataframe, metadata_lines)
        """
        template_path = Path(template_path)
        if not template_path.exists():
            raise FileNotFoundError(f"EPW template file not found: {template_path}")
        
        try:
            # Read metadata (first 8 lines)
            metadata = []
            with open(template_path, 'r', encoding='utf-8') as f:
                for i in range(self.config.processing.epw_skiprows):
                    metadata.append(f.readline())
            
            # Read weather data using pvlib for proper parsing
            epw_data, _ = pvlib.iotools.read_epw(template_path, coerce_year=coerce_year)
            
            # Read the full EPW data as DataFrame
            epw_df = pd.read_csv(
                template_path, 
                header=None, 
                sep=',', 
                skiprows=self.config.processing.epw_skiprows
            )
            
            # Set the index to match the pvlib data
            epw_df.index = epw_data.index
            
            # Ensure integer columns are properly typed
            int_columns = [0, 1, 2, 3, 4]
            for col in int_columns:
                if col < len(epw_df.columns):
                    epw_df[col] = epw_df[col].astype(int)
            
            logger.info(f"Loaded EPW template: {len(epw_df)} records")
            return epw_df, metadata
            
        except Exception as e:
            logger.error(f"Failed to read EPW template {template_path}: {e}")
            raise EPWGenerationError(f"EPW template reading failed: {e}")
    
    def generate_epw_file(self, weather_data: pd.DataFrame, station: WeatherStation,
                         year: int, output_path: str, template_path: Optional[str] = None) -> str:
        """
        Generate EPW file from processed weather data.
        
        Args:
            weather_data: Processed weather data DataFrame
            station: Weather station information
            year: Year of the data
            output_path: Output file path
            template_path: Optional template EPW file path
            
        Returns:
            Path to generated EPW file
        """
        logger.info(f"Generating EPW file for station {station.station_id} year {year}")
        
        try:
            # Use provided template or default
            if template_path is None:
                template_path = self.config.paths.epw_template_file
            
            # Read template
            epw_template, metadata = self.read_epw_template(template_path, coerce_year=year)
            
            # Create time index for the target year
            time_index = self._create_time_index(year)
            
            # Prepare EPW data structure
            epw_data = self._prepare_epw_data(epw_template, time_index, year)
            
            # Update metadata with station information
            updated_metadata = self._update_metadata(metadata, station)
            
            # Map weather data to EPW format
            epw_data = self._map_weather_data_to_epw(epw_data, weather_data)
            
            # Validate EPW data
            if not self._validate_epw_data(epw_data):
                raise EPWGenerationError("Generated EPW data failed validation")
            
            # Write EPW file
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._write_epw_file(epw_data, updated_metadata, output_path)
            
            logger.info(f"Successfully generated EPW file: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"EPW generation failed: {e}")
            raise EPWGenerationError(f"EPW generation failed: {e}")
    
    def _create_time_index(self, year: int) -> pd.DatetimeIndex:
        """Create time index for the specified year, handling leap years."""
        start_time = pd.Timestamp(f'{year}-01-01 00:00:00')
        end_time = pd.Timestamp(f'{year}-12-31 23:00:00')
        time_index = pd.date_range(start_time, end_time, freq='H')
        
        # Remove Feb 29 for leap years to maintain 8760 hours
        if year % 4 == 0:
            feb29_range = pd.date_range(
                f'{year}-02-29 00:00:00',
                f'{year}-02-29 23:00:00',
                freq='H'
            )
            time_index = time_index.drop(feb29_range)
        
        return time_index
    
    def _prepare_epw_data(self, template: pd.DataFrame, time_index: pd.DatetimeIndex, 
                         year: int) -> pd.DataFrame:
        """Prepare EPW data structure from template."""
        # Create a copy of the template
        epw_data = template.copy()
        
        # Adjust for time shift (move first hour to end)
        if len(epw_data) >= 2:
            first_two_rows = epw_data.iloc[0:2, :].copy()
            remaining_rows = epw_data.iloc[1:, :].copy()
            epw_data = pd.concat([remaining_rows, first_two_rows]).iloc[:-1, :]
        
        # Set new time index
        epw_data.index = time_index
        
        # Update year column
        epw_data[0] = year
        
        # Extract original time components for reference
        original_months = template[1].tolist()
        original_days = template[2].tolist()
        original_hours = template[3].tolist()
        
        # Update time columns with shifted values
        epw_data[1] = original_months[1:] + original_months[:1]
        epw_data[2] = original_days[1:] + original_days[:1]
        epw_data[3] = original_hours[1:] + original_hours[:1]
        
        return epw_data
    
    def _update_metadata(self, metadata: List[str], station: WeatherStation) -> List[str]:
        """Update EPW metadata with station information."""
        updated_metadata = copy.deepcopy(metadata)
        
        if len(updated_metadata) > 0:
            # Parse and update the location line (first line)
            location_parts = updated_metadata[0].split(',')
            if len(location_parts) >= 6:
                location_parts[1] = station.name  # City name
                
                # Update coordinates if available
                if not np.isnan(station.latitude):
                    location_parts[-4] = str(station.latitude)
                if not np.isnan(station.longitude):
                    location_parts[-3] = str(station.longitude)
                
                # Reconstruct the line
                updated_metadata[0] = ','.join(location_parts)
        
        return updated_metadata
    
    def _map_weather_data_to_epw(self, epw_data: pd.DataFrame, 
                                weather_data: pd.DataFrame) -> pd.DataFrame:
        """Map processed weather data to EPW format."""
        # Ensure weather data index matches EPW data index
        weather_data = weather_data.reindex(epw_data.index, method='nearest')
        
        # Map weather variables to EPW columns
        mapping = {
            'ghi': 13,    # Global horizontal radiation
            'dni': 14,    # Direct normal radiation
            'dhi': 15,    # Diffuse horizontal radiation
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
        
        # Apply the mapping
        for weather_var, epw_col in mapping.items():
            if weather_var in weather_data.columns and epw_col < len(epw_data.columns):
                epw_data.iloc[:, epw_col] = weather_data[weather_var].values
        
        # Ensure integer columns are properly typed
        int_columns = [0, 1, 2, 3, 4] + list(range(8, 21)) + [22, 23, 25, 26, 27, 28, 30, 31]
        for col in int_columns:
            if col < len(epw_data.columns):
                epw_data[col] = epw_data[col].astype(int, errors='ignore')
        
        return epw_data
    
    def _validate_epw_data(self, epw_data: pd.DataFrame) -> bool:
        """Validate generated EPW data."""
        try:
            # Check data length (should be 8760 hours)
            if len(epw_data) != 8760:
                logger.warning(f"EPW data length is {len(epw_data)}, expected 8760")
            
            # Check for required columns
            if len(epw_data.columns) < 35:
                logger.error(f"EPW data has {len(epw_data.columns)} columns, expected at least 35")
                return False
            
            # Check for reasonable temperature values
            temp_col = 6  # Dry bulb temperature
            if temp_col < len(epw_data.columns):
                temp_values = epw_data[temp_col]
                if temp_values.min() < -50 or temp_values.max() > 60:
                    logger.warning("Temperature values outside reasonable range")
            
            return True
            
        except Exception as e:
            logger.error(f"EPW validation failed: {e}")
            return False
    
    def _write_epw_file(self, epw_data: pd.DataFrame, metadata: List[str], 
                       output_path: Path):
        """Write EPW data and metadata to file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write metadata
            for line in metadata:
                f.write(line)
            
            # Write weather data
            epw_data.to_csv(f, sep=',', index=False, header=False, lineterminator='\n')
        
        logger.debug(f"EPW file written to {output_path}")
    
    def generate_multiple_epw_files(self, station_data_map: Dict[str, tuple],
                                  year: int, output_dir: str) -> Dict[str, str]:
        """
        Generate EPW files for multiple stations.
        
        Args:
            station_data_map: Dict mapping station_id -> (weather_data, station)
            year: Year of the data
            output_dir: Output directory
            
        Returns:
            Dict mapping station_id -> output_file_path
        """
        results = {}
        output_dir = Path(output_dir)
        
        for station_id, (weather_data, station) in station_data_map.items():
            try:
                # Create station-specific output directory
                station_dir = output_dir / station.name
                station_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate output filename
                output_file = station_dir / f"NLD_{station.abbreviation}_EPW_YR{year}.epw"
                
                # Generate EPW file
                result_path = self.generate_epw_file(
                    weather_data, station, year, str(output_file)
                )
                results[station_id] = result_path
                
            except Exception as e:
                logger.error(f"Failed to generate EPW for station {station_id}: {e}")
                results[station_id] = None
        
        return results
