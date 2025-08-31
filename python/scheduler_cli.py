"""
CLI interface for scheduler management.

Provides command-line tools for:
- Creating and managing scheduled tasks
- Starting/stopping the scheduler  
- Viewing task status and history
- Managing scheduler configuration
"""

import argparse
import sys
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from colored_logger import get_colored_logger, setup_colored_logging

from scheduler import TaskScheduler, StateManager, TaskExecutor, create_task
from scheduler.cron_parser import CronParser
from settings import Settings

logger = get_colored_logger(__name__)


class SchedulerCLI:
    """Command-line interface for scheduler management."""

    def __init__(self):
        """Initialize the scheduler CLI."""
        self.settings = Settings()
        self.state_manager = StateManager(self.settings.scheduler_database_path)
        self.scheduler = TaskScheduler(self.settings.scheduler_check_interval_seconds)
        self.task_executor = TaskExecutor(self.state_manager, self.settings)
        self.cron_parser = CronParser()

        # Set up scheduler with task executor
        self.scheduler.set_task_executor(self.task_executor.execute_task)

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser for scheduler commands."""
        parser = argparse.ArgumentParser(
            prog="scheduler", description="Manage scheduled Reddit downloads"
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Add task command
        add_parser = subparsers.add_parser("add", help="Add a new scheduled task")
        add_parser.add_argument("name", help="Task name")
        add_parser.add_argument("cron", help="Cron expression (e.g., '0 12 * * *')")
        add_parser.add_argument(
            "subreddits",
            help="Comma-separated subreddits (e.g., 'r/python,r/programming')",
        )
        add_parser.add_argument(
            "--max-posts",
            type=int,
            default=self.settings.scheduler_default_max_posts_per_subreddit,
            help="Maximum posts per subreddit",
        )
        add_parser.add_argument(
            "--enabled",
            action="store_true",
            default=True,
            help="Enable task immediately",
        )

        # List tasks command
        list_parser = subparsers.add_parser("list", help="List all scheduled tasks")
        list_parser.add_argument(
            "--status",
            choices=["all", "enabled", "disabled"],
            default="all",
            help="Filter by status",
        )

        # Show task details command
        show_parser = subparsers.add_parser("show", help="Show task details")
        show_parser.add_argument("task_id", help="Task ID to show")

        # Enable/disable commands
        enable_parser = subparsers.add_parser("enable", help="Enable a task")
        enable_parser.add_argument("task_id", help="Task ID to enable")

        disable_parser = subparsers.add_parser("disable", help="Disable a task")
        disable_parser.add_argument("task_id", help="Task ID to disable")

        # Remove task command
        remove_parser = subparsers.add_parser("remove", help="Remove a task")
        remove_parser.add_argument("task_id", help="Task ID to remove")
        remove_parser.add_argument(
            "--force", action="store_true", help="Force removal without confirmation"
        )

        # Start/stop scheduler commands
        subparsers.add_parser("start", help="Start the scheduler daemon")
        subparsers.add_parser("stop", help="Stop the scheduler daemon")
        subparsers.add_parser("status", help="Show scheduler status")

        # History and statistics commands
        history_parser = subparsers.add_parser("history", help="Show download history")
        history_parser.add_argument("--task-id", help="Filter by task ID")
        history_parser.add_argument("--subreddit", help="Filter by subreddit")
        history_parser.add_argument(
            "--limit", type=int, default=50, help="Number of records to show"
        )

        subparsers.add_parser("stats", help="Show scheduler statistics")

        # Validate cron expression command
        validate_parser = subparsers.add_parser(
            "validate", help="Validate cron expression"
        )
        validate_parser.add_argument("expression", help="Cron expression to validate")

        # Test task command
        test_parser = subparsers.add_parser("test", help="Test a task execution")
        test_parser.add_argument("task_id", help="Task ID to test")

        return parser

    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the scheduler CLI with given arguments."""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)

        if not parsed_args.command:
            parser.print_help()
            return 0

        try:
            # Load existing tasks from database
            tasks = self.state_manager.load_all_tasks()
            for task in tasks:
                self.scheduler.add_task(task)

            # Execute the requested command
            return self._execute_command(parsed_args)

        except Exception as e:
            logger.error("Command failed: %s", e)
            return 1
        finally:
            self.state_manager.close()

    def _execute_command(self, args: argparse.Namespace) -> int:
        """Execute the requested command."""
        command_map = {
            "add": self._cmd_add,
            "list": self._cmd_list,
            "show": self._cmd_show,
            "enable": self._cmd_enable,
            "disable": self._cmd_disable,
            "remove": self._cmd_remove,
            "start": self._cmd_start,
            "stop": self._cmd_stop,
            "status": self._cmd_status,
            "history": self._cmd_history,
            "stats": self._cmd_stats,
            "validate": self._cmd_validate,
            "test": self._cmd_test,
        }

        handler = command_map.get(args.command)
        if not handler:
            logger.error("Unknown command: %s", args.command)
            return 1

        return handler(args)

    def _cmd_add(self, args: argparse.Namespace) -> int:
        """Add a new scheduled task."""
        try:
            # Validate cron expression
            if not self.cron_parser.validate_expression(args.cron):
                logger.error("Invalid cron expression: %s", args.cron)
                return 1

            # Parse subreddits
            subreddits = [s.strip() for s in args.subreddits.split(",") if s.strip()]
            if not subreddits:
                logger.error("No subreddits specified")
                return 1

            # Create the task
            task = create_task(
                name=args.name,
                cron_expression=args.cron,
                subreddits=subreddits,
                max_posts_per_subreddit=args.max_posts,
                enabled=args.enabled,
            )

            # Add to scheduler and save to database
            self.scheduler.add_task(task)
            self.state_manager.save_task(task)

            logger.info("Added scheduled task '%s' (ID: %s)", task.name, task.id)
            logger.info("Next run: %s", task.next_run)
            return 0

        except Exception as e:
            logger.error("Failed to add task: %s", e)
            return 1

    def _cmd_list(self, args: argparse.Namespace) -> int:
        """List scheduled tasks."""
        tasks = self.scheduler.get_all_tasks()

        if not tasks:
            logger.info("No scheduled tasks found")
            return 0

        # Filter by status if requested
        if args.status == "enabled":
            tasks = [t for t in tasks if t.enabled]
        elif args.status == "disabled":
            tasks = [t for t in tasks if not t.enabled]

        print(
            f"\n{'ID':<12} {'Name':<20} {'Status':<10} {'Schedule':<15} {'Next Run':<20} {'Subreddits'}"
        )
        print("-" * 100)

        for task in tasks:
            status = "Enabled" if task.enabled else "Disabled"
            next_run = (
                task.next_run.strftime("%Y-%m-%d %H:%M") if task.next_run else "N/A"
            )
            subreddits = ", ".join(task.subreddits[:3]) + (
                "..." if len(task.subreddits) > 3 else ""
            )

            print(
                f"{task.id[:12]:<12} {task.name[:20]:<20} {status:<10} {task.cron_expression:<15} {next_run:<20} {subreddits}"
            )

        return 0

    def _cmd_show(self, args: argparse.Namespace) -> int:
        """Show detailed information about a task."""
        task = self.scheduler.get_task(args.task_id)
        if not task:
            logger.error("Task not found: %s", args.task_id)
            return 1

        print(f"\nTask Details:")
        print(f"  ID: {task.id}")
        print(f"  Name: {task.name}")
        print(f"  Status: {'Enabled' if task.enabled else 'Disabled'}")
        print(f"  Cron Expression: {task.cron_expression}")
        print(f"  Subreddits: {', '.join(task.subreddits)}")
        print(f"  Max Posts per Subreddit: {task.max_posts_per_subreddit}")
        print(f"  Retry Count: {task.retry_count}")
        print(f"  Timeout: {task.timeout_seconds}s")
        print(f"  Created: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(
            f"  Last Run: {task.last_run.strftime('%Y-%m-%d %H:%M:%S') if task.last_run else 'Never'}"
        )
        print(
            f"  Next Run: {task.next_run.strftime('%Y-%m-%d %H:%M:%S') if task.next_run else 'N/A'}"
        )

        if task.last_result:
            print(f"  Last Result:")
            print(f"    Status: {task.last_result.status.value}")
            print(
                f"    Started: {task.last_result.started_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            if task.last_result.completed_at:
                print(
                    f"    Completed: {task.last_result.completed_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            if task.last_result.output:
                print(f"    Output: {task.last_result.output}")
            if task.last_result.error:
                print(f"    Error: {task.last_result.error}")

        return 0

    def _cmd_enable(self, args: argparse.Namespace) -> int:
        """Enable a task."""
        if self.scheduler.enable_task(args.task_id):
            task = self.scheduler.get_task(args.task_id)
            self.state_manager.save_task(task)
            logger.info("Task enabled: %s", args.task_id)
            return 0
        else:
            logger.error("Task not found: %s", args.task_id)
            return 1

    def _cmd_disable(self, args: argparse.Namespace) -> int:
        """Disable a task."""
        if self.scheduler.disable_task(args.task_id):
            task = self.scheduler.get_task(args.task_id)
            self.state_manager.save_task(task)
            logger.info("Task disabled: %s", args.task_id)
            return 0
        else:
            logger.error("Task not found: %s", args.task_id)
            return 1

    def _cmd_remove(self, args: argparse.Namespace) -> int:
        """Remove a task."""
        task = self.scheduler.get_task(args.task_id)
        if not task:
            logger.error("Task not found: %s", args.task_id)
            return 1

        if not args.force:
            response = input(f"Remove task '{task.name}' (ID: {args.task_id})? [y/N]: ")
            if response.lower() not in ("y", "yes"):
                logger.info("Cancelled")
                return 0

        self.scheduler.remove_task(args.task_id)
        self.state_manager.delete_task(args.task_id)
        logger.info("Task removed: %s", args.task_id)
        return 0

    def _cmd_start(self, args: argparse.Namespace) -> int:
        """Start the scheduler daemon."""
        if not self.settings.scheduler_enabled:
            logger.warning("Scheduler is disabled in settings.json")
            logger.info("Set 'scheduler.enabled' to true to enable the scheduler")
            return 1

        try:
            logger.info("Starting scheduler daemon...")
            self.scheduler.start()

            # Keep running until interrupted
            logger.info("Scheduler running. Press Ctrl+C to stop.")
            try:
                while True:
                    import time

                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Stopping scheduler...")
                self.scheduler.stop()
                logger.info("Scheduler stopped")

            return 0

        except Exception as e:
            logger.error("Failed to start scheduler: %s", e)
            return 1

    def _cmd_stop(self, args: argparse.Namespace) -> int:
        """Stop the scheduler daemon."""
        # This would typically send a signal to a running daemon
        logger.info("Stop command would signal running scheduler daemon")
        logger.info("For now, use Ctrl+C to stop the scheduler")
        return 0

    def _cmd_status(self, args: argparse.Namespace) -> int:
        """Show scheduler status."""
        status = self.scheduler.get_status()

        print(f"\nScheduler Status:")
        print(f"  Running: {'Yes' if status['running'] else 'No'}")
        print(f"  Check Interval: {status['check_interval_seconds']}s")
        print(f"  Total Tasks: {status['total_tasks']}")
        print(f"  Enabled Tasks: {status['enabled_tasks']}")
        print(f"  Running Tasks: {status['running_tasks']}")

        # Show database statistics
        stats = self.state_manager.get_statistics()
        print(f"\nDatabase Statistics:")
        print(f"  Total Downloads: {stats['downloads']['total']}")
        print(f"  Unique Subreddits: {stats['downloads']['unique_subreddits']}")
        print(f"  Recent Downloads (7 days): {stats['downloads']['recent_7_days']}")
        print(f"  Database Size: {stats['database']['size_bytes']} bytes")

        return 0

    def _cmd_history(self, args: argparse.Namespace) -> int:
        """Show download history."""
        history = self.state_manager.get_download_history(
            task_id=args.task_id, subreddit=args.subreddit, limit=args.limit
        )

        if not history:
            logger.info("No download history found")
            return 0

        print(
            f"\n{'Downloaded':<20} {'Subreddit':<15} {'Post ID':<12} {'Title':<40} {'Task'}"
        )
        print("-" * 110)

        for record in history:
            downloaded_at = record.downloaded_at.strftime("%Y-%m-%d %H:%M:%S")
            title = (
                record.title[:37] + "..." if len(record.title) > 40 else record.title
            )
            task_id = record.task_id[:8] if record.task_id else "Manual"

            print(
                f"{downloaded_at:<20} {record.subreddit:<15} {record.post_id[:12]:<12} {title:<40} {task_id}"
            )

        return 0

    def _cmd_stats(self, args: argparse.Namespace) -> int:
        """Show detailed statistics."""
        stats = self.state_manager.get_statistics()

        print("\nScheduler Statistics:")
        print(
            f"  Tasks: {stats['tasks']['total']} total, {stats['tasks']['enabled']} enabled"
        )
        print(f"  Oldest Task: {stats['tasks']['oldest_task'] or 'N/A'}")
        print(f"  Last Execution: {stats['tasks']['last_execution'] or 'N/A'}")

        print("\nDownload Statistics:")
        print(f"  Total Downloads: {stats['downloads']['total']}")
        print(f"  Unique Posts: {stats['downloads']['unique_posts']}")
        print(f"  Unique Subreddits: {stats['downloads']['unique_subreddits']}")
        print(f"  Recent Downloads (7 days): {stats['downloads']['recent_7_days']}")
        print(f"  First Download: {stats['downloads']['first_download'] or 'N/A'}")
        print(f"  Last Download: {stats['downloads']['last_download'] or 'N/A'}")

        return 0

    def _cmd_validate(self, args: argparse.Namespace) -> int:
        """Validate a cron expression."""
        if self.cron_parser.validate_expression(args.expression):
            try:
                parsed = self.cron_parser.parse(args.expression)
                next_run = self.cron_parser.next_execution(parsed)

                logger.info("Valid cron expression: %s", args.expression)
                logger.info(
                    "Next execution: %s", next_run.strftime("%Y-%m-%d %H:%M:%S")
                )
                return 0
            except Exception as e:
                logger.error("Error calculating next execution: %s", e)
                return 1
        else:
            logger.error("Invalid cron expression: %s", args.expression)
            return 1

    def _cmd_test(self, args: argparse.Namespace) -> int:
        """Test a task execution."""
        task = self.scheduler.get_task(args.task_id)
        if not task:
            logger.error("Task not found: %s", args.task_id)
            return 1

        logger.info("Testing task execution: %s", task.name)
        result = self.task_executor.execute_task(task)

        print(f"\nTest Result:")
        print(f"  Status: {result.status.value}")
        print(f"  Started: {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if result.completed_at:
            print(f"  Completed: {result.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            duration = (result.completed_at - result.started_at).total_seconds()
            print(f"  Duration: {duration:.2f}s")
        if result.output:
            print(f"  Output: {result.output}")
        if result.error:
            print(f"  Error: {result.error}")

        return 0 if result.status.value == "completed" else 1


def main():
    """Main entry point for scheduler CLI."""
    setup_colored_logging()
    cli = SchedulerCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
