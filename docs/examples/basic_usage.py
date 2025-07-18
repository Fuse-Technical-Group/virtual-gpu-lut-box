#!/usr/bin/env python3
"""Basic usage examples for virtual-gpu-lut-box."""

import numpy as np

from virtual_gpu_lut_box import HaldConverter, StreamingFactory


def example_hald_conversion():
    """Example: Convert LUT to Hald image format."""
    print("=== Hald Conversion Examples ===")

    # Create a simple test LUT (identity LUT with some modifications)
    lut_size = 33
    
    # Create identity LUT
    identity_lut = np.zeros((lut_size, lut_size, lut_size, 3), dtype=np.float32)
    for r in range(lut_size):
        for g in range(lut_size):
            for b in range(lut_size):
                identity_lut[r, g, b, 0] = r / (lut_size - 1)  # R
                identity_lut[r, g, b, 1] = g / (lut_size - 1)  # G
                identity_lut[r, g, b, 2] = b / (lut_size - 1)  # B
    
    # Apply simple gamma correction
    gamma = 2.2
    lut = np.power(identity_lut, 1.0 / gamma)
    
    print(f"Generated LUT shape: {lut.shape}")
    print(f"LUT range: [{lut.min():.3f}, {lut.max():.3f}]")

    # Create Hald converter
    converter = HaldConverter(lut_size=lut_size)

    # Convert to Hald image
    hald_image = converter.lut_to_hald(lut)
    print(f"Hald image dimensions: {hald_image.shape}")
    print(f"Hald image size: {hald_image.shape[1]}x{hald_image.shape[0]} pixels")

    return hald_image


def example_streaming_setup():
    """Example: Set up streaming backend and stream LUT."""
    print("\n=== Streaming Setup Examples ===")

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
                print("\n🎥 Starting LUT streaming demo...")
                converter = HaldConverter(lut_size=33)

                # Create a simple gamma-corrected LUT
                lut_size = 33
                lut = np.zeros((lut_size, lut_size, lut_size, 3), dtype=np.float32)
                for r in range(lut_size):
                    for g in range(lut_size):
                        for b in range(lut_size):
                            lut[r, g, b, 0] = r / (lut_size - 1)  # R
                            lut[r, g, b, 1] = g / (lut_size - 1)  # G
                            lut[r, g, b, 2] = b / (lut_size - 1)  # B
                
                # Apply gamma correction
                lut = np.power(lut, 1.0 / 2.2)

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
            "\n💡 Platform-specific streaming dependencies are automatically installed!"
        )
        print("   - No extra steps needed - Syphon/Spout support is built-in")
        print(
            "\n🎬 Demo would stream for 15 seconds at 30 FPS if dependencies were available"
        )


def example_opengradeio_integration():
    """Example: OpenGradeIO network integration."""
    print("\n=== OpenGradeIO Integration Example ===")
    
    # This example shows how to use the OpenGradeIO network server
    # In practice, you would run this as a CLI command:
    # virtual-gpu-lut-box --host 127.0.0.1 --port 8089 --verbose
    
    print("To use OpenGradeIO integration:")
    print("1. Start the server: virtual-gpu-lut-box")
    print("2. Configure OpenGradeIO to connect to 127.0.0.1:8089")
    print("3. LUTs will be automatically streamed to GPU via Syphon/Spout")
    print("4. Stream names will be: vglb-lut-{channel}")


def main():
    """Run all examples."""
    print("Virtual GPU LUT Box - Basic Usage Examples")
    print("=" * 50)

    # Run examples
    example_hald_conversion()
    example_streaming_setup()
    example_opengradeio_integration()

    print("\n=== All Examples Complete ===")


if __name__ == "__main__":
    main()