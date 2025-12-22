#!/usr/bin/env python3
"""
Comprehensive tests for large-file-awareness hook.

Tests:
- get_large_file_threshold() configuration priority
- File discovery (git and non-git)
- File analysis and sorting
- Tool recommendations
- Output formatting
- Edge cases
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import using importlib for hyphenated name
hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "large_file_awareness", hooks_dir / "large-file-awareness.py"
)
large_file_awareness = importlib.util.module_from_spec(spec)
sys.modules["large_file_awareness"] = large_file_awareness
spec.loader.exec_module(large_file_awareness)

# Alias for convenience
lfa = large_file_awareness


# =============================================================================
# Tests for get_large_file_threshold() in hook_utils
# =============================================================================


class TestGetLargeFileThreshold:
    """Test get_large_file_threshold() configuration priority."""

    def test_returns_default_when_no_config(self, monkeypatch, tmp_path) -> None:
        """Should return 500 when no configuration is present."""
        # Clear environment
        monkeypatch.delenv("LARGE_FILE_THRESHOLD", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))

        from hook_utils import get_large_file_threshold

        assert get_large_file_threshold() == 500

    def test_reads_from_settings_json(self, monkeypatch, tmp_path) -> None:
        """Should read threshold from ~/.claude/settings.json."""
        # Setup settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"largeFileThreshold": 1000}))

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("LARGE_FILE_THRESHOLD", raising=False)

        from hook_utils import get_large_file_threshold

        assert get_large_file_threshold() == 1000

    def test_reads_from_env_var(self, monkeypatch, tmp_path) -> None:
        """Should read threshold from LARGE_FILE_THRESHOLD env var."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "750")

        from hook_utils import get_large_file_threshold

        assert get_large_file_threshold() == 750

    def test_settings_json_takes_priority_over_env(self, monkeypatch, tmp_path) -> None:
        """Should prioritize settings.json over env var."""
        # Setup settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"largeFileThreshold": 1000}))

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "750")

        from hook_utils import get_large_file_threshold

        assert get_large_file_threshold() == 1000

    def test_handles_malformed_json(self, monkeypatch, tmp_path) -> None:
        """Should fallback to env/default when settings.json is malformed."""
        # Setup malformed settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text("{invalid json")

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "750")

        from hook_utils import get_large_file_threshold

        assert get_large_file_threshold() == 750

    def test_handles_invalid_env_var(self, monkeypatch, tmp_path) -> None:
        """Should fallback to default when env var is invalid."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "not-a-number")

        from hook_utils import get_large_file_threshold

        assert get_large_file_threshold() == 500

    def test_handles_missing_home_env(self, monkeypatch) -> None:
        """Should fallback to env/default when HOME is not set."""
        monkeypatch.delenv("HOME", raising=False)
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "600")

        from hook_utils import get_large_file_threshold

        assert get_large_file_threshold() == 600


# =============================================================================
# Tests for file discovery
# =============================================================================


class TestGetProjectFiles:
    """Test get_project_files() function."""

    def test_uses_git_ls_files_in_git_repo(self, tmp_path, monkeypatch) -> None:
        """Should use git ls-files when in git repository."""
        monkeypatch.chdir(tmp_path)

        # Setup git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        (tmp_path / "file1.py").write_text("code")
        (tmp_path / "file2.js").write_text("code")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)

        files = lfa.get_project_files()

        assert "file1.py" in files
        assert "file2.js" in files

    def test_falls_back_to_walk_when_not_git_repo(self, tmp_path, monkeypatch) -> None:
        """Should use os.walk when not in git repository."""
        monkeypatch.chdir(tmp_path)

        # Create files without git
        (tmp_path / "file1.py").write_text("code")
        (tmp_path / "file2.js").write_text("code")

        files = lfa.get_project_files()

        assert "file1.py" in files
        assert "file2.js" in files

    def test_falls_back_when_git_not_installed(self, tmp_path, monkeypatch) -> None:
        """Should fallback to os.walk when git is not installed."""
        monkeypatch.chdir(tmp_path)

        # Create files
        (tmp_path / "file1.py").write_text("code")

        # Mock git command to raise FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError):
            files = lfa.get_project_files()

        assert "file1.py" in files

    def test_falls_back_on_git_timeout(self, tmp_path, monkeypatch) -> None:
        """Should fallback to os.walk when git command times out."""
        monkeypatch.chdir(tmp_path)

        # Create files
        (tmp_path / "file1.py").write_text("code")

        # Mock git command to timeout
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 2)):
            files = lfa.get_project_files()

        assert "file1.py" in files


class TestWalkWithExcludes:
    """Test walk_with_excludes() function."""

    def test_excludes_standard_directories(self, tmp_path, monkeypatch) -> None:
        """Should exclude standard directories like node_modules, .git, etc."""
        monkeypatch.chdir(tmp_path)

        # Create excluded directories
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "excluded.js").write_text("code")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "excluded").write_text("code")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "excluded.pyc").write_text("code")

        # Create included files
        (tmp_path / "included.py").write_text("code")

        files = lfa.walk_with_excludes()

        assert "included.py" in files
        assert not any("node_modules" in f for f in files)
        assert not any(".git" in f for f in files)
        assert not any("__pycache__" in f for f in files)

    def test_skips_symlinks(self, tmp_path, monkeypatch) -> None:
        """Should skip symlink files."""
        monkeypatch.chdir(tmp_path)

        # Create regular file
        regular = tmp_path / "regular.py"
        regular.write_text("code")

        # Create symlink
        symlink = tmp_path / "symlink.py"
        symlink.symlink_to(regular)

        files = lfa.walk_with_excludes()

        assert "regular.py" in files
        assert "symlink.py" not in files

    def test_returns_relative_paths(self, tmp_path, monkeypatch) -> None:
        """Should return relative paths from cwd."""
        monkeypatch.chdir(tmp_path)

        # Create nested structure
        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "file.py").write_text("code")

        files = lfa.walk_with_excludes()

        # Should be relative path
        assert "src/file.py" in files or "src\\file.py" in files


# =============================================================================
# Tests for tool recommendations
# =============================================================================


class TestRecommendTool:
    """Test recommend_tool() function."""

    def test_recommends_serena_for_code(self) -> None:
        """Should recommend Serena for code files."""
        assert lfa.recommend_tool("code") == "Serena"

    def test_recommends_grep_for_data(self) -> None:
        """Should recommend Grep for data files."""
        assert lfa.recommend_tool("data") == "Grep"

    def test_recommends_read_for_unknown(self) -> None:
        """Should recommend Read offset/limit for unknown files."""
        assert lfa.recommend_tool("unknown") == "Read offset/limit"

    def test_recommends_read_for_text(self) -> None:
        """Should recommend Read offset/limit for text files."""
        # Any non-code, non-data type should get Read recommendation
        assert lfa.recommend_tool("text") == "Read offset/limit"


# =============================================================================
# Tests for file analysis
# =============================================================================


class TestAnalyzeFiles:
    """Test analyze_files() function."""

    def test_identifies_files_above_threshold(
        self, tmp_path, monkeypatch, mock_env
    ) -> None:
        """Should identify files above threshold."""
        monkeypatch.chdir(tmp_path)
        mock_env({"LARGE_FILE_THRESHOLD": "10"})

        # Create files
        small_file = tmp_path / "small.py"
        small_file.write_text("\n" * 5)  # 5 lines

        large_file = tmp_path / "large.py"
        large_file.write_text("\n" * 15)  # 15 lines

        files = ["small.py", "large.py"]
        result = lfa.analyze_files(files)

        assert len(result) == 1
        assert result[0]["path"] == "large.py"
        assert result[0]["lines"] == 15

    def test_sorts_by_line_count_descending(
        self, tmp_path, monkeypatch, mock_env
    ) -> None:
        """Should sort files by line count descending."""
        monkeypatch.chdir(tmp_path)
        mock_env({"LARGE_FILE_THRESHOLD": "10"})

        # Create files with different sizes
        (tmp_path / "medium.py").write_text("\n" * 15)  # 15 lines
        (tmp_path / "huge.py").write_text("\n" * 30)  # 30 lines
        (tmp_path / "large.py").write_text("\n" * 20)  # 20 lines

        files = ["medium.py", "huge.py", "large.py"]
        result = lfa.analyze_files(files)

        assert result[0]["path"] == "huge.py"
        assert result[1]["path"] == "large.py"
        assert result[2]["path"] == "medium.py"

    def test_estimates_tokens_correctly(self, tmp_path, monkeypatch, mock_env) -> None:
        """Should estimate tokens from file content."""
        monkeypatch.chdir(tmp_path)
        mock_env({"LARGE_FILE_THRESHOLD": "1"})

        # Create file with known content (3500 chars = ~1000 tokens)
        large_file = tmp_path / "large.py"
        large_file.write_text("a" * 3500)

        files = ["large.py"]
        result = lfa.analyze_files(files)

        assert result[0]["tokens"] == 1000

    def test_includes_correct_metadata(self, tmp_path, monkeypatch, mock_env) -> None:
        """Should include all required metadata fields."""
        monkeypatch.chdir(tmp_path)
        mock_env({"LARGE_FILE_THRESHOLD": "1"})

        # Create file
        (tmp_path / "file.py").write_text("\n" * 10)

        files = ["file.py"]
        result = lfa.analyze_files(files)

        assert "path" in result[0]
        assert "lines" in result[0]
        assert "tokens" in result[0]
        assert "type" in result[0]
        assert "tool" in result[0]

    def test_skips_binary_files(self, tmp_path, monkeypatch, mock_env) -> None:
        """Should skip binary files."""
        monkeypatch.chdir(tmp_path)
        mock_env({"LARGE_FILE_THRESHOLD": "1"})

        # Create binary file
        binary = tmp_path / "image.png"
        binary.write_bytes(b"\x89PNG" * 1000)  # Large binary file

        files = ["image.png"]
        result = lfa.analyze_files(files)

        assert len(result) == 0

    def test_skips_nonexistent_files(self, tmp_path, monkeypatch, mock_env) -> None:
        """Should skip files that don't exist (race condition)."""
        monkeypatch.chdir(tmp_path)
        mock_env({"LARGE_FILE_THRESHOLD": "1"})

        files = ["nonexistent.py"]
        result = lfa.analyze_files(files)

        assert len(result) == 0

    def test_continues_on_file_error(self, tmp_path, monkeypatch, mock_env) -> None:
        """Should continue processing when individual file errors occur."""
        monkeypatch.chdir(tmp_path)
        mock_env({"LARGE_FILE_THRESHOLD": "1"})

        # Create valid file
        (tmp_path / "valid.py").write_text("\n" * 10)

        files = ["nonexistent.py", "valid.py"]
        result = lfa.analyze_files(files)

        assert len(result) == 1
        assert result[0]["path"] == "valid.py"


