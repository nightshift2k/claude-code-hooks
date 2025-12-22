#!/usr/bin/env python3
"""
Prompt Flag Appender Hook - Appends markdown snippets based on trailing triggers.

This hook processes Claude Code prompts to detect trailing triggers (e.g., "+ultrathink")
and replaces them with the contents of corresponding markdown files. This allows
users to quickly inject common prompt modifications using trigger words.

Additionally, this hook supports session-based modes via flag files in the project's
.claude/ directory. Files matching the pattern "hook-*-mode-on" will automatically
inject their corresponding markdown fragments for the entire session.

Usage:
    Include mapped triggers at the end of the prompt (e.g., "+ultrathink +absolute").
    Triggers are stripped from the prompt and replaced by the contents of the mapped
    markdown files if they exist in the prompt-fragments/ directory.

    For session-based modes, create flag files in your project's .claude/ directory:
        touch .claude/hook-approval-mode-on  # Enables approval mode for project
        rm .claude/hook-approval-mode-on     # Disables approval mode

Example:
    User prompt: "Refactor this code +ultrathink"
    Result: "Refactor this code\n\n[ultrathink.md contents]"

    Session mode: $CLAUDE_PROJECT_DIR/.claude/hook-approval-mode-on exists
    User prompt: "Refactor this code"
    Result: "Refactor this code\n\n[approval.md contents]"
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from hook_utils import exit_if_disabled

# Trigger prefix character
TRIGGER_PREFIX = "+"

# Map trigger words to markdown filenames in prompt-fragments/ directory
TRIGGER_FILE_MAP: dict[str, str] = {
    "+ultrathink": "ultrathink.md",
    "+absolute": "absolute.md",
    "+approval": "approval.md",
    "+seqthi": "sequential-thinking.md",
}


def get_active_mode_fragments() -> list[str]:
    """
    Scan project's .claude/ for hook-*-mode-on files and load corresponding fragments.

    This function enables session-based modes by detecting flag files in the
    project's .claude/ directory. Flag files follow the pattern "hook-<mode>-mode-on",
    and the corresponding markdown fragment is loaded from prompt-fragments/<mode>.md.

    Returns:
        List of markdown fragment contents for active modes. Empty list if no
        active modes, CLAUDE_PROJECT_DIR is not set, or .claude/ doesn't exist.

    Example:
        Flag file: $CLAUDE_PROJECT_DIR/.claude/hook-approval-mode-on
        Loads: prompt-fragments/approval.md
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_dir:
        return []

    claude_dir = Path(project_dir) / ".claude"
    fragments_dir = Path(__file__).resolve().parent / "prompt-fragments"
    fragments: list[str] = []

    if not claude_dir.is_dir():
        return fragments

    for flag_file in claude_dir.glob("hook-*-mode-on"):
        # Extract mode name: hook-approval-mode-on → approval
        mode_name = flag_file.name[5:-8]  # strip "hook-" and "-mode-on"
        fragment_path = fragments_dir / f"{mode_name}.md"
        if fragment_path.is_file():
            fragments.append(fragment_path.read_text(encoding="utf-8"))

    return fragments


