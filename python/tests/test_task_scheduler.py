"""
Tests for the TaskScheduler module.

Tests cover:
- Task creation and validation
- Task management (add/remove/enable/disable)
- Scheduler status reporting
- Task execution callback integration
"""

import unittest
import time
import threading
from datetime import datetime, timedelta
import tempfile
import os

# Add parent directory to path for imports
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.task_scheduler import (
    TaskScheduler,
    ScheduledTask,
    TaskResult,
    TaskStatus,
    create_task,
)


class TestScheduledTask(unittest.TestCase):
    """Test ScheduledTask dataclass validation."""

    def test_valid_task_creation(self):
        """Valid ScheduledTask should be created successfully."""
        task = ScheduledTask(
            id="test-id",
            name="Test Task",
            cron_expression="0 12 * * *",
            subreddits=["r/python"],
        )
        self.assertEqual(task.name, "Test Task")

    def test_task_id_is_set(self):
        """Task ID should be set correctly."""
        task = ScheduledTask(
            id="test-id",
            name="Test Task",
            cron_expression="0 12 * * *",
            subreddits=["r/python"],
        )
        self.assertEqual(task.id, "test-id")

    def test_task_subreddits_are_set(self):
        """Task subreddits should be set correctly."""
        task = ScheduledTask(
            id="test-id",
            name="Test Task",
            cron_expression="0 12 * * *",
            subreddits=["r/python", "r/programming"],
        )
        self.assertEqual(task.subreddits, ["r/python", "r/programming"])

    def test_task_defaults_are_applied(self):
        """Task default values should be applied correctly."""
        task = ScheduledTask(
            id="test-id",
            name="Test Task",
            cron_expression="0 12 * * *",
            subreddits=["r/python"],
        )
        self.assertTrue(task.enabled)

    def test_task_max_posts_default(self):
        """Task max_posts_per_subreddit default should be 25."""
        task = ScheduledTask(
            id="test-id",
            name="Test Task",
            cron_expression="0 12 * * *",
            subreddits=["r/python"],
        )
        self.assertEqual(task.max_posts_per_subreddit, 25)

    def test_empty_name_raises_error(self):
        """Empty task name should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            ScheduledTask(
                id="test-id",
                name="",
                cron_expression="0 12 * * *",
                subreddits=["r/python"],
            )
        self.assertIn("name cannot be empty", str(cm.exception))

    def test_empty_subreddits_raises_error(self):
        """Empty subreddits list should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            ScheduledTask(
                id="test-id",
                name="Test Task",
                cron_expression="0 12 * * *",
                subreddits=[],
            )
        self.assertIn("at least one subreddit", str(cm.exception))

    def test_negative_max_posts_raises_error(self):
        """Negative max_posts_per_subreddit should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            ScheduledTask(
                id="test-id",
                name="Test Task",
                cron_expression="0 12 * * *",
                subreddits=["r/python"],
                max_posts_per_subreddit=-1,
            )
        self.assertIn("must be positive", str(cm.exception))

    def test_negative_retry_count_raises_error(self):
        """Negative retry_count should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            ScheduledTask(
                id="test-id",
                name="Test Task",
                cron_expression="0 12 * * *",
                subreddits=["r/python"],
                retry_count=-1,
            )
        self.assertIn("cannot be negative", str(cm.exception))

    def test_zero_timeout_raises_error(self):
        """Zero timeout_seconds should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            ScheduledTask(
                id="test-id",
                name="Test Task",
                cron_expression="0 12 * * *",
                subreddits=["r/python"],
                timeout_seconds=0,
            )
        self.assertIn("must be positive", str(cm.exception))


class TestTaskScheduler(unittest.TestCase):
    """Test TaskScheduler functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.scheduler = TaskScheduler(
            check_interval_seconds=1
        )  # Fast interval for testing
        self.test_results = []

        # Mock task executor that just records calls
        def mock_executor(task):
            self.test_results.append(f"executed_{task.id}")
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )

        self.scheduler.set_task_executor(mock_executor)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self.scheduler, "_running") and self.scheduler._running:
            self.scheduler.stop(timeout_seconds=5)

    def test_scheduler_initialization(self):
        """Scheduler should initialize with correct defaults."""
        self.assertEqual(self.scheduler.check_interval_seconds, 1)

    def test_scheduler_not_running_initially(self):
        """Scheduler should not be running initially."""
        self.assertFalse(self.scheduler._running)

    def test_add_task_succeeds(self):
        """Adding a valid task should succeed."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.scheduler.add_task(task)

        retrieved = self.scheduler.get_task(task.id)
        self.assertEqual(retrieved.name, "Test Task")

    def test_add_task_calculates_next_run(self):
        """Adding a task should calculate next run time."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.scheduler.add_task(task)

        retrieved = self.scheduler.get_task(task.id)
        self.assertIsNotNone(retrieved.next_run)

    def test_add_task_with_invalid_cron_raises_error(self):
        """Adding task with invalid cron should raise ValueError."""
        task = create_task("Test Task", "invalid", ["r/python"])

        with self.assertRaises(ValueError) as cm:
            self.scheduler.add_task(task)
        self.assertIn("Invalid cron expression", str(cm.exception))

    def test_remove_existing_task_returns_true(self):
        """Removing existing task should return True."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.scheduler.add_task(task)

        result = self.scheduler.remove_task(task.id)
        self.assertTrue(result)

    def test_remove_nonexistent_task_returns_false(self):
        """Removing nonexistent task should return False."""
        result = self.scheduler.remove_task("nonexistent-id")
        self.assertFalse(result)

    def test_get_all_tasks_returns_all_tasks(self):
        """get_all_tasks should return all added tasks."""
        task1 = create_task("Task 1", "0 12 * * *", ["r/python"])
        task2 = create_task("Task 2", "0 13 * * *", ["r/programming"])

        self.scheduler.add_task(task1)
        self.scheduler.add_task(task2)

        all_tasks = self.scheduler.get_all_tasks()
        self.assertEqual(len(all_tasks), 2)

    def test_get_all_tasks_returns_correct_names(self):
        """get_all_tasks should return tasks with correct names."""
        task1 = create_task("Task 1", "0 12 * * *", ["r/python"])
        task2 = create_task("Task 2", "0 13 * * *", ["r/programming"])

        self.scheduler.add_task(task1)
        self.scheduler.add_task(task2)

        all_tasks = self.scheduler.get_all_tasks()
        names = {task.name for task in all_tasks}
        self.assertEqual(names, {"Task 1", "Task 2"})

    def test_enable_existing_task_returns_true(self):
        """Enabling existing task should return True."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        task.enabled = False
        self.scheduler.add_task(task)

        result = self.scheduler.enable_task(task.id)
        self.assertTrue(result)

    def test_enable_existing_task_sets_enabled(self):
        """Enabling existing task should set enabled to True."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        task.enabled = False
        self.scheduler.add_task(task)

        self.scheduler.enable_task(task.id)
        retrieved = self.scheduler.get_task(task.id)
        self.assertTrue(retrieved.enabled)

    def test_enable_nonexistent_task_returns_false(self):
        """Enabling nonexistent task should return False."""
        result = self.scheduler.enable_task("nonexistent-id")
        self.assertFalse(result)

    def test_disable_existing_task_returns_true(self):
        """Disabling existing task should return True."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.scheduler.add_task(task)

        result = self.scheduler.disable_task(task.id)
        self.assertTrue(result)

    def test_disable_existing_task_sets_disabled(self):
        """Disabling existing task should set enabled to False."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.scheduler.add_task(task)

        self.scheduler.disable_task(task.id)
        retrieved = self.scheduler.get_task(task.id)
        self.assertFalse(retrieved.enabled)

    def test_disable_nonexistent_task_returns_false(self):
        """Disabling nonexistent task should return False."""
        result = self.scheduler.disable_task("nonexistent-id")
        self.assertFalse(result)

    def test_start_without_executor_raises_error(self):
        """Starting scheduler without executor should raise RuntimeError."""
        scheduler = TaskScheduler()

        with self.assertRaises(RuntimeError) as cm:
            scheduler.start()
        self.assertIn("executor callback", str(cm.exception))

    def test_get_status_returns_correct_structure(self):
        """get_status should return correctly structured status."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.scheduler.add_task(task)

        status = self.scheduler.get_status()
        self.assertIn("running", status)

    def test_get_status_includes_task_count(self):
        """get_status should include correct task count."""
        task1 = create_task("Task 1", "0 12 * * *", ["r/python"])
        task2 = create_task("Task 2", "0 13 * * *", ["r/programming"])

        self.scheduler.add_task(task1)
        self.scheduler.add_task(task2)

        status = self.scheduler.get_status()
        self.assertEqual(status["total_tasks"], 2)

    def test_get_status_includes_enabled_count(self):
        """get_status should include correct enabled task count."""
        task1 = create_task("Task 1", "0 12 * * *", ["r/python"])
        task2 = create_task("Task 2", "0 13 * * *", ["r/programming"])
        task2.enabled = False

        self.scheduler.add_task(task1)
        self.scheduler.add_task(task2)

        status = self.scheduler.get_status()
        self.assertEqual(status["enabled_tasks"], 1)

    def test_get_status_includes_tasks_list(self):
        """get_status should include list of tasks."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.scheduler.add_task(task)

        status = self.scheduler.get_status()
        self.assertEqual(len(status["tasks"]), 1)

    def test_get_status_task_has_required_fields(self):
        """get_status task entries should have required fields."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.scheduler.add_task(task)

        status = self.scheduler.get_status()
        task_info = status["tasks"][0]

        required_fields = ["id", "name", "enabled", "cron_expression", "subreddits"]
        for field in required_fields:
            self.assertIn(field, task_info)


class TestCreateTask(unittest.TestCase):
    """Test create_task convenience function."""

    def test_create_task_with_minimal_args(self):
        """create_task should work with minimal arguments."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.assertEqual(task.name, "Test Task")

    def test_create_task_generates_id(self):
        """create_task should generate a unique ID."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"])
        self.assertIsInstance(task.id, str)

    def test_create_task_id_is_unique(self):
        """create_task should generate unique IDs."""
        task1 = create_task("Task 1", "0 12 * * *", ["r/python"])
        task2 = create_task("Task 2", "0 13 * * *", ["r/programming"])
        self.assertNotEqual(task1.id, task2.id)

    def test_create_task_accepts_custom_id(self):
        """create_task should accept custom ID."""
        task = create_task("Test Task", "0 12 * * *", ["r/python"], id="custom-id")
        self.assertEqual(task.id, "custom-id")

    def test_create_task_accepts_kwargs(self):
        """create_task should pass through additional kwargs."""
        task = create_task(
            "Test Task", "0 12 * * *", ["r/python"], max_posts_per_subreddit=50
        )
        self.assertEqual(task.max_posts_per_subreddit, 50)


if __name__ == "__main__":
    unittest.main()
