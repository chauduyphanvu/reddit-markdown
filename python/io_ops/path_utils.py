"""
Path utilities for archive operations.

This module provides utilities for generating secure archive paths
and handling file path operations safely.
"""

import random
from datetime import datetime
from pathlib import Path
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class ArchivePathGenerator:
    """Generates secure archive paths with proper sanitization."""

    def sanitize_directory_name(self, dir_name: str) -> str:
        """Sanitize directory name for use in file paths."""
        if not dir_name:
            return "reddit_archive"

        # Remove problematic characters and limit length
        safe_name = "".join(c for c in dir_name if c.isalnum() or c in "_-")[:50]
        return safe_name if safe_name else "reddit_archive"

    def generate_timestamp(self) -> str:
        """Generate timestamp for archive naming."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def generate_random_suffix(self, min_val: int = 1000, max_val: int = 9999) -> str:
        """Generate random suffix for uniqueness."""
        return f"{random.randint(min_val, max_val)}"

    def determine_extension(self, compression_format: str) -> str:
        """Determine file extension based on compression format."""
        if compression_format == "zstd":
            return "zst"
        elif compression_format == "zip":
            return "zip"
        else:
            raise ValueError(f"Unknown compression format: {compression_format}")

    def determine_parent_directory(self, source_path: Path) -> Path:
        """Determine where to place the archive."""
        try:
            parent_dir = source_path.parent
            if str(parent_dir) == str(source_path):  # Root directory case
                parent_dir = Path.cwd()
            return parent_dir
        except (OSError, ValueError):
            # Fallback to current directory
            return Path.cwd()

    def generate_archive_path(
        self, source_directory: str, compression_format: str
    ) -> str:
        """Generate secure archive filename based on source directory and timestamp."""
        source_path = Path(source_directory)

        # Sanitize directory name
        dir_name = source_path.name or "reddit_archive"
        safe_dir_name = self.sanitize_directory_name(dir_name)

        # Generate components
        timestamp = self.generate_timestamp()
        random_suffix = self.generate_random_suffix()
        extension = self.determine_extension(compression_format)

        # Construct archive name
        archive_name = f"{safe_dir_name}_{timestamp}_{random_suffix}.{extension}"

        # Determine parent directory
        parent_dir = self.determine_parent_directory(source_path)

        return str(parent_dir / archive_name)

    def ensure_extension(self, archive_path: str, compression_format: str) -> str:
        """Ensure archive path has correct extension."""
        expected_ext = self.determine_extension(compression_format)

        if not archive_path.endswith(f".{expected_ext}"):
            return f"{archive_path}.{expected_ext}"

        return archive_path


class TempFileManager:
    """Manages temporary file creation and cleanup."""

    @staticmethod
    def generate_temp_path(base_path: str, suffix: str = "tmp") -> str:
        """Generate temporary file path."""
        import os

        return f"{base_path}.{suffix}.{os.getpid()}"

    @staticmethod
    def cleanup_temp_file(temp_path: str) -> None:
        """Clean up temporary file safely."""
        import os

        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as e:
                logger.debug("Failed to cleanup temp file %s: %s", temp_path, e)

    @staticmethod
    def atomic_move(src_path: str, dest_path: str) -> None:
        """Perform atomic file move."""
        import os

        try:
            os.rename(src_path, dest_path)
        except OSError as e:
            logger.error("Failed to move %s to %s: %s", src_path, dest_path, e)
            raise
