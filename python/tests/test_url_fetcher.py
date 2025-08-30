import sys
import unittest
from unittest.mock import patch, Mock, mock_open, MagicMock
import json
import tempfile
import os
import logging
import requests

from url_fetcher import UrlFetcher


# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class MockSettings:
    """Mock Settings class for testing."""

    def __init__(self):
        self.multi_reddits = {"m/test": ["r/python", "r/programming"], "m/empty": []}


class MockCliArgs:
    """Mock CLI Args class for testing."""

    def __init__(self, urls=None, src_files=None, subs=None, multis=None):
        self.urls = urls or []
        self.src_files = src_files or []
        self.subs = subs or []
        self.multis = multis or []


class TestUrlFetcher(unittest.TestCase):
    """Comprehensive test suite for url_fetcher.py module."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = MockSettings()
        self.access_token = "test_token"

        # Clear caches to ensure test isolation
        import reddit_utils

        reddit_utils._json_cache.clear()
        reddit_utils._cache_timestamps.clear()

        # Disable logging during tests
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Clean up after tests."""
        logging.disable(logging.NOTSET)

    def test_init_with_direct_urls(self):
        """Test UrlFetcher initialization with direct URLs."""
        cli_args = MockCliArgs(
            urls=["https://reddit.com/r/test/1", "https://reddit.com/r/test/2"]
        )

        fetcher = UrlFetcher(
            self.mock_settings, cli_args, self.access_token, prompt_for_input=False
        )

        self.assertEqual(len(fetcher.urls), 2)
        self.assertIn("https://reddit.com/r/test/1", fetcher.urls)
        self.assertIn("https://reddit.com/r/test/2", fetcher.urls)

    @patch("builtins.input", return_value="https://reddit.com/r/test/comments/123/post")
    def test_init_prompts_for_input_when_no_args(self, mock_input):
        """Test UrlFetcher prompts for input when no CLI args provided."""
        cli_args = MockCliArgs()

        fetcher = UrlFetcher(self.mock_settings, cli_args)

        self.assertEqual(len(fetcher.urls), 1)
        self.assertEqual(fetcher.urls[0], "https://reddit.com/r/test/comments/123/post")

    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", mock_open(read_data="url1,url2\nurl3,url4"))
    def test_urls_from_file_success(self, mock_isfile):
        """Test reading URLs from file successfully."""
        cli_args = MockCliArgs(src_files=["test_file.csv"])

        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        self.assertEqual(len(fetcher.urls), 4)
        self.assertIn("url1", fetcher.urls)
        self.assertIn("url2", fetcher.urls)
        self.assertIn("url3", fetcher.urls)
        self.assertIn("url4", fetcher.urls)

    @patch("os.path.isfile", return_value=False)
    def test_urls_from_file_not_found(self, mock_isfile):
        """Test handling of missing file."""
        cli_args = MockCliArgs(src_files=["missing_file.csv"])

        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        self.assertEqual(len(fetcher.urls), 0)

    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_urls_from_file_read_error(self, mock_open, mock_isfile):
        """Test handling file read errors."""
        cli_args = MockCliArgs(src_files=["protected_file.csv"])

        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        self.assertEqual(len(fetcher.urls), 0)

    @patch("url_fetcher.UrlFetcher._get_subreddit_posts")
    def test_subreddit_collection(self, mock_get_posts):
        """Test collection of URLs from subreddits."""
        mock_get_posts.return_value = [
            "https://reddit.com/r/python/1",
            "https://reddit.com/r/python/2",
        ]
        cli_args = MockCliArgs(subs=["r/python"])

        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        self.assertEqual(len(fetcher.urls), 2)
        mock_get_posts.assert_called_once_with("r/python")

    @patch("url_fetcher.UrlFetcher._get_subreddit_posts")
    def test_multireddit_collection(self, mock_get_posts):
        """Test collection of URLs from multireddits."""
        mock_get_posts.side_effect = [
            ["https://reddit.com/r/python/1"],
            ["https://reddit.com/r/programming/1"],
        ]
        cli_args = MockCliArgs(multis=["m/test"])

        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        self.assertEqual(len(fetcher.urls), 2)
        self.assertEqual(mock_get_posts.call_count, 2)

    def test_multireddit_collection_not_found(self):
        """Test multireddit collection when multireddit is not in settings."""
        cli_args = MockCliArgs(multis=["m/nonexistent"])

        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        self.assertEqual(len(fetcher.urls), 0)

    @patch("builtins.input", side_effect=["", "https://reddit.com/r/test/1"])
    def test_prompt_for_input_retries_empty_input(self, mock_input):
        """Test prompt retries when user provides empty input."""
        cli_args = MockCliArgs()

        fetcher = UrlFetcher(self.mock_settings, cli_args)

        self.assertEqual(len(fetcher.urls), 1)
        self.assertEqual(mock_input.call_count, 2)

    @patch("builtins.input", return_value="demo")
    def test_interpret_input_demo_mode(self, mock_input):
        """Test demo mode input interpretation."""
        cli_args = MockCliArgs()

        fetcher = UrlFetcher(self.mock_settings, cli_args)

        self.assertEqual(len(fetcher.urls), 1)
        self.assertIn("pcmasterrace", fetcher.urls[0])

    @patch("builtins.input", return_value="surprise")
    @patch("url_fetcher.UrlFetcher._fetch_posts_from_sub")
    def test_interpret_input_surprise_mode(self, mock_fetch_posts, mock_input):
        """Test surprise mode input interpretation."""
        mock_fetch_posts.return_value = ["https://reddit.com/r/popular/1"]
        cli_args = MockCliArgs()

        fetcher = UrlFetcher(self.mock_settings, cli_args)

        mock_fetch_posts.assert_called_once_with("r/popular", pick_random=True)

    @patch("builtins.input", return_value="r/python")
    @patch("url_fetcher.UrlFetcher._get_subreddit_posts")
    def test_interpret_input_subreddit_mode(self, mock_get_posts, mock_input):
        """Test subreddit mode input interpretation."""
        mock_get_posts.return_value = ["https://reddit.com/r/python/1"]
        cli_args = MockCliArgs()

        fetcher = UrlFetcher(self.mock_settings, cli_args)

        mock_get_posts.assert_called_once_with("r/python", best=True)

    @patch("builtins.input", return_value="m/test")
    @patch("url_fetcher.UrlFetcher._get_subreddit_posts")
    def test_interpret_input_multireddit_mode(self, mock_get_posts, mock_input):
        """Test multireddit mode input interpretation."""
        mock_get_posts.side_effect = [
            ["https://reddit.com/r/python/1"],
            ["https://reddit.com/r/programming/1"],
        ]
        cli_args = MockCliArgs()

        fetcher = UrlFetcher(self.mock_settings, cli_args)

        self.assertEqual(mock_get_posts.call_count, 2)
        mock_get_posts.assert_any_call("r/python", best=True)
        mock_get_posts.assert_any_call("r/programming", best=True)

    @patch("builtins.input", return_value="url1,url2, url3 ")
    def test_interpret_input_direct_urls(self, mock_input):
        """Test direct URL input interpretation."""
        cli_args = MockCliArgs()

        fetcher = UrlFetcher(self.mock_settings, cli_args)

        self.assertEqual(len(fetcher.urls), 3)
        self.assertIn("url1", fetcher.urls)
        self.assertIn("url2", fetcher.urls)
        self.assertIn("url3", fetcher.urls)

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_success(self, mock_download):
        """Test successful fetching of posts from subreddit."""
        mock_data = {
            "data": {
                "children": [
                    {"data": {"permalink": "/r/python/comments/1/test1"}},
                    {"data": {"permalink": "/r/python/comments/2/test2"}},
                ]
            }
        }
        mock_download.return_value = mock_data

        cli_args = MockCliArgs()
        fetcher = UrlFetcher(
            self.mock_settings, cli_args, self.access_token, prompt_for_input=False
        )

        # Test the internal method directly
        result = fetcher._fetch_posts_from_sub("r/python")

        self.assertEqual(len(result), 2)
        self.assertIn("https://www.reddit.com/r/python/comments/1/test1", result)
        self.assertIn("https://www.reddit.com/r/python/comments/2/test2", result)

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_with_best_endpoint(self, mock_download):
        """Test fetching posts with best endpoint."""
        mock_data = {
            "data": {
                "children": [{"data": {"permalink": "/r/python/comments/1/test1"}}]
            }
        }
        mock_download.return_value = mock_data

        cli_args = MockCliArgs()
        fetcher = UrlFetcher(
            self.mock_settings, cli_args, self.access_token, prompt_for_input=False
        )

        result = fetcher._fetch_posts_from_sub("r/python", best=True)

        # Should call with /best endpoint
        mock_download.assert_called_with("https://oauth.reddit.com/r/python/best")

    @patch("url_fetcher.UrlFetcher._download_post_json")
    @patch("random.choice")
    def test_fetch_posts_from_sub_pick_random(self, mock_choice, mock_download):
        """Test picking random post from subreddit."""
        mock_data = {
            "data": {
                "children": [
                    {"data": {"permalink": "/r/python/comments/1/test1"}},
                    {"data": {"permalink": "/r/python/comments/2/test2"}},
                ]
            }
        }
        mock_download.return_value = mock_data
        mock_choice.return_value = "https://www.reddit.com/r/python/comments/1/test1"

        cli_args = MockCliArgs()
        fetcher = UrlFetcher(
            self.mock_settings, cli_args, self.access_token, prompt_for_input=False
        )

        result = fetcher._fetch_posts_from_sub("r/python", pick_random=True)

        self.assertEqual(len(result), 1)
        mock_choice.assert_called_once()

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_no_data(self, mock_download):
        """Test fetching posts when no data is returned."""
        mock_download.return_value = None

        cli_args = MockCliArgs()
        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        result = fetcher._fetch_posts_from_sub("r/nonexistent")

        self.assertEqual(len(result), 0)

    @patch("url_fetcher.UrlFetcher._download_post_json")
    def test_fetch_posts_from_sub_invalid_data(self, mock_download):
        """Test fetching posts with invalid data structure."""
        mock_download.return_value = {"invalid": "structure"}

        cli_args = MockCliArgs()
        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        result = fetcher._fetch_posts_from_sub("r/test")

        self.assertEqual(len(result), 0)

    @patch("requests.get")
    def test_download_post_json_success(self, mock_get):
        """Test successful JSON download."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        cli_args = MockCliArgs()
        fetcher = UrlFetcher(
            self.mock_settings, cli_args, self.access_token, prompt_for_input=False
        )

        result = fetcher._download_post_json("https://reddit.com/r/test")

        self.assertEqual(result, {"data": "test"})
        mock_get.assert_called_with(
            "https://oauth.reddit.com/r/test.json",
            headers={
                "User-Agent": "RedditMarkdownConverter/1.0 (Safe Download Bot)",
                "Authorization": "bearer test_token",
            },
            timeout=30,
        )

    @patch("requests.get")
    def test_download_post_json_without_token(self, mock_get):
        """Test JSON download without access token."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        cli_args = MockCliArgs()
        fetcher = UrlFetcher(
            self.mock_settings, cli_args, prompt_for_input=False
        )  # No access token

        result = fetcher._download_post_json("https://reddit.com/r/test")

        self.assertEqual(result, {"data": "test"})
        mock_get.assert_called_with(
            "https://reddit.com/r/test.json",
            headers={"User-Agent": "RedditMarkdownConverter/1.0 (Safe Download Bot)"},
            timeout=30,
        )

    @patch("requests.get")
    @patch("builtins.input", return_value="https://test.com")
    def test_download_post_json_already_json(self, mock_input, mock_get):
        """Test JSON download when URL already has .json extension."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        cli_args = MockCliArgs()
        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        result = fetcher._download_post_json("https://reddit.com/r/test.json")

        self.assertEqual(result, {"data": "test"})
        mock_get.assert_called_with(
            "https://reddit.com/r/test.json",
            headers={"User-Agent": "RedditMarkdownConverter/1.0 (Safe Download Bot)"},
            timeout=30,
        )

    @patch("requests.get")
    @patch("builtins.input", return_value="https://test.com")
    def test_download_post_json_network_error(self, mock_input, mock_get):
        """Test JSON download with network error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        cli_args = MockCliArgs()
        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        result = fetcher._download_post_json("https://reddit.com/r/test")

        self.assertIsNone(result)

    @patch("requests.get")
    @patch("builtins.input", return_value="https://test.com")
    def test_download_post_json_http_error(self, mock_input, mock_get):
        """Test JSON download with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        cli_args = MockCliArgs()
        fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

        result = fetcher._download_post_json("https://reddit.com/r/test")

        self.assertIsNone(result)

    @patch("builtins.input", return_value="https://test.com")
    def test_get_subreddit_posts_calls_fetch_with_best(self, mock_input):
        """Test _get_subreddit_posts calls _fetch_posts_from_sub with best=True by default."""
        with patch.object(UrlFetcher, "_fetch_posts_from_sub") as mock_fetch:
            mock_fetch.return_value = []

            cli_args = MockCliArgs()
            fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

            fetcher._get_subreddit_posts("r/test")

            mock_fetch.assert_called_once_with("r/test", pick_random=False, best=True)

    @patch("builtins.input", return_value="https://test.com")
    def test_get_subreddit_posts_calls_fetch_without_best(self, mock_input):
        """Test _get_subreddit_posts can call _fetch_posts_from_sub with best=False."""
        with patch.object(UrlFetcher, "_fetch_posts_from_sub") as mock_fetch:
            mock_fetch.return_value = []

            cli_args = MockCliArgs()
            fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

            fetcher._get_subreddit_posts("r/test", best=False)

            mock_fetch.assert_called_once_with("r/test", pick_random=False, best=False)

    @patch("builtins.input", return_value="https://test.com")
    def test_fetch_posts_strips_leading_slash(self, mock_input):
        """Test that leading slash is stripped from subreddit string."""
        with patch.object(UrlFetcher, "_download_post_json") as mock_download:
            mock_download.return_value = {"data": {"children": []}}

            cli_args = MockCliArgs()
            fetcher = UrlFetcher(self.mock_settings, cli_args, prompt_for_input=False)

            fetcher._fetch_posts_from_sub("/r/python")

            # Should call without leading slash
            expected_url = "https://www.reddit.com/r/python"
            mock_download.assert_called_with(expected_url)

    def test_mixed_input_sources(self):
        """Test UrlFetcher with mixed input sources."""
        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", mock_open(read_data="file_url1,file_url2")):
                with patch.object(UrlFetcher, "_get_subreddit_posts") as mock_get_posts:
                    mock_get_posts.return_value = ["sub_url1"]

                    cli_args = MockCliArgs(
                        urls=["direct_url1"],
                        src_files=["test_file.csv"],
                        subs=["r/python"],
                    )

                    fetcher = UrlFetcher(
                        self.mock_settings, cli_args, prompt_for_input=False
                    )

                    # Should have URLs from all sources
                    self.assertIn("direct_url1", fetcher.urls)
                    self.assertIn("file_url1", fetcher.urls)
                    self.assertIn("file_url2", fetcher.urls)
                    self.assertIn("sub_url1", fetcher.urls)


if __name__ == "__main__":
    unittest.main()
