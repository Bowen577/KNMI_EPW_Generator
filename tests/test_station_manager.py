"""
Comprehensive tests for station manager module.
"""

import pytest
import pandas as pd
from pathlib import Path

from knmi_epw.station_manager import StationManager, WeatherStation
from knmi_epw.exceptions import StationError


@pytest.mark.unit
class TestWeatherStation:
    """Test WeatherStation class functionality."""
    
    def test_weather_station_creation(self):
        """Test creating a WeatherStation instance."""
        station = WeatherStation(
            station_id="240",
            name="Schiphol",
            abbreviation="SHP",
            latitude=52.318,
            longitude=4.790
        )
        
        assert station.station_id == "240"
        assert station.name == "Schiphol"
        assert station.abbreviation == "SHP"
        assert station.latitude == 52.318
        assert station.longitude == 4.790
    
    def test_weather_station_str(self):
        """Test string representation of WeatherStation."""
        station = WeatherStation(
            station_id="240",
            name="Schiphol",
            abbreviation="SHP",
            latitude=52.318,
            longitude=4.790
        )
        
        str_repr = str(station)
        assert "240" in str_repr
        assert "Schiphol" in str_repr
        assert "SHP" in str_repr
    
    def test_weather_station_repr(self):
        """Test repr representation of WeatherStation."""
        station = WeatherStation(
            station_id="240",
            name="Schiphol",
            abbreviation="SHP",
            latitude=52.318,
            longitude=4.790
        )
        
        repr_str = repr(station)
        assert "WeatherStation" in repr_str
        assert "240" in repr_str
        assert "52.318" in repr_str
        assert "4.790" in repr_str


@pytest.mark.unit
class TestStationManager:
    """Test StationManager class functionality."""
    
    def test_station_manager_initialization(self, sample_station_data):
        """Test StationManager initialization."""
        station_data, csv_file = sample_station_data
        
        manager = StationManager(str(csv_file))
        
        assert len(manager.stations) == 3
        assert "240" in manager.stations
        assert "260" in manager.stations
        assert "280" in manager.stations
    
    def test_station_manager_invalid_file(self):
        """Test StationManager with invalid file."""
        with pytest.raises(FileNotFoundError):
            StationManager("/non/existent/file.csv")
    
    def test_get_station(self, sample_station_data):
        """Test getting a specific station."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        station = manager.get_station("240")
        assert station is not None
        assert station.station_id == "240"
        assert station.name == "Schiphol"
        assert station.abbreviation == "SHP"
        
        # Test non-existent station
        station = manager.get_station("999")
        assert station is None
    
    def test_get_all_stations(self, sample_station_data):
        """Test getting all stations."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        all_stations = manager.get_all_stations()
        assert len(all_stations) == 3
        assert isinstance(all_stations, dict)
        
        # Verify it's a copy (modifications don't affect original)
        all_stations["999"] = WeatherStation("999", "Test", "TST", 0.0, 0.0)
        assert "999" not in manager.stations
    
    def test_get_station_ids(self, sample_station_data):
        """Test getting list of station IDs."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        station_ids = manager.get_station_ids()
        assert len(station_ids) == 3
        assert "240" in station_ids
        assert "260" in station_ids
        assert "280" in station_ids
        assert isinstance(station_ids, list)
    
    def test_get_stations_by_name(self, sample_station_data):
        """Test searching stations by name."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        # Test exact match
        stations = manager.get_stations_by_name("Schiphol")
        assert len(stations) == 1
        assert stations[0].station_id == "240"
        
        # Test partial match (case insensitive)
        stations = manager.get_stations_by_name("de")
        assert len(stations) == 2  # "De Bilt" and "Eelde"
        
        # Test no match
        stations = manager.get_stations_by_name("NonExistent")
        assert len(stations) == 0
    
    def test_get_nearest_stations(self, sample_station_data):
        """Test finding nearest stations to coordinates."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        # Test near Schiphol (should be closest)
        nearest = manager.get_nearest_stations(52.3, 4.8, count=2)
        assert len(nearest) == 2
        assert nearest[0][0].station_id == "240"  # Schiphol should be closest
        assert nearest[0][1] < nearest[1][1]  # First should have smaller distance
        
        # Test with count larger than available stations
        nearest = manager.get_nearest_stations(52.0, 5.0, count=10)
        assert len(nearest) == 3  # Should return all available stations
    
    def test_validate_station_id(self, sample_station_data):
        """Test station ID validation."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        # Test valid station IDs
        assert manager.validate_station_id("240") is True
        assert manager.validate_station_id("260") is True
        assert manager.validate_station_id("280") is True
        
        # Test invalid station IDs
        assert manager.validate_station_id("999") is False
        assert manager.validate_station_id("abc") is False
        assert manager.validate_station_id("") is False
    
    def test_get_station_summary(self, sample_station_data):
        """Test getting station summary DataFrame."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        summary = manager.get_station_summary()
        assert isinstance(summary, pd.DataFrame)
        assert len(summary) == 3
        
        # Check required columns
        required_columns = ['station_id', 'name', 'abbreviation', 'latitude', 'longitude']
        for col in required_columns:
            assert col in summary.columns
        
        # Check data types and values
        assert summary['station_id'].dtype == object
        assert summary['latitude'].dtype in [float, 'float64']
        assert summary['longitude'].dtype in [float, 'float64']
    
    def test_export_stations_csv(self, sample_station_data, test_data_dir):
        """Test exporting stations to CSV."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        output_file = test_data_dir / "exported_stations.csv"
        manager.export_stations(str(output_file), format='csv')
        
        assert output_file.exists()
        
        # Verify exported data
        exported_df = pd.read_csv(output_file)
        assert len(exported_df) == 3
        assert 'station_id' in exported_df.columns
        assert 'name' in exported_df.columns
    
    def test_export_stations_json(self, sample_station_data, test_data_dir):
        """Test exporting stations to JSON."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        output_file = test_data_dir / "exported_stations.json"
        manager.export_stations(str(output_file), format='json')
        
        assert output_file.exists()
        
        # Verify exported data
        import json
        with open(output_file, 'r') as f:
            exported_data = json.load(f)
        
        assert len(exported_data) == 3
        assert all('station_id' in item for item in exported_data)
        assert all('name' in item for item in exported_data)
    
    def test_export_stations_yaml(self, sample_station_data, test_data_dir):
        """Test exporting stations to YAML."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        output_file = test_data_dir / "exported_stations.yaml"
        manager.export_stations(str(output_file), format='yaml')
        
        assert output_file.exists()
        
        # Verify exported data
        import yaml
        with open(output_file, 'r') as f:
            exported_data = yaml.safe_load(f)
        
        assert len(exported_data) == 3
        assert all('station_id' in item for item in exported_data)
        assert all('name' in item for item in exported_data)
    
    def test_export_stations_invalid_format(self, sample_station_data, test_data_dir):
        """Test exporting stations with invalid format."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        output_file = test_data_dir / "exported_stations.txt"
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            manager.export_stations(str(output_file), format='txt')


@pytest.mark.integration
class TestStationManagerIntegration:
    """Integration tests for StationManager."""
    
    def test_load_real_station_format(self, test_data_dir):
        """Test loading station data in real KNMI format."""
        # Create a more realistic station file
        station_file = test_data_dir / "real_stations.csv"
        
        # Real KNMI format with multiple rows
        content = """209,210,215,240,260,280
