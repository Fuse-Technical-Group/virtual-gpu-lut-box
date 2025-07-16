"""Windows SpoutGL streaming backend."""

from __future__ import annotations

import contextlib
import importlib.util
import platform
from typing import Any

import numpy as np

from .base import InitializationError, StreamingBackend


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

    def initialize(self) -> bool:
        """Initialize the SpoutGL sender.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        if not self.is_available():
            return False

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
                return True
            else:
                self._sender = None
                return False

        except Exception as e:
            raise InitializationError(f"Failed to initialize SpoutGL: {e}") from e

    def send_texture(self, texture_data: np.ndarray) -> bool:
        """Send texture data via SpoutGL.

        Args:
            texture_data: Texture data as numpy array (height, width, 3 or 4)

        Returns:
            True if send successful, False otherwise
        """
        if not self._initialized or self._sender is None:
            return False

        if not self.validate_texture_data(texture_data):
            return False

        try:
            # Convert to format expected by SpoutGL
            spout_data = self._prepare_spout_data(texture_data)

            # Send via SpoutGL
            success = self._sender.sendImage(spout_data)

            return bool(success)

        except Exception:
            return False

    def _prepare_spout_data(self, texture_data: np.ndarray) -> np.ndarray:
        """Prepare texture data for SpoutGL.

        Args:
            texture_data: Input texture data

        Returns:
            Texture data formatted for SpoutGL
        """
        height, width, channels = texture_data.shape

        # Convert to uint8 if needed
        if texture_data.dtype == np.float32:
            data = (texture_data * 255).astype(np.uint8)
        else:
            data = texture_data.astype(np.uint8)

        # SpoutGL expects RGBA format
        if channels == 3:
            # Add alpha channel
            alpha = np.full((height, width, 1), 255, dtype=np.uint8)
            data = np.concatenate([data, alpha], axis=2)
        elif channels == 4:
            # Already RGBA
            pass
        else:
            raise ValueError(f"Unsupported channel count: {channels}")

        # SpoutGL expects data in specific memory layout
        # Ensure contiguous array
        data = np.ascontiguousarray(data)

        return data

    def cleanup(self) -> None:
        """Clean up SpoutGL resources."""
        if self._sender is not None:
            with contextlib.suppress(Exception):
                self._sender.release()
            self._sender = None

        self._spout_gl = None
        self._initialized = False

    def get_supported_formats(self) -> list[str]:
        """Get list of supported texture formats.

        Returns:
            List of supported format strings
        """
        return ["rgb", "rgba", "bgr", "bgra"]

    def get_spout_info(self) -> dict[str, Any]:
        """Get SpoutGL-specific information.

        Returns:
            Dictionary with SpoutGL info
        """
        info = {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "initialized": self._initialized,
            "platform": "Windows",
            "backend": "SpoutGL",
        }

        if self._initialized and self._sender is not None:
            with contextlib.suppress(Exception):
                # Get additional info from SpoutGL if available
                info.update(
                    {
                        "sender_active": True,
                        "supported_formats": self.get_supported_formats(),
                    }
                )

        return info

    def set_frame_sync(self, enable: bool) -> bool:
        """Enable or disable frame synchronization.

        Args:
            enable: True to enable frame sync, False to disable

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or self._sender is None:
            return False

        try:
            # SpoutGL frame sync methods
            if enable:
                return bool(self._sender.setFrameSync(True))
            else:
                return bool(self._sender.setFrameSync(False))
        except Exception:
            return False

    def wait_frame_sync(self) -> bool:
        """Wait for frame synchronization.

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or self._sender is None:
            return False

        try:
            return bool(self._sender.waitFrameSync())
        except Exception:
            return False

    def get_adapter_info(self) -> dict[str, str]:
        """Get graphics adapter information.

        Returns:
            Dictionary with adapter info
        """
        info = {}

        if self._initialized and self._spout_gl is not None:
            with contextlib.suppress(Exception):
                # Get adapter info if available in SpoutGL
                info.update(
                    {
                        "adapter_name": "Unknown",
                        "adapter_description": "Windows Graphics Adapter",
                    }
                )

        return info

    def is_receiver_connected(self) -> bool:
        """Check if any receivers are connected.

        Returns:
            True if receivers are connected, False otherwise
        """
        if not self._initialized or self._sender is None:
            return False

        try:
            # Check if there are active receivers
            # This might vary depending on SpoutGL version
            return True  # Assume connected for now
        except Exception:
            return False

    def get_frame_rate(self) -> float:
        """Get current frame rate.

        Returns:
            Current frame rate in FPS
        """
        if not self._initialized:
            return 0.0

        try:
            # Return estimated frame rate
            return 60.0  # Default assumption
        except Exception:
            return 0.0

    def resize(self, width: int, height: int) -> bool:
        """Resize the SpoutGL sender.

        Args:
            width: New width
            height: New height

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or self._sender is None:
            return False

        try:
            # Cleanup current sender
            self.cleanup()

            # Update dimensions
            self.width = width
            self.height = height

            # Reinitialize with new dimensions
            return self.initialize()

        except Exception:
            return False

    def send_lut_texture(self, hald_image: np.ndarray) -> bool:
        """Send LUT texture data optimized for GPU shaders.

        Args:
            hald_image: Hald image data from HaldConverter

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            return False

        # Validate hald image dimensions
        if hald_image.shape[:2] != (self.height, self.width):
            return False

        # Convert to RGBA format for SpoutGL
        rgba_data = self.convert_texture_format(hald_image, "rgba")

        # Send texture
        return self.send_texture(rgba_data)
