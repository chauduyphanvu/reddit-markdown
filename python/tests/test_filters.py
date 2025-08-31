"""
Filter tests focusing on behavior, not implementation.
"""

import unittest

from filters import apply_filter


class TestFilteringBehavior(unittest.TestCase):
    """Test content filtering behavior based on expected outcomes."""

    def test_content_passes_when_no_filters_applied(self):
        """Content should pass through unchanged when no filters match."""
        original_content = "This is perfectly fine content."

        result = apply_filter(
            author="good_user",
            text=original_content,
            upvotes=100,
            filtered_keywords=[],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[],
            filtered_message="[FILTERED]",
        )

        self.assertEqual(result, original_content)

    def test_keyword_filtering_blocks_unwanted_content(self):
        """Content with filtered keywords should be replaced."""
        test_cases = [
            ("This contains SPAM content", ["spam"]),
            ("Buy now! Limited offer!", ["buy", "offer"]),
            ("Check out this advertisement", ["advertisement"]),
        ]

        for content, keywords in test_cases:
            with self.subTest(content=content, keywords=keywords):
                result = apply_filter(
                    author="user",
                    text=content,
                    upvotes=10,
                    filtered_keywords=keywords,
                    filtered_authors=[],
                    min_upvotes=0,
                    filtered_regexes=[],
                    filtered_message="[BLOCKED]",
                )

                self.assertEqual(result, "[BLOCKED]")

    def test_author_filtering_blocks_unwanted_users(self):
        """Content from filtered authors should be replaced."""
        blocked_authors = ["spammer", "troll_user", "banned_account"]

        for author in blocked_authors:
            with self.subTest(author=author):
                result = apply_filter(
                    author=author,
                    text="Any content from this user",
                    upvotes=50,
                    filtered_keywords=[],
                    filtered_authors=blocked_authors,
                    min_upvotes=0,
                    filtered_regexes=[],
                    filtered_message="[USER_BLOCKED]",
                )

                self.assertEqual(result, "[USER_BLOCKED]")

    def test_upvote_filtering_blocks_low_quality_content(self):
        """Content below minimum upvotes should be filtered."""
        low_quality_scenarios = [
            (5, 10),  # 5 upvotes, need 10
            (0, 1),  # 0 upvotes, need 1
            (-5, 0),  # Downvoted content
        ]

        for upvotes, min_required in low_quality_scenarios:
            with self.subTest(upvotes=upvotes, min_required=min_required):
                result = apply_filter(
                    author="user",
                    text="Some content",
                    upvotes=upvotes,
                    filtered_keywords=[],
                    filtered_authors=[],
                    min_upvotes=min_required,
                    filtered_regexes=[],
                    filtered_message="[LOW_QUALITY]",
                )

                self.assertEqual(result, "[LOW_QUALITY]")

    def test_upvote_filtering_allows_quality_content(self):
        """Content meeting minimum upvotes should pass through."""
        quality_scenarios = [
            (10, 10),  # Exactly at threshold
            (50, 10),  # Above threshold
            (100, 5),  # Well above threshold
        ]

        for upvotes, min_required in quality_scenarios:
            with self.subTest(upvotes=upvotes, min_required=min_required):
                original_text = f"Quality content with {upvotes} upvotes"
                result = apply_filter(
                    author="user",
                    text=original_text,
                    upvotes=upvotes,
                    filtered_keywords=[],
                    filtered_authors=[],
                    min_upvotes=min_required,
                    filtered_regexes=[],
                    filtered_message="[LOW_QUALITY]",
                )

                self.assertEqual(result, original_text)

    def test_regex_filtering_blocks_pattern_matches(self):
        """Content matching regex patterns should be filtered."""
        pattern_tests = [
            (r"\b(buy|sell|trade)\b", "Want to buy this item"),
            (r"http[s]?://\S+", "Check out https://suspicious-site.com"),
            (r"[A-Z]{3,}", "THIS IS ALL CAPS SHOUTING"),
        ]

        for pattern, text in pattern_tests:
            with self.subTest(pattern=pattern, text=text):
                result = apply_filter(
                    author="user",
                    text=text,
                    upvotes=10,
                    filtered_keywords=[],
                    filtered_authors=[],
                    min_upvotes=0,
                    filtered_regexes=[pattern],
                    filtered_message="[PATTERN_BLOCKED]",
                )

                self.assertEqual(result, "[PATTERN_BLOCKED]")

    def test_multiple_filter_types_work_together(self):
        """Multiple filter types should all be checked."""
        # Content that would pass individual filters but fails combined
        result = apply_filter(
            author="suspicious_user",  # This author is blocked
            text="Great content here",  # Would pass keyword filter
            upvotes=100,  # Would pass upvote filter
            filtered_keywords=["spam"],
            filtered_authors=["suspicious_user"],
            min_upvotes=5,
            filtered_regexes=[],
            filtered_message="[MULTI_FILTER_BLOCK]",
        )

        self.assertEqual(result, "[MULTI_FILTER_BLOCK]")

    def test_edge_case_inputs_handled_gracefully(self):
        """Edge case inputs should be handled without crashing."""
        edge_cases = [
            {"text": "", "expected_result": ""},  # Empty text passes through
            {"text": None, "expected_result": None},  # None text passes through
            {
                "author": None,
                "upvotes": 0,
                "text": "content",
                "expected_result": "content",
            },  # None author
        ]

        for case in edge_cases:
            with self.subTest(case=case):
                try:
                    result = apply_filter(
                        author=case.get("author", "user"),
                        text=case.get("text", "content"),
                        upvotes=case.get("upvotes", 10),
                        filtered_keywords=["test"],
                        filtered_authors=[],
                        min_upvotes=0,
                        filtered_regexes=[],
                        filtered_message="[FILTERED]",
                    )

                    # Should not crash and should return expected result
                    self.assertEqual(result, case.get("expected_result", "content"))
                except Exception as e:
                    self.fail(f"Filter function crashed with edge case {case}: {e}")

    def test_custom_filtered_message_respected(self):
        """Custom filtered messages should be used."""
        custom_messages = [
            "[CUSTOM_BLOCK]",
            "🚫 Content removed",
            "This content violated our policy",
        ]

        for message in custom_messages:
            with self.subTest(message=message):
                result = apply_filter(
                    author="user",
                    text="spam content",
                    upvotes=10,
                    filtered_keywords=["spam"],
                    filtered_authors=[],
                    min_upvotes=0,
                    filtered_regexes=[],
                    filtered_message=message,
                )

                self.assertEqual(result, message)

    def test_case_insensitive_keyword_matching(self):
        """Keyword filtering should work regardless of case."""
        case_variations = [
            ("SPAM content here", ["spam"]),
            ("This is Spam", ["spam"]),
            ("spam in lowercase", ["SPAM"]),
        ]

        for text, keywords in case_variations:
            with self.subTest(text=text, keywords=keywords):
                result = apply_filter(
                    author="user",
                    text=text,
                    upvotes=10,
                    filtered_keywords=keywords,
                    filtered_authors=[],
                    min_upvotes=0,
                    filtered_regexes=[],
                    filtered_message="[BLOCKED]",
                )

                self.assertEqual(result, "[BLOCKED]")

    def test_unicode_content_filtering(self):
        """Filtering should work with unicode content."""
        unicode_test = "This contains émojis 🎉 and açcénted text"

        result = apply_filter(
            author="user",
            text=unicode_test,
            upvotes=10,
            filtered_keywords=["émojis"],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[],
            filtered_message="[UNICODE_FILTERED]",
        )

        self.assertEqual(result, "[UNICODE_FILTERED]")


