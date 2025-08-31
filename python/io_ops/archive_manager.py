import json
import os
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)

try:
    import zstandard as zstd

    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    logger.debug("zstandard not available, falling back to ZIP compression")


class ArchiveManager:
    """
    Manages creation of compressed archives for Reddit markdown content.
    Supports ZSTD (preferred) and ZIP compression with performance optimizations.
    """

    SUPPORTED_FORMATS = ["zstd", "zip"]
    DEFAULT_COMPRESSION_LEVEL = {
        "zstd": 3,  # Good balance of speed and compression
        "zip": 6,  # Standard ZIP compression level
    }

    def __init__(
        self, compression_format: str = "auto", compression_level: Optional[int] = None
    ):
        """
        Initialize ArchiveManager with specified compression settings.

        Args:
            compression_format: 'zstd', 'zip', or 'auto' (prefers zstd if available)
            compression_level: Compression level (None for defaults)
        """
        if compression_format == "auto":
            self.compression_format = "zstd" if ZSTD_AVAILABLE else "zip"
        elif compression_format == "zstd" and not ZSTD_AVAILABLE:
            logger.warning("ZSTD requested but not available, falling back to ZIP")
            self.compression_format = "zip"
        elif compression_format in self.SUPPORTED_FORMATS:
            self.compression_format = compression_format
        else:
            raise ValueError(f"Unsupported compression format: {compression_format}")

        # Use specified compression level or default if None
        if compression_level is not None:
            self.compression_level = compression_level
        else:
            self.compression_level = self.DEFAULT_COMPRESSION_LEVEL[
                self.compression_format
            ]

        logger.debug(
            "ArchiveManager initialized: format=%s, level=%d",
            self.compression_format,
            self.compression_level,
        )

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
        source_path = Path(source_directory)
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_directory}")

        if not archive_path:
            archive_path = self._generate_archive_path(source_directory)

        logger.info(
            "Creating %s archive: %s", self.compression_format.upper(), archive_path
        )

        # Get list of files to archive
        files_to_archive = self._get_files_to_archive(source_path)
        total_files = len(files_to_archive)

        if total_files == 0:
            logger.warning("No files found to archive in: %s", source_directory)
            return ""

        logger.info("Archiving %d files...", total_files)

        # Create archive based on format
        start_time = time.time()

        if self.compression_format == "zstd":
            archive_path = self._create_zstd_archive(
                files_to_archive, archive_path, source_path, progress_callback
            )
        else:  # zip
            archive_path = self._create_zip_archive(
                files_to_archive, archive_path, source_path, progress_callback
            )

        # Include metadata if requested
        if include_metadata:
            self._add_metadata_to_archive(
                archive_path, source_directory, files_to_archive
            )

        elapsed_time = time.time() - start_time
        archive_size = os.path.getsize(archive_path)

        logger.success(
            "Archive created successfully: %s (%.2f MB, %.2f seconds)",
            archive_path,
            archive_size / (1024 * 1024),
            elapsed_time,
        )

        # Verify archive integrity
        if self._verify_archive_integrity(archive_path):
            logger.debug("Archive integrity verified")
        else:
            logger.warning("Archive integrity check failed")

        return archive_path

    def _get_files_to_archive(self, source_path: Path) -> List[Tuple[Path, str]]:
        """Get list of (file_path, archive_name) tuples for files to archive."""
        files = []
        for file_path in source_path.rglob("*"):
            if file_path.is_file():
                # Calculate relative path for archive
                rel_path = file_path.relative_to(source_path)
                files.append((file_path, str(rel_path)))
        return files

    def _create_zstd_archive(
        self,
        files: List[Tuple[Path, str]],
        archive_path: str,
        source_path: Path,
        progress_callback: Optional[callable],
    ) -> str:
        """Create ZSTD compressed archive using tar format."""
        if not archive_path.endswith(".zst"):
            archive_path = f"{archive_path}.zst"

        import tarfile
        import io

        # Create tar data in memory first
        tar_buffer = io.BytesIO()

        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            for i, (file_path, archive_name) in enumerate(files):
                try:
                    tar.add(file_path, arcname=archive_name)

                    if progress_callback:
                        progress_callback(i + 1, len(files))

                except Exception as e:
                    logger.warning("Failed to add file %s to archive: %s", file_path, e)
                    continue

        # Compress the tar data with ZSTD
        tar_data = tar_buffer.getvalue()
        cctx = zstd.ZstdCompressor(level=self.compression_level)
        compressed_data = cctx.compress(tar_data)

        # Write compressed data to file
        with open(archive_path, "wb") as f:
            f.write(compressed_data)

        return archive_path

    def _create_zip_archive(
        self,
        files: List[Tuple[Path, str]],
        archive_path: str,
        source_path: Path,
        progress_callback: Optional[callable],
    ) -> str:
        """Create ZIP compressed archive."""
        if not archive_path.endswith(".zip"):
            archive_path = f"{archive_path}.zip"

        with zipfile.ZipFile(
            archive_path,
            "w",
            zipfile.ZIP_DEFLATED,
            compresslevel=self.compression_level,
        ) as zipf:

            for i, (file_path, archive_name) in enumerate(files):
                try:
                    zipf.write(file_path, archive_name)

                    if progress_callback:
                        progress_callback(i + 1, len(files))

                except Exception as e:
                    logger.warning("Failed to add file %s to archive: %s", file_path, e)
                    continue

        return archive_path

    def _add_metadata_to_archive(
        self, archive_path: str, source_directory: str, files: List[Tuple[Path, str]]
    ) -> None:
        """Add metadata file to existing archive."""
        metadata = {
            "created_at": datetime.now().isoformat(),
            "source_directory": source_directory,
            "compression_format": self.compression_format,
            "compression_level": self.compression_level,
            "total_files": len(files),
            "archive_size_bytes": os.path.getsize(archive_path),
            "files": [
                {
                    "name": archive_name,
                    "size_bytes": file_path.stat().st_size,
                    "modified_at": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat(),
                }
                for file_path, archive_name in files
            ],
        }

        # Create temporary metadata file
        metadata_content = json.dumps(metadata, indent=2)
        temp_metadata_path = f"{archive_path}.metadata.tmp"

        try:
            with open(temp_metadata_path, "w", encoding="utf-8") as f:
                f.write(metadata_content)

            # Add metadata to archive based on format
            if self.compression_format == "zip":
                with zipfile.ZipFile(archive_path, "a") as zipf:
                    zipf.write(temp_metadata_path, "archive_metadata.json")
            # Note: For ZSTD, metadata would need to be added during creation
            # This is a simplified implementation

        finally:
            if os.path.exists(temp_metadata_path):
                os.remove(temp_metadata_path)

    def _generate_archive_path(self, source_directory: str) -> str:
        """Generate archive filename based on source directory and timestamp."""
        source_path = Path(source_directory)
        dir_name = source_path.name or "reddit_archive"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        extension = "zst" if self.compression_format == "zstd" else "zip"
        archive_name = f"{dir_name}_{timestamp}.{extension}"

        # Place archive in parent directory of source
        return str(source_path.parent / archive_name)

    def _verify_archive_integrity(self, archive_path: str) -> bool:
        """Verify archive can be opened and read."""
        try:
            if archive_path.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zipf:
                    # Test archive integrity
                    bad_file = zipf.testzip()
                    return bad_file is None  # None means no bad files
            elif archive_path.endswith(".zst"):
                # ZSTD+tar integrity check
                with open(archive_path, "rb") as f:
                    compressed_data = f.read()
                    dctx = zstd.ZstdDecompressor()
                    decompressed_data = dctx.decompress(compressed_data)

                    # Try to read as tar
                    import tarfile
                    import io

                    tar_buffer = io.BytesIO(decompressed_data)

                    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
                        # Try to list files to verify tar structure
                        tar.getnames()
                        return True

        except Exception as e:
            logger.debug("Archive integrity check failed: %s", e)
            return False

        return False

    @staticmethod
    def get_optimal_compression_format() -> str:
        """Get the optimal compression format for the current system."""
        return "zstd" if ZSTD_AVAILABLE else "zip"

    @staticmethod
    def install_zstd_hint() -> str:
        """Return installation hint for ZSTD if not available."""
        if ZSTD_AVAILABLE:
            return ""
        return "For better compression performance, install zstandard: pip install zstandard"


def create_archive_with_progress(
    source_directory: str,
    compression_format: str = "auto",
    compression_level: Optional[int] = None,
    archive_path: Optional[str] = None,
) -> str:
    """
    Convenience function to create archive with progress reporting.

    Args:
        source_directory: Directory to archive
        compression_format: Compression format to use
        compression_level: Compression level (None for default)
        archive_path: Output path (auto-generated if None)

    Returns:
        Path to created archive
    """

    def progress_callback(current: int, total: int):
        percentage = (current / total) * 100
        if current % max(1, total // 20) == 0 or current == total:  # Update every 5%
            logger.progress(
                "Archiving progress: %d/%d files (%.1f%%)", current, total, percentage
            )

    manager = ArchiveManager(compression_format, compression_level)
    return manager.create_archive(
        source_directory,
        archive_path,
        include_metadata=True,
        progress_callback=progress_callback,
    )
