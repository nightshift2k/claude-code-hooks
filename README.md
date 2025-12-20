# Claude Code Hooks

Protect your codebase and enhance Claude Code with safety guardrails, standard enforcement, and context injection.

## Installation

1. Copy the `hooks/` directory to `~/.claude/hooks/`
2. Merge `settings.json.example` into `~/.claude/settings.json`

```bash
# Copy hooks
cp -r hooks/* ~/.claude/hooks/

# Make executable
chmod +x ~/.claude/hooks/*.py
```

## Available Hooks

### Safety & Guardrails

| Hook | Event | Description |
|------|-------|-------------|
| `git-branch-protection.py` | PreToolUse (Edit/Write) | Blocks file edits on protected branches (main, master, production, prod) |
| `git-safety-check.py` | PreToolUse (Bash) | Blocks `--no-verify`, protected branch deletion |
| `git-commit-message-filter.py` | PreToolUse (Bash) | Blocks Claude auto-generated attribution in commits |
| `doc-update-check.py` | PreToolUse (Bash) | Blocks merge-to-main without documentation updates |
| `python-uv-enforcer.py` | PreToolUse (Bash) | Enforces `uv` over direct pip/python usage |

### Context & Prompts

| Hook | Event | Description |
|------|-------|-------------|
| `environment-awareness.py` | SessionStart | Injects date, time, timezone, OS, and working directory |
| `rules-reminder.py` | SessionStart, UserPromptSubmit | Reminds Claude about CLAUDE.md and .claude/rules/* |
| `prompt-flag-appender.py` | UserPromptSubmit | Injects markdown via `+ultrathink`, `+absolute`, `+approval` triggers |

### Shared Utilities

| File | Description |
|------|-------------|
| `hook_utils.py` | Shared utilities: `exit_if_disabled()`, `Colors` class |

## Disabling Hooks Per-Project

Create `.claude/disabled-hooks` in your project root:

```
# Disable uv enforcement for legacy Python project
python-uv-enforcer

# Allow edits on main for initial setup
git-branch-protection

# Skip doc check during rapid prototyping
doc-update-check
```

Lines starting with `#` are comments.

## Hook Details

### git-branch-protection.py

Prevents accidental edits on protected branches.

```
$ edit file on main branch
❌ Cannot edit files on protected branch 'main'!
📝 Create a feature branch first:
   git checkout -b feature/your-feature-name
💡 Or disable this hook:
   echo "git-branch-protection" >> .claude/disabled-hooks
```

**Protected branches:** main, master, production, prod

### git-safety-check.py

Blocks dangerous git operations.

```
$ git commit --no-verify
❌ Using --no-verify to skip Git hooks is prohibited!

$ git branch -D main
❌ Blocked: Cannot delete protected branch 'main'
```

### git-commit-message-filter.py

Blocks commits with Claude auto-generated markers.

```
$ git commit -m "Fix bug\n\n🤖 Generated with Claude Code..."
❌ Commit message contains auto-generated Claude markers. Please use a custom commit message.
```

### doc-update-check.py

Ensures documentation is updated when merging to main.

```
$ git merge feature-branch  # on main branch
❌ No documentation updates detected in this branch.

📝 Files checked: CHANGELOG.md, README.md, *.md (excluding .doc-check-ignore patterns)

💡 Options:
   1. Update relevant documentation, then retry merge
   2. If no docs needed, ask user to confirm, then run:
      SKIP_DOC_CHECK=1 git merge <branch>

🔍 Branch diff: git diff main...HEAD --name-only
```

**Detects merge-to-main via:**
- `git merge` while on main branch
- `git checkout main && git merge` command chains
- `gh pr merge` operations

**Skip conditions:**
- `SKIP_DOC_CHECK=1` environment variable
- Hook disabled via `.claude/disabled-hooks`
- `.doc-check-ignore` patterns (optional)

**Example `.doc-check-ignore`:**
```
# Exclude planning and brainstorming
docs/plans/**
docs/brainstorms/**

# Exclude temporary files
*-todo.md
*-scratch.md
*-draft.md
```

### python-uv-enforcer.py

Enforces modern Python tooling.

```
$ pip install requests
❌ Direct Python tool usage detected!
📝 Command blocked: pip install requests
✨ Use uv instead:
   uv pip install ...
💡 Learn more: https://github.com/astral-sh/uv
```

### environment-awareness.py

Injects system environment context at session start and resume.

```
## Environment
- Date: 2025-12-14 (Sunday)
- Time: 14:32 CET
- OS: macOS 15.1
- Directory: ~/code/my-project
```

### rules-reminder.py

Reminds Claude to check project rules on:
- Session start/resume (always)
- User prompts containing implementation keywords (implement, fix, refactor, design, etc.)

```
## Project Rules Reminder

This project may have rules defined in:
- CLAUDE.md (project root and .claude/ directory)
- .claude/rules/* (rule files)

Review and follow all project rules strictly before making changes.
```

### prompt-flag-appender.py

Appends markdown fragments based on trigger words or session modes.

#### Per-Prompt Triggers

| Trigger | File | Effect |
|---------|------|--------|
| `+ultrathink` | ultrathink.md | Deep analysis mode |
| `+absolute` | absolute.md | Direct, no-filler responses |
| `+approval` | approval.md | Human-in-the-loop mode (propose, don't execute) |

**Usage:**
```
refactor this code +ultrathink
help me understand this +absolute
implement feature +approval
complex task +ultrathink +absolute
```

#### Session-Based Modes

Enable modes for the entire session via flag files in `~/.claude/`:

```bash
# Enable approval mode for entire session
touch ~/.claude/hook-approval-mode-on

# Now every prompt includes approval mode fragment
# No need to add +approval to each prompt

# Disable approval mode
rm ~/.claude/hook-approval-mode-on
```

**Mode precedence:** Session modes are injected first, then per-prompt triggers are appended.

**Example:**
```bash
# Enable approval mode for session
touch ~/.claude/hook-approval-mode-on

# This prompt gets both approval mode (from flag file) and ultrathink (from trigger)
"refactor this code +ultrathink"
```

#### Adding Custom Triggers

1. Create markdown file in `~/.claude/hooks/prompt-fragments/`
2. Add mapping to `TRIGGER_FILE_MAP` in `prompt-flag-appender.py`:

```python
TRIGGER_FILE_MAP = {
    "+ultrathink": "ultrathink.md",
    "+absolute": "absolute.md",
    "+approval": "approval.md",
    "+concise": "concise.md",  # your custom trigger
}
```

#### Adding Custom Session Modes

1. Create markdown file in `~/.claude/hooks/prompt-fragments/<mode>.md`
2. Add trigger mapping to `TRIGGER_FILE_MAP` (optional, if you want both trigger and mode support)
3. Create flag file: `touch ~/.claude/hook-<mode>-mode-on`

**Example: Adding "verbose" mode**
```bash
# 1. Create fragment
cat > ~/.claude/hooks/prompt-fragments/verbose.md << 'EOF'
---
## Verbose Mode
Provide detailed explanations with step-by-step reasoning.
---
EOF

# 2. (Optional) Add to TRIGGER_FILE_MAP for +verbose trigger support

# 3. Enable as session mode
touch ~/.claude/hook-verbose-mode-on
```

## Configuration

### settings.json Structure

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {"type": "command", "command": "~/.claude/hooks/environment-awareness.py"},
          {"type": "command", "command": "~/.claude/hooks/rules-reminder.py"}
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {"type": "command", "command": "~/.claude/hooks/prompt-flag-appender.py"},
          {"type": "command", "command": "~/.claude/hooks/rules-reminder.py"}
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "~/.claude/hooks/git-commit-message-filter.py"},
          {"type": "command", "command": "~/.claude/hooks/python-uv-enforcer.py"},
          {"type": "command", "command": "~/.claude/hooks/git-safety-check.py"},
          {"type": "command", "command": "~/.claude/hooks/doc-update-check.py"}
        ]
      },
      {
        "matcher": "Edit|Write|mcp__morphllm.*|mcp__serena.*(replace|insert).*",
        "hooks": [
          {"type": "command", "command": "~/.claude/hooks/git-branch-protection.py"}
        ]
      }
    ]
  }
}
```

### Hook Output Behavior

| Event | stdout behavior |
|-------|-----------------|
| SessionStart | Injected as context |
| UserPromptSubmit | Injected as context |
| PreToolUse | Shown in verbose mode only |

| Exit code | Effect |
|-----------|--------|
| 0 | Success (stdout processed per event type) |
| 2 | Block action, show stderr as error |
| 1/other | Non-blocking, stderr shown in verbose mode |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `CLAUDE_PROJECT_DIR` | Project root directory |
| `CLAUDE_CODE_REMOTE` | "true" if web, empty if CLI |
| `SKIP_DOC_CHECK` | "1" to bypass doc-update-check hook |

## Development

### Adding a New Hook

1. Create `hooks/your-hook.py`:

```python
#!/usr/bin/env python3
"""Your Hook - Description."""

import json
import sys
from typing import Dict, Any

from hook_utils import exit_if_disabled, Colors


def main() -> None:
    exit_if_disabled()

    try:
        input_data: Dict[str, Any] = json.load(sys.stdin)
        # Your logic here
        sys.exit(0)
    except Exception:
        sys.exit(0)  # Silent failure


if __name__ == "__main__":
    main()
```

2. Make executable: `chmod +x hooks/your-hook.py`
3. Add to `settings.json.example`
4. Test: `echo '{"tool_name": "Bash", "tool_input": {"command": "test"}}' | python3 your-hook.py`

### Testing Hooks

```bash
# Test PreToolUse hook
echo '{"tool_name": "Bash", "tool_input": {"command": "pip install foo"}}' | python3 python-uv-enforcer.py

# Test UserPromptSubmit hook
echo '{"hook_event_name": "UserPromptSubmit", "prompt": "implement feature"}' | python3 rules-reminder.py

# Test SessionStart hook
echo '{"hook_event_name": "SessionStart"}' | python3 rules-reminder.py

# Test doc-update-check hook
echo '{"tool_name": "Bash", "tool_input": {"command": "git merge feature"}}' | python3 doc-update-check.py

# Test prompt-flag-appender with triggers
echo '{"hook_event_name": "UserPromptSubmit", "prompt": "fix this +ultrathink +approval"}' | python3 prompt-flag-appender.py

# Test prompt-flag-appender with session mode
touch ~/.claude/hook-approval-mode-on
echo '{"hook_event_name": "UserPromptSubmit", "prompt": "fix this"}' | python3 prompt-flag-appender.py
rm ~/.claude/hook-approval-mode-on
```

## License

MIT
