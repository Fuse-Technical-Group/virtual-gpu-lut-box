// TouchDesigner Hald LUT Pixel Shader
// For use with virtual-gpu-lut-box Spout streaming
//
// This shader applies a Hald image LUT to your input texture.
// Hald images are 2D representations of 3D LUTs optimized for GPU sampling.
//
// SETUP IN TOUCHDESIGNER:
// 1. Create a GLSL TOP
// 2. Load this file as Pixel Shader (or paste code into built-in editor)
// 3. Connect inputs:
//    - Input 1: Your image to color grade
//    - Input 2: Spout In TOP receiving the Hald LUT stream
// 4. Done! No uniforms needed - LUT size is auto-detected!

// Output
out vec4 fragColor;

void main()
{
    // Sample the input image to be graded
    vec4 textureColor = texture(sTD2DInputs[0], vUV.st);
    vec3 color = textureColor.rgb;

    // Auto-detect LUT size from Hald texture dimensions
    // Use textureSize() to directly query the sampler (more reliable!)
    ivec2 haldSize = textureSize(sTD2DInputs[1], 0);  // Returns (width, height)
    float lutSize = float(haldSize.y);  // Height = LUT size

    // Validate LUT dimensions - if invalid/dead stream, pass through unchanged
    // Valid Hald LUT must have: height >= 16 and width == height²
    bool isValidLUT = (haldSize.y >= 16) && (haldSize.x == haldSize.y * haldSize.y);

    if (!isValidLUT) {
        // Invalid or missing LUT - pass through input unchanged (identity)
        fragColor = TDOutputSwizzle(textureColor);
        return;
    }

    // Calculate Hald LUT coordinates from RGB color values
    // The Hald image is laid out as a grid: width = lutSize * lutSize, height = lutSize
    // Each "page" in the blue dimension is laid out horizontally

    float lutSizeMinusOne = lutSize - 1.0;

    // Scale color values from [0,1] to LUT index space [0, lutSize-1]
    vec3 scaledColor = color * lutSizeMinusOne;

    // Determine which "blue layer" (page) we're sampling from
    float blueLayer = floor(scaledColor.b);
    float blueFraction = scaledColor.b - blueLayer;

    // Calculate positions in the Hald image for the two blue layers we'll interpolate
    float haldWidth = lutSize * lutSize;

    // First blue layer
    float xOffset1 = blueLayer * lutSize;
    vec2 haldUV1 = vec2(
        (scaledColor.g + xOffset1) / haldWidth,
        1.0 - (scaledColor.r / lutSize)  // V-flip for numpy->OpenGL conversion
    );

    // Second blue layer (for interpolation)
    float blueLayer2 = min(blueLayer + 1.0, lutSizeMinusOne);
    float xOffset2 = blueLayer2 * lutSize;
    vec2 haldUV2 = vec2(
        (scaledColor.g + xOffset2) / haldWidth,
        1.0 - (scaledColor.r / lutSize)  // V-flip for numpy->OpenGL conversion
    );

    // Sample both blue layers
    vec3 color1 = texture(sTD2DInputs[1], haldUV1).rgb;
    vec3 color2 = texture(sTD2DInputs[1], haldUV2).rgb;

    // Interpolate between the two layers for smooth gradients
    vec3 gradedColor = mix(color1, color2, blueFraction);

    // Output the graded color with original alpha
    fragColor = TDOutputSwizzle(vec4(gradedColor, textureColor.a));
}
