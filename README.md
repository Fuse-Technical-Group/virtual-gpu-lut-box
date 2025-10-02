# Virtual GPU LUT Box

Enhance professional color grading workflows with a cross-platform Python package for network-to-GPU streaming of color correction LUTs from OpenGradeIO (aka Pomfort LiveGrade) to GPU LUT processors via Spout (Windows) and Syphon (macOS).

## Features

- **Network-to-GPU LUT Streaming**: Direct OpenGradeIO to GPU texture streaming
- **Adaptive LUT Sizes**: Support for any LUT size (16x16x16, 33x33x33, 64x64x64, etc.)
- **Precision Preservation**: 32-bit float only - no 8-bit conversion or quantization
- **Hald Image Conversion**: Efficient 3D→2D texture format conversion for GPU shaders
- **Cross-Platform Streaming**: Spout on Windows, Syphon on macOS
- **Channel-Aware Streaming**: Automatic stream naming based on OpenGradeIO channels/instances
- **HDR/Creative LUT Support**: Values outside [0,1] range preserved exactly
- **Reference Shaders**: Easy-to-fork reference shaders implementing tetrahedral interpolation, pre-built solutions for Touch Designer and Pixera
- **High-Performance Architecture**: Multi-process server with multi-threaded client handling for concurrent connections

## Installation

### From Source

```bash
git clone https://github.com/repentsinner/virtual-gpu-lut-box.git
cd virtual-gpu-lut-box
uv sync
```

### ~~Using [uv](https://docs.astral.sh/uv/getting-started/installation/) (Recommended)~~

```bash
uv add virtual-gpu-lut-box
```

### ~~Using pip~~

```bash
pip install virtual-gpu-lut-box
```

> *Note: This package is not yet published to PyPI. Once published, it will be installable via uv add virtual-gpu-lut-box or pip install virtual-gpu-lut-box.*

## Quick Start

### Command Line Usage

Start OpenGradeIO network server:
```bash
# Listen for OpenGradeIO connections (default: 0.0.0.0:8089)
uv run virtual-gpu-lut-box

# Custom configuration
uv run virtual-gpu-lut-box --host 0.0.0.0 --port 8089 --verbose

# Localhost only (for development/testing)
uv run virtual-gpu-lut-box --host 127.0.0.1

# Custom base stream name for OpenGradeIO LUTs
uv run virtual-gpu-lut-box --stream-name "MyProject-LUT" --verbose
```

**Network Configuration:**
- **Default (`0.0.0.0`)**: Listens on all network interfaces - accepts connections from any machine
- **Localhost (`127.0.0.1`)**: Only accepts connections from the same machine (development/testing)
- **Windows**: May require firewall rule for Python or port 8089 when using `0.0.0.0`
- **Security**: OpenGradeIO has no authentication - only use on trusted production networks


### Client Integration Shaders

Pre-built GLSL shaders with tetrahedral interpolation for professional color accuracy:

#### TouchDesigner
- **File**: `client_integrations/td_hald_lut.glsl`
- **Platforms**: Windows (Spout), macOS (Syphon)
- Standard GLSL TOP shader with auto-detected LUT size
- **[Setup Guide](client_integrations/TD_SETUP_GUIDE.md)**

#### Pixera
- **File**: `client_integrations/pixera_hald_lut.glsl`
- **Platforms**: Windows (Spout)
- Struct-based shader format for Pixera media server
- **[Setup Guide](client_integrations/PIXERA_SETUP_GUIDE.md)**

### OpenGradeIO-Compatible Controller

Point your OpenGradeIO-compatible grading software (such as Pomfort LiveGrade) to `[hostname]`.
- To accomplish this you will have to use the unfortunately named `PomfortVL for Unreal Engine` "device", and your virtual-gpu-lut-box compatible system will show up with a goofy `U` next to it in Livegrade.

> Pomfort has not opted to define a single OpenGradeIO protocol that all device vendors adhere to for some insane reason, instead preferring to complicate their software with over a dozen "unique" device vendors that they "support".

## Platform Support

| Platform | Streaming Backend | Precision | Format Support | Status |
|----------|------------------|-----------|----------------|--------|
| Windows  | Spout            | 32-bit float only | RGB/RGBA | ✅ Supported |
| macOS    | Syphon           | 32-bit float only | RGB/RGBA (Metal) | ✅ Supported |
| Linux    | None             | N/A | N/A | ❌ Not supported |\

# Development

## Architecture

### Components

- **HaldConverter**: Converts 3D LUTs to 2D Hald image format for GPU consumption. Note that OpenGL texture orientation is different from numpy orientation
- **StreamingFactory**: Platform-aware factory with lazy initialization and size adaptation
- **SpoutBackend**: Windows Spout streaming with 32-bit float precision support
- **SyphonBackend**: macOS Syphon streaming with Metal integration and 32-bit float textures
- **OpenGradeIOServer**: TCP server for OpenGradeIO BSON protocol
- **OpenGradeIOLUTStreamer**: Integration layer with channel-aware streaming

