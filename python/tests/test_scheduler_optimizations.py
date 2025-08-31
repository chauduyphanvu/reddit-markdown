"""
Comprehensive tests for scheduler optimizations including safety, reliability, and performance features.
"""

import pytest
import threading
import time
import tempfile
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from scheduler.task_scheduler import (
    TaskScheduler,
    ScheduledTask,
    TaskStatus,
    TaskResult,
    ResourceMonitor,
)
from scheduler.state_manager import StateManager, DownloadRecord, BloomFilter
from scheduler.task_executor import TaskExecutor, RetryConfig
from scheduler.cron_parser import CronParser


class TestTaskSchedulerOptimizations:
    """Test safety, reliability and performance optimizations in TaskScheduler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scheduler = TaskScheduler(
            check_interval_seconds=1,
            max_concurrent_tasks=2,
            max_memory_mb=100,
            enable_monitoring=True,
        )

    def teardown_method(self):
        """Clean up after tests."""
        if hasattr(self.scheduler, "_running") and self.scheduler._running:
            self.scheduler.stop(timeout_seconds=5)

    def test_resource_monitoring_initialization(self):
        """Test resource monitoring is properly initialized."""
        assert self.scheduler.max_memory_mb == 100
        assert self.scheduler.enable_monitoring is True
        assert self.scheduler._resource_monitor is not None
        assert isinstance(self.scheduler._resource_monitor, ResourceMonitor)

    def test_circuit_breaker_functionality(self):
        """Test circuit breaker prevents task execution after failures."""
        task_id = "test_task"

        # Record multiple failures
        for _ in range(3):
            self.scheduler._record_task_failure(task_id)

        # Circuit breaker should be open
        assert self.scheduler._is_circuit_breaker_open(task_id) is True

        # Wait for cooldown period
        time.sleep(0.1)

        # Circuit breaker should still be open within cooldown period
        assert self.scheduler._is_circuit_breaker_open(task_id) is True

    def test_circuit_breaker_reset_after_success(self):
        """Test circuit breaker resets after successful execution."""
        task_id = "test_task"

        # Record failures
        self.scheduler._record_task_failure(task_id)
        self.scheduler._record_task_failure(task_id)

        # Record success - should reset circuit breaker
        self.scheduler._record_task_success(task_id)

        assert self.scheduler._circuit_breaker_failures.get(task_id, 0) == 0

    def test_rate_limiting(self):
        """Test rate limiting prevents rapid task execution."""
        task_id = "test_task"

        # Update rate limiter
        self.scheduler._update_rate_limiter(task_id)

        # Should be rate limited immediately after
        assert self.scheduler._is_rate_limited(task_id) is True

    @patch("psutil.Process")
    def test_memory_monitoring(self, mock_process):
        """Test memory usage monitoring and limits."""
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance
        mock_process_instance.memory_info.return_value = Mock(
            rss=200 * 1024 * 1024
        )  # 200MB

        memory_usage = self.scheduler._get_memory_usage()
        assert memory_usage == 200

    @patch("psutil.cpu_percent")
    def test_cpu_monitoring(self, mock_cpu):
        """Test CPU usage monitoring."""
        mock_cpu.return_value = 45.5

        cpu_usage = self.scheduler._get_cpu_usage()
        assert cpu_usage == 45.5

    def test_thread_pool_execution(self):
        """Test tasks are executed using thread pool."""
        assert self.scheduler._thread_pool is not None
        assert self.scheduler._thread_pool._max_workers == 2

    def test_graceful_shutdown_with_running_tasks(self):
        """Test graceful shutdown waits for running tasks."""

        # Mock task executor
        def mock_executor(task):
            time.sleep(0.5)  # Simulate work
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )

        self.scheduler.set_task_executor(mock_executor)

        # Create and add a task
        task = ScheduledTask(
            id="test_task",
            name="Test Task",
            cron_expression="* * * * *",
            subreddits=["test"],
        )

        self.scheduler.add_task(task)
        # Force task to run immediately by setting next_run to now
        task.next_run = datetime.now()
        self.scheduler.start()

        # Let task start
        time.sleep(0.1)

        # Stop scheduler - should wait for task to complete
        start_time = time.time()
        self.scheduler.stop(timeout_seconds=2)
        duration = time.time() - start_time

        # Should have waited for task completion
        assert (
            duration >= 0.35
        )  # Task should have had time to complete (allow for timing variance)

    def test_stuck_task_detection(self):
        """Test detection of tasks that are stuck/running too long."""
        task = ScheduledTask(
            id="stuck_task",
            name="Stuck Task",
            cron_expression="* * * * *",
            subreddits=["test"],
            last_run=datetime.now() - timedelta(hours=3),  # 3 hours ago
        )

        task.last_result = TaskResult(
            task_id=task.id, status=TaskStatus.RUNNING, started_at=task.last_run
        )

        self.scheduler._tasks[task.id] = task

        # Should detect stuck task
        with patch("scheduler.task_scheduler.logger") as mock_logger:
            self.scheduler._check_stuck_tasks()
            mock_logger.warning.assert_called_once()


class TestStateManagerOptimizations:
    """Test reliability and performance optimizations in StateManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.state_manager = StateManager(
            db_path=self.temp_db.name,
            pool_size=3,
            enable_wal=True,
            backup_enabled=False,  # Disable for testing
        )

    def teardown_method(self):
        """Clean up after tests."""
        self.state_manager.close()
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_connection_pooling(self):
        """Test connection pooling functionality."""
        assert self.state_manager.pool_size == 3
        assert self.state_manager._connection_pool.qsize() == 3

    def test_connection_pool_exhaustion_handling(self):
        """Test behavior when connection pool is exhausted."""
        # Get all connections from pool
        connections = []
        for _ in range(3):
            with self.state_manager._get_connection() as conn:
                connections.append(conn)

        # Should still work by creating temporary connection
        with self.state_manager._get_connection() as conn:
            assert conn is not None

    def test_bloom_filter_functionality(self):
        """Test bloom filter for duplicate detection."""
        bloom = BloomFilter(capacity=1000, error_rate=0.1)

        # Add items
        bloom.add("test_item_1")
        bloom.add("test_item_2")

        # Check membership
        assert bloom.might_contain("test_item_1") is True
        assert bloom.might_contain("test_item_2") is True
        assert bloom.might_contain("non_existent_item") is False

    def test_batch_cleanup_operations(self):
        """Test batch cleanup of old records."""
        # Add some test records
        for i in range(100):
            record = DownloadRecord(
                post_id=f"post_{i}",
                post_url=f"https://reddit.com/post_{i}",
                subreddit="test",
                title=f"Test Post {i}",
                author="test_author",
                downloaded_at=datetime.now() - timedelta(days=100),  # Old records
                file_path=f"/tmp/post_{i}.md",
            )
            self.state_manager.record_download(record)

        # Cleanup with batch processing
        deleted_count = self.state_manager.cleanup_old_history(
            days_to_keep=30, batch_size=10
        )
        assert deleted_count == 100

    def test_database_integrity_check(self):
        """Test database integrity checking."""
        with self.state_manager._get_connection() as conn:
            integrity_ok = self.state_manager._check_database_integrity(conn)
            assert integrity_ok is True

    def test_retry_logic_on_database_errors(self):
        """Test retry logic for database operations."""
        task = ScheduledTask(
            id="retry_test",
            name="Retry Test",
            cron_expression="0 0 * * *",
            subreddits=["test"],
        )

        # Mock database error on first attempt
        with patch.object(self.state_manager, "_save_task_impl") as mock_save:
            mock_save.side_effect = [
                sqlite3.OperationalError("database is locked"),
                None,
            ]

            # Should retry and succeed
            self.state_manager.save_task(task)
            assert mock_save.call_count == 2

    def test_optimized_duplicate_detection(self):
        """Test optimized duplicate detection using bloom filter."""
        # Record a download
        record = DownloadRecord(
            post_id="test_post",
            post_url="https://reddit.com/test",
            subreddit="test_sub",
            title="Test Post",
            author="test_author",
            downloaded_at=datetime.now(),
            file_path="/tmp/test.md",
        )
        self.state_manager.record_download(record)

        # Check if post is downloaded (should use bloom filter + DB)
        is_downloaded = self.state_manager.is_post_downloaded("test_post", "test_sub")
        assert is_downloaded is True

        # Check non-existent post (bloom filter should shortcut)
        is_downloaded = self.state_manager.is_post_downloaded(
            "non_existent", "test_sub"
        )
        assert is_downloaded is False


