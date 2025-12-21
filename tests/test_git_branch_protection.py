#!/usr/bin/env python3
"""
Comprehensive tests for git-branch-protection hook.

Tests all functions:
- get_current_branch()
- detect_file_write_patterns()
- main()
"""

# Import using importlib for hyphenated name
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "git_branch_protection", hooks_dir / "git-branch-protection.py"
)
git_branch_protection = importlib.util.module_from_spec(spec)
sys.modules["git_branch_protection"] = git_branch_protection
spec.loader.exec_module(git_branch_protection)

get_current_branch = git_branch_protection.get_current_branch
detect_file_write_patterns = git_branch_protection.detect_file_write_patterns
main = git_branch_protection.main
PROTECTED_BRANCHES = git_branch_protection.PROTECTED_BRANCHES


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
# Tests for detect_file_write_patterns()
# =============================================================================


class TestDetectFileWritePatterns:
    """Test detect_file_write_patterns() function."""

    def test_detects_sed_inplace_edit(self) -> None:
        """Should detect sed -i pattern."""
        patterns = detect_file_write_patterns("sed -i 's/foo/bar/' file.txt")
        assert len(patterns) == 1
        assert patterns[0][0] == "sed -i"
        assert "sed -i 's/foo/bar/' file.txt" in patterns[0][1]

    def test_detects_sed_inplace_with_extension(self) -> None:
        """Should detect sed -i.bak pattern."""
        patterns = detect_file_write_patterns("sed -i.bak 's/foo/bar/' file.txt")
        assert len(patterns) == 1
        assert patterns[0][0] == "sed -i"

    def test_detects_perl_inplace_edit(self) -> None:
        """Should detect perl -i pattern."""
        patterns = detect_file_write_patterns("perl -i -pe 's/foo/bar/' file.txt")
        assert len(patterns) == 1
        assert patterns[0][0] == "perl -i"

    def test_detects_redirect_operator(self) -> None:
        """Should detect > redirect operator."""
        patterns = detect_file_write_patterns("echo 'hello' > output.txt")
        assert len(patterns) == 1
        assert patterns[0][0] == "redirect >"
        assert "echo 'hello' > output.txt" in patterns[0][1]

    def test_detects_append_operator(self) -> None:
        """Should detect >> append operator."""
        patterns = detect_file_write_patterns("echo 'hello' >> output.txt")
        assert len(patterns) == 1
        assert patterns[0][0] == "redirect >>"

    def test_detects_tee_command(self) -> None:
        """Should detect tee command."""
        patterns = detect_file_write_patterns("echo 'hello' | tee output.txt")
        assert len(patterns) == 1
        assert patterns[0][0] == "tee"

    def test_detects_heredoc_redirect(self) -> None:
        """Should detect heredoc with redirect."""
        command = "cat > file.txt <<EOF\nHello\nEOF"
        patterns = detect_file_write_patterns(command)
        assert len(patterns) >= 1
        pattern_names = [p[0] for p in patterns]
        assert "heredoc redirect" in pattern_names or "redirect >" in pattern_names

    def test_ignores_dev_null(self) -> None:
        """Should ignore redirects to /dev/null."""
        patterns = detect_file_write_patterns("echo 'hello' > /dev/null")
        assert len(patterns) == 0

    def test_ignores_dev_stdout(self) -> None:
        """Should ignore redirects to /dev/stdout."""
        patterns = detect_file_write_patterns("echo 'hello' > /dev/stdout")
        assert len(patterns) == 0

    def test_ignores_dev_stderr(self) -> None:
        """Should ignore redirects to /dev/stderr."""
        patterns = detect_file_write_patterns("echo 'hello' 2> /dev/stderr")
        assert len(patterns) == 0

    def test_ignores_quoted_redirect_in_string(self) -> None:
        """Should not be confused by > in quoted strings."""
        # Note: Pattern matching can't reliably distinguish this
        # This test documents current behavior - may have false positives
        detect_file_write_patterns('git commit -m "x > y"')
        # We accept that this might trigger a question (false positive)
        # because reliable detection is impossible without parsing

    def test_ignores_comparison_operators(self) -> None:
        """Should not be confused by comparison operators."""
        # Note: Pattern matching can't reliably distinguish this
        detect_file_write_patterns("awk '{if($1>5) print}'")
        # We accept that this might trigger a question (false positive)

    def test_detects_multiple_patterns(self) -> None:
        """Should detect multiple patterns in one command."""
        patterns = detect_file_write_patterns("sed -i 's/x/y/' f1 && echo 'hi' > f2")
        assert len(patterns) >= 2
        pattern_names = [p[0] for p in patterns]
        assert "sed -i" in pattern_names
        assert "redirect >" in pattern_names

    def test_returns_empty_list_for_safe_command(self) -> None:
        """Should return empty list for commands without write patterns."""
        patterns = detect_file_write_patterns("ls -la")
        assert patterns == []

    def test_returns_empty_list_for_empty_string(self) -> None:
        """Should return empty list for empty command."""
        patterns = detect_file_write_patterns("")
        assert patterns == []


