"""
File scanning and validation for archive operations.

This module handles discovering files in source directories and validating
them against security and size constraints.
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from colored_logger import get_colored_logger
from .archive_security import SecurityValidator

logger = get_colored_logger(__name__)


class FileStats:
    """Container for file processing statistics."""

    def __init__(self):
        self.total_files = 0
        self.total_size = 0
        self.skipped_files = 0
        self.error_files = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "total_files": self.total_files,
            "total_size": self.total_size,
            "skipped_files": self.skipped_files,
            "error_files": self.error_files,
        }

    def add_file(self, file_size: int) -> None:
        """Add a successfully processed file."""
        self.total_files += 1
        self.total_size += file_size

    def skip_file(self) -> None:
        """Record a skipped file."""
        self.skipped_files += 1

    def error_file(self) -> None:
        """Record a file processing error."""
        self.error_files += 1


class FileScanner:
    """Scans directories and validates files for archiving."""

    def __init__(self, security_validator: Optional[SecurityValidator] = None):
        self.security_validator = security_validator or SecurityValidator()

    def scan_directory(self, source_path: Path) -> List[Path]:
        """Scan source directory and return list of files."""
        return [
            file_path for file_path in source_path.rglob("*") if file_path.is_file()
        ]

    def generate_archive_name(self, file_path: Path, source_path: Path) -> str:
        """Generate sanitized archive name for file."""
        rel_path = file_path.relative_to(source_path)
        archive_name = str(rel_path)
        return self.security_validator.sanitize_archive_name(archive_name)

    def validate_single_file(
        self, file_path: Path, source_path: Path, stats: FileStats
    ) -> Optional[Tuple[Path, str]]:
        """Validate a single file for inclusion in archive."""
        try:
            # Security validation
            if not self.security_validator.validate_path_safety(file_path, source_path):
                stats.skip_file()
                return None

            # Check file accessibility
            if not self.security_validator.validate_file_accessibility(file_path):
                stats.skip_file()
                return None

            # Check file extension
            if not self.security_validator.validate_file_extension(file_path):
                stats.skip_file()
                return None

            # Get file size and validate
            file_stat = file_path.stat()
            file_size = file_stat.st_size

            if not self.security_validator.validate_file_size(file_path, file_size):
                stats.skip_file()
                return None

            # Generate archive name
            archive_name = self.generate_archive_name(file_path, source_path)

            # Update statistics
            stats.add_file(file_size)

            # Check archive limits
            if not self.security_validator.check_archive_limits(
                stats.total_size, stats.total_files
            ):
                # Return the file but indicate limits will be exceeded
                return (file_path, archive_name)

            return (file_path, archive_name)

        except (OSError, ValueError) as e:
            logger.warning("Error processing file %s: %s", file_path, e)
            stats.error_file()
            return None

    def get_files_to_archive(
        self, source_path: Path
    ) -> Tuple[List[Tuple[Path, str]], FileStats]:
        """Get list of (file_path, archive_name) tuples and metadata for files to archive."""
        files = []
        stats = FileStats()

        # Scan all files in source directory
        all_files = self.scan_directory(source_path)

        # Process each file
        for file_path in all_files:
            result = self.validate_single_file(file_path, source_path, stats)

            if result is not None:
                files.append(result)

                # Stop if limits exceeded
                if not self.security_validator.check_archive_limits(
                    stats.total_size, stats.total_files
                ):
                    break

        return files, stats


class ArchiveFileCollector:
    """High-level interface for collecting files for archiving."""

    def __init__(self, validate_paths: bool = True):
        self.security_validator = SecurityValidator(validate_paths)
        self.file_scanner = FileScanner(self.security_validator)

    def collect_files(
        self, source_directory: str
    ) -> Tuple[List[Tuple[Path, str]], Dict[str, Any]]:
        """Collect files from source directory for archiving."""
        source_path = Path(source_directory)

        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_directory}")

        if not source_path.is_dir():
            raise NotADirectoryError(
                f"Source path is not a directory: {source_directory}"
            )

        files, stats = self.file_scanner.get_files_to_archive(source_path)

        return files, stats.to_dict()

    def validate_archive_path(self, archive_path: str) -> bool:
        """Validate archive output path."""
        return self.security_validator.validate_archive_path(archive_path)
