"""
Streamlined main module tests focusing on behavior, not implementation details.
"""

import sys
import os
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main


class TestMainModuleBehavior(unittest.TestCase):
    """Test main module behavior and workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create basic settings data
        self.settings_data = {
            "version": "1.0.0",
            "file_format": "md",
            "login_on_startup": False,
            "default_save_location": self.temp_dir,
        }

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_to_file_creates_file_with_content(self):
        """Write to file should create file with specified content."""
        test_path = Path(self.temp_dir) / "test_file.md"
        test_content = "# Test Content\n\nThis is a test file."

        main._write_to_file(test_path, test_content)

        self.assertTrue(test_path.exists())

    def test_write_to_file_content_matches_input(self):
        """Write to file should write exact content provided."""
        test_path = Path(self.temp_dir) / "test_file.md"
        test_content = "# Test Content\n\nThis is a test file."

        main._write_to_file(test_path, test_content)

        with open(test_path, "r", encoding="utf-8") as f:
            actual_content = f.read()
        self.assertEqual(actual_content, test_content)

    def test_write_to_file_creates_parent_directories(self):
        """Write to file should create parent directories if they don't exist."""
        nested_path = Path(self.temp_dir) / "nested" / "dir" / "test_file.md"
        test_content = "# Test Content"

        main._write_to_file(nested_path, test_content)

        self.assertTrue(nested_path.parent.exists())

    def test_write_to_file_nested_file_exists_after_creation(self):
        """Write to file should create nested file successfully."""
        nested_path = Path(self.temp_dir) / "nested" / "dir" / "test_file.md"
        test_content = "# Test Content"

        main._write_to_file(nested_path, test_content)

        self.assertTrue(nested_path.exists())

    @patch("main.Settings")
    def test_load_settings_returns_settings_instance(self, mock_settings_class):
        """Load settings should return a Settings instance."""
        mock_settings_instance = Mock()
        mock_settings_instance.update_check_on_startup = False
        mock_settings_class.return_value = mock_settings_instance

        result = main._load_settings()

        self.assertEqual(result, mock_settings_instance)

    @patch("main.Settings")
    def test_load_settings_calls_settings_constructor(self, mock_settings_class):
        """Load settings should instantiate Settings class."""
        mock_settings_instance = Mock()
        mock_settings_instance.update_check_on_startup = False
        mock_settings_class.return_value = mock_settings_instance

        main._load_settings()

        mock_settings_class.assert_called_once()

    @patch("main.CommandLineArgs")
    def test_parse_cli_args_returns_cli_args_instance(self, mock_cli_args_class):
        """Parse CLI args should return CommandLineArgs instance."""
        mock_cli_args_instance = Mock()
        mock_cli_args_class.return_value = mock_cli_args_instance

        result = main._parse_cli_args()

        self.assertEqual(result, mock_cli_args_instance)

    @patch("main.CommandLineArgs")
    def test_parse_cli_args_calls_constructor(self, mock_cli_args_class):
        """Parse CLI args should instantiate CommandLineArgs class."""
        mock_cli_args_instance = Mock()
        mock_cli_args_class.return_value = mock_cli_args_instance

        main._parse_cli_args()

        mock_cli_args_class.assert_called_once()

    @patch("main.utils.valid_url")
    def test_process_single_url_returns_false_for_invalid_url(self, mock_valid_url):
        """Process single URL should return False for invalid URLs."""
        mock_valid_url.return_value = False
        mock_settings = Mock()

        result = main._process_single_url(
            index=1,
            url="invalid_url",
            total=1,
            settings=mock_settings,
            base_save_dir=self.temp_dir,
            colors=["🟩"],
            access_token="",
        )

        self.assertFalse(result)

    @patch("main.UrlFetcher")
    @patch("main.utils.clean_url")
    def test_fetch_urls_returns_cleaned_urls(
        self, mock_clean_url, mock_url_fetcher_class
    ):
        """Fetch URLs should return cleaned URLs."""
        mock_settings = Mock()
        mock_cli_args = Mock()
        mock_access_token = "test_token"

        # Mock UrlFetcher
        mock_fetcher = Mock()
        mock_fetcher.urls = ["dirty_url1", "dirty_url2"]
        mock_url_fetcher_class.return_value = mock_fetcher

        # Mock clean_url
        mock_clean_url.side_effect = ["clean_url1", "clean_url2"]

        result = main._fetch_urls(mock_settings, mock_cli_args, mock_access_token)

        self.assertEqual(result, ["clean_url1", "clean_url2"])

    @patch("main.UrlFetcher")
    @patch("main.utils.clean_url")
    def test_fetch_urls_filters_empty_urls(
        self, mock_clean_url, mock_url_fetcher_class
    ):
        """Fetch URLs should filter out empty URLs."""
        mock_settings = Mock()
        mock_cli_args = Mock()
        mock_access_token = "test_token"

        # Mock UrlFetcher with empty URL
        mock_fetcher = Mock()
        mock_fetcher.urls = ["url1", "", "url2"]
        mock_url_fetcher_class.return_value = mock_fetcher

        # Mock clean_url
        mock_clean_url.side_effect = ["clean_url1", "clean_url2"]

        result = main._fetch_urls(mock_settings, mock_cli_args, mock_access_token)

        self.assertEqual(len(result), 2)

    @patch("main.UrlFetcher")
    @patch("main.utils.clean_url")
    def test_fetch_urls_creates_url_fetcher_with_token(
        self, mock_clean_url, mock_url_fetcher_class
    ):
        """Fetch URLs should create UrlFetcher with access token."""
        mock_settings = Mock()
        mock_cli_args = Mock()
        mock_access_token = "test_token"

        # Mock UrlFetcher
        mock_fetcher = Mock()
        mock_fetcher.urls = ["url1"]
        mock_url_fetcher_class.return_value = mock_fetcher

        mock_clean_url.return_value = "clean_url1"

        main._fetch_urls(mock_settings, mock_cli_args, mock_access_token)

        mock_url_fetcher_class.assert_called_once_with(
            mock_settings, mock_cli_args, mock_access_token
        )


