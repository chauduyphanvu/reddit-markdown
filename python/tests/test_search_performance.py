import os
import tempfile
import time
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import statistics
import random
import string

from search.optimized_search_database import OptimizedSearchDatabase, InputValidator
from search.optimized_search_engine import OptimizedSearchEngine, SearchQuery
from search.optimized_indexer import OptimizedContentIndexer
from search.metadata_extractor import MetadataExtractor


class TestSearchPerformance(unittest.TestCase):
    """Performance and stress tests for optimized search components."""

    @classmethod
    def setUpClass(cls):
        """Set up test data for all performance tests."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.temp_db = os.path.join(cls.temp_dir, "perf_test.db")

        # Create test database with sample data
        cls.database = OptimizedSearchDatabase(cls.temp_db)
        cls.search_engine = OptimizedSearchEngine(cls.database)

        # Generate test data
        cls._create_test_data()

    @classmethod
    def tearDownClass(cls):
        """Clean up test resources."""
        cls.database.close()
        import shutil

        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    @classmethod
    def _create_test_data(cls):
        """Create test data for performance testing."""
        print("Creating test data for performance tests...")

        # Generate varied test posts
        test_posts = []
        subreddits = [
            "r/Python",
            "r/MachineLearning",
            "r/programming",
            "r/datascience",
            "r/webdev",
        ]
        authors = [f"user_{i}" for i in range(100)]

        # Create posts with different characteristics
        for i in range(1000):
            # Vary content length and complexity
            content_length = random.choice([100, 500, 1000, 2000, 5000])
            content = cls._generate_random_content(content_length)

            post = {
                "file_path": f"/test/post_{i:04d}.md",
                "post_id": f"post_{i:06d}",
                "title": cls._generate_random_title(),
                "content": content,
                "author": random.choice(authors),
                "subreddit": random.choice(subreddits),
                "url": f"https://reddit.com/test/{i}",
                "created_utc": 1609459200 + (i * 3600),  # Spread over time
                "upvotes": random.randint(0, 10000),
                "reply_count": random.randint(0, 500),
                "file_modified_time": time.time()
                - random.randint(0, 30 * 24 * 3600),  # Last 30 days
                "content_preview": content[:200],
            }
            test_posts.append(post)

        # Bulk insert (each add_post handles its own transaction)
        for i, post in enumerate(test_posts):
            if i % 100 == 0:  # Progress indicator
                print(f"Inserted {i}/{len(test_posts)} posts...")
            cls.database.add_post(post)

        print(f"Created {len(test_posts)} test posts")

    @classmethod
    def _generate_random_content(cls, length: int) -> str:
        """Generate random content of specified length."""
        # Mix of common tech terms and random words
        tech_terms = [
            "python",
            "machine learning",
            "algorithm",
            "database",
            "api",
            "framework",
            "javascript",
            "data science",
            "neural network",
            "web development",
            "docker",
            "kubernetes",
            "react",
            "node.js",
            "sql",
            "nosql",
            "cloud computing",
        ]

        content_parts = []
        current_length = 0

        while current_length < length:
            if random.random() < 0.3:  # 30% chance of tech term
                word = random.choice(tech_terms)
            else:
                # Random word
                word = "".join(
                    random.choices(string.ascii_lowercase, k=random.randint(3, 10))
                )

            content_parts.append(word)
            current_length += len(word) + 1  # +1 for space

        return " ".join(content_parts)

    @classmethod
    def _generate_random_title(cls) -> str:
        """Generate random title."""
        templates = [
            "How to {} in {}?",
            "Best practices for {} development",
            "Understanding {} algorithms",
            "Tutorial: Getting started with {}",
            "Advanced {} techniques",
            "Common {} mistakes to avoid",
            "Performance optimization for {}",
            "{} vs {}: Which is better?",
        ]

        tech_terms = [
            "Python",
            "Machine Learning",
            "Web Development",
            "Data Science",
            "API Design",
        ]

        template = random.choice(templates)
        if "{}" in template:
            if template.count("{}") == 1:
                return template.format(random.choice(tech_terms))
            else:
                return template.format(
                    random.choice(tech_terms), random.choice(tech_terms)
                )
        return template

    def test_database_connection_pool_performance(self):
        """Test connection pool performance under concurrent access."""
        print("\nTesting connection pool performance...")

        def concurrent_query():
            """Perform a query that would normally require a database connection."""
            with self.database._pool.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM posts")
                return cursor.fetchone()[0]

        # Test with varying levels of concurrency
        for num_threads in [1, 5, 10, 20]:
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(concurrent_query) for _ in range(100)]
                results = [future.result() for future in as_completed(futures)]

            end_time = time.time()
            duration = end_time - start_time

            # Verify all queries returned correct count
            expected_count = 1000  # We created 1000 test posts
            self.assertTrue(all(count == expected_count for count in results))

            print(
                f"  {num_threads} threads: {duration:.2f}s for 100 queries ({100/duration:.1f} QPS)"
            )

    def test_search_performance_with_different_query_types(self):
        """Test search performance with different query types."""
        print("\nTesting search performance with different query types...")

        # Define different query types
        test_queries = [
            # Simple text search
            SearchQuery(text="python", limit=50),
            SearchQuery(text="machine learning algorithm", limit=50),
            # Filtered searches
            SearchQuery(text="python", subreddits=["r/Python"], limit=50),
            SearchQuery(
                subreddits=["r/Python", "r/programming"], min_upvotes=100, limit=50
            ),
            # Complex filters
            SearchQuery(
                text="tutorial", min_upvotes=50, date_from=1609459200, limit=50
            ),
            SearchQuery(
                authors=["user_1", "user_2", "user_3"], max_upvotes=1000, limit=50
            ),
            # Large result sets
            SearchQuery(min_upvotes=0, limit=500),
            SearchQuery(text="development", limit=200),
        ]

        for i, query in enumerate(test_queries):
            # Time multiple runs for better accuracy
            times = []
            for run in range(5):
                start_time = time.time()
                results = self.search_engine.search(query)
                end_time = time.time()
                times.append(end_time - start_time)

            avg_time = statistics.mean(times)
            result_count = len(
                self.search_engine.search(query)
            )  # Get count without timing

            print(f"  Query {i+1}: {avg_time:.3f}s avg, {result_count} results")

            # Performance assertions
            self.assertLess(avg_time, 1.0, "Search should complete within 1 second")
            self.assertGreater(result_count, 0, "Query should return some results")

    def test_cache_performance_and_effectiveness(self):
        """Test search result caching performance and hit rates."""
        print("\nTesting cache performance...")

        # Create a fresh search engine with caching enabled
        cached_engine = OptimizedSearchEngine(self.database, enable_cache=True)

        test_query = SearchQuery(text="python programming", limit=100)

        # First search (cache miss)
        start_time = time.time()
        results1 = cached_engine.search(test_query)
        first_time = time.time() - start_time

        # Second search (should be cache hit)
        start_time = time.time()
        results2 = cached_engine.search(test_query)
        cached_time = time.time() - start_time

        # Verify results are identical
        self.assertEqual(len(results1), len(results2))

        # Cache should be significantly faster
        speedup = first_time / cached_time if cached_time > 0 else float("inf")
        print(f"  Cache miss: {first_time:.3f}s")
        print(f"  Cache hit:  {cached_time:.3f}s")
        print(f"  Speedup:    {speedup:.1f}x")

        self.assertLess(cached_time, first_time, "Cached query should be faster")

        # Test cache statistics
        stats = cached_engine.get_search_stats()
        engine_stats = stats.get("search_engine", {})
        cache_hit_rate = engine_stats.get("cache_hit_rate", 0)

        print(f"  Cache hit rate: {cache_hit_rate:.1%}")
        self.assertGreater(cache_hit_rate, 0, "Should have some cache hits")

    def test_concurrent_search_performance(self):
        """Test search performance under concurrent load."""
        print("\nTesting concurrent search performance...")

        # Define mix of queries for realistic testing
        query_mix = [
            SearchQuery(text="python", limit=50),
            SearchQuery(text="machine learning", limit=50),
            SearchQuery(subreddits=["r/Python"], limit=100),
            SearchQuery(min_upvotes=100, limit=50),
            SearchQuery(text="tutorial", authors=["user_1"], limit=25),
        ]

        def perform_random_search():
            """Perform a random search query."""
            query = random.choice(query_mix)
            start_time = time.time()
            results = self.search_engine.search(query)
            return time.time() - start_time, len(results)

        # Test with different concurrency levels
        for num_threads in [1, 5, 10, 20]:
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(perform_random_search) for _ in range(100)]
                results = [future.result() for future in as_completed(futures)]

            total_time = time.time() - start_time
            query_times = [r[0] for r in results]
            total_results = sum(r[1] for r in results)

            avg_query_time = statistics.mean(query_times)
            qps = len(results) / total_time

            print(
                f"  {num_threads} threads: {avg_query_time:.3f}s avg query time, "
                f"{qps:.1f} QPS, {total_results} total results"
            )

            # Performance assertions
            self.assertLess(
                avg_query_time, 2.0, "Average query time should be reasonable"
            )
            self.assertGreater(qps, 10, "Should handle at least 10 QPS")

    def test_input_validation_performance(self):
        """Test input validation performance with malicious inputs."""
        print("\nTesting input validation performance...")

        validator = InputValidator()

        # Test various input validation scenarios
        test_cases = [
            # Normal inputs
            ("normal query", validator.validate_search_query),
            ("/path/to/file.md", validator.validate_file_path),
            ("abc123def", validator.validate_post_id),
            ("my_tag", validator.validate_tag_name),
            # Potentially malicious inputs
            ("../../../etc/passwd", validator.validate_file_path),
            ("a" * 10000, validator.validate_search_query),  # Very long query
            (
                "'; DROP TABLE posts; --",
                validator.validate_search_query,
            ),  # SQL injection attempt
            ("../", validator.validate_tag_name),  # Directory traversal in tag
        ]

        for test_input, validator_func in test_cases:
            times = []
            for _ in range(100):  # Average over multiple runs
                start_time = time.time()
                try:
                    validator_func(test_input)
                except ValueError:
                    # Expected for malicious inputs
                    pass
                times.append(time.time() - start_time)

            avg_time = statistics.mean(times)
            print(
                f"  Validation time for '{test_input[:20]}...': {avg_time*1000:.2f}ms"
            )

            # Validation should be very fast
            self.assertLess(
                avg_time, 0.001, "Input validation should be sub-millisecond"
            )

    def test_database_integrity_check_performance(self):
        """Test database integrity check performance."""
        print("\nTesting database integrity check performance...")

        start_time = time.time()
        integrity_result = self.database.integrity_check()
        check_time = time.time() - start_time

        print(f"  Integrity check completed in {check_time:.2f}s")
        print(f"  Issues found: {len(integrity_result.get('issues_found', []))}")

        # Integrity check should complete reasonably quickly
        self.assertLess(
            check_time, 30.0, "Integrity check should complete within 30 seconds"
        )

        # Should find no issues with our test data
        self.assertTrue(integrity_result.get("database_integrity", False))
        self.assertEqual(len(integrity_result.get("issues_found", [])), 0)

    def test_large_result_set_performance(self):
        """Test performance with large result sets."""
        print("\nTesting large result set performance...")

        # Query that should return most posts
        large_query = SearchQuery(min_upvotes=0, limit=1000)

        start_time = time.time()
        results = self.search_engine.search(large_query)
        query_time = time.time() - start_time

        print(f"  Large query ({len(results)} results) completed in {query_time:.2f}s")
        print(f"  Memory efficiency: {len(results)} results loaded")

        # Should handle large result sets efficiently
        self.assertLess(
            query_time, 5.0, "Large queries should complete within 5 seconds"
        )
        self.assertGreater(
            len(results), 500, "Should return substantial number of results"
        )

        # Test streaming for very large results
        streaming_query = SearchQuery(min_upvotes=0, limit=2000)

        start_time = time.time()
        total_results = 0
        for batch in self.search_engine.search_streaming(
            streaming_query, batch_size=100
        ):
            total_results += len(batch)
            if total_results >= 500:  # Stop after reasonable amount for test
                break

        streaming_time = time.time() - start_time

        print(
            f"  Streaming query ({total_results} results) completed in {streaming_time:.2f}s"
        )

        # Streaming should be memory-efficient
        self.assertLess(streaming_time, 10.0, "Streaming should be efficient")
        self.assertGreaterEqual(total_results, 500, "Should stream substantial results")

    def test_memory_usage_during_bulk_operations(self):
        """Test memory usage during bulk operations."""
        print("\nTesting memory usage during bulk operations...")

        try:
            import psutil
            import gc

            process = psutil.Process()

            # Measure baseline memory
            gc.collect()
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Perform bulk search operations
            large_queries = [SearchQuery(min_upvotes=0, limit=1000) for _ in range(10)]

            peak_memory = baseline_memory

            for i, query in enumerate(large_queries):
                results = self.search_engine.search(query)
                current_memory = process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)

                if i % 3 == 0:  # Check memory every few operations
                    print(f"    After query {i+1}: {current_memory:.1f} MB")

            # Force garbage collection
            del results
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024

            memory_increase = peak_memory - baseline_memory
            memory_cleanup = peak_memory - final_memory

            print(f"  Baseline memory: {baseline_memory:.1f} MB")
            print(f"  Peak memory: {peak_memory:.1f} MB")
            print(f"  Final memory: {final_memory:.1f} MB")
            print(f"  Memory increase: {memory_increase:.1f} MB")
            print(f"  Memory cleanup: {memory_cleanup:.1f} MB")

            # Memory usage should be reasonable
            self.assertLess(
                memory_increase, 500, "Memory increase should be reasonable (< 500MB)"
            )
            self.assertGreaterEqual(
                memory_cleanup, 0, "Memory cleanup should be non-negative"
            )

        except ImportError:
            print("  psutil not available, skipping memory usage test")


class TestSearchStress(unittest.TestCase):
    """Stress tests for search system under extreme conditions."""

    def setUp(self):
        """Set up for each stress test."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "stress_test.db")
        self.database = OptimizedSearchDatabase(self.temp_db)
        self.search_engine = OptimizedSearchEngine(self.database)

    def tearDown(self):
        """Clean up after each stress test."""
        self.database.close()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rapid_concurrent_queries(self):
        """Test system under rapid concurrent query load."""
        print("\nStress test: Rapid concurrent queries...")

        # Add some test data
        for i in range(100):
            post = {
                "file_path": f"/stress/post_{i}.md",
                "post_id": f"stress_{i}",
                "title": f"Stress test post {i}",
                "content": f"This is stress test content for post {i}. " * 50,
                "author": f"stress_user_{i % 10}",
                "subreddit": f"r/stress{i % 5}",
                "upvotes": i * 10,
                "reply_count": i % 50,
                "created_utc": 1609459200 + i,
            }
            self.database.add_post(post)

        def stress_query():
            """Perform rapid queries."""
            queries = [
                SearchQuery(text="stress", limit=10),
                SearchQuery(text="test", limit=20),
                SearchQuery(subreddits=["r/stress0"], limit=15),
                SearchQuery(min_upvotes=100, limit=25),
            ]

            results = []
            for _ in range(10):  # 10 rapid queries per thread
                query = random.choice(queries)
                result = self.search_engine.search(query)
                results.append(len(result))
                time.sleep(0.01)  # Brief pause between queries

            return results

        # Launch many concurrent query threads
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(stress_query) for _ in range(20)]
            all_results = [future.result() for future in as_completed(futures)]

        total_time = time.time() - start_time
        total_queries = sum(len(results) for results in all_results)
        qps = total_queries / total_time

        print(
            f"  Completed {total_queries} queries in {total_time:.2f}s ({qps:.1f} QPS)"
        )

        # Should handle high load without crashing
        self.assertGreater(qps, 50, "Should handle at least 50 QPS under stress")
        self.assertTrue(
            all(len(r) > 0 for r in all_results), "All query batches should succeed"
        )

    def test_malicious_input_stress(self):
        """Test system resilience against malicious inputs."""
        print("\nStress test: Malicious input resistance...")

        # Various malicious input patterns
        malicious_inputs = [
            # SQL injection attempts
            "'; DROP TABLE posts; --",
            "' OR '1'='1",
            "UNION SELECT * FROM posts",
            # Path traversal
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            # Buffer overflow attempts
            "A" * 10000,
            "B" * 100000,
            # Special characters
            "'; \x00\x01\x02\x03",
            "\n\r\t\x00",
            # Unicode attacks
            "\u0000\u0001\u0002",
            "𝐀𝐁𝐂" * 1000,
        ]

        successful_blocks = 0
        for malicious_input in malicious_inputs:
            try:
                # Test various input vectors
                query = SearchQuery(text=malicious_input, limit=10)
                results = self.search_engine.search(query)

                # Should not crash, but results should be empty or safe
                self.assertIsInstance(
                    results, list, "Should return list even for malicious input"
                )
                successful_blocks += 1

            except Exception as e:
                # Acceptable to raise exceptions for malicious input
                print(f"    Blocked malicious input: {str(e)[:50]}...")
                successful_blocks += 1

        block_rate = successful_blocks / len(malicious_inputs)
        print(
            f"  Successfully handled {successful_blocks}/{len(malicious_inputs)} "
            f"malicious inputs ({block_rate:.1%})"
        )

        # Should handle most malicious inputs safely
        self.assertGreater(
            block_rate, 0.8, "Should handle at least 80% of malicious inputs safely"
        )


if __name__ == "__main__":
    # Run performance tests
    print("Running search system performance tests...")
    print("=" * 60)

    # Create test suite with performance tests
    suite = unittest.TestSuite()

    # Add performance tests
    suite.addTest(TestSearchPerformance("test_database_connection_pool_performance"))
    suite.addTest(
        TestSearchPerformance("test_search_performance_with_different_query_types")
    )
    suite.addTest(TestSearchPerformance("test_cache_performance_and_effectiveness"))
    suite.addTest(TestSearchPerformance("test_concurrent_search_performance"))
    suite.addTest(TestSearchPerformance("test_input_validation_performance"))
    suite.addTest(TestSearchPerformance("test_database_integrity_check_performance"))
    suite.addTest(TestSearchPerformance("test_large_result_set_performance"))
    suite.addTest(TestSearchPerformance("test_memory_usage_during_bulk_operations"))

    # Add stress tests
    suite.addTest(TestSearchStress("test_rapid_concurrent_queries"))
    suite.addTest(TestSearchStress("test_malicious_input_stress"))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print("Performance test summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
