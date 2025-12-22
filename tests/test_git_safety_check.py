#!/usr/bin/env python3
"""
Comprehensive tests for git-safety-check hook.

Tests all functions:
- check_git_command()
- main()
"""

# Import using importlib for hyphenated name
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "git_safety_check", hooks_dir / "git-safety-check.py"
)
git_safety_check = importlib.util.module_from_spec(spec)
sys.modules["git_safety_check"] = git_safety_check
spec.loader.exec_module(git_safety_check)

check_git_command = git_safety_check.check_git_command
main = git_safety_check.main


# =============================================================================
# Tests for check_git_command()
# =============================================================================


class TestCheckGitCommand:
    """Test check_git_command() function."""

    def test_blocks_no_verify_flag(self, capsys) -> None:
        """Should block git commands using --no-verify flag."""
        with pytest.raises(SystemExit) as exc_info:
            check_git_command("git commit --no-verify -m 'test'")

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Using --no-verify to skip Git hooks is prohibited" in captured.err

    def test_blocks_no_verify_in_push(self, capsys) -> None:
        """Should block git push with --no-verify flag."""
        with pytest.raises(SystemExit) as exc_info:
            check_git_command("git push --no-verify origin main")

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Using --no-verify to skip Git hooks is prohibited" in captured.err

    def test_allows_no_verify_in_commit_message(self) -> None:
        """Should allow --no-verify when it's inside commit message."""
        # Should not raise SystemExit
        check_git_command('git commit -m "fix: remove --no-verify usage"')

    def test_allows_no_verify_in_heredoc(self) -> None:
        """Should allow --no-verify when it's inside heredoc."""
        command = '''git commit -m "$(cat <<'EOF'
Fix bug with --no-verify
EOF
)"'''
        # Should not raise SystemExit
        check_git_command(command)

    def test_blocks_main_branch_deletion_remote(self, capsys) -> None:
        """Should block deletion of main branch on remote."""
        with pytest.raises(SystemExit) as exc_info:
            check_git_command("git push origin :main")

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot delete protected branch 'main'" in captured.err

    def test_blocks_master_branch_deletion_remote(self, capsys) -> None:
        """Should block deletion of master branch on remote."""
        with pytest.raises(SystemExit) as exc_info:
            check_git_command("git push origin :master")

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot delete protected branch 'master'" in captured.err

    def test_blocks_production_branch_deletion_remote(self, capsys) -> None:
        """Should block deletion of production branch on remote."""
        with pytest.raises(SystemExit) as exc_info:
            check_git_command("git push origin :production")

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot delete protected branch 'production'" in captured.err

    def test_blocks_prod_branch_deletion_remote(self, capsys) -> None:
        """Should block deletion of prod branch on remote."""
        with pytest.raises(SystemExit) as exc_info:
            check_git_command("git push origin :prod")

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot delete protected branch 'prod'" in captured.err

    def test_blocks_main_branch_deletion_local_lowercase_d(self, capsys) -> None:
        """Should block local deletion of main branch with -d flag."""
        with pytest.raises(SystemExit) as exc_info:
            check_git_command("git branch -d main")

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot delete protected branch 'main'" in captured.err

    def test_blocks_main_branch_deletion_local_uppercase_d(self, capsys) -> None:
        """Should block local deletion of main branch with -D flag."""
        with pytest.raises(SystemExit) as exc_info:
            check_git_command("git branch -D main")

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Cannot delete protected branch 'main'" in captured.err

    def test_allows_feature_branch_deletion(self) -> None:
        """Should allow deletion of feature branches."""
        # Should not raise SystemExit
        check_git_command("git branch -d feature-123")

    def test_allows_push_to_main(self) -> None:
        """Should allow pushing to main branch (not deletion)."""
        # Should not raise SystemExit
        check_git_command("git push origin main")

    def test_allows_non_git_commands(self) -> None:
        """Should allow non-git commands to pass through."""
        # Should not raise SystemExit
        check_git_command("npm install")
        check_git_command("echo 'hello world'")

    def test_blocks_branch_deletion_with_separator(self, capsys) -> None:
        """Should block protected branch deletion even with command separators."""
        with pytest.raises(SystemExit) as exc_info:
            check_git_command("git branch -d main && echo done")

        assert exc_info.value.code == 2

    def test_allows_branch_deletion_in_chained_command(self) -> None:
        """Should not false positive on protected branch name in other commands."""
        # "main" appears but not as deletion target
        # Should not raise SystemExit
        check_git_command("git branch -d feature && git push origin main")


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_blocks_dangerous_git_command(self, capsys) -> None:
        """Should block dangerous git operations."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit --no-verify -m 'test'"},
        }

        with patch("git_safety_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Using --no-verify" in captured.err

    def test_allows_safe_git_command(self) -> None:
        """Should allow safe git operations."""
        input_data = {"tool_name": "Bash", "tool_input": {"command": "git status"}}

        with patch("git_safety_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_non_bash_tool(self) -> None:
        """Should exit 0 for non-Bash tool invocations."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
        }

        with patch("git_safety_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_non_git_command(self) -> None:
        """Should exit 0 for commands without git."""
        input_data = {"tool_name": "Bash", "tool_input": {"command": "npm install"}}

        with patch("git_safety_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_successfully_on_exception(self) -> None:
        """Should exit 0 on unexpected exceptions (silent failure)."""
        with patch("git_safety_check.exit_if_disabled"):
            with patch("sys.stdin.read", side_effect=Exception("Unexpected error")):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_malformed_json(self) -> None:
        """Should exit 0 when stdin contains malformed JSON."""
        with patch("git_safety_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value="not valid json"):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_missing_command(self) -> None:
        """Should exit 0 when command is missing from tool_input."""
        input_data = {"tool_name": "Bash", "tool_input": {}}

        with patch("git_safety_check.exit_if_disabled"):
            with patch("sys.stdin.read", return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0
