"""Tests for streaming functionality."""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from virtual_gpu_lut_box.gpu_texture_stream.base import (
    InitializationError,
    StreamingBackend,
)
from virtual_gpu_lut_box.gpu_texture_stream.factory import (
    PlatformNotSupportedError,
    StreamingFactory,
)


class MockBackend(StreamingBackend):
    """Mock streaming backend for testing."""

    def __init__(
        self, name: str, width: int, height: int, available: bool = True
    ) -> None:
        super().__init__(name, width, height)
        self._available = available
        self._init_success = True

    def initialize(self) -> None:
        if not self._available:
            raise InitializationError("Mock backend not available")
        self._initialized = self._init_success
        if not self._init_success:
            raise InitializationError("Mock initialization failed")

    def send_texture(self, texture_data: np.ndarray) -> None:
        if not self._initialized:
            raise RuntimeError("Mock backend not initialized")
        self.validate_texture_data(texture_data)

    def cleanup(self) -> None:
        self._initialized = False

    def is_available(self) -> bool:
        return self._available

    def get_supported_formats(self) -> list[str]:
        return ["rgb", "rgba", "bgr", "bgra"]


class TestStreamingBackend:
    """Test cases for StreamingBackend base class."""

    def test_init(self) -> None:
        """Test backend initialization."""
        backend = MockBackend("test", 100, 200)
        assert backend.name == "test"
        assert backend.width == 100
        assert backend.height == 200
        assert backend.initialized is False

    def test_validate_texture_data_valid_rgb(self) -> None:
        """Test texture data validation with valid RGB data."""
        backend = MockBackend("test", 10, 20)
        texture_data = np.random.randint(0, 256, (20, 10, 3), dtype=np.uint8)

        assert backend.validate_texture_data(texture_data) is True

    def test_validate_texture_data_valid_rgba(self) -> None:
        """Test texture data validation with valid RGBA data."""
        backend = MockBackend("test", 10, 20)
        texture_data = np.random.randint(0, 256, (20, 10, 4), dtype=np.uint8)

        assert backend.validate_texture_data(texture_data) is True

    def test_validate_texture_data_valid_float32(self) -> None:
        """Test texture data validation with valid float32 data."""
        backend = MockBackend("test", 10, 20)
        texture_data = np.random.rand(20, 10, 3).astype(np.float32)

        assert backend.validate_texture_data(texture_data) is True

    def test_validate_texture_data_wrong_dimensions(self) -> None:
        """Test texture data validation with wrong dimensions."""
        backend = MockBackend("test", 10, 20)
        texture_data = np.random.randint(
            0, 256, (20, 15, 3), dtype=np.uint8
        )  # Wrong width

        assert backend.validate_texture_data(texture_data) is False

    def test_validate_texture_data_wrong_shape(self) -> None:
        """Test texture data validation with wrong shape."""
        backend = MockBackend("test", 10, 20)
        texture_data = np.random.randint(
            0, 256, (20, 10), dtype=np.uint8
        )  # Missing channel dim

        assert backend.validate_texture_data(texture_data) is False

    def test_validate_texture_data_wrong_channels(self) -> None:
        """Test texture data validation with wrong channel count."""
        backend = MockBackend("test", 10, 20)
        texture_data = np.random.randint(
            0, 256, (20, 10, 2), dtype=np.uint8
        )  # 2 channels

        assert backend.validate_texture_data(texture_data) is False

    def test_validate_texture_data_wrong_dtype(self) -> None:
        """Test texture data validation with wrong data type."""
        backend = MockBackend("test", 10, 20)
        texture_data = np.random.randint(0, 256, (20, 10, 3), dtype=np.int32)

        assert backend.validate_texture_data(texture_data) is False

    def test_validate_texture_data_invalid_range_uint8(self) -> None:
        """Test texture data validation with invalid uint8 range."""
        backend = MockBackend("test", 10, 20)
        texture_data = np.random.randint(0, 256, (20, 10, 3), dtype=np.uint8)
        texture_data[0, 0, 0] = 256  # Invalid value

        assert backend.validate_texture_data(texture_data) is False

    def test_validate_texture_data_invalid_range_float32(self) -> None:
        """Test texture data validation with invalid float32 range."""
        backend = MockBackend("test", 10, 20)
        texture_data = np.random.rand(20, 10, 3).astype(np.float32)
        texture_data[0, 0, 0] = 1.5  # Invalid value

        assert backend.validate_texture_data(texture_data) is False

    def test_convert_texture_format_rgb_to_rgba(self) -> None:
        """Test texture format conversion from RGB to RGBA."""
        backend = MockBackend("test", 10, 20)
        rgb_data = np.random.rand(20, 10, 3).astype(np.float32)

        rgba_data = backend.convert_texture_format(rgb_data, "rgba")

        assert rgba_data.shape == (20, 10, 4)
        assert np.all(rgba_data[:, :, 3] == 1.0)  # Alpha should be 1.0

    def test_convert_texture_format_rgba_to_rgb(self) -> None:
        """Test texture format conversion from RGBA to RGB."""
        backend = MockBackend("test", 10, 20)
        rgba_data = np.random.rand(20, 10, 4).astype(np.float32)

        rgb_data = backend.convert_texture_format(rgba_data, "rgb")

        assert rgb_data.shape == (20, 10, 3)

    def test_convert_texture_format_rgb_to_bgr(self) -> None:
        """Test texture format conversion from RGB to BGR."""
        backend = MockBackend("test", 10, 20)
        rgb_data = np.random.rand(20, 10, 3).astype(np.float32)

        bgr_data = backend.convert_texture_format(rgb_data, "bgr")

        assert bgr_data.shape == (20, 10, 3)
        # Check that R and B channels are swapped
        assert np.allclose(rgb_data[:, :, 0], bgr_data[:, :, 2])
        assert np.allclose(rgb_data[:, :, 2], bgr_data[:, :, 0])

    def test_convert_texture_format_uint8_to_float32(self) -> None:
        """Test texture format conversion from uint8 to float32."""
        backend = MockBackend("test", 10, 20)
        uint8_data = np.random.randint(0, 256, (20, 10, 3), dtype=np.uint8)

        float32_data = backend.convert_texture_format(uint8_data, "rgb")

        assert float32_data.dtype == np.float32
        assert np.all(float32_data >= 0)
        assert np.all(float32_data <= 1)

    def test_convert_texture_format_invalid_format(self) -> None:
        """Test texture format conversion with invalid format."""
        backend = MockBackend("test", 10, 20)
        rgb_data = np.random.rand(20, 10, 3).astype(np.float32)

        with pytest.raises(ValueError, match="Unsupported format"):
            backend.convert_texture_format(rgb_data, "invalid")

    def test_context_manager_success(self) -> None:
        """Test context manager with successful initialization."""
        backend = MockBackend("test", 10, 20)

        with backend:
            assert backend.initialized is True

        assert backend.initialized is False

    def test_context_manager_failure(self) -> None:
        """Test context manager with failed initialization."""
        backend = MockBackend("test", 10, 20, available=False)

        with pytest.raises(RuntimeError, match="Failed to initialize"), backend:
            pass

    def test_send_texture_success(self) -> None:
        """Test successful texture sending."""
        backend = MockBackend("test", 10, 20)
        backend.initialize()

        texture_data = np.random.rand(20, 10, 3).astype(np.float32)
        result = backend.send_texture(texture_data)

        assert result is True

    def test_send_texture_not_initialized(self) -> None:
        """Test texture sending when not initialized."""
        backend = MockBackend("test", 10, 20)

        texture_data = np.random.rand(20, 10, 3).astype(np.float32)
        result = backend.send_texture(texture_data)

        assert result is False

    def test_send_texture_invalid_data(self) -> None:
        """Test texture sending with invalid data."""
        backend = MockBackend("test", 10, 20)
        backend.initialize()

        texture_data = np.random.rand(15, 10, 3).astype(np.float32)  # Wrong height
        result = backend.send_texture(texture_data)

        assert result is False


