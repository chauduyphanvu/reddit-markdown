"""
Streamlined integration tests focusing on essential behavior and workflows.
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

import reddit_utils as utils
from url_fetcher import UrlFetcher
from post_renderer import build_post_content
from filters import apply_filter
from settings import Settings


class TestEssentialIntegration(unittest.TestCase):
    """Test essential integration between modules."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_settings_loads_from_valid_json_file(self):
        """Settings should load successfully from valid JSON file."""
        settings_data = {
            "version": "1.0.0",
            "file_format": "md",
            "show_upvotes": True,
        }

        settings_file = os.path.join(self.temp_dir, "settings.json")
        with open(settings_file, "w") as f:
            json.dump(settings_data, f)

        settings = Settings(settings_file)
        self.assertEqual(settings.file_format, "md")

    def test_settings_provides_defaults_for_missing_values(self):
        """Settings should provide defaults when values are missing."""
        minimal_settings = {"version": "1.0.0"}

        settings_file = os.path.join(self.temp_dir, "settings.json")
        with open(settings_file, "w") as f:
            json.dump(minimal_settings, f)

        settings = Settings(settings_file)
        self.assertEqual(settings.show_upvotes, True)  # Default value

    def test_url_fetcher_collects_direct_urls(self):
        """URL fetcher should collect direct URLs provided."""
        mock_settings = Mock()
        mock_settings.multi_reddits = {}

        mock_args = Mock()
        mock_args.urls = ["https://reddit.com/r/test/comments/123/post"]
        mock_args.src_files = []
        mock_args.subs = []
        mock_args.multis = []

        fetcher = UrlFetcher(mock_settings, mock_args, prompt_for_input=False)
        self.assertIn("https://reddit.com/r/test/comments/123/post", fetcher.urls)

    def test_url_fetcher_handles_empty_input_gracefully(self):
        """URL fetcher should handle empty input without errors."""
        mock_settings = Mock()
        mock_settings.multi_reddits = {}

        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = []
        mock_args.multis = []

        fetcher = UrlFetcher(mock_settings, mock_args, prompt_for_input=False)
        self.assertEqual(len(fetcher.urls), 0)

    def test_post_renderer_produces_markdown_output(self):
        """Post renderer should produce markdown output from post data."""
        post_data = {
            "title": "Test Post",
            "author": "test_author",
            "subreddit_name_prefixed": "r/test",
            "selftext": "Test content",
            "ups": 100,
            "created_utc": 1640995200,
            "locked": False,
            "url": "https://reddit.com/r/test/comments/123/test",
        }

        mock_settings = Mock()
        mock_settings.show_upvotes = True
        mock_settings.show_timestamp = True
        mock_settings.show_auto_mod_comment = False
        mock_settings.enable_media_downloads = False
        mock_settings.apply_comment_filters = False
        mock_settings.reply_depth_color_indicators = True
        mock_settings.line_break_between_parent_replies = True
        mock_settings.filtered_keywords = []
        mock_settings.filtered_authors = []
        mock_settings.filtered_regexes = []
        mock_settings.filtered_min_upvotes = 0
        mock_settings.filtered_message = "[FILTERED]"

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=post_data,
                replies_data=[],
                settings=mock_settings,
                colors=["🟩"],
                url="https://reddit.com/r/test/comments/123/test",
                target_path=tmp.name,
            )

        self.assertIn("Test Post", content)

    def test_post_renderer_includes_post_metadata(self):
        """Post renderer should include post metadata in output."""
        post_data = {
            "title": "Test Post",
            "author": "test_author",
            "subreddit_name_prefixed": "r/test",
            "selftext": "Test content",
            "ups": 100,
            "created_utc": 1640995200,
            "locked": False,
            "url": "https://reddit.com/r/test/comments/123/test",
        }

        mock_settings = Mock()
        mock_settings.show_upvotes = True
        mock_settings.show_timestamp = True
        mock_settings.show_auto_mod_comment = False
        mock_settings.enable_media_downloads = False
        mock_settings.apply_comment_filters = False
        mock_settings.reply_depth_color_indicators = True
        mock_settings.line_break_between_parent_replies = True
        mock_settings.filtered_keywords = []
        mock_settings.filtered_authors = []
        mock_settings.filtered_regexes = []
        mock_settings.filtered_min_upvotes = 0
        mock_settings.filtered_message = "[FILTERED]"

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=post_data,
                replies_data=[],
                settings=mock_settings,
                colors=["🟩"],
                url="https://reddit.com/r/test/comments/123/test",
                target_path=tmp.name,
            )

        self.assertIn("test_author", content)

    def test_filters_apply_keyword_filtering(self):
        """Filters should apply keyword filtering to content."""
        result = apply_filter(
            author="user",
            text="This contains spam content",
            upvotes=10,
            filtered_keywords=["spam"],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[],
            filtered_message="[FILTERED]",
        )
        self.assertEqual(result, "[FILTERED]")

    def test_filters_allow_content_without_keywords(self):
        """Filters should allow content that doesn't contain filtered keywords."""
        result = apply_filter(
            author="user",
            text="This is clean content",
            upvotes=10,
            filtered_keywords=["spam"],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[],
            filtered_message="[FILTERED]",
        )
        self.assertEqual(result, "This is clean content")

    @patch("requests.get")
    def test_reddit_utils_downloads_json_data(self, mock_get):
        """Reddit utils should download and parse JSON data."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = utils.download_post_json("https://reddit.com/r/test/comments/123/post")
        self.assertEqual(result, {"data": "test"})

    @patch("requests.get")
    def test_reddit_utils_handles_network_errors_gracefully(self, mock_get):
        """Reddit utils should handle network errors gracefully."""
        import requests

        # Clear cache to ensure fresh request
        utils._json_cache.clear()
        utils._cache_timestamps.clear()

        mock_get.side_effect = requests.ConnectionError("Network error")

        result = utils.download_post_json("https://reddit.com/r/test/comments/123/post")
        self.assertIsNone(result)

    def test_reddit_utils_validates_urls_correctly(self):
        """Reddit utils should validate URLs correctly."""
        valid_url = "https://www.reddit.com/r/python/comments/abc123/test/"
        invalid_url = "https://google.com/search"

        self.assertTrue(utils.valid_url(valid_url))

    def test_reddit_utils_rejects_invalid_urls(self):
        """Reddit utils should reject invalid URLs."""
        invalid_url = "https://google.com/search"

        self.assertFalse(utils.valid_url(invalid_url))

    def test_reddit_utils_cleans_urls_properly(self):
        """Reddit utils should clean URLs by removing tracking parameters."""
        dirty_url = "https://reddit.com/r/test/comments/123?utm_source=share"
        expected_clean_url = "https://reddit.com/r/test/comments/123"

        result = utils.clean_url(dirty_url)
        self.assertEqual(result, expected_clean_url)

    def test_reddit_utils_preserves_clean_urls(self):
        """Reddit utils should preserve URLs that are already clean."""
        clean_url = "https://reddit.com/r/test/comments/123"

        result = utils.clean_url(clean_url)
        self.assertEqual(result, clean_url)


class TestWorkflowIntegration(unittest.TestCase):
    """Test integration of complete workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_filename_generation_creates_safe_paths(self):
        """Filename generation should create safe file paths."""
        filename = utils.generate_filename(
            base_dir=self.temp_dir,
            url="https://reddit.com/r/test/comments/123/test_post/",
            subreddit="r/test",
            use_timestamped_dirs=False,
            post_timestamp="2024-01-01 12:00:00",
            file_format="md",
            overwrite=False,
        )

        self.assertTrue(filename.endswith(".md"))

    def test_filename_generation_creates_paths_within_base_dir(self):
        """Filename generation should create paths within the base directory."""
        filename = utils.generate_filename(
            base_dir=self.temp_dir,
            url="https://reddit.com/r/test/comments/123/test_post/",
            subreddit="r/test",
            use_timestamped_dirs=False,
            post_timestamp="2024-01-01 12:00:00",
            file_format="md",
            overwrite=False,
        )

        # Handle macOS /private prefix
        import os

        tmpdir_real = os.path.realpath(self.temp_dir)
        filename_real = os.path.realpath(filename)
        self.assertTrue(filename_real.startswith(tmpdir_real))

    def test_directory_resolution_returns_provided_path(self):
        """Directory resolution should return the provided path."""
        test_path = os.path.join(self.temp_dir, "test_dir")

        resolved = utils.resolve_save_dir(test_path)
        self.assertEqual(resolved, test_path)

    def test_markdown_conversion_produces_html(self):
        """Markdown conversion should produce HTML output."""
        markdown = "# Title\n\n**Bold** text"
        html = utils.markdown_to_html(markdown)

        self.assertIn("<h1>", html.lower())

    def test_markdown_conversion_handles_formatting(self):
        """Markdown conversion should handle bold formatting."""
        markdown = "# Title\n\n**Bold** text"
        html = utils.markdown_to_html(markdown)

        self.assertIn("<strong>", html.lower())

    @patch("requests.get")
    def test_performance_configuration_applies_settings(self, mock_get):
        """Performance configuration should apply settings successfully."""
        mock_settings = Mock()
        mock_settings.rate_limit_requests_per_minute = 60
        mock_settings.cache_ttl_seconds = 300
        mock_settings.max_cache_entries = 100

        # Should not raise exception
        utils.configure_performance(mock_settings)

        # Test that configuration allows requests
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = utils.download_post_json("https://reddit.com/r/test/comments/123/post")
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
