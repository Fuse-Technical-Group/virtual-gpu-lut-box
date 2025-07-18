"""Command-line interface for virtual-gpu-lut-box."""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    import numpy as np
else:
    pass

from .gpu_texture_stream.factory import PlatformNotSupportedError, StreamingFactory
from .network import OpenGradeIOLUTStreamer, OpenGradeIOServer


@click.group()
@click.version_option()
def main() -> None:
    """Virtual GPU LUT Box - Network-to-GPU LUT streaming for professional color grading."""
    pass


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
        click.echo(f"\nCurrent platform: {current_platform}")

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

        # Show streaming info
        click.echo("\nStreaming Information:")
        click.echo("  Protocol: OpenGradeIO BSON over TCP")
        click.echo("  Precision: 32-bit float only (no 8-bit conversion)")
        click.echo("  Formats: RGB and RGBA with HDR support")
        click.echo("  Channel naming: vglb-lut-{channel}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--host", default="127.0.0.1", help="Server host address")
@click.option("--port", default=8089, help="Server port number")
@click.option(
    "--stream-name",
    default="OpenGradeIO-LUT",
    help="Base Spout/Syphon stream name",
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
        click.echo(f"Base stream name: {stream_name}")
        click.echo("Channel streams will be named: vglb-lut-{channel}")

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
        click.echo("GPU texture streaming not supported on this platform")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
