#!/usr/bin/env python3
"""
Comprehensive tests for python-uv-enforcer hook.

Tests main() function and various Python tool detection scenarios.
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
    "python_uv_enforcer", hooks_dir / "python-uv-enforcer.py"
)
python_uv_enforcer = importlib.util.module_from_spec(spec)
sys.modules["python_uv_enforcer"] = python_uv_enforcer
spec.loader.exec_module(python_uv_enforcer)

main = python_uv_enforcer.main


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_blocks_pip_install(self, capsys) -> None:
        """Should block pip install commands."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "pip install requests"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Direct Python tool usage detected" in captured.err
        assert "uv pip install" in captured.err

    def test_blocks_pip3_install(self, capsys) -> None:
        """Should block pip3 install commands."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "pip3 install numpy"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "uv pip install" in captured.err

    def test_blocks_python_command(self, capsys) -> None:
        """Should block python command execution."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "python script.py"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "uv run python" in captured.err

    def test_blocks_python3_command(self, capsys) -> None:
        """Should block python3 command execution."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "python3 script.py"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "uv run python" in captured.err

    def test_blocks_pytest_command(self, capsys) -> None:
        """Should block pytest command execution."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "uv run pytest" in captured.err

    def test_blocks_black_command(self, capsys) -> None:
        """Should block black command execution."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "black ."}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "uv run black" in captured.err

    def test_blocks_mypy_command(self, capsys) -> None:
        """Should block mypy command execution."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "mypy src/"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "uv run mypy" in captured.err

    def test_allows_uv_commands(self) -> None:
        """Should allow uv commands to pass through."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "uv pip install requests"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_allows_uv_run_commands(self) -> None:
        """Should allow uv run commands to pass through."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "uv run pytest tests/"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_allows_python_venv_creation(self) -> None:
        """Should allow python -m venv commands."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m venv .venv"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_allows_non_python_commands(self) -> None:
        """Should allow non-Python commands."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git status"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_exits_for_non_bash_tool(self) -> None:
        """Should exit 0 for non-Bash tool invocations."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"}
        }

        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', return_value=input_data):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_exits_successfully_on_exception(self) -> None:
        """Should exit 0 on unexpected exceptions (silent failure)."""
        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=Exception("Unexpected error")):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_handles_malformed_json(self) -> None:
        """Should exit 0 when stdin contains malformed JSON."""
        with patch('python_uv_enforcer.exit_if_disabled'):
            with patch('sys.stdin', MagicMock()):
                with patch('json.load', side_effect=json.JSONDecodeError("msg", "doc", 0)):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
