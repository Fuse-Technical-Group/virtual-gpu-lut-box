"""High-level server interface for virtual-gpu-lut-box."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    import numpy as np

from .network import OpenGradeIOLUTStreamer, OpenGradeIOServer

logger = logging.getLogger(__name__)


class VirtualGPULUTBoxServer:
    """High-level server that manages both network and GPU streaming components."""
    
    DEFAULT_PORT = OpenGradeIOServer.DEFAULT_PORT
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = DEFAULT_PORT,
        stream_name: str = "OpenGradeIO-LUT",
        verbose: bool = False,
        info_logging: bool = False,
        lut_callback: Callable[[np.ndarray[Any, Any], str | None], None] | None = None,
    ) -> None:
        """Initialize the virtual GPU LUT box server.
        
        Args:
            host: Server host address
            port: Server port number
            stream_name: Base Spout/Syphon stream name
            verbose: Enable verbose (debug) logging
            info_logging: Enable info-level logging
            lut_callback: Optional custom callback for LUT processing (overrides GPU streaming)
        """
        self.host = host
        self.port = port
        self.stream_name = stream_name
        
        # Configure logging based on flags
        if verbose:
            log_level = logging.DEBUG
        elif info_logging:
            log_level = logging.INFO
        else:
            log_level = logging.WARNING  # Quiet mode - only warnings and errors
        
        logging.basicConfig(
            level=log_level, 
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # Essential startup info - always show in quiet mode
        print(f"🚀 Starting OpenGradeIO virtual LUT box server on {host}:{port}")
        
        # Additional info for info/verbose modes
        if info_logging or verbose:
            logger.info(f"Base stream name: {stream_name}")
            logger.info("Channel streams will be named: vglb-lut-{channel}")
        
        # Create LUT streamer (unless custom callback provided)
        self._streamer = None
        if lut_callback is None:
            self._streamer = OpenGradeIOLUTStreamer(stream_name=stream_name)
            lut_callback = self._create_default_lut_callback()
        
        # Create network server
        self._network_server = OpenGradeIOServer(
            host=host,
            port=port,
            lut_callback=lut_callback,
        )
    
    def _create_default_lut_callback(self) -> Callable[[np.ndarray[Any, Any], str | None], None]:
        """Create the default LUT callback that forwards to the streamer."""
        def default_lut_callback(
            lut_data: np.ndarray[Any, Any], channel_name: str | None = None
        ) -> None:
            try:
                if self._streamer:
                    self._streamer.process_lut(lut_data, channel_name)
            except ValueError as e:
                logger.error(f"Invalid LUT data: {e}")
                raise
            except RuntimeError as e:
                logger.error(f"Streaming error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error processing LUT: {e}")
                raise
        
        return default_lut_callback
    
    def start(self) -> None:
        """Start the server."""
        try:
            self._network_server.start()
            # Essential status - always show
            print("✅ OpenGradeIO server started successfully")
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise RuntimeError(f"Failed to start server: {e}") from e
    
    def stop(self) -> None:
        """Stop the server and clean up all resources."""
        self._network_server.stop()
        if self._streamer:
            self._streamer.stop_streaming()
    
    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._network_server.is_running

    @staticmethod
    def get_platform_info() -> dict[str, Any]:
        """Get system and platform information for GPU streaming.
        
        Returns:
            Dictionary with platform information
        """
        from .gpu_texture_stream.factory import StreamingFactory
        
        # Get basic platform info (dict[str, str])
        base_platform_info = StreamingFactory.get_platform_info()
        
        # Create a new dict with proper typing that can hold Any values
        platform_info: dict[str, Any] = dict(base_platform_info)
        
        # Add streaming-specific information
        platform_info.update({
            "current_platform": StreamingFactory.get_current_platform(),
            "available_backends": StreamingFactory.get_available_backends(),
            "platform_supported": StreamingFactory.is_platform_supported(),
        })
        
        if StreamingFactory.is_platform_supported():
            platform_info["supported_formats"] = StreamingFactory.list_supported_formats()
        
        return platform_info