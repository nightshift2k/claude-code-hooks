# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.9] - 2025-12-26

### Added

- **prompt-flag-appender.py** - Always-on injection via special `[_always]` section in TOML config. Content is injected at the start of every prompt, before mode and trigger fragments. Useful for persistent project-specific instructions.

### Changed

- **prompt-flag-appender.py** - Refactored to use single TOML configuration file instead of multiple markdown fragments. Triggers and their content are now defined in `prompt-flag-appender.toml` with support for aliases (e.g., `+seq` → `sequential-thinking`). Supports project-level overrides via `$CLAUDE_PROJECT_DIR/.claude/prompt-flag-appender.toml` that merge with system config (project wins on conflicts). Mode flag files (`.claude/hook-*-mode-on`) now resolve through the TOML trigger system, gaining alias support.

### Removed

- **hooks/prompt-fragments/** - Deleted directory containing individual markdown fragment files (ultrathink.md, absolute.md, approval.md, sequential-thinking.md). Content migrated to consolidated `prompt-flag-appender.toml`.

### Fixed

- **Documentation sync** - Corrected `serena_awareness.py` filename references (was incorrectly using hyphen instead of underscore in settings.json.example and README). Added missing hooks to CLAUDE.md (changelog-reminder, release-check, release-reminder). Updated README example to use Python 3.12+ type hints (`dict[str, Any]` instead of `Dict[str, Any]`).

## [0.1.8] - 2025-12-22

### Added

- **serena-awareness.py** - New UserPromptSubmit hook that detects Serena-configured projects on first prompt, suggesting `activate_project` or `onboarding` for optimal MCP integration. Features session-aware first-prompt detection via marker files, aggressive mode toggle via flag file (`.claude/hook-serena-awareness-aggressive-on`), stdlib-only YAML parsing, language detection for 30+ programming languages, and self-cleaning session markers (7-day expiry).

### Changed

- **serena-awareness.py** - Session markers now stored in project-local `.claude/hook_serena_awareness_session_markers/` instead of global `~/.claude/session_markers/`.

### Fixed

- **Security: CLAUDE_PROJECT_DIR** - Replaced dangerous `Path.cwd()` and `os.getcwd()` with `CLAUDE_PROJECT_DIR` environment variable in `large-file-awareness.py`, `release-check.py`, and `doc-update-check.py`. The env var is stable across directory changes, preventing potential path confusion attacks.

## [0.1.7] - 2025-12-21

### Added

- **large-file-awareness.py** - New SessionStart hook that scans project at session start and injects awareness of large files (>500 lines) to enable efficient navigation strategies. Works with large-file-guard for defense-in-depth. Features git-based file discovery with os.walk fallback, top 10 largest files display with tool recommendations (Serena for code, Grep for data, Read offset/limit for text), and configurable threshold via `LARGE_FILE_THRESHOLD` env var or `largeFileThreshold` in settings.json.



- **hook_utils.py** - Added language detection utilities: `FilenameMatcher` class for glob-pattern matching, `Language` enum with 30+ programming languages (Python, TypeScript, Rust, Go, Java, etc.) and their file patterns, `detect_project_languages()` function that scans directory trees. Also added utilities for file analysis: `classify_file()`, `estimate_tokens()`, `count_lines()`, `get_large_file_threshold()`.

### Changed

- **Python requirement** - Bumped minimum Python version from 3.8 to 3.12 for modern type hint support (dict, list, X | None syntax)
- **All hooks** - Applied ruff auto-fixes to modernize type hints: `Dict` → `dict`, `List` → `list`, `Optional[X]` → `X | None`
- **CI workflows** - Updated test.yml and lint.yml to run only on Python 3.12 (removed 3.8, 3.9, 3.10, 3.11 from matrix)
- **pyproject.toml** - Updated `requires-python = ">=3.12"` and `target-version = "py312"`
- **README.md** - Updated Python badge from 3.8+ to 3.12+, added serena-awareness to features table
- **hook_utils.py** - Added shared utilities for file analysis: `classify_file()` (binary/code/data/unknown classification), `estimate_tokens()` (3.5 chars/token ratio), `count_lines()` (memory-efficient streaming line counter), `get_large_file_threshold()` (configurable threshold with settings.json, env var, and default fallback).
## [0.1.6] - 2025-12-21

### Added

- **release-check.py** - Human-in-the-loop confirmation for release operations. Hook now requires explicit user approval before `git tag v*` (via `CONFIRM_TAG=1`) and `gh release create v*` (via `CONFIRM_RELEASE=1`). Ensures humans stay in the loop for critical release actions.

- **release-reminder.py** - Added step 5 to checklist: reminder to run `gh release create` after tagging.

- **CLAUDE.md** - Added Releasing workflow to Git Conventions section.

## [0.1.5] - 2025-12-21

### Added

- **git-branch-protection.py** - Bash file-write pattern detection. Hook now analyzes bash commands for potential file-writing operations (`sed -i`, `perl -i`, `>`, `>>`, `tee`, heredocs) and outputs a reflective question asking Claude to verify if the command writes files when on protected branches. Unlike Edit/Write tools (which are blocked), bash commands trigger analysis rather than blocking to reduce false positives.

### Fixed

- **settings.json.example** - Fixed git-branch-protection matcher regex from `Edit|Write|...` to `^(Edit|Write)$|...` to prevent false positives with TodoWrite tool.

## [0.1.4] - 2025-12-21

### Added

- **CI/CD** - Added GitHub Actions test workflow (`test.yml`) that runs pytest across Python 3.8-3.12 on push to main and pull requests.

- **changelog-reminder.py** - New hook that blocks git commits when meaningful files are staged without CHANGELOG.md update. Enforces changelog hygiene by requiring documentation of production code changes. Filters out non-meaningful files (tests, .github, __pycache__, .md, .gitignore, .claude). Supports `SKIP_CHANGELOG_CHECK=1` bypass and project-level disabling via `.claude/disabled-hooks`.

- **release-reminder.py** - New UserPromptSubmit hook that reminds about release verification checklist when release-related keywords are detected (`release`, `tag v`, `version bump`, `prepare release`, version patterns). Provides pre-flight checklist for CHANGELOG.md updates, version file synchronization, clean working tree, and branch verification.

- **release-check.py** - New PreToolUse Bash hook that blocks `git tag v*` commands when the version is not found in CHANGELOG.md. Simple safety net to ensure documentation is updated before releases. Supports `SKIP_RELEASE_CHECK=1` bypass. Fail-open for projects without CHANGELOG.md.

## [0.1.3] - 2025-12-21

### Added

- **prompt-flag-appender.py** - Added `+seqthi` trigger for invoking sequential thinking MCP tool during complex analysis tasks.

- **doc-update-check.py** - AI-powered merge detection mode using Claude Haiku. Enable with `DOC_CHECK_USE_AI=1` environment variable or `.claude/hook-doc-check-ai-mode-on` flag file for semantic understanding of complex merge commands.

- **Test Suite** - Comprehensive pytest test suite with 221 tests covering all hooks. Run with `uv run pytest tests/ -v`.

### Fixed

- **doc-update-check.py** - Fixed false positives from commit messages containing "merge" text. Now correctly extracts git subcommand instead of substring matching.

- **doc-update-check.py** - Fixed `extract_merge_target()` to correctly parse branch names when options like `--no-ff`, `--squash`, or `-m` are used.

## [0.1.2] - 2025-12-14

### Added

- **prompt-flag-appender.py** - Session-based modes via flag files. Enable persistent modes by creating `.claude/hook-<mode>-mode-on` files in project root. Example: `touch .claude/hook-approval-mode-on` enables approval mode for entire session without per-prompt triggers.

- **doc-update-check.py** - Optional `.doc-check-ignore` file for excluding documentation files from merge-to-main check. Supports gitignore-style patterns (*, **, path matching). Useful for excluding planning docs, brainstorms, and temporary markdown files.

### Changed

- **prompt-flag-appender.py** - Refactored trigger processing to support both per-prompt triggers (+ultrathink) and session modes (flag files). Session modes are injected first, then prompt triggers are appended.

## [0.1.1] - 2025-12-12

### Added

- **doc-update-check.py** - New hook that blocks merge-to-main operations unless documentation files (*.md) have been modified. Enforces documentation hygiene by requiring doc updates when merging to main/master branches. Supports `SKIP_DOC_CHECK=1` environment variable bypass.

- **git-commit-message-filter.py** - New hook that blocks git commit commands containing Claude auto-generated markers (Generated with Claude Code, Co-Authored-By: Claude, etc.). Ensures custom, meaningful commit messages instead of auto-generated attribution.

### Fixed

- **git-safety-check.py** - Fixed false positive when `--no-verify` appears in commit messages or heredocs. Now only blocks when `--no-verify` is used as a command argument, not when it's part of message content.

- **git-safety-check.py** - Fixed false positive when protected branch names appear in chained commands. Now uses word boundaries and specific separators (&&, ;, |, end of command) to match exact branch deletion commands.

## [0.1.0] - 2025-12-11

### Added

- **git-branch-protection.py** - Blocks file edits on protected branches (main, master, production, prod). Prevents accidental modifications on stable branches.

- **git-safety-check.py** - Blocks dangerous git operations including `--no-verify` flag usage and deletion of protected branches (main, master, production, prod).

- **python-uv-enforcer.py** - Enforces modern Python tooling by blocking direct pip/python/pytest usage and suggesting uv alternatives.

- **environment-awareness.py** - Injects environment context (date, time, timezone, OS, working directory) at session start and resume.

- **rules-reminder.py** - Reminds Claude to check project rules (CLAUDE.md, .claude/rules/*) on session start and when implementation keywords are detected.

- **prompt-flag-appender.py** - Appends markdown fragments based on trigger words (+ultrathink, +absolute, +approval). Enables per-prompt behavior modification.

- **hook_utils.py** - Shared utilities for hooks including Colors class (ANSI color formatting), exit_if_disabled() (hook disabling via .claude/disabled-hooks), and get_hook_name() (automatic hook name detection).

### Infrastructure

- Project structure with hooks/, tests/, and comprehensive documentation.
- settings.json.example with hook configurations for SessionStart, UserPromptSubmit, and PreToolUse events.
- Python 3.8+ compatibility with stdlib-only dependencies.
- MIT License.
