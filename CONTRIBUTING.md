# Contributing to Claude Code Hooks

## Getting Started

1. **Fork the repository**
2. **Create a feature branch** following naming conventions:
   - `feature/your-feature-name`
   - `fix/issue-description`
   - `refactor/component-name`
   - `docs/documentation-update`
3. **Make your changes**
4. **Submit a pull request** to the main repository

## Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature or hook
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior changes
- `docs`: Documentation updates
- `test`: Test additions or modifications
- `chore`: Maintenance tasks

**Examples:**
```
feat(hooks): add python-uv-enforcer hook
fix(git-safety-check): handle branch deletion edge case
docs(readme): clarify installation instructions
```

## Code Requirements

All hook contributions must follow these standards:

- **Python version**: 3.8+ compatibility required
- **Dependencies**: Standard library only (no external packages)
- **Type hints**: Required for all functions and methods
- **Docstrings**: Required for all public functions
- **Shebang**: Use `#!/usr/bin/env python3`
- **Error handling**: Silent failure with `sys.exit(0)` for unexpected errors
- **Hook utilities**: Import `exit_if_disabled` from `hook_utils` at entry point
- **Terminal output**: Use `Colors` class from `hook_utils`
- **Exit codes**:
  - `0` = success/allow action
  - `2` = block action

## Testing Your Hooks

Test hooks locally before submitting:

1. Copy your hook to `hooks/` directory
2. Configure hook settings in your `settings.json`
3. Test all execution paths (success, failure, edge cases)
4. Verify proper exit codes and user messaging

See [README.md](README.md) for detailed hook creation instructions and architecture.

## Pull Request Process

1. Ensure your code follows all requirements above
2. Update documentation if adding new hooks or features
3. Test thoroughly in a development environment
4. Provide clear description of changes in PR
5. Reference any related issues

## Questions or Issues?

- Check existing issues before creating new ones
- Provide reproduction steps for bugs
- Include environment details (OS, Python version, Claude Code version)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
