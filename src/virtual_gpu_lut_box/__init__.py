# SPDX-FileCopyrightText: 2025 Fuse Technical Group
#
# SPDX-License-Identifier: BSD-3-Clause

"""Virtual GPU LUT Box - Cross-platform LUT streaming for GPU shaders.

A Python package for streaming color correction LUTs from OpenGradeIO to GPU
shaders via Spout (Windows) and Syphon (macOS).

Simple usage:
    import vglb
    server = vglb.VirtualGPULUTBoxServer()
    server.start()  # Starts OpenGradeIO server with GPU streaming
"""

__version__ = "0.1.0"
__author__ = "Fuse Technical Group"

# Public API - minimal surface area
from .server import VirtualGPULUTBoxServer

__all__ = [
    "VirtualGPULUTBoxServer",
]
