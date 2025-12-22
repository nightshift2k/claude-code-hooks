#!/usr/bin/env python3
"""
Large File Awareness Hook - SessionStart

Scans project at session start and injects awareness of large files
to enable efficient navigation strategies from the beginning.

Works alongside large-file-guard.py for defense-in-depth protection.

Event: SessionStart
Matcher: (no matcher needed - hook_event_name is SessionStart)
Exit Codes:
    0 - Success (or silent failure)
    Never exits non-zero (fail open design)

Configuration:
    Threshold from ~/.claude/settings.json (largeFileThreshold)
    or LARGE_FILE_THRESHOLD env var, default 500 lines

Output Format:
    ## Large Files (symbolic navigation required)
    path/to/file.py (N lines, ~M tokens) → Tool
    ...
    (+X more files over Y lines)

    Action: tool guidance
"""

import json
import os
import subprocess
import sys

from hook_utils import (
    classify_file,
    count_lines,
    estimate_tokens,
    exit_if_disabled,
    get_large_file_threshold,
)

# Standard excluded directories for os.walk fallback
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "vendor",
    "dist",
    "build",
    ".next",
    "target",
    ".tox",
    "htmlcov",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
}


def get_project_files() -> list[str]:
    """
    Get project files using git when available, fallback to os.walk.

    Strategy:
    1. Check if in git repository
    2. If yes: Use 'git ls-files' (respects .gitignore)
    3. If no: Use os.walk with standard excludes

    Returns:
        List of relative file paths.
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return walk_with_excludes()

    try:
        # Check if we're in a git repo
        check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=project_dir,
        )

        if check.returncode == 0 and check.stdout.strip() == "true":
            # Use git ls-files for git repositories
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=project_dir,
            )

            if result.returncode == 0:
                files = [f for f in result.stdout.strip().split("\n") if f]
                return files

    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: os.walk with excludes
    return walk_with_excludes()


def walk_with_excludes() -> list[str]:
    """
    Walk directory tree with standard exclusions.

    Excludes:
        - Directories in EXCLUDE_DIRS
        - Symlinks (security consideration)

    Returns:
        List of relative file paths.
    """
    files = []
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    for root, dirs, filenames in os.walk(project_dir):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for f in filenames:
            full_path = os.path.join(root, f)

            # Skip symlinks (security consideration)
            if os.path.islink(full_path):
                continue

            # Convert to relative path
            rel_path = os.path.relpath(full_path, project_dir)
            files.append(rel_path)

    return files


def recommend_tool(file_type: str) -> str:
    """
    Recommend navigation tool based on file type.

    Args:
        file_type: File classification from classify_file().

    Returns:
        Recommended tool name.

    Tool Recommendations:
        - code → Serena (symbol-aware navigation)
        - data → Grep (pattern matching)
        - unknown/text → Read offset/limit (section reading)
    """
    if file_type == "code":
        return "Serena"
    elif file_type == "data":
        return "Grep"
    else:
        return "Read offset/limit"


def analyze_files(files: list[str]) -> list[dict[str, any]]:
    """
    Analyze files and identify large ones.

    Args:
        files: List of relative file paths.

    Returns:
        List of dicts with file metadata, sorted by line count descending.

    Metadata structure:
        {
            'path': str,           # Relative path
            'lines': int,          # Line count
            'tokens': int,         # Estimated tokens
            'type': str,           # 'code', 'data', 'binary', 'unknown'
            'tool': str            # Recommended tool: 'Serena', 'Grep', etc.
        }
    """
    threshold = get_large_file_threshold()
    large_files = []

    for file_path in files:
        try:
            # Skip if file doesn't exist (race condition)
            if not os.path.exists(file_path):
                continue

            # Skip binary files
            file_type = classify_file(file_path)
            if file_type == "binary":
                continue

            # Count lines
            lines = count_lines(file_path)

            # Check threshold
            if lines < threshold:
                continue

            # Estimate tokens
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    tokens = estimate_tokens(content)
            except Exception:
                # Fallback: rough estimate from lines (~8 tokens/line average)
                tokens = int(lines * 8)

            # Recommend tool
            tool = recommend_tool(file_type)

            large_files.append(
                {
                    "path": file_path,
                    "lines": lines,
                    "tokens": tokens,
                    "type": file_type,
                    "tool": tool,
                }
            )

        except Exception:
            # Skip files that error during analysis
            continue

    # Sort by line count descending
    large_files.sort(key=lambda x: x["lines"], reverse=True)

    return large_files


def print_action_guidance(shown: list[dict[str, any]]) -> None:
    """
    Print tool-specific guidance based on file types present.

    Args:
        shown: List of file metadata dicts (top 10).
    """
    tools_present = set(f["tool"] for f in shown)

    guidance = []
    if "Serena" in tools_present:
        guidance.append("find_symbol for code")
    if "Grep" in tools_present:
        guidance.append("Grep for patterns")
    if "Read offset/limit" in tools_present:
        guidance.append("Read offset/limit for sections")

    if guidance:
        print(f"\nAction: {', '.join(guidance)}.")


def print_awareness(large_files: list[dict[str, any]]) -> None:
    """
    Print LLM-optimized awareness message.

    Args:
        large_files: Sorted list of file metadata dicts.

    Output Format:
        ## Large Files (symbolic navigation required)
        path/to/file.py (N lines, ~M tokens) → Tool
        ...
        (+X more files over Y lines)

        Action: tool guidance
    """
    threshold = get_large_file_threshold()

    # Header
    print("\n## Large Files (symbolic navigation required)")

    # Top 10 files
    shown = large_files[:10]
    for file_info in shown:
        print(
            f"{file_info['path']} "
            f"({file_info['lines']} lines, ~{file_info['tokens']} tokens) "
            f"→ {file_info['tool']}"
        )

    # Remainder count
    if len(large_files) > 10:
        remainder = len(large_files) - 10
        print(f"(+{remainder} more files over {threshold} lines)")

    # Action guidance
    print_action_guidance(shown)
    print()  # Blank line for spacing


def main() -> None:
    """Main entry point for large-file-awareness hook."""
    exit_if_disabled("large-file-awareness")

    try:
        # Parse stdin
        data = json.loads(sys.stdin.read())
        event_name = data.get("hook_event_name", "")

        # Validate event type - only run on SessionStart
        if event_name != "SessionStart":
            sys.exit(0)

        # Discover files
        files = get_project_files()

        # Analyze files
        large_files = analyze_files(files)

        # Generate and print awareness
        if large_files:
            print_awareness(large_files)

        sys.exit(0)

    except Exception:
        # Silent failure - never block session start
        sys.exit(0)


if __name__ == "__main__":
    main()
