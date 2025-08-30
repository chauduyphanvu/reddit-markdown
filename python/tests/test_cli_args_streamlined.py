"""
Streamlined CLI args tests focusing on input/output behavior.
"""

import sys
import unittest
from unittest.mock import patch

from cli_args import CommandLineArgs, _parse_csv


class TestCSVParsing(unittest.TestCase):
    """Test CSV parsing behavior with single assertions per test."""

    def test_parse_csv_splits_comma_separated_items(self):
        """CSV parsing should split comma-separated items."""
        result = _parse_csv("item1,item2,item3")
        self.assertEqual(result, ["item1", "item2", "item3"])

    def test_parse_csv_removes_whitespace_around_items(self):
        """CSV parsing should strip whitespace around items."""
        result = _parse_csv("item1, item2 , item3")
        self.assertEqual(result, ["item1", "item2", "item3"])

    def test_parse_csv_returns_empty_list_for_empty_string(self):
        """CSV parsing should return empty list for empty string."""
        result = _parse_csv("")
        self.assertEqual(result, [])

    def test_parse_csv_handles_none_input(self):
        """CSV parsing should handle None input gracefully."""
        result = _parse_csv(None)
        self.assertEqual(result, [])

    def test_parse_csv_handles_single_item(self):
        """CSV parsing should handle single items without commas."""
        result = _parse_csv("single_item")
        self.assertEqual(result, ["single_item"])

    def test_parse_csv_filters_empty_items(self):
        """CSV parsing should filter out empty items."""
        result = _parse_csv("item1,,item3,")
        self.assertEqual(result, ["item1", "item3"])

    def test_parse_csv_handles_only_commas(self):
        """CSV parsing should handle input with only commas."""
        result = _parse_csv(",,,")
        self.assertEqual(result, [])

    def test_parse_csv_filters_whitespace_only_items(self):
        """CSV parsing should filter out whitespace-only items."""
        result = _parse_csv("item1,   ,item3, \t ")
        self.assertEqual(result, ["item1", "item3"])

    def test_parse_csv_preserves_special_characters(self):
        """CSV parsing should preserve special characters in items."""
        result = _parse_csv("item!@#, $%^&*(), item_with_underscores")
        self.assertEqual(result, ["item!@#", "$%^&*()", "item_with_underscores"])

    def test_parse_csv_handles_url_strings(self):
        """CSV parsing should handle Reddit URL strings."""
        urls = "https://reddit.com/r/test/1,https://reddit.com/r/test/2"
        result = _parse_csv(urls)
        self.assertEqual(
            result, ["https://reddit.com/r/test/1", "https://reddit.com/r/test/2"]
        )


class TestCommandLineArgumentParsing(unittest.TestCase):
    """Test command line argument parsing behavior with single assertions per test."""

    @patch.object(sys, "argv", ["script.py"])
    def test_no_arguments_produces_empty_urls(self):
        """No arguments should result in empty URL list."""
        args = CommandLineArgs()
        self.assertEqual(args.urls, [])

    @patch.object(sys, "argv", ["script.py"])
    def test_no_arguments_produces_empty_src_files(self):
        """No arguments should result in empty source files list."""
        args = CommandLineArgs()
        self.assertEqual(args.src_files, [])

    @patch.object(sys, "argv", ["script.py"])
    def test_no_arguments_produces_empty_subs(self):
        """No arguments should result in empty subreddits list."""
        args = CommandLineArgs()
        self.assertEqual(args.subs, [])

    @patch.object(sys, "argv", ["script.py"])
    def test_no_arguments_produces_empty_multis(self):
        """No arguments should result in empty multireddits list."""
        args = CommandLineArgs()
        self.assertEqual(args.multis, [])

    @patch.object(sys, "argv", ["script.py", "--urls", "https://reddit.com/r/test/1"])
    def test_single_url_argument_parsed_correctly(self):
        """Single URL argument should be parsed into URLs list."""
        args = CommandLineArgs()
        self.assertEqual(args.urls, ["https://reddit.com/r/test/1"])

    @patch.object(sys, "argv", ["script.py", "--urls", "url1,url2,url3"])
    def test_multiple_urls_argument_parsed_correctly(self):
        """Multiple URLs in comma-separated string should be parsed."""
        args = CommandLineArgs()
        self.assertEqual(args.urls, ["url1", "url2", "url3"])

    @patch.object(sys, "argv", ["script.py", "--src-files", "file1.txt,file2.txt"])
    def test_src_files_argument_parsed_correctly(self):
        """Source files argument should be parsed into list."""
        args = CommandLineArgs()
        self.assertEqual(args.src_files, ["file1.txt", "file2.txt"])

    @patch.object(sys, "argv", ["script.py", "--subs", "r/python,r/askreddit"])
    def test_subreddits_argument_parsed_correctly(self):
        """Subreddits argument should be parsed into list."""
        args = CommandLineArgs()
        self.assertEqual(args.subs, ["r/python", "r/askreddit"])

    @patch.object(sys, "argv", ["script.py", "--multis", "m/programming,m/news"])
    def test_multireddits_argument_parsed_correctly(self):
        """Multireddits argument should be parsed into list."""
        args = CommandLineArgs()
        self.assertEqual(args.multis, ["m/programming", "m/news"])

    @patch.object(sys, "argv", ["script.py", "--urls", ""])
    def test_empty_urls_argument_produces_empty_list(self):
        """Empty URLs argument should produce empty list."""
        args = CommandLineArgs()
        self.assertEqual(args.urls, [])

    @patch.object(sys, "argv", ["script.py", "--urls", "url1, , url3"])
    def test_urls_with_empty_items_filters_correctly(self):
        """URLs argument with empty items should filter them out."""
        args = CommandLineArgs()
        self.assertEqual(args.urls, ["url1", "url3"])

    @patch.object(sys, "argv", ["script.py", "--subs", "r/python, , r/askreddit,   "])
    def test_subs_with_whitespace_filters_correctly(self):
        """Subreddits argument should filter whitespace and empty items."""
        args = CommandLineArgs()
        self.assertEqual(args.subs, ["r/python", "r/askreddit"])

    @patch.object(
        sys, "argv", ["script.py", "--src-files", "/path/with spaces/file.txt"]
    )
    def test_src_files_handles_spaces_in_paths(self):
        """Source files should handle spaces in file paths."""
        args = CommandLineArgs()
        self.assertEqual(args.src_files, ["/path/with spaces/file.txt"])

    @patch.object(sys, "argv", ["script.py", "--urls", "url1,url2", "--urls", "url3"])
    def test_multiple_same_arguments_uses_last_value(self):
        """Multiple instances of same argument should use the last value."""
        args = CommandLineArgs()
        self.assertEqual(args.urls, ["url3"])

    @patch.object(sys, "argv", ["script.py", "--urls", "  url1  ,  url2  "])
    def test_arguments_strip_extra_whitespace(self):
        """Arguments should strip extra whitespace from items."""
        args = CommandLineArgs()
        self.assertEqual(args.urls, ["url1", "url2"])

    def test_help_argument_triggers_system_exit(self):
        """Help argument should trigger SystemExit."""
        with patch.object(sys, "argv", ["script.py", "--help"]):
            with self.assertRaises(SystemExit):
                CommandLineArgs()

    @patch.object(sys, "argv", ["script.py"])
    def test_parser_has_urls_action(self):
        """Parser should have URLs action configured."""
        args = CommandLineArgs()
        parser_actions = [action.dest for action in args.parser._actions]
        self.assertIn("urls", parser_actions)

    @patch.object(sys, "argv", ["script.py"])
    def test_parser_has_src_files_action(self):
        """Parser should have source files action configured."""
        args = CommandLineArgs()
        parser_actions = [action.dest for action in args.parser._actions]
        self.assertIn("src_files", parser_actions)

    @patch.object(sys, "argv", ["script.py"])
    def test_parser_has_subs_action(self):
        """Parser should have subreddits action configured."""
        args = CommandLineArgs()
        parser_actions = [action.dest for action in args.parser._actions]
        self.assertIn("subs", parser_actions)

    @patch.object(sys, "argv", ["script.py"])
    def test_parser_has_multis_action(self):
        """Parser should have multireddits action configured."""
        args = CommandLineArgs()
        parser_actions = [action.dest for action in args.parser._actions]
        self.assertIn("multis", parser_actions)


