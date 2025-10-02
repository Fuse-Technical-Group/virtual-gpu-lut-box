# SPDX-FileCopyrightText: 2025 Fuse Technical Group
#
# SPDX-License-Identifier: BSD-3-Clause

"""High-level server interface for virtual-gpu-lut-box."""

from __future__ import annotations

import logging
import multiprocessing
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event

    import numpy as np

    LUTCallbackType = Callable[[np.ndarray[Any, Any], str | None], None]
else:
    LUTCallbackType = Callable[..., None]

from .network import OpenGradeIOLUTStreamer, OpenGradeIOServer

logger = logging.getLogger(__name__)


def _server_process_worker(
    host: str,
    port: int,
    stream_name: str,
    verbose: bool,
    info_logging: bool,
    lut_callback: LUTCallbackType | None,
    shutdown_event: Event,
) -> None:
    """Worker function that runs the server in a separate process."""
    # Configure logging in the process
    if verbose:
        log_level = logging.DEBUG
    elif info_logging:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger(__name__)

    # Create LUT streamer (unless custom callback provided)
    streamer = None
    if lut_callback is None:
        quiet_mode = not (verbose or info_logging)
        streamer = OpenGradeIOLUTStreamer(
            stream_name=stream_name, quiet_mode=quiet_mode
        )

        def default_lut_callback(
            lut_data: Any, channel_name: str | None = None
        ) -> None:
            try:
                if streamer:
                    streamer.process_lut(lut_data, channel_name)
            except ValueError as e:
                logger.error(f"Invalid LUT data: {e}")
                raise
            except RuntimeError as e:
                logger.error(f"Streaming error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error processing LUT: {e}")
                raise

        lut_callback = default_lut_callback

    # Create network server
    network_server = OpenGradeIOServer(
        host=host,
        port=port,
        lut_callback=lut_callback,
    )

    try:
        # Start the server
        network_server.start()
        logger.info("Server process started successfully")

        # Wait for shutdown signal
        shutdown_event.wait()

    except KeyboardInterrupt:
        # Expected when main process sends SIGINT - suppress traceback
        logger.debug("Server process interrupted by signal")
    except Exception as e:
        logger.error(f"Server process error: {e}")
    finally:
        # Clean up
        network_server.stop()
        if streamer:
            streamer.stop_streaming()
        logger.info("Server process stopped")


class VirtualGPULUTBoxServer:
    """High-level server that manages both network and GPU streaming components in a separate process."""

    DEFAULT_HOST = OpenGradeIOServer.DEFAULT_HOST
    DEFAULT_PORT = OpenGradeIOServer.DEFAULT_PORT

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        stream_name: str = "OpenGradeIO-LUT",
        verbose: bool = False,
        info_logging: bool = False,
        lut_callback: LUTCallbackType | None = None,
    ) -> None:
        """Initialize the virtual GPU LUT box server.

        Args:
            host: Server host address
            port: Server port number
            stream_name: Base Spout/Syphon stream name
            verbose: Enable verbose (debug) logging
            info_logging: Enable info-level logging
            lut_callback: Optional custom callback for LUT processing (overrides GPU streaming)
        """
        self.host = host
        self.port = port
        self.stream_name = stream_name
        self.verbose = verbose
        self.info_logging = info_logging
        self.lut_callback = lut_callback

        # Process management
        self._process: multiprocessing.Process | None = None
        self._shutdown_event: Event = multiprocessing.Event()

        # Configure logging in main process
        if verbose:
            log_level = logging.DEBUG
        elif info_logging:
            log_level = logging.INFO
        else:
            log_level = logging.WARNING  # Quiet mode - only warnings and errors

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Essential startup info - always show in quiet mode
        print(f"🚀 Starting OpenGradeIO virtual LUT box server on {host}:{port}")

        # Additional info for info/verbose modes
        if info_logging or verbose:
            logger.info(f"Base stream name: {stream_name}")
            logger.info("Channel streams will be named: vglb-lut-{channel}")

        # Create and start the server process
        self._process = multiprocessing.Process(
            target=_server_process_worker,
            args=(
                host,
                port,
                stream_name,
                verbose,
                info_logging,
                lut_callback,
                self._shutdown_event,
            ),
            daemon=True,
        )

        self._process.start()
        logger.info("Server process created and started")

    def start(self) -> None:
        """Start the server process (already started in __init__)."""
        # Process is already started in __init__, just verify it's running
        if self._process and self._process.is_alive():
            print("✅ OpenGradeIO server started successfully")
        else:
            raise RuntimeError("Failed to start server process")

    def stop(self) -> None:
        """Stop the server process and clean up all resources."""
        if self._process and self._process.is_alive():
            # Signal the process to shut down
            self._shutdown_event.set()

            # Wait for the process to finish
            self._process.join(timeout=5.0)

            # Force terminate if it didn't shut down gracefully
            if self._process.is_alive():
                logger.warning(
                    "Server process did not shut down gracefully, terminating"
                )
                self._process.terminate()
                self._process.join(timeout=2.0)

            logger.info("Server process stopped")

    @property
    def is_running(self) -> bool:
        """Check if server process is running."""
        return self._process is not None and self._process.is_alive()

    @staticmethod
    def get_platform_info() -> dict[str, Any]:
        """Get system and platform information for GPU streaming.

        Returns:
            Dictionary with platform information
        """
        from .gpu_texture_stream.factory import StreamingFactory

        # Get basic platform info (dict[str, str])
        base_platform_info = StreamingFactory.get_platform_info()

        # Create a new dict with proper typing that can hold Any values
        platform_info: dict[str, Any] = dict(base_platform_info)

        # Add streaming-specific information
        platform_info.update(
            {
                "current_platform": StreamingFactory.get_current_platform(),
                "available_backends": StreamingFactory.get_available_backends(),
                "platform_supported": StreamingFactory.is_platform_supported(),
            }
        )

        if StreamingFactory.is_platform_supported():
            platform_info["supported_formats"] = (
                StreamingFactory.list_supported_formats()
            )

        return platform_info
