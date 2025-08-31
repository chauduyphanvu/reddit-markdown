"""
Task executor for running scheduled download tasks.

Integrates with the existing download system to execute scheduled tasks.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict
from dataclasses import dataclass
from colored_logger import get_colored_logger

from .task_scheduler import ScheduledTask, TaskResult, TaskStatus
from .state_manager import StateManager, DownloadRecord

logger = get_colored_logger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


class TaskExecutor:
    """
    Executes scheduled download tasks by integrating with the existing download system.

    Features:
    - Integrates with existing Reddit download pipeline
    - Duplicate detection and prevention
    - Error handling and retries
    - Progress tracking and logging
    """

    def __init__(
        self,
        state_manager: StateManager,
        settings: Any,
        max_concurrent_subreddits: int = 3,
        batch_size: int = 10,
    ):
        """
        Initialize the task executor.

        Args:
            state_manager: StateManager instance for tracking downloads
            settings: Settings object for configuration
            max_concurrent_subreddits: Maximum concurrent subreddit processing
            batch_size: Batch size for processing posts
        """
        self.state_manager = state_manager
        self.settings = settings
        self.max_concurrent_subreddits = max_concurrent_subreddits
        self.batch_size = batch_size
        self._lock = threading.Lock()

        # Initialize retry configuration
        self.retry_config = RetryConfig()

        # Initialize execution metrics
        self._execution_metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_downloads": 0,
            "average_duration": 0.0,
        }

        logger.info(
            "Task executor initialized with %d max concurrent subreddits, batch size %d",
            max_concurrent_subreddits,
            batch_size,
        )

    def execute_task(self, task: ScheduledTask) -> TaskResult:
        """
        Execute a scheduled task by downloading posts from configured subreddits.

        Args:
            task: The scheduled task to execute

        Returns:
            TaskResult with execution details
        """
        start_time = datetime.now()

        try:
            logger.info("Starting execution of task '%s' (ID: %s)", task.name, task.id)

            # Check if task should run (basic validation)
            if not task.enabled:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    started_at=start_time,
                    completed_at=datetime.now(),
                    error="Task is disabled",
                )

            if not task.subreddits:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    started_at=start_time,
                    completed_at=datetime.now(),
                    error="No subreddits configured",
                )

            # Execute the task with timeout
            result = self._execute_with_timeout(task, task.timeout_seconds, start_time)

            if result.status == TaskStatus.FAILED and "timed out" in (
                result.error or ""
            ):
                logger.error(
                    "Task '%s' timed out after %ds", task.name, task.timeout_seconds
                )
            else:
                logger.info("Task '%s' completed successfully", task.name)

            return result

        except Exception as e:
            logger.error("Error executing task '%s': %s", task.name, e)
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                started_at=start_time,
                completed_at=datetime.now(),
                error=str(e),
            )

    def _execute_with_timeout(
        self, task: ScheduledTask, timeout_seconds: int, start_time: datetime = None
    ) -> TaskResult:
        """Execute task with timeout protection."""
        if start_time is None:
            start_time = datetime.now()
        result_container = [None]
        exception_container = [None]

        def task_runner():
            try:
                result_container[0] = self._do_execute_task(task, start_time)
            except Exception as e:
                exception_container[0] = e

        # Run task in separate thread for timeout control
        thread = threading.Thread(target=task_runner, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            # Task is still running - it timed out
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                started_at=start_time,
                completed_at=datetime.now(),
                error=f"Task execution timed out after {timeout_seconds} seconds",
            )

        if exception_container[0]:
            raise exception_container[0]

        return result_container[0]

    def _do_execute_task(self, task: ScheduledTask, start_time: datetime) -> TaskResult:
        """Actually execute the task (called in separate thread)."""
        downloaded_posts = 0
        skipped_posts = 0
        errors = []

        for subreddit in task.subreddits:
            try:
                logger.info(
                    "Processing subreddit %s for task '%s'", subreddit, task.name
                )

                # Get recent posts to avoid re-downloading
                recent_posts = self.state_manager.get_downloaded_posts(
                    subreddit, since_days=30
                )

                # Use real download pipeline
                posts_downloaded, posts_skipped, subreddit_errors = (
                    self._download_from_subreddit(task, subreddit, recent_posts)
                )

                downloaded_posts += posts_downloaded
                skipped_posts += posts_skipped
                errors.extend(subreddit_errors)

            except Exception as e:
                error_msg = f"Error processing subreddit {subreddit}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Determine overall status
        if errors and downloaded_posts == 0:
            status = TaskStatus.FAILED
        elif errors:
            status = TaskStatus.COMPLETED  # Partial success
        else:
            status = TaskStatus.COMPLETED

        # Create output summary
        output_lines = [
            f"Downloaded: {downloaded_posts} posts",
            f"Skipped: {skipped_posts} posts",
            f"Subreddits processed: {len(task.subreddits)}",
        ]

        if errors:
            output_lines.append(f"Errors: {len(errors)}")

        return TaskResult(
            task_id=task.id,
            status=status,
            started_at=start_time,
            completed_at=datetime.now(),
            error=(
                "; ".join(errors[:3]) if errors else None
            ),  # Limit error message length
            output="\n".join(output_lines),
        )

    def _download_from_subreddit(
        self, task: ScheduledTask, subreddit: str, recent_posts: set
    ) -> tuple[int, int, List[str]]:
        """
        Download posts from a subreddit using the existing download pipeline.

        Integrates with UrlFetcher and existing download system.

        Returns:
            Tuple of (downloaded_count, skipped_count, errors)
        """
        downloaded = 0
        skipped = 0
        errors = []

        try:
            # Import existing modules for download pipeline
            from url_fetcher import UrlFetcher
            import reddit_utils as utils
            from post_renderer import build_post_content
            from processing import ContentConverter
            from pathlib import Path

            # Create UrlFetcher to get posts from subreddit
            fetcher = UrlFetcher(
                settings=self.settings,
                cli_args=type(
                    "Args",
                    (),
                    {"urls": [], "src_files": [], "subs": [subreddit], "multis": []},
                )(),
                access_token=getattr(self.settings, "access_token", ""),
                prompt_for_input=False,
            )

            # Get URLs from subreddit
            post_urls = fetcher._get_subreddit_posts(subreddit, best=True)[
                : task.max_posts_per_subreddit
            ]

            base_save_dir = utils.resolve_save_dir(self.settings.default_save_location)

            for url in post_urls:
                try:
                    # Clean the URL
                    clean_url = utils.clean_url(url)

                    # Extract post ID for duplicate check
                    post_id = self._extract_post_id(clean_url)
                    if post_id in recent_posts:
                        skipped += 1
                        logger.debug("Skipping already downloaded post: %s", post_id)
                        continue

                    # Validate URL
                    if not utils.valid_url(clean_url):
                        logger.warning("Invalid URL: %s", clean_url)
                        errors.append(f"Invalid URL: {clean_url}")
                        continue

                    # Download post JSON
                    data = utils.download_post_json(
                        clean_url, getattr(self.settings, "access_token", "")
                    )
                    if not data or not isinstance(data, list) or len(data) < 2:
                        logger.error("Invalid data structure for URL: %s", clean_url)
                        errors.append(f"Invalid data for: {clean_url}")
                        continue

                    # Extract post information
                    post_info = data[0].get("data", {}).get("children", [])
                    if not post_info or not isinstance(post_info[0], dict):
                        logger.error("No post info found for: %s", clean_url)
                        errors.append(f"No post info: {clean_url}")
                        continue

                    post_data = post_info[0].get("data", {})
                    replies_data = (
                        data[1].get("data", {}).get("children", [])
                        if isinstance(data[1], dict)
                        else []
                    )

                    # Generate filename
                    post_timestamp = ""
                    if "created_utc" in post_data and isinstance(
                        post_data["created_utc"], (int, float)
                    ):
                        try:
                            from datetime import timezone

                            dt = datetime.fromtimestamp(
                                post_data["created_utc"], timezone.utc
                            )
                            post_timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except (ValueError, OSError):
                            pass

                    target_path = utils.generate_filename(
                        base_dir=base_save_dir,
                        url=clean_url,
                        subreddit=post_data.get("subreddit_name_prefixed", ""),
                        use_timestamped_dirs=self.settings.use_timestamped_directories,
                        post_timestamp=post_timestamp,
                        file_format=self.settings.file_format,
                        overwrite=self.settings.overwrite_existing_file,
                    )

                    # Build content
                    colors = ["🟩", "🟨", "🟧", "🟦", "🟪", "🟥", "🟫", "⬛️", "⬜️"]
                    raw_markdown = build_post_content(
                        post_data=post_data,
                        replies_data=replies_data,
                        settings=self.settings,
                        colors=colors,
                        url=clean_url,
                        target_path=target_path,
                    )

                    # Convert format if needed
                    if self.settings.file_format.lower() == "html":
                        final_content = ContentConverter.markdown_to_html(raw_markdown)
                    else:
                        final_content = raw_markdown

                    # Save file
                    file_path = Path(target_path)
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with file_path.open("w", encoding="utf-8") as f:
                        f.write(final_content)

                    # Record successful download
                    record = DownloadRecord(
                        post_id=post_id,
                        post_url=clean_url,
                        subreddit=subreddit,
                        title=post_data.get("title", "Untitled"),
                        author=post_data.get("author", "[unknown]"),
                        downloaded_at=datetime.now(),
                        file_path=target_path,
                        task_id=task.id,
                    )

                    with self._lock:
                        self.state_manager.record_download(record)

                    downloaded += 1
                    logger.info(
                        "Successfully downloaded: %s", post_data.get("title", clean_url)
                    )

                    # Rate limiting
                    time.sleep(0.1)

                except Exception as e:
                    error_msg = f"Error downloading {url}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    continue

        except Exception as e:
            error_msg = f"Error processing subreddit {subreddit}: {e}"
            errors.append(error_msg)
            logger.error(error_msg)

        return downloaded, skipped, errors

    def _extract_post_id(self, url: str) -> str:
        """Extract Reddit post ID from URL."""
        import re

        # Match Reddit URL patterns to extract post ID
        patterns = [
            r"/comments/([a-zA-Z0-9]+)/",
            r"redd\.it/([a-zA-Z0-9]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Fallback: use URL hash as ID
        import hashlib

        return hashlib.md5(url.encode()).hexdigest()[:12]

    def _validate_task(self, task: ScheduledTask) -> Optional[str]:
        """Validate task configuration and return error message if invalid."""
        if not task.enabled:
            return "Task is disabled"

        if not task.subreddits:
            return "No subreddits configured"

        if task.max_posts_per_subreddit <= 0:
            return "Invalid max_posts_per_subreddit value"

        return None

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay using exponential backoff with jitter."""
        base_delay = 1.0
        max_delay = 60.0
        backoff_multiplier = 2.0

        delay = min(base_delay * (backoff_multiplier ** (attempt - 1)), max_delay)

        # Add jitter to prevent thundering herd
        import random

        jitter = random.uniform(0.1, 0.3) * delay
        return delay + jitter

    def _process_subreddits_concurrently(
        self, task: ScheduledTask
    ) -> List[Dict[str, Any]]:
        """Process subreddits concurrently and return results."""
        import concurrent.futures

        results = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_concurrent_subreddits
        ) as executor:
            # Submit tasks for each subreddit
            future_to_subreddit = {
                executor.submit(
                    self._process_single_subreddit, task, subreddit
                ): subreddit
                for subreddit in task.subreddits
            }

            # Collect results
            for future in concurrent.futures.as_completed(future_to_subreddit):
                subreddit = future_to_subreddit[future]
                try:
                    result = future.result()
                    result["subreddit"] = subreddit
                    results.append(result)
                except Exception as e:
                    results.append(
                        {
                            "subreddit": subreddit,
                            "error": str(e),
                            "downloaded": 0,
                            "skipped": 0,
                        }
                    )

        return results

    def _process_single_subreddit(
        self, task: ScheduledTask, subreddit: str
    ) -> Dict[str, Any]:
        """Process a single subreddit and return results."""
        try:
            # Get recent posts to avoid re-downloading
            recent_posts = self.state_manager.get_downloaded_posts(
                subreddit, since_days=30
            )

            # Use existing download pipeline
            downloaded, skipped, errors = self._download_from_subreddit(
                task, subreddit, recent_posts
            )

            return {"downloaded": downloaded, "skipped": skipped, "errors": errors}
        except Exception as e:
            return {"downloaded": 0, "skipped": 0, "errors": [str(e)]}

    def get_metrics(self) -> Dict[str, Any]:
        """Get current execution metrics."""
        with self._lock:
            metrics = self._execution_metrics.copy()

            # Calculate success rate percentage
            total = metrics.get("total_tasks", 0)
            successful = metrics.get("successful_tasks", 0)

            if total > 0:
                metrics["success_rate_percent"] = (successful / total) * 100.0
            else:
                metrics["success_rate_percent"] = 0.0

            return metrics

    def _update_average_duration(self, duration: float) -> None:
        """Update average task duration metric."""
        with self._lock:
            current_count = self._execution_metrics["total_tasks"]
            current_avg = self._execution_metrics["average_duration"]

            # Calculate new average based on current count
            if current_count > 0:
                new_avg = (
                    (current_avg * (current_count - 1)) + duration
                ) / current_count
                self._execution_metrics["average_duration"] = new_avg
            else:
                self._execution_metrics["average_duration"] = duration

    def reset_metrics(self) -> None:
        """Reset execution metrics."""
        with self._lock:
            self._execution_metrics = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "total_downloads": 0,
                "average_duration": 0.0,
            }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        try:
            # Test state manager connectivity
            stats = self.state_manager.get_statistics()

            # Test basic functionality
            test_posts = self.state_manager.get_downloaded_posts("test", since_days=1)

            return {
                "status": "healthy",
                "state_manager_connected": True,
                "database_accessible": True,
                "metrics": self.get_metrics(),
                "database_stats": stats,
            }

        except Exception as e:
            logger.error("Health check failed: %s", e)
            return {
                "status": "unhealthy",
                "error": str(e),
                "state_manager_connected": False,
                "database_accessible": False,
            }

    def cleanup_resources(self) -> None:
        """Clean up resources used by the executor."""
        try:
            # Reset metrics
            self.reset_metrics()

            # Clear any cached data
            if hasattr(self, "_session_pool") and self._session_pool:
                self._session_pool.close()

            logger.info("Task executor resources cleaned up")

        except Exception as e:
            logger.error("Error during resource cleanup: %s", e)
