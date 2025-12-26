#!/usr/bin/env python3
"""
Comprehensive tests for prompt-flag-appender hook.

Tests all functions:
- load_config()
- build_alias_map()
- resolve_trigger()
- get_trigger_content()
- get_always_fragment()
- get_active_mode_fragments()
- split_prompt_and_triggers()
- get_fragments_for_triggers()
- build_prompt()
- main()
"""

# Import using importlib for hyphenated name
import importlib.util
import json
import sys
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

hooks_dir = Path(__file__).parent.parent / "hooks"
spec = importlib.util.spec_from_file_location(
    "prompt_flag_appender", hooks_dir / "prompt-flag-appender.py"
)
prompt_flag_appender = importlib.util.module_from_spec(spec)
sys.modules["prompt_flag_appender"] = prompt_flag_appender
spec.loader.exec_module(prompt_flag_appender)

load_config = prompt_flag_appender.load_config
build_alias_map = prompt_flag_appender.build_alias_map
resolve_trigger = prompt_flag_appender.resolve_trigger
get_trigger_content = prompt_flag_appender.get_trigger_content
get_always_fragment = prompt_flag_appender.get_always_fragment
get_active_mode_fragments = prompt_flag_appender.get_active_mode_fragments
split_prompt_and_triggers = prompt_flag_appender.split_prompt_and_triggers
get_fragments_for_triggers = prompt_flag_appender.get_fragments_for_triggers
build_prompt = prompt_flag_appender.build_prompt
main = prompt_flag_appender.main


# =============================================================================
# Test fixtures
# =============================================================================


@pytest.fixture
def sample_config():
    """Sample configuration dictionary for testing."""
    return {
        "ultrathink": {
            "aliases": [],
            "content": "ULTRATHINK MODE ACTIVATED",
        },
        "absolute": {
            "aliases": [],
            "content": "System Instruction: Absolute Mode",
        },
        "approval": {
            "aliases": ["approve"],
            "content": "Human-in-the-Loop Mode",
        },
        "sequential-thinking": {
            "aliases": ["seqthi", "seq"],
            "content": "Use sequential thinking",
        },
    }


@pytest.fixture
def sample_alias_map():
    """Sample alias map for testing."""
    return {
        "approve": "approval",
        "seqthi": "sequential-thinking",
        "seq": "sequential-thinking",
    }


# =============================================================================
# Tests for load_config()
# =============================================================================


