#!/usr/bin/env python3
"""
Tests for serena_awareness UserPromptSubmit hook.

Tests detection states:
- Configured project: .git/ + .serena/project.yml with project_name
- Code project: .git/ + code files (no .serena/)
- Not a project: no .git/

Also tests session marker functionality:
- First prompt detection via session markers
- Marker cleanup for stale sessions
"""

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the hook module
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
import serena_awareness


@pytest.fixture
def clean_session_markers(tmp_path, monkeypatch):
    """
    Fixture to use a temporary session markers directory.

    Patches get_session_markers_dir() to return tmp_path for test isolation.
    """
    markers_dir = tmp_path / "hook_serena_awareness_session_markers"
    monkeypatch.setattr(
        serena_awareness, "get_session_markers_dir", lambda: markers_dir
    )
    return markers_dir


# =============================================================================
# Tests for parse_project_name()
# =============================================================================


class TestParseProjectName:
    """Test parse_project_name() YAML parsing without external library."""

    def test_parses_project_name_simple(self, tmp_path) -> None:
        """Should parse simple project_name from YAML."""
        config = tmp_path / "project.yml"
        config.write_text("project_name: my-project\n")

        result = serena_awareness.parse_project_name(str(config))
        assert result == "my-project"

    def test_parses_project_name_with_quotes(self, tmp_path) -> None:
        """Should parse quoted project_name."""
        config = tmp_path / "project.yml"
        config.write_text('project_name: "my-project"\n')

        result = serena_awareness.parse_project_name(str(config))
        assert result == "my-project"

    def test_parses_project_name_with_single_quotes(self, tmp_path) -> None:
        """Should parse single-quoted project_name."""
        config = tmp_path / "project.yml"
        config.write_text("project_name: 'my-project'\n")

        result = serena_awareness.parse_project_name(str(config))
        assert result == "my-project"

    def test_parses_project_name_with_whitespace(self, tmp_path) -> None:
        """Should handle extra whitespace."""
        config = tmp_path / "project.yml"
        config.write_text("  project_name:   my-project  \n")

        result = serena_awareness.parse_project_name(str(config))
        assert result == "my-project"

    def test_parses_project_name_among_other_fields(self, tmp_path) -> None:
        """Should extract project_name from multi-field YAML."""
        config = tmp_path / "project.yml"
        config.write_text(
            """
other_field: value
project_name: test-project
another_field: value2
"""
        )

        result = serena_awareness.parse_project_name(str(config))
        assert result == "test-project"

    def test_returns_none_for_missing_field(self, tmp_path) -> None:
        """Should return None when project_name field missing."""
        config = tmp_path / "project.yml"
        config.write_text("other_field: value\n")

        result = serena_awareness.parse_project_name(str(config))
        assert result is None

    def test_returns_none_for_empty_value(self, tmp_path) -> None:
        """Should return None for empty project_name value."""
        config = tmp_path / "project.yml"
        config.write_text("project_name:\n")

        result = serena_awareness.parse_project_name(str(config))
        assert result is None

    def test_returns_none_for_nonexistent_file(self) -> None:
        """Should return None for nonexistent config file."""
        result = serena_awareness.parse_project_name("/nonexistent/file.yml")
        assert result is None

    def test_handles_malformed_yaml_gracefully(self, tmp_path) -> None:
        """Should return None for malformed YAML without crashing."""
        config = tmp_path / "project.yml"
        config.write_text("project_name: [unclosed bracket\n")

        result = serena_awareness.parse_project_name(str(config))
        # Should fail gracefully, returning None (regex won't match invalid chars)
        assert result is None


# =============================================================================
# Tests for get_project_state()
# =============================================================================


