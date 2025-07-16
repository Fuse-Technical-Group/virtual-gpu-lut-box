"""Virtual GPU LUT Box - Cross-platform LUT streaming for GPU shaders.

A Python package for creating and streaming 33x33x33 color correction LUTs
to GPU shaders via Spout (Windows) and Syphon (macOS).
"""

__version__ = "0.1.0"
__author__ = "Virtual GPU LUT Box"
__email__ = "support@example.com"

from .lut.generator import LUTGenerator
from .lut.hald_converter import HaldConverter
from .streaming.factory import StreamingFactory

__all__ = ["LUTGenerator", "HaldConverter", "StreamingFactory"]
