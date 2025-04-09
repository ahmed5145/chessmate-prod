# Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to run code quality checks before each commit. This helps maintain code quality and catch issues early.

## Setup

1. Install pre-commit:

```bash
pip install pre-commit
```

2. Set up the git hooks:

```bash
pre-commit install
```

This will install the git hooks specified in `.pre-commit-config.yaml` in your local repository.

## Hooks Overview

The following hooks are configured:

### General:

- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Makes sure files end with a newline
- **check-yaml**: Validates YAML files
- **check-json**: Validates JSON files
- **check-added-large-files**: Prevents giant files from being committed
- **check-merge-conflict**: Checks for files with merge conflict strings
- **detect-private-key**: Checks for presence of private keys
- **mixed-line-ending**: Ensures consistent line endings

### Python:

- **isort**: Sorts Python imports
- **flake8**: Lints Python code
- **black**: Formats Python code
- **bandit**: Finds common security issues
- **mypy**: Type checks Python code
- **safety**: Checks for security vulnerabilities in dependencies
- **pylint-django**: Checks Django-specific code issues

### JavaScript/React:

- **eslint**: Lints JavaScript code
- **prettier**: Formats JavaScript/TypeScript code

## Running Pre-commit

Pre-commit runs automatically on `git commit`. If any hook fails, the commit will be aborted.

You can also run the hooks manually:

```bash
# Run on all files
pre-commit run --all-files

# Run on specific files
pre-commit run --files path/to/file1.py path/to/file2.js

# Run a specific hook
pre-commit run black --all-files
```

## Bypassing Pre-commit

In rare cases, you may need to bypass pre-commit (not recommended):

```bash
git commit -m "Commit message" --no-verify
```

## Continuous Integration

These same checks are run in the CI pipeline, so even if you bypass them locally, they will still be enforced before merging to the main branch.

## Updating Hooks

Update to the latest versions of the hooks:

```bash
pre-commit autoupdate
```
