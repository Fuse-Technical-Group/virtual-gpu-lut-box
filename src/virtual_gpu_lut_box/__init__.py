"""Virtual GPU LUT Box - Cross-platform LUT streaming for GPU shaders.

A Python package for creating and streaming 33x33x33 color correction LUTs
to GPU shaders via Spout (Windows) and Syphon (macOS).
"""

__version__ = "0.1.0"
__author__ = "Fuse Technical Group"

from .gpu_texture_stream.factory import StreamingFactory
from .lut.hald_converter import HaldConverter
from .network import OpenGradeIOLUTStreamer, OpenGradeIOServer

__all__ = [
    "HaldConverter",
    "StreamingFactory",
    "OpenGradeIOServer",
    "OpenGradeIOLUTStreamer",
]
