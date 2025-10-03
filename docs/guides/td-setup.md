# TouchDesigner Setup Guide

Real-time LUT streaming integration for TouchDesigner.

## Network Setup

```
[Movie In TOP / Camera]
         ↓
    [GLSL TOP] ← [Spout In TOP]
         ↓
    [Out TOP]
```

## Configuration

### 1. Spout/Syphon Input

Add **Spout In TOP** (Windows) or **Syphon In TOP** (macOS):

- **Spout/Syphon** page:
  - **Name**: Your stream name (e.g., "MyProject-LUT" or "vglb-lut-{channel}")
- **Common** page:
  - **Output Resolution**: Use Input (default)
  - **Use Global Res Multiplier**: Off
  - **Output Aspect**: Use Input
  - **Pixel Format**: Use Input (default)
  - **Fill Viewer**: any
  - **Viewer Smoothness**: any

Stream should auto-detect as RGBA32Float with dimensions like 1089x33 for 33³ LUT.

### 2. GLSL TOP

1. Add **GLSL TOP**
2. **Inputs** tab: Connect your image to Input 1, Spout In TOP to Input 2
3. **GLSL** page → **Pixel Shader** → Click the Text DAT path field
4. Load `client_integrations/td_hald_lut.glsl`
5. In the Text DAT: **Sync to File** → On

LUT size is auto-detected from texture dimensions - no uniforms needed.

## Troubleshooting

**No Spout stream found:**
- Verify `virtual-gpu-lut-box` is running
- Check stream name matches exactly
- Toggle Spout In TOP Active parameter

**Colors incorrect:**
- Verify Spout In TOP resolution (should be e.g., 1089x33)
- Ensure Pixel Format is RGBA (not RGB)

**Performance issues:**
- Use smaller LUT size (33³ instead of 64³)
- Reduce input resolution
- Verify GPU acceleration enabled

**LUT not updating:**
- Check OpenGradeIO connection to server
- Verify server console shows "Streamed LUT" messages

## Platform Notes

- **Windows**: Spout streaming (RGBA32Float required)
- **macOS**: Syphon streaming via Metal (RGBA32Float required)
- **Precision**: 32-bit float only - no 8-bit formats supported
- **HDR**: Values outside [0,1] preserved

## Links

- **Project**: https://github.com/repentsinner/virtual-gpu-lut-box
- **Spout**: http://spout.zeal.co/
- **Syphon**: http://syphon.v002.info/
