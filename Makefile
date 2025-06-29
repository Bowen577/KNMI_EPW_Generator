# Makefile for KNMI EPW Generator development tasks
# Provides convenient commands for development, testing, and deployment

.PHONY: help install install-dev clean test test-unit test-integration test-performance test-coverage lint format type-check security docs docs-serve build publish pre-commit setup-dev

# Default target
help:
	@echo "KNMI EPW Generator - Development Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup Commands:"
	@echo "  install         Install package in production mode"
	@echo "  install-dev     Install package in development mode with all dependencies"
	@echo "  setup-dev       Complete development environment setup"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint            Run all linting tools (flake8, pylint)"
	@echo "  format          Format code with black and isort"
	@echo "  type-check      Run type checking with mypy"
	@echo "  security        Run security checks with bandit"
	@echo "  pre-commit      Run pre-commit hooks on all files"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test            Run all tests"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-performance Run performance tests only"
	@echo "  test-coverage   Run tests with coverage report"
	@echo ""
	@echo "Documentation Commands:"
	@echo "  docs            Build documentation"
	@echo "  docs-serve      Serve documentation locally"
	@echo ""
	@echo "Build & Release Commands:"
	@echo "  build           Build package for distribution"
	@echo "  publish         Publish package to PyPI"
	@echo "  clean           Clean build artifacts and cache files"
	@echo ""
	@echo "Example Usage:"
	@echo "  make setup-dev  # Set up development environment"
	@echo "  make test       # Run all tests"
	@echo "  make lint       # Check code quality"
	@echo "  make docs       # Build documentation"

# Installation commands
install:
	pip install .

install-dev:
	pip install -e ".[dev,test,docs]"
	pip install pre-commit
	pre-commit install

setup-dev: install-dev
	@echo "Setting up development environment..."
	@echo "Creating necessary directories..."
	mkdir -p data/knmi data/knmi_zip data/stations data/templates output/epw logs
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify installation."

# Code quality commands
lint:
	@echo "Running flake8..."
	flake8 src/ tests/ examples/
	@echo "Running pylint..."
	pylint src/knmi_epw/ --rcfile=.pylintrc || true
	@echo "Running pydocstyle..."
	pydocstyle src/knmi_epw/ --convention=google

format:
	@echo "Formatting code with black..."
	black src/ tests/ examples/
	@echo "Sorting imports with isort..."
	isort src/ tests/ examples/

type-check:
	@echo "Running type checks with mypy..."
	mypy src/knmi_epw/ --config-file=pyproject.toml

security:
	@echo "Running security checks with bandit..."
	bandit -r src/ -f json -o bandit-report.json
	bandit -r src/ -f txt

pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

# Testing commands
test:
	@echo "Running all tests..."
	pytest tests/ -v --tb=short

test-unit:
	@echo "Running unit tests..."
	pytest tests/ -v -m "unit" --tb=short

test-integration:
	@echo "Running integration tests..."
	pytest tests/ -v -m "integration" --tb=short

test-performance:
	@echo "Running performance tests..."
	pytest tests/ -v -m "performance" --tb=short

test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=knmi_epw --cov-report=html --cov-report=term --cov-report=xml
	@echo "Coverage report generated in htmlcov/"

# Documentation commands
docs:
	@echo "Building documentation..."
	cd docs && make html
	@echo "Documentation built in docs/_build/html/"

docs-serve:
	@echo "Serving documentation locally..."
	cd docs/_build/html && python -m http.server 8000

docs-clean:
	@echo "Cleaning documentation build..."
	cd docs && make clean

# Build and release commands
build: clean
	@echo "Building package..."
	python -m build

publish: build
	@echo "Publishing to PyPI..."
	@echo "WARNING: This will publish to PyPI. Make sure you want to do this!"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ]
	python -m twine upload dist/*

publish-test: build
	@echo "Publishing to Test PyPI..."
	python -m twine upload --repository testpypi dist/*

# Cleaning commands
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .tox/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	find . -type f -name ".DS_Store" -delete

# Development utilities
check-deps:
	@echo "Checking for outdated dependencies..."
	pip list --outdated

update-deps:
	@echo "Updating development dependencies..."
	pip install --upgrade pip setuptools wheel
	pip install --upgrade -e ".[dev,test,docs]"

# Performance profiling
profile:
	@echo "Running performance profiling..."
	python -m cProfile -o profile.stats examples/performance_comparison.py
	python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"

# Memory profiling
memory-profile:
	@echo "Running memory profiling..."
	python -m memory_profiler examples/basic_usage.py

# Code complexity analysis
complexity:
	@echo "Analyzing code complexity..."
	radon cc src/knmi_epw/ -a -nc
	radon mi src/knmi_epw/ -nc

# Generate requirements files
requirements:
	@echo "Generating requirements files..."
	pip-compile requirements.in
	pip-compile requirements-dev.in

# Database/cache management
clean-cache:
	@echo "Cleaning cache files..."
	rm -rf data/cache/
	@echo "Cache cleaned."

reset-data:
	@echo "Resetting data directories..."
	rm -rf data/knmi/ data/knmi_zip/ output/
	mkdir -p data/knmi data/knmi_zip output/epw
	@echo "Data directories reset."

# Git hooks and utilities
install-hooks:
	@echo "Installing git hooks..."
	pre-commit install
	pre-commit install --hook-type commit-msg

# Continuous integration simulation
ci: lint type-check security test-coverage
	@echo "All CI checks passed!"

# Release preparation
prepare-release:
	@echo "Preparing release..."
	@echo "1. Running all quality checks..."
	make ci
	@echo "2. Building documentation..."
	make docs
	@echo "3. Building package..."
	make build
	@echo "Release preparation complete!"
	@echo "Review the build artifacts in dist/ before publishing."

# Development server for testing
dev-server:
	@echo "Starting development server for testing..."
	python -m http.server 8080 --directory examples/

# Quick development cycle
dev: format lint test-unit
	@echo "Quick development cycle complete!"

# Full development cycle
full-dev: format lint type-check security test docs
	@echo "Full development cycle complete!"
