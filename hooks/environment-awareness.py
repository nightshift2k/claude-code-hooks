#!/usr/bin/env python3
"""
Environment Awareness Hook - Injects system environment context.

Provides the AI with awareness of:
- Current date and day of week
- Current time and timezone
- Operating system
- Working directory
"""

import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from hook_utils import exit_if_disabled


def get_environment_context() -> str:
    """
    Gather environment information and format as markdown block.

    Returns:
        Formatted markdown string with environment details.
    """
    now = datetime.now().astimezone()

    # Format date with day of week
    date_str = now.strftime("%Y-%m-%d (%A)")

    # Format time with timezone
    time_str = now.strftime("%H:%M %Z")

    # Get OS info
    os_name = platform.system()
    os_release = platform.release()
    if os_name == "Darwin":
        os_name = "macOS"
    os_str = f"{os_name} {os_release}"

    # Get working directory, collapse home to ~
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    home = str(Path.home())
    if project_dir.startswith(home):
        project_dir = "~" + project_dir[len(home) :]

    return f"""## Environment
- Date: {date_str}
- Time: {time_str}
- OS: {os_str}
- Directory: {project_dir}
"""


def main() -> None:
    """Main entry point for the environment awareness hook."""
    exit_if_disabled()

    try:
        input_data: Dict[str, Any] = json.load(sys.stdin)

        # Only process SessionStart events
        if input_data.get("hook_event_name") != "SessionStart":
            sys.exit(0)

        # Output environment context (injected as context)
        print(get_environment_context())
        sys.exit(0)

    except Exception:
        # Silent failure
        sys.exit(0)


if __name__ == "__main__":
    main()
