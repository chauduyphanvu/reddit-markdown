"""
Integration tests for standalone archive CLI tool.
"""

import unittest
import tempfile
import os
import json
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from cli_archive import ArchiveCLI


class TestArchiveCLIBehavior(unittest.TestCase):
    """Test standalone archive CLI tool."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cli = ArchiveCLI()

        # Create test files for archiving
        self._create_test_content()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_content(self):
        """Create test Reddit posts for archiving."""
        test_posts = {
            "r_python/post1.md": "# Python Discussion\n\nGreat discussion about Python!",
            "r_science/post2.md": "# Science News\n\nLatest scientific breakthrough.",
            "r_programming/nested/post3.md": "# Programming Tips\n\nUseful coding tips.",
            "general_post.md": "# General Post\n\nGeneral Reddit discussion.",
        }

        for file_path, content in test_posts.items():
            full_path = Path(self.temp_dir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

    def test_cli_create_command_basic(self):
        """CLI create command should create archive successfully."""
        args = ["create", self.temp_dir]

        # Mock to suppress actual archive creation for speed
        archive_path = os.path.join(self.temp_dir, "test.zip")
        with open(archive_path, "wb") as f:
            f.write(b"fake archive content")

        with patch("cli_archive.create_archive_with_progress") as mock_create:
            mock_create.return_value = archive_path
            result = self.cli.run(args)

        self.assertEqual(result, 0)
        mock_create.assert_called_once()

    def test_cli_create_command_with_format(self):
        """CLI create command should accept format specification."""
        args = ["create", self.temp_dir, "--format", "zip", "--level", "9"]

        # Mock to suppress actual archive creation for speed
        archive_path = os.path.join(self.temp_dir, "test.zip")
        with open(archive_path, "wb") as f:
            f.write(b"fake archive content")

        with patch("cli_archive.create_archive_with_progress") as mock_create:
            mock_create.return_value = archive_path
            result = self.cli.run(args)

        self.assertEqual(result, 0)
        call_args = mock_create.call_args
        self.assertEqual(call_args[1]["compression_format"], "zip")
        self.assertEqual(call_args[1]["compression_level"], 9)

    def test_cli_create_command_nonexistent_directory(self):
        """CLI create command should fail for nonexistent directory."""
        args = ["create", "/nonexistent/directory"]
        result = self.cli.run(args)
        self.assertEqual(result, 1)

    def test_cli_info_command(self):
        """CLI info command should display archive information."""
        # Create a test ZIP archive
        archive_path = os.path.join(self.temp_dir, "test.zip")
        with zipfile.ZipFile(archive_path, "w") as zipf:
            zipf.writestr("test.md", "# Test Post")

        args = ["info", archive_path]

        with patch("cli_archive.logger") as mock_logger:
            result = self.cli.run(args)

        self.assertEqual(result, 0)
        mock_logger.info.assert_called()

    def test_cli_verify_command_valid_archive(self):
        """CLI verify command should pass for valid archives."""
        # Create a test ZIP archive
        archive_path = os.path.join(self.temp_dir, "test.zip")
        with zipfile.ZipFile(archive_path, "w") as zipf:
            zipf.writestr("test.md", "# Test Post")

        args = ["verify", archive_path]
        result = self.cli.run(args)

        self.assertEqual(result, 0)

    def test_cli_verify_command_invalid_archive(self):
        """CLI verify command should fail for invalid archives."""
        # Create invalid archive file
        archive_path = os.path.join(self.temp_dir, "invalid.zip")
        with open(archive_path, "wb") as f:
            f.write(b"invalid data")

        args = ["verify", archive_path]
        result = self.cli.run(args)

        self.assertEqual(result, 1)

    def test_cli_formats_command(self):
        """CLI formats command should list available formats."""
        args = ["formats"]

        with patch("cli_archive.logger") as mock_logger:
            result = self.cli.run(args)

        self.assertEqual(result, 0)
        mock_logger.info.assert_called()

    def test_cli_no_command(self):
        """CLI should show help when no command is provided."""
        result = self.cli.run([])
        self.assertEqual(result, 1)


class TestArchiveCLIEdgeCases(unittest.TestCase):
    """Test edge cases in archive CLI."""

    def setUp(self):
        self.cli = ArchiveCLI()

    def test_cli_create_empty_directory(self):
        """CLI should handle empty directories gracefully."""
        temp_dir = tempfile.mkdtemp()
        try:
            args = ["create", temp_dir]
            result = self.cli.run(args)
            self.assertEqual(result, 1)  # Should fail for empty directory
        finally:
            os.rmdir(temp_dir)

    def test_cli_info_nonexistent_file(self):
        """CLI info command should fail for nonexistent files."""
        args = ["info", "/nonexistent/archive.zip"]
        result = self.cli.run(args)
        self.assertEqual(result, 1)

    def test_cli_verify_nonexistent_file(self):
        """CLI verify command should fail for nonexistent files."""
        args = ["verify", "/nonexistent/archive.zip"]
        result = self.cli.run(args)
        self.assertEqual(result, 1)

    def test_cli_keyboard_interrupt(self):
        """CLI should handle keyboard interrupts gracefully."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create test file
            test_file = Path(temp_dir) / "test.md"
            with open(test_file, "w") as f:
                f.write("test")

            args = ["create", temp_dir]

            with patch(
                "cli_archive.create_archive_with_progress",
                side_effect=KeyboardInterrupt,
            ):
                result = self.cli.run(args)
                self.assertEqual(result, 130)

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
