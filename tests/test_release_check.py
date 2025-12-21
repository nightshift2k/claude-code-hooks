#!/usr/bin/env python3
"""
Comprehensive tests for release-check hook.

Tests all functions:
- extract_version()
- check_version_in_changelog()
- main()
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Import using importlib for hyphenated name
import importlib.util

hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "release_check", hooks_dir / "release-check.py"
)
release_check = importlib.util.module_from_spec(spec)
sys.modules["release_check"] = release_check
spec.loader.exec_module(release_check)

extract_tag_version = release_check.extract_tag_version
extract_release_version = release_check.extract_release_version
check_version_in_changelog = release_check.check_version_in_changelog
main = release_check.main


# =============================================================================
# Tests for extract_tag_version()
# =============================================================================


class TestExtractTagVersion:
    """Test extract_tag_version() function."""

    def test_extracts_simple_version(self) -> None:
        """Should extract version from simple tag command."""
        version = extract_tag_version("git tag v0.1.4")
        assert version == "0.1.4"

    def test_extracts_version_with_message_flag(self) -> None:
        """Should extract version when -m flag present."""
        version = extract_tag_version("git tag v1.2.3 -m 'Release version 1.2.3'")
        assert version == "1.2.3"

    def test_extracts_version_with_annotated_flag(self) -> None:
        """Should extract version when -a flag present."""
        version = extract_tag_version("git tag -a v2.0.0 -m 'Major release'")
        assert version == "2.0.0"

    def test_extracts_version_with_multiple_digits(self) -> None:
        """Should extract version with multiple digits."""
        version = extract_tag_version("git tag v10.20.30")
        assert version == "10.20.30"

    def test_extracts_version_with_patch_only(self) -> None:
        """Should extract version with patch number."""
        version = extract_tag_version("git tag v0.0.1")
        assert version == "0.0.1"

    def test_returns_none_for_non_tag_command(self) -> None:
        """Should return None for non-tag commands."""
        version = extract_tag_version("git commit -m 'test'")
        assert version is None

    def test_returns_none_for_tag_without_v_prefix(self) -> None:
        """Should return None for tags without 'v' prefix."""
        version = extract_tag_version("git tag 1.2.3")
        assert version is None

    def test_returns_none_for_invalid_version_format(self) -> None:
        """Should return None for invalid version formats."""
        version = extract_tag_version("git tag vInvalid")
        assert version is None


# =============================================================================
# Tests for extract_release_version()
# =============================================================================


class TestExtractReleaseVersion:
    """Test extract_release_version() function."""

    def test_extracts_simple_version(self) -> None:
        """Should extract version from simple gh release command."""
        version = extract_release_version("gh release create v0.1.4")
        assert version == "0.1.4"

    def test_extracts_version_with_notes(self) -> None:
        """Should extract version when --notes flag present."""
        version = extract_release_version(
            "gh release create v1.2.3 --notes 'Release notes'"
        )
        assert version == "1.2.3"

    def test_extracts_version_with_title(self) -> None:
        """Should extract version when --title flag present."""
        version = extract_release_version(
            "gh release create v2.0.0 --title 'Major Release'"
        )
        assert version == "2.0.0"

    def test_extracts_version_with_multiple_digits(self) -> None:
        """Should extract version with multiple digits."""
        version = extract_release_version("gh release create v10.20.30")
        assert version == "10.20.30"

    def test_returns_none_for_non_release_command(self) -> None:
        """Should return None for non-release commands."""
        version = extract_release_version("gh pr create")
        assert version is None

    def test_returns_none_for_release_without_v_prefix(self) -> None:
        """Should return None for releases without 'v' prefix."""
        version = extract_release_version("gh release create 1.2.3")
        assert version is None

    def test_returns_none_for_gh_release_list(self) -> None:
        """Should return None for gh release list commands."""
        version = extract_release_version("gh release list")
        assert version is None


# =============================================================================
# Tests for check_version_in_changelog()
# =============================================================================


class TestCheckVersionInChangelog:
    """Test check_version_in_changelog() function."""

    def test_returns_true_when_version_found(self) -> None:
        """Should return True when version exists in CHANGELOG."""
        changelog_content = """# Changelog

