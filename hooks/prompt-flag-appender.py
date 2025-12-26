#!/usr/bin/env python3
"""
Prompt Flag Appender Hook - Appends markdown snippets based on trailing triggers.

This hook processes Claude Code prompts to detect trailing triggers (e.g., "+ultrathink")
and replaces them with the contents of corresponding markdown fragments defined in TOML
configuration. This allows users to quickly inject common prompt modifications using
trigger words.

Configuration:
    System config: hooks/prompt-flag-appender.toml (next to this script)
    Project config: $CLAUDE_PROJECT_DIR/.claude/prompt-flag-appender.toml (optional)
    Project entries override system entries with the same key.

Additionally, this hook supports:
- Always-on injection: A special [_always] section in the TOML that injects on every prompt
- Session-based modes via flag files in the project's .claude/ directory. Files matching
  the pattern "hook-*-mode-on" will automatically inject their corresponding fragments
  for the entire session.

Usage:
    Include mapped triggers at the end of the prompt (e.g., "+ultrathink +absolute").
    Triggers are stripped from the prompt and replaced by the contents of the mapped
    fragments if they exist in the configuration.

    For session-based modes, create flag files in your project's .claude/ directory:
        touch .claude/hook-approval-mode-on  # Enables approval mode for project
        rm .claude/hook-approval-mode-on     # Disables approval mode

Example:
    User prompt: "Refactor this code +ultrathink"
    Result: "Refactor this code\n\n[ultrathink content]"

    Session mode: $CLAUDE_PROJECT_DIR/.claude/hook-approval-mode-on exists
    User prompt: "Refactor this code"
    Result: "Refactor this code\n\n[approval content]"
"""

import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any

from hook_utils import exit_if_disabled

# Trigger prefix character
TRIGGER_PREFIX = "+"


def load_config() -> dict[str, dict[str, Any]]:
    """
    Load and merge TOML configuration from system and project files.

    Loads the system configuration from prompt-flag-appender.toml next to this script,
    then merges any project-specific overrides from $CLAUDE_PROJECT_DIR/.claude/
    prompt-flag-appender.toml. Project entries completely replace system entries
    with the same key.

    Returns:
        Dictionary mapping trigger names to their configuration (aliases, content).
        Empty dict on load failure (fail open).

    Example:
        >>> config = load_config()
        >>> config["ultrathink"]["content"]
        "ULTRATHINK MODE ACTIVATED..."
    """
    config: dict[str, dict[str, Any]] = {}

    # Load system config
    system_toml = Path(__file__).resolve().with_suffix(".toml")
    if system_toml.is_file():
        try:
            with open(system_toml, "rb") as f:
                config = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            print(
                f"prompt_flag_appender warning: malformed system TOML - {e}",
                file=sys.stderr,
            )
            # Continue with empty config

    # Load project config (overrides system)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        project_toml = Path(project_dir) / ".claude" / "prompt-flag-appender.toml"
        if project_toml.is_file():
            try:
                with open(project_toml, "rb") as f:
                    project_config = tomllib.load(f)
                # Merge: project entries override system entries
                config.update(project_config)
            except tomllib.TOMLDecodeError as e:
                print(
                    f"prompt_flag_appender warning: malformed project TOML - {e}",
                    file=sys.stderr,
                )
                # Continue with system config

    return config


def build_alias_map(config: dict[str, dict[str, Any]]) -> dict[str, str]:
    """
    Build a mapping from aliases to canonical trigger names.

    Args:
        config: The loaded configuration dictionary.

    Returns:
        Dictionary mapping alias names to their canonical trigger names.
        Skips reserved section names like "_always".

    Example:
        >>> config = {"sequential-thinking": {"aliases": ["seqthi"], "content": "..."}}
        >>> build_alias_map(config)
        {"seqthi": "sequential-thinking"}
    """
    alias_map: dict[str, str] = {}
    for trigger_name, trigger_config in config.items():
        # Skip reserved sections
        if trigger_name.startswith("_"):
            continue
        if isinstance(trigger_config, dict):
            aliases = trigger_config.get("aliases", [])
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str):
                        alias_map[alias] = trigger_name
    return alias_map


def resolve_trigger(
    trigger: str,
    config: dict[str, dict[str, Any]],
    alias_map: dict[str, str],
) -> str | None:
    """
    Resolve a trigger name to its canonical form.

    Checks for direct match first, then alias lookup.

    Args:
        trigger: The trigger name without the + prefix.
        config: The loaded configuration dictionary.
        alias_map: Mapping from aliases to canonical names.

    Returns:
        The canonical trigger name, or None if not found.

    Example:
        >>> resolve_trigger("seqthi", config, alias_map)
        "sequential-thinking"
    """
    # Direct match
    if trigger in config:
        return trigger
    # Alias lookup
    if trigger in alias_map:
        return alias_map[trigger]
    return None


def get_trigger_content(
    trigger_name: str,
    config: dict[str, dict[str, Any]],
) -> str | None:
    """
    Get the content for a canonical trigger name.

    Args:
        trigger_name: The canonical trigger name.
        config: The loaded configuration dictionary.

    Returns:
        The trigger content string, or None if not found or invalid.
    """
    trigger_config = config.get(trigger_name)
    if not isinstance(trigger_config, dict):
        return None
    content = trigger_config.get("content")
    if isinstance(content, str):
        return content.strip()
    return None


