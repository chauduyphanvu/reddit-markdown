"""
Additional edge case tests for auth.py module.
Focuses on scenarios not fully covered in the existing test_auth.py.
"""

import unittest
from unittest.mock import patch, Mock
import requests

from auth import get_access_token
from .test_utils import AuthTestCase, MockFactory


class TestAuthEdgeCases(AuthTestCase):
    """Additional edge case tests for auth module."""

    @patch("auth.requests.post")
    def test_authentication_json_decode_error_handling(self, mock_post):
        """Test that JSON decode errors are properly handled."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        # The function should handle JSON decode errors gracefully
        # Currently it doesn't catch ValueError, so this is a potential improvement
        with self.assertRaises(ValueError):
            get_access_token(self.client_id, self.client_secret)

    @patch("auth.requests.post")
    def test_authentication_attribute_error_handling(self, mock_post):
        """Test handling when response is not a dict."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = "not_a_dict"  # String instead of dict
        mock_post.return_value = mock_response

        # This will cause AttributeError when trying to call .get() on a string
        with self.assertRaises(AttributeError):
            get_access_token(self.client_id, self.client_secret)

    @patch("auth.requests.post")
    def test_authentication_with_response_status_code_handling(self, mock_post):
        """Test various HTTP status codes."""
        # Test 401 Unauthorized
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized"
        )
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        result = get_access_token(self.client_id, self.client_secret)
        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_authentication_with_unicode_credentials(self, mock_post):
        """Test authentication with Unicode characters in credentials."""
        unicode_client_id = "test_üñíçødé_client"
        unicode_client_secret = "secret_ñäñúñá"

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"access_token": "valid_token"}
        mock_post.return_value = mock_response

        result = get_access_token(unicode_client_id, unicode_client_secret)

        self.assertEqual(result, "valid_token")

        # Verify Unicode credentials were passed correctly
        call_args = mock_post.call_args
        auth = call_args[1]["auth"]
        self.assertEqual(auth.username, unicode_client_id)
        self.assertEqual(auth.password, unicode_client_secret)

    @patch("auth.requests.post")
    def test_authentication_with_very_long_credentials(self, mock_post):
        """Test authentication with very long credentials."""
        long_client_id = "x" * 1000
        long_client_secret = "y" * 1000

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"access_token": "valid_token"}
        mock_post.return_value = mock_response

        result = get_access_token(long_client_id, long_client_secret)

        self.assertEqual(result, "valid_token")

    @patch("auth.requests.post")
    def test_authentication_with_ssl_error(self, mock_post):
        """Test authentication with SSL certificate error."""
        mock_post.side_effect = requests.exceptions.SSLError(
            "SSL certificate verification failed"
        )

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_authentication_with_proxy_error(self, mock_post):
        """Test authentication with proxy error."""
        mock_post.side_effect = requests.exceptions.ProxyError(
            "Proxy connection failed"
        )

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_authentication_response_with_extra_fields(self, mock_post):
        """Test response with additional fields beyond access_token."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "access_token": "valid_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "scope": "*",
            "extra_field": "extra_value",
        }
        mock_post.return_value = mock_response

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "valid_token")

    @patch("auth.requests.post")
    def test_authentication_with_numeric_token(self, mock_post):
        """Test when access_token is returned as a number instead of string."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"access_token": 123456}
        mock_post.return_value = mock_response

        result = get_access_token(self.client_id, self.client_secret)

        # Should still work since Python handles type conversion
        self.assertEqual(result, 123456)


if __name__ == "__main__":
    unittest.main()
