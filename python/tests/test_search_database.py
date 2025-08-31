import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from search.search_database import SearchDatabase


class TestSearchDatabase(unittest.TestCase):
    """Test cases for SearchDatabase class."""

    def setUp(self):
        """Set up test database with temporary file."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db = SearchDatabase(self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database file."""
        self.db.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_database_initialization_creates_file(self):
        """Database initialization should create the database file."""
        self.assertTrue(os.path.exists(self.temp_db.name))

    def test_database_tables_are_created(self):
        """Database initialization should create required tables."""
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('posts', 'posts_fts', 'tags', 'post_tags')
            """
            )
            tables = [row[0] for row in cursor.fetchall()]

        expected_tables = {"posts", "posts_fts", "tags", "post_tags"}
        self.assertEqual(set(tables), expected_tables)

    def test_add_post_with_required_fields_succeeds(self):
        """Adding a post with required fields should succeed and return post ID."""
        post_data = {
            "file_path": "/test/path.md",
            "post_id": "abc123",
            "title": "Test Post",
            "content": "This is test content",
        }

        result = self.db.add_post(post_data)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_add_post_missing_required_field_raises_error(self):
        """Adding a post without required fields should raise ValueError."""
        post_data = {
            "file_path": "/test/path.md",
            "title": "Test Post",  # Missing post_id
        }

        with self.assertRaises(ValueError):
            self.db.add_post(post_data)

    def test_add_post_creates_fts_index_entry(self):
        """Adding a post with content should create FTS index entry."""
        post_data = {
            "file_path": "/test/path.md",
            "post_id": "abc123",
            "title": "Test Post",
            "content": "This is test content",
        }

        post_id = self.db.add_post(post_data)

        # Check FTS entry exists
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM posts_fts WHERE rowid = ?", (post_id,)
            )
            count = cursor.fetchone()[0]

        self.assertEqual(count, 1)

    def test_add_post_with_optional_metadata_stores_correctly(self):
        """Adding a post with optional metadata should store all fields."""
        post_data = {
            "file_path": "/test/path.md",
            "post_id": "abc123",
            "title": "Test Post",
            "author": "testuser",
            "subreddit": "r/test",
            "url": "https://reddit.com/test",
            "upvotes": 100,
            "reply_count": 25,
            "created_utc": 1609459200,  # 2021-01-01 00:00:00 UTC
        }

        post_id = self.db.add_post(post_data)
        stored_post = self.db.get_post_by_file_path("/test/path.md")

        self.assertEqual(stored_post["author"], "testuser")
        self.assertEqual(stored_post["subreddit"], "r/test")
        self.assertEqual(stored_post["upvotes"], 100)
        self.assertEqual(stored_post["reply_count"], 25)
        self.assertEqual(stored_post["created_utc"], 1609459200)

    def test_get_post_by_file_path_existing_post_returns_post(self):
        """Getting an existing post by file path should return the post data."""
        post_data = {
            "file_path": "/test/path.md",
            "post_id": "abc123",
            "title": "Test Post",
        }

        self.db.add_post(post_data)
        result = self.db.get_post_by_file_path("/test/path.md")

        self.assertIsNotNone(result)
        self.assertEqual(result["post_id"], "abc123")
        self.assertEqual(result["title"], "Test Post")

    def test_get_post_by_file_path_nonexistent_post_returns_none(self):
        """Getting a non-existent post by file path should return None."""
        result = self.db.get_post_by_file_path("/nonexistent/path.md")
        self.assertIsNone(result)

    def test_search_posts_no_params_returns_all_posts(self):
        """Searching without parameters should return all posts."""
        # Add test posts
        for i in range(3):
            self.db.add_post(
                {
                    "file_path": f"/test/path{i}.md",
                    "post_id": f"abc{i}",
                    "title": f"Test Post {i}",
                }
            )

        results = self.db.search_posts()
        self.assertEqual(len(results), 3)

    def test_search_posts_with_text_query_returns_matching_posts(self):
        """Searching with text query should return posts matching the text."""
        # Add posts with different content
        self.db.add_post(
            {
                "file_path": "/test/python.md",
                "post_id": "abc1",
                "title": "Python Tutorial",
                "content": "Learn Python programming basics",
            }
        )

        self.db.add_post(
            {
                "file_path": "/test/java.md",
                "post_id": "abc2",
                "title": "Java Guide",
                "content": "Java programming fundamentals",
            }
        )

        results = self.db.search_posts(query="Python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["post_id"], "abc1")

    def test_search_posts_with_subreddit_filter_returns_matching_posts(self):
        """Searching with subreddit filter should return posts from that subreddit."""
        self.db.add_post(
            {
                "file_path": "/test/post1.md",
                "post_id": "abc1",
                "title": "Post 1",
                "subreddit": "r/Python",
            }
        )

        self.db.add_post(
            {
                "file_path": "/test/post2.md",
                "post_id": "abc2",
                "title": "Post 2",
                "subreddit": "r/Java",
            }
        )

        results = self.db.search_posts(subreddit="r/Python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["subreddit"], "r/Python")

    def test_search_posts_with_min_upvotes_filter_returns_matching_posts(self):
        """Searching with minimum upvotes should return posts above threshold."""
        self.db.add_post(
            {
                "file_path": "/test/low.md",
                "post_id": "abc1",
                "title": "Low Upvotes",
                "upvotes": 5,
            }
        )

        self.db.add_post(
            {
                "file_path": "/test/high.md",
                "post_id": "abc2",
                "title": "High Upvotes",
                "upvotes": 150,
            }
        )

        results = self.db.search_posts(min_upvotes=100)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["post_id"], "abc2")

    def test_search_posts_respects_limit_parameter(self):
        """Searching with limit should return maximum specified number of results."""
        # Add 5 posts
        for i in range(5):
            self.db.add_post(
                {
                    "file_path": f"/test/post{i}.md",
                    "post_id": f"abc{i}",
                    "title": f"Post {i}",
                }
            )

        results = self.db.search_posts(limit=3)
        self.assertEqual(len(results), 3)

    def test_delete_post_existing_post_removes_post(self):
        """Deleting an existing post should remove it from database."""
        post_data = {
            "file_path": "/test/path.md",
            "post_id": "abc123",
            "title": "Test Post",
        }

        self.db.add_post(post_data)
        result = self.db.delete_post("/test/path.md")

        self.assertTrue(result)

    def test_delete_post_existing_post_removes_fts_entry(self):
        """Deleting an existing post should remove FTS index entry."""
        post_data = {
            "file_path": "/test/path.md",
            "post_id": "abc123",
            "title": "Test Post",
            "content": "Test content",
        }

        post_id = self.db.add_post(post_data)
        self.db.delete_post("/test/path.md")

        # Check FTS entry is removed
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM posts_fts WHERE rowid = ?", (post_id,)
            )
            count = cursor.fetchone()[0]

        self.assertEqual(count, 0)

    def test_delete_post_nonexistent_post_returns_false(self):
        """Deleting a non-existent post should return False."""
        result = self.db.delete_post("/nonexistent/path.md")
        self.assertFalse(result)

    def test_get_stats_empty_database_returns_zero_counts(self):
        """Getting stats from empty database should return zero counts."""
        stats = self.db.get_stats()

        self.assertEqual(stats["total_posts"], 0)
        self.assertEqual(stats["total_tags"], 0)
        self.assertEqual(stats["total_subreddits"], 0)
        self.assertEqual(stats["total_authors"], 0)

    def test_get_stats_with_data_returns_correct_counts(self):
        """Getting stats with data should return correct counts."""
        # Add posts with different subreddits and authors
        self.db.add_post(
            {
                "file_path": "/test/post1.md",
                "post_id": "abc1",
                "title": "Post 1",
                "author": "user1",
                "subreddit": "r/Python",
            }
        )

        self.db.add_post(
            {
                "file_path": "/test/post2.md",
                "post_id": "abc2",
                "title": "Post 2",
                "author": "user2",
                "subreddit": "r/Java",
            }
        )

        stats = self.db.get_stats()

        self.assertEqual(stats["total_posts"], 2)
        self.assertEqual(stats["total_subreddits"], 2)
        self.assertEqual(stats["total_authors"], 2)

    def test_add_post_replace_existing_updates_post(self):
        """Adding a post with same file path should update existing post."""
        # Add initial post
        post_data = {
            "file_path": "/test/path.md",
            "post_id": "abc123",
            "title": "Original Title",
        }

        original_id = self.db.add_post(post_data)

        # Update with new data
        updated_data = {
            "file_path": "/test/path.md",
            "post_id": "abc123",
            "title": "Updated Title",
        }

        updated_id = self.db.add_post(updated_data)

        # Should return same ID and update the post
        self.assertEqual(original_id, updated_id)

        stored_post = self.db.get_post_by_file_path("/test/path.md")
        self.assertEqual(stored_post["title"], "Updated Title")


if __name__ == "__main__":
    unittest.main()
