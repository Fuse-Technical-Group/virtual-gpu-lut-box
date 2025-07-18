"""Command-line interface for virtual-gpu-lut-box."""

from __future__ import annotations

import sys

import click

from .gpu_texture_stream.factory import PlatformNotSupportedError, StreamingFactory
from .server import get_platform_info, start_server


@click.command()
@click.option("--host", default="127.0.0.1", help="Server host address")
@click.option("--port", default=8089, help="Server port number")
@click.option(
    "--stream-name",
    default="OpenGradeIO-LUT",
    help="Base Spout/Syphon stream name",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--info", is_flag=True, help="Show system information and exit")
@click.version_option()
def main(
    host: str,
    port: int,
    stream_name: str,
    verbose: bool,
    info: bool,
) -> None:
    """Virtual GPU LUT Box - Network-to-GPU LUT streaming for professional color grading.

    By default, starts the OpenGradeIO server. Use --info to show system information instead.
    """
    if info:
        show_system_info()
        return

    start_server_cli(host, port, stream_name, verbose)


def show_system_info() -> None:
    """Show system and platform information."""
    try:
        platform_info = get_platform_info()
        
        # Show basic platform info
        click.echo("System Information:")
        for key, value in platform_info.items():
            if key not in ["current_platform", "available_backends", "platform_supported", "supported_formats"]:
                click.echo(f"  {key}: {value}")

        # Show streaming-specific info
        click.echo(f"\nCurrent platform: {platform_info['current_platform']}")
        click.echo(f"Available backends: {', '.join(platform_info['available_backends'])}")
        click.echo(f"Platform supported: {platform_info['platform_supported']}")

        if platform_info['platform_supported']:
            click.echo(f"Supported formats: {', '.join(platform_info['supported_formats'])}")

        # Show streaming info
        click.echo("\nStreaming Information:")
        click.echo("  Protocol: OpenGradeIO BSON over TCP")
        click.echo("  Precision: 32-bit float only (no 8-bit conversion)")
        click.echo("  Formats: RGB and RGBA with HDR support")
        click.echo("  Channel naming: vglb-lut-{channel}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def start_server_cli(
    host: str,
    port: int,
    stream_name: str,
    verbose: bool,
) -> None:
    """Start OpenGradeIO virtual LUT box server via CLI."""
    try:
        start_server(
            host=host,
            port=port,
            stream_name=stream_name,
            verbose=verbose,
            blocking=True,
        )
    except PlatformNotSupportedError as e:
        click.echo(f"Platform error: {e}", err=True)
        click.echo("GPU texture streaming not supported on this platform")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
