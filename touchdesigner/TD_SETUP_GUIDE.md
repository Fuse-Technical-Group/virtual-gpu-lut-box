# TouchDesigner Hald LUT Setup Guide

Complete guide for using virtual-gpu-lut-box with TouchDesigner for real-time color grading.

## Quick Start

### 1. Start the LUT Server

```bash
# In your virtual-gpu-lut-box project
uv run virtual-gpu-lut-box --stream-name "MyProject-LUT"
```

The server will:
- Listen for OpenGradeIO connections on port 8089
- Stream LUTs via Spout to Windows

### 2. TouchDesigner Network Setup

```
[Movie In TOP or Camera]
         ↓
    [GLSL TOP] ← [Spout In TOP]
         ↓
    [Out TOP]
```

### 3. Configure Spout In TOP

1. Add **Spout In TOP**
2. Parameters:
   - **Spout Name**: Set to your stream name (e.g., "MyProject-LUT" or "vglb-lut-{channel}")
   - **Pixel Format**: RGBA32Float (if available) or RGBA8Fixed
   - **Resolution**: Should auto-detect (e.g., 1089x33 for 33³ LUT)

### 4. Configure GLSL TOP

#### Method A: Load External Shader (Recommended)

1. Add **GLSL TOP**
2. **Inputs** tab:
   - Connect your image to Input 1
   - Connect Spout In TOP to Input 2
3. **GLSL** page → **Shader** section:
   - Click folder icon next to "Pixel Shader"
   - Select `td_hald_lut.glsl`
4. **Done!** No uniforms needed - LUT size is auto-detected from the Hald texture

#### Method B: Paste Shader Code

1. Add **GLSL TOP**
2. **Inputs** tab:
   - Connect your image to Input 1
   - Connect Spout In TOP to Input 2
3. **GLSL** page → **Shader** section:
   - Click **Edit Pixel Shader** button (folder icon next to Pixel Shader field)
   - Delete default code
   - Paste contents of `td_hald_lut.glsl`
4. **Done!** No configuration needed

### 5. Connect to OpenGradeIO

1. In your grading software (DaVinci Resolve, Baselight, etc.):
   - Configure Virtual LUT Box connection
   - Set to `127.0.0.1:8089`
2. Apply LUTs in your grading software
3. See real-time results in TouchDesigner!

## LUT Size Reference

| LUT Size | Hald Dimensions | Quality |
|----------|----------------|---------|
| 16³ | 256x16 | Low (faster) |
| 33³ | 1089x33 | Standard |
| 64³ | 4096x64 | High (slower) |

**LUT size is auto-detected!** The shader reads it from the Hald texture height:
- 16x16 Hald (256x16) → 16³ LUT
- 1089x33 Hald → 33³ LUT
- 4096x64 Hald → 64³ LUT

No manual configuration needed!

## Advanced: Multiple Channels

If using multiple OpenGradeIO channels/instances:

```
[Your Image]
     ↓
[GLSL TOP] ← [Spout In TOP: "vglb-lut-channel1"]
     ↓
[GLSL TOP] ← [Spout In TOP: "vglb-lut-channel2"]
     ↓
[Out TOP]
```

Stack multiple GLSL TOPs with different Spout streams to apply multiple LUTs in sequence.

## Troubleshooting

### "No Spout stream found"
- Verify virtual-gpu-lut-box is running
- Check stream name matches exactly
- Restart Spout In TOP (toggle Active parameter)

### "Colors look wrong"
- Verify `lutSize` uniform matches your LUT
- Check Spout In TOP shows correct resolution
- Ensure Pixel Format is RGBA (not RGB)

### "Performance issues"
- Use smaller LUT size (16 or 33 instead of 64)
- Reduce input resolution
- Check Spout In TOP is using GPU acceleration

### "LUT not updating"
- Check OpenGradeIO connection to server
- Verify server console shows "Streamed LUT" messages
- Try changing LUT in grading software to trigger update

## Example Workflow: Live Grading

1. **Start server**: `uv run virtual-gpu-lut-box`
2. **TouchDesigner**: Setup network as above with live camera input
3. **DaVinci Resolve**:
   - Open Color page
   - Configure Virtual LUT Box to 127.0.0.1:8089
   - Create nodes and adjust color
4. **See results**: Live camera feed in TouchDesigner updates in real-time with your grades!

## HDR / Creative LUTs

The shader supports HDR and creative LUTs with values outside [0,1]:
- Server preserves float32 precision
- Spout streams 32-bit float data (with GL_RGBA32F support)
- Shader applies values directly without clamping

**No special setup needed** - it just works!

## Performance Tips

1. **Resolution**: Lower Spout In TOP resolution if not using full quality
2. **LUT Size**: Start with 33³, only use 64³ if you need the precision
3. **GPU Format**: Use RGBA32Float if available, falls back to RGBA8Fixed gracefully
4. **Caching**: TouchDesigner caches Spout textures automatically

## Technical Details

**Hald Image Format:**
- 2D texture representing 3D LUT
- Layout: Each "blue slice" is laid out horizontally
- Width = size × size, Height = size
- RGB channels contain color data, Alpha is 1.0

**Shader Interpolation:**
- Bilinear sampling within each 2D layer
- Trilinear interpolation across blue dimension
- Smooth gradients even with coarse LUTs

**Float32 Precision:**
- Full pipeline preserves 32-bit float precision
- Critical for professional color grading
- Supports values outside [0,1] range for HDR

## Files

- `td_hald_lut.glsl` - GLSL pixel shader for TouchDesigner
- `TD_SETUP_GUIDE.md` - This guide
- `../test_spout_precision.py` - Test float32 precision preservation

## Questions?

- **Project**: https://github.com/repentsinner/virtual-gpu-lut-box
- **Issues**: https://github.com/repentsinner/virtual-gpu-lut-box/issues
- **Spout**: http://spout.zeal.co/
- **TouchDesigner**: https://derivative.ca/

Happy grading! 🎨
