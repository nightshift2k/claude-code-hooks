#!/usr/bin/env python3
"""
Release Check Hook - Validates CHANGELOG.md before git tag.

This hook prevents tagging releases when the version doesn't exist in CHANGELOG.md.
It's a simple safety net to ensure documentation is updated before releases.

Bypass: SKIP_RELEASE_CHECK=1 environment variable or inline in command
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from hook_utils import Colors, exit_if_disabled


def extract_version(command: str) -> Optional[str]:
    """
    Extract version number from git tag command.

    Extracts version from commands like:
    - git tag v0.1.4
    - git tag -a v1.2.3 -m "message"
    - git tag v10.20.30

    Args:
        command: The git tag command string.

    Returns:
        Version string (e.g., "0.1.4") or None if not found.
    """
    # Match git tag v{version} pattern
    match = re.search(r'git\s+tag\s+(?:-[a-z]\s+)?v(\d+\.\d+\.\d+)', command)
    if match:
        return match.group(1)
    return None


def check_version_in_changelog(version: str) -> bool:
    """
    Check if version string exists in CHANGELOG.md.

    Uses simple string search to find the version anywhere in the changelog.
    If CHANGELOG.md doesn't exist or can't be read, returns True (allow).

    Args:
        version: Version string to search for (e.g., "0.1.4").

    Returns:
        True if version found or CHANGELOG.md doesn't exist, False otherwise.
    """
    changelog_path = Path.cwd() / "CHANGELOG.md"

    # If CHANGELOG doesn't exist, allow (some projects don't use it)
    if not changelog_path.exists():
        return True

    try:
        with changelog_path.open("r", encoding="utf-8") as f:
            changelog_content = f.read()
            # Simple string search - version appears anywhere in changelog
            return version in changelog_content

    except OSError:
        # If we can't read the file, allow (fail open)
        return True


def main() -> None:
    """Main entry point for the release check hook."""
    exit_if_disabled()

    try:
        # Check for skip environment variable
        if os.environ.get("SKIP_RELEASE_CHECK") == "1":
            sys.exit(0)

        # Read hook data from stdin
        tool_use_json = sys.stdin.read()
        tool_use: Dict[str, Any] = json.loads(tool_use_json)

        # Only process Bash commands
        if tool_use.get("tool_name") != "Bash":
            sys.exit(0)

        command = tool_use.get("tool_input", {}).get("command", "")

        # Check for inline skip in command
        if re.search(r"SKIP_RELEASE_CHECK=1", command):
            sys.exit(0)

        # Only check git tag v* commands
        if not re.search(r'git\s+tag\s+(?:-[a-z]\s+)?v\d+\.\d+\.\d+', command):
            sys.exit(0)

        # Extract version from command
        version = extract_version(command)
        if not version:
            sys.exit(0)

        # Check if version exists in CHANGELOG.md
        if check_version_in_changelog(version):
            sys.exit(0)

        # Version not found - block the tag
        error_msg = f"""{Colors.red(f"❌ Version {version} not found in CHANGELOG.md!")}

{Colors.yellow("📝 Before tagging, update CHANGELOG.md:")}
   - Rename [Unreleased] section to [{version}]
   - Add release date

{Colors.blue("💡 Bypass:")} SKIP_RELEASE_CHECK=1 git tag v{version}"""

        print(error_msg, file=sys.stderr)
        sys.exit(2)

    except Exception:
        # Silent failure: exit cleanly on unexpected errors
        sys.exit(0)


if __name__ == "__main__":
    main()
