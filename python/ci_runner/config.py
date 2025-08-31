"""
Configuration management for the CI/CD system.
Simple YAML-based configuration with sensible defaults.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


DEFAULT_CONFIG = {
    "global": {
        "working_directory": "python",
        "python_executable": "python3",
        "requirements_file": "requirements.txt",
        "test_directory": "tests",
        "reports_directory": "ci-reports",
    },
    "commands": {
        "ci": {
            "description": "Full CI pipeline (test + quality + security)",
            "steps": ["test", "quality", "security"],
            "fail_fast": True,
        },
        "test": {
            "description": "Run all tests",
            "timeout": 600,
            "patterns": ["tests/test_*.py"],
            "coverage": True,
        },
        "quality": {
            "description": "Code quality checks",
            "tools": {
                "black": {"enabled": True, "args": ["--check", "--diff"]},
                "flake8": {"enabled": True, "args": ["--max-line-length=88"]},
                "mypy": {"enabled": True, "args": ["--ignore-missing-imports"]},
            },
        },
        "security": {
            "description": "Security scans",
            "tools": {
                "bandit": {"enabled": True, "args": ["-r", ".", "-x", "tests/"]},
                "safety": {"enabled": True, "args": ["check"]},
            },
        },
        "deps": {
            "description": "Update dependencies",
            "auto_update": False,
            "create_backup": True,
        },
        "release": {
            "description": "Create release",
            "require_clean_repo": True,
            "create_github_release": True,
        },
    },
}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load CI configuration from YAML file with fallback to defaults.

    Args:
        config_path: Optional path to config file

    Returns:
        Configuration dictionary
    """
    # Determine config file path
    if config_path:
        config_file = Path(config_path)
    else:
        # Look for config in standard locations
        project_root = Path(__file__).parent.parent.parent
        possible_paths = [
            project_root / "python" / "ci-config.yml",
            project_root / "ci-config.yml",
            project_root / ".ci-config.yml",
        ]
        config_file = None
        for path in possible_paths:
            if path.exists():
                config_file = path
                break

    # Load config or use defaults
    config = DEFAULT_CONFIG.copy()

    if config_file and config_file.exists():
        try:
            with open(config_file, "r") as f:
                user_config = yaml.safe_load(f) or {}

            # Merge user config with defaults (deep merge)
            config = _deep_merge(config, user_config)

        except Exception as e:
            print(f"⚠️  Warning: Failed to load config from {config_file}: {e}")
            print("   Using default configuration")

    # Apply environment overrides
    config = _apply_env_overrides(config)

    return config


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary
        override: Dictionary to merge into base

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply environment variable overrides to config.

    Environment variables follow pattern: CI_<SECTION>_<KEY>=value
    Example: CI_GLOBAL_PYTHON_EXECUTABLE=python3.9

    Args:
        config: Base configuration

    Returns:
        Configuration with environment overrides applied
    """
    env_prefix = "CI_"

    for env_key, env_value in os.environ.items():
        if not env_key.startswith(env_prefix):
            continue

        # Parse environment key: CI_GLOBAL_PYTHON_EXECUTABLE -> ["global", "python_executable"]
        key_parts = env_key[len(env_prefix) :].lower().split("_")
        if len(key_parts) < 2:
            continue

        # Navigate and set config value
        current = config
        for part in key_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value (with type conversion)
        final_key = key_parts[-1]
        current[final_key] = _convert_env_value(env_value)

    return config


def _convert_env_value(value: str) -> Any:
    """
    Convert environment variable string to appropriate Python type.

    Args:
        value: Environment variable value

    Returns:
        Converted value
    """
    # Boolean conversion
    if value.lower() in ("true", "yes", "1", "on"):
        return True
    elif value.lower() in ("false", "no", "0", "off"):
        return False

    # Integer conversion
    try:
        return int(value)
    except ValueError:
        pass

    # Float conversion
    try:
        return float(value)
    except ValueError:
        pass

    # List conversion (comma-separated)
    if "," in value:
        return [item.strip() for item in value.split(",")]

    # String (default)
    return value
