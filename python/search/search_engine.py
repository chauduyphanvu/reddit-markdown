import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from colored_logger import get_colored_logger
from .search_database import SearchDatabase

logger = get_colored_logger(__name__)


@dataclass
class SearchResult:
    """
    Represents a single search result with metadata and ranking information.
    """

    post_id: str
    title: str
    author: str
    subreddit: str
    url: str
    file_path: str
    created_utc: int
    upvotes: int
    reply_count: int
    content_preview: str
    snippet: str = ""
    rank_score: float = 0.0
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class SearchQuery:
    """
    Represents a search query with filtering and sorting options.
    """

    text: str = ""
    subreddits: List[str] = None
    authors: List[str] = None
    tags: List[str] = None
    min_upvotes: int = None
    max_upvotes: int = None
    date_from: int = None  # Unix timestamp
    date_to: int = None  # Unix timestamp
    sort_by: str = "relevance"  # relevance, date, upvotes, replies
    sort_order: str = "desc"  # asc, desc
    limit: int = 50

    def __post_init__(self):
        if self.subreddits is None:
            self.subreddits = []
        if self.authors is None:
            self.authors = []
        if self.tags is None:
            self.tags = []


class SearchEngine:
    """
    Full-text search engine for Reddit posts with advanced filtering and ranking.

    Features:
    - Full-text search using SQLite FTS5
    - Advanced filtering by metadata
    - Multiple sorting options
    - Search result highlighting
    - Query suggestions and auto-complete
    - Search statistics and analytics
    """

    def __init__(self, database: SearchDatabase = None):
        """
        Initialize the search engine.

        Args:
            database: SearchDatabase instance. If None, creates default instance.
        """
        self.database = database or SearchDatabase()

    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Perform a search with the given query parameters.

        Args:
            query: SearchQuery object containing search parameters

        Returns:
            List of SearchResult objects ordered by relevance/specified sort
        """
        try:
            # Build and execute search query
            sql, params = self._build_search_sql(query)

            with sqlite3.connect(self.database.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()

            # Convert to SearchResult objects
            results = []
            for row in rows:
                result = self._row_to_search_result(dict(row))

                # Add tags for this post
                result.tags = self._get_post_tags(result.post_id)

                results.append(result)

            logger.debug("Search returned %d results", len(results))
            return results

        except Exception as e:
            logger.error("Search failed: %s", e)
            return []

    def search_simple(self, text: str, limit: int = 20) -> List[SearchResult]:
        """
        Perform a simple text search (convenience method).

        Args:
            text: Search text
            limit: Maximum results to return

        Returns:
            List of SearchResult objects
        """
        query = SearchQuery(text=text, limit=limit)
        return self.search(query)

    def get_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """
        Get search suggestions based on partial query.

        Args:
            partial_query: Partial search text
            limit: Maximum suggestions to return

        Returns:
            List of suggested search terms
        """
        if not partial_query or len(partial_query) < 2:
            return []

        try:
            with sqlite3.connect(self.database.db_path) as conn:
                # Get suggestions from titles and subreddits
                suggestions = []

                # Title suggestions
                cursor = conn.execute(
                    """
                    SELECT DISTINCT title 
                    FROM posts 
                    WHERE title LIKE ? 
                    ORDER BY upvotes DESC 
                    LIMIT ?
                """,
                    (f"%{partial_query}%", limit),
                )

                for row in cursor.fetchall():
                    title = row[0]
                    # Extract relevant words from title
                    words = re.findall(r"\b\w{3,}\b", title.lower())
                    for word in words:
                        if partial_query.lower() in word and word not in suggestions:
                            suggestions.append(word)
                            if len(suggestions) >= limit:
                                break
                    if len(suggestions) >= limit:
                        break

                return suggestions

        except Exception as e:
            logger.error("Failed to get suggestions: %s", e)
            return []

    def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get popular search terms based on content analysis.

        Args:
            limit: Maximum results to return

        Returns:
            List of popular search term dictionaries
        """
        try:
            with sqlite3.connect(self.database.db_path) as conn:
                # Get most common subreddits
                cursor = conn.execute(
                    """
                    SELECT subreddit, COUNT(*) as post_count, SUM(upvotes) as total_upvotes
                    FROM posts 
                    WHERE subreddit IS NOT NULL 
                    GROUP BY subreddit 
                    ORDER BY post_count DESC 
                    LIMIT ?
                """,
                    (limit,),
                )

                popular = []
                for row in cursor.fetchall():
                    popular.append(
                        {
                            "term": row[0],
                            "type": "subreddit",
                            "post_count": row[1],
                            "total_upvotes": row[2],
                        }
                    )

                return popular

        except Exception as e:
            logger.error("Failed to get popular searches: %s", e)
            return []

    def get_search_stats(self) -> Dict[str, Any]:
        """Get search database statistics."""
        return self.database.get_stats()

    def _build_search_sql(self, query: SearchQuery) -> Tuple[str, List[Any]]:
        """Build SQL query from SearchQuery object."""
        params = []

        if query.text:
            # Full-text search query
            base_sql = """
                SELECT p.*, 
                       snippet(posts_fts, 2, '<mark>', '</mark>', '...', 32) as snippet,
                       bm25(posts_fts) as rank_score
                FROM posts p
                JOIN posts_fts ON p.id = posts_fts.rowid
                WHERE posts_fts MATCH ?
            """
            # Prepare FTS query - escape special characters
            fts_query = self._prepare_fts_query(query.text)
            params.append(fts_query)
        else:
            # Metadata-only search
            base_sql = "SELECT *, '' as snippet, 0 as rank_score FROM posts WHERE 1=1"

        # Add filters
        conditions = []

        if query.subreddits:
            placeholders = ",".join(["?" for _ in query.subreddits])
            column_name = "p.subreddit" if query.text else "subreddit"
            conditions.append(f"{column_name} IN ({placeholders})")
            params.extend(query.subreddits)

        if query.authors:
            placeholders = ",".join(["?" for _ in query.authors])
            column_name = "p.author" if query.text else "author"
            conditions.append(f"{column_name} IN ({placeholders})")
            params.extend(query.authors)

        if query.min_upvotes is not None:
            column_name = "p.upvotes" if query.text else "upvotes"
            conditions.append(f"{column_name} >= ?")
            params.append(query.min_upvotes)

        if query.max_upvotes is not None:
            column_name = "p.upvotes" if query.text else "upvotes"
            conditions.append(f"{column_name} <= ?")
            params.append(query.max_upvotes)

        if query.date_from is not None:
            column_name = "p.created_utc" if query.text else "created_utc"
            conditions.append(f"{column_name} >= ?")
            params.append(query.date_from)

        if query.date_to is not None:
            column_name = "p.created_utc" if query.text else "created_utc"
            conditions.append(f"{column_name} <= ?")
            params.append(query.date_to)

        # Handle tag filtering
        if query.tags:
            if query.text:
                # Need to add JOIN for tags
                base_sql = base_sql.replace(
                    "FROM posts p",
                    """FROM posts p
                       JOIN post_tags pt ON p.id = pt.post_id
                       JOIN tags t ON pt.tag_id = t.id""",
                )
            else:
                # Insert JOIN before WHERE clause
                base_sql = base_sql.replace(
                    "FROM posts WHERE 1=1",
                    """FROM posts
                       JOIN post_tags pt ON posts.id = pt.post_id
                       JOIN tags t ON pt.tag_id = t.id
                       WHERE 1=1""",
                )

            placeholders = ",".join(["?" for _ in query.tags])
            conditions.append(f"t.name IN ({placeholders})")
            params.extend(query.tags)

        # Add conditions to query
        if conditions:
            separator = (
                " AND "
                if "WHERE" in base_sql and "WHERE 1=1" not in base_sql
                else " AND "
            )
            if "WHERE 1=1" in base_sql:
                separator = " AND "
            base_sql += separator + " AND ".join(conditions)

        # Add sorting
        if query.sort_by == "relevance" and query.text:
            base_sql += " ORDER BY rank_score ASC"
        elif query.sort_by == "date":
            base_sql += f" ORDER BY created_utc {query.sort_order.upper()}"
        elif query.sort_by == "upvotes":
            base_sql += f" ORDER BY upvotes {query.sort_order.upper()}"
        elif query.sort_by == "replies":
            base_sql += f" ORDER BY reply_count {query.sort_order.upper()}"
        else:
            # Default sort
            base_sql += " ORDER BY created_utc DESC"

        # Add limit
        base_sql += " LIMIT ?"
        params.append(query.limit)

        return base_sql, params

    def _prepare_fts_query(self, text: str) -> str:
        """Prepare text for FTS5 query, handling special characters and operators."""
        if not text:
            return ""

        # Handle quoted phrases
        if '"' in text:
            return text  # Return as-is for phrase queries

        # Split into words and escape special FTS characters
        words = re.findall(r"\b\w+\b", text)
        if not words:
            return ""

        # Build FTS query - use prefix matching for better results
        fts_words = []
        for word in words:
            if len(word) >= 3:  # Only use prefix matching for longer words
                fts_words.append(f"{word}*")
            else:
                fts_words.append(word)

        return " ".join(fts_words)

    def _row_to_search_result(self, row: Dict[str, Any]) -> SearchResult:
        """Convert database row to SearchResult object."""
        return SearchResult(
            post_id=row.get("post_id", ""),
            title=row.get("title", ""),
            author=row.get("author", ""),
            subreddit=row.get("subreddit", ""),
            url=row.get("url", ""),
            file_path=row.get("file_path", ""),
            created_utc=row.get("created_utc", 0),
            upvotes=row.get("upvotes", 0),
            reply_count=row.get("reply_count", 0),
            content_preview=row.get("content_preview", ""),
            snippet=row.get("snippet", ""),
            rank_score=row.get("rank_score", 0.0),
        )

    def _get_post_tags(self, post_id: str) -> List[str]:
        """Get tags for a specific post."""
        try:
            with sqlite3.connect(self.database.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT t.name 
                    FROM tags t
                    JOIN post_tags pt ON t.id = pt.tag_id
                    JOIN posts p ON pt.post_id = p.id
                    WHERE p.post_id = ?
                    ORDER BY t.name
                """,
                    (post_id,),
                )

                return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            logger.error("Failed to get tags for post %s: %s", post_id, e)
            return []