class TestTaskExecutorOptimizations:
    """Test performance and reliability optimizations in TaskExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.state_manager = StateManager(db_path=self.temp_db.name)
        self.settings = Mock()
        self.executor = TaskExecutor(
            state_manager=self.state_manager,
            settings=self.settings,
            max_concurrent_subreddits=2,
            batch_size=5,
        )

    def teardown_method(self):
        """Clean up after tests."""
        self.state_manager.close()
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_retry_configuration(self):
        """Test retry configuration is properly initialized."""
        assert self.executor.retry_config.max_retries == 3
        assert self.executor.retry_config.base_delay == 1.0
        assert self.executor.retry_config.backoff_multiplier == 2.0

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        delay1 = self.executor._calculate_retry_delay(1)
        delay2 = self.executor._calculate_retry_delay(2)
        delay3 = self.executor._calculate_retry_delay(3)

        # Should increase exponentially (with jitter, so approximate)
        assert 0.5 <= delay1 <= 1.5  # Base delay with jitter
        assert 1.0 <= delay2 <= 3.0  # 2x base delay with jitter
        assert 2.0 <= delay3 <= 6.0  # 4x base delay with jitter

    def test_concurrent_subreddit_processing(self):
        """Test concurrent processing of multiple subreddits."""
        task = ScheduledTask(
            id="concurrent_test",
            name="Concurrent Test",
            cron_expression="0 0 * * *",
            subreddits=["sub1", "sub2", "sub3"],
            max_posts_per_subreddit=5,
        )

        # Mock the single subreddit processing method
        with patch.object(self.executor, "_process_single_subreddit") as mock_process:
            mock_process.return_value = (2, 1, [])  # downloaded, skipped, errors

            results = self.executor._process_subreddits_concurrently(task)

            # Should have processed all subreddits
            assert len(results) == 3
            assert mock_process.call_count == 3

    def test_task_validation(self):
        """Test comprehensive task validation."""
        # Test disabled task
        task = ScheduledTask(
            id="test",
            name="Test",
            cron_expression="0 0 * * *",
            subreddits=["test"],
            enabled=False,
        )
        error = self.executor._validate_task(task)
        assert error == "Task is disabled"

        # Test no subreddits
        task.enabled = True
        task.subreddits = []
        error = self.executor._validate_task(task)
        assert error == "No subreddits configured"

        # Test invalid max posts
        task.subreddits = ["test"]
        task.max_posts_per_subreddit = 0
        error = self.executor._validate_task(task)
        assert error == "Invalid max_posts_per_subreddit value"

    def test_metrics_tracking(self):
        """Test execution metrics are properly tracked."""
        initial_metrics = self.executor.get_metrics()
        assert initial_metrics["total_tasks"] == 0
        assert initial_metrics["successful_tasks"] == 0

        # Update metrics
        self.executor._execution_metrics["total_tasks"] = 10
        self.executor._execution_metrics["successful_tasks"] = 8

        updated_metrics = self.executor.get_metrics()
        assert updated_metrics["total_tasks"] == 10
        assert updated_metrics["success_rate_percent"] == 80.0

    def test_health_check(self):
        """Test health check functionality."""
        health = self.executor.health_check()

        assert "status" in health
        assert "state_manager_connected" in health
        assert "database_accessible" in health
        assert "metrics" in health

    def test_resource_cleanup(self):
        """Test proper resource cleanup."""
        # Set some metrics
        self.executor._execution_metrics["total_tasks"] = 5

        # Cleanup resources
        self.executor.cleanup_resources()

        # Metrics should be reset
        assert self.executor._execution_metrics["total_tasks"] == 0

    def test_timeout_handling_with_futures(self):
        """Test timeout handling using concurrent futures."""
        task = ScheduledTask(
            id="timeout_test",
            name="Timeout Test",
            cron_expression="0 0 * * *",
            subreddits=["test"],
            timeout_seconds=1,  # Very short timeout
        )

        # Mock a long-running task
        def slow_task(task, start_time):
            time.sleep(2)  # Longer than timeout
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                started_at=start_time,
                completed_at=datetime.now(),
            )

        with patch.object(self.executor, "_do_execute_task", slow_task):
            result = self.executor._execute_with_timeout(task, 1, datetime.now())

            assert result.status == TaskStatus.FAILED
            assert "timed out" in result.error

    def test_average_duration_calculation(self):
        """Test rolling average duration calculation."""
        # Initial average should be 0
        assert self.executor._execution_metrics["average_duration"] == 0.0

        # Add some durations
        self.executor._execution_metrics["total_tasks"] = 1
        self.executor._update_average_duration(10.0)
        assert self.executor._execution_metrics["average_duration"] == 10.0

        self.executor._execution_metrics["total_tasks"] = 2
        self.executor._update_average_duration(20.0)
        assert self.executor._execution_metrics["average_duration"] == 15.0


class TestCronParserSafety:
    """Test safety features in CronParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CronParser()

    def test_malicious_input_rejection(self):
        """Test rejection of potentially malicious cron expressions."""
        malicious_inputs = [
            "; rm -rf /",
            "$(cat /etc/passwd)",
            "0 0 * * * & rm -rf /",
            "0 0 * * *; wget malicious.com",
            "`whoami`",
            "${HOME}",
            "0 0 * * *\n; rm -rf /",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValueError, match="Invalid characters"):
                self.parser.parse(malicious_input)

    def test_infinite_loop_prevention(self):
        """Test prevention of infinite loops in next execution calculation."""
        # This should not cause infinite loop
        expr = self.parser.parse("0 0 30 2 *")  # Feb 30th (doesn't exist)

        # Should find next valid time or raise exception within reasonable time
        start_time = time.time()
        try:
            next_time = self.parser.next_execution(expr)
            duration = time.time() - start_time
            assert duration < 5.0  # Should complete within 5 seconds
        except RuntimeError as e:
            # Expected if no valid time found within limit
            assert "Could not find next execution time" in str(e)
            duration = time.time() - start_time
            assert duration < 5.0