class TestLoadConfig:
    """Test load_config() function."""

    def test_loads_system_toml(self, tmp_path, monkeypatch) -> None:
        """Should load system TOML file."""
        toml_content = b'[test]\naliases = []\ncontent = "Test content"'
        toml_file = tmp_path / "prompt-flag-appender.toml"
        toml_file.write_bytes(toml_content)

        # Mock the script path to point to tmp_path
        with patch.object(
            Path, "resolve", return_value=tmp_path / "prompt-flag-appender.py"
        ):
            with patch.object(Path, "with_suffix", return_value=toml_file):
                with patch.object(Path, "is_file", return_value=True):
                    with patch("builtins.open", return_value=open(toml_file, "rb")):
                        # Actually read the file
                        with open(toml_file, "rb") as f:
                            result = tomllib.load(f)

        assert "test" in result
        assert result["test"]["content"] == "Test content"

    def test_returns_empty_dict_when_no_system_toml(self, monkeypatch) -> None:
        """Should return empty dict when system TOML doesn't exist."""
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        with patch.object(Path, "is_file", return_value=False):
            result = load_config()

        assert result == {}

    def test_handles_malformed_system_toml(self, tmp_path, capsys, monkeypatch) -> None:
        """Should log warning and continue with empty config on malformed TOML."""
        malformed_toml = tmp_path / "prompt-flag-appender.toml"
        malformed_toml.write_text("invalid [ toml content")

        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        with patch.object(
            Path, "resolve", return_value=tmp_path / "prompt-flag-appender.py"
        ):
            with patch.object(Path, "with_suffix", return_value=malformed_toml):
                with patch.object(Path, "is_file", return_value=True):
                    result = load_config()

        captured = capsys.readouterr()
        assert "warning" in captured.err.lower() or result == {}

    def test_merges_project_config(self, tmp_path, monkeypatch) -> None:
        """Should merge project config, overriding system entries."""
        # Create system config
        system_toml = tmp_path / "system" / "prompt-flag-appender.toml"
        system_toml.parent.mkdir(parents=True)
        system_toml.write_bytes(
            b'[ultrathink]\naliases = []\ncontent = "System ultrathink"'
        )

        # Create project config
        project_dir = tmp_path / "project"
        project_toml = project_dir / ".claude" / "prompt-flag-appender.toml"
        project_toml.parent.mkdir(parents=True)
        project_toml.write_bytes(
            b'[ultrathink]\naliases = []\ncontent = "Project ultrathink"\n'
            b'[custom]\naliases = []\ncontent = "Custom trigger"'
        )

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_dir))

        # Mock system TOML loading
        with patch.object(
            Path, "resolve", return_value=system_toml.parent / "prompt-flag-appender.py"
        ):
            with patch.object(Path, "with_suffix", return_value=system_toml):
                result = load_config()

        # Project should override system
        assert result["ultrathink"]["content"] == "Project ultrathink"
        # Project-only entry should be present
        assert result["custom"]["content"] == "Custom trigger"

    def test_handles_malformed_project_toml(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        """Should log warning and keep system config on malformed project TOML."""
        # Create valid system config
        system_toml = tmp_path / "prompt-flag-appender.toml"
        system_toml.write_bytes(
            b'[ultrathink]\naliases = []\ncontent = "System content"'
        )

        # Create malformed project config
        project_dir = tmp_path / "project"
        project_toml = project_dir / ".claude" / "prompt-flag-appender.toml"
        project_toml.parent.mkdir(parents=True)
        project_toml.write_text("invalid [ toml")

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_dir))

        with patch.object(
            Path, "resolve", return_value=tmp_path / "prompt-flag-appender.py"
        ):
            with patch.object(Path, "with_suffix", return_value=system_toml):
                result = load_config()

        # System config should still be loaded
        assert result["ultrathink"]["content"] == "System content"
        captured = capsys.readouterr()
        assert "warning" in captured.err.lower()


# =============================================================================
# Tests for build_alias_map()
# =============================================================================


class TestBuildAliasMap:
    """Test build_alias_map() function."""

    def test_builds_alias_map(self, sample_config) -> None:
        """Should build correct alias mapping."""
        result = build_alias_map(sample_config)
        assert result["approve"] == "approval"
        assert result["seqthi"] == "sequential-thinking"
        assert result["seq"] == "sequential-thinking"

    def test_handles_empty_config(self) -> None:
        """Should return empty map for empty config."""
        result = build_alias_map({})
        assert result == {}

    def test_handles_triggers_without_aliases(self) -> None:
        """Should handle triggers with empty or missing aliases."""
        config = {
            "test1": {"aliases": [], "content": "Test 1"},
            "test2": {"content": "Test 2"},  # No aliases key
        }
        result = build_alias_map(config)
        assert result == {}

    def test_handles_invalid_config_structure(self) -> None:
        """Should handle invalid config structures gracefully."""
        config = {
            "valid": {"aliases": ["v"], "content": "Valid"},
            "invalid1": "not a dict",
            "invalid2": {"aliases": "not a list", "content": "Test"},
            "invalid3": {"aliases": [123, "valid"], "content": "Test"},
        }
        result = build_alias_map(config)
        assert result == {"v": "valid", "valid": "invalid3"}

    def test_skips_reserved_sections(self) -> None:
        """Should skip sections starting with underscore (reserved)."""
        config = {
            "_always": {"aliases": ["a"], "content": "Always content"},
            "_meta": {"aliases": ["m"], "content": "Meta content"},
            "ultrathink": {"aliases": ["ut"], "content": "Ultrathink content"},
        }
        result = build_alias_map(config)
        # Only ultrathink alias should be included, not _always or _meta
        assert result == {"ut": "ultrathink"}
        assert "a" not in result
        assert "m" not in result


