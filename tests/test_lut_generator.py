"""Tests for LUT generator."""

import numpy as np
import pytest

from virtual_gpu_lut_box.lut.generator import LUTGenerator


class TestLUTGenerator:
    """Test cases for LUTGenerator class."""

    def test_init_default_size(self) -> None:
        """Test default initialization."""
        generator = LUTGenerator()
        assert generator.size == 33

    def test_init_custom_size(self) -> None:
        """Test initialization with custom size."""
        generator = LUTGenerator(17)
        assert generator.size == 17

    def test_init_invalid_size(self) -> None:
        """Test initialization with invalid size."""
        with pytest.raises(ValueError, match="LUT size must be at least 2"):
            LUTGenerator(1)

    def test_identity_lut_shape(self) -> None:
        """Test identity LUT has correct shape."""
        generator = LUTGenerator(33)
        lut = generator.identity_lut
        assert lut.shape == (33, 33, 33, 3)

    def test_identity_lut_values(self) -> None:
        """Test identity LUT values are correct."""
        generator = LUTGenerator(3)
        lut = generator.identity_lut

        # Check corner values
        assert np.allclose(lut[0, 0, 0], [0.0, 0.0, 0.0])
        assert np.allclose(lut[2, 2, 2], [1.0, 1.0, 1.0])
        assert np.allclose(lut[1, 1, 1], [0.5, 0.5, 0.5])

    def test_identity_lut_caching(self) -> None:
        """Test identity LUT is cached."""
        generator = LUTGenerator(33)
        lut1 = generator.identity_lut
        lut2 = generator.identity_lut
        assert lut1 is lut2

    def test_identity_lut_dtype(self) -> None:
        """Test identity LUT has correct data type."""
        generator = LUTGenerator(33)
        lut = generator.identity_lut
        assert lut.dtype == np.float32

    def test_apply_gamma_normal(self) -> None:
        """Test gamma correction with normal values."""
        generator = LUTGenerator(3)
        lut = generator.apply_gamma(2.2)

        # Check that gamma is applied correctly
        expected = np.power(0.5, 1.0 / 2.2)
        assert np.allclose(lut[1, 1, 1], [expected, expected, expected])

    def test_apply_gamma_invalid(self) -> None:
        """Test gamma correction with invalid values."""
        generator = LUTGenerator(3)
        with pytest.raises(ValueError, match="Gamma must be positive"):
            generator.apply_gamma(0)
        with pytest.raises(ValueError, match="Gamma must be positive"):
            generator.apply_gamma(-1)

    def test_apply_brightness_contrast(self) -> None:
        """Test brightness and contrast adjustment."""
        generator = LUTGenerator(3)
        lut = generator.apply_brightness_contrast(brightness=0.1, contrast=1.2)

        # Check that adjustments are applied
        # Midpoint (0.5) should become (0.5 - 0.5) * 1.2 + 0.5 + 0.1 = 0.6
        assert np.allclose(lut[1, 1, 1], [0.6, 0.6, 0.6])

    def test_apply_brightness_contrast_invalid(self) -> None:
        """Test brightness and contrast with invalid values."""
        generator = LUTGenerator(3)
        with pytest.raises(ValueError, match="Contrast must be positive"):
            generator.apply_brightness_contrast(contrast=0)

    def test_apply_hue_saturation(self) -> None:
        """Test hue and saturation adjustment."""
        generator = LUTGenerator(3)
        # Test with small adjustments
        lut = generator.apply_hue_saturation(hue_shift=0.1, saturation=1.2)

        # Check that result is valid
        assert lut.shape == (3, 3, 3, 3)
        assert np.all(lut >= 0)
        assert np.all(lut <= 1)

    def test_apply_hue_saturation_invalid(self) -> None:
        """Test hue and saturation with invalid values."""
        generator = LUTGenerator(3)
        with pytest.raises(ValueError, match="Saturation must be non-negative"):
            generator.apply_hue_saturation(saturation=-1)

    def test_rgb_to_hsv_conversion(self) -> None:
        """Test RGB to HSV conversion."""
        generator = LUTGenerator(3)

        # Test with known values
        rgb = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        hsv = generator._rgb_to_hsv(rgb)

        # Check shapes
        assert hsv.shape == (3, 3)

        # Check value channel (should be 1.0 for pure colors)
        assert np.allclose(hsv[:, 2], [1.0, 1.0, 1.0])

    def test_hsv_to_rgb_conversion(self) -> None:
        """Test HSV to RGB conversion."""
        generator = LUTGenerator(3)

        # Test round trip conversion
        rgb_original = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        hsv = generator._rgb_to_hsv(rgb_original)
        rgb_converted = generator._hsv_to_rgb(hsv)

        assert np.allclose(rgb_original, rgb_converted, atol=1e-6)

    def test_create_custom_lut(self) -> None:
        """Test creating custom LUT with all parameters."""
        generator = LUTGenerator(5)
        lut = generator.create_custom_lut(
            gamma=2.2, brightness=0.1, contrast=1.1, hue_shift=0.1, saturation=1.2
        )

        # Check shape and validity
        assert lut.shape == (5, 5, 5, 3)
        assert np.all(lut >= 0)
        assert np.all(lut <= 1)
        assert lut.dtype == np.float32

    def test_create_custom_lut_identity(self) -> None:
        """Test creating custom LUT with identity parameters."""
        generator = LUTGenerator(3)
        lut = generator.create_custom_lut()

        # Should be identical to identity LUT
        identity = generator.identity_lut
        assert np.allclose(lut, identity)

    def test_apply_transform_custom(self) -> None:
        """Test applying custom transform function."""
        generator = LUTGenerator(3)

        def invert_transform(rgb: np.ndarray) -> np.ndarray:
            return 1.0 - rgb

        lut = generator.apply_transform(invert_transform)

        # Check that corners are inverted
        assert np.allclose(lut[0, 0, 0], [1.0, 1.0, 1.0])
        assert np.allclose(lut[2, 2, 2], [0.0, 0.0, 0.0])

    def test_lut_value_range(self) -> None:
        """Test that LUT values are always in valid range."""
        generator = LUTGenerator(5)

        # Test with extreme parameters
        lut = generator.create_custom_lut(
            gamma=0.1, brightness=0.5, contrast=2.0, hue_shift=np.pi, saturation=2.0
        )

        # Values should be clamped to [0, 1]
        assert np.all(lut >= 0)
        assert np.all(lut <= 1)

    def test_different_sizes(self) -> None:
        """Test LUT generation with different sizes."""
        sizes = [3, 5, 17, 33, 65]

        for size in sizes:
            generator = LUTGenerator(size)
            lut = generator.identity_lut

            assert lut.shape == (size, size, size, 3)
            assert lut.dtype == np.float32
            assert np.all(lut >= 0)
            assert np.all(lut <= 1)

    def test_generator_consistency(self) -> None:
        """Test that multiple generators produce consistent results."""
        gen1 = LUTGenerator(17)
        gen2 = LUTGenerator(17)

        lut1 = gen1.apply_gamma(2.2)
        lut2 = gen2.apply_gamma(2.2)

        assert np.allclose(lut1, lut2)