# =============================================================================
# Tests for output formatting
# =============================================================================


class TestPrintActionGuidance:
    """Test print_action_guidance() function."""

    def test_shows_serena_guidance_for_code(self, capsys) -> None:
        """Should show Serena guidance when code files present."""
        shown = [{"tool": "Serena", "path": "file.py"}]
        lfa.print_action_guidance(shown)

        captured = capsys.readouterr()
        assert "find_symbol for code" in captured.out

    def test_shows_grep_guidance_for_data(self, capsys) -> None:
        """Should show Grep guidance when data files present."""
        shown = [{"tool": "Grep", "path": "file.json"}]
        lfa.print_action_guidance(shown)

        captured = capsys.readouterr()
        assert "Grep for patterns" in captured.out

    def test_shows_read_guidance_for_text(self, capsys) -> None:
        """Should show Read guidance when text files present."""
        shown = [{"tool": "Read offset/limit", "path": "file.txt"}]
        lfa.print_action_guidance(shown)

        captured = capsys.readouterr()
        assert "Read offset/limit for sections" in captured.out

    def test_shows_multiple_guidance_items(self, capsys) -> None:
        """Should show all relevant guidance when multiple file types present."""
        shown = [
            {"tool": "Serena", "path": "file.py"},
            {"tool": "Grep", "path": "file.json"},
            {"tool": "Read offset/limit", "path": "file.txt"},
        ]
        lfa.print_action_guidance(shown)

        captured = capsys.readouterr()
        assert "find_symbol for code" in captured.out
        assert "Grep for patterns" in captured.out
        assert "Read offset/limit for sections" in captured.out


