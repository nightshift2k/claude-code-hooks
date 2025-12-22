#!/usr/bin/env python3
"""
Serena project detection UserPromptSubmit hook.

Runs on every user prompt but only outputs on the first prompt in a session.
Uses session markers to track seen sessions with self-cleaning mechanism.

Detects three states:
1. Configured: .git/ + .serena/project.yml with project_name
   Output: Suggest activate_project with project name and languages
2. Code project: .git/ + code files (no .serena/ or no project_name)
   Output: Suggest onboarding with detected languages
3. Not a project: No .git/
   Output: Silent (no output)
"""

import json
import os
import re
import sys
import time
from pathlib import Path

# Maximum age for session markers before cleanup (in days)
SESSION_MARKER_MAX_AGE_DAYS = 7


def get_session_markers_dir() -> Path:
    """
    Get the session markers directory for the current project.

    Uses CLAUDE_PROJECT_DIR environment variable to ensure markers are
    stored in the project's .claude directory, not globally.

    Returns:
        Path to the project-local session markers directory.
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        return Path(project_dir) / ".claude" / "hook_serena_awareness_session_markers"
    # Fallback to home directory if no project dir (shouldn't happen)
    return Path.home() / ".claude" / "hook_serena_awareness_session_markers"


# Import shared utilities
try:
    from hook_utils import Colors, detect_project_languages, exit_if_disabled
except ImportError:
    # Fallback if hook_utils not available (shouldn't happen in production)
    sys.exit(0)


def cleanup_old_session_markers(current_session_id: str) -> None:
    """
    Remove session markers older than SESSION_MARKER_MAX_AGE_DAYS.

    Preserves the current session's marker to avoid cleaning itself.
    Runs on every hook invocation for self-maintenance.

    Args:
        current_session_id: The session ID to preserve (never delete)
    """
    markers_dir = get_session_markers_dir()
    if not markers_dir.exists():
        return

    cutoff = time.time() - (SESSION_MARKER_MAX_AGE_DAYS * 86400)

    for marker in markers_dir.glob("*.seen"):
        # Never clean current session
        if marker.stem == current_session_id:
            continue
        # Remove if older than cutoff
        try:
            if marker.stat().st_mtime < cutoff:
                marker.unlink()
        except OSError:
            # Ignore errors (file may have been deleted by another process)
            pass


def is_first_prompt_in_session(session_id: str) -> bool:
    """
    Check if this is the first prompt in the session.

    Uses marker files to track seen sessions. Creates marker on first
    prompt, returns False on subsequent prompts.

    Args:
        session_id: The session ID from UserPromptSubmit input

    Returns:
        True if this is the first prompt, False otherwise
    """
    markers_dir = get_session_markers_dir()
    markers_dir.mkdir(parents=True, exist_ok=True)

    marker = markers_dir / f"{session_id}.seen"
    is_first = not marker.exists()

    # Mark session as seen (touch creates or updates mtime)
    marker.touch()

    # Self-clean old markers (except current)
    cleanup_old_session_markers(session_id)

    return is_first


def is_aggressive_mode_enabled() -> bool:
    """
    Check if aggressive mode is enabled via flag file or environment variable.

    Aggressive mode outputs prescriptive instructions that REQUIRE Serena MCP
    usage for code exploration, instead of passive suggestions.

    Can be enabled via:
    - SERENA_AGGRESSIVE_MODE=1 environment variable
    - .claude/hook-serena-awareness-aggressive-on flag file in project directory

    Returns:
        True if aggressive mode is enabled, False otherwise.
    """
    # Environment variable takes precedence
    if os.environ.get("SERENA_AGGRESSIVE_MODE") == "1":
        return True

    # Check for project flag file
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        flag_file = (
            Path(project_dir) / ".claude" / "hook-serena-awareness-aggressive-on"
        )
        if flag_file.exists():
            return True

    return False


def parse_project_name(config_path: str) -> str | None:
    """
    Parse project_name from .serena/project.yml without YAML library.

    Uses regex to extract project_name value from YAML file.

    Args:
        config_path: Path to project.yml file

    Returns:
        Project name string, or None if not found or invalid

    Example:
        parse_project_name(".serena/project.yml")  # Returns "my-project"
    """
    try:
        with open(config_path, encoding="utf-8") as f:
            content = f.read()

        # Match: project_name: value (with optional quotes and whitespace)
        # Pattern: project_name: followed by optional whitespace, optional quotes, value, optional quotes
        # Only accept alphanumeric, dash, underscore, and dot characters to avoid malformed YAML
        pattern = r'^\s*project_name\s*:\s*["\']?([a-zA-Z0-9_.-]+)["\']?\s*$'
        match = re.search(pattern, content, re.MULTILINE)

        if match:
            project_name = match.group(1).strip()
            return project_name if project_name else None

        return None

    except (OSError, UnicodeDecodeError):
        return None


def get_project_state() -> dict[str, any]:
    """
    Detect project state based on directory structure.

    Returns:
        Dictionary with:
        - type: "configured", "code_project", or "not_project"
        - project_name: str (only for configured)
        - languages: List[str] (display names, only for configured/code_project)

    Example:
        state = get_project_state()
        if state["type"] == "configured":
            print(f"Project: {state['project_name']}")
    """
    # Get project directory from environment
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_dir:
        return {"type": "not_project"}

    project_path = Path(project_dir)

    # Check for .git directory
    git_dir = project_path / ".git"
    if not git_dir.exists():
        return {"type": "not_project"}

    # Detect languages in project
    detected_languages = detect_project_languages(str(project_path))
    language_names = [lang.display_name for lang in detected_languages]

    # Check for .serena/project.yml with project_name
    serena_config = project_path / ".serena" / "project.yml"
    if serena_config.is_file():
        project_name = parse_project_name(str(serena_config))
        if project_name:
            return {
                "type": "configured",
                "project_name": project_name,
                "languages": language_names,
            }

    # Git project with code but no Serena configuration
    return {"type": "code_project", "languages": language_names}


def format_output(state: dict[str, any]) -> str:
    """
    Format detection output for Claude.

    Args:
        state: Project state dictionary from get_project_state()

    Returns:
        Formatted markdown output, or empty string for silent cases

    Example:
        output = format_output({"type": "configured", "project_name": "test", "languages": ["Python"]})
        print(output)  # Displays Serena project detection message
    """
    if state["type"] == "not_project":
        return ""

    if state["type"] == "configured":
        project_name = state["project_name"]
        languages = state["languages"]
        language_list = ", ".join(languages).lower() if languages else "none detected"

        return f"""## Serena Project Detected
