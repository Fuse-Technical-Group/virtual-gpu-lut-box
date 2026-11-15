# Virtual GPU LUT Box

Enhance professional color grading workflows with a cross-platform Python
package for network-to-GPU streaming of color correction LUTs from OpenGradeIO
(aka Pomfort Livegrade) to GPU LUT processors via Spout (Windows) and Syphon
(macOS).

## Features

- **Network-to-GPU LUT Streaming**: Direct OpenGradeIO to GPU texture streaming
- **Adaptive LUT Sizes**: Support for any LUT size (16x16x16, 33x33x33,
  64x64x64, etc.)
- **Precision Preservation**: 32-bit float only - no 8-bit conversion or
  quantization
- **Hald Image Conversion**: Efficient 3D→2D texture format conversion for GPU
  shaders
- **Cross-Platform Streaming**: Spout on Windows, Syphon on macOS
- **Channel-Aware Streaming**: Automatic stream naming based on OpenGradeIO
  channels/instances
- **HDR/Creative LUT Support**: Values outside [0,1] range preserved exactly
- **Reference Shaders**: Easy-to-fork reference shaders implementing
  tetrahedral interpolation, pre-built solutions for Touch Designer and Pixera
- **High-Performance Architecture**: Multi-process server with multi-threaded
  client handling for concurrent connections

## Installation

### From Source

```bash
git clone https://github.com/Fuse-Technical-Group/virtual-gpu-lut-box
cd virtual-gpu-lut-box
uv sync
```

### From PyPI (not yet published)