class TestStreamingFactory:
    """Test cases for StreamingFactory class."""

    def test_register_backend(self) -> None:
        """Test backend registration."""
        # Clear existing backends
        original_backends = StreamingFactory._backends.copy()
        StreamingFactory._backends.clear()

        try:
            StreamingFactory.register_backend("TestOS", MockBackend)
            assert "TestOS" in StreamingFactory._backends
            assert StreamingFactory._backends["TestOS"] is MockBackend
        finally:
            StreamingFactory._backends = original_backends

    def test_get_available_backends(self) -> None:
        """Test getting available backends."""
        backends = StreamingFactory.get_available_backends()
        assert isinstance(backends, list)

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_create_backend_success(self, mock_platform: Mock) -> None:
        """Test successful backend creation."""
        mock_platform.return_value = "TestOS"

        # Register test backend
        original_backends = StreamingFactory._backends.copy()
        StreamingFactory._backends["TestOS"] = MockBackend

        try:
            backend = StreamingFactory.create_backend("test", 100, 200)
            assert isinstance(backend, MockBackend)
            assert backend.name == "test"
            assert backend.width == 100
            assert backend.height == 200
        finally:
            StreamingFactory._backends = original_backends

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_create_backend_unsupported_platform(self, mock_platform: Mock) -> None:
        """Test backend creation with unsupported platform."""
        mock_platform.return_value = "UnsupportedOS"

        with pytest.raises(
            PlatformNotSupportedError, match="Platform 'UnsupportedOS' is not supported"
        ):
            StreamingFactory.create_backend("test", 100, 200)

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_create_backend_unavailable(self, mock_platform: Mock) -> None:
        """Test backend creation when backend is unavailable."""
        mock_platform.return_value = "TestOS"

        # Register unavailable backend
        original_backends = StreamingFactory._backends.copy()

        class UnavailableBackend(MockBackend):
            def is_available(self) -> bool:
                return False

        StreamingFactory._backends["TestOS"] = UnavailableBackend

        try:
            with pytest.raises(
                PlatformNotSupportedError, match="Backend for 'TestOS' is not available"
            ):
                StreamingFactory.create_backend("test", 100, 200)
        finally:
            StreamingFactory._backends = original_backends

    def test_create_backend_override_platform(self) -> None:
        """Test backend creation with platform override."""
        # Register test backend
        original_backends = StreamingFactory._backends.copy()
        StreamingFactory._backends["TestOS"] = MockBackend

        try:
            backend = StreamingFactory.create_backend(
                "test", 100, 200, platform_name="TestOS"
            )
            assert isinstance(backend, MockBackend)
        finally:
            StreamingFactory._backends = original_backends

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_get_current_platform(self, mock_platform: Mock) -> None:
        """Test getting current platform."""
        mock_platform.return_value = "TestOS"
        platform_name = StreamingFactory.get_current_platform()
        assert platform_name == "TestOS"

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_is_platform_supported_true(self, mock_platform: Mock) -> None:
        """Test platform support check (supported)."""
        mock_platform.return_value = "TestOS"

        # Register test backend
        original_backends = StreamingFactory._backends.copy()
        StreamingFactory._backends["TestOS"] = MockBackend

        try:
            is_supported = StreamingFactory.is_platform_supported()
            assert is_supported is True
        finally:
            StreamingFactory._backends = original_backends

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_is_platform_supported_false(self, mock_platform: Mock) -> None:
        """Test platform support check (not supported)."""
        mock_platform.return_value = "UnsupportedOS"

        is_supported = StreamingFactory.is_platform_supported()
        assert is_supported is False

    def test_create_lut_streamer(self) -> None:
        """Test LUT streamer creation."""
        # Register test backend
        original_backends = StreamingFactory._backends.copy()
        StreamingFactory._backends["TestOS"] = MockBackend

        try:
            backend = StreamingFactory.create_lut_streamer(
                "test", lut_size=17, platform_name="TestOS"
            )
            assert isinstance(backend, MockBackend)
            assert backend.width == 17 * 17  # 289
            assert backend.height == 17
        finally:
            StreamingFactory._backends = original_backends

    def test_list_supported_formats(self) -> None:
        """Test listing supported formats."""
        # Register test backend
        original_backends = StreamingFactory._backends.copy()
        StreamingFactory._backends["TestOS"] = MockBackend

        try:
            formats = StreamingFactory.list_supported_formats("TestOS")
            assert formats == ["rgb", "rgba", "bgr", "bgra"]
        finally:
            StreamingFactory._backends = original_backends

    def test_list_supported_formats_unsupported(self) -> None:
        """Test listing formats for unsupported platform."""
        formats = StreamingFactory.list_supported_formats("UnsupportedOS")
        assert formats == []

    @patch("virtual_gpu_lut_box.streaming.factory.platform")
    def test_get_platform_info(self, mock_platform: Mock) -> None:
        """Test getting platform information."""
        mock_platform.system.return_value = "TestOS"
        mock_platform.release.return_value = "1.0"
        mock_platform.version.return_value = "1.0.0"
        mock_platform.machine.return_value = "x86_64"
        mock_platform.processor.return_value = "Intel"
        mock_platform.python_version.return_value = "3.9.0"

        info = StreamingFactory.get_platform_info()

        assert info["system"] == "TestOS"
        assert info["release"] == "1.0"
        assert info["version"] == "1.0.0"
        assert info["machine"] == "x86_64"
        assert info["processor"] == "Intel"
        assert info["python_version"] == "3.9.0"
