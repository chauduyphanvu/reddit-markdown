"""
State management for scheduler persistence and duplicate detection.

Handles:
- Task configuration persistence
- Download history tracking  
- Duplicate post detection
- State recovery on startup
"""

import json
import os
import sqlite3
import threading
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import asdict, dataclass
from colored_logger import get_colored_logger

from .task_scheduler import ScheduledTask, TaskResult, TaskStatus

logger = get_colored_logger(__name__)


@dataclass
class DownloadRecord:
    """Record of a downloaded post."""

    post_id: str
    post_url: str
    subreddit: str
    title: str
    author: str
    downloaded_at: datetime
    file_path: str
    task_id: Optional[str] = None


class StateManager:
    """
    Manages persistent state for the scheduler.

    Features:
    - SQLite database for reliable storage
    - Thread-safe operations
    - Automatic schema migrations
    - Duplicate detection
    - History cleanup
    """

    def __init__(
        self,
        db_path: str = "scheduler_state.db",
        pool_size: int = 5,
        enable_wal: bool = True,
        backup_enabled: bool = True,
    ):
        """
        Initialize the state manager.

        Args:
            db_path: Path to SQLite database file
            pool_size: Size of connection pool
            enable_wal: Whether to enable WAL mode for better concurrency
            backup_enabled: Whether to enable automatic backups
        """
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self.enable_wal = enable_wal
        self.backup_enabled = backup_enabled
        self._lock = threading.Lock()
        self._connection_cache = {}

        # Initialize connection pool
        import queue

        self._connection_pool = queue.Queue(maxsize=pool_size)

        # Pre-populate the connection pool
        for _ in range(pool_size):
            self._connection_pool.put(self._create_connection())

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_database()

        logger.info(
            "State manager initialized with database: %s (pool_size=%d, wal=%s, backup=%s)",
            self.db_path,
            pool_size,
            enable_wal,
            backup_enabled,
        )

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimal settings."""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable column access by name

        if self.enable_wal:
            conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/performance
        conn.execute("PRAGMA temp_store=MEMORY")  # Store temp data in memory
        conn.execute("PRAGMA cache_size=10000")  # Increase cache size

        return conn

    def _check_database_integrity(self, conn: sqlite3.Connection) -> bool:
        """Check database integrity."""
        try:
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            return result and result[0] == "ok"
        except Exception as e:
            logger.error("Database integrity check failed: %s", e)
            return False

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection from the pool."""
        try:
            # Try to get a connection from the pool with a timeout
            conn = self._connection_pool.get(timeout=5.0)
            return conn
        except:
            # If pool is empty, create a new connection
            logger.warning("Connection pool exhausted, creating new connection")
            return self._create_connection()

    def _return_connection(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool."""
        try:
            self._connection_pool.put_nowait(conn)
        except:
            # Pool is full, close the connection
            conn.close()

    def _init_database(self) -> None:
        """Initialize the database schema."""
        with self._lock:
            conn = self._get_connection()
            try:
                # Create tasks table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scheduled_tasks (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        cron_expression TEXT NOT NULL,
                        subreddits TEXT NOT NULL,  -- JSON array
                        enabled INTEGER NOT NULL DEFAULT 1,
                        max_posts_per_subreddit INTEGER NOT NULL DEFAULT 25,
                        retry_count INTEGER NOT NULL DEFAULT 3,
                        retry_delay_seconds INTEGER NOT NULL DEFAULT 60,
                        timeout_seconds INTEGER NOT NULL DEFAULT 3600,
                        created_at TEXT NOT NULL,
                        last_run TEXT,
                        next_run TEXT,
                        last_result TEXT,  -- JSON
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create download history table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS download_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        post_id TEXT NOT NULL,
                        post_url TEXT NOT NULL,
                        subreddit TEXT NOT NULL,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        downloaded_at TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        task_id TEXT,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (task_id) REFERENCES scheduled_tasks (id) ON DELETE SET NULL
                    )
                """
                )

                # Create indexes for performance
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_download_history_post_id 
                    ON download_history (post_id)
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_download_history_subreddit 
                    ON download_history (subreddit, downloaded_at)
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_download_history_task_id 
                    ON download_history (task_id, downloaded_at)
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run 
                    ON scheduled_tasks (next_run, enabled)
                """
                )

                conn.commit()
                logger.info("Database schema initialized")
            finally:
                self._return_connection(conn)

    def save_task(self, task: ScheduledTask) -> None:
        """Save or update a scheduled task."""
        with self._lock:
            conn = self._get_connection()

            # Convert task to database format
            last_result_json = None
            if task.last_result:
                result_dict = asdict(task.last_result)
                # Convert enum to string for JSON serialization
                result_dict["status"] = task.last_result.status.value
                # Convert datetime objects to ISO format strings
                if result_dict["started_at"]:
                    result_dict["started_at"] = result_dict["started_at"].isoformat()
                if result_dict["completed_at"]:
                    result_dict["completed_at"] = result_dict[
                        "completed_at"
                    ].isoformat()
                last_result_json = json.dumps(result_dict)

            task_data = {
                "id": task.id,
                "name": task.name,
                "cron_expression": task.cron_expression,
                "subreddits": json.dumps(task.subreddits),
                "enabled": 1 if task.enabled else 0,
                "max_posts_per_subreddit": task.max_posts_per_subreddit,
                "retry_count": task.retry_count,
                "retry_delay_seconds": task.retry_delay_seconds,
                "timeout_seconds": task.timeout_seconds,
                "created_at": task.created_at.isoformat(),
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "last_result": last_result_json,
                "updated_at": datetime.now().isoformat(),
            }

            # Use INSERT OR REPLACE for upsert functionality
            conn.execute(
                """
                INSERT OR REPLACE INTO scheduled_tasks 
                (id, name, cron_expression, subreddits, enabled, max_posts_per_subreddit,
                 retry_count, retry_delay_seconds, timeout_seconds, created_at, 
                 last_run, next_run, last_result, updated_at)
                VALUES (:id, :name, :cron_expression, :subreddits, :enabled, :max_posts_per_subreddit,
                        :retry_count, :retry_delay_seconds, :timeout_seconds, :created_at,
                        :last_run, :next_run, :last_result, :updated_at)
            """,
                task_data,
            )

            conn.commit()
            logger.debug("Saved task '%s' to database", task.name)

    def load_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Load a task from the database."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_task(row)

    def load_all_tasks(self) -> List[ScheduledTask]:
        """Load all tasks from the database."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute("SELECT * FROM scheduled_tasks ORDER BY created_at")
            rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]

    def delete_task(self, task_id: str) -> bool:
        """Delete a task from the database."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                "DELETE FROM scheduled_tasks WHERE id = ?", (task_id,)
            )
            conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info("Deleted task '%s' from database", task_id)
            return deleted

    def _row_to_task(self, row: sqlite3.Row) -> ScheduledTask:
        """Convert a database row to a ScheduledTask object."""
        # Parse JSON fields
        subreddits = json.loads(row["subreddits"])
        last_result = None
        if row["last_result"]:
            result_data = json.loads(row["last_result"])
            # Convert status back to enum
            result_data["status"] = TaskStatus(result_data["status"])
            # Convert datetime strings back to datetime objects
            result_data["started_at"] = datetime.fromisoformat(
                result_data["started_at"]
            )
            if result_data["completed_at"]:
                result_data["completed_at"] = datetime.fromisoformat(
                    result_data["completed_at"]
                )
            last_result = TaskResult(**result_data)

        return ScheduledTask(
            id=row["id"],
            name=row["name"],
            cron_expression=row["cron_expression"],
            subreddits=subreddits,
            enabled=bool(row["enabled"]),
            max_posts_per_subreddit=row["max_posts_per_subreddit"],
            retry_count=row["retry_count"],
            retry_delay_seconds=row["retry_delay_seconds"],
            timeout_seconds=row["timeout_seconds"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_run=(
                datetime.fromisoformat(row["last_run"]) if row["last_run"] else None
            ),
            next_run=(
                datetime.fromisoformat(row["next_run"]) if row["next_run"] else None
            ),
            last_result=last_result,
        )

    def record_download(self, record: DownloadRecord) -> None:
        """Record a successful download."""
        with self._lock:
            conn = self._get_connection()

            conn.execute(
                """
                INSERT INTO download_history 
                (post_id, post_url, subreddit, title, author, downloaded_at, file_path, task_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.post_id,
                    record.post_url,
                    record.subreddit,
                    record.title,
                    record.author,
                    record.downloaded_at.isoformat(),
                    record.file_path,
                    record.task_id,
                ),
            )

            conn.commit()
            logger.debug("Recorded download for post %s", record.post_id)

    def is_post_downloaded(self, post_id: str, subreddit: str) -> bool:
        """Check if a post has already been downloaded."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT 1 FROM download_history 
                WHERE post_id = ? AND subreddit = ? 
                LIMIT 1
            """,
                (post_id, subreddit),
            )

            return cursor.fetchone() is not None

    def get_downloaded_posts(self, subreddit: str, since_days: int = 30) -> Set[str]:
        """Get set of post IDs downloaded from a subreddit in recent days."""
        with self._lock:
            conn = self._get_connection()
            since_date = (datetime.now() - timedelta(days=since_days)).isoformat()

            cursor = conn.execute(
                """
                SELECT post_id FROM download_history 
                WHERE subreddit = ? AND downloaded_at >= ?
            """,
                (subreddit, since_date),
            )

            return {row[0] for row in cursor.fetchall()}

    def get_download_history(
        self,
        task_id: Optional[str] = None,
        subreddit: Optional[str] = None,
        limit: int = 100,
    ) -> List[DownloadRecord]:
        """Get download history with optional filtering."""
        with self._lock:
            conn = self._get_connection()

            query = "SELECT * FROM download_history WHERE 1=1"
            params = []

            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)

            if subreddit:
                query += " AND subreddit = ?"
                params.append(subreddit)

            query += " ORDER BY downloaded_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            return [
                DownloadRecord(
                    post_id=row["post_id"],
                    post_url=row["post_url"],
                    subreddit=row["subreddit"],
                    title=row["title"],
                    author=row["author"],
                    downloaded_at=datetime.fromisoformat(row["downloaded_at"]),
                    file_path=row["file_path"],
                    task_id=row["task_id"],
                )
                for row in rows
            ]

    def cleanup_old_history(
        self, days_to_keep: int = 90, batch_size: Optional[int] = None
    ) -> int:
        """Clean up old download history records with optional batch processing."""
        with self._lock:
            conn = self._get_connection()
            try:
                cutoff_date = (
                    datetime.now() - timedelta(days=days_to_keep)
                ).isoformat()

                if batch_size is None:
                    # Single operation cleanup
                    cursor = conn.execute(
                        """
                        DELETE FROM download_history 
                        WHERE downloaded_at < ?
                    """,
                        (cutoff_date,),
                    )
                    conn.commit()
                    deleted_count = cursor.rowcount
                else:
                    # Batch cleanup using rowid
                    deleted_count = 0
                    while True:
                        # Find rowids to delete in this batch
                        cursor = conn.execute(
                            """
                            SELECT rowid FROM download_history 
                            WHERE downloaded_at < ?
                            LIMIT ?
                        """,
                            (cutoff_date, batch_size),
                        )
                        rowids = [row[0] for row in cursor.fetchall()]

                        if not rowids:
                            # No more records to delete
                            break

                        # Delete the records by rowid
                        placeholders = ",".join("?" * len(rowids))
                        cursor = conn.execute(
                            f"""
                            DELETE FROM download_history 
                            WHERE rowid IN ({placeholders})
                        """,
                            rowids,
                        )
                        conn.commit()
                        batch_deleted = cursor.rowcount
                        deleted_count += batch_deleted

                        if len(rowids) < batch_size:
                            # Last batch, no more records to delete
                            break

                if deleted_count > 0:
                    logger.info("Cleaned up %d old download records", deleted_count)

                return deleted_count
            finally:
                self._return_connection(conn)

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._lock:
            conn = self._get_connection()

            # Task statistics
            task_cursor = conn.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled,
                    MIN(created_at) as oldest_task,
                    MAX(last_run) as last_execution
                FROM scheduled_tasks
            """
            )
            task_stats = task_cursor.fetchone()

            # Download statistics
            download_cursor = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_downloads,
                    COUNT(DISTINCT subreddit) as unique_subreddits,
                    COUNT(DISTINCT post_id) as unique_posts,
                    MIN(downloaded_at) as first_download,
                    MAX(downloaded_at) as last_download
                FROM download_history
            """
            )
            download_stats = download_cursor.fetchone()

            # Recent activity (last 7 days)
            recent_cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            recent_cursor = conn.execute(
                """
                SELECT COUNT(*) as recent_downloads
                FROM download_history 
                WHERE downloaded_at >= ?
            """,
                (recent_cutoff,),
            )
            recent_stats = recent_cursor.fetchone()

            return {
                "tasks": {
                    "total": task_stats["total"] or 0,
                    "enabled": task_stats["enabled"] or 0,
                    "oldest_task": task_stats["oldest_task"],
                    "last_execution": task_stats["last_execution"],
                },
                "downloads": {
                    "total": download_stats["total_downloads"] or 0,
                    "unique_subreddits": download_stats["unique_subreddits"] or 0,
                    "unique_posts": download_stats["unique_posts"] or 0,
                    "first_download": download_stats["first_download"],
                    "last_download": download_stats["last_download"],
                    "recent_7_days": recent_stats["recent_downloads"] or 0,
                },
                "database": {
                    "path": str(self.db_path),
                    "size_bytes": (
                        self.db_path.stat().st_size if self.db_path.exists() else 0
                    ),
                },
            }

    def close(self) -> None:
        """Close all database connections."""
        with self._lock:
            # Close connections in cache
            for conn in self._connection_cache.values():
                conn.close()
            self._connection_cache.clear()

            # Close connections in pool
            while not self._connection_pool.empty():
                try:
                    conn = self._connection_pool.get_nowait()
                    conn.close()
                except:
                    break

            logger.info("Database connections closed")


class BloomFilter:
    """Simple Bloom filter for duplicate detection."""

    def __init__(self, capacity: int = 100000, error_rate: float = 0.1):
        import math

        self.capacity = capacity
        self.error_rate = error_rate

        # Calculate optimal bit array size and number of hash functions
        self.bit_array_size = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))
        self.hash_count = int(self.bit_array_size * math.log(2) / capacity)

        # Use a simple bit array (list of booleans)
        self._bit_array = [False] * self.bit_array_size
        self._item_count = 0

    def _hash(self, item: str, seed: int) -> int:
        """Generate hash for item with given seed."""
        hash_obj = hashlib.md5(f"{item}:{seed}".encode())
        return int(hash_obj.hexdigest(), 16) % self.bit_array_size

    def add(self, item: str) -> None:
        """Add item to bloom filter."""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            self._bit_array[index] = True
        self._item_count += 1

    def might_contain(self, item: str) -> bool:
        """Check if item might be in the set (may have false positives)."""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            if not self._bit_array[index]:
                return False
        return True

    def __len__(self) -> int:
        """Return estimated number of items."""
        return self._item_count
