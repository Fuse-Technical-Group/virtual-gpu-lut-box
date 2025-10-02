# Agent Memory - Virtual GPU LUT Box

## Project Overview
Cross-platform Python package for streaming color correction LUTs from OpenGradeIO to GPU shaders via Spout (Windows) and Syphon (macOS). Focus on precision-preserving network-to-GPU streaming for professional color grading workflows.

**Python Version**: Requires Python 3.11+ for compatibility with TouchDesigner 2025+ (which includes Python 3.11). Uses modern Python syntax including union types (`X | None`) and `collections.abc` imports.

## Development Environment

**Package Manager**: This project uses `uv` for Python package management.

- ✅ **Correct**: `uv run python script.py`, `uv run pytest`
- ❌ **Wrong**: `python script.py`, `python3 script.py`, `pip install`

**Key Commands**:
- `uv run python -m virtual_gpu_lut_box` - Run the application
- `uv run pytest` - Run tests
- `uv add <package>` - Add dependencies
- `uv sync` - Sync dependencies from pyproject.toml

**Why uv**:
- Fast, reliable dependency resolution
- Built-in virtual environment management
- Lockfile-based reproducible builds
- All dependencies managed via `pyproject.toml`

## Key Architecture Decisions

### Error Handling Best Practice (2025)
**Always use exceptions instead of boolean return values for error handling.** This is a modern Python best practice that should be followed consistently:

- ✅ **Good:** `def process_data(data) -> None:` - raises `ValueError` on invalid data
- ❌ **Bad:** `def process_data(data) -> bool:` - returns `False` on error

**Why exceptions are preferred:**
1. **More informative** - can include detailed error messages and context
2. **Cleaner code** - no need for error checking after every function call
3. **Consistent** - follows Python standard library conventions
4. **Composable** - exceptions propagate naturally through call stacks
5. **IDE support** - better static analysis and error detection

**Exception Guidelines:**
- Use specific exception types (`ValueError`, `RuntimeError`, `TypeError`)
- Include descriptive error messages with context
- Chain exceptions using `raise ... from e` to preserve stack traces
- Only use boolean returns for actual boolean operations (availability checks, state queries)

### String Formatting Best Practice (2025)
**Always use f-strings for string formatting.** This is the modern Python standard:

- ✅ **Good:** `logger.info(f"Processing {lut_size}x{lut_size}x{lut_size} LUT")`
- ❌ **Bad:** `logger.info("Processing %dx%dx%d LUT", lut_size, lut_size, lut_size)`

**Why f-strings are preferred:**
- **Performance:** Fastest string formatting method in Python
- **Readability:** Variables are inline, making code more readable
- **Maintainability:** Less prone to argument mismatch errors
- **Consistency:** One formatting style throughout the codebase
- **IDE Support:** Better syntax highlighting and autocomplete

**Ruff enforcement:** UP032 rule ensures f-strings are used consistently

### LUT Processing Pipeline
- **Input:** OpenGradeIO BSON protocol over TCP
- **Processing:** 32-bit float precision preservation throughout
- **Output:** Hald image format for GPU consumption via Spout/Syphon

### Precision Preservation
- **No 8-bit conversion** - maintain exact float32 values
- **HDR/Creative LUT support** - values outside [0,1] range preserved
- **Alpha channel detection** - automatic RGB vs RGBA based on meaningful alpha data

## Key Components

### GPU Backends
- `SyphonBackend` - macOS Metal integration with Syphon
- `SpoutBackend` - Windows DirectX/OpenGL integration with Spout
- All backends use exception-based error handling (not boolean returns)

### Network Layer
- `OpenGradeIOServer` - TCP server for BSON protocol
- `OpenGradeIOLUTStreamer` - Integration with GPU streaming
- Channel-aware streaming with automatic naming

### LUT Conversion
- `HaldConverter` - 3D LUT to 2D texture conversion
- Adaptive sizing (16x16x16 to 64x64x64 and beyond)
- Preserves exact channel count and precision

### Shader Build System
- **Source**: `client_integrations/src/` - Core GLSL functions and platform templates
- **Build Script**: `client_integrations/build_shaders.py` - Generates client integrations
- **Output**: `client_integrations/` - Platform-specific shaders (built in place)
- **Platforms**: TouchDesigner, Pixera (Unreal/Notch planned)
- **Interpolation**: Tetrahedral (industry standard, 4-sample accuracy)

**Building Shaders**:
```bash
uv run python client_integrations/build_shaders.py
```

## Development Standards

### Code Quality
- **Ruff** for linting and formatting
- **Pyright** for type checking
- **Exception-based error handling** throughout
- **32-bit float precision** enforcement
- **No silent failures** - all errors must be handled or propagated

### Testing
- Use `pytest` for testing
- Test error conditions with proper exception types
- Validate precision preservation in LUT processing

### Platform Support
- macOS: Syphon with Metal backend
- Windows: Spout with DirectX/OpenGL backend
- Linux: Not supported (no texture streaming framework)

## Command Line Interface
- `virtual-gpu-lut-box` - Start OpenGradeIO server (default behavior)
- `virtual-gpu-lut-box --info` - Platform and capability information
- Simple, focused CLI with server startup as the primary function
- All CLI commands handle exceptions gracefully with user-friendly error messages

## Stream Naming Convention
- Base stream name: configurable (default: "OpenGradeIO-LUT")
- Channel streams: `vglb-lut-{channel}` format
- Automatic channel detection from OpenGradeIO metadata

## Code Cleanup History
- **Dead Code Removal (2025)**: Removed ~500 lines of unused methods from GPU backends
  - Removed unused info/utility methods (`get_syphon_info`, `get_spout_info`, `get_metal_device_info`)
  - Removed unused streaming methods (`resize`, `set_frame_sync`, `wait_frame_sync`)
  - Removed unused client/server listing methods (`list_clients`, `list_servers`)
  - Updated example files to use only implemented functionality
  - Removed tests for non-existent `LUTGenerator` class
  - Fixed test mocks to match actual method signatures
- **String Formatting Modernization (2025)**: Converted all % formatting to f-strings
  - Standardized ~50+ logging statements to use f-strings
  - Added UP032 ruff rule to enforce f-string usage going forward
  - Improved readability and performance of string formatting
- **Shader Architecture (2025)**: Implemented build system for multi-platform shaders
  - Created `client_integrations/src/` with core GLSL functions using tetrahedral interpolation
  - Platform-specific templates for TouchDesigner and Pixera
  - Python build script generates client integrations to `client_integrations/`
  - Replaced trilinear with tetrahedral interpolation (industry standard)
