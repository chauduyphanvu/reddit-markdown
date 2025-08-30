"""
Comprehensive tests for url_fetcher.py module covering edge cases and error scenarios.
"""

import sys
import os
import unittest
from unittest.mock import patch, Mock, mock_open
import csv
import json
import requests

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from url_fetcher import UrlFetcher
from .test_utils import BaseTestCase, MockFactory, TestDataFixtures


class TestUrlFetcherEdgeCases(BaseTestCase):
    """Comprehensive edge case tests for UrlFetcher class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_settings = MockFactory.create_settings_mock()
        self.mock_cli_args = MockFactory.create_cli_args_mock()
        self.access_token = "test_token"

    def test_url_fetcher_init_with_no_input_and_prompting_disabled(self):
        """Test UrlFetcher initialization with no input and prompting disabled."""
        fetcher = UrlFetcher(
            self.mock_settings,
            self.mock_cli_args,
            self.access_token,
            prompt_for_input=False,
        )

        self.assertEqual(fetcher.urls, [])
        self.assertEqual(fetcher.access_token, self.access_token)

    @patch("builtins.input", side_effect=["demo"])
    def test_url_fetcher_demo_mode(self, mock_input):
        """Test demo mode input handling."""
        fetcher = UrlFetcher(self.mock_settings, self.mock_cli_args, self.access_token)

        expected_demo_url = "https://www.reddit.com/r/pcmasterrace/comments/101kjyq/my_dad_has_been_playing_civilization_almost_daily/"
        self.assertEqual(fetcher.urls, [expected_demo_url])

    @patch("url_fetcher.UrlFetcher._fetch_posts_from_sub")
    @patch("builtins.input", side_effect=["surprise"])
    def test_url_fetcher_surprise_mode(self, mock_input, mock_fetch_posts):
        """Test surprise mode with random post selection."""
        mock_fetch_posts.return_value = [
            "https://reddit.com/r/popular/comments/123/random_post"
        ]

        fetcher = UrlFetcher(self.mock_settings, self.mock_cli_args, self.access_token)

        mock_fetch_posts.assert_called_once_with("r/popular", pick_random=True)
        self.assertEqual(
            fetcher.urls, ["https://reddit.com/r/popular/comments/123/random_post"]
        )

    @patch("url_fetcher.UrlFetcher._get_subreddit_posts")
    @patch("builtins.input", side_effect=["r/python"])
    def test_url_fetcher_subreddit_mode(self, mock_input, mock_get_subreddit_posts):
        """Test subreddit mode input handling."""
        mock_get_subreddit_posts.return_value = [
            "https://reddit.com/r/python/comments/123/post1"
        ]

        fetcher = UrlFetcher(self.mock_settings, self.mock_cli_args, self.access_token)

        mock_get_subreddit_posts.assert_called_once_with("r/python", best=True)
        self.assertEqual(
            fetcher.urls, ["https://reddit.com/r/python/comments/123/post1"]
        )

    @patch(
        "builtins.input",
        side_effect=[
            "https://reddit.com/r/test/comments/1/post1, https://reddit.com/r/test/comments/2/post2"
        ],
    )
    def test_url_fetcher_multiple_direct_urls(self, mock_input):
        """Test direct URL input with multiple URLs."""
        fetcher = UrlFetcher(self.mock_settings, self.mock_cli_args, self.access_token)

        expected_urls = [
            "https://reddit.com/r/test/comments/1/post1",
            "https://reddit.com/r/test/comments/2/post2",
        ]
        self.assertEqual(fetcher.urls, expected_urls)

    @patch(
        "builtins.input",
        side_effect=["", "https://reddit.com/r/test/comments/123/post"],
    )
    def test_url_fetcher_empty_input_retry(self, mock_input):
        """Test handling of empty input with retry."""
        fetcher = UrlFetcher(self.mock_settings, self.mock_cli_args, self.access_token)

        self.assertEqual(fetcher.urls, ["https://reddit.com/r/test/comments/123/post"])
        self.assertEqual(mock_input.call_count, 2)

    def test_urls_from_file_csv_format(self):
        """Test reading URLs from CSV file."""
        csv_content = "https://reddit.com/r/test/comments/1/post1,https://reddit.com/r/test/comments/2/post2\n"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            with patch("os.path.isfile", return_value=True):
                fetcher = UrlFetcher(
                    self.mock_settings,
                    MockFactory.create_cli_args_mock(src_files=["test.csv"]),
                    self.access_token,
                    prompt_for_input=False,
                )

        expected_urls = [
            "https://reddit.com/r/test/comments/1/post1",
            "https://reddit.com/r/test/comments/2/post2",
        ]
        self.assertEqual(fetcher.urls, expected_urls)

    def test_urls_from_file_multirow_csv(self):
        """Test reading URLs from multi-row CSV file."""
        csv_content = """https://reddit.com/r/test/comments/1/post1,https://reddit.com/r/test/comments/2/post2
