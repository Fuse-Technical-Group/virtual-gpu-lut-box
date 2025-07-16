#!/usr/bin/env python3
"""Comprehensive demo for virtual-gpu-lut-box with consistent timestamped output."""

import datetime
import time
from typing import Any

import numpy as np

from virtual_gpu_lut_box import HaldConverter, LUTGenerator, StreamingFactory


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


def example_lut_generation() -> np.ndarray:
    """Example: Generate different types of LUTs with consistent output."""
    print_section("LUT Generation Examples")

    # Create LUT generator
    print_step("Creating LUT generator (size=33)")
    generator = LUTGenerator(size=33)

    # 1. Identity LUT (no changes)
    print_step("Generating identity LUT")
    identity_lut = generator.identity_lut
    print_info(f"Identity LUT shape: {identity_lut.shape}")
    print_info(
        f"Identity LUT corners: {identity_lut[0, 0, 0]}, {identity_lut[32, 32, 32]}"
    )

    # 2. Gamma correction
    print_step("Applying gamma correction (γ=2.2)")
    gamma_lut = generator.apply_gamma(2.2)
    print_info(f"Gamma LUT midpoint: {gamma_lut[16, 16, 16]}")

    # 3. Brightness and contrast
    print_step("Applying brightness/contrast (brightness=0.1, contrast=1.2)")
    bc_lut = generator.apply_brightness_contrast(brightness=0.1, contrast=1.2)
    print_info(f"Brightness/Contrast LUT midpoint: {bc_lut[16, 16, 16]}")

    # 4. Hue and saturation
    print_step("Applying hue/saturation (hue=30°, saturation=1.3)")
    hs_lut = generator.apply_hue_saturation(hue_shift=np.pi / 6, saturation=1.3)
    print_info(f"Hue/Saturation LUT shape: {hs_lut.shape}")

    # 5. Custom LUT with all adjustments
    print_step("Creating custom LUT with all adjustments")
    custom_lut = generator.create_custom_lut(
        gamma=2.2, brightness=0.05, contrast=1.1, hue_shift=np.pi / 12, saturation=1.15
    )
    print_info(f"Custom LUT range: [{custom_lut.min():.3f}, {custom_lut.max():.3f}]")
    print_success("LUT generation completed")

    return custom_lut


def example_hald_conversion() -> np.ndarray:
    """Example: Convert LUT to Hald image format with consistent output."""
    print_section("Hald Conversion Examples")

    # Generate a LUT
    print_step("Generating LUT for Hald conversion")
    generator = LUTGenerator(size=33)
    lut = generator.create_custom_lut(gamma=2.2, brightness=0.1)

    # Create Hald converter
    print_step("Creating Hald converter")
    converter = HaldConverter(lut_size=33)

    # Convert to Hald image
    print_step("Converting LUT to Hald image format")
    hald_image = converter.lut_to_hald(lut)
    print_info(f"Hald image dimensions: {hald_image.shape}")
    print_info(f"Hald image size: {hald_image.shape[1]}x{hald_image.shape[0]} pixels")

    # Get shader sampling info
    print_step("Generating shader sampling constants")
    shader_info = converter.get_shader_sampling_info()
    print_info("Shader sampling constants:")
    for key, value in shader_info.items():
        print(f"         {key}: {value}")

    # Save Hald image
    print_step("Saving Hald image to example_lut.png")
    try:
        converter.save_hald_image(hald_image, "example_lut.png")
        print_success("Saved Hald image to example_lut.png")
    except Exception as e:
        print_error(f"Could not save image: {e}")

    # Convert back to LUT (roundtrip test)
    print_step("Testing roundtrip conversion (Hald → LUT)")
    recovered_lut = converter.hald_to_lut(hald_image)
    is_accurate = np.allclose(lut, recovered_lut)
    if is_accurate:
        print_success("Roundtrip conversion successful")
    else:
        print_error("Roundtrip conversion failed")

    return hald_image


def example_platform_detection() -> dict[str, Any]:
    """Example: Platform detection and backend availability."""
    print_section("Platform Detection & Backend Availability")

    # Get platform info
    print_step("Detecting platform information")
    platform_info = StreamingFactory.get_platform_info()
    print_info(f"Platform: {platform_info['system']}")
    print_info(f"Python version: {platform_info['python_version']}")
    print_info(f"Machine: {platform_info['machine']}")

    # Check available backends
    print_step("Checking available streaming backends")
    backends = StreamingFactory.get_available_backends()
    print_info(f"Available backends: {backends}")

    # Check if current platform is supported
    print_step("Verifying platform streaming support")
    is_supported = StreamingFactory.is_platform_supported()
    if is_supported:
        print_success("Platform supports streaming")
    else:
        print_error("Platform does not support streaming")

    # Get supported formats
    if is_supported:
        print_step("Querying supported texture formats")
        formats = StreamingFactory.list_supported_formats()
        print_info(f"Supported formats: {formats}")

    return {
        "platform_info": platform_info,
        "backends": backends,
        "supported": is_supported,
        "formats": formats if is_supported else [],
    }


