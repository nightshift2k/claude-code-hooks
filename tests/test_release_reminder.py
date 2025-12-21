#!/usr/bin/env python3
"""
Comprehensive tests for release-reminder hook.

Tests main() function and keyword detection for release-related prompts.
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
    "release_reminder", hooks_dir / "release-reminder.py"
)
release_reminder = importlib.util.module_from_spec(spec)
sys.modules["release_reminder"] = release_reminder
spec.loader.exec_module(release_reminder)

main = release_reminder.main


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_outputs_reminder_on_release_keyword(self, capsys) -> None:
        """Should output reminder when 'release' keyword found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "prepare a new release for version 0.1.4"
        }

        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Release Verification Required" in captured.out
        assert "CHANGELOG.md has version section" in captured.out
        assert "All version files are synchronized" in captured.out
        assert "Working tree is clean" in captured.out

    def test_outputs_reminder_on_tag_v_keyword(self, capsys) -> None:
        """Should output reminder when 'tag v' keyword found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "tag v0.2.0 for the next release"
        }

        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Release Verification Required" in captured.out

    def test_outputs_reminder_on_version_bump_keyword(self, capsys) -> None:
        """Should output reminder when 'version bump' keyword found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "version bump to 1.2.3"
        }

        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Release Verification Required" in captured.out

    def test_outputs_reminder_on_prepare_release_keyword(self, capsys) -> None:
        """Should output reminder when 'prepare release' keyword found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "prepare release for the new feature"
        }

        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Release Verification Required" in captured.out

    def test_outputs_reminder_on_version_pattern_v0_1_dot(self, capsys) -> None:
        """Should output reminder when version pattern like 'v0.1.' found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "update to v0.1.5"
        }

        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Release Verification Required" in captured.out

    def test_outputs_reminder_on_version_pattern_v1_0_dot(self, capsys) -> None:
        """Should output reminder when version pattern like 'v1.0.' found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "tag v1.0.0"
        }

        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Release Verification Required" in captured.out

    def test_does_not_output_reminder_on_non_release_prompt(self, capsys) -> None:
        """Should not output reminder when no release keywords found."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "implement a new feature for user authentication"
        }

        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_does_not_output_reminder_on_question_prompt(self, capsys) -> None:
        """Should not output reminder for question prompts."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "what is the latest version?"
        }

        with patch('release_reminder.exit_if_disabled'):
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
            "prompt": "RELEASE the new version"
        }

        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Release Verification Required" in captured.out

    def test_exits_silently_on_unknown_event(self, capsys) -> None:
        """Should exit silently for unknown event types."""
        input_data = {"hook_event_name": "UnknownEvent"}

        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_exits_successfully_on_exception(self) -> None:
        """Should exit 0 on unexpected exceptions (silent failure)."""
        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=Exception("Unexpected error")):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_handles_malformed_json(self) -> None:
        """Should exit 0 when stdin contains malformed JSON."""
        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=json.JSONDecodeError("msg", "doc", 0)):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_does_not_trigger_on_session_start(self, capsys) -> None:
        """Should not output anything on SessionStart event."""
        input_data = {"hook_event_name": "SessionStart"}

        with patch('release_reminder.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == ""
