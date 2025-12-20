# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Do not open public issues for security vulnerabilities.**

To report a security issue, use one of the following methods:

1. **GitHub Security Advisories** (preferred)
   - Navigate to the repository's Security tab
   - Click "Report a vulnerability"
   - Provide detailed information about the issue

2. **Email**
   - Send details to the repository maintainer
   - Include "SECURITY" in the subject line
   - Provide reproduction steps and impact assessment

## What Constitutes a Security Issue

Given that hooks execute code in user environments, security issues include:

- **Arbitrary code execution** beyond documented hook behavior
- **Privilege escalation** or unauthorized system access
- **Information disclosure** of sensitive user data or credentials
- **Path traversal** vulnerabilities in file operations
- **Command injection** through unsanitized inputs
- **Bypass of safety mechanisms** (e.g., circumventing git-safety-check)

## Response Timeline

- **Initial response**: Within 72 hours
- **Status update**: Within 7 days
- **Resolution target**: 30 days for critical issues, 90 days for moderate issues

Security fixes will be released as patch versions and documented in release notes without exposing exploitation details until users have time to update.

## Security Best Practices

When using claude-code-hooks:

- Review hook source code before installation
- Keep hooks updated to the latest version
- Use `settings.json` to disable untrusted or unnecessary hooks
- Monitor hook execution logs for unexpected behavior
- Report suspicious activity immediately