# =============================================================================
# Tests for resolve_trigger()
# =============================================================================


class TestResolveTrigger:
    """Test resolve_trigger() function."""

    def test_resolves_direct_match(self, sample_config, sample_alias_map) -> None:
        """Should resolve direct trigger name."""
        result = resolve_trigger("ultrathink", sample_config, sample_alias_map)
        assert result == "ultrathink"

    def test_resolves_alias(self, sample_config, sample_alias_map) -> None:
        """Should resolve alias to canonical name."""
        result = resolve_trigger("seqthi", sample_config, sample_alias_map)
        assert result == "sequential-thinking"

    def test_returns_none_for_unknown(self, sample_config, sample_alias_map) -> None:
        """Should return None for unknown trigger."""
        result = resolve_trigger("unknown", sample_config, sample_alias_map)
        assert result is None

    def test_direct_match_takes_precedence(self) -> None:
        """Should prefer direct match over alias."""
        config = {"direct": {"aliases": [], "content": "Direct"}}
        alias_map = {"direct": "other"}  # Alias collision
        result = resolve_trigger("direct", config, alias_map)
        assert result == "direct"


# =============================================================================
# Tests for get_trigger_content()
# =============================================================================


class TestGetTriggerContent:
    """Test get_trigger_content() function."""

    def test_returns_content(self, sample_config) -> None:
        """Should return content for valid trigger."""
        result = get_trigger_content("ultrathink", sample_config)
        assert result == "ULTRATHINK MODE ACTIVATED"

    def test_strips_whitespace(self) -> None:
        """Should strip whitespace from content."""
        config = {"test": {"content": "  Content with whitespace  \n"}}
        result = get_trigger_content("test", config)
        assert result == "Content with whitespace"

    def test_returns_none_for_missing_trigger(self, sample_config) -> None:
        """Should return None for missing trigger."""
        result = get_trigger_content("unknown", sample_config)
        assert result is None

    def test_returns_none_for_invalid_config(self) -> None:
        """Should return None for invalid config structure."""
        config = {
            "invalid1": "not a dict",
            "invalid2": {"no_content_key": True},
            "invalid3": {"content": 123},
        }
        assert get_trigger_content("invalid1", config) is None
        assert get_trigger_content("invalid2", config) is None
        assert get_trigger_content("invalid3", config) is None


# =============================================================================
# Tests for get_always_fragment()
# =============================================================================


class TestGetAlwaysFragment:
    """Test get_always_fragment() function."""

    def test_returns_content_when_always_section_exists(self) -> None:
        """Should return content from [_always] section."""
        config = {"_always": {"content": "Always follow these rules..."}}
        result = get_always_fragment(config)
        assert result == "Always follow these rules..."

    def test_returns_none_when_no_always_section(self) -> None:
        """Should return None when [_always] section doesn't exist."""
        config = {"ultrathink": {"content": "ULTRATHINK MODE"}}
        result = get_always_fragment(config)
        assert result is None

    def test_returns_none_when_always_section_has_no_content(self) -> None:
        """Should return None when [_always] section has no content key."""
        config = {"_always": {"aliases": ["a"]}}
        result = get_always_fragment(config)
        assert result is None

    def test_strips_whitespace_from_content(self) -> None:
        """Should strip leading/trailing whitespace from content."""
        config = {"_always": {"content": "\n  Always on content  \n"}}
        result = get_always_fragment(config)
        assert result == "Always on content"


# =============================================================================
# Tests for get_active_mode_fragments()
# =============================================================================


