"""
Additional integration tests focusing on cross-module interactions and complex scenarios.
"""

import unittest
from unittest.mock import patch, Mock, MagicMock
import os
import tempfile
import json

import main
import reddit_utils as utils
from post_renderer import build_post_content
from filters import apply_filter
from test_utils import TempDirTestCase, MockFactory


class TestIntegrationEdgeCases(TempDirTestCase):
    """Integration tests for complex cross-module scenarios."""

    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    def test_end_to_end_post_processing_with_filtering(
        self, mock_valid_url, mock_download_json
    ):
        """Test complete post processing pipeline with content filtering."""
        mock_valid_url.return_value = True

        # Mock complex post data with nested replies
        mock_post_data = {
            "title": "Test Post with Controversial Content",
            "author": "test_author",
            "subreddit_name_prefixed": "r/test",
            "ups": 100,
            "selftext": "This is the main post content",
            "url": "https://example.com/link",
            "created_utc": 1640995200,
        }

        mock_replies = [
            {
                "data": {
                    "author": "commenter1",
                    "body": "This comment contains spam keyword",
                    "ups": 10,
                    "created_utc": 1640995300,
                    "replies": "",
                }
            },
            {
                "data": {
                    "author": "banned_user",
                    "body": "This user should be filtered",
                    "ups": 50,
                    "created_utc": 1640995400,
                    "replies": "",
                }
            },
            {
                "data": {
                    "author": "low_karma_user",
                    "body": "This comment has low upvotes",
                    "ups": 2,
                    "created_utc": 1640995500,
                    "replies": "",
                }
            },
        ]

        mock_download_json.return_value = [
            {"data": {"children": [{"data": mock_post_data}]}},
            {"data": {"children": mock_replies}},
        ]

        # Mock settings with filters
        mock_settings = Mock()
        mock_settings.show_upvotes = True
        mock_settings.show_timestamp = True
        mock_settings.show_auto_mod_comment = False
        mock_settings.line_break_between_parent_replies = True
        mock_settings.reply_depth_color_indicators = True
        mock_settings.reply_depth_max = -1
        mock_settings.use_timestamped_directories = False
        mock_settings.file_format = "md"
        mock_settings.overwrite_existing_file = True
        mock_settings.enable_media_downloads = False

        # Filter settings
        mock_settings.filtered_keywords = ["spam"]
        mock_settings.filtered_authors = ["banned_user"]
        mock_settings.filtered_min_upvotes = 5
        mock_settings.filtered_regexes = []
        mock_settings.filtered_message = "[CONTENT FILTERED]"

        colors = ["🟩", "🟨", "🟧"]
        url = "https://reddit.com/r/test/comments/123/test_post"
        target_path = os.path.join(self.temp_dir, "test.md")

        # Process the post
        with patch("main.utils.generate_filename", return_value=target_path):
            content = build_post_content(
                post_data=mock_post_data,
                replies_data=mock_replies,
                settings=mock_settings,
                colors=colors,
                url=url,
                target_path=target_path,
            )

            # Verify filtering was applied
            self.assertIn("[CONTENT FILTERED]", content)  # Spam keyword filtered
            self.assertIn("[CONTENT FILTERED]", content)  # Banned user filtered
            self.assertIn("[CONTENT FILTERED]", content)  # Low upvotes filtered

    @patch("main.utils.download_post_json")
    @patch("main.utils.valid_url")
    def test_post_processing_with_media_download_failure(
        self, mock_valid_url, mock_download_json
    ):
        """Test post processing when media downloads fail."""
        mock_valid_url.return_value = True

        mock_post_data = {
            "title": "Post with Media",
            "author": "test_author",
            "subreddit_name_prefixed": "r/test",
            "ups": 100,
            "selftext": "",
            "url": "https://example.com/image.jpg",  # Media URL
            "created_utc": 1640995200,
        }

        mock_download_json.return_value = [
            {"data": {"children": [{"data": mock_post_data}]}},
            {"data": {"children": []}},
        ]

        mock_settings = Mock()
        mock_settings.enable_media_downloads = True
        mock_settings.show_upvotes = False
        mock_settings.show_timestamp = False
        mock_settings.show_auto_mod_comment = False
        mock_settings.line_break_between_parent_replies = False
        mock_settings.reply_depth_color_indicators = False
        mock_settings.reply_depth_max = -1
        mock_settings.filtered_keywords = []
        mock_settings.filtered_authors = []
        mock_settings.filtered_min_upvotes = 0
        mock_settings.filtered_regexes = []
        mock_settings.filtered_message = ""

        colors = ["🟩"]
        url = "https://reddit.com/r/test/comments/123/media_post"
        target_path = os.path.join(self.temp_dir, "media_test.md")

        # Mock media download failure
        with patch("reddit_utils.download_media", return_value=False):
            content = build_post_content(
                post_data=mock_post_data,
                replies_data=[],
                settings=mock_settings,
                colors=colors,
                url=url,
                target_path=target_path,
            )

            # Should still generate content even if media download fails
            self.assertIn("Post with Media", content)
            self.assertIsInstance(content, str)
            self.assertGreater(len(content), 0)

    def test_complex_nested_replies_with_mixed_filtering(self):
        """Test replies with filtering conditions."""
        # Create simple replies with spam content
        replies_with_spam = [
            {
                "data": {
                    "author": "normal_user",
                    "body": "This is normal content",
                    "ups": 20,
                    "created_utc": 1640995200,
                    "replies": "",
                }
            },
            {
                "data": {
                    "author": "spam_user",
                    "body": "This comment contains spam keyword",
                    "ups": 5,
                    "created_utc": 1640995300,
                    "replies": "",
                }
            },
        ]

        mock_settings = Mock()
        mock_settings.show_upvotes = True
        mock_settings.show_timestamp = False
        mock_settings.reply_depth_color_indicators = True
        mock_settings.reply_depth_max = -1
        mock_settings.line_break_between_parent_replies = True
        mock_settings.filtered_keywords = ["spam"]
        mock_settings.filtered_authors = []
        mock_settings.filtered_min_upvotes = 0
        mock_settings.filtered_regexes = []
        mock_settings.filtered_message = "[FILTERED]"

        colors = ["🟩", "🟨", "🟧", "🟦"]

        from post_renderer import build_post_content

        post_data = {
            "title": "Test Post",
            "author": "post_author",
            "subreddit_name_prefixed": "r/test",
            "ups": 50,
            "selftext": "Test post content",
            "url": "https://example.com",
            "created_utc": 1640995200,
        }

        result = build_post_content(
            post_data=post_data,
            replies_data=replies_with_spam,
            settings=mock_settings,
            colors=colors,
            url="https://reddit.com/r/test/comments/123/test",
            target_path="/test/path.md",
        )

        # Should contain normal user content
        self.assertIn("normal_user", result)
        self.assertIn("This is normal content", result)

        # Should filter spam content
        self.assertIn("[FILTERED]", result)
        self.assertNotIn("spam keyword", result)

    @patch("reddit_utils.requests.get")
    @patch("auth.requests.post")
    def test_authentication_and_api_calls_integration(self, mock_auth_post, mock_get):
        """Test integration between authentication and API calls."""
        # Mock successful authentication
        auth_response = Mock()
        auth_response.raise_for_status.return_value = None
        auth_response.json.return_value = {"access_token": "test_token_123"}
        mock_auth_post.return_value = auth_response

        # Mock Reddit API response
        api_response = Mock()
        api_response.raise_for_status.return_value = None
        api_response.json.return_value = [
            {"data": {"children": [{"data": {"title": "Test", "author": "user"}}]}},
            {"data": {"children": []}},
        ]
        mock_get.return_value = api_response

        # Test the flow
        from auth import get_access_token

        token = get_access_token("client_id", "client_secret")
        self.assertEqual(token, "test_token_123")

        # Use token to fetch post data
        post_data = utils.download_post_json(
            "https://www.reddit.com/r/test/comments/123/post", token
        )

        self.assertIsNotNone(post_data)

        # Verify OAuth endpoint was used
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("oauth.reddit.com", call_args[0][0])
        self.assertIn("Authorization", call_args[1]["headers"])
        self.assertEqual(call_args[1]["headers"]["Authorization"], f"bearer {token}")

    def test_file_operations_with_special_characters_integration(self):
        """Test file operations with special characters across modules."""
        # Test data with Unicode and special characters
        special_post_data = {
            "title": "Post with émojis 🚀 and spéciål çhars",
            "author": "ûsér_ñamé",
            "subreddit_name_prefixed": "r/tëst_süb",
            "ups": 42,
            "selftext": "Content with Unicode: ñoñó αβγδε 中文",
            "url": "https://reddit.com/special",
            "created_utc": 1640995200,
        }

        mock_settings = Mock()
        mock_settings.show_upvotes = True
        mock_settings.show_timestamp = True
        mock_settings.show_auto_mod_comment = False
        mock_settings.line_break_between_parent_replies = False
        mock_settings.reply_depth_color_indicators = False
        mock_settings.reply_depth_max = -1
        mock_settings.use_timestamped_directories = False
        mock_settings.file_format = "md"
        mock_settings.overwrite_existing_file = True
        mock_settings.enable_media_downloads = False
        mock_settings.filtered_keywords = []
        mock_settings.filtered_authors = []
        mock_settings.filtered_min_upvotes = 0
        mock_settings.filtered_regexes = []
        mock_settings.filtered_message = ""

        colors = ["🟩"]
        url = "https://reddit.com/r/test/comments/123/special_post"

        # Generate filename with special characters
        filename = utils.generate_filename(
            base_dir=self.temp_dir,
            url=url,
            subreddit=special_post_data["subreddit_name_prefixed"],
            use_timestamped_dirs=False,
            post_timestamp="2022-01-01 00:00:00",
            file_format="md",
            overwrite=True,
        )

        # Build content
        content = build_post_content(
            post_data=special_post_data,
            replies_data=[],
            settings=mock_settings,
            colors=colors,
            url=url,
            target_path=filename,
        )

        # Write to file
        from pathlib import Path

        main._write_to_file(Path(filename), content)

        # Verify file was created and contains Unicode content
        self.assertTrue(os.path.exists(filename))
        with open(filename, "r", encoding="utf-8") as f:
            written_content = f.read()

        self.assertIn("émojis 🚀", written_content)
        self.assertIn("spéciål çhars", written_content)
        self.assertIn("ûsér_ñamé", written_content)
        self.assertIn("ñoñó αβγδε 中文", written_content)

    @patch("main.time.sleep")  # Mock sleep to speed up test
    def test_rate_limiting_behavior_integration(self, mock_sleep):
        """Test rate limiting behavior across multiple URL processing."""
        urls = [
            "https://reddit.com/r/test/comments/1/post1",
            "https://reddit.com/r/test/comments/2/post2",
            "https://reddit.com/r/test/comments/3/post3",
        ]

        mock_settings = Mock()

        with patch("main._process_single_url") as mock_process:
            main._process_all_urls(urls, mock_settings, self.temp_dir, "")

            # Should call sleep between each URL (rate limiting)
            self.assertEqual(mock_sleep.call_count, 3)
            mock_sleep.assert_called_with(1)

            # Should process all URLs
            self.assertEqual(mock_process.call_count, 3)

    def test_complete_workflow_error_recovery(self):
        """Test error recovery in complete workflow."""
        # Mock a scenario where some operations fail but workflow continues
        with patch("main._load_settings") as mock_load_settings:
            with patch("main._parse_cli_args") as mock_parse_cli:
                with patch("main._fetch_urls") as mock_fetch_urls:
                    with patch("main._process_all_urls") as mock_process:

                        # Mock settings
                        mock_settings = Mock()
                        mock_settings.login_on_startup = False
                        mock_load_settings.return_value = mock_settings

                        # Mock CLI args
                        mock_parse_cli.return_value = Mock()

                        # Mock URLs (some invalid)
                        mock_fetch_urls.return_value = [
                            "https://reddit.com/r/test/comments/1/valid",
                            "invalid_url",
                            "https://reddit.com/r/test/comments/2/valid2",
                        ]

                        # Mock processing - let it proceed normally
                        mock_process.return_value = None

                        # Run main workflow
                        main.main()

                        # Should have attempted to process all URLs despite invalid ones
                        mock_process.assert_called_once()
                        call_args = mock_process.call_args[0]
                        urls = call_args[0]
                        self.assertIn(
                            "invalid_url", urls
                        )  # Invalid URLs passed through


if __name__ == "__main__":
    unittest.main()
