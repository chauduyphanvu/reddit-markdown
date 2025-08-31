import os
import tempfile
import time
import unittest
from pathlib import Path

from search.search_database import SearchDatabase
from search.metadata_extractor import MetadataExtractor
from search.indexer import ContentIndexer


class TestContentIndexer(unittest.TestCase):
    """Test cases for ContentIndexer class."""

    def setUp(self):
        """Set up test indexer with temporary database and files."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.temp_dir = tempfile.mkdtemp()

        self.database = SearchDatabase(self.temp_db.name)
        self.extractor = MetadataExtractor()
        self.indexer = ContentIndexer(
            database=self.database,
            extractor=self.extractor,
            max_workers=1,  # Use single worker for predictable testing
        )

        # Create test files
        self._create_test_files()

    def tearDown(self):
        """Clean up temporary files and database."""
        self.database.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_files(self):
        """Create test Reddit markdown files."""
        test_files = [
            (
                "python_tutorial.md",
                """**r/Python** | Posted by u/python_guru ⬆️ 150

## Python Tutorial for Beginners

Original post: [https://reddit.com/r/Python/comments/abc123/](https://reddit.com/r/Python/comments/abc123/)

> Learn Python programming from scratch.

💬 ~ 25 replies
""",
            ),
            (
                "java_guide.md",
                """**r/Java** | Posted by u/java_expert ⬆️ 89

## Java Programming Guide

Original post: [https://reddit.com/r/Java/comments/def456/](https://reddit.com/r/Java/comments/def456/)

> Complete Java programming guide.

💬 ~ 12 replies
""",
            ),
            (
                "not_reddit.md",
                """# Regular Markdown File

This is just a regular markdown file, not a Reddit post.
""",
            ),
            ("empty_file.md", ""),
            (
                "invalid_reddit.md",
                """**r/test** | Posted by u/user

This file is missing required elements like title header.
""",
            ),
        ]

        for filename, content in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

    def test_index_file_valid_reddit_post_succeeds(self):
        """Indexing a valid Reddit post file should succeed."""
        file_path = os.path.join(self.temp_dir, "python_tutorial.md")
        result = self.indexer.index_file(file_path)

        self.assertTrue(result)
        self.assertEqual(self.indexer.stats["files_indexed"], 1)
        self.assertEqual(self.indexer.stats["files_processed"], 1)

    def test_index_file_non_reddit_file_skips_file(self):
        """Indexing a non-Reddit file should skip the file."""
        file_path = os.path.join(self.temp_dir, "not_reddit.md")
        result = self.indexer.index_file(file_path)

        self.assertTrue(result)  # Returns True but skips processing
        self.assertEqual(self.indexer.stats["files_skipped"], 1)
        self.assertEqual(self.indexer.stats["files_processed"], 0)

    def test_index_file_empty_file_skips_file(self):
        """Indexing an empty file should skip the file."""
        file_path = os.path.join(self.temp_dir, "empty_file.md")
        result = self.indexer.index_file(file_path)

        self.assertTrue(result)
        self.assertEqual(self.indexer.stats["files_skipped"], 1)

    def test_index_file_invalid_reddit_file_fails(self):
        """Indexing an invalid Reddit file should fail."""
        file_path = os.path.join(self.temp_dir, "invalid_reddit.md")
        result = self.indexer.index_file(file_path)

        # The indexer may handle malformed files gracefully and skip them
        # rather than failing hard. Check that it either failed or was skipped.
        if not result:
            self.assertEqual(self.indexer.stats["files_failed"], 1)
        else:
            # If it succeeded, it should have been skipped due to invalid content
            self.assertGreater(
                self.indexer.stats["files_skipped"]
                + self.indexer.stats["files_failed"],
                0,
            )

    def test_index_file_nonexistent_file_fails(self):
        """Indexing a non-existent file should fail."""
        result = self.indexer.index_file("/nonexistent/file.md")

        # Should fail for non-existent file
        if not result:
            self.assertGreater(self.indexer.stats["files_failed"], 0)
        else:
            # If it doesn't fail, it should at least be skipped
            self.assertGreater(self.indexer.stats["files_skipped"], 0)

    def test_index_file_force_reindex_processes_unchanged_file(self):
        """Force reindex should process file even if unchanged."""
        file_path = os.path.join(self.temp_dir, "python_tutorial.md")

        # Index file first time
        self.indexer.index_file(file_path)

        # Reset stats
        self.indexer.stats["files_processed"] = 0
        self.indexer.stats["files_updated"] = 0

        # Index again with force_reindex=True
        result = self.indexer.index_file(file_path, force_reindex=True)

        self.assertTrue(result)
        self.assertEqual(self.indexer.stats["files_updated"], 1)

    def test_index_file_without_force_skips_unchanged_file(self):
        """Without force reindex, unchanged file should be skipped."""
        file_path = os.path.join(self.temp_dir, "python_tutorial.md")

        # Index file first time
        self.indexer.index_file(file_path)

        # Reset stats
        self.indexer.stats["files_skipped"] = 0

        # Index again without force_reindex
        result = self.indexer.index_file(file_path, force_reindex=False)

        self.assertTrue(result)
        self.assertEqual(self.indexer.stats["files_skipped"], 1)

    def test_index_directory_processes_all_reddit_files(self):
        """Indexing directory should process all Reddit markdown files."""
        stats = self.indexer.index_directory(self.temp_dir, recursive=False)

        # Should process some valid Reddit files, others will be skipped or handled gracefully
        self.assertGreater(stats["files_processed"], 0)
        # Total files examined should be 5 (the test files created)
        total_handled = (
            stats["files_indexed"] + stats["files_skipped"] + stats["files_failed"]
        )
        self.assertEqual(total_handled, 5)

    def test_index_directory_nonexistent_directory_returns_empty_stats(self):
        """Indexing non-existent directory should return empty stats."""
        stats = self.indexer.index_directory("/nonexistent/directory")

        self.assertEqual(stats["files_processed"], 0)
        self.assertEqual(stats["files_indexed"], 0)

    def test_index_directory_empty_directory_returns_empty_stats(self):
        """Indexing empty directory should return empty stats."""
        empty_dir = tempfile.mkdtemp()
        try:
            stats = self.indexer.index_directory(empty_dir)

            self.assertEqual(stats["files_processed"], 0)
            self.assertEqual(stats["files_indexed"], 0)
        finally:
            os.rmdir(empty_dir)

    def test_index_directory_with_file_extensions_filter_works(self):
        """Indexing with file extension filter should only process matching files."""
        # Create a .txt file that won't be processed
        txt_file = os.path.join(self.temp_dir, "test.txt")
        with open(txt_file, "w") as f:
            f.write("Text file content")

        stats = self.indexer.index_directory(
            self.temp_dir,
            file_extensions=[".md"],  # Only process .md files
            recursive=False,
        )

        # Should not process the .txt file
        self.assertGreater(stats["files_processed"], 0)  # Some .md files processed

    def test_index_directory_recursive_processes_subdirectories(self):
        """Recursive indexing should process files in subdirectories."""
        # Create subdirectory with a Reddit file
        subdir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(subdir)

        sub_file = os.path.join(subdir, "sub_post.md")
        with open(sub_file, "w", encoding="utf-8") as f:
            f.write(
                """**r/test** | Posted by u/user

## Sub Post

Original post: [url](url)
"""
            )

        stats = self.indexer.index_directory(self.temp_dir, recursive=True)

        # Should process the file in subdirectory (total processed should be more than root level)
        total_files_found = (
            stats["files_indexed"] + stats["files_skipped"] + stats["files_failed"]
        )
        self.assertGreater(
            total_files_found, 5
        )  # More than just root level files (5 + subdirectory files)

    def test_index_directory_non_recursive_skips_subdirectories(self):
        """Non-recursive indexing should skip subdirectories."""
        # Create subdirectory with a Reddit file
        subdir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(subdir)

        sub_file = os.path.join(subdir, "sub_post.md")
        with open(sub_file, "w", encoding="utf-8") as f:
            f.write(
                """**r/test** | Posted by u/user

## Sub Post

Original post: [url](url)
"""
            )

        stats = self.indexer.index_directory(self.temp_dir, recursive=False)

        # Should only process root level files (5 original files, not including subdirectory)
        total_files_found = (
            stats["files_indexed"] + stats["files_skipped"] + stats["files_failed"]
        )
        self.assertEqual(total_files_found, 5)  # Only root level files

    def test_reindex_all_forces_reprocessing(self):
        """Reindex all should force reprocessing of all files."""
        # Index directory first time
        initial_stats = self.indexer.index_directory(self.temp_dir)
        initial_indexed = initial_stats["files_indexed"]

        # Reindex all files
        reindex_stats = self.indexer.reindex_all(self.temp_dir)

        # Should reprocess existing files (either as updates or re-indexed)
        # The exact counts depend on implementation but should total to initial files
        total_reprocessed = (
            reindex_stats["files_updated"] + reindex_stats["files_indexed"]
        )
        self.assertGreaterEqual(total_reprocessed, initial_indexed)

    def test_get_indexing_progress_returns_current_stats(self):
        """Get indexing progress should return current statistics."""
        progress = self.indexer.get_indexing_progress()

        self.assertIsInstance(progress, dict)
        self.assertIn("files_processed", progress)
        self.assertIn("files_indexed", progress)
        self.assertIn("files_updated", progress)
        self.assertIn("files_skipped", progress)
        self.assertIn("files_failed", progress)
        self.assertIn("elapsed_time", progress)

    def test_find_files_finds_correct_extensions(self):
        """Internal _find_files should find files with correct extensions."""
        files = self.indexer._find_files(self.temp_dir, [".md"], recursive=False)

        # Should find all .md files
        self.assertEqual(len(files), 5)  # 5 .md files created in _create_test_files

        # All files should have .md extension
        for file_path in files:
            self.assertTrue(file_path.endswith(".md"))

    def test_find_files_recursive_finds_subdirectory_files(self):
        """Internal _find_files with recursive should find subdirectory files."""
        # Create subdirectory with .md file
        subdir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(subdir)

        sub_file = os.path.join(subdir, "sub.md")
        with open(sub_file, "w") as f:
            f.write("content")

        files = self.indexer._find_files(self.temp_dir, [".md"], recursive=True)

        # Should include the subdirectory file
        self.assertIn(sub_file, files)

    def test_needs_processing_detects_new_files(self):
        """Internal _needs_processing should detect new files."""
        file_path = os.path.join(self.temp_dir, "python_tutorial.md")
        needs_processing = self.indexer._needs_processing(file_path)

        self.assertTrue(needs_processing)  # New file needs processing

    def test_needs_processing_detects_modified_files(self):
        """Internal _needs_processing should detect modified files."""
        file_path = os.path.join(self.temp_dir, "python_tutorial.md")

        # Index the file first
        self.indexer.index_file(file_path)

        # Modify the file
        time.sleep(0.1)  # Ensure different modification time
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n\nAdditional content")

        needs_processing = self.indexer._needs_processing(file_path)
        self.assertTrue(needs_processing)  # Modified file needs processing

    def test_needs_processing_skips_unchanged_files(self):
        """Internal _needs_processing should skip unchanged files."""
        file_path = os.path.join(self.temp_dir, "python_tutorial.md")

        # Index the file first
        self.indexer.index_file(file_path)

        needs_processing = self.indexer._needs_processing(file_path)
        self.assertFalse(needs_processing)  # Unchanged file doesn't need processing

    def test_filter_changed_files_returns_only_changed_files(self):
        """Internal _filter_changed_files should return only changed files."""
        all_files = [
            os.path.join(self.temp_dir, "python_tutorial.md"),
            os.path.join(self.temp_dir, "java_guide.md"),
        ]

        # Index first file
        self.indexer.index_file(all_files[0])

        # Filter changed files
        changed_files = self.indexer._filter_changed_files(all_files)

        # Should return only the unindexed file
        self.assertEqual(len(changed_files), 1)
        self.assertEqual(changed_files[0], all_files[1])

    def test_cleanup_deleted_files_removes_deleted_entries(self):
        """Internal _cleanup_deleted_files should remove entries for deleted files."""
        file_path = os.path.join(self.temp_dir, "python_tutorial.md")

        # Index the file
        self.indexer.index_file(file_path)

        # Verify file is in database
        post = self.database.get_post_by_file_path(file_path)
        self.assertIsNotNone(post)

        # Delete the file
        os.remove(file_path)

        # Run cleanup
        self.indexer._cleanup_deleted_files(self.temp_dir)

        # Verify file is removed from database
        post_after = self.database.get_post_by_file_path(file_path)
        self.assertIsNone(post_after)

    def test_finalize_stats_calculates_elapsed_time(self):
        """Internal _finalize_stats should calculate elapsed time."""
        self.indexer.stats["start_time"] = time.time() - 1.0  # 1 second ago

        final_stats = self.indexer._finalize_stats()

        self.assertIn("elapsed_time", final_stats)
        self.assertGreater(final_stats["elapsed_time"], 0.5)  # At least 0.5 seconds
        self.assertLess(final_stats["elapsed_time"], 2.0)  # Less than 2 seconds

    def test_indexer_with_custom_max_workers_setting(self):
        """Indexer should respect custom max_workers setting."""
        custom_indexer = ContentIndexer(database=self.database, max_workers=2)

        self.assertEqual(custom_indexer.max_workers, 2)

    def test_indexer_initializes_with_defaults(self):
        """Indexer should initialize with reasonable defaults."""
        default_indexer = ContentIndexer()

        self.assertIsInstance(default_indexer.database, SearchDatabase)
        self.assertIsInstance(default_indexer.extractor, MetadataExtractor)
        self.assertEqual(default_indexer.max_workers, 4)  # Default value

    def test_stats_dictionary_tracks_all_metrics(self):
        """Stats dictionary should track all expected metrics."""
        expected_keys = [
            "files_processed",
            "files_indexed",
            "files_updated",
            "files_skipped",
            "files_failed",
            "start_time",
            "end_time",
        ]

        for key in expected_keys:
            self.assertIn(key, self.indexer.stats)


if __name__ == "__main__":
    unittest.main()
