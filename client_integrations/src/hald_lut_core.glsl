// Hald LUT Core Functions
// Tetrahedral interpolation for 3D LUTs in 2D Hald image format
//
// This file contains shared functions for applying Hald LUTs with tetrahedral
// interpolation across multiple platforms (TouchDesigner, Pixera, etc.)
//
// Tetrahedral interpolation uses 4 samples instead of trilinear's 8, providing
// more accurate color interpolation and reduced artifacts in gradients.

// Helper function: Convert 3D LUT coordinate to 2D Hald image UV
//
// lutCoord: 3D coordinate in LUT space [0, lutSize-1]
// lutSize: Size of the LUT (e.g., 16, 32, 64)
//
// Returns: 2D UV coordinate for sampling the Hald image
vec2 calculateHaldUV(vec3 lutCoord, float lutSize) {
    float haldWidth = lutSize * lutSize;

    // Determine which "blue layer" (page) we're sampling from
    float blueLayer = floor(lutCoord.b);

    // Calculate position in the Hald image
    // The Hald image is laid out as: width = lutSize * lutSize, height = lutSize
    // Each "page" in the blue dimension is laid out horizontally
    float xOffset = blueLayer * lutSize;

    return vec2(
        (lutCoord.g + xOffset) / haldWidth,
        1.0 - (lutCoord.r / lutSize)  // V-flip for numpy->OpenGL conversion
    );
}

// Tetrahedral interpolation for 3D LUT lookup
//
// The unit cube is subdivided into 6 tetrahedra based on the ordering of RGB components.
// This provides more accurate interpolation than trilinear (4 samples vs 8) and is the
// industry standard used in DaVinci Resolve, Baselight, and other professional tools.
//
// color: Input RGB color [0,1]
// haldLUT: Hald image sampler
// lutSize: Size of the LUT (auto-detected from texture)
//
// Returns: Color-graded RGB value
vec3 applyTetrahedralLUT(vec3 color, sampler2D haldLUT, float lutSize) {
    float lutSizeMinusOne = lutSize - 1.0;

    // Scale color values from [0,1] to LUT index space [0, lutSize-1]
    vec3 scaledColor = color * lutSizeMinusOne;

    // Get the base lattice point (lower corner of the cube)
    vec3 baseLUT = floor(scaledColor);

    // Get fractional part for interpolation
    vec3 frac = scaledColor - baseLUT;

    // Clamp to valid LUT range
    baseLUT = clamp(baseLUT, vec3(0.0), vec3(lutSizeMinusOne - 1.0));

    // Determine which tetrahedron we're in based on RGB component ordering
    // There are 6 cases based on which component is largest, middle, and smallest
    //
    // The 6 tetrahedra are defined by the permutations:
    // 1. r >= g >= b
    // 2. r >= b >= g
    // 3. g >= r >= b
    // 4. g >= b >= r
    // 5. b >= r >= g
    // 6. b >= g >= r

    vec3 c0, c1, c2, c3;  // The 4 corner points of the tetrahedron
    float w0, w1, w2, w3;  // Barycentric weights

    // Common base point for all tetrahedra
    c0 = baseLUT;

    if (frac.r >= frac.g) {
        if (frac.g >= frac.b) {
            // Case 1: r >= g >= b
            c1 = baseLUT + vec3(1.0, 0.0, 0.0);
            c2 = baseLUT + vec3(1.0, 1.0, 0.0);
            c3 = baseLUT + vec3(1.0, 1.0, 1.0);
            w0 = 1.0 - frac.r;
            w1 = frac.r - frac.g;
            w2 = frac.g - frac.b;
            w3 = frac.b;
        } else if (frac.r >= frac.b) {
            // Case 2: r >= b >= g
            c1 = baseLUT + vec3(1.0, 0.0, 0.0);
            c2 = baseLUT + vec3(1.0, 0.0, 1.0);
            c3 = baseLUT + vec3(1.0, 1.0, 1.0);
            w0 = 1.0 - frac.r;
            w1 = frac.r - frac.b;
            w2 = frac.b - frac.g;
            w3 = frac.g;
        } else {
            // Case 5: b >= r >= g
            c1 = baseLUT + vec3(0.0, 0.0, 1.0);
            c2 = baseLUT + vec3(1.0, 0.0, 1.0);
            c3 = baseLUT + vec3(1.0, 1.0, 1.0);
            w0 = 1.0 - frac.b;
            w1 = frac.b - frac.r;
            w2 = frac.r - frac.g;
            w3 = frac.g;
        }
    } else {
        if (frac.b >= frac.g) {
            // Case 6: b >= g >= r
            c1 = baseLUT + vec3(0.0, 0.0, 1.0);
            c2 = baseLUT + vec3(0.0, 1.0, 1.0);
            c3 = baseLUT + vec3(1.0, 1.0, 1.0);
            w0 = 1.0 - frac.b;
            w1 = frac.b - frac.g;
            w2 = frac.g - frac.r;
            w3 = frac.r;
        } else if (frac.b >= frac.r) {
            // Case 4: g >= b >= r
            c1 = baseLUT + vec3(0.0, 1.0, 0.0);
            c2 = baseLUT + vec3(0.0, 1.0, 1.0);
            c3 = baseLUT + vec3(1.0, 1.0, 1.0);
            w0 = 1.0 - frac.g;
            w1 = frac.g - frac.b;
            w2 = frac.b - frac.r;
            w3 = frac.r;
        } else {
            // Case 3: g >= r >= b
            c1 = baseLUT + vec3(0.0, 1.0, 0.0);
            c2 = baseLUT + vec3(1.0, 1.0, 0.0);
            c3 = baseLUT + vec3(1.0, 1.0, 1.0);
            w0 = 1.0 - frac.g;
            w1 = frac.g - frac.r;
            w2 = frac.r - frac.b;
            w3 = frac.b;
        }
    }

    // Convert 3D LUT coordinates to 2D Hald UVs and sample
    vec2 uv0 = calculateHaldUV(c0, lutSize);
    vec2 uv1 = calculateHaldUV(c1, lutSize);
    vec2 uv2 = calculateHaldUV(c2, lutSize);
    vec2 uv3 = calculateHaldUV(c3, lutSize);

    vec3 sample0 = texture(haldLUT, uv0).rgb;
    vec3 sample1 = texture(haldLUT, uv1).rgb;
    vec3 sample2 = texture(haldLUT, uv2).rgb;
    vec3 sample3 = texture(haldLUT, uv3).rgb;

    // Blend using barycentric weights
    return w0 * sample0 + w1 * sample1 + w2 * sample2 + w3 * sample3;
}