class TestGetProjectState:
    """Test get_project_state() detection logic."""

    def test_detects_configured_project(self, tmp_path, monkeypatch) -> None:
        """Should detect configured Serena project."""
        # Setup .git directory
        (tmp_path / ".git").mkdir()

        # Setup .serena/project.yml with project_name
        serena_dir = tmp_path / ".serena"
        serena_dir.mkdir()
        config = serena_dir / "project.yml"
        config.write_text("project_name: test-project\n")

        # Add a Python file
        (tmp_path / "main.py").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        state = serena_awareness.get_project_state()
        assert state["type"] == "configured"
        assert state["project_name"] == "test-project"
        assert "Python" in state["languages"]

    def test_detects_code_project_without_serena(self, tmp_path, monkeypatch) -> None:
        """Should detect code project without Serena configuration."""
        # Setup .git directory
        (tmp_path / ".git").mkdir()

        # Add code files (no .serena/)
        (tmp_path / "main.py").touch()
        (tmp_path / "app.js").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        state = serena_awareness.get_project_state()
        assert state["type"] == "code_project"
        assert "Python" in state["languages"]
        assert "JavaScript" in state["languages"]

    def test_detects_non_project(self, tmp_path, monkeypatch) -> None:
        """Should detect when directory is not a git project."""
        # No .git directory
        (tmp_path / "README.md").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        state = serena_awareness.get_project_state()
        assert state["type"] == "not_project"

    def test_treats_missing_project_name_as_code_project(
        self, tmp_path, monkeypatch
    ) -> None:
        """Should treat .serena/ without project_name as code project."""
        # Setup .git directory
        (tmp_path / ".git").mkdir()

        # Setup .serena/project.yml WITHOUT project_name
        serena_dir = tmp_path / ".serena"
        serena_dir.mkdir()
        config = serena_dir / "project.yml"
        config.write_text("other_field: value\n")

        # Add code file
        (tmp_path / "main.rs").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        state = serena_awareness.get_project_state()
        assert state["type"] == "code_project"
        assert "Rust" in state["languages"]

    def test_handles_missing_claude_project_dir(self, monkeypatch) -> None:
        """Should return not_project when CLAUDE_PROJECT_DIR not set."""
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        state = serena_awareness.get_project_state()
        assert state["type"] == "not_project"

    def test_handles_symlinked_git_directory(self, tmp_path, monkeypatch) -> None:
        """Should handle symlinked .git directory."""
        # Create real .git directory elsewhere
        real_git = tmp_path / "real_git"
        real_git.mkdir()

        # Create project directory with symlink to .git
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        git_link = project_dir / ".git"
        try:
            git_link.symlink_to(real_git)
        except OSError:
            pytest.skip("Symlink creation not supported")

        # Add code file
        (project_dir / "main.go").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_dir))

        state = serena_awareness.get_project_state()
        assert state["type"] == "code_project"
        assert "Go" in state["languages"]


# =============================================================================
# Tests for format_output()
# =============================================================================


class TestFormatOutput:
    """Test format_output() message generation."""

    def test_formats_configured_project_output(self) -> None:
        """Should format output for configured Serena project."""
        state = {
            "type": "configured",
            "project_name": "claude-code-hooks",
            "languages": ["Python"],
        }

        output = serena_awareness.format_output(state)
        assert "## Serena Project Detected" in output
        assert "claude-code-hooks" in output
        assert "python" in output.lower()
        assert "activate_project" in output

    def test_formats_code_project_output(self) -> None:
        """Should format output for code project without Serena."""
        state = {"type": "code_project", "languages": ["Python", "TypeScript", "Rust"]}

        output = serena_awareness.format_output(state)
        assert "## Code Project Detected" in output
        assert "Python" in output
        assert "TypeScript" in output
        assert "Rust" in output
        assert "onboarding" in output

    def test_returns_empty_for_not_project(self) -> None:
        """Should return empty string for non-project."""
        state = {"type": "not_project"}

        output = serena_awareness.format_output(state)
        assert output == ""

    def test_formats_multiple_languages_correctly(self) -> None:
        """Should format language list with proper separators."""
        state = {"type": "code_project", "languages": ["Python", "JavaScript", "Go"]}

        output = serena_awareness.format_output(state)
        # Should have comma-separated list
        assert "Python, JavaScript, Go" in output


# =============================================================================
# Tests for Session Marker Functions
# =============================================================================