class TestMainWorkflowBehavior(unittest.TestCase):
    """Test main workflow behavior patterns."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("main._process_single_url")
    @patch("time.sleep")
    def test_process_all_urls_calls_process_for_each_url(
        self, mock_sleep, mock_process_single
    ):
        """Process all URLs should call process single URL for each URL."""
        urls = ["url1", "url2", "url3"]
        mock_settings = Mock()
        base_save_dir = self.temp_dir
        access_token = "test_token"

        main._process_all_urls(urls, mock_settings, base_save_dir, access_token)

        self.assertEqual(mock_process_single.call_count, 3)

    @patch("main._process_single_url")
    @patch("time.sleep")
    def test_process_all_urls_sleeps_between_requests(
        self, mock_sleep, mock_process_single
    ):
        """Process all URLs should sleep between requests."""
        urls = ["url1", "url2", "url3"]
        mock_settings = Mock()

        main._process_all_urls(urls, mock_settings, self.temp_dir, "")

        self.assertEqual(mock_sleep.call_count, 3)

    @patch("main._process_single_url")
    @patch("time.sleep")
    def test_process_all_urls_sleeps_correct_duration(
        self, mock_sleep, mock_process_single
    ):
        """Process all URLs should sleep for correct duration between requests."""
        urls = ["url1", "url2"]
        mock_settings = Mock()

        main._process_all_urls(urls, mock_settings, self.temp_dir, "")

        mock_sleep.assert_called_with(0.1)

    @patch("main.auth.get_access_token")
    @patch("main._process_all_urls")
    @patch("main._fetch_urls")
    @patch("main._parse_cli_args")
    @patch("main._load_settings")
    def test_main_calls_load_settings(
        self,
        mock_load_settings,
        mock_parse_cli,
        mock_fetch_urls,
        mock_process,
        mock_auth,
    ):
        """Main function should call load settings."""
        mock_settings = Mock()
        mock_settings.login_on_startup = False
        mock_settings.default_save_location = self.temp_dir
        mock_load_settings.return_value = mock_settings

        mock_cli_args = Mock()
        mock_parse_cli.return_value = mock_cli_args
        mock_fetch_urls.return_value = []
        mock_process.return_value = None

        main.main()

        mock_load_settings.assert_called_once()

    @patch("main.auth.get_access_token")
    @patch("main._process_all_urls")
    @patch("main._fetch_urls")
    @patch("main._parse_cli_args")
    @patch("main._load_settings")
    def test_main_calls_parse_cli_args(
        self,
        mock_load_settings,
        mock_parse_cli,
        mock_fetch_urls,
        mock_process,
        mock_auth,
    ):
        """Main function should call parse CLI args."""
        mock_settings = Mock()
        mock_settings.login_on_startup = False
        mock_settings.default_save_location = self.temp_dir
        mock_load_settings.return_value = mock_settings

        mock_cli_args = Mock()
        mock_parse_cli.return_value = mock_cli_args
        mock_fetch_urls.return_value = []
        mock_process.return_value = None

        main.main()

        mock_parse_cli.assert_called_once()

    @patch("main.auth.get_access_token")
    @patch("main._process_all_urls")
    @patch("main._fetch_urls")
    @patch("main._parse_cli_args")
    @patch("main._load_settings")
    def test_main_calls_fetch_urls(
        self,
        mock_load_settings,
        mock_parse_cli,
        mock_fetch_urls,
        mock_process,
        mock_auth,
    ):
        """Main function should call fetch URLs."""
        mock_settings = Mock()
        mock_settings.login_on_startup = False
        mock_settings.default_save_location = self.temp_dir
        mock_load_settings.return_value = mock_settings

        mock_cli_args = Mock()
        mock_parse_cli.return_value = mock_cli_args
        mock_fetch_urls.return_value = []
        mock_process.return_value = None

        main.main()

        mock_fetch_urls.assert_called_once()

    @patch("main.auth.get_access_token")
    @patch("main._process_all_urls")
    @patch("main._fetch_urls")
    @patch("main._parse_cli_args")
    @patch("main._load_settings")
    def test_main_calls_process_all_urls(
        self,
        mock_load_settings,
        mock_parse_cli,
        mock_fetch_urls,
        mock_process,
        mock_auth,
    ):
        """Main function should call process all URLs."""
        mock_settings = Mock()
        mock_settings.login_on_startup = False
        mock_settings.default_save_location = self.temp_dir
        mock_load_settings.return_value = mock_settings

        mock_cli_args = Mock()
        mock_parse_cli.return_value = mock_cli_args
        mock_fetch_urls.return_value = ["test_url"]
        mock_process.return_value = None

        main.main()

        mock_process.assert_called_once()

    @patch("main.auth.get_access_token")
    @patch("main._process_all_urls")
    @patch("main._fetch_urls")
    @patch("main._parse_cli_args")
    @patch("main._load_settings")
    def test_main_attempts_authentication_when_enabled(
        self,
        mock_load_settings,
        mock_parse_cli,
        mock_fetch_urls,
        mock_process,
        mock_auth,
    ):
        """Main function should attempt authentication when login_on_startup is enabled."""
        mock_settings = Mock()
        mock_settings.login_on_startup = True
        mock_settings.client_id = "test_id"
        mock_settings.client_secret = "test_secret"
        mock_settings.default_save_location = self.temp_dir
        mock_load_settings.return_value = mock_settings

        mock_cli_args = Mock()
        mock_parse_cli.return_value = mock_cli_args
        mock_auth.return_value = "test_token"
        mock_fetch_urls.return_value = []
        mock_process.return_value = None

        main.main()

        mock_auth.assert_called_once_with("test_id", "test_secret")

    @patch("main.auth.get_access_token")
    @patch("main._process_all_urls")
    @patch("main._fetch_urls")
    @patch("main._parse_cli_args")
    @patch("main._load_settings")
    def test_main_continues_with_empty_token_on_auth_failure(
        self,
        mock_load_settings,
        mock_parse_cli,
        mock_fetch_urls,
        mock_process,
        mock_auth,
    ):
        """Main function should continue with empty token when authentication fails."""
        mock_settings = Mock()
        mock_settings.login_on_startup = True
        mock_settings.client_id = "test_id"
        mock_settings.client_secret = "test_secret"
        mock_settings.default_save_location = self.temp_dir
        mock_load_settings.return_value = mock_settings

        mock_cli_args = Mock()
        mock_parse_cli.return_value = mock_cli_args
        mock_auth.return_value = ""  # Auth failure
        mock_fetch_urls.return_value = []
        mock_process.return_value = None

        main.main()

        # Should call fetch_urls with empty token
        mock_fetch_urls.assert_called_once_with(mock_settings, mock_cli_args, "")


if __name__ == "__main__":
    unittest.main()
