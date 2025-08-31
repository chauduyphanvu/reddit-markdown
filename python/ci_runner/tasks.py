"""
Task runners for CI/CD operations.
Consolidated implementation of all CI/CD tasks in one file for simplicity.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .runner import CIRunner


class BaseTaskRunner:
    """Base class for all task runners."""

    def __init__(self, ci_runner: "CIRunner"):
        self.ci = ci_runner
        self.config = ci_runner.config
        self.python_dir = ci_runner.python_dir
        self.project_root = ci_runner.project_root

    def run(self, **kwargs) -> bool:
        """Run the task. Must be implemented by subclasses."""
        raise NotImplementedError


class TestRunner(BaseTaskRunner):
    """Handles test execution."""

    def run(self, **kwargs) -> bool:
        """Run all tests."""
        self.ci.log_info("🧪 Running test suite")

        config = self.config["commands"]["test"]

        # Check if pytest is available
        if not self.ci.check_tool_available("pytest"):
            self.ci.log_error(
                "pytest is not available. Install with: pip install pytest"
            )
            return False

        # Build pytest command
        cmd = ["python3", "-m", "pytest"]

        # Add test patterns
        if kwargs.get("test_pattern"):
            cmd.append(kwargs["test_pattern"])
        else:
            cmd.extend(config.get("patterns", ["tests/"]))

        # Add coverage if enabled
        if config.get("coverage", True) and self.ci.check_tool_available("coverage"):
            cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])

        # Add verbosity
        if self.ci.verbose:
            cmd.extend(["-v", "-s"])
        else:
            cmd.append("-q")

        # Skip Ruby tests if requested
        if kwargs.get("python_only", False):
            self.ci.log_info("🐍 Running Python tests only")

        # Run tests
        result = self.ci.run_command(cmd, timeout=config.get("timeout", 600))

        if result.returncode == 0:
            self.ci.log_success("✅ All tests passed")
            return True
        else:
            self.ci.log_error(f"❌ Tests failed (exit code: {result.returncode})")
            if result.stdout and self.ci.verbose:
                self.ci.log_debug(f"Test output:\\n{result.stdout}")
            return False


class QualityRunner(BaseTaskRunner):
    """Handles code quality checks."""

    def run(self, **kwargs) -> bool:
        """Run quality checks."""
        self.ci.log_info("🔍 Running quality checks")

        config = self.config["commands"]["quality"]
        tools = config.get("tools", {})

        overall_success = True

        for tool_name, tool_config in tools.items():
            if not tool_config.get("enabled", True):
                continue

            success = self._run_quality_tool(tool_name, tool_config, **kwargs)
            if not success:
                overall_success = False

        if overall_success:
            self.ci.log_success("✅ All quality checks passed")
        else:
            self.ci.log_error("❌ Some quality checks failed")

        return overall_success

    def _run_quality_tool(
        self, tool_name: str, tool_config: Dict[str, Any], **kwargs
    ) -> bool:
        """Run a specific quality tool."""
        self.ci.log_info(f"🔧 Running {tool_name}")

        # Check if tool is available
        if not self.ci.check_tool_available(tool_name):
            self.ci.log_warning(f"{tool_name} is not available, skipping")
            return True  # Don't fail if optional tool is missing

        # Build command
        cmd = [tool_name]

        # Add configured arguments
        args = tool_config.get("args", [])

        # Apply auto-fix if requested and supported
        if kwargs.get("fix", False):
            if tool_name == "black":
                # Remove --check and --diff for auto-fix
                args = [arg for arg in args if arg not in ["--check", "--diff"]]
            elif tool_name == "flake8":
                self.ci.log_info(f"⚠️  {tool_name} cannot auto-fix, running check only")

        cmd.extend(args)

        # Add target directory/files
        if tool_name == "mypy":
            cmd.append(".")  # mypy needs explicit target
        elif tool_name == "black":
            cmd.append(".")
        elif tool_name == "flake8":
            cmd.append(".")

        # Run the tool
        result = self.ci.run_command(cmd, timeout=300)

        if result.returncode == 0:
            self.ci.log_success(f"✅ {tool_name} passed")
            return True
        else:
            self.ci.log_error(f"❌ {tool_name} failed")
            if result.stdout and self.ci.verbose:
                self.ci.log_debug(f"{tool_name} output:\\n{result.stdout}")
            return False


class SecurityRunner(BaseTaskRunner):
    """Handles security scans."""

    def run(self, **kwargs) -> bool:
        """Run security scans."""
        self.ci.log_info("🛡️  Running security scans")

        config = self.config["commands"]["security"]
        tools = config.get("tools", {})

        overall_success = True

        for tool_name, tool_config in tools.items():
            if not tool_config.get("enabled", True):
                continue

            success = self._run_security_tool(tool_name, tool_config)
            if not success:
                overall_success = False

        if overall_success:
            self.ci.log_success("✅ All security scans passed")
        else:
            self.ci.log_error("❌ Some security scans found issues")

        return overall_success

    def _run_security_tool(self, tool_name: str, tool_config: Dict[str, Any]) -> bool:
        """Run a specific security tool."""
        self.ci.log_info(f"🔒 Running {tool_name}")

        # Check if tool is available
        if not self.ci.check_tool_available(tool_name):
            self.ci.log_warning(f"{tool_name} is not available, skipping")
            return True  # Don't fail if optional tool is missing

        # Build command
        cmd = [tool_name]
        cmd.extend(tool_config.get("args", []))

        # Run the tool
        result = self.ci.run_command(cmd, timeout=600)

        if result.returncode == 0:
            self.ci.log_success(f"✅ {tool_name} found no issues")
            return True
        else:
            self.ci.log_error(f"❌ {tool_name} found security issues")
            if result.stdout and self.ci.verbose:
                self.ci.log_debug(f"{tool_name} output:\\n{result.stdout}")
            return False


class DependencyRunner(BaseTaskRunner):
    """Handles dependency management."""

    def run(self, **kwargs) -> bool:
        """Update dependencies."""
        self.ci.log_info("📦 Managing dependencies")

        config = self.config["commands"]["deps"]

        # Create backup if requested
        if config.get("create_backup", True):
            self._backup_requirements()

        # Update Python dependencies
        python_success = self._update_python_dependencies()

        # Update Ruby dependencies (if Gemfile exists)
        ruby_success = True
        if (self.project_root / "Gemfile").exists():
            ruby_success = self._update_ruby_dependencies()

        overall_success = python_success and ruby_success

        if overall_success:
            self.ci.log_success("✅ Dependencies updated successfully")
        else:
            self.ci.log_error("❌ Some dependency updates failed")

        return overall_success

    def _backup_requirements(self):
        """Create backup of requirements files."""
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            backup_file = requirements_file.with_suffix(".txt.backup")
            shutil.copy2(requirements_file, backup_file)
            self.ci.log_info(f"📄 Created backup: {backup_file}")

    def _update_python_dependencies(self) -> bool:
        """Update Python dependencies."""
        self.ci.log_info("🐍 Updating Python dependencies")

        # Update pip first
        result = self.ci.run_command(
            ["python3", "-m", "pip", "install", "--upgrade", "pip"]
        )
        if result.returncode != 0:
            self.ci.log_error("Failed to update pip")
            return False

        # Install/update requirements
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            result = self.ci.run_command(
                [
                    "python3",
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(requirements_file),
                    "--upgrade",
                ]
            )
            if result.returncode != 0:
                self.ci.log_error("Failed to update Python dependencies")
                return False

        return True

    def _update_ruby_dependencies(self) -> bool:
        """Update Ruby dependencies."""
        self.ci.log_info("💎 Updating Ruby dependencies")

        # Check if bundler is available
        if not self.ci.check_tool_available("bundle"):
            self.ci.log_warning("Bundler not available, skipping Ruby dependencies")
            return True

        # Update Ruby gems
        result = self.ci.run_command(["bundle", "update"], cwd=self.project_root)
        if result.returncode != 0:
            self.ci.log_error("Failed to update Ruby dependencies")
            return False

        return True


class ReleaseRunner(BaseTaskRunner):
    """Handles release creation."""

    def run(self, version: str, **kwargs) -> bool:
        """Create a release."""
        self.ci.log_info(f"🚀 Creating release {version}")

        config = self.config["commands"]["release"]

        # Check for clean repo if required
        if config.get("require_clean_repo", True):
            if not self._is_repo_clean():
                self.ci.log_error(
                    "Repository has uncommitted changes. Commit or stash changes first."
                )
                return False

        # Validate version format
        if not self._validate_version(version):
            self.ci.log_error(f"Invalid version format: {version}")
            return False

        # Create git tag
        if not self._create_git_tag(version):
            return False

        # Create GitHub release if requested
        if config.get("create_github_release", True) and not kwargs.get("draft", False):
            if not self._create_github_release(version):
                return False

        self.ci.log_success(f"✅ Release {version} created successfully")
        return True

    def _is_repo_clean(self) -> bool:
        """Check if git repository is clean."""
        result = self.ci.run_command(
            ["git", "status", "--porcelain"], cwd=self.project_root
        )
        return result.returncode == 0 and not result.stdout.strip()

    def _validate_version(self, version: str) -> bool:
        """Validate version string format."""
        # Simple semantic version validation
        pattern = r"^v?\d+\.\d+\.\d+(?:-[\w\.-]+)?$"
        return bool(re.match(pattern, version))

    def _create_git_tag(self, version: str) -> bool:
        """Create git tag for version."""
        self.ci.log_info(f"🏷️  Creating git tag: {version}")

        result = self.ci.run_command(
            ["git", "tag", "-a", version, "-m", f"Release {version}"],
            cwd=self.project_root,
        )

        if result.returncode != 0:
            self.ci.log_error(f"Failed to create git tag: {version}")
            return False

        # Push tag to remote
        result = self.ci.run_command(
            ["git", "push", "origin", version], cwd=self.project_root
        )

        if result.returncode != 0:
            self.ci.log_warning(f"Failed to push tag to remote: {version}")
            # Don't fail the release for push issues

        return True

    def _create_github_release(self, version: str) -> bool:
        """Create GitHub release using gh CLI."""
        self.ci.log_info(f"🐙 Creating GitHub release: {version}")

        # Check if gh CLI is available
        if not self.ci.check_tool_available("gh"):
            self.ci.log_warning(
                "GitHub CLI (gh) not available, skipping GitHub release"
            )
            return True

        # Create release
        result = self.ci.run_command(
            [
                "gh",
                "release",
                "create",
                version,
                "--title",
                f"Release {version}",
                "--notes",
                f"Release {version} created by CI/CD system",
            ],
            cwd=self.project_root,
        )

        if result.returncode != 0:
            self.ci.log_error(f"Failed to create GitHub release: {version}")
            return False

        return True
