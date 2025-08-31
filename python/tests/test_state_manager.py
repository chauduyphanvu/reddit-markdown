"""
Tests for the StateManager module.

Tests cover:
- Task persistence (save/load) 
- Download history tracking
- Duplicate detection
- Database operations
- Statistics generation
"""

import unittest
import tempfile
import os
import shutil
from datetime import datetime, timedelta

# Add parent directory to path for imports
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.state_manager import StateManager, DownloadRecord
from scheduler.task_scheduler import ScheduledTask, TaskResult, TaskStatus, create_task


class TestStateManager(unittest.TestCase):
    """Test StateManager functionality."""

    def setUp(self):
        """Set up test fixtures with temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.state_manager = StateManager(db_path=self.db_path)

    def tearDown(self):
        """Clean up test fixtures."""
        self.state_manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_initialization(self):
        """Database should be initialized with correct schema."""
        # Database file should exist
        self.assertTrue(os.path.exists(self.db_path))

    def test_save_task_creates_record(self):
        """Saving a task should create a database record."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.state_manager.save_task(task)

        loaded_task = self.state_manager.load_task(task.id)
        self.assertEqual(loaded_task.name, "Test Task")

    def test_save_task_preserves_id(self):
        """Saving a task should preserve the task ID."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.state_manager.save_task(task)

        loaded_task = self.state_manager.load_task(task.id)
        self.assertEqual(loaded_task.id, task.id)

    def test_save_task_preserves_cron_expression(self):
        """Saving a task should preserve the cron expression."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.state_manager.save_task(task)

        loaded_task = self.state_manager.load_task(task.id)
        self.assertEqual(loaded_task.cron_expression, "0 12 * * *")

    def test_save_task_preserves_subreddits(self):
        """Saving a task should preserve subreddits list."""
        task = create_task("Test Task", "0 12 * * *", ["r/python", "r/programming"])
        self.state_manager.save_task(task)

        loaded_task = self.state_manager.load_task(task.id)
        self.assertEqual(loaded_task.subreddits, ["r/python", "r/programming"])

    def test_save_task_preserves_enabled_state(self):
        """Saving a task should preserve enabled state."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        task.enabled = False
        self.state_manager.save_task(task)

        loaded_task = self.state_manager.load_task(task.id)
        self.assertFalse(loaded_task.enabled)

    def test_save_task_preserves_configuration(self):
        """Saving a task should preserve configuration parameters."""
        task = create_task(
            "Test Task",
            "0 12 * * *",
            ["r/python"],
            max_posts_per_subreddit=50,
            retry_count=5,
        )
        self.state_manager.save_task(task)

        loaded_task = self.state_manager.load_task(task.id)
        self.assertEqual(loaded_task.max_posts_per_subreddit, 50)

    def test_save_task_preserves_retry_count(self):
        """Saving a task should preserve retry count."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"], retry_count=5)
        self.state_manager.save_task(task)

        loaded_task = self.state_manager.load_task(task.id)
        self.assertEqual(loaded_task.retry_count, 5)

    def test_save_task_with_result_preserves_result(self):
        """Saving a task with result should preserve the result."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        result = TaskResult(
            task_id=task.id,
            status=TaskStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        task.last_result = result
        self.state_manager.save_task(task)

        loaded_task = self.state_manager.load_task(task.id)
        self.assertEqual(loaded_task.last_result.status, TaskStatus.COMPLETED)

    def test_load_nonexistent_task_returns_none(self):
        """Loading nonexistent task should return None."""
        result = self.state_manager.load_task("nonexistent-id")
        self.assertIsNone(result)

    def test_load_all_tasks_returns_empty_initially(self):
        """Loading all tasks should return empty list initially."""
        tasks = self.state_manager.load_all_tasks()
        self.assertEqual(len(tasks), 0)

    def test_load_all_tasks_returns_all_saved_tasks(self):
        """Loading all tasks should return all saved tasks."""
        task1 = create_task("Task 1", "0 12 * * *", ["r/python"])
        task2 = create_task("Task 2", "0 13 * * *", ["r/programming"])

        self.state_manager.save_task(task1)
        self.state_manager.save_task(task2)

        tasks = self.state_manager.load_all_tasks()
        self.assertEqual(len(tasks), 2)

    def test_load_all_tasks_returns_correct_names(self):
        """Loading all tasks should return tasks with correct names."""
        task1 = create_task("Task 1", "0 12 * * *", ["r/python"])
        task2 = create_task("Task 2", "0 13 * * *", ["r/programming"])

        self.state_manager.save_task(task1)
        self.state_manager.save_task(task2)

        tasks = self.state_manager.load_all_tasks()
        names = {task.name for task in tasks}
        self.assertEqual(names, {"Task 1", "Task 2"})

    def test_delete_existing_task_returns_true(self):
        """Deleting existing task should return True."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.state_manager.save_task(task)

        result = self.state_manager.delete_task(task.id)
        self.assertTrue(result)

    def test_delete_existing_task_removes_task(self):
        """Deleting existing task should remove it from database."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.state_manager.save_task(task)

        self.state_manager.delete_task(task.id)
        loaded_task = self.state_manager.load_task(task.id)
        self.assertIsNone(loaded_task)

    def test_delete_nonexistent_task_returns_false(self):
        """Deleting nonexistent task should return False."""
        result = self.state_manager.delete_task("nonexistent-id")
        self.assertFalse(result)

    def test_record_download_creates_record(self):
        """Recording a download should create a database record."""
        record = DownloadRecord(
            post_id="abc123",
            post_url="https://reddit.com/r/python/comments/abc123",
            subreddit="r/python",
            title="Test Post",
            author="testuser",
            downloaded_at=datetime.now(),
            file_path="/path/to/file.md",
        )

        self.state_manager.record_download(record)

        # Verify record exists
        self.assertTrue(self.state_manager.is_post_downloaded("abc123", "r/python"))

    def test_is_post_downloaded_returns_false_for_new_post(self):
        """is_post_downloaded should return False for new post."""
        result = self.state_manager.is_post_downloaded("new_post", "r/python")
        self.assertFalse(result)

    def test_is_post_downloaded_returns_true_for_existing_post(self):
        """is_post_downloaded should return True for existing post."""
        record = DownloadRecord(
            post_id="abc123",
            post_url="https://reddit.com/r/python/comments/abc123",
            subreddit="r/python",
            title="Test Post",
            author="testuser",
            downloaded_at=datetime.now(),
            file_path="/path/to/file.md",
        )
        self.state_manager.record_download(record)

        result = self.state_manager.is_post_downloaded("abc123", "r/python")
        self.assertTrue(result)

    def test_get_downloaded_posts_returns_empty_for_new_subreddit(self):
        """get_downloaded_posts should return empty set for new subreddit."""
        posts = self.state_manager.get_downloaded_posts("r/newsubreddit")
        self.assertEqual(len(posts), 0)

    def test_get_downloaded_posts_returns_post_ids(self):
        """get_downloaded_posts should return correct post IDs."""
        record1 = DownloadRecord(
            post_id="abc123",
            post_url="https://reddit.com/r/python/comments/abc123",
            subreddit="r/python",
            title="Test Post 1",
            author="testuser1",
            downloaded_at=datetime.now(),
            file_path="/path/to/file1.md",
        )
        record2 = DownloadRecord(
            post_id="def456",
            post_url="https://reddit.com/r/python/comments/def456",
            subreddit="r/python",
            title="Test Post 2",
            author="testuser2",
            downloaded_at=datetime.now(),
            file_path="/path/to/file2.md",
        )

        self.state_manager.record_download(record1)
        self.state_manager.record_download(record2)

        posts = self.state_manager.get_downloaded_posts("r/python")
        self.assertEqual(posts, {"abc123", "def456"})

    def test_get_downloaded_posts_respects_date_filter(self):
        """get_downloaded_posts should respect date filter."""
        # Old record (beyond date filter)
        old_record = DownloadRecord(
            post_id="old123",
            post_url="https://reddit.com/r/python/comments/old123",
            subreddit="r/python",
            title="Old Post",
            author="testuser",
            downloaded_at=datetime.now() - timedelta(days=40),
            file_path="/path/to/old.md",
        )

        # Recent record (within date filter)
        recent_record = DownloadRecord(
            post_id="new123",
            post_url="https://reddit.com/r/python/comments/new123",
            subreddit="r/python",
            title="Recent Post",
            author="testuser",
            downloaded_at=datetime.now(),
            file_path="/path/to/recent.md",
        )

        self.state_manager.record_download(old_record)
        self.state_manager.record_download(recent_record)

        # Should only return recent posts (30 days by default)
        posts = self.state_manager.get_downloaded_posts("r/python", since_days=30)
        self.assertEqual(posts, {"new123"})

    def test_get_download_history_returns_empty_initially(self):
        """get_download_history should return empty list initially."""
        history = self.state_manager.get_download_history()
        self.assertEqual(len(history), 0)

    def test_get_download_history_returns_records(self):
        """get_download_history should return download records."""
        record = DownloadRecord(
            post_id="abc123",
            post_url="https://reddit.com/r/python/comments/abc123",
            subreddit="r/python",
            title="Test Post",
            author="testuser",
            downloaded_at=datetime.now(),
            file_path="/path/to/file.md",
        )
        self.state_manager.record_download(record)

        history = self.state_manager.get_download_history()
        self.assertEqual(len(history), 1)

    def test_get_download_history_record_has_correct_data(self):
        """get_download_history records should have correct data."""
        record = DownloadRecord(
            post_id="abc123",
            post_url="https://reddit.com/r/python/comments/abc123",
            subreddit="r/python",
            title="Test Post",
            author="testuser",
            downloaded_at=datetime.now(),
            file_path="/path/to/file.md",
        )
        self.state_manager.record_download(record)

        history = self.state_manager.get_download_history()
        retrieved_record = history[0]
        self.assertEqual(retrieved_record.post_id, "abc123")

    def test_cleanup_old_history_returns_zero_for_no_old_records(self):
        """cleanup_old_history should return 0 when no old records exist."""
        result = self.state_manager.cleanup_old_history(days_to_keep=30)
        self.assertEqual(result, 0)

    def test_cleanup_old_history_removes_old_records(self):
        """cleanup_old_history should remove old records."""
        # Add old record
        old_record = DownloadRecord(
            post_id="old123",
            post_url="https://reddit.com/r/python/comments/old123",
            subreddit="r/python",
            title="Old Post",
            author="testuser",
            downloaded_at=datetime.now() - timedelta(days=100),
            file_path="/path/to/old.md",
        )
        self.state_manager.record_download(old_record)

        # Cleanup records older than 30 days
        deleted_count = self.state_manager.cleanup_old_history(days_to_keep=30)
        self.assertEqual(deleted_count, 1)

    def test_get_statistics_returns_correct_structure(self):
        """get_statistics should return correctly structured data."""
        stats = self.state_manager.get_statistics()

        self.assertIn("tasks", stats)
        self.assertIn("downloads", stats)
        self.assertIn("database", stats)

    def test_get_statistics_task_counts_initially_zero(self):
        """get_statistics should show zero task counts initially."""
        stats = self.state_manager.get_statistics()
        self.assertEqual(stats["tasks"]["total"], 0)

    def test_get_statistics_task_counts_after_adding_task(self):
        """get_statistics should show correct task counts after adding task."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.state_manager.save_task(task)

        stats = self.state_manager.get_statistics()
        self.assertEqual(stats["tasks"]["total"], 1)

    def test_get_statistics_download_counts_initially_zero(self):
        """get_statistics should show zero download counts initially."""
        stats = self.state_manager.get_statistics()
        self.assertEqual(stats["downloads"]["total"], 0)

    def test_get_statistics_download_counts_after_recording(self):
        """get_statistics should show correct download counts after recording."""
        record = DownloadRecord(
            post_id="abc123",
            post_url="https://reddit.com/r/python/comments/abc123",
            subreddit="r/python",
            title="Test Post",
            author="testuser",
            downloaded_at=datetime.now(),
            file_path="/path/to/file.md",
        )
        self.state_manager.record_download(record)

        stats = self.state_manager.get_statistics()
        self.assertEqual(stats["downloads"]["total"], 1)


class TestDownloadRecord(unittest.TestCase):
    """Test DownloadRecord dataclass."""

    def test_download_record_creation(self):
        """DownloadRecord should be created successfully."""
        record = DownloadRecord(
            post_id="abc123",
            post_url="https://reddit.com/r/python/comments/abc123",
            subreddit="r/python",
            title="Test Post",
            author="testuser",
            downloaded_at=datetime.now(),
            file_path="/path/to/file.md",
        )

        self.assertEqual(record.post_id, "abc123")

    def test_download_record_optional_task_id(self):
        """DownloadRecord should handle optional task_id."""
        record = DownloadRecord(
            post_id="abc123",
            post_url="https://reddit.com/r/python/comments/abc123",
            subreddit="r/python",
            title="Test Post",
            author="testuser",
            downloaded_at=datetime.now(),
            file_path="/path/to/file.md",
            task_id="task123",
        )

        self.assertEqual(record.task_id, "task123")


if __name__ == "__main__":
    unittest.main()
