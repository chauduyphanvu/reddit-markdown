from .file_manager import FileManager

# Modular archive components
from .archive_security import (
    SecurityValidator,
    ArchiveLimitsExceededError,
    PathSecurityError,
)
from .file_scanner import FileScanner, ArchiveFileCollector, FileStats
from .archive_creators import (
    ArchiveCreator,
    ZipArchiveCreator,
    ZstdArchiveCreator,
    ArchiveCreatorFactory,
    ProgressReporter,
)
from .metadata_manager import (
    MetadataGenerator,
    MetadataInjector,
    ArchiveMetadataManager,
)
from .archive_verifier import ZipArchiveVerifier, ZstdArchiveVerifier, ArchiveVerifier
from .path_utils import ArchivePathGenerator, TempFileManager

# Main archive manager (now using modular architecture)
from .archive_manager import ArchiveManager, create_archive_with_progress

__all__ = [
    # Core components
    "FileManager",
    "ArchiveManager",
    "create_archive_with_progress",
    # Security components
    "SecurityValidator",
    "ArchiveLimitsExceededError",
    "PathSecurityError",
    # File scanning components
    "FileScanner",
    "ArchiveFileCollector",
    "FileStats",
    # Archive creation components
    "ArchiveCreator",
    "ZipArchiveCreator",
    "ZstdArchiveCreator",
    "ArchiveCreatorFactory",
    "ProgressReporter",
    # Metadata management
    "MetadataGenerator",
    "MetadataInjector",
    "ArchiveMetadataManager",
    # Verification components
    "ZipArchiveVerifier",
    "ZstdArchiveVerifier",
    "ArchiveVerifier",
    # Path utilities
    "ArchivePathGenerator",
    "TempFileManager",
]
