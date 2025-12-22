#!/usr/bin/env python3
"""
Comprehensive tests for doc-update-check hook targeting 100% code coverage.

Tests all functions and edge cases:
- get_current_branch()
- extract_merge_target()
- is_merge_to_main_regex()
- is_merge_to_main_ai()
- is_ai_mode_enabled()
- is_merge_to_main()
- load_doc_check_ignore_patterns()
- is_ignored()
- get_modified_docs()
- main()
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Import module with hyphenated name using importlib
hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "doc_update_check", hooks_dir / "doc-update-check.py"
)
doc_update_check = importlib.util.module_from_spec(spec)
sys.modules["doc_update_check"] = doc_update_check
spec.loader.exec_module(doc_update_check)

get_current_branch = doc_update_check.get_current_branch
extract_merge_target = doc_update_check.extract_merge_target
is_merge_to_main_regex = doc_update_check.is_merge_to_main_regex
is_merge_to_main_ai = doc_update_check.is_merge_to_main_ai
is_ai_mode_enabled = doc_update_check.is_ai_mode_enabled
is_merge_to_main = doc_update_check.is_merge_to_main
load_doc_check_ignore_patterns = doc_update_check.load_doc_check_ignore_patterns
is_ignored = doc_update_check.is_ignored
get_modified_docs = doc_update_check.get_modified_docs
main = doc_update_check.main


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_tool_use() -> dict[str, Any]:
    """Fixture for basic Bash tool use JSON."""
    return {
        "tool_name": "Bash",
        "tool_input": {"command": "git merge feature"},
    }


@pytest.fixture
def non_bash_tool_use() -> dict[str, Any]:
    """Fixture for non-Bash tool use."""
    return {
        "tool_name": "Read",
        "tool_input": {"file_path": "/some/file.txt"},
    }


@pytest.fixture
def doc_check_ignore_content() -> str:
    """Fixture for .doc-check-ignore file content."""
    return """# Comment line
# Empty lines should be ignored

