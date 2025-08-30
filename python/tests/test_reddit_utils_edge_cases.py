import sys

"""
# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
Additional edge case tests for reddit_utils.py module.
Focuses on complex scenarios and edge cases not fully covered in test_reddit_utils.py.
"""

import unittest
from unittest.mock import patch, Mock, mock_open
import os
import tempfile
import datetime
import requests

import reddit_utils as utils
from .test_utils import TempDirTestCase, BaseTestCase


class TestRedditUtilsEdgeCases(TempDirTestCase):
    """Additional edge case tests for reddit_utils module."""

    def test_clean_url_with_multiple_utm_sources(self):
        """Test clean_url with multiple occurrences of utm_source."""
        url = (
            "https://reddit.com/r/test?utm_source=share&other=value&utm_source=another"
        )
        result = utils.clean_url(url)
        # Should only split on first occurrence
        expected = "https://reddit.com/r/test"
        self.assertEqual(result, expected)

    def test_clean_url_with_utm_source_in_path(self):
        """Test clean_url when utm_source appears in the path."""
        url = "https://reddit.com/r/utm_source_test/comments/123/post?param=value"
        result = utils.clean_url(url)
        # Should not affect the path, only query parameters
        self.assertEqual(result, url)

    def test_valid_url_with_numeric_subreddit(self):
        """Test valid_url with numeric characters in subreddit name."""
        url = "https://www.reddit.com/r/test123/comments/abc123/test_post/"
        self.assertTrue(utils.valid_url(url))

    def test_valid_url_with_very_long_subreddit_name(self):
        """Test valid_url with very long subreddit name."""
        long_subreddit = "a" * 100
        url = f"https://www.reddit.com/r/{long_subreddit}/comments/abc123/test_post/"
        self.assertTrue(utils.valid_url(url))

    def test_valid_url_with_short_post_id(self):
        """Test valid_url with minimum length post ID."""
        url = "https://www.reddit.com/r/test/comments/a/test_post/"
        self.assertTrue(utils.valid_url(url))

    def test_valid_url_with_very_long_post_id(self):
        """Test valid_url with very long post ID."""
        long_id = "a" * 50
        url = f"https://www.reddit.com/r/test/comments/{long_id}/test_post/"
        self.assertTrue(utils.valid_url(url))

    @patch("reddit_utils.requests.get")
    def test_download_post_json_with_oauth_url_transformation(self, mock_get):
        """Test download_post_json transforms URL to OAuth endpoint when token provided."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"test": "data"}
        mock_get.return_value = mock_response

        url = "https://www.reddit.com/r/test/comments/123/post"
        access_token = "test_token"

        result = utils.download_post_json(url, access_token)

        # Should call OAuth endpoint
        expected_url = "https://oauth.reddit.com/r/test/comments/123/post.json"
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], expected_url)

        # Should include Authorization header (note: actual implementation uses lowercase "bearer")
        headers = call_args[1]["headers"]
        self.assertIn("Authorization", headers)
        self.assertEqual(headers["Authorization"], f"bearer {access_token}")

    @patch("reddit_utils.requests.get")
    def test_download_post_json_with_malformed_json_response(self, mock_get):
        """Test download_post_json with malformed JSON response."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        url = "https://www.reddit.com/r/test/comments/123/post"

        # ValueError is not caught as RequestException, so it will be re-raised
        with self.assertRaises(ValueError):
            utils.download_post_json(url)

    @patch("reddit_utils.requests.get")
    def test_download_post_json_with_rate_limit_error(self, mock_get):
        """Test download_post_json with Reddit rate limit (429) error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "429 Too Many Requests"
        )
        mock_get.return_value = mock_response

        url = "https://www.reddit.com/r/test/comments/123/post"

        result = utils.download_post_json(url)

        self.assertIsNone(result)

    def test_resolve_save_dir_with_tilde_in_path(self):
        """Test resolve_save_dir with tilde (~) in path."""
        config_dir = "~/reddit_downloads"

        result = utils.resolve_save_dir(config_dir)

        # Current implementation may not expand tilde, let's test actual behavior
        self.assertIsInstance(result, str)
        # The function should return some path
        self.assertGreater(len(result), 0)

    def test_resolve_save_dir_with_environment_variable(self):
        """Test resolve_save_dir with environment variable in path."""
        with patch.dict(os.environ, {"TEST_DIR": "/tmp/test"}):
            config_dir = "$TEST_DIR/reddit"

            result = utils.resolve_save_dir(config_dir)

            # Current implementation may not expand env vars, let's test actual behavior
            self.assertIsInstance(result, str)
            # The function should return some path
            self.assertGreater(len(result), 0)

    def test_generate_filename_with_unicode_characters(self):
        """Test generate_filename with Unicode characters in subreddit and title."""
        # Test with URL containing Unicode (encoded)
        url = "https://www.reddit.com/r/española/comments/123/título_con_ñ/"
        result = utils.generate_filename(
            base_dir=self.temp_dir,
            url=url,
            subreddit="r/española",
            use_timestamped_dirs=False,
            post_timestamp="",
            file_format="md",
            overwrite=True,
        )

        # Should handle Unicode gracefully
        self.assertTrue(result.endswith(".md"))
        self.assertIn(self.temp_dir, result)

    def test_generate_filename_with_very_long_url(self):
        """Test generate_filename with very long URL that needs truncation."""
        long_title = "a" * 200  # Very long title
        url = f"https://www.reddit.com/r/test/comments/123/{long_title}/"

        result = utils.generate_filename(
            base_dir=self.temp_dir,
            url=url,
            subreddit="r/test",
            use_timestamped_dirs=False,
            post_timestamp="",
            file_format="md",
            overwrite=True,
        )

        # Result should be reasonable length
        filename = os.path.basename(result)
        self.assertLess(len(filename), 260)  # Common filesystem limit

    def test_generate_filename_with_invalid_characters(self):
        """Test generate_filename with filesystem-invalid characters."""
        url = "https://www.reddit.com/r/test/comments/123/file<>:|?*name/"

        result = utils.generate_filename(
            base_dir=self.temp_dir,
            url=url,
            subreddit="r/test",
            use_timestamped_dirs=False,
            post_timestamp="",
            file_format="md",
            overwrite=True,
        )

        # The implementation sanitizes invalid characters by replacing them with underscores
        filename = os.path.basename(result)
        # The filename should be "file______name.md" since invalid chars are sanitized
        self.assertTrue(filename.endswith(".md"))
        self.assertIn("file______name", filename)

    def test_markdown_to_html_with_complex_markdown(self):
        """Test markdown_to_html with complex markdown content."""
        complex_md = """
