"""
KNMI EPW Generator

A professional-grade tool for converting KNMI weather data to EnergyPlus EPW files.

This package provides functionality to:
- Download weather data from KNMI (Royal Netherlands Meteorological Institute)
- Process and validate the data
- Generate EPW (EnergyPlus Weather) files for building energy simulations

Author: Bowen Tian
Contact: b.tian@tue.nl
License: MIT
"""

__version__ = "2.0.0"
__author__ = "Bowen Tian"
__email__ = "b.tian@tue.nl"
__license__ = "MIT"

from .epw_generator import EPWGenerator
from .downloader import KNMIDownloader
from .processor import DataProcessor
from .station_manager import StationManager
from .config import Config
from .batch_processor import BatchProcessor

__all__ = [
    "EPWGenerator",
    "KNMIDownloader",
    "DataProcessor",
    "StationManager",
    "Config",
    "BatchProcessor",
]
