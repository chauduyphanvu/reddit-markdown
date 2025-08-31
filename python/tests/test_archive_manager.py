"""
Archive manager tests focusing on behavior and functionality.
"""

import unittest
import tempfile
import os
import json
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

try:
    import zstandard as zstd

    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

from io_ops.archive_manager import ArchiveManager, create_archive_with_progress


class TestArchiveManagerBehavior(unittest.TestCase):
    """Test archive manager core functionality."""

    def setUp(self):
        """Create temporary directory structure for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = {}

        # Create test files with various content
        test_content = {
            "post1.md": "# Test Post 1\n\nThis is test content for post 1.",
            "post2.md": "# Test Post 2\n\nThis is test content for post 2 with more text.",
            "subdir/post3.md": "# Nested Post\n\nThis post is in a subdirectory.",
            "large_post.md": "Large content\n" * 1000,  # Larger file for testing
        }

        for file_path, content in test_content.items():
            full_path = Path(self.temp_dir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.test_files[file_path] = full_path

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_archive_manager_initialization_auto(self):
        """ArchiveManager should initialize with optimal compression format."""
        manager = ArchiveManager("auto")

        if ZSTD_AVAILABLE:
            self.assertEqual(manager.compression_format, "zstd")
        else:
            self.assertEqual(manager.compression_format, "zip")

    def test_archive_manager_initialization_specific_format(self):
        """ArchiveManager should initialize with specified format."""
        # Test ZIP format
        manager = ArchiveManager("zip")
        self.assertEqual(manager.compression_format, "zip")
        self.assertEqual(manager.compression_level, 6)  # Default ZIP level

        # Test custom compression level
        manager = ArchiveManager("zip", compression_level=9)
        self.assertEqual(manager.compression_level, 9)

    def test_archive_manager_invalid_format(self):
        """ArchiveManager should reject invalid compression formats."""
        with self.assertRaises(ValueError):
            ArchiveManager("invalid_format")

    def test_create_zip_archive_basic(self):
        """Should create valid ZIP archive with correct content."""
        manager = ArchiveManager("zip")
        archive_path = manager.create_archive(
            source_directory=self.temp_dir, include_metadata=False
        )

        # Verify archive was created
        self.assertTrue(os.path.exists(archive_path))
        self.assertTrue(archive_path.endswith(".zip"))

        # Verify archive contents
        with zipfile.ZipFile(archive_path, "r") as zipf:
            archive_files = zipf.namelist()
            self.assertIn("post1.md", archive_files)
            self.assertIn("post2.md", archive_files)
            self.assertIn("subdir/post3.md", archive_files)

            # Test content extraction
            with zipf.open("post1.md") as f:
                content = f.read().decode("utf-8")
                self.assertIn("Test Post 1", content)

    def test_create_archive_with_metadata(self):
        """Should include metadata file when requested."""
        manager = ArchiveManager("zip")
        archive_path = manager.create_archive(
            source_directory=self.temp_dir, include_metadata=True
        )

        with zipfile.ZipFile(archive_path, "r") as zipf:
            archive_files = zipf.namelist()
            self.assertIn("archive_metadata.json", archive_files)

            # Verify metadata content
            with zipf.open("archive_metadata.json") as f:
                metadata = json.loads(f.read().decode("utf-8"))
                self.assertIn("created_at", metadata)
                self.assertIn("total_files", metadata)
                self.assertIn("compression_format", metadata)
                self.assertEqual(metadata["compression_format"], "zip")

    def test_create_archive_custom_path(self):
        """Should create archive at specified custom path."""
        manager = ArchiveManager("zip")
        custom_path = os.path.join(self.temp_dir, "custom_archive.zip")

        archive_path = manager.create_archive(
            source_directory=self.temp_dir,
            archive_path=custom_path,
            include_metadata=False,
        )

        self.assertEqual(archive_path, custom_path)
        self.assertTrue(os.path.exists(custom_path))

    def test_create_archive_progress_callback(self):
        """Should call progress callback during archive creation."""
        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        manager = ArchiveManager("zip")
        manager.create_archive(
            source_directory=self.temp_dir,
            progress_callback=progress_callback,
            include_metadata=False,
        )

        # Should have received progress updates
        self.assertTrue(len(progress_calls) > 0)

        # Final call should be for all files
        final_current, final_total = progress_calls[-1]
        self.assertEqual(final_current, final_total)
        self.assertEqual(final_total, 4)  # We have 4 test files

    def test_create_archive_empty_directory(self):
        """Should handle empty directory gracefully."""
        empty_dir = tempfile.mkdtemp()
        try:
            manager = ArchiveManager("zip")
            archive_path = manager.create_archive(
                source_directory=empty_dir, include_metadata=False
            )

            # Should return empty string for empty directory
            self.assertEqual(archive_path, "")

        finally:
            os.rmdir(empty_dir)

    def test_create_archive_nonexistent_directory(self):
        """Should raise FileNotFoundError for nonexistent directory."""
        manager = ArchiveManager("zip")

        with self.assertRaises(FileNotFoundError):
            manager.create_archive(
                source_directory="/nonexistent/directory", include_metadata=False
            )

    @unittest.skipIf(not ZSTD_AVAILABLE, "ZSTD not available")
    def test_create_zstd_archive(self):
        """Should create ZSTD archive when available."""
        manager = ArchiveManager("zstd")
        archive_path = manager.create_archive(
            source_directory=self.temp_dir, include_metadata=False
        )

        # Verify archive was created with correct extension
        self.assertTrue(os.path.exists(archive_path))
        self.assertTrue(archive_path.endswith(".zst"))

        # Verify we can decompress and extract tar content
        with open(archive_path, "rb") as f:
            compressed_data = f.read()
            dctx = zstd.ZstdDecompressor()
            decompressed_data = dctx.decompress(compressed_data)

            # Should contain tar data
            self.assertGreater(len(decompressed_data), 0)

            # Should be able to read as tar
            import tarfile
            import io

            tar_buffer = io.BytesIO(decompressed_data)

            with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
                files = tar.getnames()
                self.assertIn("post1.md", files)
                self.assertIn("post2.md", files)

    def test_archive_integrity_verification(self):
        """Should verify archive integrity after creation."""
        manager = ArchiveManager("zip")
        archive_path = manager.create_archive(
            source_directory=self.temp_dir, include_metadata=False
        )

        # Archive should pass integrity check
        self.assertTrue(manager._verify_archive_integrity(archive_path))

        # Corrupt the archive significantly and verify it fails
        with open(archive_path, "wb") as f:
            f.write(b"completely_invalid_zip_data" * 100)

        self.assertFalse(manager._verify_archive_integrity(archive_path))

    def test_get_optimal_compression_format(self):
        """Should return optimal compression format for system."""
        optimal = ArchiveManager.get_optimal_compression_format()

        if ZSTD_AVAILABLE:
            self.assertEqual(optimal, "zstd")
        else:
            self.assertEqual(optimal, "zip")

    def test_install_zstd_hint(self):
        """Should provide installation hint when ZSTD not available."""
        hint = ArchiveManager.install_zstd_hint()

        if ZSTD_AVAILABLE:
            self.assertEqual(hint, "")
        else:
            self.assertIn("pip install zstandard", hint)


class TestArchiveManagerIntegration(unittest.TestCase):
    """Integration tests for archive manager in realistic scenarios."""

    def setUp(self):
        """Create realistic test directory structure."""
        self.temp_dir = tempfile.mkdtemp()

        # Create realistic reddit post structure
        posts = [
            "r_python/python_post_abc123.md",
            "r_python/python_post_def456.md",
            "r_machinelearning/ml_post_ghi789.md",
            "r_programming/prog_post_jkl012.md",
            "2024_01/archived_post_mno345.md",
            "2024_01/another_post_pqr678.md",
        ]

        for post_path in posts:
            full_path = Path(self.temp_dir) / post_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            content = f"""# {post_path.replace('.md', '').replace('_', ' ').title()}

