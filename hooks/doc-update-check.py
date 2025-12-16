#!/usr/bin/env python3
"""
Documentation Update Check Hook - Ensures documentation is updated when merging to main.

This hook blocks merge-to-main operations unless documentation files (*.md) have been
modified in the branch being merged. This enforces documentation hygiene by requiring
that code changes are accompanied by documentation updates.

The hook can be bypassed with SKIP_DOC_CHECK=1 environment variable or by adding
files to .doc-check-ignore following gitignore-style patterns.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from hook_utils import exit_if_disabled, Colors


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


def is_merge_to_main(command: str) -> bool:
    """
    Detect if the command is attempting to merge into main branch.

    Checks for:
    1. 'git merge' while on main branch
    2. 'checkout main' followed by 'merge' in command chain
    3. 'gh pr merge' command

    Args:
        command: The bash command being executed.

    Returns:
        True if merge-to-main is detected, False otherwise.
    """
    # Check for gh pr merge
    if "gh" in command and "pr" in command and "merge" in command:
        return True

    # Check for git merge operations
    if "git" in command and "merge" in command:
        # Case 1: Already on main branch
        current_branch = get_current_branch()
        if current_branch == "main":
            return True

        # Case 2: Command contains checkout main followed by merge
        # Match patterns like: git checkout main && git merge
        # or: git checkout main; git merge
        if re.search(r"checkout\s+main\s*(?:&&|;|$).*merge", command):
            return True

    return False


def load_doc_check_ignore_patterns() -> List[str]:
    """
    Load ignore patterns from .doc-check-ignore file.

    Returns:
        List of glob-style patterns to exclude from documentation check.
    """
    ignore_file = Path.cwd() / ".doc-check-ignore"
    patterns: List[str] = []

    if not ignore_file.exists():
        return patterns

    try:
        with ignore_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
    except (OSError, IOError):
        pass

    return patterns


def is_ignored(file_path: str, patterns: List[str]) -> bool:
    """
    Check if a file path matches any ignore pattern.

    Uses simple glob-style pattern matching:
    - * matches anything in current directory
    - ** matches across directories
    - Patterns ending with / match directories

    Args:
        file_path: The file path to check.
        patterns: List of glob-style patterns.

    Returns:
        True if file matches any ignore pattern, False otherwise.
    """
    from pathlib import Path

    for pattern in patterns:
        # Convert glob pattern to regex
        # Simple implementation: * -> [^/]*, ** -> .*
        regex_pattern = pattern.replace("**", "DOUBLESTAR")
        regex_pattern = regex_pattern.replace("*", "[^/]*")
        regex_pattern = regex_pattern.replace("DOUBLESTAR", ".*")

        # Add anchors
        if not regex_pattern.startswith("^"):
            regex_pattern = "^" + regex_pattern
        if not regex_pattern.endswith("$"):
            regex_pattern = regex_pattern + "$"

        if re.match(regex_pattern, file_path):
            return True

    return False


def get_modified_docs() -> List[str]:
    """
    Get list of modified documentation files in current branch vs main.

    Returns:
        List of .md file paths modified in the branch.
    """
    try:
        # Get list of changed files in branch
        result = subprocess.run(
            ["git", "diff", "main...HEAD", "--name-only"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        # Filter to .md files (case insensitive)
        all_files = result.stdout.strip().split("\n")
        md_files = [
            f for f in all_files
            if f.lower().endswith(".md")
        ]

        # Apply ignore patterns
        ignore_patterns = load_doc_check_ignore_patterns()
        filtered_files = [
            f for f in md_files
            if not is_ignored(f, ignore_patterns)
        ]

        return filtered_files

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def main() -> None:
    """Main entry point for the documentation update check hook."""
    exit_if_disabled()

    try:
        # Check for skip environment variable
        if os.environ.get("SKIP_DOC_CHECK") == "1":
            sys.exit(0)

        # Read hook data from stdin
        tool_use_json = sys.stdin.read()
        tool_use: Dict[str, Any] = json.loads(tool_use_json)

        # Only process Bash commands
        if tool_use.get("tool_name") != "Bash":
            sys.exit(0)

        command = tool_use.get("tool_input", {}).get("command", "")

        # Check if this is a merge-to-main operation
        if not is_merge_to_main(command):
            sys.exit(0)

        # Get list of modified documentation files
        modified_docs = get_modified_docs()

        # If docs were modified, allow the merge
        if modified_docs:
            sys.exit(0)

        # No docs modified - block the merge
        error_msg = f"""{Colors.red("❌ No documentation updates detected in this branch.")}

{Colors.yellow("📝 Files checked:")} CHANGELOG.md, README.md, *.md (excluding .doc-check-ignore patterns)

{Colors.blue("💡 Options:")}
   1. Update relevant documentation, then retry merge
   2. If no docs needed, ask user to confirm, then run:
      {Colors.green("SKIP_DOC_CHECK=1")} git merge <branch>

{Colors.cyan("🔍 Branch diff:")} git diff main...HEAD --name-only"""

        print(error_msg, file=sys.stderr)
        sys.exit(2)

    except Exception:
        # Silent failure: exit cleanly on unexpected errors
        sys.exit(0)


if __name__ == "__main__":
    main()
