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
from typing import Any

from hook_utils import Colors, exit_if_disabled


def get_current_branch() -> str | None:
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


def extract_merge_target(command: str) -> str | None:
    """
    Extract branch name from git merge command.

    Parses the command to find the first non-flag argument after 'merge'.
    Handles options like --squash, --no-ff, -m "msg", etc.

    Args:
        command: The git merge command string.

    Returns:
        The branch name being merged, or None if not found.
    """
    parts = command.split()
    try:
        merge_idx = parts.index("merge")
        # Find first non-flag argument after merge
        i = merge_idx + 1
        while i < len(parts):
            part = parts[i]
            # Skip flags (start with -)
            if part.startswith("-"):
                # If it's -m, skip the next argument too (the message)
                if part == "-m" and i + 1 < len(parts):
                    i += 2  # Skip -m and its value
                    continue
                i += 1
                continue
            return part
    except ValueError:
        pass
    return None


def is_merge_to_main_regex(command: str) -> bool:
    """
    Detect if the command is attempting to merge into main branch using strict regex.

    This function uses regex patterns to avoid false positives from commit messages
    containing "merge" as text. It checks for:
    1. 'gh pr merge' command with strict word boundaries
    2. 'git merge' subcommand (not 'git commit' with merge in message)
    3. 'checkout main' followed by 'merge' in command chain

    Args:
        command: The bash command being executed.

    Returns:
        True if merge-to-main is detected, False otherwise.
    """
    # Check for gh pr merge (strict word boundary matching at start)
    if re.match(r"^\s*gh\s+pr\s+merge\b", command):
        return True

    # Extract git subcommand to verify it's actually "merge"
    git_match = re.match(r"^\s*git\s+(\w+)", command)
    if git_match:
        subcommand = git_match.group(1)
        if subcommand == "merge":
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


def is_merge_to_main_ai(command: str) -> bool:
    """
    Use Claude Haiku to detect merge-to-main intent via AI analysis.

    This function calls the claude CLI with a simple prompt asking if the command
    merges code INTO the main or master branch. It provides a fail-open fallback
    on errors (returns False) to avoid blocking legitimate commands when the AI
    service is unavailable.

    Args:
        command: The bash command being executed.

    Returns:
        True if AI determines this is a merge to main, False otherwise or on error.
    """
    prompt = f"""Analyze this bash command. Does it merge changes INTO the main or master branch (as the target/destination)?

Examples of YES:
- git checkout main && git merge feature (merges feature INTO main)
- gh pr merge 123 (merges PR INTO default branch)
- git merge feature (when on main branch)

Examples of NO:
- git checkout feature && git merge main (merges main INTO feature)
- git commit -m "merge fix" (just a commit message)
- git log --oneline | grep merge (just searching)

Command: {command}

Answer ONLY "yes" or "no"."""

    try:
        result = subprocess.run(
            ["claude", "--model", "haiku", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return "yes" in result.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False  # Fail open on errors


def is_ai_mode_enabled() -> bool:
    """
    Check if AI mode is enabled via flag file or environment variable.

    AI mode uses Claude Haiku to semantically analyze commands instead of regex.
    Can be enabled via:
    - DOC_CHECK_USE_AI=1 environment variable
    - .claude/hook-doc-check-ai-mode-on flag file in project directory

    Returns:
        True if AI mode is enabled, False otherwise.
    """
    # Environment variable takes precedence
    if os.environ.get("DOC_CHECK_USE_AI") == "1":
        return True

    # Check for project flag file
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        flag_file = Path(project_dir) / ".claude" / "hook-doc-check-ai-mode-on"
        if flag_file.exists():
            return True

    return False


def is_merge_to_main(command: str) -> bool:
    """
    Detect if the command is attempting to merge into main branch.

    Uses regex-first approach for performance, with optional AI fallback for
    edge cases. When AI mode is enabled, AI is only called if:
    1. Regex returned False (no obvious merge detected)
    2. Command contains merge-related keywords (pre-filter)

    Args:
        command: The bash command being executed.

    Returns:
        True if merge-to-main is detected, False otherwise.
    """
    # Always try fast regex first
    if is_merge_to_main_regex(command):
        return True

    # AI fallback only if enabled + command has keywords + regex said no
    if is_ai_mode_enabled():
        command_lower = command.lower()
        if "merge" in command_lower or "gh" in command_lower:
            return is_merge_to_main_ai(command)

    return False


def load_doc_check_ignore_patterns() -> list[str]:
    """
    Load ignore patterns from .doc-check-ignore file.

    Returns:
        List of glob-style patterns to exclude from documentation check.
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return []  # Can't load ignore file without project directory
    ignore_file = Path(project_dir) / ".doc-check-ignore"
    patterns: list[str] = []

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
    except OSError:
        pass

    return patterns


def is_ignored(file_path: str, patterns: list[str]) -> bool:
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


def get_modified_docs(merge_target: str | None = None) -> list[str]:
    """
    Get list of modified documentation files in current branch vs main.

    Args:
        merge_target: Optional branch name being merged. If provided, diff against
                      this branch instead of main. Used when already on main branch.

    Returns:
        List of .md file paths modified in the branch.
    """
    try:
        # Determine diff range
        if merge_target:
            # When on main, diff against the branch being merged
            diff_range = [merge_target]
        else:
            # When on feature branch, diff against main
            diff_range = ["main...HEAD"]

        # Get list of changed files in branch
        result = subprocess.run(
            ["git", "diff"] + diff_range + ["--name-only"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        # Filter to .md files (case insensitive)
        all_files = result.stdout.strip().split("\n")
        md_files = [f for f in all_files if f.lower().endswith(".md")]

        # Apply ignore patterns
        ignore_patterns = load_doc_check_ignore_patterns()
        filtered_files = [f for f in md_files if not is_ignored(f, ignore_patterns)]

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
        tool_use: dict[str, Any] = json.loads(tool_use_json)

        # Only process Bash commands
        if tool_use.get("tool_name") != "Bash":
            sys.exit(0)

        command = tool_use.get("tool_input", {}).get("command", "")

        # Check for skip in command string (inline env var anywhere in command)
        if re.search(r"SKIP_DOC_CHECK=1", command):
            sys.exit(0)

        # Check if this is a merge-to-main operation
        if not is_merge_to_main(command):
            sys.exit(0)

        # Get current branch and extract merge target if needed
        current_branch = get_current_branch()
        merge_target = (
            extract_merge_target(command) if current_branch == "main" else None
        )

        # Get list of modified documentation files
        modified_docs = get_modified_docs(merge_target)

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
