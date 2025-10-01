#!/usr/bin/env python3
"""Comprehensive demo for virtual-gpu-lut-box with consistent timestamped output."""

import datetime
import time

import numpy as np

from virtual_gpu_lut_box.lut.hald_converter import HaldConverter
from virtual_gpu_lut_box.gpu_texture_stream.factory import StreamingFactory


def format_timestamp() -> str:
    """Get current timestamp in consistent format."""
    return datetime.datetime.now().strftime("%H:%M:%S")


def print_section(title: str) -> None:
    """Print section header with consistent formatting."""
    timestamp = format_timestamp()
    print(f"\n[{timestamp}] === {title} ===")


def print_step(message: str) -> None:
    """Print step message with timestamp."""
    timestamp = format_timestamp()
    print(f"[{timestamp}] {message}")


def print_success(message: str) -> None:
    """Print success message with timestamp."""
    timestamp = format_timestamp()
    print(f"[{timestamp}] ✅ {message}")


def print_info(message: str) -> None:
    """Print info message with timestamp."""
    timestamp = format_timestamp()
    print(f"[{timestamp}] 📊 {message}")


def print_error(message: str) -> None:
    """Print error message with timestamp."""
    timestamp = format_timestamp()
    print(f"[{timestamp}] ❌ {message}")


def create_identity_lut(lut_size: int) -> np.ndarray:
    """Create an identity LUT of given size."""
    print_step(f"Creating {lut_size}x{lut_size}x{lut_size} identity LUT")

    lut = np.zeros((lut_size, lut_size, lut_size, 3), dtype=np.float32)
    for r in range(lut_size):
        for g in range(lut_size):
            for b in range(lut_size):
                lut[r, g, b, 0] = r / (lut_size - 1)  # R
                lut[r, g, b, 1] = g / (lut_size - 1)  # G
                lut[r, g, b, 2] = b / (lut_size - 1)  # B

    print_success(f"Identity LUT created with shape {lut.shape}")
    return lut


def apply_gamma_correction(lut: np.ndarray, gamma: float) -> np.ndarray:
    """Apply gamma correction to LUT."""
    print_step(f"Applying gamma correction (γ = {gamma})")
    corrected_lut = np.power(lut, 1.0 / gamma)
    print_success(
        f"Gamma correction applied, range: [{corrected_lut.min():.3f}, {corrected_lut.max():.3f}]"
    )
    return corrected_lut


def example_lut_generation() -> np.ndarray:
    """Example: Generate different types of LUTs with consistent output."""
    print_section("LUT Generation Examples")

    # Create identity LUT
    identity_lut = create_identity_lut(33)
    print_info(
        f"Identity LUT corners: {identity_lut[0, 0, 0]}, {identity_lut[32, 32, 32]}"
    )

    # Apply gamma correction
    gamma_lut = apply_gamma_correction(identity_lut, 2.2)
    print_info(f"Gamma LUT midpoint: {gamma_lut[16, 16, 16]}")

    # Create a LUT with brightness adjustment
    print_step("Applying brightness adjustment (+0.1)")
    brightness_lut = np.clip(gamma_lut + 0.1, 0.0, 1.0)
    print_success(
        f"Brightness adjustment applied, range: [{brightness_lut.min():.3f}, {brightness_lut.max():.3f}]"
    )

    return brightness_lut


def example_hald_conversion() -> np.ndarray:
    """Example: Convert LUT to Hald image format with consistent output."""
    print_section("Hald Conversion Examples")

    # Generate a LUT
    lut = example_lut_generation()

    # Create Hald converter
    print_step("Creating Hald converter")
    converter = HaldConverter(lut_size=33)
    print_success("Hald converter created")

    # Convert to Hald image
    print_step("Converting LUT to Hald image format")
    hald_image = converter.lut_to_hald(lut)
    print_success(f"Hald image created with dimensions: {hald_image.shape}")
    print_info(f"Hald image size: {hald_image.shape[1]}x{hald_image.shape[0]} pixels")

    return hald_image


