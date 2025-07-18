"""Windows SpoutGL streaming backend."""

from __future__ import annotations

import importlib.util
import platform
from typing import Any

import numpy as np

from .base import (
    InitializationError,
    StreamingBackend,
    StreamingError,
    TextureFormatError,
)


class SpoutBackend(StreamingBackend):
    """Windows SpoutGL streaming backend."""

    def __init__(self, name: str, width: int, height: int) -> None:
        """Initialize SpoutGL backend.

        Args:
            name: Name identifier for the Spout stream
            width: Width of the texture in pixels
            height: Height of the texture in pixels
        """
        super().__init__(name, width, height)
        self._sender: Any | None = None
        self._spout_gl: Any | None = None

    def is_available(self) -> bool:
        """Check if SpoutGL is available on this platform.

        Returns:
            True if SpoutGL is available, False otherwise
        """
        # Check if we're on Windows
        if platform.system() != "Windows":
            return False

        # Try to import SpoutGL
        return importlib.util.find_spec("SpoutGL") is not None

    def initialize(self) -> None:
        """Initialize the SpoutGL sender.

        Raises:
            InitializationError: If initialization fails
        """
        if self._initialized:
            return

        if not self.is_available():
            raise InitializationError(
                "SpoutGL not available: requires Windows with SpoutGL package"
            )

        try:
            # Import SpoutGL modules
            import SpoutGL
            from SpoutGL import SpoutSender

            # Store reference to SpoutGL module
            self._spout_gl = SpoutGL

            # Create SpoutGL sender
            self._sender = SpoutSender()

            # Initialize sender with name and dimensions
            # SpoutGL expects RGBA format by default
            success = self._sender.init(self.name, self.width, self.height)

            if success:
                self._initialized = True
            else:
                raise InitializationError(
                    f"Failed to initialize SpoutGL sender '{self.name}'"
                )

        except Exception as e:
            raise InitializationError(f"Failed to initialize SpoutGL: {e}") from e

    def send_texture(self, texture_data: np.ndarray) -> None:
        """Send texture data via SpoutGL.

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
            # Convert to format expected by SpoutGL
            spout_data = self._prepare_spout_data(texture_data)

            # Send via SpoutGL
            success = self._sender.sendImage(spout_data)

            if not success:
                raise StreamingError("SpoutGL sendImage failed")

        except Exception as e:
            raise StreamingError(f"SpoutGL streaming error: {e}") from e

    def _prepare_spout_data(self, texture_data: np.ndarray) -> np.ndarray:
        """Prepare texture data for SpoutGL with full precision preservation.

        Args:
            texture_data: Input texture data (must be float32)

        Returns:
            Texture data formatted for SpoutGL

        Raises:
            TextureFormatError: If texture data is not float32
        """
        height, width, channels = texture_data.shape

        # Enforce float32 precision only - no conversion allowed
        if texture_data.dtype != np.float32:
            raise TextureFormatError(
                f"SpoutGL backend requires float32 input, got {texture_data.dtype}. "
                f"No format conversion is performed to preserve precision."
            )

        print("🎯 Using 32-bit float precision for SpoutGL")
        data = texture_data.copy()

        # SpoutGL expects RGBA format
        if channels == 3:
            # Add alpha channel with 1.0 values
            alpha = np.full((height, width, 1), 1.0, dtype=np.float32)
            data = np.concatenate([data, alpha], axis=2)
        elif channels == 4:
            # Already RGBA
            pass
        else:
            raise TextureFormatError(f"Unsupported channel count: {channels}")

        # SpoutGL expects data in specific memory layout
        # Ensure contiguous array
        data = np.ascontiguousarray(data)

        return data

    def cleanup(self) -> None:
        """Clean up SpoutGL resources."""
        if self._sender is not None:
            try:
                self._sender.release()
            except Exception as e:
                # Log the error but continue cleanup
                print(f"Warning: Error releasing Spout sender: {e}")
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
        """Send LUT texture data optimized for GPU shaders.

        Args:
            hald_image: Hald image data from HaldConverter

        Raises:
            RuntimeError: If backend is not initialized
            TextureFormatError: If Hald image dimensions are incorrect
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

        # Convert to RGBA format for SpoutGL while preserving data type
        try:
            rgba_data = self.convert_texture_format(hald_image, "rgba")
            # Ensure we keep the original data type (float32 for LUTs)
            rgba_data = rgba_data.astype(hald_image.dtype)
        except Exception as e:
            raise TextureFormatError(
                f"Failed to convert Hald image to RGBA: {e}"
            ) from e

        # Send texture
        self.send_texture(rgba_data)
