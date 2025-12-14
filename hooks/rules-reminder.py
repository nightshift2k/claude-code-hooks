#!/usr/bin/env python3
"""
Rules Reminder Hook - Reminds Claude to follow project rules.

This hook outputs a reminder about project rules at strategic moments:
- SessionStart (startup/resume): Always outputs the reminder
- UserPromptSubmit: Outputs reminder when implementation keywords are detected

The reminder points Claude to CLAUDE.md and .claude/rules/* without
duplicating their content, encouraging rule review before making changes.

Trigger Keywords:
    Implementation verbs like: implement, add, create, fix, refactor, update, etc.
    Planning verbs like: design, plan, propose, architect, etc.

Usage:
    This hook runs automatically via settings.json configuration and requires
    no user interaction. It outputs directly to stdout for Claude to see.
"""

import json
import re
import sys
from typing import Any, Dict

from hook_utils import exit_if_disabled


# Regex pattern matching keywords that indicate Claude is about to make changes
# or plan implementation work
TRIGGER_KEYWORDS = re.compile(
    r"\b("
    r"implement|add|create|build|develop|write|make|introduce|setup|set up|"
    r"fix|refactor|update|change|modify|edit|adjust|improve|enhance|optimize|rewrite|rework|"
    r"remove|delete|clean ?up|deprecate|drop|"
    r"restructure|reorganize|redesign|migrate|convert|integrate|connect|configure|"
    r"brainstorm|design|plan|propose|architect|draft|outline|sketch|spec|specify|prototype"
    r")\b",
    re.IGNORECASE,
)

# The reminder text shown to Claude
REMINDER = """## Project Rules Reminder

This project may have rules defined in:
- CLAUDE.md (project root and .claude/ directory)
- .claude/rules/* (rule files)

Review and follow all project rules strictly before making changes."""


def main() -> None:
    """
    Main entry point for the rules reminder hook.

    Reads hook event data from stdin and outputs the reminder based on:
    - SessionStart events: Always outputs reminder
    - UserPromptSubmit events: Outputs reminder only if trigger keywords found

    Exits silently (status 0) on any errors to avoid disrupting Claude's workflow.
    """
    exit_if_disabled()

    try:
        input_data: Dict[str, Any] = json.load(sys.stdin)
        event_name = input_data.get("hook_event_name", "")

        if event_name == "SessionStart":
            # SessionStart stdout is injected as context
            print(REMINDER)

        elif event_name == "UserPromptSubmit":
            # UserPromptSubmit stdout is injected as context (per docs)
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
