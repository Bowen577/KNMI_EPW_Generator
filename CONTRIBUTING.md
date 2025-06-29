# Contributing to KNMI EPW Generator

Thank you for your interest in contributing to the KNMI EPW Generator! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/KNMI_EPW_Generator.git
   cd KNMI_EPW_Generator
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Development Dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify Installation**
   ```bash
   pytest
   knmi-epw --help
   ```

## 🛠️ Development Workflow

### Code Style and Quality

We use several tools to maintain code quality:

- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking
- **Pytest**: Testing

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Run tests
pytest
```

### Pre-commit Hooks (Recommended)

Install pre-commit hooks to automatically check code quality:

```bash
pip install pre-commit
pre-commit install
```

### Testing

#### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=knmi_epw --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests

# Run specific test file
pytest tests/test_config.py
```

#### Writing Tests
- Write tests for all new functionality
- Aim for >90% test coverage
- Use descriptive test names
- Include both positive and negative test cases
- Use pytest fixtures for common setup

Example test structure:
```python
def test_function_name_should_do_something():
    """Test that function does something specific."""
    # Arrange
    input_data = create_test_data()
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_result
```

## 📝 Contribution Types

### Bug Reports

When reporting bugs, please include:

1. **Environment Information**
   - Python version
   - Package version
   - Operating system

2. **Steps to Reproduce**
   - Minimal code example
   - Command line arguments used
   - Expected vs actual behavior

3. **Error Messages**
   - Full error traceback
   - Log output (use `--log-level DEBUG`)

### Feature Requests

For new features, please:

1. **Check Existing Issues** - Avoid duplicates
2. **Describe the Use Case** - Why is this needed?
3. **Propose Implementation** - How should it work?
4. **Consider Alternatives** - Are there other solutions?

### Code Contributions

#### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow coding standards
   - Add tests for new functionality
   - Update documentation if needed

3. **Test Your Changes**
   ```bash
   pytest
   black src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "Add feature: your feature description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

#### Commit Message Guidelines

Use clear, descriptive commit messages:

```
Add feature: brief description

Longer description if needed explaining:
- What was changed
- Why it was changed
- Any breaking changes

Fixes #123
```

Types of commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

## 📚 Documentation

### Code Documentation

- Use clear, descriptive docstrings for all public functions and classes
- Follow Google-style docstrings
- Include type hints for all function parameters and return values

Example:
```python
def process_weather_data(data: pd.DataFrame, station: WeatherStation, 
                        year: int) -> pd.DataFrame:
    """
    Process KNMI weather data for EPW generation.
    
    Args:
        data: Raw KNMI weather data
        station: Weather station information
        year: Year being processed
        
    Returns:
        Processed weather data ready for EPW generation
        
    Raises:
        DataValidationError: If data validation fails
    """
```

### User Documentation

- Update README.md for user-facing changes
- Add examples for new features
- Update CLI help text
- Consider adding Jupyter notebook examples

## 🏗️ Architecture Guidelines

### Code Organization

- Keep modules focused and cohesive
- Use dependency injection for better testability
- Separate concerns (data access, business logic, presentation)
- Follow SOLID principles

### Error Handling

- Use specific exception types
- Provide helpful error messages
- Log errors appropriately
- Fail fast when possible

### Performance Considerations

- Use generators for large datasets
- Implement caching where appropriate
- Consider memory usage for large operations
- Profile performance-critical code

## 🔍 Code Review Guidelines

### For Contributors

- Keep PRs focused and small
- Provide clear description of changes
- Respond to feedback promptly
- Be open to suggestions

### For Reviewers

- Be constructive and helpful
- Focus on code quality and maintainability
- Check for test coverage
- Verify documentation updates

## 📋 Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes (backward compatible)

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version number bumped
- [ ] Changelog updated
- [ ] Release notes prepared

## 🤝 Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help others learn and grow

### Communication

- Use GitHub Issues for bug reports and feature requests
- Use GitHub Discussions for questions and general discussion
- Be patient and helpful in responses
- Search existing issues before creating new ones

## 📞 Getting Help

If you need help with contributing:

1. Check existing documentation
2. Search GitHub Issues and Discussions
3. Ask questions in GitHub Discussions
4. Contact maintainers: b.tian@tue.nl

Thank you for contributing to KNMI EPW Generator! 🎉
