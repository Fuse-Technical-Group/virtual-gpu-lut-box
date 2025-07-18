"""Convert 3D LUT to 2D Hald image format for GPU textures."""

from __future__ import annotations

import numpy as np


class HaldConverter:
    """Convert 3D LUT to 2D Hald image format optimized for GPU shaders."""

    def __init__(self, lut_size: int = 33) -> None:
        """Initialize Hald converter.

        Args:
            lut_size: Size of the 3D LUT cube (default: 33)
        """
        if lut_size < 2:
            raise ValueError("LUT size must be at least 2")
        self.lut_size = lut_size
        self.hald_width = lut_size * lut_size
        self.hald_height = lut_size

    def lut_to_hald(self, lut: np.ndarray) -> np.ndarray:
        """Convert 3D LUT to 2D Hald image format.

        For a 33x33x33 LUT, creates a 1089x33 pixel image where:
        - Width = 33 * 33 = 1089 pixels (33 slices of 33 pixels each)
        - Height = 33 pixels
        - Each slice represents a different blue channel value

        Args:
            lut: 3D LUT array with shape (size, size, size, 3) - RGB only

        Returns:
            2D Hald image array with shape (height, width, 4) - RGBA with alpha=1.0
        """
        # Validate LUT dimensions
        if len(lut.shape) != 4:
            raise ValueError(f"LUT must be 4D array, got shape {lut.shape}")

        if lut.shape[:3] != (self.lut_size, self.lut_size, self.lut_size):
            raise ValueError(
                f"LUT must have spatial shape ({self.lut_size}, {self.lut_size}, {self.lut_size}), "
                f"got {lut.shape[:3]}"
            )

        channels = lut.shape[3]
        if channels != 3:
            raise ValueError(f"LUT must have 3 channels (RGB), got {channels}")

        # Initialize Hald image with RGBA format (always 4 channels)
        hald = np.zeros((self.hald_height, self.hald_width, 4), dtype=lut.dtype)

        # Convert each blue slice to a horizontal strip
        for b in range(self.lut_size):
            # Extract the slice at blue index b
            slice_data = lut[:, :, b, :]  # Shape: (size, size, 3) - RGB

            # Calculate position in Hald image
            start_x = b * self.lut_size
            end_x = start_x + self.lut_size

            # Place RGB data in Hald image
            # Note: LUT indexing is [R, G, B] but image indexing is [Y, X]
            hald[:, start_x:end_x, :3] = slice_data

            # Set alpha channel to 1.0 (fully opaque)
            hald[:, start_x:end_x, 3] = 1.0

        return hald