class TestIsFirstPromptInSession:
    """Test is_first_prompt_in_session() session tracking."""

    def test_returns_true_on_first_call(self, clean_session_markers) -> None:
        """Should return True on first prompt for a session."""
        result = serena_awareness.is_first_prompt_in_session("session-abc123")
        assert result is True

    def test_returns_false_on_second_call(self, clean_session_markers) -> None:
        """Should return False on subsequent prompts for same session."""
        serena_awareness.is_first_prompt_in_session("session-xyz789")
        result = serena_awareness.is_first_prompt_in_session("session-xyz789")
        assert result is False

    def test_creates_marker_file(self, clean_session_markers) -> None:
        """Should create marker file for session."""
        serena_awareness.is_first_prompt_in_session("session-marker-test")
        marker = clean_session_markers / "session-marker-test.seen"
        assert marker.exists()

    def test_creates_markers_directory(self, clean_session_markers) -> None:
        """Should create markers directory if it doesn't exist."""
        assert not clean_session_markers.exists()
        serena_awareness.is_first_prompt_in_session("session-new")
        assert clean_session_markers.exists()

    def test_different_sessions_are_independent(self, clean_session_markers) -> None:
        """Should track sessions independently."""
        result1 = serena_awareness.is_first_prompt_in_session("session-1")
        result2 = serena_awareness.is_first_prompt_in_session("session-2")
        result1_again = serena_awareness.is_first_prompt_in_session("session-1")

        assert result1 is True
        assert result2 is True
        assert result1_again is False


