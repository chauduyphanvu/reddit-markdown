"""
Post renderer tests focusing on behavior, not implementation.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import os

from post_renderer import build_post_content


class TestPostRenderingBehavior(unittest.TestCase):
    """Test post rendering behavior and output characteristics."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_post = {
            "title": "Test Post Title",
            "author": "test_author",
            "subreddit_name_prefixed": "r/test",
            "selftext": "This is the post content.",
            "ups": 1500,
            "created_utc": 1640995200,  # 2022-01-01 00:00:00
            "locked": False,
            "url": "https://reddit.com/r/test/comments/123/test",
        }

        self.sample_comment = {
            "data": {
                "author": "commenter1",
                "body": "This is a test comment.",
                "ups": 50,
                "created_utc": 1640995800,  # 2022-01-01 00:10:00
                "replies": "",
            }
        }

        self.basic_settings = Mock()
        self.basic_settings.show_upvotes = True
        self.basic_settings.show_timestamp = True
        self.basic_settings.show_auto_mod_comment = False
        self.basic_settings.enable_media_downloads = False
        self.basic_settings.apply_comment_filters = False
        self.basic_settings.reply_depth_color_indicators = True
        self.basic_settings.line_break_between_parent_replies = True

        # Add filter attributes that need to be iterable
        self.basic_settings.filtered_keywords = []
        self.basic_settings.filtered_authors = []
        self.basic_settings.filtered_regexes = []
        self.basic_settings.filtered_min_upvotes = 0
        self.basic_settings.filtered_message = "[FILTERED]"

        self.colors = ["🟩", "🟨", "🟧", "🟦", "🟪"]

    def test_basic_post_content_generation(self):
        """Post content should contain essential post information."""
        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=self.sample_post,
                replies_data=[self.sample_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should contain post title
        self.assertIn("Test Post Title", content)

        # Should contain subreddit
        self.assertIn("r/test", content)

        # Should contain author
        self.assertIn("test_author", content)

        # Should contain post content
        self.assertIn("This is the post content", content)

        # Should contain comment
        self.assertIn("This is a test comment", content)
        self.assertIn("commenter1", content)

    def test_upvote_display_control(self):
        """Upvote display should be controlled by settings."""
        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            # Test with upvotes enabled
            self.basic_settings.show_upvotes = True
            content_with_upvotes = build_post_content(
                post_data=self.sample_post,
                replies_data=[self.sample_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

            # Test with upvotes disabled
            self.basic_settings.show_upvotes = False
            content_without_upvotes = build_post_content(
                post_data=self.sample_post,
                replies_data=[self.sample_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should show upvotes when enabled
        self.assertIn("⬆️", content_with_upvotes)
        self.assertIn("1k", content_with_upvotes)  # 1500 formatted as 1k

        # Should not show upvotes when disabled
        self.assertNotIn("⬆️", content_without_upvotes)

    def test_timestamp_display_control(self):
        """Timestamp display should be controlled by settings."""
        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            # Test with timestamps enabled
            self.basic_settings.show_timestamp = True
            content_with_timestamps = build_post_content(
                post_data=self.sample_post,
                replies_data=[self.sample_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

            # Test with timestamps disabled
            self.basic_settings.show_timestamp = False
            content_without_timestamps = build_post_content(
                post_data=self.sample_post,
                replies_data=[self.sample_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should show timestamps when enabled
        self.assertIn("2022-01-01", content_with_timestamps)

        # Should not show timestamps when disabled
        self.assertNotIn("2022-01-01", content_without_timestamps)

    def test_locked_post_indication(self):
        """Locked posts should be clearly indicated."""
        locked_post = self.sample_post.copy()
        locked_post["locked"] = True

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=locked_post,
                replies_data=[self.sample_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should indicate locked status
        self.assertIn("🔒", content)
        self.assertIn("locked", content.lower())

    def test_automod_comment_filtering(self):
        """AutoModerator comments should be filtered based on settings."""
        automod_comment = {
            "data": {
                "author": "AutoModerator",
                "body": "This post has been removed for violating rules.",
                "ups": 1,
                "created_utc": 1640995800,
                "replies": "",
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            # Test with AutoMod comments hidden (default)
            self.basic_settings.show_auto_mod_comment = False
            content_hidden = build_post_content(
                post_data=self.sample_post,
                replies_data=[automod_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

            # Test with AutoMod comments shown
            self.basic_settings.show_auto_mod_comment = True
            content_shown = build_post_content(
                post_data=self.sample_post,
                replies_data=[automod_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should not show AutoMod when hidden
        self.assertNotIn("AutoModerator", content_hidden)
        self.assertNotIn("This post has been removed", content_hidden)

        # Should show AutoMod when enabled
        self.assertIn("AutoModerator", content_shown)
        self.assertIn("This post has been removed", content_shown)

    def test_deleted_comment_handling(self):
        """Deleted comments should be handled appropriately."""
        deleted_comment = {
            "data": {
                "author": "[deleted]",
                "body": "[deleted]",
                "ups": 0,
                "created_utc": 1640995800,
                "replies": "",
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=self.sample_post,
                replies_data=[deleted_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should indicate comment was deleted
        self.assertIn("deleted", content.lower())

    def test_op_comment_marking(self):
        """Original poster comments should be marked as (OP)."""
        op_comment = {
            "data": {
                "author": "test_author",  # Same as post author
                "body": "Thanks for all the comments!",
                "ups": 25,
                "created_utc": 1640995800,
                "replies": "",
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=self.sample_post,
                replies_data=[op_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should mark OP comments
        self.assertIn("(OP)", content)

    def test_user_mention_linking(self):
        """User mentions should be converted to clickable links."""
        mention_comment = {
            "data": {
                "author": "commenter1",
                "body": "Hey u/test_user, great post! Also ping u/another_user",
                "ups": 10,
                "created_utc": 1640995800,
                "replies": "",
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=self.sample_post,
                replies_data=[mention_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should create clickable links for user mentions
        self.assertIn("[u/test_user](https://www.reddit.com/user/test_user)", content)
        self.assertIn(
            "[u/another_user](https://www.reddit.com/user/another_user)", content
        )

    def test_html_entity_unescaping(self):
        """HTML entities should be properly unescaped."""
        escaped_post = self.sample_post.copy()
        escaped_post["selftext"] = (
            "This has &amp; entities &lt;like&gt; &quot;these&quot;"
        )

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=escaped_post,
                replies_data=[],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should unescape HTML entities
        self.assertIn('This has & entities <like> "these"', content)

    def test_color_indicators_control(self):
        """Color indicators should be controlled by settings."""
        nested_comment = {
            "data": {
                "author": "nested_user",
                "body": "This is a nested reply",
                "ups": 15,
                "created_utc": 1640995800,
                "replies": "",
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            # Test with color indicators enabled
            self.basic_settings.reply_depth_color_indicators = True
            content_with_colors = build_post_content(
                post_data=self.sample_post,
                replies_data=[self.sample_comment, nested_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

            # Test with color indicators disabled
            self.basic_settings.reply_depth_color_indicators = False
            content_without_colors = build_post_content(
                post_data=self.sample_post,
                replies_data=[self.sample_comment, nested_comment],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should include color emojis when enabled
        color_found_with = any(color in content_with_colors for color in self.colors)
        self.assertTrue(color_found_with)

        # Should not include color emojis when disabled
        color_found_without = any(
            color in content_without_colors for color in self.colors
        )
        self.assertFalse(color_found_without)

    def test_empty_replies_handling(self):
        """Posts with no replies should be handled gracefully."""
        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=self.sample_post,
                replies_data=[],  # No replies
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should still contain post information
        self.assertIn("Test Post Title", content)
        self.assertIn("test_author", content)

        # Should indicate no replies
        self.assertIn("0 replies", content)

    def test_media_content_handling(self):
        """Media content should be handled appropriately."""
        # Test image post
        image_post = self.sample_post.copy()
        image_post["post_hint"] = "image"
        image_post["url"] = "https://i.redd.it/example.jpg"

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=image_post,
                replies_data=[],
                settings=self.basic_settings,
                colors=self.colors,
                url="https://reddit.com/r/test/comments/123",
                target_path=tmp.name,
            )

        # Should include reference to the image
        self.assertIn("i.redd.it/example.jpg", content)


class TestPostRenderingIntegration(unittest.TestCase):
    """Integration tests for post rendering with realistic scenarios."""

    def test_complex_post_with_nested_replies(self):
        """Test rendering a complex post with multiple levels of replies."""
        complex_post = {
            "title": "Complex Discussion Topic",
            "author": "discussion_starter",
            "subreddit_name_prefixed": "r/science",
            "selftext": "Let's discuss this complex topic in detail...",
            "ups": 5000,
            "created_utc": 1640995200,
            "locked": False,
            "url": "https://reddit.com/r/science/comments/xyz/complex",
        }

        complex_replies = [
            {
                "data": {
                    "author": "expert_user",
                    "body": "Great question! Here's my detailed analysis...",
                    "ups": 500,
                    "created_utc": 1640995800,
                    "replies": "",
                }
            },
            {
                "data": {
                    "author": "discussion_starter",  # OP reply
                    "body": "Thanks for the insight! What about u/another_expert?",
                    "ups": 200,
                    "created_utc": 1640996400,
                    "replies": "",
                }
            },
        ]

        settings = Mock()
        settings.show_upvotes = True
        settings.show_timestamp = True
        settings.show_auto_mod_comment = False
        settings.enable_media_downloads = False
        settings.apply_comment_filters = False
        settings.reply_depth_color_indicators = True
        settings.line_break_between_parent_replies = True

        # Add filter attributes that need to be iterable
        settings.filtered_keywords = []
        settings.filtered_authors = []
        settings.filtered_regexes = []
        settings.filtered_min_upvotes = 0
        settings.filtered_message = "[FILTERED]"

        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            content = build_post_content(
                post_data=complex_post,
                replies_data=complex_replies,
                settings=settings,
                colors=["🟩", "🟨", "🟧", "🟦", "🟪"],
                url="https://reddit.com/r/science/comments/xyz/complex",
                target_path=tmp.name,
            )

        # Verify all components are present
        self.assertIn("Complex Discussion Topic", content)
        self.assertIn("r/science", content)
        self.assertIn("discussion_starter", content)
        self.assertIn("expert_user", content)
        self.assertIn("Great question", content)
        self.assertIn("(OP)", content)  # OP reply should be marked
        self.assertIn("[u/another_expert]", content)  # User mention should be linked
        self.assertIn("⬆️", content)  # Upvotes should be shown
        self.assertIn("5k", content)  # Post upvotes formatted

        # Should be substantial content
        self.assertGreater(len(content), 500)


if __name__ == "__main__":
    unittest.main()
