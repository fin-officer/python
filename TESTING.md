# Testing Framework for Fin Officer

This document describes the testing framework and code quality tools set up for the Fin Officer project.

## Overview

We've implemented a comprehensive testing and code quality framework that includes:

- **Unit Tests**: Using pytest for testing individual components
- **Code Formatting**: Using Black to ensure consistent code style
- **Linting**: Using Flake8 and Pylint to catch potential issues
- **Import Sorting**: Using isort to organize imports
- **Continuous Integration**: Using GitHub Actions to automate testing

## Running Tests

### Using Tox

Tox is configured to run tests in isolated environments. To run all tests and checks:

```bash
tox
```

To run only the tests:

```bash
tox -e py310
```

To run only the linting checks:

```bash
tox -e lint
```

To run only the formatting checks:

```bash
tox -e format
```

### Using Pytest Directly

To run tests directly with pytest:

```bash
python -m pytest tests/
```

To run a specific test file:

```bash
python -m pytest tests/test_mcp_auto_reply_unit.py
```

## Code Quality Tools

### Black

To format your code with Black:

```bash
black app/ tests/
```

### Isort

To sort imports with isort:

```bash
isort app/ tests/
```

### Flake8

To check your code with Flake8:

```bash
flake8 app/ tests/
```

### Pylint

To check your code with Pylint:

```bash
pylint app/
```

## Continuous Integration

GitHub Actions is configured to run tests and code quality checks on every push to the main branch and on pull requests. The workflow is defined in `.github/workflows/python-tests.yml`.

## Test Coverage

To generate a test coverage report:

```bash
python -m pytest --cov=app tests/
```

## Writing Tests

### Unit Tests

Unit tests should be placed in the `tests/` directory and should follow the naming convention `test_*.py`. Each test function should be prefixed with `test_`.

For asynchronous tests, use the `@pytest.mark.asyncio` decorator.

Example:

```python
import pytest

@pytest.mark.asyncio
async def test_generate_auto_reply():
    # Test code here
    pass
```

### Mocking

Use the `unittest.mock` module for mocking dependencies in tests.

Example:

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_with_mocks():
    with patch('module.function', return_value=AsyncMock()):
        # Test code here
        pass
```

## Test Data

Test data should be defined in fixtures to make it reusable across tests.

Example:

```python
@pytest.fixture
def sample_email():
    return EmailSchema(
        id=1,
        from_email="test@example.com",
        to_email="support@finofficer.com",
        subject="Test Subject",
        content="Test Content",
        received_date="2025-05-20T00:00:00"
    )
```

## Best Practices

1. Write tests before implementing features (Test-Driven Development)
2. Keep tests small and focused on a single functionality
3. Use descriptive test names that explain what is being tested
4. Use fixtures for common setup code
5. Mock external dependencies to isolate the code being tested
6. Run tests frequently during development
7. Maintain high test coverage for critical components