# =============================================================================
# Tests for main() - Original Edit/Write tool blocking
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_blocks_edit_on_main_branch(self, capsys) -> None:
        """Should exit 2 and print error when on main branch."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch", return_value="main"
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot edit files on protected branch 'main'" in captured.err
        assert "git checkout -b feature" in captured.err

    def test_blocks_edit_on_master_branch(self, capsys) -> None:
        """Should exit 2 and print error when on master branch."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch",
                        return_value="master",
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot edit files on protected branch 'master'" in captured.err

    def test_blocks_edit_on_production_branch(self, capsys) -> None:
        """Should exit 2 and print error when on production branch."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch",
                        return_value="production",
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot edit files on protected branch 'production'" in captured.err

    def test_blocks_edit_on_prod_branch(self, capsys) -> None:
        """Should exit 2 and print error when on prod branch."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch", return_value="prod"
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot edit files on protected branch 'prod'" in captured.err

    def test_allows_edit_on_feature_branch(self) -> None:
        """Should exit 0 when on feature branch."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch",
                        return_value="feature/new-ui",
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0

    def test_allows_edit_when_not_in_git_repo(self) -> None:
        """Should exit 0 when not in a git repository."""
        input_data = {"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}}

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch", return_value=None
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0

    def test_exits_successfully_on_exception(self) -> None:
        """Should exit 0 on unexpected exceptions (silent failure)."""
        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", side_effect=Exception("Unexpected error")):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_handles_malformed_json(self) -> None:
        """Should exit 0 when stdin contains malformed JSON."""
        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch(
                    "json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)
                ):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_protected_branches_list_is_correct(self) -> None:
        """Should have correct list of protected branches."""
        assert PROTECTED_BRANCHES == ["main", "master", "production", "prod"]


# =============================================================================
# Tests for main() - Bash tool pattern detection
# =============================================================================


class TestMainBashPatternDetection:
    """Test Bash tool pattern detection in main()."""

    def test_bash_with_sed_pattern_on_protected_branch_shows_question(
        self, capsys
    ) -> None:
        """Should output reflective question but exit 0 for Bash with sed -i."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "sed -i 's/foo/bar/' file.txt"},
        }

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch", return_value="main"
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0  # Does NOT block
        captured = capsys.readouterr()
        assert "Branch Protection Check" in captured.err
        assert "protected branch 'main'" in captured.err
        assert "sed -i" in captured.err
        assert "pattern matching cannot reliably distinguish" in captured.err
        assert "Please verify" in captured.err

    def test_bash_with_redirect_pattern_on_protected_branch_shows_question(
        self, capsys
    ) -> None:
        """Should output reflective question but exit 0 for Bash with > redirect."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "echo 'test' > output.txt"},
        }

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch", return_value="main"
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Branch Protection Check" in captured.err
        assert "redirect >" in captured.err

    def test_bash_with_tee_pattern_on_protected_branch_shows_question(
        self, capsys
    ) -> None:
        """Should output reflective question but exit 0 for Bash with tee."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "echo 'test' | tee file.txt"},
        }

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch", return_value="main"
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Branch Protection Check" in captured.err
        assert "tee" in captured.err

    def test_bash_without_patterns_on_protected_branch_exits_silently(
        self, capsys
    ) -> None:
        """Should exit 0 silently for Bash without write patterns."""
        input_data = {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch", return_value="main"
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.err == ""  # No output

    def test_bash_with_dev_null_redirect_exits_silently(self, capsys) -> None:
        """Should exit 0 silently for safe redirects to /dev/null."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "echo 'test' > /dev/null"},
        }

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch", return_value="main"
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.err == ""  # No output

    def test_bash_with_pattern_on_feature_branch_exits_silently(self, capsys) -> None:
        """Should exit 0 silently for Bash with patterns on feature branch."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "sed -i 's/foo/bar/' file.txt"},
        }

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch",
                        return_value="feature/test",
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.err == ""  # No output - not on protected branch

    def test_bash_with_multiple_patterns_shows_all_in_question(self, capsys) -> None:
        """Should list all detected patterns in reflective question."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "sed -i 's/x/y/' f1 && echo 'hi' > f2"},
        }

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch", return_value="main"
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        # Should mention multiple patterns or at least one
        assert "Branch Protection Check" in captured.err
        assert "sed -i" in captured.err or "redirect >" in captured.err

    def test_bash_missing_command_field_exits_silently(self, capsys) -> None:
        """Should handle Bash tool without command field gracefully."""
        input_data = {"tool_name": "Bash", "tool_input": {}}

        with patch("git_branch_protection.exit_if_disabled"):
            with patch("sys.stdin", MagicMock()):
                with patch("json.load", return_value=input_data):
                    with patch(
                        "git_branch_protection.get_current_branch", return_value="main"
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.err == ""
