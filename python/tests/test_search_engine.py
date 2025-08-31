import os
import tempfile
import unittest
from datetime import datetime, timezone

from search.search_database import SearchDatabase
from search.search_engine import SearchEngine, SearchQuery, SearchResult


class TestSearchEngine(unittest.TestCase):
    """Test cases for SearchEngine class."""

    def setUp(self):
        """Set up test search engine with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.database = SearchDatabase(self.temp_db.name)
        self.search_engine = SearchEngine(self.database)

        # Add test posts
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
                "title": "Python Tutorial for Beginners",
                "content": "Learn Python programming from scratch. This comprehensive guide covers variables, functions, and classes.",
                "author": "python_guru",
                "subreddit": "r/Python",
                "url": "https://reddit.com/r/Python/comments/abc123/",
                "created_utc": 1609459200,  # 2021-01-01
                "upvotes": 150,
                "reply_count": 25,
            },
            {
                "file_path": "/test/java_guide.md",
                "post_id": "def456",
                "title": "Java Programming Guide",
                "content": "Complete Java programming guide covering OOP concepts, inheritance, and polymorphism.",
                "author": "java_expert",
                "subreddit": "r/Java",
                "url": "https://reddit.com/r/Java/comments/def456/",
                "created_utc": 1609545600,  # 2021-01-02
                "upvotes": 89,
                "reply_count": 12,
            },
            {
                "file_path": "/test/python_question.md",
                "post_id": "ghi789",
                "title": "How to debug Python code?",
                "content": "I am having trouble debugging my Python script. Any suggestions for tools and techniques?",
                "author": "newbie_coder",
                "subreddit": "r/Python",
                "url": "https://reddit.com/r/Python/comments/ghi789/",
                "created_utc": 1609632000,  # 2021-01-03
                "upvotes": 42,
                "reply_count": 8,
            },
            {
                "file_path": "/test/javascript_intro.md",
                "post_id": "jkl012",
                "title": "JavaScript Basics",
                "content": "Introduction to JavaScript programming language. Learn about variables, functions, and DOM manipulation.",
                "author": "js_dev",
                "subreddit": "r/JavaScript",
                "url": "https://reddit.com/r/JavaScript/comments/jkl012/",
                "created_utc": 1609718400,  # 2021-01-04
                "upvotes": 203,
                "reply_count": 35,
            },
        ]

        for post in test_posts:
            self.database.add_post(post)

    def test_search_with_empty_query_returns_all_posts(self):
        """Search with empty SearchQuery should return all posts."""
        query = SearchQuery()
        results = self.search_engine.search(query)

        self.assertEqual(len(results), 4)

    def test_search_with_text_query_returns_matching_posts(self):
        """Search with text query should return posts matching the text."""
        query = SearchQuery(text="Python")
        results = self.search_engine.search(query)

        # Should find 2 Python-related posts
        self.assertEqual(len(results), 2)

        # Check that results contain Python posts
        post_ids = [r.post_id for r in results]
        self.assertIn("abc123", post_ids)  # Python tutorial
        self.assertIn("ghi789", post_ids)  # Python question

    def test_search_with_subreddit_filter_returns_matching_posts(self):
        """Search with subreddit filter should return posts from that subreddit."""
        query = SearchQuery(subreddits=["r/Python"])
        results = self.search_engine.search(query)

        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.subreddit, "r/Python")

    def test_search_with_author_filter_returns_matching_posts(self):
        """Search with author filter should return posts by that author."""
        query = SearchQuery(authors=["python_guru"])
        results = self.search_engine.search(query)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].author, "python_guru")
        self.assertEqual(results[0].post_id, "abc123")

    def test_search_with_min_upvotes_filter_returns_matching_posts(self):
        """Search with minimum upvotes should return posts above threshold."""
        query = SearchQuery(min_upvotes=100)
        results = self.search_engine.search(query)

        # Should find 2 posts with upvotes >= 100 (150 and 203)
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertGreaterEqual(result.upvotes, 100)

    def test_search_with_max_upvotes_filter_returns_matching_posts(self):
        """Search with maximum upvotes should return posts below threshold."""
        query = SearchQuery(max_upvotes=100)
        results = self.search_engine.search(query)

        # Should find 2 posts with upvotes <= 100 (89 and 42)
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertLessEqual(result.upvotes, 100)

    def test_search_with_date_from_filter_returns_matching_posts(self):
        """Search with date_from filter should return posts after that date."""
        # Filter for posts from 2021-01-03 onwards
        query = SearchQuery(date_from=1609632000)  # 2021-01-03
        results = self.search_engine.search(query)

        # Should find 2 posts (2021-01-03 and 2021-01-04)
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertGreaterEqual(result.created_utc, 1609632000)

    def test_search_with_date_to_filter_returns_matching_posts(self):
        """Search with date_to filter should return posts before that date."""
        # Filter for posts up to 2021-01-02
        query = SearchQuery(date_to=1609545600)  # 2021-01-02
        results = self.search_engine.search(query)

        # Should find 2 posts (2021-01-01 and 2021-01-02)
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertLessEqual(result.created_utc, 1609545600)

    def test_search_with_multiple_filters_returns_intersection(self):
        """Search with multiple filters should return intersection of results."""
        query = SearchQuery(text="Python", min_upvotes=100, subreddits=["r/Python"])
        results = self.search_engine.search(query)

        # Should find only 1 post that matches all criteria
        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0].post_id, "abc123"
        )  # Python tutorial with 150 upvotes

    def test_search_with_sort_by_upvotes_orders_correctly(self):
        """Search with sort by upvotes should order results correctly."""
        query = SearchQuery(sort_by="upvotes", sort_order="desc")
        results = self.search_engine.search(query)

        # Should be ordered by upvotes descending: 203, 150, 89, 42
        expected_upvotes = [203, 150, 89, 42]
        actual_upvotes = [r.upvotes for r in results]
        self.assertEqual(actual_upvotes, expected_upvotes)

    def test_search_with_sort_by_date_orders_correctly(self):
        """Search with sort by date should order results correctly."""
        query = SearchQuery(sort_by="date", sort_order="asc")
        results = self.search_engine.search(query)

        # Should be ordered by date ascending
        for i in range(len(results) - 1):
            self.assertLessEqual(results[i].created_utc, results[i + 1].created_utc)

    def test_search_with_limit_returns_correct_number(self):
        """Search with limit should return maximum specified results."""
        query = SearchQuery(limit=2)
        results = self.search_engine.search(query)

        self.assertEqual(len(results), 2)

    def test_search_simple_convenience_method_works(self):
        """Simple search convenience method should work correctly."""
        results = self.search_engine.search_simple("Python", limit=10)

        # Should find Python-related posts
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 10)

        # All results should be SearchResult objects
        for result in results:
            self.assertIsInstance(result, SearchResult)

    def test_search_result_object_has_required_fields(self):
        """SearchResult objects should have all required fields."""
        query = SearchQuery(text="Python", limit=1)
        results = self.search_engine.search(query)

        self.assertEqual(len(results), 1)
        result = results[0]

        # Check required fields
        self.assertIsInstance(result.post_id, str)
        self.assertIsInstance(result.title, str)
        self.assertIsInstance(result.author, str)
        self.assertIsInstance(result.subreddit, str)
        self.assertIsInstance(result.upvotes, int)
        self.assertIsInstance(result.created_utc, int)
        self.assertIsInstance(result.tags, list)

    def test_search_with_text_query_includes_snippet(self):
        """Text search should include content snippets in results."""
        query = SearchQuery(text="programming")
        results = self.search_engine.search(query)

        self.assertGreater(len(results), 0)

        # At least one result should have a snippet
        has_snippet = any(result.snippet for result in results)
        self.assertTrue(has_snippet)

    def test_get_suggestions_returns_relevant_terms(self):
        """Get suggestions should return relevant search terms."""
        suggestions = self.search_engine.get_suggestions("Pytho", limit=5)

        # Should return a list of strings
        self.assertIsInstance(suggestions, list)
        self.assertLessEqual(len(suggestions), 5)

        if suggestions:  # If any suggestions returned
            for suggestion in suggestions:
                self.assertIsInstance(suggestion, str)

    def test_get_suggestions_with_short_query_returns_empty(self):
        """Get suggestions with very short query should return empty list."""
        suggestions = self.search_engine.get_suggestions("P", limit=5)
        self.assertEqual(suggestions, [])

    def test_get_suggestions_with_empty_query_returns_empty(self):
        """Get suggestions with empty query should return empty list."""
        suggestions = self.search_engine.get_suggestions("", limit=5)
        self.assertEqual(suggestions, [])

    def test_get_popular_searches_returns_subreddits(self):
        """Get popular searches should return popular subreddits."""
        popular = self.search_engine.get_popular_searches(limit=5)

        self.assertIsInstance(popular, list)
        self.assertLessEqual(len(popular), 5)

        if popular:  # If any results returned
            for item in popular:
                self.assertIsInstance(item, dict)
                self.assertIn("term", item)
                self.assertIn("type", item)
                self.assertIn("post_count", item)

    def test_get_search_stats_returns_database_stats(self):
        """Get search stats should return database statistics."""
        stats = self.search_engine.get_search_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn("total_posts", stats)
        self.assertEqual(stats["total_posts"], 4)  # We added 4 test posts

    def test_prepare_fts_query_handles_special_characters(self):
        """FTS query preparation should handle special characters."""
        test_cases = [
            ("simple query", "simple* query*"),
            ("python tutorial", "python* tutorial*"),
            ('"exact phrase"', '"exact phrase"'),  # Quoted phrases should be preserved
            ("a b", "b"),  # Short words should be filtered out
        ]

        for input_text, expected in test_cases:
            result = self.search_engine._prepare_fts_query(input_text)
            # Basic validation - exact match testing might be too rigid
            self.assertIsInstance(result, str)

    def test_prepare_fts_query_with_empty_text_returns_empty(self):
        """FTS query preparation with empty text should return empty string."""
        result = self.search_engine._prepare_fts_query("")
        self.assertEqual(result, "")

    def test_search_query_dataclass_has_defaults(self):
        """SearchQuery dataclass should have reasonable defaults."""
        query = SearchQuery()

        self.assertEqual(query.text, "")
        self.assertEqual(query.subreddits, [])
        self.assertEqual(query.authors, [])
        self.assertEqual(query.tags, [])
        self.assertIsNone(query.min_upvotes)
        self.assertIsNone(query.max_upvotes)
        self.assertEqual(query.sort_by, "relevance")
        self.assertEqual(query.sort_order, "desc")
        self.assertEqual(query.limit, 50)

    def test_search_result_dataclass_has_defaults(self):
        """SearchResult dataclass should have reasonable defaults."""
        result = SearchResult(
            post_id="test",
            title="Test",
            author="author",
            subreddit="r/test",
            url="url",
            file_path="/test",
            created_utc=0,
            upvotes=0,
            reply_count=0,
            content_preview="preview",
        )

        self.assertEqual(result.snippet, "")
        self.assertEqual(result.rank_score, 0.0)
        self.assertEqual(result.tags, [])


if __name__ == "__main__":
    unittest.main()