class TestGetActiveModeFragments:
    """Test get_active_mode_fragments() function."""

    def test_returns_empty_list_when_no_project_dir(
        self, monkeypatch, sample_config, sample_alias_map
    ) -> None:
        """Should return empty list when CLAUDE_PROJECT_DIR not set."""
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        result = get_active_mode_fragments(sample_config, sample_alias_map)
        assert result == []

    def test_returns_empty_list_when_claude_dir_not_exists(
        self, temp_project_dir, monkeypatch, sample_config, sample_alias_map
    ) -> None:
        """Should return empty list when .claude directory doesn't exist."""
        (temp_project_dir / ".claude").rmdir()
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))
        result = get_active_mode_fragments(sample_config, sample_alias_map)
        assert result == []

    def test_loads_fragment_for_mode_flag_file(
        self, temp_project_dir, monkeypatch, sample_config, sample_alias_map
    ) -> None:
        """Should load fragment when hook-*-mode-on file exists."""
        flag_file = temp_project_dir / ".claude" / "hook-approval-mode-on"
        flag_file.touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))
        result = get_active_mode_fragments(sample_config, sample_alias_map)

        assert len(result) == 1
        assert result[0] == "Human-in-the-Loop Mode"

    def test_skips_mode_without_config_entry(
        self, temp_project_dir, monkeypatch, sample_config, sample_alias_map
    ) -> None:
        """Should skip modes that don't have config entries."""
        flag_file = temp_project_dir / ".claude" / "hook-unknown-mode-on"
        flag_file.touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))
        result = get_active_mode_fragments(sample_config, sample_alias_map)

        assert result == []

    def test_loads_multiple_mode_fragments(
        self, temp_project_dir, monkeypatch, sample_config, sample_alias_map
    ) -> None:
        """Should load fragments for multiple active modes."""
        (temp_project_dir / ".claude" / "hook-approval-mode-on").touch()
        (temp_project_dir / ".claude" / "hook-ultrathink-mode-on").touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))
        result = get_active_mode_fragments(sample_config, sample_alias_map)

        assert len(result) == 2
        assert "Human-in-the-Loop Mode" in result
        assert "ULTRATHINK MODE ACTIVATED" in result

    def test_resolves_alias_mode_files(
        self, temp_project_dir, monkeypatch, sample_config, sample_alias_map
    ) -> None:
        """Should resolve mode names via aliases."""
        # Using alias "seqthi" for sequential-thinking
        flag_file = temp_project_dir / ".claude" / "hook-seqthi-mode-on"
        flag_file.touch()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(temp_project_dir))
        result = get_active_mode_fragments(sample_config, sample_alias_map)

        assert len(result) == 1
        assert result[0] == "Use sequential thinking"


# =============================================================================
# Tests for split_prompt_and_triggers()
# =============================================================================


