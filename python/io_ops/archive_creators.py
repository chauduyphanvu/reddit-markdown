"""
Archive creation implementations for different compression formats.

This module provides format-specific archive creators that handle the actual
compression and file writing operations.
"""

import os
import zipfile
import tarfile
import threading
from pathlib import Path
from typing import List, Tuple, Optional, Protocol
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)

try:
    import zstandard as zstd

    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False


class ProgressReporter:
    """Thread-safe progress reporting."""

    def __init__(self):
        self._lock = threading.Lock()

    def should_report_progress(self, current_index: int, total_files: int) -> bool:
        """Determine if progress should be reported for current file."""
        return (
            current_index % max(1, total_files // 20) == 0
            or current_index == total_files - 1
        )

    def report_progress_safely(
        self, progress_callback: Optional[callable], current: int, total: int
    ) -> None:
        """Report progress with thread safety."""
        if progress_callback:
            with self._lock:
                progress_callback(current, total)


class ArchiveCreator(Protocol):
    """Protocol defining interface for archive creators."""

    def create_archive(
        self,
        files: List[Tuple[Path, str]],
        archive_path: str,
        source_path: Path,
        progress_callback: Optional[callable] = None,
    ) -> str:
        """Create archive with given files."""
        ...


class ZipArchiveCreator:
    """Creates ZIP format archives with optimized performance."""

    def __init__(self, compression_level: int = 6, chunk_size: int = 8192):
        self.compression_level = compression_level
        self.chunk_size = max(1024, chunk_size)  # Minimum 1KB chunks
        self.progress_reporter = ProgressReporter()

    def _create_zipfile_instance(self, temp_archive_path: str) -> zipfile.ZipFile:
        """Create ZipFile instance with optimal settings."""
        return zipfile.ZipFile(
            temp_archive_path,
            "w",
            zipfile.ZIP_DEFLATED,
            compresslevel=self.compression_level,
            allowZip64=True,  # Support large archives
        )

    def _is_large_file(self, file_path: Path) -> bool:
        """Determine if file should use streaming compression."""
        return file_path.stat().st_size > 10 * 1024 * 1024  # 10MB threshold

    def _add_large_file_to_zip(
        self, zipf: zipfile.ZipFile, file_path: Path, archive_name: str
    ) -> bool:
        """Add large file to ZIP using streaming compression."""
        try:
            with open(file_path, "rb") as src_file:
                with zipf.open(archive_name, "w") as dst_file:
                    while True:
                        chunk = src_file.read(self.chunk_size)
                        if not chunk:
                            break
                        dst_file.write(chunk)
            return True
        except (OSError, zipfile.BadZipFile) as e:
            logger.warning("Failed to add large file %s to archive: %s", file_path, e)
            return False

    def _add_small_file_to_zip(
        self, zipf: zipfile.ZipFile, file_path: Path, archive_name: str
    ) -> bool:
        """Add small file to ZIP using standard method."""
        try:
            zipf.write(file_path, archive_name)
            return True
        except (OSError, zipfile.BadZipFile) as e:
            logger.warning("Failed to add file %s to archive: %s", file_path, e)
            return False

    def _add_file_to_zip_archive(
        self, zipf: zipfile.ZipFile, file_path: Path, archive_name: str
    ) -> bool:
        """Add file to ZIP archive using appropriate method based on size."""
        if self._is_large_file(file_path):
            return self._add_large_file_to_zip(zipf, file_path, archive_name)
        else:
            return self._add_small_file_to_zip(zipf, file_path, archive_name)

    def _cleanup_temp_file(self, temp_file_path: str) -> None:
        """Clean up temporary file."""
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass

    def create_archive(
        self,
        files: List[Tuple[Path, str]],
        archive_path: str,
        source_path: Path,
        progress_callback: Optional[callable] = None,
    ) -> str:
        """Create ZIP compressed archive with optimized performance and atomic creation."""
        if not archive_path.endswith(".zip"):
            archive_path = f"{archive_path}.zip"

        temp_archive_path = f"{archive_path}.tmp.{os.getpid()}"

        try:
            with self._create_zipfile_instance(temp_archive_path) as zipf:
                for i, (file_path, archive_name) in enumerate(files):
                    self._add_file_to_zip_archive(zipf, file_path, archive_name)

                    if self.progress_reporter.should_report_progress(i, len(files)):
                        self.progress_reporter.report_progress_safely(
                            progress_callback, i + 1, len(files)
                        )

            # Atomic move to final location
            os.rename(temp_archive_path, archive_path)

        except Exception as e:
            self._cleanup_temp_file(temp_archive_path)
            raise e

        return archive_path


class ZstdArchiveCreator:
    """Creates ZSTD format archives with streaming compression."""

    def __init__(self, compression_level: int = 3):
        self.compression_level = compression_level
        self.progress_reporter = ProgressReporter()

        if not ZSTD_AVAILABLE:
            raise ImportError(
                "ZSTD library not available. Install with: pip install zstandard"
            )

    def _setup_zstd_compressor(self) -> "zstd.ZstdCompressor":
        """Set up ZSTD compressor with optimal settings."""
        return zstd.ZstdCompressor(
            level=self.compression_level,
            write_content_size=True,
            write_checksum=True,
        )

    def _add_file_to_tar_archive(
        self, tar: "tarfile.TarFile", file_path: Path, archive_name: str
    ) -> bool:
        """Add single file to TAR archive with error handling."""
        try:
            tar.add(file_path, arcname=archive_name, recursive=False)
            return True
        except (OSError, tarfile.TarError) as e:
            logger.warning("Failed to add file %s to archive: %s", file_path, e)
            return False

    def _cleanup_temp_file(self, temp_file_path: str) -> None:
        """Clean up temporary file."""
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass

    def create_archive(
        self,
        files: List[Tuple[Path, str]],
        archive_path: str,
        source_path: Path,
        progress_callback: Optional[callable] = None,
    ) -> str:
        """Create ZSTD compressed archive using streaming tar format for better memory efficiency."""
        if not archive_path.endswith(".zst"):
            archive_path = f"{archive_path}.zst"

        temp_archive_path = f"{archive_path}.tmp.{os.getpid()}"

        try:
            cctx = self._setup_zstd_compressor()

            with open(temp_archive_path, "wb") as temp_file:
                with cctx.stream_writer(temp_file) as compressor:
                    with tarfile.open(fileobj=compressor, mode="w|") as tar:
                        for i, (file_path, archive_name) in enumerate(files):
                            self._add_file_to_tar_archive(tar, file_path, archive_name)

                            if self.progress_reporter.should_report_progress(
                                i, len(files)
                            ):
                                self.progress_reporter.report_progress_safely(
                                    progress_callback, i + 1, len(files)
                                )

            # Atomic move to final location
            os.rename(temp_archive_path, archive_path)

        except Exception as e:
            self._cleanup_temp_file(temp_archive_path)
            raise e

        return archive_path


class ArchiveCreatorFactory:
    """Factory for creating appropriate archive creators."""

    @staticmethod
    def create_archive_creator(
        compression_format: str, compression_level: Optional[int] = None, **kwargs
    ) -> ArchiveCreator:
        """Create appropriate archive creator based on format."""
        if compression_format == "zip":
            level = compression_level if compression_level is not None else 6
            return ZipArchiveCreator(level, **kwargs)
        elif compression_format == "zstd":
            if not ZSTD_AVAILABLE:
                raise ImportError(
                    "ZSTD library not available. Install with: pip install zstandard"
                )
            level = compression_level if compression_level is not None else 3
            return ZstdArchiveCreator(level)
        else:
            raise ValueError(f"Unsupported compression format: {compression_format}")

    @staticmethod
    def get_optimal_format() -> str:
        """Get optimal compression format for current system."""
        return "zstd" if ZSTD_AVAILABLE else "zip"

    @staticmethod
    def get_supported_formats() -> List[str]:
        """Get list of supported compression formats."""
        formats = ["zip"]  # ZIP is always available
        if ZSTD_AVAILABLE:
            formats.append("zstd")
        return formats