## [0.1.4] - 2025-12-21
- New feature added
"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = mock_open(read_data=changelog_content)
        mock_path.open = mock_file

        with patch('pathlib.Path.cwd', return_value=Path('/fake')):
            with patch('pathlib.Path.__truediv__', return_value=mock_path):
                result = check_version_in_changelog("0.1.4")
                assert result is True

    def test_returns_true_for_different_version_formats(self) -> None:
        """Should find version in different formats."""
        changelog_content = """# Changelog

## Version 1.2.3 (2025-12-21)
- Bug fixes
"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = mock_open(read_data=changelog_content)
        mock_path.open = mock_file

        with patch('pathlib.Path.cwd', return_value=Path('/fake')):
            with patch('pathlib.Path.__truediv__', return_value=mock_path):
                result = check_version_in_changelog("1.2.3")
                assert result is True

    def test_returns_false_when_version_not_found(self) -> None:
        """Should return False when version doesn't exist in CHANGELOG."""
        changelog_content = """# Changelog

## [0.1.3] - 2025-12-20
- Old feature
"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = mock_open(read_data=changelog_content)
        mock_path.open = mock_file

        with patch('pathlib.Path.cwd', return_value=Path('/fake')):
            with patch('pathlib.Path.__truediv__', return_value=mock_path):
                result = check_version_in_changelog("0.1.4")
                assert result is False

    def test_returns_true_when_changelog_missing(self) -> None:
        """Should return True (allow) when CHANGELOG.md doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False

        with patch('pathlib.Path.cwd', return_value=Path('/fake')):
            with patch('pathlib.Path.__truediv__', return_value=mock_path):
                result = check_version_in_changelog("0.1.4")
                assert result is True

    def test_returns_true_on_file_read_error(self) -> None:
        """Should return True (allow) when CHANGELOG.md can't be read."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.open.side_effect = OSError("Permission denied")

        with patch('pathlib.Path.cwd', return_value=Path('/fake')):
            with patch('pathlib.Path.__truediv__', return_value=mock_path):
                result = check_version_in_changelog("0.1.4")
                assert result is True

    def test_simple_string_search(self) -> None:
        """Should use simple string search to find version."""
        changelog_content = """# Changelog

The version 2.5.0 is our latest release.
"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = mock_open(read_data=changelog_content)
        mock_path.open = mock_file

        with patch('pathlib.Path.cwd', return_value=Path('/fake')):
            with patch('pathlib.Path.__truediv__', return_value=mock_path):
                result = check_version_in_changelog("2.5.0")
                assert result is True


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_blocks_tag_when_version_not_in_changelog(self, capsys) -> None:
        """Should block tag when version not found in CHANGELOG."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git tag v0.1.4"}
        }

        changelog_content = """# Changelog

## [0.1.3] - 2025-12-20
- Old version
"""

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = mock_open(read_data=changelog_content)
        mock_path.open = mock_file

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with patch('pathlib.Path.cwd', return_value=Path('/fake')):
                    with patch('pathlib.Path.__truediv__', return_value=mock_path):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Version 0.1.4 not found in CHANGELOG.md" in captured.err

    def test_requires_confirmation_when_version_in_changelog(self, capsys) -> None:
        """Should require confirmation when version found in CHANGELOG."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git tag v0.1.4"}
        }

        changelog_content = """# Changelog

## [0.1.4] - 2025-12-21
- New version
"""

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = mock_open(read_data=changelog_content)
        mock_path.open = mock_file

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with patch('pathlib.Path.cwd', return_value=Path('/fake')):
                    with patch('pathlib.Path.__truediv__', return_value=mock_path):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Confirm: Create git tag v0.1.4" in captured.err
        assert "CONFIRM_TAG=1" in captured.err

    def test_allows_tag_with_confirm_flag(self) -> None:
        """Should allow tag when CONFIRM_TAG=1 is in command."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "CONFIRM_TAG=1 git tag v0.1.4"}
        }

        changelog_content = """# Changelog

