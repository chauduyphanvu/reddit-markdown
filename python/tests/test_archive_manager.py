"""
Tests for the new modular archive system.

This test suite validates the decomposed archive components work correctly
both individually and when orchestrated together.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from io_ops import (
    SecurityValidator,
    ArchiveLimitsExceededError,
    PathSecurityError,
    FileScanner,
    ArchiveFileCollector,
    FileStats,
    ZipArchiveCreator,
    ZstdArchiveCreator,
    ArchiveCreatorFactory,
    MetadataGenerator,
    ArchiveMetadataManager,
    ArchiveVerifier,
    ArchivePathGenerator,
    ArchiveManager,
)


class TestSecurityValidator(unittest.TestCase):
    """Test security validation component."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SecurityValidator(validate_paths=True)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_extension_validation(self):
        """Test file extension validation."""
        md_file = Path(self.temp_dir) / "test.md"
        exe_file = Path(self.temp_dir) / "test.exe"

        md_file.touch()
        exe_file.touch()

        self.assertTrue(self.validator.validate_file_extension(md_file))
        self.assertFalse(self.validator.validate_file_extension(exe_file))

    def test_path_safety_validation(self):
        """Test path traversal prevention."""
        base_path = Path(self.temp_dir)
        safe_file = base_path / "safe.md"

        safe_file.touch()

        self.assertTrue(self.validator.validate_path_safety(safe_file, base_path))

    def test_content_validation_text_files(self):
        """Test content validation for text files."""
        # Valid text file
        text_file = Path(self.temp_dir) / "test.txt"
        text_file.write_text("This is a valid text file", encoding="utf-8")
        self.assertTrue(self.validator.validate_file_content(text_file))

        # Valid markdown file
        md_file = Path(self.temp_dir) / "test.md"
        md_file.write_text("# This is markdown content", encoding="utf-8")
        self.assertTrue(self.validator.validate_file_content(md_file))

    def test_content_validation_json_files(self):
        """Test content validation for JSON files."""
        # Valid JSON file
        json_file = Path(self.temp_dir) / "test.json"
        json_file.write_text('{"key": "value"}', encoding="utf-8")
        self.assertTrue(self.validator.validate_file_content(json_file))

        # Invalid JSON file (looks like text)
        invalid_json = Path(self.temp_dir) / "invalid.json"
        invalid_json.write_text("This is not JSON", encoding="utf-8")
        self.assertFalse(self.validator.validate_file_content(invalid_json))

    def test_content_validation_html_xml_files(self):
        """Test content validation for HTML/XML files."""
        # Valid HTML file
        html_file = Path(self.temp_dir) / "test.html"
        html_file.write_text(
            "<!DOCTYPE html><html><body>Test</body></html>", encoding="utf-8"
        )
        self.assertTrue(self.validator.validate_file_content(html_file))

        # Valid XML file
        xml_file = Path(self.temp_dir) / "test.xml"
        xml_file.write_text('<?xml version="1.0"?><root>Test</root>', encoding="utf-8")
        self.assertTrue(self.validator.validate_file_content(xml_file))

        # Invalid HTML file (doesn't start with <)
        invalid_html = Path(self.temp_dir) / "invalid.html"
        invalid_html.write_text("This is not HTML", encoding="utf-8")
        self.assertFalse(self.validator.validate_file_content(invalid_html))

    def test_content_validation_dangerous_files(self):
        """Test detection of dangerous file types by magic numbers."""
        # Simulate Windows executable (MZ header)
        exe_file = Path(self.temp_dir) / "disguised.txt"
        exe_file.write_bytes(b"MZ\x90\x00This is a disguised executable")
        self.assertFalse(self.validator.validate_file_content(exe_file))

        # Simulate ZIP file (PK header)
        zip_file = Path(self.temp_dir) / "disguised.md"
        zip_file.write_bytes(b"PK\x03\x04This looks like a ZIP file")
        self.assertFalse(self.validator.validate_file_content(zip_file))

    def test_content_validation_binary_in_text(self):
        """Test detection of binary content in text files."""
        # Text file with null bytes (suspicious)
        binary_text = Path(self.temp_dir) / "binary.txt"
        binary_text.write_bytes(b"This has null\x00bytes in it")
        self.assertFalse(self.validator.validate_file_content(binary_text))

    def test_content_validation_disabled(self):
        """Test that content validation can be disabled."""
        validator_no_content = SecurityValidator(
            validate_paths=True, validate_content=False
        )

        # Even a dangerous file should pass when content validation is disabled
        dangerous_file = Path(self.temp_dir) / "dangerous.txt"
        dangerous_file.write_bytes(b"MZ\x90\x00Executable content")
        self.assertTrue(validator_no_content.validate_file_content(dangerous_file))

    def test_archive_name_sanitization(self):
        """Test archive name sanitization."""
        dangerous_name = "../../../etc/passwd"
        sanitized = self.validator.sanitize_archive_name(dangerous_name)

        self.assertEqual(sanitized, "_/_/_/etc/passwd")
        self.assertNotIn("..", sanitized)


