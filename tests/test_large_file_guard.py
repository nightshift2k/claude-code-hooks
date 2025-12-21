#!/usr/bin/env python3
"""
Comprehensive tests for large-file-guard hook.

Tests all functions:
- classify_file()
- estimate_tokens()
- count_lines()
- should_skip_check()
- check_file_size()
- main()
"""

import importlib.util
import sys
from pathlib import Path

# Import hook_utils for shared utilities
import hook_utils
import pytest

# Import large-file-guard using importlib for hyphenated name
hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "large_file_guard", hooks_dir / "large-file-guard.py"
)
large_file_guard = importlib.util.module_from_spec(spec)
sys.modules["large_file_guard"] = large_file_guard
spec.loader.exec_module(large_file_guard)

main = large_file_guard.main


# =============================================================================
# Tests for classify_file() in hook_utils
# =============================================================================


class TestClassifyFile:
    """Test classify_file() function in hook_utils."""

    def test_identifies_binary_png_file(self) -> None:
        """Should classify .png files as binary."""
        result = hook_utils.classify_file("image.png")
        assert result == "binary"

    def test_identifies_binary_jpg_file(self) -> None:
        """Should classify .jpg files as binary."""
        result = hook_utils.classify_file("photo.jpg")
        assert result == "binary"

    def test_identifies_binary_pdf_file(self) -> None:
        """Should classify .pdf files as binary."""
        result = hook_utils.classify_file("document.pdf")
        assert result == "binary"

    def test_identifies_binary_zip_file(self) -> None:
        """Should classify .zip files as binary."""
        result = hook_utils.classify_file("archive.zip")
        assert result == "binary"

    def test_identifies_code_python_file(self) -> None:
        """Should classify .py files as code."""
        result = hook_utils.classify_file("script.py")
        assert result == "code"

    def test_identifies_code_javascript_file(self) -> None:
        """Should classify .js files as code."""
        result = hook_utils.classify_file("app.js")
        assert result == "code"

    def test_identifies_code_typescript_file(self) -> None:
        """Should classify .ts files as code."""
        result = hook_utils.classify_file("component.ts")
        assert result == "code"

    def test_identifies_data_json_file(self) -> None:
        """Should classify .json files as data."""
        result = hook_utils.classify_file("config.json")
        assert result == "data"

    def test_identifies_data_yaml_file(self) -> None:
        """Should classify .yaml files as data."""
        result = hook_utils.classify_file("config.yaml")
        assert result == "data"

    def test_identifies_data_csv_file(self) -> None:
        """Should classify .csv files as data."""
        result = hook_utils.classify_file("data.csv")
        assert result == "data"

    def test_identifies_unknown_file(self) -> None:
        """Should classify unknown extensions as unknown."""
        result = hook_utils.classify_file("readme.txt")
        assert result == "unknown"

    def test_case_insensitive_extension(self) -> None:
        """Should handle uppercase extensions."""
        result = hook_utils.classify_file("image.PNG")
        assert result == "binary"


# =============================================================================
# Tests for estimate_tokens() in hook_utils
# =============================================================================


class TestEstimateTokens:
    """Test estimate_tokens() function in hook_utils."""

    def test_empty_string_returns_zero(self) -> None:
        """Should return 0 for empty string."""
        result = hook_utils.estimate_tokens("")
        assert result == 0

    def test_short_text_calculates_correctly(self) -> None:
        """Should calculate tokens using 3.5 chars/token ratio."""
        # 35 characters = 10 tokens
        text = "This is a test of token counting."
        result = hook_utils.estimate_tokens(text)
        assert result == int(len(text) / 3.5)

    def test_long_text_calculates_correctly(self) -> None:
        """Should handle longer text correctly."""
        text = "a" * 3500  # 3500 chars = 1000 tokens
        result = hook_utils.estimate_tokens(text)
        assert result == 1000

    def test_multiline_text(self) -> None:
        """Should count newlines as characters."""
        text = "line1\nline2\nline3"  # 17 chars
        result = hook_utils.estimate_tokens(text)
        assert result == int(17 / 3.5)


# =============================================================================
# Tests for count_lines() in hook_utils
# =============================================================================