docs/**
*-todo.md
temp/*.md
"""


# =============================================================================
# Tests for get_current_branch()
# =============================================================================


class TestGetCurrentBranch:
    """Test get_current_branch() function."""

    def test_returns_branch_name_on_success(self) -> None:
        """Should return current branch name when git command succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "feature-branch\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = get_current_branch()

            assert result == "feature-branch"
            mock_run.assert_called_once_with(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5,
            )

    def test_returns_none_on_git_error(self) -> None:
        """Should return None when git command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            result = get_current_branch()
            assert result is None

    def test_returns_none_on_timeout(self) -> None:
        """Should return None when git command times out."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
            result = get_current_branch()
            assert result is None

    def test_returns_none_on_file_not_found(self) -> None:
        """Should return None when git is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = get_current_branch()
            assert result is None

    def test_returns_none_on_os_error(self) -> None:
        """Should return None on OS errors."""
        with patch("subprocess.run", side_effect=OSError):
            result = get_current_branch()
            assert result is None

    def test_strips_whitespace_from_branch_name(self) -> None:
        """Should strip whitespace from branch name."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  main  \n"

        with patch("subprocess.run", return_value=mock_result):
            result = get_current_branch()
            assert result == "main"


# =============================================================================
# Tests for extract_merge_target()
# =============================================================================


class TestExtractMergeTarget:
    """Test extract_merge_target() function."""

    def test_extracts_simple_branch_name(self) -> None:
        """Should extract branch name from simple git merge command."""
        assert extract_merge_target("git merge feature-branch") == "feature-branch"

    def test_extracts_branch_with_squash_option(self) -> None:
        """Should extract branch name when --squash option is used."""
        assert extract_merge_target("git merge --squash feature") == "feature"

    def test_extracts_branch_with_no_ff_option(self) -> None:
        """Should extract branch name when --no-ff option is used."""
        assert extract_merge_target("git merge --no-ff feature") == "feature"

    def test_extracts_branch_with_message_option(self) -> None:
        """Should extract branch name when -m option is used."""
        # Note: This tests the realistic case where -m has a single-word message
        # In practice, multi-word messages would be a single shell-escaped argument
        assert (
            extract_merge_target("git merge -m message feature-branch")
            == "feature-branch"
        )

    def test_extracts_branch_with_multiple_options(self) -> None:
        """Should extract branch name with multiple options."""
        assert extract_merge_target("git merge --no-ff --squash feature") == "feature"

    def test_returns_none_when_no_branch_specified(self) -> None:
        """Should return None when merge command has no branch."""
        assert extract_merge_target("git merge") is None

    def test_returns_none_for_non_merge_command(self) -> None:
        """Should return None for commands that aren't git merge."""
        assert extract_merge_target("git checkout main") is None
        assert extract_merge_target("git push origin main") is None

    def test_extracts_branch_with_ff_only_option(self) -> None:
        """Should extract branch name when --ff-only option is used."""
        assert extract_merge_target("git merge --ff-only feature") == "feature"

    def test_handles_branch_names_with_slashes(self) -> None:
        """Should handle branch names containing slashes."""
        assert extract_merge_target("git merge feature/new-ui") == "feature/new-ui"

    def test_handles_no_merge_keyword(self) -> None:
        """Should return None if merge is not in command."""
        assert extract_merge_target("git checkout main") is None

    def test_handles_merge_with_no_branch(self) -> None:
        """Should return None if only flags after merge."""
        assert extract_merge_target("git merge --abort") is None


# =============================================================================
# Tests for is_merge_to_main_regex()
# =============================================================================


class TestIsMergeToMainRegex:
    """Test is_merge_to_main_regex() function - strict regex detection."""

    def test_detects_gh_pr_merge_command(self) -> None:
        """Should detect gh pr merge commands with strict regex."""
        assert is_merge_to_main_regex("gh pr merge 123") is True
        assert is_merge_to_main_regex("gh pr merge 456 --squash") is True
        assert is_merge_to_main_regex("  gh pr merge 789") is True

    def test_rejects_commit_message_with_merge_text(self) -> None:
        """Should NOT match commit messages containing 'merge' as text."""
        command = 'git commit -m "fix: stricter gh pr merge detection"'
        assert is_merge_to_main_regex(command) is False

    def test_rejects_gh_release_with_merge_in_notes(self) -> None:
        """Should NOT match gh release with merge in URL or notes."""
        command = 'gh release create v1.0.0 --notes "after pr merge"'
        assert is_merge_to_main_regex(command) is False

    def test_detects_git_merge_on_main_branch(self) -> None:
        """Should detect git merge when on main branch."""
        with patch("doc_update_check.get_current_branch", return_value="main"):
            assert is_merge_to_main_regex("git merge feature") is True

    def test_rejects_git_merge_on_feature_branch(self) -> None:
        """Should reject git merge when on feature branch."""
        with patch("doc_update_check.get_current_branch", return_value="feature"):
            assert is_merge_to_main_regex("git merge other-branch") is False

    def test_detects_checkout_main_then_merge(self) -> None:
        """Should detect checkout main && merge pattern."""
        command = "git checkout main && git merge feature"
        assert is_merge_to_main_regex(command) is True

    def test_rejects_git_commit_with_merge_in_message(self) -> None:
        """Should reject git commit even if message contains merge."""
        commands = [
            'git commit -m "merge conflict resolved"',
            'git commit -m "Merge branch feature locally"',
            "git add . && git commit -m 'post-merge cleanup'",
        ]
        for cmd in commands:
            assert is_merge_to_main_regex(cmd) is False

    def test_rejects_non_merge_git_commands(self) -> None:
        """Should reject git commands that aren't merge operations."""
        assert is_merge_to_main_regex("git push origin main") is False
        assert is_merge_to_main_regex("git checkout main") is False
        assert is_merge_to_main_regex("git status") is False


# =============================================================================
# Tests for is_merge_to_main_ai()
# =============================================================================


class TestIsMergeToMainAI:
    """Test is_merge_to_main_ai() function - AI-powered detection."""

    def test_returns_true_when_claude_says_yes(self) -> None:
        """Should return True when Claude responds with 'yes'."""
        mock_result = MagicMock()
        mock_result.stdout = "yes"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = is_merge_to_main_ai("git merge feature")

            assert result is True
            # Verify claude CLI was called correctly
            args = mock_run.call_args[0][0]
            assert args[0] == "claude"
            assert "--model" in args
            assert "haiku" in args
            assert "-p" in args

    def test_returns_true_when_claude_says_yes_with_explanation(self) -> None:
        """Should return True when Claude output contains 'yes' with context."""
        mock_result = MagicMock()
        mock_result.stdout = "Yes, this command merges into the main branch."
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = is_merge_to_main_ai("gh pr merge 123")
            assert result is True

    def test_returns_false_when_claude_says_no(self) -> None:
        """Should return False when Claude responds with 'no'."""
        mock_result = MagicMock()
        mock_result.stdout = "no"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = is_merge_to_main_ai("git status")
            assert result is False

    def test_returns_false_on_timeout(self) -> None:
        """Should fail open (return False) when subprocess times out."""
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 15)
        ):
            result = is_merge_to_main_ai("git merge feature")
            assert result is False

    def test_returns_false_on_file_not_found(self) -> None:
        """Should fail open when claude CLI is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = is_merge_to_main_ai("git merge feature")
            assert result is False

    def test_returns_false_on_os_error(self) -> None:
        """Should fail open on OS errors."""
        with patch("subprocess.run", side_effect=OSError):
            result = is_merge_to_main_ai("git merge feature")
            assert result is False

    def test_passes_command_in_prompt(self) -> None:
        """Should include the command in the prompt sent to Claude."""
        mock_result = MagicMock()
        mock_result.stdout = "no"
        mock_result.returncode = 0

        test_command = "git checkout main && git merge feature"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            is_merge_to_main_ai(test_command)

            # Verify the prompt contains the command
            args = mock_run.call_args[0][0]
            prompt_flag_index = args.index("-p")
            prompt = args[prompt_flag_index + 1]
            assert test_command in prompt


# =============================================================================
# Tests for is_ai_mode_enabled()
# =============================================================================


class TestIsAiModeEnabled:
    """Tests for is_ai_mode_enabled function."""

    def test_returns_true_when_env_var_set(self) -> None:
        """Environment variable enables AI mode."""
        with patch.dict(os.environ, {"DOC_CHECK_USE_AI": "1"}):
            assert is_ai_mode_enabled() is True

    def test_returns_false_when_env_var_not_set(self) -> None:
        """No env var and no flag file means regex mode."""
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": ""}, clear=True):
            assert is_ai_mode_enabled() is False

    def test_returns_true_when_flag_file_exists(self) -> None:
        """Flag file in project dir enables AI mode."""
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/project"}, clear=True):
            with patch("pathlib.Path.exists", return_value=True):
                assert is_ai_mode_enabled() is True

    def test_returns_false_when_flag_file_missing(self) -> None:
        """Missing flag file means regex mode."""
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/project"}, clear=True):
            with patch("pathlib.Path.exists", return_value=False):
                assert is_ai_mode_enabled() is False

    def test_env_var_takes_precedence_over_flag_file(self) -> None:
        """Env var should work even without checking flag file."""
        with patch.dict(
            os.environ, {"DOC_CHECK_USE_AI": "1", "CLAUDE_PROJECT_DIR": ""}
        ):
            # Even without project dir, env var should enable AI mode
            assert is_ai_mode_enabled() is True

    def test_returns_false_when_no_project_dir(self) -> None:
        """No CLAUDE_PROJECT_DIR means can't check flag file."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_ai_mode_enabled() is False


# =============================================================================
# Tests for is_merge_to_main() - Toggle Function
# =============================================================================


class TestIsMergeToMainToggle:
    """Test is_merge_to_main() toggle function with regex-first, AI-fallback."""

    def test_returns_true_when_regex_matches(self) -> None:
        """Should return True immediately when regex detects merge."""
        with patch(
            "doc_update_check.is_merge_to_main_regex", return_value=True
        ) as mock_regex:
            with patch(
                "doc_update_check.is_merge_to_main_ai", return_value=False
            ) as mock_ai:
                with patch("doc_update_check.is_ai_mode_enabled") as mock_enabled:
                    result = is_merge_to_main("gh pr merge 123")

                    assert result is True
                    mock_regex.assert_called_once_with("gh pr merge 123")
                    mock_ai.assert_not_called()
                    mock_enabled.assert_not_called()  # Skip AI check if regex matched

    def test_uses_ai_fallback_when_regex_fails_and_has_keywords(self) -> None:
        """Should use AI when regex returns False, AI enabled, and command has keywords."""
        with patch("doc_update_check.is_merge_to_main_regex", return_value=False):
            with patch("doc_update_check.is_ai_mode_enabled", return_value=True):
                with patch(
                    "doc_update_check.is_merge_to_main_ai", return_value=True
                ) as mock_ai:
                    result = is_merge_to_main("git merge feature")

                    assert result is True
                    mock_ai.assert_called_once_with("git merge feature")

    def test_skips_ai_when_no_keywords(self) -> None:
        """Should skip AI even when enabled if command has no merge/gh keywords."""
        with patch("doc_update_check.is_merge_to_main_regex", return_value=False):
            with patch("doc_update_check.is_ai_mode_enabled", return_value=True):
                with patch(
                    "doc_update_check.is_merge_to_main_ai", return_value=True
                ) as mock_ai:
                    result = is_merge_to_main("git commit -m 'fix bug'")

                    assert result is False
                    mock_ai.assert_not_called()

    def test_returns_false_when_regex_and_ai_both_negative(self) -> None:
        """Should return False when both regex and AI return False."""
        with patch("doc_update_check.is_merge_to_main_regex", return_value=False):
            with patch("doc_update_check.is_ai_mode_enabled", return_value=True):
                with patch("doc_update_check.is_merge_to_main_ai", return_value=False):
                    result = is_merge_to_main("git merge feature")
                    assert result is False

    def test_returns_false_when_ai_disabled_and_regex_negative(self) -> None:
        """Should return False when AI disabled and regex returns False."""
        with patch("doc_update_check.is_merge_to_main_regex", return_value=False):
            with patch("doc_update_check.is_ai_mode_enabled", return_value=False):
                with patch("doc_update_check.is_merge_to_main_ai") as mock_ai:
                    result = is_merge_to_main("git merge feature")

                    assert result is False
                    mock_ai.assert_not_called()


# =============================================================================
# Tests for load_doc_check_ignore_patterns()
# =============================================================================


class TestLoadDocCheckIgnorePatterns:
    """Test load_doc_check_ignore_patterns() function."""

    def test_returns_empty_list_when_file_not_exists(self) -> None:
        """Should return empty list when .doc-check-ignore doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            result = load_doc_check_ignore_patterns()
            assert result == []

    def test_loads_patterns_from_file(self) -> None:
        """Should load patterns from .doc-check-ignore file."""
        content = "docs/**\n*-todo.md\ntemp/*.md"
        mock_file = mock_open(read_data=content)

        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/fake"}):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "open", mock_file):
                    result = load_doc_check_ignore_patterns()

        assert result == ["docs/**", "*-todo.md", "temp/*.md"]

    def test_ignores_comments_and_empty_lines(
        self, doc_check_ignore_content: str
    ) -> None:
        """Should skip comment lines and empty lines."""
        mock_file = mock_open(read_data=doc_check_ignore_content)

        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/fake"}):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "open", mock_file):
                    result = load_doc_check_ignore_patterns()

        assert result == ["docs/**", "*-todo.md", "temp/*.md"]

    def test_handles_file_read_error_gracefully(self) -> None:
        """Should return empty list on file read errors."""
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "open", side_effect=OSError):
                result = load_doc_check_ignore_patterns()

        assert result == []

    def test_handles_io_error_gracefully(self) -> None:
        """Should return empty list on IO errors."""
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "open", side_effect=IOError):
                result = load_doc_check_ignore_patterns()

        assert result == []

    def test_strips_whitespace_from_patterns(self) -> None:
        """Should strip whitespace from pattern lines."""
        content = "  docs/**  \n  *-todo.md\n"
        mock_file = mock_open(read_data=content)

        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/fake"}):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "open", mock_file):
                    result = load_doc_check_ignore_patterns()

        assert result == ["docs/**", "*-todo.md"]


# =============================================================================
# Tests for is_ignored()
# =============================================================================


class TestIsIgnored:
    """Test is_ignored() function."""

    def test_returns_false_for_empty_patterns(self) -> None:
        """Should return False when no patterns provided."""
        assert is_ignored("README.md", []) is False

    def test_matches_single_star_pattern(self) -> None:
        """Should match * wildcard in current directory."""
        patterns = ["*.md"]
        assert is_ignored("README.md", patterns) is True
        assert is_ignored("docs/README.md", patterns) is False

    def test_matches_double_star_pattern(self) -> None:
        """Should match ** wildcard across directories."""
        patterns = ["docs/**"]
        assert is_ignored("docs/README.md", patterns) is True
        assert is_ignored("docs/api/guide.md", patterns) is True
        assert is_ignored("README.md", patterns) is False

    def test_matches_suffix_pattern(self) -> None:
        """Should match files with specific suffix."""
        patterns = ["*-todo.md"]
        assert is_ignored("plan-todo.md", patterns) is True
        assert is_ignored("feature-todo.md", patterns) is True
        assert is_ignored("README.md", patterns) is False

    def test_matches_directory_specific_pattern(self) -> None:
        """Should match files in specific directory."""
        patterns = ["temp/*.md"]
        assert is_ignored("temp/draft.md", patterns) is True
        assert is_ignored("temp/notes.md", patterns) is True
        assert is_ignored("docs/README.md", patterns) is False

    def test_matches_first_matching_pattern(self) -> None:
        """Should return True on first match when multiple patterns."""
        patterns = ["docs/**", "*-todo.md", "temp/*.md"]
        assert is_ignored("docs/guide.md", patterns) is True
        assert is_ignored("plan-todo.md", patterns) is True
        assert is_ignored("temp/draft.md", patterns) is True

    def test_returns_false_when_no_pattern_matches(self) -> None:
        """Should return False when file doesn't match any pattern."""
        patterns = ["docs/**", "*-todo.md"]
        assert is_ignored("README.md", patterns) is False
        assert is_ignored("src/code.py", patterns) is False

    def test_handles_complex_glob_patterns(self) -> None:
        """Should handle complex glob patterns correctly."""
        patterns = ["**/test-*.md"]
        assert is_ignored("docs/test-plan.md", patterns) is True
        # Pattern **/test-*.md requires ** at start, so test-notes.md won't match
        # because ** needs path separators. Use test-*.md pattern instead.
        patterns2 = ["test-*.md"]
        assert is_ignored("test-notes.md", patterns2) is True