class TestCleanupOldSessionMarkers:
    """Test cleanup_old_session_markers() stale marker removal."""

    def test_removes_old_markers(self, clean_session_markers) -> None:
        """Should remove markers older than max age."""
        clean_session_markers.mkdir(parents=True)

        # Create an old marker (10 days ago)
        old_marker = clean_session_markers / "old-session.seen"
        old_marker.touch()
        old_time = time.time() - (10 * 86400)  # 10 days ago
        import os

        os.utime(old_marker, (old_time, old_time))

        # Run cleanup
        serena_awareness.cleanup_old_session_markers("current-session")

        assert not old_marker.exists()

    def test_preserves_current_session(self, clean_session_markers) -> None:
        """Should never delete current session's marker, even if old."""
        clean_session_markers.mkdir(parents=True)

        # Create current session marker (even if it were old)
        current_marker = clean_session_markers / "current-session.seen"
        current_marker.touch()
        old_time = time.time() - (10 * 86400)  # 10 days ago
        import os

        os.utime(current_marker, (old_time, old_time))

        # Run cleanup with current session ID
        serena_awareness.cleanup_old_session_markers("current-session")

        assert current_marker.exists()

    def test_preserves_recent_markers(self, clean_session_markers) -> None:
        """Should not remove markers within max age."""
        clean_session_markers.mkdir(parents=True)

        # Create a recent marker (1 day ago)
        recent_marker = clean_session_markers / "recent-session.seen"
        recent_marker.touch()
        recent_time = time.time() - (1 * 86400)  # 1 day ago
        import os

        os.utime(recent_marker, (recent_time, recent_time))

        # Run cleanup
        serena_awareness.cleanup_old_session_markers("other-session")

        assert recent_marker.exists()

    def test_handles_missing_directory(self, clean_session_markers) -> None:
        """Should not error if markers directory doesn't exist."""
        # Directory doesn't exist
        assert not clean_session_markers.exists()

        # Should not raise
        serena_awareness.cleanup_old_session_markers("any-session")


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Test full hook execution via main()."""

    def test_main_outputs_for_configured_project(
        self, tmp_path, monkeypatch, capsys, clean_session_markers
    ) -> None:
        """Should output detection message for configured project on first prompt."""
        # Setup configured project
        (tmp_path / ".git").mkdir()
        serena_dir = tmp_path / ".serena"
        serena_dir.mkdir()
        config = serena_dir / "project.yml"
        config.write_text("project_name: test-project\n")
        (tmp_path / "main.py").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        # Mock stdin with session_id (UserPromptSubmit format)
        stdin_data = json.dumps({"session_id": "test-session-1", "prompt": "hello"})
        monkeypatch.setattr("sys.stdin.read", lambda: stdin_data)

        # Run main - expect SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            serena_awareness.main()

        assert exc_info.value.code == 0

        # Check output
        captured = capsys.readouterr()
        assert "## Serena Project Detected" in captured.out
        assert "test-project" in captured.out

    def test_main_outputs_for_code_project(
        self, tmp_path, monkeypatch, capsys, clean_session_markers
    ) -> None:
        """Should output detection message for code project on first prompt."""
        # Setup code project
        (tmp_path / ".git").mkdir()
        (tmp_path / "main.rs").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        # Mock stdin with session_id
        stdin_data = json.dumps({"session_id": "test-session-2", "prompt": "hello"})
        monkeypatch.setattr("sys.stdin.read", lambda: stdin_data)

        # Run main - expect SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            serena_awareness.main()

        assert exc_info.value.code == 0

        # Check output
        captured = capsys.readouterr()
        assert "## Code Project Detected" in captured.out
        assert "Rust" in captured.out

    def test_main_silent_for_not_project(
        self, tmp_path, monkeypatch, capsys, clean_session_markers
    ) -> None:
        """Should be silent for non-project directory."""
        # No .git directory
        (tmp_path / "README.md").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        # Mock stdin with session_id
        stdin_data = json.dumps({"session_id": "test-session-3", "prompt": "hello"})
        monkeypatch.setattr("sys.stdin.read", lambda: stdin_data)

        # Run main - expect SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            serena_awareness.main()

        assert exc_info.value.code == 0

        # Check output
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_main_exits_cleanly_on_invalid_json(self, monkeypatch, capsys) -> None:
        """Should exit with status 0 on invalid JSON (fail open)."""
        # Force an exception by providing invalid stdin
        monkeypatch.setattr("sys.stdin.read", lambda: "invalid json")

        # Should not raise exception, should exit 0
        with pytest.raises(SystemExit) as exc_info:
            serena_awareness.main()

        assert exc_info.value.code == 0

    def test_main_exits_cleanly_on_missing_session_id(
        self, monkeypatch, capsys
    ) -> None:
        """Should exit with status 0 when session_id is missing."""
        # Valid JSON but no session_id
        stdin_data = json.dumps({"prompt": "hello"})
        monkeypatch.setattr("sys.stdin.read", lambda: stdin_data)

        # Should exit 0 without output
        with pytest.raises(SystemExit) as exc_info:
            serena_awareness.main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_main_silent_on_second_prompt(
        self, tmp_path, monkeypatch, capsys, clean_session_markers
    ) -> None:
        """Should be silent on second prompt in same session."""
        # Setup configured project
        (tmp_path / ".git").mkdir()
        serena_dir = tmp_path / ".serena"
        serena_dir.mkdir()
        config = serena_dir / "project.yml"
        config.write_text("project_name: test-project\n")
        (tmp_path / "main.py").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        # First prompt - should output
        stdin_data = json.dumps({"session_id": "repeat-session", "prompt": "first"})
        monkeypatch.setattr("sys.stdin.read", lambda: stdin_data)

        with pytest.raises(SystemExit):
            serena_awareness.main()

        first_output = capsys.readouterr()
        assert "## Serena Project Detected" in first_output.out

        # Second prompt - should be silent
        stdin_data = json.dumps({"session_id": "repeat-session", "prompt": "second"})
        monkeypatch.setattr("sys.stdin.read", lambda: stdin_data)

        with pytest.raises(SystemExit):
            serena_awareness.main()

        second_output = capsys.readouterr()
        assert second_output.out == ""

    def test_main_respects_disabled_hooks(
        self, tmp_path, monkeypatch, capsys, clean_session_markers
    ) -> None:
        """Should exit silently when hook is disabled."""
        # Setup project
        (tmp_path / ".git").mkdir()
        (tmp_path / "main.py").touch()

        # Disable the hook
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        disabled_file = claude_dir / "disabled-hooks"
        disabled_file.write_text("serena-awareness\n")

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        # Mock stdin with session_id
        stdin_data = json.dumps({"session_id": "disabled-session", "prompt": "hello"})
        monkeypatch.setattr("sys.stdin.read", lambda: stdin_data)

        # Mock sys.argv to set hook name
        with patch.object(sys, "argv", ["/path/to/serena-awareness.py"]):
            # Should exit without running
            with pytest.raises(SystemExit) as exc_info:
                serena_awareness.main()

            assert exc_info.value.code == 0

        # No output should be produced
        captured = capsys.readouterr()
        assert captured.out == ""


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_handles_permission_error_on_serena_dir(
        self, tmp_path, monkeypatch
    ) -> None:
        """Should handle permission errors gracefully."""
        # Setup project
        (tmp_path / ".git").mkdir()
        serena_dir = tmp_path / ".serena"
        serena_dir.mkdir()

        # Create config but make it unreadable
        config = serena_dir / "project.yml"
        config.write_text("project_name: test\n")
        config.chmod(0o000)

        (tmp_path / "main.py").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        try:
            # Should still detect as code project (fallback behavior)
            state = serena_awareness.get_project_state()
            assert state["type"] in ["configured", "code_project"]
        finally:
            # Restore permissions for cleanup
            config.chmod(0o644)

    def test_handles_empty_project_directory(self, tmp_path, monkeypatch) -> None:
        """Should handle empty project directory."""
        # Only .git, no code files
        (tmp_path / ".git").mkdir()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        state = serena_awareness.get_project_state()
        assert state["type"] == "code_project"
        assert len(state["languages"]) == 0

    def test_handles_very_large_project(self, tmp_path, monkeypatch) -> None:
        """Should handle project with many files efficiently."""
        # Setup .git
        (tmp_path / ".git").mkdir()

        # Create many code files
        for i in range(100):
            (tmp_path / f"file{i}.py").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        # Should complete quickly
        import time

        start = time.time()
        state = serena_awareness.get_project_state()
        elapsed = time.time() - start

        assert state["type"] == "code_project"
        assert "Python" in state["languages"]
        # Should complete in reasonable time (< 1 second)
        assert elapsed < 1.0


# =============================================================================
# Tests for is_aggressive_mode_enabled()
# =============================================================================


class TestIsAggressiveModeEnabled:
    """Test is_aggressive_mode_enabled() flag file and env var detection."""

    def test_disabled_by_default(self, tmp_path, monkeypatch) -> None:
        """Should return False when no flag file or env var exists."""
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.delenv("SERENA_AGGRESSIVE_MODE", raising=False)

        result = serena_awareness.is_aggressive_mode_enabled()
        assert result is False

    def test_enabled_by_env_var(self, tmp_path, monkeypatch) -> None:
        """Should return True when SERENA_AGGRESSIVE_MODE=1."""
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.setenv("SERENA_AGGRESSIVE_MODE", "1")

        result = serena_awareness.is_aggressive_mode_enabled()
        assert result is True

    def test_disabled_by_env_var_other_value(self, tmp_path, monkeypatch) -> None:
        """Should return False when SERENA_AGGRESSIVE_MODE is not '1'."""
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.setenv("SERENA_AGGRESSIVE_MODE", "0")

        result = serena_awareness.is_aggressive_mode_enabled()
        assert result is False

    def test_enabled_by_flag_file(self, tmp_path, monkeypatch) -> None:
        """Should return True when flag file exists."""
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.delenv("SERENA_AGGRESSIVE_MODE", raising=False)

        # Create flag file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        flag_file = claude_dir / "hook-serena-awareness-aggressive-on"
        flag_file.touch()

        result = serena_awareness.is_aggressive_mode_enabled()
        assert result is True

    def test_env_var_takes_precedence_over_flag_file(
        self, tmp_path, monkeypatch
    ) -> None:
        """Should use env var value when both env var and flag file exist."""
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        # Create flag file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        flag_file = claude_dir / "hook-serena-awareness-aggressive-on"
        flag_file.touch()

        # Env var should take precedence (set to 1, should be enabled)
        monkeypatch.setenv("SERENA_AGGRESSIVE_MODE", "1")
        assert serena_awareness.is_aggressive_mode_enabled() is True

    def test_handles_missing_project_dir(self, monkeypatch) -> None:
        """Should return False when CLAUDE_PROJECT_DIR not set."""
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("SERENA_AGGRESSIVE_MODE", raising=False)

        result = serena_awareness.is_aggressive_mode_enabled()
        assert result is False


# =============================================================================
# Tests for format_aggressive_output()
# =============================================================================


class TestFormatAggressiveOutput:
    """Test format_aggressive_output() mandatory message generation."""

    def test_formats_configured_project_aggressively(self) -> None:
        """Should format aggressive output for configured Serena project."""
        state = {
            "type": "configured",
            "project_name": "test-project",
            "languages": ["Python"],
        }

        output = serena_awareness.format_aggressive_output(state)
        assert "## Serena Project Active" in output
        assert "test-project" in output
        assert "<MANDATORY>" in output
        assert "REQUIRED" in output
        assert "find_symbol" in output
        assert "DO NOT" in output
        assert "Grep" in output
        assert "activate_project" in output

    def test_formats_code_project_aggressively(self) -> None:
        """Should format aggressive output for code project."""
        state = {"type": "code_project", "languages": ["TypeScript", "Go"]}

        output = serena_awareness.format_aggressive_output(state)
        assert "## Code Project Detected" in output
        assert "<MANDATORY>" in output
        assert "onboarding" in output
        assert "REQUIRED" in output
        assert "DO NOT" in output

    def test_returns_empty_for_not_project(self) -> None:
        """Should return empty string for non-project."""
        state = {"type": "not_project"}

        output = serena_awareness.format_aggressive_output(state)
        assert output == ""

    def test_contains_anti_rationalization_message(self) -> None:
        """Should contain anti-rationalization pattern."""
        state = {
            "type": "configured",
            "project_name": "test-project",
            "languages": ["Python"],
        }

        output = serena_awareness.format_aggressive_output(state)
        # Check for the anti-rationalization pattern
        assert "Grep is faster" in output or "simple query" in output
        assert "WRONG" in output


# =============================================================================
# Aggressive Mode Integration Tests
# =============================================================================


class TestAggressiveModeIntegration:
    """Test main() with aggressive mode enabled."""

    def test_main_uses_aggressive_output_with_env_var(
        self, tmp_path, monkeypatch, capsys, clean_session_markers
    ) -> None:
        """Should output aggressive message when env var is set."""
        # Setup configured project
        (tmp_path / ".git").mkdir()
        serena_dir = tmp_path / ".serena"
        serena_dir.mkdir()
        config = serena_dir / "project.yml"
        config.write_text("project_name: test-project\n")
        (tmp_path / "main.py").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.setenv("SERENA_AGGRESSIVE_MODE", "1")

        # Mock stdin with session_id
        stdin_data = json.dumps({"session_id": "aggressive-env-session", "prompt": "x"})
        monkeypatch.setattr("sys.stdin.read", lambda: stdin_data)

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            serena_awareness.main()

        assert exc_info.value.code == 0

        # Check aggressive output
        captured = capsys.readouterr()
        assert "## Serena Project Active" in captured.out
        assert "<MANDATORY>" in captured.out
        assert "REQUIRED" in captured.out

    def test_main_uses_aggressive_output_with_flag_file(
        self, tmp_path, monkeypatch, capsys, clean_session_markers
    ) -> None:
        """Should output aggressive message when flag file exists."""
        # Setup configured project
        (tmp_path / ".git").mkdir()
        serena_dir = tmp_path / ".serena"
        serena_dir.mkdir()
        config = serena_dir / "project.yml"
        config.write_text("project_name: test-project\n")
        (tmp_path / "main.py").touch()

        # Create flag file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        flag_file = claude_dir / "hook-serena-awareness-aggressive-on"
        flag_file.touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.delenv("SERENA_AGGRESSIVE_MODE", raising=False)

        # Mock stdin with session_id
        stdin_data = json.dumps(
            {"session_id": "aggressive-flag-session", "prompt": "x"}
        )
        monkeypatch.setattr("sys.stdin.read", lambda: stdin_data)

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            serena_awareness.main()

        assert exc_info.value.code == 0

        # Check aggressive output
        captured = capsys.readouterr()
        assert "<MANDATORY>" in captured.out

    def test_main_uses_normal_output_without_flag(
        self, tmp_path, monkeypatch, capsys, clean_session_markers
    ) -> None:
        """Should output normal message when aggressive mode disabled."""
        # Setup configured project
        (tmp_path / ".git").mkdir()
        serena_dir = tmp_path / ".serena"
        serena_dir.mkdir()
        config = serena_dir / "project.yml"
        config.write_text("project_name: test-project\n")
        (tmp_path / "main.py").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.delenv("SERENA_AGGRESSIVE_MODE", raising=False)

        # Mock stdin with session_id
        stdin_data = json.dumps({"session_id": "normal-mode-session", "prompt": "x"})
        monkeypatch.setattr("sys.stdin.read", lambda: stdin_data)

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            serena_awareness.main()

        assert exc_info.value.code == 0

        # Check normal output (not aggressive)
        captured = capsys.readouterr()
        assert "## Serena Project Detected" in captured.out
        assert "<MANDATORY>" not in captured.out
