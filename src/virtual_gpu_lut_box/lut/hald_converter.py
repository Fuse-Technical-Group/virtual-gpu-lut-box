"""Convert 3D LUT to 2D Hald image format for GPU textures."""

from __future__ import annotations

import numpy as np
from PIL import Image


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
            lut: 3D LUT array with shape (size, size, size, 3)

        Returns:
            2D Hald image array with shape (height, width, 3)
        """
        if lut.shape != (self.lut_size, self.lut_size, self.lut_size, 3):
            raise ValueError(
                f"LUT must have shape ({self.lut_size}, {self.lut_size}, {self.lut_size}, 3)"
            )

        # Initialize Hald image
        hald = np.zeros((self.hald_height, self.hald_width, 3), dtype=np.float32)

        # Convert each blue slice to a horizontal strip
        for b in range(self.lut_size):
            # Extract the slice at blue index b
            slice_data = lut[:, :, b, :]  # Shape: (size, size, 3)

            # Calculate position in Hald image
            start_x = b * self.lut_size
            end_x = start_x + self.lut_size

            # Place slice in Hald image
            # Note: LUT indexing is [R, G, B] but image indexing is [Y, X]
            # We need to transpose to get correct orientation
            hald[:, start_x:end_x, :] = slice_data

        return hald

    def hald_to_lut(self, hald: np.ndarray) -> np.ndarray:
        """Convert 2D Hald image back to 3D LUT format.

        Args:
            hald: 2D Hald image array with shape (height, width, 3)

        Returns:
            3D LUT array with shape (size, size, size, 3)
        """
        if hald.shape != (self.hald_height, self.hald_width, 3):
            raise ValueError(
                f"Hald image must have shape ({self.hald_height}, {self.hald_width}, 3)"
            )

        # Initialize LUT
        lut = np.zeros(
            (self.lut_size, self.lut_size, self.lut_size, 3), dtype=np.float32
        )

        # Extract each slice from Hald image
        for b in range(self.lut_size):
            # Calculate position in Hald image
            start_x = b * self.lut_size
            end_x = start_x + self.lut_size

            # Extract slice and place in LUT
            slice_data = hald[:, start_x:end_x, :]
            lut[:, :, b, :] = slice_data

        return lut

    def save_hald_image(self, hald: np.ndarray, filepath: str) -> None:
        """Save Hald image to file.

        Args:
            hald: 2D Hald image array with shape (height, width, 3)
            filepath: Output file path
        """
        # Convert to 8-bit and ensure proper range
        hald_8bit = np.clip(hald * 255, 0, 255).astype(np.uint8)

        # Create PIL image and save
        image = Image.fromarray(hald_8bit, mode="RGB")
        image.save(filepath)

    def load_hald_image(self, filepath: str) -> np.ndarray:
        """Load Hald image from file.

        Args:
            filepath: Input file path

        Returns:
            2D Hald image array with shape (height, width, 3)
        """
        # Load image
        image = Image.open(filepath)

        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")  # type: ignore[assignment]

        # Resize if needed
        if image.size != (self.hald_width, self.hald_height):
            image = image.resize(  # type: ignore[assignment]
                (self.hald_width, self.hald_height), Image.Resampling.LANCZOS
            )

        # Convert to numpy array and normalize to [0, 1]
        hald_array = np.array(image, dtype=np.float32) / 255.0

        return hald_array

    def create_gpu_texture_coords(self) -> tuple[np.ndarray, np.ndarray]:
        """Create texture coordinates for GPU shader sampling.

        Returns proper texture coordinates with 0.5 offset for accurate sampling.

        Returns:
            tuple: (u_coords, v_coords) arrays for texture sampling
        """
        # Create U coordinates (0.5 offset for texel centers)
        u_coords = np.linspace(
            0.5 / self.hald_width, 1.0 - 0.5 / self.hald_width, self.hald_width
        )

        # Create V coordinates (0.5 offset for texel centers)
        v_coords = np.linspace(
            0.5 / self.hald_height, 1.0 - 0.5 / self.hald_height, self.hald_height
        )

        return u_coords, v_coords

    def get_slice_boundaries(self) -> list[tuple[float, float]]:
        """Get slice boundaries for proper GPU interpolation.

        Returns slice boundaries to prevent interpolation across slice edges.

        Returns:
            List of (start_u, end_u) tuples for each slice
        """
        boundaries = []
        for b in range(self.lut_size):
            start_u = b * self.lut_size / self.hald_width
            end_u = (b + 1) * self.lut_size / self.hald_width
            boundaries.append((start_u, end_u))
        return boundaries

    def validate_hald_image(self, hald: np.ndarray) -> bool:
        """Validate that Hald image has correct dimensions and format.

        Args:
            hald: 2D Hald image array to validate

        Returns:
            True if valid, False otherwise
        """
        # Check dimensions
        if hald.shape != (self.hald_height, self.hald_width, 3):
            return False

        # Check data type
        if hald.dtype != np.float32:
            return False

        # Check value range
        return not (np.any(hald < 0) or np.any(hald > 1))

    def create_identity_hald(self) -> np.ndarray:
        """Create identity Hald image for testing.

        Returns:
            Identity Hald image where output equals input
        """
        # Create identity LUT first
        from .generator import LUTGenerator

        generator = LUTGenerator(self.lut_size)
        identity_lut = generator.identity_lut

        # Convert to Hald format
        return self.lut_to_hald(identity_lut)

    def get_shader_sampling_info(self) -> dict[str, float]:
        """Get information needed for GPU shader sampling.

        Returns:
            Dictionary with shader constants for proper LUT sampling
        """
        return {
            "lut_size": float(self.lut_size),
            "hald_width": float(self.hald_width),
            "hald_height": float(self.hald_height),
            "texel_width": 1.0 / self.hald_width,
            "texel_height": 1.0 / self.hald_height,
            "slice_width": 1.0 / self.lut_size,
            "uv_offset": 0.5,  # For texel center sampling
        }

    def convert_lut_to_texture_data(
        self, lut: np.ndarray, format: str = "rgba"
    ) -> np.ndarray:
        """Convert LUT to texture data format for GPU upload.

        Args:
            lut: 3D LUT array with shape (size, size, size, 3)
            format: Output format ('rgb', 'rgba', 'bgr', 'bgra')

        Returns:
            Texture data ready for GPU upload
        """
        # Convert to Hald format
        hald = self.lut_to_hald(lut)

        # Handle different formats
        if format.lower() == "rgb":
            return hald
        elif format.lower() == "rgba":
            # Add alpha channel
            alpha = np.ones((hald.shape[0], hald.shape[1], 1), dtype=hald.dtype)
            return np.concatenate([hald, alpha], axis=2)
        elif format.lower() == "bgr":
            # Swap R and B channels
            return hald[:, :, [2, 1, 0]]
        elif format.lower() == "bgra":
            # Swap R and B channels and add alpha
            bgr = hald[:, :, [2, 1, 0]]
            alpha = np.ones((bgr.shape[0], bgr.shape[1], 1), dtype=bgr.dtype)
            return np.concatenate([bgr, alpha], axis=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_optimal_texture_size(self) -> tuple[int, int]:
        """Get optimal texture size for GPU efficiency.

        Returns:
            tuple: (width, height) for optimal GPU texture size
        """
        # For 33x33x33 LUT: 1089x33 is the natural size
        # Check if we need to pad to power of 2 for older GPUs
        width = self.hald_width
        height = self.hald_height

        # Most modern GPUs support non-power-of-2 textures
        # But we could add padding logic here if needed

        return width, height
