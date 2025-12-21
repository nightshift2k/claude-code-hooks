#!/usr/bin/env python3
"""
Shared utilities for Claude Code hooks.

This module provides common functionality for hook scripts including:
- Hook name detection
- Disabled hook checking
- Environment variable access
- Centralized ANSI color formatting
"""

import os
import sys
from pathlib import Path
from typing import Optional


class Colors:
    """ANSI color codes for terminal output with convenience methods."""

    # Color codes
    RED = "\033[1;31m"
    YELLOW = "\033[1;33m"
    GREEN = "\033[1;32m"
    BLUE = "\033[1;34m"
    CYAN = "\033[1;36m"
    RESET = "\033[0m"

    @classmethod
    def red(cls, text: str) -> str:
        """Format text in red (for errors and blocking messages)."""
        return f"{cls.RED}{text}{cls.RESET}"

    @classmethod
    def yellow(cls, text: str) -> str:
        """Format text in yellow (for warnings and labels)."""
        return f"{cls.YELLOW}{text}{cls.RESET}"

    @classmethod
    def green(cls, text: str) -> str:
        """Format text in green (for suggestions and alternatives)."""
        return f"{cls.GREEN}{text}{cls.RESET}"

    @classmethod
    def blue(cls, text: str) -> str:
        """Format text in blue (for tips and informational messages)."""
        return f"{cls.BLUE}{text}{cls.RESET}"

    @classmethod
    def cyan(cls, text: str) -> str:
        """Format text in cyan (for highlighting)."""
        return f"{cls.CYAN}{text}{cls.RESET}"


def get_hook_name() -> str:
    """
    Return the calling hook script's filename without the .py extension.

    Returns:
        The hook name derived from the calling script's filename.

    Example:
        If the calling script is 'git-commit-message-filter.py',
        returns 'git-commit-message-filter'.
    """
    # Get the calling script's filename
    caller_path = Path(sys.argv[0])
    hook_name = caller_path.stem  # filename without extension
    return hook_name


def is_hook_disabled(hook_name: Optional[str] = None) -> bool:
    """
    Check if a hook is disabled via the .claude/disabled-hooks file.

    The disabled-hooks file should be located at:
    $CLAUDE_PROJECT_DIR/.claude/disabled-hooks

    Each line in the file should contain a single hook name (without .py extension).
    Lines starting with # are treated as comments and ignored.
    Empty lines are ignored.

    Args:
        hook_name: The name of the hook to check. If None, uses get_hook_name().

    Returns:
        True if the hook is disabled, False otherwise.

    Example:
        # In .claude/disabled-hooks:
        # git-commit-message-filter
        # python-uv-enforcer

        is_hook_disabled('git-commit-message-filter')  # Returns True
        is_hook_disabled('prompt-flag-appender')       # Returns False
    """
    if hook_name is None:
        hook_name = get_hook_name()

    # Get the project directory from environment variable
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_dir:
        # If CLAUDE_PROJECT_DIR is not set, assume hooks are not disabled
        return False

    # Construct path to disabled-hooks file
    disabled_hooks_file = Path(project_dir) / ".claude" / "disabled-hooks"

    # If the file doesn't exist, no hooks are disabled
    if not disabled_hooks_file.is_file():
        return False

    try:
        # Read and parse the disabled-hooks file
        with disabled_hooks_file.open("r", encoding="utf-8") as f:
            for line in f:
                # Strip whitespace and skip comments and empty lines
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Check if this hook is disabled
                if line == hook_name:
                    return True

        return False

    except OSError:
        # If we can't read the file, assume the hook is not disabled
        return False


def exit_if_disabled(hook_name: Optional[str] = None) -> None:
    """
    Exit the hook script with status 0 if the hook is disabled.

    This is a convenience function that combines is_hook_disabled() with
    an immediate exit. If the hook is not disabled, this function returns
    normally and execution continues.

    Args:
        hook_name: The name of the hook to check. If None, uses get_hook_name().

    Example:
        # At the start of a hook script:
        exit_if_disabled()
        # Rest of hook logic continues only if not disabled
    """
    if is_hook_disabled(hook_name):
        sys.exit(0)
