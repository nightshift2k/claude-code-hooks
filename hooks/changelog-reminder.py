#!/usr/bin/env python3
"""
Changelog Reminder Hook - Ensures CHANGELOG.md is updated with meaningful changes.

This hook blocks git commit operations when meaningful files are staged but
CHANGELOG.md is not included. This enforces changelog hygiene by requiring
that code changes are accompanied by changelog updates.

Meaningful files exclude:
- tests/*
- .github/*
- __pycache__, *.pyc
- .gitignore, conftest.py
- .claude/*
- *.md files (documentation)

The hook can be bypassed with SKIP_CHANGELOG_CHECK=1 environment variable.
"""

import json
import os
import re
import subprocess
import sys
from typing import Any

from hook_utils import Colors, exit_if_disabled


def is_meaningful_file(file_path: str) -> bool:
    """
    Determine if a file is meaningful for changelog purposes.

    Meaningful files are production code changes that should be documented.
    Excludes test files, configuration, documentation, and build artifacts.

    Args:
        file_path: The file path to check.

    Returns:
        True if file is meaningful and requires changelog update, False otherwise.
    """
    if not file_path:
        return False

    # Normalize path for consistent checking
    path = file_path.strip()

    # Exclude test files
    if path.startswith("tests/") or "/tests/" in path:
        return False

    # Exclude GitHub workflows and templates
    if path.startswith(".github/") or "/.github/" in path:
        return False

    # Exclude Python cache files
    if "__pycache__" in path or path.endswith(".pyc"):
        return False

    # Exclude specific configuration files
    if path == ".gitignore" or path.endswith("/.gitignore"):
        return False

    if path == "conftest.py" or path.endswith("/conftest.py"):
        return False

    # Exclude .claude directory
    if path.startswith(".claude/") or "/.claude/" in path:
        return False

    # Exclude all markdown files (documentation)
    if path.lower().endswith(".md"):
        return False

    # Everything else is meaningful
    return True


def get_staged_files() -> list[str]:
    """
    Get list of files currently staged for commit.

    Returns:
        List of staged file paths, or empty list on error.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return []

        # Split output into lines and filter empty lines
        files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        return files

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def is_changelog_staged(staged_files: list[str]) -> bool:
    """
    Check if CHANGELOG.md is in the staged files.

    Args:
        staged_files: List of staged file paths.

    Returns:
        True if CHANGELOG.md is staged, False otherwise.
    """
    return any("CHANGELOG.md" in f for f in staged_files)


def is_git_commit_command(command: str) -> bool:
    """
    Detect if the command is a git commit operation.

    Args:
        command: The bash command being executed.

    Returns:
        True if command is git commit, False otherwise.
    """
    # Match "git commit" with word boundaries to avoid false matches
    return bool(re.search(r"\bgit\s+commit\b", command))


def main() -> None:
    """Main entry point for the changelog reminder hook."""
    exit_if_disabled()

    try:
        # Check for skip environment variable
        if os.environ.get("SKIP_CHANGELOG_CHECK") == "1":
            sys.exit(0)

        # Read hook data from stdin
        tool_use_json = sys.stdin.read()
        tool_use: dict[str, Any] = json.loads(tool_use_json)

        # Only process Bash commands
        if tool_use.get("tool_name") != "Bash":
            sys.exit(0)

        command = tool_use.get("tool_input", {}).get("command", "")

        # Check for skip in command string (inline env var anywhere in command)
        if re.search(r"SKIP_CHANGELOG_CHECK=1", command):
            sys.exit(0)

        # Check if this is a git commit command
        if not is_git_commit_command(command):
            sys.exit(0)

        # Get staged files
        staged_files = get_staged_files()

        # Filter to meaningful files only
        meaningful_files = [f for f in staged_files if is_meaningful_file(f)]

        # If no meaningful files staged, allow commit
        if not meaningful_files:
            sys.exit(0)

        # Check if CHANGELOG.md is staged
        if is_changelog_staged(staged_files):
            sys.exit(0)

        # Block commit - meaningful files without CHANGELOG.md
        error_msg = f"""{Colors.red("❌ Meaningful changes without CHANGELOG.md update!")}

{Colors.yellow("📝 Staged files requiring changelog:")}
{chr(10).join(f"   - {f}" for f in meaningful_files)}

{Colors.blue("💡 Options:")}
   1. Update CHANGELOG.md, then retry commit
   2. {Colors.green("SKIP_CHANGELOG_CHECK=1")} git commit ..."""

        print(error_msg, file=sys.stderr)
        sys.exit(2)

    except Exception:
        # Silent failure: exit cleanly on unexpected errors
        sys.exit(0)


if __name__ == "__main__":
    main()
