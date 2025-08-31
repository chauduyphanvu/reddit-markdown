"""
Streamlined tests for reddit_utils focusing on behavior, not implementation.
"""

import unittest
from unittest.mock import patch, Mock
import tempfile
import os
import time
import requests

import reddit_utils as utils
from processing import ContentConverter


class TestRedditUtilsBehavior(unittest.TestCase):
    """Test reddit_utils functions based on expected behavior."""

    def test_url_cleaning(self):
        """Test that URLs are properly cleaned."""
        test_cases = [
            # (input, expected_output) - clean_url only removes utm_source
            (
                "https://reddit.com/r/test/comments/123?utm_source=share",
                "https://reddit.com/r/test/comments/123",
            ),
            (
                "https://reddit.com/r/test/comments/123?ref=share",
                "https://reddit.com/r/test/comments/123?ref=share",  # ref is not removed
            ),
            (
                "https://reddit.com/r/test/comments/123/",
                "https://reddit.com/r/test/comments/123/",  # trailing slash preserved
            ),
            (
                "https://reddit.com/r/test/comments/123",
                "https://reddit.com/r/test/comments/123",
            ),
            ("", ""),
        ]

        for input_url, expected in test_cases:
            with self.subTest(input=input_url):
                self.assertEqual(utils.clean_url(input_url), expected)

    def test_url_validation(self):
        """Test that only valid Reddit URLs pass validation."""
        valid_urls = [
            "https://www.reddit.com/r/python/comments/abc123/test/",
            "https://reddit.com/r/test/comments/123/post/",
            "https://old.reddit.com/r/test/comments/456/title/",
        ]

        invalid_urls = [
            "http://reddit.com/r/test/comments/123/",  # HTTP not allowed
            "https://google.com/search",
            "not_a_url",
            "",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(utils.valid_url(url))

        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(utils.valid_url(url))

    @patch("requests.get")
    def test_download_json_returns_data(self, mock_get):
        """Test that download_post_json returns parsed JSON data."""
        expected_data = {"kind": "Listing", "data": {"children": []}}

        mock_response = Mock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = utils.download_post_json("https://reddit.com/r/test/comments/123")

        self.assertEqual(result, expected_data)

    @patch("requests.get")
    def test_download_json_handles_errors_gracefully(self, mock_get):
        """Test that download_post_json returns None on errors."""
        # Test network error
        mock_get.side_effect = requests.RequestException("Network error")
        result = utils.download_post_json("https://reddit.com/r/test/comments/123")
        self.assertIsNone(result)

        # Test HTTP error
        mock_get.side_effect = None
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_response
        result = utils.download_post_json("https://reddit.com/r/test/comments/456")
        self.assertIsNone(result)

    @patch("requests.get")
    def test_caching_reduces_api_calls(self, mock_get):
        """Test that caching prevents duplicate API calls."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "https://reddit.com/r/test/comments/789"

        # First call should hit the API
        result1 = utils.download_post_json(url)
        self.assertEqual(result1, {"data": "test"})
        self.assertEqual(mock_get.call_count, 1)

        # Second call should use cache
        result2 = utils.download_post_json(url)
        self.assertEqual(result2, {"data": "test"})
        self.assertEqual(mock_get.call_count, 1)  # Still 1, not 2

    def test_filename_generation(self):
        """Test that filenames are generated safely and uniquely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate first filename
            filename1 = utils.generate_filename(
                base_dir=tmpdir,
                url="https://reddit.com/r/test/comments/abc123/test_post/",
                subreddit="r/test",
                use_timestamped_dirs=False,
                post_timestamp="2024-01-01 12:00:00",
                file_format="md",
                overwrite=False,
            )

            # Should contain the post title from URL
            self.assertIn("test_post", filename1)
            # Should have correct extension
            self.assertTrue(filename1.endswith(".md"))
            # Should be in the correct directory (handle macOS /private prefix)
            import os

            tmpdir_real = os.path.realpath(tmpdir)
            filename1_real = os.path.realpath(filename1)
            self.assertTrue(filename1_real.startswith(tmpdir_real))

            # Create the file
            open(filename1, "w").close()

            # Generate second filename for same URL
            filename2 = utils.generate_filename(
                base_dir=tmpdir,
                url="https://reddit.com/r/test/comments/abc123/test_post/",
                subreddit="r/test",
                use_timestamped_dirs=False,
                post_timestamp="2024-01-01 12:00:00",
                file_format="md",
                overwrite=False,
            )

            # Should be different (numbered)
            self.assertNotEqual(filename1, filename2)
            self.assertIn("_1", filename2)

    def test_markdown_to_html_conversion(self):
        """Test that Markdown is converted to HTML."""
        markdown = "# Title\n\nThis is **bold** and *italic* text."
        html = ContentConverter.markdown_to_html(markdown)

        # Should contain HTML tags (case insensitive)
        html_lower = html.lower()
        self.assertIn("<!doctype html>", html_lower)
        self.assertIn("<h1", html_lower)  # h1 with id attribute
        self.assertIn("<strong>", html_lower)
        self.assertIn("<em>", html_lower)

    def test_reply_extraction(self):
        """Test that replies are extracted from Reddit data structure."""
        reply_data = {
            "data": {
                "body": "Top level reply",
                "author": "user1",
                "ups": 10,
                "replies": {
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "id": "child123",
                                    "body": "Nested reply",
                                    "author": "user2",
                                    "ups": 5,
                                    "depth": 1,
                                    "replies": "",
                                }
                            }
                        ]
                    }
                },
            }
        }

        replies = utils.get_replies(reply_data, max_depth=2)

        # Should extract replies using child IDs as keys
        self.assertIn("child123", replies)

        # Should contain the reply data structure
        self.assertEqual(replies["child123"]["depth"], 1)
        self.assertEqual(
            replies["child123"]["child_reply"]["data"]["body"], "Nested reply"
        )

    @patch("requests.get")
    def test_rate_limiting_configuration_accepted(self, mock_get):
        """Test that rate limiting configuration is accepted without errors."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Configure rate limiting settings
        settings = Mock()
        settings.rate_limit_requests_per_minute = 60
        settings.cache_ttl_seconds = 600
        settings.max_cache_entries = 100

        # Should configure without errors
        utils.configure_performance(settings)

        # Should still make successful requests
        result = utils.download_post_json("https://reddit.com/r/test/comments/1")
        self.assertIsNotNone(result)
        self.assertEqual(result, {"data": "test"})

    def test_performance_configuration(self):
        """Test that performance settings are applied."""
        settings = Mock()
        settings.rate_limit_requests_per_minute = 120
        settings.cache_ttl_seconds = 600
        settings.max_cache_entries = 500

        # This should not raise an exception
        utils.configure_performance(settings)

        # The function should handle Mock objects gracefully
        settings.rate_limit_requests_per_minute = Mock()
        utils.configure_performance(settings)  # Should use defaults


class TestRedditUtilsIntegration(unittest.TestCase):
    """Integration tests for reddit_utils."""

    @patch("requests.get")
    def test_download_with_oauth_endpoint(self, mock_get):
        """Test that OAuth endpoint is used with access token."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "authenticated"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = utils.download_post_json(
            "https://reddit.com/r/test/comments/123", access_token="test_token"
        )

        self.assertEqual(result, {"data": "authenticated"})

        # Verify OAuth endpoint was used
        called_url = mock_get.call_args[0][0]
        self.assertIn("oauth.reddit.com", called_url)

        # Verify authorization header was set
        headers = mock_get.call_args[1]["headers"]
        self.assertIn("Authorization", headers)
        self.assertIn("test_token", headers["Authorization"])

    def test_safe_directory_creation(self):
        """Test that directory path resolution works safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test with nested directory path
            save_dir = os.path.join(tmpdir, "reddit", "posts", "2024")

            # resolve_save_dir should return the path as-is when given a specific path
            resolved = utils.resolve_save_dir(save_dir)

            self.assertEqual(resolved, save_dir)
            # resolve_save_dir in reddit_utils.py doesn't create directories, just returns paths
            # Directory creation happens elsewhere in the workflow

    def test_filename_sanitization(self):
        """Test that dangerous characters are removed from filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # URL with dangerous characters
            dangerous_url = "https://reddit.com/r/test/comments/../../etc/passwd"

            filename = utils.generate_filename(
                base_dir=tmpdir,
                url=dangerous_url,
                subreddit="r/../../../test",
                use_timestamped_dirs=False,
                post_timestamp="2024-01-01 12:00:00",
                file_format="md",
                overwrite=False,
            )

            # Should not contain path traversal sequences
            self.assertNotIn("..", filename)
            self.assertNotIn("/etc/", filename)
            # Should still be in the tmpdir (handle macOS /private prefix)
            import os

            tmpdir_real = os.path.realpath(tmpdir)
            filename_real = os.path.realpath(filename)
            self.assertTrue(filename_real.startswith(tmpdir_real))


if __name__ == "__main__":
    unittest.main()
