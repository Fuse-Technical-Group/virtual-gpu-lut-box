"""Virtual GPU LUT Box - Cross-platform LUT streaming for GPU shaders.

A Python package for streaming color correction LUTs from OpenGradeIO to GPU
shaders via Spout (Windows) and Syphon (macOS).

Simple usage:
    import vglb
    vglb.start_server()  # Starts OpenGradeIO server with GPU streaming
"""

__version__ = "0.1.0"
__author__ = "Fuse Technical Group"

# Public API - minimal surface area
from .server import get_platform_info, start_server

# Advanced API - for users who need direct control
from .network import OpenGradeIOServer

__all__ = [
    "start_server",
    "get_platform_info", 
    "OpenGradeIOServer",
]
