"""
Metadata management for archives.

This module handles generating, sanitizing, and injecting metadata into archives
of different formats while maintaining security best practices.
"""

import json
import os
import tempfile
import tarfile
import zipfile
import hashlib
import io
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)

try:
    import zstandard as zstd

    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False


class MetadataGenerator:
    """Generates secure metadata for archives."""

    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = max(1024, chunk_size)

    def sanitize_source_directory_name(self, source_directory: str) -> str:
        """Sanitize source directory name for metadata."""
        return Path(source_directory).name or "reddit_archive"

    def generate_base_metadata(
        self,
        archive_path: str,
        source_directory: str,
        files: List[Tuple[Path, str]],
        file_stats: Dict[str, Any],
        compression_format: str,
        compression_level: int,
    ) -> Dict[str, Any]:
        """Generate base metadata fields."""
        sanitized_source = self.sanitize_source_directory_name(source_directory)

        return {
            "created_at": datetime.now().isoformat(),
            "source_directory_name": sanitized_source,
            "compression_format": compression_format,
            "compression_level": compression_level,
            "total_files": len(files),
            "total_size_bytes": file_stats["total_size"],
            "skipped_files": file_stats["skipped_files"],
            "error_files": file_stats["error_files"],
            "archive_size_bytes": os.path.getsize(archive_path),
            "tool_version": "reddit-markdown-archive-v2.0",
            "checksum_sha256": self.calculate_archive_checksum(archive_path),
        }

    def generate_file_metadata_entry(
        self, file_path: Path, archive_name: str
    ) -> Dict[str, Any]:
        """Generate metadata entry for a single file."""
        return {
            "name": archive_name,
            "size_bytes": file_path.stat().st_size,
            "modified_at": datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat(),
        }

    def generate_files_metadata(
        self, files: List[Tuple[Path, str]], max_files: int = 1000
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Generate metadata for files with size limiting."""
        files_metadata = [
            self.generate_file_metadata_entry(file_path, archive_name)
            for file_path, archive_name in files[:max_files]
        ]

        truncation_info = {}
        if len(files) > max_files:
            truncation_info = {
                "files_truncated": True,
                "files_shown": max_files,
                "total_files_actual": len(files),
            }

        return files_metadata, truncation_info

    def calculate_archive_checksum(self, archive_path: str) -> str:
        """Calculate SHA256 checksum of archive for integrity verification."""
        sha256_hash = hashlib.sha256()
        try:
            with open(archive_path, "rb") as f:
                for chunk in iter(lambda: f.read(self.chunk_size), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except (OSError, IOError) as e:
            logger.warning("Could not calculate archive checksum: %s", e)
            return ""

    def generate_archive_metadata(
        self,
        archive_path: str,
        source_directory: str,
        files: List[Tuple[Path, str]],
        file_stats: Dict[str, Any],
        compression_format: str,
        compression_level: int,
    ) -> Dict[str, Any]:
        """Generate secure metadata for archive."""
        metadata = self.generate_base_metadata(
            archive_path,
            source_directory,
            files,
            file_stats,
            compression_format,
            compression_level,
        )

        files_metadata, truncation_info = self.generate_files_metadata(files)
        metadata["files"] = files_metadata
        metadata.update(truncation_info)

        return metadata


class MetadataInjector:
    """Handles injection of metadata into different archive formats."""

    def __init__(self, compression_level: int = 6):
        self.compression_level = compression_level

    def create_metadata_temp_file(self, metadata: Dict[str, Any]) -> str:
        """Create secure temporary file with metadata content."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            prefix="archive_meta_",
            delete=False,
        ) as temp_file:
            temp_metadata_path = temp_file.name
            json.dump(metadata, temp_file, indent=2, ensure_ascii=False)
        return temp_metadata_path

    def cleanup_metadata_temp_file(self, temp_metadata_path: str) -> None:
        """Clean up temporary metadata file."""
        try:
            os.unlink(temp_metadata_path)
        except OSError:
            pass

    def add_metadata_to_zip_archive(
        self, archive_path: str, temp_metadata_path: str
    ) -> None:
        """Add metadata to ZIP archive."""
        with zipfile.ZipFile(
            archive_path, "a", compression=zipfile.ZIP_DEFLATED
        ) as zipf:
            zipf.write(temp_metadata_path, "archive_metadata.json")

    def read_existing_zstd_archive(self, archive_path: str) -> bytes:
        """Read and decompress existing ZSTD archive."""
        if not ZSTD_AVAILABLE:
            raise ImportError("ZSTD library not available")

        with open(archive_path, "rb") as f:
            compressed_data = f.read()

        dctx = zstd.ZstdDecompressor()
        return dctx.decompress(compressed_data)

    def copy_existing_tar_members(
        self, old_tar: "tarfile.TarFile", new_tar: "tarfile.TarFile"
    ) -> None:
        """Copy existing tar members to new archive."""
        for member in old_tar:
            if member.isfile():
                file_data = old_tar.extractfile(member).read()
                tarinfo = tarfile.TarInfo(name=member.name)
                tarinfo.size = len(file_data)
                tarinfo.mtime = member.mtime
                new_tar.addfile(tarinfo, io.BytesIO(file_data))

    def create_new_zstd_archive_with_metadata(
        self, temp_new_archive: str, decompressed_data: bytes, metadata_file_path: str
    ) -> None:
        """Create new ZSTD archive including existing files and metadata."""
        if not ZSTD_AVAILABLE:
            raise ImportError("ZSTD library not available")

        cctx = zstd.ZstdCompressor(
            level=self.compression_level,
            write_content_size=True,
            write_checksum=True,
        )

        with open(temp_new_archive, "wb") as new_file:
            with cctx.stream_writer(new_file) as compressor:
                with tarfile.open(fileobj=compressor, mode="w|") as new_tar:
                    # Add existing files from old archive
                    old_tar_buffer = io.BytesIO(decompressed_data)
                    with tarfile.open(fileobj=old_tar_buffer, mode="r|") as old_tar:
                        self.copy_existing_tar_members(old_tar, new_tar)

                    # Add metadata file
                    new_tar.add(metadata_file_path, arcname="archive_metadata.json")

    def cleanup_temp_file(self, temp_file_path: str) -> None:
        """Clean up temporary file."""
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass

    def add_metadata_to_zstd_archive(
        self, archive_path: str, metadata_file_path: str
    ) -> None:
        """Add metadata to ZSTD archive by recreating with metadata included."""
        temp_new_archive = f"{archive_path}.with_metadata.tmp"

        try:
            # Read and decompress existing archive
            decompressed_data = self.read_existing_zstd_archive(archive_path)

            # Create new archive with metadata
            self.create_new_zstd_archive_with_metadata(
                temp_new_archive, decompressed_data, metadata_file_path
            )

            # Replace original with new archive
            os.rename(temp_new_archive, archive_path)

        except Exception as e:
            logger.warning("Failed to add metadata to ZSTD archive: %s", e)
            self.cleanup_temp_file(temp_new_archive)

    def add_metadata_to_archive(
        self,
        archive_path: str,
        metadata: Dict[str, Any],
        compression_format: str,
    ) -> None:
        """Add metadata file to existing archive with proper security."""
        temp_metadata_path = self.create_metadata_temp_file(metadata)

        try:
            if compression_format == "zip":
                self.add_metadata_to_zip_archive(archive_path, temp_metadata_path)
            elif compression_format == "zstd":
                self.add_metadata_to_zstd_archive(archive_path, temp_metadata_path)
            else:
                raise ValueError(
                    f"Unsupported compression format: {compression_format}"
                )

            logger.debug("Metadata added to archive successfully")

        except Exception as e:
            logger.warning("Failed to add metadata to archive: %s", e)
        finally:
            self.cleanup_metadata_temp_file(temp_metadata_path)


class ArchiveMetadataManager:
    """High-level metadata management for archives."""

    def __init__(self, compression_level: int = 6, chunk_size: int = 8192):
        self.generator = MetadataGenerator(chunk_size)
        self.injector = MetadataInjector(compression_level)

    def add_metadata_to_archive(
        self,
        archive_path: str,
        source_directory: str,
        files: List[Tuple[Path, str]],
        file_stats: Dict[str, Any],
        compression_format: str,
        compression_level: int,
    ) -> None:
        """Generate and add metadata to archive."""
        metadata = self.generator.generate_archive_metadata(
            archive_path,
            source_directory,
            files,
            file_stats,
            compression_format,
            compression_level,
        )

        self.injector.add_metadata_to_archive(
            archive_path, metadata, compression_format
        )
