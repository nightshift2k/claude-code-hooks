#!/usr/bin/env python3
"""
Comprehensive tests for changelog-reminder hook targeting 100% code coverage.

Tests all functions and edge cases:
- is_meaningful_file()
- get_staged_files()
- is_changelog_staged()
- is_git_commit_command()
- main()
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Import module with hyphenated name using importlib
hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "changelog_reminder", hooks_dir / "changelog-reminder.py"
)
changelog_reminder = importlib.util.module_from_spec(spec)
sys.modules["changelog_reminder"] = changelog_reminder
spec.loader.exec_module(changelog_reminder)

is_meaningful_file = changelog_reminder.is_meaningful_file
get_staged_files = changelog_reminder.get_staged_files
is_changelog_staged = changelog_reminder.is_changelog_staged
is_git_commit_command = changelog_reminder.is_git_commit_command
main = changelog_reminder.main


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_tool_use() -> Dict[str, Any]:
    """Fixture for basic Bash tool use JSON."""
    return {
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m 'Add feature'"},
    }


@pytest.fixture
def non_bash_tool_use() -> Dict[str, Any]:
    """Fixture for non-Bash tool use."""
    return {
        "tool_name": "Read",
        "tool_input": {"file_path": "/some/file.txt"},
    }


# =============================================================================
# Tests for is_meaningful_file()
# =============================================================================


class TestIsMeaningfulFile:
    """Test is_meaningful_file() function."""

    def test_returns_true_for_production_code(self) -> None:
        """Should return True for production code files."""
        assert is_meaningful_file("hooks/new-hook.py") is True
        assert is_meaningful_file("hooks/hook_utils.py") is True
        assert is_meaningful_file("src/main.py") is True

    def test_returns_false_for_test_files(self) -> None:
        """Should return False for test files."""
        assert is_meaningful_file("tests/test_hook.py") is False
        assert is_meaningful_file("tests/conftest.py") is False

    def test_returns_false_for_github_files(self) -> None:
        """Should return False for GitHub workflow files."""
        assert is_meaningful_file(".github/workflows/test.yml") is False
        assert is_meaningful_file(".github/ISSUE_TEMPLATE.md") is False

    def test_returns_false_for_pycache(self) -> None:
        """Should return False for __pycache__ files."""
        assert is_meaningful_file("__pycache__/module.pyc") is False
        assert is_meaningful_file("src/__pycache__/utils.pyc") is False

    def test_returns_false_for_pyc_files(self) -> None:
        """Should return False for .pyc files."""
        assert is_meaningful_file("module.pyc") is False
        assert is_meaningful_file("src/utils.pyc") is False

    def test_returns_false_for_gitignore(self) -> None:
        """Should return False for .gitignore."""
        assert is_meaningful_file(".gitignore") is False

    def test_returns_false_for_conftest(self) -> None:
        """Should return False for conftest.py."""
        assert is_meaningful_file("conftest.py") is False

    def test_returns_false_for_claude_directory(self) -> None:
        """Should return False for .claude/ directory files."""
        assert is_meaningful_file(".claude/rules/custom.md") is False
        assert is_meaningful_file(".claude/disabled-hooks") is False

    def test_returns_false_for_other_markdown_files(self) -> None:
        """Should return False for markdown files (except CHANGELOG.md check elsewhere)."""
        assert is_meaningful_file("README.md") is False
        assert is_meaningful_file("docs/guide.md") is False
        assert is_meaningful_file("CONTRIBUTING.md") is False

    def test_returns_false_for_changelog(self) -> None:
        """Should return False for CHANGELOG.md (checked separately)."""
        assert is_meaningful_file("CHANGELOG.md") is False

    def test_handles_empty_string(self) -> None:
        """Should handle empty string gracefully."""
        assert is_meaningful_file("") is False

    def test_handles_relative_paths(self) -> None:
        """Should handle relative paths correctly."""
        assert is_meaningful_file("./hooks/new.py") is True
        assert is_meaningful_file("./tests/test.py") is False

    def test_handles_absolute_paths(self) -> None:
        """Should handle absolute paths correctly."""
        assert is_meaningful_file("/home/user/project/hooks/hook.py") is True
        assert is_meaningful_file("/home/user/project/tests/test.py") is False


# =============================================================================
# Tests for get_staged_files()
# =============================================================================


class TestGetStagedFiles:
    """Test get_staged_files() function."""

    def test_returns_staged_files_on_success(self) -> None:
        """Should return list of staged files when git command succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "hooks/new-hook.py\nREADME.md\ntests/test.py\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = get_staged_files()

            assert result == ["hooks/new-hook.py", "README.md", "tests/test.py"]
            mock_run.assert_called_once_with(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                timeout=5,
            )

    def test_returns_empty_list_on_git_error(self) -> None:
        """Should return empty list when git command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files()
            assert result == []

    def test_returns_empty_list_on_timeout(self) -> None:
        """Should return empty list when git command times out."""
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)
        ):
            result = get_staged_files()
            assert result == []

    def test_returns_empty_list_on_file_not_found(self) -> None:
        """Should return empty list when git is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = get_staged_files()
            assert result == []

    def test_returns_empty_list_on_os_error(self) -> None:
        """Should return empty list on OS errors."""
        with patch("subprocess.run", side_effect=OSError):
            result = get_staged_files()
            assert result == []

    def test_strips_whitespace_from_filenames(self) -> None:
        """Should strip whitespace from filenames."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  hooks/new.py  \n  README.md\n"

        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files()
            assert result == ["hooks/new.py", "README.md"]

    def test_handles_empty_git_output(self) -> None:
        """Should handle empty output from git diff."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files()
            assert result == []

    def test_filters_empty_lines(self) -> None:
        """Should filter out empty lines from output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "hooks/new.py\n\n\nREADME.md\n"

        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files()
            assert result == ["hooks/new.py", "README.md"]


# =============================================================================
# Tests for is_changelog_staged()
# =============================================================================


class TestIsChangelogStaged:
    """Test is_changelog_staged() function."""

    def test_returns_true_when_changelog_staged(self) -> None:
        """Should return True when CHANGELOG.md is in staged files."""
        staged_files = ["hooks/new.py", "CHANGELOG.md", "README.md"]
        assert is_changelog_staged(staged_files) is True

    def test_returns_true_with_path_prefix(self) -> None:
        """Should return True when CHANGELOG.md has path prefix."""
        staged_files = ["hooks/new.py", "docs/CHANGELOG.md"]
        assert is_changelog_staged(staged_files) is True

    def test_returns_false_when_changelog_not_staged(self) -> None:
        """Should return False when CHANGELOG.md is not staged."""
        staged_files = ["hooks/new.py", "README.md"]
        assert is_changelog_staged(staged_files) is False

    def test_returns_false_for_empty_list(self) -> None:
        """Should return False for empty staged files list."""
        assert is_changelog_staged([]) is False

    def test_case_sensitive_matching(self) -> None:
        """Should match CHANGELOG.md case-sensitively."""
        # changelog.md (lowercase) should not match
        staged_files = ["changelog.md"]
        assert is_changelog_staged(staged_files) is False

        # CHANGELOG.md (uppercase) should match
        staged_files = ["CHANGELOG.md"]
        assert is_changelog_staged(staged_files) is True

    def test_matches_changelog_anywhere_in_path(self) -> None:
        """Should match CHANGELOG.md in any directory."""
        assert is_changelog_staged(["CHANGELOG.md"]) is True
        assert is_changelog_staged(["docs/CHANGELOG.md"]) is True
        assert is_changelog_staged(["project/docs/CHANGELOG.md"]) is True


# =============================================================================
# Tests for is_git_commit_command()
# =============================================================================


class TestIsGitCommitCommand:
    """Test is_git_commit_command() function."""

    def test_detects_simple_git_commit(self) -> None:
        """Should detect simple git commit command."""
        assert is_git_commit_command("git commit -m 'message'") is True

    def test_detects_git_commit_with_options(self) -> None:
        """Should detect git commit with various options."""
        assert is_git_commit_command("git commit -am 'message'") is True
        assert is_git_commit_command("git commit --amend") is True
        assert is_git_commit_command("git commit -m 'msg' --no-edit") is True

    def test_detects_git_commit_in_chain(self) -> None:
        """Should detect git commit in command chain."""
        assert is_git_commit_command("git add . && git commit -m 'msg'") is True
        assert is_git_commit_command("git status; git commit -m 'msg'") is True

    def test_detects_git_commit_with_whitespace(self) -> None:
        """Should detect git commit with leading/trailing whitespace."""
        assert is_git_commit_command("  git commit -m 'msg'  ") is True

    def test_rejects_non_git_commands(self) -> None:
        """Should reject non-git commands."""
        assert is_git_commit_command("npm install") is False
        assert is_git_commit_command("python script.py") is False

    def test_rejects_other_git_commands(self) -> None:
        """Should reject other git commands."""
        assert is_git_commit_command("git push origin main") is False
        assert is_git_commit_command("git add file.py") is False
        assert is_git_commit_command("git status") is False

    def test_rejects_commit_in_message_text(self) -> None:
        """Should not match 'commit' in message text."""
        # This should not match because we're looking for git commit as a command
        assert is_git_commit_command("git log | grep commit") is False

    def test_handles_empty_string(self) -> None:
        """Should handle empty string gracefully."""
        assert is_git_commit_command("") is False


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_exits_when_skip_changelog_check_env_set(
        self, mock_tool_use: Dict[str, Any]
    ) -> None:
        """Should exit 0 when SKIP_CHANGELOG_CHECK=1 in environment."""
        stdin_data = json.dumps(mock_tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch.dict(os.environ, {"SKIP_CHANGELOG_CHECK": "1"}):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_exits_when_skip_changelog_check_in_command(
        self, mock_tool_use: Dict[str, Any]
    ) -> None:
        """Should exit 0 when SKIP_CHANGELOG_CHECK=1 in command string."""
        mock_tool_use["tool_input"]["command"] = (
            "SKIP_CHANGELOG_CHECK=1 git commit -m 'Add hook'"
        )
        stdin_data = json.dumps(mock_tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_when_skip_changelog_check_inline_in_chain(
        self, mock_tool_use: Dict[str, Any]
    ) -> None:
        """Should exit 0 when SKIP_CHANGELOG_CHECK=1 appears inline in command chain."""
        mock_tool_use["tool_input"]["command"] = (
            "git add . && SKIP_CHANGELOG_CHECK=1 git commit -m 'message'"
        )
        stdin_data = json.dumps(mock_tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_non_bash_tool(
        self, non_bash_tool_use: Dict[str, Any]
    ) -> None:
        """Should exit 0 for non-Bash tool invocations."""
        stdin_data = json.dumps(non_bash_tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_when_not_git_commit(
        self, mock_tool_use: Dict[str, Any]
    ) -> None:
        """Should exit 0 when command is not git commit."""
        mock_tool_use["tool_input"]["command"] = "git status"
        stdin_data = json.dumps(mock_tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_when_no_meaningful_files_staged(
        self, mock_tool_use: Dict[str, Any]
    ) -> None:
        """Should exit 0 when only non-meaningful files are staged."""
        stdin_data = json.dumps(mock_tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch(
                    "changelog_reminder.get_staged_files",
                    return_value=["tests/test.py", ".gitignore"],
                ):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_exits_when_changelog_is_staged(
        self, mock_tool_use: Dict[str, Any]
    ) -> None:
        """Should exit 0 when CHANGELOG.md is staged with meaningful files."""
        stdin_data = json.dumps(mock_tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch(
                    "changelog_reminder.get_staged_files",
                    return_value=["hooks/new.py", "CHANGELOG.md"],
                ):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_blocks_when_meaningful_files_without_changelog(
        self, mock_tool_use: Dict[str, Any], capsys
    ) -> None:
        """Should exit 2 and print error when meaningful files staged without CHANGELOG.md."""
        stdin_data = json.dumps(mock_tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch(
                    "changelog_reminder.get_staged_files",
                    return_value=["hooks/new-hook.py", "hooks/utils.py"],
                ):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Meaningful changes without CHANGELOG.md update!" in captured.err
        assert "hooks/new-hook.py" in captured.err
        assert "hooks/utils.py" in captured.err
        assert "SKIP_CHANGELOG_CHECK=1" in captured.err

    def test_shows_meaningful_files_in_error_message(
        self, mock_tool_use: Dict[str, Any], capsys
    ) -> None:
        """Should show only meaningful files in error message."""
        stdin_data = json.dumps(mock_tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch(
                    "changelog_reminder.get_staged_files",
                    return_value=[
                        "hooks/new.py",
                        "tests/test.py",  # Not meaningful
                        "README.md",       # Not meaningful
                        "src/utils.py",
                    ],
                ):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        # Should show meaningful files
        assert "hooks/new.py" in captured.err
        assert "src/utils.py" in captured.err
        # Should not show non-meaningful files
        assert "tests/test.py" not in captured.err
        assert "README.md" not in captured.err

    def test_exits_successfully_on_exception(
        self, mock_tool_use: Dict[str, Any]
    ) -> None:
        """Should exit 0 on unexpected exceptions (silent failure)."""
        stdin_data = json.dumps(mock_tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", side_effect=Exception("Unexpected")):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_malformed_json(self) -> None:
        """Should exit 0 when stdin contains malformed JSON."""
        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value="not valid json"):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_missing_tool_input(self) -> None:
        """Should exit 0 when tool_input is missing from JSON."""
        tool_use = {"tool_name": "Bash"}  # Missing tool_input
        stdin_data = json.dumps(tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_missing_command(self) -> None:
        """Should exit 0 when command is missing from tool_input."""
        tool_use = {"tool_name": "Bash", "tool_input": {}}
        stdin_data = json.dumps(tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow_commit_with_hook_and_changelog(self) -> None:
        """Test complete workflow: committing hook with CHANGELOG.md."""
        tool_use = {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'Add new hook'"},
        }
        stdin_data = json.dumps(tool_use)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "hooks/new-hook.py\nCHANGELOG.md\n"

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch("subprocess.run", return_value=mock_result):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_full_workflow_commit_hook_without_changelog(
        self, capsys
    ) -> None:
        """Test complete workflow: committing hook without CHANGELOG.md."""
        tool_use = {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'Add new hook'"},
        }
        stdin_data = json.dumps(tool_use)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "hooks/new-hook.py\nREADME.md\n"

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch("subprocess.run", return_value=mock_result):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "hooks/new-hook.py" in captured.err

    def test_full_workflow_commit_tests_only(self) -> None:
        """Test complete workflow: committing only test files."""
        tool_use = {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'Add tests'"},
        }
        stdin_data = json.dumps(tool_use)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "tests/test_new.py\ntests/conftest.py\n"

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch("subprocess.run", return_value=mock_result):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_full_workflow_with_bypass_flag(self) -> None:
        """Test complete workflow: using bypass flag."""
        tool_use = {
            "tool_name": "Bash",
            "tool_input": {
                "command": "SKIP_CHANGELOG_CHECK=1 git commit -m 'Add hook'"
            },
        }
        stdin_data = json.dumps(tool_use)

        with patch("changelog_reminder.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        # Should bypass without calling git
        assert exc_info.value.code == 0
