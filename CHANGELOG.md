# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-14

### Added

- **hook_utils.py** - Shared utilities with `exit_if_disabled()` and `Colors` class
- **environment-awareness.py** - Injects date, time, timezone, OS, and working directory at session start
- **git-branch-protection.py** - Blocks file edits on protected branches (main, master, production, prod)
- **git-safety-check.py** - Blocks `--no-verify` flag and protected branch deletion
- **git-commit-message-filter.py** - Blocks Claude auto-generated attribution in commits
- **python-uv-enforcer.py** - Enforces `uv` over direct pip/python usage
- **rules-reminder.py** - Reminds about CLAUDE.md and .claude/rules/* on session start and prompts
- **prompt-flag-appender.py** - Injects markdown fragments via `+ultrathink`, `+absolute` triggers
- Per-project disable mechanism via `.claude/disabled-hooks` file
- MIT License
- README with installation and usage documentation
