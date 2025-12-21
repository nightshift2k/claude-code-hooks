#!/usr/bin/env python3
"""
Release Reminder Hook - Reminds about release verification steps.

This hook outputs a reminder when release-related keywords are detected in
user prompts. It triggers on UserPromptSubmit event only.

Trigger Keywords:
    - release
    - tag v
    - version bump
    - prepare release
    - version patterns like v0.1., v0.2., v1.0., etc.

Usage:
    This hook runs automatically via settings.json configuration and requires
    no user interaction. It outputs directly to stdout for Claude to see.
"""

import json
import re
import sys
from typing import Any, Dict

from hook_utils import exit_if_disabled

# Regex pattern matching release-related keywords
TRIGGER_KEYWORDS = re.compile(
    r"\b("
    r"release|"
    r"tag\s+v|"
    r"version\s+bump|"
    r"prepare\s+release|"
    r"v\d+\.\d+\."
    r")",
    re.IGNORECASE,
)

# The reminder text shown to Claude
REMINDER = """---
## Release Verification Required

Before tagging/releasing, ensure:
1. CHANGELOG.md has version section matching the release (not just [Unreleased])
2. All version files are synchronized (check project-specific: pyproject.toml, package.json, etc.)
3. Working tree is clean
4. You're on the correct branch

Confirm these checks before proceeding with git tag.
---"""


def main() -> None:
    """
    Main entry point for the release reminder hook.

    Reads hook event data from stdin and outputs the reminder based on:
    - UserPromptSubmit events: Outputs reminder only if trigger keywords found
    - Other events: Silent exit

    Exits silently (status 0) on any errors to avoid disrupting Claude's workflow.
    """
    exit_if_disabled()

    try:
        input_data: Dict[str, Any] = json.load(sys.stdin)
        event_name = input_data.get("hook_event_name", "")

        if event_name == "UserPromptSubmit":
            # UserPromptSubmit stdout is injected as context
            # Only output reminder if trigger keywords found
            prompt = input_data.get("prompt", "")
            if TRIGGER_KEYWORDS.search(prompt):
                print(REMINDER)
            # If no keywords, output nothing (don't bloat context)

        sys.exit(0)

    except Exception:
        # Silent failure - don't disrupt Claude's workflow on errors
        sys.exit(0)


if __name__ == "__main__":
    main()
