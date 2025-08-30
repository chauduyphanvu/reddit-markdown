import sys
import os
import unittest
from unittest.mock import patch, Mock, mock_open, MagicMock
import json
import datetime
import requests

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import reddit_utils as utils
from .test_utils import (
    BaseTestCase,
    TempDirTestCase,
    MockFactory,
    TEST_URLS,
    TEST_USER_AGENTS,
    TEST_TIMEOUTS,
)


class TestCleanUrl(BaseTestCase):
    """Test the clean_url function."""

    def test_clean_url_with_utm_source(self):
        """Test URL cleaning with utm_source parameter."""
        url = "https://reddit.com/r/test/comments/123/post?utm_source=share"
        result = utils.clean_url(url)
        expected = "https://reddit.com/r/test/comments/123/post"
        self.assertEqual(result, expected)

    def test_clean_url_without_utm_source(self):
        """Test URL cleaning without utm_source parameter."""
        url = "https://reddit.com/r/test/comments/123/post"
        result = utils.clean_url(url)
        self.assertEqual(result, url)

    def test_clean_url_with_other_parameters(self):
        """Test URL cleaning preserves other parameters."""
        url = "https://reddit.com/r/test/comments/123/post?other_param=value"
        result = utils.clean_url(url)
        self.assertEqual(result, url)

    def test_clean_url_with_whitespace(self):
        """Test URL cleaning strips whitespace."""
        url = "  https://reddit.com/r/test/comments/123/post  "
        result = utils.clean_url(url)
        expected = "https://reddit.com/r/test/comments/123/post"
        self.assertEqual(result, expected)

    def test_clean_url_empty_string(self):
        """Test URL cleaning with empty string."""
        result = utils.clean_url("")
        self.assertEqual(result, "")

    def test_clean_url_utm_source_mid_url(self):
        """Test URL cleaning when utm_source appears mid-URL."""
        url = "https://reddit.com/r/test?utm_source=share&other=value"
        result = utils.clean_url(url)
        expected = "https://reddit.com/r/test"
        self.assertEqual(result, expected)


class TestValidUrl(BaseTestCase):
    """Test the valid_url function."""

    def test_valid_url_correct_format(self):
        """Test URL validation with correct Reddit post format."""
        self.assertTrue(utils.valid_url(TEST_URLS["valid_reddit_post"]))

    def test_valid_url_without_trailing_slash(self):
        """Test URL validation without trailing slash."""
        url = "https://www.reddit.com/r/python/comments/abc123/test_post"
        self.assertTrue(utils.valid_url(url))

    def test_valid_url_with_underscores_in_subreddit(self):
        """Test URL validation with underscores in subreddit name."""
        url = "https://www.reddit.com/r/test_sub/comments/abc123/test_post/"
        self.assertTrue(utils.valid_url(url))

    def test_invalid_url_wrong_domain(self):
        """Test URL validation with wrong domain."""
        url = "https://google.com/r/python/comments/abc123/test_post/"
        self.assertFalse(utils.valid_url(url))

    def test_invalid_url_missing_subreddit(self):
        """Test URL validation missing subreddit."""
        url = "https://www.reddit.com/comments/abc123/test_post/"
        self.assertFalse(utils.valid_url(url))

    def test_invalid_url_missing_comments(self):
        """Test URL validation missing 'comments' part."""
        url = "https://www.reddit.com/r/python/abc123/test_post/"
        self.assertFalse(utils.valid_url(url))

    def test_invalid_url_http_instead_of_https(self):
        """Test URL validation with http instead of https."""
        url = "http://www.reddit.com/r/python/comments/abc123/test_post/"
        self.assertFalse(utils.valid_url(url))

    def test_invalid_url_empty_string(self):
        """Test URL validation with empty string."""
        self.assertFalse(utils.valid_url(""))

    def test_invalid_url_random_string(self):
        """Test URL validation with random string."""
        self.assertFalse(utils.valid_url("random string"))


