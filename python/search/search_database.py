import sqlite3
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class SearchDatabase:
    """
    SQLite-based search database for indexing Reddit posts.

    Provides full-text search capabilities with FTS5 and stores
    post metadata, content, and user-defined tags.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize the search database.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            db_path = os.path.join(os.getcwd(), "reddit_search.db")

        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database tables and indexes."""
        try:
            # Ensure parent directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(
                    """
                    -- Posts table for metadata
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
                        UNIQUE(file_path)
                    );
                    
                    -- FTS5 virtual table for full-text search
                    CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
                        post_id,
                        title,
                        content,
                        author,
                        subreddit
                    );
                    
                    -- Tags table
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        color TEXT,
                        created_time REAL DEFAULT (strftime('%s', 'now'))
                    );
                    
                    -- Post-tag relationships (many-to-many)
                    CREATE TABLE IF NOT EXISTS post_tags (
                        post_id INTEGER,
                        tag_id INTEGER,
                        created_time REAL DEFAULT (strftime('%s', 'now')),
                        PRIMARY KEY (post_id, tag_id),
                        FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
                        FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                    );
                    
                    -- Indexes for performance
                    CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit);
                    CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author);
                    CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_utc);
                    CREATE INDEX IF NOT EXISTS idx_posts_upvotes ON posts(upvotes);
                    CREATE INDEX IF NOT EXISTS idx_posts_file_modified ON posts(file_modified_time);
                """
                )

            logger.debug("Search database initialized at %s", self.db_path)

        except sqlite3.Error as e:
            logger.error("Failed to initialize search database: %s", e)
            raise

    def add_post(self, post_data: Dict[str, Any]) -> int:
        """
        Add or update a post in the database.

        Args:
            post_data: Dictionary containing post metadata and content

        Returns:
            The post ID (database primary key)

        Raises:
            sqlite3.Error: If database operation fails
        """
        required_fields = ["file_path", "post_id", "title"]
        for field in required_fields:
            if field not in post_data:
                raise ValueError(f"Missing required field: {field}")

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if post already exists
                existing_cursor = conn.execute(
                    "SELECT id FROM posts WHERE file_path = ?",
                    (post_data["file_path"],),
                )
                existing_result = existing_cursor.fetchone()
                is_update = existing_result is not None

                if is_update:
                    # Update existing post
                    conn.execute(
                        """
                        UPDATE posts SET
                            post_id = ?, title = ?, author = ?, subreddit = ?, url = ?,
                            created_utc = ?, upvotes = ?, reply_count = ?, 
                            file_modified_time = ?, content_preview = ?
                        WHERE file_path = ?
                    """,
                        (
                            post_data["post_id"],
                            post_data["title"],
                            post_data.get("author"),
                            post_data.get("subreddit"),
                            post_data.get("url"),
                            post_data.get("created_utc"),
                            post_data.get("upvotes", 0),
                            post_data.get("reply_count", 0),
                            post_data.get("file_modified_time"),
                            post_data.get("content_preview"),
                            post_data["file_path"],
                        ),
                    )
                    post_id = existing_result[0]
                else:
                    # Insert new post
                    cursor = conn.execute(
                        """
                        INSERT INTO posts (
                            file_path, post_id, title, author, subreddit, url,
                            created_utc, upvotes, reply_count, file_modified_time,
                            content_preview
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            post_data["file_path"],
                            post_data["post_id"],
                            post_data["title"],
                            post_data.get("author"),
                            post_data.get("subreddit"),
                            post_data.get("url"),
                            post_data.get("created_utc"),
                            post_data.get("upvotes", 0),
                            post_data.get("reply_count", 0),
                            post_data.get("file_modified_time"),
                            post_data.get("content_preview"),
                        ),
                    )
                    post_id = cursor.lastrowid

                # Update FTS index
                if "content" in post_data:
                    if is_update:
                        # Delete old FTS entry first
                        conn.execute(
                            "DELETE FROM posts_fts WHERE rowid = ?", (post_id,)
                        )

                    # Insert new FTS entry
                    conn.execute(
                        """
                        INSERT INTO posts_fts (
                            rowid, post_id, title, content, author, subreddit
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            post_id,
                            post_data["post_id"],
                            post_data["title"],
                            post_data["content"],
                            post_data.get("author", ""),
                            post_data.get("subreddit", ""),
                        ),
                    )

                logger.debug("Added post %s to search database", post_data["post_id"])
                return post_id

        except sqlite3.Error as e:
            logger.error("Failed to add post %s: %s", post_data.get("post_id"), e)
            raise

    def search_posts(
        self,
        query: str = None,
        subreddit: str = None,
        author: str = None,
        min_upvotes: int = None,
        tags: List[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search posts using full-text search and filters.

        Args:
            query: Full-text search query
            subreddit: Filter by subreddit
            author: Filter by author
            min_upvotes: Minimum upvotes threshold
            tags: Filter by tag names
            limit: Maximum results to return

        Returns:
            List of matching posts with metadata
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Build query based on parameters
                if query:
                    # Full-text search
                    sql = """
                        SELECT p.*, 
                               snippet(posts_fts, 2, '<mark>', '</mark>', '...', 32) as snippet,
                               bm25(posts_fts) as rank_score
                        FROM posts p
                        JOIN posts_fts ON p.id = posts_fts.rowid
                        WHERE posts_fts MATCH ?
                        ORDER BY rank_score
                    """
                    params = [query]
                else:
                    # Metadata-only search
                    sql = "SELECT * FROM posts"
                    params = []

                # Add filters
                where_conditions = []

                if subreddit:
                    where_conditions.append("subreddit = ?")
                    params.append(subreddit)

                if author:
                    where_conditions.append("author = ?")
                    params.append(author)

                if min_upvotes is not None:
                    where_conditions.append("upvotes >= ?")
                    params.append(min_upvotes)

                if tags:
                    # Join with tags
                    if query:
                        # Already have JOIN with FTS, add tag join
                        sql = sql.replace(
                            "FROM posts p",
                            """
                            FROM posts p
                            JOIN post_tags pt ON p.id = pt.post_id
                            JOIN tags t ON pt.tag_id = t.id
                        """,
                        )
                    else:
                        sql += """
                            JOIN post_tags pt ON posts.id = pt.post_id
                            JOIN tags t ON pt.tag_id = t.id
                        """

                    placeholders = ",".join(["?" for _ in tags])
                    where_conditions.append(f"t.name IN ({placeholders})")
                    params.extend(tags)

                # Add WHERE clause
                if where_conditions:
                    connector = " AND " if query and "WHERE" not in sql else " WHERE "
                    sql += connector + " AND ".join(where_conditions)

                # Add ordering and limit
                if not query:
                    sql += " ORDER BY created_utc DESC"

                sql += " LIMIT ?"
                params.append(limit)

                cursor = conn.execute(sql, params)
                results = [dict(row) for row in cursor.fetchall()]

                logger.debug("Found %d posts matching search criteria", len(results))
                return results

        except sqlite3.Error as e:
            logger.error("Search query failed: %s", e)
            return []

    def get_post_by_file_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get a post by its file path."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM posts WHERE file_path = ?", (file_path,)
                )
                result = cursor.fetchone()
                return dict(result) if result else None

        except sqlite3.Error as e:
            logger.error("Failed to get post by file path %s: %s", file_path, e)
            return None

    def delete_post(self, file_path: str) -> bool:
        """Delete a post from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get post ID first
                cursor = conn.execute(
                    "SELECT id FROM posts WHERE file_path = ?", (file_path,)
                )
                result = cursor.fetchone()
                if not result:
                    return False

                post_id = result[0]

                # Delete from FTS index first
                conn.execute(
                    "DELETE FROM posts_fts WHERE post_id IN (SELECT post_id FROM posts WHERE id = ?)",
                    (post_id,),
                )

                # Delete from main table (cascade will handle post_tags)
                conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))

                logger.debug("Deleted post with file path %s", file_path)
                return True

        except sqlite3.Error as e:
            logger.error("Failed to delete post %s: %s", file_path, e)
            return False

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}

                # Post count
                cursor = conn.execute("SELECT COUNT(*) FROM posts")
                stats["total_posts"] = cursor.fetchone()[0]

                # Tag count
                cursor = conn.execute("SELECT COUNT(*) FROM tags")
                stats["total_tags"] = cursor.fetchone()[0]

                # Subreddit count
                cursor = conn.execute(
                    "SELECT COUNT(DISTINCT subreddit) FROM posts WHERE subreddit IS NOT NULL"
                )
                stats["total_subreddits"] = cursor.fetchone()[0]

                # Author count
                cursor = conn.execute(
                    "SELECT COUNT(DISTINCT author) FROM posts WHERE author IS NOT NULL"
                )
                stats["total_authors"] = cursor.fetchone()[0]

                return stats

        except sqlite3.Error as e:
            logger.error("Failed to get database stats: %s", e)
            return {}

    def close(self) -> None:
        """Close database connection (no-op since we use context managers)."""
        pass
