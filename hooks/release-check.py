#!/usr/bin/env python3
"""
Release Check Hook - Validates and confirms release operations.

This hook provides human-in-the-loop confirmation for release operations:
1. Validates CHANGELOG.md contains the version before git tag
2. Requires explicit confirmation before git tag v*
3. Requires explicit confirmation before gh release create

Confirmation Bypass:
- CONFIRM_TAG=1 git tag v0.1.0 (after human approves tag creation)
- CONFIRM_RELEASE=1 gh release create v0.1.0 (after human approves release)

Skip All Checks:
- SKIP_RELEASE_CHECK=1 (skips all validation and confirmation)
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from hook_utils import Colors, exit_if_disabled


def extract_tag_version(command: str) -> Optional[str]:
    """
    Extract version number from git tag command.

    Args:
        command: The git tag command string.

    Returns:
        Version string (e.g., "0.1.4") or None if not found.
    """
    match = re.search(r"git\s+tag\s+(?:-[a-z]\s+)?v(\d+\.\d+\.\d+)", command)
    return match.group(1) if match else None


def extract_release_version(command: str) -> Optional[str]:
    """
    Extract version number from gh release create command.

    Args:
        command: The gh release create command string.

    Returns:
        Version string (e.g., "0.1.4") or None if not found.
    """
    match = re.search(r"gh\s+release\s+create\s+v(\d+\.\d+\.\d+)", command)
    return match.group(1) if match else None


def check_version_in_changelog(version: str) -> bool:
    """
    Check if version string exists in CHANGELOG.md.

    Args:
        version: Version string to search for (e.g., "0.1.4").

    Returns:
        True if version found or CHANGELOG.md doesn't exist, False otherwise.
    """
    changelog_path = Path.cwd() / "CHANGELOG.md"

    if not changelog_path.exists():
        return True

    try:
        with changelog_path.open("r", encoding="utf-8") as f:
            return version in f.read()
    except OSError:
        return True


def main() -> None:
    """Main entry point for the release check hook."""
    exit_if_disabled()

    try:
        # Check for skip environment variable
        if os.environ.get("SKIP_RELEASE_CHECK") == "1":
            sys.exit(0)

        # Read hook data from stdin
        tool_use: Dict[str, Any] = json.loads(sys.stdin.read())

        # Only process Bash commands
        if tool_use.get("tool_name") != "Bash":
            sys.exit(0)

        command = tool_use.get("tool_input", {}).get("command", "")

        # Check for inline skip in command
        if re.search(r"SKIP_RELEASE_CHECK=1", command):
            sys.exit(0)

        # Check for git tag v* command
        tag_version = extract_tag_version(command)
        if tag_version:
            # Check for confirmation bypass
            if re.search(r"CONFIRM_TAG=1", command):
                # Confirmed - still validate CHANGELOG
                if not check_version_in_changelog(tag_version):
                    msg = f"{Colors.red(f'❌ Version {tag_version} not found in CHANGELOG.md!')}"
                    print(msg, file=sys.stderr)
                    sys.exit(2)
                sys.exit(0)

            # No confirmation - first validate CHANGELOG
            if not check_version_in_changelog(tag_version):
                msg = f"""{Colors.red(f"❌ Version {tag_version} not found in CHANGELOG.md!")}

{Colors.yellow("📝 Before tagging, update CHANGELOG.md:")}
   - Rename [Unreleased] section to [{tag_version}]
   - Add release date"""
                print(msg, file=sys.stderr)
                sys.exit(2)

            # CHANGELOG OK - require confirmation
            msg = f"""{Colors.yellow(f"⚠️ Confirm: Create git tag v{tag_version}?")}

{Colors.blue("To proceed:")} CONFIRM_TAG=1 git tag v{tag_version}"""
            print(msg, file=sys.stderr)
            sys.exit(2)

        # Check for gh release create command
        release_version = extract_release_version(command)
        if release_version:
            # Check for confirmation bypass
            if re.search(r"CONFIRM_RELEASE=1", command):
                sys.exit(0)

            # No confirmation - require it
            msg = f"""{Colors.yellow(f"⚠️ Confirm: Create GitHub release v{release_version}?")}

{Colors.blue("To proceed:")} CONFIRM_RELEASE=1 gh release create v{release_version} ..."""
            print(msg, file=sys.stderr)
            sys.exit(2)

        sys.exit(0)

    except Exception:
        # Silent failure: exit cleanly on unexpected errors
        sys.exit(0)


if __name__ == "__main__":
    main()