class TestDownloadPostJson(BaseTestCase):
    """Test the download_post_json function."""

    def setUp(self):
        """Set up test fixtures and clear cache."""
        super().setUp()
        # Clear the global cache to ensure test isolation
        utils._json_cache.clear()
        utils._cache_timestamps.clear()

    @patch("reddit_utils.requests.get")
    def test_download_post_json_success(self, mock_get):
        """Test successful JSON download."""
        mock_get.return_value = MockFactory.create_http_response(
            json_data={"data": "test"}
        )

        url = "https://reddit.com/r/test/comments/123/post"
        result = utils.download_post_json(url)

        self.assertEqual(result, {"data": "test"})
        mock_get.assert_called_once_with(
            url + ".json",
            headers={"User-Agent": TEST_USER_AGENTS["default"]},
            timeout=TEST_TIMEOUTS["download_post_json"],
        )

    @patch("reddit_utils.requests.get")
    def test_download_post_json_with_access_token(self, mock_get):
        """Test JSON download with access token."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        url = "https://reddit.com/r/test/comments/123/post"
        access_token = "test_token"
        result = utils.download_post_json(url, access_token)

        self.assertEqual(result, {"data": "test"})
        expected_url = "https://oauth.reddit.com/r/test/comments/123/post.json"
        expected_headers = {
            "User-Agent": TEST_USER_AGENTS["default"],
            "Authorization": "bearer test_token",
        }
        mock_get.assert_called_once_with(
            expected_url,
            headers=expected_headers,
            timeout=TEST_TIMEOUTS["download_post_json"],
        )

    @patch("reddit_utils.requests.get")
    def test_download_post_json_already_has_json_extension(self, mock_get):
        """Test JSON download when URL already has .json extension."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        url = "https://reddit.com/r/test/comments/123/post.json"
        result = utils.download_post_json(url)

        self.assertEqual(result, {"data": "test"})
        mock_get.assert_called_once_with(
            url,  # Should not add another .json
            headers={"User-Agent": TEST_USER_AGENTS["default"]},
            timeout=TEST_TIMEOUTS["download_post_json"],
        )

    @patch("reddit_utils.requests.get")
    def test_download_post_json_http_error(self, mock_get):
        """Test JSON download with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        url = "https://reddit.com/r/test/comments/123/post"
        result = utils.download_post_json(url)

        self.assertIsNone(result)

    @patch("reddit_utils.requests.get")
    def test_download_post_json_network_error(self, mock_get):
        """Test JSON download with network error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        url = "https://reddit.com/r/test/comments/123/post"
        result = utils.download_post_json(url)

        self.assertIsNone(result)

    @patch("reddit_utils.requests.get")
    def test_download_post_json_timeout(self, mock_get):
        """Test JSON download with timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        url = "https://reddit.com/r/test/comments/123/post"
        result = utils.download_post_json(url)

        self.assertIsNone(result)


class TestGetReplies(BaseTestCase):
    """Test the get_replies function."""

    def test_get_replies_no_replies(self):
        """Test get_replies with no replies."""
        reply_data = {"data": {"replies": ""}}
        result = utils.get_replies(reply_data)
        self.assertEqual(result, {})

    def test_get_replies_single_reply(self):
        """Test get_replies with single reply."""
        reply_data = {
            "data": {
                "replies": {
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "id": "child1",
                                    "depth": 1,
                                    "body": "Test reply",
                                    "replies": "",
                                }
                            }
                        ]
                    }
                }
            }
        }

        result = utils.get_replies(reply_data)
        expected = {
            "child1": {
                "depth": 1,
                "child_reply": {
                    "data": {
                        "id": "child1",
                        "depth": 1,
                        "body": "Test reply",
                        "replies": "",
                    }
                },
            }
        }
        self.assertEqual(result, expected)

    def test_get_replies_nested_replies(self):
        """Test get_replies with nested replies."""
        reply_data = {
            "data": {
                "replies": {
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "id": "child1",
                                    "depth": 1,
                                    "body": "Parent reply",
                                    "replies": {
                                        "data": {
                                            "children": [
                                                {
                                                    "data": {
                                                        "id": "child2",
                                                        "depth": 2,
                                                        "body": "Nested reply",
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
                }
            }
        }

        result = utils.get_replies(reply_data)

        self.assertIn("child1", result)
        self.assertIn("child2", result)
        self.assertEqual(result["child1"]["depth"], 1)
        self.assertEqual(result["child2"]["depth"], 2)

    def test_get_replies_max_depth_limit(self):
        """Test get_replies respects max depth limit."""
        reply_data = {
            "data": {
                "replies": {
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "id": "child1",
                                    "depth": 1,
                                    "body": "Depth 1",
                                    "replies": {
                                        "data": {
                                            "children": [
                                                {
                                                    "data": {
                                                        "id": "child2",
                                                        "depth": 2,
                                                        "body": "Depth 2",
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
                }
            }
        }

        result = utils.get_replies(reply_data, max_depth=1)

        self.assertIn("child1", result)
        self.assertNotIn("child2", result)

    def test_get_replies_empty_body_filtered(self):
        """Test get_replies filters empty body replies."""
        reply_data = {
            "data": {
                "replies": {
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "id": "child1",
                                    "depth": 1,
                                    "body": "",
                                    "replies": "",
                                }
                            },
                            {
                                "data": {
                                    "id": "child2",
                                    "depth": 1,
                                    "body": "Valid reply",
                                    "replies": "",
                                }
                            },
                        ]
                    }
                }
            }
        }

        result = utils.get_replies(reply_data)

        self.assertNotIn("child1", result)
        self.assertIn("child2", result)


class TestResolveSaveDir(BaseTestCase):
    """Test the resolve_save_dir function."""

    @patch.dict(os.environ, {"DEFAULT_REDDIT_SAVE_LOCATION": "/test/path"})
    def test_resolve_save_dir_environment_variable(self):
        """Test resolve_save_dir with environment variable."""
        result = utils.resolve_save_dir("DEFAULT_REDDIT_SAVE_LOCATION")
        self.assertEqual(result, "/test/path")

    def test_resolve_save_dir_missing_environment_variable(self):
        """Test resolve_save_dir with missing environment variable."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                utils.resolve_save_dir("DEFAULT_REDDIT_SAVE_LOCATION")

    def test_resolve_save_dir_direct_path(self):
        """Test resolve_save_dir with direct path."""
        test_path = "/direct/path"
        result = utils.resolve_save_dir(test_path)
        self.assertEqual(result, test_path)

    @patch("builtins.input", side_effect=["", "/user/selected/path"])
    @patch("os.path.isdir", side_effect=[True, True])
    @patch("os.getcwd", return_value="/current/dir")
    def test_resolve_save_dir_user_input_empty_then_valid(
        self, mock_getcwd, mock_isdir, mock_input
    ):
        """Test resolve_save_dir with user input (empty first, then valid)."""
        result = utils.resolve_save_dir("")
        self.assertEqual(result, "/current/dir")

    @patch("builtins.input", side_effect=["/invalid/path", "/valid/path"])
    @patch("os.path.isdir", side_effect=[False, True])
    def test_resolve_save_dir_user_input_invalid_then_valid(
        self, mock_isdir, mock_input
    ):
        """Test resolve_save_dir with invalid then valid user input."""
        result = utils.resolve_save_dir("")
        self.assertEqual(result, "/valid/path")


