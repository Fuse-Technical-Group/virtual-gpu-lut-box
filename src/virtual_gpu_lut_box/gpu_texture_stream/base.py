# SPDX-FileCopyrightText: 2025 Fuse Technical Group
#
# SPDX-License-Identifier: BSD-3-Clause

"""Abstract base class for streaming backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class StreamingBackend(ABC):
    """Abstract base class for texture streaming backends."""

    def __init__(self, name: str, width: int, height: int) -> None:
        """Initialize streaming backend.

        Args:
            name: Name identifier for the stream
            width: Width of the texture in pixels
            height: Height of the texture in pixels
        """
        self.name = name
        self.width = width
        self.height = height
        self._initialized = False
        self._context: Any | None = None

    @property
    def initialized(self) -> bool:
        """Check if backend is initialized."""
        return self._initialized

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the streaming backend.

        Raises:
            InitializationError: If initialization fails
        """
        pass

    @abstractmethod
    def send_texture(self, texture_data: np.ndarray) -> None:
        """Send texture data to the stream.

        Args:
            texture_data: Texture data as numpy array

        Raises:
            RuntimeError: If backend is not initialized
            TextureFormatError: If texture data is invalid
            StreamingError: If sending fails
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources and close the stream."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available on this platform.

        Returns:
            True if backend is available, False otherwise
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """Get list of supported texture formats.

        Returns:
            List of supported format strings
        """
        pass

    def validate_texture_data(self, texture_data: np.ndarray) -> bool:
        """Validate texture data format and dimensions.

        Args:
            texture_data: Texture data to validate

        Returns:
            True if valid, False otherwise

        Raises:
            TextureFormatError: If texture data is fundamentally invalid
        """
        # Check if numpy array
        if not isinstance(texture_data, np.ndarray):
            raise TextureFormatError(f"Expected numpy array, got {type(texture_data)}")

        # Check dimensions
        if len(texture_data.shape) != 3:
            raise TextureFormatError(
                f"Expected 3D array (height, width, channels), got {len(texture_data.shape)}D: {texture_data.shape}"
            )

        height, width, channels = texture_data.shape

        # Check size matches expected
        if height != self.height or width != self.width:
            raise TextureFormatError(
                f"Dimension mismatch: expected {self.height}x{self.width}, got {height}x{width}"
            )

        # Check channel count - expect RGBA from HaldConverter (RGB LUT data padded to RGBA)
        if channels != 4:
            raise TextureFormatError(
                f"Unsupported channel count: {channels}. Expected 4 (RGBA) from HaldConverter"
            )

        # Check data type - enforce float32 only for precision preservation
        if texture_data.dtype != np.float32:
            raise TextureFormatError(
                f"Unsupported data type: {texture_data.dtype}. Only float32 is supported to preserve precision."
            )

        # Check value range for float32
        # For LUT data, values can be outside [0,1] range (e.g., for HDR or creative looks)
        # Just ensure they're reasonable finite values
        if np.any(~np.isfinite(texture_data)):
            raise TextureFormatError("float32 contains non-finite values (NaN/Inf)")
        # Log if values are outside typical [0,1] range for debugging
        if np.any(texture_data < 0) or np.any(texture_data > 1):
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(
                "LUT contains values outside [0,1] range: [%.3f, %.3f] - this is normal for HDR/creative LUTs",
                texture_data.min(),
                texture_data.max(),
            )

        return True

    def convert_texture_format(
        self, texture_data: np.ndarray, target_format: str
    ) -> np.ndarray:
        """Convert texture data to target format.

        Args:
            texture_data: Source texture data (RGBA from HaldConverter)
            target_format: Target format ('rgb', 'rgba', 'bgr', 'bgra')

        Returns:
            Converted texture data
        """
        if not self.validate_texture_data(texture_data):
            raise ValueError("Invalid texture data")

        _, _, channels = texture_data.shape

        # Input should always be RGBA (4 channels) from HaldConverter
        if channels != 4:
            raise ValueError(f"Expected RGBA input (4 channels), got {channels}")

        # Keep data in original format for processing to preserve precision
        # Only float32 is supported for precision preservation
        data = texture_data.copy()

        # Handle format conversion
        target_format = target_format.lower()

        if target_format == "rgb":
            # Remove alpha channel
            data = data[:, :, :3]
        elif target_format == "rgba":
            # Already RGBA, no conversion needed
            pass
        elif target_format == "bgr":
            # Remove alpha and swap R/B channels
            data = data[:, :, [2, 1, 0]]
        elif target_format == "bgra":
            # Swap R/B channels, keep alpha
            data = data[:, :, [2, 1, 0, 3]]
        else:
            raise ValueError(f"Unsupported format: {target_format}")

        return data

    def send_lut_texture(self, hald_image: np.ndarray) -> None:
        """Send LUT texture data.

        Default implementation just calls send_texture.
        Subclasses may override for specialized LUT handling.

        Args:
            hald_image: Hald image data

        Raises:
            RuntimeError: If backend is not initialized
            TextureFormatError: If texture data is invalid
            StreamingError: If sending fails
        """
        if not self._initialized:
            raise RuntimeError(
                f"Backend '{self.name}' is not initialized. Call initialize() first."
            )

        self.send_texture(hald_image)

    def __enter__(self) -> StreamingBackend:
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        del exc_type, exc_val, exc_tb  # Mark as used for static analysis
        self.cleanup()

    def __del__(self) -> None:
        """Destructor to ensure cleanup."""
        if self._initialized:
            self.cleanup()


class StreamingError(Exception):
    """Exception raised by streaming backends."""

    pass


class PlatformNotSupportedError(StreamingError):
    """Exception raised when platform is not supported."""

    pass


class InitializationError(StreamingError):
    """Exception raised when initialization fails."""

    pass


class TextureFormatError(StreamingError):
    """Exception raised when texture format is invalid."""

    pass
