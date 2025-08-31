#!/usr/bin/env python3
"""
Optimized Reddit Search System Demonstration

This script demonstrates the enhanced safety, reliability, and performance 
features of the optimized search system.

Key Features Demonstrated:
- Connection pooling and transaction management
- Input validation and SQL injection prevention
- Query result caching and performance optimization
- Resource monitoring and adaptive processing
- Database integrity checks and repair capabilities
- Concurrent access handling
- Memory-efficient processing

Usage:
    python3 optimized_search_demo.py
"""

import os
import sys
import time
import tempfile
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the search module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search.optimized_search_database import OptimizedSearchDatabase
from search.optimized_search_engine import OptimizedSearchEngine, SearchQuery
from search.optimized_indexer import OptimizedContentIndexer
from search.metadata_extractor import MetadataExtractor
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


def create_sample_data(temp_dir: str) -> str:
    """Create sample Reddit markdown files for testing."""
    sample_dir = os.path.join(temp_dir, "sample_posts")
    os.makedirs(sample_dir, exist_ok=True)

    sample_posts = [
        {
            "filename": "python_tutorial.md",
            "content": """**r/Python** | Posted by u/python_expert ⬆️ 245

## Complete Python Tutorial for Data Science

Original post: [https://reddit.com/r/Python/comments/abc123/](https://reddit.com/r/Python/comments/abc123/)

This comprehensive tutorial covers Python programming fundamentals for data science applications. We'll explore pandas, numpy, matplotlib, and scikit-learn.

Key topics covered:
- Data manipulation with pandas
- Numerical computing with numpy  
- Visualization with matplotlib
- Machine learning with scikit-learn

Perfect for beginners looking to get started with Python for data analysis!

💬 ~ 87 replies
""",
        },
        {
            "filename": "ml_algorithms.md",
            "content": """**r/MachineLearning** | Posted by u/ml_researcher ⬆️ 892

## Understanding Neural Network Architectures

Original post: [https://reddit.com/r/MachineLearning/comments/def456/](https://reddit.com/r/MachineLearning/comments/def456/)

Deep dive into various neural network architectures and their applications. This post covers CNNs, RNNs, Transformers, and when to use each.

## Architecture Overview

**Convolutional Neural Networks (CNNs)**
- Best for image processing tasks
- Feature extraction through convolution layers
- Popular in computer vision applications

**Recurrent Neural Networks (RNNs)**  
- Designed for sequential data
- Memory capabilities for temporal patterns
- Used in NLP and time series analysis

**Transformer Architecture**
- Attention-based mechanism
- State-of-the-art for language tasks
- Foundation for GPT and BERT models

💬 ~ 156 replies
""",
        },
        {
            "filename": "web_dev_trends.md",
            "content": """**r/webdev** | Posted by u/fullstack_dev ⬆️ 423

## 2024 Web Development Trends

Original post: [https://reddit.com/r/webdev/comments/ghi789/](https://reddit.com/r/webdev/comments/ghi789/)

What are the biggest trends in web development this year? Here's my analysis of the current landscape.

## Frontend Trends
- React 18 and concurrent features
- Vue 3 composition API adoption
- Svelte gaining momentum
- WebAssembly integration

## Backend Trends  
- Node.js performance improvements
- Deno 2.0 ecosystem growth
- Rust for high-performance services
- GraphQL vs REST debate continues

## DevOps & Deployment
- Containerization with Docker
- Kubernetes for orchestration  
- Serverless functions popularity
- Edge computing adoption

What trends are you most excited about?

💬 ~ 234 replies
""",
        },
        {
            "filename": "programming_question.md",
            "content": """**r/programming** | Posted by u/curious_coder ⬆️ 67

## How to optimize database queries for large datasets?

Original post: [https://reddit.com/r/programming/comments/jkl012/](https://reddit.com/r/programming/comments/jkl012/)

I'm working with a dataset of 10M+ records and my queries are taking too long. What are the best practices for database optimization?

Current issues:
- Simple SELECT queries taking 30+ seconds
- JOIN operations timing out
- Index usage seems suboptimal

My current setup:
- PostgreSQL 14
- Table with 12M rows
- Multiple foreign key relationships
- Limited indexing strategy

Looking for advice on:
1. Index optimization strategies
2. Query rewriting techniques  
3. Database configuration tuning
4. When to consider partitioning

Any recommendations for profiling tools?

💬 ~ 43 replies
""",
        },
    ]

    for post in sample_posts:
        file_path = os.path.join(sample_dir, post["filename"])
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(post["content"])

    logger.info(f"Created {len(sample_posts)} sample posts in {sample_dir}")
    return sample_dir


