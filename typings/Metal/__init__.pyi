"""Type stubs for Metal framework via PyObjC.

This stub file provides type information for the Metal APIs used in this project.
The PyObjC Metal framework loads its APIs dynamically, so static type checkers
need these explicit declarations.
"""

from typing import Any, Optional, Protocol

class MTLDevice(Protocol):
    def name(self) -> str: ...
    def hasUnifiedMemory(self) -> bool: ...
    def newCommandQueue(self) -> Optional[MTLCommandQueue]: ...
    def newTextureWithDescriptor_(self, descriptor: MTLTextureDescriptor) -> Optional[MTLTexture]: ...

class MTLCommandQueue(Protocol):
    pass

class MTLTexture(Protocol):
    def replaceRegion_mipmapLevel_withBytes_bytesPerRow_(
        self, 
        region: MTLRegion, 
        mipmap_level: int, 
        bytes_data: bytes, 
        bytes_per_row: int
    ) -> None: ...

class MTLTextureDescriptor(Protocol):
    @classmethod
    def texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
        cls, 
        pixel_format: int, 
        width: int, 
        height: int, 
        mipmapped: bool
    ) -> MTLTextureDescriptor: ...
    
    def setUsage_(self, usage: int) -> None: ...

class MTLRegion:
    def __init__(self, origin: MTLOrigin, size: MTLSize) -> None: ...

class MTLOrigin:
    def __init__(self, x: int, y: int, z: int) -> None: ...

class MTLSize:
    def __init__(self, width: int, height: int, depth: int) -> None: ...

# Constants - these are loaded dynamically by PyObjC but we provide types here
MTLPixelFormatRGBA8Unorm: int
MTLPixelFormatRGBA32Float: int
# RGB-only formats for efficiency (no alpha channel)
MTLPixelFormatRG11B10Float: int  # 32-bit RGB float format
MTLPixelFormatRGB9E5Float: int   # 32-bit RGB shared exponent format
MTLTextureUsageShaderRead: int
MTLTextureUsageShaderWrite: int

# Functions
def MTLCreateSystemDefaultDevice() -> Optional[MTLDevice]: ...

# Export all the types that might be used
__all__ = [
    'MTLDevice',
    'MTLCommandQueue', 
    'MTLTexture',
    'MTLTextureDescriptor',
    'MTLRegion',
    'MTLOrigin',
    'MTLSize',
    'MTLPixelFormatRGBA8Unorm',
    'MTLPixelFormatRGBA32Float',
    'MTLPixelFormatRG11B10Float',
    'MTLPixelFormatRGB9E5Float',
    'MTLTextureUsageShaderRead',
    'MTLTextureUsageShaderWrite',
    'MTLCreateSystemDefaultDevice',
]