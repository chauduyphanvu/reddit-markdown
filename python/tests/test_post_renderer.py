import sys
import os
import unittest
from unittest.mock import patch, Mock
import datetime

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from post_renderer import build_post_content
from .test_utils import BaseTestCase, MockFactory, TestDataFixtures


class TestPostRenderer(BaseTestCase):
    """Test suite for post_renderer.py module."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_settings = MockFactory.create_settings_mock()
        self.colors = ["🟩", "🟨", "🟧", "🟦", "🟪"]
        self.url = "https://reddit.com/r/test/comments/123/test_post"
        self.target_path = "/test/path/test_post.md"

        # Use shared test data fixtures
        self.post_data = TestDataFixtures.get_sample_post_data()
        self.post_data.update(
            {
                "title": "Test Post Title",
                "author": "test_author",
                "ups": 1500,
                "selftext": "This is the post content.",
            }
        )

        self.replies_data = [TestDataFixtures.get_sample_comment_data()]
        self.replies_data[0]["data"].update(
            {
                "author": "commenter1",
                "body": "This is a test comment.",
                "ups": 50,
            }
        )

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_basic(self, mock_get_replies):
        """Test basic post content building."""
        mock_get_replies.return_value = {}

        result = build_post_content(
            post_data=self.post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("Test Post Title", result)
        self.assertIn("r/test", result)
        self.assertIn("test_author", result)
        self.assertIn("This is the post content", result)
        self.assertIn("This is a test comment", result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_with_upvotes(self, mock_get_replies):
        """Test post content includes upvote display."""
        mock_get_replies.return_value = {}

        result = build_post_content(
            post_data=self.post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("⬆️ 1k", result)  # Should format 1500 as 1k
        self.assertIn("⬆️ 50", result)  # Should show comment upvotes

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_without_upvotes(self, mock_get_replies):
        """Test post content without upvote display."""
        mock_get_replies.return_value = {}
        self.mock_settings.show_upvotes = False

        result = build_post_content(
            post_data=self.post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertNotIn("⬆️", result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_with_timestamps(self, mock_get_replies):
        """Test post content includes timestamps."""
        mock_get_replies.return_value = {}

        result = build_post_content(
            post_data=self.post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("2022-01-01 00:00:00", result)  # Post timestamp
        self.assertIn("2022-01-01 00:10:00", result)  # Comment timestamp

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_without_timestamps(self, mock_get_replies):
        """Test post content without timestamps."""
        mock_get_replies.return_value = {}
        self.mock_settings.show_timestamp = False

        result = build_post_content(
            post_data=self.post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertNotIn("2022-01-01", result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_locked_post(self, mock_get_replies):
        """Test locked post displays lock message."""
        mock_get_replies.return_value = {}
        locked_post_data = self.post_data.copy()
        locked_post_data["locked"] = True

        result = build_post_content(
            post_data=locked_post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("🔒", result)
        self.assertIn("locked by the moderators", result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_html_escaping(self, mock_get_replies):
        """Test HTML entity unescaping in post content."""
        mock_get_replies.return_value = {}
        escaped_post_data = self.post_data.copy()
        escaped_post_data["selftext"] = (
            "This is &amp; test with &lt;tags&gt; and &quot;quotes&quot;"
        )

        result = build_post_content(
            post_data=escaped_post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn('This is & test with <tags> and "quotes"', result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_automod_comment_hidden(self, mock_get_replies):
        """Test AutoModerator comments are hidden when configured."""
        mock_get_replies.return_value = {}
        automod_replies = [
            {
                "data": {
                    "author": "AutoModerator",
                    "body": "This is an AutoModerator comment.",
                    "ups": 1,
                    "created_utc": 1640995800,
                    "replies": "",
                }
            }
        ]

        result = build_post_content(
            post_data=self.post_data,
            replies_data=automod_replies,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertNotIn("AutoModerator", result)
        self.assertNotIn("This is an AutoModerator comment", result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_automod_comment_shown(self, mock_get_replies):
        """Test AutoModerator comments are shown when configured."""
        mock_get_replies.return_value = {}
        self.mock_settings.show_auto_mod_comment = True

        automod_replies = [
            {
                "data": {
                    "author": "AutoModerator",
                    "body": "This is an AutoModerator comment.",
                    "ups": 1,
                    "created_utc": 1640995800,
                    "replies": "",
                }
            }
        ]

        result = build_post_content(
            post_data=self.post_data,
            replies_data=automod_replies,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("AutoModerator", result)
        self.assertIn("This is an AutoModerator comment", result)

    @patch("post_renderer.utils.get_replies")
    @patch("post_renderer.apply_filter")
    def test_build_post_content_filtered_comment(
        self, mock_apply_filter, mock_get_replies
    ):
        """Test filtered comments display filtered message."""
        mock_get_replies.return_value = {}
        mock_apply_filter.return_value = "[FILTERED]"

        result = build_post_content(
            post_data=self.post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("[FILTERED]", result)
        mock_apply_filter.assert_called()

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_deleted_comment(self, mock_get_replies):
        """Test deleted comments display deletion message."""
        mock_get_replies.return_value = {}
        deleted_replies = [
            {
                "data": {
                    "author": "[deleted]",
                    "body": "[deleted]",
                    "ups": 0,
                    "created_utc": 1640995800,
                    "replies": "",
                }
            }
        ]

        result = build_post_content(
            post_data=self.post_data,
            replies_data=deleted_replies,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("Comment deleted by user", result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_op_author_marking(self, mock_get_replies):
        """Test original poster is marked as (OP) in comments."""
        mock_get_replies.return_value = {}
        op_replies = [
            {
                "data": {
                    "author": "test_author",  # Same as post author
                    "body": "OP's reply.",
                    "ups": 10,
                    "created_utc": 1640995800,
                    "replies": "",
                }
            }
        ]

        result = build_post_content(
            post_data=self.post_data,
            replies_data=op_replies,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("(OP)", result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_user_link_formatting(self, mock_get_replies):
        """Test u/username is converted to clickable links."""
        mock_get_replies.return_value = {}
        replies_with_mentions = [
            {
                "data": {
                    "author": "commenter1",
                    "body": "Hey u/test_user, check this out!",
                    "ups": 5,
                    "created_utc": 1640995800,
                    "replies": "",
                }
            }
        ]

        result = build_post_content(
            post_data=self.post_data,
            replies_data=replies_with_mentions,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("[u/test_user](https://www.reddit.com/user/test_user)", result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_nested_replies(self, mock_get_replies):
        """Test nested replies are processed with proper indentation."""
        nested_replies = {
            "nested_id": {
                "depth": 2,
                "child_reply": {
                    "data": {
                        "author": "nested_author",
                        "body": "This is a nested reply.",
                        "ups": 5,
                        "created_utc": 1640996400,
                    }
                },
            }
        }
        mock_get_replies.return_value = nested_replies

        result = build_post_content(
            post_data=self.post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("nested_author", result)
        self.assertIn("This is a nested reply", result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_color_indicators(self, mock_get_replies):
        """Test color indicators are included when enabled."""
        nested_replies = {
            "nested_id": {
                "depth": 1,
                "child_reply": {
                    "data": {
                        "author": "nested_author",
                        "body": "Nested reply.",
                        "ups": 5,
                        "created_utc": 1640996400,
                    }
                },
            }
        }
        mock_get_replies.return_value = nested_replies

        result = build_post_content(
            post_data=self.post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        # Should include color indicators from the colors array
        self.assertIn("🟩", result)  # colors[0] for top-level
        self.assertIn("🟨", result)  # colors[1] for nested

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_no_color_indicators(self, mock_get_replies):
        """Test no color indicators when disabled."""
        mock_get_replies.return_value = {}
        self.mock_settings.reply_depth_color_indicators = False

        result = build_post_content(
            post_data=self.post_data,
            replies_data=self.replies_data,
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        # Should not include color indicators
        self.assertNotIn("🟩", result)
        self.assertNotIn("🟨", result)

    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_empty_replies(self, mock_get_replies):
        """Test post content with empty replies list."""
        mock_get_replies.return_value = {}

        result = build_post_content(
            post_data=self.post_data,
            replies_data=[],
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("Test Post Title", result)
        self.assertIn("0 replies", result)  # Should show 0 replies

    def test_build_post_content_missing_post_data(self):
        """Test handling of missing post data fields."""
        minimal_post_data = {"title": "Test"}  # Missing most fields

        result = build_post_content(
            post_data=minimal_post_data,
            replies_data=[],
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        self.assertIn("Test", result)
        # Should handle missing fields gracefully with defaults

    @patch("post_renderer.utils.download_media")
    @patch("post_renderer.utils.generate_unique_media_filename")
    @patch("post_renderer.utils.ensure_dir_exists")
    @patch("post_renderer.utils.get_replies")
    def test_build_post_content_video_media_collision_handling(
        self,
        mock_get_replies,
        mock_ensure_dir,
        mock_generate_filename,
        mock_download_media,
    ):
        """Test video media handling with collision-safe filename generation."""
        mock_get_replies.return_value = {}
        mock_generate_filename.return_value = "/test/path/media/video_1.mp4"
        mock_download_media.return_value = True

        video_post_data = self.post_data.copy()
        video_post_data["is_video"] = True
        video_post_data["media"] = {
            "reddit_video": {"fallback_url": "https://example.com/video.mp4"}
        }
        self.mock_settings.enable_media_downloads = True

        result = build_post_content(
            post_data=video_post_data,
            replies_data=[],
            settings=self.mock_settings,
            colors=self.colors,
            url=self.url,
            target_path=self.target_path,
        )

        # Verify the unique filename function was called
        mock_generate_filename.assert_called_once_with(
            "https://example.com/video.mp4", "/test/path/media"
        )

        # Verify download was attempted with the unique path
        mock_download_media.assert_called_once_with(
            "https://example.com/video.mp4", "/test/path/media/video_1.mp4"
        )

        # Verify video tag uses the collision-safe filename
        self.assertIn('<video controls src="./media/video_1.mp4"></video>', result)


if __name__ == "__main__":
    unittest.main()
