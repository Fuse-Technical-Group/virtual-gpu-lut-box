# TouchDesigner Integration

Real-time color grading in TouchDesigner using virtual-gpu-lut-box and Spout.

## Files

- **`td_hald_lut.glsl`** - GLSL pixel shader for applying Hald LUT to images
- **`TD_SETUP_GUIDE.md`** - Complete setup and troubleshooting guide

## Quick Start

### 1. Start the Server
```bash
cd /path/to/virtual-gpu-lut-box
uv run virtual-gpu-lut-box
```

### 2. In TouchDesigner

**Network:**
```
Movie In TOP → GLSL TOP → Out TOP
                   ↑
            Spout In TOP (receiving LUT)
```

**GLSL TOP Setup:**
1. Load `td_hald_lut.glsl` as Pixel Shader
2. Input 1: Your image
3. Input 2: Spout In TOP
4. Done! (LUT size auto-detected)

**Spout In TOP Setup:**
- Spout Name: `virtual-gpu-lut-box` (or your custom stream name)
- Should receive 1089x33 texture for 33³ LUT

### 3. Connect OpenGradeIO
- Point your grading software to `127.0.0.1:8089`
- Apply LUTs → see results in TouchDesigner instantly!

## What You Get

✅ **Real-time color grading** - See LUT updates immediately in TouchDesigner
✅ **Float32 precision** - Professional-grade color accuracy (with GL_RGBA32F)
✅ **HDR support** - Values outside [0,1] work correctly
✅ **Multiple channels** - Receive different LUTs on different Spout streams
✅ **Any LUT size** - Works with 16³, 33³, 64³, and beyond

## Learn More

See **TD_SETUP_GUIDE.md** for:
- Detailed parameter explanations
- Troubleshooting tips
- Advanced multi-channel workflows
- Performance optimization
- HDR/Creative LUT handling

## Example Use Cases

1. **Live camera grading** - Apply Resolve LUTs to live camera feed
2. **Real-time preview** - See color grade on projection before rendering
3. **Interactive installation** - Live-controlled color grading via OpenGradeIO
4. **Multi-screen grading** - Different LUT channels for different displays

## Requirements

- **Windows** (Spout is Windows-only)
- **TouchDesigner** (2022.20000+ recommended for RGBA32F support)
- **OpenGradeIO-compatible grading software** (DaVinci Resolve, Baselight, etc.)

---

**Note**: If you're on macOS, this same workflow works with Syphon instead of Spout!
