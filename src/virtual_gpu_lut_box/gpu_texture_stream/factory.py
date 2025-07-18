"""Factory for creating platform-specific streaming backends."""

from __future__ import annotations

import platform

from .base import PlatformNotSupportedError, StreamingBackend


class StreamingFactory:
    """Factory for creating platform-specific streaming backends."""

    _backends: dict[str, type[StreamingBackend]] = {}

    @classmethod
    def register_backend(
        cls, platform_name: str, backend_class: type[StreamingBackend]
    ) -> None:
        """Register a streaming backend for a platform.

        Args:
            platform_name: Platform name ('Windows', 'Darwin', 'Linux')
            backend_class: Backend class to register
        """
        cls._backends[platform_name] = backend_class

    @classmethod
    def get_available_backends(cls) -> list[str]:
        """Get list of available backend names.

        Returns:
            List of available backend platform names
        """
        return list(cls._backends.keys())

    @classmethod
    def create_backend(
        cls,
        name: str = "virtual-gpu-lut-box",
        width: int = 1089,
        height: int = 33,
        platform_name: str | None = None,
    ) -> StreamingBackend:
        """Create appropriate streaming backend for current platform.

        Args:
            name: Name identifier for the stream
            width: Width of the texture in pixels
            height: Height of the texture in pixels
            platform_name: Override platform detection (for testing)

        Returns:
            Platform-specific streaming backend

        Raises:
            ValueError: If dimensions are invalid
            PlatformNotSupportedError: If platform is not supported
        """
        # Validate inputs
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid stream name: {name!r}")

        if width <= 0 or height <= 0:
            raise ValueError(
                f"Invalid dimensions: {width}x{height}. Must be positive integers."
            )

        if width > 16384 or height > 16384:
            raise ValueError(
                f"Dimensions too large: {width}x{height}. Maximum is 16384x16384."
            )

        # Detect platform if not specified
        if platform_name is None:
            platform_name = platform.system()

        # Check if backend is available
        if platform_name not in cls._backends:
            available = list(cls._backends.keys())
            raise PlatformNotSupportedError(
                f"Platform '{platform_name}' is not supported. Available platforms: {available}"
            )

        # Create backend instance
        backend_class = cls._backends[platform_name]
        try:
            backend = backend_class(name, width, height)
        except Exception as e:
            raise RuntimeError(f"Failed to create {platform_name} backend: {e}") from e

        # Verify backend is available
        if not backend.is_available():
            raise PlatformNotSupportedError(
                f"Backend for '{platform_name}' is not available on this system"
            )

        return backend

    @classmethod
    def get_current_platform(cls) -> str:
        """Get current platform name.

        Returns:
            Current platform name
        """
        return platform.system()

    @classmethod
    def is_platform_supported(cls, platform_name: str | None = None) -> bool:
        """Check if platform is supported.

        Args:
            platform_name: Platform name to check (defaults to current)

        Returns:
            True if platform is supported, False otherwise
        """
        if platform_name is None:
            platform_name = platform.system()

        if platform_name not in cls._backends:
            return False

        try:
            # Try to create a minimal backend to test availability
            backend_class = cls._backends[platform_name]
            backend = backend_class("test", 1, 1)
            return backend.is_available()
        except Exception:
            return False

    @classmethod
    def create_lut_streamer(
        cls,
        name: str = "virtual-gpu-lut-box",
        lut_size: int = 33,
        platform_name: str | None = None,
    ) -> StreamingBackend:
        """Create streaming backend optimized for LUT streaming.

        Args:
            name: Name identifier for the stream
            lut_size: Size of the LUT cube (default: 33)
            platform_name: Override platform detection

        Returns:
            Streaming backend configured for LUT dimensions

        Raises:
            ValueError: If lut_size is invalid
            PlatformNotSupportedError: If platform is not supported
        """
        # Validate LUT size
        if lut_size <= 0:
            raise ValueError(f"Invalid LUT size: {lut_size}. Must be positive.")

        if lut_size > 256:
            raise ValueError(
                f"LUT size too large: {lut_size}. Maximum supported is 256."
            )

        # Calculate Hald image dimensions
        width = lut_size * lut_size  # 33 * 33 = 1089
        height = lut_size  # 33

        try:
            return cls.create_backend(name, width, height, platform_name)
        except Exception as e:
            raise RuntimeError(
                f"Failed to create LUT streamer for {lut_size}x{lut_size}x{lut_size}: {e}"
            ) from e

    @classmethod
    def list_supported_formats(cls, platform_name: str | None = None) -> list[str]:
        """List supported texture formats for platform.

        Args:
            platform_name: Platform name to check (defaults to current)

        Returns:
            List of supported format strings
        """
        if platform_name is None:
            platform_name = platform.system()

        if platform_name not in cls._backends:
            return []

        try:
            backend_class = cls._backends[platform_name]
            backend = backend_class("test", 1, 1)
            if backend.is_available():
                return backend.get_supported_formats()
        except Exception:  # noqa: S110
            # Backend unavailable or failed to initialize
            pass

        return []

    @classmethod
    def get_platform_info(cls) -> dict[str, str]:
        """Get detailed platform information.

        Returns:
            Dictionary with platform details
        """
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }


# Register backends when modules are imported
def _register_backends() -> None:
    """Register available backends based on platform."""
    current_platform = platform.system()

    if current_platform == "Windows":
        try:
            from .spout import SpoutBackend

            StreamingFactory.register_backend("Windows", SpoutBackend)
        except ImportError:
            pass  # SpoutGL not available

    elif current_platform == "Darwin":
        try:
            from .syphon import SyphonBackend

            StreamingFactory.register_backend("Darwin", SyphonBackend)
        except ImportError:
            pass  # syphon-python not available


# Auto-register backends
_register_backends()