class TestIntegrationOptimizations:
    """Integration tests for scheduler optimizations."""

    def setup_method(self):
        """Set up integration test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.state_manager = StateManager(db_path=self.temp_db.name)
        self.settings = Mock()
        self.scheduler = TaskScheduler(check_interval_seconds=1, max_concurrent_tasks=2)
        self.executor = TaskExecutor(self.state_manager, self.settings)

        self.scheduler.set_task_executor(self.executor.execute_task)

    def teardown_method(self):
        """Clean up integration test environment."""
        if self.scheduler._running:
            self.scheduler.stop(timeout_seconds=5)
        self.state_manager.close()
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_end_to_end_task_execution_with_optimizations(self):
        """Test end-to-end task execution with all optimizations enabled."""
        # Create a task
        task = ScheduledTask(
            id="integration_test",
            name="Integration Test",
            cron_expression="* * * * *",  # Every minute
            subreddits=["test"],
            max_posts_per_subreddit=1,
        )

        # Mock the download pipeline to avoid actual Reddit API calls
        with patch("scheduler.task_executor.UrlFetcher") as mock_fetcher:
            mock_instance = Mock()
            mock_fetcher.return_value = mock_instance
            mock_instance._get_subreddit_posts.return_value = [
                "https://reddit.com/test"
            ]

            with patch("scheduler.task_executor.utils") as mock_utils:
                mock_utils.clean_url.return_value = "https://reddit.com/test"
                mock_utils.valid_url.return_value = True
                mock_utils.download_post_json.return_value = [
                    {
                        "data": {
                            "children": [{"data": {"title": "Test", "id": "test123"}}]
                        }
                    },
                    {"data": {"children": []}},
                ]
                mock_utils.generate_filename.return_value = "/tmp/test.md"
                mock_utils.resolve_save_dir.return_value = "/tmp"

                with patch("scheduler.task_executor.build_post_content") as mock_build:
                    mock_build.return_value = "# Test Post Content"

                    with patch("builtins.open", mock_open()) as mock_file:
                        # Add task and start scheduler
                        self.scheduler.add_task(task)
                        self.scheduler.start()

                        # Wait for task execution
                        time.sleep(2)

                        # Stop scheduler
                        self.scheduler.stop(timeout_seconds=5)

                        # Check that task was executed
                        final_task = self.scheduler.get_task(task.id)
                        assert final_task is not None
                        assert final_task.last_result is not None

    def test_scheduler_resilience_under_load(self):
        """Test scheduler resilience with multiple tasks and failures."""
        # Create multiple tasks
        tasks = []
        for i in range(5):
            task = ScheduledTask(
                id=f"load_test_{i}",
                name=f"Load Test {i}",
                cron_expression="* * * * *",
                subreddits=[f"test_{i}"],
                max_posts_per_subreddit=1,
            )
            tasks.append(task)
            self.scheduler.add_task(task)

        # Mock some tasks to fail intermittently
        def mock_executor(task):
            import random

            if random.random() < 0.3:  # 30% failure rate
                raise Exception("Simulated failure")
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )

        self.scheduler.set_task_executor(mock_executor)
        self.scheduler.start()

        # Let scheduler run for a few seconds
        time.sleep(3)

        self.scheduler.stop(timeout_seconds=10)

        # Verify scheduler handled the load and failures gracefully
        status = self.scheduler.get_status()
        assert status["running"] is False
        assert status["total_tasks"] == 5


def mock_open(content=""):
    """Mock file open function."""
    from unittest.mock import mock_open as mock_open_orig

    return mock_open_orig(read_data=content)


if __name__ == "__main__":
    pytest.main([__file__])
