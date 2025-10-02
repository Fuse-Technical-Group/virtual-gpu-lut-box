# Project Tasks

This project uses [Invoke](https://pyinvoke.org/) for task automation. Tasks are defined in `tasks.py` and provide a convenient way to run common development operations.

## Setup

First, install the development dependencies including invoke:

```bash
uv sync --extra dev
```

**Note**: If you get an error with `uv run invoke`, try:
```bash
# Install invoke explicitly
uv add invoke --dev
```

## Available Tasks

### Development Tasks

- **`invoke clean`** - Clean build artifacts, cache files, and temporary files
- **`invoke format`** - Format code with ruff
- **`invoke lint`** - Run linting with ruff
- **`invoke typecheck`** - Run type checking with pyright
- **`invoke spell`** - Run spell checking with codespell
  - `--fix` - Automatically fix spelling issues
- **`invoke security`** - Run security analysis with bandit
- **`invoke check-patterns`** - Check for banned code patterns
- **`invoke reuse-annotate`** - Add SPDX license headers to source files missing them
- **`invoke reuse-lint`** - Verify REUSE compliance (check SPDX headers)
  - Note: May timeout on Windows systems with >=64 logical processors ([multiprocessing limitation](https://stackoverflow.com/q/65252807))
- **`invoke test`** - Run tests with pytest
  - `--no-coverage` - Skip coverage report
  - `--verbose` - Run with verbose output
- **`invoke quality`** - Run all quality checks (format, lint, typecheck, spell, security, check-patterns, test)

### Build & Release Tasks

- **`invoke build`** - Build the package for distribution
- **`invoke publish`** - Publish package to PyPI
  - `--test` - Publish to test PyPI instead of production
- **`invoke install`** - Install the package
  - `--dev` - Install with development dependencies
  - `--no-editable` - Install in non-editable mode

**Alternative Build Method**: If invoke is not working, you can build manually:
```bash
uv run python -m build    # Build package
uv run invoke clean        # Clean build artifacts
```

### Documentation & Setup

- **`invoke docs`** - Generate API documentation
- **`invoke dev-setup`** - Set up development environment (install + pre-commit hooks)
- **`invoke demo`** - Run a quick demo of the package

### Release Management

- **`invoke release --version=1.0.0`** - Prepare a release with version bumping
- **`invoke all`** - Run complete CI/CD pipeline (clean, quality, build)

## Example Usage

### Basic Development Workflow

```bash
# Set up development environment
invoke dev-setup

# Run quality checks
invoke quality

# Build the package
invoke build

# Run demo
invoke demo
```

### Release Workflow

```bash
# Prepare release
invoke release --version=1.0.0

# After reviewing changes, publish
invoke publish --test  # Test PyPI first
invoke publish         # Production PyPI
```

### Quick Tasks

```bash
# Format and lint code
invoke format lint

# Run tests with coverage
invoke test

# Clean and rebuild
invoke clean build

# Complete CI/CD pipeline
invoke all
```

## Task Dependencies

Some tasks have dependencies that run automatically:

- `invoke quality` → runs `format`, `lint`, `typecheck`, `spell`, `security`, `check-patterns`, `test`
- `invoke build` → runs `clean` first
- `invoke publish` → runs `build` first
- `invoke release` → runs `quality` and `build`
- `invoke all` → runs `clean`, `quality`, `build`

## Configuration

Tasks can be configured by editing `tasks.py`. Common configurations:

- **Test options**: Modify the `test()` task to change pytest arguments
- **Build options**: Modify the `build()` task to change build parameters
- **Linting rules**: Modify the `lint()` task to change ruff configuration
- **Coverage settings**: Modify the `test()` task to change coverage options

## Integration with CI/CD

The tasks are designed to work well with CI/CD systems:

```bash
# In GitHub Actions or similar
invoke all  # Runs complete pipeline
```

## Troubleshooting

**Task not found**: Make sure you have invoke installed:
```bash
uv add invoke --dev
```

**Import errors**: Make sure the package is installed:
```bash
uv run invoke install --dev
```

**Permission errors**: Make sure you have the right permissions for publishing:
```bash
uv add twine --dev
```

For more information about invoke, see the [official documentation](https://pyinvoke.org/).
