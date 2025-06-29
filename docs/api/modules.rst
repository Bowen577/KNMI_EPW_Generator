API Reference
=============

This section provides comprehensive API documentation for all modules in the KNMI EPW Generator package.

Core Modules
------------

.. toctree::
   :maxdepth: 2

   config
   station_manager
   downloader
   processor
   epw_generator
   batch_processor
   utils

Module Overview
---------------

The KNMI EPW Generator is organized into focused modules, each handling specific aspects of the weather data processing pipeline:

Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   knmi_epw.config.Config
   knmi_epw.config.Paths
   knmi_epw.config.URLs
   knmi_epw.config.Processing

Station Management
~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   knmi_epw.station_manager.StationManager
   knmi_epw.station_manager.WeatherStation

Data Download
~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   knmi_epw.downloader.KNMIDownloader
   knmi_epw.downloader.DownloadError

Data Processing
~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   knmi_epw.processor.DataProcessor
   knmi_epw.processor.DataValidationError
   knmi_epw.processor.MemoryMonitor

EPW Generation
~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   knmi_epw.epw_generator.EPWGenerator
   knmi_epw.epw_generator.EPWGenerationError

Batch Processing
~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   knmi_epw.batch_processor.BatchProcessor
   knmi_epw.batch_processor.BatchResult
   knmi_epw.batch_processor.BatchStats

Utilities
~~~~~~~~~

.. autosummary::
   :toctree: generated/

   knmi_epw.utils.IntelligentCache
   knmi_epw.utils.SimpleCache
   knmi_epw.utils.MemoryMonitor

Quick Reference
---------------

Most Common Classes
~~~~~~~~~~~~~~~~~~~

For typical usage, you'll primarily work with these classes:

.. code-block:: python

   from knmi_epw import (
       Config,              # Configuration management
       StationManager,      # Weather station operations
       BatchProcessor,      # High-performance processing
       KNMIDownloader,      # Data downloading
       DataProcessor,       # Data processing
       EPWGenerator         # EPW file generation
   )

High-Level Workflow
~~~~~~~~~~~~~~~~~~~

The typical workflow involves these steps:

1. **Configuration**: Load or create configuration settings
2. **Station Management**: Identify and validate weather stations
3. **Data Download**: Retrieve KNMI weather data files
4. **Data Processing**: Parse and validate weather data
5. **EPW Generation**: Create EnergyPlus weather files

Example:

.. code-block:: python

   # Initialize components
   config = Config()
   batch_processor = BatchProcessor(config)
   
   # Process stations
   station_years = [("240", 2023), ("260", 2023)]
   results, stats = batch_processor.process_batch(station_years)
   
   # Check results
   successful = [r for r in results if r.success]
   print(f"Generated {len(successful)} EPW files")

Performance Features
~~~~~~~~~~~~~~~~~~~~

The package includes several performance optimization features:

* **Parallel Processing**: Multi-threaded downloads and processing
* **Streaming Processing**: Memory-efficient data handling
* **Intelligent Caching**: Automatic caching with TTL management
* **Progress Tracking**: Real-time progress reporting
* **Resource Management**: Automatic memory and CPU optimization

Error Handling
~~~~~~~~~~~~~~

The package provides comprehensive error handling through custom exception classes:

* ``DownloadError``: Issues with data downloading
* ``DataValidationError``: Problems with data quality or format
* ``EPWGenerationError``: Errors during EPW file creation

All exceptions include detailed error messages and context information for debugging.

Thread Safety
~~~~~~~~~~~~~~

The package is designed to be thread-safe for concurrent operations:

* **BatchProcessor**: Safe for parallel station processing
* **IntelligentCache**: Thread-safe caching operations
* **KNMIDownloader**: Concurrent download support
* **DataProcessor**: Safe for parallel data processing

Configuration Options
~~~~~~~~~~~~~~~~~~~~~~

The package supports extensive configuration through:

* **YAML/JSON files**: Structured configuration files
* **Environment variables**: Runtime configuration overrides
* **Programmatic configuration**: Direct API configuration
* **Command-line arguments**: CLI-specific options

For detailed configuration options, see the :doc:`config` module documentation.