class TestPrintAwareness:
    """Test print_awareness() function."""

    def test_shows_header(self, capsys, mock_env) -> None:
        """Should show header with file count."""
        mock_env({"LARGE_FILE_THRESHOLD": "500"})

        files = [
            {
                "path": "file.py",
                "lines": 600,
                "tokens": 2000,
                "type": "code",
                "tool": "Serena",
            }
        ]
        lfa.print_awareness(files)

        captured = capsys.readouterr()
        assert "Large Files (symbolic navigation required)" in captured.out

    def test_shows_top_10_files(self, capsys, mock_env) -> None:
        """Should show top 10 files when more than 10 large files exist."""
        mock_env({"LARGE_FILE_THRESHOLD": "500"})

        files = [
            {
                "path": f"file{i}.py",
                "lines": 600 + i,
                "tokens": 2000,
                "type": "code",
                "tool": "Serena",
            }
            for i in range(20)
        ]
        lfa.print_awareness(files)

        captured = capsys.readouterr()

        # Should show first 10 files
        assert "file0.py" in captured.out
        assert "file9.py" in captured.out

        # Should show remainder count
        assert "+10 more files over 500 lines" in captured.out

    def test_shows_file_details(self, capsys, mock_env) -> None:
        """Should show file path, lines, tokens, and tool."""
        mock_env({"LARGE_FILE_THRESHOLD": "500"})

        files = [
            {
                "path": "src/large.py",
                "lines": 1234,
                "tokens": 5678,
                "type": "code",
                "tool": "Serena",
            }
        ]
        lfa.print_awareness(files)

        captured = capsys.readouterr()
        assert "src/large.py" in captured.out
        assert "1234 lines" in captured.out
        assert "5678 tokens" in captured.out
        assert "Serena" in captured.out

    def test_no_remainder_when_10_or_fewer(self, capsys, mock_env) -> None:
        """Should not show remainder when 10 or fewer files."""
        mock_env({"LARGE_FILE_THRESHOLD": "500"})

        files = [
            {
                "path": f"file{i}.py",
                "lines": 600,
                "tokens": 2000,
                "type": "code",
                "tool": "Serena",
            }
            for i in range(5)
        ]
        lfa.print_awareness(files)

        captured = capsys.readouterr()
        assert "+5 more files" not in captured.out
        assert "more files" not in captured.out


