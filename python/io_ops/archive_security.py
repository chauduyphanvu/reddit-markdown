"""
Security validation components for archive operations.

This module provides security-focused validation for file paths, extensions,
and size limits to prevent directory traversal and other security issues.
"""

import os
from pathlib import Path, PurePath
from typing import Set
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)

# Security constants
MAX_ARCHIVE_SIZE = 50 * 1024 * 1024 * 1024  # 50GB limit
MAX_FILES_PER_ARCHIVE = 100000  # File count limit
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".html", ".xml", ".csv"}
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB per file limit


class SecurityValidator:
    """Handles security validation for archive operations."""

    def __init__(self, validate_paths: bool = True):
        self.validate_paths = validate_paths
        self.allowed_extensions = ALLOWED_EXTENSIONS.copy()

    def validate_path_safety(self, path: Path, base_path: Path) -> bool:
        """Validate that path is safe and within base directory."""
        if not self.validate_paths:
            return True

        try:
            # Resolve symlinks and normalize paths
            resolved_path = path.resolve()
            resolved_base = base_path.resolve()

            # Check if path is within base directory
            try:
                resolved_path.relative_to(resolved_base)
            except ValueError:
                logger.warning("Path traversal attempt blocked: %s", path)
                return False

            # Check for suspicious path components
            path_parts = PurePath(resolved_path).parts
            suspicious_parts = {"..", "~", "$"}
            if any(part.startswith(tuple(suspicious_parts)) for part in path_parts):
                logger.warning("Suspicious path component in: %s", path)
                return False

            return True

        except (OSError, ValueError) as e:
            logger.warning("Path validation failed for %s: %s", path, e)
            return False

    def validate_archive_path(self, archive_path: str) -> bool:
        """Validate archive output path for security."""
        if not self.validate_paths:
            return True

        try:
            path = Path(archive_path).resolve()

            # Ensure parent directory exists or can be created
            parent = path.parent
            if not parent.exists():
                try:
                    parent.mkdir(parents=True, exist_ok=True)
                except (OSError, PermissionError) as e:
                    logger.error("Cannot create archive directory %s: %s", parent, e)
                    return False

            # Check write permissions
            if not os.access(parent, os.W_OK):
                logger.error("No write permission for archive directory: %s", parent)
                return False

            # Prevent overwriting system directories
            system_dirs = {
                "/bin",
                "/sbin",
                "/usr/bin",
                "/usr/sbin",
                "/etc",
                "/var",
                "/sys",
                "/proc",
            }
            if str(path).startswith(tuple(system_dirs)):
                logger.error("Archive path in system directory blocked: %s", path)
                return False

            return True

        except (OSError, ValueError) as e:
            logger.error("Archive path validation failed: %s", e)
            return False

    def validate_file_accessibility(self, file_path: Path) -> bool:
        """Check if file can be read."""
        if not os.access(file_path, os.R_OK):
            logger.warning("Cannot read file, skipping: %s", file_path)
            return False
        return True

    def validate_file_extension(self, file_path: Path) -> bool:
        """Validate file extension against allowed types."""
        if not self.validate_paths:
            return True

        if file_path.suffix.lower() not in self.allowed_extensions:
            logger.warning("File extension not allowed, skipping: %s", file_path)
            return False
        return True

    def validate_file_size(self, file_path: Path, file_size: int) -> bool:
        """Validate file size against limits."""
        if file_size > LARGE_FILE_THRESHOLD:
            logger.warning(
                "File too large, skipping: %s (%.2f MB)",
                file_path,
                file_size / (1024 * 1024),
            )
            return False
        return True

    def check_archive_limits(self, total_size: int, total_files: int) -> bool:
        """Check if archive limits have been exceeded."""
        if total_size > MAX_ARCHIVE_SIZE:
            logger.error("Archive size limit exceeded (50GB), stopping")
            return False

        if total_files > MAX_FILES_PER_ARCHIVE:
            logger.error("File count limit exceeded (100k files), stopping")
            return False

        return True

    def sanitize_archive_name(self, archive_name: str) -> str:
        """Sanitize archive name for security."""
        # Remove potentially problematic characters
        sanitized = archive_name.replace("..", "_").replace("~", "_")

        # Limit path length
        if len(sanitized) > 255:
            logger.warning("Path too long, truncating: %s", sanitized)
            sanitized = sanitized[:252] + "..."

        return sanitized

    def add_allowed_extension(self, extension: str) -> None:
        """Add an allowed file extension."""
        self.allowed_extensions.add(extension.lower())

    def remove_allowed_extension(self, extension: str) -> None:
        """Remove an allowed file extension."""
        self.allowed_extensions.discard(extension.lower())

    def get_allowed_extensions(self) -> Set[str]:
        """Get copy of allowed extensions."""
        return self.allowed_extensions.copy()


class ArchiveLimitsExceededError(Exception):
    """Raised when archive size or file count limits are exceeded."""

    pass


class PathSecurityError(Exception):
    """Raised when path security validation fails."""

    pass