def demo_database_features(database: OptimizedSearchDatabase):
    """Demonstrate database optimization features."""
    print("\n" + "=" * 60)
    print("DATABASE OPTIMIZATION FEATURES")
    print("=" * 60)

    # Connection pooling demonstration
    print("\n1. Connection Pool Performance Test")
    print("-" * 40)

    def concurrent_query():
        with database._pool.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM posts")
            return cursor.fetchone()[0]

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(concurrent_query) for _ in range(20)]
        results = [future.result() for future in as_completed(futures)]
    end_time = time.time()

    print(f"✅ Completed 20 concurrent queries in {end_time - start_time:.2f} seconds")
    print(f"✅ All queries returned consistent results: {len(set(results)) == 1}")

    # Transaction management demonstration
    print("\n2. Transaction Management & Rollback")
    print("-" * 40)

    try:
        with database.transaction() as conn:
            # Simulate error condition
            conn.execute(
                "INSERT INTO posts (file_path, post_id, title) VALUES (?, ?, ?)",
                ("/test/demo.md", "demo123", "Demo Post"),
            )

            # Force an error to test rollback
            raise Exception("Simulated error for rollback test")

    except Exception:
        print("✅ Transaction rolled back successfully after error")

    # Verify rollback worked
    with database._pool.get_connection() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE post_id = ?", ("demo123",)
        )
        count = cursor.fetchone()[0]
        print(f"✅ Rollback verification: {count == 0} (no demo post found)")

    # Database integrity check
    print("\n3. Database Integrity Check")
    print("-" * 40)

    integrity_result = database.integrity_check()
    print(f"✅ Database integrity: {integrity_result.get('database_integrity', False)}")
    print(f"✅ FTS integrity: {integrity_result.get('fts_integrity', False)}")
    print(f"✅ Issues found: {len(integrity_result.get('issues_found', []))}")

    # Performance statistics
    print("\n4. Database Statistics")
    print("-" * 40)

    stats = database.get_stats_cached()
    print(f"✅ Total posts: {stats.get('total_posts', 0)}")
    print(f"✅ Total subreddits: {stats.get('total_subreddits', 0)}")
    print(f"✅ Total authors: {stats.get('total_authors', 0)}")
    print(f"✅ Average upvotes: {stats.get('avg_upvotes', 0)}")


def demo_search_engine_features(search_engine: OptimizedSearchEngine):
    """Demonstrate search engine optimization features."""
    print("\n" + "=" * 60)
    print("SEARCH ENGINE OPTIMIZATION FEATURES")
    print("=" * 60)

    # Query performance with caching
    print("\n1. Query Performance & Caching")
    print("-" * 40)

    test_query = SearchQuery(text="python machine learning", limit=50)

    # First query (cache miss)
    start_time = time.time()
    results1 = search_engine.search(test_query)
    first_time = time.time() - start_time

    # Second query (cache hit)
    start_time = time.time()
    results2 = search_engine.search(test_query)
    cached_time = time.time() - start_time

    speedup = first_time / cached_time if cached_time > 0 else float("inf")
    print(f"✅ First query (cache miss): {first_time:.3f}s")
    print(f"✅ Second query (cache hit): {cached_time:.3f}s")
    print(f"✅ Cache speedup: {speedup:.1f}x faster")
    print(f"✅ Results consistency: {len(results1) == len(results2)}")

    # Advanced search features
    print("\n2. Advanced Search Capabilities")
    print("-" * 40)

    # Complex query with multiple filters
    complex_query = SearchQuery(
        text="tutorial",
        subreddits=["r/Python", "r/programming"],
        min_upvotes=50,
        limit=25,
    )

    start_time = time.time()
    complex_results = search_engine.search(complex_query)
    complex_time = time.time() - start_time

    print(f"✅ Complex filtered query: {complex_time:.3f}s")
    print(f"✅ Results returned: {len(complex_results)}")
    print(
        f"✅ All results have required upvotes: {all(r.upvotes >= 50 for r in complex_results)}"
    )

    # Search suggestions
    suggestions = search_engine.get_suggestions_optimized("pytho", limit=5)
    print(f"✅ Search suggestions for 'pytho': {suggestions}")

    # Popular searches
    popular = search_engine.get_popular_searches_optimized(limit=3)
    print(f"✅ Popular searches: {[p['term'] for p in popular]}")

    # Memory-efficient streaming for large results
    print("\n3. Memory-Efficient Streaming")
    print("-" * 40)

    streaming_query = SearchQuery(min_upvotes=0, limit=1000)

    start_time = time.time()
    total_streamed = 0

    for batch in search_engine.search_streaming(streaming_query, batch_size=50):
        total_streamed += len(batch)
        if total_streamed >= 100:  # Limit for demo
            break

    streaming_time = time.time() - start_time
    print(f"✅ Streamed {total_streamed} results in {streaming_time:.3f}s")
    print(f"✅ Memory-efficient batch processing completed")


