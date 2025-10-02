# SPDX-FileCopyrightText: 2025 Fuse Technical Group
#
# SPDX-License-Identifier: BSD-3-Clause

"""Command-line interface for virtual-gpu-lut-box."""

from __future__ import annotations

import sys
import time

import click

from .gpu_texture_stream.factory import PlatformNotSupportedError
from .server import VirtualGPULUTBoxServer


@click.command()
@click.option(
    "--host",
    default=VirtualGPULUTBoxServer.DEFAULT_HOST,
    help="Server host address (0.0.0.0 = all interfaces)",
)
@click.option(
    "--port", default=VirtualGPULUTBoxServer.DEFAULT_PORT, help="Server port number"
)
@click.option(
    "--stream-name",
    default="OpenGradeIO-LUT",
    help="Base Spout/Syphon stream name",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose (debug) logging")
@click.option("--info-logging", is_flag=True, help="Enable info-level logging")
@click.option("--info", is_flag=True, help="Show system information and exit")
@click.version_option()
def main(
    host: str,
    port: int,
    stream_name: str,
    verbose: bool,
    info_logging: bool,
    info: bool,
) -> None:
    """Virtual GPU LUT Box - Network-to-GPU LUT streaming for professional color grading.

    By default, starts the OpenGradeIO server with minimal output.
    Use --info-logging for detailed operational info, --verbose for debug output.
    Use --info to show system information instead.
    """
    if info:
        show_system_info()
        return

    start_server_cli(host, port, stream_name, verbose, info_logging)


def show_system_info() -> None:
    """Show system and platform information."""
    try:
        platform_info = VirtualGPULUTBoxServer.get_platform_info()

        # Show basic platform info
        click.echo("System Information:")
        for key, value in platform_info.items():
            if key not in [
                "current_platform",
                "available_backends",
                "platform_supported",
                "supported_formats",
            ]:
                click.echo(f"  {key}: {value}")

        # Show streaming-specific info
        click.echo(f"\nCurrent platform: {platform_info['current_platform']}")
        click.echo(
            f"Available backends: {', '.join(platform_info['available_backends'])}"
        )
        click.echo(f"Platform supported: {platform_info['platform_supported']}")

        if platform_info["platform_supported"]:
            click.echo(
                f"Supported formats: {', '.join(platform_info['supported_formats'])}"
            )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def start_server_cli(
    host: str,
    port: int,
    stream_name: str,
    verbose: bool,
    info_logging: bool,
) -> None:
    """Start virtual LUT box server via CLI."""
    server = None

    try:
        # Create and start server
        server = VirtualGPULUTBoxServer(
            host=host,
            port=port,
            stream_name=stream_name,
            verbose=verbose,
            info_logging=info_logging,
        )
        server.start()

        # Handle server lifetime in CLI
        try:
            click.echo("🔄 Server running. Press Ctrl+C to stop.")
            while server.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            click.echo("🛑 Stopping server...")

    except PlatformNotSupportedError as e:
        click.echo(f"Platform error: {e}", err=True)
        click.echo("GPU texture streaming not supported on this platform")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        # Clean up resources
        if server:
            server.stop()
        click.echo("✅ Server stopped")


if __name__ == "__main__":
    main()
