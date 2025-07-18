"""Command-line interface for virtual-gpu-lut-box."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import click
import numpy as np

from .gpu_texture_stream.factory import PlatformNotSupportedError, StreamingFactory
from .lut.generator import LUTGenerator
from .lut.hald_converter import HaldConverter
from .network import OpenGradeIOLUTStreamer, OpenGradeIOServer


@click.group()
@click.version_option()
def main() -> None:
    """Virtual GPU LUT Box - Cross-platform LUT streaming for GPU shaders."""
    pass


@main.command()
@click.option("--size", default=33, help="LUT size (default: 33 for 33x33x33)")
@click.option(
    "--output", "-o", type=click.Path(), help="Output file path for Hald image"
)
@click.option("--gamma", default=1.0, help="Gamma correction value")
@click.option("--brightness", default=0.0, help="Brightness adjustment (-1 to 1)")
@click.option("--contrast", default=1.0, help="Contrast multiplier")
@click.option("--hue-shift", default=0.0, help="Hue shift in degrees")
@click.option("--saturation", default=1.0, help="Saturation multiplier")
def generate(
    size: int,
    output: str | None,
    gamma: float,
    brightness: float,
    contrast: float,
    hue_shift: float,
    saturation: float,
) -> None:
    """Generate a 3D LUT and convert to Hald image format."""
    try:
        # Create LUT generator
        generator = LUTGenerator(size)

        # Convert hue shift from degrees to radians
        hue_shift_rad = np.radians(hue_shift)

        # Generate custom LUT
        click.echo(f"Generating {size}x{size}x{size} LUT...")
        lut = generator.create_custom_lut(
            gamma=gamma,
            brightness=brightness,
            contrast=contrast,
            hue_shift=hue_shift_rad,
            saturation=saturation,
        )

        # Create Hald converter
        converter = HaldConverter(size)

        # Convert to Hald image
        click.echo("Converting to Hald image format...")
        hald_image = converter.lut_to_hald(lut)

        # Save if output specified
        if output:
            output_path = Path(output)
            click.echo(f"Saving Hald image to {output_path}")
            converter.save_hald_image(hald_image, str(output_path))

        # Show info
        click.echo(f"Generated LUT: {lut.shape}")
        click.echo(f"Hald image: {hald_image.shape}")
        click.echo(f"Gamma: {gamma}")
        click.echo(f"Brightness: {brightness}")
        click.echo(f"Contrast: {contrast}")
        click.echo(f"Hue shift: {hue_shift}°")
        click.echo(f"Saturation: {saturation}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--name",
    default="virtual-gpu-lut-box",
    help="Stream name (default: virtual-gpu-lut-box)",
)
@click.option("--size", default=33, help="LUT size (default: 33)")
@click.option("--fps", default=30, help="Target frame rate")
@click.option("--once", is_flag=True, help="Send only one frame and exit")
@click.option(
    "--duration", type=int, help="Stream for specified seconds (default: infinite)"
)
@click.option("--platform", help="Override platform detection")
def stream(
    input_file: str,
    name: str,
    size: int,
    fps: int,
    once: bool,
    duration: int | None,
    platform: str | None,
) -> None:
    """Stream a Hald image via Spout/Syphon. Streams continuously by default."""
    try:
        # Load Hald image
        converter = HaldConverter(size)
        click.echo(f"Loading Hald image from {input_file}")
        hald_image = converter.load_hald_image(input_file)

        # Create streaming backend
        click.echo(f"Creating streaming backend for {name}")
        backend = StreamingFactory.create_lut_streamer(
            name, size, platform_name=platform
        )

        # Initialize backend
        click.echo(f"Initializing {backend.__class__.__name__}")
        if not backend.initialize():
            click.echo("Failed to initialize streaming backend", err=True)
            sys.exit(1)

        # Calculate frame delay
        frame_delay = 1.0 / fps
        frame_count = 0

        # Stream loop
        try:
            with backend:
                if once:
                    click.echo("Sending single frame...")
                elif duration:
                    click.echo(
                        f"Streaming at {fps} FPS for {duration} seconds. Press Ctrl+C to stop."
                    )
                else:
                    click.echo(f"Streaming at {fps} FPS. Press Ctrl+C to stop.")
                start_streaming_time = time.time()

                while True:
                    frame_start_time = time.time()

                    # Send frame
                    if not backend.send_lut_texture(hald_image):
                        click.echo("Failed to send frame", err=True)
                        break

                    frame_count += 1

                    # Exit if only sending one frame
                    if once:
                        break

                    # Exit if duration exceeded
                    if duration and (time.time() - start_streaming_time) >= duration:
                        break

                    # Calculate timing
                    elapsed = time.time() - frame_start_time
                    sleep_time = max(0, frame_delay - elapsed)

                    if sleep_time > 0:
                        time.sleep(sleep_time)

                    # Show progress
                    if frame_count % (fps * 5) == 0:  # Every 5 seconds
                        click.echo(f"Streamed {frame_count} frames")

        except KeyboardInterrupt:
            click.echo("\\nStopping stream...")

        click.echo(f"Streamed {frame_count} frames total")

    except PlatformNotSupportedError as e:
        click.echo(f"Platform error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--platform", help="Override platform detection")
def info(platform: str | None) -> None:
    """Show system and platform information."""
    try:
        # Show platform info
        platform_info = StreamingFactory.get_platform_info()
        click.echo("System Information:")
        for key, value in platform_info.items():
            click.echo(f"  {key}: {value}")

        # Show current platform
        current_platform = platform or StreamingFactory.get_current_platform()
        click.echo(f"\\nCurrent platform: {current_platform}")

        # Show supported platforms
        available_backends = StreamingFactory.get_available_backends()
        click.echo(f"Available backends: {', '.join(available_backends)}")

        # Show platform support
        is_supported = StreamingFactory.is_platform_supported(platform)
        click.echo(f"Platform supported: {is_supported}")

        # Show supported formats
        if is_supported:
            formats = StreamingFactory.list_supported_formats(platform)
            click.echo(f"Supported formats: {', '.join(formats)}")

        # Show LUT info
        click.echo("\\nLUT Information:")
        click.echo("  Default size: 33x33x33")
        click.echo("  Hald dimensions: 1089x33")
        click.echo("  Total LUT entries: 35,937")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--size", default=33, help="LUT size (default: 33)")
def validate(input_file: str, size: int) -> None:
    """Validate a Hald image file."""
    try:
        # Load and validate Hald image
        converter = HaldConverter(size)
        click.echo(f"Loading Hald image from {input_file}")
        hald_image = converter.load_hald_image(input_file)

        # Validate
        is_valid = converter.validate_hald_image(hald_image)

        if is_valid:
            click.echo("✓ Hald image is valid")
            click.echo(f"  Dimensions: {hald_image.shape}")
            click.echo(f"  Data type: {hald_image.dtype}")
            click.echo(
                f"  Value range: [{hald_image.min():.3f}, {hald_image.max():.3f}]"
            )
        else:
            click.echo("✗ Hald image is invalid", err=True)
            sys.exit(1)

        # Show additional info
        shader_info = converter.get_shader_sampling_info()
        click.echo("\\nShader sampling info:")
        for key, value in shader_info.items():
            click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--size", default=33, help="LUT size (default: 33)")
@click.option(
    "--output", "-o", type=click.Path(), required=True, help="Output file path"
)
def identity(size: int, output: str) -> None:
    """Generate identity Hald image for testing."""
    try:
        # Create identity Hald image
        converter = HaldConverter(size)
        click.echo(f"Generating identity Hald image ({size}x{size}x{size})")
        hald_image = converter.create_identity_hald()

        # Save
        output_path = Path(output)
        click.echo(f"Saving to {output_path}")
        converter.save_hald_image(hald_image, str(output_path))

        click.echo(f"Identity Hald image saved: {hald_image.shape}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--name",
    default="virtual-gpu-lut-box",
    help="Stream name (default: virtual-gpu-lut-box)",
)
@click.option("--size", default=33, help="LUT size (default: 33)")
@click.option("--gamma", default=1.0, help="Gamma correction value")
@click.option("--brightness", default=0.0, help="Brightness adjustment")
@click.option("--contrast", default=1.0, help="Contrast multiplier")
@click.option("--hue-shift", default=0.0, help="Hue shift in degrees")
@click.option("--saturation", default=1.0, help="Saturation multiplier")
@click.option("--fps", default=30, help="Target frame rate")
@click.option("--interactive", is_flag=True, help="Interactive mode (not implemented)")
def live(
    input_file: str,
    name: str,
    size: int,
    gamma: float,
    brightness: float,
    contrast: float,
    hue_shift: float,
    saturation: float,
    fps: int,
    interactive: bool,
) -> None:
    """Live LUT generation and streaming."""
    if interactive:
        click.echo("Interactive mode is not yet implemented")
        return

    try:
        # Load base Hald image
        converter = HaldConverter(size)
        click.echo(f"Loading base Hald image from {input_file}")
        converter.load_hald_image(input_file)

        # Create streaming backend
        click.echo(f"Creating streaming backend for {name}")
        backend = StreamingFactory.create_lut_streamer(name, size)

        # Initialize backend
        if not backend.initialize():
            click.echo("Failed to initialize streaming backend", err=True)
            sys.exit(1)

        # Create generator for live adjustments
        generator = LUTGenerator(size)

        # Calculate frame delay
        frame_delay = 1.0 / fps
        frame_count = 0

        # Stream loop
        try:
            with backend:
                click.echo(f"Live streaming at {fps} FPS. Press Ctrl+C to stop.")
                while True:
                    start_time = time.time()

                    # Generate LUT with current parameters
                    hue_shift_rad = np.radians(hue_shift)
                    lut = generator.create_custom_lut(
                        gamma=gamma,
                        brightness=brightness,
                        contrast=contrast,
                        hue_shift=hue_shift_rad,
                        saturation=saturation,
                    )

                    # Convert to Hald image
                    hald_image = converter.lut_to_hald(lut)

                    # Send frame
                    if not backend.send_lut_texture(hald_image):
                        click.echo("Failed to send frame", err=True)
                        break

                    frame_count += 1

                    # Calculate timing
                    elapsed = time.time() - start_time
                    sleep_time = max(0, frame_delay - elapsed)

                    if sleep_time > 0:
                        time.sleep(sleep_time)

                    # Show progress
                    if frame_count % (fps * 5) == 0:  # Every 5 seconds
                        click.echo(f"Streamed {frame_count} frames")

        except KeyboardInterrupt:
            click.echo("\\nStopping live stream...")

        click.echo(f"Streamed {frame_count} frames total")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--host", default="127.0.0.1", help="Server host address")
@click.option("--port", default=8089, help="Server port number")
@click.option(
    "--stream-name",
    default="OpenGradeIO-LUT",
    help="Spout/Syphon stream name",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def listen(
    host: str,
    port: int,
    stream_name: str,
    verbose: bool,
) -> None:
    """Start OpenGradeIO virtual LUT box server."""
    import logging

    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        click.echo(f"Starting OpenGradeIO virtual LUT box server on {host}:{port}")
        click.echo(f"Stream name: {stream_name}")

        # Create LUT streamer (will initialize lazily when first LUT is received)
        streamer = OpenGradeIOLUTStreamer(stream_name=stream_name)

        # Create LUT callback wrapper
        def lut_callback(
            lut_data: np.ndarray[Any, Any], channel_name: str | None = None
        ) -> None:
            try:
                streamer.process_lut(lut_data, channel_name)
                # Success - no need to log unless verbose
                if verbose:
                    channel_info = (
                        f" for channel '{channel_name}'" if channel_name else ""
                    )
                    click.echo(
                        f"Successfully processed {lut_data.shape[0]}³ LUT{channel_info}"
                    )
            except ValueError as e:
                click.echo(f"Invalid LUT data: {e}", err=True)
            except RuntimeError as e:
                click.echo(f"Streaming error: {e}", err=True)
            except Exception as e:
                click.echo(f"Unexpected error processing LUT: {e}", err=True)

        # Create and configure server
        server = OpenGradeIOServer(
            host=host,
            port=port,
            lut_callback=lut_callback,
        )

        # Start server
        server.start()

        try:
            click.echo("OpenGradeIO server running. Press Ctrl+C to stop.")
            while server.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            click.echo("\nStopping server...")
        finally:
            server.stop()
            streamer.stop_streaming()

        click.echo("Server stopped")

    except PlatformNotSupportedError as e:
        click.echo(f"Platform error: {e}", err=True)
        click.echo("Streaming not supported on this platform")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