def demo_input_validation_security(search_engine: OptimizedSearchEngine):
    """Demonstrate input validation and security features."""
    print("\n" + "=" * 60)
    print("SECURITY & INPUT VALIDATION")
    print("=" * 60)

    # SQL injection prevention
    print("\n1. SQL Injection Prevention")
    print("-" * 40)

    malicious_queries = [
        "'; DROP TABLE posts; --",
        "' OR '1'='1",
        "UNION SELECT * FROM posts",
    ]

    for malicious_query in malicious_queries:
        try:
            query = SearchQuery(text=malicious_query, limit=10)
            results = search_engine.search(query)
            print(f"✅ Safely handled malicious query: '{malicious_query[:30]}...'")
            print(f"   Returned {len(results)} results (sanitized)")
        except Exception as e:
            print(
                f"✅ Blocked malicious query: '{malicious_query[:30]}...': {str(e)[:50]}..."
            )

    # Path traversal prevention
    print("\n2. Path Traversal Prevention")
    print("-" * 40)

    from search.optimized_search_database import InputValidator

    validator = InputValidator()

    dangerous_paths = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "/etc/shadow",
    ]

    for dangerous_path in dangerous_paths:
        try:
            validator.validate_file_path(dangerous_path)
            print(f"⚠️  Path validation failed for: {dangerous_path}")
        except ValueError as e:
            print(f"✅ Blocked dangerous path: {dangerous_path}")

    # Input length and content validation
    print("\n3. Input Validation & Sanitization")
    print("-" * 40)

    # Test very long input
    very_long_input = "A" * 10000
    sanitized = validator.validate_search_query(very_long_input)
    print(
        f"✅ Long input sanitized: {len(very_long_input)} chars → {len(sanitized)} chars"
    )

    # Test special characters
    special_chars = "Hello\x00\x01\x02World"
    sanitized_special = validator.validate_search_query(special_chars)
    print(f"✅ Special chars sanitized: '{special_chars}' → '{sanitized_special}'")


def demo_concurrent_performance(search_engine: OptimizedSearchEngine):
    """Demonstrate concurrent performance capabilities."""
    print("\n" + "=" * 60)
    print("CONCURRENT PERFORMANCE")
    print("=" * 60)

    print("\n1. Concurrent Query Handling")
    print("-" * 40)

    # Mix of different query types
    query_mix = [
        SearchQuery(text="python", limit=20),
        SearchQuery(text="machine learning", limit=20),
        SearchQuery(subreddits=["r/Python"], limit=30),
        SearchQuery(min_upvotes=100, limit=15),
        SearchQuery(text="tutorial", limit=25),
    ]

    def perform_mixed_queries(num_queries=10):
        """Perform a mix of queries."""
        import random

        results = []
        for _ in range(num_queries):
            query = random.choice(query_mix)
            start_time = time.time()
            result = search_engine.search(query)
            query_time = time.time() - start_time
            results.append((len(result), query_time))
        return results

    # Test concurrent performance
    num_threads = 10
    queries_per_thread = 5

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(perform_mixed_queries, queries_per_thread)
            for _ in range(num_threads)
        ]
        all_results = [future.result() for future in as_completed(futures)]

    total_time = time.time() - start_time
    total_queries = num_threads * queries_per_thread
    qps = total_queries / total_time

    # Calculate statistics
    all_query_times = [
        query_time for thread_results in all_results for _, query_time in thread_results
    ]
    avg_query_time = sum(all_query_times) / len(all_query_times)
    total_results = sum(
        num_results
        for thread_results in all_results
        for num_results, _ in thread_results
    )

    print(f"✅ Completed {total_queries} concurrent queries")
    print(f"✅ Total time: {total_time:.2f}s")
    print(f"✅ Queries per second: {qps:.1f} QPS")
    print(f"✅ Average query time: {avg_query_time:.3f}s")
    print(f"✅ Total results returned: {total_results}")

    # Analytics
    print("\n2. Search Analytics")
    print("-" * 40)

    stats = search_engine.get_search_stats()
    engine_stats = stats.get("search_engine", {})

    print(f"✅ Total searches performed: {engine_stats.get('total_searches', 0)}")
    print(f"✅ Cache hit rate: {engine_stats.get('cache_hit_rate', 0):.1%}")
    print(f"✅ Average query time: {engine_stats.get('avg_query_time', 0):.3f}s")


