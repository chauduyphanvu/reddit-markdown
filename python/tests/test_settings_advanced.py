"""
Advanced edge case tests for settings.py module.
Focuses on environment variable handling, .env file parsing, and complex scenarios.
"""

import sys
import os
import unittest
from unittest.mock import patch, mock_open, Mock
import json
import tempfile
from urllib.error import URLError

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from settings import Settings, _load_env_file
from .test_utils import BaseTestCase, TempDirTestCase


class TestEnvFileLoading(BaseTestCase):
    """Tests for .env file loading functionality."""

    def test_load_env_file_basic(self):
        """Test basic .env file loading."""
        env_content = """REDDIT_CLIENT_ID=test_client_id
REDDIT_CLIENT_SECRET=test_client_secret
REDDIT_USERNAME=test_user
"""

        with patch("builtins.open", mock_open(read_data=env_content)):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    _load_env_file(".env")

                    self.assertEqual(os.environ["REDDIT_CLIENT_ID"], "test_client_id")
                    self.assertEqual(
                        os.environ["REDDIT_CLIENT_SECRET"], "test_client_secret"
                    )
                    self.assertEqual(os.environ["REDDIT_USERNAME"], "test_user")

    def test_load_env_file_with_quotes(self):
        """Test .env file loading with quoted values."""
        env_content = """REDDIT_CLIENT_ID="test_client_id_quoted"
REDDIT_CLIENT_SECRET='test_client_secret_quoted'
REDDIT_PASSWORD="password with spaces"
"""

        with patch("builtins.open", mock_open(read_data=env_content)):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    _load_env_file(".env")

                    self.assertEqual(
                        os.environ["REDDIT_CLIENT_ID"], "test_client_id_quoted"
                    )
                    self.assertEqual(
                        os.environ["REDDIT_CLIENT_SECRET"], "test_client_secret_quoted"
                    )
                    self.assertEqual(
                        os.environ["REDDIT_PASSWORD"], "password with spaces"
                    )

    def test_load_env_file_with_comments_and_empty_lines(self):
        """Test .env file loading with comments and empty lines."""
        env_content = """# This is a comment
REDDIT_CLIENT_ID=test_id

# Another comment
REDDIT_CLIENT_SECRET=test_secret

# Empty line above and below

REDDIT_USERNAME=test_user
"""

        with patch("builtins.open", mock_open(read_data=env_content)):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    _load_env_file(".env")

                    self.assertEqual(os.environ["REDDIT_CLIENT_ID"], "test_id")
                    self.assertEqual(os.environ["REDDIT_CLIENT_SECRET"], "test_secret")
                    self.assertEqual(os.environ["REDDIT_USERNAME"], "test_user")

    def test_load_env_file_with_equals_in_values(self):
        """Test .env file loading with equals signs in values."""
        env_content = """REDDIT_CLIENT_ID=client_id_with=equals
REDDIT_URL=https://www.reddit.com/api/v1/access_token
COMPLEX_VALUE=key1=value1&key2=value2
"""

        with patch("builtins.open", mock_open(read_data=env_content)):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    _load_env_file(".env")

                    self.assertEqual(
                        os.environ["REDDIT_CLIENT_ID"], "client_id_with=equals"
                    )
                    self.assertEqual(
                        os.environ["REDDIT_URL"],
                        "https://www.reddit.com/api/v1/access_token",
                    )
                    self.assertEqual(
                        os.environ["COMPLEX_VALUE"], "key1=value1&key2=value2"
                    )

    def test_load_env_file_overwrites_existing_env_vars(self):
        """Test that .env file values overwrite existing environment variables."""
        with patch(
            "builtins.open", mock_open(read_data="REDDIT_CLIENT_ID=env_file_value")
        ):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(
                    os.environ, {"REDDIT_CLIENT_ID": "original_value"}, clear=True
                ):
                    _load_env_file(".env")

                    # .env file should take precedence
                    self.assertEqual(os.environ["REDDIT_CLIENT_ID"], "env_file_value")

    def test_load_env_file_handles_whitespace_keys_and_values(self):
        """Test .env file loading handles whitespace in keys and values."""
        env_content = """  REDDIT_CLIENT_ID  =  test_id_with_spaces  
REDDIT_CLIENT_SECRET=test_secret
   REDDIT_USERNAME   =   test_user   
"""

        with patch("builtins.open", mock_open(read_data=env_content)):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    _load_env_file(".env")

                    self.assertEqual(
                        os.environ["REDDIT_CLIENT_ID"], "test_id_with_spaces"
                    )
                    self.assertEqual(os.environ["REDDIT_CLIENT_SECRET"], "test_secret")
                    self.assertEqual(os.environ["REDDIT_USERNAME"], "test_user")

    def test_load_env_file_ignores_empty_keys(self):
        """Test that empty keys are ignored."""
        env_content = """REDDIT_CLIENT_ID=test_id
=empty_key_ignored
 = also_empty_key
REDDIT_CLIENT_SECRET=test_secret
"""

        with patch("builtins.open", mock_open(read_data=env_content)):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    _load_env_file(".env")

                    self.assertEqual(os.environ["REDDIT_CLIENT_ID"], "test_id")
                    self.assertEqual(os.environ["REDDIT_CLIENT_SECRET"], "test_secret")
                    # Empty keys should not be added
                    self.assertNotIn("", os.environ)

    def test_load_env_file_missing_file(self):
        """Test that missing .env file is handled gracefully."""
        with patch("os.path.isfile", return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                # Should not raise exception
                _load_env_file(".env")

                # Environment should remain empty
                self.assertEqual(len(os.environ), 0)

    def test_load_env_file_read_error(self):
        """Test that .env file read errors are handled gracefully."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    # Should not raise exception
                    _load_env_file(".env")

                    # Environment should remain empty
                    self.assertEqual(len(os.environ), 0)

    def test_load_env_file_malformed_lines(self):
        """Test handling of malformed lines in .env file."""
        env_content = """REDDIT_CLIENT_ID=test_id
malformed_line_without_equals
REDDIT_CLIENT_SECRET=test_secret
another_malformed_line
REDDIT_USERNAME=test_user
"""

        with patch("builtins.open", mock_open(read_data=env_content)):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    _load_env_file(".env")

                    # Valid lines should be processed
                    self.assertEqual(os.environ["REDDIT_CLIENT_ID"], "test_id")
                    self.assertEqual(os.environ["REDDIT_CLIENT_SECRET"], "test_secret")
                    self.assertEqual(os.environ["REDDIT_USERNAME"], "test_user")

    def test_load_env_file_unicode_content(self):
        """Test .env file loading with unicode content."""
        env_content = """REDDIT_USERNAME=用户名
REDDIT_PASSWORD=пароль
DESCRIPTION=This is a tëst with ünïcödé
"""

        with patch("builtins.open", mock_open(read_data=env_content)):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    _load_env_file(".env")

                    self.assertEqual(os.environ["REDDIT_USERNAME"], "用户名")
                    self.assertEqual(os.environ["REDDIT_PASSWORD"], "пароль")
                    self.assertEqual(
                        os.environ["DESCRIPTION"], "This is a tëst with ünïcödé"
                    )


class TestSettingsEnvironmentIntegration(BaseTestCase):
    """Tests for Settings class integration with environment variables."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.minimal_settings = {"version": "1.0.0"}

    def test_settings_reads_from_environment_variables(self):
        """Test that Settings reads credentials from environment variables."""
        env_vars = {
            "REDDIT_CLIENT_ID": "env_client_id",
            "REDDIT_CLIENT_SECRET": "env_client_secret",
            "REDDIT_USERNAME": "env_username",
            "REDDIT_PASSWORD": "env_password",
        }

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.minimal_settings))
        ):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, env_vars, clear=True):
                    settings = Settings("test_settings.json")

                    self.assertEqual(settings.client_id, "env_client_id")
                    self.assertEqual(settings.client_secret, "env_client_secret")
                    self.assertEqual(settings.username, "env_username")
                    self.assertEqual(settings.password, "env_password")

    def test_settings_handles_missing_environment_variables(self):
        """Test that Settings handles missing environment variables gracefully."""
        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.minimal_settings))
        ):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    settings = Settings("test_settings.json")

                    self.assertEqual(settings.client_id, "")
                    self.assertEqual(settings.client_secret, "")
                    self.assertEqual(settings.username, "")
                    self.assertEqual(settings.password, "")

    def test_settings_credential_validation_warnings(self):
        """Test that Settings warns about invalid credentials."""
        settings_data = {"version": "1.0.0", "auth": {"login_on_startup": True}}

        placeholder_credentials = {
            "REDDIT_CLIENT_ID": "your_actual_client_id_here",
            "REDDIT_CLIENT_SECRET": "d3yMnipxSomeSecretKey",
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(settings_data))):
            with patch("os.path.isfile", return_value=True):
                with patch.dict(os.environ, placeholder_credentials, clear=True):
                    # Should complete without raising exception despite placeholder values
                    settings = Settings("test_settings.json")

                    # Should still store the placeholder values
                    self.assertEqual(settings.client_id, "your_actual_client_id_here")
                    self.assertTrue(settings.client_secret.startswith("d3yMnipx"))

    def test_settings_performance_settings_integration(self):
        """Test that Settings properly exposes performance settings."""
        settings_data = {
            "version": "1.0.0",
            "performance": {
                "cache_ttl_seconds": 600,
                "max_cache_entries": 2000,
                "rate_limit_requests_per_minute": 45,
            },
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(settings_data))):
            with patch("os.path.isfile", return_value=True):
                settings = Settings("test_settings.json")

                self.assertEqual(settings.cache_ttl_seconds, 600)
                self.assertEqual(settings.max_cache_entries, 2000)
                self.assertEqual(settings.rate_limit_requests_per_minute, 45)

    def test_settings_performance_settings_defaults(self):
        """Test that Settings uses defaults for missing performance settings."""
        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.minimal_settings))
        ):
            with patch("os.path.isfile", return_value=True):
                settings = Settings("test_settings.json")

                # Should use defaults
                self.assertEqual(settings.cache_ttl_seconds, 300)
                self.assertEqual(settings.max_cache_entries, 1000)
                self.assertEqual(settings.rate_limit_requests_per_minute, 30)

    def test_settings_with_partial_performance_settings(self):
        """Test Settings with partial performance settings."""
        settings_data = {
            "version": "1.0.0",
            "performance": {
                "cache_ttl_seconds": 600,
                # Missing max_cache_entries and rate_limit_requests_per_minute
            },
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(settings_data))):
            with patch("os.path.isfile", return_value=True):
                settings = Settings("test_settings.json")

                self.assertEqual(settings.cache_ttl_seconds, 600)  # From settings
                self.assertEqual(settings.max_cache_entries, 1000)  # Default
                self.assertEqual(settings.rate_limit_requests_per_minute, 30)  # Default


