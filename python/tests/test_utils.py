"""
Shared test utilities and fixtures for reddit-markdown tests.

This module provides common test utilities, mock factories, and base classes
to reduce code duplication across test files.
"""

import unittest
import logging
import tempfile
import shutil
import os
import json
import sys
import requests
from unittest.mock import Mock, patch
from datetime import datetime


class BaseTestCase(unittest.TestCase):
    """Base test case that handles common setup and teardown operations."""

    def setUp(self):
        """Set up common test fixtures."""
        # Disable logging during tests to reduce noise
        logging.disable(logging.CRITICAL)

        # Add parent directory to path for module imports
        parent_dir = os.path.join(os.path.dirname(__file__), "..")
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

    def tearDown(self):
        """Clean up after tests."""
        # Re-enable logging
        logging.disable(logging.NOTSET)


class TempDirTestCase(BaseTestCase):
    """Base test case that provides temporary directory management."""

    def setUp(self):
        """Set up test fixtures including temporary directory."""
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory and other fixtures."""
        super().tearDown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class AuthTestCase(BaseTestCase):
    """Base test case for authentication-related tests with common setup."""

    def setUp(self):
        """Set up common authentication test fixtures."""
        super().setUp()
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.valid_token = "test_access_token_123"
        self.access_token = "test_token"


class RedditUtilsTestCase(BaseTestCase):
    """Base test case for reddit_utils tests with cache clearing."""

    def setUp(self):
        """Set up test fixtures and clear cache."""
        super().setUp()
        # Clear the global cache to ensure test isolation
        try:
            import reddit_utils as utils

            utils._json_cache.clear()
            utils._cache_timestamps.clear()
        except (ImportError, AttributeError):
            # Cache variables might not exist yet
            pass


class FiltersTestCase(BaseTestCase):
    """Base test case for filters tests with regex cache clearing."""

    def setUp(self):
        """Set up test fixtures and clear regex cache."""
        super().setUp()
        self.default_filtered_message = "[FILTERED]"
        # Clear regex cache to ensure test isolation
        try:
            from filters import _regex_cache

            _regex_cache.clear()
        except (ImportError, AttributeError):
            # Cache might not exist yet
            pass


class MockFactory:
    """Factory class for creating common mock objects."""

    @staticmethod
    def create_http_response(
        json_data=None, raise_for_status=None, status_code=200, iter_content=None
    ):
        """Create a mock HTTP response object."""
        mock_response = Mock()
        mock_response.status_code = status_code

        if raise_for_status is not None:
            mock_response.raise_for_status.side_effect = raise_for_status
        else:
            mock_response.raise_for_status.return_value = None

        if json_data is not None:
            mock_response.json.return_value = json_data

        if iter_content is not None:
            mock_response.iter_content.return_value = iter_content

        return mock_response

    @staticmethod
    def create_network_error_mock(error_class, error_message):
        """Create a mock that raises network errors."""
        mock_response = Mock()
        mock_response.side_effect = error_class(error_message)
        return mock_response

    @staticmethod
    def create_auth_success_response(access_token="test_access_token_123"):
        """Create a mock successful authentication response."""
        return MockFactory.create_http_response(
            json_data={"access_token": access_token}
        )

    @staticmethod
    def create_auth_error_response(error_type="http"):
        """Create a mock authentication error response."""
        if error_type == "http":
            return MockFactory.create_http_response(
                raise_for_status=requests.exceptions.HTTPError("401 Unauthorized")
            )
        elif error_type == "network":
            return MockFactory.create_network_error_mock(
                requests.exceptions.ConnectionError, "Network error"
            )
        elif error_type == "timeout":
            return MockFactory.create_network_error_mock(
                requests.exceptions.Timeout, "Request timed out"
            )
        elif error_type == "missing_token":
            return MockFactory.create_http_response(
                json_data={"error": "invalid_grant"}
            )
        else:
            return MockFactory.create_http_response(
                raise_for_status=requests.exceptions.RequestException("Generic error")
            )

    @staticmethod
    def create_context_manager_mock(mock_object):
        """Create a context manager from a mock object."""
        mock_object.__enter__ = Mock(return_value=mock_object)
        mock_object.__exit__ = Mock(return_value=None)
        return mock_object

    @staticmethod
    def create_settings_mock(**overrides):
        """Create a mock Settings object with default values."""
        defaults = {
            "version": "1.0.0",
            "file_format": "md",
            "update_check_on_startup": True,
            "show_upvotes": True,
            "show_timestamp": True,
            "show_auto_mod_comment": False,
            "line_break_between_parent_replies": True,
            "reply_depth_color_indicators": True,
            "reply_depth_max": -1,
            "overwrite_existing_file": False,
            "save_posts_by_subreddits": False,
            "use_timestamped_directories": False,
            "enable_media_downloads": False,
            "login_on_startup": False,
            "client_id": "",
            "client_secret": "",
            "username": "",
            "password": "",
            "filtered_message": "[FILTERED]",
            "filtered_keywords": [],
            "filtered_authors": [],
            "filtered_min_upvotes": 0,
            "filtered_regexes": [],
            "default_save_location": "",
            "multi_reddits": {},
            "cache_ttl_seconds": 300,
            "max_cache_entries": 1000,
            "rate_limit_delay": 1.0,
            "timeout": 10,
        }

        # Apply overrides
        defaults.update(overrides)

        mock_settings = Mock()
        for key, value in defaults.items():
            setattr(mock_settings, key, value)

        return mock_settings

    @staticmethod
    def create_cli_args_mock(urls=None, src_files=None, subs=None, multis=None):
        """Create a mock CLI args object."""
        mock_args = Mock()
        mock_args.urls = urls or []
        mock_args.src_files = src_files or []
        mock_args.subs = subs or []
        mock_args.multis = multis or []
        return mock_args


class TestDataFixtures:
    """Common test data fixtures."""

    @staticmethod
    def get_sample_post_data():
        """Get sample Reddit post data."""
        return {
            "title": "Sample Post Title",
            "author": "sample_author",
            "subreddit_name_prefixed": "r/test",
            "ups": 100,
            "locked": False,
            "selftext": "This is sample post content.",
            "url": "https://reddit.com/r/test/comments/123/sample_post",
            "created_utc": 1640995200,  # 2022-01-01 00:00:00
        }

    @staticmethod
    def get_sample_comment_data():
        """Get sample Reddit comment data."""
        return {
            "data": {
                "author": "commenter",
                "body": "This is a sample comment.",
                "ups": 10,
                "created_utc": 1640995800,  # 2022-01-01 00:10:00
                "replies": "",
            }
        }

    @staticmethod
    def get_sample_reddit_json_response():
        """Get sample Reddit API JSON response."""
        return [
            {"data": {"children": [{"data": TestDataFixtures.get_sample_post_data()}]}},
            {"data": {"children": [TestDataFixtures.get_sample_comment_data()]}},
        ]

    @staticmethod
    def get_sample_settings_data():
        """Get sample settings JSON data."""
        return {
            "version": "1.0.0",
            "file_format": "md",
            "update_check_on_startup": True,
            "show_upvotes": True,
            "show_timestamp": True,
            "show_auto_mod_comment": False,
            "line_break_between_parent_replies": True,
            "reply_depth_color_indicators": True,
            "reply_depth_max": -1,
            "overwrite_existing_file": False,
            "save_posts_by_subreddits": False,
            "use_timestamped_directories": False,
            "enable_media_downloads": True,
            "auth": {
                "login_on_startup": False,
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "username": "test_user",
                "password": "test_pass",
            },
            "filtered_message": "Filtered",
            "filters": {
                "keywords": ["spam", "bad"],
                "min_upvotes": 0,
                "authors": ["banned_user"],
                "regexes": ["regex_pattern"],
            },
            "default_save_location": "/test/path",
            "multi_reddits": {"m/test": ["r/python", "r/programming"]},
        }


class AssertionHelpers:
    """Helper methods for common assertion patterns."""

    @staticmethod
    def assert_mock_called_with_headers(mock_call, expected_headers):
        """Assert that a mock was called with expected headers."""
        call_args = mock_call.call_args
        if call_args and len(call_args) > 1:
            actual_headers = call_args[1].get("headers", {})
            for key, value in expected_headers.items():
                assert key in actual_headers, f"Header {key} not found"
                assert actual_headers[key] == value, f"Header {key} mismatch"

    @staticmethod
    def assert_urls_equal_ignoring_order(actual_urls, expected_urls):
        """Assert that two lists of URLs are equal, ignoring order."""
        assert len(actual_urls) == len(
            expected_urls
        ), f"URL count mismatch: {len(actual_urls)} vs {len(expected_urls)}"
        assert set(actual_urls) == set(expected_urls), f"URL sets don't match"

    @staticmethod
    def assert_auth_request_called_correctly(
        mock_post,
        client_id,
        client_secret,
        expected_url="https://www.reddit.com/api/v1/access_token",
    ):
        """Assert that an authentication request was made correctly."""
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check URL
        assert call_args[0][0] == expected_url

        # Check data
        data = call_args[1]["data"]
        assert data["grant_type"] == "client_credentials"

        # Check auth
        auth = call_args[1]["auth"]
        assert auth.username == client_id
        assert auth.password == client_secret

        # Check headers
        headers = call_args[1]["headers"]
        assert "User-Agent" in headers

        # Check timeout
        assert "timeout" in call_args[1]

    @staticmethod
    def assert_file_written_correctly(mock_write, expected_filename, expected_content):
        """Assert that a file was written with correct parameters."""
        mock_write.assert_called_once()
        call_args = mock_write.call_args
        assert call_args[0][0] == expected_filename
        assert call_args[0][1] == expected_content

    @staticmethod
    def assert_directory_created(temp_dir, expected_path):
        """Assert that a directory was created at the expected path."""
        import os

        full_path = (
            os.path.join(temp_dir, expected_path)
            if not os.path.isabs(expected_path)
            else expected_path
        )
        assert os.path.exists(full_path), f"Directory {full_path} was not created"
        assert os.path.isdir(full_path), f"Path {full_path} is not a directory"


class MockContextManager:
    """Utility for creating context managers for testing."""

    def __init__(self, mock_object):
        self.mock_object = mock_object

    def __enter__(self):
        return self.mock_object

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def create_temp_file_with_content(content, suffix=".txt"):
    """Create a temporary file with given content."""
    temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=suffix)
    temp_file.write(content)
    temp_file.close()
    return temp_file.name


def patch_requests_get(return_value=None, side_effect=None):
    """Decorator to patch requests.get with common response."""

    def decorator(test_func):
        def wrapper(*args, **kwargs):
            with patch("requests.get") as mock_get:
                if return_value:
                    mock_get.return_value = return_value
                if side_effect:
                    mock_get.side_effect = side_effect
                return test_func(*args, **kwargs)

        return wrapper

    return decorator


def patch_requests_post(return_value=None, side_effect=None):
    """Decorator to patch requests.post with common response."""

    def decorator(test_func):
        def wrapper(*args, **kwargs):
            with patch("requests.post") as mock_post:
                if return_value:
                    mock_post.return_value = return_value
                if side_effect:
                    mock_post.side_effect = side_effect
                return test_func(*args, **kwargs)

        return wrapper

    return decorator


def patch_module_import(module_name, side_effect=ImportError("Module not available")):
    """Decorator to patch module imports."""

    def decorator(test_func):
        def wrapper(*args, **kwargs):
            with patch.dict("sys.modules", {module_name: None}):
                with patch("builtins.__import__", side_effect=side_effect):
                    return test_func(*args, **kwargs)

        return wrapper

    return decorator


class RequestsTestMixin:
    """Mixin class for testing code that uses requests library."""

    def create_mock_requests_response(
        self, json_data=None, status_code=200, raise_for_status=None, iter_content=None
    ):
        """Create a comprehensive mock requests response."""
        mock_response = Mock()
        mock_response.status_code = status_code

        if raise_for_status is not None:
            mock_response.raise_for_status.side_effect = raise_for_status
        else:
            mock_response.raise_for_status.return_value = None

        if json_data is not None:
            mock_response.json.return_value = json_data

        if iter_content is not None:
            mock_response.iter_content.return_value = iter_content

        return mock_response

    def mock_successful_json_response(self, json_data):
        """Create a mock for successful JSON response."""
        return self.create_mock_requests_response(json_data=json_data)

    def mock_network_error_response(self, error_class, error_message):
        """Create a mock that raises a network error."""
        mock_response = Mock()
        mock_response.side_effect = error_class(error_message)
        return mock_response


# Common test constants
TEST_URLS = {
    "valid_reddit_post": "https://www.reddit.com/r/python/comments/abc123/test_post/",
    "reddit_post_no_trailing_slash": "https://www.reddit.com/r/python/comments/abc123/test_post",
    "invalid_domain": "https://google.com/r/python/comments/abc123/test_post/",
    "missing_subreddit": "https://www.reddit.com/comments/abc123/test_post/",
}

TEST_USER_AGENTS = {
    "default": "RedditMarkdownConverter/1.0 (Safe Download Bot)",
}

TEST_TIMESTAMPS = {
    "post_time": 1640995200,  # 2022-01-01 00:00:00
    "comment_time": 1640995800,  # 2022-01-01 00:10:00
    "formatted_post_time": "2022-01-01 00:00:00",
    "formatted_comment_time": "2022-01-01 00:10:00",
}

TEST_TIMEOUTS = {
    "download_post_json": 30,
    "download_media": 10,
}
