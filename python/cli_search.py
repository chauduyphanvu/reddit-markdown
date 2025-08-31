#!/usr/bin/env python3

import argparse
import os
import sys
from datetime import datetime
from typing import List, Optional

from colored_logger import setup_colored_logging, get_colored_logger
from search import SearchDatabase, SearchEngine, TagManager, ContentIndexer, SearchQuery

logger = get_colored_logger(__name__)


class SearchCLI:
    """
    Command-line interface for Reddit-Markdown search functionality.

    Provides commands for:
    - Indexing posts from directories
    - Searching posts with various filters
    - Managing tags and tag assignments
    - Viewing search statistics
    """

    def __init__(self):
        """Initialize the search CLI."""
        self.database = SearchDatabase()
        self.search_engine = SearchEngine(self.database)
        self.tag_manager = TagManager(self.database)
        self.indexer = ContentIndexer(self.database)

    def run(self, args: List[str] = None) -> int:
        """
        Run the search CLI with the given arguments.

        Args:
            args: Command line arguments. If None, uses sys.argv.

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            parser = self._create_parser()
            parsed_args = parser.parse_args(args)

            # Set up logging level
            if hasattr(parsed_args, "verbose") and parsed_args.verbose:
                setup_colored_logging(level="DEBUG")
            else:
                setup_colored_logging(level="INFO")

            # Execute the appropriate command
            if hasattr(parsed_args, "func"):
                return parsed_args.func(parsed_args)
            else:
                parser.print_help()
                return 1

        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 1
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            return 1

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all subcommands."""
        parser = argparse.ArgumentParser(
            prog="reddit-search",
            description="Search and organize downloaded Reddit posts",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s index /path/to/posts              # Index posts in directory
  %(prog)s search "python tutorial"          # Search for posts about Python tutorials
  %(prog)s search --subreddit r/Python       # Search posts from r/Python
  %(prog)s search --author john --min-upvotes 100  # Search posts by john with 100+ upvotes
  %(prog)s tag create "favorites"            # Create a new tag called "favorites"
  %(prog)s tag apply "abc123" favorites      # Apply "favorites" tag to post abc123
  %(prog)s stats                             # Show search database statistics
            """,
        )

        # Global options
        parser.add_argument(
            "-v", "--verbose", action="store_true", help="Enable verbose logging"
        )

        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Index command
        self._add_index_parser(subparsers)

        # Search command
        self._add_search_parser(subparsers)

        # Tag commands
        self._add_tag_parser(subparsers)

        # Stats command
        self._add_stats_parser(subparsers)

        return parser

    def _add_index_parser(self, subparsers):
        """Add index subcommand parser."""
        index_parser = subparsers.add_parser(
            "index", help="Index Reddit posts for searching"
        )
        index_parser.add_argument(
            "directory", help="Directory containing Reddit markdown files"
        )
        index_parser.add_argument(
            "-r",
            "--recursive",
            action="store_true",
            help="Search subdirectories recursively",
        )
        index_parser.add_argument(
            "--force",
            action="store_true",
            help="Force reindex all files (ignore modification times)",
        )
        index_parser.add_argument(
            "--extensions",
            nargs="+",
            default=[".md", ".html"],
            help="File extensions to index (default: .md .html)",
        )
        index_parser.add_argument(
            "--max-workers",
            type=int,
            default=4,
            help="Maximum parallel workers for indexing (default: 4)",
        )
        index_parser.set_defaults(func=self._cmd_index)

    def _add_search_parser(self, subparsers):
        """Add search subcommand parser."""
        search_parser = subparsers.add_parser(
            "search", help="Search indexed Reddit posts"
        )
        search_parser.add_argument(
            "query",
            nargs="?",
            default="",
            help="Search text (leave empty to search all posts)",
        )
        search_parser.add_argument(
            "-s",
            "--subreddit",
            action="append",
            help="Filter by subreddit (can be used multiple times)",
        )
        search_parser.add_argument(
            "-a",
            "--author",
            action="append",
            help="Filter by author (can be used multiple times)",
        )
        search_parser.add_argument(
            "-t",
            "--tag",
            action="append",
            help="Filter by tag (can be used multiple times)",
        )
        search_parser.add_argument(
            "--min-upvotes", type=int, help="Minimum upvotes threshold"
        )
        search_parser.add_argument(
            "--max-upvotes", type=int, help="Maximum upvotes threshold"
        )
        search_parser.add_argument(
            "--date-from", type=str, help="Filter posts from date (YYYY-MM-DD)"
        )
        search_parser.add_argument(
            "--date-to", type=str, help="Filter posts to date (YYYY-MM-DD)"
        )
        search_parser.add_argument(
            "--sort",
            choices=["relevance", "date", "upvotes", "replies"],
            default="relevance",
            help="Sort results by (default: relevance)",
        )
        search_parser.add_argument(
            "--order",
            choices=["asc", "desc"],
            default="desc",
            help="Sort order (default: desc)",
        )
        search_parser.add_argument(
            "-l",
            "--limit",
            type=int,
            default=20,
            help="Maximum results to show (default: 20)",
        )
        search_parser.add_argument(
            "--format",
            choices=["table", "list", "json"],
            default="table",
            help="Output format (default: table)",
        )
        search_parser.set_defaults(func=self._cmd_search)

    def _add_tag_parser(self, subparsers):
        """Add tag management subcommand parser."""
        tag_parser = subparsers.add_parser("tag", help="Manage post tags")
        tag_subparsers = tag_parser.add_subparsers(
            dest="tag_action", help="Tag actions"
        )

        # Create tag
        create_parser = tag_subparsers.add_parser("create", help="Create a new tag")
        create_parser.add_argument("name", help="Tag name")
        create_parser.add_argument(
            "-d", "--description", default="", help="Tag description"
        )
        create_parser.add_argument(
            "-c", "--color", help="Tag color (hex format: #RRGGBB)"
        )
        create_parser.set_defaults(func=self._cmd_tag_create)

        # List tags
        list_parser = tag_subparsers.add_parser("list", help="List all tags")
        list_parser.add_argument(
            "-l",
            "--limit",
            type=int,
            default=50,
            help="Maximum tags to show (default: 50)",
        )
        list_parser.set_defaults(func=self._cmd_tag_list)

        # Apply tag
        apply_parser = tag_subparsers.add_parser("apply", help="Apply tag(s) to post")
        apply_parser.add_argument("post_id", help="Reddit post ID")
        apply_parser.add_argument("tags", nargs="+", help="Tag names to apply")
        apply_parser.set_defaults(func=self._cmd_tag_apply)

        # Remove tag
        remove_parser = tag_subparsers.add_parser(
            "remove", help="Remove tag(s) from post"
        )
        remove_parser.add_argument("post_id", help="Reddit post ID")
        remove_parser.add_argument(
            "tags", nargs="*", help="Tag names to remove (empty to remove all)"
        )
        remove_parser.set_defaults(func=self._cmd_tag_remove)

        # Show post tags
        show_parser = tag_subparsers.add_parser("show", help="Show tags for a post")
        show_parser.add_argument("post_id", help="Reddit post ID")
        show_parser.set_defaults(func=self._cmd_tag_show)

        # Auto-tag
        auto_parser = tag_subparsers.add_parser(
            "auto", help="Auto-tag post based on content"
        )
        auto_parser.add_argument("post_id", help="Reddit post ID")
        auto_parser.set_defaults(func=self._cmd_tag_auto)

        # Delete tag
        delete_parser = tag_subparsers.add_parser("delete", help="Delete a tag")
        delete_parser.add_argument("name", help="Tag name to delete")
        delete_parser.add_argument(
            "--confirm", action="store_true", help="Confirm deletion without prompting"
        )
        delete_parser.set_defaults(func=self._cmd_tag_delete)

    def _add_stats_parser(self, subparsers):
        """Add stats subcommand parser."""
        stats_parser = subparsers.add_parser(
            "stats", help="Show search database statistics"
        )
        stats_parser.set_defaults(func=self._cmd_stats)

    # Command implementations
    def _cmd_index(self, args) -> int:
        """Handle index command."""
        if not os.path.exists(args.directory):
            logger.error("Directory does not exist: %s", args.directory)
            return 1

        logger.info("Starting indexing of directory: %s", args.directory)

        # Configure indexer
        self.indexer.max_workers = args.max_workers

        # Start indexing
        stats = self.indexer.index_directory(
            directory=args.directory,
            recursive=args.recursive,
            file_extensions=args.extensions,
            force_reindex=args.force,
        )

        # Report results
        print(f"\nIndexing Results:")
        print(f"  Files processed: {stats['files_processed']}")
        print(f"  Files indexed: {stats['files_indexed']}")
        print(f"  Files updated: {stats['files_updated']}")
        print(f"  Files skipped: {stats['files_skipped']}")
        print(f"  Files failed: {stats['files_failed']}")
        print(f"  Time elapsed: {stats['elapsed_time']:.1f} seconds")

        if stats["files_failed"] > 0:
            print(f"  ⚠️  {stats['files_failed']} files failed to index")
            return 1

        print("  ✅ Indexing completed successfully")
        return 0

    def _cmd_search(self, args) -> int:
        """Handle search command."""
        # Build search query
        query = SearchQuery(
            text=args.query,
            subreddits=args.subreddit or [],
            authors=args.author or [],
            tags=args.tag or [],
            min_upvotes=args.min_upvotes,
            max_upvotes=args.max_upvotes,
            sort_by=args.sort,
            sort_order=args.order,
            limit=args.limit,
        )

        # Parse date filters
        if args.date_from:
            try:
                dt = datetime.strptime(args.date_from, "%Y-%m-%d")
                query.date_from = int(dt.timestamp())
            except ValueError:
                logger.error(
                    "Invalid date format for --date-from: %s (use YYYY-MM-DD)",
                    args.date_from,
                )
                return 1

        if args.date_to:
            try:
                dt = datetime.strptime(args.date_to, "%Y-%m-%d")
                query.date_to = int(dt.timestamp())
            except ValueError:
                logger.error(
                    "Invalid date format for --date-to: %s (use YYYY-MM-DD)",
                    args.date_to,
                )
                return 1

        # Perform search
        results = self.search_engine.search(query)

        # Display results
        if not results:
            print("No results found.")
            return 0

        self._display_search_results(results, args.format)
        return 0

    def _cmd_tag_create(self, args) -> int:
        """Handle tag create command."""
        tag = self.tag_manager.create_tag(
            name=args.name, description=args.description, color=args.color or ""
        )

        if tag:
            print(f"✅ Created tag: {tag.name}")
            if tag.description:
                print(f"   Description: {tag.description}")
            if tag.color:
                print(f"   Color: {tag.color}")
            return 0
        else:
            print(f"❌ Failed to create tag: {args.name}")
            return 1

    def _cmd_tag_list(self, args) -> int:
        """Handle tag list command."""
        tags = self.tag_manager.list_tags(limit=args.limit)

        if not tags:
            print("No tags found.")
            return 0

        print(f"\nFound {len(tags)} tags:")
        print(f"{'Name':<20} {'Posts':<8} {'Description':<30}")
        print("-" * 60)

        for tag in tags:
            print(f"{tag.name:<20} {tag.post_count:<8} {tag.description:<30}")

        return 0

    def _cmd_tag_apply(self, args) -> int:
        """Handle tag apply command."""
        applied_count = self.tag_manager.tag_post(args.post_id, args.tags)

        if applied_count > 0:
            print(f"✅ Applied {applied_count} tag(s) to post {args.post_id}")
            return 0
        else:
            print(f"❌ Failed to apply tags to post {args.post_id}")
            return 1

    def _cmd_tag_remove(self, args) -> int:
        """Handle tag remove command."""
        tag_names = args.tags if args.tags else None
        removed_count = self.tag_manager.untag_post(args.post_id, tag_names)

        if removed_count > 0:
            action = "all tags" if tag_names is None else f"{removed_count} tag(s)"
            print(f"✅ Removed {action} from post {args.post_id}")
            return 0
        else:
            print(f"❌ No tags removed from post {args.post_id}")
            return 1

    def _cmd_tag_show(self, args) -> int:
        """Handle tag show command."""
        tags = self.tag_manager.get_post_tags(args.post_id)

        if not tags:
            print(f"Post {args.post_id} has no tags.")
            return 0

        print(f"Tags for post {args.post_id}:")
        for tag in tags:
            print(f"  • {tag.name}")
            if tag.description:
                print(f"    {tag.description}")

        return 0

    def _cmd_tag_auto(self, args) -> int:
        """Handle tag auto command."""
        applied_tags = self.tag_manager.auto_tag_post(args.post_id)

        if applied_tags:
            print(
                f"✅ Auto-applied tags to post {args.post_id}: {', '.join(applied_tags)}"
            )
            return 0
        else:
            print(f"No auto-tags applied to post {args.post_id}")
            return 0

    def _cmd_tag_delete(self, args) -> int:
        """Handle tag delete command."""
        if not args.confirm:
            tag = self.tag_manager.get_tag(args.name)
            if tag and tag.post_count > 0:
                response = input(
                    f"Tag '{args.name}' is applied to {tag.post_count} post(s). Delete anyway? [y/N]: "
                )
                if response.lower() not in ["y", "yes"]:
                    print("Deletion cancelled.")
                    return 0

        if self.tag_manager.delete_tag(args.name):
            print(f"✅ Deleted tag: {args.name}")
            return 0
        else:
            print(f"❌ Failed to delete tag: {args.name}")
            return 1

    def _cmd_stats(self, args) -> int:
        """Handle stats command."""
        stats = self.search_engine.get_search_stats()

        if not stats:
            print("No statistics available.")
            return 0

        print("\nSearch Database Statistics:")
        print(f"  Total posts: {stats.get('total_posts', 0):,}")
        print(f"  Total tags: {stats.get('total_tags', 0):,}")
        print(f"  Total subreddits: {stats.get('total_subreddits', 0):,}")
        print(f"  Total authors: {stats.get('total_authors', 0):,}")

        return 0

    def _display_search_results(self, results, format_type: str) -> None:
        """Display search results in the specified format."""
        if format_type == "json":
            import json

            output = []
            for result in results:
                output.append(
                    {
                        "post_id": result.post_id,
                        "title": result.title,
                        "author": result.author,
                        "subreddit": result.subreddit,
                        "url": result.url,
                        "upvotes": result.upvotes,
                        "created_utc": result.created_utc,
                        "tags": result.tags,
                        "snippet": result.snippet,
                    }
                )
            print(json.dumps(output, indent=2))

        elif format_type == "list":
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title}")
                print(
                    f"   Author: {result.author} | Subreddit: {result.subreddit} | Upvotes: {result.upvotes}"
                )
                if result.tags:
                    print(f"   Tags: {', '.join(result.tags)}")
                if result.snippet:
                    print(f"   Preview: {result.snippet}")
                print(f"   File: {result.file_path}")
                print()

        else:  # table format
            print(f"\nFound {len(results)} result(s):")
            print(f"{'#':<3} {'Title':<40} {'Author':<15} {'Sub':<15} {'Upvotes':<8}")
            print("-" * 85)

            for i, result in enumerate(results, 1):
                title = (
                    result.title[:37] + "..."
                    if len(result.title) > 40
                    else result.title
                )
                author = (
                    result.author[:12] + "..."
                    if len(result.author) > 15
                    else result.author
                )
                subreddit = (
                    result.subreddit[:12] + "..."
                    if len(result.subreddit) > 15
                    else result.subreddit
                )

                print(
                    f"{i:<3} {title:<40} {author:<15} {subreddit:<15} {result.upvotes:<8}"
                )


def main():
    """Main entry point for the search CLI."""
    cli = SearchCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
