# SPDX-FileCopyrightText: 2025 Fuse Technical Group
#
# SPDX-License-Identifier: BSD-3-Clause

"""macOS Syphon streaming backend using Metal."""

from __future__ import annotations

import importlib.util
import platform
import time
from typing import Any

import numpy as np

from .base import (
    InitializationError,
    StreamingBackend,
    StreamingError,
    TextureFormatError,
)

try:
    import Metal
except ImportError:
    Metal = None  # type: ignore[assignment]

# Message elision for quiet mode - track repeated messages
_message_counts: dict[str, int] = {}
_last_message_time: dict[str, float] = {}


def _should_show_message(message: str, quiet_mode: bool = True) -> bool:
    """Determine if a repeated message should be shown based on quiet mode and frequency."""
    if not quiet_mode:
        return True

    current_time = time.time()

    # Always show first occurrence
    if message not in _message_counts:
        _message_counts[message] = 1
        _last_message_time[message] = current_time
        return True

    _message_counts[message] += 1
    time_since_last = current_time - _last_message_time[message]

    # Show every 10th message or after 5 seconds, whichever comes first
    if _message_counts[message] % 10 == 0 or time_since_last >= 5.0:
        _last_message_time[message] = current_time
        return True

    return False


def _elided_print(message: str, quiet_mode: bool = True) -> None:
    """Print a message with elision logic for quiet mode."""
    if _should_show_message(message, quiet_mode):
        count = _message_counts.get(message, 0)
        if count > 1:
            print(f"{message} ({count} times)")
        else:
            print(message)


