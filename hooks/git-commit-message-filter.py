#!/usr/bin/env python3
"""
Commit Message Filter Hook - Filters specific content from commit messages.

This hook blocks commits that contain Claude auto-generation markers,
ensuring that users write custom commit messages instead of using
the default Claude-generated attribution.
"""

import json
import re
import sys
from typing import Any

from hook_utils import Colors, exit_if_disabled


def check_commit_message(command: str) -> None:
    """
    Check if the commit message contains content that should be filtered.

    This function looks for Claude attribution markers and blocks commits
    that contain them, requiring users to write custom commit messages.

    Args:
        command: The bash command being executed.

    Raises:
        SystemExit: With exit code 2 if blocked patterns are found.
    """
    # Patterns to block in commit messages
    blocked_patterns = [
        r"🤖\s*Generated with\s*\[Claude Code\]",
        r"Co-Authored-By:\s*Claude\s*<noreply@anthropic\.com>",
        r"Generated with.*Claude.*Code",
        r"Claude\s*<noreply@anthropic\.com>",
    ]

    # Check if this is a git commit command
    if "git commit" in command:
        for pattern in blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE | re.MULTILINE):
                error_msg = Colors.red(
                    "❌ Commit message contains auto-generated Claude markers. "
                    "Please use a custom commit message."
                )
                print(error_msg, file=sys.stderr)
                sys.exit(2)  # Exit code 2 = blocking error


def main() -> None:
    """Main entry point for the commit message filter hook."""
    # Exit early if this hook is disabled
    exit_if_disabled()

    # Read hook data from stdin
    tool_use_json = sys.stdin.read()
    tool_use: dict[str, Any] = json.loads(tool_use_json)

    # Only process Bash commands
    if tool_use.get("tool_name") != "Bash":
        sys.exit(0)

    command = tool_use.get("tool_input", {}).get("command", "")

    # Check the commit message
    check_commit_message(command)

    # If no issues found, exit silently
    sys.exit(0)


if __name__ == "__main__":
    main()
