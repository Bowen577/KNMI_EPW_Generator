"""
Batch processing module for KNMI EPW Generator.

This module provides optimized batch processing capabilities for handling
multiple weather stations efficiently with parallel processing and resource optimization.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Callable, Any
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing as mp
from dataclasses import dataclass
import time
from tqdm import tqdm
import pandas as pd

from .config import Config
from .station_manager import StationManager, WeatherStation
from .downloader import KNMIDownloader
from .processor import DataProcessor
from .epw_generator import EPWGenerator
from .utils import IntelligentCache

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of batch processing operation."""
    station_id: str
    year: int
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    data_records: int = 0


@dataclass
class BatchStats:
    """Statistics for batch processing operation."""
    total_stations: int
    successful: int
    failed: int
    total_time: float
    average_time_per_station: float
    total_data_records: int
    cache_hits: int
    cache_misses: int


class BatchProcessor:
    """
    Optimized batch processor for multiple weather stations.
    
    Provides efficient parallel processing with resource management,
    progress tracking, and intelligent caching.
    """
    
    def __init__(self, config: Config):
        """
        Initialize batch processor.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.station_manager = StationManager(config.paths.station_info_file)
        self.downloader = KNMIDownloader(config, self.station_manager)
        self.processor = DataProcessor(config)
        self.epw_generator = EPWGenerator(config, self.processor)
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Initialize batch cache
        if config.processing.cache_enabled:
            cache_dir = Path(config.paths.data_dir) / "cache" / "batch"
            self.batch_cache = IntelligentCache(cache_dir, max_size_mb=200, default_ttl=24*3600)
        else:
            self.batch_cache = None
    
    def process_single_station(self, station_id: str, year: int, 
                             force_download: bool = False,
                             use_streaming: bool = True) -> BatchResult:
        """
        Process a single weather station.
        
        Args:
            station_id: KNMI station ID
            year: Year to process
            force_download: Force re-download of data
            use_streaming: Use streaming processing for memory efficiency
            
        Returns:
            BatchResult with processing outcome
        """
        start_time = time.time()
        result = BatchResult(station_id=station_id, year=year, success=False)
        
        try:
            # Get station information
            station = self.station_manager.get_station(station_id)
            if not station:
                result.error_message = f"Station {station_id} not found"
                return result
            
            # Check batch cache for complete result
            cache_key = f"batch_result_{station_id}_{year}"
            if self.batch_cache and self.batch_cache.has(cache_key) and not force_download:
                cached_result = self.batch_cache.get(cache_key)
                if cached_result and cached_result.get('success'):
                    logger.debug(f"Using cached result for station {station_id} year {year}")
                    self.cache_hits += 1
                    result.success = True
                    result.output_path = cached_result.get('output_path')
                    result.data_records = cached_result.get('data_records', 0)
                    result.processing_time = time.time() - start_time
                    return result
            
            self.cache_misses += 1
            
            # Download data
            logger.debug(f"Downloading data for station {station_id} year {year}")
            data_path = self.downloader.download_station_data(station_id, year, force_download)
            
            if not data_path:
                result.error_message = f"Failed to download data for station {station_id} year {year}"
                return result
            
            # Process weather data
            logger.debug(f"Processing weather data for station {station_id} year {year}")
            if use_streaming:
                weather_data = self.processor.process_weather_data_streaming(data_path, station, year)
            else:
                knmi_data = self.processor.read_knmi_data(data_path)
                weather_data = self.processor.process_weather_data(knmi_data, station, year)
            
            # Validate processed data
            if not self.processor.validate_processed_data(weather_data):
                result.error_message = f"Data validation failed for station {station_id} year {year}"
                return result
            
            result.data_records = len(weather_data)
            
            # Generate EPW file
            logger.debug(f"Generating EPW file for station {station_id} year {year}")
            station_dir = Path(self.config.paths.epw_output_dir) / station.name
            output_file = station_dir / f"NLD_{station.abbreviation}_EPW_YR{year}.epw"
            
            epw_path = self.epw_generator.generate_epw_file(
                weather_data, station, year, str(output_file)
            )
            
            result.success = True
            result.output_path = epw_path
            result.processing_time = time.time() - start_time
            
            # Cache the successful result
            if self.batch_cache:
                cache_data = {
                    'success': True,
                    'output_path': epw_path,
                    'data_records': result.data_records,
                    'processing_time': result.processing_time
                }
                self.batch_cache.set(cache_key, cache_data)
            
            logger.debug(f"✓ Completed station {station_id} in {result.processing_time:.1f}s")
            return result
            
        except Exception as e:
            result.error_message = str(e)
            result.processing_time = time.time() - start_time
            logger.error(f"✗ Failed to process station {station_id}: {e}")
            return result
    
    def process_multiple_stations_parallel(self, station_years: List[Tuple[str, int]],
                                         max_workers: Optional[int] = None,
                                         force_download: bool = False,
                                         use_streaming: bool = True,
                                         progress_callback: Optional[Callable] = None) -> List[BatchResult]:
        """
        Process multiple stations in parallel using thread pool.
        
        Args:
            station_years: List of (station_id, year) tuples
            max_workers: Maximum number of parallel workers
            force_download: Force re-download of data
            use_streaming: Use streaming processing for memory efficiency
            progress_callback: Optional progress callback function
            
        Returns:
            List of BatchResult objects
        """
        if max_workers is None:
            max_workers = min(self.config.processing.max_workers, len(station_years))
        
        results = []
        completed = 0
        total = len(station_years)
        
        logger.info(f"Processing {total} station-years with {max_workers} workers (parallel)")
        
        with tqdm(total=total, desc="Processing stations", unit="station") as pbar:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_station = {
                    executor.submit(
                        self.process_single_station, 
                        station_id, year, force_download, use_streaming
                    ): (station_id, year)
                    for station_id, year in station_years
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_station):
                    station_id, year = future_to_station[future]
                    try:
                        result = future.result()
                        results.append(result)
                        completed += 1
                        
                        if result.success:
                            pbar.set_postfix_str(f"✓ {station_id} ({result.data_records} records)")
                        else:
                            pbar.set_postfix_str(f"✗ {station_id} - {result.error_message}")
                        
                        pbar.update(1)
                        
                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(completed, total, result)
                            
                    except Exception as e:
                        logger.error(f"Unexpected error processing station {station_id}: {e}")
                        error_result = BatchResult(
                            station_id=station_id, 
                            year=year, 
                            success=False, 
                            error_message=str(e)
                        )
                        results.append(error_result)
                        completed += 1
                        pbar.update(1)
        
        return results
    
    def process_multiple_stations_sequential(self, station_years: List[Tuple[str, int]],
                                           force_download: bool = False,
                                           use_streaming: bool = True,
                                           progress_callback: Optional[Callable] = None) -> List[BatchResult]:
        """
        Process multiple stations sequentially (for debugging or resource constraints).
        
        Args:
            station_years: List of (station_id, year) tuples
            force_download: Force re-download of data
            use_streaming: Use streaming processing for memory efficiency
            progress_callback: Optional progress callback function
            
        Returns:
            List of BatchResult objects
        """
        results = []
        total = len(station_years)
        
        logger.info(f"Processing {total} station-years sequentially")
        
        with tqdm(total=total, desc="Processing stations", unit="station") as pbar:
            for i, (station_id, year) in enumerate(station_years):
                result = self.process_single_station(station_id, year, force_download, use_streaming)
                results.append(result)
                
                if result.success:
                    pbar.set_postfix_str(f"✓ {station_id} ({result.data_records} records)")
                else:
                    pbar.set_postfix_str(f"✗ {station_id} - {result.error_message}")
                
                pbar.update(1)
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i + 1, total, result)
        
        return results
    
    def generate_batch_stats(self, results: List[BatchResult], total_time: float) -> BatchStats:
        """
        Generate statistics from batch processing results.
        
        Args:
            results: List of BatchResult objects
            total_time: Total processing time
            
        Returns:
            BatchStats object
        """
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_records = sum(r.data_records for r in results if r.success)
        avg_time = total_time / len(results) if results else 0
        
        return BatchStats(
            total_stations=len(results),
            successful=successful,
            failed=failed,
            total_time=total_time,
            average_time_per_station=avg_time,
            total_data_records=total_records,
            cache_hits=self.cache_hits,
            cache_misses=self.cache_misses
        )
    
    def process_batch(self, station_years: List[Tuple[str, int]],
                     parallel: bool = True,
                     max_workers: Optional[int] = None,
                     force_download: bool = False,
                     use_streaming: bool = True,
                     progress_callback: Optional[Callable] = None) -> Tuple[List[BatchResult], BatchStats]:
        """
        Process a batch of stations with comprehensive statistics.
        
        Args:
            station_years: List of (station_id, year) tuples
            parallel: Use parallel processing
            max_workers: Maximum number of parallel workers
            force_download: Force re-download of data
            use_streaming: Use streaming processing for memory efficiency
            progress_callback: Optional progress callback function
            
        Returns:
            Tuple of (results, statistics)
        """
        start_time = time.time()
        
        # Reset cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Process stations
        if parallel:
            results = self.process_multiple_stations_parallel(
                station_years, max_workers, force_download, use_streaming, progress_callback
            )
        else:
            results = self.process_multiple_stations_sequential(
                station_years, force_download, use_streaming, progress_callback
            )
        
        total_time = time.time() - start_time
        stats = self.generate_batch_stats(results, total_time)
        
        # Log summary
        logger.info(f"\nBatch processing complete:")
        logger.info(f"  Total stations: {stats.total_stations}")
        logger.info(f"  Successful: {stats.successful}")
        logger.info(f"  Failed: {stats.failed}")
        logger.info(f"  Total time: {stats.total_time:.1f}s")
        logger.info(f"  Average time per station: {stats.average_time_per_station:.1f}s")
        logger.info(f"  Total data records: {stats.total_data_records:,}")
        logger.info(f"  Cache hits: {stats.cache_hits}, misses: {stats.cache_misses}")
        
        return results, stats