class TestSettingsUpdateChecking(BaseTestCase):
    """Advanced tests for update checking functionality."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.settings_data = {
            "version": "1.0.0",
            "update_check_on_startup": False,  # Disable to avoid double calls
        }

    @patch("urllib.request.urlopen")
    def test_check_for_updates_with_prerelease_versions(self, mock_urlopen):
        """Test update checking handles pre-release versions correctly."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            [{"tag_name": "2.0.0-beta.1"}, {"tag_name": "1.5.0"}, {"tag_name": "1.0.0"}]
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.settings_data))
        ):
            with patch("os.path.isfile", return_value=True):
                # Mock packaging.version to handle comparison
                with patch("packaging.version.Version") as mock_version:
                    mock_version.side_effect = lambda v: Mock(
                        __gt__=lambda self, other: v
                        == "1.5.0"  # Only 1.5.0 is newer than 1.0.0
                    )

                    settings = Settings("test_settings.json")
                    settings.check_for_updates()

                    # Should have made the request
                    mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_check_for_updates_request_headers(self, mock_urlopen):
        """Test that update check uses proper request headers."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.settings_data))
        ):
            with patch("os.path.isfile", return_value=True):
                settings = Settings("test_settings.json")
                settings.check_for_updates()

                # Check that proper User-Agent was used
                call_args = mock_urlopen.call_args
                request = call_args[0][0]
                self.assertEqual(request.headers["User-agent"], "Mozilla/5.0")

    @patch("urllib.request.urlopen")
    def test_check_for_updates_malformed_json_response(self, mock_urlopen):
        """Test update checking handles malformed JSON gracefully."""
        mock_response = Mock()
        mock_response.read.return_value = b'{"invalid": json structure'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.settings_data))
        ):
            with patch("os.path.isfile", return_value=True):
                # Should not raise exception
                settings = Settings("test_settings.json")
                settings.check_for_updates()

    @patch("urllib.request.urlopen")
    def test_check_for_updates_handles_http_errors(self, mock_urlopen):
        """Test update checking handles various HTTP errors."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url="test_url", code=404, msg="Not Found", hdrs={}, fp=None
        )

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.settings_data))
        ):
            with patch("os.path.isfile", return_value=True):
                # Should not raise exception
                settings = Settings("test_settings.json")
                settings.check_for_updates()

    @patch("urllib.request.urlopen")
    def test_check_for_updates_timeout_handling(self, mock_urlopen):
        """Test update checking handles timeout gracefully."""
        import socket

        mock_urlopen.side_effect = socket.timeout("Connection timed out")

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.settings_data))
        ):
            with patch("os.path.isfile", return_value=True):
                # Should not raise exception
                settings = Settings("test_settings.json")
                settings.check_for_updates()

    @patch("urllib.request.urlopen")
    def test_check_for_updates_ssl_error_handling(self, mock_urlopen):
        """Test update checking handles SSL errors."""
        import ssl

        mock_urlopen.side_effect = ssl.SSLError("SSL certificate verification failed")

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.settings_data))
        ):
            with patch("os.path.isfile", return_value=True):
                # Should not raise exception
                settings = Settings("test_settings.json")
                settings.check_for_updates()

    @patch("urllib.request.urlopen")
    def test_check_for_updates_without_packaging_module(self, mock_urlopen):
        """Test update checking when packaging module is not available."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([{"tag_name": "2.0.0"}]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.settings_data))
        ):
            with patch("os.path.isfile", return_value=True):
                # Mock import error for packaging module
                with patch(
                    "builtins.__import__",
                    side_effect=ImportError("No module named 'packaging'"),
                ):
                    # Should handle import error gracefully
                    settings = Settings("test_settings.json")
                    settings.check_for_updates()


class TestSettingsComplexScenarios(BaseTestCase):
    """Tests for complex Settings scenarios and edge cases."""

    def test_settings_with_very_large_json_file(self):
        """Test Settings handles very large JSON configuration files."""
        # Create a large settings object with many entries
        large_settings = {
            "version": "1.0.0",
            "filters": {
                "keywords": [f"keyword_{i}" for i in range(1000)],
                "authors": [f"author_{i}" for i in range(500)],
                "regexes": [f"regex_{i}" for i in range(100)],
            },
            "multi_reddits": {
                f"m/multi_{i}": [f"r/sub_{j}" for j in range(10)] for i in range(50)
            },
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(large_settings))):
            with patch("os.path.isfile", return_value=True):
                settings = Settings("test_settings.json")

                # Should handle large data structures
                self.assertEqual(len(settings.filtered_keywords), 1000)
                self.assertEqual(len(settings.filtered_authors), 500)
                self.assertEqual(len(settings.multi_reddits), 50)

    def test_settings_with_deeply_nested_json(self):
        """Test Settings handles deeply nested JSON structures."""
        nested_settings = {
            "version": "1.0.0",
            "deeply": {
                "nested": {
                    "structure": {"with": {"many": {"levels": {"value": "deep_value"}}}}
                }
            },
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(nested_settings))):
            with patch("os.path.isfile", return_value=True):
                # Should not crash on deeply nested structures
                settings = Settings("test_settings.json")
                self.assertEqual(settings.version, "1.0.0")

    def test_settings_json_with_numeric_strings(self):
        """Test Settings handles numeric values as strings."""
        settings_data = {
            "version": "1.0.0",
            "reply_depth_max": "5",  # String instead of int
            "filters": {"min_upvotes": "10"},  # String instead of int
            "performance": {
                "cache_ttl_seconds": "600",  # String instead of int
                "rate_limit_requests_per_minute": "30",  # String instead of int
            },
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(settings_data))):
            with patch("os.path.isfile", return_value=True):
                settings = Settings("test_settings.json")

                # Should store as strings (application logic determines type handling)
                self.assertEqual(settings.reply_depth_max, "5")
                self.assertEqual(settings.filtered_min_upvotes, "10")
                self.assertEqual(settings.cache_ttl_seconds, "600")

    def test_settings_with_mixed_case_boolean_strings(self):
        """Test Settings with various boolean string representations."""
        settings_data = {
            "version": "1.0.0",
            "update_check_on_startup": "True",  # String boolean
            "show_upvotes": "FALSE",  # String boolean, different case
            "show_timestamp": "yes",  # Non-standard boolean
            "login_on_startup": 1,  # Numeric boolean
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(settings_data))):
            with patch("os.path.isfile", return_value=True):
                settings = Settings("test_settings.json")

                # Should store actual values (type coercion handled by application logic)
                self.assertEqual(settings.update_check_on_startup, "True")
                self.assertEqual(settings.show_upvotes, "FALSE")
                self.assertEqual(settings.show_timestamp, "yes")


if __name__ == "__main__":
    unittest.main()
