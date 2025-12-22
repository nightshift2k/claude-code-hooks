#!/usr/bin/env python3
"""
Comprehensive tests for hook_utils module.

Tests all utility functions:
- Colors class methods
- get_hook_name()
- is_hook_disabled()
- exit_if_disabled()
- classify_file()
- estimate_tokens()
- count_lines()
- get_large_file_threshold()
- FilenameMatcher class
- Language enum
- detect_project_languages()
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import hook_utils
import pytest

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
        with patch.object(sys, "argv", ["/path/to/git-safety-check.py"]):
            result = hook_utils.get_hook_name()
            assert result == "git-safety-check"

    def test_handles_path_with_multiple_directories(self) -> None:
        """Should extract name from nested directory paths."""
        with patch.object(sys, "argv", ["/a/b/c/environment-awareness.py"]):
            result = hook_utils.get_hook_name()
            assert result == "environment-awareness"

    def test_handles_relative_path(self) -> None:
        """Should handle relative paths correctly."""
        with patch.object(sys, "argv", ["hooks/doc-update-check.py"]):
            result = hook_utils.get_hook_name()
            assert result == "doc-update-check"


# =============================================================================
# Tests for is_hook_disabled()
# =============================================================================


class TestIsHookDisabled:
    """Test is_hook_disabled() function."""

    def test_returns_false_when_no_claude_project_dir(self, monkeypatch) -> None:
        """Should return False when CLAUDE_PROJECT_DIR is not set."""
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        result = hook_utils.is_hook_disabled("test-hook")
        assert result is False

    def test_returns_false_when_disabled_hooks_file_not_exists(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return False when disabled-hooks file doesn't exist."""
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))
        result = hook_utils.is_hook_disabled("test-hook")
        assert result is False

    def test_returns_true_when_hook_in_disabled_list(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return True when hook is listed in disabled-hooks."""
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text("git-safety-check\npython-uv-enforcer\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        result = hook_utils.is_hook_disabled("git-safety-check")
        assert result is True

    def test_returns_false_when_hook_not_in_disabled_list(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return False when hook is not listed in disabled-hooks."""
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text("git-safety-check\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        result = hook_utils.is_hook_disabled("other-hook")
        assert result is False

    def test_ignores_comments_in_disabled_hooks_file(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should ignore lines starting with # in disabled-hooks."""
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text(
            "# Comment line\ngit-safety-check\n# Another comment\n"
        )
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        result = hook_utils.is_hook_disabled("git-safety-check")
        assert result is True

    def test_ignores_empty_lines_in_disabled_hooks_file(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should ignore empty lines in disabled-hooks."""
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text("\n\ngit-safety-check\n\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        result = hook_utils.is_hook_disabled("git-safety-check")
        assert result is True

    def test_strips_whitespace_from_hook_names(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should strip whitespace from hook names in file."""
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text("  git-safety-check  \n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        result = hook_utils.is_hook_disabled("git-safety-check")
        assert result is True

    def test_returns_false_on_file_read_error(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return False when unable to read disabled-hooks file."""
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text("git-safety-check\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        with patch.object(Path, "open", side_effect=OSError):
            result = hook_utils.is_hook_disabled("git-safety-check")
            assert result is False

    def test_uses_get_hook_name_when_hook_name_is_none(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should use get_hook_name() when hook_name parameter is None."""
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text("test-hook\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        with patch("hook_utils.get_hook_name", return_value="test-hook"):
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
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text("test-hook\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        with pytest.raises(SystemExit) as exc_info:
            hook_utils.exit_if_disabled("test-hook")

        assert exc_info.value.code == 0

    def test_continues_execution_when_hook_not_disabled(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should return normally when hook is not disabled."""
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text("other-hook\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        # Should not raise SystemExit
        hook_utils.exit_if_disabled("test-hook")

    def test_uses_get_hook_name_when_hook_name_is_none(
        self, temp_project_dir, monkeypatch
    ) -> None:
        """Should use get_hook_name() when hook_name parameter is None."""
        disabled_file = temp_project_dir / ".claude" / "disabled-hooks"
        disabled_file.write_text("test-hook\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))

        with patch("hook_utils.get_hook_name", return_value="test-hook"):
            with pytest.raises(SystemExit) as exc_info:
                hook_utils.exit_if_disabled(None)

            assert exc_info.value.code == 0


# =============================================================================
# Tests for get_large_file_threshold()
# =============================================================================


class TestGetLargeFileThreshold:
    """Test get_large_file_threshold() function."""

    def test_returns_default_when_no_config(self, monkeypatch, tmp_path) -> None:
        """Should return 500 when no configuration is present."""
        # Clear environment
        monkeypatch.delenv("LARGE_FILE_THRESHOLD", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))

        assert hook_utils.get_large_file_threshold() == 500

    def test_reads_from_settings_json(self, monkeypatch, tmp_path) -> None:
        """Should read threshold from ~/.claude/settings.json."""
        # Setup settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"largeFileThreshold": 1000}))

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("LARGE_FILE_THRESHOLD", raising=False)

        assert hook_utils.get_large_file_threshold() == 1000

    def test_reads_from_env_var(self, monkeypatch, tmp_path) -> None:
        """Should read threshold from LARGE_FILE_THRESHOLD env var."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "750")

        assert hook_utils.get_large_file_threshold() == 750

    def test_settings_json_takes_priority_over_env(self, monkeypatch, tmp_path) -> None:
        """Should prioritize settings.json over env var."""
        # Setup settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"largeFileThreshold": 1000}))

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "750")

        assert hook_utils.get_large_file_threshold() == 1000

    def test_handles_malformed_json(self, monkeypatch, tmp_path) -> None:
        """Should fallback to env/default when settings.json is malformed."""
        # Setup malformed settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text("{invalid json")

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "750")

        assert hook_utils.get_large_file_threshold() == 750

    def test_handles_invalid_env_var(self, monkeypatch, tmp_path) -> None:
        """Should fallback to default when env var is invalid."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "not-a-number")

        assert hook_utils.get_large_file_threshold() == 500

    def test_handles_missing_home_env(self, monkeypatch) -> None:
        """Should fallback to env/default when HOME is not set."""
        monkeypatch.delenv("HOME", raising=False)
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "600")

        assert hook_utils.get_large_file_threshold() == 600

    def test_handles_missing_threshold_key_in_settings(
        self, monkeypatch, tmp_path
    ) -> None:
        """Should fallback to env/default when settings.json lacks threshold key."""
        # Setup settings.json without largeFileThreshold key
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"otherKey": "value"}))

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "600")

        assert hook_utils.get_large_file_threshold() == 600


# =============================================================================
# Tests for FilenameMatcher class
# =============================================================================


class TestFilenameMatcher:
    """Test FilenameMatcher class for pattern-based filename matching."""

    def test_matches_single_pattern(self) -> None:
        """Should match filename against single pattern."""
        matcher = hook_utils.FilenameMatcher(["*.py"])
        assert matcher.matches("script.py") is True
        assert matcher.matches("file.txt") is False

    def test_matches_multiple_patterns(self) -> None:
        """Should match filename against multiple patterns."""
        matcher = hook_utils.FilenameMatcher(["*.py", "*.js"])
        assert matcher.matches("script.py") is True
        assert matcher.matches("app.js") is True
        assert matcher.matches("doc.md") is False

    def test_matches_with_path(self) -> None:
        """Should match filename in path."""
        matcher = hook_utils.FilenameMatcher(["*.py"])
        assert matcher.matches("/path/to/script.py") is True
        assert matcher.matches("relative/path/file.py") is True

    def test_matches_exact_filename(self) -> None:
        """Should match exact filename pattern."""
        matcher = hook_utils.FilenameMatcher(["Makefile"])
        assert matcher.matches("Makefile") is True
        assert matcher.matches("/path/Makefile") is True
        assert matcher.matches("Makefile.bak") is False

    def test_empty_patterns(self) -> None:
        """Should never match with empty pattern list."""
        matcher = hook_utils.FilenameMatcher([])
        assert matcher.matches("any.file") is False


# =============================================================================
# Tests for Language enum
# =============================================================================


class TestLanguageEnum:
    """Test Language enum and source file pattern matching."""

    def test_python_patterns(self) -> None:
        """Should match Python file patterns."""
        matcher = hook_utils.Language.PYTHON.get_source_fn_matcher()
        assert matcher.matches("script.py") is True
        assert matcher.matches("types.pyi") is True
        assert matcher.matches("notpython.txt") is False

    def test_javascript_patterns(self) -> None:
        """Should match JavaScript file patterns."""
        matcher = hook_utils.Language.JAVASCRIPT.get_source_fn_matcher()
        assert matcher.matches("app.js") is True
        assert matcher.matches("component.jsx") is True
        assert matcher.matches("module.mjs") is True
        assert matcher.matches("common.cjs") is True
        assert matcher.matches("index.ts") is False

    def test_typescript_patterns(self) -> None:
        """Should match TypeScript file patterns."""
        matcher = hook_utils.Language.TYPESCRIPT.get_source_fn_matcher()
        assert matcher.matches("types.ts") is True
        assert matcher.matches("component.tsx") is True
        assert matcher.matches("app.js") is False

    def test_rust_patterns(self) -> None:
        """Should match Rust file patterns."""
        matcher = hook_utils.Language.RUST.get_source_fn_matcher()
        assert matcher.matches("main.rs") is True
        assert matcher.matches("lib.rs") is True
        assert matcher.matches("file.go") is False

    def test_go_patterns(self) -> None:
        """Should match Go file patterns."""
        matcher = hook_utils.Language.GO.get_source_fn_matcher()
        assert matcher.matches("main.go") is True
        assert matcher.matches("handler.go") is True
        assert matcher.matches("file.rs") is False

    def test_experimental_flag(self) -> None:
        """Should have experimental flag set for experimental languages."""
        assert hook_utils.Language.PYTHON.is_experimental is False
        assert hook_utils.Language.TYPESCRIPT.is_experimental is False
        # Assuming MARKDOWN is experimental
        assert hook_utils.Language.MARKDOWN.is_experimental is True

    def test_display_name(self) -> None:
        """Should have proper display names."""
        assert hook_utils.Language.PYTHON.display_name == "Python"
        assert hook_utils.Language.JAVASCRIPT.display_name == "JavaScript"
        assert hook_utils.Language.TYPESCRIPT.display_name == "TypeScript"
        assert hook_utils.Language.CSHARP.display_name == "C#"
        assert hook_utils.Language.CPP.display_name == "C++"


# =============================================================================
# Tests for detect_project_languages()
# =============================================================================


class TestDetectProjectLanguages:
    """Test detect_project_languages() function."""

    def test_detects_python_project(self, tmp_path) -> None:
        """Should detect Python language in project."""
        (tmp_path / "main.py").touch()
        (tmp_path / "utils.py").touch()

        languages = hook_utils.detect_project_languages(str(tmp_path))
        assert hook_utils.Language.PYTHON in languages

    def test_detects_multiple_languages(self, tmp_path) -> None:
        """Should detect multiple languages in project."""
        (tmp_path / "main.py").touch()
        (tmp_path / "app.js").touch()
        (tmp_path / "types.ts").touch()

        languages = hook_utils.detect_project_languages(str(tmp_path))
        assert hook_utils.Language.PYTHON in languages
        assert hook_utils.Language.JAVASCRIPT in languages
        assert hook_utils.Language.TYPESCRIPT in languages

    def test_scans_subdirectories(self, tmp_path) -> None:
        """Should scan subdirectories for language files."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.rs").touch()

        languages = hook_utils.detect_project_languages(str(tmp_path))
        assert hook_utils.Language.RUST in languages

    def test_returns_empty_for_no_code_files(self, tmp_path) -> None:
        """Should return empty list when no code files found."""
        (tmp_path / "README.md").touch()
        (tmp_path / "data.json").touch()

        languages = hook_utils.detect_project_languages(str(tmp_path))
        assert len(languages) == 0

    def test_handles_nonexistent_directory(self) -> None:
        """Should return empty list for nonexistent directory."""
        languages = hook_utils.detect_project_languages("/nonexistent/path")
        assert len(languages) == 0

    def test_ignores_hidden_directories(self, tmp_path) -> None:
        """Should skip hidden directories like .git, .venv, node_modules."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.py").touch()  # Should be ignored

        (tmp_path / "main.py").touch()  # Should be detected

        languages = hook_utils.detect_project_languages(str(tmp_path))
        assert hook_utils.Language.PYTHON in languages
        # We can't verify .git was skipped directly, but main.py should be found

    def test_excludes_experimental_languages(self, tmp_path) -> None:
        """Should exclude experimental languages from detection."""
        (tmp_path / "README.md").touch()
        (tmp_path / "main.py").touch()

        languages = hook_utils.detect_project_languages(str(tmp_path))
        # Markdown should not be in results even if files exist
        assert hook_utils.Language.MARKDOWN not in languages
        assert hook_utils.Language.PYTHON in languages

    def test_handles_symlinks(self, tmp_path) -> None:
        """Should handle symlinks gracefully."""
        real_file = tmp_path / "real.py"
        real_file.touch()
        link = tmp_path / "link.py"
        try:
            link.symlink_to(real_file)
        except OSError:
            pytest.skip("Symlink creation not supported")

        languages = hook_utils.detect_project_languages(str(tmp_path))
        assert hook_utils.Language.PYTHON in languages
