#!/usr/bin/env python3
"""
Large File Guard - PreToolUse hook for Read tool.

Blocks reading large files (> threshold lines) and suggests alternatives:
- Serena find_symbol for code files
- Grep patterns for searching
- Read with offset/limit for partial reads

Configuration (priority order):
1. LARGE_FILE_THRESHOLD env var
2. ~/.claude/hook-large-file-guard-config file
3. Default: 500 lines

Two-stage size detection:
- Stage 1: Byte check (< 5KB instant allow, > 100KB instant block)
- Stage 2: Accurate line counting for files 5-100KB

Skip conditions (exit 0 without blocking):
- Binary file extension
- offset or limit parameter present in tool_input (non-null)
- ALLOW_LARGE_READ=1 env var
- File doesn't exist
- Malformed JSON input
"""

import json
import os
import sys
from pathlib import Path

from hook_utils import (
    Colors,
    classify_file,
    count_lines,
    estimate_tokens,
    exit_if_disabled,
)

# Constants
DEFAULT_THRESHOLD = 500
INSTANT_ALLOW_BYTES = 5 * 1024  # 5KB
INSTANT_BLOCK_BYTES = 100 * 1024  # 100KB


def get_threshold() -> int:
    """
    Get the large file threshold from configuration.

    Priority order:
    1. LARGE_FILE_THRESHOLD env var
    2. ~/.claude/hook-large-file-guard-config file
    3. Default: 500 lines

    Returns:
        Threshold in number of lines.
    """
    # Check env var first
    env_threshold = os.environ.get("LARGE_FILE_THRESHOLD")
    if env_threshold:
        try:
            return int(env_threshold)
        except ValueError:
            pass

    # Check config file second
    home = os.environ.get("HOME")
    if home:
        config_file = Path(home) / ".claude" / "hook-large-file-guard-config"
        if config_file.is_file():
            try:
                content = config_file.read_text(encoding="utf-8").strip()
                return int(content)
            except (ValueError, OSError):
                pass

    # Return default
    return DEFAULT_THRESHOLD


def should_skip_check(tool_input: dict, file_path: str) -> bool:
    """
    Determine if we should skip the size check.

    Skip conditions:
    - Binary file extension
    - offset or limit parameter present (non-null)
    - ALLOW_LARGE_READ=1 env var
    - File doesn't exist

    Args:
        tool_input: The tool_input dictionary from stdin.
        file_path: Path to the file being read.

    Returns:
        True if check should be skipped, False otherwise.
    """
    # Skip if bypass env var is set
    if os.environ.get("ALLOW_LARGE_READ") == "1":
        return True

    # Skip if binary file
    if classify_file(file_path) == "binary":
        return True

    # Skip if offset or limit parameter present (non-null)
    # Note: Read tool sends {"offset": null} for full reads, which should NOT skip
    if tool_input.get("offset") is not None:
        return True
    if tool_input.get("limit") is not None:
        return True

    # Skip if file doesn't exist
    if not Path(file_path).is_file():
        return True

    return False


def get_file_size_bytes(file_path: str) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: Path to the file.

    Returns:
        File size in bytes, or 0 on error.
    """
    try:
        return Path(file_path).stat().st_size
    except OSError:
        return 0


def check_file_size(file_path: str, threshold: int) -> tuple[bool, int, int]:
    """
    Check if file exceeds threshold using two-stage detection.

    Stage 1: Byte check (< 5KB instant allow, > 100KB instant block)
    Stage 2: Accurate line counting for files 5-100KB

    Args:
        file_path: Path to the file to check.
        threshold: Maximum allowed lines.

    Returns:
        Tuple of (exceeds_threshold, line_count, token_estimate)
    """
    # Stage 1: Byte check for quick decisions
    size_bytes = get_file_size_bytes(file_path)

    if size_bytes < INSTANT_ALLOW_BYTES:  # < 5KB - instant allow
        return False, 0, 0

    if size_bytes > INSTANT_BLOCK_BYTES:  # > 100KB - instant block
        # Estimate lines (assume ~80 chars per line)
        estimated_lines = size_bytes // 80
        # Use byte-based token estimate (don't read file into memory)
        tokens = int(size_bytes / 3.5)
        return True, estimated_lines, tokens

    # Stage 2: Accurate line counting for normal files (5-100KB)
    line_count = count_lines(file_path)

    if line_count > threshold:
        # Read content for token estimate (safe for files <= 100KB)
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
            tokens = estimate_tokens(content)
        except OSError:
            tokens = int(size_bytes / 3.5)  # Fallback estimate
        return True, line_count, tokens

    return False, line_count, 0


def format_error_message(file_path: str, lines: int, tokens: int) -> str:
    """
    Format the error message for large file blocking.

    Args:
        file_path: Path to the blocked file.
        lines: Number of lines in the file.
        tokens: Estimated token count.

    Returns:
        Formatted error message.
    """
    file_type = classify_file(file_path)

    # Build alternatives list based on file type
    alternatives = []
    if file_type == "code":
        alternatives.append("Serena find_symbol")
    alternatives.extend(["Grep patterns", "Read offset/limit"])

    alternatives_str = " • ".join(alternatives)

    error = f"{Colors.red('❌ Large file:')} {file_path} ({lines:,} lines, ~{tokens:,} tokens est.)\n\n"
    error += f"{Colors.yellow('📝 Alternatives:')} {alternatives_str}\n\n"
    error += f"{Colors.blue('💡 Bypass:')} ALLOW_LARGE_READ=1"

    return error


def main() -> None:
    """Main entry point for the large-file-guard hook."""
    exit_if_disabled()

    try:
        # Read and parse stdin
        stdin_data = sys.stdin.read()
        data = json.loads(stdin_data)

        # Extract tool name and input
        tool_name = data.get("tool_name")
        tool_input = data.get("tool_input", {})

        # Only check Read tool
        if tool_name != "Read":
            sys.exit(0)

        # Extract file path
        file_path = tool_input.get("file_path")
        if not file_path:
            sys.exit(0)

        # Check skip conditions
        if should_skip_check(tool_input, file_path):
            sys.exit(0)

        # Get threshold
        threshold = get_threshold()

        # Check file size
        exceeds, lines, tokens = check_file_size(file_path, threshold)

        if exceeds:
            # Block the read
            error_msg = format_error_message(file_path, lines, tokens)
            print(error_msg, file=sys.stderr)
            sys.exit(2)

        # Allow the read
        sys.exit(0)

    except Exception:
        # Fail open on any unexpected error
        sys.exit(0)


if __name__ == "__main__":
    main()
