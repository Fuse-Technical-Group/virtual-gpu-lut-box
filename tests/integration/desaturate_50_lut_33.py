#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Fuse Technical Group
#
# SPDX-License-Identifier: BSD-3-Clause

"""Stream an animated desaturation LUT that ramps between full color and grayscale.

This LUT animates over 3 seconds, ramping from full saturation (0%) to
full desaturation (100%) and back, creating a breathing color effect.

This demonstrates real-time LUT animation - useful for creative effects,
transitions, or testing dynamic color grading pipelines.

Press Ctrl+C to exit.
"""

import sys
import time

import numpy as np

from virtual_gpu_lut_box.gpu_texture_stream.factory import StreamingFactory
from virtual_gpu_lut_box.lut.hald_converter import HaldConverter


def create_desaturation_lut(
    lut_size: int = 33, desaturation: float = 0.5
) -> np.ndarray:
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
                lut[r, g, b, 0] = luminance * desaturation + r_val * (
                    1.0 - desaturation
                )
                lut[r, g, b, 1] = luminance * desaturation + g_val * (
                    1.0 - desaturation
                )
                lut[r, g, b, 2] = luminance * desaturation + b_val * (
                    1.0 - desaturation
                )

    return lut


def main():
    """Stream animated desaturation LUT until key press."""
    lut_size = 33
    animation_period = 3.0  # 3 seconds per cycle

    print("=" * 70)
    print("Animated Desaturation LUT Streaming Test")
    print("=" * 70)
    print(f"\nAnimation: 0% → 100% → 0% desaturation over {animation_period}s")
    print(f"LUT size: {lut_size}³")

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

    # Stream the animated LUT
    print("\n" + "=" * 70)
    print("Streaming Animated Desaturation LUT")
    print("=" * 70)
    print(f"\nStream name: '{backend.name}'")
    print("   Open your Spout/Syphon receiver (TouchDesigner, etc.)")
    print(f"\n   Watch the colors breathe in and out over {animation_period}s cycles!")
    print("   Full color → Grayscale → Full color\n")
    print("   Press Ctrl+C to stop streaming...\n")

    frame_count = 0
    start_time = time.time()
    converter = HaldConverter(lut_size=lut_size)

    try:
        with backend:
            # Stream continuously until interrupted
            while True:
                # Calculate current desaturation based on elapsed time
                elapsed = time.time() - start_time
                cycle_position = (elapsed % animation_period) / (animation_period / 2.0)

                # Triangle wave: 0→1→0 over animation_period
                if cycle_position <= 1.0:
                    desaturation = cycle_position  # Ramp up: 0 to 1
                else:
                    desaturation = 2.0 - cycle_position  # Ramp down: 1 to 0

                # Generate LUT with current desaturation value
                lut = create_desaturation_lut(lut_size, desaturation)
                hald_image = converter.lut_to_hald(lut)

                # Send to GPU
                backend.send_lut_texture(hald_image)
                frame_count += 1

                # Progress indicator - update every frame with current desaturation
                print(
                    f"\r   Streaming... {frame_count} frames | "
                    f"Desaturation: {desaturation * 100:5.1f}% | "
                    f"Time: {elapsed:.1f}s",
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
