import re
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
from colored_logger import get_colored_logger
from .optimized_search_database import OptimizedSearchDatabase, InputValidator

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
    Enhanced with validation and optimization hints.
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
    offset: int = 0  # For pagination

    def __post_init__(self):
        if self.subreddits is None:
            self.subreddits = []
        if self.authors is None:
            self.authors = []
        if self.tags is None:
            self.tags = []


class QueryCache:
    """LRU cache for search queries with TTL support."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._access_order = deque()
        self._lock = threading.RLock()

    def _generate_key(self, query: SearchQuery) -> str:
        """Generate cache key from search query."""
        key_parts = [
            f"text:{query.text}",
            f"subreddits:{','.join(sorted(query.subreddits))}",
            f"authors:{','.join(sorted(query.authors))}",
            f"tags:{','.join(sorted(query.tags))}",
            f"min_upvotes:{query.min_upvotes}",
            f"max_upvotes:{query.max_upvotes}",
            f"date_from:{query.date_from}",
            f"date_to:{query.date_to}",
            f"sort:{query.sort_by}:{query.sort_order}",
            f"limit:{query.limit}",
            f"offset:{query.offset}",
        ]
        return "|".join(key_parts)

    def get(self, query: SearchQuery) -> Optional[List[Dict[str, Any]]]:
        """Get cached results for query."""
        key = self._generate_key(query)
        current_time = time.time()

        with self._lock:
            if key in self._cache:
                cached_time, results = self._cache[key]

                # Check if expired
                if current_time - cached_time > self.ttl_seconds:
                    del self._cache[key]
                    self._access_order.remove(key)
                    return None

                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)

                logger.debug("Cache hit for query")
                return results.copy()

        return None

    def put(self, query: SearchQuery, results: List[Dict[str, Any]]):
        """Cache results for query."""
        key = self._generate_key(query)
        current_time = time.time()

        with self._lock:
            # Remove if already exists
            if key in self._cache:
                self._access_order.remove(key)

            # Add new entry
            self._cache[key] = (current_time, results.copy())
            self._access_order.append(key)

            # Evict oldest if over capacity
            while len(self._cache) > self.max_size:
                oldest_key = self._access_order.popleft()
                del self._cache[oldest_key]

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()


class SearchAnalytics:
    """Track search analytics and performance metrics."""

    def __init__(self):
        self._lock = threading.RLock()
        self.reset_stats()

    def reset_stats(self):
        """Reset all statistics."""
        with self._lock:
            self.stats = {
                "total_searches": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "avg_query_time": 0.0,
                "popular_terms": defaultdict(int),
                "popular_subreddits": defaultdict(int),
                "query_times": deque(maxlen=1000),  # Keep last 1000 query times
            }

    def record_search(self, query: SearchQuery, query_time: float, cache_hit: bool):
        """Record search statistics."""
        with self._lock:
            self.stats["total_searches"] += 1

            if cache_hit:
                self.stats["cache_hits"] += 1
            else:
                self.stats["cache_misses"] += 1

            self.stats["query_times"].append(query_time)

            # Update average query time
            if self.stats["query_times"]:
                self.stats["avg_query_time"] = sum(self.stats["query_times"]) / len(
                    self.stats["query_times"]
                )

            # Track popular terms
            if query.text:
                words = re.findall(r"\b\w+\b", query.text.lower())
                for word in words:
                    if len(word) > 2:  # Only meaningful words
                        self.stats["popular_terms"][word] += 1

            # Track popular subreddits
            for subreddit in query.subreddits:
                self.stats["popular_subreddits"][subreddit] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current analytics statistics."""
        with self._lock:
            stats = self.stats.copy()

            # Convert defaultdicts to regular dicts
            stats["popular_terms"] = dict(stats["popular_terms"])
            stats["popular_subreddits"] = dict(stats["popular_subreddits"])

            # Calculate cache hit rate
            total_queries = self.stats["cache_hits"] + self.stats["cache_misses"]
            if total_queries > 0:
                stats["cache_hit_rate"] = self.stats["cache_hits"] / total_queries
            else:
                stats["cache_hit_rate"] = 0.0

            # Calculate query time percentiles
            if self.stats["query_times"]:
                sorted_times = sorted(self.stats["query_times"])
                stats["query_time_p50"] = sorted_times[len(sorted_times) // 2]
                stats["query_time_p95"] = sorted_times[int(len(sorted_times) * 0.95)]
                stats["query_time_p99"] = sorted_times[int(len(sorted_times) * 0.99)]

            return stats


class OptimizedSearchEngine:
    """
    High-performance search engine for Reddit posts with advanced optimizations.

    Enhancements:
    - Query result caching with LRU eviction
    - Batch tag loading to eliminate N+1 queries
    - Query analytics and performance monitoring
    - Memory-efficient result streaming for large datasets
    - Query suggestion optimization
    - Smart query rewriting and expansion
    """

    def __init__(
        self,
        database: OptimizedSearchDatabase = None,
        enable_cache: bool = True,
        cache_size: int = 1000,
    ):
        """
        Initialize the optimized search engine.

        Args:
            database: OptimizedSearchDatabase instance. If None, creates default instance.
            enable_cache: Whether to enable query result caching.
            cache_size: Maximum number of cached queries.
        """
        self.database = database or OptimizedSearchDatabase()
        self.validator = InputValidator()

        # Initialize caching
        self.enable_cache = enable_cache
        if enable_cache:
            self._query_cache = QueryCache(max_size=cache_size)

        # Analytics
        self.analytics = SearchAnalytics()

    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Perform an optimized search with caching and batch loading.

        Args:
            query: SearchQuery object containing search parameters

        Returns:
            List of SearchResult objects ordered by relevance/specified sort
        """
        start_time = time.time()
        cache_hit = False

        try:
            # Check cache first
            if self.enable_cache:
                cached_results = self._query_cache.get(query)
                if cached_results is not None:
                    cache_hit = True
                    results = self._convert_to_search_results(cached_results)
                    # Load tags in batch for cached results
                    self._load_tags_batch(results)

                    query_time = time.time() - start_time
                    self.analytics.record_search(query, query_time, cache_hit)

                    return results

            # Execute search query
            raw_results = self.database.search_posts_optimized(
                query=query.text,
                subreddits=query.subreddits,
                authors=query.authors,
                min_upvotes=query.min_upvotes,
                max_upvotes=query.max_upvotes,
                tags=query.tags,
                date_from=query.date_from,
                date_to=query.date_to,
                limit=query.limit,
                offset=query.offset,
            )

            # Convert to SearchResult objects
            results = self._convert_to_search_results(raw_results)

            # Load tags in batch for better performance
            self._load_tags_batch(results)

            # Cache results
            if self.enable_cache:
                self._query_cache.put(query, raw_results)

            query_time = time.time() - start_time
            self.analytics.record_search(query, query_time, cache_hit)

            logger.debug(
                "Search completed in %.3f seconds, returned %d results",
                query_time,
                len(results),
            )
            return results

        except Exception as e:
            logger.error("Optimized search failed: %s", e)
            query_time = time.time() - start_time
            self.analytics.record_search(query, query_time, cache_hit)
            return []

    def search_simple(self, text: str, limit: int = 20) -> List[SearchResult]:
        """
        Perform a simple text search with optimizations (convenience method).

        Args:
            text: Search text
            limit: Maximum results to return

        Returns:
            List of SearchResult objects
        """
        query = SearchQuery(text=text, limit=limit)
        return self.search(query)

    def search_streaming(self, query: SearchQuery, batch_size: int = 100):
        """
        Generator that yields search results in batches for memory efficiency.

        Args:
            query: SearchQuery object
            batch_size: Number of results to yield per batch

        Yields:
            Batches of SearchResult objects
        """
        offset = query.offset
        original_limit = query.limit

        while True:
            # Create query for current batch
            batch_query = SearchQuery(
                text=query.text,
                subreddits=query.subreddits,
                authors=query.authors,
                tags=query.tags,
                min_upvotes=query.min_upvotes,
                max_upvotes=query.max_upvotes,
                date_from=query.date_from,
                date_to=query.date_to,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
                limit=(
                    min(batch_size, original_limit - offset)
                    if original_limit > 0
                    else batch_size
                ),
                offset=offset,
            )

            # Get batch results
            batch_results = self.search(batch_query)

            if not batch_results:
                break

            yield batch_results

            # Update offset for next batch
            offset += len(batch_results)

            # Check if we've reached the limit
            if original_limit > 0 and offset >= original_limit:
                break

            # If we got fewer results than requested, we've reached the end
            if len(batch_results) < batch_query.limit:
                break

    def get_suggestions_optimized(
        self, partial_query: str, limit: int = 10
    ) -> List[str]:
        """
        Get optimized search suggestions with caching and smart ranking.

        Args:
            partial_query: Partial search text
            limit: Maximum suggestions to return

        Returns:
            List of suggested search terms
        """
        if not partial_query or len(partial_query) < 2:
            return []

        try:
            # Validate input
            clean_query = self.validator.validate_search_query(partial_query)
            if not clean_query:
                return []

            with self.database._pool.get_connection() as conn:
                suggestions = set()  # Use set to avoid duplicates

                # Get suggestions from titles (most relevant)
                cursor = conn.execute(
                    """
                    SELECT title, upvotes 
                    FROM posts 
                    WHERE title LIKE ? 
                    ORDER BY upvotes DESC 
                    LIMIT ?
                """,
                    (f"%{clean_query}%", limit * 2),
                )

                for row in cursor.fetchall():
                    title = row[0]
                    # Extract meaningful words from title
                    words = re.findall(r"\b\w{3,}\b", title.lower())
                    for word in words:
                        if clean_query.lower() in word:
                            suggestions.add(word)
                            if len(suggestions) >= limit:
                                break
                    if len(suggestions) >= limit:
                        break

                # Get subreddit suggestions if not enough from titles
                if len(suggestions) < limit:
                    cursor = conn.execute(
                        """
                        SELECT subreddit, COUNT(*) as post_count
                        FROM posts 
                        WHERE subreddit LIKE ?
                        GROUP BY subreddit
                        ORDER BY post_count DESC
                        LIMIT ?
                    """,
                        (f"%{clean_query}%", limit - len(suggestions)),
                    )

                    for row in cursor.fetchall():
                        subreddit = row[0]
                        if subreddit:
                            suggestions.add(subreddit)

                # Convert to list and limit results
                result = list(suggestions)[:limit]

                logger.debug(
                    "Generated %d suggestions for query '%s'",
                    len(result),
                    partial_query,
                )
                return result

        except Exception as e:
            logger.error("Failed to get optimized suggestions: %s", e)
            return []

    def get_popular_searches_optimized(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get popular search terms with enhanced analytics.

        Args:
            limit: Maximum results to return

        Returns:
            List of popular search term dictionaries
        """
        try:
            with self.database._pool.get_connection() as conn:
                popular = []

                # Most active subreddits by post count and engagement
                cursor = conn.execute(
                    """
                    SELECT 
                        subreddit,
                        COUNT(*) as post_count,
                        SUM(upvotes) as total_upvotes,
                        AVG(upvotes) as avg_upvotes,
                        COUNT(DISTINCT author) as unique_authors
                    FROM posts 
                    WHERE subreddit IS NOT NULL 
                    GROUP BY subreddit 
                    HAVING post_count > 1
                    ORDER BY (post_count * 0.4 + total_upvotes * 0.4 + unique_authors * 0.2) DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                for row in cursor.fetchall():
                    popular.append(
                        {
                            "term": row[0],
                            "type": "subreddit",
                            "post_count": row[1],
                            "total_upvotes": row[2],
                            "avg_upvotes": round(row[3], 2),
                            "unique_authors": row[4],
                            "engagement_score": round(
                                row[1] * 0.4 + row[2] * 0.4 + row[4] * 0.2, 2
                            ),
                        }
                    )

                return popular

        except Exception as e:
            logger.error("Failed to get optimized popular searches: %s", e)
            return []

    def get_search_stats(self) -> Dict[str, Any]:
        """Get combined database and search engine statistics."""
        db_stats = self.database.get_stats_cached()
        engine_stats = self.analytics.get_stats()

        return {"database": db_stats, "search_engine": engine_stats}

    def warm_cache(self, common_queries: List[SearchQuery] = None):
        """
        Pre-warm the cache with common queries for better performance.

        Args:
            common_queries: List of common queries to cache. If None, generates default set.
        """
        if not self.enable_cache:
            return

        logger.info("Warming search cache...")

        if common_queries is None:
            # Generate common queries based on popular content
            common_queries = self._generate_common_queries()

        for query in common_queries:
            try:
                # Execute search to populate cache
                self.search(query)
                logger.debug("Cached query: %s", query.text)
            except Exception as e:
                logger.warning("Failed to cache query: %s", e)

        logger.info("Cache warming completed")

    def clear_cache(self):
        """Clear all cached results."""
        if self.enable_cache:
            self._query_cache.clear()
            logger.info("Search cache cleared")

    def _convert_to_search_results(
        self, raw_results: List[Dict[str, Any]]
    ) -> List[SearchResult]:
        """Convert raw database results to SearchResult objects."""
        results = []
        for row in raw_results:
            result = SearchResult(
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
            results.append(result)
        return results

    def _load_tags_batch(self, results: List[SearchResult]):
        """Load tags for all results in a single batch query to avoid N+1 problem."""
        if not results:
            return

        try:
            # Get all post IDs
            post_ids = [result.post_id for result in results]

            with self.database._pool.get_connection() as conn:
                # Build query for all post IDs at once
                placeholders = ",".join(["?" for _ in post_ids])
                cursor = conn.execute(
                    f"""
                    SELECT p.post_id, t.name 
                    FROM posts p
                    JOIN post_tags pt ON p.id = pt.post_id
                    JOIN tags t ON pt.tag_id = t.id
                    WHERE p.post_id IN ({placeholders})
                    ORDER BY p.post_id, t.name
                """,
                    post_ids,
                )

                # Group tags by post ID
                tags_by_post = defaultdict(list)
                for row in cursor.fetchall():
                    tags_by_post[row[0]].append(row[1])

                # Assign tags to results
                for result in results:
                    result.tags = tags_by_post.get(result.post_id, [])

        except Exception as e:
            logger.error("Failed to load tags in batch: %s", e)
            # Fallback: set empty tags for all results
            for result in results:
                result.tags = []

    def _generate_common_queries(self) -> List[SearchQuery]:
        """Generate common queries for cache warming."""
        common_queries = []

        # Popular subreddit queries
        popular_subreddits = [
            "r/Python",
            "r/programming",
            "r/MachineLearning",
            "r/datascience",
        ]
        for subreddit in popular_subreddits:
            common_queries.append(SearchQuery(subreddits=[subreddit], limit=20))

        # Common search terms
        common_terms = ["tutorial", "guide", "python", "javascript", "machine learning"]
        for term in common_terms:
            common_queries.append(SearchQuery(text=term, limit=20))

        # High upvote threshold queries
        common_queries.append(SearchQuery(min_upvotes=100, limit=50))
        common_queries.append(SearchQuery(min_upvotes=500, limit=20))

        return common_queries