class TestCountLines:
    """Test count_lines() function in hook_utils."""

    def test_counts_lines_in_single_line_file(self, tmp_path) -> None:
        """Should count single line file correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("single line")

        result = hook_utils.count_lines(str(test_file))
        assert result == 1

    def test_counts_lines_in_multiline_file(self, tmp_path) -> None:
        """Should count multiple lines correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3\n")

        result = hook_utils.count_lines(str(test_file))
        assert result == 3

    def test_counts_lines_without_trailing_newline(self, tmp_path) -> None:
        """Should count lines when no trailing newline."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3")

        result = hook_utils.count_lines(str(test_file))
        assert result == 3

    def test_returns_zero_for_empty_file(self, tmp_path) -> None:
        """Should return 0 for empty file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("")

        result = hook_utils.count_lines(str(test_file))
        assert result == 0

    def test_handles_file_not_found(self) -> None:
        """Should return 0 for non-existent file."""
        result = hook_utils.count_lines("/nonexistent/file.txt")
        assert result == 0

    def test_handles_encoding_errors(self, tmp_path) -> None:
        """Should handle files with encoding issues."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"\xff\xfe\x00\x00")

        # Should not crash, return 0 or best effort count
        result = hook_utils.count_lines(str(test_file))
        assert isinstance(result, int)
        assert result >= 0


# =============================================================================
# Tests for main() - Small files
# =============================================================================


class TestMainSmallFiles:
    """Test main() with files under threshold."""

    def test_allows_small_file_under_500_lines(
        self, mock_stdin, tmp_path, monkeypatch
    ) -> None:
        """Should allow reading files under 500 lines (default threshold)."""
        test_file = tmp_path / "small.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(400)]))

        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_allows_file_at_threshold(self, mock_stdin, tmp_path, monkeypatch) -> None:
        """Should allow reading files exactly at threshold."""
        test_file = tmp_path / "exact.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(500)]))

        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "500")
        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0


# =============================================================================
# Tests for main() - Large files
# =============================================================================


class TestMainLargeFiles:
    """Test main() with files over threshold."""

    def test_blocks_large_file_over_500_lines(
        self, mock_stdin, tmp_path, capsys
    ) -> None:
        """Should block reading files over 500 lines (default threshold)."""
        test_file = tmp_path / "large.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(600)]))

        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2

        captured = capsys.readouterr()
        assert "Large file" in captured.err
        assert "600 lines" in captured.err
        assert "Serena find_symbol" in captured.err or "Grep patterns" in captured.err

    def test_includes_token_estimate_in_error(
        self, mock_stdin, tmp_path, capsys
    ) -> None:
        """Should include token estimate in error message."""
        test_file = tmp_path / "large.py"
        content = "\n".join([f"line {i}" for i in range(600)])
        test_file.write_text(content)

        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2

        captured = capsys.readouterr()
        assert "tokens est." in captured.err

    def test_shows_serena_for_code_files(self, mock_stdin, tmp_path, capsys) -> None:
        """Should suggest Serena for code files."""
        test_file = tmp_path / "large.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(600)]))

        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2

        captured = capsys.readouterr()
        assert "Serena find_symbol" in captured.err

    def test_omits_serena_for_data_files(self, mock_stdin, tmp_path, capsys) -> None:
        """Should omit Serena suggestion for data files."""
        test_file = tmp_path / "large.json"
        test_file.write_text("\n".join([f'"line {i}"' for i in range(600)]))

        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2

        captured = capsys.readouterr()
        assert "Serena" not in captured.err
        assert "Grep patterns" in captured.err


# =============================================================================
# Tests for main() - Skip conditions
# =============================================================================


class TestMainSkipConditions:
    """Test main() skip conditions."""

    def test_skips_check_for_binary_files(self, mock_stdin, tmp_path) -> None:
        """Should skip check for binary file extensions."""
        test_file = tmp_path / "image.png"
        test_file.write_bytes(b"\x89PNG" + b"\x00" * 10000)

        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_skips_check_when_offset_present(self, mock_stdin, tmp_path) -> None:
        """Should skip check when offset parameter is present."""
        test_file = tmp_path / "large.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(600)]))

        mock_stdin(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": str(test_file), "offset": 100},
            }
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_skips_check_when_limit_present(self, mock_stdin, tmp_path) -> None:
        """Should skip check when limit parameter is present."""
        test_file = tmp_path / "large.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(600)]))

        mock_stdin(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": str(test_file), "limit": 100},
            }
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_skips_check_with_explicit_zero_offset(self, mock_stdin, tmp_path) -> None:
        """Should skip check when offset=0 (explicit zero is a targeted read)."""
        test_file = tmp_path / "large.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(600)]))

        mock_stdin(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": str(test_file), "offset": 0},
            }
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_checks_file_with_null_offset(self, mock_stdin, tmp_path, capsys) -> None:
        """Should NOT skip check when offset=null (full read, not targeted)."""
        test_file = tmp_path / "large.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(600)]))

        # Explicitly pass null for offset
        mock_stdin(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": str(test_file), "offset": None},
            }
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should block because offset=null means full read
        assert exc_info.value.code == 2

    def test_checks_file_without_offset_key(self, mock_stdin, tmp_path, capsys) -> None:
        """Should NOT skip check when offset key is missing (full read)."""
        test_file = tmp_path / "large.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(600)]))

        # Don't include offset key at all
        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should block because no offset means full read
        assert exc_info.value.code == 2

    def test_skips_check_when_file_not_exists(self, mock_stdin) -> None:
        """Should skip check when file doesn't exist."""
        mock_stdin(
            {"tool_name": "Read", "tool_input": {"file_path": "/nonexistent/file.py"}}
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_bypasses_with_allow_large_read_env(
        self, mock_stdin, tmp_path, monkeypatch
    ) -> None:
        """Should bypass check when ALLOW_LARGE_READ=1 is set."""
        test_file = tmp_path / "large.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(600)]))

        monkeypatch.setenv("ALLOW_LARGE_READ", "1")
        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0


# =============================================================================
# Tests for main() - Configuration
# =============================================================================


class TestMainConfiguration:
    """Test main() configuration precedence."""

    def test_uses_env_var_threshold(self, mock_stdin, tmp_path, monkeypatch) -> None:
        """Should use LARGE_FILE_THRESHOLD env var."""
        test_file = tmp_path / "medium.py"
        # Create file > 5KB to avoid instant-allow optimization
        # 300 lines with 100 chars each = ~30KB
        test_file.write_text("\n".join(["x" * 100 for _ in range(300)]))

        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "200")
        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should block because 300 > 200
        assert exc_info.value.code == 2

    def test_uses_config_file_threshold(
        self, mock_stdin, tmp_path, monkeypatch
    ) -> None:
        """Should use ~/.claude/hook-large-file-guard-config file."""
        test_file = tmp_path / "medium.py"
        # Create file > 5KB to avoid instant-allow optimization
        # 300 lines with 100 chars each = ~30KB
        test_file.write_text("\n".join(["x" * 100 for _ in range(300)]))

        # Create .claude directory and config file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        config_file = claude_dir / "hook-large-file-guard-config"
        config_file.write_text("200\n")

        monkeypatch.setenv("HOME", str(tmp_path))
        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should block because 300 > 200
        assert exc_info.value.code == 2

    def test_env_var_overrides_config_file(
        self, mock_stdin, tmp_path, monkeypatch
    ) -> None:
        """Should prefer env var over config file."""
        test_file = tmp_path / "medium.py"
        # Create file > 5KB to avoid instant-allow optimization
        # 300 lines with 100 chars each = ~30KB
        test_file.write_text("\n".join(["x" * 100 for _ in range(300)]))

        # Create .claude directory and config file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        config_file = claude_dir / "hook-large-file-guard-config"
        config_file.write_text("200\n")

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LARGE_FILE_THRESHOLD", "400")
        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should allow because 300 < 400 (env var wins)
        assert exc_info.value.code == 0

    def test_uses_default_when_no_config(
        self, mock_stdin, tmp_path, monkeypatch
    ) -> None:
        """Should use default 500 when no configuration."""
        test_file = tmp_path / "medium.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(450)]))

        monkeypatch.delenv("LARGE_FILE_THRESHOLD", raising=False)
        monkeypatch.setenv("HOME", "/nonexistent")
        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should allow because 450 < 500 (default)
        assert exc_info.value.code == 0