def get_always_fragment(config: dict[str, dict[str, Any]]) -> str | None:
    """
    Get the always-on injection content from the special [_always] section.

    The [_always] section is a reserved trigger name that injects its content
    on every prompt, before any mode or trigger fragments.

    Args:
        config: The loaded configuration dictionary.

    Returns:
        The always-on content string, or None if not defined.

    Example:
        >>> config = {"_always": {"content": "Always follow these rules..."}}
        >>> get_always_fragment(config)
        "Always follow these rules..."
    """
    return get_trigger_content("_always", config)


def get_active_mode_fragments(
    config: dict[str, dict[str, Any]],
    alias_map: dict[str, str],
) -> list[str]:
    """
    Scan project's .claude/ for hook-*-mode-on files and load corresponding fragments.

    This function enables session-based modes by detecting flag files in the
    project's .claude/ directory. Flag files follow the pattern "hook-<mode>-mode-on",
    and the corresponding fragment is loaded from the configuration.

    Args:
        config: The loaded configuration dictionary.
        alias_map: Mapping from aliases to canonical names.

    Returns:
        List of markdown fragment contents for active modes. Empty list if no
        active modes, CLAUDE_PROJECT_DIR is not set, or .claude/ doesn't exist.

    Example:
        Flag file: $CLAUDE_PROJECT_DIR/.claude/hook-approval-mode-on
        Loads: config["approval"]["content"]
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_dir:
        return []

    claude_dir = Path(project_dir) / ".claude"
    fragments: list[str] = []

    if not claude_dir.is_dir():
        return fragments

    for flag_file in claude_dir.glob("hook-*-mode-on"):
        # Extract mode name: hook-approval-mode-on -> approval
        mode_name = flag_file.name[5:-8]  # strip "hook-" and "-mode-on"
        canonical = resolve_trigger(mode_name, config, alias_map)
        if canonical:
            content = get_trigger_content(canonical, config)
            if content:
                fragments.append(content)

    return fragments


def split_prompt_and_triggers(
    prompt: str,
    config: dict[str, dict[str, Any]],
    alias_map: dict[str, str],
) -> tuple[str, list[str]]:
    """
    Extract trailing trigger tokens from prompt and return cleaned prompt with trigger list.

    This function scans the prompt from right to left, collecting any trailing
    tokens that start with "+". Recognized triggers (direct or via alias) are
    collected for later processing, while unrecognized triggers are discarded.
    All trigger-like tokens are stripped from the output prompt.

    Args:
        prompt: The original user prompt, potentially with trailing triggers.
        config: The loaded configuration dictionary.
        alias_map: Mapping from aliases to canonical names.

    Returns:
        A tuple of (cleaned_prompt, list_of_canonical_triggers) where:
        - cleaned_prompt: The prompt with all trailing trigger tokens removed
        - list_of_canonical_triggers: Ordered list of canonical trigger names (deduplicated)

    Example:
        >>> split_prompt_and_triggers("Fix this code +ultrathink +seqthi", config, alias_map)
        ("Fix this code", ["ultrathink", "sequential-thinking"])
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
            trigger_name = token[1:]  # Remove + prefix
            canonical = resolve_trigger(trigger_name, config, alias_map)
            if canonical:
                triggers.append(canonical)
            # Drop all trailing trigger-like tokens (recognized or not) from output
            continue
        else:
            # Non-trigger token encountered; stop scanning
            last_keep = end
            break

    base_prompt = text[:last_keep].rstrip()

    triggers.reverse()
    # Deduplicate while preserving the original order (left-to-right)
    seen: set[str] = set()
    unique_triggers: list[str] = []
    for trigger in triggers:
        if trigger in seen:
            continue
        seen.add(trigger)
        unique_triggers.append(trigger)

    return base_prompt, unique_triggers


def get_fragments_for_triggers(
    triggers: list[str],
    config: dict[str, dict[str, Any]],
) -> list[str]:
    """
    Get fragment contents for a list of canonical trigger names.

    Args:
        triggers: List of canonical trigger names.
        config: The loaded configuration dictionary.

    Returns:
        List of fragment contents in the same order as triggers.
        Non-existent triggers are silently skipped.

    Example:
        >>> get_fragments_for_triggers(["ultrathink", "absolute"], config)
        ["ULTRATHINK MODE ACTIVATED...", "System Instruction: Absolute Mode..."]
    """
    fragments: list[str] = []
    for trigger in triggers:
        content = get_trigger_content(trigger, config)
        if content:
            fragments.append(content)
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
        # Load configuration
        config = load_config()
        alias_map = build_alias_map(config)

        input_data: dict[str, Any] = json.load(sys.stdin)
        prompt = input_data.get("prompt", "")
        if not isinstance(prompt, str):
            raise ValueError("prompt must be a string")

        # Get always-on fragment (from [_always] section)
        always_fragment = get_always_fragment(config)

        # Get mode-based fragments (from flag files in .claude/)
        mode_fragments = get_active_mode_fragments(config, alias_map)

        # Get trigger-based fragments (from prompt triggers)
        base_prompt, triggers = split_prompt_and_triggers(prompt, config, alias_map)
        trigger_fragments = get_fragments_for_triggers(triggers, config)

        # Combine: always first, then mode fragments, then trigger fragments
        all_fragments: list[str] = []
        if always_fragment:
            all_fragments.append(always_fragment)
        all_fragments.extend(mode_fragments)
        all_fragments.extend(trigger_fragments)

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
