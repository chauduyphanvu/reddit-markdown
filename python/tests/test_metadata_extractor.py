import os
import tempfile
import unittest
from pathlib import Path

from search.metadata_extractor import MetadataExtractor


class TestMetadataExtractor(unittest.TestCase):
    """Test cases for MetadataExtractor class."""

    def setUp(self):
        """Set up test extractor and temporary directory."""
        self.extractor = MetadataExtractor()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_file(self, filename: str, content: str) -> str:
        """Create a test file with given content."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_extract_from_nonexistent_file_returns_none(self):
        """Extracting from non-existent file should return None."""
        result = self.extractor.extract_from_file("/nonexistent/file.md")
        self.assertIsNone(result)

    def test_extract_from_empty_file_returns_none(self):
        """Extracting from empty file should return None."""
        file_path = self._create_test_file("empty.md", "")
        result = self.extractor.extract_from_file(file_path)
        self.assertIsNone(result)

    def test_extract_basic_reddit_post_extracts_metadata(self):
        """Extracting from basic Reddit post should return metadata."""
        content = """**r/Python** | Posted by u/testuser ⬆️ 150 _(2023-01-15 10:30:00)_

## How to learn Python effectively?

Original post: [https://www.reddit.com/r/Python/comments/abc123/how_to_learn_python_effectively/](https://www.reddit.com/r/Python/comments/abc123/how_to_learn_python_effectively/)

> I'm new to programming and want to learn Python. Any suggestions?

💬 ~ 25 replies

---
"""

        file_path = self._create_test_file("test_post.md", content)
        result = self.extractor.extract_from_file(file_path)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "How to learn Python effectively?")
        self.assertEqual(result["author"], "testuser")
        self.assertEqual(result["subreddit"], "r/Python")
        self.assertEqual(result["upvotes"], 150)
        self.assertEqual(result["reply_count"], 25)
        self.assertEqual(
            result["url"],
            "https://www.reddit.com/r/Python/comments/abc123/how_to_learn_python_effectively/",
        )

    def test_extract_post_with_minimal_content_extracts_title(self):
        """Extracting from minimal Reddit post should extract at least title."""
        content = """**r/test** | Posted by u/user

## Simple test post

This is just a test.
"""

        file_path = self._create_test_file("minimal.md", content)
        result = self.extractor.extract_from_file(file_path)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Simple test post")
        self.assertEqual(result["author"], "user")
        self.assertEqual(result["subreddit"], "r/test")

    def test_extract_post_without_title_returns_none(self):
        """Extracting from post without title should return None."""
        content = """**r/test** | Posted by u/user

Some content without a title header.
"""

        file_path = self._create_test_file("no_title.md", content)
        result = self.extractor.extract_from_file(file_path)

        self.assertIsNone(result)

    def test_extract_includes_file_metadata(self):
        """Extraction should include file path and modification time."""
        content = """**r/test** | Posted by u/user

## Test post
"""

        file_path = self._create_test_file("test.md", content)
        result = self.extractor.extract_from_file(file_path)

        self.assertEqual(result["file_path"], file_path)
        self.assertIn("file_modified_time", result)
        self.assertIn("content", result)
        self.assertIn("content_preview", result)

    def test_parse_upvote_count_handles_k_suffix(self):
        """Upvote parsing should handle 'k' suffix correctly."""
        test_cases = [
            ("150", 150),
            ("1k", 1000),
            ("1.5k", 1500),
            ("2.3k", 2300),
            ("invalid", 0),
        ]

        for input_str, expected in test_cases:
            result = self.extractor._parse_upvote_count(input_str)
            self.assertEqual(result, expected)

    def test_parse_timestamp_converts_to_epoch(self):
        """Timestamp parsing should convert to Unix epoch."""
        timestamp_str = "2023-01-15 10:30:00"
        result = self.extractor._parse_timestamp(timestamp_str)

        # Should be a positive integer (Unix timestamp)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_parse_timestamp_invalid_format_returns_zero(self):
        """Invalid timestamp format should return 0."""
        result = self.extractor._parse_timestamp("invalid-date")
        self.assertEqual(result, 0)

    def test_extract_post_id_from_url_extracts_correctly(self):
        """Post ID extraction from URL should work correctly."""
        url = "https://www.reddit.com/r/Python/comments/abc123/title/"
        result = self.extractor.patterns["post_id_from_url"].search(url)

        self.assertIsNotNone(result)
        self.assertEqual(result.group(1), "abc123")

    def test_extract_post_id_from_filename_extracts_correctly(self):
        """Post ID extraction from filename should work correctly."""
        # Test various filename patterns
        test_cases = [
            ("r_Python_abc123.md", "abc123"),
            ("post_def456.md", "def456"),
            ("abc123.md", "abc123"),
        ]

        for filename, expected_id in test_cases:
            file_path = self._create_test_file(
                filename,
                """**r/test** | Posted by u/user

## Test post""",
            )

            result = self.extractor.extract_from_file(file_path)
            self.assertEqual(result["post_id"], expected_id)

    def test_generate_preview_creates_readable_summary(self):
        """Content preview generation should create readable summary."""
        content = """**r/Python** | Posted by u/testuser

## How to learn Python?

Original post: [url](url)

> This is the main content of the post.
> It spans multiple lines and contains
> some interesting information about Python.

💬 ~ 5 replies
"""

        preview = self.extractor._generate_preview(content, max_length=50)

        self.assertIsInstance(preview, str)
        self.assertLessEqual(len(preview), 53)  # Account for ellipsis
        # Preview should contain some of the actual content
        self.assertTrue(len(preview) > 0)
        self.assertNotEqual(preview, "No preview available")

    def test_generate_preview_handles_empty_content(self):
        """Preview generation should handle empty content gracefully."""
        preview = self.extractor._generate_preview("", max_length=100)
        self.assertEqual(preview, "No preview available")

    def test_strip_markdown_removes_formatting(self):
        """Markdown stripping should remove formatting elements."""
        markdown_text = """**Bold text** and *italic text* with `code` and [link](url)
        
> Quote text
        
More text."""

        result = self.extractor._strip_markdown(markdown_text)

        self.assertNotIn("**", result)
        self.assertNotIn("*", result)
        self.assertNotIn("`", result)
        self.assertNotIn("[", result)
        self.assertNotIn(">", result)
        self.assertIn("Bold text", result)
        self.assertIn("code", result)

    def test_is_reddit_markdown_file_identifies_reddit_files(self):
        """Reddit file identification should correctly identify Reddit posts."""
        # Valid Reddit markdown content
        reddit_content = """**r/Python** | Posted by u/testuser

## Test Post

Original post: [https://reddit.com/r/Python/comments/abc123/](https://reddit.com/r/Python/comments/abc123/)

💬 ~ 5 replies"""

        reddit_file = self._create_test_file("reddit.md", reddit_content)
        result = self.extractor.is_reddit_markdown_file(reddit_file)
        self.assertTrue(result)

    def test_is_reddit_markdown_file_rejects_non_reddit_files(self):
        """Reddit file identification should reject non-Reddit files."""
        # Regular markdown content
        regular_content = """# Regular Markdown

This is just a regular markdown file without Reddit-specific patterns."""

        regular_file = self._create_test_file("regular.md", regular_content)
        result = self.extractor.is_reddit_markdown_file(regular_file)
        self.assertFalse(result)

    def test_is_reddit_markdown_file_handles_nonexistent_file(self):
        """Reddit file identification should handle non-existent files."""
        result = self.extractor.is_reddit_markdown_file("/nonexistent/file.md")
        self.assertFalse(result)

    def test_extract_handles_post_with_special_characters(self):
        """Extraction should handle posts with special characters in title."""
        content = """**r/programming** | Posted by u/coder ⬆️ 42

## How to handle UTF-8 encoding in Python? 🐍

Original post: [url](url)

> Content with special chars: α, β, γ, emoji: 🚀"""

        file_path = self._create_test_file("special_chars.md", content)
        result = self.extractor.extract_from_file(file_path)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "How to handle UTF-8 encoding in Python? 🐍")
        self.assertEqual(result["upvotes"], 42)

    def test_extract_handles_post_with_no_upvotes(self):
        """Extraction should handle posts without upvote information."""
        content = """**r/test** | Posted by u/user

## Post without upvotes

No upvote info in this post."""

        file_path = self._create_test_file("no_upvotes.md", content)
        result = self.extractor.extract_from_file(file_path)

        self.assertIsNotNone(result)
        self.assertNotIn("upvotes", result)

    def test_extract_handles_deleted_author(self):
        """Extraction should handle posts by deleted users."""
        content = """**r/test** | Posted by u/[deleted]

## Post by deleted user

This post was made by a deleted user."""

        file_path = self._create_test_file("deleted_user.md", content)
        result = self.extractor.extract_from_file(file_path)

        self.assertIsNotNone(result)
        self.assertEqual(result["author"], "[deleted]")


if __name__ == "__main__":
    unittest.main()
