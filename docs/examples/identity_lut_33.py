#!/usr/bin/env python3
"""Stream a 33x33x33 identity LUT until a key is pressed.

An identity LUT passes colors through unchanged - useful for testing
that your pipeline is working correctly. The image should look identical
to the original with an identity LUT applied.

Press any key to exit.
"""

import sys

import numpy as np

from virtual_gpu_lut_box.gpu_texture_stream.factory import StreamingFactory
from virtual_gpu_lut_box.lut.hald_converter import HaldConverter


def create_identity_lut(lut_size: int = 33) -> np.ndarray:
    """Create an identity LUT where output = input.

    Args:
        lut_size: Size of the LUT cube (default: 33)

    Returns:
        Identity LUT array with shape (size, size, size, 3)
    """
    lut = np.zeros((lut_size, lut_size, lut_size, 3), dtype=np.float32)

    for r in range(lut_size):
        for g in range(lut_size):
            for b in range(lut_size):
                lut[r, g, b, 0] = r / (lut_size - 1)  # R
                lut[r, g, b, 1] = g / (lut_size - 1)  # G
                lut[r, g, b, 2] = b / (lut_size - 1)  # B

    return lut


def main():
    """Stream identity LUT until key press."""
    lut_size = 33

    print("=" * 70)
    print("Identity LUT Streaming Test")
    print("=" * 70)
    print(f"\nCreating {lut_size}³ identity LUT...")

    # Create identity LUT
    lut = create_identity_lut(lut_size)
    print(f"Created LUT with shape: {lut.shape}")
    print(f"  Range: [{lut.min():.3f}, {lut.max():.3f}]")

    # Debug: Check specific coordinates
    print("\n  Debug - Sample LUT values:")
    print(f"    lut[0,0,0] = {lut[0,0,0]} (should be [0.0, 0.0, 0.0])")
    print(f"    lut[32,0,0] = {lut[32,0,0]} (should be [1.0, 0.0, 0.0])")
    print(f"    lut[0,32,0] = {lut[0,32,0]} (should be [0.0, 1.0, 0.0])")
    print(f"    lut[0,0,32] = {lut[0,0,32]} (should be [0.0, 0.0, 1.0])")
    print(f"    lut[32,32,32] = {lut[32,32,32]} (should be [1.0, 1.0, 1.0])")

    # Convert to Hald format
    print("\nConverting to Hald image format...")
    converter = HaldConverter(lut_size=lut_size)
    hald_image = converter.lut_to_hald(lut)
    print(f"Hald image dimensions: {hald_image.shape[1]}x{hald_image.shape[0]}")

    # Debug: Check Hald image corners and key positions
    print("\n  Debug - Sample Hald image values:")
    print(f"    Top-left corner [0,0] = {hald_image[0,0,:3]} (should be [0.0, 0.0, 0.0])")
    print(f"    Top-right of first page [0,32] = {hald_image[0,32,:3]} (should be [0.0, 1.0, 0.0])")
    print(f"    Bottom-left of first page [32,0] = {hald_image[32,0,:3]} (should be [1.0, 0.0, 0.0])")
    print(f"    Top-left of last page [0,1056] = {hald_image[0,1056,:3]} (should be [0.0, 0.0, 1.0])")
    print(f"    Bottom-right corner [32,1088] = {hald_image[32,1088,:3]} (should be [1.0, 1.0, 1.0])")

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
    print("Streaming Identity LUT")
    print("=" * 70)
    print(f"\nStream name: '{backend.name}'")
    print("   Open your Spout/Syphon receiver (TouchDesigner, etc.)")
    print("\n   With an identity LUT, your image should look UNCHANGED.")
    print("   If colors look different, something is wrong in your pipeline!\n")
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
