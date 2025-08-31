import os
import tempfile
import unittest
from pathlib import Path

from search import SearchDatabase, SearchEngine, TagManager, ContentIndexer, SearchQuery


class TestSearchIntegration(unittest.TestCase):
    """Integration tests for the complete search functionality."""

    def setUp(self):
        """Set up complete search system with test data."""
        # Create temporary database and directory
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.temp_dir = tempfile.mkdtemp()

        # Initialize search system components
        self.database = SearchDatabase(self.temp_db.name)
        self.search_engine = SearchEngine(self.database)
        self.tag_manager = TagManager(self.database)
        self.indexer = ContentIndexer(self.database, max_workers=1)

        # Create test Reddit posts
        self._create_test_posts()

        # Index the posts
        self.indexer.index_directory(self.temp_dir)

    def tearDown(self):
        """Clean up temporary files and database."""
        self.database.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_posts(self):
        """Create test Reddit markdown files."""
        test_posts = [
            (
                "python_tutorial.md",
                """**r/Python** | Posted by u/python_guru ⬆️ 150 _(2023-01-15 10:30:00)_

## Python Tutorial for Beginners

Original post: [https://reddit.com/r/Python/comments/abc123/python_tutorial/](https://reddit.com/r/Python/comments/abc123/python_tutorial/)

> Learn Python programming from scratch. This comprehensive tutorial covers variables, functions, loops, and classes.

💬 ~ 25 replies

---
""",
            ),
            (
                "python_question.md",
                """**r/Python** | Posted by u/newbie_coder ⬆️ 42 _(2023-01-16 14:20:00)_

## How to debug Python code effectively?

Original post: [https://reddit.com/r/Python/comments/def456/debug_question/](https://reddit.com/r/Python/comments/def456/debug_question/)

> I'm having trouble debugging my Python scripts. What tools and techniques do you recommend for effective debugging?

💬 ~ 18 replies

---
""",
            ),
            (
                "javascript_guide.md",
                """**r/JavaScript** | Posted by u/js_expert ⬆️ 203 _(2023-01-17 09:15:00)_

## Complete JavaScript Guide for Web Development

Original post: [https://reddit.com/r/JavaScript/comments/ghi789/javascript_guide/](https://reddit.com/r/JavaScript/comments/ghi789/javascript_guide/)

> Master JavaScript fundamentals including variables, functions, DOM manipulation, and modern ES6+ features.

💬 ~ 45 replies

---
""",
            ),
            (
                "web_discussion.md",
                """**r/webdev** | Posted by u/web_developer ⬆️ 89 _(2023-01-18 16:45:00)_

## What do you think about the new React features?

Original post: [https://reddit.com/r/webdev/comments/jkl012/react_discussion/](https://reddit.com/r/webdev/comments/jkl012/react_discussion/)

> The latest React release introduced some interesting hooks. I'd love to hear your thoughts and opinions on these changes.

💬 ~ 32 replies

---
""",
            ),
            (
                "tutorial_review.md",
                """**r/programming** | Posted by u/code_reviewer ⬆️ 127 _(2023-01-19 11:30:00)_

## Review: Best Programming Tutorial Sites

Original post: [https://reddit.com/r/programming/comments/mno345/tutorial_review/](https://reddit.com/r/programming/comments/mno345/tutorial_review/)

> Here's my comprehensive review and rating of the top programming tutorial websites. Which ones do you recommend?

💬 ~ 28 replies

---
""",
            ),
        ]

        for filename, content in test_posts:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

    def test_end_to_end_search_workflow(self):
        """Test complete workflow: index posts, search, and verify results."""
        # Verify posts were indexed
        stats = self.database.get_stats()
        self.assertEqual(stats["total_posts"], 5)

        # Test text search
        results = self.search_engine.search_simple("Python")
        self.assertEqual(len(results), 2)  # Should find 2 Python-related posts

        # Test metadata search
        query = SearchQuery(subreddits=["r/Python"])
        results = self.search_engine.search(query)
        self.assertEqual(len(results), 2)

        # Test filtered search
        query = SearchQuery(min_upvotes=100)
        results = self.search_engine.search(query)
        self.assertEqual(len(results), 3)  # Posts with 150, 203, 127 upvotes

    def test_end_to_end_tagging_workflow(self):
        """Test complete tagging workflow: create tags, apply them, search by tags."""
        # Create tags
        tutorial_tag = self.tag_manager.create_tag("tutorial", "Educational content")
        question_tag = self.tag_manager.create_tag("question", "Question posts")

        self.assertIsNotNone(tutorial_tag)
        self.assertIsNotNone(question_tag)

        # Apply tags to posts
        applied_tutorial = self.tag_manager.tag_post(
            "abc123", ["tutorial"]
        )  # Python tutorial
        applied_question = self.tag_manager.tag_post(
            "def456", ["question"]
        )  # Python question

        self.assertEqual(applied_tutorial, 1)
        self.assertEqual(applied_question, 1)

        # Search by tags
        query = SearchQuery(tags=["tutorial"])
        results = self.search_engine.search(query)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].post_id, "abc123")

        # Verify tags in results
        self.assertIn("tutorial", results[0].tags)

    def test_auto_tagging_integration(self):
        """Test auto-tagging integration with content patterns."""
        # Auto-tag posts
        applied_tags_1 = self.tag_manager.auto_tag_post("abc123")  # Tutorial post
        applied_tags_2 = self.tag_manager.auto_tag_post(
            "def456"
        )  # Question post (has '?' in title)
        applied_tags_3 = self.tag_manager.auto_tag_post("jkl012")  # Discussion post
        applied_tags_4 = self.tag_manager.auto_tag_post("mno345")  # Review post

        # Verify some tags were applied
        self.assertIsInstance(applied_tags_1, list)
        self.assertIsInstance(applied_tags_2, list)
        self.assertIsInstance(applied_tags_3, list)
        self.assertIsInstance(applied_tags_4, list)

        # Question post should have 'question' tag due to '?' in title
        if applied_tags_2:
            self.assertIn("question", applied_tags_2)

        # Discussion post should have 'discussion' tag due to content patterns
        if applied_tags_3:
            self.assertIn("discussion", applied_tags_3)

        # Review post should have 'review' tag
        if applied_tags_4:
            self.assertIn("review", applied_tags_4)

    def test_search_with_combined_filters_and_tags(self):
        """Test search combining text, metadata filters, and tags."""
        # Create and apply tags
        self.tag_manager.create_tag("advanced")
        self.tag_manager.tag_post("ghi789", ["advanced"])  # JavaScript guide

        # Search with multiple criteria
        query = SearchQuery(text="JavaScript", min_upvotes=150, tags=["advanced"])
        results = self.search_engine.search(query)

        # Should find only the JavaScript post with high upvotes and 'advanced' tag
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].post_id, "ghi789")
        self.assertIn("JavaScript", results[0].title)
        self.assertGreaterEqual(results[0].upvotes, 150)
        self.assertIn("advanced", results[0].tags)

    def test_incremental_indexing_workflow(self):
        """Test incremental indexing when new posts are added."""
        # Get initial post count
        initial_stats = self.database.get_stats()
        initial_count = initial_stats["total_posts"]

        # Add a new post
        new_post_content = """**r/Python** | Posted by u/new_user ⬆️ 75

## New Python Post

Original post: [https://reddit.com/r/Python/comments/new123/](https://reddit.com/r/Python/comments/new123/)

> This is a new Python post added later.
"""

        new_file = os.path.join(self.temp_dir, "new_python_post.md")
        with open(new_file, "w", encoding="utf-8") as f:
            f.write(new_post_content)

        # Re-index directory (should only process new file)
        index_stats = self.indexer.index_directory(self.temp_dir)

        # Verify new post was indexed
        final_stats = self.database.get_stats()
        self.assertEqual(final_stats["total_posts"], initial_count + 1)
        self.assertEqual(index_stats["files_indexed"], 1)  # Only new file
        self.assertEqual(
            index_stats["files_skipped"], initial_count
        )  # Existing files skipped

        # Verify new post is searchable
        results = self.search_engine.search_simple("new Python")
        self.assertGreater(len(results), 0)
        new_post_found = any(r.post_id == "new123" for r in results)
        self.assertTrue(new_post_found)

    def test_tag_management_full_lifecycle(self):
        """Test complete tag management lifecycle."""
        # Create tags with metadata
        tag1 = self.tag_manager.create_tag("important", "Important posts", "#FF0000")
        tag2 = self.tag_manager.create_tag("favorites", "My favorite posts", "#00FF00")

        # List tags
        all_tags = self.tag_manager.list_tags()
        tag_names = [tag.name for tag in all_tags]
        self.assertIn("important", tag_names)
        self.assertIn("favorites", tag_names)

        # Apply tags to posts
        self.tag_manager.tag_post("abc123", ["important", "favorites"])
        self.tag_manager.tag_post("ghi789", ["important"])

        # Verify tag counts
        important_tag = self.tag_manager.get_tag("important")
        favorites_tag = self.tag_manager.get_tag("favorites")
        self.assertEqual(important_tag.post_count, 2)
        self.assertEqual(favorites_tag.post_count, 1)

        # Search by tags
        important_posts = self.search_engine.search(SearchQuery(tags=["important"]))
        favorites_posts = self.search_engine.search(SearchQuery(tags=["favorites"]))

        self.assertEqual(len(important_posts), 2)
        self.assertEqual(len(favorites_posts), 1)

        # Remove tags
        removed = self.tag_manager.untag_post("abc123", ["favorites"])
        self.assertEqual(removed, 1)

        # Verify tag count updated
        favorites_tag_updated = self.tag_manager.get_tag("favorites")
        self.assertEqual(favorites_tag_updated.post_count, 0)

        # Delete tag
        deleted = self.tag_manager.delete_tag("favorites")
        self.assertTrue(deleted)

        # Verify tag is gone
        deleted_tag = self.tag_manager.get_tag("favorites")
        self.assertIsNone(deleted_tag)

    def test_search_sorting_and_pagination(self):
        """Test search result sorting and pagination."""
        # Test sort by upvotes descending
        query = SearchQuery(sort_by="upvotes", sort_order="desc", limit=3)
        results = self.search_engine.search(query)

        self.assertLessEqual(len(results), 3)

        # Verify sorted order (descending upvotes)
        if len(results) > 1:
            for i in range(len(results) - 1):
                self.assertGreaterEqual(results[i].upvotes, results[i + 1].upvotes)

        # Test sort by date ascending
        query = SearchQuery(sort_by="date", sort_order="asc", limit=2)
        results = self.search_engine.search(query)

        self.assertLessEqual(len(results), 2)

        # Verify sorted order (ascending dates)
        if len(results) > 1:
            for i in range(len(results) - 1):
                self.assertLessEqual(results[i].created_utc, results[i + 1].created_utc)

    def test_search_suggestions_functionality(self):
        """Test search suggestions based on indexed content."""
        suggestions = self.search_engine.get_suggestions("Pyt", limit=5)

        # Should return suggestions containing "Pyt"
        self.assertIsInstance(suggestions, list)

        # If suggestions returned, they should be relevant
        if suggestions:
            for suggestion in suggestions:
                self.assertIsInstance(suggestion, str)
                # Note: Exact content depends on extraction logic

    def test_popular_searches_functionality(self):
        """Test popular searches based on indexed content."""
        popular = self.search_engine.get_popular_searches(limit=3)

        self.assertIsInstance(popular, list)
        self.assertLessEqual(len(popular), 3)

        if popular:
            for item in popular:
                self.assertIn("term", item)
                self.assertIn("type", item)
                self.assertIn("post_count", item)
                self.assertEqual(item["type"], "subreddit")

    def test_bulk_operations_integration(self):
        """Test bulk operations across the search system."""
        # Bulk tag multiple posts
        post_ids = ["abc123", "def456", "ghi789"]
        bulk_tags = ["bulk_test", "integration"]

        stats = self.tag_manager.bulk_tag_posts(post_ids, bulk_tags)

        self.assertEqual(stats["success"], 3)
        self.assertEqual(stats["failed"], 0)

        # Verify all posts have the bulk tags
        for post_id in post_ids:
            post_tags = self.tag_manager.get_post_tags(post_id)
            tag_names = [tag.name for tag in post_tags]
            self.assertIn("bulk_test", tag_names)
            self.assertIn("integration", tag_names)

        # Search by bulk tags
        query = SearchQuery(tags=["bulk_test"])
        results = self.search_engine.search(query)
        self.assertEqual(len(results), 3)

    def test_database_consistency_after_operations(self):
        """Test database consistency after various operations."""
        # Perform various operations
        self.tag_manager.create_tag("consistency_test")
        self.tag_manager.tag_post("abc123", ["consistency_test"])

        # Delete a post from database
        deleted = self.database.delete_post(
            os.path.join(self.temp_dir, "python_tutorial.md")
        )
        self.assertTrue(deleted)

        # Verify related data is cleaned up (tags should handle cascade)
        remaining_posts = self.database.search_posts()
        self.assertEqual(len(remaining_posts), 4)  # 5 - 1 deleted

        # Verify stats are consistent
        stats = self.database.get_stats()
        self.assertEqual(stats["total_posts"], 4)

    def test_error_handling_integration(self):
        """Test error handling across integrated components."""
        # Test search with invalid parameters
        query = SearchQuery(min_upvotes=-1, max_upvotes=-5)  # Invalid range
        results = self.search_engine.search(query)

        # Should handle gracefully and return empty or valid results
        self.assertIsInstance(results, list)

        # Test tagging non-existent post
        result = self.tag_manager.tag_post("nonexistent", ["test_tag"])
        self.assertEqual(result, 0)  # Should return 0, not crash

        # Test indexing corrupted file
        corrupted_file = os.path.join(self.temp_dir, "corrupted.md")
        with open(corrupted_file, "wb") as f:
            f.write(b"\xff\xfe\x00\x00")  # Invalid UTF-8

        result = self.indexer.index_file(corrupted_file)
        self.assertFalse(result)  # Should fail gracefully


if __name__ == "__main__":
    unittest.main()
