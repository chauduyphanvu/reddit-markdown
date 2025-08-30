import sys
import os
import unittest
import re

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from filters import apply_filter
from .test_utils import BaseTestCase


class TestApplyFilter(BaseTestCase):
    """Comprehensive test suite for filters.py module."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_author = "test_user"
        self.test_text = "This is a test comment."
        self.test_upvotes = 5
        self.filtered_message = "[FILTERED]"

        # Default empty filter lists
        self.empty_keywords = []
        self.empty_authors = []
        self.empty_regexes = []

    def test_no_filters_applied(self):
        """Test when no filters are triggered - should return original text."""
        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=self.empty_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.test_text)

    def test_keyword_filter_case_insensitive_match(self):
        """Test keyword filtering with case insensitive match."""
        keywords = ["test"]

        result = apply_filter(
            author=self.test_author,
            text="This is a TEST comment.",
            upvotes=self.test_upvotes,
            filtered_keywords=keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_keyword_filter_exact_match(self):
        """Test keyword filtering with exact match."""
        keywords = ["test"]

        result = apply_filter(
            author=self.test_author,
            text="This is a test comment.",
            upvotes=self.test_upvotes,
            filtered_keywords=keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_keyword_filter_partial_match(self):
        """Test keyword filtering with partial word match."""
        keywords = ["tes"]

        result = apply_filter(
            author=self.test_author,
            text="This is a test comment.",
            upvotes=self.test_upvotes,
            filtered_keywords=keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_keyword_filter_no_match(self):
        """Test keyword filtering when no keywords match."""
        keywords = ["xyz"]

        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.test_text)

    def test_multiple_keywords_one_matches(self):
        """Test multiple keywords where only one matches."""
        keywords = ["xyz", "test", "abc"]

        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_author_filter_exact_match(self):
        """Test author filtering with exact match."""
        filtered_authors = [self.test_author]

        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=self.empty_keywords,
            filtered_authors=filtered_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_author_filter_no_match(self):
        """Test author filtering when author is not in filtered list."""
        filtered_authors = ["different_user"]

        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=self.empty_keywords,
            filtered_authors=filtered_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.test_text)

    def test_author_filter_case_sensitive(self):
        """Test that author filtering is case sensitive."""
        filtered_authors = ["TEST_USER"]

        result = apply_filter(
            author=self.test_author,  # lowercase
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=self.empty_keywords,
            filtered_authors=filtered_authors,  # uppercase
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.test_text)

    def test_upvotes_filter_below_minimum(self):
        """Test upvotes filtering when upvotes are below minimum."""
        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=3,
            filtered_keywords=self.empty_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=5,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_upvotes_filter_equal_minimum(self):
        """Test upvotes filtering when upvotes equal minimum."""
        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=5,
            filtered_keywords=self.empty_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=5,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.test_text)

    def test_upvotes_filter_above_minimum(self):
        """Test upvotes filtering when upvotes are above minimum."""
        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=10,
            filtered_keywords=self.empty_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=5,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.test_text)

    def test_upvotes_filter_negative_upvotes(self):
        """Test upvotes filtering with negative upvotes."""
        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=-2,
            filtered_keywords=self.empty_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_regex_filter_simple_match(self):
        """Test regex filtering with simple pattern match."""
        regexes = [r"test"]

        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=self.empty_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_regex_filter_complex_pattern(self):
        """Test regex filtering with complex pattern."""
        regexes = [r"\b[Tt]est\b"]  # Word boundary test

        result = apply_filter(
            author=self.test_author,
            text="This is a test comment.",
            upvotes=self.test_upvotes,
            filtered_keywords=self.empty_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_regex_filter_no_match(self):
        """Test regex filtering when pattern doesn't match."""
        regexes = [r"xyz"]

        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=self.empty_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.test_text)

    def test_regex_filter_invalid_pattern(self):
        """Test regex filtering with invalid regex pattern."""
        regexes = [r"[invalid"]  # Invalid regex

        # Should handle invalid regex gracefully and return original text
        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=self.empty_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=regexes,
            filtered_message=self.filtered_message,
        )
        # Should return original text since invalid regex is skipped
        self.assertEqual(result, self.test_text)

    def test_multiple_regexes_one_matches(self):
        """Test multiple regex patterns where one matches."""
        regexes = [r"xyz", r"test", r"abc"]

        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=self.empty_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_filter_priority_keyword_first(self):
        """Test that filters are applied in order (keyword found first)."""
        keywords = ["test"]
        filtered_authors = [self.test_author]

        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=keywords,
            filtered_authors=filtered_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_all_filters_combined_no_match(self):
        """Test with all filter types but none matching."""
        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=["xyz"],
            filtered_authors=["other_user"],
            min_upvotes=0,
            filtered_regexes=[r"xyz"],
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.test_text)

    def test_empty_text(self):
        """Test filtering with empty text."""
        result = apply_filter(
            author=self.test_author,
            text="",
            upvotes=self.test_upvotes,
            filtered_keywords=["test"],
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, "")

    def test_none_text(self):
        """Test filtering with None text."""
        result = apply_filter(
            author=self.test_author,
            text=None,
            upvotes=self.test_upvotes,
            filtered_keywords=["test"],
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        # None text should be returned as-is (no filtering applied)
        self.assertIsNone(result)

    def test_none_author(self):
        """Test filtering with None author."""
        filtered_authors = [None]

        result = apply_filter(
            author=None,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=self.empty_keywords,
            filtered_authors=filtered_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_unicode_text_and_keywords(self):
        """Test filtering with unicode text and keywords."""
        unicode_text = "This is a tëst cômment with ünïcödé."
        unicode_keywords = ["tëst"]

        result = apply_filter(
            author=self.test_author,
            text=unicode_text,
            upvotes=self.test_upvotes,
            filtered_keywords=unicode_keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_special_characters_in_filtered_message(self):
        """Test with special characters in filtered message."""
        special_message = "🚫 [FILTERED] 🚫"

        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=["test"],
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=special_message,
        )

        self.assertEqual(result, special_message)

    def test_whitespace_only_keyword(self):
        """Test with whitespace-only keyword."""
        keywords = ["   "]

        result = apply_filter(
            author=self.test_author,
            text="   This has spaces   ",
            upvotes=self.test_upvotes,
            filtered_keywords=keywords,
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message=self.filtered_message,
        )

        self.assertEqual(result, self.filtered_message)

    def test_empty_filtered_message(self):
        """Test with empty filtered message."""
        result = apply_filter(
            author=self.test_author,
            text=self.test_text,
            upvotes=self.test_upvotes,
            filtered_keywords=["test"],
            filtered_authors=self.empty_authors,
            min_upvotes=0,
            filtered_regexes=self.empty_regexes,
            filtered_message="",
        )

        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
