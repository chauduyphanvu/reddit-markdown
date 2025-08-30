# GitHub Actions Workflows

This directory contains the CI/CD workflows for the reddit-markdown project.

## Workflows Overview

### 🔄 CI (`ci.yml`)
**Triggers:** Push to main/develop, Pull Requests, Manual dispatch

**What it does:**
- Tests Python implementation on multiple versions (3.8-3.12) and OS (Ubuntu, macOS, Windows)
- Tests Ruby implementation on multiple versions (2.7-3.2) on Ubuntu and macOS
- Runs code quality checks (flake8, black, mypy)
- Performs security scanning with bandit
- Runs comprehensive test suites

### 🚀 Release (`release.yml`)
**Triggers:** Version tags (v*.*.*), Manual dispatch

**What it does:**
- Validates code before release
- Generates changelog from git commits
- Creates release archives (Python-focused, Ruby-focused, Complete)
- Publishes GitHub releases with detailed installation instructions
- Prioritizes Python in release notes and instructions

### 🔍 Code Quality (`code-quality.yml`)
**Triggers:** Weekly schedule, Push to main, Manual dispatch

**What it does:**
- Runs comprehensive linting with pylint
- Calculates code complexity metrics
- Performs security scans
- Audits dependencies for security vulnerabilities
- Uploads quality reports as artifacts

### 🔄 Dependency Updates (`dependency-updates.yml`)
**Triggers:** Monthly schedule, Manual dispatch

**What it does:**
- Updates Python and Ruby dependencies
- Tests with updated dependencies
- Creates pull requests with dependency updates
- Includes testing status and review guidelines

## Usage

### Running Tests Locally
```bash
# Python tests
cd python && python -m unittest discover -s . -p "test_*.py" -v

# Install development dependencies
pip install -r requirements.txt

# Code formatting
black python/
flake8 python/

# Security scan
bandit -r python/
```

### Creating Releases
1. Create and push a version tag:
   ```bash
   git tag v1.13.0
   git push origin v1.13.0
   ```
2. The release workflow will automatically create a GitHub release

### Manual Workflow Triggers
All workflows support manual triggering via the GitHub Actions UI under the "Actions" tab.

## Dependencies
- **Python:** requests, pytest, flake8, black, mypy, bandit
- **Ruby:** json, kramdown (from Gemfile)

## Notes
- Python is prioritized as the main implementation
- Ruby support is maintained as an alternative
- All workflows include security scanning and quality checks
- Releases include separate archives for Python, Ruby, and complete packages