This is a realistic Reddit post content with:
- Multiple paragraphs
- **Bold text** and *italic text*
- [Links](https://example.com)
- Code blocks:

```python
def example_function():
    return "Hello, Reddit!"
```

## Comments Section

**Author1**: This is a great post!

**Author2**: I disagree, but here's my perspective...

And much more content to make this realistic.
"""
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

    def tearDown(self):
        """Clean up test files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_realistic_archive_creation_workflow(self):
        """Test complete archive creation workflow with realistic data."""
        # Test with progress callback
        progress_updates = []

        def track_progress(current, total):
            progress_updates.append((current, total))

        # Create archive
        archive_path = create_archive_with_progress(
            source_directory=self.temp_dir, compression_format="auto", archive_path=None
        )

        # Verify archive was created successfully
        self.assertTrue(os.path.exists(archive_path))
        self.assertGreater(os.path.getsize(archive_path), 0)

        # Verify archive contains expected files
        if archive_path.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zipf:
                files = zipf.namelist()
                self.assertIn("r_python/python_post_abc123.md", files)
                self.assertIn("r_machinelearning/ml_post_ghi789.md", files)
                self.assertIn("2024_01/archived_post_mno345.md", files)

                # Verify content quality
                with zipf.open("r_python/python_post_abc123.md") as f:
                    content = f.read().decode("utf-8")
                    self.assertIn("def example_function()", content)
                    self.assertIn("**Bold text**", content)

    def test_large_archive_performance(self):
        """Test archive creation with larger dataset."""
        # Create more files to test performance
        for i in range(50):
            content = f"# Post {i}\n\n" + ("Large content line\n" * 100)
            file_path = Path(self.temp_dir) / f"post_{i:03d}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        import time

        start_time = time.time()

        archive_path = create_archive_with_progress(
            source_directory=self.temp_dir,
            compression_format="zip",  # Use zip for consistency
        )

        elapsed = time.time() - start_time

        # Archive should be created reasonably quickly (< 10 seconds)
        self.assertLess(elapsed, 10.0)

        # Archive should exist and be reasonably sized
        self.assertTrue(os.path.exists(archive_path))
        archive_size = os.path.getsize(archive_path)
        self.assertGreater(archive_size, 1000)  # Should be at least 1KB

    def test_unicode_content_archiving(self):
        """Test archiving with unicode content."""
        # Create files with various unicode content
        unicode_files = {
            "japanese.md": "# 日本語のポスト\n\nこんにちは、世界！\n\n**太字**と*斜体*のテスト",
            "arabic.md": "# منشور بالعربية\n\nمرحبا بالعالم!\n\n**نص عريض** و*نص مائل*",
            "emoji.md": "# Emoji Post 🚀\n\nTesting emojis: 🎉 🌟 ⭐ 🔥 💯\n\n**Bold with emoji** 🎯",
        }

        for filename, content in unicode_files.items():
            file_path = Path(self.temp_dir) / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        archive_path = create_archive_with_progress(
            source_directory=self.temp_dir, compression_format="zip"
        )

        # Verify unicode content is preserved
        with zipfile.ZipFile(archive_path, "r") as zipf:
            with zipf.open("japanese.md") as f:
                content = f.read().decode("utf-8")
                self.assertIn("日本語", content)
                self.assertIn("こんにちは", content)

            with zipf.open("emoji.md") as f:
                content = f.read().decode("utf-8")
                self.assertIn("🚀", content)
                self.assertIn("🎉", content)


class TestArchiveManagerEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_archive_with_special_filenames(self):
        """Test archiving files with special characters in names."""
        special_files = {
            "file with spaces.md": "Content with spaces",
            "file-with-dashes.md": "Content with dashes",
            "file.with.dots.md": "Content with dots",
            "file_with_underscores.md": "Content with underscores",
        }

        for filename, content in special_files.items():
            file_path = Path(self.temp_dir) / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        manager = ArchiveManager("zip")
        archive_path = manager.create_archive(
            source_directory=self.temp_dir, include_metadata=False
        )

        with zipfile.ZipFile(archive_path, "r") as zipf:
            files = zipf.namelist()
            for expected_file in special_files.keys():
                self.assertIn(expected_file, files)

    def test_archive_with_empty_files(self):
        """Test archiving empty files."""
        # Create empty file
        empty_file = Path(self.temp_dir) / "empty.md"
        empty_file.touch()

        # Create normal file
        normal_file = Path(self.temp_dir) / "normal.md"
        with open(normal_file, "w") as f:
            f.write("Normal content")

        manager = ArchiveManager("zip")
        archive_path = manager.create_archive(
            source_directory=self.temp_dir, include_metadata=False
        )

        with zipfile.ZipFile(archive_path, "r") as zipf:
            files = zipf.namelist()
            self.assertIn("empty.md", files)
            self.assertIn("normal.md", files)

    @patch("io_ops.archive_manager.logger")
    def test_archive_with_file_read_error(self, mock_logger):
        """Test behavior when file cannot be read during archiving."""
        # Create a normal file
        normal_file = Path(self.temp_dir) / "normal.md"
        with open(normal_file, "w") as f:
            f.write("Normal content")

        manager = ArchiveManager("zip")

        # Mock file access error during archiving
        original_open = open

        def mock_open(file_path, *args, **kwargs):
            if "normal.md" in str(file_path) and "rb" in args:
                raise PermissionError("Access denied")
            return original_open(file_path, *args, **kwargs)

        with patch("builtins.open", mock_open):
            archive_path = manager.create_archive(
                source_directory=self.temp_dir, include_metadata=False
            )

        # Should still create archive and log warning
        self.assertTrue(os.path.exists(archive_path))
        mock_logger.warning.assert_called()

    def test_compression_level_bounds(self):
        """Test compression level boundary conditions."""
        # Test minimum compression level for ZIP
        manager = ArchiveManager("zip", compression_level=0)
        self.assertEqual(manager.compression_level, 0)

        # Test maximum compression level for ZIP
        manager = ArchiveManager("zip", compression_level=9)
        self.assertEqual(manager.compression_level, 9)

        # Test default compression level for ZIP
        manager_default = ArchiveManager("zip")
        self.assertEqual(manager_default.compression_level, 6)  # Default ZIP level

        # ZSTD tests only if available
        if ZSTD_AVAILABLE:
            manager = ArchiveManager("zstd", compression_level=1)
            self.assertEqual(manager.compression_level, 1)

            manager = ArchiveManager("zstd", compression_level=22)
            self.assertEqual(manager.compression_level, 22)

            # Test default compression level for ZSTD
            manager_default = ArchiveManager("zstd")
            self.assertEqual(manager_default.compression_level, 3)  # Default ZSTD level


if __name__ == "__main__":
    unittest.main()