## [0.1.4] - 2025-12-21
- New version
"""

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = mock_open(read_data=changelog_content)
        mock_path.open = mock_file

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with patch('pathlib.Path.cwd', return_value=Path('/fake')):
                    with patch('pathlib.Path.__truediv__', return_value=mock_path):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 0

    def test_blocks_confirm_tag_when_version_not_in_changelog(self, capsys) -> None:
        """Should block even with CONFIRM_TAG=1 if version not in CHANGELOG."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "CONFIRM_TAG=1 git tag v0.1.4"}
        }

        changelog_content = """# Changelog

## [0.1.3] - 2025-12-20
- Old version
"""

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = mock_open(read_data=changelog_content)
        mock_path.open = mock_file

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with patch('pathlib.Path.cwd', return_value=Path('/fake')):
                    with patch('pathlib.Path.__truediv__', return_value=mock_path):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Version 0.1.4 not found in CHANGELOG.md" in captured.err

    def test_requires_confirmation_when_changelog_missing(self, capsys) -> None:
        """Should require confirmation when CHANGELOG.md doesn't exist."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git tag v0.1.4"}
        }

        mock_path = MagicMock()
        mock_path.exists.return_value = False

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with patch('pathlib.Path.cwd', return_value=Path('/fake')):
                    with patch('pathlib.Path.__truediv__', return_value=mock_path):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Confirm: Create git tag v0.1.4" in captured.err

    def test_bypasses_check_with_skip_env_var(self) -> None:
        """Should bypass check when SKIP_RELEASE_CHECK=1 in environment."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git tag v0.1.4"}
        }

        with patch('release_check.exit_if_disabled'):
            with patch('os.environ.get', return_value='1'):
                with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_bypasses_check_with_inline_skip(self) -> None:
        """Should bypass check when SKIP_RELEASE_CHECK=1 in command."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "SKIP_RELEASE_CHECK=1 git tag v0.1.4"}
        }

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_non_bash_tool(self) -> None:
        """Should exit 0 for non-Bash tool invocations."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"}
        }

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_non_tag_command(self) -> None:
        """Should exit 0 for git commands that are not tag v*."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'test'"}
        }

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_tag_without_v_prefix(self) -> None:
        """Should exit 0 for tags without 'v' prefix."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git tag 1.2.3"}
        }

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_successfully_on_exception(self) -> None:
        """Should exit 0 on unexpected exceptions (silent failure)."""
        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', side_effect=Exception("Unexpected error")):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_malformed_json(self) -> None:
        """Should exit 0 when stdin contains malformed JSON."""
        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value="not valid json"):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_handles_missing_command(self) -> None:
        """Should exit 0 when command is missing from tool_input."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {}
        }

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0


# =============================================================================
# Tests for gh release create confirmation
# =============================================================================


class TestGhReleaseConfirmation:
    """Test gh release create confirmation behavior."""

    def test_requires_confirmation_for_gh_release_create(self, capsys) -> None:
        """Should require confirmation for gh release create command."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "gh release create v0.1.4 --notes 'Release'"}
        }

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Confirm: Create GitHub release v0.1.4" in captured.err
        assert "CONFIRM_RELEASE=1" in captured.err

    def test_allows_gh_release_with_confirm_flag(self) -> None:
        """Should allow gh release create when CONFIRM_RELEASE=1 is in command."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {
                "command": "CONFIRM_RELEASE=1 gh release create v0.1.4 --notes 'Release'"
            }
        }

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_gh_release_list(self) -> None:
        """Should exit 0 for gh release list commands (not create)."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "gh release list"}
        }

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_exits_for_gh_release_without_version(self) -> None:
        """Should exit 0 for gh release without v* version."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "gh release create 1.2.3"}
        }

        with patch('release_check.exit_if_disabled'):
            with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 0

    def test_bypasses_gh_release_with_skip_env_var(self) -> None:
        """Should bypass gh release check with SKIP_RELEASE_CHECK=1."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "gh release create v0.1.4"}
        }

        with patch('release_check.exit_if_disabled'):
            with patch('os.environ.get', return_value='1'):
                with patch('sys.stdin.read', return_value=json.dumps(input_data)):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
