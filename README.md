# Virtual GPU LUT Box

A cross-platform Python package for creating and streaming 33x33x33 color correction LUTs to GPU shaders via Spout (Windows) and Syphon (macOS).

## Features

- **33x33x33 LUT Generation**: Production-quality color correction LUTs
- **Hald Image Conversion**: Convert 3D LUTs to 2D texture format for GPU shaders
- **Cross-Platform Streaming**: Spout on Windows, Syphon on macOS
- **CLI Interface**: Easy-to-use command-line tools
- **Modern Python**: Type hints, comprehensive testing, and modern packaging

## Installation

```bash
pip install virtual-gpu-lut-box
```

### Development Dependencies

For development (includes linting, testing, building tools):
```bash
pip install virtual-gpu-lut-box[dev]
```

**Note**: Platform-specific streaming dependencies (Spout for Windows, Syphon for macOS) are automatically installed based on your operating system.

**Syphon Debug Messages**: You may see debug messages like `"SYPHON DEBUG: SyphonServer: Server deallocing, name: (null)"` - these are normal cleanup messages from the Syphon framework and can be safely ignored.

## Quick Start

### Command Line Usage

Generate a LUT and save as Hald image:
```bash
virtual-gpu-lut-box generate --gamma 2.2 --brightness 0.1 --output my_lut.png
```

Stream a LUT via Spout/Syphon:
```bash
# Uses default stream name "virtual-gpu-lut-box"
virtual-gpu-lut-box stream my_lut.png --fps 30 --loop

# Or specify a custom name
virtual-gpu-lut-box stream my_lut.png --name "My Custom Stream" --fps 30 --loop
```

Check platform support:
```bash
virtual-gpu-lut-box info
```

### Python API

```python
from virtual_gpu_lut_box import LUTGenerator, HaldConverter, StreamingFactory

# Generate a custom LUT
generator = LUTGenerator(size=33)
lut = generator.create_custom_lut(
    gamma=2.2,
    brightness=0.1,
    contrast=1.2,
    saturation=1.1
)

# Convert to Hald image format
converter = HaldConverter(size=33)
hald_image = converter.lut_to_hald(lut)

# Stream to GPU shader (uses default name "virtual-gpu-lut-box")
with StreamingFactory.create_lut_streamer() as streamer:
    streamer.send_lut_texture(hald_image)

# Or specify a custom name
with StreamingFactory.create_lut_streamer("My Custom Stream") as streamer:
    streamer.send_lut_texture(hald_image)
```

## Architecture

### Components

- **LUTGenerator**: Creates 33x33x33 color correction LUTs with various adjustments
- **HaldConverter**: Converts 3D LUTs to 2D Hald image format (1089x33 pixels)
- **StreamingFactory**: Platform-aware factory for creating streaming backends
- **SpoutBackend**: Windows Spout streaming implementation
- **SyphonBackend**: macOS Syphon streaming implementation

### LUT Format

The package uses 33x33x33 LUTs, which provide production-quality color correction with 35,937 color entries. These are converted to Hald images with dimensions:
- Width: 1089 pixels (33 × 33)
- Height: 33 pixels
- Format: RGB/RGBA

## Platform Support

| Platform | Streaming Backend | Status |
|----------|------------------|--------|
| Windows  | Spout            | ✅ Supported |
| macOS    | Syphon           | ✅ Supported |
| Linux    | None             | ❌ Not supported |

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
invoke dev-setup
```

### Development Tasks

This project uses [Invoke](https://pyinvoke.org/) for task automation. See [TASKS.md](TASKS.md) for full details.

```bash
# Run all quality checks
invoke quality

# Build the package
invoke build

# Run complete CI/CD pipeline
invoke all

# Format and lint code
invoke format lint

# Run tests with coverage
invoke test

# Type checking
invoke typecheck
```

### Manual Commands

```bash
# Testing
pytest

# Linting
ruff check src tests
ruff format src tests

# Type checking
mypy src/virtual_gpu_lut_box

# Building
python -m build
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [Spout](https://spout.zeal.co/) for Windows texture sharing
- [Syphon](http://syphon.v002.info/) for macOS texture sharing
- The OpenGL and GPU shader communities
