import unittest
from unittest.mock import patch, mock_open, Mock
import json
import tempfile
import os
import sys
import logging
from urllib.error import URLError

from settings import Settings


class TestSettings(unittest.TestCase):
    """Comprehensive test suite for settings.py module."""

    def setUp(self):
        """Set up test fixtures."""
        self.valid_settings = {
            "version": "1.0.0",
            "file_format": "md",
            "update_check_on_startup": True,
            "show_auto_mod_comment": True,
            "line_break_between_parent_replies": True,
            "show_upvotes": True,
            "reply_depth_color_indicators": True,
            "reply_depth_max": -1,
            "overwrite_existing_file": False,
            "save_posts_by_subreddits": False,
            "show_timestamp": True,
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

        # Disable logging during tests
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Clean up after tests."""
        logging.disable(logging.NOTSET)

    @patch("builtins.open", mock_open(read_data='{"version": "1.0.0"}'))
    @patch("os.path.isfile", return_value=True)
    def test_settings_minimal_valid_file(self, mock_isfile):
        """Test Settings with minimal valid JSON file."""
        settings = Settings("test_settings.json")

        self.assertEqual(settings.version, "1.0.0")
        # Test default values are applied
        self.assertEqual(settings.file_format, "md")
        self.assertEqual(settings.update_check_on_startup, True)

    @patch("builtins.open", mock_open())
    @patch("os.path.isfile", return_value=True)
    def test_settings_loads_all_properties(self, mock_isfile):
        """Test Settings loads all properties from complete JSON."""
        with patch(
            "builtins.open", mock_open(read_data=json.dumps(self.valid_settings))
        ):
            settings = Settings("test_settings.json")

        # Test basic config
        self.assertEqual(settings.version, "1.0.0")
        self.assertEqual(settings.file_format, "md")
        self.assertEqual(settings.update_check_on_startup, True)
        self.assertEqual(settings.show_auto_mod_comment, True)
        self.assertEqual(settings.line_break_between_parent_replies, True)
        self.assertEqual(settings.show_upvotes, True)
        self.assertEqual(settings.reply_depth_color_indicators, True)
        self.assertEqual(settings.reply_depth_max, -1)
        self.assertEqual(settings.overwrite_existing_file, False)
        self.assertEqual(settings.save_posts_by_subreddits, False)
        self.assertEqual(settings.show_timestamp, True)
        self.assertEqual(settings.use_timestamped_directories, False)
        self.assertEqual(settings.enable_media_downloads, True)

        # Test auth settings
        self.assertEqual(settings.login_on_startup, False)
        self.assertEqual(settings.client_id, "test_client_id")
        self.assertEqual(settings.client_secret, "test_client_secret")
        self.assertEqual(settings.username, "test_user")
        self.assertEqual(settings.password, "test_pass")

        # Test filtering options
        self.assertEqual(settings.filtered_message, "Filtered")
        self.assertEqual(settings.filtered_keywords, ["spam", "bad"])
        self.assertEqual(settings.filtered_min_upvotes, 0)
        self.assertEqual(settings.filtered_authors, ["banned_user"])
        self.assertEqual(settings.filtered_regexes, ["regex_pattern"])

        # Test additional settings
        self.assertEqual(settings.default_save_location, "/test/path")
        self.assertEqual(
            settings.multi_reddits, {"m/test": ["r/python", "r/programming"]}
        )

    @patch("os.path.isfile", return_value=False)
    def test_settings_missing_file_exits(self, mock_isfile):
        """Test Settings exits when file is missing."""
        with self.assertRaises(SystemExit):
            Settings("missing_settings.json")

    @patch("builtins.open", mock_open(read_data=""))
    @patch("os.path.isfile", return_value=True)
    def test_settings_empty_file_exits(self, mock_isfile):
        """Test Settings exits when file is empty."""
        with self.assertRaises(SystemExit):
            Settings("empty_settings.json")

    @patch("builtins.open", mock_open(read_data="invalid json"))
    @patch("os.path.isfile", return_value=True)
    def test_settings_invalid_json_exits(self, mock_isfile):
        """Test Settings exits when JSON is invalid."""
        with self.assertRaises(SystemExit):
            Settings("invalid_settings.json")

    @patch("builtins.open", mock_open(read_data="null"))
    @patch("os.path.isfile", return_value=True)
    def test_settings_null_json_exits(self, mock_isfile):
        """Test Settings exits when JSON is null."""
        with self.assertRaises(SystemExit):
            Settings("null_settings.json")

    @patch("builtins.open", mock_open())
    @patch("os.path.isfile", return_value=True)
    def test_settings_default_values_when_missing(self, mock_isfile):
        """Test Settings applies default values when properties are missing."""
        minimal_settings = {"version": "1.0.0"}
        with patch("builtins.open", mock_open(read_data=json.dumps(minimal_settings))):
            settings = Settings("test_settings.json")

        # Test all defaults are applied
        self.assertEqual(settings.version, "1.0.0")
        self.assertEqual(settings.file_format, "md")
        self.assertEqual(settings.update_check_on_startup, True)
        self.assertEqual(settings.show_auto_mod_comment, True)
        self.assertEqual(settings.line_break_between_parent_replies, True)
        self.assertEqual(settings.show_upvotes, True)
        self.assertEqual(settings.reply_depth_color_indicators, True)
        self.assertEqual(settings.reply_depth_max, -1)
        self.assertEqual(settings.overwrite_existing_file, False)
        self.assertEqual(settings.save_posts_by_subreddits, False)
        self.assertEqual(settings.show_timestamp, True)
        self.assertEqual(settings.use_timestamped_directories, False)
        self.assertEqual(settings.enable_media_downloads, True)

        # Test auth defaults
        self.assertEqual(settings.login_on_startup, False)
        self.assertEqual(settings.client_id, "")
        self.assertEqual(settings.client_secret, "")
        self.assertEqual(settings.username, "")
        self.assertEqual(settings.password, "")

        # Test filter defaults
        self.assertEqual(settings.filtered_message, "Filtered")
        self.assertEqual(settings.filtered_keywords, [])
        self.assertEqual(settings.filtered_min_upvotes, 0)
        self.assertEqual(settings.filtered_authors, [])
        self.assertEqual(settings.filtered_regexes, [])

        # Test other defaults
        self.assertEqual(settings.default_save_location, "")
        self.assertEqual(settings.multi_reddits, {})

    @patch("builtins.open", mock_open())
    @patch("os.path.isfile", return_value=True)
    def test_settings_partial_auth_section(self, mock_isfile):
        """Test Settings handles partial auth section."""
        partial_auth_settings = {
            "version": "1.0.0",
            "auth": {
                "login_on_startup": True,
                "client_id": "test_id",
                # Missing client_secret, username, password
            },
        }
        with patch(
            "builtins.open", mock_open(read_data=json.dumps(partial_auth_settings))
        ):
            settings = Settings("test_settings.json")

        self.assertEqual(settings.login_on_startup, True)
        self.assertEqual(settings.client_id, "test_id")
        self.assertEqual(settings.client_secret, "")
        self.assertEqual(settings.username, "")
        self.assertEqual(settings.password, "")

    @patch("builtins.open", mock_open())
    @patch("os.path.isfile", return_value=True)
    def test_settings_partial_filters_section(self, mock_isfile):
        """Test Settings handles partial filters section."""
        partial_filters_settings = {
            "version": "1.0.0",
            "filters": {
                "keywords": ["test"],
                "min_upvotes": 5,
                # Missing authors, regexes
            },
        }
        with patch(
            "builtins.open", mock_open(read_data=json.dumps(partial_filters_settings))
        ):
            settings = Settings("test_settings.json")

        self.assertEqual(settings.filtered_keywords, ["test"])
        self.assertEqual(settings.filtered_min_upvotes, 5)
        self.assertEqual(settings.filtered_authors, [])
        self.assertEqual(settings.filtered_regexes, [])

    @patch("builtins.open", mock_open())
    @patch("os.path.isfile", return_value=True)
    def test_settings_custom_file_path(self, mock_isfile):
        """Test Settings with custom file path."""
        with patch(
            "builtins.open",
            mock_open(
                read_data='{"version": "1.0.0", "update_check_on_startup": false}'
            ),
        ):
            settings = Settings("/custom/path/settings.json")

        self.assertEqual(settings.version, "1.0.0")
        # Verify the correct file path was called at some point
        mock_isfile.assert_any_call("/custom/path/settings.json")

    @patch("builtins.open", side_effect=IOError("File read error"))
    @patch("os.path.isfile", return_value=True)
    def test_settings_load_json_exception_handling(self, mock_isfile, mock_open):
        """Test Settings handles JSON loading exceptions."""
        # Should handle the exception and return None from _load_json
        # Which should then cause SystemExit
        with self.assertRaises(SystemExit):
            Settings("test_settings.json")

    @patch("builtins.open", mock_open(read_data='{"version": "1.0.0"}'))
    @patch("os.path.isfile", return_value=True)
    def test_check_for_updates_disabled(self, mock_isfile):
        """Test update checking is disabled when update_check_on_startup is False."""
        settings_data = {"version": "1.0.0", "update_check_on_startup": False}
        with patch("builtins.open", mock_open(read_data=json.dumps(settings_data))):
            with patch.object(Settings, "check_for_updates") as mock_check:
                settings = Settings("test_settings.json")
                mock_check.assert_not_called()

    @patch("builtins.open", mock_open(read_data='{"version": "1.0.0"}'))
    @patch("os.path.isfile", return_value=True)
    def test_check_for_updates_enabled(self, mock_isfile):
        """Test update checking is called when update_check_on_startup is True."""
        settings_data = {"version": "1.0.0", "update_check_on_startup": True}
        with patch("builtins.open", mock_open(read_data=json.dumps(settings_data))):
            with patch.object(Settings, "check_for_updates") as mock_check:
                settings = Settings("test_settings.json")
                mock_check.assert_called_once()

    @patch(
        "builtins.open",
        mock_open(read_data='{"version": "1.0.0", "update_check_on_startup": false}'),
    )
    @patch("os.path.isfile", return_value=True)
    @patch("urllib.request.urlopen")
    def test_check_for_updates_newer_version_available(self, mock_urlopen, mock_isfile):
        """Test update checking when newer version is available."""
        # Mock GitHub API response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([{"tag_name": "2.0.0"}]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch("packaging.version.Version") as mock_version:
            mock_version.side_effect = lambda v: Mock(
                __gt__=lambda self, other: v == "2.0.0"
            )

            settings = Settings("test_settings.json")
            settings.check_for_updates()

            mock_urlopen.assert_called_once()

    @patch(
        "builtins.open",
        mock_open(read_data='{"version": "2.0.0", "update_check_on_startup": false}'),
    )
    @patch("os.path.isfile", return_value=True)
    @patch("urllib.request.urlopen")
    def test_check_for_updates_current_version_up_to_date(
        self, mock_urlopen, mock_isfile
    ):
        """Test update checking when current version is up to date."""
        # Mock GitHub API response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([{"tag_name": "1.0.0"}]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch("packaging.version.Version") as mock_version:
            mock_version.side_effect = lambda v: Mock(__gt__=lambda self, other: False)

            settings = Settings("test_settings.json")
            settings.check_for_updates()

            mock_urlopen.assert_called_once()

    @patch(
        "builtins.open",
        mock_open(read_data='{"version": "1.0.0", "update_check_on_startup": false}'),
    )
    @patch("os.path.isfile", return_value=True)
    @patch("urllib.request.urlopen")
    def test_check_for_updates_no_releases(self, mock_urlopen, mock_isfile):
        """Test update checking when no releases are found."""
        # Mock GitHub API response with empty list
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        settings = Settings("test_settings.json")
        settings.check_for_updates()

        mock_urlopen.assert_called_once()

    @patch(
        "builtins.open",
        mock_open(read_data='{"version": "1.0.0", "update_check_on_startup": false}'),
    )
    @patch("os.path.isfile", return_value=True)
    @patch("urllib.request.urlopen")
    def test_check_for_updates_invalid_version_format(self, mock_urlopen, mock_isfile):
        """Test update checking with invalid version format from GitHub."""
        # Mock GitHub API response with invalid version
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            [{"tag_name": "invalid-version"}]
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        settings = Settings("test_settings.json")
        settings.check_for_updates()

        mock_urlopen.assert_called_once()

    @patch(
        "builtins.open",
        mock_open(read_data='{"version": "1.0.0", "update_check_on_startup": false}'),
    )
    @patch("os.path.isfile", return_value=True)
    @patch("urllib.request.urlopen")
    def test_check_for_updates_network_error(self, mock_urlopen, mock_isfile):
        """Test update checking handles network errors."""
        mock_urlopen.side_effect = URLError("Network error")

        settings = Settings("test_settings.json")
        settings.check_for_updates()

        mock_urlopen.assert_called_once()

    @patch(
        "builtins.open",
        mock_open(read_data='{"version": "1.0.0", "update_check_on_startup": false}'),
    )
    @patch("os.path.isfile", return_value=True)
    @patch("urllib.request.urlopen")
    def test_check_for_updates_timeout(self, mock_urlopen, mock_isfile):
        """Test update checking handles timeout."""
        import socket

        mock_urlopen.side_effect = socket.timeout("Request timed out")

        settings = Settings("test_settings.json")
        settings.check_for_updates()

        mock_urlopen.assert_called_once()

    @patch(
        "builtins.open",
        mock_open(read_data='{"version": "1.0.0", "update_check_on_startup": false}'),
    )
    @patch("os.path.isfile", return_value=True)
    @patch("urllib.request.urlopen")
    def test_check_for_updates_json_decode_error(self, mock_urlopen, mock_isfile):
        """Test update checking handles JSON decode errors."""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.read.return_value = b"invalid json"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        settings = Settings("test_settings.json")
        settings.check_for_updates()

        mock_urlopen.assert_called_once()

    @patch("builtins.open", mock_open())
    @patch("os.path.isfile", return_value=True)
    def test_settings_with_unicode_content(self, mock_isfile):
        """Test Settings handles unicode content correctly."""
        unicode_settings = {
            "version": "1.0.0",
            "filtered_message": "フィルタリング済み",  # Japanese text
            "filters": {
                "keywords": ["spam", "スパム"],  # Mixed languages
                "authors": ["ユーザー"],
            },
        }
        with patch(
            "builtins.open",
            mock_open(read_data=json.dumps(unicode_settings, ensure_ascii=False)),
        ):
            settings = Settings("test_settings.json")

        self.assertEqual(settings.filtered_message, "フィルタリング済み")
        self.assertEqual(settings.filtered_keywords, ["spam", "スパム"])
        self.assertEqual(settings.filtered_authors, ["ユーザー"])

    @patch("builtins.open", mock_open())
    @patch("os.path.isfile", return_value=True)
    def test_settings_boolean_type_coercion(self, mock_isfile):
        """Test Settings handles different boolean representations."""
        boolean_settings = {
            "version": "1.0.0",
            "update_check_on_startup": "true",  # String instead of boolean
            "show_upvotes": 1,  # Integer instead of boolean
            "overwrite_existing_file": 0,  # Integer instead of boolean
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(boolean_settings))):
            settings = Settings("test_settings.json")

        # Test how the application handles non-boolean values
        self.assertEqual(settings.update_check_on_startup, "true")  # Will be truthy
        self.assertEqual(settings.show_upvotes, 1)  # Will be truthy
        self.assertEqual(settings.overwrite_existing_file, 0)  # Will be falsy


if __name__ == "__main__":
    unittest.main()