### LUT Format and Precision

The package supports any cubic LUT size with automatic Hald image calculation:
- **33x33x33 LUT**: 1089x33 Hald image (35,937 entries) - Standard
- **64x64x64 LUT**: 4096x64 Hald image (262,144 entries) - High precision
- **Format**: 32-bit float only (RGB or RGBA) for maximum precision
- **Range**: Supports HDR/creative LUTs with values outside [0,1] range

### OpenGradeIO Integration

- **BSON Protocol**: Full support for OpenGradeIO virtual LUT box protocol
- **Channel Awareness**: Automatic stream naming using `vglb-lut-{channel}` format
- **Lazy Initialization**: Streaming backend adapts to incoming LUT size automatically
- **Metadata Extraction**: Parse service, instance, and type information from messages
- **Error Handling**: Comprehensive error handling with detailed logging

## Development Dependencies

For development (includes linting, testing, building tools):
```bash
# With uv (recommended)
uv sync --extra dev

# Or with pip
pip install virtual-gpu-lut-box[dev]
```

**Note**: Platform-specific streaming dependencies (Spout for Windows, Syphon for macOS) are automatically installed based on your operating system.

**Syphon Debug Messages**: You may see debug messages like `"SYPHON DEBUG: SyphonServer: Server deallocing, name: (null)"` - these are normal cleanup messages from the Syphon framework and can be safely ignored.

## Python API

For embedding the LUT server directly in your Python application (rather than running as an external CLI process).

**Note:** The server automatically spawns a separate process to avoid Python GIL blocking, ensuring network I/O doesn't stall your main application.

### OpenGradeIO Network Server

```python
from virtual_gpu_lut_box import VirtualGPULUTBoxServer

# Start OpenGradeIO server with GPU streaming (default: 0.0.0.0:8089)
server = VirtualGPULUTBoxServer(
    stream_name="OpenGradeIO-LUT",
    verbose=False
)

server.start()
# Server runs in background process (non-blocking)

# Or specify custom host/port:
# server = VirtualGPULUTBoxServer(host="0.0.0.0", port=8089)
```

### Setup

```bash
git clone https://github.com/example/virtual-gpu-lut-box.git
cd virtual-gpu-lut-box

# With uv (recommended)
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"

# Or use invoke for automated setup
uv run invoke dev-setup
```

### Development Tasks

This project uses [Invoke](https://pyinvoke.org/) for task automation. See [TASKS.md](TASKS.md) for full details.

```bash
# Run all quality checks
uv run invoke quality

# Build the package
uv run invoke build

# Run complete CI/CD pipeline
uv run invoke all

# Format and lint code
uv run invoke format lint

# Run tests with coverage
uv run invoke test

# Type checking with Pyright
uv run invoke typecheck

# Spell checking with codespell
uv run invoke spell

# Security analysis with bandit
uv run invoke security

# Check for banned code patterns
uv run invoke check-patterns
```

### Building Shaders

Client integration shaders are generated from source templates:

```bash
# Build all shaders
uv run python client_integrations/build_shaders.py

# Clean generated shaders
uv run python client_integrations/build_shaders.py --clean
```

**Sources**:
- `client_integrations/src/hald_lut_core.glsl` - Shared tetrahedral interpolation functions
- `client_integrations/src/*.template.glsl` - Platform-specific wrappers
- `client_integrations/*.glsl` - Generated shaders (tracked in git)

### Code Quality

The project uses modern Python tooling:
- **Pyright**: Fast, accurate type checking
- **Ruff**: Ultra-fast Python linter and formatter
- **CSpell**: Comprehensive spell checking for code and documentation
- **Bandit**: Security analysis for Python code
- **TID Rules**: Enforced fully qualified imports for better maintainability
- **32-bit Float Support**: Custom Metal type stubs for macOS, enforced precision preservation
- **Exception Handling**: No silent failures - all exceptions are properly handled
- **Format Validation**: Strict validation that errors on unsupported formats
- **Pattern Checking**: Automated detection of banned code patterns

### Manual Commands

```bash
# Testing
uv run pytest

# Linting and formatting
uv run ruff check src tests
uv run ruff format src tests

# Type checking
uv run pyright

# Spell checking
uv run codespell

# Security analysis
uv run bandit -r src/virtual_gpu_lut_box

# Building
uv run python -m build
```
## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite (`uv run invoke quality`)
6. Submit a pull request

## License

[BSD 3-Clause License](./LICENSES/BSD-3-Clause.txt).

## Acknowledgments

- [Spout](https://spout.zeal.co/) for Windows texture sharing
- [Syphon](http://syphon.v002.info/) for macOS texture sharing
- [PyObjC](https://pyobjc.readthedocs.io/) for Metal framework integration on macOS
- The OpenGL and GPU shader communities

Happy Grading! 🎨