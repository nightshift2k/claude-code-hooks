#!/usr/bin/env python3
"""
Git Branch Protection Hook - Prevents code edits on protected branches.

This hook blocks file editing operations when working on protected branches
(main, master, production, prod), enforcing good git hygiene by requiring
feature branches for development work.

Note: Tool filtering is handled by the matcher in settings.json.
This hook assumes it's only called for edit-related tools.
"""

import json
import subprocess
import sys
from typing import Dict, Any, List, Optional

from hook_utils import exit_if_disabled, Colors


# Branches where edits are blocked
PROTECTED_BRANCHES: List[str] = [
    "main",
    "master",
    "production",
    "prod",
]


def get_current_branch() -> Optional[str]:
    """
    Get the current git branch name.

    Returns:
        The current branch name, or None if not in a git repo or error.
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def main() -> None:
    """Main entry point for the git branch protection hook."""
    exit_if_disabled()

    try:
        # Consume stdin (required even if not used)
        json.load(sys.stdin)

        # Get current branch
        current_branch = get_current_branch()
        if current_branch is None:
            # Not in a git repo or can't determine branch - allow
            sys.exit(0)

        # Check if on protected branch
        if current_branch in PROTECTED_BRANCHES:
            error_msg = f"""{Colors.red(f"❌ Cannot edit files on protected branch '{current_branch}'!")}
{Colors.yellow("📝 Create a feature branch first:")}
   git checkout -b feature/your-feature-name
{Colors.blue("💡 Or disable this hook:")}
   echo "git-branch-protection" >> .claude/disabled-hooks"""
            print(error_msg, file=sys.stderr)
            sys.exit(2)

        sys.exit(0)

    except Exception:
        # Silent failure
        sys.exit(0)


if __name__ == "__main__":
    main()
