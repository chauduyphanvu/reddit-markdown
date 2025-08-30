# Reddit Markdown Test Suite

This directory contains comprehensive tests for the reddit-markdown application, organized into multiple categories for thorough coverage.

## Test Categories

### Unit Tests
- `test_auth.py` - Authentication module tests
- `test_cli_args.py` - Command line argument parsing tests
- `test_filters.py` - Content filtering tests
- `test_post_renderer.py` - Post rendering tests
- `test_reddit_utils.py` - Reddit utilities tests
- `test_settings.py` - Settings management tests
- `test_url_fetcher.py` - URL fetching tests

### Edge Case Tests
- `test_auth_edge_cases.py` - Authentication edge cases
- `test_filters_edge_cases.py` - Content filtering edge cases
- `test_main_edge_cases.py` - Main module edge cases
- `test_reddit_utils_edge_cases.py` - Reddit utilities edge cases

### Comprehensive Tests
- `test_url_fetcher_comprehensive.py` - Comprehensive URL fetcher scenarios
- `test_rate_limiter_and_caching.py` - Rate limiting and caching functionality
- `test_settings_advanced.py` - Advanced settings scenarios including .env handling

### Integration Tests
- `test_main_integration.py` - Main module integration tests
- `test_integration_edge_cases.py` - Cross-module integration edge cases
- `test_comprehensive_integration.py` - End-to-end workflow tests

### Test Utilities
- `test_utils.py` - Shared test utilities, fixtures, and mock factories

## Running Tests

### Run All Tests
```bash
cd /Users/vu/Workspace/reddit-markdown/python
python -m pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Unit tests only
python -m pytest tests/test_auth.py tests/test_cli_args.py tests/test_filters.py -v

# Edge case tests
python -m pytest tests/test_*_edge_cases.py -v

# Integration tests
python -m pytest tests/test_*_integration*.py -v
```

### Run Tests with Coverage
```bash
python -m pytest tests/ --cov=. --cov-report=html
```

## Test Structure

### Base Classes
- `BaseTestCase` - Basic test setup with logging disabled
- `TempDirTestCase` - Tests requiring temporary directories

### Mock Factories
- `MockFactory.create_settings_mock()` - Settings object mocks
- `MockFactory.create_cli_args_mock()` - CLI args object mocks
- `MockFactory.create_http_response()` - HTTP response mocks

### Test Data Fixtures
- `TestDataFixtures.get_sample_post_data()` - Sample Reddit post data
- `TestDataFixtures.get_sample_comment_data()` - Sample Reddit comment data
- `TestDataFixtures.get_sample_reddit_json_response()` - Complete Reddit API response

## Coverage Areas

The test suite covers:

### Core Functionality
- Reddit API authentication
- Post and comment fetching
- Content filtering and processing
- File generation and saving
- Settings management

### Edge Cases
- Network errors and timeouts
- Malformed JSON responses
- Invalid URL handling
- Rate limiting scenarios
- Cache management
- File system errors

### Advanced Scenarios
- Unicode content handling
- Large dataset processing
- Complex nested comment threads
- Environment variable integration
- Cross-module interactions

### Security & Performance
- Input validation
- Path traversal prevention
- ReDoS attack prevention in regex
- Memory management
- Rate limiting enforcement

## Adding New Tests

When adding new tests:

1. Choose appropriate test file based on the module being tested
2. Use existing base classes (`BaseTestCase`, `TempDirTestCase`)
3. Leverage mock factories and fixtures from `test_utils.py`
4. Follow naming convention: `test_<functionality>_<scenario>`
5. Add docstrings explaining what is being tested
6. Include both positive and negative test cases

## Test Configuration

The tests are configured to:
- Disable logging output during test runs
- Use temporary directories for file operations
- Mock external dependencies (network calls, file system)
- Provide isolated test environments
- Support parallel test execution