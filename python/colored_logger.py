import logging
import sys
from typing import Dict, Any

# Define custom logging levels
TRACE_LEVEL = 5
SUCCESS_LEVEL = 25
PROGRESS_LEVEL = 22
NOTICE_LEVEL = 35
FAILURE_LEVEL = 45

# Add custom levels to logging module
logging.addLevelName(TRACE_LEVEL, "TRACE")
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")
logging.addLevelName(PROGRESS_LEVEL, "PROGRESS")
logging.addLevelName(NOTICE_LEVEL, "NOTICE")
logging.addLevelName(FAILURE_LEVEL, "FAILURE")


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds color codes to log messages based on log level."""

    # Extended ANSI color codes with styles
    COLORS = {
        "TRACE": "\033[90m",  # Bright Black (Gray)
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "PROGRESS": "\033[94m",  # Bright Blue
        "SUCCESS": "\033[92m",  # Bright Green
        "WARNING": "\033[33m",  # Yellow
        "NOTICE": "\033[96m",  # Bright Cyan
        "ERROR": "\033[31m",  # Red
        "FAILURE": "\033[91m",  # Bright Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def __init__(self, fmt: str = None, datefmt: str = None):
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        # Get the base formatted message
        message = super().format(record)

        # Only add colors if output is to a terminal
        if sys.stderr.isatty():
            level_color = self.COLORS.get(record.levelname, "")
            reset_color = self.COLORS["RESET"]
            return f"{level_color}{message}{reset_color}"

        return message


def setup_colored_logging(level: int = logging.INFO) -> None:
    """
    Configure colored logging for the application.

    Args:
        level: Logging level (default: logging.INFO)
    """
    # Create formatter
    formatter = ColoredFormatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler with color formatting
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


class EnhancedLogger:
    """Enhanced logger wrapper with custom level methods."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def trace(self, msg, *args, **kwargs):
        """Log with TRACE level (gray) - very detailed debugging info."""
        self._logger.log(TRACE_LEVEL, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        """Log with DEBUG level (cyan) - debugging info."""
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """Log with INFO level (green) - general information."""
        self._logger.info(msg, *args, **kwargs)

    def progress(self, msg, *args, **kwargs):
        """Log with PROGRESS level (bright blue) - progress updates."""
        self._logger.log(PROGRESS_LEVEL, msg, *args, **kwargs)

    def success(self, msg, *args, **kwargs):
        """Log with SUCCESS level (bright green) - successful operations."""
        self._logger.log(SUCCESS_LEVEL, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Log with WARNING level (yellow) - warnings."""
        self._logger.warning(msg, *args, **kwargs)

    def notice(self, msg, *args, **kwargs):
        """Log with NOTICE level (bright cyan) - important notices."""
        self._logger.log(NOTICE_LEVEL, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Log with ERROR level (red) - errors."""
        self._logger.error(msg, *args, **kwargs)

    def failure(self, msg, *args, **kwargs):
        """Log with FAILURE level (bright red) - critical failures."""
        self._logger.log(FAILURE_LEVEL, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """Log with CRITICAL level (magenta) - critical errors."""
        self._logger.critical(msg, *args, **kwargs)

    # Delegate other logger methods
    def __getattr__(self, name):
        return getattr(self._logger, name)


class ColoredLogger:
    """Wrapper class for easy logger creation with colored output."""

    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize colored logger.

        Args:
            name: Logger name
            level: Logging level
        """
        self.name = name
        self.logger = self._create_logger(name, level)

    def _create_logger(self, name: str, level: int) -> EnhancedLogger:
        """Create and configure the logger."""
        # Setup colored logging if not already configured
        if not logging.getLogger().handlers:
            setup_colored_logging(level)

        base_logger = logging.getLogger(name)
        base_logger.setLevel(level)

        return EnhancedLogger(base_logger)


def get_colored_logger(name: str) -> EnhancedLogger:
    """
    Get an enhanced logger instance with colored output support and custom levels.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Enhanced logger instance with custom level methods
    """
    base_logger = logging.getLogger(name)
    return EnhancedLogger(base_logger)
