// TouchDesigner Hald LUT Pixel Shader (Template)
// For use with virtual-gpu-lut-box Spout streaming
//
// This shader applies a Hald image LUT to your input texture using tetrahedral
// interpolation for professional-grade color accuracy.
//
// SETUP IN TOUCHDESIGNER:
// 1. Create a GLSL TOP
// 2. Load the compiled version of this shader (from build/client_integrations/)
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

    // Apply tetrahedral interpolation from core functions
    vec3 gradedColor = applyTetrahedralLUT(color, sTD2DInputs[1], lutSize);

    // Output the graded color with original alpha
    fragColor = TDOutputSwizzle(vec4(gradedColor, textureColor.a));
}
