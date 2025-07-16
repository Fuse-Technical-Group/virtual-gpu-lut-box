"""Abstract base class for streaming backends."""

from __future__ import annotations

import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Any


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
        self._context: Optional[Any] = None

    @property
    def initialized(self) -> bool:
        """Check if backend is initialized."""
        return self._initialized

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the streaming backend.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    def send_texture(self, texture_data: np.ndarray) -> bool:
        """Send texture data to the stream.

        Args:
            texture_data: Texture data as numpy array

        Returns:
            True if send successful, False otherwise
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
        """
        # Check if numpy array
        if not isinstance(texture_data, np.ndarray):
            return False

        # Check dimensions
        if len(texture_data.shape) != 3:
            return False

        height, width, channels = texture_data.shape

        # Check size matches expected
        if height != self.height or width != self.width:
            return False

        # Check channel count (RGB or RGBA)
        if channels not in [3, 4]:
            return False

        # Check data type
        if texture_data.dtype not in [np.uint8, np.float32]:
            return False

        # Check value range
        if texture_data.dtype == np.uint8:
            if np.any(texture_data < 0) or np.any(texture_data > 255):
                return False
        elif texture_data.dtype == np.float32:
            if np.any(texture_data < 0) or np.any(texture_data > 1):
                return False

        return True

    def convert_texture_format(
        self, texture_data: np.ndarray, target_format: str
    ) -> np.ndarray:
        """Convert texture data to target format.

        Args:
            texture_data: Source texture data
            target_format: Target format ('rgb', 'rgba', 'bgr', 'bgra')

        Returns:
            Converted texture data
        """
        if not self.validate_texture_data(texture_data):
            raise ValueError("Invalid texture data")

        height, width, channels = texture_data.shape

        # Convert to float32 for processing
        if texture_data.dtype == np.uint8:
            data = texture_data.astype(np.float32) / 255.0
        else:
            data = texture_data.copy()

        # Handle format conversion
        target_format = target_format.lower()

        if target_format == "rgb":
            if channels == 4:
                # Remove alpha channel
                data = data[:, :, :3]
            elif channels == 3:
                # Already RGB
                pass
        elif target_format == "rgba":
            if channels == 3:
                # Add alpha channel
                alpha = np.ones((height, width, 1), dtype=data.dtype)
                data = np.concatenate([data, alpha], axis=2)
            elif channels == 4:
                # Already RGBA
                pass
        elif target_format == "bgr":
            if channels == 4:
                # Remove alpha and swap R/B
                data = data[:, :, [2, 1, 0]]
            elif channels == 3:
                # Swap R/B channels
                data = data[:, :, [2, 1, 0]]
        elif target_format == "bgra":
            if channels == 3:
                # Swap R/B and add alpha
                bgr = data[:, :, [2, 1, 0]]
                alpha = np.ones((height, width, 1), dtype=data.dtype)
                data = np.concatenate([bgr, alpha], axis=2)
            elif channels == 4:
                # Swap R/B channels
                data = data[:, :, [2, 1, 0, 3]]
        else:
            raise ValueError(f"Unsupported format: {target_format}")

        return data

    def __enter__(self) -> StreamingBackend:
        """Context manager entry."""
        if not self.initialize():
            raise RuntimeError("Failed to initialize streaming backend")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
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
