"""
Streamlined URL fetcher tests focusing on behavior, not implementation.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import os

from url_fetcher import UrlFetcher


class TestUrlFetchingBehavior(unittest.TestCase):
    """Test URL fetching behavior and input processing."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.multi_reddits = {
            "m/tech": ["r/programming", "r/technology"],
            "m/news": ["r/news", "r/worldnews"],
        }

    def test_direct_url_collection(self):
        """Direct URLs should be collected and stored."""
        mock_args = Mock()
        mock_args.urls = [
            "https://reddit.com/r/python/comments/123/post1",
            "https://reddit.com/r/javascript/comments/456/post2",
        ]
        mock_args.src_files = []
        mock_args.subs = []
        mock_args.multis = []

        fetcher = UrlFetcher(
            self.mock_settings,
            mock_args,
            access_token="test_token",
            prompt_for_input=False,
        )

        self.assertEqual(len(fetcher.urls), 2)
        self.assertIn("https://reddit.com/r/python/comments/123/post1", fetcher.urls)
        self.assertIn(
            "https://reddit.com/r/javascript/comments/456/post2", fetcher.urls
        )

    def test_file_based_url_collection(self):
        """URLs should be loaded from CSV files."""
        # Create a temporary CSV file with URLs
        test_urls = [
            "https://reddit.com/r/test/comments/1/post1",
            "https://reddit.com/r/test/comments/2/post2",
            "https://reddit.com/r/test/comments/3/post3",
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(",".join(test_urls[:2]) + "\n")  # First row
            f.write(test_urls[2])  # Second row
            temp_path = f.name

        try:
            mock_args = Mock()
            mock_args.urls = []
            mock_args.src_files = [temp_path]
            mock_args.subs = []
            mock_args.multis = []

            fetcher = UrlFetcher(
                self.mock_settings,
                mock_args,
                access_token="test_token",
                prompt_for_input=False,
            )

            # Should have loaded all URLs from file
            self.assertEqual(len(fetcher.urls), 3)
            for url in test_urls:
                self.assertIn(url, fetcher.urls)

        finally:
            os.unlink(temp_path)

    def test_missing_file_handling(self):
        """Missing source files should be handled gracefully."""
        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = ["/nonexistent/file.csv"]
        mock_args.subs = []
        mock_args.multis = []

        # Should not crash, should just have no URLs
        fetcher = UrlFetcher(self.mock_settings, mock_args, prompt_for_input=False)

        self.assertEqual(len(fetcher.urls), 0)

    @patch("url_fetcher.UrlFetcher._get_subreddit_posts")
    def test_subreddit_post_collection(self, mock_get_posts):
        """URLs should be collected from specified subreddits."""
        mock_get_posts.return_value = [
            "https://reddit.com/r/python/comments/111/post1",
            "https://reddit.com/r/python/comments/222/post2",
        ]

        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = ["r/python"]
        mock_args.multis = []

        fetcher = UrlFetcher(
            self.mock_settings,
            mock_args,
            access_token="test_token",
            prompt_for_input=False,
        )

        self.assertEqual(len(fetcher.urls), 2)
        mock_get_posts.assert_called_once_with("r/python")

    @patch("url_fetcher.UrlFetcher._get_subreddit_posts")
    def test_multireddit_expansion(self, mock_get_posts):
        """Multi-reddits should be expanded to component subreddits."""
        mock_get_posts.side_effect = [
            ["https://reddit.com/r/programming/comments/111/post1"],  # First subreddit
            ["https://reddit.com/r/technology/comments/222/post2"],  # Second subreddit
        ]

        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = []
        mock_args.multis = ["m/tech"]  # Should expand to r/programming, r/technology

        fetcher = UrlFetcher(
            self.mock_settings,
            mock_args,
            access_token="test_token",
            prompt_for_input=False,
        )

        # Should have called _get_subreddit_posts for each subreddit in the multi
        self.assertEqual(mock_get_posts.call_count, 2)
        self.assertEqual(len(fetcher.urls), 2)

    def test_unknown_multireddit_handling(self):
        """Unknown multi-reddits should be handled gracefully."""
        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = []
        mock_args.multis = ["m/nonexistent"]  # Not in settings

        fetcher = UrlFetcher(self.mock_settings, mock_args, prompt_for_input=False)

        # Should not crash, should have no URLs
        self.assertEqual(len(fetcher.urls), 0)

    @patch("builtins.input")
    def test_interactive_url_input(self, mock_input):
        """Interactive input should be processed correctly."""
        mock_input.return_value = "https://reddit.com/r/test/comments/123/interactive"

        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = []
        mock_args.multis = []

        fetcher = UrlFetcher(
            self.mock_settings, mock_args
        )  # prompt_for_input defaults to True

        self.assertEqual(len(fetcher.urls), 1)
        self.assertIn(
            "https://reddit.com/r/test/comments/123/interactive", fetcher.urls
        )

    @patch("builtins.input")
    @patch("url_fetcher.UrlFetcher._get_subreddit_posts")
    def test_interactive_subreddit_input(self, mock_get_posts, mock_input):
        """Interactive subreddit input should fetch posts."""
        mock_input.return_value = "r/python"
        mock_get_posts.return_value = [
            "https://reddit.com/r/python/comments/111/interactive1"
        ]

        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = []
        mock_args.multis = []

        fetcher = UrlFetcher(self.mock_settings, mock_args)

        mock_get_posts.assert_called_once_with("r/python", best=True)
        self.assertEqual(len(fetcher.urls), 1)

    @patch("builtins.input")
    def test_interactive_multiple_url_input(self, mock_input):
        """Interactive input should handle comma-separated URLs."""
        mock_input.return_value = "url1,url2, url3 "  # Various spacing

        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = []
        mock_args.multis = []

        fetcher = UrlFetcher(self.mock_settings, mock_args)

        self.assertEqual(len(fetcher.urls), 3)
        self.assertIn("url1", fetcher.urls)
        self.assertIn("url2", fetcher.urls)
        self.assertIn("url3", fetcher.urls)

    @patch("builtins.input")
    def test_demo_mode_activation(self, mock_input):
        """Demo mode should provide sample URLs."""
        mock_input.return_value = "demo"

        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = []
        mock_args.multis = []

        fetcher = UrlFetcher(self.mock_settings, mock_args)

        # Should provide at least one demo URL
        self.assertGreater(len(fetcher.urls), 0)
        # Demo URLs should be valid Reddit URLs
        for url in fetcher.urls:
            self.assertIn("reddit.com", url)

    def test_mixed_input_sources(self):
        """Multiple input sources should be combined."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("file_url1,file_url2")
            temp_path = f.name

        try:
            with patch("url_fetcher.UrlFetcher._get_subreddit_posts") as mock_get_posts:
                mock_get_posts.return_value = ["sub_url1"]

                mock_args = Mock()
                mock_args.urls = ["direct_url1", "direct_url2"]
                mock_args.src_files = [temp_path]
                mock_args.subs = ["r/test"]
                mock_args.multis = []

                fetcher = UrlFetcher(
                    self.mock_settings, mock_args, prompt_for_input=False
                )

                # Should have URLs from all sources
                self.assertGreater(len(fetcher.urls), 4)  # At least 5 URLs total
                self.assertIn("direct_url1", fetcher.urls)
                self.assertIn("direct_url2", fetcher.urls)
                self.assertIn("file_url1", fetcher.urls)
                self.assertIn("file_url2", fetcher.urls)
                self.assertIn("sub_url1", fetcher.urls)

        finally:
            os.unlink(temp_path)


class TestUrlFetchingIntegration(unittest.TestCase):
    """Integration tests for URL fetching with realistic scenarios."""

    @patch("requests.get")
    def test_subreddit_post_fetching_with_authentication(self, mock_get):
        """Test fetching posts from subreddit with OAuth authentication."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {"data": {"permalink": "/r/python/comments/111/post1"}},
                    {"data": {"permalink": "/r/python/comments/222/post2"}},
                ]
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_settings = Mock()
        mock_settings.multi_reddits = {}

        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = ["r/python"]
        mock_args.multis = []

        fetcher = UrlFetcher(
            mock_settings,
            mock_args,
            access_token="test_oauth_token",
            prompt_for_input=False,
        )

        # Should have fetched URLs from the subreddit
        self.assertEqual(len(fetcher.urls), 2)

        # Should have used OAuth endpoint
        call_args = mock_get.call_args
        self.assertIn("oauth.reddit.com", call_args[0][0])

        # Should have included authorization header
        headers = call_args[1]["headers"]
        self.assertIn("Authorization", headers)
        self.assertIn("test_oauth_token", headers["Authorization"])

    @patch("requests.get")
    def test_subreddit_post_fetching_without_authentication(self, mock_get):
        """Test fetching posts from subreddit without authentication."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "children": [{"data": {"permalink": "/r/public/comments/111/post1"}}]
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_settings = Mock()
        mock_settings.multi_reddits = {}

        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = ["r/public"]
        mock_args.multis = []

        fetcher = UrlFetcher(
            mock_settings,
            mock_args,
            access_token=None,  # No authentication
            prompt_for_input=False,
        )

        self.assertEqual(len(fetcher.urls), 1)

        # Should use regular Reddit endpoint
        call_args = mock_get.call_args
        self.assertIn("www.reddit.com", call_args[0][0])

        # Should not have authorization header
        headers = call_args[1]["headers"]
        self.assertNotIn("Authorization", headers)

    @patch("requests.get")
    def test_network_error_handling(self, mock_get):
        """Network errors should be handled gracefully."""
        import requests

        mock_get.side_effect = requests.ConnectionError("Network unavailable")

        mock_settings = Mock()
        mock_settings.multi_reddits = {}

        mock_args = Mock()
        mock_args.urls = []
        mock_args.src_files = []
        mock_args.subs = ["r/test"]
        mock_args.multis = []

        # Should not crash, should just have no URLs
        fetcher = UrlFetcher(mock_settings, mock_args, prompt_for_input=False)

        self.assertEqual(len(fetcher.urls), 0)

    def test_comprehensive_url_collection_workflow(self):
        """Test a comprehensive URL collection scenario."""
        # Create a sample file with URLs
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("https://reddit.com/r/file/comments/1/post1,")
            f.write("https://reddit.com/r/file/comments/2/post2")
            temp_path = f.name

        try:
            with patch("url_fetcher.UrlFetcher._get_subreddit_posts") as mock_get_posts:
                # Mock different responses for different subreddits
                mock_get_posts.side_effect = [
                    # r/programming (from m/tech multi)
                    ["https://reddit.com/r/programming/comments/111/prog1"],
                    # r/technology (from m/tech multi)
                    ["https://reddit.com/r/technology/comments/222/tech1"],
                    # r/direct subreddit
                    ["https://reddit.com/r/direct/comments/333/direct1"],
                ]

                mock_settings = Mock()
                mock_settings.multi_reddits = {
                    "m/tech": ["r/programming", "r/technology"]
                }

                mock_args = Mock()
                mock_args.urls = [
                    "https://reddit.com/r/direct1/comments/aaa/manual1",
                    "https://reddit.com/r/direct2/comments/bbb/manual2",
                ]
                mock_args.src_files = [temp_path]
                mock_args.subs = ["r/direct"]
                mock_args.multis = ["m/tech"]

                fetcher = UrlFetcher(
                    mock_settings,
                    mock_args,
                    access_token="test_token",
                    prompt_for_input=False,
                )

                # Should have collected URLs from all sources:
                # - 2 direct URLs
                # - 2 file URLs
                # - 1 direct subreddit URL
                # - 2 multi-reddit URLs
                self.assertEqual(len(fetcher.urls), 7)

                # Verify URLs from each source are present
                self.assertIn(
                    "https://reddit.com/r/direct1/comments/aaa/manual1", fetcher.urls
                )
                self.assertIn(
                    "https://reddit.com/r/file/comments/1/post1", fetcher.urls
                )
                self.assertIn(
                    "https://reddit.com/r/direct/comments/333/direct1", fetcher.urls
                )
                self.assertIn(
                    "https://reddit.com/r/programming/comments/111/prog1", fetcher.urls
                )

        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
