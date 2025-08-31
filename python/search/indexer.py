import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from colored_logger import get_colored_logger
from .search_database import SearchDatabase
from .metadata_extractor import MetadataExtractor

logger = get_colored_logger(__name__)


class ContentIndexer:
    """
    Content indexing engine that scans directories for Reddit markdown files
    and builds a searchable database index.

    Features:
    - Batch processing with progress tracking
    - Incremental indexing (only processes changed files)
    - Multi-threaded processing for performance
    - Automatic cleanup of deleted files
    """

    def __init__(
        self,
        database: SearchDatabase = None,
        extractor: MetadataExtractor = None,
        max_workers: int = 4,
    ):
        """
        Initialize the content indexer.

        Args:
            database: SearchDatabase instance. If None, creates default instance.
            extractor: MetadataExtractor instance. If None, creates default instance.
            max_workers: Maximum threads for parallel processing.
        """
        self.database = database or SearchDatabase()
        self.extractor = extractor or MetadataExtractor()
        self.max_workers = max_workers

        # Statistics tracking
        self.stats = {
            "files_processed": 0,
            "files_indexed": 0,
            "files_updated": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "start_time": 0,
            "end_time": 0,
        }

    def index_directory(
        self,
        directory: str,
        recursive: bool = True,
        file_extensions: List[str] = None,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """
        Index all Reddit markdown files in a directory.

        Args:
            directory: Path to directory to index
            recursive: If True, search subdirectories recursively
            file_extensions: List of extensions to process (default: ['.md', '.html'])
            force_reindex: If True, reindex all files regardless of modification time

        Returns:
            Dictionary containing indexing statistics
        """
        if not os.path.exists(directory):
            logger.error("Directory does not exist: %s", directory)
            return self.stats

        if file_extensions is None:
            file_extensions = [".md", ".html"]

        logger.info("Starting indexing of directory: %s", directory)

        # Reset stats for this indexing run
        self.stats = {
            "files_processed": 0,
            "files_indexed": 0,
            "files_updated": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "start_time": time.time(),
            "end_time": 0,
        }

        # Find all potential files
        files_to_process = self._find_files(directory, file_extensions, recursive)
        logger.info("Found %d files to examine", len(files_to_process))

        if not files_to_process:
            logger.info("No files found to index")
            return self._finalize_stats()

        # Filter files that need processing
        if not force_reindex:
            files_to_process = self._filter_changed_files(files_to_process)
            logger.info("Need to process %d changed/new files", len(files_to_process))

        # Process files in batches
        self._process_files_batch(files_to_process, force_reindex)

        # Cleanup deleted files
        self._cleanup_deleted_files(directory)

        return self._finalize_stats()

    def index_file(self, file_path: str, force_reindex: bool = False) -> bool:
        """
        Index a single file.

        Args:
            file_path: Path to file to index
            force_reindex: If True, reindex even if file hasn't changed

        Returns:
            True if file was successfully indexed, False otherwise
        """
        try:
            # Check if file needs processing
            if not force_reindex and not self._needs_processing(file_path):
                logger.debug("File %s is up to date, skipping", file_path)
                self.stats["files_skipped"] += 1
                return True

            # Check if this is a Reddit markdown file
            try:
                if not self.extractor.is_reddit_markdown_file(file_path):
                    logger.debug(
                        "File %s is not a Reddit markdown file, skipping", file_path
                    )
                    self.stats["files_skipped"] += 1
                    return True
            except UnicodeDecodeError as e:
                # Corrupted or binary file
                logger.warning(
                    "File %s appears to be corrupted or binary: %s", file_path, e
                )
                self.stats["files_failed"] += 1
                return False

            # Extract metadata
            metadata = self.extractor.extract_from_file(file_path)
            if not metadata:
                logger.warning("Could not extract metadata from %s", file_path)
                self.stats["files_failed"] += 1
                return False

            # Check if this is an update or new file
            existing_post = self.database.get_post_by_file_path(file_path)
            is_update = existing_post is not None

            # Add to database
            post_id = self.database.add_post(metadata)

            if is_update:
                self.stats["files_updated"] += 1
                logger.debug("Updated post %s in index", metadata["post_id"])
            else:
                self.stats["files_indexed"] += 1
                logger.debug("Added post %s to index", metadata["post_id"])

            self.stats["files_processed"] += 1
            return True

        except Exception as e:
            logger.error("Failed to index file %s: %s", file_path, e)
            self.stats["files_failed"] += 1
            return False

    def reindex_all(self, directory: str) -> Dict[str, Any]:
        """
        Force reindex all files in directory (ignores modification times).

        Args:
            directory: Path to directory to reindex

        Returns:
            Dictionary containing indexing statistics
        """
        logger.info("Starting full reindex of directory: %s", directory)
        return self.index_directory(directory, force_reindex=True)

    def get_indexing_progress(self) -> Dict[str, Any]:
        """Get current indexing statistics."""
        current_stats = self.stats.copy()
        if self.stats["start_time"] > 0 and self.stats["end_time"] == 0:
            current_stats["elapsed_time"] = time.time() - self.stats["start_time"]
        elif self.stats["end_time"] > 0:
            current_stats["elapsed_time"] = (
                self.stats["end_time"] - self.stats["start_time"]
            )
        else:
            current_stats["elapsed_time"] = 0

        return current_stats

    def _find_files(
        self, directory: str, extensions: List[str], recursive: bool
    ) -> List[str]:
        """Find all files with specified extensions in directory."""
        files = []
        directory_path = Path(directory)

        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"

        for ext in extensions:
            for file_path in directory_path.glob(f"{pattern}{ext}"):
                if file_path.is_file():
                    files.append(str(file_path))

        return sorted(files)  # Sort for consistent processing order

    def _filter_changed_files(self, file_paths: List[str]) -> List[str]:
        """Filter list to only include files that need processing."""
        filtered_files = []

        for file_path in file_paths:
            if self._needs_processing(file_path):
                filtered_files.append(file_path)
            else:
                self.stats["files_skipped"] += 1

        return filtered_files

    def _needs_processing(self, file_path: str) -> bool:
        """Check if file needs to be processed (new or modified)."""
        try:
            # Get file modification time
            file_stat = os.stat(file_path)
            file_mtime = file_stat.st_mtime

            # Check if file is in database
            existing_post = self.database.get_post_by_file_path(file_path)
            if not existing_post:
                return True  # New file

            # Check if file was modified since last indexing
            db_mtime = existing_post.get("file_modified_time", 0)
            return file_mtime > db_mtime

        except Exception as e:
            logger.debug("Error checking file %s: %s", file_path, e)
            return True  # Process if we can't determine

    def _process_files_batch(
        self, file_paths: List[str], force_reindex: bool = False
    ) -> None:
        """Process files in batches using thread pool."""
        if not file_paths:
            return

        if len(file_paths) == 1 or self.max_workers == 1:
            # Process single file or sequential processing
            for file_path in file_paths:
                self.index_file(file_path, force_reindex)
        else:
            # Multi-threaded processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(
                        self.index_file, file_path, force_reindex
                    ): file_path
                    for file_path in file_paths
                }

                # Process completed tasks
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        result = future.result()
                        if not result:
                            logger.warning("Failed to process file: %s", file_path)
                    except Exception as e:
                        logger.error("Exception processing file %s: %s", file_path, e)
                        self.stats["files_failed"] += 1

    def _cleanup_deleted_files(self, directory: str) -> None:
        """Remove entries from database for files that no longer exist."""
        try:
            # Get all posts in database that should be in this directory
            posts = self.database.search_posts(limit=10000)  # Get all posts

            deleted_count = 0
            for post in posts:
                file_path = post.get("file_path", "")
                if not file_path:
                    continue

                # Check if this post's file is within the indexed directory
                if not file_path.startswith(directory):
                    continue

                # Check if file still exists
                if not os.path.exists(file_path):
                    if self.database.delete_post(file_path):
                        deleted_count += 1
                        logger.debug("Removed deleted file from index: %s", file_path)

            if deleted_count > 0:
                logger.info("Cleaned up %d deleted files from index", deleted_count)

        except Exception as e:
            logger.error("Error during cleanup of deleted files: %s", e)

    def _finalize_stats(self) -> Dict[str, Any]:
        """Finalize and return indexing statistics."""
        self.stats["end_time"] = time.time()
        self.stats["elapsed_time"] = self.stats["end_time"] - self.stats["start_time"]

        logger.info(
            "Indexing complete. Processed: %d, Indexed: %d, Updated: %d, Skipped: %d, Failed: %d",
            self.stats["files_processed"],
            self.stats["files_indexed"],
            self.stats["files_updated"],
            self.stats["files_skipped"],
            self.stats["files_failed"],
        )

        if self.stats["elapsed_time"] > 0:
            rate = self.stats["files_processed"] / self.stats["elapsed_time"]
            logger.info("Processing rate: %.1f files/second", rate)

        return self.stats.copy()
