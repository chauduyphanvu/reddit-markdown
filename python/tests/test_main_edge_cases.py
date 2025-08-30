import sys

"""
# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
Additional edge case tests for main.py module.
Focuses on error scenarios and complex edge cases not fully covered in test_main_integration.py.
"""

import unittest
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
import tempfile
import os
import json
import logging

import main
from .test_utils import TempDirTestCase


class TestMainEdgeCases(TempDirTestCase):
    """Additional edge case tests for main.py module."""

    @patch("main._write_to_file")
    @patch("main.build_post_content")
    @patch("main.utils.generate_filename")
    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    def test_process_single_url_empty_post_data(
        self,
        mock_valid_url,
        mock_download_json,
        mock_generate_filename,
        mock_build_content,
        mock_write_file,
    ):
        """Test _process_single_url with empty post data."""
        mock_valid_url.return_value = True
        mock_download_json.return_value = []  # Empty data

        mock_settings = Mock()
        mock_settings.use_timestamped_directories = False
        mock_settings.file_format = "md"

        result = main._process_single_url(
            index=1,
            url="https://reddit.com/r/test/comments/123/post",
            total=1,
            settings=mock_settings,
            base_save_dir=self.temp_dir,
            colors=["🟩"],
            access_token="",
        )

        self.assertFalse(result)
        # Should not proceed to generate filename or write file
        mock_generate_filename.assert_not_called()
        mock_write_file.assert_not_called()

    @patch("main._write_to_file")
    @patch("main.build_post_content")
    @patch("main.utils.generate_filename")
    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    def test_process_single_url_malformed_data_structure(
        self,
        mock_valid_url,
        mock_download_json,
        mock_generate_filename,
        mock_build_content,
        mock_write_file,
    ):
        """Test _process_single_url with malformed data structure."""
        mock_valid_url.return_value = True
        # Malformed data - missing expected structure
        mock_download_json.return_value = [
            {"wrong_key": "wrong_value"},
            {"also_wrong": "data"},
        ]

        mock_settings = Mock()

        result = main._process_single_url(
            index=1,
            url="https://reddit.com/r/test/comments/123/post",
            total=1,
            settings=mock_settings,
            base_save_dir=self.temp_dir,
            colors=["🟩"],
            access_token="",
        )

        self.assertFalse(result)
        mock_generate_filename.assert_not_called()
        mock_write_file.assert_not_called()

    @patch("main._write_to_file")
    @patch("main.build_post_content")
    @patch("main.utils.generate_filename")
    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    def test_process_single_url_html_conversion(
        self,
        mock_valid_url,
        mock_download_json,
        mock_generate_filename,
        mock_build_content,
        mock_write_file,
    ):
        """Test _process_single_url with HTML file format."""
        mock_valid_url.return_value = True

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

        mock_generate_filename.return_value = os.path.join(self.temp_dir, "test.html")
        mock_build_content.return_value = "# Test Markdown Content"

        mock_settings = Mock()
        mock_settings.use_timestamped_directories = False
        mock_settings.file_format = "html"  # HTML format
        mock_settings.overwrite_existing_file = False

        with patch("main.utils.markdown_to_html") as mock_markdown_to_html:
            mock_markdown_to_html.return_value = "<h1>Test HTML Content</h1>"

            main._process_single_url(
                index=1,
                url="https://reddit.com/r/test/comments/123/post",
                total=1,
                settings=mock_settings,
                base_save_dir=self.temp_dir,
                colors=["🟩"],
                access_token="",
            )

            mock_markdown_to_html.assert_called_once_with("# Test Markdown Content")
            mock_write_file.assert_called_once()
            # Verify HTML content was written
            call_args = mock_write_file.call_args[0]
            self.assertEqual(call_args[1], "<h1>Test HTML Content</h1>")

    @patch("main._write_to_file")
    @patch("main.build_post_content")
    @patch("main.utils.generate_filename")
    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    def test_process_single_url_missing_created_utc(
        self,
        mock_valid_url,
        mock_download_json,
        mock_generate_filename,
        mock_build_content,
        mock_write_file,
    ):
        """Test _process_single_url with missing created_utc timestamp."""
        mock_valid_url.return_value = True

        # Post data without created_utc
        mock_post_data = {
            "title": "Test Post",
            "author": "test_author",
            "subreddit_name_prefixed": "r/test",
            # Missing created_utc
        }
        mock_download_json.return_value = [
            {"data": {"children": [{"data": mock_post_data}]}},
            {"data": {"children": []}},
        ]

        mock_generate_filename.return_value = os.path.join(self.temp_dir, "test.md")
        mock_build_content.return_value = "# Test Content"

        mock_settings = Mock()
        mock_settings.use_timestamped_directories = False
        mock_settings.file_format = "md"
        mock_settings.overwrite_existing_file = False

        main._process_single_url(
            index=1,
            url="https://reddit.com/r/test/comments/123/post",
            total=1,
            settings=mock_settings,
            base_save_dir=self.temp_dir,
            colors=["🟩"],
            access_token="",
        )

        # Should still proceed normally, just with empty timestamp
        mock_generate_filename.assert_called_once()
        call_args = mock_generate_filename.call_args[1]
        self.assertEqual(call_args["post_timestamp"], "")

    def test_write_to_file_permission_error(self):
        """Test _write_to_file with permission error."""
        from pathlib import Path

        # Create a directory where we want to write a file (will cause permission error)
        problem_path = Path(self.temp_dir) / "readonly_dir"
        problem_path.mkdir()
        problem_path.chmod(0o444)  # Read-only

        file_path = problem_path / "test_file.md"
        test_content = "# Test Content"

        # This should raise a PermissionError
        with self.assertRaises(PermissionError):
            main._write_to_file(file_path, test_content)

        # Clean up
        problem_path.chmod(0o755)

    def test_write_to_file_with_unicode_content(self):
        """Test _write_to_file with Unicode content."""
        from pathlib import Path

        test_path = Path(self.temp_dir) / "unicode_test.md"
        unicode_content = "# Test with Unicode: 🚀 ñáñúñá αβγδε 中文 🎉"

        main._write_to_file(test_path, unicode_content)

        # Verify file was created with correct Unicode content
        self.assertTrue(test_path.exists())
        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, unicode_content)

    @patch("main._process_single_url")
    def test_process_all_urls_with_exception_in_single_url(self, mock_process_single):
        """Test _process_all_urls when _process_single_url raises an exception."""
        mock_process_single.side_effect = [
            None,  # First URL succeeds
            Exception("Test error"),  # Second URL fails
            None,  # Third URL succeeds
        ]

        urls = ["url1", "url2", "url3"]
        mock_settings = Mock()

        # Should not crash, but continue processing remaining URLs
        with patch("time.sleep"):  # Don't actually sleep in test
            with self.assertRaises(Exception):
                main._process_all_urls(urls, mock_settings, self.temp_dir, "")

    @patch("main.utils.resolve_save_dir")
    @patch("main._fetch_urls")
    @patch("main._parse_cli_args")
    @patch("main._load_settings")
    def test_main_with_empty_url_list(
        self, mock_load_settings, mock_parse_cli, mock_fetch_urls, mock_resolve_save_dir
    ):
        """Test main function with empty URL list."""
        mock_settings = Mock()
        mock_settings.login_on_startup = False
        mock_settings.default_save_location = self.temp_dir
        mock_load_settings.return_value = mock_settings

        mock_cli_args = Mock()
        mock_parse_cli.return_value = mock_cli_args

        mock_fetch_urls.return_value = []  # Empty URL list
        mock_resolve_save_dir.return_value = self.temp_dir

        with patch("main._process_all_urls") as mock_process:
            main.main()

            # Should still call _process_all_urls, even with empty list
            mock_process.assert_called_once_with([], mock_settings, self.temp_dir, "")

    @patch("main._write_to_file")
    @patch("main.build_post_content")
    @patch("main.utils.generate_filename")
    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    def test_process_single_url_with_case_insensitive_html_format(
        self,
        mock_valid_url,
        mock_download_json,
        mock_generate_filename,
        mock_build_content,
        mock_write_file,
    ):
        """Test _process_single_url with HTML format in different cases."""
        mock_valid_url.return_value = True

        mock_post_data = {"title": "Test", "author": "test"}
        mock_download_json.return_value = [
            {"data": {"children": [{"data": mock_post_data}]}},
            {"data": {"children": []}},
        ]

        mock_generate_filename.return_value = "test.html"
        mock_build_content.return_value = "# Test"

        # Test different cases of "html"
        for format_case in ["HTML", "Html", "hTmL"]:
            mock_settings = Mock()
            mock_settings.file_format = format_case
            mock_settings.use_timestamped_directories = False
            mock_settings.overwrite_existing_file = False

            with patch("main.utils.markdown_to_html") as mock_markdown_to_html:
                mock_markdown_to_html.return_value = "<h1>Test</h1>"

                main._process_single_url(
                    index=1,
                    url="https://reddit.com/r/test/comments/123/post",
                    total=1,
                    settings=mock_settings,
                    base_save_dir=self.temp_dir,
                    colors=["🟩"],
                    access_token="",
                )

                # Should convert to HTML regardless of case
                mock_markdown_to_html.assert_called_once()


if __name__ == "__main__":
    unittest.main()
