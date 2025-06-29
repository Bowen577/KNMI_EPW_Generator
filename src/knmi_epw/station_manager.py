"""
Weather station management for KNMI EPW Generator.

This module handles loading and managing weather station information,
including coordinates, names, and data availability.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class WeatherStation:
    """Represents a KNMI weather station."""
    station_id: str
    name: str
    abbreviation: str
    latitude: float
    longitude: float
    
    def __str__(self) -> str:
        return f"Station {self.station_id}: {self.name} ({self.abbreviation})"
    
    def __repr__(self) -> str:
        return (f"WeatherStation(id='{self.station_id}', name='{self.name}', "
                f"lat={self.latitude}, lon={self.longitude})")


class StationManager:
    """Manages KNMI weather station information and operations."""
    
    def __init__(self, station_info_file: str):
        """
        Initialize station manager.
        
        Args:
            station_info_file: Path to CSV file containing station information
        """
        self.station_info_file = Path(station_info_file)
        self.stations: Dict[str, WeatherStation] = {}
        self._load_stations()
    
    def _load_stations(self):
        """Load station information from CSV file."""
        if not self.station_info_file.exists():
            raise FileNotFoundError(f"Station info file not found: {self.station_info_file}")
        
        try:
            # Read the CSV file with station information
            df = pd.read_csv(self.station_info_file)
            
            # Extract station data from the specific format
            station_ids = df.columns.tolist()
            locations = df.iloc[0].tolist()
            abbreviations = df.iloc[1].tolist()
            latitudes = df.iloc[2].tolist()
            longitudes = df.iloc[3].tolist()
            
            # Create WeatherStation objects
            for i, station_id in enumerate(station_ids):
                try:
                    station = WeatherStation(
                        station_id=str(station_id),
                        name=locations[i],
                        abbreviation=abbreviations[i],
                        latitude=float(latitudes[i]),
                        longitude=float(longitudes[i])
                    )
                    self.stations[station_id] = station
                    logger.debug(f"Loaded station: {station}")
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to load station {station_id}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.stations)} weather stations")
            
        except Exception as e:
            logger.error(f"Failed to load station information: {e}")
            raise
    
    def get_station(self, station_id: str) -> Optional[WeatherStation]:
        """Get station by ID."""
        return self.stations.get(str(station_id))
    
    def get_all_stations(self) -> Dict[str, WeatherStation]:
        """Get all stations."""
        return self.stations.copy()
    
    def get_station_ids(self) -> List[str]:
        """Get list of all station IDs."""
        return list(self.stations.keys())
    
    def get_stations_by_name(self, name_pattern: str) -> List[WeatherStation]:
        """Get stations matching name pattern (case-insensitive)."""
        pattern = name_pattern.lower()
        return [
            station for station in self.stations.values()
            if pattern in station.name.lower()
        ]
    
    def get_nearest_stations(self, latitude: float, longitude: float, 
                           count: int = 5) -> List[Tuple[WeatherStation, float]]:
        """
        Get nearest stations to given coordinates.
        
        Args:
            latitude: Target latitude
            longitude: Target longitude
            count: Number of nearest stations to return
            
        Returns:
            List of (station, distance) tuples sorted by distance
        """
        stations_with_distance = []
        
        for station in self.stations.values():
            # Simple Euclidean distance (good enough for Netherlands)
            distance = ((station.latitude - latitude) ** 2 + 
                       (station.longitude - longitude) ** 2) ** 0.5
            stations_with_distance.append((station, distance))
        
        # Sort by distance and return top N
        stations_with_distance.sort(key=lambda x: x[1])
        return stations_with_distance[:count]
    
    def validate_station_id(self, station_id: str) -> bool:
        """Check if station ID is valid."""
        return str(station_id) in self.stations
    
    def get_station_summary(self) -> pd.DataFrame:
        """Get summary DataFrame of all stations."""
        data = []
        for station in self.stations.values():
            data.append({
                'station_id': station.station_id,
                'name': station.name,
                'abbreviation': station.abbreviation,
                'latitude': station.latitude,
                'longitude': station.longitude
            })
        
        return pd.DataFrame(data)
    
    def export_stations(self, output_file: str, format: str = 'csv'):
        """
        Export station information to file.
        
        Args:
            output_file: Output file path
            format: Export format ('csv', 'json', 'yaml')
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df = self.get_station_summary()
        
        if format.lower() == 'csv':
            df.to_csv(output_path, index=False)
        elif format.lower() == 'json':
            df.to_json(output_path, orient='records', indent=2)
        elif format.lower() == 'yaml':
            import yaml
            data = df.to_dict('records')
            with open(output_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Exported {len(df)} stations to {output_path}")
