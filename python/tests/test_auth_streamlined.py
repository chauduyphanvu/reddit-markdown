"""
Streamlined auth tests focusing on behavior, not implementation.
"""

import unittest
from unittest.mock import patch, Mock
import requests

from auth import get_access_token


class TestAuthBehavior(unittest.TestCase):
    """Test authentication behavior and expected outcomes."""

    @patch("requests.post")
    def test_successful_authentication_returns_token(self, mock_post):
        """Valid credentials should return an access token."""
        expected_token = "valid_access_token_12345"

        mock_response = Mock()
        mock_response.json.return_value = {"access_token": expected_token}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        token = get_access_token("valid_client_id", "valid_client_secret")

        self.assertEqual(token, expected_token)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)

    @patch("requests.post")
    def test_invalid_credentials_return_empty(self, mock_post):
        """Invalid credentials should return empty string."""
        # Simulate HTTP 401 Unauthorized
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "401 Unauthorized"
        )
        mock_post.return_value = mock_response

        token = get_access_token("invalid_id", "invalid_secret")

        self.assertEqual(token, "")

    @patch("requests.post")
    def test_network_error_returns_empty(self, mock_post):
        """Network errors should return empty string, not crash."""
        mock_post.side_effect = requests.ConnectionError("Network unreachable")

        token = get_access_token("client_id", "client_secret")

        self.assertEqual(token, "")

    def test_empty_credentials_return_empty(self):
        """Empty credentials should return empty string without making API calls."""
        # No mocking needed - should not make any HTTP requests
        token1 = get_access_token("", "")
        token2 = get_access_token(None, None)

        self.assertEqual(token1, "")
        self.assertEqual(token2, "")

    @patch("requests.post")
    def test_authentication_uses_correct_endpoint(self, mock_post):
        """Authentication should use Reddit's OAuth endpoint."""
        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "test_token"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        get_access_token("test_id", "test_secret")

        # Verify the correct Reddit OAuth endpoint was called
        call_args = mock_post.call_args
        self.assertIn("reddit.com", call_args[0][0])
        self.assertIn("access_token", call_args[0][0])

        # Verify credentials were passed correctly
        self.assertIn("auth", call_args[1])
        auth = call_args[1]["auth"]
        self.assertEqual(auth.username, "test_id")
        self.assertEqual(auth.password, "test_secret")


class TestAuthIntegration(unittest.TestCase):
    """Integration-style tests for authentication flow."""

    @patch("requests.post")
    def test_auth_token_format_validation(self, mock_post):
        """Returned tokens should be valid format."""
        test_tokens = [
            "AbC123-XyZ_789",  # Typical OAuth token
            "a" * 50,  # Long token
            "short",  # Short token
        ]

        for test_token in test_tokens:
            with self.subTest(token=test_token):
                mock_response = Mock()
                mock_response.json.return_value = {"access_token": test_token}
                mock_response.raise_for_status.return_value = None
                mock_post.return_value = mock_response

                result = get_access_token("client_id", "client_secret")

                self.assertEqual(result, test_token)
                # Token should be non-empty string
                self.assertIsInstance(result, str)
                if test_token:  # Non-empty input should produce non-empty output
                    self.assertGreater(len(result), 0)

    @patch("requests.post")
    def test_error_handling_graceful_degradation(self, mock_post):
        """Authentication errors should degrade gracefully."""
        error_scenarios = [
            requests.Timeout("Request timed out"),
            requests.ConnectionError("Connection failed"),
            requests.HTTPError("HTTP 500 Internal Server Error"),
            requests.RequestException("Generic request error"),
        ]

        for error in error_scenarios:
            with self.subTest(error=type(error).__name__):
                mock_post.side_effect = error

                # Should not raise exception, should return empty string
                result = get_access_token("test_id", "test_secret")
                self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
