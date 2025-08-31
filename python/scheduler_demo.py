#!/usr/bin/env python3
"""
Demonstration script for the Reddit-Markdown Scheduler system.

Shows how to use the scheduled download functionality.
"""

import sys
import time
from datetime import datetime, timedelta
from colored_logger import setup_colored_logging, get_colored_logger

from scheduler import create_task
from scheduler_integration import SchedulerIntegration
from settings import Settings

logger = get_colored_logger(__name__)


def demo_scheduler():
    """Demonstrate the scheduler functionality."""
    setup_colored_logging()

    logger.info("=== Reddit-Markdown Scheduler Demo ===")

    # Load settings
    settings = Settings()
    logger.info("Loaded settings (scheduler enabled: %s)", settings.scheduler_enabled)

    # Create scheduler integration
    integration = SchedulerIntegration(settings)

    try:
        # Start the scheduler
        logger.info("Starting scheduler...")
        if not integration.startup():
            logger.error("Failed to start scheduler")
            return 1

        # Create a demo task
        logger.info("Creating demo scheduled task...")
        demo_task = create_task(
            name="Demo Daily Python Posts",
            cron_expression="*/2 * * * *",  # Every 2 minutes for demo
            subreddits=["r/python"],
            max_posts_per_subreddit=3,
            enabled=True,
        )

        # Add task to scheduler
        integration.scheduler.add_task(demo_task)
        integration.state_manager.save_task(demo_task)

        logger.info("Demo task created: '%s' (ID: %s)", demo_task.name, demo_task.id)
        logger.info("Next run: %s", demo_task.next_run)

        # Show scheduler status
        status = integration.get_status()
        logger.info(
            "Scheduler status: %d total tasks, %d enabled",
            status.get("total_tasks", 0),
            status.get("enabled_tasks", 0),
        )

        # Run for a short time to demonstrate
        logger.info("Running scheduler for 30 seconds...")
        logger.info("The task will execute every 2 minutes (for demo purposes)")
        logger.info(
            "In production, you'd use normal cron expressions like '0 12 * * *' for daily at noon"
        )

        start_time = time.time()
        while time.time() - start_time < 30:
            time.sleep(1)

            # Check if task has run
            current_task = integration.scheduler.get_task(demo_task.id)
            if current_task and current_task.last_result:
                logger.info(
                    "Task last result: %s", current_task.last_result.status.value
                )
                if current_task.last_result.output:
                    logger.info("Task output: %s", current_task.last_result.output)

        # Show download history
        logger.info("Checking download history...")
        history = integration.state_manager.get_download_history(limit=10)
        if history:
            logger.info("Recent downloads:")
            for record in history[:5]:  # Show first 5
                logger.info("  - %s: %s", record.subreddit, record.title[:50])
        else:
            logger.info("No downloads recorded yet")

        # Show statistics
        stats = integration.state_manager.get_statistics()
        logger.info("Database statistics:")
        logger.info("  Total downloads: %d", stats["downloads"]["total"])
        logger.info("  Unique subreddits: %d", stats["downloads"]["unique_subreddits"])

        logger.info("Demo completed successfully!")
        return 0

    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
        return 0

    except Exception as e:
        logger.error("Demo failed: %s", e)
        return 1

    finally:
        # Clean up
        logger.info("Shutting down scheduler...")
        integration.shutdown()


def show_cli_examples():
    """Show examples of using the CLI interface."""
    logger.info("\n=== CLI Interface Examples ===")

    examples = [
        (
            "Add a daily task",
            "python3 scheduler_cli.py add 'Daily Python Posts' '0 12 * * *' 'r/python,r/learnpython' --max-posts 10",
        ),
        ("List all tasks", "python3 scheduler_cli.py list"),
        ("Show task details", "python3 scheduler_cli.py show TASK_ID"),
        ("Start scheduler daemon", "python3 scheduler_cli.py start"),
        ("Show status", "python3 scheduler_cli.py status"),
        ("Show download history", "python3 scheduler_cli.py history --limit 20"),
        ("Show statistics", "python3 scheduler_cli.py stats"),
        ("Validate cron expression", "python3 scheduler_cli.py validate '0 */6 * * *'"),
        ("Test task execution", "python3 scheduler_cli.py test TASK_ID"),
    ]

    for description, command in examples:
        logger.info("  %s:", description)
        logger.info("    %s", command)
        logger.info("")


def show_configuration_example():
    """Show example configuration in settings.json."""
    logger.info("\n=== Configuration Example ===")

    config_example = """
In settings.json:

{
  "scheduler": {
    "enabled": true,
    "check_interval_seconds": 30,
    "database_path": "scheduler_state.db", 
    "cleanup_old_history_days": 90,
    "default_max_posts_per_subreddit": 25,
    "default_retry_count": 3,
    "scheduled_tasks": [
      {
        "name": "Daily Programming News",
        "cron_expression": "0 9 * * *",
        "subreddits": ["r/programming", "r/coding", "r/softwareengineer"],
        "max_posts_per_subreddit": 15,
        "enabled": true
      },
      {
        "name": "Weekly Python Roundup", 
        "cron_expression": "0 10 * * 1",
        "subreddits": ["r/python", "r/learnpython"],
        "max_posts_per_subreddit": 30,
        "enabled": true
      }
    ]
  }
}
    """

    logger.info(config_example)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        setup_colored_logging()
        show_cli_examples()
        show_configuration_example()
        sys.exit(0)

    sys.exit(demo_scheduler())
