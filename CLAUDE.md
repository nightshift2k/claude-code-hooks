# Claude Code Hooks Development

## Project
Safety guardrails, standard enforcement, and context injection for Claude Code.

## Hooks
- `environment-awareness` - Injects date, time, timezone, OS, directory at session start
- `large-file-awareness` - Scans project at session start, warns about large files for efficient navigation
- `serena-awareness` - Detects Serena projects on first prompt, suggests activate_project or onboarding
- `git-branch-protection` - Blocks edits to protected branches (main, master, production, prod)
- `git-safety-check` - Blocks --no-verify flag and protected branch deletion
- `git-commit-message-filter` - Blocks commits with Claude auto-generated attribution
- `doc-update-check` - Blocks merge-to-main without documentation updates
- `python-uv-enforcer` - Blocks pip/python, enforces uv
- `rules-reminder` - Reminds Claude about CLAUDE.md and .claude/rules/* at session start and implementation
- `prompt-flag-appender` - Injects markdown fragments via +triggers (+ultrathink, +absolute)
- `large-file-guard` - Blocks Read for large files (>500 lines), suggests Serena/Grep alternatives

## Structure
- `hooks/*.py` - Hook scripts (stdlib only, Python 3.12+)
- `hooks/hook_utils.py` - Shared utilities (Colors, exit_if_disabled, Language detection)
- `hooks/prompt-fragments/*.md` - Prompt injection templates
- `settings.json.example` - Hook configuration template

## Development Setup
- Enable pre-commit: `git config core.hooksPath .githooks`
- Run tests: `uv run pytest tests/ -v`
- Format: `uv run ruff format hooks/`
- Lint: `uv run ruff check hooks/`

## Local Installation
- Copy hooks: `cp hooks/*.py ~/.claude/hooks/`
- Verify sync: `diff -rq hooks/ ~/.claude/hooks/ | grep differ`

## Rules
- Start all hooks with `#!/usr/bin/env python3`
- Import `exit_if_disabled` from `hook_utils` at entry
- Use `Colors` class for terminal output
- Silent failure: `except Exception: sys.exit(0)`
- Exit 0 = success, Exit 2 = block action
- Type hints required
- Anchor settings.json matchers with `^(ToolName)$` to avoid substring matches
- Use `re.DOTALL` or word boundaries for patterns in quoted strings
- Use explicit separators `(\s|$|&&|;|\|)` for command/branch name matching

## Git Conventions
**Commits**: `type(scope): description` (imperative, <50 chars, lowercase, no period)

| Type | Usage | Type | Usage |
|------|-------|------|-------|
| `feat` | New feature | `fix` | Bug fix |
| `refactor` | Code restructure | `docs` | Documentation |
| `test` | Tests | `chore` | Build/deps |

**Branches**: `feature/*`, `fix/*`, `refactor/*`, `docs/*` - never commit to main

**Merging**: Squash before merge: `git reset --soft origin/main && git commit`

**Releasing**: After tagging, create GitHub release: `gh release create v0.1.x --notes "..."`

## Security
- Never log/print stdin data (may contain secrets)
- Validate JSON input, fail silently on malformed data
- Offline only - no network calls
- No file writes beyond explicit hook purpose

## Design Principles
- Fail open: Silent failure (exit 0) on unexpected exceptions
- Defense in depth: Layer multiple hooks for different failure modes
- Pragmatic trade-offs: Better UX with gaps than strict but annoying
- Document limitations: Write tests for edge cases and false positives

## Code Quality
- Write failing tests before implementation (TDD)
- Test edge cases explicitly, including known false positives
- Format with `ruff format` before commit
- Lint with `ruff check` before push
- Run `uv run ruff format hooks/` after subagent code generation
- All functions need docstrings

## Compatibility
- Python 3.12+ stdlib only (no external dependencies)
- Cross-platform: macOS, Linux, Windows (Git Bash)
