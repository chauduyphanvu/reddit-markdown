"""
Scheduler module for automated Reddit downloads.

This module provides:
- Cron-like scheduling expressions
- Background task execution
- Persistent state management
- Duplicate detection
- Error handling and recovery
"""

from .cron_parser import CronParser, CronExpression
from .task_scheduler import TaskScheduler, ScheduledTask, create_task
from .state_manager import StateManager
from .task_executor import TaskExecutor

__all__ = [
    "CronParser",
    "CronExpression",
    "TaskScheduler",
    "ScheduledTask",
    "StateManager",
    "TaskExecutor",
    "create_task",
]
