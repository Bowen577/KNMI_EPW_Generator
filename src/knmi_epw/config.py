"""
Configuration management for KNMI EPW Generator.

This module handles all configuration settings including paths, URLs,
processing parameters, and default values.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class Paths:
    """Configuration for file and directory paths."""
    data_dir: str = "data"
    knmi_dir: str = "data/knmi"
    knmi_zip_dir: str = "data/knmi_zip"
    epw_output_dir: str = "output/epw"
    station_info_file: str = "data/stations/knmi_STN_infor.csv"
    epw_template_file: str = "data/templates/NLD_Amsterdam.062400_IWEC.epw"


@dataclass
class URLs:
    """Configuration for KNMI data URLs."""
    base_url: str = "https://www.knmi.nl/nederland-nu/klimatologie/uurgegevens"
    link_pattern: str = "<a href='(.*zip)'>"


@dataclass
class Processing:
    """Configuration for data processing parameters."""
    local_time_shift: float = 1.0
    skiprows: int = 31
    epw_skiprows: int = 8
    coerce_year: int = 2021
    max_workers: int = 4
    chunk_size: int = 10000
    cache_enabled: bool = True


@dataclass
class Config:
    """Main configuration class for KNMI EPW Generator."""
    paths: Paths = None
    urls: URLs = None
    processing: Processing = None
    
    def __post_init__(self):
        if self.paths is None:
            self.paths = Paths()
        if self.urls is None:
            self.urls = URLs()
        if self.processing is None:
            self.processing = Processing()
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """Load configuration from a file (JSON or YAML)."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() in ['.yml', '.yaml']:
                data = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {config_path.suffix}")
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create configuration from dictionary."""
        paths = Paths(**data.get('paths', {}))
        urls = URLs(**data.get('urls', {}))
        processing = Processing(**data.get('processing', {}))
        
        return cls(paths=paths, urls=urls, processing=processing)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'paths': asdict(self.paths),
            'urls': asdict(self.urls),
            'processing': asdict(self.processing)
        }
    
    def save(self, config_path: str):
        """Save configuration to file."""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            if config_path.suffix.lower() in ['.yml', '.yaml']:
                yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
            elif config_path.suffix.lower() == '.json':
                json.dump(self.to_dict(), f, indent=2)
            else:
                raise ValueError(f"Unsupported config file format: {config_path.suffix}")
    
    def ensure_directories(self):
        """Create all necessary directories."""
        directories = [
            self.paths.data_dir,
            self.paths.knmi_dir,
            self.paths.knmi_zip_dir,
            self.paths.epw_output_dir,
            os.path.dirname(self.paths.station_info_file),
            os.path.dirname(self.paths.epw_template_file),
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


def get_default_config() -> Config:
    """Get default configuration."""
    return Config()


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or return default."""
    if config_path and os.path.exists(config_path):
        return Config.from_file(config_path)
    return get_default_config()