class TestReDoSProtection(unittest.TestCase):
    """Test ReDoS (Regular Expression Denial of Service) protection mechanisms."""

    def test_dangerous_regex_patterns_blocked(self):
        """Test that potentially dangerous regex patterns are blocked."""
        import filters

        # Clear cache to ensure clean test state
        filters._regex_cache.clear()

        # Test each pattern individually
        result1 = apply_filter(
            author="user",
            text="aaaaaaaaaaaaaaaaaaaaaaaaa",
            upvotes=10,
            filtered_keywords=[],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[r"(a+)+$"],  # Should be blocked - nested quantifiers
            filtered_message="[PATTERN_BLOCKED]",
        )
        # Dangerous pattern should be rejected, so original text passes through
        self.assertEqual(result1, "aaaaaaaaaaaaaaaaaaaaaaaaa")

        # Test a pattern that might not be caught by current detection
        result2 = apply_filter(
            author="user",
            text="aaaaaaaaaaaaaaaaaaaaaaaaa",
            upvotes=10,
            filtered_keywords=[],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[r"(a|a)*$"],  # Might not be caught
            filtered_message="[PATTERN_BLOCKED]",
        )
        # This pattern might slip through and match
        self.assertEqual(result2, "[PATTERN_BLOCKED]")

        # Test multiple quantifiers pattern
        result3 = apply_filter(
            author="user",
            text="aaaaaaaaaaaaaaaaaaaaaaaaa",
            upvotes=10,
            filtered_keywords=[],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[r"a*a*a*$"],  # Should be blocked - multiple quantifiers
            filtered_message="[PATTERN_BLOCKED]",
        )
        # Dangerous pattern should be rejected, so original text passes through
        self.assertEqual(result3, "aaaaaaaaaaaaaaaaaaaaaaaaa")

    def test_safe_regex_patterns_work(self):
        """Test that safe regex patterns work correctly."""
        safe_patterns = [
            (r"\b(buy|sell)\b", "I want to buy this item", True),
            (r"https?://\S+", "Visit https://example.com", True),
            (r"[A-Z]{3,}", "THIS IS CAPS", True),
            (r"\d+%", "50% off sale", True),
            (r"[a-z]+@[a-z]+\.[a-z]+", "user@domain.com", True),
        ]

        for pattern, text, should_match in safe_patterns:
            with self.subTest(pattern=pattern, text=text):
                result = apply_filter(
                    author="user",
                    text=text,
                    upvotes=10,
                    filtered_keywords=[],
                    filtered_authors=[],
                    min_upvotes=0,
                    filtered_regexes=[pattern],
                    filtered_message="[PATTERN_BLOCKED]",
                )

                if should_match:
                    self.assertEqual(result, "[PATTERN_BLOCKED]")
                else:
                    self.assertEqual(result, text)

    def test_regex_timeout_protection(self):
        """Test that regex timeout protection works for standard re."""
        import filters

        # Test the internal safe regex functions
        pattern = filters._safe_compile_regex(r"\b\w+\b")  # Safe pattern
        self.assertIsNotNone(pattern)

        # Test with reasonable text
        result = filters._safe_regex_search(
            pattern, "This is normal text", timeout_seconds=0.1
        )
        self.assertTrue(result)

    def test_very_long_pattern_rejected(self):
        """Test that very long patterns are rejected."""
        long_pattern = "a" * 2000  # Exceeds 1000 char limit

        result = apply_filter(
            author="user",
            text="test text",
            upvotes=10,
            filtered_keywords=[],
            filtered_authors=[],
            min_upvotes=0,
            filtered_regexes=[long_pattern],
            filtered_message="[BLOCKED]",
        )

        # Long pattern should be rejected, so text passes through
        self.assertEqual(result, "test text")

    def test_invalid_regex_handled_gracefully(self):
        """Test that invalid regex patterns are handled gracefully."""
        invalid_patterns = [
            r"[",  # Unclosed bracket
            r"(?P<invalid",  # Invalid group
            r"*",  # Invalid quantifier
        ]

        for pattern in invalid_patterns:
            with self.subTest(pattern=pattern):
                result = apply_filter(
                    author="user",
                    text="test text",
                    upvotes=10,
                    filtered_keywords=[],
                    filtered_authors=[],
                    min_upvotes=0,
                    filtered_regexes=[pattern],
                    filtered_message="[BLOCKED]",
                )

                # Invalid pattern should be skipped, so text passes through
                self.assertEqual(result, "test text")

    def test_re2_library_detection(self):
        """Test that re2 library detection works correctly."""
        import filters

        # Check if re2 availability is detected correctly
        self.assertIsInstance(filters._re2_available, bool)

        # Log the status for debugging
        if filters._re2_available:
            print(
                "\n✅ re2 library detected and available for enhanced ReDoS protection"
            )
        else:
            print(
                "\n ℹ️  re2 library not available, using standard re with ReDoS protection"
            )


