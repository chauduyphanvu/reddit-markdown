import os
import time
import threading
import gc
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import psutil
import queue

from colored_logger import get_colored_logger
from .optimized_search_database import OptimizedSearchDatabase, InputValidator
from .metadata_extractor import MetadataExtractor

logger = get_colored_logger(__name__)


@dataclass
class IndexingTask:
    """Represents a single file indexing task."""

    file_path: str
    priority: int = 0  # Higher values = higher priority
    estimated_size: int = 0  # File size in bytes


class ResourceMonitor:
    """Monitor system resources during indexing."""

    def __init__(self, max_memory_percent: float = 80.0):
        self.max_memory_percent = max_memory_percent
        self.start_memory = psutil.virtual_memory().percent
        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.Lock()

    def start_monitoring(self):
        """Start resource monitoring in background thread."""
        with self._lock:
            if not self._monitoring:
                self._monitoring = True
                self._monitor_thread = threading.Thread(target=self._monitor_loop)
                self._monitor_thread.daemon = True
                self._monitor_thread.start()
                logger.debug("Resource monitoring started")

    def stop_monitoring(self):
        """Stop resource monitoring."""
        with self._lock:
            self._monitoring = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=5)
                self._monitor_thread = None
                logger.debug("Resource monitoring stopped")

    def should_throttle(self) -> bool:
        """Check if processing should be throttled due to resource constraints."""
        memory = psutil.virtual_memory()
        return memory.percent > self.max_memory_percent

    def get_resource_stats(self) -> Dict[str, Any]:
        """Get current resource statistics."""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        return {
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "cpu_percent": cpu,
            "memory_increase": memory.percent - self.start_memory,
        }

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._monitoring:
            if self.should_throttle():
                logger.warning(
                    "High memory usage detected (%.1f%%), consider throttling",
                    psutil.virtual_memory().percent,
                )
                # Trigger garbage collection
                gc.collect()
            time.sleep(10)  # Check every 10 seconds


class BatchProcessor:
    """Processes indexing tasks in optimized batches."""

    def __init__(
        self,
        database: OptimizedSearchDatabase,
        extractor: MetadataExtractor,
        batch_size: int = 100,
    ):
        self.database = database
        self.extractor = extractor
        self.batch_size = batch_size
        self.validator = InputValidator()

    def process_batch(self, tasks: List[IndexingTask]) -> Dict[str, int]:
        """Process a batch of indexing tasks efficiently."""
        stats = {"processed": 0, "indexed": 0, "updated": 0, "skipped": 0, "failed": 0}

        batch_start = time.time()

        try:
            # Sort by priority and size (process smaller files first for better progress feedback)
            tasks.sort(key=lambda t: (-t.priority, t.estimated_size))

            with self.database.transaction() as conn:
                for task in tasks:
                    try:
                        result = self._process_single_task(task)
                        stats[result] += 1
                        stats["processed"] += 1

                        # Periodic commit for long batches
                        if stats["processed"] % 50 == 0:
                            conn.commit()
                            conn.execute("BEGIN IMMEDIATE")

                    except Exception as e:
                        logger.error("Failed to process task %s: %s", task.file_path, e)
                        stats["failed"] += 1
                        stats["processed"] += 1

        except Exception as e:
            logger.error("Batch processing failed: %s", e)
            # Individual task errors are already counted

        batch_time = time.time() - batch_start
        logger.debug(
            "Processed batch of %d tasks in %.2f seconds", len(tasks), batch_time
        )

        return stats

    def _process_single_task(self, task: IndexingTask) -> str:
        """Process a single indexing task. Returns status: indexed, updated, skipped, failed."""
        file_path = task.file_path

        try:
            # Validate file path
            validated_path = self.validator.validate_file_path(file_path)

            # Check if this is a Reddit markdown file
            if not self.extractor.is_reddit_markdown_file(validated_path):
                logger.debug(
                    "File %s is not a Reddit markdown file, skipping", file_path
                )
                return "skipped"

            # Extract metadata
            metadata = self.extractor.extract_from_file(validated_path)
            if not metadata:
                logger.warning("Could not extract metadata from %s", file_path)
                return "failed"

            # Check if this is an update or new file
            existing_post = self.database.get_post_by_file_path(validated_path)
            is_update = existing_post is not None

            # Add to database
            post_id = self.database.add_post(metadata)

            if is_update:
                logger.debug("Updated post %s in index", metadata["post_id"])
                return "updated"
            else:
                logger.debug("Added post %s to index", metadata["post_id"])
                return "indexed"

        except UnicodeDecodeError as e:
            logger.warning(
                "File %s appears to be corrupted or binary: %s", file_path, e
            )
            return "failed"
        except Exception as e:
            logger.error("Failed to process file %s: %s", file_path, e)
            return "failed"


