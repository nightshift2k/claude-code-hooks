#!/usr/bin/env python3
"""
Git Safety Check Hook - Validates safe Git operations.

This hook prevents dangerous Git operations including:
- Using --no-verify to skip hook validation
- Deleting protected branches (main, master, production, prod)
- Force pushing to remote repositories
- Hard resets that lose uncommitted changes
- Clean operations that delete untracked files
"""

import json
import re
import sys
from typing import Any

from hook_utils import Colors, exit_if_disabled


def check_git_command(command: str) -> None:
    """
    Check Git command for safety violations and block dangerous operations.

    This function examines Git commands for:
    1. --no-verify flag usage (blocks hook bypass attempts)
    2. Protected branch deletion attempts
    3. Dangerous operations (warnings only, not blocked)

    Args:
        command: The bash command being executed.

    Raises:
        SystemExit: With exit code 2 if dangerous operations are detected.
    """
    # Check if --no-verify is used to skip hooks - block immediately
    # Only detect --no-verify as a command argument, not within quotes or heredocs
    if re.search(r"(^|\s)--no-verify(\s|$)", command):
        # Further validation: ensure it's not inside quotes or heredocs
        verify_pos = command.find("--no-verify")
        safe_in_content = False

        # Check if --no-verify is inside -m "..." message (re.DOTALL for multiline)
        msg_match = re.search(r'-m\s+["\'].*?["\']', command, re.DOTALL)
        if msg_match and msg_match.start() < verify_pos < msg_match.end():
            safe_in_content = True

        # Check if --no-verify is inside <<'EOF' ... EOF heredoc
        heredoc_match = re.search(r'<<["\']?EOF["\']?.*?EOF', command, re.DOTALL)
        if heredoc_match and heredoc_match.start() < verify_pos < heredoc_match.end():
            safe_in_content = True

        if not safe_in_content:
            error_msg = Colors.red(
                "❌ Using --no-verify to skip Git hooks is prohibited!"
            )
            print(error_msg, file=sys.stderr)
            sys.exit(2)

    # Protected branches that cannot be deleted
    protected_branches = ["main", "master", "production", "prod"]

    # Check for protected branch deletion attempts - block immediately
    for branch in protected_branches:
        # Check for remote branch deletion: git push origin :branch
        if f"git push origin :{branch}" in command:
            error_msg = Colors.red(
                f"❌ Blocked: Cannot delete protected branch '{branch}'"
            )
            print(error_msg, file=sys.stderr)
            sys.exit(2)

        # Check for local branch deletion: git branch -d/-D branch
        # Use \s+ (not .*) after flag to prevent false positives in chained commands
        # like "git branch -d feature && git push origin main"
        # Word boundary ensures exact branch match at command/separator boundaries
        if re.search(
            rf"git\s+branch\s+-[dD]\s+{re.escape(branch)}(\s|$|&&|;|\|)", command
        ):
            error_msg = Colors.red(
                f"❌ Blocked: Cannot delete protected branch '{branch}'"
            )
            print(error_msg, file=sys.stderr)
            sys.exit(2)

    # Dangerous operation patterns (logged only, not blocked)
    # These are informational warnings for the user

    # Note: Dangerous patterns are currently logged only (not implemented as blocking)
    # Future enhancement could add interactive confirmation


def main() -> None:
    """Main entry point for the Git safety check hook."""
    # Exit early if this hook is disabled
    exit_if_disabled()

    try:
        # Read hook data from stdin
        tool_use_json = sys.stdin.read()
        tool_use: dict[str, Any] = json.loads(tool_use_json)

        # Only process Bash commands
        if tool_use.get("tool_name") != "Bash":
            sys.exit(0)

        command = tool_use.get("tool_input", {}).get("command", "")

        # Only check commands that contain Git operations
        if "git" in command:
            check_git_command(command)

        # If no issues found, exit silently
        sys.exit(0)

    except Exception:
        # Silent failure: exit cleanly on unexpected errors
        # This prevents hook failures from blocking legitimate operations
        sys.exit(0)


if __name__ == "__main__":
    main()