class TestCliArgsIntegration(unittest.TestCase):
    """Integration tests for realistic CLI argument scenarios."""

    @patch.object(
        sys,
        "argv",
        [
            "script.py",
            "--urls",
            "https://www.reddit.com/r/python/comments/abc123/test_post/",
            "--subs",
            "r/python,r/learnpython,r/django",
        ],
    )
    def test_realistic_mixed_arguments_urls_parsed(self):
        """Realistic mixed arguments should parse URLs correctly."""
        args = CommandLineArgs()
        expected_urls = ["https://www.reddit.com/r/python/comments/abc123/test_post/"]
        self.assertEqual(args.urls, expected_urls)

    @patch.object(
        sys,
        "argv",
        [
            "script.py",
            "--urls",
            "https://www.reddit.com/r/python/comments/abc123/test_post/",
            "--subs",
            "r/python,r/learnpython,r/django",
        ],
    )
    def test_realistic_mixed_arguments_subs_parsed(self):
        """Realistic mixed arguments should parse subreddits correctly."""
        args = CommandLineArgs()
        expected_subs = ["r/python", "r/learnpython", "r/django"]
        self.assertEqual(args.subs, expected_subs)

    @patch.object(
        sys,
        "argv",
        [
            "script.py",
            "--urls",
            "url1,url2",
            "--src-files",
            "file1.txt",
            "--subs",
            "r/python",
            "--multis",
            "m/programming",
        ],
    )
    def test_all_argument_types_urls_populated(self):
        """All argument types should populate URLs correctly."""
        args = CommandLineArgs()
        self.assertEqual(args.urls, ["url1", "url2"])

    @patch.object(
        sys,
        "argv",
        [
            "script.py",
            "--urls",
            "url1,url2",
            "--src-files",
            "file1.txt",
            "--subs",
            "r/python",
            "--multis",
            "m/programming",
        ],
    )
    def test_all_argument_types_src_files_populated(self):
        """All argument types should populate source files correctly."""
        args = CommandLineArgs()
        self.assertEqual(args.src_files, ["file1.txt"])

    @patch.object(
        sys,
        "argv",
        [
            "script.py",
            "--urls",
            "url1,url2",
            "--src-files",
            "file1.txt",
            "--subs",
            "r/python",
            "--multis",
            "m/programming",
        ],
    )
    def test_all_argument_types_subs_populated(self):
        """All argument types should populate subreddits correctly."""
        args = CommandLineArgs()
        self.assertEqual(args.subs, ["r/python"])

    @patch.object(
        sys,
        "argv",
        [
            "script.py",
            "--urls",
            "url1,url2",
            "--src-files",
            "file1.txt",
            "--subs",
            "r/python",
            "--multis",
            "m/programming",
        ],
    )
    def test_all_argument_types_multis_populated(self):
        """All argument types should populate multireddits correctly."""
        args = CommandLineArgs()
        self.assertEqual(args.multis, ["m/programming"])


if __name__ == "__main__":
    unittest.main()
