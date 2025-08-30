import unittest
from unittest.mock import patch
import sys
import logging

from cli_args import CommandLineArgs, _parse_csv


class TestParseCsv(unittest.TestCase):
    """Test the _parse_csv helper function."""

    def setUp(self):
        """Set up test fixtures."""
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Clean up after tests."""
        logging.disable(logging.NOTSET)

    def test_parse_csv_basic(self):
        """Test basic CSV parsing."""
        result = _parse_csv("item1,item2,item3")
        self.assertEqual(result, ["item1", "item2", "item3"])

    def test_parse_csv_with_spaces(self):
        """Test CSV parsing with whitespace around items."""
        result = _parse_csv("item1, item2 , item3")
        self.assertEqual(result, ["item1", "item2", "item3"])

    def test_parse_csv_empty_string(self):
        """Test CSV parsing with empty string."""
        result = _parse_csv("")
        self.assertEqual(result, [])

    def test_parse_csv_none(self):
        """Test CSV parsing with None input."""
        result = _parse_csv(None)
        self.assertEqual(result, [])

    def test_parse_csv_single_item(self):
        """Test CSV parsing with single item."""
        result = _parse_csv("single_item")
        self.assertEqual(result, ["single_item"])

    def test_parse_csv_with_empty_items(self):
        """Test CSV parsing with empty items (should be filtered out)."""
        result = _parse_csv("item1,,item3,")
        self.assertEqual(result, ["item1", "item3"])

    def test_parse_csv_only_commas(self):
        """Test CSV parsing with only commas."""
        result = _parse_csv(",,,")
        self.assertEqual(result, [])

    def test_parse_csv_whitespace_only_items(self):
        """Test CSV parsing with whitespace-only items (should be filtered out)."""
        result = _parse_csv("item1,   ,item3, \t ")
        self.assertEqual(result, ["item1", "item3"])

    def test_parse_csv_with_special_characters(self):
        """Test CSV parsing with special characters."""
        result = _parse_csv("item!@#, $%^&*(), item_with_underscores")
        self.assertEqual(result, ["item!@#", "$%^&*()", "item_with_underscores"])

    def test_parse_csv_with_urls(self):
        """Test CSV parsing with Reddit URLs."""
        urls = "https://reddit.com/r/test/1,https://reddit.com/r/test/2"
        result = _parse_csv(urls)
        expected = ["https://reddit.com/r/test/1", "https://reddit.com/r/test/2"]
        self.assertEqual(result, expected)


class TestCommandLineArgs(unittest.TestCase):
    """Test the CommandLineArgs class."""

    def setUp(self):
        """Set up test fixtures."""
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Clean up after tests."""
        logging.disable(logging.NOTSET)

    @patch.object(sys, "argv", ["script.py"])
    def test_no_arguments(self):
        """Test with no command line arguments."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, [])
        self.assertEqual(args.src_files, [])
        self.assertEqual(args.subs, [])
        self.assertEqual(args.multis, [])

    @patch.object(sys, "argv", ["script.py", "--urls", "https://reddit.com/r/test/1"])
    def test_single_url(self):
        """Test with single URL argument."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, ["https://reddit.com/r/test/1"])
        self.assertEqual(args.src_files, [])
        self.assertEqual(args.subs, [])
        self.assertEqual(args.multis, [])

    @patch.object(sys, "argv", ["script.py", "--urls", "url1,url2,url3"])
    def test_multiple_urls(self):
        """Test with multiple URLs."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, ["url1", "url2", "url3"])
        self.assertEqual(args.src_files, [])
        self.assertEqual(args.subs, [])
        self.assertEqual(args.multis, [])

    @patch.object(sys, "argv", ["script.py", "--src-files", "file1.txt,file2.txt"])
    def test_src_files(self):
        """Test with source files argument."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, [])
        self.assertEqual(args.src_files, ["file1.txt", "file2.txt"])
        self.assertEqual(args.subs, [])
        self.assertEqual(args.multis, [])

    @patch.object(sys, "argv", ["script.py", "--subs", "r/python,r/askreddit"])
    def test_subreddits(self):
        """Test with subreddits argument."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, [])
        self.assertEqual(args.src_files, [])
        self.assertEqual(args.subs, ["r/python", "r/askreddit"])
        self.assertEqual(args.multis, [])

    @patch.object(sys, "argv", ["script.py", "--multis", "m/programming,m/news"])
    def test_multireddits(self):
        """Test with multireddits argument."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, [])
        self.assertEqual(args.src_files, [])
        self.assertEqual(args.subs, [])
        self.assertEqual(args.multis, ["m/programming", "m/news"])

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
    def test_all_arguments_combined(self):
        """Test with all arguments combined."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, ["url1", "url2"])
        self.assertEqual(args.src_files, ["file1.txt"])
        self.assertEqual(args.subs, ["r/python"])
        self.assertEqual(args.multis, ["m/programming"])

    @patch.object(sys, "argv", ["script.py", "--urls", ""])
    def test_empty_urls_argument(self):
        """Test with empty URLs argument."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, [])
        self.assertEqual(args.src_files, [])
        self.assertEqual(args.subs, [])
        self.assertEqual(args.multis, [])

    @patch.object(sys, "argv", ["script.py", "--urls", "url1, , url3"])
    def test_urls_with_empty_items(self):
        """Test URLs argument with empty items."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, ["url1", "url3"])
        self.assertEqual(args.src_files, [])
        self.assertEqual(args.subs, [])
        self.assertEqual(args.multis, [])

    @patch.object(sys, "argv", ["script.py", "--subs", "r/python, , r/askreddit,   "])
    def test_subs_with_whitespace_and_empty_items(self):
        """Test subreddits argument with whitespace and empty items."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, [])
        self.assertEqual(args.src_files, [])
        self.assertEqual(args.subs, ["r/python", "r/askreddit"])
        self.assertEqual(args.multis, [])

    @patch.object(sys, "argv", ["script.py", "--multis", ""])
    def test_empty_multis_argument(self):
        """Test with empty multireddits argument."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, [])
        self.assertEqual(args.src_files, [])
        self.assertEqual(args.subs, [])
        self.assertEqual(args.multis, [])

    @patch.object(
        sys, "argv", ["script.py", "--src-files", "/path/with spaces/file.txt"]
    )
    def test_src_files_with_spaces(self):
        """Test source files with spaces in path."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, [])
        self.assertEqual(args.src_files, ["/path/with spaces/file.txt"])
        self.assertEqual(args.subs, [])
        self.assertEqual(args.multis, [])

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
    def test_realistic_arguments(self):
        """Test with realistic argument combinations."""
        args = CommandLineArgs()

        expected_urls = ["https://www.reddit.com/r/python/comments/abc123/test_post/"]
        expected_subs = ["r/python", "r/learnpython", "r/django"]

        self.assertEqual(args.urls, expected_urls)
        self.assertEqual(args.src_files, [])
        self.assertEqual(args.subs, expected_subs)
        self.assertEqual(args.multis, [])

    def test_help_argument(self):
        """Test that help argument works (should exit with SystemExit)."""
        with patch.object(sys, "argv", ["script.py", "--help"]):
            with self.assertRaises(SystemExit):
                CommandLineArgs()

    def test_parser_attributes(self):
        """Test that the parser has the correct attributes."""
        with patch.object(sys, "argv", ["script.py"]):
            args = CommandLineArgs()

            # Test that the parser exists and has the expected actions
            parser_actions = [action.dest for action in args.parser._actions]

            expected_actions = ["help", "urls", "src_files", "subs", "multis"]
            for action in expected_actions:
                self.assertIn(action, parser_actions)

    @patch.object(sys, "argv", ["script.py", "--urls", "url1,url2", "--urls", "url3"])
    def test_multiple_same_arguments(self):
        """Test behavior with multiple instances of same argument (last one should win)."""
        args = CommandLineArgs()

        # argparse behavior: later values override earlier ones
        self.assertEqual(args.urls, ["url3"])

    @patch.object(
        sys,
        "argv",
        [
            "script.py",
            "--urls",
            "  url1  ,  url2  ",
            "--subs",
            "  r/python  ,  r/askreddit  ",
        ],
    )
    def test_arguments_with_extra_whitespace(self):
        """Test arguments with extra whitespace."""
        args = CommandLineArgs()

        self.assertEqual(args.urls, ["url1", "url2"])
        self.assertEqual(args.subs, ["r/python", "r/askreddit"])


if __name__ == "__main__":
    unittest.main()