class TestEnsureDirExists(TempDirTestCase):
    """Test the ensure_dir_exists function."""

    def test_ensure_dir_exists_creates_directory(self):
        """Test ensure_dir_exists creates directory when it doesn't exist."""
        test_path = os.path.join(self.temp_dir, "new_dir")
        self.assertFalse(os.path.exists(test_path))

        utils.ensure_dir_exists(test_path)

        self.assertTrue(os.path.isdir(test_path))

    def test_ensure_dir_exists_does_nothing_if_exists(self):
        """Test ensure_dir_exists does nothing when directory exists."""
        # temp_dir already exists
        utils.ensure_dir_exists(self.temp_dir)

        # Should still exist and be a directory
        self.assertTrue(os.path.isdir(self.temp_dir))

    def test_ensure_dir_exists_creates_nested_directories(self):
        """Test ensure_dir_exists creates nested directories."""
        test_path = os.path.join(self.temp_dir, "level1", "level2", "level3")
        self.assertFalse(os.path.exists(test_path))

        utils.ensure_dir_exists(test_path)

        self.assertTrue(os.path.isdir(test_path))


class TestGenerateFilename(TempDirTestCase):
    """Test the generate_filename function."""

    def test_generate_filename_basic(self):
        """Test basic filename generation."""
        url = "https://reddit.com/r/test/comments/123/test_post/"
        result = utils.generate_filename(
            base_dir=self.temp_dir,
            url=url,
            subreddit="r/test",
            use_timestamped_dirs=False,
            post_timestamp="",
            file_format="md",
            overwrite=False,
        )

        expected_path = os.path.join(self.temp_dir, "test", "test_post.md")
        # Normalize paths to handle macOS symlink differences (/var vs /private/var)
        self.assertEqual(os.path.realpath(result), os.path.realpath(expected_path))

    def test_generate_filename_with_timestamp_dirs(self):
        """Test filename generation with timestamped directories."""
        url = "https://reddit.com/r/test/comments/123/test_post/"
        timestamp = "2023-01-15 10:30:00"

        result = utils.generate_filename(
            base_dir=self.temp_dir,
            url=url,
            subreddit="r/test",
            use_timestamped_dirs=True,
            post_timestamp=timestamp,
            file_format="md",
            overwrite=False,
        )

        expected_path = os.path.join(
            self.temp_dir, "test", "2023-01-15", "test_post.md"
        )
        self.assertEqual(os.path.realpath(result), os.path.realpath(expected_path))

    def test_generate_filename_html_format(self):
        """Test filename generation with HTML format."""
        url = "https://reddit.com/r/test/comments/123/test_post/"
        result = utils.generate_filename(
            base_dir=self.temp_dir,
            url=url,
            subreddit="r/test",
            use_timestamped_dirs=False,
            post_timestamp="",
            file_format="html",
            overwrite=False,
        )

        expected_path = os.path.join(self.temp_dir, "test", "test_post.html")
        self.assertEqual(os.path.realpath(result), os.path.realpath(expected_path))

    def test_generate_filename_file_exists_no_overwrite(self):
        """Test filename generation when file exists and overwrite=False."""
        url = "https://reddit.com/r/test/comments/123/test_post/"

        # Create the expected file first
        test_dir = os.path.join(self.temp_dir, "test")
        os.makedirs(test_dir)
        existing_file = os.path.join(test_dir, "test_post.md")
        with open(existing_file, "w") as f:
            f.write("existing content")

        result = utils.generate_filename(
            base_dir=self.temp_dir,
            url=url,
            subreddit="r/test",
            use_timestamped_dirs=False,
            post_timestamp="",
            file_format="md",
            overwrite=False,
        )

        expected_path = os.path.join(self.temp_dir, "test", "test_post_1.md")
        self.assertEqual(os.path.realpath(result), os.path.realpath(expected_path))

    def test_generate_filename_file_exists_with_overwrite(self):
        """Test filename generation when file exists and overwrite=True."""
        url = "https://reddit.com/r/test/comments/123/test_post/"

        # Create the expected file first
        test_dir = os.path.join(self.temp_dir, "test")
        os.makedirs(test_dir)
        existing_file = os.path.join(test_dir, "test_post.md")
        with open(existing_file, "w") as f:
            f.write("existing content")

        result = utils.generate_filename(
            base_dir=self.temp_dir,
            url=url,
            subreddit="r/test",
            use_timestamped_dirs=False,
            post_timestamp="",
            file_format="md",
            overwrite=True,
        )

        expected_path = os.path.join(self.temp_dir, "test", "test_post.md")
        self.assertEqual(os.path.realpath(result), os.path.realpath(expected_path))

    def test_generate_filename_invalid_timestamp(self):
        """Test filename generation with invalid timestamp."""
        url = "https://reddit.com/r/test/comments/123/test_post/"
        invalid_timestamp = "invalid-timestamp"

        with patch("reddit_utils.datetime.datetime") as mock_datetime:
            # Mock strptime to raise ValueError for invalid timestamp
            mock_datetime.strptime.side_effect = ValueError("Invalid timestamp")

            # Mock now().strftime() to return expected date string
            mock_now = Mock()
            mock_now.strftime.return_value = "2023-01-01"
            mock_datetime.now.return_value = mock_now

            result = utils.generate_filename(
                base_dir=self.temp_dir,
                url=url,
                subreddit="r/test",
                use_timestamped_dirs=True,
                post_timestamp=invalid_timestamp,
                file_format="md",
                overwrite=False,
            )

        expected_path = os.path.join(
            self.temp_dir, "test", "2023-01-01", "test_post.md"
        )
        self.assertEqual(os.path.realpath(result), os.path.realpath(expected_path))


