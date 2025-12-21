#!/usr/bin/env python3
"""
Comprehensive tests for git-branch-protection hook.

Tests all functions:
- get_current_branch()
- main()
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import using importlib for hyphenated name
import importlib.util

hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "git_branch_protection", hooks_dir / "git-branch-protection.py"
)
git_branch_protection = importlib.util.module_from_spec(spec)
sys.modules["git_branch_protection"] = git_branch_protection
spec.loader.exec_module(git_branch_protection)

get_current_branch = git_branch_protection.get_current_branch
main = git_branch_protection.main
PROTECTED_BRANCHES = git_branch_protection.PROTECTED_BRANCHES


# =============================================================================
# Tests for get_current_branch()
# =============================================================================


class TestGetCurrentBranch:
    """Test get_current_branch() function."""

    def test_returns_branch_name_on_success(self) -> None:
        """Should return current branch name when git command succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "feature-branch\n"

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            result = get_current_branch()

            assert result == "feature-branch"
            mock_run.assert_called_once_with(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5,
            )

    def test_returns_none_on_git_error(self) -> None:
        """Should return None when git command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch('subprocess.run', return_value=mock_result):
            result = get_current_branch()
            assert result is None

    def test_returns_none_on_timeout(self) -> None:
        """Should return None when git command times out."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("git", 5)):
            result = get_current_branch()
            assert result is None

    def test_returns_none_on_file_not_found(self) -> None:
        """Should return None when git is not installed."""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = get_current_branch()
            assert result is None

    def test_returns_none_on_os_error(self) -> None:
        """Should return None on OS errors."""
        with patch('subprocess.run', side_effect=OSError):
            result = get_current_branch()
            assert result is None

    def test_strips_whitespace_from_branch_name(self) -> None:
        """Should strip whitespace from branch name."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  main  \n"

        with patch('subprocess.run', return_value=mock_result):
            result = get_current_branch()
            assert result == "main"


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_blocks_edit_on_main_branch(self, capsys) -> None:
        """Should exit 2 and print error when on main branch."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch('git_branch_protection.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with patch('git_branch_protection.get_current_branch', return_value='main'):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot edit files on protected branch 'main'" in captured.err
        assert "git checkout -b feature" in captured.err

    def test_blocks_edit_on_master_branch(self, capsys) -> None:
        """Should exit 2 and print error when on master branch."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch('git_branch_protection.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with patch('git_branch_protection.get_current_branch', return_value='master'):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot edit files on protected branch 'master'" in captured.err

    def test_blocks_edit_on_production_branch(self, capsys) -> None:
        """Should exit 2 and print error when on production branch."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch('git_branch_protection.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with patch('git_branch_protection.get_current_branch', return_value='production'):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot edit files on protected branch 'production'" in captured.err

    def test_blocks_edit_on_prod_branch(self, capsys) -> None:
        """Should exit 2 and print error when on prod branch."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch('git_branch_protection.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with patch('git_branch_protection.get_current_branch', return_value='prod'):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot edit files on protected branch 'prod'" in captured.err

    def test_allows_edit_on_feature_branch(self) -> None:
        """Should exit 0 when on feature branch."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch('git_branch_protection.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with patch('git_branch_protection.get_current_branch', return_value='feature/new-ui'):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0

    def test_allows_edit_when_not_in_git_repo(self) -> None:
        """Should exit 0 when not in a git repository."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch('git_branch_protection.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with patch('git_branch_protection.get_current_branch', return_value=None):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0

    def test_exits_successfully_on_exception(self) -> None:
        """Should exit 0 on unexpected exceptions (silent failure)."""
        with patch('git_branch_protection.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=Exception("Unexpected error")):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_handles_malformed_json(self) -> None:
        """Should exit 0 when stdin contains malformed JSON."""
        with patch('git_branch_protection.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=json.JSONDecodeError("msg", "doc", 0)):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_protected_branches_list_is_correct(self) -> None:
        """Should have correct list of protected branches."""
        assert PROTECTED_BRANCHES == ["main", "master", "production", "prod"]