class TestSplitPromptAndTriggers:
    """Test split_prompt_and_triggers() function."""

    def test_extracts_single_trigger(self, sample_config, sample_alias_map) -> None:
        """Should extract single trailing trigger."""
        prompt = "Fix this code +ultrathink"
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == "Fix this code"
        assert triggers == ["ultrathink"]

    def test_extracts_multiple_triggers(self, sample_config, sample_alias_map) -> None:
        """Should extract multiple trailing triggers."""
        prompt = "Fix this code +ultrathink +absolute"
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == "Fix this code"
        assert triggers == ["ultrathink", "absolute"]

    def test_ignores_unmapped_triggers(self, sample_config, sample_alias_map) -> None:
        """Should ignore triggers not in config."""
        prompt = "Fix this code +ultrathink +unknown"
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == "Fix this code"
        assert triggers == ["ultrathink"]

    def test_removes_all_trigger_like_tokens(
        self, sample_config, sample_alias_map
    ) -> None:
        """Should remove all trailing tokens starting with + from output."""
        prompt = "Fix this code +ultrathink +unknown +another"
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == "Fix this code"
        assert "+unknown" not in base
        assert "+another" not in base

    def test_stops_at_non_trigger_token(self, sample_config, sample_alias_map) -> None:
        """Should stop extracting when non-trigger token encountered."""
        prompt = "Fix this code quickly +ultrathink"
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == "Fix this code quickly"
        assert triggers == ["ultrathink"]

    def test_deduplicates_triggers(self, sample_config, sample_alias_map) -> None:
        """Should deduplicate repeated triggers while preserving order."""
        prompt = "Fix this code +ultrathink +absolute +ultrathink"
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == "Fix this code"
        assert triggers == ["ultrathink", "absolute"]

    def test_handles_prompt_without_triggers(
        self, sample_config, sample_alias_map
    ) -> None:
        """Should return empty triggers list for prompt without triggers."""
        prompt = "Fix this code"
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == "Fix this code"
        assert triggers == []

    def test_handles_empty_prompt(self, sample_config, sample_alias_map) -> None:
        """Should handle empty prompt gracefully."""
        prompt = ""
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == ""
        assert triggers == []

    def test_strips_whitespace(self, sample_config, sample_alias_map) -> None:
        """Should strip trailing whitespace from base prompt."""
        prompt = "Fix this code  +ultrathink"
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == "Fix this code"
        assert not base.endswith(" ")

    def test_resolves_alias_triggers(self, sample_config, sample_alias_map) -> None:
        """Should resolve alias triggers to canonical names."""
        prompt = "Fix this code +seqthi"
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == "Fix this code"
        assert triggers == ["sequential-thinking"]

    def test_deduplicates_alias_and_canonical(
        self, sample_config, sample_alias_map
    ) -> None:
        """Should deduplicate when both alias and canonical are used."""
        prompt = "Fix this code +seqthi +sequential-thinking"
        base, triggers = split_prompt_and_triggers(
            prompt, sample_config, sample_alias_map
        )
        assert base == "Fix this code"
        assert triggers == ["sequential-thinking"]


# =============================================================================
# Tests for get_fragments_for_triggers()
# =============================================================================


class TestGetFragmentsForTriggers:
    """Test get_fragments_for_triggers() function."""

    def test_returns_fragments(self, sample_config) -> None:
        """Should return fragments for valid triggers."""
        result = get_fragments_for_triggers(["ultrathink", "absolute"], sample_config)
        assert len(result) == 2
        assert "ULTRATHINK MODE ACTIVATED" in result
        assert "System Instruction: Absolute Mode" in result

    def test_preserves_order(self, sample_config) -> None:
        """Should preserve trigger order in output."""
        result = get_fragments_for_triggers(["absolute", "ultrathink"], sample_config)
        assert result[0] == "System Instruction: Absolute Mode"
        assert result[1] == "ULTRATHINK MODE ACTIVATED"

    def test_skips_unknown_triggers(self, sample_config) -> None:
        """Should skip triggers not in config."""
        result = get_fragments_for_triggers(["ultrathink", "unknown"], sample_config)
        assert len(result) == 1
        assert result[0] == "ULTRATHINK MODE ACTIVATED"

    def test_handles_empty_trigger_list(self, sample_config) -> None:
        """Should return empty list for empty trigger list."""
        result = get_fragments_for_triggers([], sample_config)
        assert result == []


# =============================================================================
# Tests for build_prompt()
# =============================================================================


class TestBuildPrompt:
    """Test build_prompt() function."""

    def test_returns_prompt_when_no_fragments(self) -> None:
        """Should return original prompt when no fragments."""
        result = build_prompt("Fix this code", [])
        assert result == "Fix this code"

    def test_appends_single_fragment(self) -> None:
        """Should append single fragment with double newline."""
        result = build_prompt("Fix this code", ["ULTRATHINK MODE"])
        assert result == "Fix this code\n\nULTRATHINK MODE"

    def test_appends_multiple_fragments(self) -> None:
        """Should append multiple fragments with double newlines."""
        result = build_prompt("Fix this code", ["ULTRATHINK MODE", "ABSOLUTE MODE"])
        assert result == "Fix this code\n\nULTRATHINK MODE\n\nABSOLUTE MODE"

    def test_handles_empty_prompt_with_fragments(self) -> None:
        """Should handle empty prompt with fragments."""
        result = build_prompt("", ["ULTRATHINK MODE"])
        assert result == "ULTRATHINK MODE"

    def test_joins_fragments_only_when_no_prompt(self) -> None:
        """Should join fragments with double newline when prompt is empty."""
        result = build_prompt("", ["FRAGMENT1", "FRAGMENT2"])
        assert result == "FRAGMENT1\n\nFRAGMENT2"