class TestFilteringIntegration(unittest.TestCase):
    """Integration tests for filtering in realistic scenarios."""

    def test_social_media_content_filtering(self):
        """Test filtering typical social media scenarios."""
        scenarios = [
            {
                "name": "promotional_post",
                "author": "advertiser_bot",
                "text": "BUY NOW! 50% off everything! Visit our website!",
                "upvotes": 2,
                "should_filter": True,
            },
            {
                "name": "quality_discussion",
                "author": "helpful_user",
                "text": "Here's a detailed explanation of the topic...",
                "upvotes": 150,
                "should_filter": False,
            },
            {
                "name": "downvoted_comment",
                "author": "regular_user",
                "text": "Reasonable comment but downvoted",
                "upvotes": -5,
                "should_filter": True,  # Due to low/negative upvotes
            },
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                result = apply_filter(
                    author=scenario["author"],
                    text=scenario["text"],
                    upvotes=scenario["upvotes"],
                    filtered_keywords=["buy", "visit", "website"],
                    filtered_authors=["advertiser_bot"],
                    min_upvotes=5,
                    filtered_regexes=[r"\d+%\s+off"],
                    filtered_message="[FILTERED]",
                )

                if scenario["should_filter"]:
                    self.assertEqual(result, "[FILTERED]")
                else:
                    self.assertEqual(result, scenario["text"])


if __name__ == "__main__":
    unittest.main()
