#!/usr/bin/env python3
"""
Prompt Flag Appender Hook - Appends markdown snippets based on trailing triggers.

This hook processes Claude Code prompts to detect trailing triggers (e.g., "+ultrathink")
and replaces them with the contents of corresponding markdown files. This allows
users to quickly inject common prompt modifications using trigger words.

Usage:
    Include mapped triggers at the end of the prompt (e.g., "+ultrathink +absolute").
    Triggers are stripped from the prompt and replaced by the contents of the mapped
    markdown files if they exist in the prompt-fragments/ directory.

Example:
    User prompt: "Refactor this code +ultrathink"
    Result: "Refactor this code\n\n[ultrathink.md contents]"
"""

from pathlib import Path
import json
import sys
from typing import Dict, List, Tuple, Any

from hook_utils import exit_if_disabled

# Trigger prefix character
TRIGGER_PREFIX = "+"

# Map trigger words to markdown filenames in prompt-fragments/ directory
TRIGGER_FILE_MAP: Dict[str, str] = {
    "+ultrathink": "ultrathink.md",
    "+absolute": "absolute.md",
}


def split_prompt_and_triggers(prompt: str) -> Tuple[str, List[str]]:
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
    triggers: List[str] = []
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
    unique_triggers: List[str] = []
    for trigger in triggers:
        if trigger in seen:
            continue
        seen.add(trigger)
        unique_triggers.append(trigger)

    return base_prompt, unique_triggers


def load_fragments(triggers: List[str]) -> List[str]:
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
    fragments: List[str] = []

    for trigger in triggers:
        filename = TRIGGER_FILE_MAP.get(trigger)
        if not filename:
            continue

        path = fragments_dir / filename
        if path.is_file():
            fragments.append(path.read_text(encoding="utf-8"))

    return fragments


def build_prompt(prompt: str, fragments: List[str]) -> str:
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

    parts: List[str] = []
    if prompt:
        parts.append(prompt)
    parts.extend(fragments)
    return "\n\n".join(parts)


def main() -> None:
    """Main entry point for the prompt flag appender hook."""
    # Exit early if this hook is disabled
    exit_if_disabled()

    try:
        input_data: Dict[str, Any] = json.load(sys.stdin)
        prompt = input_data.get("prompt", "")
        if not isinstance(prompt, str):
            raise ValueError("prompt must be a string")

        base_prompt, triggers = split_prompt_and_triggers(prompt)
        fragments = load_fragments(triggers)
        result = build_prompt(base_prompt, fragments)
        print(result)
    except json.JSONDecodeError as e:
        print(f"prompt_flag_appender error: Invalid JSON input - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"prompt_flag_appender error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
