"""macOS Syphon streaming backend using Metal."""

from __future__ import annotations

import numpy as np
import platform
import time
from typing import Optional, Any

from .base import StreamingBackend, InitializationError

try:
    import Metal
    METAL_AVAILABLE = True
except ImportError:
    METAL_AVAILABLE = False


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
        self._server: Optional[Any] = None
        self._syphon: Optional[Any] = None
        self._device: Optional[Any] = None
        self._command_queue: Optional[Any] = None
        self._texture: Optional[Any] = None
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
        try:
            import syphon
            return METAL_AVAILABLE
        except ImportError:
            return False

    def initialize(self) -> bool:
        """Initialize the Syphon Metal server.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        if not self.is_available():
            return False

        try:
            # Import syphon-python
            import syphon

            # Store reference to syphon module
            self._syphon = syphon

            # Initialize Metal device and command queue
            if not self._init_metal():
                return False

            # Create Syphon Metal server
            print(f"🎥 Creating Syphon Metal server with name: '{self.name}'")
            self._server = syphon.SyphonMetalServer(
                self.name, 
                device=self._device, 
                command_queue=self._command_queue
            )

            if self._server is not None:
                self._initialized = True
                print(f"✅ Syphon Metal server '{self.name}' created successfully")
                print(f"📱 Metal device: {self._device.name()}")
                return True
            else:
                print(f"❌ Failed to create Syphon Metal server '{self.name}'")
                return False

        except Exception as e:
            raise InitializationError(f"Failed to initialize Syphon Metal: {e}")

    def send_texture(self, texture_data: np.ndarray) -> bool:
        """Send texture data via Syphon Metal.

        Args:
            texture_data: Texture data as numpy array (height, width, 3 or 4)

        Returns:
            True if send successful, False otherwise
        """
        if not self._initialized or self._server is None:
            return False

        if not self.validate_texture_data(texture_data):
            return False

        try:
            # Create or update Metal texture
            if not self._create_metal_texture(texture_data):
                return False

            # Publish frame via Syphon Metal server
            self._server.publish_frame_texture(self._texture)

            # Update frame counter and log FPS periodically
            self._frame_count += 1
            current_time = time.time()
            if current_time - self._last_fps_check > 2.0:  # Every 2 seconds
                elapsed = current_time - self._last_fps_check
                fps = (self._frame_count - (getattr(self, '_last_frame_count', 0))) / elapsed
                print(f"📊 Syphon Metal streaming: {fps:.1f} FPS, Clients: {self.has_clients}")
                self._last_frame_count = self._frame_count
                self._last_fps_check = current_time

            return True

        except Exception as e:
            print(f"⚠️  Syphon Metal streaming error: {e}")
            return False

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

    def get_syphon_info(self) -> dict[str, Any]:
        """Get Syphon-specific information.

        Returns:
            Dictionary with Syphon info
        """
        info = {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "initialized": self._initialized,
            "platform": "macOS",
            "backend": "Syphon Metal",
            "frame_count": self._frame_count,
        }

        if self._initialized and self._server is not None:
            try:
                info.update({
                    "server_active": True,
                    "has_clients": self.has_clients,
                    "supported_formats": self.get_supported_formats(),
                    "metal_device": self._device.name() if self._device else "Unknown",
                })
            except Exception:
                pass

        return info

    @property
    def has_clients(self) -> bool:
        """Check if any clients are connected.

        Returns:
            True if clients are connected, False otherwise
        """
        if not self._initialized or self._server is None:
            return False

        try:
            return self._server.has_clients
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
            # Calculate FPS based on frame count
            if hasattr(self, '_last_fps_check') and hasattr(self, '_last_frame_count'):
                elapsed = time.time() - self._last_fps_check
                if elapsed > 0:
                    return (self._frame_count - self._last_frame_count) / elapsed
            return 60.0  # Default assumption
        except Exception:
            return 0.0

    def resize(self, width: int, height: int) -> bool:
        """Resize the Syphon server.

        Args:
            width: New width
            height: New height

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or self._server is None:
            return False

        try:
            # Cleanup current server
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

        # Convert to RGBA format for Metal
        rgba_data = self.convert_texture_format(hald_image, "rgba")

        # Send texture
        return self.send_texture(rgba_data)

    def get_metal_device_info(self) -> dict[str, str]:
        """Get Metal device information.

        Returns:
            Dictionary with Metal device info
        """
        info = {}

        if self._initialized and self._device:
            try:
                info.update({
                    "device_name": self._device.name(),
                    "device_description": f"Metal Device: {self._device.name()}",
                    "supports_unified_memory": str(self._device.hasUnifiedMemory()),
                    "max_texture_size": "16384x16384",  # Metal typical limit
                })
            except Exception:
                pass

        return info

    def get_texture_format_info(self) -> dict[str, Any]:
        """Get texture format information.

        Returns:
            Dictionary with texture format info
        """
        return {
            "preferred_format": "RGBA",
            "supported_formats": self.get_supported_formats(),
            "bit_depth": 8,
            "color_space": "sRGB",
            "alpha_support": True,
            "backend": "Metal",
        }

    def _init_metal(self) -> bool:
        """Initialize Metal device and command queue.
        
        Returns:
            True if successful, False otherwise
        """
        if not METAL_AVAILABLE:
            return False

        try:
            # Create Metal device
            self._device = Metal.MTLCreateSystemDefaultDevice()
            if self._device is None:
                print("❌ No Metal device available")
                return False

            # Create command queue
            self._command_queue = self._device.newCommandQueue()
            if self._command_queue is None:
                print("❌ Failed to create Metal command queue")
                return False

            print(f"✅ Metal device initialized: {self._device.name()}")
            return True
            
        except Exception as e:
            print(f"⚠️  Metal initialization failed: {e}")
            return False

    def _create_metal_texture(self, texture_data: np.ndarray) -> bool:
        """Create Metal texture from numpy array.
        
        Args:
            texture_data: Texture data as numpy array
            
        Returns:
            True if successful, False otherwise
        """
        if not METAL_AVAILABLE or self._device is None:
            return False

        try:
            # Prepare texture data
            height, width, channels = texture_data.shape
            
            # Convert to RGBA format if needed
            if channels == 3:
                # Add alpha channel
                alpha = np.full((height, width, 1), 255, dtype=np.uint8)
                rgba_data = np.concatenate([texture_data, alpha], axis=2)
            elif channels == 4:
                rgba_data = texture_data
            else:
                raise ValueError(f"Unsupported channel count: {channels}")

            # Convert to uint8 if needed
            if rgba_data.dtype == np.float32:
                rgba_data = (rgba_data * 255).astype(np.uint8)
            else:
                rgba_data = rgba_data.astype(np.uint8)

            # Ensure contiguous array
            rgba_data = np.ascontiguousarray(rgba_data)

            # Create texture descriptor
            texture_desc = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
                Metal.MTLPixelFormatRGBA8Unorm, width, height, False
            )
            texture_desc.setUsage_(Metal.MTLTextureUsageShaderRead | Metal.MTLTextureUsageShaderWrite)

            # Create the texture
            self._texture = self._device.newTextureWithDescriptor_(texture_desc)

            # Upload data to texture
            region = Metal.MTLRegion(
                Metal.MTLOrigin(0, 0, 0), 
                Metal.MTLSize(width, height, 1)
            )
            self._texture.replaceRegion_mipmapLevel_withBytes_bytesPerRow_(
                region, 0, rgba_data.tobytes(), width * 4
            )

            return True
            
        except Exception as e:
            print(f"⚠️  Metal texture creation failed: {e}")
            return False

    def set_server_name(self, name: str) -> bool:
        """Set the Syphon server name.

        Args:
            name: New server name

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or self._server is None:
            return False

        try:
            # Update server name
            self.name = name

            # Restart server with new name
            return self.resize(self.width, self.height)

        except Exception:
            return False

    def list_clients(self) -> list[dict[str, str]]:
        """List connected Syphon clients.

        Returns:
            List of client info dictionaries
        """
        if not self._initialized or self._syphon is None:
            return []

        try:
            # Get list of Syphon clients from server directory
            directory = self._syphon.SyphonServerDirectory()
            return directory.get_clients() if hasattr(directory, 'get_clients') else []
        except Exception:
            return []

    def list_servers(self) -> list[dict[str, str]]:
        """List available Syphon servers.

        Returns:
            List of server info dictionaries
        """
        if not self._initialized or self._syphon is None:
            return []

        try:
            # Get list of Syphon servers from server directory
            directory = self._syphon.SyphonServerDirectory()
            return directory.get_servers() if hasattr(directory, 'get_servers') else []
        except Exception:
            return []