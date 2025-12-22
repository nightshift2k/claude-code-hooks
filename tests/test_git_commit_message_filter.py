#!/usr/bin/env python3
"""
Comprehensive tests for git-commit-message-filter hook.

Tests all functions:
- check_commit_message()
- main()
"""

# Import using importlib for hyphenated name
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "git_commit_message_filter", hooks_dir / "git-commit-message-filter.py"
)
git_commit_message_filter = importlib.util.module_from_spec(spec)
sys.modules["git_commit_message_filter"] = git_commit_message_filter
spec.loader.exec_module(git_commit_message_filter)

check_commit_message = git_commit_message_filter.check_commit_message
main = git_commit_message_filter.main


# =============================================================================
# Tests for check_commit_message()
# =============================================================================


class TestCheckCommitMessage:
    """Test check_commit_message() function."""

    def test_blocks_emoji_generated_with_claude_code(self, capsys) -> None:
        """Should block commits with emoji Claude Code marker."""
        command = 'git commit -m "Fix bug\n\n🤖 Generated with [Claude Code]"'

        with pytest.raises(SystemExit) as exc_info:
            check_commit_message(command)

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "auto-generated Claude markers" in captured.err

    def test_blocks_co_authored_by_claude(self, capsys) -> None:
        """Should block commits with Co-Authored-By Claude marker."""
        command = (
            'git commit -m "Fix bug\n\nCo-Authored-By: Claude <noreply@anthropic.com>"'
        )

        with pytest.raises(SystemExit) as exc_info:
            check_commit_message(command)

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "auto-generated Claude markers" in captured.err

    def test_blocks_generated_with_text(self, capsys) -> None:
        """Should block commits with 'Generated with...Claude...Code' text."""
        command = 'git commit -m "Fix bug\n\nGenerated with Claude Code"'

        with pytest.raises(SystemExit) as exc_info:
            check_commit_message(command)

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "auto-generated Claude markers" in captured.err

    def test_blocks_claude_email_address(self, capsys) -> None:
        """Should block commits with Claude email address."""
        command = 'git commit -m "Fix bug\n\nClaude <noreply@anthropic.com>"'

        with pytest.raises(SystemExit) as exc_info:
            check_commit_message(command)

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "auto-generated Claude markers" in captured.err

    def test_allows_clean_commit_message(self) -> None:
        """Should allow commits without Claude markers."""
        command = 'git commit -m "Fix authentication bug"'
        # Should not raise SystemExit
        check_commit_message(command)

    def test_allows_non_git_commit_command(self) -> None:
        """Should allow non-commit git commands."""
        command = "git push origin main"
        # Should not raise SystemExit
        check_commit_message(command)

    def test_case_insensitive_matching(self, capsys) -> None:
        """Should detect markers case-insensitively."""
        command = 'git commit -m "Fix\n\ngenerated with CLAUDE code"'

        with pytest.raises(SystemExit) as exc_info:
            check_commit_message(command)

        assert exc_info.value.code == 2

    def test_multiline_message_detection(self, capsys) -> None:
        """Should detect markers in multiline commit messages."""
        command = '''git commit -m "$(cat <<'EOF'
Fix authentication bug

🤖 Generated with [Claude Code]

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"'''

        with pytest.raises(SystemExit) as exc_info:
            check_commit_message(command)

        assert exc_info.value.code == 2


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_blocks_commit_with_claude_markers(self, capsys) -> None:
        """Should block git commits containing Claude markers."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'git commit -m "Fix\n\n🤖 Generated with [Claude Code]"'
            },
        }

        with patch("git_commit_message_filter.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "auto-generated Claude markers" in captured.err

    def test_allows_clean_commit(self) -> None:
        """Should allow commits without Claude markers."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": 'git commit -m "Fix authentication bug"'},
        }

        with patch("git_commit_message_filter.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_non_bash_tool(self) -> None:
        """Should exit 0 for non-Bash tool invocations."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
        }

        with patch("git_commit_message_filter.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_non_git_command(self) -> None:
        """Should exit 0 for commands without git commit."""
        input_data = {"tool_name": "Bash", "tool_input": {"command": "npm install"}}

        with patch("git_commit_message_filter.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_missing_command(self) -> None:
        """Should handle missing command gracefully."""
        input_data = {"tool_name": "Bash", "tool_input": {}}

        with patch("git_commit_message_filter.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0
