"""
Comprehensive tests for rate limiting and caching functionality in reddit_utils.py.
"""

import sys
import os
import unittest
from unittest.mock import patch, Mock, MagicMock
import time
import requests

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import reddit_utils as utils
from .test_utils import BaseTestCase, MockFactory


class TestRateLimiter(BaseTestCase):
    """Comprehensive tests for RateLimiter class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Reset global rate limiter
        utils._rate_limiter = None

    def test_rate_limiter_initialization_default(self):
        """Test RateLimiter initialization with default values."""
        limiter = utils.RateLimiter()

        self.assertEqual(limiter.max_requests, 60)
        self.assertEqual(limiter.window_seconds, 60)
        self.assertEqual(limiter.requests, [])

    def test_rate_limiter_initialization_custom(self):
        """Test RateLimiter initialization with custom values."""
        limiter = utils.RateLimiter(max_requests=30, window_seconds=120)

        self.assertEqual(limiter.max_requests, 30)
        self.assertEqual(limiter.window_seconds, 120)

    def test_rate_limiter_initialization_with_mock_objects(self):
        """Test RateLimiter handles Mock objects during testing."""
        mock_max_requests = Mock()
        mock_window_seconds = Mock()

        limiter = utils.RateLimiter(
            max_requests=mock_max_requests, window_seconds=mock_window_seconds
        )

        # Should fall back to defaults when Mock objects are passed
        self.assertEqual(limiter.max_requests, 60)
        self.assertEqual(limiter.window_seconds, 60)

    @patch("time.time")
    def test_rate_limiter_allows_initial_requests(self, mock_time):
        """Test that rate limiter allows initial requests."""
        mock_time.return_value = 1000.0

        limiter = utils.RateLimiter(max_requests=5, window_seconds=60)

        for i in range(5):
            self.assertTrue(limiter.is_allowed())

        # Should have recorded all requests
        self.assertEqual(len(limiter.requests), 5)

    @patch("time.time")
    def test_rate_limiter_blocks_excess_requests(self, mock_time):
        """Test that rate limiter blocks requests exceeding limit."""
        mock_time.return_value = 1000.0

        limiter = utils.RateLimiter(max_requests=3, window_seconds=60)

        # First 3 requests should be allowed
        for i in range(3):
            self.assertTrue(limiter.is_allowed())

        # 4th request should be blocked
        self.assertFalse(limiter.is_allowed())

    @patch("time.time")
    def test_rate_limiter_window_cleanup(self, mock_time):
        """Test that rate limiter cleans up old requests outside the window."""
        limiter = utils.RateLimiter(max_requests=2, window_seconds=60)

        # First request at time 1000
        mock_time.return_value = 1000.0
        self.assertTrue(limiter.is_allowed())

        # Second request at time 1010
        mock_time.return_value = 1010.0
        self.assertTrue(limiter.is_allowed())

        # Third request at time 1020 should be blocked (both previous requests still in window)
        mock_time.return_value = 1020.0
        self.assertFalse(limiter.is_allowed())

        # Fourth request at time 1065 should be allowed (first request now outside 60s window)
        mock_time.return_value = 1065.0
        self.assertTrue(limiter.is_allowed())

    @patch("time.time")
    def test_rate_limiter_wait_time_calculation(self, mock_time):
        """Test wait time calculation."""
        mock_time.return_value = 1000.0

        limiter = utils.RateLimiter(max_requests=1, window_seconds=60)

        # Make a request
        self.assertTrue(limiter.is_allowed())

        # Calculate wait time for next request
        mock_time.return_value = 1030.0  # 30 seconds later
        wait_time = limiter.wait_time()

        # Should wait 30 more seconds (60 - 30 = 30)
        self.assertEqual(wait_time, 30.0)

    @patch("time.time")
    def test_rate_limiter_wait_time_no_wait_needed(self, mock_time):
        """Test wait time when no waiting is needed."""
        mock_time.return_value = 1000.0

        limiter = utils.RateLimiter(max_requests=1, window_seconds=60)

        # Make a request
        self.assertTrue(limiter.is_allowed())

        # Check wait time after window has passed
        mock_time.return_value = 1065.0  # 65 seconds later
        wait_time = limiter.wait_time()

        # Should not need to wait
        self.assertEqual(wait_time, 0)

    def test_rate_limiter_wait_time_empty_requests(self):
        """Test wait time with no previous requests."""
        limiter = utils.RateLimiter(max_requests=1, window_seconds=60)

        wait_time = limiter.wait_time()
        self.assertEqual(wait_time, 0)

    def test_configure_performance_with_settings(self):
        """Test configure_performance with settings object."""
        mock_settings = Mock()
        mock_settings.rate_limit_requests_per_minute = 45
        mock_settings.cache_ttl_seconds = 600
        mock_settings.max_cache_entries = 2000

        utils.configure_performance(mock_settings)

        # Test that global rate limiter was configured
        rate_limiter = utils._get_rate_limiter()
        self.assertEqual(rate_limiter.max_requests, 45)
        self.assertEqual(rate_limiter.window_seconds, 60)

        # Test that cache settings were configured
        self.assertEqual(utils._cache_ttl_seconds, 600)
        self.assertEqual(utils._max_cache_entries, 2000)

    def test_configure_performance_with_mock_settings(self):
        """Test configure_performance handles Mock objects in settings."""
        mock_settings = Mock()
        # Mock objects that aren't integers
        mock_settings.rate_limit_requests_per_minute = Mock()
        mock_settings.cache_ttl_seconds = Mock()
        mock_settings.max_cache_entries = Mock()

        utils.configure_performance(mock_settings)

        # Should fall back to defaults
        rate_limiter = utils._get_rate_limiter()
        self.assertEqual(rate_limiter.max_requests, 30)  # Default fallback
        self.assertEqual(utils._cache_ttl_seconds, 300)  # Default fallback
        self.assertEqual(utils._max_cache_entries, 1000)  # Default fallback

    def test_get_rate_limiter_creates_default(self):
        """Test that _get_rate_limiter creates default instance if none configured."""
        utils._rate_limiter = None

        rate_limiter = utils._get_rate_limiter()

        self.assertIsNotNone(rate_limiter)
        self.assertEqual(rate_limiter.max_requests, 30)
        self.assertEqual(rate_limiter.window_seconds, 60)


class TestCachingFunctionality(BaseTestCase):
    """Comprehensive tests for caching functionality."""

    def setUp(self):
        """Set up test fixtures and clear cache."""
        super().setUp()
        # Clear global cache
        utils._json_cache.clear()
        utils._cache_timestamps.clear()
        # Reset cache settings
        utils._cache_ttl_seconds = 300
        utils._max_cache_entries = 1000

    @patch("time.time")
    @patch("reddit_utils.requests.get")
    def test_cache_stores_successful_requests(self, mock_get, mock_time):
        """Test that successful requests are cached."""
        mock_time.return_value = 1000.0

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "test_data"}
        mock_get.return_value = mock_response

        # Mock rate limiter to always allow
        with patch("reddit_utils._get_rate_limiter") as mock_get_limiter:
            mock_limiter = Mock()
            mock_limiter.is_allowed.return_value = True
            mock_get_limiter.return_value = mock_limiter

            url = "https://reddit.com/r/test/comments/123/post"
            result = utils.download_post_json(url)

            self.assertEqual(result, {"data": "test_data"})

            # Check that cache was populated
            cache_key = f"{url}.json:False"
            self.assertIn(cache_key, utils._json_cache)
            self.assertIn(cache_key, utils._cache_timestamps)

    @patch("time.time")
    @patch("reddit_utils.requests.get")
    def test_cache_retrieval_within_ttl(self, mock_get, mock_time):
        """Test that cached data is returned within TTL."""
        mock_time.return_value = 1000.0

        # Pre-populate cache
        cache_key = "https://reddit.com/r/test/comments/123/post.json:False"
        cached_data = {"data": "cached_data"}
        utils._json_cache[cache_key] = cached_data
        utils._cache_timestamps[cache_key] = 1000.0

        # Set TTL to 300 seconds
        utils._cache_ttl_seconds = 300

        # Request within TTL (200 seconds later)
        mock_time.return_value = 1200.0

        url = "https://reddit.com/r/test/comments/123/post"
        result = utils.download_post_json(url)

        # Should return cached data without making HTTP request
        self.assertEqual(result, cached_data)
        mock_get.assert_not_called()

    @patch("time.time")
    @patch("reddit_utils.requests.get")
    def test_cache_expiration_beyond_ttl(self, mock_get, mock_time):
        """Test that expired cache entries trigger new requests."""
        # Pre-populate cache
        cache_key = "https://reddit.com/r/test/comments/123/post.json:False"
        cached_data = {"data": "cached_data"}
        utils._json_cache[cache_key] = cached_data
        utils._cache_timestamps[cache_key] = 1000.0

        # Set TTL to 300 seconds
        utils._cache_ttl_seconds = 300

        # Request after TTL (400 seconds later)
        mock_time.return_value = 1400.0

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "fresh_data"}
        mock_get.return_value = mock_response

        # Mock rate limiter
        with patch("reddit_utils._get_rate_limiter") as mock_get_limiter:
            mock_limiter = Mock()
            mock_limiter.is_allowed.return_value = True
            mock_get_limiter.return_value = mock_limiter

            url = "https://reddit.com/r/test/comments/123/post"
            result = utils.download_post_json(url)

            # Should return fresh data and make HTTP request
            self.assertEqual(result, {"data": "fresh_data"})
            mock_get.assert_called_once()

    @patch("time.time")
    def test_cache_cleanup_expired_entries(self, mock_time):
        """Test that cache cleanup removes expired entries."""
        mock_time.return_value = 1000.0

        # Add some cache entries with different timestamps
        utils._json_cache["key1"] = {"data": "data1"}
        utils._cache_timestamps["key1"] = 500.0  # Old, should be removed

        utils._json_cache["key2"] = {"data": "data2"}
        utils._cache_timestamps["key2"] = 800.0  # Recent, should be kept

        utils._cache_ttl_seconds = 300

        # Trigger cleanup
        utils._cleanup_cache()

        # key1 should be removed (1000 - 500 = 500s > 300s TTL)
        self.assertNotIn("key1", utils._json_cache)
        self.assertNotIn("key1", utils._cache_timestamps)

        # key2 should be kept (1000 - 800 = 200s < 300s TTL)
        self.assertIn("key2", utils._json_cache)
        self.assertIn("key2", utils._cache_timestamps)

    @patch("time.time")
    def test_cache_size_limit_enforcement(self, mock_time):
        """Test that cache enforces size limits by removing oldest entries."""
        mock_time.return_value = 1000.0

        # Set small cache limit
        original_max_entries = utils._max_cache_entries
        utils._max_cache_entries = 2

        try:
            # Add 3 entries (exceeds limit of 2)
            utils._json_cache["key1"] = {"data": "data1"}
            utils._cache_timestamps["key1"] = 900.0  # Oldest

            utils._json_cache["key2"] = {"data": "data2"}
            utils._cache_timestamps["key2"] = 950.0  # Middle

            utils._json_cache["key3"] = {"data": "data3"}
            utils._cache_timestamps["key3"] = 1000.0  # Newest

            # Trigger cleanup
            utils._cleanup_cache()

            # Should keep only 2 newest entries
            self.assertNotIn("key1", utils._json_cache)  # Oldest removed
            self.assertIn("key2", utils._json_cache)  # Kept
            self.assertIn("key3", utils._json_cache)  # Kept

            self.assertEqual(len(utils._json_cache), 2)

        finally:
            # Restore original limit
            utils._max_cache_entries = original_max_entries

    @patch("time.time")
    def test_cache_size_limit_with_mock_max_entries(self, mock_time):
        """Test cache size limit handling with Mock object."""
        mock_time.return_value = 1000.0

        # Set max_cache_entries to a Mock object (simulates test environment)
        original_max_entries = utils._max_cache_entries
        utils._max_cache_entries = Mock()

        try:
            # Add entries
            utils._json_cache["key1"] = {"data": "data1"}
            utils._cache_timestamps["key1"] = 1000.0

            # Should handle Mock object gracefully and use default of 1000
            utils._cleanup_cache()

            # Entry should still be there (under default limit)
            self.assertIn("key1", utils._json_cache)

        finally:
            utils._max_cache_entries = original_max_entries

    def test_cache_key_generation_with_access_token(self):
        """Test that cache keys differentiate between authenticated and non-authenticated requests."""
        with patch("reddit_utils.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"data": "test"}
            mock_get.return_value = mock_response

            with patch("reddit_utils._get_rate_limiter") as mock_get_limiter:
                mock_limiter = Mock()
                mock_limiter.is_allowed.return_value = True
                mock_get_limiter.return_value = mock_limiter

                url = "https://reddit.com/r/test/comments/123/post"

                # Request without token
                utils.download_post_json(url, "")
                cache_key_no_token = f"{url}.json:False"
                self.assertIn(cache_key_no_token, utils._json_cache)

                # Request with token
                utils.download_post_json(url, "token123")
                cache_key_with_token = f"{url}.json:True"
                self.assertIn(cache_key_with_token, utils._json_cache)

                # Should have separate cache entries
                self.assertNotEqual(cache_key_no_token, cache_key_with_token)

    @patch("time.time")
    @patch("reddit_utils.requests.get")
    def test_cache_integration_with_rate_limiting(self, mock_get, mock_time):
        """Test integration between caching and rate limiting."""
        mock_time.return_value = 1000.0

        # Mock rate limiter that blocks after first request
        mock_limiter = Mock()
        mock_limiter.is_allowed.side_effect = [True, False]  # Allow first, block second
        mock_limiter.wait_time.return_value = 5.0

        with patch("reddit_utils._get_rate_limiter", return_value=mock_limiter):
            with patch("time.sleep") as mock_sleep:
                mock_response = Mock()
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {"data": "test"}
                mock_get.return_value = mock_response

                url = "https://reddit.com/r/test/comments/123/post"

                # First request should succeed and populate cache
                result1 = utils.download_post_json(url)
                self.assertEqual(result1, {"data": "test"})

                # Clear the mock to track second call
                mock_get.reset_mock()

                # Second request should return cached data without hitting rate limiter
                result2 = utils.download_post_json(url)
                self.assertEqual(result2, {"data": "test"})

                # Should not have made second HTTP request due to cache hit
                mock_get.assert_not_called()
                # Should not have slept due to cache hit
                mock_sleep.assert_not_called()


class TestRateLimitingIntegration(BaseTestCase):
    """Integration tests for rate limiting in download_post_json."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        utils._rate_limiter = None
        utils._json_cache.clear()
        utils._cache_timestamps.clear()

    @patch("time.sleep")
    @patch("reddit_utils.requests.get")
    def test_rate_limiting_triggers_sleep(self, mock_get, mock_sleep):
        """Test that rate limiting triggers sleep when limit is exceeded."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        # Mock rate limiter that blocks and requires waiting
        mock_limiter = Mock()
        mock_limiter.is_allowed.return_value = False
        mock_limiter.wait_time.return_value = 3.5

        with patch("reddit_utils._get_rate_limiter", return_value=mock_limiter):
            url = "https://reddit.com/r/test/comments/123/post"
            result = utils.download_post_json(url)

            # Should have slept for the wait time
            mock_sleep.assert_called_once_with(3.5)

            # Should still return the result
            self.assertEqual(result, {"data": "test"})

    @patch("reddit_utils.requests.get")
    def test_rate_limiting_allows_when_under_limit(self, mock_get):
        """Test that requests proceed normally when under rate limit."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        # Mock rate limiter that allows requests
        mock_limiter = Mock()
        mock_limiter.is_allowed.return_value = True

        with patch("reddit_utils._get_rate_limiter", return_value=mock_limiter):
            with patch("time.sleep") as mock_sleep:
                url = "https://reddit.com/r/test/comments/123/post"
                result = utils.download_post_json(url)

                # Should not have slept
                mock_sleep.assert_not_called()

                # Should return the result
                self.assertEqual(result, {"data": "test"})


if __name__ == "__main__":
    unittest.main()
