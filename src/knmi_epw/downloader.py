"""
KNMI data downloader module.

This module handles downloading weather data from KNMI's online database,
including URL discovery, file downloading, and extraction.
"""

import os
import re
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import time
import asyncio
import aiohttp
import aiofiles
from tqdm import tqdm

from .config import Config
from .station_manager import StationManager
from .utils import retry_on_exception, IntelligentCache

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Exception raised when download fails."""
    pass


class KNMIDownloader:
    """Downloads KNMI weather data files."""
    
    def __init__(self, config: Config, station_manager: StationManager):
        """
        Initialize KNMI downloader.

        Args:
            config: Configuration object
            station_manager: Station manager instance
        """
        self.config = config
        self.station_manager = station_manager
        self.available_urls: Dict[str, Dict[int, str]] = {}

        # Initialize intelligent cache if enabled
        if config.processing.cache_enabled:
            cache_dir = Path(config.paths.data_dir) / "cache"
            self.cache = IntelligentCache(cache_dir, max_size_mb=500, default_ttl=7*24*3600)  # 7 days TTL
        else:
            self.cache = None
        
    def discover_available_data(self) -> Dict[str, Dict[int, str]]:
        """
        Discover available data URLs from KNMI website.

        Returns:
            Dictionary mapping station_id -> {year: url}
        """
        # Check cache first
        cache_key = f"knmi_urls_{self.config.urls.base_url}"
        if self.cache and self.cache.has(cache_key):
            logger.info("Loading available KNMI data URLs from cache...")
            cached_urls = self.cache.get(cache_key)
            if cached_urls:
                self.available_urls = cached_urls
                logger.info(f"Loaded data for {len(cached_urls)} stations from cache")
                return cached_urls

        logger.info("Discovering available KNMI data URLs...")

        try:
            req = urllib.request.Request(self.config.urls.base_url)
            html = urllib.request.urlopen(req)
            doc = html.read().decode('utf8')
            
            # Find all ZIP file URLs
            url_list = list(set(re.findall(self.config.urls.link_pattern, doc)))
            
            # Clean up URL list
            cleaned_urls = []
            for url_element in url_list:
                if isinstance(url_element, str):
                    if '.zip' in url_element:
                        cleaned_urls.append(url_element)
                else:
                    # Handle tuple case
                    for url in url_element:
                        if '.zip' in url:
                            cleaned_urls.append(url)
            
            # Parse URLs to extract station and year information
            station_urls = {}
            for url in cleaned_urls:
                file_name = url.split('/')[-1].lower()
                if file_name.startswith('uurgeg') and not file_name.endswith('-.zip'):
                    try:
                        station_id = file_name[7:10]
                        year_str = file_name[11:20]
                        start_year, end_year = year_str.split('-')
                        
                        if station_id not in station_urls:
                            station_urls[station_id] = {}
                        
                        # Map each year in the range to this URL
                        for year in range(int(start_year), int(end_year) + 1):
                            station_urls[station_id][year] = url
                            
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse URL {url}: {e}")
                        continue
            
            self.available_urls = station_urls

            # Cache the discovered URLs
            if self.cache:
                self.cache.set(cache_key, station_urls, ttl=24*3600)  # Cache for 24 hours
                logger.debug("Cached discovered URLs")

            logger.info(f"Discovered data for {len(station_urls)} stations")
            return station_urls
            
        except Exception as e:
            logger.error(f"Failed to discover KNMI data URLs: {e}")
            raise DownloadError(f"URL discovery failed: {e}")
    
    def download_station_data(self, station_id: str, year: int, 
                            force_download: bool = False) -> Optional[str]:
        """
        Download data for a specific station and year.
        
        Args:
            station_id: KNMI station ID
            year: Year to download
            force_download: Force re-download even if file exists
            
        Returns:
            Path to downloaded and extracted file, or None if failed
        """
        if not self.available_urls:
            self.discover_available_data()
        
        if station_id not in self.available_urls:
            logger.warning(f"No data available for station {station_id}")
            return None
        
        if year not in self.available_urls[station_id]:
            logger.warning(f"No data available for station {station_id} year {year}")
            return None
        
        url = self.available_urls[station_id][year]
        return self._download_and_extract(url, station_id, year, force_download)
    
    def _download_and_extract(self, url: str, station_id: str, year: int,
                            force_download: bool = False) -> Optional[str]:
        """Download and extract a single file."""
        try:
            # Prepare file paths
            filename = url.split('/')[-1].lower()
            zip_path = Path(self.config.paths.knmi_zip_dir) / filename
            extracted_path = Path(self.config.paths.knmi_dir) / f"{filename[:-4]}.txt"
            
            # Create directories if they don't exist
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            extracted_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists and is valid
            if not force_download and extracted_path.exists():
                if self._validate_file(extracted_path):
                    logger.debug(f"File already exists: {extracted_path}")
                    return str(extracted_path)
                else:
                    logger.warning(f"Existing file is invalid, re-downloading: {extracted_path}")
            
            # Download file with progress tracking
            logger.info(f"Downloading {filename} for station {station_id} year {year}")
            
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    sys.stdout.write(f'\r>> Downloading {filename} {percent}%')
                    sys.stdout.flush()
            
            full_url = 'https:' + url if url.startswith('//') else url
            urllib.request.urlretrieve(full_url, zip_path, progress_hook)
            print()  # New line after progress
            
            # Extract file
            logger.info(f"Extracting {filename}")
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                zip_file.extractall(self.config.paths.knmi_dir)
            
            # Validate extracted file
            if self._validate_file(extracted_path):
                logger.info(f"Successfully downloaded and extracted: {extracted_path}")
                return str(extracted_path)
            else:
                logger.error(f"Downloaded file is invalid: {extracted_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None
    
    def _validate_file(self, file_path: Path) -> bool:
        """Validate that a downloaded file is complete and valid."""
        try:
            if not file_path.exists():
                return False
            
            # Check file size (should be > 1KB for valid KNMI data)
            if file_path.stat().st_size < 1024:
                return False
            
            # Check file header
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                if not first_line.startswith('BRON: KONINKLIJK NEDERLANDS METEOROLOGISCH INSTITUUT'):
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"File validation failed for {file_path}: {e}")
            return False
    
    def download_multiple_stations(self, station_years: List[Tuple[str, int]],
                                 max_workers: int = None,
                                 force_download: bool = False,
                                 progress_callback: Optional[Callable] = None) -> Dict[Tuple[str, int], Optional[str]]:
        """
        Download data for multiple stations in parallel.

        Args:
            station_years: List of (station_id, year) tuples
            max_workers: Maximum number of concurrent downloads
            force_download: Force re-download even if files exist
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary mapping (station_id, year) -> file_path or None
        """
        if max_workers is None:
            max_workers = min(self.config.processing.max_workers, len(station_years))

        results = {}
        completed = 0
        total = len(station_years)

        # Use tqdm for progress tracking
        with tqdm(total=total, desc="Downloading stations", unit="station") as pbar:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all download tasks
                future_to_station = {
                    executor.submit(self.download_station_data, station_id, year, force_download):
                    (station_id, year)
                    for station_id, year in station_years
                }

                # Collect results as they complete
                for future in as_completed(future_to_station):
                    station_id, year = future_to_station[future]
                    try:
                        result = future.result()
                        results[(station_id, year)] = result
                        completed += 1

                        if result:
                            pbar.set_postfix_str(f"✓ Station {station_id}")
                            logger.debug(f"✓ Downloaded station {station_id} year {year}")
                        else:
                            pbar.set_postfix_str(f"✗ Station {station_id}")
                            logger.warning(f"✗ Failed to download station {station_id} year {year}")

                        pbar.update(1)

                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(completed, total, f"Downloaded {completed}/{total}")

                    except Exception as e:
                        logger.error(f"✗ Error downloading station {station_id} year {year}: {e}")
                        results[(station_id, year)] = None
                        completed += 1
                        pbar.update(1)

        return results

    async def download_multiple_stations_async(self, station_years: List[Tuple[str, int]],
                                             max_concurrent: int = None,
                                             force_download: bool = False,
                                             progress_callback: Optional[Callable] = None) -> Dict[Tuple[str, int], Optional[str]]:
        """
        Download data for multiple stations asynchronously.

        Args:
            station_years: List of (station_id, year) tuples
            max_concurrent: Maximum number of concurrent downloads
            force_download: Force re-download even if files exist
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary mapping (station_id, year) -> file_path or None
        """
        if max_concurrent is None:
            max_concurrent = min(self.config.processing.max_workers, len(station_years))

        # Discover URLs if not already done
        if not self.available_urls:
            await self.discover_available_data_async()

        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_single(station_id: str, year: int) -> Tuple[Tuple[str, int], Optional[str]]:
            async with semaphore:
                try:
                    result = await self._download_station_data_async(station_id, year, force_download)
                    return (station_id, year), result
                except Exception as e:
                    logger.error(f"Async download failed for station {station_id} year {year}: {e}")
                    return (station_id, year), None

        # Create tasks for all downloads
        tasks = [download_single(station_id, year) for station_id, year in station_years]

        # Execute with progress tracking
        completed = 0
        total = len(tasks)

        with tqdm(total=total, desc="Downloading stations (async)", unit="station") as pbar:
            for coro in asyncio.as_completed(tasks):
                (station_id, year), result = await coro
                results[(station_id, year)] = result
                completed += 1

                if result:
                    pbar.set_postfix_str(f"✓ Station {station_id}")
                    logger.debug(f"✓ Downloaded station {station_id} year {year}")
                else:
                    pbar.set_postfix_str(f"✗ Station {station_id}")
                    logger.warning(f"✗ Failed to download station {station_id} year {year}")

                pbar.update(1)

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(completed, total, f"Downloaded {completed}/{total}")

        return results

    async def discover_available_data_async(self) -> Dict[str, Dict[int, str]]:
        """
        Asynchronously discover available data URLs from KNMI website.

        Returns:
            Dictionary mapping station_id -> {year: url}
        """
        logger.info("Discovering available KNMI data URLs (async)...")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.config.urls.base_url) as response:
                    doc = await response.text()

            # Find all ZIP file URLs (same logic as sync version)
            url_list = list(set(re.findall(self.config.urls.link_pattern, doc)))

            # Clean up URL list
            cleaned_urls = []
            for url_element in url_list:
                if isinstance(url_element, str):
                    if '.zip' in url_element:
                        cleaned_urls.append(url_element)
                else:
                    for url in url_element:
                        if '.zip' in url:
                            cleaned_urls.append(url)

            # Parse URLs to extract station and year information
            station_urls = {}
            for url in cleaned_urls:
                file_name = url.split('/')[-1].lower()
                if file_name.startswith('uurgeg') and not file_name.endswith('-.zip'):
                    try:
                        station_id = file_name[7:10]
                        year_str = file_name[11:20]
                        start_year, end_year = year_str.split('-')

                        if station_id not in station_urls:
                            station_urls[station_id] = {}

                        # Map each year in the range to this URL
                        for year in range(int(start_year), int(end_year) + 1):
                            station_urls[station_id][year] = url

                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse URL {url}: {e}")
                        continue

            self.available_urls = station_urls
            logger.info(f"Discovered data for {len(station_urls)} stations (async)")
            return station_urls

        except Exception as e:
            logger.error(f"Failed to discover KNMI data URLs (async): {e}")
            raise DownloadError(f"Async URL discovery failed: {e}")

    async def _download_station_data_async(self, station_id: str, year: int,
                                         force_download: bool = False) -> Optional[str]:
        """
        Asynchronously download data for a specific station and year.

        Args:
            station_id: KNMI station ID
            year: Year to download
            force_download: Force re-download even if file exists

        Returns:
            Path to downloaded and extracted file, or None if failed
        """
        if not self.available_urls:
            await self.discover_available_data_async()

        if station_id not in self.available_urls:
            logger.warning(f"No data available for station {station_id}")
            return None

        if year not in self.available_urls[station_id]:
            logger.warning(f"No data available for station {station_id} year {year}")
            return None

        url = self.available_urls[station_id][year]
        return await self._download_and_extract_async(url, station_id, year, force_download)

    async def _download_and_extract_async(self, url: str, station_id: str, year: int,
                                        force_download: bool = False) -> Optional[str]:
        """Asynchronously download and extract a single file."""
        try:
            # Prepare file paths
            filename = url.split('/')[-1].lower()
            zip_path = Path(self.config.paths.knmi_zip_dir) / filename
            extracted_path = Path(self.config.paths.knmi_dir) / f"{filename[:-4]}.txt"

            # Create directories if they don't exist
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            extracted_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file already exists and is valid
            if not force_download and extracted_path.exists():
                if self._validate_file(extracted_path):
                    logger.debug(f"File already exists: {extracted_path}")
                    return str(extracted_path)
                else:
                    logger.warning(f"Existing file is invalid, re-downloading: {extracted_path}")

            # Download file asynchronously
            logger.debug(f"Downloading {filename} for station {station_id} year {year} (async)")

            full_url = 'https:' + url if url.startswith('//') else url

            async with aiohttp.ClientSession() as session:
                async with session.get(full_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(zip_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                    else:
                        logger.error(f"HTTP {response.status} for {full_url}")
                        return None

            # Extract file (synchronous operation)
            logger.debug(f"Extracting {filename}")
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                zip_file.extractall(self.config.paths.knmi_dir)

            # Validate extracted file
            if self._validate_file(extracted_path):
                logger.debug(f"Successfully downloaded and extracted: {extracted_path}")
                return str(extracted_path)
            else:
                logger.error(f"Downloaded file is invalid: {extracted_path}")
                return None

        except Exception as e:
            logger.error(f"Failed to download {url} (async): {e}")
            return None

    def get_available_years(self, station_id: str) -> List[int]:
        """Get list of available years for a station."""
        if not self.available_urls:
            self.discover_available_data()
        
        return list(self.available_urls.get(station_id, {}).keys())
    
    def cleanup_old_files(self, keep_days: int = 30):
        """Remove old downloaded files to save disk space."""
        cutoff_time = time.time() - (keep_days * 24 * 3600)
        
        for directory in [self.config.paths.knmi_zip_dir, self.config.paths.knmi_dir]:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
                
            for file_path in dir_path.glob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        logger.debug(f"Removed old file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove old file {file_path}: {e}")
