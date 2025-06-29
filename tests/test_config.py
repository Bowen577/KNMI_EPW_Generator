"""
Comprehensive tests for configuration module.
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path

from knmi_epw.config import Config, Paths, URLs, Processing, load_config
from knmi_epw.exceptions import ConfigurationError


@pytest.mark.unit
class TestPaths:
    """Test Paths configuration class."""

    def test_default_paths(self):
        """Test default path values."""
        paths = Paths()

        assert paths.data_dir == "data"
        assert paths.knmi_dir == "data/knmi"
        assert paths.knmi_zip_dir == "data/knmi_zip"
        assert paths.epw_output_dir == "output/epw"
        assert "knmi_STN_infor.csv" in paths.station_info_file
        assert "NLD_Amsterdam" in paths.epw_template_file

    def test_custom_paths(self):
        """Test custom path configuration."""
        paths = Paths(
            data_dir="/custom/data",
            knmi_dir="/custom/knmi",
            epw_output_dir="/custom/output"
        )

        assert paths.data_dir == "/custom/data"
        assert paths.knmi_dir == "/custom/knmi"
        assert paths.epw_output_dir == "/custom/output"


@pytest.mark.unit
class TestURLs:
    """Test URLs configuration class."""

    def test_default_urls(self):
        """Test default URL values."""
        urls = URLs()

        assert "knmi.nl" in urls.base_url
        assert "uurgegevens" in urls.base_url
        assert "zip" in urls.link_pattern

    def test_custom_urls(self):
        """Test custom URL configuration."""
        urls = URLs(
            base_url="https://custom.api.com/data",
            link_pattern="<link>(.*\\.zip)</link>"
        )

        assert urls.base_url == "https://custom.api.com/data"
        assert urls.link_pattern == "<link>(.*\\.zip)</link>"


@pytest.mark.unit
class TestProcessing:
    """Test Processing configuration class."""

    def test_default_processing(self):
        """Test default processing values."""
        processing = Processing()

        assert processing.local_time_shift == 1.0
        assert processing.skiprows == 31
        assert processing.epw_skiprows == 8
        assert processing.coerce_year == 2021
        assert processing.max_workers == 4
        assert processing.chunk_size == 10000
        assert processing.cache_enabled is True

    def test_custom_processing(self):
        """Test custom processing configuration."""
        processing = Processing(
            max_workers=8,
            chunk_size=5000,
            cache_enabled=False,
            local_time_shift=2.0
        )

        assert processing.max_workers == 8
        assert processing.chunk_size == 5000
        assert processing.cache_enabled is False
        assert processing.local_time_shift == 2.0


@pytest.mark.unit
class TestConfig:
    """Test main Config class functionality."""

    def test_default_config(self):
        """Test default configuration creation."""
        config = Config()

        assert config.paths is not None
        assert config.urls is not None
        assert config.processing is not None

        # Check default values
        assert config.paths.data_dir == "data"
        assert config.processing.local_time_shift == 1.0
        assert "knmi.nl" in config.urls.base_url

    def test_config_with_custom_components(self):
        """Test configuration with custom components."""
        custom_paths = Paths(data_dir="/custom/data")
        custom_processing = Processing(max_workers=8)

        config = Config(paths=custom_paths, processing=custom_processing)

        assert config.paths.data_dir == "/custom/data"
        assert config.processing.max_workers == 8
        assert config.urls is not None  # Should use default

    def test_config_from_dict(self):
        """Test configuration creation from dictionary."""
        data = {
            'paths': {
                'data_dir': '/custom/data',
                'knmi_dir': '/custom/knmi'
            },
            'processing': {
                'max_workers': 8,
                'local_time_shift': 2.0,
                'cache_enabled': False
            },
            'urls': {
                'base_url': 'https://custom.api.com'
            }
        }

        config = Config.from_dict(data)

        assert config.paths.data_dir == '/custom/data'
        assert config.paths.knmi_dir == '/custom/knmi'
        assert config.processing.max_workers == 8
        assert config.processing.local_time_shift == 2.0
        assert config.processing.cache_enabled is False
        assert config.urls.base_url == 'https://custom.api.com'

    def test_config_from_partial_dict(self):
        """Test configuration from partial dictionary (should use defaults)."""
        data = {
            'processing': {
                'max_workers': 6
            }
        }

        config = Config.from_dict(data)

        # Should use custom value
        assert config.processing.max_workers == 6

        # Should use defaults
        assert config.paths.data_dir == "data"
        assert config.processing.cache_enabled is True
        assert "knmi.nl" in config.urls.base_url

    def test_config_to_dict(self):
        """Test configuration conversion to dictionary."""
        config = Config()
        config.paths.data_dir = '/test/data'
        config.processing.max_workers = 6

        data = config.to_dict()

        assert 'paths' in data
        assert 'urls' in data
        assert 'processing' in data

        assert data['paths']['data_dir'] == '/test/data'
        assert data['processing']['max_workers'] == 6
        assert data['processing']['local_time_shift'] == 1.0

    def test_config_save_load_json(self, config_file_json):
        """Test saving and loading configuration as JSON."""
        # Load from fixture
        config = Config.from_file(str(config_file_json))

        assert config.processing.max_workers == 4
        assert config.processing.cache_enabled is False
        assert config.processing.chunk_size == 5000

    def test_config_save_load_yaml(self, config_file_yaml):
        """Test saving and loading configuration as YAML."""
        # Load from fixture
        config = Config.from_file(str(config_file_yaml))

        assert config.processing.max_workers == 2
        assert config.processing.cache_enabled is True
        assert config.processing.chunk_size == 1000
        assert config.urls.base_url == "https://test.knmi.nl/data"

    def test_config_save_new_file(self, test_data_dir):
        """Test saving configuration to new file."""
        config = Config()
        config.paths.data_dir = '/test/data'
        config.processing.max_workers = 6

        # Test YAML save
        yaml_file = test_data_dir / "new_config.yaml"
        config.save(str(yaml_file))

        assert yaml_file.exists()
        loaded_config = Config.from_file(str(yaml_file))
        assert loaded_config.paths.data_dir == '/test/data'
        assert loaded_config.processing.max_workers == 6

        # Test JSON save
        json_file = test_data_dir / "new_config.json"
        config.save(str(json_file))

        assert json_file.exists()
        loaded_config = Config.from_file(str(json_file))
        assert loaded_config.paths.data_dir == '/test/data'
        assert loaded_config.processing.max_workers == 6

    def test_config_ensure_directories(self, test_data_dir):
        """Test directory creation."""
        config = Config()
        config.paths.data_dir = str(test_data_dir / "new_data")
        config.paths.knmi_dir = str(test_data_dir / "new_data" / "knmi")
        config.paths.epw_output_dir = str(test_data_dir / "new_output")

        # Directories shouldn't exist yet
        assert not Path(config.paths.data_dir).exists()
        assert not Path(config.paths.knmi_dir).exists()
        assert not Path(config.paths.epw_output_dir).exists()

        # Create directories
        config.ensure_directories()

        # Directories should now exist
        assert Path(config.paths.data_dir).exists()
        assert Path(config.paths.knmi_dir).exists()
        assert Path(config.paths.epw_output_dir).exists()

    def test_config_invalid_file_format(self, test_data_dir):
        """Test loading configuration from invalid file format."""
        invalid_file = test_data_dir / "invalid_config.txt"
        with open(invalid_file, 'w') as f:
            f.write("This is not a valid config file")

        with pytest.raises(ValueError, match="Unsupported config file format"):
            Config.from_file(str(invalid_file))

    def test_config_nonexistent_file(self):
        """Test loading configuration from non-existent file."""
        with pytest.raises(FileNotFoundError):
            Config.from_file("/non/existent/file.yaml")

    def test_config_invalid_yaml(self, test_data_dir):
        """Test loading configuration from invalid YAML."""
        invalid_yaml = test_data_dir / "invalid.yaml"
        with open(invalid_yaml, 'w') as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(Exception):  # YAML parsing error
            Config.from_file(str(invalid_yaml))

    def test_config_invalid_json(self, test_data_dir):
        """Test loading configuration from invalid JSON."""
        invalid_json = test_data_dir / "invalid.json"
        with open(invalid_json, 'w') as f:
            f.write('{"invalid": json content}')

        with pytest.raises(Exception):  # JSON parsing error
            Config.from_file(str(invalid_json))


@pytest.mark.unit
class TestConfigUtilities:
    """Test configuration utility functions."""

    def test_load_config_with_file(self, config_file_yaml):
        """Test load_config function with existing file."""
        config = load_config(str(config_file_yaml))

        assert config.processing.max_workers == 2
        assert config.processing.cache_enabled is True

    def test_load_config_with_nonexistent_file(self):
        """Test load_config function with non-existent file."""
        config = load_config('/non/existent/file.yaml')

        # Should return default configuration
        assert config.paths.data_dir == 'data'
        assert config.processing.max_workers == 4

    def test_load_config_with_none(self):
        """Test load_config function with None."""
        config = load_config(None)

        # Should return default configuration
        assert config.paths.data_dir == 'data'
        assert config.processing.max_workers == 4