# =============================================================================
# Tests for main() function
# =============================================================================


class TestMain:
    """Test main() function."""

    def test_exits_when_hook_disabled(
        self, monkeypatch, temp_project_dir, mock_stdin
    ) -> None:
        """Should exit with 0 when hook is disabled."""
        # Setup disabled hook
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text("large-file-awareness\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        mock_stdin({"hook_event_name": "SessionStart"})

        with pytest.raises(SystemExit) as exc_info:
            lfa.main()

        assert exc_info.value.code == 0

    def test_exits_for_wrong_event_type(self, mock_stdin) -> None:
        """Should exit for non-startup/resume events."""
        mock_stdin({"event": "other"})

        with pytest.raises(SystemExit) as exc_info:
            lfa.main()

        assert exc_info.value.code == 0

    def test_processes_startup_event(
        self, mock_stdin, tmp_path, monkeypatch, capsys
    ) -> None:
        """Should process startup event."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "5")

        # Create large file
        (tmp_path / "large.py").write_text("\n" * 10)

        mock_stdin({"hook_event_name": "SessionStart"})

        with pytest.raises(SystemExit) as exc_info:
            lfa.main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "Large Files" in captured.out
        assert "large.py" in captured.out

    def test_processes_resume_event(
        self, mock_stdin, tmp_path, monkeypatch, capsys
    ) -> None:
        """Should process resume event."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "5")

        # Create large file
        (tmp_path / "large.py").write_text("\n" * 10)

        mock_stdin({"hook_event_name": "SessionStart"})

        with pytest.raises(SystemExit) as exc_info:
            lfa.main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "Large Files" in captured.out
        assert "large.py" in captured.out

    def test_silent_when_no_large_files(
        self, mock_stdin, tmp_path, monkeypatch, capsys
    ) -> None:
        """Should produce no output when no large files."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "500")

        # Create small file
        (tmp_path / "small.py").write_text("\n" * 10)

        mock_stdin({"hook_event_name": "SessionStart"})

        with pytest.raises(SystemExit) as exc_info:
            lfa.main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "Large Files" not in captured.out

    def test_silent_when_empty_project(
        self, mock_stdin, tmp_path, monkeypatch, capsys
    ) -> None:
        """Should produce no output for empty project."""
        monkeypatch.chdir(tmp_path)

        mock_stdin({"hook_event_name": "SessionStart"})

        with pytest.raises(SystemExit) as exc_info:
            lfa.main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "Large Files" not in captured.out

    def test_fails_silently_on_malformed_json(self, monkeypatch) -> None:
        """Should exit with 0 on malformed JSON input."""
        monkeypatch.setattr("sys.stdin.read", lambda: "{invalid json")

        with pytest.raises(SystemExit) as exc_info:
            lfa.main()

        assert exc_info.value.code == 0

    def test_fails_silently_on_exception(self, mock_stdin, monkeypatch) -> None:
        """Should exit with 0 on any unexpected exception."""
        mock_stdin({"hook_event_name": "SessionStart"})

        # Mock get_project_files to raise exception
        with patch.object(
            lfa, "get_project_files", side_effect=Exception("Mock error")
        ):
            with pytest.raises(SystemExit) as exc_info:
                lfa.main()

        assert exc_info.value.code == 0


# =============================================================================
# Integration tests
# =============================================================================


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_full_workflow_git_repo(
        self, tmp_path, monkeypatch, mock_stdin, capsys
    ) -> None:
        """Test complete workflow in git repository."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "10")

        # Setup git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

        # Create files
        (tmp_path / "large_code.py").write_text("\n" * 50)
        (tmp_path / "large_data.json").write_text("\n" * 30)
        (tmp_path / "small.py").write_text("\n" * 5)

        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)

        mock_stdin({"hook_event_name": "SessionStart"})

        with pytest.raises(SystemExit) as exc_info:
            lfa.main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "large_code.py" in captured.out
        assert "large_data.json" in captured.out
        assert "small.py" not in captured.out
        assert "Serena" in captured.out
        assert "Grep" in captured.out

    def test_full_workflow_non_git(
        self, tmp_path, monkeypatch, mock_stdin, capsys
    ) -> None:
        """Test complete workflow without git repository."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "10")

        # Create files without git
        (tmp_path / "large.py").write_text("\n" * 50)
        (tmp_path / "small.py").write_text("\n" * 5)

        # Create excluded directory
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "excluded.js").write_text("\n" * 100)

        mock_stdin({"hook_event_name": "SessionStart"})

        with pytest.raises(SystemExit) as exc_info:
            lfa.main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "large.py" in captured.out
        assert "small.py" not in captured.out
        assert "excluded.js" not in captured.out
