import unittest
from unittest.mock import patch, Mock, MagicMock
import tempfile
import os
import json
import logging

import main


class TestMainIntegration(unittest.TestCase):
    """Integration tests for main.py module."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create a temporary settings file
        self.settings_data = {
            "version": "1.0.0",
            "file_format": "md",
            "update_check_on_startup": False,
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
            "auth": {
                "login_on_startup": False,
                "client_id": "",
                "client_secret": "",
                "username": "",
                "password": "",
            },
            "filtered_message": "Filtered",
            "filters": {"keywords": [], "min_upvotes": 0, "authors": [], "regexes": []},
            "default_save_location": self.temp_dir,
            "multi_reddits": {},
        }

        self.settings_file = os.path.join(self.temp_dir, "settings.json")
        with open(self.settings_file, "w") as f:
            json.dump(self.settings_data, f)

        logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Clean up after tests."""
        logging.disable(logging.NOTSET)
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("main._process_all_urls")
    @patch("main._fetch_urls")
    @patch("main._parse_cli_args")
    @patch("main._load_settings")
    def test_main_flow_without_auth(
        self, mock_load_settings, mock_parse_cli, mock_fetch_urls, mock_process
    ):
        """Test main function flow without authentication."""
        # Mock the settings
        mock_settings = Mock()
        mock_settings.login_on_startup = False
        mock_settings.default_save_location = self.temp_dir
        mock_load_settings.return_value = mock_settings

        # Mock CLI args
        mock_cli_args = Mock()
        mock_parse_cli.return_value = mock_cli_args

        # Mock URL fetching
        mock_fetch_urls.return_value = ["https://reddit.com/r/test/comments/123/post"]

        # Mock processing
        mock_process.return_value = None

        # Run main
        main.main()

        # Verify the flow
        mock_load_settings.assert_called_once()
        mock_parse_cli.assert_called_once()
        mock_fetch_urls.assert_called_once_with(mock_settings, mock_cli_args, "")
        mock_process.assert_called_once()

    @patch("main.auth.get_access_token")
    @patch("main._process_all_urls")
    @patch("main._fetch_urls")
    @patch("main._parse_cli_args")
    @patch("main._load_settings")
    def test_main_flow_with_auth_success(
        self,
        mock_load_settings,
        mock_parse_cli,
        mock_fetch_urls,
        mock_process,
        mock_auth,
    ):
        """Test main function flow with successful authentication."""
        # Mock the settings
        mock_settings = Mock()
        mock_settings.login_on_startup = True
        mock_settings.client_id = "test_id"
        mock_settings.client_secret = "test_secret"
        mock_settings.default_save_location = self.temp_dir
        mock_load_settings.return_value = mock_settings

        # Mock CLI args
        mock_cli_args = Mock()
        mock_parse_cli.return_value = mock_cli_args

        # Mock successful authentication
        mock_auth.return_value = "test_token"

        # Mock URL fetching
        mock_fetch_urls.return_value = ["https://reddit.com/r/test/comments/123/post"]

        # Mock processing
        mock_process.return_value = None

        # Run main
        main.main()

        # Verify authentication was attempted
        mock_auth.assert_called_once_with("test_id", "test_secret")
        mock_fetch_urls.assert_called_once_with(
            mock_settings, mock_cli_args, "test_token"
        )

    @patch("main.auth.get_access_token")
    @patch("main._process_all_urls")
    @patch("main._fetch_urls")
    @patch("main._parse_cli_args")
    @patch("main._load_settings")
    def test_main_flow_with_auth_failure(
        self,
        mock_load_settings,
        mock_parse_cli,
        mock_fetch_urls,
        mock_process,
        mock_auth,
    ):
        """Test main function flow with failed authentication."""
        # Mock the settings
        mock_settings = Mock()
        mock_settings.login_on_startup = True
        mock_settings.client_id = "test_id"
        mock_settings.client_secret = "test_secret"
        mock_settings.default_save_location = self.temp_dir
        mock_load_settings.return_value = mock_settings

        # Mock CLI args
        mock_cli_args = Mock()
        mock_parse_cli.return_value = mock_cli_args

        # Mock failed authentication
        mock_auth.return_value = ""

        # Mock URL fetching
        mock_fetch_urls.return_value = ["https://reddit.com/r/test/comments/123/post"]

        # Mock processing
        mock_process.return_value = None

        # Run main
        main.main()

        # Verify it continues without token
        mock_fetch_urls.assert_called_once_with(mock_settings, mock_cli_args, "")

    @patch("main.Settings")
    def test_load_settings(self, mock_settings_class):
        """Test _load_settings function."""
        mock_settings_instance = Mock()
        mock_settings_instance.update_check_on_startup = False
        mock_settings_class.return_value = mock_settings_instance

        result = main._load_settings()

        self.assertEqual(result, mock_settings_instance)
        mock_settings_class.assert_called_once()

    @patch("main.Settings")
    def test_load_settings_with_update_check(self, mock_settings_class):
        """Test _load_settings function with update check enabled."""
        mock_settings_instance = Mock()
        mock_settings_instance.update_check_on_startup = True
        mock_settings_class.return_value = mock_settings_instance

        result = main._load_settings()

        mock_settings_instance.check_for_updates.assert_called_once()

    @patch("main.CommandLineArgs")
    def test_parse_cli_args(self, mock_cli_args_class):
        """Test _parse_cli_args function."""
        mock_cli_args_instance = Mock()
        mock_cli_args_class.return_value = mock_cli_args_instance

        result = main._parse_cli_args()

        self.assertEqual(result, mock_cli_args_instance)
        mock_cli_args_class.assert_called_once()

    @patch("main.UrlFetcher")
    @patch("main.utils.clean_url")
    def test_fetch_urls(self, mock_clean_url, mock_url_fetcher_class):
        """Test _fetch_urls function."""
        mock_settings = Mock()
        mock_cli_args = Mock()
        mock_access_token = "test_token"

        # Mock UrlFetcher
        mock_fetcher = Mock()
        mock_fetcher.urls = ["dirty_url1", "dirty_url2", ""]
        mock_url_fetcher_class.return_value = mock_fetcher

        # Mock clean_url
        mock_clean_url.side_effect = ["clean_url1", "clean_url2"]

        result = main._fetch_urls(mock_settings, mock_cli_args, mock_access_token)

        self.assertEqual(result, ["clean_url1", "clean_url2"])
        mock_url_fetcher_class.assert_called_once_with(
            mock_settings, mock_cli_args, mock_access_token
        )
        self.assertEqual(mock_clean_url.call_count, 2)

    @patch("main._process_single_url")
    @patch("time.sleep")
    def test_process_all_urls(self, mock_sleep, mock_process_single):
        """Test _process_all_urls function."""
        urls = ["url1", "url2", "url3"]
        mock_settings = Mock()
        base_save_dir = self.temp_dir
        access_token = "test_token"

        main._process_all_urls(urls, mock_settings, base_save_dir, access_token)

        # Should call _process_single_url for each URL
        self.assertEqual(mock_process_single.call_count, 3)

        # Should sleep between requests
        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_called_with(1)

    @patch("main.utils.valid_url")
    def test_process_single_url_invalid_url(self, mock_valid_url):
        """Test _process_single_url with invalid URL."""
        mock_valid_url.return_value = False
        mock_settings = Mock()

        # Should return early for invalid URL
        result = main._process_single_url(
            index=1,
            url="invalid_url",
            total=1,
            settings=mock_settings,
            base_save_dir=self.temp_dir,
            colors=["🟩"],
            access_token="",
        )

        self.assertIsNone(result)

    @patch("main._write_to_file")
    @patch("main.build_post_content")
    @patch("main.utils.generate_filename")
    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    def test_process_single_url_success(
        self,
        mock_valid_url,
        mock_download_json,
        mock_generate_filename,
        mock_build_content,
        mock_write_file,
    ):
        """Test successful processing of single URL."""
        mock_valid_url.return_value = True

        # Mock downloaded data
        mock_post_data = {
            "title": "Test Post",
            "author": "test_author",
            "subreddit_name_prefixed": "r/test",
            "created_utc": 1640995200,
        }
        mock_download_json.return_value = [
            {"data": {"children": [{"data": mock_post_data}]}},
            {"data": {"children": []}},
        ]

        # Mock filename generation
        mock_generate_filename.return_value = os.path.join(
            self.temp_dir, "test_post.md"
        )

        # Mock content building
        mock_build_content.return_value = "# Test Post Content"

        # Mock settings
        mock_settings = Mock()
        mock_settings.use_timestamped_directories = False
        mock_settings.file_format = "md"
        mock_settings.overwrite_existing_file = False

        # Process URL
        main._process_single_url(
            index=1,
            url="https://reddit.com/r/test/comments/123/post",
            total=1,
            settings=mock_settings,
            base_save_dir=self.temp_dir,
            colors=["🟩"],
            access_token="",
        )

        # Verify calls were made
        mock_download_json.assert_called_once()
        mock_generate_filename.assert_called_once()
        mock_build_content.assert_called_once()
        mock_write_file.assert_called_once()

    def test_write_to_file(self):
        """Test _write_to_file function."""
        from pathlib import Path

        test_path = Path(self.temp_dir) / "test_file.md"
        test_content = "# Test Content\n\nThis is a test file."

        main._write_to_file(test_path, test_content)

        # Verify file was created and content is correct
        self.assertTrue(test_path.exists())
        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, test_content)

    def test_write_to_file_creates_directories(self):
        """Test _write_to_file creates parent directories."""
        from pathlib import Path

        nested_path = Path(self.temp_dir) / "nested" / "dir" / "test_file.md"
        test_content = "# Test Content"

        main._write_to_file(nested_path, test_content)

        # Verify nested directories were created
        self.assertTrue(nested_path.parent.exists())
        self.assertTrue(nested_path.exists())


if __name__ == "__main__":
    unittest.main()
