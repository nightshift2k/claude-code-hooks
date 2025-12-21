#!/usr/bin/env python3
"""
Git Branch Protection Hook - Prevents code edits on protected branches.

This hook blocks file editing operations when working on protected branches
(main, master, production, prod), enforcing good git hygiene by requiring
feature branches for development work.

For Bash commands, it detects potential file-writing patterns and outputs
a reflective question to prompt Claude to verify the operation, but does
not block execution.

Note: Tool filtering is handled by the matcher in settings.json.
This hook assumes it's only called for edit-related tools.
"""

import json
import re
import subprocess
import sys
from typing import List, Optional, Tuple

from hook_utils import Colors, exit_if_disabled

# Branches where edits are blocked
PROTECTED_BRANCHES: List[str] = [
    "main",
    "master",
    "production",
    "prod",
]

# Safe redirect targets that should be ignored
SAFE_REDIRECT_TARGETS = ["/dev/null", "/dev/stdout", "/dev/stderr"]


def get_current_branch() -> Optional[str]:
    """
    Get the current git branch name.

    Returns:
        The current branch name, or None if not in a git repo or error.
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def detect_file_write_patterns(command: str) -> List[Tuple[str, str]]:
    """
    Detect potential file-writing patterns in a bash command.

    This uses simple regex patterns and cannot reliably distinguish between:
    - Actual file writes (echo "x" > file)
    - Quoted text (git commit -m "x > y")
    - Comparison operators (awk '{if(x>5)}')

    Args:
        command: The bash command to analyze

    Returns:
        List of tuples (pattern_name, matching_text) for detected patterns.
        Empty list if no patterns found.
    """
    if not command:
        return []

    patterns: List[Tuple[str, str]] = []

    # Check for sed -i (in-place edit)
    sed_match = re.search(r"sed\s+-i(?:\.\w+)?", command)
    if sed_match:
        patterns.append(("sed -i", command))

    # Check for perl -i (in-place edit)
    perl_match = re.search(r"perl\s+-i", command)
    if perl_match:
        patterns.append(("perl -i", command))

    # Check for redirect operators (>, >>)
    # Look for > or >> followed by something that's not a safe target
    redirect_match = re.search(r">\s*(?!\s*/dev/(?:null|stdout|stderr))", command)
    if redirect_match:
        # Make sure it's not redirecting to /dev/null, /dev/stdout, or /dev/stderr
        is_safe = False
        for safe_target in SAFE_REDIRECT_TARGETS:
            if safe_target in command[redirect_match.start() :]:
                # Check if the safe target is actually after this redirect
                remaining = command[redirect_match.start() :]
                if re.search(r">\s*" + re.escape(safe_target), remaining):
                    is_safe = True
                    break

        if not is_safe:
            if ">>" in command[redirect_match.start() : redirect_match.start() + 3]:
                patterns.append(("redirect >>", command))
            else:
                patterns.append(("redirect >", command))

    # Check for tee command (writes to file)
    tee_match = re.search(r"\btee\s+", command)
    if tee_match:
        # Make sure it's not tee to /dev/null
        remaining = command[tee_match.end() :]
        is_safe = any(
            safe in remaining.split()[0] if remaining.split() else ""
            for safe in SAFE_REDIRECT_TARGETS
        )
        if not is_safe:
            patterns.append(("tee", command))

    # Check for heredoc with redirect (<<EOF ... > file)
    heredoc_match = re.search(r"<<\w+.*?>", command, re.DOTALL)
    if heredoc_match:
        is_safe = any(
            safe in command[heredoc_match.start() :] for safe in SAFE_REDIRECT_TARGETS
        )
        if not is_safe:
            patterns.append(("heredoc redirect", command))

    return patterns


def main() -> None:
    """Main entry point for the git branch protection hook."""
    exit_if_disabled()

    try:
        # Read and parse stdin
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Get current branch
        current_branch = get_current_branch()
        if current_branch is None:
            # Not in a git repo or can't determine branch - allow
            sys.exit(0)

        # Check if on protected branch
        if current_branch not in PROTECTED_BRANCHES:
            # Not on a protected branch - allow
            sys.exit(0)

        # For Edit/Write tools: Block with exit 2
        if tool_name in ["Edit", "Write"]:
            error_msg = f"""{Colors.red(f"❌ Cannot edit files on protected branch '{current_branch}'!")}
{Colors.yellow("📝 Create a feature branch first:")}
   git checkout -b feature/your-feature-name
{Colors.blue("💡 Or disable this hook:")}
   echo "git-branch-protection" >> .claude/disabled-hooks"""
            print(error_msg, file=sys.stderr)
            sys.exit(2)

        # For Bash tool: Check for file-write patterns
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            patterns = detect_file_write_patterns(command)

            if patterns:
                # Output reflective question but don't block
                pattern_descriptions = "\n".join(
                    f"   - Pattern: `{name}`" for name, _ in patterns
                )

                question = f"""---
{Colors.yellow("## Branch Protection Check")}

You are on protected branch '{current_branch}'.

I detected patterns in your bash command that sometimes indicate file writing:
{pattern_descriptions}

Command: `{command}`

However, pattern matching cannot reliably distinguish between:
- Shell redirection (`echo "x" > file`) - writes to file
- Quoted text (`git commit -m "x > y"`) - just text
- Comparison operators (`awk '{{if(x>5)}}'`) - not a write

{Colors.blue("Please verify:")} Does this command actually write files on the protected branch?
If yes, consider using the Edit tool or a feature branch instead.
---"""
                print(question, file=sys.stderr)

        # Allow (exit 0) for Bash tool regardless of pattern detection
        sys.exit(0)

    except Exception:
        # Silent failure
        sys.exit(0)


if __name__ == "__main__":
    main()
