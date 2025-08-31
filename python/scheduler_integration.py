"""
Scheduler integration with the main Reddit-Markdown application.

Provides seamless integration between the scheduler system and existing
download functionality.
"""

import threading
import atexit
from typing import Optional
from colored_logger import get_colored_logger

from scheduler import TaskScheduler, StateManager, TaskExecutor
from settings import Settings

logger = get_colored_logger(__name__)


class SchedulerIntegration:
    """
    Manages integration between scheduler and main application.

    Features:
    - Automatic startup when enabled in settings
    - Graceful shutdown on application exit
    - Thread-safe operation alongside normal downloads
    - Persistent state management
    """

    _instance: Optional["SchedulerIntegration"] = None
    _lock = threading.Lock()

    def __new__(cls, settings: Optional[Settings] = None):
        """Singleton pattern to ensure only one scheduler instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the scheduler integration."""
        if getattr(self, "_initialized", False):
            return

        self.settings = settings or Settings()
        self.state_manager: Optional[StateManager] = None
        self.scheduler: Optional[TaskScheduler] = None
        self.task_executor: Optional[TaskExecutor] = None
        self._running = False
        self._initialized = True

        # Register shutdown handler
        atexit.register(self.shutdown)

        logger.info("Scheduler integration initialized")

    def startup(self) -> bool:
        """
        Start the scheduler if enabled in settings.

        Returns:
            True if scheduler was started, False otherwise
        """
        if not self.settings.scheduler_enabled:
            logger.info("Scheduler disabled in settings")
            return False

        if self._running:
            logger.warning("Scheduler already running")
            return True

        try:
            # Initialize components
            self.state_manager = StateManager(self.settings.scheduler_database_path)
            self.scheduler = TaskScheduler(
                self.settings.scheduler_check_interval_seconds
            )
            self.task_executor = TaskExecutor(self.state_manager, self.settings)

            # Set up scheduler with task executor
            self.scheduler.set_task_executor(self.task_executor.execute_task)

            # Load existing tasks from database
            tasks = self.state_manager.load_all_tasks()
            for task in tasks:
                self.scheduler.add_task(task)

            # Load any tasks defined in settings
            for task_config in self.settings.scheduler_scheduled_tasks:
                self._load_task_from_config(task_config)

            # Start the scheduler
            self.scheduler.start()
            self._running = True

            logger.info("Scheduler started successfully with %d tasks", len(tasks))

            # Schedule periodic cleanup
            self._schedule_maintenance()

            return True

        except Exception as e:
            logger.error("Failed to start scheduler: %s", e)
            self.shutdown()
            return False

    def shutdown(self) -> None:
        """Gracefully shutdown the scheduler."""
        if not self._running:
            return

        try:
            logger.info("Shutting down scheduler...")

            if self.scheduler:
                self.scheduler.stop(timeout_seconds=30)

            if self.state_manager:
                self.state_manager.close()

            self._running = False
            logger.info("Scheduler shutdown complete")

        except Exception as e:
            logger.error("Error during scheduler shutdown: %s", e)

    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._running and (self.scheduler is not None)

    def get_status(self) -> dict:
        """Get scheduler status information."""
        if not self._running or not self.scheduler:
            return {"running": False, "error": "Scheduler not initialized"}

        try:
            status = self.scheduler.get_status()

            # Add integration-specific information
            status["integration"] = {
                "settings_enabled": self.settings.scheduler_enabled,
                "database_path": self.settings.scheduler_database_path,
                "check_interval": self.settings.scheduler_check_interval_seconds,
            }

            # Add database statistics if available
            if self.state_manager:
                stats = self.state_manager.get_statistics()
                status["database_stats"] = stats

            return status

        except Exception as e:
            logger.error("Error getting scheduler status: %s", e)
            return {"running": False, "error": str(e)}

    def add_task_from_config(self, config: dict) -> bool:
        """
        Add a task from configuration dictionary.

        Args:
            config: Task configuration dictionary

        Returns:
            True if task was added successfully
        """
        if not self._running or not self.scheduler or not self.state_manager:
            logger.error("Scheduler not running, cannot add task")
            return False

        return self._load_task_from_config(config)

    def _load_task_from_config(self, config: dict) -> bool:
        """Load a task from configuration dictionary."""
        try:
            from scheduler import create_task

            # Extract configuration
            name = config.get("name")
            cron_expression = config.get("cron_expression")
            subreddits = config.get("subreddits", [])

            if not all([name, cron_expression, subreddits]):
                logger.error("Invalid task configuration: missing required fields")
                return False

            # Create task with defaults from settings
            task = create_task(
                name=name,
                cron_expression=cron_expression,
                subreddits=subreddits,
                id=config.get("id"),
                enabled=config.get("enabled", True),
                max_posts_per_subreddit=config.get(
                    "max_posts_per_subreddit",
                    self.settings.scheduler_default_max_posts_per_subreddit,
                ),
                retry_count=config.get(
                    "retry_count", self.settings.scheduler_default_retry_count
                ),
                retry_delay_seconds=config.get(
                    "retry_delay_seconds",
                    self.settings.scheduler_default_retry_delay_seconds,
                ),
                timeout_seconds=config.get(
                    "timeout_seconds", self.settings.scheduler_default_timeout_seconds
                ),
            )

            # Add to scheduler and save to database
            self.scheduler.add_task(task)
            self.state_manager.save_task(task)

            logger.info("Loaded scheduled task from config: %s", task.name)
            return True

        except Exception as e:
            logger.error("Failed to load task from config: %s", e)
            return False

    def _schedule_maintenance(self) -> None:
        """Schedule periodic maintenance tasks."""
        if not self.state_manager:
            return

        def maintenance():
            try:
                # Clean up old history
                deleted = self.state_manager.cleanup_old_history(
                    self.settings.scheduler_cleanup_old_history_days
                )
                if deleted > 0:
                    logger.info("Cleaned up %d old download records", deleted)

            except Exception as e:
                logger.error("Error during maintenance: %s", e)

        # Schedule maintenance to run periodically (every 24 hours)
        import threading

        timer = threading.Timer(24 * 3600, maintenance)  # 24 hours
        timer.daemon = True
        timer.start()


def get_scheduler() -> Optional[SchedulerIntegration]:
    """Get the global scheduler integration instance."""
    return SchedulerIntegration._instance


def ensure_scheduler_started(settings: Optional[Settings] = None) -> bool:
    """
    Ensure the scheduler is started if enabled in settings.

    Args:
        settings: Settings object (will create new one if not provided)

    Returns:
        True if scheduler is running or was started successfully
    """
    integration = SchedulerIntegration(settings)

    if integration.is_running():
        return True

    return integration.startup()


def stop_scheduler() -> None:
    """Stop the global scheduler instance if running."""
    integration = get_scheduler()
    if integration:
        integration.shutdown()
