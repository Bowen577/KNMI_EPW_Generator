# Legacy Files

This directory contains the original files from the KNMI EPW Generator project before the modernization and restructuring.

## Contents

- `gen_epw.py` - Original monolithic script for EPW generation
- `prepare_data/` - Original data files and templates
- `suneye/` - Original suneye module for shading calculations
- `test/` - Original test files and examples

## Migration Notes

The original functionality has been completely refactored and modernized in the new package structure:

### Original → New Mapping

| Original File | New Location | Notes |
|---------------|--------------|-------|
| `gen_epw.py` | `src/knmi_epw/` (multiple modules) | Split into modular components |
| `prepare_data/knmi_STN_infor.csv` | `data/stations/knmi_STN_infor.csv` | Moved to new data structure |
| `prepare_data/NLD_Amsterdam.062400_IWEC.epw` | `data/templates/NLD_Amsterdam.062400_IWEC.epw` | Moved to templates directory |
| `suneye/suneye.py` | Not migrated | Specialized functionality, kept for reference |

### Key Improvements in New Version

1. **Modular Architecture**: Single script split into focused modules
2. **Error Handling**: Comprehensive error handling and validation
3. **Performance**: Parallel processing and memory optimization
4. **CLI Interface**: Professional command-line interface
5. **Configuration**: Flexible YAML/JSON configuration system
6. **Testing**: Comprehensive test suite
7. **Documentation**: Professional documentation and examples

## Using Legacy Code

If you need to reference the original implementation:

1. The original `gen_epw.py` script is preserved as-is
2. All original data files are maintained
3. The original functionality is fully replicated in the new package

## Migration Guide

To migrate from the legacy script to the new package:

### Old Usage
```bash
python gen_epw.py --download_year=2023
```

### New Usage
```bash
knmi-epw generate --year 2023
```

### Python API Migration

#### Old Approach
```python
# Direct function calls from gen_epw.py
knmi_data = read_knmi_data(file_path)
epw_data = read_epw_data(template_path)
# ... manual processing ...
```

#### New Approach
```python
from knmi_epw import Config, StationManager, KNMIDownloader, DataProcessor, EPWGenerator

config = Config()
station_manager = StationManager(config.paths.station_info_file)
downloader = KNMIDownloader(config, station_manager)
processor = DataProcessor(config)
epw_generator = EPWGenerator(config, processor)

# Clean, modular API
station = station_manager.get_station("240")
data_path = downloader.download_station_data("240", 2023)
weather_data = processor.process_weather_data(knmi_data, station, 2023)
epw_path = epw_generator.generate_epw_file(weather_data, station, 2023, "output.epw")
```

## Preservation Notice

These files are preserved for:
- Historical reference
- Debugging and comparison
- Understanding the evolution of the codebase
- Academic and research purposes

The new package provides all the functionality of the original script with significant improvements in reliability, performance, and usability.
