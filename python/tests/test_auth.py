import unittest
from unittest.mock import patch, Mock
import requests

from auth import get_access_token
from .test_utils import AuthTestCase, MockFactory, AssertionHelpers, TEST_USER_AGENTS


class TestAuth(AuthTestCase):
    """Comprehensive test suite for auth.py module."""

    @patch("auth.requests.post")
    def test_successful_authentication(self, mock_post):
        """Test successful authentication returns access token."""
        mock_post.return_value = MockFactory.create_auth_success_response(
            self.valid_token
        )

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, self.valid_token)
        AssertionHelpers.assert_auth_request_called_correctly(
            mock_post, self.client_id, self.client_secret
        )

    @patch("auth.requests.post")
    def test_authentication_missing_token_in_response(self, mock_post):
        """Test when response JSON doesn't contain access_token."""
        mock_post.return_value = MockFactory.create_auth_error_response("missing_token")

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
        mock_post.return_value = MockFactory.create_auth_error_response("http")

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_authentication_network_error(self, mock_post):
        """Test authentication with network connection error."""
        mock_post.side_effect = MockFactory.create_network_error_mock(
            requests.exceptions.ConnectionError, "Network unreachable"
        ).side_effect

        result = get_access_token(self.client_id, self.client_secret)

        self.assertEqual(result, "")

    @patch("auth.requests.post")
    def test_authentication_timeout_error(self, mock_post):
        """Test authentication with timeout error."""
        mock_post.side_effect = MockFactory.create_network_error_mock(
            requests.exceptions.Timeout, "Request timed out"
        ).side_effect

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