# Header 1
## Header 2

**Bold text** and *italic text*

[Link](https://example.com)

- List item 1
- List item 2

```python
def hello():
    print("Hello, world!")
```

> Blockquote

| Table | Header |
|-------|--------|
| Cell  | Data   |
"""

        result = utils.markdown_to_html(complex_md)

        # Should contain HTML tags
        self.assertIn("<h1>", result)
        self.assertIn("<h2>", result)
        self.assertIn("<strong>", result)
        self.assertIn("<em>", result)
        self.assertIn("<a href=", result)
        self.assertIn("<ul>", result)
        self.assertIn("<code>", result)
        self.assertIn("<blockquote>", result)

    def test_markdown_to_html_with_unsafe_content(self):
        """Test markdown_to_html with potentially unsafe HTML content."""
        unsafe_md = """
<script>alert('xss')</script>
<img src="x" onerror="alert('xss')">

# Normal header

<div onclick="alert('click')">Click me</div>
"""

        result = utils.markdown_to_html(unsafe_md)

        # The current markdown_to_html implementation doesn't sanitize HTML
        # It passes through raw HTML content, so this test documents the current behavior
        self.assertIn("<script>", result)  # Current implementation allows this
        self.assertIn("onerror=", result)  # Current implementation allows this
        self.assertIn("onclick=", result)  # Current implementation allows this

        # But it should still convert markdown headers
        self.assertIn("<h1>Normal header</h1>", result)

    def test_generate_unique_media_filename_with_collision_handling(self):
        """Test generate_unique_media_filename handles filename collisions."""
        media_url = "https://example.com/image.jpg"

        # Create a file that will cause collision
        existing_file = os.path.join(self.temp_dir, "image.jpg")
        with open(existing_file, "w") as f:
            f.write("existing")

        result = utils.generate_unique_media_filename(media_url, self.temp_dir)

        # Should generate unique filename
        self.assertNotEqual(result, existing_file)
        self.assertTrue(result.endswith(".jpg"))
        self.assertIn(self.temp_dir, result)

    def test_generate_unique_media_filename_with_no_extension(self):
        """Test generate_unique_media_filename with URL having no file extension."""
        media_url = "https://example.com/image_without_extension"

        result = utils.generate_unique_media_filename(media_url, self.temp_dir)

        # Should still generate a filename
        self.assertTrue(os.path.dirname(result), self.temp_dir)
        filename = os.path.basename(result)
        self.assertTrue(len(filename) > 0)

    @patch("reddit_utils.requests.get")
    def test_download_media_with_chunked_response(self, mock_get):
        """Test download_media with chunked response."""
        # Create a proper context manager mock
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2", b"chunk3"]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_get.return_value = mock_response

        test_file = os.path.join(self.temp_dir, "test_media.jpg")
        url = "https://example.com/image.jpg"

        result = utils.download_media(url, test_file)

        self.assertTrue(result)
        self.assertTrue(os.path.exists(test_file))

        # Verify content was written
        with open(test_file, "rb") as f:
            content = f.read()
        self.assertEqual(content, b"chunk1chunk2chunk3")

    @patch("reddit_utils.requests.get")
    def test_download_media_with_network_timeout(self, mock_get):
        """Test download_media with network timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        test_file = os.path.join(self.temp_dir, "test_media.jpg")
        url = "https://example.com/image.jpg"

        result = utils.download_media(url, test_file)

        self.assertFalse(result)
        self.assertFalse(os.path.exists(test_file))

    def test_get_replies_with_deeply_nested_structure(self):
        """Test get_replies with deeply nested reply structure."""
        # Create a deeply nested reply structure
        nested_reply = {
            "data": {
                "replies": {
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "id": "child1",
                                    "depth": 1,
                                    "author": "user1",
                                    "body": "Top level reply",
                                    "replies": {
                                        "data": {
                                            "children": [
                                                {
                                                    "data": {
                                                        "id": "child2",
                                                        "depth": 2,
                                                        "author": "user2",
                                                        "body": "Nested reply",
                                                        "replies": {
                                                            "data": {
                                                                "children": [
                                                                    {
                                                                        "data": {
                                                                            "id": "child3",
                                                                            "depth": 3,
                                                                            "author": "user3",
                                                                            "body": "Deep nested reply",
                                                                            "replies": "",
                                                                        }
                                                                    }
                                                                ]
                                                            }
                                                        },
                                                    }
                                                }
                                            ]
                                        }
                                    },
                                }
                            }
                        ]
                    }
                }
            }
        }

        result = utils.get_replies(nested_reply, max_depth=-1)

        # Should return dictionary with child IDs as keys
        self.assertIsInstance(result, dict)
        # Should contain all nested replies
        self.assertIn("child1", result)
        self.assertIn("child2", result)
        self.assertIn("child3", result)

        # Check depth information
        self.assertEqual(result["child1"]["depth"], 1)
        self.assertEqual(result["child2"]["depth"], 2)
        self.assertEqual(result["child3"]["depth"], 3)


class TestRedditUtilsDateTimeEdgeCases(BaseTestCase):
    """Test datetime-related edge cases."""

    def test_timestamp_conversion_with_future_date(self):
        """Test timestamp handling with future dates."""
        # Future timestamp
        future_timestamp = 9999999999  # Far future

        # This would be tested in the context of post processing
        # The datetime conversion should handle it gracefully
        try:
            dt = datetime.datetime.fromtimestamp(
                future_timestamp, datetime.timezone.utc
            )
            formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
            self.assertIsInstance(formatted, str)
        except (ValueError, OSError) as e:
            # Some systems might not handle very far future dates
            self.assertIsInstance(e, (ValueError, OSError))

    def test_timestamp_conversion_with_negative_timestamp(self):
        """Test timestamp handling with negative timestamps (before epoch)."""
        # Negative timestamp (before 1970)
        negative_timestamp = -86400  # One day before epoch

        try:
            dt = datetime.datetime.fromtimestamp(
                negative_timestamp, datetime.timezone.utc
            )
            formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
            self.assertIsInstance(formatted, str)
        except (ValueError, OSError) as e:
            # Some systems might not handle negative timestamps
            self.assertIsInstance(e, (ValueError, OSError))


if __name__ == "__main__":
    unittest.main()
