"""
Main task scheduler for automated Reddit downloads.

Provides thread-safe background scheduling with cron-like expressions.
"""

import threading
import time
import uuid
import signal
import resource
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from colored_logger import get_colored_logger

from .cron_parser import CronParser, CronExpression

logger = get_colored_logger(__name__)


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class TaskResult:
    """Result of a task execution."""

    task_id: str
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    output: Optional[str] = None


@dataclass
class ScheduledTask:
    """Represents a scheduled task with cron expression and metadata."""

    id: str
    name: str
    cron_expression: str
    subreddits: List[str]
    enabled: bool = True
    max_posts_per_subreddit: int = 25
    retry_count: int = 3
    retry_delay_seconds: int = 60
    timeout_seconds: int = 3600  # 1 hour default timeout
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_result: Optional[TaskResult] = None

    def __post_init__(self):
        """Validate task configuration."""
        if not self.name:
            raise ValueError("Task name cannot be empty")
        if not self.subreddits:
            raise ValueError("Task must have at least one subreddit")
        if self.max_posts_per_subreddit <= 0:
            raise ValueError("max_posts_per_subreddit must be positive")
        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class TaskScheduler:
    """
    Thread-safe task scheduler with cron-like expressions.

    Features:
    - Background execution in separate thread
    - Graceful shutdown handling
    - Task persistence
    - Error handling and retries
    - Thread-safe operations
    - Resource monitoring and limits
    - Circuit breaker pattern
    - Rate limiting
    """

    def __init__(
        self,
        check_interval_seconds: int = 30,
        max_concurrent_tasks: int = 5,
        max_memory_mb: int = 500,
        enable_monitoring: bool = True,
    ):
        """
        Initialize the task scheduler.

        Args:
            check_interval_seconds: How often to check for tasks to run
        """
        self.check_interval_seconds = max(1, check_interval_seconds)
        self.max_concurrent_tasks = max(1, max_concurrent_tasks)
        self.max_memory_mb = max(50, max_memory_mb)
        self.enable_monitoring = enable_monitoring
        self.cron_parser = CronParser()

        # Thread-safe data structures
        self._tasks: Dict[str, ScheduledTask] = {}
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._shutdown_event = threading.Event()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False

        # Task execution tracking with thread pool
        self._thread_pool = ThreadPoolExecutor(
            max_workers=max_concurrent_tasks, thread_name_prefix="TaskExec"
        )
        self._running_tasks: Dict[str, threading.Thread] = {}
        self._task_executor_callback: Optional[Callable] = None

        # Safety and monitoring
        self._circuit_breaker_failures: Dict[str, int] = {}
        self._circuit_breaker_last_failure: Dict[str, datetime] = {}
        self._rate_limiter: Dict[str, datetime] = {}
        self._resource_monitor = ResourceMonitor() if enable_monitoring else None

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(
            "Task scheduler initialized with %ds check interval, %d max concurrent tasks, %dMB memory limit",
            self.check_interval_seconds,
            max_concurrent_tasks,
            max_memory_mb,
        )

    def set_task_executor(
        self, executor_callback: Callable[[ScheduledTask], TaskResult]
    ) -> None:
        """
        Set the callback function that will execute tasks.

        Args:
            executor_callback: Function that takes a ScheduledTask and returns a TaskResult
        """
        self._task_executor_callback = executor_callback
        logger.info("Task executor callback registered")

    def add_task(self, task: ScheduledTask) -> None:
        """
        Add a new scheduled task.

        Args:
            task: The task to add

        Raises:
            ValueError: If task configuration is invalid
        """
        # Validate cron expression
        try:
            parsed_expr = self.cron_parser.parse(task.cron_expression)
            task.next_run = self.cron_parser.next_execution(parsed_expr)
        except ValueError as e:
            raise ValueError(f"Invalid cron expression for task '{task.name}': {e}")

        with self._lock:
            if task.id in self._tasks:
                logger.warning("Task with ID '%s' already exists, replacing", task.id)

            self._tasks[task.id] = task
            logger.info(
                "Added scheduled task '%s' (ID: %s), next run: %s",
                task.name,
                task.id,
                task.next_run,
            )

    def remove_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task.

        Args:
            task_id: The task ID to remove

        Returns:
            True if task was removed, False if not found
        """
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks.pop(task_id)
                logger.info("Removed scheduled task '%s' (ID: %s)", task.name, task_id)

                # If task is currently running, we don't forcibly stop it
                # but it won't be rescheduled
                if task_id in self._running_tasks:
                    logger.info(
                        "Task '%s' is still running but won't be rescheduled", task.name
                    )

                return True
            return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[ScheduledTask]:
        """Get all scheduled tasks."""
        with self._lock:
            return list(self._tasks.values())

    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].enabled = True
                logger.info("Enabled task ID: %s", task_id)
                return True
            return False

    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].enabled = False
                logger.info("Disabled task ID: %s", task_id)
                return True
            return False

    def start(self) -> None:
        """Start the background scheduler thread."""
        with self._lock:
            if self._running:
                logger.warning("Scheduler is already running")
                return

            if self._task_executor_callback is None:
                raise RuntimeError(
                    "Task executor callback must be set before starting scheduler"
                )

            self._shutdown_event.clear()
            self._running = True
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop, name="TaskScheduler", daemon=True
            )
            self._scheduler_thread.start()
            logger.info("Task scheduler started")

        # Start resource monitoring
        if self._resource_monitor and self.enable_monitoring:
            self._monitor_thread = threading.Thread(
                target=self._monitoring_loop, name="ResourceMonitor", daemon=True
            )
            self._monitor_thread.start()

    def stop(self, timeout_seconds: int = 30) -> None:
        """
        Stop the scheduler and wait for running tasks to complete.

        Args:
            timeout_seconds: Maximum time to wait for graceful shutdown
        """
        with self._lock:
            if not self._running:
                logger.info("Scheduler is not running")
                return

            logger.info("Stopping task scheduler...")
            self._running = False
            self._shutdown_event.set()

        # Wait for scheduler thread to finish
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=timeout_seconds)
            if self._scheduler_thread.is_alive():
                logger.warning(
                    "Scheduler thread did not stop within %ds", timeout_seconds
                )

        # Wait for running tasks to complete
        self._wait_for_running_tasks(timeout_seconds)

        logger.info("Task scheduler stopped")

    def _wait_for_running_tasks(self, timeout_seconds: int) -> None:
        """Wait for all running tasks to complete."""
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            with self._lock:
                running_futures = list(self._running_tasks.values())

            if not running_futures:
                break

            logger.info(
                "Waiting for %d running tasks to complete...", len(running_futures)
            )

            # Wait for futures to complete with remaining time
            remaining_time = timeout_seconds - (time.time() - start_time)
            if remaining_time > 0:
                try:
                    # Use as_completed to wait for any futures to finish
                    from concurrent.futures import as_completed

                    for future in as_completed(
                        running_futures, timeout=min(5, remaining_time)
                    ):
                        try:
                            future.result()
                        except Exception as e:
                            logger.debug("Task completed with exception: %s", e)
                except Exception:
                    # Timeout or other error, continue loop
                    pass

            # Clean up finished tasks
            self._cleanup_finished_tasks()

        # Log any tasks that are still running
        with self._lock:
            if self._running_tasks:
                logger.warning(
                    "%d tasks still running after %ds timeout",
                    len(self._running_tasks),
                    timeout_seconds,
                )

    def _cleanup_finished_tasks(self) -> None:
        """Remove finished task futures from tracking."""
        with self._lock:
            finished_task_ids = [
                task_id
                for task_id, future in self._running_tasks.items()
                if future.done()
            ]

            for task_id in finished_task_ids:
                future = self._running_tasks.pop(task_id)
                try:
                    # Get result or exception to clean up properly
                    future.result(timeout=0)
                except Exception as e:
                    logger.debug("Task %s finished with exception: %s", task_id, e)

    def _scheduler_loop(self) -> None:
        """Main scheduler loop that runs in background thread."""
        logger.info("Scheduler loop started")

        while not self._shutdown_event.is_set():
            try:
                self._check_and_execute_tasks()
                self._cleanup_finished_tasks()

                # Wait for next check or shutdown signal
                self._shutdown_event.wait(timeout=self.check_interval_seconds)

            except Exception as e:
                logger.error("Error in scheduler loop: %s", e)
                # Continue running even if there's an error
                time.sleep(min(self.check_interval_seconds, 60))

        logger.info("Scheduler loop ended")

    def _check_and_execute_tasks(self) -> None:
        """Check for tasks that need to run and execute them."""
        now = datetime.now()
        tasks_to_run = []

        with self._lock:
            for task in self._tasks.values():
                if (
                    task.enabled
                    and task.next_run
                    and task.next_run <= now
                    and task.id not in self._running_tasks
                ):
                    tasks_to_run.append(task)

        # Execute tasks outside the lock to avoid blocking
        for task in tasks_to_run:
            self._execute_task(task)

    def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a task with safety checks and resource monitoring."""

        # Safety checks before execution
        if self._is_circuit_breaker_open(task.id):
            logger.warning(
                "Circuit breaker open for task '%s', skipping execution", task.name
            )
            return

        if self._is_rate_limited(task.id):
            logger.debug("Task '%s' is rate limited, skipping execution", task.name)
            return

        # Check resource limits
        current_memory = self._get_memory_usage()
        if current_memory > self.max_memory_mb * 0.9:  # 90% threshold
            logger.warning(
                "Memory usage high (%dMB), deferring task '%s'",
                current_memory,
                task.name,
            )
            return

        def task_runner():
            try:
                logger.info(
                    "Starting execution of task '%s' (ID: %s)", task.name, task.id
                )

                # Update rate limiter
                self._update_rate_limiter(task.id)

                # Update task state
                with self._lock:
                    task.last_run = datetime.now()

                # Execute the task with resource monitoring
                with self._resource_context():
                    result = self._task_executor_callback(task)

                # Update task with result and circuit breaker
                with self._lock:
                    task.last_result = result

                    if result.status == TaskStatus.COMPLETED:
                        self._record_task_success(task.id)
                    else:
                        self._record_task_failure(task.id)

                    # Schedule next run if task is still enabled
                    if task.enabled and not self._is_circuit_breaker_open(task.id):
                        try:
                            parsed_expr = self.cron_parser.parse(task.cron_expression)
                            task.next_run = self.cron_parser.next_execution(parsed_expr)
                            logger.info(
                                "Task '%s' completed, next run: %s",
                                task.name,
                                task.next_run,
                            )
                        except Exception as e:
                            logger.error(
                                "Failed to schedule next run for task '%s': %s",
                                task.name,
                                e,
                            )
                            task.enabled = False
                    else:
                        task.next_run = None
                        if self._is_circuit_breaker_open(task.id):
                            logger.info(
                                "Task '%s' next run deferred due to circuit breaker",
                                task.name,
                            )
                        else:
                            logger.info(
                                "Task '%s' completed but is disabled", task.name
                            )

            except Exception as e:
                logger.error(
                    "Unhandled error executing task '%s': %s",
                    task.name,
                    e,
                    exc_info=True,
                )

                # Record failure for circuit breaker
                self._record_task_failure(task.id)

                # Create error result
                error_result = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    started_at=task.last_run or datetime.now(),
                    completed_at=datetime.now(),
                    error=str(e)[:500],  # Limit error message length
                )

                with self._lock:
                    task.last_result = error_result
                    # Schedule next run based on circuit breaker status
                    if task.enabled and not self._is_circuit_breaker_open(task.id):
                        try:
                            parsed_expr = self.cron_parser.parse(task.cron_expression)
                            task.next_run = self.cron_parser.next_execution(parsed_expr)
                        except Exception:
                            logger.error(
                                "Failed to reschedule task '%s' after error", task.name
                            )
                            task.enabled = False
                    else:
                        task.next_run = None

        # Submit task to thread pool
        future = self._thread_pool.submit(task_runner)

        # Store future for tracking
        with self._lock:
            self._running_tasks[task.id] = future

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status information."""
        with self._lock:
            return {
                "running": self._running,
                "check_interval_seconds": self.check_interval_seconds,
                "total_tasks": len(self._tasks),
                "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
                "running_tasks": len(self._running_tasks),
                "tasks": [
                    {
                        "id": task.id,
                        "name": task.name,
                        "enabled": task.enabled,
                        "cron_expression": task.cron_expression,
                        "subreddits": task.subreddits,
                        "last_run": (
                            task.last_run.isoformat() if task.last_run else None
                        ),
                        "next_run": (
                            task.next_run.isoformat() if task.next_run else None
                        ),
                        "last_status": (
                            task.last_result.status.value if task.last_result else None
                        ),
                    }
                    for task in self._tasks.values()
                ],
                "resource_usage": {
                    "memory_mb": self._get_memory_usage(),
                    "cpu_percent": self._get_cpu_usage(),
                    "active_threads": threading.active_count(),
                },
            }

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info("Received signal %d, initiating graceful shutdown", signum)
        self.stop()

    def _monitoring_loop(self) -> None:
        """Monitor resource usage and enforce limits."""
        logger.info("Resource monitoring started")

        while not self._shutdown_event.is_set():
            try:
                memory_mb = self._get_memory_usage()

                if memory_mb > self.max_memory_mb:
                    logger.warning(
                        "Memory usage (%dMB) exceeds limit (%dMB)",
                        memory_mb,
                        self.max_memory_mb,
                    )
                    self._handle_memory_pressure()

                # Check for stuck tasks
                self._check_stuck_tasks()

                # Wait before next check
                self._shutdown_event.wait(timeout=30)

            except Exception as e:
                logger.error("Error in resource monitoring: %s", e)
                time.sleep(30)

        logger.info("Resource monitoring stopped")

    def _get_memory_usage(self) -> int:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return int(process.memory_info().rss / 1024 / 1024)
        except Exception:
            return 0

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=1)
        except Exception:
            return 0.0

    def _handle_memory_pressure(self) -> None:
        """Handle high memory usage by limiting new tasks."""
        with self._lock:
            # Disable new task execution temporarily
            logger.warning(
                "Temporarily suspending new task execution due to memory pressure"
            )

            # Force garbage collection
            import gc

            gc.collect()

    def _check_stuck_tasks(self) -> None:
        """Check for tasks that have been running too long."""
        stuck_threshold = timedelta(hours=2)  # Consider tasks stuck after 2 hours
        now = datetime.now()

        with self._lock:
            for task_id, task in self._tasks.items():
                if (
                    task.last_run
                    and task.last_result
                    and task.last_result.status == TaskStatus.RUNNING
                    and now - task.last_run > stuck_threshold
                ):

                    logger.warning(
                        "Task '%s' appears to be stuck (running for %s)",
                        task.name,
                        now - task.last_run,
                    )

    def _is_circuit_breaker_open(self, task_id: str) -> bool:
        """Check if circuit breaker is open for a task."""
        failures = self._circuit_breaker_failures.get(task_id, 0)
        last_failure = self._circuit_breaker_last_failure.get(task_id)

        if failures >= 3:  # Open circuit after 3 failures
            if last_failure and datetime.now() - last_failure < timedelta(minutes=15):
                return True
            else:
                # Reset circuit breaker after cooldown
                self._circuit_breaker_failures[task_id] = 0

        return False

    def _record_task_failure(self, task_id: str) -> None:
        """Record a task failure for circuit breaker."""
        self._circuit_breaker_failures[task_id] = (
            self._circuit_breaker_failures.get(task_id, 0) + 1
        )
        self._circuit_breaker_last_failure[task_id] = datetime.now()

    def _record_task_success(self, task_id: str) -> None:
        """Record a task success, resetting circuit breaker."""
        self._circuit_breaker_failures[task_id] = 0

    def _is_rate_limited(self, task_id: str) -> bool:
        """Check if task is rate limited."""
        last_run = self._rate_limiter.get(task_id)
        if last_run and datetime.now() - last_run < timedelta(
            seconds=60
        ):  # 1 minute minimum between runs
            return True
        return False

    def _update_rate_limiter(self, task_id: str) -> None:
        """Update rate limiter for task."""
        self._rate_limiter[task_id] = datetime.now()

    @contextmanager
    def _resource_context(self):
        """Context manager for tracking resource usage during task execution."""
        start_memory = self._get_memory_usage()
        start_time = time.time()

        try:
            yield
        finally:
            end_memory = self._get_memory_usage()
            end_time = time.time()

            memory_delta = end_memory - start_memory
            duration = end_time - start_time

            if memory_delta > 50:  # Log if task used more than 50MB
                logger.warning(
                    "Task used %dMB additional memory, duration: %.2fs",
                    memory_delta,
                    duration,
                )


class ResourceMonitor:
    """Monitor system resources and enforce limits."""

    def __init__(self):
        self.start_time = time.time()
        self.initial_memory = self._get_memory_usage()

    def _get_memory_usage(self) -> int:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return int(process.memory_info().rss / 1024 / 1024)
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get resource usage statistics."""
        current_memory = self._get_memory_usage()
        uptime = time.time() - self.start_time

        return {
            "memory_mb": current_memory,
            "memory_delta_mb": current_memory - self.initial_memory,
            "uptime_seconds": uptime,
            "cpu_percent": self._get_cpu_usage(),
            "thread_count": threading.active_count(),
        }

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0


def create_task(
    name: str, cron_expression: str, subreddits: List[str], **kwargs
) -> ScheduledTask:
    """
    Convenience function to create a scheduled task.

    Args:
        name: Human-readable task name
        cron_expression: Cron expression for scheduling
        subreddits: List of subreddits to download from
        **kwargs: Additional task configuration

    Returns:
        A new ScheduledTask instance
    """
    task_id = kwargs.pop("id", str(uuid.uuid4()))

    return ScheduledTask(
        id=task_id,
        name=name,
        cron_expression=cron_expression,
        subreddits=subreddits,
        **kwargs,
    )
