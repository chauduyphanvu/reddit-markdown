"""
Security validation components for archive operations.

This module provides security-focused validation for file paths, extensions,
size limits, and content-based validation using magic numbers to prevent 
directory traversal and malicious file inclusion.
"""

import os
from pathlib import Path, PurePath
from typing import Set, Dict, Optional
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)

# Security constants
MAX_ARCHIVE_SIZE = 50 * 1024 * 1024 * 1024  # 50GB limit
MAX_FILES_PER_ARCHIVE = 100000  # File count limit
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".html", ".xml", ".csv"}
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB per file limit

# Magic number signatures for allowed file types
# These are the first few bytes that identify legitimate file types
ALLOWED_MAGIC_NUMBERS: Dict[str, bytes] = {
    # Text files (UTF-8, ASCII, or with BOM)
    ".txt": b"",  # Text files can start with any valid text characters
    ".md": b"",  # Markdown files are plain text
    # JSON files
    ".json": b"{",  # JSON typically starts with { or [
    # YAML files
    ".yaml": b"",  # YAML can start with various characters
    ".yml": b"",
    # HTML files
    ".html": b"<",  # HTML starts with < (DOCTYPE or tag)
    ".xml": b"<",  # XML starts with < (declaration or root element)
    # CSV files
    ".csv": b"",  # CSV can start with any text characters
}

# Known dangerous magic numbers (executable files, archives, etc.)
DANGEROUS_MAGIC_NUMBERS = {
    b"MZ": "Windows PE executable",
    b"\x7fELF": "Linux ELF executable",
    b"\xca\xfe\xba\xbe": "Java class file",
    b"\xfe\xed\xfa\xce": "Mach-O executable",
    b"PK": "ZIP archive/Java JAR",
    b"\x1f\x8b": "GZIP compressed",
    b"BZ": "BZIP2 compressed",
    b"\x28\xb5\x2f\xfd": "Zstandard compressed",
    b"\x50\x4b\x03\x04": "ZIP file",
    b"\x50\x4b\x05\x06": "Empty ZIP file",
    b"\x50\x4b\x07\x08": "Spanned ZIP file",
    b"\x52\x61\x72\x21": "RAR archive",
    b"\x37\x7a\xbc\xaf": "7-Zip archive",
    b"\x00\x00\x00\x00\x66\x74\x79\x70": "MP4/MOV video",
    b"\x47\x49\x46\x38": "GIF image",
    b"\x89\x50\x4e\x47": "PNG image",
    b"\xff\xd8\xff": "JPEG image",
    b"\x42\x4d": "BMP image",
}


class SecurityValidator:
    """Handles security validation for archive operations."""

    def __init__(self, validate_paths: bool = True, validate_content: bool = True):
        self.validate_paths = validate_paths
        self.validate_content = validate_content
        self.allowed_extensions = ALLOWED_EXTENSIONS.copy()
        self._magic_available = self._check_magic_availability()

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

    def _check_magic_availability(self) -> bool:
        """Check if python-magic library is available."""
        try:
            import magic

            return True
        except ImportError:
            logger.debug(
                "python-magic not available, using built-in magic number validation"
            )
            return False

    def _read_file_header(
        self, file_path: Path, bytes_to_read: int = 16
    ) -> Optional[bytes]:
        """Safely read the first few bytes of a file."""
        try:
            with open(file_path, "rb") as f:
                return f.read(bytes_to_read)
        except (OSError, IOError) as e:
            logger.warning("Cannot read file header for %s: %s", file_path, e)
            return None

    def _validate_with_python_magic(self, file_path: Path) -> Optional[bool]:
        """Validate file using python-magic library if available."""
        if not self._magic_available:
            return None

        try:
            import magic

            mime = magic.Magic(mime=True)
            file_type = mime.from_file(str(file_path))

            # Allow text-based MIME types that correspond to our allowed extensions
            allowed_mime_types = {
                "text/plain",  # .txt, .md
                "text/markdown",  # .md
                "application/json",  # .json
                "text/yaml",  # .yaml, .yml
                "application/x-yaml",  # .yaml, .yml
                "text/html",  # .html
                "application/xhtml+xml",  # .html
                "text/xml",  # .xml
                "application/xml",  # .xml
                "text/csv",  # .csv
                "application/csv",  # .csv
            }

            if file_type in allowed_mime_types:
                return True
            else:
                logger.warning(
                    "File type not allowed by MIME validation: %s (%s)",
                    file_path,
                    file_type,
                )
                return False

        except Exception as e:
            logger.debug("python-magic validation failed for %s: %s", file_path, e)
            return None

    def _validate_with_builtin_magic(self, file_path: Path) -> bool:
        """Validate file using built-in magic number checking."""
        header = self._read_file_header(file_path, 16)
        if header is None:
            return False

        # Check for dangerous magic numbers first
        for dangerous_magic, description in DANGEROUS_MAGIC_NUMBERS.items():
            if header.startswith(dangerous_magic):
                logger.error(
                    "Dangerous file type detected: %s (%s)", file_path, description
                )
                return False

        # For text-based files, check if they contain valid text
        extension = file_path.suffix.lower()

        if extension in {".txt", ".md", ".csv", ".yaml", ".yml"}:
            # Check if file appears to be text (no null bytes in first chunk)
            try:
                if b"\x00" in header:
                    logger.warning(
                        "Binary content detected in text file: %s", file_path
                    )
                    return False

                # Try to decode as UTF-8
                header.decode("utf-8", errors="strict")
                return True
            except UnicodeDecodeError:
                # Try other encodings or allow if it's mostly text
                try:
                    header.decode("latin1", errors="strict")
                    logger.debug("Non-UTF-8 text file detected: %s", file_path)
                    return True
                except UnicodeDecodeError:
                    logger.warning("Invalid text encoding in file: %s", file_path)
                    return False

        elif extension == ".json":
            # JSON should start with { or [ (after whitespace)
            header_str = header.decode("utf-8", errors="ignore").lstrip()
            if header_str.startswith(("{", "[")):
                return True
            else:
                logger.warning("Invalid JSON format in file: %s", file_path)
                return False

        elif extension in {".html", ".xml"}:
            # HTML/XML should start with < (after whitespace)
            header_str = header.decode("utf-8", errors="ignore").lstrip()
            if header_str.startswith("<"):
                return True
            else:
                logger.warning("Invalid HTML/XML format in file: %s", file_path)
                return False

        # Default: allow if extension is in allowed list
        return True

    def validate_file_content(self, file_path: Path) -> bool:
        """Validate file content using magic numbers and content analysis."""
        if not self.validate_content:
            return True

        # First try python-magic if available
        magic_result = self._validate_with_python_magic(file_path)
        if magic_result is not None:
            return magic_result

        # Fallback to built-in magic number validation
        return self._validate_with_builtin_magic(file_path)

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