class SyphonBackend(StreamingBackend):
    """macOS Syphon streaming backend using Metal."""

    def __init__(self, name: str, width: int, height: int) -> None:
        """Initialize Syphon backend.

        Args:
            name: Name identifier for the Syphon stream
            width: Width of the texture in pixels
            height: Height of the texture in pixels
        """
        super().__init__(name, width, height)
        self._server: Any | None = None
        self._syphon: Any | None = None
        self._device: Any | None = None
        self._command_queue: Any | None = None
        self._texture: Any | None = None
        self._frame_count = 0
        self._last_fps_check = time.time()

    def is_available(self) -> bool:
        """Check if Syphon is available on this platform.

        Returns:
            True if Syphon is available, False otherwise
        """
        # Check if we're on macOS
        if platform.system() != "Darwin":
            return False

        # Try to import syphon-python and Metal
        return Metal is not None and importlib.util.find_spec("syphon") is not None

    def initialize(self) -> None:
        """Initialize the Syphon Metal server.

        Raises:
            InitializationError: If initialization fails
        """
        if self._initialized:
            return

        if not self.is_available():
            raise InitializationError(
                "Syphon not available: requires macOS with syphon-python and Metal"
            )

        try:
            # Import syphon-python
            import syphon

            # Store reference to syphon module
            self._syphon = syphon

            # Initialize Metal device and command queue
            self._init_metal()

            # Create Syphon Metal server
            print(f"🎥 Creating Syphon Metal server with name: '{self.name}'")
            self._server = syphon.SyphonMetalServer(
                self.name, device=self._device, command_queue=self._command_queue
            )

            if self._server is not None:
                self._initialized = True
                print(f"✅ Syphon Metal server '{self.name}' created successfully")
                if self._device is not None:
                    print(f"📱 Metal device: {self._device.name()}")
            else:
                raise InitializationError(
                    f"Failed to create Syphon Metal server '{self.name}'"
                )

        except Exception as e:
            raise InitializationError(f"Failed to initialize Syphon Metal: {e}") from e

    def send_texture(self, texture_data: np.ndarray) -> None:
        """Send texture data via Syphon Metal.

        Args:
            texture_data: Texture data as numpy array (height, width, 3 or 4)

        Raises:
            RuntimeError: If backend is not initialized
            TextureFormatError: If texture data is invalid
            StreamingError: If sending fails
        """
        if not self._initialized or self._server is None:
            raise RuntimeError(f"Syphon backend '{self.name}' is not initialized")

        # This will raise TextureFormatError if invalid
        self.validate_texture_data(texture_data)

        try:
            # Create or update Metal texture
            self._create_metal_texture(texture_data)

            # Publish frame via Syphon Metal server
            self._server.publish_frame_texture(self._texture)

            # Update frame counter and log FPS periodically
            self._frame_count += 1
            current_time = time.time()
            if current_time - self._last_fps_check > 2.0:  # Every 2 seconds
                elapsed = current_time - self._last_fps_check
                fps = (
                    self._frame_count - (getattr(self, "_last_frame_count", 0))
                ) / elapsed
                _elided_print(f"📊 Syphon Metal streaming: {fps:.1f} FPS")
                self._last_frame_count = self._frame_count
                self._last_fps_check = current_time

        except Exception as e:
            raise StreamingError(f"Syphon Metal streaming error: {e}") from e

    def cleanup(self) -> None:
        """Clean up Syphon and Metal resources."""
        if self._server is not None:
            print(f"🛑 Stopping Syphon Metal server '{self.name}'")
            try:
                self._server.stop()
                print(f"✅ Syphon Metal server '{self.name}' stopped successfully")
            except Exception as e:
                print(f"⚠️  Error stopping Syphon Metal server '{self.name}': {e}")
            self._server = None

        # Clean up Metal resources
        self._texture = None
        self._command_queue = None
        self._device = None
        self._syphon = None
        self._initialized = False

    def get_supported_formats(self) -> list[str]:
        """Get list of supported texture formats.

        Returns:
            List of supported format strings
        """
        return ["rgb", "rgba", "bgr", "bgra"]

    def send_lut_texture(self, hald_image: np.ndarray) -> None:
        """Send LUT texture data with full precision preservation.

        Args:
            hald_image: Hald image data from HaldConverter (float32 format)

        Raises:
            RuntimeError: If backend is not initialized
            TextureFormatError: If Hald image format is incorrect
            StreamingError: If sending fails
        """
        if not self._initialized:
            raise RuntimeError(f"Syphon backend '{self.name}' is not initialized")

        # Validate hald image dimensions
        if hald_image.shape[:2] != (self.height, self.width):
            raise TextureFormatError(
                f"Hald image dimension mismatch: expected {self.height}x{self.width}, "
                f"got {hald_image.shape[0]}x{hald_image.shape[1]}"
            )

        # Validate that input is float32 (no conversion allowed)
        if hald_image.dtype != np.float32:
            raise TextureFormatError(
                f"Hald image must be float32 format, got {hald_image.dtype}. "
                f"No format conversion is performed to preserve precision."
            )

        # Send texture directly without any format conversion
        self.send_texture(hald_image)

    def _init_metal(self) -> None:
        """Initialize Metal device and command queue.

        Raises:
            InitializationError: If Metal initialization fails
        """
        if Metal is None:
            raise InitializationError("Metal framework is not available")

        try:
            # Create Metal device
            self._device = Metal.MTLCreateSystemDefaultDevice()
            if self._device is None:
                raise InitializationError("No Metal device available")

            # Create command queue
            self._command_queue = self._device.newCommandQueue()
            if self._command_queue is None:
                raise InitializationError("Failed to create Metal command queue")

            print(f"✅ Metal device initialized: {self._device.name()}")

        except Exception as e:
            raise InitializationError(f"Metal initialization failed: {e}") from e

    def _create_metal_texture(self, texture_data: np.ndarray) -> None:
        """Create Metal texture from numpy array.

        Args:
            texture_data: Texture data as numpy array

        Raises:
            TextureFormatError: If the texture format is not supported by GPU
            StreamingError: If Metal texture creation fails
        """
        if Metal is None or self._device is None:
            raise StreamingError("Metal device not available")

        try:
            # Prepare texture data
            height, width, channels = texture_data.shape

            # Validate that we only support float32 for precision preservation
            if texture_data.dtype != np.float32:
                raise TextureFormatError(
                    f"Unsupported texture data type: {texture_data.dtype}. "
                    f"Only float32 is supported for precision preservation."
                )

            # Choose Metal pixel format based on channel count
            # For RGB data, we'll add a dummy alpha channel since Metal RGBA32Float is more universally supported
            if channels == 3:
                # Add alpha channel with 1.0 values for Metal RGBA format compatibility
                alpha = np.full((height, width, 1), 1.0, dtype=np.float32)
                final_data = np.concatenate([texture_data, alpha], axis=2)
                pixel_format = Metal.MTLPixelFormatRGBA32Float
                _elided_print(
                    "🎯 Using RGBA32Float with dummy alpha for RGB data (full precision)"
                )
            elif channels == 4:
                # Use RGBA format directly
                final_data = np.ascontiguousarray(texture_data)
                pixel_format = Metal.MTLPixelFormatRGBA32Float
                _elided_print(
                    "🎯 Using RGBA32Float with actual alpha data (full precision)"
                )
            else:
                raise TextureFormatError(
                    f"Unsupported channel count: {channels}. "
                    f"Only RGB (3 channels) and RGBA (4 channels) are supported."
                )

            # Ensure contiguous array for Metal
            final_data = np.ascontiguousarray(final_data)

            # Create texture descriptor
            texture_desc = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
                pixel_format, width, height, False
            )
            texture_desc.setUsage_(
                Metal.MTLTextureUsageShaderRead | Metal.MTLTextureUsageShaderWrite
            )

            # Create the texture
            self._texture = self._device.newTextureWithDescriptor_(texture_desc)
            if self._texture is None:
                raise StreamingError("Failed to create Metal texture")

            # Upload data to texture
            region = Metal.MTLRegion(
                Metal.MTLOrigin(0, 0, 0), Metal.MTLSize(width, height, 1)
            )

            # Calculate bytes per row for RGBA32Float format
            bytes_per_row = width * 16  # Always RGBA32Float now

            self._texture.replaceRegion_mipmapLevel_withBytes_bytesPerRow_(
                region, 0, final_data.tobytes(), bytes_per_row
            )

        except Exception as e:
            raise StreamingError(f"Metal texture creation failed: {e}") from e
