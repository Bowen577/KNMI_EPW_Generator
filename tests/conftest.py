"""
Pytest configuration and fixtures for KNMI EPW Generator tests.

This module provides comprehensive test fixtures, mock data, and utilities
for testing all components of the KNMI EPW Generator package.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import yaml

from knmi_epw.config import Config, Paths, URLs, Processing
from knmi_epw.station_manager import StationManager, WeatherStation
from knmi_epw.exceptions import *


@pytest.fixture(scope="session")
def test_data_dir():
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp(prefix="knmi_epw_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_config(test_data_dir):
    """Create sample configuration for testing."""
    config = Config()
    config.paths.data_dir = str(test_data_dir / "data")
    config.paths.knmi_dir = str(test_data_dir / "data" / "knmi")
    config.paths.knmi_zip_dir = str(test_data_dir / "data" / "knmi_zip")
    config.paths.epw_output_dir = str(test_data_dir / "output" / "epw")
    config.paths.station_info_file = str(test_data_dir / "data" / "stations" / "knmi_STN_infor.csv")
    config.paths.epw_template_file = str(test_data_dir / "data" / "templates" / "template.epw")
    
    # Ensure directories exist
    config.ensure_directories()
    
    return config


@pytest.fixture
def sample_station_data(test_data_dir):
    """Create sample station information data."""
    station_data = {
        '240': {
            'name': 'Schiphol',
            'abbreviation': 'SHP',
            'latitude': 52.318,
            'longitude': 4.790
        },
        '260': {
            'name': 'De Bilt',
            'abbreviation': 'DBL',
            'latitude': 52.100,
            'longitude': 5.180
        },
        '280': {
            'name': 'Eelde',
            'abbreviation': 'ELD',
            'latitude': 53.125,
            'longitude': 6.585
        }
    }
    
    # Create CSV file in KNMI format
    stations_dir = test_data_dir / "data" / "stations"
    stations_dir.mkdir(parents=True, exist_ok=True)
    
    csv_file = stations_dir / "knmi_STN_infor.csv"
    
    # Create CSV content
    station_ids = list(station_data.keys())
    names = [station_data[sid]['name'] for sid in station_ids]
    abbreviations = [station_data[sid]['abbreviation'] for sid in station_ids]
    latitudes = [station_data[sid]['latitude'] for sid in station_ids]
    longitudes = [station_data[sid]['longitude'] for sid in station_ids]
    
    csv_content = f"{','.join(station_ids)}\n"
    csv_content += f"{','.join(names)}\n"
    csv_content += f"{','.join(abbreviations)}\n"
    csv_content += f"{','.join(map(str, latitudes))}\n"
    csv_content += f"{','.join(map(str, longitudes))}\n"
    
    with open(csv_file, 'w') as f:
        f.write(csv_content)
    
    return station_data, csv_file


@pytest.fixture
def sample_weather_stations(sample_station_data):
    """Create sample WeatherStation objects."""
    station_data, _ = sample_station_data
    stations = {}
    
    for station_id, data in station_data.items():
        stations[station_id] = WeatherStation(
            station_id=station_id,
            name=data['name'],
            abbreviation=data['abbreviation'],
            latitude=data['latitude'],
            longitude=data['longitude']
        )
    
    return stations


@pytest.fixture
def sample_knmi_data():
    """Create sample KNMI weather data."""
    # Create 24 hours of sample data
    dates = []
    hours = []
    
    base_date = "20230101"
    for hour in range(1, 25):  # KNMI uses 1-24 hour format
        dates.append(base_date)
        hours.append(hour)
    
    data = {
        'YYYYMMDD': dates,
        'HH': hours,
        'DD': np.random.randint(0, 360, 24),  # Wind direction
        'FH': np.random.randint(0, 200, 24),  # Wind speed (0.1 m/s)
        'T': np.random.randint(-100, 300, 24),  # Temperature (0.1 °C)
        'TD': np.random.randint(-150, 250, 24),  # Dew point (0.1 °C)
        'DR': np.random.randint(0, 10, 24),  # Precipitation duration (0.1 h)
        'RH': np.random.randint(0, 100, 24),  # Precipitation amount (0.1 mm)
        'P': np.random.randint(9800, 10300, 24),  # Pressure (0.1 hPa)
        'VV': np.random.randint(10, 999, 24),  # Visibility (0.1 km)
        'N': np.random.randint(0, 9, 24),  # Cloud cover (octas)
        'U': np.random.randint(30, 100, 24),  # Relative humidity (%)
        'R': np.random.choice([0, 1], 24),  # Rain indicator
        'Q': np.random.randint(0, 3000, 24)  # Global radiation (J/cm2)
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def sample_knmi_file(test_data_dir, sample_knmi_data):
    """Create sample KNMI data file."""
    knmi_dir = test_data_dir / "data" / "knmi"
    knmi_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = knmi_dir / "uurgeg_240_2023-2023.txt"
    
    # Create KNMI file header
    header_lines = [
        "BRON: KONINKLIJK NEDERLANDS METEOROLOGISCH INSTITUUT (KNMI)",
        "Opmerking: door stationsverplaatsing en verandering van waarneemmethodieken",
        "zijn deze tijdreeksen van uurwaarden mogelijk niet homogeen! Dat betekent dat",
        "deze reeks van gemeten waarden niet geschikt is voor trendanalyse. Voor",
        "studies naar klimaatverandering verwijzen we naar de gehomogeniseerde reeks",
        "maandtemperaturen van De Bilt <http://www.knmi.nl/klimatologie/onderzoeksgegevens/homogeen_260/index.html>",
        "of de Centraal Nederland Temperatuur <http://www.knmi.nl/klimatologie/onderzoeksgegevens/CNT/>.",
        "",
        "STN      LON(east)   LAT(north)     ALT(m)  NAME",
        "240:         4.790       52.318      -3.30  SCHIPHOL",
        "",
        "YYYYMMDD = datum (YYYY=jaar,MM=maand,DD=dag);",
        "HH       = tijd (HH=uur, UT.12 UT=13 MET, 24 UT=01 MET volgende dag);",
        "DD       = Windrichting (in graden) gemiddeld over de laatste 10 minuten van het afgelopen uur (360=noord, 90=oost, 180=zuid, 270=west, 0=windstil 990=veranderlijk. Zie http://www.knmi.nl/kennis-en-datacentrum/achtergrond/klimatologische-brochures-en-boeken);",
        "FH       = Uurgemiddelde windsnelheid (in 0.1 m/s). Zie http://www.knmi.nl/kennis-en-datacentrum/achtergrond/klimatologische-brochures-en-boeken;",
        "FF       = Windsnelheid (in 0.1 m/s) gemiddeld over de laatste 10 minuten van het afgelopen uur;",
        "FX       = Hoogste windstoot (in 0.1 m/s) over het afgelopen uurvak;",
        "T        = Temperatuur (in 0.1 graden Celsius) op 1.50 m hoogte tijdens de waarneming;",
        "T10N     = Minimumtemperatuur (in 0.1 graden Celsius) op 10 cm hoogte in de afgelopen 6 uur;",
        "TD       = Dauwpuntstemperatuur (in 0.1 graden Celsius) op 1.50 m hoogte tijdens de waarneming;",
        "SQ       = Duur van de zonneschijn (in 0.1 uren) per uurvak, berekend uit globale straling  (-1 voor <0.05 uur);",
        "Q        = Globale straling (in J/cm2) per uurvak;",
        "DR       = Duur van de neerslag (in 0.1 uur) per uurvak;",
        "RH       = Uursom van de neerslag (in 0.1 mm) (-1 voor <0.05 mm);",
        "P        = Luchtdruk (in 0.1 hPa) herleid naar zeeniveau, tijdens de waarneming;",
        "VV       = Horizontaal zicht tijdens de waarneming (0=minder dan 100m, 1=100-200m, 2=200-300m,..., 49=4900-5000m, 50=5-6km, 56=6-7km, 57=7-8km, ..., 79=29-30km, 80=30-35km, 81=35-40km,..., 89=meer dan 70km);",
        "N        = Bewolking (bedekkingsgraad van de bovenlucht in achtsten), tijdens de waarneming (9=bovenlucht onzichtbaar);",
        "U        = Relatieve vochtigheid (in procenten) op 1.50 m hoogte tijdens de waarneming;",
        "WW       = Weercode (00-99), visueel(WW) of automatisch(WaWa) waargenomen, voor het actuele weer of het weer in het afgelopen uur. Zie http://bibliotheek.knmi.nl/scholierenpdf/weercodes_Nederland;",
        "IX       = Weercode indicator voor de wijze van waarnemen op een bemand of automatisch station (1=bemand gebruikmakend van code uit visuele waarnemingen, 2,3=bemand en weggelaten (geen belangrijk weersverschijnsel, geen gegevens), 4=automatisch en opgenomen (gebruikmakend van code uit visuele waarnemingen), 5,6=automatisch en weggelaten (geen belangrijk weersverschijnsel, geen gegevens), 7=automatisch gebruikmakend van code uit automatische waarnemingen);",
        "M        = Mist 0=niet voorgekomen, 1=wel voorgekomen in het voorgaande uur en/of tijdens de waarneming;",
        "R        = Regen 0=niet voorgekomen, 1=wel voorgekomen in het voorgaande uur en/of tijdens de waarneming;",
        "S        = Sneeuw 0=niet voorgekomen, 1=wel voorgekomen in het voorgaande uur en/of tijdens de waarneming;",
        "O        = Onweer 0=niet voorgekomen, 1=wel voorgekomen in het voorgaande uur en/of tijdens de waarneming;",
        "Y        = IJsvorming 0=niet voorgekomen, 1=wel voorgekomen in het voorgaande uur en/of tijdens de waarneming;",
        "",
        "STN,YYYYMMDD,HH,DD,FH,FF,FX,T,T10N,TD,SQ,Q,DR,RH,P,VV,N,U,WW,IX,M,R,S,O,Y"
    ]
    
    # Write header and data
    with open(file_path, 'w') as f:
        for line in header_lines:
            f.write(line + '\n')
        
        # Write data
        for _, row in sample_knmi_data.iterrows():
            line = f"240,{row['YYYYMMDD']},{row['HH']},{row['DD']},{row['FH']},,,"
            line += f"{row['T']},{row['TD']},{row['TD']},,{row['Q']},{row['DR']},{row['RH']},"
            line += f"{row['P']},{row['VV']},{row['N']},{row['U']},,,,{row['R']},,,\n"
            f.write(line)
    
    return file_path


@pytest.fixture
def sample_epw_template(test_data_dir):
    """Create sample EPW template file."""
    templates_dir = test_data_dir / "data" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    template_path = templates_dir / "template.epw"
    
    # Create minimal EPW template
    epw_header = [
        "LOCATION,Amsterdam,NLD,IWEC Data,062400,52.30,4.77,1.0,0.0",
        "DESIGN CONDITIONS,1,Climate Design Data 2009 ASHRAE Handbook,,Heating,12,-9.8,-7.2,0.4,-7.4,3.2,4.1,Cooling,7,29.1,20.8,30.6,20.3,32.1,19.8,21.4,24.8,22.0,23.6,21.6,22.8,4.6,250,20.8,15.8,23.6,20.3,15.1,22.8,Extremes,10.6,9.2,8.1,24.8,-12.4,34.8,2.3,1.8,-14.8,36.2,-16.8,37.4,-18.6,38.4,-21.1,40.1",
        "TYPICAL/EXTREME PERIODS,6,Summer - Week Nearest Max Temperature For Period,Extreme,7/16,7/22,Summer - Week Nearest Average Temperature For Period,Typical,7/30,8/ 5,Winter - Week Nearest Min Temperature For Period,Extreme,1/14,1/20,Winter - Week Nearest Average Temperature For Period,Typical,1/28,2/ 3,Spring - Week Nearest Average Temperature For Period,Typical,4/22,4/28,Autumn - Week Nearest Average Temperature For Period,Typical,10/21,10/27",
        "GROUND TEMPERATURES,3,.5,,,,-0.28,1.83,5.89,10.78,15.11,17.78,18.33,16.72,13.39,8.89,4.17,1.11,2,,,,1.89,3.17,5.89,9.33,12.89,15.61,16.89,16.39,14.39,11.39,7.89,4.89,4,,,,3.89,4.61,6.11,8.33,10.89,12.89,14.11,14.39,13.61,12.11,9.89,7.61",
        "HOLIDAYS/DAYLIGHT SAVINGS,No,0,0,0",
        "COMMENTS 1,",
        "COMMENTS 2,",
        "DATA PERIODS,1,1,Data,Sunday, 1/ 1,12/31"
    ]
    
    # Create 24 hours of sample EPW data
    epw_data = []
    for hour in range(24):
        # EPW format: Year,Month,Day,Hour,Minute,DataSource,DryBulb,DewPoint,RelHum,AtmPress,ExtHorzRad,ExtDirNormRad,HorzIRRad,GloHorzRad,DirNormRad,DifHorzRad,GloHorzIllum,DirNormIllum,DifHorzIllum,ZenLum,WindDir,WindSpeed,TotalSkyCover,OpaqueSkyCover,Visibility,CeilingHeight,PresWeathObs,PresWeathCodes,PrecipWater,AerosolOptDepth,SnowDepth,DaysSinceLastSnow,Albedo,LiquidPrecipDepth,LiquidPrecipQuantity
        line = f"2023,1,1,{hour+1},0,?9?9?9?9E0?9?9?9?9?9?9?9?9?9?9?9?9?9?9?9*A7*9*9*9?9?9,"
        line += f"5.0,2.0,80,101325,0,0,315,100,0,100,10000,0,1000,6500,180,3.0,10,10,25000,77777,9,999999999,50,999,999,99,999,999,999"
        epw_data.append(line)
    
    # Write EPW file
    with open(template_path, 'w') as f:
        for line in epw_header:
            f.write(line + '\n')
        for line in epw_data:
            f.write(line + '\n')
    
    return template_path


@pytest.fixture
def mock_urls():
    """Mock URLs for testing download functionality."""
    return {
        "240": {
            2023: "//cdn.knmi.nl/knmi/map/page/klimatologie/gegevens/uurgegevens/uurgeg_240_2023-2023.zip"
        },
        "260": {
            2023: "//cdn.knmi.nl/knmi/map/page/klimatologie/gegevens/uurgegevens/uurgeg_260_2023-2023.zip"
        }
    }


@pytest.fixture
def sample_batch_results():
    """Create sample batch processing results."""
    from knmi_epw.batch_processor import BatchResult
    
    results = [
        BatchResult(
            station_id="240",
            year=2023,
            success=True,
            output_path="/test/output/240_2023.epw",
            processing_time=15.5,
            data_records=8760
        ),
        BatchResult(
            station_id="260",
            year=2023,
            success=True,
            output_path="/test/output/260_2023.epw",
            processing_time=12.3,
            data_records=8760
        ),
        BatchResult(
            station_id="280",
            year=2023,
            success=False,
            error_message="Download failed",
            processing_time=2.1,
            data_records=0
        )
    ]
    
    return results


@pytest.fixture
def config_file_yaml(test_data_dir):
    """Create sample YAML configuration file."""
    config_data = {
        'paths': {
            'data_dir': str(test_data_dir / "data"),
            'knmi_dir': str(test_data_dir / "data" / "knmi"),
            'epw_output_dir': str(test_data_dir / "output")
        },
        'processing': {
            'max_workers': 2,
            'cache_enabled': True,
            'chunk_size': 1000
        },
        'urls': {
            'base_url': "https://test.knmi.nl/data"
        }
    }
    
    config_file = test_data_dir / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    return config_file


@pytest.fixture
def config_file_json(test_data_dir):
    """Create sample JSON configuration file."""
    config_data = {
        'paths': {
            'data_dir': str(test_data_dir / "data"),
            'knmi_dir': str(test_data_dir / "data" / "knmi"),
            'epw_output_dir': str(test_data_dir / "output")
        },
        'processing': {
            'max_workers': 4,
            'cache_enabled': False,
            'chunk_size': 5000
        }
    }
    
    config_file = test_data_dir / "test_config.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    return config_file


# Test utilities
def assert_file_exists(file_path):
    """Assert that a file exists."""
    assert Path(file_path).exists(), f"File does not exist: {file_path}"


def assert_directory_exists(dir_path):
    """Assert that a directory exists."""
    assert Path(dir_path).is_dir(), f"Directory does not exist: {dir_path}"


def create_mock_response(status_code=200, content=b"test content"):
    """Create mock HTTP response for testing."""
    class MockResponse:
        def __init__(self, status_code, content):
            self.status_code = status_code
            self.content = content
            self.status = status_code
        
        def read(self):
            return self.content
        
        def decode(self, encoding='utf-8'):
            return self.content.decode(encoding)
    
    return MockResponse(status_code, content)


# Performance testing utilities
@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            return self.elapsed
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow
