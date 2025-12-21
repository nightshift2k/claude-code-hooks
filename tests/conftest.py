"""Pytest configuration for claude-code-hooks tests."""

import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

# Add hooks directory to path for imports - must happen before pytest collects
hooks_dir = Path(__file__).parent.parent / "hooks"
if str(hooks_dir) not in sys.path:
    sys.path.insert(0, str(hooks_dir))


# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def mock_stdin(monkeypatch):
    """
    Mock sys.stdin.read to return JSON data.

    Usage:
        def test_example(mock_stdin):
            mock_stdin({"tool_name": "Bash", "tool_input": {"command": "ls"}})
            # Test code that reads from stdin
    """
    import json

    def _mock(data: Dict[str, Any]) -> None:
        monkeypatch.setattr('sys.stdin.read', lambda: json.dumps(data))

    return _mock


@pytest.fixture
def mock_subprocess(monkeypatch):
    """
    Mock subprocess.run with configurable return values.

    Usage:
        def test_example(mock_subprocess):
            result = mock_subprocess(returncode=0, stdout='main\n')
            # Test code that uses subprocess.run
            assert result.returncode == 0
    """
    def _mock(returncode: int = 0, stdout: str = '', stderr: str = ''):
        result = MagicMock()
        result.returncode = returncode
        result.stdout = stdout
        result.stderr = stderr
        monkeypatch.setattr('subprocess.run', lambda *a, **kw: result)
        return result

    return _mock


@pytest.fixture
def mock_env(monkeypatch):
    """
    Mock environment variables.

    Usage:
        def test_example(mock_env):
            mock_env({"CLAUDE_PROJECT_DIR": "/tmp/project"})
            # Test code that uses os.environ
    """
    def _mock(env_vars: Dict[str, str]) -> None:
        for k, v in env_vars.items():
            monkeypatch.setenv(k, v)

    return _mock


@pytest.fixture
def temp_project_dir(tmp_path):
    """
    Create a temporary project directory with .claude subdirectory.

    Usage:
        def test_example(temp_project_dir):
            # temp_project_dir is a Path object with .claude/ already created
            (temp_project_dir / ".claude" / "disabled-hooks").write_text("hook-name\n")
    """
    claude_dir = tmp_path / '.claude'
    claude_dir.mkdir()
    return tmp_path