.serena/ with project "{Colors.cyan(project_name)}" found.
Configured languages: {language_list}
If Serena MCP is available: {Colors.green("`activate_project`")}"""

    if state["type"] == "code_project":
        languages = state["languages"]
        if languages:
            language_list = ", ".join(languages)
        else:
            language_list = "none detected"

        return f"""## Code Project Detected
Detected languages: {language_list}
If Serena MCP is available, consider {Colors.green("`onboarding`")} for semantic code navigation."""

    return ""


def format_aggressive_output(state: dict[str, any]) -> str:
    """
    Format aggressive detection output that REQUIRES Serena MCP usage.

    Uses prescriptive language with MANDATORY tags and anti-rationalization
    patterns to ensure Claude uses Serena tools instead of Grep/Glob.

    Args:
        state: Project state dictionary from get_project_state()

    Returns:
        Formatted markdown output with mandatory instructions, or empty string

    Example:
        output = format_aggressive_output({"type": "configured", "project_name": "test", "languages": ["Python"]})
        print(output)  # Displays mandatory Serena usage instructions
    """
    if state["type"] == "not_project":
        return ""

    if state["type"] == "configured":
        project_name = state["project_name"]
        languages = state["languages"]
        language_list = ", ".join(languages).lower() if languages else "none detected"

        return f"""## Serena Project Active
Project: {Colors.cyan(project_name)} ({language_list})

<MANDATORY>
**Serena MCP is REQUIRED for all code exploration in this project.**

DO:
- `find_symbol` for locating classes, functions, methods
- `get_symbols_overview` for file structure
- `find_referencing_symbols` for usage/callers

DO NOT:
- Grep for function/class definitions
- Glob for finding code files by pattern
- Read entire files to find symbols

If you think "Grep is faster" or "this is a simple query" → WRONG. Use Serena.
</MANDATORY>

Action: Run {Colors.green("`activate_project`")} now if not already active."""

    if state["type"] == "code_project":
        languages = state["languages"]
        language_list = ", ".join(languages) if languages else "none detected"

        return f"""## Code Project Detected
Detected languages: {language_list}

<MANDATORY>
**Run {Colors.green("`onboarding`")} to enable Serena MCP for semantic code navigation.**

After onboarding, Serena tools are REQUIRED for code exploration:
- `find_symbol` instead of Grep for definitions
- `get_symbols_overview` instead of reading files
- `find_referencing_symbols` for usage analysis

DO NOT use Grep/Glob for code symbol operations.
</MANDATORY>"""

    return ""


def main() -> None:
    """
    Main entry point for serena-awareness hook.

    Reads UserPromptSubmit hook input from stdin, extracts session_id,
    checks if this is the first prompt in the session, and outputs
    detection message only on first prompt.
    """
    try:
        # Check if hook is disabled
        exit_if_disabled()

        # Read and parse JSON input from stdin
        stdin_data = sys.stdin.read()
        try:
            input_data = json.loads(stdin_data)
        except json.JSONDecodeError:
            # Invalid JSON - fail silently
            sys.exit(0)

        # Extract session_id from input
        session_id = input_data.get("session_id")
        if not session_id:
            # No session ID available - fail silently
            sys.exit(0)

        # Only output on first prompt in session
        if not is_first_prompt_in_session(session_id):
            sys.exit(0)

        # Detect project state
        state = get_project_state()

        # Format and output message (aggressive mode if enabled)
        if is_aggressive_mode_enabled():
            output = format_aggressive_output(state)
        else:
            output = format_output(state)
        if output:
            print(output)

    except Exception:
        # Fail open: silent failure on any exception
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
