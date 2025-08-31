#!/usr/bin/env python3
"""
Reddit Markdown Archive CLI Tool

A standalone command-line interface for creating compressed archives 
of downloaded Reddit content. Supports high-performance ZSTD and 
universal ZIP compression formats.

Usage:
    python3 cli_archive.py create /path/to/reddit-posts
    python3 cli_archive.py create /path/to/reddit-posts --format zstd --level 5
    python3 cli_archive.py info /path/to/archive.zip
    python3 cli_archive.py verify /path/to/archive.zst
"""

import argparse
import json
import logging
import os
import sys
import zipfile
from pathlib import Path
from typing import Optional

from colored_logger import setup_colored_logging, get_colored_logger
from io_ops.archive_manager import ArchiveManager, create_archive_with_progress

logger = get_colored_logger(__name__)


class ArchiveCLI:
    """Command-line interface for Reddit content archiving."""

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all commands and options."""
        parser = argparse.ArgumentParser(
            description="Archive downloaded Reddit content with high-performance compression",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Create archive with auto-detected optimal format
  python3 cli_archive.py create /path/to/reddit-posts

  # Create ZSTD archive with custom compression level
  python3 cli_archive.py create /path/to/reddit-posts --format zstd --level 5

  # Create ZIP archive with custom output path
  python3 cli_archive.py create /path/to/reddit-posts --format zip --output /backups/reddit-2024.zip

  # Show archive information
  python3 cli_archive.py info /path/to/archive.zip

  # Verify archive integrity
  python3 cli_archive.py verify /path/to/archive.zst

  # List supported formats and their capabilities
  python3 cli_archive.py formats
            """,
        )

        # Add subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Create command
        create_parser = subparsers.add_parser(
            "create", help="Create a compressed archive of downloaded content"
        )
        create_parser.add_argument(
            "source_directory",
            help="Directory containing downloaded Reddit posts to archive",
        )
        create_parser.add_argument(
            "--format",
            "-f",
            choices=["auto", "zstd", "zip"],
            default="auto",
            help="Compression format (auto=detect optimal format for system)",
        )
        create_parser.add_argument(
            "--level",
            "-l",
            type=int,
            help="Compression level (zstd: 1-22, zip: 0-9, default: optimal for format)",
        )
        create_parser.add_argument(
            "--output",
            "-o",
            help="Output archive path (auto-generated if not specified)",
        )
        create_parser.add_argument(
            "--no-metadata",
            action="store_true",
            help="Do not include archive metadata file",
        )
        create_parser.add_argument(
            "--quiet", "-q", action="store_true", help="Suppress progress output"
        )

        # Info command
        info_parser = subparsers.add_parser(
            "info", help="Display information about an existing archive"
        )
        info_parser.add_argument("archive_path", help="Path to the archive file")
        info_parser.add_argument(
            "--detailed", action="store_true", help="Show detailed file listing"
        )

        # Verify command
        verify_parser = subparsers.add_parser("verify", help="Verify archive integrity")
        verify_parser.add_argument(
            "archive_path", help="Path to the archive file to verify"
        )

        # Formats command
        subparsers.add_parser(
            "formats", help="List supported compression formats and their capabilities"
        )

        return parser

    def run(self, args: Optional[list] = None) -> int:
        """Run the CLI with the given arguments."""
        parsed_args = self.parser.parse_args(args)

        if not parsed_args.command:
            self.parser.print_help()
            return 1

        try:
            if parsed_args.command == "create":
                return self._handle_create(parsed_args)
            elif parsed_args.command == "info":
                return self._handle_info(parsed_args)
            elif parsed_args.command == "verify":
                return self._handle_verify(parsed_args)
            elif parsed_args.command == "formats":
                return self._handle_formats(parsed_args)
            else:
                logger.error("Unknown command: %s", parsed_args.command)
                return 1

        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 130
        except Exception as e:
            logger.error("Error: %s", e)
            logger.debug("Full error details:", exc_info=True)
            return 1

    def _handle_create(self, args) -> int:
        """Handle the 'create' command."""
        source_dir = Path(args.source_directory)

        if not source_dir.exists():
            logger.error("Source directory does not exist: %s", source_dir)
            return 1

        if not source_dir.is_dir():
            logger.error("Source path is not a directory: %s", source_dir)
            return 1

        # Count files to archive
        file_count = sum(1 for _ in source_dir.rglob("*") if _.is_file())
        if file_count == 0:
            logger.warning("No files found in source directory: %s", source_dir)
            return 1

        logger.info("Found %d files to archive in: %s", file_count, source_dir)

        # Show ZSTD installation hint if needed
        zstd_hint = ArchiveManager.install_zstd_hint()
        if zstd_hint:
            logger.info(zstd_hint)

        # Create archive
        try:
            if args.quiet:
                # Create archive without progress callback
                manager = ArchiveManager(args.format, args.level)
                archive_path = manager.create_archive(
                    source_directory=str(source_dir),
                    archive_path=args.output,
                    include_metadata=not args.no_metadata,
                    progress_callback=None,
                )
            else:
                # Create archive with progress reporting
                archive_path = create_archive_with_progress(
                    source_directory=str(source_dir),
                    compression_format=args.format,
                    compression_level=args.level,
                    archive_path=args.output,
                )

            if archive_path:
                archive_size = os.path.getsize(archive_path)
                logger.success(
                    "Archive created successfully: %s (%.2f MB)",
                    archive_path,
                    archive_size / (1024 * 1024),
                )
                return 0
            else:
                logger.error("Archive creation failed")
                return 1

        except Exception as e:
            logger.error("Failed to create archive: %s", e)
            return 1

    def _handle_info(self, args) -> int:
        """Handle the 'info' command."""
        archive_path = Path(args.archive_path)

        if not archive_path.exists():
            logger.error("Archive file does not exist: %s", archive_path)
            return 1

        try:
            self._display_archive_info(str(archive_path), args.detailed)
            return 0
        except Exception as e:
            logger.error("Failed to read archive info: %s", e)
            return 1

    def _handle_verify(self, args) -> int:
        """Handle the 'verify' command."""
        archive_path = Path(args.archive_path)

        if not archive_path.exists():
            logger.error("Archive file does not exist: %s", archive_path)
            return 1

        try:
            logger.info("Verifying archive integrity: %s", archive_path)
            manager = ArchiveManager()

            if manager.verify_archive_integrity(str(archive_path)):
                logger.success("Archive integrity check passed")
                return 0
            else:
                logger.error("Archive integrity check failed")
                return 1

        except Exception as e:
            logger.error("Failed to verify archive: %s", e)
            return 1

    def _handle_formats(self, args) -> int:
        """Handle the 'formats' command."""
        logger.info("Supported compression formats:")
        logger.info("")

        # Check ZSTD availability
        optimal_format = ArchiveManager.get_optimal_compression_format()

        formats_info = [
            {
                "name": "ZSTD",
                "extension": ".zst",
                "available": optimal_format == "zstd",
                "speed": "⚡⚡⚡ Ultra Fast",
                "compression": "🗜️🗜️ Excellent",
                "levels": "1-22 (default: 3)",
                "description": "Modern compression with superior speed and ratios",
            },
            {
                "name": "ZIP",
                "extension": ".zip",
                "available": True,
                "speed": "⚡⚡ Fast",
                "compression": "🗜️ Good",
                "levels": "0-9 (default: 6)",
                "description": "Universal format with wide compatibility",
            },
        ]

        for fmt in formats_info:
            status = "✅ Available" if fmt["available"] else "❌ Not Available"
            recommended = (
                " (Recommended)" if fmt["name"] == "ZSTD" and fmt["available"] else ""
            )

            logger.info("Format: %s%s", fmt["name"], recommended)
            logger.info("  Status: %s", status)
            logger.info("  Extension: %s", fmt["extension"])
            logger.info("  Speed: %s", fmt["speed"])
            logger.info("  Compression: %s", fmt["compression"])
            logger.info("  Levels: %s", fmt["levels"])
            logger.info("  Description: %s", fmt["description"])
            logger.info("")

        if optimal_format != "zstd":
            logger.info("💡 Tip: Install ZSTD for better performance:")
            logger.info("   pip3 install zstandard")
            logger.info("")

        logger.info(
            "Current optimal format for your system: %s", optimal_format.upper()
        )
        return 0

    def _display_archive_info(self, archive_path: str, detailed: bool = False) -> None:
        """Display information about an archive file."""
        archive_file = Path(archive_path)

        # Basic file information
        file_size = archive_file.stat().st_size
        logger.info("Archive: %s", archive_path)
        logger.info("Size: %.2f MB (%d bytes)", file_size / (1024 * 1024), file_size)
        logger.info("Modified: %s", archive_file.stat().st_mtime)

        # Format-specific information
        if archive_path.endswith(".zip"):
            self._display_zip_info(archive_path, detailed)
        elif archive_path.endswith(".zst"):
            self._display_zstd_info(archive_path, detailed)
        else:
            logger.warning("Unknown archive format")

    def _display_zip_info(self, archive_path: str, detailed: bool) -> None:
        """Display ZIP archive information."""
        logger.info("Format: ZIP")

        with zipfile.ZipFile(archive_path, "r") as zipf:
            file_list = zipf.infolist()
            total_files = len(file_list)
            total_compressed = sum(f.compress_size for f in file_list)
            total_uncompressed = sum(f.file_size for f in file_list)

            compression_ratio = (
                (1 - total_compressed / total_uncompressed) * 100
                if total_uncompressed > 0
                else 0
            )

            logger.info("Files: %d", total_files)
            logger.info("Compressed size: %.2f MB", total_compressed / (1024 * 1024))
            logger.info(
                "Uncompressed size: %.2f MB", total_uncompressed / (1024 * 1024)
            )
            logger.info("Compression ratio: %.1f%%", compression_ratio)

            # Check for metadata file
            has_metadata = any(f.filename == "archive_metadata.json" for f in file_list)
            logger.info("Contains metadata: %s", "Yes" if has_metadata else "No")

            if has_metadata:
                try:
                    with zipf.open("archive_metadata.json") as f:
                        metadata = json.loads(f.read().decode("utf-8"))
                        logger.info(
                            "Created: %s", metadata.get("created_at", "Unknown")
                        )
                        logger.info(
                            "Source: %s", metadata.get("source_directory", "Unknown")
                        )
                except Exception as e:
                    logger.warning("Could not read metadata: %s", e)

            if detailed:
                logger.info("")
                logger.info("File listing:")
                for info in sorted(file_list, key=lambda x: x.filename):
                    if info.filename != "archive_metadata.json":
                        logger.info(
                            "  %s (%.1f KB)", info.filename, info.file_size / 1024
                        )

    def _display_zstd_info(self, archive_path: str, detailed: bool) -> None:
        """Display ZSTD archive information."""
        logger.info("Format: ZSTD + TAR")

        try:
            import zstandard as zstd
            import tarfile
            import io

            with open(archive_path, "rb") as f:
                compressed_data = f.read()

            dctx = zstd.ZstdDecompressor()
            decompressed_data = dctx.decompress(compressed_data)

            tar_buffer = io.BytesIO(decompressed_data)

            with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
                members = tar.getmembers()
                total_files = len([m for m in members if m.isfile()])
                total_uncompressed = sum(m.size for m in members if m.isfile())

                compression_ratio = (
                    (1 - len(compressed_data) / total_uncompressed) * 100
                    if total_uncompressed > 0
                    else 0
                )

                logger.info("Files: %d", total_files)
                logger.info(
                    "Compressed size: %.2f MB", len(compressed_data) / (1024 * 1024)
                )
                logger.info(
                    "Uncompressed size: %.2f MB", total_uncompressed / (1024 * 1024)
                )
                logger.info("Compression ratio: %.1f%%", compression_ratio)

                if detailed:
                    logger.info("")
                    logger.info("File listing:")
                    for member in sorted(members, key=lambda x: x.name):
                        if member.isfile():
                            logger.info(
                                "  %s (%.1f KB)", member.name, member.size / 1024
                            )

        except ImportError:
            logger.warning("ZSTD library not available - cannot read archive details")
            logger.info("Install with: pip3 install zstandard")
        except Exception as e:
            logger.warning("Could not read ZSTD archive details: %s", e)


def main():
    """Main entry point for the CLI."""
    setup_colored_logging(level=logging.INFO)

    cli = ArchiveCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
