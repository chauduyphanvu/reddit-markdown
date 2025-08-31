"""
Main CI/CD runner - orchestrates all CI/CD operations.
Implementation with built-in task execution.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import json

from .tasks import (
    TestRunner,
    QualityRunner,
    SecurityRunner,
    DependencyRunner,
    ReleaseRunner,
)


class CIRunner:
    """Main CI/CD pipeline orchestrator."""

    def __init__(
        self, config: Dict[str, Any], verbose: bool = False, dry_run: bool = False
    ):
        self.config = config
        self.verbose = verbose
        self.dry_run = dry_run

        # Set up paths
        self.project_root = Path(__file__).parent.parent.parent
        self.python_dir = self.project_root / self.config["global"]["working_directory"]
        self.reports_dir = (
            self.project_root / self.config["global"]["reports_directory"]
        )

        # Initialize task runners
        self.test_runner = TestRunner(self)
        self.quality_runner = QualityRunner(self)
        self.security_runner = SecurityRunner(self)
        self.dependency_runner = DependencyRunner(self)
        self.release_runner = ReleaseRunner(self)

        # Ensure reports directory exists
        self.reports_dir.mkdir(exist_ok=True)

    def log_info(self, message: str):
        """Log info message."""
        print(f"ℹ️  {message}")

    def log_success(self, message: str):
        """Log success message."""
        print(f"✅ {message}")

    def log_warning(self, message: str):
        """Log warning message."""
        print(f"⚠️  {message}")

    def log_error(self, message: str):
        """Log error message."""
        print(f"❌ {message}")

    def log_debug(self, message: str):
        """Log debug message (only in verbose mode)."""
        if self.verbose:
            print(f"🐛 {message}")

    def run_command(
        self,
        cmd: List[str],
        cwd: Optional[Union[str, Path]] = None,
        capture_output: bool = True,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """
        Run a command with consistent logging and error handling.

        Args:
            cmd: Command to run as list of strings
            cwd: Working directory (defaults to python directory)
            capture_output: Whether to capture stdout/stderr
            timeout: Command timeout in seconds

        Returns:
            CompletedProcess result
        """
        if cwd is None:
            cwd = self.python_dir

        cmd_str = " ".join(cmd)
        self.log_debug(f"Running: {cmd_str} (cwd: {cwd})")

        if self.dry_run:
            self.log_info(f"[DRY RUN] Would run: {cmd_str}")
            # Return a mock successful result for dry run
            result = subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            return result

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False,  # Don't raise on non-zero exit, let caller handle
            )

            if result.returncode == 0:
                self.log_debug(f"✅ Command succeeded: {cmd_str}")
            else:
                self.log_debug(
                    f"❌ Command failed (code {result.returncode}): {cmd_str}"
                )
                if self.verbose and result.stderr:
                    self.log_debug(f"STDERR: {result.stderr.strip()}")

            return result

        except subprocess.TimeoutExpired as e:
            self.log_error(f"⏰ Command timed out after {timeout}s: {cmd_str}")
            raise
        except Exception as e:
            self.log_error(f"💥 Command failed with exception: {cmd_str} - {e}")
            raise

    def list_commands(self):
        """List all available commands."""
        self.log_info("Available CI/CD commands:")

        for cmd, config in self.config["commands"].items():
            description = config.get("description", "No description")
            self.log_info(f"  {cmd:12} - {description}")

            # Show steps for composite commands
            if "steps" in config:
                steps_str = " → ".join(config["steps"])
                self.log_info(f"               Steps: {steps_str}")

    def run_ci_pipeline(self, **kwargs) -> bool:
        """Run the full CI pipeline."""
        self.log_info("🚀 Starting full CI pipeline")

        steps = self.config["commands"]["ci"]["steps"]
        fail_fast = self.config["commands"]["ci"]["fail_fast"]

        results = {}
        overall_success = True

        for step in steps:
            self.log_info(f"🔄 Running step: {step}")

            if step == "test":
                success = self.test_runner.run(**kwargs)
            elif step == "quality":
                success = self.quality_runner.run(**kwargs)
            elif step == "security":
                success = self.security_runner.run(**kwargs)
            else:
                self.log_error(f"Unknown pipeline step: {step}")
                success = False

            results[step] = success

            if not success:
                overall_success = False
                if fail_fast:
                    self.log_error(
                        f"❌ Step '{step}' failed, stopping pipeline (fail_fast=True)"
                    )
                    break
                else:
                    self.log_warning(
                        f"⚠️  Step '{step}' failed, continuing (fail_fast=False)"
                    )

        # Generate pipeline report
        self._save_pipeline_report("ci", results)

        return overall_success

    def run_tests(self, **kwargs) -> bool:
        """Run tests."""
        return self.test_runner.run(**kwargs)

    def run_quality(self, **kwargs) -> bool:
        """Run quality checks."""
        return self.quality_runner.run(**kwargs)

    def run_security(self, **kwargs) -> bool:
        """Run security scans."""
        return self.security_runner.run(**kwargs)

    def run_dependencies(self, **kwargs) -> bool:
        """Update dependencies."""
        return self.dependency_runner.run(**kwargs)

    def run_release(self, version: str, **kwargs) -> bool:
        """Create a release."""
        return self.release_runner.run(version, **kwargs)

    def _save_pipeline_report(self, pipeline_name: str, results: Dict[str, bool]):
        """Save pipeline execution report."""
        try:
            report = {
                "pipeline": pipeline_name,
                "timestamp": time.time(),
                "results": results,
                "overall_success": all(results.values()),
                "config": self.config,
            }

            report_file = self.reports_dir / f"{pipeline_name}-report.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)

            self.log_debug(f"📄 Pipeline report saved to: {report_file}")

        except Exception as e:
            self.log_warning(f"Failed to save pipeline report: {e}")

    def check_tool_available(self, tool: str) -> bool:
        """Check if a command-line tool is available."""
        try:
            result = self.run_command([tool, "--version"], capture_output=True)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
