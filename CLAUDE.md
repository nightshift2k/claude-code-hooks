# Claude Code Hooks Development

## Project
Protect your codebase and enhance Claude Code with safety guardrails, standard enforcement, and context injection.

## Hooks
- `environment-awareness` - Injects date, time, timezone, OS, and directory at session start
- `git-branch-protection` - Blocks file edits on protected branches (main, master, production, prod)
- `git-safety-check` - Blocks --no-verify flag and protected branch deletion
- `git-commit-message-filter` - Blocks commits containing Claude auto-generated attribution
- `doc-update-check` - Blocks merge-to-main without documentation updates
- `python-uv-enforcer` - Blocks direct pip/python usage, enforces uv
- `rules-reminder` - Reminds Claude about CLAUDE.md and .claude/rules/* on session start and implementation prompts
- `prompt-flag-appender` - Injects markdown fragments via +triggers (+ultrathink, +absolute)

## Structure
- `hooks/*.py` - Hook scripts (stdlib only, Python 3.8+)
- `hooks/hook_utils.py` - Shared utilities (Colors, exit_if_disabled)
- `hooks/prompt-fragments/*.md` - Prompt injection templates
- `settings.json.example` - Hook configuration template

## Rules
- All hooks use `#!/usr/bin/env python3`
- Import `exit_if_disabled` from `hook_utils` at entry
- Use `Colors` class for terminal output
- Silent failure: `except Exception: sys.exit(0)`
- Exit 0 = success, Exit 2 = block action
- Type hints required

## Git Conventions
**Commits**: `type(scope): description` (imperative, <50 chars, lowercase, no period)

| Type | Usage | Type | Usage |
|------|-------|------|-------|
| `feat` | New feature | `fix` | Bug fix |
| `refactor` | Code restructure | `docs` | Documentation |
| `test` | Tests | `chore` | Build/deps |

**Branches**: `feature/*`, `fix/*`, `refactor/*`, `docs/*` - never commit directly to main

## Security
- Never log/print stdin data (may contain secrets)
- Validate JSON input, fail silently on malformed data
- No network calls - offline operation only
- No file writes outside explicit hook purpose

## Code Quality
- Format with `ruff format` before commit
- Lint with `ruff check` before push
- All functions require docstrings

## Compatibility
- Python 3.8+ stdlib only (no external dependencies)
- Cross-platform: macOS, Linux, Windows (Git Bash)