# =============================================================================
# Tests for main() - Two-stage size detection
# =============================================================================


class TestMainTwoStageDetection:
    """Test main() two-stage byte check optimization."""

    def test_instant_allow_for_tiny_files(self, mock_stdin, tmp_path) -> None:
        """Should instantly allow files < 5KB without line counting."""
        test_file = tmp_path / "tiny.py"
        test_file.write_text("x" * 4000)  # < 5KB

        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_instant_block_for_huge_files(self, mock_stdin, tmp_path, capsys) -> None:
        """Should instantly block files > 100KB without line counting."""
        test_file = tmp_path / "huge.py"
        test_file.write_text("x" * 110000)  # > 100KB

        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2

    def test_accurate_line_count_for_medium_files(self, mock_stdin, tmp_path) -> None:
        """Should perform accurate line count for 5-100KB files."""
        # Create a file in the 5-100KB range
        test_file = tmp_path / "medium.py"
        test_file.write_text("\n".join([f"line {i}" for i in range(400)]))  # ~5-10KB

        mock_stdin({"tool_name": "Read", "tool_input": {"file_path": str(test_file)}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should allow because 400 < 500
        assert exc_info.value.code == 0


# =============================================================================
# Tests for main() - Error handling
# =============================================================================


class TestMainErrorHandling:
    """Test main() error handling."""

    def test_allows_on_malformed_json(self, monkeypatch) -> None:
        """Should exit 0 on malformed JSON input."""
        monkeypatch.setattr("sys.stdin.read", lambda: "not json")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_allows_on_missing_tool_name(self, mock_stdin) -> None:
        """Should exit 0 when tool_name is missing."""
        mock_stdin({"tool_input": {"file_path": "/some/file.py"}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_allows_on_missing_tool_input(self, mock_stdin) -> None:
        """Should exit 0 when tool_input is missing."""
        mock_stdin({"tool_name": "Read"})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_allows_on_missing_file_path(self, mock_stdin) -> None:
        """Should exit 0 when file_path is missing."""
        mock_stdin({"tool_name": "Read", "tool_input": {}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_allows_on_non_read_tool(self, mock_stdin) -> None:
        """Should exit 0 for non-Read tools."""
        mock_stdin({"tool_name": "Write", "tool_input": {"file_path": "/some/file.py"}})

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
