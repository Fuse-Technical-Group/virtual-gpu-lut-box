# Virtual GPU LUT Box

A cross-platform Python package for streaming color correction LUTs from OpenGradeIO to GPU shaders via Spout (Windows) and Syphon (macOS). Focused on precision-preserving network-to-GPU LUT streaming for professional color grading workflows.

## Features

- **Network-to-GPU LUT Streaming**: Direct OpenGradeIO to GPU texture streaming
- **Adaptive LUT Sizes**: Support for any LUT size (16x16x16, 33x33x33, 64x64x64, etc.)
- **Precision Preservation**: 32-bit float only - no 8-bit conversion or quantization
- **Hald Image Conversion**: Efficient 3D→2D texture format conversion for GPU shaders
- **Cross-Platform Streaming**: Spout on Windows, Syphon on macOS with Metal integration
- **Channel-Aware Streaming**: Automatic stream naming based on OpenGradeIO channels/instances
- **HDR/Creative LUT Support**: Values outside [0,1] range preserved exactly
- **Professional Workflow**: Built for high-end color grading pipelines

## Installation

### Using uv (Recommended)

```bash
uv add virtual-gpu-lut-box
```

### Using pip

```bash
pip install virtual-gpu-lut-box
```

### Development Dependencies

For development (includes linting, testing, building tools):
```bash
# With uv (recommended)
uv sync --extra dev

# Or with pip
pip install virtual-gpu-lut-box[dev]
```

**Note**: Platform-specific streaming dependencies (Spout for Windows, Syphon for macOS) are automatically installed based on your operating system.

**Syphon Debug Messages**: You may see debug messages like `"SYPHON DEBUG: SyphonServer: Server deallocing, name: (null)"` - these are normal cleanup messages from the Syphon framework and can be safely ignored.

## Quick Start

### Command Line Usage

Start OpenGradeIO network server:
```bash
# Listen for OpenGradeIO connections with default settings
uv run virtual-gpu-lut-box

# Custom configuration
uv run virtual-gpu-lut-box --host 127.0.0.1 --port 8089 --verbose

# Custom base stream name for OpenGradeIO LUTs
uv run virtual-gpu-lut-box --stream-name "MyProject-LUT" --verbose
```

Check platform support and system information:
```bash
uv run virtual-gpu-lut-box --info
```

### Python API

#### OpenGradeIO Network Server

```python
from virtual_gpu_lut_box import OpenGradeIOServer, OpenGradeIOLUTStreamer
import numpy as np

# Create LUT streamer with automatic channel naming
streamer = OpenGradeIOLUTStreamer(stream_name="OpenGradeIO-LUT")

# LUT callback function
def lut_callback(lut_data: np.ndarray, channel_name: str = None):
    try:
        streamer.process_lut(lut_data, channel_name)
        print(f"Streamed LUT for channel: {channel_name or 'default'}")
    except Exception as e:
        print(f"Error streaming LUT: {e}")

# Start OpenGradeIO server
server = OpenGradeIOServer(
    host="127.0.0.1",
    port=8089,
    lut_callback=lut_callback
)

server.start()
# Server runs in background thread
```

## Architecture

### Components

- **HaldConverter**: Converts 3D LUTs to 2D Hald image format for GPU consumption
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

## Platform Support

| Platform | Streaming Backend | Precision | Format Support | Status |
|----------|------------------|-----------|----------------|--------|
| Windows  | Spout            | 32-bit float only | RGB/RGBA | ✅ Supported |
| macOS    | Syphon           | 32-bit float only | RGB/RGBA (Metal) | ✅ Supported |
| Linux    | None             | N/A | N/A | ❌ Not supported |

## Development

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
```

### Code Quality

The project uses modern Python tooling:
- **Pyright**: Fast, accurate type checking
- **Ruff**: Ultra-fast Python linter and formatter
- **TID Rules**: Enforced fully qualified imports for better maintainability
- **32-bit Float Support**: Custom Metal type stubs for macOS, enforced precision preservation
- **Exception Handling**: No silent failures - all exceptions are properly handled
- **Format Validation**: Strict validation that errors on unsupported formats

### Manual Commands

```bash
# Testing
uv run pytest

# Linting and formatting
uv run ruff check src tests
uv run ruff format src tests

# Type checking
uv run pyright

# Building
uv run python -m build
```

## OpenGradeIO Workflow

1. **Start Server**: `uv run virtual-gpu-lut-box`
2. **Configure OpenGradeIO**: Set virtual LUT box to `127.0.0.1:8089`
3. **Apply LUTs**: LUTs are automatically texture streamed to `vglb-lut-{channel}`
4. **GPU Integration**: Consume the LUT in Hald format in your rendering/compositing application

The server supports:
- Multiple concurrent channels
- Any LUT size (16x16x16 to 64x64x64 and beyond)
- Real-time updates
- Automatic gpu texture stream naming based on OpenGradeIO channels
- 32-bit float precision for professional color grading

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite (`uv run invoke quality`)
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [Spout](https://spout.zeal.co/) for Windows texture sharing
- [Syphon](http://syphon.v002.info/) for macOS texture sharing
- [PyObjC](https://pyobjc.readthedocs.io/) for Metal framework integration on macOS
- The OpenGL and GPU shader communities