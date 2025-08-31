"""
Archive integrity verification.

This module provides comprehensive integrity verification for different
archive formats including content validation and structure checking.
"""

import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)

try:
    import zstandard as zstd

    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False


class ZipArchiveVerifier:
    """Verifies ZIP archive integrity."""

    def verify_integrity(self, archive_path: str) -> bool:
        """Verify ZIP archive integrity."""
        try:
            with zipfile.ZipFile(archive_path, "r") as zipf:
                # Test archive integrity
                bad_file = zipf.testzip()
                if bad_file is not None:
                    logger.debug("ZIP integrity check failed on file: %s", bad_file)
                    return False

                # Try to read a few files to ensure they're accessible
                file_list = zipf.namelist()
                test_files = file_list[: min(5, len(file_list))]  # Test first 5 files

                for filename in test_files:
                    try:
                        with zipf.open(filename) as f:
                            f.read(
                                1024
                            )  # Read first chunk to verify decompression works
                    except Exception as e:
                        logger.debug("Failed to read file %s from ZIP: %s", filename, e)
                        return False

                return True
        except Exception as e:
            logger.debug("ZIP integrity verification failed: %s", e)
            return False

    def get_archive_info(self, archive_path: str) -> Dict[str, Any]:
        """Get detailed information about ZIP archive."""
        try:
            with zipfile.ZipFile(archive_path, "r") as zipf:
                file_list = zipf.infolist()
                return {
                    "file_count": len(file_list),
                    "compressed_size": sum(f.compress_size for f in file_list),
                    "uncompressed_size": sum(f.file_size for f in file_list),
                    "compression_ratio": (
                        (
                            1
                            - sum(f.compress_size for f in file_list)
                            / sum(f.file_size for f in file_list)
                        )
                        * 100
                        if sum(f.file_size for f in file_list) > 0
                        else 0
                    ),
                }
        except Exception as e:
            logger.debug("Error getting ZIP info: %s", e)
            return {
                "file_count": 0,
                "compressed_size": 0,
                "uncompressed_size": 0,
                "compression_ratio": 0,
            }


class ZstdArchiveVerifier:
    """Verifies ZSTD archive integrity."""

    def verify_integrity(self, archive_path: str) -> bool:
        """Verify ZSTD archive integrity."""
        if not ZSTD_AVAILABLE:
            logger.debug("ZSTD library not available for verification")
            return False

        try:
            with open(archive_path, "rb") as f:
                dctx = zstd.ZstdDecompressor()

                # Use streaming decompression to avoid memory issues
                with dctx.stream_reader(f) as decompressor:
                    with tarfile.open(fileobj=decompressor, mode="r|") as tar:
                        # Verify we can read tar structure
                        file_count = 0
                        for member in tar:
                            if member.isfile() and file_count < 5:  # Test first 5 files
                                try:
                                    # Try to extract a small amount of data
                                    file_data = tar.extractfile(member)
                                    if file_data:
                                        file_data.read(1024)
                                    file_count += 1
                                except Exception as e:
                                    logger.debug(
                                        "Failed to read file %s from ZSTD archive: %s",
                                        member.name,
                                        e,
                                    )
                                    return False
                            elif file_count >= 5:
                                break  # Don't test all files, just verify structure

                return True

        except zstd.ZstdError as e:
            logger.debug("ZSTD decompression error: %s", e)
            return False
        except tarfile.TarError as e:
            logger.debug("TAR structure error: %s", e)
            return False
        except Exception as e:
            logger.debug("ZSTD integrity verification failed: %s", e)
            return False

    def get_archive_info(self, archive_path: str) -> Dict[str, Any]:
        """Get detailed information about ZSTD archive."""
        if not ZSTD_AVAILABLE:
            logger.debug("ZSTD library not available for info extraction")
            return {
                "file_count": 0,
                "compressed_size": 0,
                "uncompressed_size": 0,
                "compression_ratio": 0,
            }

        try:
            with open(archive_path, "rb") as f:
                compressed_size = f.seek(0, 2)  # Seek to end to get size
                f.seek(0)  # Reset to beginning

                dctx = zstd.ZstdDecompressor()
                with dctx.stream_reader(f) as decompressor:
                    with tarfile.open(fileobj=decompressor, mode="r|") as tar:
                        file_count = 0
                        uncompressed_size = 0

                        for member in tar:
                            if member.isfile():
                                file_count += 1
                                uncompressed_size += member.size

                        return {
                            "file_count": file_count,
                            "compressed_size": compressed_size,
                            "uncompressed_size": uncompressed_size,
                            "compression_ratio": (
                                (1 - compressed_size / uncompressed_size) * 100
                                if uncompressed_size > 0
                                else 0
                            ),
                        }

        except Exception as e:
            logger.debug("Error getting ZSTD info: %s", e)
            return {
                "file_count": 0,
                "compressed_size": 0,
                "uncompressed_size": 0,
                "compression_ratio": 0,
            }


class ArchiveVerifier:
    """High-level archive verification interface."""

    def __init__(self):
        self.zip_verifier = ZipArchiveVerifier()
        self.zstd_verifier = ZstdArchiveVerifier()

    def verify_archive_integrity(self, archive_path: str) -> bool:
        """Verify archive integrity based on file extension."""
        try:
            if archive_path.endswith(".zip"):
                return self.zip_verifier.verify_integrity(archive_path)
            elif archive_path.endswith(".zst"):
                return self.zstd_verifier.verify_integrity(archive_path)
            else:
                logger.debug("Unknown archive format for integrity check")
                return False

        except Exception as e:
            logger.debug("Archive integrity check failed: %s", e)
            return False

    def get_archive_info(self, archive_path: str) -> Dict[str, Any]:
        """Get comprehensive information about an archive."""
        path = Path(archive_path)

        if not path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        # Basic file information
        info = {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "size_mb": path.stat().st_size / (1024 * 1024),
            "modified_time": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "format": "unknown",
            "valid": False,
            "file_count": 0,
        }

        # Format-specific information
        if archive_path.endswith(".zip"):
            info["format"] = "zip"
            format_info = self.zip_verifier.get_archive_info(archive_path)
        elif archive_path.endswith(".zst"):
            info["format"] = "zstd"
            format_info = self.zstd_verifier.get_archive_info(archive_path)
        else:
            format_info = {
                "file_count": 0,
                "compressed_size": 0,
                "uncompressed_size": 0,
                "compression_ratio": 0,
            }

        info.update(format_info)
        info["valid"] = self.verify_archive_integrity(archive_path)

        return info
