#!/usr/bin/env python3
"""
Comprehensive tests for rules-reminder hook.

Tests main() function and trigger keyword detection.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import using importlib for hyphenated name
import importlib.util

hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "rules_reminder", hooks_dir / "rules-reminder.py"
)
rules_reminder = importlib.util.module_from_spec(spec)
sys.modules["rules_reminder"] = rules_reminder
spec.loader.exec_module(rules_reminder)

main = rules_reminder.main
REMINDER = rules_reminder.REMINDER


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_outputs_reminder_on_session_start(self, capsys) -> None:
        """Should output reminder on SessionStart event."""
        input_data = {"hook_event_name": "SessionStart"}

        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Project Rules Reminder" in captured.out
        assert "CLAUDE.md" in captured.out
        assert ".claude/rules/" in captured.out

    def test_outputs_reminder_on_implement_keyword(self, capsys) -> None:
        """Should output reminder when 'implement' keyword found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "implement a new authentication system"
        }

        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Project Rules Reminder" in captured.out

    def test_outputs_reminder_on_fix_keyword(self, capsys) -> None:
        """Should output reminder when 'fix' keyword found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "fix the authentication bug"
        }

        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Project Rules Reminder" in captured.out

    def test_outputs_reminder_on_refactor_keyword(self, capsys) -> None:
        """Should output reminder when 'refactor' keyword found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "refactor the database layer"
        }

        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Project Rules Reminder" in captured.out

    def test_outputs_reminder_on_design_keyword(self, capsys) -> None:
        """Should output reminder when 'design' keyword found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "design a new API endpoint"
        }

        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Project Rules Reminder" in captured.out

    def test_does_not_output_reminder_on_non_trigger_keyword(self, capsys) -> None:
        """Should not output reminder when no trigger keywords found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "what is the weather today?"
        }

        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_does_not_output_reminder_on_explain_prompt(self, capsys) -> None:
        """Should not output reminder for explanation prompts."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "explain how this code works"
        }

        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_case_insensitive_keyword_matching(self, capsys) -> None:
        """Should match keywords case-insensitively."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "IMPLEMENT a new feature"
        }

        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Project Rules Reminder" in captured.out

    def test_exits_silently_on_unknown_event(self, capsys) -> None:
        """Should exit silently for unknown event types."""
        input_data = {"hook_event_name": "UnknownEvent"}

        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_exits_successfully_on_exception(self) -> None:
        """Should exit 0 on unexpected exceptions (silent failure)."""
        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=Exception("Unexpected error")):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_handles_malformed_json(self) -> None:
        """Should exit 0 when stdin contains malformed JSON."""
        with patch('rules_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=json.JSONDecodeError("msg", "doc", 0)):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
