"""Integration layer for streaming LUTs from OpenGradeIO to GPU."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np
else:
    pass

from virtual_gpu_lut_box.gpu_texture_stream.factory import (
    PlatformNotSupportedError,
    StreamingFactory,
)
from virtual_gpu_lut_box.lut.hald_converter import HaldConverter

logger = logging.getLogger(__name__)


class OpenGradeIOLUTStreamer:
    """Integrate OpenGradeIO LUT data with GPU streaming."""

    def __init__(
        self,
        stream_name: str = "OpenGradeIO-LUT",
    ) -> None:
        """Initialize LUT streamer.

        Args:
            stream_name: Name for the Spout/Syphon stream
        """
        self.stream_name = stream_name
        self._converter: HaldConverter | None = None
        self._streamer: object | None = None
        self._current_lut_size: int | None = None
        self._is_streaming = False

    def _ensure_streaming_backend(
        self, lut_size: int, stream_name: str | None = None
    ) -> bool:
        """Ensure streaming backend exists and matches LUT size.

        Args:
            lut_size: Required LUT size
            stream_name: Optional override for stream name (e.g., channel/instance)

        Returns:
            True if backend is ready, False if failed

        Raises:
            ValueError: If lut_size is invalid
            PlatformNotSupportedError: If platform doesn't support streaming
        """
        if lut_size <= 0:
            raise ValueError(f"Invalid LUT size: {lut_size}")

        # Use provided stream name or fall back to default
        effective_stream_name = stream_name or self.stream_name

        # Check if we need to create or recreate the backend
        needs_recreation = (
            self._streamer is None
            or self._current_lut_size != lut_size
            or not self._is_streaming
        )

        if needs_recreation:
            # Clean up existing backend if any
            if self._streamer is not None:
                if self._current_lut_size != lut_size:
                    logger.debug(
                        f"Recreating streaming backend for LUT size change: {self._current_lut_size} -> {lut_size}"
                    )
                else:
                    logger.debug("Recreating streaming backend")
                try:
                    self._streamer.__exit__(None, None, None)  # type: ignore[attr-defined]
                except Exception as e:
                    logger.warning(f"Error cleaning up old backend: {e}")
                self._streamer = None
                self._is_streaming = False

            # Create new backend with correct dimensions
            try:
                logger.debug(
                    f"Creating streaming backend for {lut_size}x{lut_size}x{lut_size} LUT"
                )
                self._streamer = StreamingFactory.create_lut_streamer(
                    effective_stream_name, lut_size
                )

                # Initialize the backend
                self._streamer.initialize()

                self._current_lut_size = lut_size
                self._is_streaming = True
                logger.debug(
                    f"Started streaming to '{effective_stream_name}' with {lut_size}x{lut_size}x{lut_size} LUT"
                )
                return True

            except PlatformNotSupportedError:
                logger.error("Platform not supported for streaming")
                raise
            except Exception as e:
                logger.error(f"Failed to create streaming backend: {e}")
                raise RuntimeError(f"Failed to create streaming backend: {e}") from e

        return True

    def stop_streaming(self) -> None:
        """Stop GPU streaming."""
        if not self._is_streaming:
            return

        try:
            if self._streamer:
                self._streamer.__exit__(None, None, None)  # type: ignore[attr-defined]
                self._streamer = None
            self._is_streaming = False
            logger.debug("Stopped streaming")

        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")

    def process_lut(
        self, lut_data: np.ndarray[Any, Any], channel_name: str | None = None
    ) -> bool:
        """Process LUT data from OpenGradeIO and stream to GPU.

        Args:
            lut_data: LUT array from OpenGradeIO with shape (size, size, size, 3)
            channel_name: Optional channel/instance name for stream naming

        Returns:
            True if processed and streamed successfully

        Raises:
            ValueError: If LUT data is invalid
            RuntimeError: If streaming backend cannot be created
            PlatformNotSupportedError: If platform doesn't support streaming
        """
        # Validate LUT data shape
        if len(lut_data.shape) != 4 or lut_data.shape[3] != 3:
            raise ValueError(
                f"Invalid LUT data shape: {lut_data.shape}. Expected (size, size, size, 3)"
            )

        if (
            lut_data.shape[0] != lut_data.shape[1]
            or lut_data.shape[0] != lut_data.shape[2]
        ):
            raise ValueError(f"LUT must be cubic, got shape: {lut_data.shape}")

        try:
            # Get LUT size from received data
            lut_size = lut_data.shape[0]
            logger.debug(f"Processing {lut_size}x{lut_size}x{lut_size} LUT data")

            # Ensure streaming backend is ready for this LUT size
            # Use channel_name for stream naming if provided
            stream_name = None
            if channel_name:
                stream_name = f"vglb-lut-{channel_name}"
                logger.debug(f"Using channel-specific stream name: {stream_name}")

            self._ensure_streaming_backend(lut_size, stream_name)

            # Create converter for this LUT size if needed
            if self._converter is None or self._converter.lut_size != lut_size:
                self._converter = HaldConverter(lut_size)
                logger.debug(
                    f"Created converter for {lut_size}x{lut_size}x{lut_size} LUT"
                )

            # Convert to Hald image format
            hald_image = self._converter.lut_to_hald(lut_data)
            logger.debug(f"Converted LUT to Hald image: {hald_image.shape}")

            # Stream to GPU - backend should be ready at this point
            if not self._is_streaming or self._streamer is None:
                raise RuntimeError("Streaming backend not ready after initialization")

            try:
                self._streamer.send_lut_texture(hald_image)  # type: ignore[attr-defined]

                effective_name = stream_name or self.stream_name
                # Show essential streaming success info - always show
                print(f"🎯 Streamed {lut_size}³ LUT to '{effective_name}'")
                return True

            except Exception as e:
                logger.error(f"Failed to stream LUT: {e}")
                raise RuntimeError(f"Failed to stream LUT: {e}") from e

        except (ValueError, RuntimeError, PlatformNotSupportedError):
            # Re-raise validation and known errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing LUT: {e}")
            raise RuntimeError(f"Unexpected error processing LUT: {e}") from e

    @property
    def is_streaming(self) -> bool:
        """Check if currently streaming."""
        return self._is_streaming

    @property
    def current_lut_size(self) -> int | None:
        """Get current LUT size, if any."""
        return self._current_lut_size

    def get_status(self) -> dict[str, Any]:
        """Get current streaming status.

        Returns:
            Dictionary with status information
        """
        return {
            "stream_name": self.stream_name,
            "is_streaming": self._is_streaming,
            "current_lut_size": self._current_lut_size,
            "has_converter": self._converter is not None,
            "has_streamer": self._streamer is not None,
        }