https://reddit.com/r/test/comments/3/post3
"https://reddit.com/r/test/comments/4/post4","https://reddit.com/r/test/comments/5/post5"
"""

        with patch("builtins.open", mock_open(read_data=csv_content)):
            with patch("os.path.isfile", return_value=True):
                fetcher = UrlFetcher(
                    self.mock_settings,
                    MockFactory.create_cli_args_mock(src_files=["test.csv"]),
                    self.access_token,
                    prompt_for_input=False,
                )

        expected_urls = [
            "https://reddit.com/r/test/comments/1/post1",
            "https://reddit.com/r/test/comments/2/post2",
            "https://reddit.com/r/test/comments/3/post3",
            "https://reddit.com/r/test/comments/4/post4",
            "https://reddit.com/r/test/comments/5/post5",
        ]
        self.assertEqual(fetcher.urls, expected_urls)

    def test_urls_from_file_missing_file(self):
        """Test handling of missing source file."""
        with patch("os.path.isfile", return_value=False):
            fetcher = UrlFetcher(
                self.mock_settings,
                MockFactory.create_cli_args_mock(src_files=["missing.csv"]),
                self.access_token,
                prompt_for_input=False,
            )

        self.assertEqual(fetcher.urls, [])

    def test_urls_from_file_read_error(self):
        """Test handling of file read errors."""
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            with patch("os.path.isfile", return_value=True):
                fetcher = UrlFetcher(
                    self.mock_settings,
                    MockFactory.create_cli_args_mock(src_files=["protected.csv"]),
                    self.access_token,
                    prompt_for_input=False,
                )

        self.assertEqual(fetcher.urls, [])

    def test_urls_from_file_with_empty_rows(self):
        """Test reading CSV file with empty rows and cells."""
        csv_content = """https://reddit.com/r/test/comments/1/post1,,
