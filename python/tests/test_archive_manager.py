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
