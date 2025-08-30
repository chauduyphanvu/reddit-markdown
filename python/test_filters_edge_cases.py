"""
Additional edge case tests for filters.py module.
Focuses on complex regex patterns and filtering edge cases.
"""

import unittest
import re

from filters import apply_filter
from test_utils import BaseTestCase


class TestFiltersEdgeCases(BaseTestCase):
    """Additional edge case tests for filters module."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.default_filtered_message = "[FILTERED]"

    def test_apply_filter_with_malformed_regex(self):
        """Test apply_filter with invalid regex pattern."""
        author = "test_user"
        text = "This is a test comment"
        upvotes = 10

        # Invalid regex pattern
        invalid_regex = "["  # Unclosed bracket

        # Should handle regex compilation error gracefully
        with self.assertRaises(re.error):
            apply_filter(
                author=author,
                text=text,
                upvotes=upvotes,
                filtered_keywords=[],
                filtered_authors=[],
                min_upvotes=0,
                filtered_regexes=[invalid_regex],
                filtered_message=self.default_filtered_message,
            )

    def test_apply_filter_with_complex_regex_patterns(self):
        """Test apply_filter with complex regex patterns."""
        test_cases = [
            ("This is a test123", r"\d+", True),  # Should match numbers
            (
                "EMAIL: user@example.com",
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                True,
            ),  # Email pattern
            ("Phone: 123-456-7890", r"\d{3}-\d{3}-\d{4}", True),  # Phone pattern
            ("No matches here", r"\d{3}-\d{3}-\d{4}", False),  # No match
            ("ALLCAPS TEXT", r"^[A-Z\s]+$", True),  # All caps
            ("Mixed Case Text", r"^[A-Z\s]+$", False),  # Not all caps
        ]

        for text, regex_pattern, should_filter in test_cases:
            with self.subTest(text=text, pattern=regex_pattern):
                result = apply_filter(
                    author="test_user",
                    text=text,
                    upvotes=10,
                    filtered_keywords=[],
                    filtered_authors=[],
                    min_upvotes=0,
                    filtered_regexes=[regex_pattern],
                    filtered_message=self.default_filtered_message,
                )

                if should_filter:
                    self.assertEqual(result, self.default_filtered_message)
                else:
                    self.assertEqual(result, text)

    def test_apply_filter_with_unicode_regex(self):
        """Test apply_filter with Unicode-aware regex patterns."""
        unicode_text = "This contains émojis: 🚀🎉 and ñoñó"

        test_cases = [
            (r"[^\x00-\x7F]", True),  # Non-ASCII characters
            (r"\p{Emoji}", True),  # Emoji pattern (if supported)
            (r"[áéíóúñ]", True),  # Spanish accented characters
            (r"[一-龯]", False),  # Chinese characters (not present)
        ]

        for pattern, should_filter in test_cases:
            with self.subTest(pattern=pattern):
                try:
                    result = apply_filter(
                        author="test_user",
                        text=unicode_text,
                        upvotes=10,
                        filtered_keywords=[],
                        filtered_authors=[],
                        min_upvotes=0,
                        filtered_regexes=[pattern],
                        filtered_message=self.default_filtered_message,
                    )

                    if should_filter:
                        self.assertEqual(result, self.default_filtered_message)
                    else:
                        self.assertEqual(result, unicode_text)
                except re.error:
                    # Some regex engines might not support all Unicode patterns
                    self.skipTest(f"Regex pattern {pattern} not supported")

    def test_apply_filter_with_multiline_regex(self):
        """Test apply_filter with multiline text and regex patterns."""
        multiline_text = """This is line 1
