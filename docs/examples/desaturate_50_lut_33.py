#!/usr/bin/env python3
"""Stream a 33x33x33 desaturation LUT (50%) until a key is pressed.

A 50% desaturation LUT blends the input colors halfway with their grayscale
(luminance) values, creating a partially desaturated look.

This demonstrates how 3D LUTs can encode any color transformation,
not just identity passes.

Press Ctrl+C to exit.
"""

import sys

import numpy as np

from virtual_gpu_lut_box.gpu_texture_stream.factory import StreamingFactory
from virtual_gpu_lut_box.lut.hald_converter import HaldConverter


def create_desaturation_lut(lut_size: int = 33, desaturation: float = 0.5) -> np.ndarray:
    """Create a desaturation LUT.

    Args:
        lut_size: Size of the LUT cube (default: 33)
        desaturation: Amount of desaturation, 0.0=full color, 1.0=grayscale (default: 0.5)

    Returns:
        Desaturation LUT array with shape (size, size, size, 3)
    """
    lut = np.zeros((lut_size, lut_size, lut_size, 3), dtype=np.float32)

    # Rec. 709 luminance coefficients (standard for HD video)
    luma_r = 0.2126
    luma_g = 0.7152
    luma_b = 0.0722

    for r in range(lut_size):
        for g in range(lut_size):
            for b in range(lut_size):
                # Original color values
                r_val = r / (lut_size - 1)
                g_val = g / (lut_size - 1)
                b_val = b / (lut_size - 1)

                # Calculate luminance (grayscale value)
                luminance = luma_r * r_val + luma_g * g_val + luma_b * b_val

                # Blend between grayscale and original color
                # desaturation=0.0 → full color (luminance weight = 0%)
                # desaturation=1.0 → full grayscale (luminance weight = 100%)
                lut[r, g, b, 0] = luminance * desaturation + r_val * (1.0 - desaturation)
                lut[r, g, b, 1] = luminance * desaturation + g_val * (1.0 - desaturation)
                lut[r, g, b, 2] = luminance * desaturation + b_val * (1.0 - desaturation)

    return lut


def main():
    """Stream desaturation LUT until key press."""
    lut_size = 33
    desaturation_amount = 0.5  # 50% desaturation

    print("=" * 70)
    print(f"Desaturation LUT Streaming Test ({desaturation_amount*100:.0f}%)")
    print("=" * 70)
    print(f"\nCreating {lut_size}³ desaturation LUT...")

    # Create desaturation LUT
    lut = create_desaturation_lut(lut_size, desaturation_amount)
    print(f"Created LUT with shape: {lut.shape}")
    print(f"  Range: [{lut.min():.3f}, {lut.max():.3f}]")

    # Debug: Check specific colors
    print("\n  Debug - Sample LUT transformations:")
    print(f"    Black [0,0,0] → {lut[0,0,0]} (should stay [0.0, 0.0, 0.0])")
    print(f"    White [32,32,32] → {lut[32,32,32]} (should stay [1.0, 1.0, 1.0])")
    print(f"    Pure Red [32,0,0] → {lut[32,0,0]} (should be desaturated red)")
    print(f"    Pure Green [0,32,0] → {lut[0,32,0]} (should be desaturated green)")
    print(f"    Pure Blue [0,0,32] → {lut[0,0,32]} (should be desaturated blue)")

    # Convert to Hald format
    print("\nConverting to Hald image format...")
    converter = HaldConverter(lut_size=lut_size)
    hald_image = converter.lut_to_hald(lut)
    print(f"Hald image dimensions: {hald_image.shape[1]}x{hald_image.shape[0]}")

    # Create streaming backend
    print("\nInitializing streaming backend...")
    try:
        backend = StreamingFactory.create_lut_streamer(
            name="virtual-gpu-lut-box", lut_size=lut_size
        )
        print(f"Created backend: {backend.__class__.__name__}")
        print(f"  Stream name: {backend.name}")
        print(f"  Dimensions: {backend.width}x{backend.height}")

    except Exception as e:
        print(f"\nError creating backend: {e}")
        print("\nIs Spout/Syphon available on this platform?")
        sys.exit(1)

    # Stream the LUT
    print("\n" + "=" * 70)
    print(f"Streaming {desaturation_amount*100:.0f}% Desaturation LUT")
    print("=" * 70)
    print(f"\nStream name: '{backend.name}'")
    print("   Open your Spout/Syphon receiver (TouchDesigner, etc.)")
    print(f"\n   With this LUT, your image should look {desaturation_amount*100:.0f}% desaturated.")
    print("   Colors should be less vibrant, moving halfway toward grayscale.\n")
    print("   Press Ctrl+C to stop streaming...\n")

    frame_count = 0

    try:
        with backend:
            # Stream continuously until interrupted
            while True:
                backend.send_lut_texture(hald_image)
                frame_count += 1

                # Progress indicator - update in place every 30 frames (~1 second)
                if frame_count % 30 == 0:
                    elapsed = frame_count / 30  # seconds at 30 FPS
                    print(
                        f"\r   Streaming... {frame_count} frames ({elapsed:.0f}s)",
                        end="",
                        flush=True,
                    )

    except KeyboardInterrupt:
        elapsed = frame_count / 30  # seconds at 30 FPS
        print(f"\n\nStopped streaming after {frame_count} frames ({elapsed:.1f}s)")
        print("Stream closed successfully.")

    except Exception as e:
        print(f"\n\nError during streaming: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
