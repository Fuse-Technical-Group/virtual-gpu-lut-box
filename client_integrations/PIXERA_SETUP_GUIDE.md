# Pixera Setup Guide

Real-time LUT streaming integration for Pixera media server.

## Layer Structure

```
Content Layer (your video/image)
    ↓
Effect: pixera_hald_lut
    ├── inputImage: Content (auto-connected)
    └── lutImage: Spout Input Layer
```

## Configuration

### 1. Import Shader

1. Copy `client_integrations/pixera_hald_lut.glsl` to Pixera effects folder
2. Restart Pixera to refresh effects library
3. Shader appears as "pixera_hald_lut"

### 2. Spout Input Layer

Add **Spout Input Layer**:

- **Source**: Spout input
- **Name**: Your stream name (e.g., "MyProject-LUT" or "vglb-lut-{channel}")
- **Resolution**: Auto-detects (e.g., 1089x33 for 33³ LUT)

Stream should show Hald image texture (rainbow gradient grid).

### 3. Apply Effect

1. Select your content layer
2. Add "pixera_hald_lut" effect
3. Connect **lutImage** to Spout Input Layer (inputImage auto-connects to content)

LUT size is auto-detected from texture dimensions - no manual configuration.

## Multiple Channels

For multi-screen/multi-zone grading:

1. Create separate Spout Input Layers per channel
2. Names: "vglb-lut-channel1", "vglb-lut-channel2", etc.
3. Apply effect to each content layer with appropriate LUT input

## Troubleshooting

**Shader not appearing:**
- Verify filename is exactly `pixera_hald_lut.glsl`
- Check correct effects directory
- Restart Pixera

**No Spout stream:**
- Verify `virtual-gpu-lut-box` is running
- Check stream name matches exactly
- Refresh input layer

**Colors incorrect:**
- Verify Spout input resolution (should be e.g., 1089x33)
- Ensure lutImage connected to correct Spout layer

**LUT not updating:**
- Check OpenGradeIO connection to server
- Verify server console shows "Streamed LUT" messages

## Platform Notes

- **Windows**: Spout streaming (RGBA32Float required)
- **Precision**: 32-bit float only - no 8-bit formats supported
- **HDR**: Values outside [0,1] preserved
- **Shader Format**: Pixera-specific struct-based format (returns vec4)

## Links

- **Project**: https://github.com/repentsinner/virtual-gpu-lut-box
- **Spout**: http://spout.zeal.co/
- **Pixera**: https://pixera.one/
