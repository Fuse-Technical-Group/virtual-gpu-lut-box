/*
 * SPDX-FileCopyrightText: 2025 Fuse Technical Group
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

// Hald LUT Core Functions
// Tetrahedral interpolation for 3D LUTs in 2D Hald image format
//
// This file contains shared functions for applying Hald LUTs with tetrahedral
// interpolation across multiple platforms (TouchDesigner, Pixera, etc.)
//
// Tetrahedral interpolation uses 4 samples instead of trilinear's 8, providing
// more accurate color interpolation and reduced artifacts in gradients.

// Helper function: Convert a 3D LUT coordinate to a 2D integer pixel coordinate.
// lutCoord: Integer 3D coordinate in LUT space [0, lutSize-1]
// lutSize:  Size of the LUT (e.g., 16, 33, 64)
// Returns:  2D integer pixel coordinate for `texelFetch`
ivec2 calculateHaldPixelCoord(vec3 lutCoord, float lutSize) {
    // Determine which "blue layer" (page) we're sampling from
    float blueLayer = floor(lutCoord.b);
    int x = int(lutCoord.g + blueLayer * lutSize);

    // V-flip for numpy->OpenGL conversion
    // The Hald image is generated in numpy, where (0,0) is top-left.
    // In OpenGL textures, (0,0) is often bottom-left. This flips the R (Y) axis.
    int y = int(lutSize - 1.0 - lutCoord.r);

    return ivec2(x, y);
}

// Tetrahedral interpolation for 3D LUT lookup
//
// The unit cube is subdivided into 6 tetrahedra based on the ordering of RGB components.
// This provides more accurate interpolation than trilinear (4 samples vs 8) and is the
// industry standard for professional color grading.
//
// This implementation follows the algorithm described in NVIDIA's GPU Gems 2,
// Chapter 24: "Using Lookup Tables to Accelerate Color Transformations".
// https://developer.nvidia.com/gpugems/gpugems2/part-iii-high-quality-rendering/chapter-24-using-lookup-tables-accelerate-color
//
// This implementation is designed for linear floating-point color spaces and correctly
// handles HDR values outside the [0,1] range by clamping them to the LUT's edge.
//
// color: Input RGB color. Designed for linear float data, including HDR values.
// haldLUT: Hald image sampler
// lutSize: Size of the LUT (auto-detected from texture)
//
// --- How it Works (Schematically) ---
// 1. **Scale**: The input color (e.g., `vec3(0.5, 0.2, 0.8)`) is scaled from the
//    [0,1] range to the LUT's index space (e.g., [0, 32] for a 33-size LUT).
//    This gives a floating-point coordinate within the LUT's 3D grid.
// 2. **Locate**: We find the 8 integer grid points that form a small "sub-cube"
//    around our scaled coordinate.
// 3. **Interpolate**: Instead of simple trilinear interpolation between the 8 corners,
//    this function divides the sub-cube into 6 tetrahedra and finds which one
//    our point is in. It then performs a more accurate blend using the 4 corners
//    of that specific tetrahedron.
//
vec3 applyTetrahedralLUT(vec3 color, sampler2D haldLUT, float lutSize) {
    float lutSizeMinusOne = lutSize - 1.0;

    // Scale color values from [0,1] to LUT index space [0, lutSize-1]
    vec3 scaledColor = color * lutSizeMinusOne;

    // Get the base lattice point (lower corner of the cube)
    vec3 baseLUT = floor(scaledColor);

    // Get fractional part for interpolation
    vec3 frac = scaledColor - baseLUT;

    // Clamp the base lookup coordinate to the valid range of the LUT.
    //
    // HDR Handling (Display-Referred Workflow):
    // Values >1.0 are clamped to the LUT's white point. This is appropriate for
    // display-referred workflows where the LUT operates on [0,1] SDR content and
    // HDR highlights (specular reflections, bright lights) inherit the white point's
    // transform without further grading.
    //
    // Scene-Referred HDR Limitation:
    // For scene-referred HDR workflows spanning multiple stops (e.g., -6 to +10 EV),
    // a shaper curve (log2, PQ, etc.) would be needed to compress the full HDR range
    // into [0,1] before LUT application. This is not currently implemented.
    baseLUT = clamp(baseLUT, vec3(0.0), vec3(lutSizeMinusOne));

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

    // Select the appropriate tetrahedron for the input color/point
    // Clamp corner coordinates to prevent texelFetch out-of-bounds access at LUT edges
    if (frac.r >= frac.g) {
        if (frac.g >= frac.b) {
            // Case 1: r >= g >= b
            c1 = clamp(baseLUT + vec3(1.0, 0.0, 0.0), vec3(0.0), vec3(lutSizeMinusOne));
            c2 = clamp(baseLUT + vec3(1.0, 1.0, 0.0), vec3(0.0), vec3(lutSizeMinusOne));
            c3 = clamp(baseLUT + vec3(1.0, 1.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            w0 = 1.0 - frac.r;
            w1 = frac.r - frac.g;
            w2 = frac.g - frac.b;
            w3 = frac.b;
        } else if (frac.r >= frac.b) {
            // Case 2: r >= b >= g
            c1 = clamp(baseLUT + vec3(1.0, 0.0, 0.0), vec3(0.0), vec3(lutSizeMinusOne));
            c2 = clamp(baseLUT + vec3(1.0, 0.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            c3 = clamp(baseLUT + vec3(1.0, 1.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            w0 = 1.0 - frac.r;
            w1 = frac.r - frac.b;
            w2 = frac.b - frac.g;
            w3 = frac.g;
        } else {
            // Case 5: b >= r >= g
            c1 = clamp(baseLUT + vec3(0.0, 0.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            c2 = clamp(baseLUT + vec3(1.0, 0.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            c3 = clamp(baseLUT + vec3(1.0, 1.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            w0 = 1.0 - frac.b;
            w1 = frac.b - frac.r;
            w2 = frac.r - frac.g;
            w3 = frac.g;
        }
    } else {
        if (frac.b >= frac.g) {
            // Case 6: b >= g >= r
            c1 = clamp(baseLUT + vec3(0.0, 0.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            c2 = clamp(baseLUT + vec3(0.0, 1.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            c3 = clamp(baseLUT + vec3(1.0, 1.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            w0 = 1.0 - frac.b;
            w1 = frac.b - frac.g;
            w2 = frac.g - frac.r;
            w3 = frac.r;
        } else if (frac.b >= frac.r) {
            // Case 4: g >= b >= r
            c1 = clamp(baseLUT + vec3(0.0, 1.0, 0.0), vec3(0.0), vec3(lutSizeMinusOne));
            c2 = clamp(baseLUT + vec3(0.0, 1.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            c3 = clamp(baseLUT + vec3(1.0, 1.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            w0 = 1.0 - frac.g;
            w1 = frac.g - frac.b;
            w2 = frac.b - frac.r;
            w3 = frac.r;
        } else {
            // Case 3: g >= r >= b
            c1 = clamp(baseLUT + vec3(0.0, 1.0, 0.0), vec3(0.0), vec3(lutSizeMinusOne));
            c2 = clamp(baseLUT + vec3(1.0, 1.0, 0.0), vec3(0.0), vec3(lutSizeMinusOne));
            c3 = clamp(baseLUT + vec3(1.0, 1.0, 1.0), vec3(0.0), vec3(lutSizeMinusOne));
            w0 = 1.0 - frac.g;
            w1 = frac.g - frac.r;
            w2 = frac.r - frac.b;
            w3 = frac.b;
        }
    }

    // The logic above operates in a conceptual 3D LUT space, identifying the
    // four 3D integer coordinates (c0, c1, c2, c3) of the tetrahedron's corners.
    //
    // Now, we translate each of these 3D coordinates into a 2D UV coordinate
    // for sampling the Hald image. The `calculateHaldUV` function handles this
    // mapping, ensuring that the blue component correctly offsets the lookup
    // to the right "page" in the 2D texture.
    //
    // This separation of concerns (3D logic first, 2D translation last) ensures
    // that we perform a true 3D tetrahedral interpolation without any loss of
    // quality or precision on any axis.
    ivec2 p0 = calculateHaldPixelCoord(c0, lutSize);
    ivec2 p1 = calculateHaldPixelCoord(c1, lutSize);
    ivec2 p2 = calculateHaldPixelCoord(c2, lutSize);
    ivec2 p3 = calculateHaldPixelCoord(c3, lutSize);

    // Sample the four corner points of the tetrahedron.
    // `texelFetch` performs a direct integer lookup, fetching the exact value of a
    // single texel without any hardware interpolation. This is ideal for our manual
    // barycentric blend. The third argument (LOD) is 0 for non-mipmapped textures.
    // On modern GPUs, performance is equivalent to using texture() with a calculated
    // offset, but this approach is more explicit about its intent.
    vec3 sample0 = texelFetch(haldLUT, p0, 0).rgb;
    vec3 sample1 = texelFetch(haldLUT, p1, 0).rgb;
    vec3 sample2 = texelFetch(haldLUT, p2, 0).rgb;
    vec3 sample3 = texelFetch(haldLUT, p3, 0).rgb;

    // Blend using barycentric weights
    return w0 * sample0 + w1 * sample1 + w2 * sample2 + w3 * sample3;
}
