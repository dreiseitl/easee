# Test Suite

This directory contains comprehensive tests for the EV Charging Invoicing System.

## Test Structure

- `test_easee_api.py` - Unit tests for the EaseeAPI class
- `test_flask_routes.py` - Integration tests for Flask routes and endpoints
- `test_consumption_processing.py` - Tests for consumption data processing and calculations
- `test_templates.py` - Tests for HTML template structure and rendering
- `conftest.py` - Pytest configuration and shared fixtures

## Running Tests

### Run all tests:
```bash
pytest
```

### Run with coverage report:
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file:
```bash
pytest tests/test_easee_api.py
```

### Run specific test:
```bash
pytest tests/test_easee_api.py::TestEaseeAPI::test_authenticate_success
```

### Run with verbose output:
```bash
pytest -v
```

## Test Coverage

The test suite covers:
- ✅ Authentication flow
- ✅ API endpoint calls (sites, chargers, consumption)
- ✅ Data processing and calculations
- ✅ Error handling
- ✅ Route protection (authentication required)
- ✅ Template rendering
- ✅ Price calculations (1 kWh = 1 NOK)

## Continuous Integration

These tests are designed to be run in CI/CD pipelines to ensure the application works correctly after changes.

