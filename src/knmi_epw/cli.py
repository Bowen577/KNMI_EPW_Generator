"""
Command-line interface for KNMI EPW Generator.

This module provides the main CLI entry point and command handling
for the KNMI EPW Generator package.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional
import pandas as pd

from .config import Config, load_config
from .station_manager import StationManager
from .downloader import KNMIDownloader
from .processor import DataProcessor
from .epw_generator import EPWGenerator
from .batch_processor import BatchProcessor, BatchResult
from . import __version__


def setup_logging(level: str = 'INFO'):
    """Setup logging configuration."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='KNMI EPW Generator - Convert KNMI weather data to EPW files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate EPW files for all stations for 2023
  knmi-epw generate --year 2023
  
  # Generate for specific stations
  knmi-epw generate --year 2023 --stations 240,260,280
  
  # List available stations
  knmi-epw stations --list
  
  # Download data only (no EPW generation)
  knmi-epw download --year 2023 --stations 240
        """
    )
    
    parser.add_argument(
        '--version', 
        action='version', 
        version=f'KNMI EPW Generator {__version__}'
    )
    
    parser.add_argument(
        '--config', 
        type=str, 
        help='Path to configuration file (JSON or YAML)'
    )
    
    parser.add_argument(
        '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    generate_parser = subparsers.add_parser(
        'generate', 
        help='Generate EPW files from KNMI data'
    )
    generate_parser.add_argument(
        '--year', 
        type=int, 
        required=True,
        help='Year to generate EPW files for'
    )
    generate_parser.add_argument(
        '--stations', 
        type=str,
        help='Comma-separated list of station IDs (default: all available)'
    )
    generate_parser.add_argument(
        '--output-dir', 
        type=str,
        help='Output directory for EPW files'
    )
    generate_parser.add_argument(
        '--force-download', 
        action='store_true',
        help='Force re-download of data files'
    )
    generate_parser.add_argument(
        '--max-workers',
        type=int,
        help='Maximum number of parallel workers'
    )
    generate_parser.add_argument(
        '--use-streaming',
        action='store_true',
        default=True,
        help='Use streaming processing for memory efficiency (default: True)'
    )
    generate_parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Disable streaming processing'
    )
    generate_parser.add_argument(
        '--sequential',
        action='store_true',
        help='Use sequential processing instead of parallel'
    )
    generate_parser.add_argument(
        '--disable-cache',
        action='store_true',
        help='Disable caching system'
    )
    generate_parser.add_argument(
        '--show-stats',
        action='store_true',
        help='Show detailed performance statistics'
    )
    
    # Download command
    download_parser = subparsers.add_parser(
        'download', 
        help='Download KNMI data files'
    )
    download_parser.add_argument(
        '--year', 
        type=int, 
        required=True,
        help='Year to download data for'
    )
    download_parser.add_argument(
        '--stations', 
        type=str,
        help='Comma-separated list of station IDs (default: all available)'
    )
    download_parser.add_argument(
        '--force', 
        action='store_true',
        help='Force re-download even if files exist'
    )
    
    # Stations command
    stations_parser = subparsers.add_parser(
        'stations', 
        help='Manage weather stations'
    )
    stations_parser.add_argument(
        '--list', 
        action='store_true',
        help='List all available stations'
    )
    stations_parser.add_argument(
        '--info', 
        type=str,
        help='Show detailed information for specific station ID'
    )
    stations_parser.add_argument(
        '--search', 
        type=str,
        help='Search stations by name'
    )
    stations_parser.add_argument(
        '--nearest', 
        nargs=2, 
        type=float, 
        metavar=('LAT', 'LON'),
        help='Find nearest stations to given coordinates'
    )
    stations_parser.add_argument(
        '--export', 
        type=str,
        help='Export station list to file (CSV, JSON, or YAML)'
    )
    
    return parser


def parse_station_list(stations_str: str) -> List[str]:
    """Parse comma-separated station list."""
    if not stations_str:
        return []
    return [s.strip() for s in stations_str.split(',') if s.strip()]


def command_generate(args, config: Config) -> int:
    """Handle generate command."""
    logger = logging.getLogger(__name__)

    try:
        # Override config with command line arguments
        if args.output_dir:
            config.paths.epw_output_dir = args.output_dir
        if args.max_workers:
            config.processing.max_workers = args.max_workers
        if args.disable_cache:
            config.processing.cache_enabled = False

        # Determine processing options
        use_streaming = args.use_streaming and not args.no_streaming
        use_parallel = not args.sequential

        # Ensure directories exist
        config.ensure_directories()

        # Initialize batch processor
        batch_processor = BatchProcessor(config)
        
        # Determine stations to process
        if args.stations:
            station_ids = parse_station_list(args.stations)
            # Validate station IDs
            invalid_stations = [sid for sid in station_ids
                              if not batch_processor.station_manager.validate_station_id(sid)]
            if invalid_stations:
                logger.error(f"Invalid station IDs: {invalid_stations}")
                return 1
        else:
            station_ids = batch_processor.station_manager.get_station_ids()

        logger.info(f"Processing {len(station_ids)} stations for year {args.year}")

        # Prepare station-year pairs
        station_years = [(sid, args.year) for sid in station_ids]

        # Define progress callback for detailed reporting
        def progress_callback(completed: int, total: int, result: BatchResult):
            if args.show_stats and result.success:
                logger.info(f"Station {result.station_id}: {result.data_records:,} records, "
                          f"{result.processing_time:.1f}s")

        # Process batch
        logger.info(f"Starting batch processing (parallel={use_parallel}, streaming={use_streaming})")
        results, stats = batch_processor.process_batch(
            station_years,
            parallel=use_parallel,
            max_workers=args.max_workers,
            force_download=args.force_download,
            use_streaming=use_streaming,
            progress_callback=progress_callback if args.show_stats else None
        )

        # Display results
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        logger.info(f"\n🎉 Batch processing complete!")
        logger.info(f"  ✅ Successful: {len(successful_results)}/{len(results)} stations")
        logger.info(f"  ❌ Failed: {len(failed_results)} stations")
        logger.info(f"  ⏱️  Total time: {stats.total_time:.1f}s")
        logger.info(f"  📊 Average time per station: {stats.average_time_per_station:.1f}s")
        logger.info(f"  📈 Total data records: {stats.total_data_records:,}")

        if config.processing.cache_enabled:
            logger.info(f"  🗄️  Cache hits: {stats.cache_hits}, misses: {stats.cache_misses}")
            cache_hit_rate = (stats.cache_hits / (stats.cache_hits + stats.cache_misses)) * 100 if (stats.cache_hits + stats.cache_misses) > 0 else 0
            logger.info(f"  📋 Cache hit rate: {cache_hit_rate:.1f}%")

        # Show failed stations if any
        if failed_results:
            logger.warning(f"\n❌ Failed stations:")
            for result in failed_results:
                logger.warning(f"  {result.station_id}: {result.error_message}")

        # Show performance comparison if requested
        if args.show_stats:
            logger.info(f"\n📊 Performance Statistics:")
            logger.info(f"  Processing mode: {'Parallel' if use_parallel else 'Sequential'}")
            logger.info(f"  Memory mode: {'Streaming' if use_streaming else 'Standard'}")
            logger.info(f"  Workers: {config.processing.max_workers}")
            logger.info(f"  Caching: {'Enabled' if config.processing.cache_enabled else 'Disabled'}")

            if successful_results:
                processing_times = [r.processing_time for r in successful_results]
                logger.info(f"  Min processing time: {min(processing_times):.1f}s")
                logger.info(f"  Max processing time: {max(processing_times):.1f}s")
                logger.info(f"  Median processing time: {sorted(processing_times)[len(processing_times)//2]:.1f}s")

        return 0 if successful_results else 1
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return 1


def command_download(args, config: Config) -> int:
    """Handle download command."""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        station_manager = StationManager(config.paths.station_info_file)
        downloader = KNMIDownloader(config, station_manager)
        
        # Determine stations to download
        if args.stations:
            station_ids = parse_station_list(args.stations)
        else:
            station_ids = station_manager.get_station_ids()
        
        logger.info(f"Downloading data for {len(station_ids)} stations for year {args.year}")
        
        # Download data
        station_years = [(sid, args.year) for sid in station_ids]
        results = downloader.download_multiple_stations(
            station_years, 
            force_download=args.force
        )
        
        # Summary
        successful = sum(1 for path in results.values() if path is not None)
        logger.info(f"Download complete: {successful}/{len(results)} files downloaded successfully")
        
        return 0 if successful > 0 else 1
        
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return 1


def command_stations(args, config: Config) -> int:
    """Handle stations command."""
    logger = logging.getLogger(__name__)
    
    try:
        station_manager = StationManager(config.paths.station_info_file)
        
        if args.list:
            # List all stations
            stations = station_manager.get_all_stations()
            print(f"\nAvailable weather stations ({len(stations)}):")
            print("-" * 80)
            for station in stations.values():
                print(f"{station.station_id:>3} | {station.name:<20} | {station.abbreviation:<4} | "
                      f"{station.latitude:>7.4f} | {station.longitude:>8.4f}")
            
        elif args.info:
            # Show station info
            station = station_manager.get_station(args.info)
            if station:
                print(f"\nStation Information:")
                print(f"  ID: {station.station_id}")
                print(f"  Name: {station.name}")
                print(f"  Abbreviation: {station.abbreviation}")
                print(f"  Latitude: {station.latitude}")
                print(f"  Longitude: {station.longitude}")
            else:
                print(f"Station {args.info} not found")
                return 1
        
        elif args.search:
            # Search stations by name
            stations = station_manager.get_stations_by_name(args.search)
            if stations:
                print(f"\nStations matching '{args.search}':")
                for station in stations:
                    print(f"  {station.station_id}: {station.name} ({station.abbreviation})")
            else:
                print(f"No stations found matching '{args.search}'")
        
        elif args.nearest:
            # Find nearest stations
            lat, lon = args.nearest
            nearest = station_manager.get_nearest_stations(lat, lon, count=5)
            print(f"\nNearest stations to ({lat}, {lon}):")
            for station, distance in nearest:
                print(f"  {station.station_id}: {station.name} (distance: {distance:.4f})")
        
        elif args.export:
            # Export station list
            output_path = Path(args.export)
            format_type = output_path.suffix[1:].lower()  # Remove the dot
            station_manager.export_stations(args.export, format_type)
            print(f"Station list exported to {args.export}")
        
        else:
            print("Please specify an action for stations command. Use --help for options.")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Stations command failed: {e}")
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1
    
    # Handle commands
    if args.command == 'generate':
        return command_generate(args, config)
    elif args.command == 'download':
        return command_download(args, config)
    elif args.command == 'stations':
        return command_stations(args, config)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
