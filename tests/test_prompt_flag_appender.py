#!/usr/bin/env python3
"""
Comprehensive tests for prompt-flag-appender hook.

Tests all functions:
- get_active_mode_fragments()
- split_prompt_and_triggers()
- load_fragments()
- build_prompt()
- main()
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Import using importlib for hyphenated name
import importlib.util

hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "prompt_flag_appender", hooks_dir / "prompt-flag-appender.py"
)
prompt_flag_appender = importlib.util.module_from_spec(spec)
sys.modules["prompt_flag_appender"] = prompt_flag_appender
spec.loader.exec_module(prompt_flag_appender)

get_active_mode_fragments = prompt_flag_appender.get_active_mode_fragments
split_prompt_and_triggers = prompt_flag_appender.split_prompt_and_triggers
load_fragments = prompt_flag_appender.load_fragments
build_prompt = prompt_flag_appender.build_prompt
main = prompt_flag_appender.main
TRIGGER_FILE_MAP = prompt_flag_appender.TRIGGER_FILE_MAP


# =============================================================================
# Tests for get_active_mode_fragments()
# =============================================================================


class TestGetActiveModeFragments:
    """Test get_active_mode_fragments() function."""

    def test_returns_empty_list_when_no_project_dir(self, monkeypatch) -> None:
        """Should return empty list when CLAUDE_PROJECT_DIR not set."""
        monkeypatch.delenv('CLAUDE_PROJECT_DIR', raising=False)
        result = get_active_mode_fragments()
        assert result == []

    def test_returns_empty_list_when_claude_dir_not_exists(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return empty list when .claude directory doesn't exist."""
        (temp_project_dir / '.claude').rmdir()
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))
        result = get_active_mode_fragments()
        assert result == []

    def test_loads_fragment_for_mode_flag_file(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should load fragment when hook-*-mode-on file exists."""
        # Create flag file
        flag_file = temp_project_dir / '.claude' / 'hook-approval-mode-on'
        flag_file.touch()

        # Mock fragment file
        fragment_content = "APPROVAL MODE ACTIVE"
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        with patch.object(Path, 'is_file', return_value=True):
            with patch.object(Path, 'read_text', return_value=fragment_content):
                result = get_active_mode_fragments()

        assert len(result) == 1
        assert result[0] == fragment_content

    def test_skips_mode_without_fragment_file(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should skip modes that don't have corresponding fragment files."""
        # Create flag file
        flag_file = temp_project_dir / '.claude' / 'hook-unknown-mode-on'
        flag_file.touch()

        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        with patch.object(Path, 'is_file', return_value=False):
            result = get_active_mode_fragments()

        assert result == []

    def test_loads_multiple_mode_fragments(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should load fragments for multiple active modes."""
        # Create multiple flag files
        (temp_project_dir / '.claude' / 'hook-approval-mode-on').touch()
        (temp_project_dir / '.claude' / 'hook-ultrathink-mode-on').touch()

        monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(temp_project_dir))

        fragments = ["APPROVAL MODE", "ULTRATHINK MODE"]
        call_count = [0]

        def mock_read_text(encoding=None):
            result = fragments[call_count[0]]
            call_count[0] += 1
            return result

        with patch.object(Path, 'is_file', return_value=True):
            with patch.object(Path, 'read_text', side_effect=mock_read_text):
                result = get_active_mode_fragments()

        assert len(result) == 2
        assert "APPROVAL MODE" in result
        assert "ULTRATHINK MODE" in result


# =============================================================================
# Tests for split_prompt_and_triggers()
# =============================================================================


class TestSplitPromptAndTriggers:
    """Test split_prompt_and_triggers() function."""

    def test_extracts_single_trigger(self) -> None:
        """Should extract single trailing trigger."""
        prompt = "Fix this code +ultrathink"
        base, triggers = split_prompt_and_triggers(prompt)
        assert base == "Fix this code"
        assert triggers == ["+ultrathink"]

    def test_extracts_multiple_triggers(self) -> None:
        """Should extract multiple trailing triggers."""
        prompt = "Fix this code +ultrathink +absolute"
        base, triggers = split_prompt_and_triggers(prompt)
        assert base == "Fix this code"
        assert triggers == ["+ultrathink", "+absolute"]

    def test_ignores_unmapped_triggers(self) -> None:
        """Should ignore triggers not in TRIGGER_FILE_MAP."""
        prompt = "Fix this code +ultrathink +unknown"
        base, triggers = split_prompt_and_triggers(prompt)
        assert base == "Fix this code"
        assert triggers == ["+ultrathink"]

    def test_removes_all_trigger_like_tokens(self) -> None:
        """Should remove all trailing tokens starting with + from output."""
        prompt = "Fix this code +ultrathink +unknown +another"
        base, triggers = split_prompt_and_triggers(prompt)
        assert base == "Fix this code"
        assert "+unknown" not in base
        assert "+another" not in base

    def test_stops_at_non_trigger_token(self) -> None:
        """Should stop extracting when non-trigger token encountered."""
        prompt = "Fix this code quickly +ultrathink"
        base, triggers = split_prompt_and_triggers(prompt)
        assert base == "Fix this code quickly"
        assert triggers == ["+ultrathink"]

    def test_deduplicates_triggers(self) -> None:
        """Should deduplicate repeated triggers while preserving order."""
        prompt = "Fix this code +ultrathink +absolute +ultrathink"
        base, triggers = split_prompt_and_triggers(prompt)
        assert base == "Fix this code"
        assert triggers == ["+ultrathink", "+absolute"]

    def test_handles_prompt_without_triggers(self) -> None:
        """Should return empty triggers list for prompt without triggers."""
        prompt = "Fix this code"
        base, triggers = split_prompt_and_triggers(prompt)
        assert base == "Fix this code"
        assert triggers == []

    def test_handles_empty_prompt(self) -> None:
        """Should handle empty prompt gracefully."""
        prompt = ""
        base, triggers = split_prompt_and_triggers(prompt)
        assert base == ""
        assert triggers == []

    def test_strips_whitespace(self) -> None:
        """Should strip trailing whitespace from base prompt."""
        prompt = "Fix this code  +ultrathink"
        base, triggers = split_prompt_and_triggers(prompt)
        assert base == "Fix this code"
        assert not base.endswith(" ")


# =============================================================================
# Tests for load_fragments()
# =============================================================================


class TestLoadFragments:
    """Test load_fragments() function."""

    def test_loads_single_fragment(self) -> None:
        """Should load single fragment file."""
        fragment_content = "ULTRATHINK MODE ACTIVE"

        with patch.object(Path, 'is_file', return_value=True):
            with patch.object(Path, 'read_text', return_value=fragment_content):
                result = load_fragments(["+ultrathink"])

        assert len(result) == 1
        assert result[0] == fragment_content

    def test_loads_multiple_fragments(self) -> None:
        """Should load multiple fragment files in order."""
        fragments = {
            "ultrathink.md": "ULTRATHINK MODE",
            "absolute.md": "ABSOLUTE MODE",
        }

        def mock_read_text(encoding=None):
            return fragments[Path(prompt_flag_appender.__file__).parent.name]

        with patch.object(Path, 'is_file', return_value=True):
            with patch.object(Path, 'read_text', side_effect=lambda encoding=None: fragments["ultrathink.md"] if "ultrathink" in str(Path) else fragments["absolute.md"]):
                # Mock more carefully
                call_count = [0]
                def mock_read_text_ordered(encoding=None):
                    if call_count[0] == 0:
                        call_count[0] += 1
                        return "ULTRATHINK MODE"
                    else:
                        return "ABSOLUTE MODE"

                with patch.object(Path, 'read_text', side_effect=mock_read_text_ordered):
                    result = load_fragments(["+ultrathink", "+absolute"])

        assert len(result) == 2
        assert "ULTRATHINK MODE" in result
        assert "ABSOLUTE MODE" in result

    def test_skips_nonexistent_files(self) -> None:
        """Should skip triggers without corresponding files."""
        with patch.object(Path, 'is_file', return_value=False):
            result = load_fragments(["+ultrathink"])

        assert result == []

    def test_skips_unmapped_triggers(self) -> None:
        """Should skip triggers not in TRIGGER_FILE_MAP."""
        result = load_fragments(["+unknown"])
        assert result == []

    def test_handles_empty_trigger_list(self) -> None:
        """Should return empty list for empty trigger list."""
        result = load_fragments([])
        assert result == []


# =============================================================================
# Tests for build_prompt()
# =============================================================================


class TestBuildPrompt:
    """Test build_prompt() function."""

    def test_returns_prompt_when_no_fragments(self) -> None:
        """Should return original prompt when no fragments."""
        result = build_prompt("Fix this code", [])
        assert result == "Fix this code"

    def test_appends_single_fragment(self) -> None:
        """Should append single fragment with double newline."""
        result = build_prompt("Fix this code", ["ULTRATHINK MODE"])
        assert result == "Fix this code\n\nULTRATHINK MODE"

    def test_appends_multiple_fragments(self) -> None:
        """Should append multiple fragments with double newlines."""
        result = build_prompt("Fix this code", ["ULTRATHINK MODE", "ABSOLUTE MODE"])
        assert result == "Fix this code\n\nULTRATHINK MODE\n\nABSOLUTE MODE"

    def test_handles_empty_prompt_with_fragments(self) -> None:
        """Should handle empty prompt with fragments."""
        result = build_prompt("", ["ULTRATHINK MODE"])
        assert result == "ULTRATHINK MODE"

    def test_joins_fragments_only_when_no_prompt(self) -> None:
        """Should join fragments with double newline when prompt is empty."""
        result = build_prompt("", ["FRAGMENT1", "FRAGMENT2"])
        assert result == "FRAGMENT1\n\nFRAGMENT2"


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_processes_prompt_with_trigger(self, capsys) -> None:
        """Should process prompt and append fragment."""
        input_data = {"prompt": "Fix this code +ultrathink"}
        fragment_content = "ULTRATHINK MODE"

        with patch('prompt_flag_appender.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with patch('prompt_flag_appender.get_active_mode_fragments', return_value=[]):
                        with patch.object(Path, 'is_file', return_value=True):
                            with patch.object(Path, 'read_text', return_value=fragment_content):
                                main()

        captured = capsys.readouterr()
        assert "Fix this code" in captured.out
        assert "ULTRATHINK MODE" in captured.out

    def test_processes_prompt_without_triggers(self, capsys) -> None:
        """Should return original prompt when no triggers."""
        input_data = {"prompt": "Fix this code"}

        with patch('prompt_flag_appender.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with patch('prompt_flag_appender.get_active_mode_fragments', return_value=[]):
                        main()

        captured = capsys.readouterr()
        assert captured.out.strip() == "Fix this code"

    def test_combines_mode_and_trigger_fragments(self, capsys) -> None:
        """Should combine mode-based and trigger-based fragments."""
        input_data = {"prompt": "Fix this code +ultrathink"}
        mode_fragment = "APPROVAL MODE"
        trigger_fragment = "ULTRATHINK MODE"

        with patch('prompt_flag_appender.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with patch('prompt_flag_appender.get_active_mode_fragments', return_value=[mode_fragment]):
                        with patch.object(Path, 'is_file', return_value=True):
                            with patch.object(Path, 'read_text', return_value=trigger_fragment):
                                main()

        captured = capsys.readouterr()
        assert "APPROVAL MODE" in captured.out
        assert "ULTRATHINK MODE" in captured.out

    def test_handles_json_decode_error(self, capsys) -> None:
        """Should exit 1 and print error on JSON decode error."""
        with patch('prompt_flag_appender.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=json.JSONDecodeError("msg", "doc", 0)):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid JSON input" in captured.err

    def test_handles_non_string_prompt(self, capsys) -> None:
        """Should exit 1 when prompt is not a string."""
        input_data = {"prompt": 123}

        with patch('prompt_flag_appender.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "prompt must be a string" in captured.err

    def test_handles_generic_exception(self, capsys) -> None:
        """Should exit 1 on unexpected exceptions."""
        with patch('prompt_flag_appender.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=Exception("Unexpected error")):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unexpected error" in captured.err
