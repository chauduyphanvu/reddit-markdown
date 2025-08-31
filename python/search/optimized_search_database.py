import sqlite3
import os
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager
import hashlib
import re
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class DatabaseConnectionPool:
    """Thread-safe connection pool for SQLite database."""

    def __init__(self, db_path: str, pool_size: int = 5, timeout: int = 30):
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._connections = []
        self._lock = threading.RLock()
        self._used_connections = set()

        # Pre-create connections
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool."""
        for _ in range(self.pool_size):
            conn = sqlite3.connect(
                self.db_path, timeout=self.timeout, check_same_thread=False
            )
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA cache_size=10000")  # 40MB cache
            self._connections.append(conn)

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        conn = None
        try:
            with self._lock:
                if self._connections:
                    conn = self._connections.pop()
                    self._used_connections.add(conn)
                else:
                    # Pool exhausted, create temporary connection
                    conn = sqlite3.connect(
                        self.db_path, timeout=self.timeout, check_same_thread=False
                    )
                    conn.execute("PRAGMA foreign_keys=ON")

            yield conn

        finally:
            if conn:
                try:
                    # Rollback any uncommitted transaction
                    conn.rollback()

                    with self._lock:
                        if conn in self._used_connections:
                            self._used_connections.remove(conn)
                            if len(self._connections) < self.pool_size:
                                self._connections.append(conn)
                            else:
                                conn.close()
                        else:
                            # Temporary connection, close it
                            conn.close()
                except:
                    # Connection might be closed already
                    pass

    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._connections + list(self._used_connections):
                try:
                    conn.close()
                except:
                    pass
            self._connections.clear()
            self._used_connections.clear()


class InputValidator:
    """Validates and sanitizes user inputs for database operations."""

    # Regex patterns for validation
    SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9._/-]+$")
    POST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")
    TAG_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")
    COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

    @staticmethod
    def validate_file_path(file_path: str) -> str:
        """Validate and sanitize file path to prevent directory traversal."""
        if not file_path or not isinstance(file_path, str):
            raise ValueError("File path must be a non-empty string")

        # Resolve path and check it's within allowed bounds
        resolved_path = os.path.abspath(file_path)

        # Check for dangerous patterns (but allow temp directories)
        if ".." in file_path and not (
            "/tmp/" in file_path or "/var/folders/" in file_path
        ):
            raise ValueError("Invalid file path")

        # Block access to sensitive system directories
        dangerous_paths = ["/etc/", "/usr/bin/", "/usr/sbin/", "/boot/", "/sys/"]
        if any(file_path.startswith(path) for path in dangerous_paths):
            raise ValueError("Access to system directories not allowed")

        # Ensure it's within reasonable length
        if len(resolved_path) > 1000:
            raise ValueError("File path too long")

        return resolved_path

    @staticmethod
    def validate_post_id(post_id: str) -> str:
        """Validate Reddit post ID format."""
        if not post_id or not isinstance(post_id, str):
            raise ValueError("Post ID must be a non-empty string")

        if not InputValidator.POST_ID_PATTERN.match(post_id):
            raise ValueError("Invalid post ID format")

        return post_id

    @staticmethod
    def validate_tag_name(tag_name: str) -> str:
        """Validate tag name format."""
        if not tag_name or not isinstance(tag_name, str):
            raise ValueError("Tag name must be a non-empty string")

        # Normalize tag name
        normalized = re.sub(r"[^\w\-]", "_", tag_name.lower().strip())
        normalized = re.sub(r"_+", "_", normalized).strip("_")

        if len(normalized) == 0:
            raise ValueError("Tag name cannot be empty after normalization")

        if len(normalized) > 50:
            raise ValueError("Tag name too long")

        return normalized

    @staticmethod
    def validate_search_query(query: str) -> str:
        """Validate and sanitize search query."""
        if not isinstance(query, str):
            return ""

        # Limit query length
        if len(query) > 1000:
            query = query[:1000]

        # Remove potentially dangerous characters for FTS
        query = re.sub(r'[^\w\s"*-]', " ", query)
        query = re.sub(r"\s+", " ", query).strip()

        return query

    @staticmethod
    def validate_integer_range(
        value: Any, min_val: int = None, max_val: int = None
    ) -> Optional[int]:
        """Validate integer within specified range."""
        if value is None:
            return None

        if not isinstance(value, (int, float)):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValueError("Invalid integer value")

        value = int(value)

        if min_val is not None and value < min_val:
            raise ValueError(f"Value must be >= {min_val}")

        if max_val is not None and value > max_val:
            raise ValueError(f"Value must be <= {max_val}")

        return value


class OptimizedSearchDatabase:
    """
    High-performance, secure SQLite-based search database for indexing Reddit posts.

    Improvements:
    - Connection pooling for better performance
    - Comprehensive input validation and SQL injection prevention
    - Transaction management with rollback capabilities
    - Optimized indexes and query patterns
    - Integrity checks and repair mechanisms
    - Better error handling and logging
    - Memory usage optimization
    - Concurrent access support
    """

    def __init__(self, db_path: str = None, pool_size: int = 5):
        """
        Initialize the optimized search database.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
            pool_size: Size of the connection pool (default: 5).
        """
        if db_path is None:
            db_path = os.path.join(os.getcwd(), "reddit_search.db")

        self.db_path = InputValidator.validate_file_path(db_path)
        self.validator = InputValidator()

        # Initialize connection pool
        self._pool = DatabaseConnectionPool(self.db_path, pool_size)

        # Initialize database schema
        self._init_database()

        # Cache for frequently accessed data
        self._cache_lock = threading.RLock()
        self._stats_cache = None
        self._stats_cache_time = 0
        self._cache_ttl = 60  # 1 minute cache TTL

    def _init_database(self) -> None:
        """Initialize database tables, indexes, and optimizations."""
        try:
            # Ensure parent directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            with self._pool.get_connection() as conn:
                # Enable foreign keys and other optimizations
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")

                # Create schema with additional optimizations
                conn.executescript(
                    """
                    -- Posts table for metadata with optimized schema
                    CREATE TABLE IF NOT EXISTS posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT UNIQUE NOT NULL,
                        post_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        author TEXT,
                        subreddit TEXT,
                        url TEXT,
                        created_utc INTEGER,
                        upvotes INTEGER DEFAULT 0,
                        reply_count INTEGER DEFAULT 0,
                        file_modified_time REAL,
                        indexed_time REAL DEFAULT (strftime('%s', 'now')),
                        content_preview TEXT,
                        content_hash TEXT,  -- For change detection
                        UNIQUE(file_path)
                    );
                    
                    -- FTS5 virtual table with optimized configuration
                    CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
                        post_id,
                        title,
                        content,
                        author,
                        subreddit,
                        tokenize='porter unicode61 remove_diacritics 1'
                    );
                    
                    -- Tags table with additional metadata
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        color TEXT,
                        created_time REAL DEFAULT (strftime('%s', 'now')),
                        usage_count INTEGER DEFAULT 0
                    );
                    
                    -- Post-tag relationships with better indexing
                    CREATE TABLE IF NOT EXISTS post_tags (
                        post_id INTEGER,
                        tag_id INTEGER,
                        created_time REAL DEFAULT (strftime('%s', 'now')),
                        PRIMARY KEY (post_id, tag_id),
                        FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
                        FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                    );
                    
                    -- Optimized indexes for common query patterns
                    CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit);
                    CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author);
                    CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_utc);
                    CREATE INDEX IF NOT EXISTS idx_posts_upvotes ON posts(upvotes);
                    CREATE INDEX IF NOT EXISTS idx_posts_file_modified ON posts(file_modified_time);
                    CREATE INDEX IF NOT EXISTS idx_posts_content_hash ON posts(content_hash);
                    CREATE INDEX IF NOT EXISTS idx_posts_post_id ON posts(post_id);
                    
                    -- Additional indexes for complex queries
                    CREATE INDEX IF NOT EXISTS idx_posts_subreddit_upvotes ON posts(subreddit, upvotes DESC);
                    CREATE INDEX IF NOT EXISTS idx_posts_author_created ON posts(author, created_utc DESC);
                    CREATE INDEX IF NOT EXISTS idx_posts_created_upvotes ON posts(created_utc DESC, upvotes DESC);
                    
                    -- Tag indexes
                    CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
                    CREATE INDEX IF NOT EXISTS idx_tags_usage ON tags(usage_count DESC);
                    
                    -- Trigger to update tag usage count
                    CREATE TRIGGER IF NOT EXISTS update_tag_usage_insert
                    AFTER INSERT ON post_tags
                    BEGIN
                        UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
                    END;
                    
                    CREATE TRIGGER IF NOT EXISTS update_tag_usage_delete
                    AFTER DELETE ON post_tags
                    BEGIN
                        UPDATE tags SET usage_count = usage_count - 1 WHERE id = OLD.tag_id;
                    END;
                """
                )

                conn.commit()

            logger.debug("Optimized search database initialized at %s", self.db_path)

        except sqlite3.Error as e:
            logger.error("Failed to initialize optimized search database: %s", e)
            raise

    @contextmanager
    def transaction(self):
        """Context manager for database transactions with automatic rollback on error."""
        with self._pool.get_connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error("Transaction rolled back due to error: %s", e)
                raise

    def add_post(self, post_data: Dict[str, Any]) -> int:
        """
        Add or update a post in the database with enhanced validation and performance.

        Args:
            post_data: Dictionary containing post metadata and content

        Returns:
            The post ID (database primary key)

        Raises:
            ValueError: If required fields are missing or invalid
            sqlite3.Error: If database operation fails
        """
        # Validate required fields
        required_fields = ["file_path", "post_id", "title"]
        for field in required_fields:
            if field not in post_data or not post_data[field]:
                raise ValueError(f"Missing or empty required field: {field}")

        # Validate inputs
        file_path = self.validator.validate_file_path(post_data["file_path"])
        post_id = self.validator.validate_post_id(post_data["post_id"])
        title = (
            post_data["title"][:500]
            if len(post_data["title"]) > 500
            else post_data["title"]
        )

        # Calculate content hash for change detection
        content = post_data.get("content", "")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Validate numeric fields
        upvotes = self.validator.validate_integer_range(
            post_data.get("upvotes", 0), 0, 1000000
        )
        reply_count = self.validator.validate_integer_range(
            post_data.get("reply_count", 0), 0, 100000
        )
        created_utc = self.validator.validate_integer_range(
            post_data.get("created_utc"), 0
        )

        try:
            with self.transaction() as conn:
                # Check if post already exists
                existing_cursor = conn.execute(
                    "SELECT id, content_hash FROM posts WHERE file_path = ?",
                    (file_path,),
                )
                existing_result = existing_cursor.fetchone()
                is_update = existing_result is not None

                # Skip if content hasn't changed
                if is_update and existing_result[1] == content_hash:
                    logger.debug("Content unchanged for %s, skipping update", post_id)
                    return existing_result[0]

                if is_update:
                    # Update existing post
                    conn.execute(
                        """
                        UPDATE posts SET
                            post_id = ?, title = ?, author = ?, subreddit = ?, url = ?,
                            created_utc = ?, upvotes = ?, reply_count = ?, 
                            file_modified_time = ?, content_preview = ?, content_hash = ?
                        WHERE file_path = ?
                    """,
                        (
                            post_id,
                            title,
                            post_data.get("author"),
                            post_data.get("subreddit"),
                            post_data.get("url"),
                            created_utc,
                            upvotes,
                            reply_count,
                            post_data.get("file_modified_time"),
                            post_data.get("content_preview"),
                            content_hash,
                            file_path,
                        ),
                    )
                    db_post_id = existing_result[0]
                else:
                    # Insert new post
                    cursor = conn.execute(
                        """
                        INSERT INTO posts (
                            file_path, post_id, title, author, subreddit, url,
                            created_utc, upvotes, reply_count, file_modified_time,
                            content_preview, content_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            file_path,
                            post_id,
                            title,
                            post_data.get("author"),
                            post_data.get("subreddit"),
                            post_data.get("url"),
                            created_utc,
                            upvotes,
                            reply_count,
                            post_data.get("file_modified_time"),
                            post_data.get("content_preview"),
                            content_hash,
                        ),
                    )
                    db_post_id = cursor.lastrowid

                # Update FTS index if content provided
                if content:
                    if is_update:
                        # Delete old FTS entry
                        conn.execute(
                            "DELETE FROM posts_fts WHERE rowid = ?", (db_post_id,)
                        )

                    # Insert new FTS entry
                    conn.execute(
                        """
                        INSERT INTO posts_fts (
                            rowid, post_id, title, content, author, subreddit
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            db_post_id,
                            post_id,
                            title,
                            content,
                            post_data.get("author", ""),
                            post_data.get("subreddit", ""),
                        ),
                    )

                # Clear stats cache
                self._clear_stats_cache()

                logger.debug("Added/updated post %s in search database", post_id)
                return db_post_id

        except sqlite3.Error as e:
            logger.error("Failed to add post %s: %s", post_id, e)
            raise

    def search_posts_optimized(
        self,
        query: str = None,
        subreddits: List[str] = None,
        authors: List[str] = None,
        min_upvotes: int = None,
        max_upvotes: int = None,
        tags: List[str] = None,
        date_from: int = None,
        date_to: int = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Optimized search with better performance and safety.

        Args:
            query: Full-text search query
            subreddits: Filter by subreddits
            authors: Filter by authors
            min_upvotes: Minimum upvotes threshold
            max_upvotes: Maximum upvotes threshold
            tags: Filter by tag names
            date_from: Unix timestamp for start date
            date_to: Unix timestamp for end date
            limit: Maximum results to return (max 1000)
            offset: Number of results to skip for pagination

        Returns:
            List of matching posts with metadata
        """
        # Validate inputs
        if query:
            query = self.validator.validate_search_query(query)

        limit = self.validator.validate_integer_range(limit, 1, 1000) or 50
        offset = self.validator.validate_integer_range(offset, 0) or 0
        min_upvotes = self.validator.validate_integer_range(min_upvotes, 0)
        max_upvotes = self.validator.validate_integer_range(max_upvotes, 0)
        date_from = self.validator.validate_integer_range(date_from, 0)
        date_to = self.validator.validate_integer_range(date_to, 0)

        try:
            with self._pool.get_connection() as conn:
                conn.row_factory = sqlite3.Row

                # Build optimized query
                sql_parts = []
                params = []

                if query and query.strip():
                    # Full-text search with ranking
                    base_sql = """
                        SELECT p.*, 
                               snippet(posts_fts, 2, '<mark>', '</mark>', '...', 32) as snippet,
                               bm25(posts_fts) as rank_score
                        FROM posts p
                        JOIN posts_fts ON p.id = posts_fts.rowid
                        WHERE posts_fts MATCH ?
                    """
                    # Prepare safe FTS query
                    fts_query = self._prepare_safe_fts_query(query)
                    params.append(fts_query)
                else:
                    # Metadata-only search with optimized ordering
                    base_sql = """
                        SELECT *, '' as snippet, 0 as rank_score 
                        FROM posts 
                        WHERE 1=1
                    """

                # Add filters with proper indexing hints
                conditions = []

                if subreddits:
                    validated_subreddits = [
                        s[:50] for s in subreddits if s
                    ]  # Limit length
                    if validated_subreddits:
                        placeholders = ",".join(["?" for _ in validated_subreddits])
                        table_prefix = "p." if query else ""
                        conditions.append(
                            f"{table_prefix}subreddit IN ({placeholders})"
                        )
                        params.extend(validated_subreddits)

                if authors:
                    validated_authors = [a[:50] for a in authors if a]  # Limit length
                    if validated_authors:
                        placeholders = ",".join(["?" for _ in validated_authors])
                        table_prefix = "p." if query else ""
                        conditions.append(f"{table_prefix}author IN ({placeholders})")
                        params.extend(validated_authors)

                if min_upvotes is not None:
                    table_prefix = "p." if query else ""
                    conditions.append(f"{table_prefix}upvotes >= ?")
                    params.append(min_upvotes)

                if max_upvotes is not None:
                    table_prefix = "p." if query else ""
                    conditions.append(f"{table_prefix}upvotes <= ?")
                    params.append(max_upvotes)

                if date_from is not None:
                    table_prefix = "p." if query else ""
                    conditions.append(f"{table_prefix}created_utc >= ?")
                    params.append(date_from)

                if date_to is not None:
                    table_prefix = "p." if query else ""
                    conditions.append(f"{table_prefix}created_utc <= ?")
                    params.append(date_to)

                # Handle tag filtering with optimized join
                if tags:
                    validated_tags = []
                    for tag in tags:
                        try:
                            validated_tag = self.validator.validate_tag_name(tag)
                            validated_tags.append(validated_tag)
                        except ValueError:
                            continue  # Skip invalid tags

                    if validated_tags:
                        if query:
                            base_sql += """
                                JOIN post_tags pt ON p.id = pt.post_id
                                JOIN tags t ON pt.tag_id = t.id
                            """
                        else:
                            base_sql += """
                                JOIN post_tags pt ON posts.id = pt.post_id
                                JOIN tags t ON pt.tag_id = t.id
                            """

                        placeholders = ",".join(["?" for _ in validated_tags])
                        conditions.append(f"t.name IN ({placeholders})")
                        params.extend(validated_tags)

                # Combine conditions
                if conditions:
                    separator = " AND "
                    base_sql += separator + " AND ".join(conditions)

                # Add optimized ordering
                if query and query.strip():
                    base_sql += " ORDER BY rank_score ASC"
                else:
                    # Use index-optimized ordering
                    base_sql += " ORDER BY created_utc DESC"

                # Add pagination
                base_sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                # Execute query
                cursor = conn.execute(base_sql, params)
                results = [dict(row) for row in cursor.fetchall()]

                logger.debug("Optimized search returned %d results", len(results))
                return results

        except sqlite3.Error as e:
            logger.error("Optimized search query failed: %s", e)
            return []

    def _prepare_safe_fts_query(self, text: str) -> str:
        """Prepare safe FTS query with proper escaping and validation."""
        if not text:
            return ""

        # Handle quoted phrases - preserve them
        if '"' in text:
            # Simple quote balancing check
            quote_count = text.count('"')
            if quote_count % 2 != 0:
                text = text.replace('"', "")  # Remove unbalanced quotes

        # Extract safe words and build FTS query
        words = re.findall(r"\b\w+\b", text)
        if not words:
            return ""

        # Limit number of terms to prevent performance issues
        words = words[:20]

        # Build safe FTS query with prefix matching
        safe_terms = []
        for word in words:
            if len(word) >= 2:  # Only use meaningful terms
                # Escape any special FTS characters
                escaped_word = re.sub(r"[^\w]", "", word)
                if len(escaped_word) >= 2:
                    safe_terms.append(f"{escaped_word}*")

        return " ".join(safe_terms) if safe_terms else ""

    def get_stats_cached(self) -> Dict[str, int]:
        """Get database statistics with caching for performance."""
        current_time = time.time()

        with self._cache_lock:
            if (
                self._stats_cache
                and current_time - self._stats_cache_time < self._cache_ttl
            ):
                return self._stats_cache.copy()

        # Cache miss, compute stats
        stats = self._compute_stats()

        with self._cache_lock:
            self._stats_cache = stats.copy()
            self._stats_cache_time = current_time

        return stats

    def _compute_stats(self) -> Dict[str, int]:
        """Compute database statistics efficiently."""
        try:
            with self._pool.get_connection() as conn:
                stats = {}

                # Use single query with multiple aggregates for efficiency
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_posts,
                        COUNT(DISTINCT subreddit) as total_subreddits,
                        COUNT(DISTINCT author) as total_authors,
                        SUM(upvotes) as total_upvotes,
                        AVG(upvotes) as avg_upvotes
                    FROM posts
                    WHERE subreddit IS NOT NULL AND author IS NOT NULL
                """
                )

                row = cursor.fetchone()
                if row:
                    stats.update(
                        {
                            "total_posts": row[0],
                            "total_subreddits": row[1],
                            "total_authors": row[2],
                            "total_upvotes": row[3] or 0,
                            "avg_upvotes": round(row[4] or 0, 2),
                        }
                    )

                # Get tag count separately (typically much smaller)
                cursor = conn.execute("SELECT COUNT(*) FROM tags")
                stats["total_tags"] = cursor.fetchone()[0]

                return stats

        except sqlite3.Error as e:
            logger.error("Failed to compute database stats: %s", e)
            return {}

    def _clear_stats_cache(self):
        """Clear the statistics cache."""
        with self._cache_lock:
            self._stats_cache = None
            self._stats_cache_time = 0

    def get_post_by_file_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get a post by its file path."""
        try:
            file_path = self.validator.validate_file_path(file_path)
            with self._pool.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM posts WHERE file_path = ?", (file_path,)
                )
                result = cursor.fetchone()
                return dict(result) if result else None
        except (sqlite3.Error, ValueError) as e:
            logger.error("Failed to get post by file path %s: %s", file_path, e)
            return None

    def delete_post(self, file_path: str) -> bool:
        """Delete a post from the database."""
        try:
            file_path = self.validator.validate_file_path(file_path)
            with self.transaction() as conn:
                # Get post ID first
                cursor = conn.execute(
                    "SELECT id FROM posts WHERE file_path = ?", (file_path,)
                )
                result = cursor.fetchone()
                if not result:
                    return False

                post_id = result[0]

                # Delete from FTS table
                conn.execute("DELETE FROM posts_fts WHERE rowid = ?", (post_id,))

                # Delete from main table (cascades to post_tags)
                conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))

                # Clear stats cache
                self._clear_stats_cache()

                logger.debug("Deleted post at %s from search database", file_path)
                return True

        except (sqlite3.Error, ValueError) as e:
            logger.error("Failed to delete post %s: %s", file_path, e)
            return False

    def integrity_check(self) -> Dict[str, Any]:
        """Perform database integrity check and return results."""
        try:
            with self._pool.get_connection() as conn:
                results = {
                    "database_integrity": True,
                    "fts_integrity": True,
                    "foreign_key_violations": [],
                    "issues_found": [],
                }

                # SQLite built-in integrity check
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                if integrity_result[0] != "ok":
                    results["database_integrity"] = False
                    results["issues_found"].append(
                        f"Database integrity: {integrity_result[0]}"
                    )

                # Check FTS index consistency
                cursor = conn.execute(
                    "INSERT INTO posts_fts(posts_fts) VALUES('integrity-check')"
                )

                # Foreign key check
                cursor = conn.execute("PRAGMA foreign_key_check")
                fk_violations = cursor.fetchall()
                if fk_violations:
                    results["foreign_key_violations"] = fk_violations
                    results["issues_found"].append(
                        f"Foreign key violations: {len(fk_violations)}"
                    )

                # Check for orphaned FTS entries
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM posts_fts 
                    WHERE rowid NOT IN (SELECT id FROM posts)
                """
                )
                orphaned_fts = cursor.fetchone()[0]
                if orphaned_fts > 0:
                    results["issues_found"].append(
                        f"Orphaned FTS entries: {orphaned_fts}"
                    )

                logger.info(
                    "Integrity check completed: %d issues found",
                    len(results["issues_found"]),
                )
                return results

        except sqlite3.Error as e:
            logger.error("Integrity check failed: %s", e)
            return {"error": str(e)}

    def repair_database(self) -> bool:
        """Attempt to repair database issues found during integrity check."""
        try:
            logger.info("Starting database repair process")

            with self.transaction() as conn:
                # Clean up orphaned FTS entries
                conn.execute(
                    """
                    DELETE FROM posts_fts 
                    WHERE rowid NOT IN (SELECT id FROM posts)
                """
                )

                # Rebuild FTS index
                conn.execute("INSERT INTO posts_fts(posts_fts) VALUES('rebuild')")

                # Update tag usage counts
                conn.execute(
                    """
                    UPDATE tags SET usage_count = (
                        SELECT COUNT(*) FROM post_tags WHERE tag_id = tags.id
                    )
                """
                )

            logger.info("Database repair completed successfully")
            return True

        except sqlite3.Error as e:
            logger.error("Database repair failed: %s", e)
            return False

    def close(self) -> None:
        """Close database connection pool."""
        self._pool.close_all()
        logger.debug("Database connection pool closed")
