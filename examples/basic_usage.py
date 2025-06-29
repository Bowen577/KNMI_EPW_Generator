#!/usr/bin/env python3
"""
Basic usage example for KNMI EPW Generator.

This example demonstrates how to use the KNMI EPW Generator package
to download weather data and generate EPW files.
"""

import logging
from pathlib import Path

from knmi_epw import Config, StationManager, KNMIDownloader, DataProcessor, EPWGenerator, BatchProcessor


def main():
    """Main example function."""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("KNMI EPW Generator - Basic Usage Example")
    
    # Load configuration
    config = Config()
    
    # Ensure directories exist
    config.ensure_directories()
    
    # Initialize components
    logger.info("Initializing components...")
    station_manager = StationManager(config.paths.station_info_file)
    downloader = KNMIDownloader(config, station_manager)
    processor = DataProcessor(config)
    epw_generator = EPWGenerator(config, processor)
    
    # Example: Generate EPW file for Amsterdam Schiphol (station 240) for 2023
    station_id = "240"
    year = 2023
    
    logger.info(f"Processing station {station_id} for year {year}")
    
    # Get station information
    station = station_manager.get_station(station_id)
    if not station:
        logger.error(f"Station {station_id} not found")
        return
    
    logger.info(f"Station: {station.name} ({station.abbreviation})")
    logger.info(f"Location: {station.latitude:.4f}°N, {station.longitude:.4f}°E")
    
    # Download data
    logger.info("Downloading KNMI data...")
    data_path = downloader.download_station_data(station_id, year)
    
    if not data_path:
        logger.error("Failed to download data")
        return
    
    logger.info(f"Data downloaded to: {data_path}")
    
    # Process data
    logger.info("Processing weather data...")
    knmi_data = processor.read_knmi_data(data_path)
    weather_data = processor.process_weather_data(knmi_data, station, year)
    
    # Validate processed data
    if not processor.validate_processed_data(weather_data):
        logger.warning("Data validation failed")
        return
    
    logger.info(f"Processed {len(weather_data)} weather records")
    
    # Generate EPW file
    logger.info("Generating EPW file...")
    output_dir = Path(config.paths.epw_output_dir) / station.name
    output_file = output_dir / f"NLD_{station.abbreviation}_EPW_YR{year}.epw"
    
    epw_path = epw_generator.generate_epw_file(
        weather_data, station, year, str(output_file)
    )
    
    logger.info(f"EPW file generated: {epw_path}")
    
    # Display summary
    logger.info("\nSummary:")
    logger.info(f"  Station: {station.name} (ID: {station_id})")
    logger.info(f"  Year: {year}")
    logger.info(f"  Data records: {len(weather_data)}")
    logger.info(f"  Output file: {output_file}")
    logger.info(f"  File size: {Path(epw_path).stat().st_size / 1024:.1f} KB")


def batch_example():
    """Example of batch processing multiple stations."""
    logger = logging.getLogger(__name__)

    logger.info("KNMI EPW Generator - Batch Processing Example")

    # Load configuration
    config = Config()
    config.ensure_directories()

    # Initialize batch processor
    batch_processor = BatchProcessor(config)

    # Process multiple stations for 2023
    station_years = [("240", 2023), ("260", 2023), ("280", 2023)]  # Schiphol, De Bilt, Eelde

    logger.info(f"Processing {len(station_years)} stations with batch processor...")

    # Process with performance tracking
    results, stats = batch_processor.process_batch(
        station_years,
        parallel=True,
        use_streaming=True,
        force_download=False
    )

    # Display results
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    logger.info(f"\nBatch Processing Results:")
    logger.info(f"  ✅ Successful: {len(successful)}")
    logger.info(f"  ❌ Failed: {len(failed)}")
    logger.info(f"  ⏱️  Total time: {stats.total_time:.1f}s")
    logger.info(f"  📊 Average time per station: {stats.average_time_per_station:.1f}s")
    logger.info(f"  📈 Total data records: {stats.total_data_records:,}")
    logger.info(f"  🗄️  Cache hits: {stats.cache_hits}, misses: {stats.cache_misses}")

    for result in successful:
        logger.info(f"  ✓ {result.station_id}: {result.data_records:,} records in {result.processing_time:.1f}s")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        batch_example()
    else:
        main()