def split_prompt_and_triggers(prompt: str) -> tuple[str, list[str]]:
    """
    Extract trailing trigger tokens from prompt and return cleaned prompt with trigger list.

    This function scans the prompt from right to left, collecting any trailing
    tokens that start with "+". Mapped triggers are collected for later processing,
    while unmapped triggers are discarded. All trigger-like tokens are stripped from
    the output prompt.

    Args:
        prompt: The original user prompt, potentially with trailing triggers.

    Returns:
        A tuple of (cleaned_prompt, list_of_triggers) where:
        - cleaned_prompt: The prompt with all trailing trigger tokens removed
        - list_of_triggers: Ordered list of recognized triggers (deduplicated)

    Example:
        >>> split_prompt_and_triggers("Fix this code +ultrathink +absolute +unknown")
        ("Fix this code", ["+ultrathink", "+absolute"])  # +unknown is not mapped
    """
    text = prompt.rstrip()
    triggers: list[str] = []
    last_keep = len(text)

    while last_keep > 0:
        # Trim whitespace before the current token
        while last_keep > 0 and text[last_keep - 1].isspace():
            last_keep -= 1

        end = last_keep
        # Find the start of the token
        while last_keep > 0 and not text[last_keep - 1].isspace():
            last_keep -= 1
        start = last_keep

        if start == end:
            break

        token = text[start:end]
        if token.startswith(TRIGGER_PREFIX) and len(token) > 1:
            if token in TRIGGER_FILE_MAP:
                triggers.append(token)
            # Drop all trailing trigger-like tokens (mapped or not) from output
            continue
        else:
            # Non-trigger token encountered; stop scanning
            last_keep = end
            break

    base_prompt = text[:last_keep].rstrip()

    triggers.reverse()
    # Deduplicate while preserving the original order (left-to-right)
    seen: set = set()
    unique_triggers: list[str] = []
    for trigger in triggers:
        if trigger in seen:
            continue
        seen.add(trigger)
        unique_triggers.append(trigger)

    return base_prompt, unique_triggers


def load_fragments(triggers: list[str]) -> list[str]:
    """
    Load markdown file contents for each recognized trigger.

    This function looks for markdown files in the prompt-fragments/ subdirectory
    relative to this script's location. Only files that exist are loaded.

    Args:
        triggers: List of trigger identifiers (e.g., ["+ultrathink", "+absolute"])

    Returns:
        List of markdown file contents, in the same order as the triggers.
        Non-existent files are silently skipped.

    Example:
        >>> load_fragments(["+ultrathink", "+absolute"])
        ["ULTRATHINK MODE\n...", "System Instruction: Absolute Mode..."]
    """
    base_dir = Path(__file__).resolve().parent
    fragments_dir = base_dir / "prompt-fragments"
    fragments: list[str] = []

    for trigger in triggers:
        filename = TRIGGER_FILE_MAP.get(trigger)
        if not filename:
            continue

        path = fragments_dir / filename
        if path.is_file():
            fragments.append(path.read_text(encoding="utf-8"))

    return fragments


def build_prompt(prompt: str, fragments: list[str]) -> str:
    """
    Combine the base prompt with markdown fragments.

    Args:
        prompt: The cleaned prompt text (without triggers)
        fragments: List of markdown fragment contents to append

    Returns:
        The final prompt with fragments appended, separated by double newlines.
        If no fragments exist, returns the original prompt unchanged.

    Example:
        >>> build_prompt("Fix this", ["ULTRATHINK MODE"])
        "Fix this\\n\\nULTRATHINK MODE"
    """
    if not fragments:
        return prompt

    parts: list[str] = []
    if prompt:
        parts.append(prompt)
    parts.extend(fragments)
    return "\n\n".join(parts)


def main() -> None:
    """Main entry point for the prompt flag appender hook."""
    # Exit early if this hook is disabled
    exit_if_disabled()

    try:
        input_data: dict[str, Any] = json.load(sys.stdin)
        prompt = input_data.get("prompt", "")
        if not isinstance(prompt, str):
            raise ValueError("prompt must be a string")

        # Get mode-based fragments (from flag files in ~/.claude/)
        mode_fragments = get_active_mode_fragments()

        # Get trigger-based fragments (from prompt triggers)
        base_prompt, triggers = split_prompt_and_triggers(prompt)
        trigger_fragments = load_fragments(triggers)

        # Combine: mode fragments first, then trigger fragments
        all_fragments = mode_fragments + trigger_fragments

        # Build final prompt
        result = build_prompt(base_prompt, all_fragments)
        print(result)
    except json.JSONDecodeError as e:
        print(f"prompt_flag_appender error: Invalid JSON input - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"prompt_flag_appender error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
