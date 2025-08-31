"""
Refactored Archive Manager - Orchestrates archive creation with modular components.

This is the main orchestrator that coordinates file scanning, security validation,
archive creation, metadata injection, and integrity verification using focused,
single-responsibility components.
"""

import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from colored_logger import get_colored_logger

from .file_scanner import ArchiveFileCollector
from .archive_creators import ArchiveCreatorFactory
from .metadata_manager import ArchiveMetadataManager
from .archive_verifier import ArchiveVerifier
from .path_utils import ArchivePathGenerator

logger = get_colored_logger(__name__)


class ArchiveManager:
    """
    Orchestrates archive creation using modular, focused components.

    This manager delegates specific responsibilities to specialized components:
    - File discovery and validation: ArchiveFileCollector
    - Archive creation: ArchiveCreatorFactory and format-specific creators
    - Metadata management: ArchiveMetadataManager
    - Integrity verification: ArchiveVerifier
    - Path generation: ArchivePathGenerator
    """

    SUPPORTED_FORMATS = ["zstd", "zip"]
    DEFAULT_COMPRESSION_LEVEL = {
        "zstd": 3,  # Good balance of speed and compression
        "zip": 6,  # Standard ZIP compression level
    }

    def __init__(
        self,
        compression_format: str = "auto",
        compression_level: Optional[int] = None,
        max_workers: int = 4,
        chunk_size: int = 8192,
        validate_paths: bool = True,
        validate_content: bool = True,
    ):
        """
        Initialize ArchiveManager with orchestration components.

        Args:
            compression_format: 'zstd', 'zip', or 'auto' (prefers zstd if available)
            compression_level: Compression level (None for defaults)
            max_workers: Number of worker threads (for future parallelization)
            chunk_size: Chunk size for file operations
            validate_paths: Enable security path validation
            validate_content: Enable content validation using magic numbers
        """
        # Determine compression format
        if compression_format == "auto":
            self.compression_format = ArchiveCreatorFactory.get_optimal_format()
        elif compression_format in self.SUPPORTED_FORMATS:
            # Validate format availability
            try:
                ArchiveCreatorFactory.create_archive_creator(compression_format)
                self.compression_format = compression_format
            except ImportError:
                logger.warning(
                    "%s requested but not available, falling back to ZIP",
                    compression_format.upper(),
                )
                self.compression_format = "zip"
        else:
            raise ValueError(f"Unsupported compression format: {compression_format}")

        # Set compression level
        if compression_level is not None:
            self.compression_level = compression_level
        else:
            self.compression_level = self.DEFAULT_COMPRESSION_LEVEL[
                self.compression_format
            ]

        # Performance and safety settings
        self.max_workers = max(1, min(max_workers, 8))  # Limit workers for safety
        self.chunk_size = max(1024, chunk_size)  # Minimum 1KB chunks
        self.validate_paths = validate_paths
        self.validate_content = validate_content

        # Initialize components
        self.file_collector = ArchiveFileCollector(validate_paths, validate_content)
        self.metadata_manager = ArchiveMetadataManager(
            self.compression_level, chunk_size
        )
        self.verifier = ArchiveVerifier()
        self.path_generator = ArchivePathGenerator()

        logger.debug(
            "ArchiveManager initialized: format=%s, level=%d, workers=%d",
            self.compression_format,
            self.compression_level,
            self.max_workers,
        )

    def _prepare_archive_creation(
        self, source_directory: str, archive_path: Optional[str]
    ) -> tuple[Path, str]:
        """Prepare and validate archive creation parameters."""
        source_path = Path(source_directory)
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_directory}")

        if not archive_path:
            archive_path = self.path_generator.generate_archive_path(
                source_directory, self.compression_format
            )
        else:
            archive_path = self.path_generator.ensure_extension(
                archive_path, self.compression_format
            )

        # Validate archive path if validation enabled
        if not self.file_collector.validate_archive_path(archive_path):
            raise ValueError(f"Archive path validation failed: {archive_path}")

        return source_path, archive_path

    def _log_scan_results(
        self, files_to_archive: List, file_stats: Dict[str, Any]
    ) -> None:
        """Log file scanning results."""
        logger.info(
            "Archive scan complete: %d files (%.2f MB), %d skipped, %d errors",
            file_stats["total_files"],
            file_stats["total_size"] / (1024 * 1024),
            file_stats["skipped_files"],
            file_stats["error_files"],
        )

    def _validate_archive_requirements(
        self, files_to_archive: List, source_directory: str
    ) -> None:
        """Validate that archive can be created."""
        if len(files_to_archive) == 0:
            logger.warning("No files found to archive in: %s", source_directory)

    def _create_archive_with_format(
        self,
        files_to_archive: List,
        archive_path: str,
        source_path: Path,
        progress_callback: Optional[callable],
    ) -> str:
        """Create archive using appropriate format creator."""
        creator = ArchiveCreatorFactory.create_archive_creator(
            self.compression_format, self.compression_level, chunk_size=self.chunk_size
        )

        return creator.create_archive(
            files_to_archive, archive_path, source_path, progress_callback
        )

    def _finalize_archive(
        self,
        archive_path: str,
        source_directory: str,
        files_to_archive: List,
        file_stats: Dict[str, Any],
        include_metadata: bool,
        start_time: float,
    ) -> None:
        """Finalize archive with metadata and verification."""
        # Add metadata if requested
        if include_metadata:
            self.metadata_manager.add_metadata_to_archive(
                archive_path,
                source_directory,
                files_to_archive,
                file_stats,
                self.compression_format,
                self.compression_level,
            )

        # Log success
        elapsed_time = time.time() - start_time
        archive_size = Path(archive_path).stat().st_size

        logger.success(
            "Archive created successfully: %s (%.2f MB, %.2f seconds)",
            archive_path,
            archive_size / (1024 * 1024),
            elapsed_time,
        )

        # Verify archive integrity
        if self.verifier.verify_archive_integrity(archive_path):
            logger.debug("Archive integrity verified")
        else:
            logger.warning("Archive integrity check failed")

    def create_archive(
        self,
        source_directory: str,
        archive_path: Optional[str] = None,
        include_metadata: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> str:
        """
        Create a compressed archive of the specified directory.

        Args:
            source_directory: Path to directory containing files to archive
            archive_path: Output archive path (auto-generated if None)
            include_metadata: Whether to include archive metadata file
            progress_callback: Optional callback for progress updates

        Returns:
            Path to created archive file
        """
        # Prepare archive creation
        source_path, archive_path = self._prepare_archive_creation(
            source_directory, archive_path
        )

        logger.info(
            "Creating %s archive: %s", self.compression_format.upper(), archive_path
        )

        # Collect files for archiving
        files_to_archive, file_stats = self.file_collector.collect_files(
            str(source_path)
        )
        self._log_scan_results(files_to_archive, file_stats)

        # Validate archive requirements
        self._validate_archive_requirements(files_to_archive, source_directory)

        if len(files_to_archive) == 0:
            return ""

        logger.info("Archiving %d files...", len(files_to_archive))

        # Create archive with error handling
        start_time = time.time()

        try:
            archive_path = self._create_archive_with_format(
                files_to_archive, archive_path, source_path, progress_callback
            )

            self._finalize_archive(
                archive_path,
                source_directory,
                files_to_archive,
                file_stats,
                include_metadata,
                start_time,
            )

        except Exception as e:
            # Cleanup handled by individual creators
            raise e

        return archive_path

    def get_archive_info(self, archive_path: str) -> Dict[str, Any]:
        """Get comprehensive information about an archive."""
        return self.verifier.get_archive_info(archive_path)

    def verify_archive_integrity(self, archive_path: str) -> bool:
        """Verify archive integrity."""
        return self.verifier.verify_archive_integrity(archive_path)

    @staticmethod
    def get_optimal_compression_format() -> str:
        """Get the optimal compression format for the current system."""
        return ArchiveCreatorFactory.get_optimal_format()

    @staticmethod
    def get_supported_formats() -> List[str]:
        """Get list of supported compression formats."""
        return ArchiveCreatorFactory.get_supported_formats()

    @staticmethod
    def install_zstd_hint() -> str:
        """Return installation hint for ZSTD if not available."""
        supported = ArchiveCreatorFactory.get_supported_formats()
        if "zstd" not in supported:
            return "For better compression performance, install zstandard: pip install zstandard"
        return ""


def create_archive_with_progress(
    source_directory: str,
    compression_format: str = "auto",
    compression_level: Optional[int] = None,
    archive_path: Optional[str] = None,
    max_workers: int = 4,
    validate_paths: bool = True,
    validate_content: bool = True,
) -> str:
    """
    Convenience function to create optimized archive with progress reporting.

    Args:
        source_directory: Directory to archive
        compression_format: Compression format to use
        compression_level: Compression level (None for default)
        archive_path: Output path (auto-generated if None)
        max_workers: Number of worker threads for parallel operations
        validate_paths: Enable security path validation
        validate_content: Enable content validation using magic numbers

    Returns:
        Path to created archive

    Raises:
        ValueError: If source directory is invalid or security validation fails
        OSError: If file system operations fail
    """
    # Validate source directory first
    source_path = Path(source_directory)
    if not source_path.exists():
        raise ValueError(f"Source directory does not exist: {source_directory}")
    if not source_path.is_dir():
        raise ValueError(f"Source path is not a directory: {source_directory}")

    def progress_callback(current: int, total: int):
        percentage = (current / total) * 100
        # More efficient progress reporting - only update at meaningful intervals
        if current == 1 or current % max(1, total // 20) == 0 or current == total:
            logger.progress(
                "Archiving progress: %d/%d files (%.1f%%)", current, total, percentage
            )

    manager = ArchiveManager(
        compression_format=compression_format,
        compression_level=compression_level,
        max_workers=max_workers,
        validate_paths=validate_paths,
        validate_content=validate_content,
    )

    return manager.create_archive(
        source_directory=source_directory,
        archive_path=archive_path,
        include_metadata=True,
        progress_callback=progress_callback,
    )
