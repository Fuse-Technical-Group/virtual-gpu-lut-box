"""High-level server interface for virtual-gpu-lut-box."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    import numpy as np

from .gpu_texture_stream.factory import PlatformNotSupportedError
from .network import OpenGradeIOLUTStreamer, OpenGradeIOServer

logger = logging.getLogger(__name__)


def start_server(
    host: str = "127.0.0.1",
    port: int = 8089,
    stream_name: str = "OpenGradeIO-LUT",
    verbose: bool = False,
    info_logging: bool = False,
    blocking: bool = True,
    lut_callback: Callable[[np.ndarray[Any, Any], str | None], None] | None = None,
) -> OpenGradeIOServer:
    """Start OpenGradeIO virtual LUT box server.
    
    Args:
        host: Server host address
        port: Server port number  
        stream_name: Base Spout/Syphon stream name
        verbose: Enable verbose (debug) logging
        info_logging: Enable info-level logging
        blocking: If True, blocks until KeyboardInterrupt. If False, returns server instance.
        lut_callback: Optional custom callback for LUT processing (overrides GPU streaming)
        
    Returns:
        OpenGradeIOServer instance
        
    Raises:
        PlatformNotSupportedError: If GPU streaming not supported on this platform
        RuntimeError: If server cannot be started
    """
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
    streamer = None
    if lut_callback is None:
        streamer = OpenGradeIOLUTStreamer(stream_name=stream_name)
        
        # Create default LUT callback wrapper
        def default_lut_callback(
            lut_data: np.ndarray[Any, Any], channel_name: str | None = None
        ) -> None:
            try:
                streamer.process_lut(lut_data, channel_name)
                # Only show detailed processing info in verbose mode
                if verbose:
                    channel_info = f" for channel '{channel_name}'" if channel_name else ""
                    logger.info(f"Successfully processed {lut_data.shape[0]}³ LUT{channel_info}")
            except ValueError as e:
                logger.error(f"Invalid LUT data: {e}")
                raise
            except RuntimeError as e:
                logger.error(f"Streaming error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error processing LUT: {e}")
                raise
                
        lut_callback = default_lut_callback
    
    # Create and configure server
    server = OpenGradeIOServer(
        host=host,
        port=port, 
        lut_callback=lut_callback,
    )
    
    # Start server
    try:
        server.start()
        # Essential status - always show
        print("✅ OpenGradeIO server started successfully")
        
        if blocking:
            try:
                # Essential status - always show
                print("🔄 Server running. Press Ctrl+C to stop.")
                while server.is_running:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("🛑 Stopping server...")
            finally:
                server.stop()
                if streamer:
                    streamer.stop_streaming()
                print("✅ Server stopped")
                
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise RuntimeError(f"Failed to start server: {e}") from e
    
    return server


def get_platform_info() -> dict[str, Any]:
    """Get system and platform information for GPU streaming.
    
    Returns:
        Dictionary with platform information
    """
    from .gpu_texture_stream.factory import StreamingFactory
    
    platform_info = StreamingFactory.get_platform_info()
    
    # Add streaming-specific information
    platform_info.update({
        "current_platform": StreamingFactory.get_current_platform(),
        "available_backends": StreamingFactory.get_available_backends(),
        "platform_supported": StreamingFactory.is_platform_supported(),
    })
    
    if StreamingFactory.is_platform_supported():
        platform_info["supported_formats"] = StreamingFactory.list_supported_formats()
    
    return platform_info