class TestMarkdownToHtml(BaseTestCase):
    """Test the markdown_to_html function."""

    def test_markdown_to_html_with_markdown_package(self):
        """Test markdown conversion when markdown package is available."""
        # Mock the markdown module at the system level
        mock_markdown_module = Mock()
        mock_markdown_module.markdown.return_value = "<p>Test HTML</p>"

        with patch.dict("sys.modules", {"markdown": mock_markdown_module}):
            result = utils.markdown_to_html("# Test Markdown")

            self.assertEqual(result, "<p>Test HTML</p>")
            mock_markdown_module.markdown.assert_called_once_with("# Test Markdown")

    def test_markdown_to_html_without_markdown_package(self):
        """Test markdown conversion when markdown package is not available."""
        # Mock the import to raise ImportError by removing markdown from sys.modules
        with patch.dict("sys.modules", {"markdown": None}):
            # Also patch the importlib.import_module to raise ImportError
            with patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'markdown'"),
            ):
                result = utils.markdown_to_html("# Test Markdown")

                expected = "<html><body><pre># Test Markdown</pre></body></html>"
                self.assertEqual(result, expected)


class TestDownloadMedia(TempDirTestCase):
    """Test the download_media function."""

    @patch("reddit_utils.requests.get")
    def test_download_media_success(self, mock_get):
        """Test successful media download."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_get.return_value.__enter__.return_value = mock_response

        test_file = os.path.join(self.temp_dir, "test_media.jpg")
        result = utils.download_media("https://example.com/image.jpg", test_file)

        self.assertTrue(result)
        self.assertTrue(os.path.exists(test_file))

        with open(test_file, "rb") as f:
            content = f.read()
            self.assertEqual(content, b"chunk1chunk2")

    @patch("reddit_utils.requests.get")
    def test_download_media_network_error(self, mock_get):
        """Test media download with network error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        test_file = os.path.join(self.temp_dir, "test_media.jpg")
        result = utils.download_media("https://example.com/image.jpg", test_file)

        self.assertFalse(result)
        self.assertFalse(os.path.exists(test_file))

    @patch("reddit_utils.requests.get")
    def test_download_media_http_error(self, mock_get):
        """Test media download with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value.__enter__.return_value = mock_response

        test_file = os.path.join(self.temp_dir, "test_media.jpg")
        result = utils.download_media("https://example.com/image.jpg", test_file)

        self.assertFalse(result)


class TestGenerateUniqueMediaFilename(TempDirTestCase):
    """Test the generate_unique_media_filename function."""

    def test_generate_unique_media_filename_no_collision(self):
        """Test generating media filename when no collision exists."""
        url = "https://example.com/video.mp4"
        result = utils.generate_unique_media_filename(url, self.temp_dir)

        expected = os.path.join(self.temp_dir, "video.mp4")
        self.assertEqual(result, expected)

    def test_generate_unique_media_filename_with_collision(self):
        """Test generating media filename when collision exists."""
        url = "https://example.com/video.mp4"

        # Create existing file to cause collision
        existing_file = os.path.join(self.temp_dir, "video.mp4")
        with open(existing_file, "w") as f:
            f.write("existing")

        result = utils.generate_unique_media_filename(url, self.temp_dir)

        expected = os.path.join(self.temp_dir, "video_1.mp4")
        self.assertEqual(result, expected)

    def test_generate_unique_media_filename_multiple_collisions(self):
        """Test generating media filename with multiple collisions."""
        url = "https://example.com/video.mp4"

        # Create multiple existing files
        for i in range(3):
            if i == 0:
                filename = "video.mp4"
            else:
                filename = f"video_{i}.mp4"
            existing_file = os.path.join(self.temp_dir, filename)
            with open(existing_file, "w") as f:
                f.write(f"existing {i}")

        result = utils.generate_unique_media_filename(url, self.temp_dir)

        expected = os.path.join(self.temp_dir, "video_3.mp4")
        self.assertEqual(result, expected)

    def test_generate_unique_media_filename_no_extension(self):
        """Test generating media filename when URL has no file extension."""
        url = "https://example.com/video"
        result = utils.generate_unique_media_filename(url, self.temp_dir)

        # Should generate a default filename with timestamp
        self.assertTrue(result.startswith(os.path.join(self.temp_dir, "media_")))
        self.assertTrue(result.endswith(".mp4"))

    def test_generate_unique_media_filename_empty_path(self):
        """Test generating media filename when URL path is empty."""
        url = "https://example.com/"
        result = utils.generate_unique_media_filename(url, self.temp_dir)

        # Should generate a default filename with timestamp
        self.assertTrue(result.startswith(os.path.join(self.temp_dir, "media_")))
        self.assertTrue(result.endswith(".mp4"))

    def test_generate_unique_media_filename_complex_extension(self):
        """Test generating media filename with complex file extensions."""
        url = "https://example.com/video.webm"
        result = utils.generate_unique_media_filename(url, self.temp_dir)

        expected = os.path.join(self.temp_dir, "video.webm")
        self.assertEqual(result, expected)

    def test_generate_unique_media_filename_query_params(self):
        """Test generating media filename with query parameters in URL."""
        url = "https://example.com/video.mp4?quality=720p&source=reddit"
        result = utils.generate_unique_media_filename(url, self.temp_dir)

        expected = os.path.join(self.temp_dir, "video.mp4")
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
