"""Tests for Hald converter."""

import numpy as np
import pytest

from virtual_gpu_lut_box.lut.hald_converter import HaldConverter


class TestHaldConverter:
    """Test cases for HaldConverter class."""

    def test_init_default_size(self) -> None:
        """Test default initialization."""
        converter = HaldConverter()
        assert converter.lut_size == 33
        assert converter.hald_width == 33 * 33
        assert converter.hald_height == 33

    def test_init_custom_size(self) -> None:
        """Test initialization with custom size."""
        converter = HaldConverter(17)
        assert converter.lut_size == 17
        assert converter.hald_width == 17 * 17
        assert converter.hald_height == 17

    def test_init_invalid_size(self) -> None:
        """Test initialization with invalid size."""
        with pytest.raises(ValueError, match="LUT size must be at least 2"):
            HaldConverter(1)

    def test_lut_to_hald_shape(self) -> None:
        """Test LUT to Hald conversion shape."""
        converter = HaldConverter(5)
        lut = np.random.rand(5, 5, 5, 3).astype(np.float32)
        hald = converter.lut_to_hald(lut)

        assert hald.shape == (5, 25, 4)  # height=5, width=5*5=25, RGBA output
        assert hald.dtype == np.float32

    def test_lut_to_hald_rgba_input_rejected(self) -> None:
        """Test LUT to Hald conversion rejects RGBA input."""
        converter = HaldConverter(5)
        lut = np.random.rand(5, 5, 5, 4).astype(np.float32)

        # Should raise ValueError for RGBA input
        with pytest.raises(
            ValueError, match="LUT must have 3 channels \\(RGB\\), got 4"
        ):
            converter.lut_to_hald(lut)

    def test_lut_to_hald_invalid_shape(self) -> None:
        """Test LUT to Hald conversion with invalid shape."""
        converter = HaldConverter(5)
        lut = np.random.rand(4, 5, 5, 3).astype(np.float32)

        with pytest.raises(ValueError, match="LUT must have spatial shape"):
            converter.lut_to_hald(lut)

    def test_lut_to_hald_invalid_dimensions(self) -> None:
        """Test LUT to Hald conversion with invalid dimensions."""
        converter = HaldConverter(5)
        lut = np.random.rand(5, 5, 3).astype(np.float32)  # Missing one dimension

        with pytest.raises(ValueError, match="LUT must be 4D array"):
            converter.lut_to_hald(lut)

    def test_lut_to_hald_invalid_channels(self) -> None:
        """Test LUT to Hald conversion with invalid channel count."""
        converter = HaldConverter(5)
        lut = np.random.rand(5, 5, 5, 2).astype(np.float32)  # Only 2 channels

        with pytest.raises(
            ValueError, match="LUT must have 3 channels \\(RGB\\), got 2"
        ):
            converter.lut_to_hald(lut)

    def test_lut_to_hald_identity_conversion(self) -> None:
        """Test LUT to Hald conversion with identity LUT."""
        converter = HaldConverter(3)

        # Create test identity LUT manually
        original_lut = np.zeros((3, 3, 3, 3), dtype=np.float32)
        for r in range(3):
            for g in range(3):
                for b in range(3):
                    original_lut[r, g, b, 0] = r / 2.0  # Red channel
                    original_lut[r, g, b, 1] = g / 2.0  # Green channel
                    original_lut[r, g, b, 2] = b / 2.0  # Blue channel

        # Convert to Hald
        hald = converter.lut_to_hald(original_lut)

        # Check dimensions
        assert hald.shape == (3, 9, 4)  # 3 * 3 = 9, RGBA output
        assert hald.dtype == np.float32

    def test_33x33x33_lut_conversion(self) -> None:
        """Test conversion with production-size 33x33x33 LUT."""
        converter = HaldConverter(33)

        # Create a test LUT with gradient values
        lut = np.zeros((33, 33, 33, 3), dtype=np.float32)
        for r in range(33):
            for g in range(33):
                for b in range(33):
                    lut[r, g, b, 0] = r / 32.0  # Red channel
                    lut[r, g, b, 1] = g / 32.0  # Green channel
                    lut[r, g, b, 2] = b / 32.0  # Blue channel

        # Convert to Hald
        hald = converter.lut_to_hald(lut)

        # Check dimensions
        assert hald.shape == (33, 1089, 4)  # 33 * 33 = 1089, RGBA output
        assert hald.dtype == np.float32

    def test_lut_to_hald_preserves_precision(self) -> None:
        """Test that conversion preserves floating point precision."""
        converter = HaldConverter(4)

        # Create LUT with specific values
        lut = np.zeros((4, 4, 4, 3), dtype=np.float32)
        lut[0, 0, 0, :] = [0.1, 0.2, 0.3]
        lut[1, 1, 1, :] = [0.4, 0.5, 0.6]
        lut[2, 2, 2, :] = [0.7, 0.8, 0.9]

        hald = converter.lut_to_hald(lut)

        # Check specific values are preserved (RGB + alpha=1.0)
        assert np.allclose(hald[0, 0, :], [0.1, 0.2, 0.3, 1.0])
        assert np.allclose(hald[1, 5, :], [0.4, 0.5, 0.6, 1.0])  # slice 1, position 1
        assert np.allclose(hald[2, 10, :], [0.7, 0.8, 0.9, 1.0])  # slice 2, position 2

    def test_lut_to_hald_dtype_preservation(self) -> None:
        """Test that conversion preserves data type."""
        converter = HaldConverter(4)

        # Test with float32
        lut_f32 = np.random.rand(4, 4, 4, 3).astype(np.float32)
        hald_f32 = converter.lut_to_hald(lut_f32)
        assert hald_f32.dtype == np.float32

        # Test with float64
        lut_f64 = np.random.rand(4, 4, 4, 3).astype(np.float64)
        hald_f64 = converter.lut_to_hald(lut_f64)
        assert hald_f64.dtype == np.float64