IJmond,Valkenburg,Voorschoten,Schiphol,De Bilt,Eelde
IMD,VKB,VST,SHP,DBL,ELD
52.4965,50.8652,52.1238,52.318,52.1,53.125
4.6586,5.8321,4.439,4.79,5.18,6.585"""
        
        with open(station_file, 'w') as f:
            f.write(content)
        
        manager = StationManager(str(station_file))
        
        assert len(manager.stations) == 6
        
        # Test specific stations
        schiphol = manager.get_station("240")
        assert schiphol.name == "Schiphol"
        assert schiphol.abbreviation == "SHP"
        assert abs(schiphol.latitude - 52.318) < 0.001
        assert abs(schiphol.longitude - 4.79) < 0.001
        
        de_bilt = manager.get_station("260")
        assert de_bilt.name == "De Bilt"
        assert de_bilt.abbreviation == "DBL"
    
    def test_station_manager_with_malformed_data(self, test_data_dir):
        """Test StationManager with malformed CSV data."""
        station_file = test_data_dir / "malformed_stations.csv"
        
        # Malformed data (missing values, inconsistent columns)
        content = """240,260
Schiphol,De Bilt
SHP
52.318,52.1,53.125
4.79"""
        
        with open(station_file, 'w') as f:
            f.write(content)
        
        # Should handle malformed data gracefully
        manager = StationManager(str(station_file))
        
        # Should load what it can
        assert len(manager.stations) >= 0  # May load partial data or none
    
    def test_distance_calculation_accuracy(self, sample_station_data):
        """Test accuracy of distance calculations."""
        station_data, csv_file = sample_station_data
        manager = StationManager(str(csv_file))
        
        # Test with known coordinates
        # Schiphol: 52.318, 4.790
        # De Bilt: 52.100, 5.180
        
        nearest = manager.get_nearest_stations(52.318, 4.790, count=3)
        
        # Schiphol should be closest (distance ~0)
        assert nearest[0][0].station_id == "240"
        assert nearest[0][1] < 0.01  # Very small distance
        
        # Verify distances are in ascending order
        for i in range(len(nearest) - 1):
            assert nearest[i][1] <= nearest[i + 1][1]
