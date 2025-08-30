"""
Comprehensive integration tests covering complex scenarios across multiple modules.
Tests end-to-end workflows, error recovery, and edge case combinations.
"""

import sys
import os
import unittest
from unittest.mock import patch, Mock, MagicMock, mock_open
import json
import tempfile
import requests
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main
import reddit_utils as utils
from url_fetcher import UrlFetcher
from post_renderer import build_post_content
from filters import apply_filter
from settings import Settings
from auth import get_access_token
from .test_utils import BaseTestCase, TempDirTestCase, MockFactory, TestDataFixtures


class TestEndToEndWorkflows(TempDirTestCase):
    """Test complete end-to-end workflows."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_settings = MockFactory.create_settings_mock(
            default_save_location=self.temp_dir,
            login_on_startup=False,
            enable_media_downloads=False,
        )

    @patch("main.auth.get_access_token")
    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    @patch("main.UrlFetcher")
    @patch("main.Settings")
    @patch("main.CommandLineArgs")
    def test_complete_workflow_with_authentication_success(
        self,
        mock_cli_args,
        mock_settings_class,
        mock_url_fetcher,
        mock_valid_url,
        mock_download_json,
        mock_auth,
    ):
        """Test complete workflow from authentication to file output."""
        # Setup mocks
        mock_settings_class.return_value = self.mock_settings
        self.mock_settings.login_on_startup = True

        mock_cli_args_instance = MockFactory.create_cli_args_mock()
        mock_cli_args.return_value = mock_cli_args_instance

        mock_fetcher = Mock()
        mock_fetcher.urls = ["https://reddit.com/r/test/comments/123/post"]
        mock_url_fetcher.return_value = mock_fetcher

        mock_auth.return_value = "test_access_token"
        mock_valid_url.return_value = True

        # Mock complete Reddit response
        mock_post_data = TestDataFixtures.get_sample_post_data()
        mock_replies_data = [TestDataFixtures.get_sample_comment_data()]
        mock_download_json.return_value = [
            {"data": {"children": [{"data": mock_post_data}]}},
            {"data": {"children": mock_replies_data}},
        ]

        # Run main workflow
        main.main()

        # Verify authentication was called
        mock_auth.assert_called_once()

        # Verify URL fetcher was called with token
        mock_url_fetcher.assert_called_once()
        call_args = mock_url_fetcher.call_args
        self.assertEqual(call_args[0][2], "test_access_token")  # access_token parameter

        # Verify file was created
        expected_files = list(Path(self.temp_dir).rglob("*.md"))
        self.assertTrue(len(expected_files) > 0)

    @patch("main.auth.get_access_token")
    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    @patch("main.UrlFetcher")
    @patch("main.Settings")
    @patch("main.CommandLineArgs")
    def test_complete_workflow_with_authentication_failure_fallback(
        self,
        mock_cli_args,
        mock_settings_class,
        mock_url_fetcher,
        mock_valid_url,
        mock_download_json,
        mock_auth,
    ):
        """Test workflow continues gracefully when authentication fails."""
        # Setup mocks
        mock_settings_class.return_value = self.mock_settings
        self.mock_settings.login_on_startup = True

        mock_cli_args_instance = MockFactory.create_cli_args_mock()
        mock_cli_args.return_value = mock_cli_args_instance

        mock_fetcher = Mock()
        mock_fetcher.urls = ["https://reddit.com/r/test/comments/123/post"]
        mock_url_fetcher.return_value = mock_fetcher

        # Authentication fails
        mock_auth.return_value = ""
        mock_valid_url.return_value = True

        mock_post_data = TestDataFixtures.get_sample_post_data()
        mock_download_json.return_value = [
            {"data": {"children": [{"data": mock_post_data}]}},
            {"data": {"children": []}},
        ]

        # Run main workflow
        main.main()

        # Verify workflow continued without token
        mock_url_fetcher.assert_called_once()
        call_args = mock_url_fetcher.call_args
        self.assertEqual(call_args[0][2], "")  # empty access_token parameter

    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    def test_workflow_handles_network_errors_gracefully(
        self, mock_valid_url, mock_download_json
    ):
        """Test that network errors are handled gracefully without crashing."""
        mock_valid_url.return_value = True
        mock_download_json.side_effect = [
            requests.exceptions.ConnectionError("Network error"),
            None,  # Second URL also fails
        ]

        urls = [
            "https://reddit.com/r/test/comments/123/post1",
            "https://reddit.com/r/test/comments/456/post2",
        ]

        # Should not raise exception
        main._process_all_urls(urls, self.mock_settings, self.temp_dir, "")

        # Should have attempted both URLs
        self.assertEqual(mock_download_json.call_count, 2)

    @patch("main.build_post_content")
    @patch("main.utils.generate_filename")
    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    def test_workflow_handles_file_write_errors(
        self,
        mock_valid_url,
        mock_download_json,
        mock_generate_filename,
        mock_build_content,
    ):
        """Test workflow handles file write errors gracefully."""
        mock_valid_url.return_value = True

        mock_post_data = TestDataFixtures.get_sample_post_data()
        mock_download_json.return_value = [
            {"data": {"children": [{"data": mock_post_data}]}},
            {"data": {"children": []}},
        ]

        mock_generate_filename.return_value = (
            "/invalid/path/that/cannot/be/created/test.md"
        )
        mock_build_content.return_value = "# Test Content"

        # Should handle permission error gracefully
        result = main._process_single_url(
            index=1,
            url="https://reddit.com/r/test/comments/123/post",
            total=1,
            settings=self.mock_settings,
            base_save_dir=self.temp_dir,
            colors=["🟩"],
            access_token="",
        )

        # Should return False for failed processing
        self.assertFalse(result)


class TestCrossModuleInteractions(BaseTestCase):
    """Test interactions between different modules."""

    @patch("reddit_utils.download_post_json")
    def test_url_fetcher_uses_reddit_utils_correctly(self, mock_download_json):
        """Test that UrlFetcher properly uses reddit_utils functions."""
        mock_download_json.return_value = {
            "data": {
                "children": [{"data": {"permalink": "/r/python/comments/123/test/"}}]
            }
        }

        settings = MockFactory.create_settings_mock()
        cli_args = MockFactory.create_cli_args_mock()

        fetcher = UrlFetcher(settings, cli_args, "test_token", prompt_for_input=False)
        result = fetcher._fetch_posts_from_sub("r/python")

        # Should have called download_post_json with access token
        mock_download_json.assert_called_once()
        call_args = mock_download_json.call_args
        self.assertEqual(call_args[0][1], "test_token")

    @patch("post_renderer.apply_filter")
    @patch("post_renderer.utils.get_replies")
    def test_post_renderer_applies_filters_correctly(
        self, mock_get_replies, mock_apply_filter
    ):
        """Test that post renderer applies filters to comments."""
        mock_get_replies.return_value = {}
        mock_apply_filter.return_value = "[FILTERED BY KEYWORD]"

        post_data = TestDataFixtures.get_sample_post_data()
        replies_data = [TestDataFixtures.get_sample_comment_data()]

        settings = MockFactory.create_settings_mock(
            filtered_keywords=["spam"], filtered_message="[FILTERED BY KEYWORD]"
        )

        result = build_post_content(
            post_data=post_data,
            replies_data=replies_data,
            settings=settings,
            colors=["🟩"],
            url="https://reddit.com/test",
            target_path="/test/path",
        )

        # Should have applied filter to comment
        mock_apply_filter.assert_called()
        self.assertIn("[FILTERED BY KEYWORD]", result)

    def test_settings_and_reddit_utils_performance_integration(self):
        """Test that Settings properly configures reddit_utils performance settings."""
        settings_data = {
            "version": "1.0.0",
            "performance": {
                "rate_limit_requests_per_minute": 45,
                "cache_ttl_seconds": 600,
                "max_cache_entries": 2000,
            },
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(settings_data))):
            with patch("os.path.isfile", return_value=True):
                settings = Settings("test_settings.json")

                # Configure reddit_utils with these settings
                utils.configure_performance(settings)

                # Verify rate limiter was configured
                rate_limiter = utils._get_rate_limiter()
                self.assertEqual(rate_limiter.max_requests, 45)

                # Verify cache settings
                self.assertEqual(utils._cache_ttl_seconds, 600)
                self.assertEqual(utils._max_cache_entries, 2000)


class TestErrorRecoveryScenarios(BaseTestCase):
    """Test error recovery and graceful degradation scenarios."""

    def test_malformed_json_response_handling(self):
        """Test handling of malformed JSON responses from Reddit."""
        with patch("reddit_utils.requests.get") as mock_get:
            with patch("reddit_utils._get_rate_limiter") as mock_get_limiter:
                # Mock rate limiter
                mock_limiter = Mock()
                mock_limiter.is_allowed.return_value = True
                mock_get_limiter.return_value = mock_limiter

                # Mock malformed JSON response
                mock_response = Mock()
                mock_response.raise_for_status.return_value = None
                mock_response.json.side_effect = json.JSONDecodeError(
                    "Invalid JSON", "", 0
                )
                mock_get.return_value = mock_response

                result = utils.download_post_json(
                    "https://reddit.com/r/test/comments/123/post"
                )

                # Should handle error gracefully
                self.assertIsNone(result)

    def test_partial_data_structure_handling(self):
        """Test handling of partial or unexpected data structures."""
        # Test with missing post data
        incomplete_data = [
            {"data": {"children": []}},  # No post data
            {"data": {"children": []}},  # No replies
        ]

        result = main._process_single_url(
            index=1,
            url="https://reddit.com/r/test/comments/123/post",
            total=1,
            settings=MockFactory.create_settings_mock(),
            base_save_dir="/tmp",
            colors=["🟩"],
            access_token="",
        )

        # Should handle gracefully
        with patch("main.utils.valid_url", return_value=True):
            with patch("main.utils.download_post_json", return_value=incomplete_data):
                result = main._process_single_url(
                    index=1,
                    url="https://reddit.com/r/test/comments/123/post",
                    total=1,
                    settings=MockFactory.create_settings_mock(),
                    base_save_dir="/tmp",
                    colors=["🟩"],
                    access_token="",
                )
                self.assertFalse(result)

    @patch("filters._safe_compile_regex")
    def test_regex_compilation_failure_recovery(self, mock_compile_regex):
        """Test recovery from regex compilation failures in filters."""
        # Mock regex compilation failure
        mock_compile_regex.return_value = None  # Invalid regex

        result = apply_filter(
            author="test_user",
            text="This is a test comment",
            upvotes=10,
            filtered_keywords=[],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=["[invalid regex"],
            filtered_message="[FILTERED]",
        )

        # Should return original text when regex fails
        self.assertEqual(result, "This is a test comment")

    def test_memory_pressure_cache_cleanup(self):
        """Test cache cleanup under memory pressure scenarios."""
        # Simulate many cache entries
        original_max = utils._max_cache_entries
        utils._max_cache_entries = 5  # Very small limit

        try:
            # Add many entries
            for i in range(10):
                cache_key = f"test_key_{i}"
                utils._json_cache[cache_key] = {"data": f"test_data_{i}"}
                utils._cache_timestamps[cache_key] = 1000.0 + i

            # Trigger cleanup
            utils._cleanup_cache()

            # Should respect size limit
            self.assertLessEqual(len(utils._json_cache), 5)

        finally:
            utils._max_cache_entries = original_max
            utils._json_cache.clear()
            utils._cache_timestamps.clear()


class TestComplexDataScenarios(BaseTestCase):
    """Test handling of complex data scenarios."""

    def test_deeply_nested_comment_threads(self):
        """Test handling of deeply nested comment threads."""
        # Create deeply nested reply structure
        nested_reply = {"data": {"replies": {"data": {"children": []}}}}

        # Build nested structure 10 levels deep
        current_level = nested_reply
        for depth in range(10):
            child = {
                "data": {
                    "id": f"child_{depth}",
                    "depth": depth + 1,
                    "body": f"Reply at depth {depth + 1}",
                    "replies": {"data": {"children": []}} if depth < 9 else "",
                }
            }
            current_level["data"]["replies"]["data"]["children"] = [child]
            if depth < 9:
                current_level = child

        # Test with max depth limit
        result = utils.get_replies(nested_reply, max_depth=5)

        # Should only include replies up to max depth
        depths = [info["depth"] for info in result.values()]
        self.assertTrue(all(depth <= 5 for depth in depths))

    def test_unicode_content_handling(self):
        """Test handling of unicode content in posts and comments."""
        unicode_post_data = {
            "title": "Test with émojis 🚀 and ünïcödé",
            "author": "tëst_üsër",
            "selftext": "This post contains 中文, العربية, and русский text",
            "subreddit_name_prefixed": "r/tëst",
            "ups": 100,
            "created_utc": 1640995200,
        }

        unicode_reply_data = [
            {
                "data": {
                    "author": "üsér_ñãmé",
                    "body": "Comment with émojis 🎉 and special chars: àáâãäåæçèé",
                    "ups": 10,
                    "created_utc": 1640995800,
                    "replies": "",
                }
            }
        ]

        settings = MockFactory.create_settings_mock()

        result = build_post_content(
            post_data=unicode_post_data,
            replies_data=unicode_reply_data,
            settings=settings,
            colors=["🟩"],
            url="https://reddit.com/test",
            target_path="/test/path",
        )

        # Should handle unicode content without errors
        self.assertIn("émojis 🚀", result)
        self.assertIn("中文", result)
        self.assertIn("üsér_ñãmé", result)

    def test_large_dataset_processing(self):
        """Test processing of large datasets (many URLs, comments, etc.)."""
        # Generate large URL list
        large_url_list = [
            f"https://reddit.com/r/test{i}/comments/{i}/post{i}/" for i in range(100)
        ]

        settings = MockFactory.create_settings_mock()

        with patch("main.utils.valid_url", return_value=True):
            with patch("main.utils.download_post_json", return_value=None):
                with patch("time.sleep"):  # Skip sleep delays
                    # Should handle large dataset without memory issues
                    main._process_all_urls(large_url_list, settings, "/tmp", "")

    def test_concurrent_cache_access_simulation(self):
        """Test cache behavior under simulated concurrent access."""
        import threading
        import time

        # Clear cache
        utils._json_cache.clear()
        utils._cache_timestamps.clear()

        def cache_worker(worker_id):
            """Simulate concurrent cache operations."""
            for i in range(50):
                cache_key = f"worker_{worker_id}_key_{i}"
                utils._json_cache[cache_key] = {"data": f"worker_{worker_id}_data_{i}"}
                utils._cache_timestamps[cache_key] = time.time()

                # Trigger periodic cleanup
                if i % 10 == 0:
                    utils._cleanup_cache()

        # Run multiple workers (simulated concurrency)
        workers = []
        for worker_id in range(5):
            worker = threading.Thread(target=cache_worker, args=(worker_id,))
            workers.append(worker)
            worker.start()

        # Wait for all workers
        for worker in workers:
            worker.join()

        # Cache should still be in valid state
        self.assertIsInstance(utils._json_cache, dict)
        self.assertIsInstance(utils._cache_timestamps, dict)


if __name__ == "__main__":
    unittest.main()
