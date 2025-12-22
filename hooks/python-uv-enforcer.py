#!/usr/bin/env python3
"""
Python UV Enforcer Hook - Enforces use of uv instead of traditional Python tools.

This hook intercepts Python package management and execution commands,
blocking traditional tools (pip, poetry, pipenv, etc.) and suggesting
equivalent uv commands instead. This promotes consistent use of the
modern uv package manager across the project.
"""

import json
import re
import sys
from typing import Any

from hook_utils import Colors, exit_if_disabled


def main() -> None:
    """Main entry point for the Python UV enforcer hook."""
    # Exit early if this hook is disabled
    exit_if_disabled()

    try:
        # Read input from Claude Code
        input_data: dict[str, Any] = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name == "Bash":
            command = tool_input.get("command", "")

            # List of Python tools that should be replaced with uv
            python_tools = [
                "pip",
                "pip3",
                "python",
                "python3",
                "pytest",
                "pylint",
                "flake8",
                "black",
                "mypy",
                "isort",
                "poetry",
                "pipenv",
                "conda",
                "virtualenv",
                "pyenv",
            ]

            # Check if command uses Python tools (but not venv or uv)
            pattern = r"^(" + "|".join(python_tools) + r")\b"
            if re.match(pattern, command) and not re.match(
                r"^(python3?\s+-m\s+venv|uv\s+)", command
            ):
                error_msg = f"""{Colors.red("❌ Direct Python tool usage detected!")}
{Colors.yellow("📝 Command blocked:")} {command}
{Colors.green("✨ Use uv instead:")}"""

                # Provide specific suggestions based on the command
                if "pip" in command and "install" in command:
                    error_msg += "\n   uv pip install ..."
                elif command.startswith("python"):
                    error_msg += "\n   uv run python ..."
                elif command.startswith("pytest"):
                    error_msg += "\n   uv run pytest ..."
                elif command.startswith("black"):
                    error_msg += "\n   uv run black ..."
                elif command.startswith("mypy"):
                    error_msg += "\n   uv run mypy ..."
                else:
                    error_msg += f"\n   uv run {command}"

                error_msg += (
                    f"\n{Colors.blue('💡 Learn more:')} https://github.com/astral-sh/uv"
                )

                print(error_msg, file=sys.stderr)
                sys.exit(2)  # Exit code 2 = blocking error

        # If no violation, exit silently
        sys.exit(0)

    except Exception:
        # Silent failure - hooks should not break the workflow
        sys.exit(0)


if __name__ == "__main__":
    main()