def example_streaming_setup() -> None:
    """Example: Set up streaming backend and stream LUT with consistent output."""
    print_section("Streaming Setup Examples")

    # Check platform support
    print_step("Checking platform support")
    platform_info = StreamingFactory.get_platform_info()
    print_info(f"Platform: {platform_info['system']}")
    print_info(f"Python version: {platform_info['python_version']}")

    # Check available backends
    backends = StreamingFactory.get_available_backends()
    print_info(f"Available backends: {backends}")

    # Check if current platform is supported
    is_supported = StreamingFactory.is_platform_supported()
    print_info(f"Platform supported: {is_supported}")

    if is_supported:
        # Get supported formats
        formats = StreamingFactory.list_supported_formats()
        print_info(f"Supported formats: {formats}")

        try:
            # Create streaming backend
            print_step("Creating streaming backend")
            backend = StreamingFactory.create_lut_streamer()
            print_success(f"Created backend: {backend.__class__.__name__}")
            print_info(f"Backend dimensions: {backend.width}x{backend.height}")
            print_info(f"Stream name: {backend.name}")

            # Check if backend is available
            if backend.is_available():
                print_success("Backend is available for streaming")

                # Generate and stream a LUT
                print_step("Preparing LUT for streaming")
                hald_image = example_hald_conversion()

                # Stream the LUT
                print_step("Initializing streaming backend")
                with backend:
                    print_success(f"📡 Streaming LUT to '{backend.name}' stream")
                    print_info("   Check your Syphon/Spout receiver now!")
                    print_info("   Streaming for 15 seconds at 30 FPS...")

                    start_time = time.time()
                    frame_count = 0

                    while time.time() - start_time < 15.0:
                        backend.send_lut_texture(hald_image)
                        frame_count += 1
                        time.sleep(1 / 30)  # 30 FPS

                        # Progress indicator every 5 seconds
                        if frame_count % 150 == 0:  # Every 5 seconds at 30 FPS
                            elapsed = time.time() - start_time
                            print_info(
                                f"   Streaming... {elapsed:.1f}s elapsed, {frame_count} frames"
                            )

                    print_success(f"Streamed {frame_count} frames over 15 seconds")

            else:
                print_error("Backend is not available (missing dependencies)")

        except Exception as e:
            print_error(f"Could not create backend: {e}")
    else:
        print_info("Streaming not supported on this platform")
        print_info(
            "💡 Platform-specific streaming dependencies are automatically installed!"
        )
        print_info("   - No extra steps needed - Syphon/Spout support is built-in")
        print_info(
            "🎬 Demo would stream for 15 seconds at 30 FPS if dependencies were available"
        )


def example_opengradeio_workflow() -> None:
    """Example: OpenGradeIO workflow demonstration."""
    print_section("OpenGradeIO Integration Workflow")

    print_step("Setting up OpenGradeIO integration")
    print_info("This demo shows the complete OpenGradeIO to GPU workflow:")
    print_info("1. OpenGradeIO sends LUT data via BSON over TCP")
    print_info("2. Virtual GPU LUT Box receives and processes the data")
    print_info("3. LUT is converted to Hald image format")
    print_info("4. Hald image is streamed to GPU via Syphon/Spout")
    print_info("5. GPU shaders can sample the LUT for color grading")

    print_step("To use OpenGradeIO integration in practice:")
    print_info("• Start server: virtual-gpu-lut-box --verbose")
    print_info("• Configure OpenGradeIO to connect to 127.0.0.1:8089")
    print_info("• LUTs are automatically streamed with names: vglb-lut-{channel}")
    print_info("• Multiple channels/instances are supported simultaneously")
    print_info("• 32-bit float precision is preserved throughout the pipeline")

    print_success("OpenGradeIO integration workflow explained")


def example_performance_testing() -> None:
    """Example: Performance testing and optimization."""
    print_section("Performance Testing")

    print_step("Testing different LUT sizes")

    lut_sizes = [16, 33, 64]
    for lut_size in lut_sizes:
        print_step(f"Testing {lut_size}x{lut_size}x{lut_size} LUT")

        # Time LUT creation
        start_time = time.time()
        lut = create_identity_lut(lut_size)
        lut_time = time.time() - start_time

        # Time Hald conversion
        start_time = time.time()
        converter = HaldConverter(lut_size=lut_size)
        hald_image = converter.lut_to_hald(lut)
        hald_time = time.time() - start_time

        # Calculate memory usage
        lut_memory = lut.nbytes / (1024 * 1024)  # MB
        hald_memory = hald_image.nbytes / (1024 * 1024)  # MB

        print_info(f"  LUT creation: {lut_time:.4f}s")
        print_info(f"  Hald conversion: {hald_time:.4f}s")
        print_info(f"  LUT memory: {lut_memory:.2f} MB")
        print_info(f"  Hald memory: {hald_memory:.2f} MB")
        print_info(f"  Hald dimensions: {hald_image.shape[1]}x{hald_image.shape[0]}")

    print_success("Performance testing completed")


def main() -> None:
    """Run comprehensive demo with consistent timestamped output."""
    print(f"[{format_timestamp()}] Virtual GPU LUT Box - Comprehensive Demo")
    print("=" * 70)

    # Run all examples
    example_hald_conversion()
    example_streaming_setup()
    example_opengradeio_workflow()
    example_performance_testing()

    print_section("Demo Complete")
    print_success("All examples completed successfully!")
    print_info("Thank you for trying Virtual GPU LUT Box!")


if __name__ == "__main__":
    main()