class OptimizedContentIndexer:
    """
    High-performance content indexing engine with advanced optimizations.

    Enhancements:
    - Adaptive thread pool sizing based on system resources
    - Memory-conscious batch processing
    - Priority-based task scheduling
    - Resource monitoring and throttling
    - Intelligent file change detection
    - Progress reporting with ETA calculations
    - Graceful error recovery and resumption
    """

    def __init__(
        self,
        database: OptimizedSearchDatabase = None,
        extractor: MetadataExtractor = None,
        max_workers: int = None,
        batch_size: int = 100,
        max_memory_percent: float = 80.0,
    ):
        """
        Initialize the optimized content indexer.

        Args:
            database: OptimizedSearchDatabase instance. If None, creates default instance.
            extractor: MetadataExtractor instance. If None, creates default instance.
            max_workers: Maximum threads for parallel processing. If None, auto-detects.
            batch_size: Number of files to process per batch.
            max_memory_percent: Maximum memory usage before throttling (percentage).
        """
        self.database = database or OptimizedSearchDatabase()
        self.extractor = extractor or MetadataExtractor()
        self.batch_size = batch_size

        # Auto-detect optimal worker count
        if max_workers is None:
            cpu_count = os.cpu_count() or 4
            # Use CPU count but cap at 8 for I/O bound tasks
            self.max_workers = min(cpu_count, 8)
        else:
            self.max_workers = max_workers

        # Initialize components
        self.validator = InputValidator()
        self.resource_monitor = ResourceMonitor(max_memory_percent)
        self.batch_processor = BatchProcessor(self.database, self.extractor, batch_size)

        # Statistics tracking with thread safety
        self._stats_lock = threading.Lock()
        self.reset_stats()

        # Progress tracking
        self._progress_callbacks = []

    def reset_stats(self):
        """Reset indexing statistics."""
        with self._stats_lock:
            self.stats = {
                "files_processed": 0,
                "files_indexed": 0,
                "files_updated": 0,
                "files_skipped": 0,
                "files_failed": 0,
                "start_time": 0,
                "end_time": 0,
                "total_files": 0,
                "batches_completed": 0,
                "bytes_processed": 0,
            }

    def add_progress_callback(self, callback):
        """Add a progress callback function."""
        self._progress_callbacks.append(callback)

    def index_directory_optimized(
        self,
        directory: str,
        recursive: bool = True,
        file_extensions: List[str] = None,
        force_reindex: bool = False,
        priority_patterns: List[Tuple[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Optimized directory indexing with resource management and prioritization.

        Args:
            directory: Path to directory to index
            recursive: If True, search subdirectories recursively
            file_extensions: List of extensions to process (default: ['.md', '.html'])
            force_reindex: If True, reindex all files regardless of modification time
            priority_patterns: List of (pattern, priority) tuples for file prioritization

        Returns:
            Dictionary containing indexing statistics
        """
        if not os.path.exists(directory):
            logger.error("Directory does not exist: %s", directory)
            return self.stats

        if file_extensions is None:
            file_extensions = [".md", ".html"]

        logger.info("Starting optimized indexing of directory: %s", directory)

        # Reset and start tracking
        self.reset_stats()
        self.stats["start_time"] = time.time()
        self.resource_monitor.start_monitoring()

        try:
            # Find and prioritize files
            tasks = self._create_indexing_tasks(
                directory, file_extensions, recursive, force_reindex, priority_patterns
            )

            if not tasks:
                logger.info("No files found to index")
                return self._finalize_stats()

            self.stats["total_files"] = len(tasks)
            logger.info("Found %d files to process", len(tasks))

            # Process in optimized batches
            self._process_tasks_optimized(tasks)

            # Cleanup deleted files
            self._cleanup_deleted_files_optimized(directory)

        finally:
            self.resource_monitor.stop_monitoring()

        return self._finalize_stats()

    def _create_indexing_tasks(
        self,
        directory: str,
        file_extensions: List[str],
        recursive: bool,
        force_reindex: bool,
        priority_patterns: List[Tuple[str, int]] = None,
    ) -> List[IndexingTask]:
        """Create prioritized indexing tasks."""
        tasks = []

        # Find all potential files
        files = self._find_files_optimized(directory, file_extensions, recursive)

        # Filter files that need processing
        if not force_reindex:
            files = self._filter_changed_files_optimized(files)
            logger.info("Need to process %d changed/new files", len(files))

        # Create tasks with priorities and size estimates
        for file_path in files:
            try:
                file_stat = os.stat(file_path)
                file_size = file_stat.st_size

                # Calculate priority
                priority = self._calculate_file_priority(file_path, priority_patterns)

                task = IndexingTask(
                    file_path=file_path, priority=priority, estimated_size=file_size
                )
                tasks.append(task)

            except OSError as e:
                logger.warning("Cannot access file %s: %s", file_path, e)
                continue

        return tasks

    def _calculate_file_priority(
        self, file_path: str, priority_patterns: List[Tuple[str, int]] = None
    ) -> int:
        """Calculate priority for a file based on patterns."""
        priority = 0

        if priority_patterns:
            for pattern, pattern_priority in priority_patterns:
                if pattern in file_path:
                    priority += pattern_priority

        # Boost priority for smaller files (faster processing)
        try:
            file_size = os.path.getsize(file_path)
            if file_size < 10000:  # < 10KB
                priority += 10
            elif file_size < 100000:  # < 100KB
                priority += 5
        except OSError:
            pass

        return priority

    def _find_files_optimized(
        self, directory: str, extensions: List[str], recursive: bool
    ) -> List[str]:
        """Optimized file discovery with progress reporting."""
        files = []
        directory_path = Path(directory)

        logger.info("Discovering files...")

        try:
            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"

            # Use generator for memory efficiency
            for ext in extensions:
                for file_path in directory_path.glob(f"{pattern}{ext}"):
                    if file_path.is_file():
                        files.append(str(file_path.resolve()))

                        # Progress feedback for large directories
                        if len(files) % 1000 == 0:
                            logger.debug("Discovered %d files so far...", len(files))

        except Exception as e:
            logger.error("Error discovering files in %s: %s", directory, e)

        logger.info("Discovered %d files with extensions %s", len(files), extensions)
        return sorted(files)  # Sort for consistent processing order

    def _filter_changed_files_optimized(self, file_paths: List[str]) -> List[str]:
        """Optimized filtering of changed files using batch database queries."""
        if not file_paths:
            return []

        logger.debug("Filtering changed files...")
        changed_files = []

        # Process in batches to avoid large queries
        batch_size = 1000
        for i in range(0, len(file_paths), batch_size):
            batch_paths = file_paths[i : i + batch_size]

            try:
                with self.database._pool.get_connection() as conn:
                    # Get modification times for all files in batch
                    placeholders = ",".join(["?" for _ in batch_paths])
                    cursor = conn.execute(
                        f"""
                        SELECT file_path, file_modified_time 
                        FROM posts 
                        WHERE file_path IN ({placeholders})
                    """,
                        batch_paths,
                    )

                    # Create lookup dict
                    db_mtimes = {row[0]: row[1] for row in cursor.fetchall()}

                # Check each file in batch
                for file_path in batch_paths:
                    if self._needs_processing_optimized(file_path, db_mtimes):
                        changed_files.append(file_path)

            except Exception as e:
                logger.error("Error filtering batch: %s", e)
                # Fallback: include all files in this batch
                changed_files.extend(batch_paths)

        logger.debug("Found %d files that need processing", len(changed_files))
        return changed_files

    def _needs_processing_optimized(
        self, file_path: str, db_mtimes: Dict[str, float]
    ) -> bool:
        """Optimized check if file needs processing."""
        try:
            # Get file modification time
            file_stat = os.stat(file_path)
            file_mtime = file_stat.st_mtime

            # Check against database
            db_mtime = db_mtimes.get(file_path, 0)
            return file_mtime > db_mtime

        except OSError:
            # If we can't stat the file, try processing it
            return True

    def _process_tasks_optimized(self, tasks: List[IndexingTask]):
        """Process tasks with adaptive resource management."""
        if not tasks:
            return

        # Determine optimal processing strategy
        if len(tasks) <= self.batch_size or self.max_workers == 1:
            # Process in single thread for small workloads
            self._process_tasks_sequential(tasks)
        else:
            # Use parallel processing for larger workloads
            self._process_tasks_parallel(tasks)

    def _process_tasks_sequential(self, tasks: List[IndexingTask]):
        """Process tasks sequentially with memory management."""
        logger.info("Processing %d tasks sequentially", len(tasks))

        batch_stats = self.batch_processor.process_batch(tasks)
        self._merge_stats(batch_stats)

        # Report progress
        self._report_progress()

    def _process_tasks_parallel(self, tasks: List[IndexingTask]):
        """Process tasks in parallel with adaptive resource management."""
        logger.info("Processing %d tasks with %d workers", len(tasks), self.max_workers)

        # Create batches
        batches = [
            tasks[i : i + self.batch_size]
            for i in range(0, len(tasks), self.batch_size)
        ]

        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batch processing tasks
            future_to_batch = {
                executor.submit(self.batch_processor.process_batch, batch): i
                for i, batch in enumerate(batches)
            }

            # Process completed batches
            for future in as_completed(future_to_batch):
                batch_index = future_to_batch[future]

                try:
                    batch_stats = future.result()
                    self._merge_stats(batch_stats)

                    with self._stats_lock:
                        self.stats["batches_completed"] += 1

                    # Report progress
                    self._report_progress()

                    # Check if we should throttle due to resource constraints
                    if self.resource_monitor.should_throttle():
                        logger.warning("Throttling due to high resource usage")
                        time.sleep(1)  # Brief pause to let system recover

                except Exception as e:
                    logger.error("Batch %d processing failed: %s", batch_index, e)

    def _merge_stats(self, batch_stats: Dict[str, int]):
        """Merge batch statistics into global stats."""
        with self._stats_lock:
            for key in ["processed", "indexed", "updated", "skipped", "failed"]:
                if key in batch_stats:
                    stat_key = f"files_{key}"
                    self.stats[stat_key] += batch_stats[key]

    def _report_progress(self):
        """Report progress to callbacks and logs."""
        with self._stats_lock:
            progress_data = {
                "processed": self.stats["files_processed"],
                "total": self.stats["total_files"],
                "percent": (
                    self.stats["files_processed"] / max(self.stats["total_files"], 1)
                )
                * 100,
                "rate": 0,
                "eta_seconds": 0,
            }

            # Calculate processing rate and ETA
            elapsed = time.time() - self.stats["start_time"]
            if elapsed > 0 and self.stats["files_processed"] > 0:
                progress_data["rate"] = self.stats["files_processed"] / elapsed
                remaining = self.stats["total_files"] - self.stats["files_processed"]
                if progress_data["rate"] > 0:
                    progress_data["eta_seconds"] = remaining / progress_data["rate"]

        # Call progress callbacks
        for callback in self._progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                logger.warning("Progress callback failed: %s", e)

        # Log progress periodically
        if progress_data["processed"] % 100 == 0:
            logger.info(
                "Progress: %d/%d files (%.1f%%) - Rate: %.1f files/sec",
                progress_data["processed"],
                progress_data["total"],
                progress_data["percent"],
                progress_data["rate"],
            )

    def _cleanup_deleted_files_optimized(self, directory: str):
        """Optimized cleanup of deleted files."""
        try:
            logger.info("Cleaning up deleted files...")

            # Get all posts in database that should be in this directory
            with self.database._pool.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT file_path FROM posts 
                    WHERE file_path LIKE ?
                """,
                    (f"{directory}%",),
                )

                db_files = [row[0] for row in cursor.fetchall()]

            # Check which files still exist
            deleted_files = []
            for file_path in db_files:
                if not os.path.exists(file_path):
                    deleted_files.append(file_path)

            # Remove deleted files from database
            if deleted_files:
                with self.database.transaction() as conn:
                    for file_path in deleted_files:
                        conn.execute(
                            "DELETE FROM posts WHERE file_path = ?", (file_path,)
                        )
                        logger.debug("Removed deleted file from index: %s", file_path)

                logger.info(
                    "Cleaned up %d deleted files from index", len(deleted_files)
                )

        except Exception as e:
            logger.error("Error during cleanup of deleted files: %s", e)

    def _finalize_stats(self) -> Dict[str, Any]:
        """Finalize and return indexing statistics."""
        with self._stats_lock:
            self.stats["end_time"] = time.time()
            self.stats["elapsed_time"] = (
                self.stats["end_time"] - self.stats["start_time"]
            )

        # Get resource statistics
        resource_stats = self.resource_monitor.get_resource_stats()

        logger.info(
            "Optimized indexing complete. Processed: %d, Indexed: %d, Updated: %d, Skipped: %d, Failed: %d",
            self.stats["files_processed"],
            self.stats["files_indexed"],
            self.stats["files_updated"],
            self.stats["files_skipped"],
            self.stats["files_failed"],
        )

        if self.stats["elapsed_time"] > 0:
            rate = self.stats["files_processed"] / self.stats["elapsed_time"]
            logger.info("Processing rate: %.1f files/second", rate)

        # Include resource stats in final results
        final_stats = self.stats.copy()
        final_stats["resource_stats"] = resource_stats

        return final_stats

    def get_indexing_progress(self) -> Dict[str, Any]:
        """Get current indexing progress with resource information."""
        with self._stats_lock:
            progress = self.stats.copy()

        if self.stats["start_time"] > 0 and self.stats["end_time"] == 0:
            progress["elapsed_time"] = time.time() - self.stats["start_time"]
        elif self.stats["end_time"] > 0:
            progress["elapsed_time"] = self.stats["end_time"] - self.stats["start_time"]
        else:
            progress["elapsed_time"] = 0

        # Add resource information
        progress["resource_stats"] = self.resource_monitor.get_resource_stats()

        return progress

    def stop_indexing(self):
        """Stop current indexing operation gracefully."""
        # Implementation would set a stop flag that's checked during processing
        # This is a placeholder for graceful shutdown functionality
        logger.info("Indexing stop requested")
        self.resource_monitor.stop_monitoring()