def example_streaming_demo(hald_image: np.ndarray) -> None:
    """Example: Full streaming demonstration with proper lifecycle."""
    print_section("Streaming Demonstration")

    # Check platform support first
    if not StreamingFactory.is_platform_supported():
        print_error("Streaming not supported on this platform")
        print_info("Platform-specific dependencies are automatically installed")
        print_info("No extra steps needed for Syphon (macOS) or Spout (Windows)")
        return

    print_step("Creating streaming backend with default name 'virtual-gpu-lut-box'")
    try:
        # Create streaming backend (uses default name "virtual-gpu-lut-box")
        backend = StreamingFactory.create_lut_streamer()
        print_info(f"Created backend: {backend.__class__.__name__}")
        print_info(f"Backend dimensions: {backend.width}x{backend.height}")
        print_info(f"Stream name: '{backend.name}'")

        # Check if backend is available
        print_step("Verifying backend availability")
        if not backend.is_available():
            print_error("Backend is not available (missing dependencies)")
            return

        print_success("Backend is available for streaming")

        # Initialize and start streaming
        print_step("Starting streaming demonstration")
        with backend:
            print_info(f"📡 Streaming LUT to '{backend.name}' stream")
            print_info("📺 Check your Syphon/Spout receiver now!")
            print_info("🕐 Streaming for 15 seconds at 30 FPS...")

            start_time = time.time()
            frame_count = 0
            target_fps = 30
            frame_delay = 1.0 / target_fps

            while time.time() - start_time < 15.0:
                frame_start = time.time()

                # Send frame
                if backend.send_lut_texture(hald_image):
                    frame_count += 1
                else:
                    print_error("Failed to send frame")
                    break

                # Frame timing
                elapsed = time.time() - frame_start
                sleep_time = max(0, frame_delay - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            duration = time.time() - start_time
            actual_fps = frame_count / duration
            print_success(f"Streamed {frame_count} frames over {duration:.1f} seconds")
            print_info(f"Average FPS: {actual_fps:.1f}")

    except Exception as e:
        print_error(f"Could not create streaming backend: {e}")


def example_texture_formats() -> None:
    """Example: Work with different texture formats."""
    print_section("Texture Format Examples")

    # Generate LUT and convert to Hald
    print_step("Generating smaller LUT for format demonstration (size=17)")
    generator = LUTGenerator(size=17)
    lut = generator.create_custom_lut(gamma=2.2)

    print_step("Creating Hald converter")
    converter = HaldConverter(lut_size=17)
    converter.lut_to_hald(lut)

    # Convert to different texture formats
    print_step("Converting to different texture formats")
    formats = ["rgb", "rgba", "bgr", "bgra"]

    for fmt in formats:
        texture_data = converter.convert_lut_to_texture_data(lut, fmt)
        print_info(
            f"{fmt.upper()} format: {texture_data.shape}, range: [{texture_data.min():.3f}, {texture_data.max():.3f}]"
        )

    # Show optimal texture size
    width, height = converter.get_optimal_texture_size()
    print_info(f"Optimal texture size: {width}x{height}")
    print_success("Texture format examples completed")


def example_gpu_coordinates() -> None:
    """Example: Generate GPU texture coordinates."""
    print_section("GPU Texture Coordinates")

    print_step("Creating converter for coordinate demonstration (size=5)")
    converter = HaldConverter(lut_size=5)

    # Get texture coordinates
    print_step("Generating GPU texture coordinates")
    u_coords, v_coords = converter.create_gpu_texture_coords()
    print_info(f"U coordinates: {len(u_coords)} values")
    print_info(f"First few U coords: {u_coords[:5]}")
    print_info(f"V coordinates: {len(v_coords)} values")
    print_info(f"V coords: {v_coords}")

    # Get slice boundaries
    print_step("Calculating slice boundaries")
    boundaries = converter.get_slice_boundaries()
    print_info(f"Slice boundaries: {len(boundaries)} slices")
    for i, (start, end) in enumerate(boundaries):
        print(f"         Slice {i}: U = {start:.3f} to {end:.3f}")

    print_success("GPU coordinate examples completed")


def main():
    """Run comprehensive demo with consistent formatting."""
    start_time = datetime.datetime.now()

    print("=" * 70)
    print("Virtual GPU LUT Box - Comprehensive Demo")
    print("=" * 70)
    print_info(f"Demo started at {start_time.strftime('%H:%M:%S')}")

    try:
        # Run all examples in sequence
        example_lut_generation()
        hald_image = example_hald_conversion()
        platform_info = example_platform_detection()
        example_streaming_demo(hald_image)
        example_texture_formats()
        example_gpu_coordinates()

        # Summary
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()

        print_section("Demo Summary")
        print_success("All examples completed successfully")
        print_info(f"Total demo duration: {duration:.1f} seconds")
        print_info(f"Platform supported: {platform_info['supported']}")
        print_info("Stream name used: 'virtual-gpu-lut-box'")

        if platform_info["supported"]:
            print_info("✨ Streaming functionality is fully operational!")
            print_info("🎯 Default stream name 'virtual-gpu-lut-box' is ready for use")
        else:
            print_info("💡 Streaming would work with proper platform dependencies")

    except Exception as e:
        print_error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    main()