This package is not yet published to PyPI. Once published, it will be
installable with [uv](https://docs.astral.sh/uv/getting-started/installation/)
or pip:

```bash
uv add virtual-gpu-lut-box
# or
pip install virtual-gpu-lut-box
```

Platform-specific streaming dependencies (Spout for Windows, Syphon for macOS)
are installed automatically based on your operating system.

## Usage

### Command Line

Start the OpenGradeIO network server. The `vglb` command is a short alias for
`virtual-gpu-lut-box`.

```bash
# Listen for OpenGradeIO connections (default: 0.0.0.0:8089)
uv run virtual-gpu-lut-box

# Custom configuration
uv run virtual-gpu-lut-box --host 0.0.0.0 --port 8089 --verbose

# Localhost only (for development/testing)
uv run virtual-gpu-lut-box --host 127.0.0.1

# Custom base stream name for OpenGradeIO LUTs
uv run virtual-gpu-lut-box --stream-name "MyProject-LUT" --verbose

# Show system information and exit
uv run virtual-gpu-lut-box --info
```

### Network Configuration

- **Default (`0.0.0.0`)**: Listens on all network interfaces - accepts
  connections from any machine
- **Localhost (`127.0.0.1`)**: Only accepts connections from the same machine
  (development/testing)
- **Windows**: May require firewall rule for Python or port 8089 when using
  `0.0.0.0`
- **Security**: OpenGradeIO has no authentication - only use on trusted
  production networks

### Python API

Embed the LUT server directly in your Python application rather than running
the CLI as an external process.

The server spawns a separate process to avoid Python GIL blocking, so network
I/O does not stall your main application.

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

### Client Integration Shaders

Pre-built GLSL shaders with tetrahedral interpolation for professional color
accuracy:

#### TouchDesigner

- **File**: `client_integrations/td_hald_lut.glsl`
- **Platforms**: Windows (Spout), macOS (Syphon)
- Standard GLSL TOP shader with auto-detected LUT size
- **[Setup Guide](docs/guides/td-setup.md)**

#### Pixera

- **File**: `client_integrations/pixera_hald_lut.glsl`
- **Platforms**: Windows (Spout)
- Struct-based shader format for Pixera media server
- **[Setup Guide](docs/guides/pixera-setup.md)**

### OpenGradeIO-Compatible Controller

Point your OpenGradeIO-compatible grading software (such as Pomfort Livegrade)
to `[hostname]`.

- To accomplish this you will have to use the unfortunately named
  `PomfortVL for Unreal Engine` "device", and your virtual-gpu-lut-box
  compatible system will show up with a goofy `U` next to it in Livegrade.

**Syphon Debug Messages**: You may see debug messages like
`"SYPHON DEBUG: SyphonServer: Server deallocing, name: (null)"` - these are
normal cleanup messages from the Syphon framework and can be safely ignored.

## Platform Support

| Platform | Streaming Backend | Precision | Format Support | Status |
|----------|------------------|-----------|----------------|--------|
| Windows  | Spout            | 32-bit float only | RGB/RGBA | ✅ Supported |
| macOS    | Syphon           | 32-bit float only | RGB/RGBA (Metal) | ✅ Supported |
| Linux    | None             | N/A | N/A | ❌ Not supported |

## Architecture

### Components

- **HaldConverter**: Converts 3D LUTs to 2D Hald image format for GPU
  consumption. Note that OpenGL texture orientation is different from numpy
  orientation
- **StreamingFactory**: Platform-aware factory with lazy initialization and
  size adaptation
- **SpoutBackend**: Windows Spout streaming with 32-bit float precision support
- **SyphonBackend**: macOS Syphon streaming with Metal integration and 32-bit
  float textures
- **OpenGradeIOServer**: TCP server for OpenGradeIO BSON protocol
- **OpenGradeIOLUTStreamer**: Integration layer with channel-aware streaming

### LUT Format and Precision

The package supports any cubic LUT size with automatic Hald image calculation:

- **33x33x33 LUT**: 1089x33 Hald image (35,937 entries) - Standard
- **64x64x64 LUT**: 4096x64 Hald image (262,144 entries) - High precision
- **Format**: 32-bit float only (RGB or RGBA) for maximum precision
- **Range**: Supports HDR/creative LUTs with values outside [0,1] range

### HDR Handling

**Current Implementation (Display-Referred Workflow):**

The shader implementations use edge clamping for HDR values:

- Input values in the `[0,1]` range receive full LUT transformation
- Values `>1.0` are clamped to the LUT's white point
- Appropriate for workflows where HDR highlights (specular reflections, bright
  lights) should inherit the white point's color transform

**Example Use Cases:**

- Real-time rendering (TouchDesigner, game engines)
- Live event production where LUTs grade diffuse surfaces (skin tones, scenery)
- Workflows where bright highlights should remain neutral

**Scene-Referred HDR Limitation:**

For scene-referred HDR workflows spanning multiple exposure stops (e.g., -6 to
+10 EV), a shaper curve (log2, PQ, ACES) would be needed to compress the full
HDR range into `[0,1]` before LUT application, then expand back afterwards.
**This is not currently implemented** but is planned for future development.

If you need scene-referred HDR support, please open an issue describing your
workflow.

### OpenGradeIO Integration

- **BSON Protocol**: Full support for OpenGradeIO virtual LUT box protocol
- **Channel Awareness**: Automatic stream naming using `vglb-lut-{channel}`
  format
- **Lazy Initialization**: Streaming backend adapts to incoming LUT size
  automatically
- **Metadata Extraction**: Parse service, instance, and type information from
  messages
- **Error Handling**: Comprehensive error handling with detailed logging

## Development

### Setup

`uv sync` installs the development dependency group (linting, testing,
building tools) along with the package.

```bash
git clone https://github.com/Fuse-Technical-Group/virtual-gpu-lut-box
cd virtual-gpu-lut-box
uv sync
```

### Development Tasks

This project uses [Invoke](https://pyinvoke.org/) for task automation. See
[Tasks documentation](docs/tasks.md) for full details.

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

- `client_integrations/src/hald_lut_core.glsl` - Shared tetrahedral
  interpolation functions
- `client_integrations/src/*.template.glsl` - Platform-specific wrappers
- `client_integrations/*.glsl` - Generated shaders (tracked in git)

### Code Quality

The project uses modern Python tooling:

- **Pyright**: Fast, accurate type checking
- **Ruff**: Ultra-fast Python linter and formatter
- **codespell**: Comprehensive spell checking for code and documentation
- **Bandit**: Security analysis for Python code
- **TID Rules**: Enforced fully qualified imports for better maintainability
- **32-bit Float Support**: Custom Metal type stubs for macOS, enforced
  precision preservation
- **Exception Handling**: No silent failures - all exceptions are properly
  handled
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
uv build
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite (`uv run invoke quality`)
6. Submit a pull request

## License

Copyright (c) 2025, [Fuse Technical Group](https://fuse-tg.com/)

Licensed under the [BSD 3-Clause License](./LICENSES/BSD-3-Clause.txt).

## Acknowledgments

- [Spout](https://spout.zeal.co/) for Windows texture sharing
- [Syphon](http://syphon.v002.info/) for macOS texture sharing
- [PyObjC](https://pyobjc.readthedocs.io/) for Metal framework integration on
  macOS
- The OpenGL and GPU shader communities

Happy Grading! 🎨