class TestFileScanner(unittest.TestCase):
    """Test file scanning component."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SecurityValidator(validate_paths=True)
        self.scanner = FileScanner(self.validator)

        # Create test files
        test_files = {
            "good1.md": "Content 1",
            "good2.txt": "Content 2",
            "bad.exe": "Bad content",
            "subdir/nested.md": "Nested content",
        }

        for file_path, content in test_files.items():
            full_path = Path(self.temp_dir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_directory_scanning(self):
        """Test directory scanning finds all files."""
        files = self.scanner.scan_directory(Path(self.temp_dir))
        self.assertEqual(len(files), 4)  # All files including .exe

    def test_file_validation_with_security(self):
        """Test file validation respects security settings."""
        source_path = Path(self.temp_dir)
        files, stats = self.scanner.get_files_to_archive(source_path)

        # Should exclude .exe file due to security validation
        self.assertEqual(len(files), 3)  # good1.md, good2.txt, nested.md
        self.assertEqual(stats.skipped_files, 1)  # .exe file skipped

    def test_content_validation_integration(self):
        """Test integration of content validation in file scanning."""
        # Create a temporary directory for this test
        temp_dir = tempfile.mkdtemp()

        try:
            # Create files with dangerous content disguised as safe extensions
            dangerous_files = {
                "disguised_exe.txt": b"MZ\x90\x00This is an executable disguised as txt",
                "disguised_zip.md": b"PK\x03\x04This is a zip file disguised as markdown",
                "valid_text.txt": b"This is genuine text content",
                "valid_json.json": b'{"key": "value"}',
                "invalid_json.json": b"This is not JSON content",
            }

            for filename, content in dangerous_files.items():
                file_path = Path(temp_dir) / filename
                file_path.write_bytes(content)

            # Use scanner with content validation enabled
            validator = SecurityValidator(validate_paths=True, validate_content=True)
            scanner = FileScanner(validator)

            source_path = Path(temp_dir)
            files, stats = scanner.get_files_to_archive(source_path)

            # Should only include legitimate files: valid_text.txt and valid_json.json
            self.assertEqual(len(files), 2)
            self.assertEqual(stats.skipped_files, 3)  # 3 files should be skipped

            # Verify the correct files were included
            included_files = [file[1] for file in files]  # Get archive names
            self.assertIn("valid_text.txt", included_files)
            self.assertIn("valid_json.json", included_files)
            self.assertNotIn("disguised_exe.txt", included_files)
            self.assertNotIn("disguised_zip.md", included_files)
            self.assertNotIn("invalid_json.json", included_files)

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_content_validation_can_be_disabled(self):
        """Test that content validation can be disabled for compatibility."""
        # Create a temporary directory for this test
        temp_dir = tempfile.mkdtemp()

        try:
            # Create a file with dangerous content
            dangerous_file = Path(temp_dir) / "disguised.txt"
            dangerous_file.write_bytes(b"MZ\x90\x00Executable content")

            # Scanner with content validation disabled
            validator = SecurityValidator(validate_paths=True, validate_content=False)
            scanner = FileScanner(validator)

            source_path = Path(temp_dir)
            files, stats = scanner.get_files_to_archive(source_path)

            # Should include the file when content validation is disabled
            self.assertEqual(len(files), 1)
            self.assertEqual(stats.skipped_files, 0)

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


class TestArchiveCreators(unittest.TestCase):
    """Test archive creator components."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Create test files
        test_files = ["test1.md", "test2.txt"]
        for fname in test_files:
            with open(Path(self.temp_dir) / fname, "w") as f:
                f.write(f"Content of {fname}")

        # Prepare files list for archiving
        self.files = [(Path(self.temp_dir) / fname, fname) for fname in test_files]
        self.source_path = Path(self.temp_dir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_zip_archive_creator(self):
        """Test ZIP archive creation."""
        creator = ZipArchiveCreator(compression_level=6)
        archive_path = creator.create_archive(
            self.files, str(Path(self.temp_dir).parent / "test.zip"), self.source_path
        )

        self.assertTrue(os.path.exists(archive_path))
        self.assertTrue(archive_path.endswith(".zip"))

    def test_archive_creator_factory(self):
        """Test archive creator factory."""
        formats = ArchiveCreatorFactory.get_supported_formats()
        self.assertIn("zip", formats)

        # Test factory creation
        zip_creator = ArchiveCreatorFactory.create_archive_creator("zip", 6)
        self.assertIsInstance(zip_creator, ZipArchiveCreator)


class TestArchiveManager(unittest.TestCase):
    """Test the archive manager."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Create realistic test structure
        test_files = {
            "post1.md": "# Post 1\n\nContent of post 1",
            "post2.md": "# Post 2\n\nContent of post 2",
            "subdir/post3.txt": "Text content",
            "README.md": "# README\n\nProject readme",
        }

        for file_path, content in test_files.items():
            full_path = Path(self.temp_dir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_modular_manager_zip_creation(self):
        """Test modular manager creates ZIP archives correctly."""
        manager = ArchiveManager(compression_format="zip", validate_paths=True)

        archive_path = manager.create_archive(
            source_directory=self.temp_dir, include_metadata=True
        )

        self.assertTrue(os.path.exists(archive_path))
        self.assertTrue(archive_path.endswith(".zip"))

        # Test archive info
        info = manager.get_archive_info(archive_path)
        self.assertEqual(info["format"], "zip")
        self.assertEqual(info["file_count"], 5)  # 4 content files + 1 metadata file
        self.assertTrue(info["valid"])

        # Clean up
        os.remove(archive_path)

    def test_modular_manager_with_progress(self):
        """Test modular manager with progress reporting."""
        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        manager = ArchiveManager(compression_format="zip")
        archive_path = manager.create_archive(
            source_directory=self.temp_dir, progress_callback=progress_callback
        )

        # Should have received progress updates
        self.assertGreater(len(progress_calls), 0)
        final_call = progress_calls[-1]
        self.assertEqual(final_call[0], final_call[1])  # Final: current == total

        # Clean up
        os.remove(archive_path)

    def test_modular_manager_error_handling(self):
        """Test modular manager handles errors gracefully."""
        manager = ArchiveManager()

        # Test with nonexistent directory
        with self.assertRaises(FileNotFoundError):
            manager.create_archive("/nonexistent/directory")


class TestArchiveIntegration(unittest.TestCase):
    """Test integration between all modular components."""

    def test_end_to_end_archive_workflow(self):
        """Test complete end-to-end workflow with modular components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test data
            test_files = {
                "document.md": "# Document\n\nContent here",
                "data.json": '{"key": "value"}',
                "notes.txt": "Some notes",
                "subdir/nested.md": "# Nested\n\nNested content",
            }

            for file_path, content in test_files.items():
                full_path = Path(temp_dir) / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)

            # Test full workflow
            manager = ArchiveManager(
                compression_format="zip", compression_level=6, validate_paths=True
            )

            archive_path = manager.create_archive(
                source_directory=temp_dir, include_metadata=True
            )

            # Verify archive
            self.assertTrue(manager.verify_archive_integrity(archive_path))

            # Get detailed info
            info = manager.get_archive_info(archive_path)
            self.assertEqual(info["file_count"], 5)  # 4 content files + 1 metadata file
            self.assertTrue(info["valid"])

            # Clean up
            os.remove(archive_path)


if __name__ == "__main__":
    unittest.main()