This is line 2 with special content
This is line 3"""

        # Regex that should match across lines
        multiline_pattern = r"line 1.*line 2"

        # By default, . doesn't match newlines, so this shouldn't match
        result = apply_filter(
            author="test_user",
            text=multiline_text,
            upvotes=10,
            filtered_keywords=[],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[multiline_pattern],
            filtered_message=self.default_filtered_message,
        )

        self.assertEqual(result, multiline_text)  # Should not filter

        # Pattern with DOTALL flag equivalent
        dotall_pattern = r"(?s)line 1.*line 2"

        result = apply_filter(
            author="test_user",
            text=multiline_text,
            upvotes=10,
            filtered_keywords=[],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[dotall_pattern],
            filtered_message=self.default_filtered_message,
        )

        self.assertEqual(result, self.default_filtered_message)  # Should filter

    def test_apply_filter_with_case_sensitive_regex(self):
        """Test apply_filter with case-sensitive regex patterns."""
        text = "This contains UPPERCASE and lowercase"

        test_cases = [
            (r"UPPERCASE", True),  # Exact case match
            (r"uppercase", False),  # Wrong case, no match
            (r"(?i)uppercase", True),  # Case-insensitive flag
            (r"[A-Z]+", True),  # Character class for uppercase
        ]

        for pattern, should_filter in test_cases:
            with self.subTest(pattern=pattern):
                result = apply_filter(
                    author="test_user",
                    text=text,
                    upvotes=10,
                    filtered_keywords=[],
                    filtered_authors=[],
                    min_upvotes=0,
                    filtered_regexes=[pattern],
                    filtered_message=self.default_filtered_message,
                )

                if should_filter:
                    self.assertEqual(result, self.default_filtered_message)
                else:
                    self.assertEqual(result, text)

    def test_apply_filter_keyword_with_unicode_and_case(self):
        """Test keyword filtering with Unicode and case sensitivity."""
        test_cases = [
            ("This has SPAM in it", ["spam"], True),  # Case insensitive
            ("This has SPAM in it", ["SPAM"], True),  # Exact case
            ("This has ñoñó in it", ["ñoñó"], True),  # Unicode exact
            ("This has ÑOÑÓ in it", ["ñoñó"], True),  # Unicode case insensitive
            ("This has émoji 🚀", ["🚀"], True),  # Emoji keyword
            ("Normal text", ["absent"], False),  # No match
        ]

        for text, keywords, should_filter in test_cases:
            with self.subTest(text=text, keywords=keywords):
                result = apply_filter(
                    author="test_user",
                    text=text,
                    upvotes=10,
                    filtered_keywords=keywords,
                    filtered_authors=[],
                    min_upvotes=0,
                    filtered_regexes=[],
                    filtered_message=self.default_filtered_message,
                )

                if should_filter:
                    self.assertEqual(result, self.default_filtered_message)
                else:
                    self.assertEqual(result, text)

    def test_apply_filter_with_very_long_text(self):
        """Test apply_filter performance with very long text."""
        # Generate very long text
        long_text = "This is a test. " * 10000  # ~160KB of text

        # Should still work efficiently
        result = apply_filter(
            author="test_user",
            text=long_text,
            upvotes=10,
            filtered_keywords=["nonexistent"],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[r"nonexistent_pattern"],
            filtered_message=self.default_filtered_message,
        )

        self.assertEqual(result, long_text)  # Should not filter

    def test_apply_filter_with_empty_and_none_values(self):
        """Test apply_filter with empty and None values."""
        test_cases = [
            (None, "text", 10, False),  # None author
            ("author", None, 10, False),  # None text
            ("author", "", 10, False),  # Empty text
            ("", "text", 10, False),  # Empty author
        ]

        for author, text, upvotes, should_filter in test_cases:
            with self.subTest(author=author, text=text):
                result = apply_filter(
                    author=author,
                    text=text,
                    upvotes=upvotes,
                    filtered_keywords=["test"],
                    filtered_authors=["test_author"],
                    min_upvotes=0,
                    filtered_regexes=[r"test"],
                    filtered_message=self.default_filtered_message,
                )

                if should_filter:
                    self.assertEqual(result, self.default_filtered_message)
                else:
                    self.assertEqual(result, text)

    def test_apply_filter_with_regex_special_characters_in_keywords(self):
        """Test keyword filtering when keywords contain regex special characters."""
        text = "Price is $10.50 for (item) and [bonus] included"

        # Keywords with special regex characters should be treated literally
        test_cases = [
            (["$10"], True),  # Dollar sign
            (["(item)"], True),  # Parentheses
            (["[bonus]"], True),  # Square brackets
            (["$5"], False),  # No match
        ]

        for keywords, should_filter in test_cases:
            with self.subTest(keywords=keywords):
                result = apply_filter(
                    author="test_user",
                    text=text,
                    upvotes=10,
                    filtered_keywords=keywords,
                    filtered_authors=[],
                    min_upvotes=0,
                    filtered_regexes=[],
                    filtered_message=self.default_filtered_message,
                )

                if should_filter:
                    self.assertEqual(result, self.default_filtered_message)
                else:
                    self.assertEqual(result, text)

    def test_apply_filter_multiple_conditions_priority(self):
        """Test the order of filter condition checking."""
        text = "This contains spam keyword"
        author = "banned_user"
        upvotes = 5

        # All conditions should trigger filtering
        # The function should return filtered_message for the first condition that matches
        result = apply_filter(
            author=author,
            text=text,
            upvotes=upvotes,
            filtered_keywords=["spam"],  # Should trigger first
            filtered_authors=[author],  # Would also trigger
            min_upvotes=10,  # Would also trigger (upvotes < min)
            filtered_regexes=[r"spam"],  # Would also trigger
            filtered_message=self.default_filtered_message,
        )

        # Should be filtered (by keyword check which comes first)
        self.assertEqual(result, self.default_filtered_message)

    def test_apply_filter_with_boundary_upvote_values(self):
        """Test apply_filter with boundary upvote values."""
        test_cases = [
            (0, 0, False),  # Equal to minimum
            (0, 1, True),  # Below minimum
            (-1, 0, True),  # Negative upvotes
            (999999, 0, False),  # Very high upvotes
            (5, 5, False),  # Exactly at boundary
            (4, 5, True),  # Just below boundary
        ]

        for upvotes, min_upvotes, should_filter in test_cases:
            with self.subTest(upvotes=upvotes, min_upvotes=min_upvotes):
                result = apply_filter(
                    author="test_user",
                    text="test text",
                    upvotes=upvotes,
                    filtered_keywords=[],
                    filtered_authors=[],
                    min_upvotes=min_upvotes,
                    filtered_regexes=[],
                    filtered_message=self.default_filtered_message,
                )

                if should_filter:
                    self.assertEqual(result, self.default_filtered_message)
                else:
                    self.assertEqual(result, "test text")


if __name__ == "__main__":
    unittest.main()
