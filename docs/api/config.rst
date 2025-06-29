Configuration Module
===================

.. automodule:: knmi_epw.config
   :members:
   :undoc-members:
   :show-inheritance:

Overview
--------

The configuration module provides a flexible and robust system for managing all configuration settings in the KNMI EPW Generator. It supports multiple configuration sources and formats, with automatic validation and environment-specific overrides.

Key Features
------------

* **Multiple Formats**: Support for YAML, JSON, and programmatic configuration
* **Hierarchical Structure**: Organized configuration with logical groupings
* **Validation**: Automatic validation of configuration values
* **Environment Overrides**: Support for environment variable overrides
* **Default Values**: Sensible defaults for all configuration options
* **Type Safety**: Strong typing with dataclasses

Configuration Structure
-----------------------

The configuration is organized into three main sections:

Paths Configuration
~~~~~~~~~~~~~~~~~~~

.. autoclass:: knmi_epw.config.Paths
   :members:
   :undoc-members:

Manages all file and directory paths used by the application:

* ``data_dir``: Base directory for all data files
* ``knmi_dir``: Directory for processed KNMI data files
* ``knmi_zip_dir``: Directory for downloaded ZIP files
* ``epw_output_dir``: Directory for generated EPW files
* ``station_info_file``: Path to station information CSV file
* ``epw_template_file``: Path to EPW template file

URLs Configuration
~~~~~~~~~~~~~~~~~~

.. autoclass:: knmi_epw.config.URLs
   :members:
   :undoc-members:

Manages all external URLs and web service endpoints:

* ``base_url``: Base URL for KNMI data services
* ``link_pattern``: Regular expression pattern for finding download links

Processing Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: knmi_epw.config.Processing
   :members:
   :undoc-members:

Manages all data processing parameters and performance settings:

* ``local_time_shift``: Time zone offset for Netherlands (UTC+1)
* ``skiprows``: Number of header rows to skip in KNMI files
* ``epw_skiprows``: Number of header rows to skip in EPW template files
* ``coerce_year``: Year to use for EPW template data
* ``max_workers``: Maximum number of parallel processing workers
* ``chunk_size``: Size of data chunks for streaming processing
* ``cache_enabled``: Whether to enable intelligent caching

Main Configuration Class
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: knmi_epw.config.Config
   :members:
   :undoc-members:

Usage Examples
--------------

Basic Configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from knmi_epw.config import Config
   
   # Use default configuration
   config = Config()
   
   # Access configuration values
   print(f"Data directory: {config.paths.data_dir}")
   print(f"Max workers: {config.processing.max_workers}")
   print(f"Cache enabled: {config.processing.cache_enabled}")

Loading from File
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Load from YAML file
   config = Config.from_file("config.yaml")
   
   # Load from JSON file
   config = Config.from_file("config.json")

Creating from Dictionary
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   config_data = {
       'paths': {
           'data_dir': '/custom/data',
           'epw_output_dir': '/custom/output'
       },
       'processing': {
           'max_workers': 8,
           'cache_enabled': True
       }
   }
   
   config = Config.from_dict(config_data)

Saving Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Save to YAML file
   config.save("my_config.yaml")
   
   # Save to JSON file
   config.save("my_config.json")

Programmatic Modification
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   config = Config()
   
   # Modify paths
   config.paths.data_dir = "/new/data/directory"
   config.paths.epw_output_dir = "/new/output/directory"
   
   # Modify processing settings
   config.processing.max_workers = 6
   config.processing.cache_enabled = False
   
   # Ensure directories exist
   config.ensure_directories()

Configuration File Examples
---------------------------

YAML Configuration
~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # config.yaml
   paths:
     data_dir: "data"
     knmi_dir: "data/knmi"
     knmi_zip_dir: "data/knmi_zip"
     epw_output_dir: "output/epw"
     station_info_file: "data/stations/knmi_STN_infor.csv"
     epw_template_file: "data/templates/NLD_Amsterdam.062400_IWEC.epw"
   
   urls:
     base_url: "https://www.knmi.nl/nederland-nu/klimatologie/uurgegevens"
     link_pattern: "<a href='(.*zip)'>"
   
   processing:
     local_time_shift: 1.0
     skiprows: 31
     epw_skiprows: 8
     coerce_year: 2021
     max_workers: 4
     chunk_size: 10000
     cache_enabled: true

JSON Configuration
~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "paths": {
       "data_dir": "data",
       "knmi_dir": "data/knmi",
       "knmi_zip_dir": "data/knmi_zip",
       "epw_output_dir": "output/epw",
       "station_info_file": "data/stations/knmi_STN_infor.csv",
       "epw_template_file": "data/templates/NLD_Amsterdam.062400_IWEC.epw"
     },
     "urls": {
       "base_url": "https://www.knmi.nl/nederland-nu/klimatologie/uurgegevens",
       "link_pattern": "<a href='(.*zip)'>"
     },
     "processing": {
       "local_time_shift": 1.0,
       "skiprows": 31,
       "epw_skiprows": 8,
       "coerce_year": 2021,
       "max_workers": 4,
       "chunk_size": 10000,
       "cache_enabled": true
     }
   }

Environment Variables
---------------------

Configuration values can be overridden using environment variables with the prefix ``KNMI_EPW_``:

.. code-block:: bash

   export KNMI_EPW_DATA_DIR="/custom/data"
   export KNMI_EPW_MAX_WORKERS="8"
   export KNMI_EPW_CACHE_ENABLED="false"

Best Practices
--------------

1. **Use Default Configuration**: Start with default configuration and only override what you need
2. **Validate Paths**: Always call ``ensure_directories()`` after configuration changes
3. **Environment-Specific Configs**: Use different configuration files for development, testing, and production
4. **Version Control**: Keep configuration files in version control but exclude sensitive data
5. **Documentation**: Document any custom configuration options for your deployment

Thread Safety
--------------

Configuration objects are thread-safe for reading but should not be modified concurrently. Create configuration objects before starting multi-threaded operations.

Error Handling
--------------

The configuration module provides clear error messages for common issues:

* **File Not Found**: When configuration files don't exist
* **Invalid Format**: When configuration files have syntax errors
* **Missing Required Values**: When required configuration values are missing
* **Invalid Types**: When configuration values have incorrect types

Utility Functions
-----------------

.. autofunction:: knmi_epw.config.get_default_config

.. autofunction:: knmi_epw.config.load_config
