#!/usr/bin/env python3
"""
Comprehensive tests for hook_utils module.

Tests all utility functions:
- Colors class methods
- get_hook_name()
- is_hook_disabled()
- exit_if_disabled()
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import hook_utils


# =============================================================================
# Tests for Colors class
# =============================================================================


class TestColors:
    """Test Colors class ANSI color formatting methods."""

    def test_red_formats_text_with_ansi_codes(self) -> None:
        """Should wrap text in red ANSI codes."""
        result = hook_utils.Colors.red("error")
        assert result == "\033[1;31merror\033[0m"

    def test_yellow_formats_text_with_ansi_codes(self) -> None:
        """Should wrap text in yellow ANSI codes."""
        result = hook_utils.Colors.yellow("warning")
        assert result == "\033[1;33mwarning\033[0m"

    def test_green_formats_text_with_ansi_codes(self) -> None:
        """Should wrap text in green ANSI codes."""
        result = hook_utils.Colors.green("success")
        assert result == "\033[1;32msuccess\033[0m"

    def test_blue_formats_text_with_ansi_codes(self) -> None:
        """Should wrap text in blue ANSI codes."""
        result = hook_utils.Colors.blue("info")
        assert result == "\033[1;34minfo\033[0m"

    def test_cyan_formats_text_with_ansi_codes(self) -> None:
        """Should wrap text in cyan ANSI codes."""
        result = hook_utils.Colors.cyan("highlight")
        assert result == "\033[1;36mhighlight\033[0m"

    def test_color_class_constants(self) -> None:
        """Should have correct ANSI code constants."""
        assert hook_utils.Colors.RED == "\033[1;31m"
        assert hook_utils.Colors.YELLOW == "\033[1;33m"
        assert hook_utils.Colors.GREEN == "\033[1;32m"
        assert hook_utils.Colors.BLUE == "\033[1;34m"
        assert hook_utils.Colors.CYAN == "\033[1;36m"
        assert hook_utils.Colors.RESET == "\033[0m"


# =============================================================================
# Tests for get_hook_name()
# =============================================================================


class TestGetHookName:
    """Test get_hook_name() function."""

    def test_returns_hook_name_without_extension(self) -> None:
        """Should return script filename without .py extension."""
        with patch.object(sys, 'argv', ['/path/to/git-safety-check.py']):
            result = hook_utils.get_hook_name()
            assert result == "git-safety-check"

    def test_handles_path_with_multiple_directories(self) -> None:
        """Should extract name from nested directory paths."""
        with patch.object(sys, 'argv', ['/a/b/c/environment-awareness.py']):
            result = hook_utils.get_hook_name()
            assert result == "environment-awareness"

    def test_handles_relative_path(self) -> None:
        """Should handle relative paths correctly."""
        with patch.object(sys, 'argv', ['hooks/doc-update-check.py']):
            result = hook_utils.get_hook_name()
            assert result == "doc-update-check"


# =============================================================================
# Tests for is_hook_disabled()
# =============================================================================


class TestIsHookDisabled:
    """Test is_hook_disabled() function."""

    def test_returns_false_when_no_claude_project_dir(self, monkeypatch) -> None:
        """Should return False when CLAUDE_PROJECT_DIR is not set."""
        monkeypatch.delenv('CLAUDE_PROJECT_DIR', raising=False)
        result = hook_utils.is_hook_disabled('test-hook')
        assert result is False

    def test_returns_false_when_disabled_hooks_file_not_exists(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return False when disabled-hooks file doesn't exist."""
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))
        result = hook_utils.is_hook_disabled('test-hook')
        assert result is False

    def test_returns_true_when_hook_in_disabled_list(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return True when hook is listed in disabled-hooks."""
        disabled_file = temp_project_dir / '.claude' / 'disabled-hooks'
        disabled_file.write_text('git-safety-check\npython-uv-enforcer\n')
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        result = hook_utils.is_hook_disabled('git-safety-check')
        assert result is True

    def test_returns_false_when_hook_not_in_disabled_list(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return False when hook is not listed in disabled-hooks."""
        disabled_file = temp_project_dir / '.claude' / 'disabled-hooks'
        disabled_file.write_text('git-safety-check\n')
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        result = hook_utils.is_hook_disabled('other-hook')
        assert result is False

    def test_ignores_comments_in_disabled_hooks_file(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should ignore lines starting with # in disabled-hooks."""
        disabled_file = temp_project_dir / '.claude' / 'disabled-hooks'
        disabled_file.write_text('# Comment line\ngit-safety-check\n# Another comment\n')
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        result = hook_utils.is_hook_disabled('git-safety-check')
        assert result is True

    def test_ignores_empty_lines_in_disabled_hooks_file(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should ignore empty lines in disabled-hooks."""
        disabled_file = temp_project_dir / '.claude' / 'disabled-hooks'
        disabled_file.write_text('\n\ngit-safety-check\n\n')
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        result = hook_utils.is_hook_disabled('git-safety-check')
        assert result is True

    def test_strips_whitespace_from_hook_names(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should strip whitespace from hook names in file."""
        disabled_file = temp_project_dir / '.claude' / 'disabled-hooks'
        disabled_file.write_text('  git-safety-check  \n')
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        result = hook_utils.is_hook_disabled('git-safety-check')
        assert result is True

    def test_returns_false_on_file_read_error(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return False when unable to read disabled-hooks file."""
        disabled_file = temp_project_dir / '.claude' / 'disabled-hooks'
        disabled_file.write_text('git-safety-check\n')
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        with patch.object(Path, 'open', side_effect=OSError):
            result = hook_utils.is_hook_disabled('git-safety-check')
            assert result is False

    def test_uses_get_hook_name_when_hook_name_is_none(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should use get_hook_name() when hook_name parameter is None."""
        disabled_file = temp_project_dir / '.claude' / 'disabled-hooks'
        disabled_file.write_text('test-hook\n')
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        with patch('hook_utils.get_hook_name', return_value='test-hook'):
            result = hook_utils.is_hook_disabled(None)
            assert result is True


# =============================================================================
# Tests for exit_if_disabled()
# =============================================================================


class TestExitIfDisabled:
    """Test exit_if_disabled() function."""

    def test_exits_with_zero_when_hook_disabled(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should exit with status 0 when hook is disabled."""
        disabled_file = temp_project_dir / '.claude' / 'disabled-hooks'
        disabled_file.write_text('test-hook\n')
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        with pytest.raises(SystemExit) as exc_info:
            hook_utils.exit_if_disabled('test-hook')

        assert exc_info.value.code == 0

    def test_continues_execution_when_hook_not_disabled(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return normally when hook is not disabled."""
        disabled_file = temp_project_dir / '.claude' / 'disabled-hooks'
        disabled_file.write_text('other-hook\n')
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        # Should not raise SystemExit
        hook_utils.exit_if_disabled('test-hook')

    def test_uses_get_hook_name_when_hook_name_is_none(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should use get_hook_name() when hook_name parameter is None."""
        disabled_file = temp_project_dir / '.claude' / 'disabled-hooks'
        disabled_file.write_text('test-hook\n')
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        with patch('hook_utils.get_hook_name', return_value='test-hook'):
            with pytest.raises(SystemExit) as exc_info:
                hook_utils.exit_if_disabled(None)

            assert exc_info.value.code == 0