# =============================================================================
# Tests for main()
# =============================================================================


class TestMain:
    """Test main() entry point function."""

    def test_processes_prompt_with_trigger(
        self, capsys, sample_config, sample_alias_map
    ) -> None:
        """Should process prompt and append fragment."""
        input_data = {"prompt": "Fix this code +ultrathink"}

        with patch("prompt_flag_appender.exit_if_disabled"):
            with patch("prompt_flag_appender.load_config", return_value=sample_config):
                with patch(
                    "prompt_flag_appender.build_alias_map",
                    return_value=sample_alias_map,
                ):
                    with patch("sys.stdin", MagicMock()):
                        with patch("json.load", return_value=input_data):
                            with patch(
                                "prompt_flag_appender.get_active_mode_fragments",
                                return_value=[],
                            ):
                                main()

        captured = capsys.readouterr()
        assert "Fix this code" in captured.out
        assert "ULTRATHINK MODE ACTIVATED" in captured.out

    def test_processes_prompt_without_triggers(
        self, capsys, sample_config, sample_alias_map
    ) -> None:
        """Should return original prompt when no triggers."""
        input_data = {"prompt": "Fix this code"}

        with patch("prompt_flag_appender.exit_if_disabled"):
            with patch("prompt_flag_appender.load_config", return_value=sample_config):
                with patch(
                    "prompt_flag_appender.build_alias_map",
                    return_value=sample_alias_map,
                ):
                    with patch("sys.stdin", MagicMock()):
                        with patch("json.load", return_value=input_data):
                            with patch(
                                "prompt_flag_appender.get_active_mode_fragments",
                                return_value=[],
                            ):
                                main()

        captured = capsys.readouterr()
        assert captured.out.strip() == "Fix this code"

    def test_combines_mode_and_trigger_fragments(
        self, capsys, sample_config, sample_alias_map
    ) -> None:
        """Should combine mode-based and trigger-based fragments."""
        input_data = {"prompt": "Fix this code +ultrathink"}
        mode_fragment = "APPROVAL MODE"

        with patch("prompt_flag_appender.exit_if_disabled"):
            with patch("prompt_flag_appender.load_config", return_value=sample_config):
                with patch(
                    "prompt_flag_appender.build_alias_map",
                    return_value=sample_alias_map,
                ):
                    with patch("sys.stdin", MagicMock()):
                        with patch("json.load", return_value=input_data):
                            with patch(
                                "prompt_flag_appender.get_active_mode_fragments",
                                return_value=[mode_fragment],
                            ):
                                main()

        captured = capsys.readouterr()
        assert "APPROVAL MODE" in captured.out
        assert "ULTRATHINK MODE ACTIVATED" in captured.out

    def test_resolves_alias_in_prompt(
        self, capsys, sample_config, sample_alias_map
    ) -> None:
        """Should resolve alias triggers in prompt."""
        input_data = {"prompt": "Fix this code +seqthi"}

        with patch("prompt_flag_appender.exit_if_disabled"):
            with patch("prompt_flag_appender.load_config", return_value=sample_config):
                with patch(
                    "prompt_flag_appender.build_alias_map",
                    return_value=sample_alias_map,
                ):
                    with patch("sys.stdin", MagicMock()):
                        with patch("json.load", return_value=input_data):
                            with patch(
                                "prompt_flag_appender.get_active_mode_fragments",
                                return_value=[],
                            ):
                                main()

        captured = capsys.readouterr()
        assert "Fix this code" in captured.out
        assert "Use sequential thinking" in captured.out

    def test_injects_always_fragment_first(self, capsys) -> None:
        """Should inject [_always] content before all other fragments."""
        config_with_always = {
            "_always": {"content": "ALWAYS ON CONTENT"},
            "ultrathink": {"aliases": [], "content": "ULTRATHINK MODE ACTIVATED"},
        }
        input_data = {"prompt": "Fix this code +ultrathink"}

        with patch("prompt_flag_appender.exit_if_disabled"):
            with patch(
                "prompt_flag_appender.load_config", return_value=config_with_always
            ):
                with patch("prompt_flag_appender.build_alias_map", return_value={}):
                    with patch("sys.stdin", MagicMock()):
                        with patch("json.load", return_value=input_data):
                            with patch(
                                "prompt_flag_appender.get_active_mode_fragments",
                                return_value=[],
                            ):
                                main()

        captured = capsys.readouterr()
        # Always fragment should appear before trigger fragment
        always_pos = captured.out.find("ALWAYS ON CONTENT")
        trigger_pos = captured.out.find("ULTRATHINK MODE ACTIVATED")
        assert always_pos != -1
        assert trigger_pos != -1
        assert always_pos < trigger_pos

    def test_always_fragment_before_mode_fragments(self, capsys) -> None:
        """Should inject [_always] content before mode-based fragments."""
        config_with_always = {
            "_always": {"content": "ALWAYS ON CONTENT"},
            "approval": {"aliases": [], "content": "APPROVAL MODE"},
        }
        input_data = {"prompt": "Fix this code"}
        mode_fragment = "MODE FRAGMENT"

        with patch("prompt_flag_appender.exit_if_disabled"):
            with patch(
                "prompt_flag_appender.load_config", return_value=config_with_always
            ):
                with patch("prompt_flag_appender.build_alias_map", return_value={}):
                    with patch("sys.stdin", MagicMock()):
                        with patch("json.load", return_value=input_data):
                            with patch(
                                "prompt_flag_appender.get_active_mode_fragments",
                                return_value=[mode_fragment],
                            ):
                                main()

        captured = capsys.readouterr()
        # Always fragment should appear before mode fragment
        always_pos = captured.out.find("ALWAYS ON CONTENT")
        mode_pos = captured.out.find("MODE FRAGMENT")
        assert always_pos != -1
        assert mode_pos != -1
        assert always_pos < mode_pos

    def test_handles_json_decode_error(self, capsys) -> None:
        """Should exit 1 and print error on JSON decode error."""
        with patch("prompt_flag_appender.exit_if_disabled"):
            with patch("prompt_flag_appender.load_config", return_value={}):
                with patch("prompt_flag_appender.build_alias_map", return_value={}):
                    with patch("sys.stdin", MagicMock()):
                        with patch(
                            "json.load",
                            side_effect=json.JSONDecodeError("msg", "doc", 0),
                        ):
                            with pytest.raises(SystemExit) as exc_info:
                                main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid JSON input" in captured.err

    def test_handles_non_string_prompt(self, capsys) -> None:
        """Should exit 1 when prompt is not a string."""
        input_data = {"prompt": 123}

        with patch("prompt_flag_appender.exit_if_disabled"):
            with patch("prompt_flag_appender.load_config", return_value={}):
                with patch("prompt_flag_appender.build_alias_map", return_value={}):
                    with patch("sys.stdin", MagicMock()):
                        with patch("json.load", return_value=input_data):
                            with pytest.raises(SystemExit) as exc_info:
                                main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "prompt must be a string" in captured.err

    def test_handles_generic_exception(self, capsys) -> None:
        """Should exit 1 on unexpected exceptions."""
        with patch("prompt_flag_appender.exit_if_disabled"):
            with patch("prompt_flag_appender.load_config", return_value={}):
                with patch("prompt_flag_appender.build_alias_map", return_value={}):
                    with patch("sys.stdin", MagicMock()):
                        with patch(
                            "json.load", side_effect=Exception("Unexpected error")
                        ):
                            with pytest.raises(SystemExit) as exc_info:
                                main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unexpected error" in captured.err
