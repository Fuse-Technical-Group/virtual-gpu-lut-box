# Development Guide

## Setup

### Prerequisites
- Python 3.11 (for TouchDesigner 2023.x compatibility)
- [uv](https://docs.astral.sh/uv/) package manager
- Git

### Clone and Install

```bash
git clone https://github.com/Fuse-Technical-Group/virtual-gpu-lut-box.git
cd virtual-gpu-lut-box
uv sync --all-extras
```

## Development Workflow

### Running Quality Checks

```bash
# Run all quality checks (linting, types, security, patterns)
uv run invoke quality

# Run specific checks
uv run invoke format    # Format code with ruff
uv run invoke lint      # Lint with ruff
uv run invoke typecheck # Type check with pyright
uv run invoke spell     # Spell check with codespell
uv run invoke security  # Security analysis (bandit + safety)
```

### Running Tests

```bash
# Run tests with coverage
uv run invoke test

# Run tests verbosely
uv run invoke test --verbose
```

### Building

```bash
# Build package (wheel + sdist)
uv run invoke build

# Clean build artifacts
uv run invoke clean
```

### Documentation

```bash
# Build documentation
uv run invoke docs

# Serve documentation locally with live reload
uv run invoke docs-serve
# Then open http://127.0.0.1:8000
```

## Code Quality Standards

### Formatting and Linting
- **Ruff**: Ultra-fast Python linter and formatter
- **Line length**: 88 characters (Black-compatible)
- **Import sorting**: Enforced via ruff

### Type Checking
- **Pyright**: Fast, accurate type checking
- **Coverage**: All public APIs must have type hints
- **Strict mode**: Enabled for new code

### Documentation
- **Docstring style**: Google-style docstrings
- **Coverage**: All public APIs must be documented
- **Examples**: Include usage examples where appropriate

### Security
- **Bandit**: Static analysis for security issues
- **Safety**: Dependency vulnerability scanning
- **Pattern checking**: Automated detection of banned patterns

### Testing
- **Framework**: pytest
- **Coverage**: Minimum 50% coverage required
- **Fixtures**: Use fixtures for common test setup
- **Mocking**: Mock external dependencies (network, GPU)

## Architecture

### Package Structure

```
src/virtual_gpu_lut_box/
├── __init__.py              # Public API
├── server.py                # VirtualGPULUTBoxServer
├── lut/                     # LUT processing
│   └── hald_converter.py    # 3D LUT → 2D Hald conversion
├── network/                 # OpenGradeIO networking
│   ├── server.py            # TCP server
│   ├── protocol.py          # BSON protocol handler
│   └── lut_streamer.py      # LUT streaming integration
└── gpu_texture_stream/      # GPU streaming backends
    ├── base.py              # Abstract base classes
    ├── factory.py           # Platform detection/creation
    ├── spout.py             # Windows Spout backend
    └── syphon.py            # macOS Syphon backend
```

### Design Principles

1. **Precision Preservation**: 32-bit float only, no quantization
2. **Exception-Based Errors**: No boolean returns for error states
3. **Platform Awareness**: Runtime detection and graceful degradation
4. **DRY**: Single source of truth (CI uses same tasks as local dev)
5. **Modern Python**: Use f-strings, type hints, dataclasses

## Contributing

### Before Submitting a PR

1. **Run quality checks**: `uv run invoke quality`
2. **Run tests**: `uv run invoke test`
3. **Update documentation**: Add/update docstrings and guides
4. **Add tests**: Cover new functionality
5. **Check CI**: Ensure GitHub Actions pass

### Commit Messages

- Use conventional commits format
- Be descriptive about the "why"
- Reference issues when applicable

### Code Review

- All PRs require review
- Address all review comments
- Squash commits before merging

## License

BSD 3-Clause License - See [LICENSE](https://github.com/Fuse-Technical-Group/virtual-gpu-lut-box/blob/main/LICENSE) for details.
