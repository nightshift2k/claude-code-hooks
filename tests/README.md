# Test Suite for Claude Code Hooks

## Overview

Comprehensive test suite covering all hooks with 219 tests targeting 100% code coverage.

## Test Files

| Test File | Tests | Description |
|-----------|-------|-------------|
| test_hook_utils.py | 21 | Shared utilities (Colors, exit_if_disabled) |
| test_environment_awareness.py | 11 | Session start environment injection |
| test_git_branch_protection.py | 15 | Protected branch edit blocking |
| test_git_safety_check.py | 22 | Dangerous git operation blocking |
| test_git_commit_message_filter.py | 13 | Claude attribution filtering |
| test_doc_update_check.py | 82 | Merge-to-main documentation enforcement |
| test_python_uv_enforcer.py | 14 | Python tooling enforcement |
| test_rules_reminder.py | 11 | Project rules reminder injection |
| test_prompt_flag_appender.py | 30 | Prompt fragment injection |
| **Total** | **219** | |

## Running Tests

### Run all tests
```bash
uv run pytest tests/ -v
```

### Run with coverage
```bash
uv run pytest tests/ --cov=hooks
```

### Run specific test file
```bash
uv run pytest tests/test_git_safety_check.py -v
```

### Run specific test class
```bash
uv run pytest tests/test_doc_update_check.py::TestIsMergeToMain -v
```

### Run specific test
```bash
uv run pytest tests/test_doc_update_check.py::TestIsMergeToMain::test_detects_gh_pr_merge -v
```

## Test Organization

### test_hook_utils.py (21 tests)
Tests for shared utilities:
- Colors class ANSI code generation
- exit_if_disabled() hook disable detection
- Environment variable handling
- File-based hook disable mechanism
- Error handling and edge cases

### test_environment_awareness.py (11 tests)
Tests for environment context injection:
- Date, time, and timezone formatting
- OS detection and platform information
- Working directory resolution
- SessionStart event handling
- Error handling for edge cases

### test_git_branch_protection.py (15 tests)
Tests for protected branch edit blocking:
- Edit/Write tool blocking on protected branches
- Protected branch detection (main, master, production, prod)
- Feature branch edit allowance
- Error handling (git command failures)
- MCP tool integration (morphllm, serena)

### test_git_safety_check.py (22 tests)
Tests for dangerous git operation blocking:
- --no-verify flag detection
- Protected branch deletion blocking
- Command chaining and complex scenarios
- False positive prevention
- Error handling

### test_git_commit_message_filter.py (13 tests)
Tests for Claude attribution filtering:
- Auto-generated marker detection
- Commit message parsing
- Command chain handling
- Bypass mechanisms
- Error handling

### test_doc_update_check.py (82 tests)
Tests for merge-to-main documentation enforcement:
- Merge-to-main detection (git merge, gh pr merge, command chains)
- Documentation modification checking
- .doc-check-ignore pattern support
- SKIP_DOC_CHECK bypass
- AI-powered merge detection mode
- Integration tests for end-to-end workflows
- Error handling and edge cases

### test_python_uv_enforcer.py (14 tests)
Tests for Python tooling enforcement:
- pip/python command detection
- uv enforcement messaging
- Command chain handling
- Allow-listed commands
- Error handling

### test_rules_reminder.py (11 tests)
Tests for project rules reminder:
- SessionStart event handling
- UserPromptSubmit event handling
- Implementation keyword detection
- Rule file existence checking
- Error handling

### test_prompt_flag_appender.py (30 tests)
Tests for prompt fragment injection:
- Per-prompt trigger detection (+ultrathink, +absolute, +approval)
- Session-based mode flag files (hook-*-mode-on)
- Multiple trigger handling
- Fragment file loading
- Mode precedence and combination
- Error handling

## Shared Fixtures

Located in `tests/conftest.py`:
- Module path configuration for imports
- Common test data structures
- Mock tool invocation JSON
- Shared test utilities

## Test Methodology

### Mocking Strategy
- `subprocess.run` - Mocked for all git/system commands
- `sys.stdin.read` - Mocked for hook JSON input
- `Path.exists` and `Path.open` - Mocked for file operations
- `os.environ` - Patched for environment variables
- Hook utility functions - Mocked to bypass disable checks

### Edge Cases Covered
- Git command failures (non-zero exit codes)
- Subprocess timeouts
- Missing binaries (FileNotFoundError)
- OS-level errors (OSError)
- Malformed JSON input
- Missing or empty fields
- File read/write errors
- Empty command outputs
- Regex limitations and boundary conditions

## Dependencies

- pytest >= 7.0.0
- pytest-cov (for coverage reports)
- Python 3.8+ (stdlib only for hook code)

## Project Conventions

Tests follow project conventions:
- Python 3.8+ compatibility
- Type hints on all functions
- Clear docstrings for test purposes
- Comprehensive edge case coverage
- Integration tests for end-to-end workflows
- Silent failure pattern (except Exception: sys.exit(0))
