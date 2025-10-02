# SPDX-FileCopyrightText: 2025 Fuse Technical Group
#
# SPDX-License-Identifier: BSD-3-Clause

"""Windows SpoutGL streaming backend with OpenGL texture support.

REQUIREMENTS: This backend uses GL_RGBA32F OpenGL textures for full float32 precision.
This requires:
- Modified Python-SpoutGL with GL_RGBA32F support
- PyOpenGL for texture creation and management

The backend creates OpenGL textures and uses SendTexture() instead of SendImage()
to preserve full 32-bit float precision, mirroring the Syphon/Metal approach.
"""

from __future__ import annotations

import importlib.util
import platform
import time
from typing import Any

import numpy as np

try:
    from OpenGL import GL
except ImportError:
    GL = None  # type: ignore[assignment]

from .base import (
    InitializationError,
    StreamingBackend,
    StreamingError,
    TextureFormatError,
)

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


class SpoutBackend(StreamingBackend):
    """Windows SpoutGL streaming backend using OpenGL textures."""

    def __init__(
        self, name: str, width: int, height: int, quiet_mode: bool = True
    ) -> None:
        """Initialize SpoutGL backend.

        Args:
            name: Name identifier for the Spout stream
            width: Width of the texture in pixels
            height: Height of the texture in pixels
            quiet_mode: Suppress initialization and FPS messages
        """
        super().__init__(name, width, height)
        self._sender: Any | None = None
        self._spout_gl: Any | None = None
        self._texture: Any | None = None  # OpenGL texture ID
        self._frame_count = 0
        self._last_fps_check = time.time()
        self._quiet_mode = quiet_mode

    def is_available(self) -> bool:
        """Check if SpoutGL and PyOpenGL are available on this platform.

        Returns:
            True if SpoutGL and PyOpenGL are available, False otherwise
        """
        # Check if we're on Windows
        if platform.system() != "Windows":
            return False

        # Try to import SpoutGL and PyOpenGL
        return GL is not None and importlib.util.find_spec("SpoutGL") is not None

    def initialize(self) -> None:
        """Initialize the SpoutGL sender with OpenGL context.

        Raises:
            InitializationError: If initialization fails
        """
        if self._initialized:
            return

        if not self.is_available():
            raise InitializationError(
                "SpoutGL not available: requires Windows with SpoutGL and PyOpenGL"
            )

        try:
            # Import SpoutGL modules
            import SpoutGL
            from SpoutGL import SpoutSender

            # Store reference to SpoutGL module
            self._spout_gl = SpoutGL

            # Create SpoutGL sender
            self._sender = SpoutSender()

            # Set sender name
            self._sender.setSenderName(self.name)

            # Initialize OpenGL context (required for texture operations)
            if not self._quiet_mode:
                print(f"Creating Spout sender with OpenGL context: '{self.name}'")
            if not self._sender.createOpenGL():
                raise InitializationError("Failed to create OpenGL context")

            # Mark as initialized
            self._initialized = True
            if not self._quiet_mode:
                print(f"Spout sender '{self.name}' initialized successfully")

        except Exception as e:
            raise InitializationError(f"Failed to initialize SpoutGL: {e}") from e

    def send_texture(self, texture_data: np.ndarray) -> None:
        """Send texture data via SpoutGL using OpenGL textures.

        Args:
            texture_data: Texture data as numpy array (height, width, 3 or 4)

        Raises:
            RuntimeError: If backend is not initialized
            TextureFormatError: If texture data is invalid
            StreamingError: If sending fails
        """
        if not self._initialized or self._sender is None:
            raise RuntimeError(f"Spout backend '{self.name}' is not initialized")

        # This will raise TextureFormatError if invalid
        self.validate_texture_data(texture_data)

        try:
            # Create or update OpenGL texture with float32 data
            self._create_gl_texture(texture_data)

            # Send texture via SpoutGL
            # sendTexture(textureID, textureTarget, width, height, bInvert, hostFBO)
            success = self._sender.sendTexture(
                self._texture,  # OpenGL texture ID
                GL.GL_TEXTURE_2D,  # Texture target
                self.width,
                self.height,
                False,  # Don't invert
                0,  # No host FBO
            )

            if not success:
                raise StreamingError("SpoutGL sendTexture failed")

            # Update frame counter and log FPS periodically (only in verbose mode)
            if not self._quiet_mode:
                self._frame_count += 1
                current_time = time.time()
                if current_time - self._last_fps_check > 2.0:  # Every 2 seconds
                    elapsed = current_time - self._last_fps_check
                    fps = (
                        self._frame_count - (getattr(self, "_last_frame_count", 0))
                    ) / elapsed
                    print(f"Spout streaming: {fps:.1f} FPS")
                    self._last_frame_count = self._frame_count
                    self._last_fps_check = current_time

        except Exception as e:
            raise StreamingError(f"SpoutGL streaming error: {e}") from e

    def _create_gl_texture(self, texture_data: np.ndarray) -> None:
        """Create OpenGL texture from numpy array.

        Mirrors the Syphon Metal texture approach but using OpenGL.

        Args:
            texture_data: Texture data as numpy array (must be float32)

        Raises:
            TextureFormatError: If texture format is not supported
            StreamingError: If OpenGL texture creation fails
        """
        if GL is None:
            raise StreamingError("PyOpenGL not available")

        try:
            # Validate float32 precision
            if texture_data.dtype != np.float32:
                raise TextureFormatError(
                    f"Unsupported texture data type: {texture_data.dtype}. "
                    f"Only float32 is supported for precision preservation."
                )

            height, width, channels = texture_data.shape

            # Add alpha channel if needed (OpenGL RGBA32F requires 4 channels)
            if channels == 3:
                alpha = np.full((height, width, 1), 1.0, dtype=np.float32)
                final_data = np.concatenate([texture_data, alpha], axis=2)
            elif channels == 4:
                final_data = np.ascontiguousarray(texture_data)
            else:
                raise TextureFormatError(
                    f"Unsupported channel count: {channels}. "
                    f"Only RGB (3 channels) and RGBA (4 channels) are supported."
                )

            # Ensure contiguous array for OpenGL
            final_data = np.ascontiguousarray(final_data)

            # Create or reuse texture
            if self._texture is None:
                self._texture = GL.glGenTextures(1)
                if not self._quiet_mode:
                    print(f"Created OpenGL texture ID: {self._texture}")

            # Bind texture
            GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture)

            # Set texture parameters
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(
                GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE
            )
            GL.glTexParameteri(
                GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE
            )

            # Upload texture data with GL_RGBA32F format
            GL.glTexImage2D(
                GL.GL_TEXTURE_2D,  # target
                0,  # level
                GL.GL_RGBA32F,  # internal format (float32 precision)
                width,
                height,
                0,  # border
                GL.GL_RGBA,  # format
                GL.GL_FLOAT,  # type
                final_data,  # data
            )

            # Unbind texture
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        except Exception as e:
            raise StreamingError(f"OpenGL texture creation failed: {e}") from e

    def cleanup(self) -> None:
        """Clean up SpoutGL and OpenGL resources."""
        # NOTE: We don't manually delete the OpenGL texture here because:
        # 1. SpoutGL doesn't expose a way to make the context current during cleanup
        # 2. glDeleteTextures() requires an active context, which may not be available
        #    (cleanup can run on different threads, during shutdown, etc.)
        # 3. releaseSender() destroys the OpenGL context, which automatically frees
        #    all associated GL resources including our texture
        # Attempting manual deletion causes harmless but noisy GL_INVALID_OPERATION errors.
        self._texture = None

        # Clean up Spout sender (this destroys the OpenGL context and all resources)
        if self._sender is not None:
            print(f"Stopping Spout sender '{self.name}'")
            try:
                self._sender.releaseSender()
                print(f"Spout sender '{self.name}' stopped successfully")
            except Exception as e:
                print(f"Warning: Error releasing Spout sender '{self.name}': {e}")
            finally:
                self._sender = None

        self._spout_gl = None
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
            raise RuntimeError(f"Spout backend '{self.name}' is not initialized")

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
