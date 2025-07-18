# Claude Code Memory - Virtual GPU LUT Box

## Project Overview
Cross-platform Python package for streaming color correction LUTs from OpenGradeIO to GPU shaders via Spout (Windows) and Syphon (macOS). Focus on precision-preserving network-to-GPU streaming for professional color grading workflows.

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
- `virtual-gpu-lut-box listen` - Start OpenGradeIO server
- `virtual-gpu-lut-box info` - Platform and capability information
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