"""
Setup script for KNMI EPW Generator package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read version from package
version = {}
version_path = Path(__file__).parent / "src" / "knmi_epw" / "__init__.py"
with open(version_path) as f:
    exec(f.read(), version)

setup(
    name="knmi-epw-generator",
    version=version["__version__"],
    author=version["__author__"],
    author_email=version["__email__"],
    description="Professional-grade tool for converting KNMI weather data to EnergyPlus EPW files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Bowen577/KNMI_EPW_Generator",
    project_urls={
        "Bug Reports": "https://github.com/Bowen577/KNMI_EPW_Generator/issues",
        "Source": "https://github.com/Bowen577/KNMI_EPW_Generator",
        "Documentation": "https://github.com/Bowen577/KNMI_EPW_Generator/wiki",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "pvlib>=0.9.0",
        "PyYAML>=5.4.0",
        "tqdm>=4.60.0",
        "aiohttp>=3.8.0",
        "aiofiles>=0.8.0",
        "psutil>=5.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
            "sphinx>=4.0",
            "sphinx-rtd-theme>=0.5",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=0.5",
            "myst-parser>=0.15",
        ],
    },
    entry_points={
        "console_scripts": [
            "knmi-epw=knmi_epw.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "knmi_epw": ["data/*.csv", "data/templates/*.epw"],
    },
    zip_safe=False,
    keywords=[
        "weather",
        "meteorology", 
        "energyplus",
        "epw",
        "knmi",
        "building simulation",
        "climate data",
        "netherlands",
    ],
)
