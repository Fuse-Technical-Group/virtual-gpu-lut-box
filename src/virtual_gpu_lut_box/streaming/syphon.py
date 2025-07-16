"""macOS Syphon streaming backend."""

from __future__ import annotations

import numpy as np
import platform
from typing import Optional, Any

from .base import StreamingBackend, InitializationError

try:
    import OpenGL.GL as gl
    import OpenGL.arrays.vbo as glvbo
    from OpenGL.platform import CurrentContextIsValid
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False

# Try to import context creation libraries
try:
    # Try GLFW first (modern)
    import glfw
    CONTEXT_LIB = 'glfw'
except ImportError:
    try:
        # Fall back to pyglet
        import pyglet
        CONTEXT_LIB = 'pyglet'
    except ImportError:
        CONTEXT_LIB = None


class SyphonBackend(StreamingBackend):
    """macOS Syphon streaming backend."""

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
        self._gl_context: Optional[Any] = None
        self._texture_id: Optional[int] = None

    def is_available(self) -> bool:
        """Check if Syphon is available on this platform.

        Returns:
            True if Syphon is available, False otherwise
        """
        # Check if we're on macOS
        if platform.system() != "Darwin":
            return False

        # Try to import syphonpy and OpenGL
        try:
            import syphonpy
            return OPENGL_AVAILABLE
        except ImportError:
            return False

    def initialize(self) -> bool:
        """Initialize the Syphon server.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        if not self.is_available():
            return False

        try:
            # Import syphonpy
            import syphonpy

            # Store reference to syphon module
            self._syphon = syphonpy

            # Initialize OpenGL context and texture
            if not self._init_opengl():
                return False

            # IMPORTANT: Create Syphon server AFTER OpenGL context is current
            # Make sure context is current
            if self._gl_context and CONTEXT_LIB == 'glfw':
                glfw.make_context_current(self._gl_context)
            
            # Create Syphon server with current OpenGL context
            print(f"🎥 Creating Syphon server with name: '{self.name}'")
            self._server = syphonpy.SyphonServer(self.name)

            if self._server is not None:
                self._initialized = True
                print(f"✅ Syphon server '{self.name}' created successfully")
                return True
            else:
                print(f"❌ Failed to create Syphon server '{self.name}'")
                return False

        except Exception as e:
            raise InitializationError(f"Failed to initialize Syphon: {e}")

    def send_texture(self, texture_data: np.ndarray) -> bool:
        """Send texture data via Syphon.

        Args:
            texture_data: Texture data as numpy array (height, width, 3 or 4)

        Returns:
            True if send successful, False otherwise
            
        Note:
            Current syphonpy implementation requires OpenGL texture IDs.
            This method is a placeholder for future OpenGL integration.
        """
        if not self._initialized or self._server is None:
            return False

        if not self.validate_texture_data(texture_data):
            return False

        try:
            # Ensure OpenGL context is current
            if self._gl_context and CONTEXT_LIB == 'glfw':
                glfw.make_context_current(self._gl_context)
            
            # Upload numpy array to OpenGL texture
            if not self._upload_texture_data(texture_data):
                return False

            # Create rect and size for Syphon
            rect = self._syphon.MakeRect(0, 0, self.width, self.height)
            size = self._syphon.MakeSize(self.width, self.height)

            # CRITICAL: Unbind texture so Syphon can access it
            # Texture must be unbound for sharing to work
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            
            # Flush OpenGL commands to ensure texture upload is complete
            gl.glFlush()
            
            # Stream via Syphon using OpenGL texture ID exactly like tester.py
            # Texture must be unbound for Syphon to access it  
            self._server.publish_frame_texture(self._texture_id, rect, size, False)
            
            # Force OpenGL synchronization to ensure Syphon can read texture
            gl.glFinish()
            
            # Log first frame only
            if not hasattr(self, '_first_frame_logged'):
                print(f"📺 Started streaming to Syphon server '{self.name}'")
                self._first_frame_logged = True
            
            return True

        except Exception as e:
            print(f"⚠️  Syphon streaming error: {e}")
            return False

    def _prepare_syphon_data(self, texture_data: np.ndarray) -> np.ndarray:
        """Prepare texture data for Syphon.

        Args:
            texture_data: Input texture data

        Returns:
            Texture data formatted for Syphon
        """
        height, width, channels = texture_data.shape

        # Convert to uint8 if needed
        if texture_data.dtype == np.float32:
            data = (texture_data * 255).astype(np.uint8)
        else:
            data = texture_data.astype(np.uint8)

        # Syphon typically expects RGBA format
        if channels == 3:
            # Add alpha channel
            alpha = np.full((height, width, 1), 255, dtype=np.uint8)
            data = np.concatenate([data, alpha], axis=2)
        elif channels == 4:
            # Already RGBA
            pass
        else:
            raise ValueError(f"Unsupported channel count: {channels}")

        # Ensure contiguous array
        data = np.ascontiguousarray(data)

        return data

    def _prepare_syphon_data_rgb(self, texture_data: np.ndarray) -> np.ndarray:
        """Prepare texture data for Syphon using RGB format like tester.py.

        Args:
            texture_data: Input texture data

        Returns:
            Texture data formatted as RGB for Syphon (like tester.py)
        """
        height, width, channels = texture_data.shape

        # Convert to uint8 if needed
        if texture_data.dtype == np.float32:
            data = (texture_data * 255).astype(np.uint8)
        else:
            data = texture_data.astype(np.uint8)

        # Convert to RGB only (no alpha) like tester.py
        if channels == 3:
            # Already RGB
            rgb_data = data
        elif channels == 4:
            # Remove alpha channel
            rgb_data = data[:, :, :3]
        else:
            raise ValueError(f"Unsupported channel count: {channels}")

        # Ensure contiguous array
        rgb_data = np.ascontiguousarray(rgb_data)

        return rgb_data

    def cleanup(self) -> None:
        """Clean up Syphon and OpenGL resources."""
        if self._server is not None:
            print(f"🛑 Stopping Syphon server '{self.name}'")
            try:
                self._server.stop()
                print(f"✅ Syphon server '{self.name}' stopped successfully")
            except Exception as e:
                print(f"⚠️  Error stopping Syphon server '{self.name}': {e}")
            self._server = None

        # Clean up OpenGL texture
        if self._texture_id is not None and OPENGL_AVAILABLE:
            try:
                gl.glDeleteTextures([self._texture_id])
            except Exception:
                pass  # Ignore cleanup errors
            self._texture_id = None

        # Clean up OpenGL context
        if self._gl_context is not None:
            try:
                if CONTEXT_LIB == 'glfw':
                    glfw.destroy_window(self._gl_context)
                    glfw.terminate()
                elif CONTEXT_LIB == 'pyglet':
                    self._gl_context.close()
            except Exception:
                pass  # Ignore cleanup errors
            self._gl_context = None
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
            "backend": "Syphon",
        }

        if self._initialized and self._server is not None:
            try:
                # Get additional info from Syphon if available
                info.update(
                    {
                        "server_active": True,
                        "supported_formats": self.get_supported_formats(),
                    }
                )
            except Exception:
                pass

        return info

    def list_clients(self) -> list[dict[str, str]]:
        """List connected Syphon clients.

        Returns:
            List of client info dictionaries
        """
        if not self._initialized or self._syphon is None:
            return []

        try:
            # Get list of Syphon clients
            clients = self._syphon.SyphonServerDirectory.get_clients()
            return clients if clients else []
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
            # Get list of Syphon servers
            servers = self._syphon.SyphonServerDirectory.get_servers()
            return servers if servers else []
        except Exception:
            return []

    def is_client_connected(self) -> bool:
        """Check if any clients are connected.

        Returns:
            True if clients are connected, False otherwise
        """
        if not self._initialized or self._server is None:
            return False

        try:
            # Check if there are active clients
            clients = self.list_clients()
            return len(clients) > 0
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

        # Convert to RGBA format for Syphon
        rgba_data = self.convert_texture_format(hald_image, "rgba")

        # Send texture
        return self.send_texture(rgba_data)

    def get_metal_device_info(self) -> dict[str, str]:
        """Get Metal device information (macOS specific).

        Returns:
            Dictionary with Metal device info
        """
        info = {}

        if self._initialized:
            try:
                # Get Metal device info if available
                info.update(
                    {
                        "device_name": "Unknown Metal Device",
                        "device_description": "macOS Metal Graphics Device",
                    }
                )
            except Exception:
                pass

        return info

    def get_opengl_info(self) -> dict[str, str]:
        """Get OpenGL information.

        Returns:
            Dictionary with OpenGL info
        """
        info = {}

        if self._initialized:
            try:
                # Get OpenGL info if available
                info.update(
                    {
                        "renderer": "Unknown OpenGL Renderer",
                        "version": "Unknown OpenGL Version",
                        "vendor": "Unknown Vendor",
                    }
                )
            except Exception:
                pass

        return info

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
        }

    def _init_opengl(self) -> bool:
        """Initialize OpenGL context and create texture.
        
        Returns:
            True if successful, False otherwise
        """
        if not OPENGL_AVAILABLE or CONTEXT_LIB is None:
            return False

        try:
            # Create OpenGL context if needed
            if not self._create_gl_context():
                return False

            # Create OpenGL texture
            self._texture_id = gl.glGenTextures(1)
            
            # Bind and configure texture exactly like tester.py
            gl.glBindTexture(gl.GL_TEXTURE_2D, self._texture_id)
            gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
            gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
            gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR)
            
            # NOTE: Don't pre-initialize texture - let gluBuild2DMipmaps handle it
            # This matches the syphonpy tester.py approach
            
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            
            return True
            
        except Exception as e:
            print(f"⚠️  OpenGL initialization failed: {e}")
            return False

    def _create_gl_context(self) -> bool:
        """Create OpenGL context for headless rendering.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if we already have a valid context
            if CurrentContextIsValid():
                return True

            if CONTEXT_LIB == 'glfw':
                # Initialize GLFW
                if not glfw.init():
                    return False
                
                # Create invisible window for context
                glfw.window_hint(glfw.VISIBLE, False)
                glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
                glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
                
                self._gl_context = glfw.create_window(1, 1, "Syphon Context", None, None)
                if not self._gl_context:
                    glfw.terminate()
                    return False
                
                glfw.make_context_current(self._gl_context)
                return True
                
            elif CONTEXT_LIB == 'pyglet':
                # Create headless context with pyglet
                config = pyglet.gl.Config(double_buffer=False)
                self._gl_context = pyglet.window.Window(
                    width=1, height=1, visible=False, config=config
                )
                self._gl_context.switch_to()
                return True
                
            return False
            
        except Exception as e:
            print(f"⚠️  OpenGL context creation failed: {e}")
            return False

    def _upload_texture_data(self, texture_data: np.ndarray) -> bool:
        """Upload numpy array to OpenGL texture.
        
        Args:
            texture_data: Texture data as numpy array
            
        Returns:
            True if successful, False otherwise
        """
        if not OPENGL_AVAILABLE or self._texture_id is None:
            return False

        try:
            # Convert to format expected by OpenGL (RGB only, like tester.py)
            gl_data = self._prepare_syphon_data_rgb(texture_data)
            
            # Set proper pixel unpacking parameters
            gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
            
            # Bind texture and upload using gluBuild2DMipmaps like tester.py
            gl.glBindTexture(gl.GL_TEXTURE_2D, self._texture_id)
            
            # Use gluBuild2DMipmaps exactly like the syphonpy tester
            from OpenGL.GLU import gluBuild2DMipmaps
            gluBuild2DMipmaps(
                gl.GL_TEXTURE_2D, gl.GL_RGB, 
                self.width, self.height, 
                gl.GL_RGB, gl.GL_UNSIGNED_BYTE, gl_data
            )
            # NOTE: Keep texture bound for Syphon - unbinding happens in send_texture()
            
            # Check for OpenGL errors
            error = gl.glGetError()
            if error != gl.GL_NO_ERROR:
                print(f"OpenGL error in texture upload: {error}")
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️  Texture upload failed: {e}")
            return False
