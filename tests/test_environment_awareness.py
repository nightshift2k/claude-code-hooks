#!/usr/bin/env python3
"""
Comprehensive tests for environment-awareness hook.

Tests all functions:
- get_environment_context()
- main()
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import using importlib for hyphenated name
import importlib.util

hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "environment_awareness", hooks_dir / "environment-awareness.py"
)
environment_awareness = importlib.util.module_from_spec(spec)
sys.modules["environment_awareness"] = environment_awareness
spec.loader.exec_module(environment_awareness)

get_environment_context = environment_awareness.get_environment_context
main = environment_awareness.main


# =============================================================================
# Tests for get_environment_context()
# =============================================================================


class TestGetEnvironmentContext:
    """Test get_environment_context() function."""

    def test_returns_formatted_markdown_with_date(self, monkeypatch) -> None:
        """Should include formatted date with day of week."""
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y-%m-%d (%A)": "2025-12-21 (Saturday)",
            "%H:%M %Z": "14:30 PST",
        }[fmt]

        with patch('environment_awareness.datetime') as mock_dt:
            mock_dt.now.return_value.astimezone.return_value = mock_now
            with patch('environment_awareness.platform.system', return_value='Darwin'):
                with patch('environment_awareness.platform.release', return_value='24.0.0'):
                    monkeypatch.setenv('CLAUDE_PROJECT_DIR', '/home/user/project')

                    result = get_environment_context()

        assert "Date: 2025-12-21 (Saturday)" in result
        assert "Time: 14:30 PST" in result

    def test_returns_macos_for_darwin_system(self, monkeypatch) -> None:
        """Should convert Darwin to macOS in output."""
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y-%m-%d (%A)": "2025-12-21 (Saturday)",
            "%H:%M %Z": "14:30 PST",
        }[fmt]

        with patch('environment_awareness.datetime') as mock_dt:
            mock_dt.now.return_value.astimezone.return_value = mock_now
            with patch('environment_awareness.platform.system', return_value='Darwin'):
                with patch('environment_awareness.platform.release', return_value='24.0.0'):
                    monkeypatch.setenv('CLAUDE_PROJECT_DIR', '/home/user/project')

                    result = get_environment_context()

        assert "OS: macOS 24.0.0" in result

    def test_returns_linux_for_linux_system(self, monkeypatch) -> None:
        """Should return Linux as-is in output."""
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y-%m-%d (%A)": "2025-12-21 (Saturday)",
            "%H:%M %Z": "14:30 PST",
        }[fmt]

        with patch('environment_awareness.datetime') as mock_dt:
            mock_dt.now.return_value.astimezone.return_value = mock_now
            with patch('environment_awareness.platform.system', return_value='Linux'):
                with patch('environment_awareness.platform.release', return_value='6.2.0'):
                    monkeypatch.setenv('CLAUDE_PROJECT_DIR', '/home/user/project')

                    result = get_environment_context()

        assert "OS: Linux 6.2.0" in result

    def test_collapses_home_directory_to_tilde(self, monkeypatch) -> None:
        """Should replace home directory with ~ in directory path."""
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y-%m-%d (%A)": "2025-12-21 (Saturday)",
            "%H:%M %Z": "14:30 PST",
        }[fmt]

        home = str(Path.home())
        project_dir = f"{home}/projects/myapp"

        with patch('environment_awareness.datetime') as mock_dt:
            mock_dt.now.return_value.astimezone.return_value = mock_now
            with patch('environment_awareness.platform.system', return_value='Linux'):
                with patch('environment_awareness.platform.release', return_value='6.2.0'):
                    monkeypatch.setenv('CLAUDE_PROJECT_DIR', project_dir)

                    result = get_environment_context()

        assert "Directory: ~/projects/myapp" in result

    def test_does_not_collapse_non_home_directory(self, monkeypatch) -> None:
        """Should not modify paths not under home directory."""
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y-%m-%d (%A)": "2025-12-21 (Saturday)",
            "%H:%M %Z": "14:30 PST",
        }[fmt]

        with patch('environment_awareness.datetime') as mock_dt:
            mock_dt.now.return_value.astimezone.return_value = mock_now
            with patch('environment_awareness.platform.system', return_value='Linux'):
                with patch('environment_awareness.platform.release', return_value='6.2.0'):
                    monkeypatch.setenv('CLAUDE_PROJECT_DIR', '/opt/project')

                    result = get_environment_context()

        assert "Directory: /opt/project" in result

    def test_uses_cwd_when_no_claude_project_dir(self, monkeypatch) -> None:
        """Should use current working directory when CLAUDE_PROJECT_DIR not set."""
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y-%m-%d (%A)": "2025-12-21 (Saturday)",
            "%H:%M %Z": "14:30 PST",
        }[fmt]

        monkeypatch.delenv('CLAUDE_PROJECT_DIR', raising=False)

        with patch('environment_awareness.datetime') as mock_dt:
            mock_dt.now.return_value.astimezone.return_value = mock_now
            with patch('environment_awareness.platform.system', return_value='Linux'):
                with patch('environment_awareness.platform.release', return_value='6.2.0'):
                    with patch('environment_awareness.os.getcwd', return_value='/tmp/test'):
                        result = get_environment_context()

        assert "Directory: /tmp/test" in result

    def test_output_format_is_markdown(self, monkeypatch) -> None:
        """Should format output as markdown with proper headers."""
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y-%m-%d (%A)": "2025-12-21 (Saturday)",
            "%H:%M %Z": "14:30 PST",
        }[fmt]

        with patch('environment_awareness.datetime') as mock_dt:
            mock_dt.now.return_value.astimezone.return_value = mock_now
            with patch('environment_awareness.platform.system', return_value='Linux'):
                with patch('environment_awareness.platform.release', return_value='6.2.0'):
                    monkeypatch.setenv('CLAUDE_PROJECT_DIR', '/tmp/test')

                    result = get_environment_context()

        assert result.startswith("## Environment\n")
        assert "- Date:" in result
        assert "- Time:" in result
        assert "- OS:" in result
        assert "- Directory:" in result


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_exits_when_not_session_start_event(self, capsys) -> None:
        """Should exit 0 without output for non-SessionStart events."""
        input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "test"}

        with patch('environment_awareness.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_outputs_environment_context_for_session_start(self, capsys) -> None:
        """Should output environment context for SessionStart events."""
        input_data = {"hook_event_name": "SessionStart"}

        with patch('environment_awareness.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with patch('environment_awareness.get_environment_context', return_value="## Test Output"):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "## Test Output" in captured.out

    def test_exits_successfully_on_exception(self) -> None:
        """Should exit 0 on unexpected exceptions (silent failure)."""
        with patch('environment_awareness.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=Exception("Unexpected error")):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_handles_malformed_json(self) -> None:
        """Should exit 0 when stdin contains malformed JSON."""
        with patch('environment_awareness.exit_if_disabled'):
            with patch('sys.stdin.read', return_value="not valid json"):
                with patch('json.load', side_effect=json.JSONDecodeError("msg", "doc", 0)):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
