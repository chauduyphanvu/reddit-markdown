import sys
import os
import unittest
from unittest.mock import patch, Mock
import requests

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auth import get_access_token
from .test_utils import BaseTestCase, MockFactory, TEST_USER_AGENTS


class TestAuth(BaseTestCase):
    """Comprehensive test suite for auth.py module."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.valid_token = "test_access_token_123"

    @patch("auth.requests.post")
    def test_successful_authentication(self, mock_post):
        """Test successful authentication returns access token."""
        # Mock successful response using MockFactory
        mock_post.return_value = MockFactory.create_http_response(
            json_data={"access_token": self.valid_token}
        )

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, self.valid_token)
        mock_post.assert_called_once()

        # Verify the correct API call was made
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://www.reddit.com/api/v1/access_token")
        self.assertEqual(call_args[1]["data"]["grant_type"], "client_credentials")
        self.assertEqual(
            call_args[1]["headers"]["User-Agent"], TEST_USER_AGENTS["default"]
        )
        self.assertEqual(call_args[1]["timeout"], 10)

        # Verify auth was passed correctly
        auth = call_args[1]["auth"]
        self.assertEqual(auth.username, self.client_id)
        self.assertEqual(auth.password, self.client_secret)

    @patch("auth.requests.post")
    def test_authentication_missing_token_in_response(self, mock_post):
        """Test when response JSON doesn't contain access_token."""
        mock_post.return_value = MockFactory.create_http_response(
            json_data={"error": "invalid_grant"}
        )

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_authentication_empty_token_in_response(self, mock_post):
        """Test when response JSON contains empty access_token."""
        mock_post.return_value = MockFactory.create_http_response(
            json_data={"access_token": ""}
        )

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_authentication_http_error(self, mock_post):
        """Test authentication with HTTP error (4xx, 5xx)."""
        mock_post.return_value = MockFactory.create_http_response(
            raise_for_status=requests.exceptions.HTTPError("401 Unauthorized")
        )

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_authentication_network_error(self, mock_post):
        """Test authentication with network connection error."""
        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Network unreachable"
        )

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_authentication_timeout_error(self, mock_post):
        """Test authentication with timeout error."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_authentication_json_decode_error(self, mock_post):
        """Test authentication when response JSON is malformed."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        # The ValueError from json() is not caught by RequestException,
        # so this will actually cause an unhandled exception
        with self.assertRaises(ValueError):
            get_access_token(self.client_id, self.client_secret)

    @patch("auth.requests.post")
    def test_authentication_generic_request_exception(self, mock_post):
        """Test authentication with generic requests exception."""
        mock_post.side_effect = requests.exceptions.RequestException("Generic error")

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    def test_empty_client_credentials(self):
        """Test with empty client ID and secret."""
        result = get_access_token("", "")
        self.assertEqual(result, "")

    def test_none_client_credentials(self):
        """Test with None client credentials."""
        result = get_access_token(None, None)
        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_response_with_null_access_token(self, mock_post):
        """Test when response JSON contains null access_token."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"access_token": None}
        mock_post.return_value = mock_response

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_successful_authentication_with_whitespace_token(self, mock_post):
        """Test successful authentication with token containing whitespace."""
        token_with_whitespace = "  " + self.valid_token + "  "
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"access_token": token_with_whitespace}
        mock_post.return_value = mock_response

        result = get_access_token(self.client_id, self.client_secret)

        # Should return the token as-is (the function doesn't strip whitespace)
        self.assertEqual(result, token_with_whitespace)

    @patch("auth.requests.post")
    def test_authentication_with_non_dict_json_response(self, mock_post):
        """Test when JSON response is not a dictionary."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = ["invalid", "response"]
        mock_post.return_value = mock_response

        # The actual implementation will try to call .get() on a list, which will raise AttributeError
        # This is not caught by RequestException, so it will cause an unhandled exception
        with self.assertRaises(AttributeError):
            get_access_token(self.client_id, self.client_secret)

    @patch("auth.requests.post")
    def test_authentication_with_special_characters_in_credentials(self, mock_post):
        """Test authentication with special characters in credentials."""
        special_client_id = "test!@#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        special_client_secret = "secret!@#$%^&*()_+-={}[]|\\:;\"'<>?,./"

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"access_token": self.valid_token}
        mock_post.return_value = mock_response

        result = get_access_token(special_client_id, special_client_secret)

        self.assertEqual(result, self.valid_token)

        # Verify special characters were passed correctly in auth
        call_args = mock_post.call_args
        auth = call_args[1]["auth"]
        self.assertEqual(auth.username, special_client_id)
        self.assertEqual(auth.password, special_client_secret)


if __name__ == "__main__":
    unittest.main()