,https://reddit.com/r/test/comments/2/post2,
,,
https://reddit.com/r/test/comments/3/post3"""

        with patch("builtins.open", mock_open(read_data=csv_content)):
            with patch("os.path.isfile", return_value=True):
                fetcher = UrlFetcher(
                    self.mock_settings,
                    MockFactory.create_cli_args_mock(src_files=["test.csv"]),
                    self.access_token,
                    prompt_for_input=False,
                )

        expected_urls = [
            "https://reddit.com/r/test/comments/1/post1",
            "https://reddit.com/r/test/comments/2/post2",
            "https://reddit.com/r/test/comments/3/post3",
        ]
        self.assertEqual(fetcher.urls, expected_urls)

    @patch("url_fetcher.UrlFetcher._fetch_posts_from_sub")
    def test_subreddit_posts_collection(self, mock_fetch_posts):
        """Test collection of posts from subreddits."""
        mock_fetch_posts.return_value = [
            "https://reddit.com/r/python/comments/1/post1",
            "https://reddit.com/r/python/comments/2/post2",
        ]

        fetcher = UrlFetcher(
            self.mock_settings,
            MockFactory.create_cli_args_mock(subs=["r/python"]),
            self.access_token,
            prompt_for_input=False,
        )

        mock_fetch_posts.assert_called_once_with(
            "r/python", pick_random=False, best=True
        )
        expected_urls = [
            "https://reddit.com/r/python/comments/1/post1",
            "https://reddit.com/r/python/comments/2/post2",
        ]
        self.assertEqual(fetcher.urls, expected_urls)

    @patch("url_fetcher.UrlFetcher._fetch_posts_from_sub")
    def test_multireddit_expansion(self, mock_fetch_posts):
        """Test multireddit expansion from settings."""
        mock_fetch_posts.side_effect = [
            ["https://reddit.com/r/python/comments/1/post1"],
            ["https://reddit.com/r/programming/comments/1/post2"],
        ]

        self.mock_settings.multi_reddits = {
            "m/programming": ["r/python", "r/programming"]
        }

        fetcher = UrlFetcher(
            self.mock_settings,
            MockFactory.create_cli_args_mock(multis=["m/programming"]),
            self.access_token,
            prompt_for_input=False,
        )

        self.assertEqual(mock_fetch_posts.call_count, 2)
        expected_urls = [
            "https://reddit.com/r/python/comments/1/post1",
            "https://reddit.com/r/programming/comments/1/post2",
        ]
        self.assertEqual(fetcher.urls, expected_urls)

    @patch("url_fetcher.UrlFetcher._fetch_posts_from_sub")
    def test_multireddit_not_found_in_settings(self, mock_fetch_posts):
        """Test handling of multireddit not found in settings."""
        fetcher = UrlFetcher(
            self.mock_settings,
            MockFactory.create_cli_args_mock(multis=["m/nonexistent"]),
            self.access_token,
            prompt_for_input=False,
        )

        mock_fetch_posts.assert_not_called()
        self.assertEqual(fetcher.urls, [])

    @patch("builtins.input", side_effect=["m/programming"])
    @patch("url_fetcher.UrlFetcher._get_subreddit_posts")
    def test_multireddit_mode_input(self, mock_get_subreddit_posts, mock_input):
        """Test multireddit mode from user input."""
        mock_get_subreddit_posts.return_value = [
            "https://reddit.com/r/python/comments/1/post1"
        ]

        self.mock_settings.multi_reddits = {"m/programming": ["r/python"]}

        fetcher = UrlFetcher(self.mock_settings, self.mock_cli_args, self.access_token)

        mock_get_subreddit_posts.assert_called_once_with("r/python", best=True)
        self.assertEqual(fetcher.urls, ["https://reddit.com/r/python/comments/1/post1"])

    @patch("builtins.input", side_effect=["m/nonexistent"])
    def test_multireddit_mode_input_not_found(self, mock_input):
        """Test multireddit mode with nonexistent multireddit."""
        fetcher = UrlFetcher(self.mock_settings, self.mock_cli_args, self.access_token)

        self.assertEqual(fetcher.urls, [])

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_success(self, mock_download_json):
        """Test successful fetching of posts from subreddit."""
        mock_download_json.return_value = {
            "data": {
                "children": [
                    {"data": {"permalink": "/r/python/comments/1/post1/"}},
                    {"data": {"permalink": "/r/python/comments/2/post2/"}},
                ]
            }
        }

        fetcher = UrlFetcher(
            self.mock_settings,
            self.mock_cli_args,
            self.access_token,
            prompt_for_input=False,
        )
        result = fetcher._fetch_posts_from_sub("r/python")

        expected_urls = [
            "https://www.reddit.com/r/python/comments/1/post1/",
            "https://www.reddit.com/r/python/comments/2/post2/",
        ]
        self.assertEqual(result, expected_urls)

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_with_best_endpoint(self, mock_download_json):
        """Test fetching posts using /best endpoint."""
        mock_download_json.return_value = {
            "data": {
                "children": [{"data": {"permalink": "/r/python/comments/1/best_post/"}}]
            }
        }

        fetcher = UrlFetcher(
            self.mock_settings,
            self.mock_cli_args,
            self.access_token,
            prompt_for_input=False,
        )
        result = fetcher._fetch_posts_from_sub("r/python", best=True)

        # Verify the correct URL was called with /best
        mock_download_json.assert_called_once()
        called_url = mock_download_json.call_args[0][0]
        self.assertTrue(called_url.endswith("/r/python/best"))

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_pick_random(self, mock_download_json):
        """Test picking random post from subreddit."""
        mock_download_json.return_value = {
            "data": {
                "children": [
                    {"data": {"permalink": "/r/python/comments/1/post1/"}},
                    {"data": {"permalink": "/r/python/comments/2/post2/"}},
                    {"data": {"permalink": "/r/python/comments/3/post3/"}},
                ]
            }
        }

        fetcher = UrlFetcher(
            self.mock_settings,
            self.mock_cli_args,
            self.access_token,
            prompt_for_input=False,
        )
        result = fetcher._fetch_posts_from_sub("r/python", pick_random=True)

        # Should return exactly one URL
        self.assertEqual(len(result), 1)
        self.assertTrue(
            result[0].startswith("https://www.reddit.com/r/python/comments/")
        )

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_no_data(self, mock_download_json):
        """Test handling when subreddit returns no data."""
        mock_download_json.return_value = None

        fetcher = UrlFetcher(
            self.mock_settings,
            self.mock_cli_args,
            self.access_token,
            prompt_for_input=False,
        )
        result = fetcher._fetch_posts_from_sub("r/nonexistent")

        self.assertEqual(result, [])

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_malformed_data(self, mock_download_json):
        """Test handling of malformed subreddit data."""
        mock_download_json.return_value = {"invalid_structure": "missing_data_key"}

        fetcher = UrlFetcher(
            self.mock_settings,
            self.mock_cli_args,
            self.access_token,
            prompt_for_input=False,
        )
        result = fetcher._fetch_posts_from_sub("r/python")

        self.assertEqual(result, [])

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_empty_children(self, mock_download_json):
        """Test handling when subreddit has no posts."""
        mock_download_json.return_value = {"data": {"children": []}}

        fetcher = UrlFetcher(
            self.mock_settings,
            self.mock_cli_args,
            self.access_token,
            prompt_for_input=False,
        )
        result = fetcher._fetch_posts_from_sub("r/python")

        self.assertEqual(result, [])

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_missing_permalink(self, mock_download_json):
        """Test handling of posts without permalink."""
        mock_download_json.return_value = {
            "data": {
                "children": [
                    {"data": {}},  # Missing permalink
                    {"data": {"permalink": "/r/python/comments/1/post1/"}},
                ]
            }
        }

        fetcher = UrlFetcher(
            self.mock_settings,
            self.mock_cli_args,
            self.access_token,
            prompt_for_input=False,
        )
        result = fetcher._fetch_posts_from_sub("r/python")

        # Should only return the post with valid permalink
        expected_urls = ["https://www.reddit.com/r/python/comments/1/post1/"]
        self.assertEqual(result, expected_urls)

    def test_fetch_posts_oauth_vs_regular_base_url(self):
        """Test that correct base URL is used based on access token."""
        with patch("url_fetcher.UrlFetcher._download_post_json") as mock_download_json:
            mock_download_json.return_value = {"data": {"children": []}}

            # Test with access token
            fetcher_with_token = UrlFetcher(
                self.mock_settings,
                self.mock_cli_args,
                "token123",
                prompt_for_input=False,
            )
            fetcher_with_token._fetch_posts_from_sub("r/python")

            called_url = mock_download_json.call_args[0][0]
            self.assertTrue(called_url.startswith("https://oauth.reddit.com"))

            mock_download_json.reset_mock()

            # Test without access token
            fetcher_without_token = UrlFetcher(
                self.mock_settings, self.mock_cli_args, "", prompt_for_input=False
            )
            fetcher_without_token._fetch_posts_from_sub("r/python")

            called_url = mock_download_json.call_args[0][0]
            self.assertTrue(called_url.startswith("https://www.reddit.com"))

    def test_subreddit_string_normalization(self):
        """Test that subreddit strings are normalized correctly."""
        with patch("url_fetcher.UrlFetcher._download_post_json") as mock_download_json:
            mock_download_json.return_value = {"data": {"children": []}}

            fetcher = UrlFetcher(
                self.mock_settings,
                self.mock_cli_args,
                self.access_token,
                prompt_for_input=False,
            )

            # Test with leading slash
            fetcher._fetch_posts_from_sub("/r/python")
            called_url = mock_download_json.call_args[0][0]
            self.assertIn("/r/python", called_url)
            self.assertNotIn("//r/python", called_url)

    def test_combined_url_sources(self):
        """Test URL collection from multiple sources simultaneously."""
        csv_content = "https://reddit.com/r/test/comments/1/file_post"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            with patch("os.path.isfile", return_value=True):
                with patch(
                    "url_fetcher.UrlFetcher._fetch_posts_from_sub"
                ) as mock_fetch:
                    mock_fetch.return_value = [
                        "https://reddit.com/r/python/comments/1/sub_post"
                    ]

                    self.mock_settings.multi_reddits = {"m/test": ["r/programming"]}

                    cli_args = MockFactory.create_cli_args_mock(
                        urls=["https://reddit.com/r/test/comments/1/direct_url"],
                        src_files=["test.csv"],
                        subs=["r/python"],
                        multis=["m/test"],
                    )

                    fetcher = UrlFetcher(
                        self.mock_settings,
                        cli_args,
                        self.access_token,
                        prompt_for_input=False,
                    )

                    # Should have URLs from all sources
                    self.assertIn(
                        "https://reddit.com/r/test/comments/1/direct_url", fetcher.urls
                    )
                    self.assertIn(
                        "https://reddit.com/r/test/comments/1/file_post", fetcher.urls
                    )
                    self.assertIn(
                        "https://reddit.com/r/python/comments/1/sub_post", fetcher.urls
                    )

                    # Should have called fetch twice (once for r/python, once for r/programming)
                    self.assertEqual(mock_fetch.call_count, 2)


if __name__ == "__main__":
    unittest.main()
