#!/usr/bin/env python3
"""Basic usage examples for virtual-gpu-lut-box."""

import numpy as np

from virtual_gpu_lut_box import HaldConverter, LUTGenerator, StreamingFactory


def example_lut_generation():
    """Example: Generate different types of LUTs."""
    print("=== LUT Generation Examples ===")

    # Create LUT generator
    generator = LUTGenerator(size=33)

    # 1. Identity LUT (no changes)
    identity_lut = generator.identity_lut
    print(f"Identity LUT shape: {identity_lut.shape}")
    print(f"Identity LUT corners: {identity_lut[0, 0, 0]}, {identity_lut[32, 32, 32]}")

    # 2. Gamma correction
    gamma_lut = generator.apply_gamma(2.2)
    print(f"Gamma LUT midpoint: {gamma_lut[16, 16, 16]}")

    # 3. Brightness and contrast
    bc_lut = generator.apply_brightness_contrast(brightness=0.1, contrast=1.2)
    print(f"Brightness/Contrast LUT midpoint: {bc_lut[16, 16, 16]}")

    # 4. Hue and saturation
    hs_lut = generator.apply_hue_saturation(hue_shift=np.pi / 6, saturation=1.3)
    print(f"Hue/Saturation LUT shape: {hs_lut.shape}")

    # 5. Custom LUT with all adjustments
    custom_lut = generator.create_custom_lut(
        gamma=2.2, brightness=0.05, contrast=1.1, hue_shift=np.pi / 12, saturation=1.15
    )
    print(f"Custom LUT range: [{custom_lut.min():.3f}, {custom_lut.max():.3f}]")

    return custom_lut


def example_hald_conversion():
    """Example: Convert LUT to Hald image format."""
    print("\\n=== Hald Conversion Examples ===")

    # Generate a LUT
    generator = LUTGenerator(size=33)
    lut = generator.create_custom_lut(gamma=2.2, brightness=0.1)

    # Create Hald converter
    converter = HaldConverter(lut_size=33)

    # Convert to Hald image
    hald_image = converter.lut_to_hald(lut)
    print(f"Hald image dimensions: {hald_image.shape}")
    print(f"Hald image size: {hald_image.shape[1]}x{hald_image.shape[0]} pixels")

    # Get shader sampling info
    shader_info = converter.get_shader_sampling_info()
    print("Shader sampling constants:")
    for key, value in shader_info.items():
        print(f"  {key}: {value}")

    # Save Hald image
    try:
        converter.save_hald_image(hald_image, "example_lut.png")
        print("Saved Hald image to example_lut.png")
    except Exception as e:
        print(f"Could not save image: {e}")

    # Convert back to LUT (roundtrip test)
    recovered_lut = converter.hald_to_lut(hald_image)
    print(f"Roundtrip successful: {np.allclose(lut, recovered_lut)}")

    return hald_image


def example_streaming_setup():
    """Example: Set up streaming backend and stream LUT."""
    print("\\n=== Streaming Setup Examples ===")

    # Check platform support
    platform_info = StreamingFactory.get_platform_info()
    print(f"Platform: {platform_info['system']}")
    print(f"Python version: {platform_info['python_version']}")

    # Check available backends
    backends = StreamingFactory.get_available_backends()
    print(f"Available backends: {backends}")

    # Check if current platform is supported
    is_supported = StreamingFactory.is_platform_supported()
    print(f"Platform supported: {is_supported}")

    if is_supported:
        # Get supported formats
        formats = StreamingFactory.list_supported_formats()
        print(f"Supported formats: {formats}")

        try:
            # Create streaming backend (uses default name "virtual-gpu-lut-box")
            backend = StreamingFactory.create_lut_streamer()
            print(f"Created backend: {backend.__class__.__name__}")
            print(f"Backend dimensions: {backend.width}x{backend.height}")
            print(f"Stream name: {backend.name}")

            # Check if backend is available
            if backend.is_available():
                print("Backend is available for streaming")

                # Generate and stream a LUT
                print("\\n🎥 Starting LUT streaming demo...")
                generator = LUTGenerator(size=33)
                converter = HaldConverter(lut_size=33)

                # Create a LUT with some adjustments
                lut = generator.create_custom_lut(
                    gamma=2.2, brightness=0.1, contrast=1.2, saturation=1.1
                )

                # Convert to Hald image
                hald_image = converter.lut_to_hald(lut)

                # Stream the LUT
                with backend:
                    print(f"📡 Streaming LUT to '{backend.name}' stream...")
                    print("   Check your Syphon/Spout receiver now!")
                    print("   Streaming for 15 seconds...")

                    import time

                    start_time = time.time()
                    frame_count = 0

                    while time.time() - start_time < 15.0:
                        backend.send_lut_texture(hald_image)
                        frame_count += 1
                        time.sleep(1 / 30)  # 30 FPS

                    print(f"✅ Streamed {frame_count} frames over 15 seconds")

            else:
                print("Backend is not available (missing dependencies)")

        except Exception as e:
            print(f"Could not create backend: {e}")
    else:
        print("Streaming not supported on this platform")
        print(
            "\\n💡 Platform-specific streaming dependencies are automatically installed!"
        )
        print("   - No extra steps needed - Syphon/Spout support is built-in")
        print(
            "\\n🎬 Demo would stream for 15 seconds at 30 FPS if dependencies were available"
        )


def example_texture_formats():
    """Example: Work with different texture formats."""
    print("\\n=== Texture Format Examples ===")

    # Generate LUT and convert to Hald
    generator = LUTGenerator(size=17)  # Smaller for demo
    lut = generator.create_custom_lut(gamma=2.2)

    converter = HaldConverter(lut_size=17)
    converter.lut_to_hald(lut)

    # Convert to different texture formats
    formats = ["rgb", "rgba", "bgr", "bgra"]

    for fmt in formats:
        texture_data = converter.convert_lut_to_texture_data(lut, fmt)
        print(
            f"{fmt.upper()} format: {texture_data.shape}, range: [{texture_data.min():.3f}, {texture_data.max():.3f}]"
        )

    # Show optimal texture size
    width, height = converter.get_optimal_texture_size()
    print(f"Optimal texture size: {width}x{height}")


def example_gpu_coordinates():
    """Example: Generate GPU texture coordinates."""
    print("\\n=== GPU Texture Coordinates ===")

    converter = HaldConverter(lut_size=5)  # Small for demo

    # Get texture coordinates
    u_coords, v_coords = converter.create_gpu_texture_coords()
    print(f"U coordinates: {len(u_coords)} values")
    print(f"First few U coords: {u_coords[:5]}")
    print(f"V coordinates: {len(v_coords)} values")
    print(f"V coords: {v_coords}")

    # Get slice boundaries
    boundaries = converter.get_slice_boundaries()
    print(f"Slice boundaries: {len(boundaries)} slices")
    for i, (start, end) in enumerate(boundaries):
        print(f"  Slice {i}: U = {start:.3f} to {end:.3f}")


def main():
    """Run all examples."""
    print("Virtual GPU LUT Box - Basic Usage Examples")
    print("=" * 50)

    # Run examples
    example_lut_generation()
    example_hald_conversion()
    example_streaming_setup()
    example_texture_formats()
    example_gpu_coordinates()

    print("\\n=== All Examples Complete ===")


if __name__ == "__main__":
    main()
