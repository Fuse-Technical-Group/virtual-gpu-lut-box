"""33x33x33 LUT generation for color correction."""

from __future__ import annotations

from typing import Callable

import numpy as np


class LUTGenerator:
    """Generate 33x33x33 color correction LUTs."""

    def __init__(self, size: int = 33) -> None:
        """Initialize LUT generator.

        Args:
            size: Size of the LUT cube (default: 33 for 33x33x33)
        """
        if size < 2:
            raise ValueError("LUT size must be at least 2")
        self.size = size
        self._identity_lut: np.ndarray | None = None

    @property
    def identity_lut(self) -> np.ndarray:
        """Get or create identity LUT.

        Returns:
            Identity LUT as numpy array with shape (size, size, size, 3)
        """
        if self._identity_lut is None:
            self._identity_lut = self._generate_identity_lut()
        return self._identity_lut

    def _generate_identity_lut(self) -> np.ndarray:
        """Generate identity LUT where output equals input.

        Returns:
            Identity LUT as numpy array with shape (size, size, size, 3)
        """
        # Create coordinate grids for R, G, B channels
        r_coords = np.linspace(0.0, 1.0, self.size)
        g_coords = np.linspace(0.0, 1.0, self.size)
        b_coords = np.linspace(0.0, 1.0, self.size)

        # Create 3D meshgrid
        r_grid, g_grid, b_grid = np.meshgrid(
            r_coords, g_coords, b_coords, indexing="ij"
        )

        # Stack into RGBA format (size, size, size, 3)
        lut = np.stack([r_grid, g_grid, b_grid], axis=-1)

        return lut.astype(np.float32)  # type: ignore[no-any-return]

    def apply_transform(
        self, transform_func: Callable[[np.ndarray], np.ndarray]
    ) -> np.ndarray:
        """Apply color transformation function to identity LUT.

        Args:
            transform_func: Function that takes RGB values and returns transformed RGB

        Returns:
            Transformed LUT as numpy array with shape (size, size, size, 3)
        """
        lut = self.identity_lut.copy()

        # Reshape to (size^3, 3) for easier processing
        original_shape = lut.shape
        lut_flat = lut.reshape(-1, 3)

        # Apply transformation
        transformed = transform_func(lut_flat)

        # Reshape back to original
        return transformed.reshape(original_shape).astype(np.float32)

    def apply_gamma(self, gamma: float) -> np.ndarray:
        """Apply gamma correction to identity LUT.

        Args:
            gamma: Gamma value (> 0)

        Returns:
            Gamma-corrected LUT
        """
        if gamma <= 0:
            raise ValueError("Gamma must be positive")

        def gamma_transform(rgb: np.ndarray) -> np.ndarray:
            # Clamp to [0, 1] range and apply gamma
            rgb_clamped = np.clip(rgb, 0.0, 1.0)
            return np.power(rgb_clamped, 1.0 / gamma)

        return self.apply_transform(gamma_transform)

    def apply_brightness_contrast(
        self, brightness: float = 0.0, contrast: float = 1.0
    ) -> np.ndarray:
        """Apply brightness and contrast adjustments.

        Args:
            brightness: Brightness adjustment (-1 to 1)
            contrast: Contrast multiplier (> 0)

        Returns:
            Brightness/contrast adjusted LUT
        """
        if contrast <= 0:
            raise ValueError("Contrast must be positive")

        def brightness_contrast_transform(rgb: np.ndarray) -> np.ndarray:
            # Apply contrast around 0.5 midpoint, then brightness
            adjusted = (rgb - 0.5) * contrast + 0.5 + brightness
            return np.clip(adjusted, 0.0, 1.0)

        return self.apply_transform(brightness_contrast_transform)

    def apply_hue_saturation(
        self, hue_shift: float = 0.0, saturation: float = 1.0
    ) -> np.ndarray:
        """Apply hue and saturation adjustments.

        Args:
            hue_shift: Hue shift in radians (-π to π)
            saturation: Saturation multiplier (>= 0)

        Returns:
            Hue/saturation adjusted LUT
        """
        if saturation < 0:
            raise ValueError("Saturation must be non-negative")

        def hue_saturation_transform(rgb: np.ndarray) -> np.ndarray:
            # Convert RGB to HSV
            hsv = self._rgb_to_hsv(rgb)

            # Apply hue shift
            hsv[:, 0] = (hsv[:, 0] + hue_shift) % (2 * np.pi)

            # Apply saturation
            hsv[:, 1] = np.clip(hsv[:, 1] * saturation, 0.0, 1.0)

            # Convert back to RGB
            return self._hsv_to_rgb(hsv)

        return self.apply_transform(hue_saturation_transform)

    def _rgb_to_hsv(self, rgb: np.ndarray) -> np.ndarray:
        """Convert RGB to HSV color space."""
        r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]

        max_val = np.maximum(np.maximum(r, g), b)
        min_val = np.minimum(np.minimum(r, g), b)
        delta = max_val - min_val

        # Hue calculation
        hue = np.zeros_like(max_val)
        mask = delta > 0

        # Red is max
        red_mask = mask & (max_val == r)
        hue[red_mask] = ((g[red_mask] - b[red_mask]) / delta[red_mask]) % 6

        # Green is max
        green_mask = mask & (max_val == g)
        hue[green_mask] = (b[green_mask] - r[green_mask]) / delta[green_mask] + 2

        # Blue is max
        blue_mask = mask & (max_val == b)
        hue[blue_mask] = (r[blue_mask] - g[blue_mask]) / delta[blue_mask] + 4

        hue = hue * np.pi / 3  # Convert to radians

        # Saturation calculation
        saturation = np.zeros_like(max_val)
        saturation[max_val > 0] = delta[max_val > 0] / max_val[max_val > 0]

        # Value is just max
        value = max_val

        return np.stack([hue, saturation, value], axis=-1)

    def _hsv_to_rgb(self, hsv: np.ndarray) -> np.ndarray:
        """Convert HSV to RGB color space."""
        h, s, v = hsv[:, 0], hsv[:, 1], hsv[:, 2]

        # Convert hue from radians to 0-6 range
        h_deg = (h * 3 / np.pi) % 6

        c = v * s
        x = c * (1 - np.abs((h_deg % 2) - 1))
        m = v - c

        rgb = np.zeros_like(hsv)

        # Different cases based on hue sector
        mask0 = (h_deg >= 0) & (h_deg < 1)
        mask1 = (h_deg >= 1) & (h_deg < 2)
        mask2 = (h_deg >= 2) & (h_deg < 3)
        mask3 = (h_deg >= 3) & (h_deg < 4)
        mask4 = (h_deg >= 4) & (h_deg < 5)
        mask5 = (h_deg >= 5) & (h_deg < 6)

        # Set RGB values for each hue sector
        rgb[mask0, 0] = c[mask0]
        rgb[mask0, 1] = x[mask0]
        rgb[mask0, 2] = 0

        rgb[mask1, 0] = x[mask1]
        rgb[mask1, 1] = c[mask1]
        rgb[mask1, 2] = 0

        rgb[mask2, 0] = 0
        rgb[mask2, 1] = c[mask2]
        rgb[mask2, 2] = x[mask2]

        rgb[mask3, 0] = 0
        rgb[mask3, 1] = x[mask3]
        rgb[mask3, 2] = c[mask3]

        rgb[mask4, 0] = x[mask4]
        rgb[mask4, 1] = 0
        rgb[mask4, 2] = c[mask4]

        rgb[mask5, 0] = c[mask5]
        rgb[mask5, 1] = 0
        rgb[mask5, 2] = x[mask5]

        # Add the m component
        rgb += m[:, np.newaxis]

        return np.clip(rgb, 0.0, 1.0)

    def create_custom_lut(
        self,
        gamma: float = 1.0,
        brightness: float = 0.0,
        contrast: float = 1.0,
        hue_shift: float = 0.0,
        saturation: float = 1.0,
    ) -> np.ndarray:
        """Create custom LUT with multiple adjustments.

        Args:
            gamma: Gamma correction (> 0)
            brightness: Brightness adjustment (-1 to 1)
            contrast: Contrast multiplier (> 0)
            hue_shift: Hue shift in radians (-π to π)
            saturation: Saturation multiplier (>= 0)

        Returns:
            Custom LUT with all adjustments applied
        """
        # Start with identity
        lut = self.identity_lut.copy()

        # Apply gamma first
        if gamma != 1.0:
            lut = self.apply_gamma(gamma)

        # Apply brightness/contrast
        if brightness != 0.0 or contrast != 1.0:

            def bc_transform(rgb: np.ndarray) -> np.ndarray:
                adjusted = (rgb - 0.5) * contrast + 0.5 + brightness
                return np.clip(adjusted, 0.0, 1.0)

            lut = self.apply_transform(bc_transform)

        # Apply hue/saturation
        if hue_shift != 0.0 or saturation != 1.0:

            def hs_transform(rgb: np.ndarray) -> np.ndarray:
                hsv = self._rgb_to_hsv(rgb)
                hsv[:, 0] = (hsv[:, 0] + hue_shift) % (2 * np.pi)
                hsv[:, 1] = np.clip(hsv[:, 1] * saturation, 0.0, 1.0)
                return self._hsv_to_rgb(hsv)

            lut = self.apply_transform(hs_transform)

        return lut