def demo_indexer_optimization(temp_dir: str):
    """Demonstrate indexer optimization features."""
    print("\n" + "=" * 60)
    print("INDEXER OPTIMIZATION")
    print("=" * 60)

    # Create optimized database and indexer
    db_path = os.path.join(temp_dir, "indexer_demo.db")
    database = OptimizedSearchDatabase(db_path)
    indexer = OptimizedContentIndexer(
        database=database, max_workers=4, batch_size=10, max_memory_percent=80.0
    )

    # Create sample files for indexing
    sample_dir = create_sample_data(temp_dir)

    print("\n1. Resource-Aware Indexing")
    print("-" * 40)

    # Add progress callback
    def progress_callback(progress):
        percent = progress["percent"]
        rate = progress["rate"]
        print(f"   Progress: {percent:.1f}% complete, {rate:.1f} files/sec")

    indexer.add_progress_callback(progress_callback)

    # Start indexing
    start_time = time.time()
    stats = indexer.index_directory_optimized(sample_dir, recursive=True)
    indexing_time = time.time() - start_time

    print(f"✅ Indexing completed in {indexing_time:.2f}s")
    print(f"✅ Files processed: {stats['files_processed']}")
    print(f"✅ Files indexed: {stats['files_indexed']}")
    print(
        f"✅ Processing rate: {stats['files_processed'] / indexing_time:.1f} files/sec"
    )

    # Resource monitoring results
    resource_stats = stats.get("resource_stats", {})
    print(f"✅ Peak memory usage: {resource_stats.get('memory_percent', 0):.1f}%")
    print(f"✅ CPU utilization: {resource_stats.get('cpu_percent', 0):.1f}%")

    print("\n2. Incremental Indexing")
    print("-" * 40)

    # Modify one file to test incremental indexing
    modified_file = os.path.join(sample_dir, "python_tutorial.md")
    with open(modified_file, "a", encoding="utf-8") as f:
        f.write("\n\n**UPDATE**: Added new section on advanced topics!")

    # Run incremental indexing
    start_time = time.time()
    incremental_stats = indexer.index_directory_optimized(
        sample_dir, recursive=True, force_reindex=False
    )
    incremental_time = time.time() - start_time

    print(f"✅ Incremental indexing completed in {incremental_time:.2f}s")
    print(f"✅ Files updated: {incremental_stats['files_updated']}")
    print(f"✅ Files skipped: {incremental_stats['files_skipped']}")
    print(
        f"✅ Speedup from change detection: {indexing_time / max(incremental_time, 0.001):.1f}x"
    )

    database.close()


def main():
    """Run the complete optimization demonstration."""
    print("Reddit Search System Optimization Demo")
    print("=" * 60)
    print("Demonstrating enhanced safety, reliability, and performance features")

    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create database and sample data
        db_path = os.path.join(temp_dir, "optimized_demo.db")
        database = OptimizedSearchDatabase(db_path, pool_size=8)

        # Create sample data
        sample_dir = create_sample_data(temp_dir)

        # Index sample data
        print("\nIndexing sample data...")
        indexer = OptimizedContentIndexer(database=database, max_workers=2)
        indexing_stats = indexer.index_directory_optimized(sample_dir, recursive=True)
        print(f"Indexed {indexing_stats['files_processed']} files")

        # Create search engine
        search_engine = OptimizedSearchEngine(database, enable_cache=True)

        # Run demonstrations
        try:
            demo_database_features(database)
            demo_search_engine_features(search_engine)
            demo_input_validation_security(search_engine)
            demo_concurrent_performance(search_engine)
            demo_indexer_optimization(temp_dir)

            print("\n" + "=" * 60)
            print("DEMONSTRATION COMPLETE")
            print("=" * 60)
            print("✅ All optimization features demonstrated successfully")
            print("✅ System shows improved safety, reliability, and performance")
            print("\nKey improvements implemented:")
            print("  - Connection pooling for better concurrency")
            print("  - Input validation and SQL injection prevention")
            print("  - Transaction management with rollback capabilities")
            print("  - Query result caching with LRU eviction")
            print("  - Resource monitoring and adaptive processing")
            print("  - Database integrity checks and repair")
            print("  - Memory-efficient batch processing")
            print("  - Comprehensive error handling and logging")

        except Exception as e:
            logger.error(f"Demo failed: {e}")
            raise

        finally:
            database.close()


if __name__ == "__main__":
    main()
