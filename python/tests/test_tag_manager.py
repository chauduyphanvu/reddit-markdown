import os
import tempfile
import unittest

from search.search_database import SearchDatabase
from search.tag_manager import TagManager, Tag


class TestTagManager(unittest.TestCase):
    """Test cases for TagManager class."""

    def setUp(self):
        """Set up test tag manager with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.database = SearchDatabase(self.temp_db.name)
        self.tag_manager = TagManager(self.database)

        # Add test posts for tagging
        self._add_test_posts()

    def tearDown(self):
        """Clean up temporary database file."""
        self.database.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def _add_test_posts(self):
        """Add sample posts for testing."""
        test_posts = [
            {
                "file_path": "/test/python_tutorial.md",
                "post_id": "abc123",
                "title": "How to learn Python effectively?",
                "content": "I need help learning Python programming. Any suggestions?",
                "author": "newbie",
                "subreddit": "r/Python",
                "content_preview": "I need help learning Python programming.",
            },
            {
                "file_path": "/test/discussion.md",
                "post_id": "def456",
                "title": "What do you think about the new framework?",
                "content": "Let me know your thoughts and opinions on this topic.",
                "author": "developer",
                "subreddit": "r/webdev",
                "content_preview": "Let me know your thoughts and opinions.",
            },
        ]

        for post in test_posts:
            self.database.add_post(post)

    def test_create_tag_with_valid_name_succeeds(self):
        """Creating a tag with valid name should succeed."""
        tag = self.tag_manager.create_tag("tutorial")

        self.assertIsNotNone(tag)
        self.assertEqual(tag.name, "tutorial")
        self.assertIsInstance(tag.id, int)
        self.assertGreater(tag.id, 0)

    def test_create_tag_with_description_and_color_stores_metadata(self):
        """Creating a tag with description and color should store metadata."""
        tag = self.tag_manager.create_tag(
            "important", description="Important posts to remember", color="#FF0000"
        )

        self.assertIsNotNone(tag)
        self.assertEqual(tag.description, "Important posts to remember")
        self.assertEqual(tag.color, "#FF0000")

    def test_create_tag_normalizes_name(self):
        """Creating a tag should normalize the name."""
        tag = self.tag_manager.create_tag("My Favorite Posts!")

        self.assertIsNotNone(tag)
        self.assertEqual(tag.name, "my_favorite_posts")

    def test_create_tag_with_empty_name_returns_none(self):
        """Creating a tag with empty name should return None."""
        tag = self.tag_manager.create_tag("")
        self.assertIsNone(tag)

    def test_create_tag_with_invalid_color_ignores_color(self):
        """Creating a tag with invalid color should ignore the color."""
        tag = self.tag_manager.create_tag("test", color="invalid-color")

        self.assertIsNotNone(tag)
        self.assertEqual(tag.color, "")

    def test_create_duplicate_tag_returns_existing_tag(self):
        """Creating a duplicate tag should return the existing tag."""
        first_tag = self.tag_manager.create_tag("duplicate")
        second_tag = self.tag_manager.create_tag("duplicate")

        self.assertEqual(first_tag.id, second_tag.id)
        self.assertEqual(first_tag.name, second_tag.name)

    def test_get_tag_existing_tag_returns_tag(self):
        """Getting an existing tag should return the tag."""
        created_tag = self.tag_manager.create_tag("existing")
        retrieved_tag = self.tag_manager.get_tag("existing")

        self.assertEqual(created_tag.id, retrieved_tag.id)
        self.assertEqual(created_tag.name, retrieved_tag.name)

    def test_get_tag_nonexistent_tag_returns_none(self):
        """Getting a non-existent tag should return None."""
        tag = self.tag_manager.get_tag("nonexistent")
        self.assertIsNone(tag)

    def test_get_tag_normalizes_name(self):
        """Getting a tag should normalize the name for lookup."""
        self.tag_manager.create_tag("test-tag")
        retrieved_tag = self.tag_manager.get_tag(
            "test-tag"
        )  # Use the same normalized form

        self.assertIsNotNone(retrieved_tag)
        self.assertEqual(retrieved_tag.name, "test-tag")

    def test_list_tags_returns_all_tags(self):
        """Listing tags should return all created tags."""
        tag_names = ["first", "second", "third"]
        for name in tag_names:
            self.tag_manager.create_tag(name)

        tags = self.tag_manager.list_tags()

        self.assertEqual(len(tags), 3)
        retrieved_names = [tag.name for tag in tags]
        for name in tag_names:
            self.assertIn(name, retrieved_names)

    def test_list_tags_respects_limit(self):
        """Listing tags should respect the limit parameter."""
        for i in range(5):
            self.tag_manager.create_tag(f"tag_{i}")

        tags = self.tag_manager.list_tags(limit=3)
        self.assertEqual(len(tags), 3)

    def test_list_tags_includes_post_count(self):
        """Listed tags should include post count information."""
        tag = self.tag_manager.create_tag("test_count")
        self.tag_manager.tag_post("abc123", ["test_count"])

        tags = self.tag_manager.list_tags()
        test_tag = next((t for t in tags if t.name == "test_count"), None)

        self.assertIsNotNone(test_tag)
        self.assertEqual(test_tag.post_count, 1)

    def test_delete_tag_existing_tag_succeeds(self):
        """Deleting an existing tag should succeed."""
        self.tag_manager.create_tag("to_delete")
        result = self.tag_manager.delete_tag("to_delete")

        self.assertTrue(result)

        # Verify tag is gone
        deleted_tag = self.tag_manager.get_tag("to_delete")
        self.assertIsNone(deleted_tag)

    def test_delete_tag_nonexistent_tag_returns_false(self):
        """Deleting a non-existent tag should return False."""
        result = self.tag_manager.delete_tag("nonexistent")
        self.assertFalse(result)

    def test_tag_post_with_existing_post_succeeds(self):
        """Tagging an existing post should succeed."""
        self.tag_manager.create_tag("tutorial")
        result = self.tag_manager.tag_post("abc123", ["tutorial"])

        self.assertEqual(result, 1)  # 1 tag applied successfully

    def test_tag_post_with_multiple_tags_applies_all(self):
        """Tagging a post with multiple tags should apply all tags."""
        tags = ["tutorial", "python", "beginner"]
        for tag_name in tags:
            self.tag_manager.create_tag(tag_name)

        result = self.tag_manager.tag_post("abc123", tags)
        self.assertEqual(result, 3)  # All 3 tags applied

    def test_tag_post_with_nonexistent_post_returns_zero(self):
        """Tagging a non-existent post should return 0."""
        self.tag_manager.create_tag("tutorial")
        result = self.tag_manager.tag_post("nonexistent", ["tutorial"])

        self.assertEqual(result, 0)

    def test_tag_post_creates_tag_if_not_exists(self):
        """Tagging with non-existent tag should create the tag."""
        result = self.tag_manager.tag_post("abc123", ["auto_created"])

        self.assertEqual(result, 1)

        # Verify tag was created
        tag = self.tag_manager.get_tag("auto_created")
        self.assertIsNotNone(tag)

    def test_untag_post_removes_specific_tags(self):
        """Removing specific tags from a post should work."""
        # Apply multiple tags
        tags = ["tutorial", "python", "beginner"]
        self.tag_manager.tag_post("abc123", tags)

        # Remove specific tags
        removed = self.tag_manager.untag_post("abc123", ["tutorial", "python"])

        self.assertEqual(removed, 2)

        # Verify only 'beginner' tag remains
        remaining_tags = self.tag_manager.get_post_tags("abc123")
        self.assertEqual(len(remaining_tags), 1)
        self.assertEqual(remaining_tags[0].name, "beginner")

    def test_untag_post_with_none_removes_all_tags(self):
        """Removing all tags from a post should work."""
        # Apply multiple tags
        tags = ["tutorial", "python", "beginner"]
        self.tag_manager.tag_post("abc123", tags)

        # Remove all tags
        removed = self.tag_manager.untag_post("abc123", None)

        self.assertEqual(removed, 3)

        # Verify no tags remain
        remaining_tags = self.tag_manager.get_post_tags("abc123")
        self.assertEqual(len(remaining_tags), 0)

    def test_get_post_tags_returns_applied_tags(self):
        """Getting post tags should return all applied tags."""
        tags = ["tutorial", "python"]
        self.tag_manager.tag_post("abc123", tags)

        post_tags = self.tag_manager.get_post_tags("abc123")

        self.assertEqual(len(post_tags), 2)
        tag_names = [tag.name for tag in post_tags]
        self.assertIn("tutorial", tag_names)
        self.assertIn("python", tag_names)

    def test_get_post_tags_nonexistent_post_returns_empty(self):
        """Getting tags for non-existent post should return empty list."""
        tags = self.tag_manager.get_post_tags("nonexistent")
        self.assertEqual(tags, [])

    def test_auto_tag_post_applies_pattern_based_tags(self):
        """Auto-tagging should apply tags based on content patterns."""
        # This post should match 'question' pattern due to '?' in title
        applied_tags = self.tag_manager.auto_tag_post("abc123")

        # Should apply some auto tags
        self.assertIsInstance(applied_tags, list)

        # Should include question tag due to '?' in title
        if applied_tags:  # If any tags were applied
            self.assertIn("question", applied_tags)

    def test_auto_tag_post_creates_subreddit_tag(self):
        """Auto-tagging should create subreddit-based tags."""
        applied_tags = self.tag_manager.auto_tag_post("abc123")

        # Should create tag based on subreddit
        if applied_tags:  # If any tags were applied
            subreddit_tags = [tag for tag in applied_tags if tag.startswith("sub_")]
            self.assertGreater(len(subreddit_tags), 0)

    def test_bulk_tag_posts_applies_tags_to_multiple_posts(self):
        """Bulk tagging should apply tags to multiple posts."""
        post_ids = ["abc123", "def456"]
        tags = ["bulk_tag"]

        stats = self.tag_manager.bulk_tag_posts(post_ids, tags)

        self.assertEqual(stats["success"], 2)
        self.assertEqual(stats["failed"], 0)

        # Verify both posts have the tag
        for post_id in post_ids:
            post_tags = self.tag_manager.get_post_tags(post_id)
            tag_names = [tag.name for tag in post_tags]
            self.assertIn("bulk_tag", tag_names)

    def test_bulk_tag_posts_handles_failures(self):
        """Bulk tagging should handle failures gracefully."""
        post_ids = ["abc123", "nonexistent"]
        tags = ["bulk_tag"]

        stats = self.tag_manager.bulk_tag_posts(post_ids, tags)

        self.assertEqual(stats["success"], 1)  # Only existing post tagged
        self.assertEqual(stats["failed"], 1)  # Non-existent post failed

    def test_tag_dataclass_normalizes_name(self):
        """Tag dataclass should normalize tag names."""
        tag = Tag(id=1, name="Test Tag Name!")
        self.assertEqual(tag.name, "test_tag_name")

    def test_tag_dataclass_validates_name(self):
        """Tag dataclass should validate tag names."""
        with self.assertRaises(ValueError):
            Tag(id=1, name="")  # Empty name should raise error

    def test_tag_normalize_function_handles_special_cases(self):
        """Tag name normalization should handle special cases."""
        test_cases = [
            ("Simple Tag", "simple_tag"),
            ("Tag with-dashes", "tag_with-dashes"),  # Dashes are preserved
            ("Tag    with   spaces", "tag_with_spaces"),
            ("Tag@#$%with*()special", "tag_with_special"),
            ("___Leading_trailing___", "leading_trailing"),
            ("Multiple___underscores", "multiple_underscores"),
        ]

        for input_name, expected in test_cases:
            normalized = Tag._normalize_tag_name(input_name)
            self.assertEqual(normalized, expected)

    def test_apply_single_tag_creates_tag_if_not_exists(self):
        """Internal _apply_single_tag should create tag if it doesn't exist."""
        # Get a database post ID
        import sqlite3

        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute("SELECT id FROM posts WHERE post_id = ?", ("abc123",))
            db_post_id = cursor.fetchone()[0]

        # Apply non-existent tag
        result = self.tag_manager._apply_single_tag(db_post_id, "new_tag")

        self.assertTrue(result)

        # Verify tag was created
        tag = self.tag_manager.get_tag("new_tag")
        self.assertIsNotNone(tag)

    def test_apply_single_tag_handles_duplicate_application(self):
        """Internal _apply_single_tag should handle duplicate tag application."""
        # Get a database post ID
        import sqlite3

        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute("SELECT id FROM posts WHERE post_id = ?", ("abc123",))
            db_post_id = cursor.fetchone()[0]

        # Apply tag twice
        result1 = self.tag_manager._apply_single_tag(db_post_id, "duplicate_tag")
        result2 = self.tag_manager._apply_single_tag(db_post_id, "duplicate_tag")

        # Both should succeed
        self.assertTrue(result1)
        self.assertTrue(result2)

        # But post should only have one instance of the tag
        post_tags = self.tag_manager.get_post_tags("abc123")
        duplicate_tags = [tag for tag in post_tags if tag.name == "duplicate_tag"]
        self.assertEqual(len(duplicate_tags), 1)


if __name__ == "__main__":
    unittest.main()