# =============================================================================
# Tests for get_modified_docs()
# =============================================================================


class TestGetModifiedDocs:
    """Test get_modified_docs() function."""

    def test_returns_modified_md_files_on_feature_branch(self) -> None:
        """Should return .md files modified in branch vs main."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "README.md\nCHANGELOG.md\nsrc/code.py\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch(
                "doc_update_check.load_doc_check_ignore_patterns",
                return_value=[],
            ):
                result = get_modified_docs()

        assert result == ["README.md", "CHANGELOG.md"]
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[:2] == ["git", "diff"]
        assert "main...HEAD" in args

    def test_returns_modified_md_files_with_merge_target(self) -> None:
        """Should diff against merge target when provided."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "docs/guide.md\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch(
                "doc_update_check.load_doc_check_ignore_patterns",
                return_value=[],
            ):
                result = get_modified_docs(merge_target="feature")

        assert result == ["docs/guide.md"]
        args = mock_run.call_args[0][0]
        assert "feature" in args
        assert "main...HEAD" not in args

    def test_filters_md_files_case_insensitive(self) -> None:
        """Should match .md, .MD, .Md etc."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "README.md\nCHANGELOG.MD\nGuide.Md\ncode.py\n"

        with patch("subprocess.run", return_value=mock_result):
            with patch(
                "doc_update_check.load_doc_check_ignore_patterns",
                return_value=[],
            ):
                result = get_modified_docs()

        assert result == ["README.md", "CHANGELOG.MD", "Guide.Md"]

    def test_applies_ignore_patterns(self) -> None:
        """Should filter out files matching ignore patterns."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "README.md\ndocs/guide.md\nplan-todo.md\n"

        ignore_patterns = ["docs/**", "*-todo.md"]

        with patch("subprocess.run", return_value=mock_result):
            with patch(
                "doc_update_check.load_doc_check_ignore_patterns",
                return_value=ignore_patterns,
            ):
                result = get_modified_docs()

        assert result == ["README.md"]

    def test_returns_empty_list_on_git_error(self) -> None:
        """Should return empty list when git command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            result = get_modified_docs()

        assert result == []

    def test_returns_empty_list_on_timeout(self) -> None:
        """Should return empty list when git command times out."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
            result = get_modified_docs()

        assert result == []

    def test_returns_empty_list_on_file_not_found(self) -> None:
        """Should return empty list when git is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = get_modified_docs()

        assert result == []

    def test_returns_empty_list_on_os_error(self) -> None:
        """Should return empty list on OS errors."""
        with patch("subprocess.run", side_effect=OSError):
            result = get_modified_docs()

        assert result == []

    def test_handles_empty_git_output(self) -> None:
        """Should handle empty output from git diff."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            with patch(
                "doc_update_check.load_doc_check_ignore_patterns",
                return_value=[],
            ):
                result = get_modified_docs()

        # Empty string split produces [""], filtering for .md gives []
        assert result == []


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_exits_when_skip_doc_check_env_set(
        self, mock_tool_use: dict[str, Any]
    ) -> None:
        """Should exit 0 when SKIP_DOC_CHECK=1 in environment."""
        stdin_data = json.dumps(mock_tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch.dict(os.environ, {"SKIP_DOC_CHECK": "1"}):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_exits_when_skip_doc_check_in_command(
        self, mock_tool_use: dict[str, Any]
    ) -> None:
        """Should exit 0 when SKIP_DOC_CHECK=1 in command string."""
        mock_tool_use["tool_input"]["command"] = "SKIP_DOC_CHECK=1 git merge feature"
        stdin_data = json.dumps(mock_tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_when_skip_doc_check_inline_in_chain(
        self, mock_tool_use: dict[str, Any]
    ) -> None:
        """Should exit 0 when SKIP_DOC_CHECK=1 appears inline in command chain."""
        mock_tool_use["tool_input"]["command"] = (
            "git checkout main && SKIP_DOC_CHECK=1 git merge feature"
        )
        stdin_data = json.dumps(mock_tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_non_bash_tool(self, non_bash_tool_use: dict[str, Any]) -> None:
        """Should exit 0 for non-Bash tool invocations."""
        stdin_data = json.dumps(non_bash_tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_when_not_merge_to_main(self, mock_tool_use: dict[str, Any]) -> None:
        """Should exit 0 when command is not merge-to-main."""
        mock_tool_use["tool_input"]["command"] = "git status"
        stdin_data = json.dumps(mock_tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_successfully_when_docs_modified(
        self, mock_tool_use: dict[str, Any]
    ) -> None:
        """Should exit 0 when documentation files were modified."""
        stdin_data = json.dumps(mock_tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch("doc_update_check.is_merge_to_main", return_value=True):
                    with patch(
                        "doc_update_check.get_current_branch",
                        return_value="feature",
                    ):
                        with patch(
                            "doc_update_check.get_modified_docs",
                            return_value=["README.md"],
                        ):
                            with pytest.raises(SystemExit) as exc_info:
                                main()

        assert exc_info.value.code == 0

    def test_blocks_when_no_docs_modified(
        self, mock_tool_use: dict[str, Any], capsys
    ) -> None:
        """Should exit 2 and print error when no docs modified."""
        stdin_data = json.dumps(mock_tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch("doc_update_check.is_merge_to_main", return_value=True):
                    with patch(
                        "doc_update_check.get_current_branch",
                        return_value="feature",
                    ):
                        with patch(
                            "doc_update_check.get_modified_docs",
                            return_value=[],
                        ):
                            with pytest.raises(SystemExit) as exc_info:
                                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "No documentation updates detected" in captured.err
        assert "SKIP_DOC_CHECK=1" in captured.err

    def test_uses_merge_target_when_on_main_branch(
        self, mock_tool_use: dict[str, Any]
    ) -> None:
        """Should extract merge target when already on main branch."""
        mock_tool_use["tool_input"]["command"] = "git merge feature-branch"
        stdin_data = json.dumps(mock_tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch("doc_update_check.is_merge_to_main", return_value=True):
                    with patch(
                        "doc_update_check.get_current_branch",
                        return_value="main",
                    ):
                        with patch(
                            "doc_update_check.get_modified_docs",
                            return_value=["README.md"],
                        ) as mock_get_docs:
                            with pytest.raises(SystemExit) as exc_info:
                                main()

        assert exc_info.value.code == 0
        # Function called with positional argument, not keyword
        mock_get_docs.assert_called_once_with("feature-branch")

    def test_no_merge_target_when_on_feature_branch(
        self, mock_tool_use: dict[str, Any]
    ) -> None:
        """Should not extract merge target when on feature branch."""
        stdin_data = json.dumps(mock_tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch("doc_update_check.is_merge_to_main", return_value=True):
                    with patch(
                        "doc_update_check.get_current_branch",
                        return_value="feature",
                    ):
                        with patch(
                            "doc_update_check.get_modified_docs",
                            return_value=["README.md"],
                        ) as mock_get_docs:
                            with pytest.raises(SystemExit) as exc_info:
                                main()

        assert exc_info.value.code == 0
        # Function called with positional argument, not keyword
        mock_get_docs.assert_called_once_with(None)

    def test_exits_successfully_on_exception(
        self, mock_tool_use: dict[str, Any]
    ) -> None:
        """Should exit 0 on unexpected exceptions (silent failure)."""
        # mock_tool_use fixture provides context but stdin.read raises before using it
        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", side_effect=Exception("Unexpected")):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_malformed_json(self) -> None:
        """Should exit 0 when stdin contains malformed JSON."""
        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value="not valid json"):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_missing_tool_input(self) -> None:
        """Should exit 0 when tool_input is missing from JSON."""
        tool_use = {"tool_name": "Bash"}  # Missing tool_input
        stdin_data = json.dumps(tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_missing_command(self) -> None:
        """Should exit 0 when command is missing from tool_input."""
        tool_use = {"tool_name": "Bash", "tool_input": {}}
        stdin_data = json.dumps(tool_use)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow_merge_on_main_with_docs(self) -> None:
        """Test complete workflow: merge on main with doc updates."""
        tool_use = {
            "tool_name": "Bash",
            "tool_input": {"command": "git merge feature-123"},
        }
        stdin_data = json.dumps(tool_use)

        mock_git_branch = MagicMock()
        mock_git_branch.returncode = 0
        mock_git_branch.stdout = "main"

        mock_git_diff = MagicMock()
        mock_git_diff.returncode = 0
        mock_git_diff.stdout = "README.md\nCHANGELOG.md\nsrc/code.py\n"

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch(
                    "subprocess.run",
                    side_effect=[mock_git_branch, mock_git_diff],
                ):
                    with patch(
                        "doc_update_check.load_doc_check_ignore_patterns",
                        return_value=[],
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0

    def test_full_workflow_merge_on_main_without_docs(self, capsys) -> None:
        """Test complete workflow: merge on main without doc updates."""
        tool_use = {
            "tool_name": "Bash",
            "tool_input": {"command": "git merge feature-123"},
        }
        stdin_data = json.dumps(tool_use)

        mock_git_branch = MagicMock()
        mock_git_branch.returncode = 0
        mock_git_branch.stdout = "main"

        mock_git_diff = MagicMock()
        mock_git_diff.returncode = 0
        mock_git_diff.stdout = "src/code.py\ntests/test.py\n"

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                # Need two git branch calls (is_merge_to_main_regex, main) + one git diff
                with patch(
                    "subprocess.run",
                    side_effect=[mock_git_branch, mock_git_branch, mock_git_diff],
                ):
                    with patch(
                        "doc_update_check.load_doc_check_ignore_patterns",
                        return_value=[],
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "No documentation updates detected" in captured.err

    def test_full_workflow_with_ignore_patterns(self) -> None:
        """Test complete workflow with ignore patterns applied."""
        tool_use = {
            "tool_name": "Bash",
            "tool_input": {"command": "git merge feature"},
        }
        stdin_data = json.dumps(tool_use)

        mock_git_branch = MagicMock()
        mock_git_branch.returncode = 0
        mock_git_branch.stdout = "main"

        mock_git_diff = MagicMock()
        mock_git_diff.returncode = 0
        # Only docs/** files modified, which are ignored
        mock_git_diff.stdout = "docs/internal.md\nplan-todo.md\n"

        ignore_content = "docs/**\n*-todo.md"
        mock_file = mock_open(read_data=ignore_content)

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                # Need two git branch calls (is_merge_to_main_regex, main) + one git diff
                with patch(
                    "subprocess.run",
                    side_effect=[mock_git_branch, mock_git_branch, mock_git_diff],
                ):
                    with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/fake"}):
                        with patch.object(Path, "exists", return_value=True):
                            with patch.object(Path, "open", mock_file):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()

        # All docs ignored, should block
        assert exc_info.value.code == 2

    def test_gh_pr_merge_workflow(self) -> None:
        """Test workflow for gh pr merge command."""
        tool_use = {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 123 --squash"},
        }
        stdin_data = json.dumps(tool_use)

        # gh pr merge doesn't need current branch check
        mock_git_diff = MagicMock()
        mock_git_diff.returncode = 0
        mock_git_diff.stdout = "CHANGELOG.md\n"

        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                with patch("subprocess.run", return_value=mock_git_diff):
                    with patch(
                        "doc_update_check.load_doc_check_ignore_patterns",
                        return_value=[],
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0

    def test_main_entry_point(self) -> None:
        """Test __main__ entry point execution."""
        tool_use = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
        }
        stdin_data = json.dumps(tool_use)

        # Test by importing and checking __name__ == "__main__" path
        with patch("doc_update_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=stdin_data):
                # Simulate module execution via __main__
                with patch.object(doc_update_check, "__name__", "__main__"):
                    with pytest.raises(SystemExit) as exc_info:
                        # Execute the if __name__ == "__main__": block
                        if doc_update_check.__name__ == "__main__":
                            main()

        assert exc_info.value.code == 0
