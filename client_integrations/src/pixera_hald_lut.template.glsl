// Pixera Hald LUT Shader (Template)
// For use with virtual-gpu-lut-box Spout streaming
//
// This shader applies a Hald image LUT to your input texture using tetrahedral
// interpolation for professional-grade color accuracy.
//
// SETUP IN PIXERA:
// 1. Add this shader to your effects library
// 2. Apply to a layer
// 3. Connect inputs:
//    - inputImage: Your content to color grade
//    - lutImage: Spout input receiving the Hald LUT stream

// Pixera requires: filename = struct name = function name
// This must be named "pixera_hald_lut" to match the output filename
struct pixera_hald_lut {
    sampler2D inputImage;
    sampler2D lutImage;
};

// Pixera's entry point: returns vec4 instead of void main()
vec4 pixera_hald_lut(in pixera_hald_lut s, vec2 tex_coords) {
    // Sample the input image to be graded
    vec4 textureColor = texture(s.inputImage, tex_coords);
    vec3 color = textureColor.rgb;

    // Auto-detect LUT size from Hald texture dimensions
    ivec2 haldSize = textureSize(s.lutImage, 0);  // Returns (width, height)
    float lutSize = float(haldSize.y);  // Height = LUT size

    // Validate LUT dimensions - if invalid/dead stream, pass through unchanged
    // Valid Hald LUT must have: height >= 16 and width == height²
    bool isValidLUT = (haldSize.y >= 16) && (haldSize.x == haldSize.y * haldSize.y);

    if (!isValidLUT) {
        // Invalid or missing LUT - pass through input unchanged (identity)
        return textureColor;
    }

    // Apply tetrahedral interpolation from core functions
    vec3 gradedColor = applyTetrahedralLUT(color, s.lutImage, lutSize);

    // Return the graded color with original alpha
    return vec4(gradedColor, textureColor.a);
}
