"""Tests for Hald converter."""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from virtual_gpu_lut_box.lut.generator import LUTGenerator
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

        assert hald.shape == (5, 25, 3)  # height=5, width=5*5=25
        assert hald.dtype == np.float32

    def test_lut_to_hald_invalid_shape(self) -> None:
        """Test LUT to Hald conversion with invalid shape."""
        converter = HaldConverter(5)
        lut = np.random.rand(4, 5, 5, 3).astype(np.float32)

        with pytest.raises(ValueError, match="LUT must have shape"):
            converter.lut_to_hald(lut)

    def test_hald_to_lut_shape(self) -> None:
        """Test Hald to LUT conversion shape."""
        converter = HaldConverter(5)
        hald = np.random.rand(5, 25, 3).astype(np.float32)
        lut = converter.hald_to_lut(hald)

        assert lut.shape == (5, 5, 5, 3)
        assert lut.dtype == np.float32

    def test_hald_to_lut_invalid_shape(self) -> None:
        """Test Hald to LUT conversion with invalid shape."""
        converter = HaldConverter(5)
        hald = np.random.rand(4, 25, 3).astype(np.float32)

        with pytest.raises(ValueError, match="Hald image must have shape"):
            converter.hald_to_lut(hald)

    def test_roundtrip_conversion(self) -> None:
        """Test LUT to Hald and back conversion."""
        converter = HaldConverter(3)

        # Create test LUT
        generator = LUTGenerator(3)
        original_lut = generator.identity_lut

        # Convert to Hald and back
        hald = converter.lut_to_hald(original_lut)
        recovered_lut = converter.hald_to_lut(hald)

        # Should be identical
        assert np.allclose(original_lut, recovered_lut)

    def test_identity_hald_creation(self) -> None:
        """Test creating identity Hald image."""
        converter = HaldConverter(5)
        hald = converter.create_identity_hald()

        assert hald.shape == (5, 25, 3)
        assert hald.dtype == np.float32
        assert np.all(hald >= 0)
        assert np.all(hald <= 1)

    def test_validate_hald_image_valid(self) -> None:
        """Test validation of valid Hald image."""
        converter = HaldConverter(5)
        hald = np.random.rand(5, 25, 3).astype(np.float32)

        assert converter.validate_hald_image(hald) is True

    def test_validate_hald_image_invalid_shape(self) -> None:
        """Test validation of invalid Hald image shape."""
        converter = HaldConverter(5)
        hald = np.random.rand(4, 25, 3).astype(np.float32)

        assert converter.validate_hald_image(hald) is False

    def test_validate_hald_image_invalid_dtype(self) -> None:
        """Test validation of invalid Hald image dtype."""
        converter = HaldConverter(5)
        hald = np.random.rand(5, 25, 3).astype(np.uint8)

        assert converter.validate_hald_image(hald) is False

    def test_validate_hald_image_invalid_range(self) -> None:
        """Test validation of invalid Hald image value range."""
        converter = HaldConverter(5)
        hald = np.random.rand(5, 25, 3).astype(np.float32)
        hald[0, 0, 0] = -0.1  # Invalid negative value

        assert converter.validate_hald_image(hald) is False

    def test_create_gpu_texture_coords(self) -> None:
        """Test GPU texture coordinate creation."""
        converter = HaldConverter(3)
        u_coords, v_coords = converter.create_gpu_texture_coords()

        assert len(u_coords) == 9  # 3 * 3
        assert len(v_coords) == 3

        # Check that coordinates are properly offset
        assert u_coords[0] == 0.5 / 9
        assert u_coords[-1] == 1.0 - 0.5 / 9
        assert v_coords[0] == 0.5 / 3
        assert v_coords[-1] == 1.0 - 0.5 / 3

    def test_get_slice_boundaries(self) -> None:
        """Test slice boundary calculation."""
        converter = HaldConverter(3)
        boundaries = converter.get_slice_boundaries()

        assert len(boundaries) == 3
        assert boundaries[0] == (0.0, 1.0 / 3)
        assert boundaries[1] == (1.0 / 3, 2.0 / 3)
        assert boundaries[2] == (2.0 / 3, 1.0)

    def test_get_shader_sampling_info(self) -> None:
        """Test shader sampling info generation."""
        converter = HaldConverter(5)
        info = converter.get_shader_sampling_info()

        expected_keys = [
            "lut_size",
            "hald_width",
            "hald_height",
            "texel_width",
            "texel_height",
            "slice_width",
            "uv_offset",
        ]

        for key in expected_keys:
            assert key in info

        assert info["lut_size"] == 5.0
        assert info["hald_width"] == 25.0
        assert info["hald_height"] == 5.0

    def test_convert_lut_to_texture_data_rgb(self) -> None:
        """Test LUT to texture data conversion (RGB)."""
        converter = HaldConverter(3)
        lut = np.random.rand(3, 3, 3, 3).astype(np.float32)

        texture_data = converter.convert_lut_to_texture_data(lut, "rgb")

        assert texture_data.shape == (3, 9, 3)
        assert texture_data.dtype == np.float32

    def test_convert_lut_to_texture_data_rgba(self) -> None:
        """Test LUT to texture data conversion (RGBA)."""
        converter = HaldConverter(3)
        lut = np.random.rand(3, 3, 3, 3).astype(np.float32)

        texture_data = converter.convert_lut_to_texture_data(lut, "rgba")

        assert texture_data.shape == (3, 9, 4)
        assert texture_data.dtype == np.float32
        # Check alpha channel is 1.0
        assert np.all(texture_data[:, :, 3] == 1.0)

    def test_convert_lut_to_texture_data_bgr(self) -> None:
        """Test LUT to texture data conversion (BGR)."""
        converter = HaldConverter(3)
        lut = np.random.rand(3, 3, 3, 3).astype(np.float32)

        texture_data = converter.convert_lut_to_texture_data(lut, "bgr")

        assert texture_data.shape == (3, 9, 3)
        assert texture_data.dtype == np.float32

    def test_convert_lut_to_texture_data_invalid_format(self) -> None:
        """Test LUT to texture data conversion with invalid format."""
        converter = HaldConverter(3)
        lut = np.random.rand(3, 3, 3, 3).astype(np.float32)

        with pytest.raises(ValueError, match="Unsupported format"):
            converter.convert_lut_to_texture_data(lut, "invalid")

    def test_get_optimal_texture_size(self) -> None:
        """Test optimal texture size calculation."""
        converter = HaldConverter(33)
        width, height = converter.get_optimal_texture_size()

        assert width == 33 * 33
        assert height == 33

    @patch("virtual_gpu_lut_box.lut.hald_converter.Image")
    def test_save_hald_image(self, mock_image: Mock) -> None:
        """Test saving Hald image to file."""
        converter = HaldConverter(3)
        hald = np.random.rand(3, 9, 3).astype(np.float32)

        mock_pil_image = Mock()
        mock_image.fromarray.return_value = mock_pil_image

        converter.save_hald_image(hald, "test.png")

        mock_image.fromarray.assert_called_once()
        mock_pil_image.save.assert_called_once_with("test.png")

    @patch("virtual_gpu_lut_box.lut.hald_converter.Image")
    def test_load_hald_image(self, mock_image: Mock) -> None:
        """Test loading Hald image from file."""
        converter = HaldConverter(3)

        # Mock PIL Image
        mock_pil_image = Mock()
        mock_pil_image.mode = "RGB"
        mock_pil_image.size = (9, 3)
        mock_pil_image.convert.return_value = mock_pil_image

        # Mock numpy array
        mock_array = np.random.randint(0, 256, (3, 9, 3), dtype=np.uint8)

        mock_image.open.return_value = mock_pil_image

        with patch("numpy.array", return_value=mock_array):
            hald = converter.load_hald_image("test.png")

            assert hald.shape == (3, 9, 3)
            assert hald.dtype == np.float32
            assert np.all(hald >= 0)
            assert np.all(hald <= 1)

    def test_33x33x33_lut_conversion(self) -> None:
        """Test conversion with production-size 33x33x33 LUT."""
        converter = HaldConverter(33)
        generator = LUTGenerator(33)

        # Create a custom LUT
        lut = generator.create_custom_lut(gamma=2.2, brightness=0.1)

        # Convert to Hald
        hald = converter.lut_to_hald(lut)

        # Check dimensions
        assert hald.shape == (33, 1089, 3)  # 33 * 33 = 1089
        assert hald.dtype == np.float32

        # Convert back
        recovered_lut = converter.hald_to_lut(hald)

        # Should be very close (allowing for floating point precision)
        assert np.allclose(lut, recovered_lut, rtol=1e-6)

    def test_texture_coordinate_precision(self) -> None:
        """Test texture coordinate precision for GPU sampling."""
        converter = HaldConverter(33)
        u_coords, v_coords = converter.create_gpu_texture_coords()

        # Check that coordinates are properly centered
        expected_u_step = 1.0 / (33 * 33)
        expected_v_step = 1.0 / 33

        assert np.allclose(u_coords[1] - u_coords[0], expected_u_step)
        assert np.allclose(v_coords[1] - v_coords[0], expected_v_step)

        # Check boundaries
        assert u_coords[0] == 0.5 * expected_u_step
        assert v_coords[0] == 0.5 * expected_v_step
