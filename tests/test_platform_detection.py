"""Tests for platform detection functionality."""

from unittest.mock import Mock, patch

import pytest

from virtual_gpu_lut_box.gpu_texture_stream.factory import (
    PlatformNotSupportedError,
    StreamingFactory,
)


class TestPlatformDetection:
    """Test cases for platform detection functionality."""

    @patch("virtual_gpu_lut_box.gpu_texture_stream.factory.platform.system")
    def test_windows_platform_detection(self, mock_platform: Mock) -> None:
        """Test Windows platform detection."""
        mock_platform.return_value = "Windows"
        platform_name = StreamingFactory.get_current_platform()
        assert platform_name == "Windows"

    @patch("virtual_gpu_lut_box.gpu_texture_stream.factory.platform.system")
    def test_macos_platform_detection(self, mock_platform: Mock) -> None:
        """Test macOS platform detection."""
        mock_platform.return_value = "Darwin"
        platform_name = StreamingFactory.get_current_platform()
        assert platform_name == "Darwin"

    @patch("virtual_gpu_lut_box.gpu_texture_stream.factory.platform.system")
    def test_linux_platform_detection(self, mock_platform: Mock) -> None:
        """Test Linux platform detection."""
        mock_platform.return_value = "Linux"
        platform_name = StreamingFactory.get_current_platform()
        assert platform_name == "Linux"

    @patch("virtual_gpu_lut_box.gpu_texture_stream.factory.platform.system")
    def test_unsupported_platform_detection(self, mock_platform: Mock) -> None:
        """Test unsupported platform detection."""
        mock_platform.return_value = "UnsupportedOS"
        platform_name = StreamingFactory.get_current_platform()
        assert platform_name == "UnsupportedOS"

    @patch("virtual_gpu_lut_box.gpu_texture_stream.factory.platform.system")
    def test_is_platform_supported_false(self, mock_platform: Mock) -> None:
        """Test platform support check (not supported)."""
        mock_platform.return_value = "UnsupportedOS"
        is_supported = StreamingFactory.is_platform_supported()
        assert is_supported is False

    @patch("virtual_gpu_lut_box.gpu_texture_stream.factory.platform.system")
    def test_create_backend_unsupported_platform(self, mock_platform: Mock) -> None:
        """Test backend creation with unsupported platform."""
        mock_platform.return_value = "UnsupportedOS"

        with pytest.raises(
            PlatformNotSupportedError, match="Platform 'UnsupportedOS' is not supported"
        ):
            StreamingFactory.create_backend("test", 100, 200)

    def test_get_available_backends(self) -> None:
        """Test getting available backends."""
        backends = StreamingFactory.get_available_backends()
        assert isinstance(backends, list)
        # Should contain at least one backend (Windows is always registered)
        assert len(backends) >= 1

    def test_platform_info_completeness(self) -> None:
        """Test that platform info contains expected keys."""
        info = StreamingFactory.get_platform_info()

        expected_keys = [
            "system",
            "release",
            "version",
            "machine",
            "processor",
            "python_version",
        ]
        for key in expected_keys:
            assert key in info
            assert isinstance(info[key], str)

    def test_platform_info_values(self) -> None:
        """Test that platform info contains reasonable values."""
        info = StreamingFactory.get_platform_info()

        # Should have non-empty values
        assert len(info["system"]) > 0
        assert len(info["python_version"]) > 0

        # Python version should contain a dot
        assert "." in info["python_version"]

    def test_list_supported_formats_unsupported(self) -> None:
        """Test listing formats for unsupported platform."""
        formats = StreamingFactory.list_supported_formats("UnsupportedOS")
        assert formats == []

    def test_backend_registration_interface(self) -> None:
        """Test backend registration interface."""
        # Test that the register_backend method exists and can be called
        # We won't actually register anything to avoid affecting other tests
        assert hasattr(StreamingFactory, "register_backend")
        assert callable(StreamingFactory.register_backend)

    @patch("virtual_gpu_lut_box.gpu_texture_stream.factory.platform.system")
    def test_create_lut_streamer_unsupported_platform(
        self, mock_platform: Mock
    ) -> None:
        """Test LUT streamer creation with unsupported platform."""
        mock_platform.return_value = "UnsupportedOS"

        with pytest.raises(RuntimeError, match="Failed to create LUT streamer"):
            StreamingFactory.create_lut_streamer("test", lut_size=17)

    def test_factory_methods_exist(self) -> None:
        """Test that all expected factory methods exist."""
        expected_methods = [
            "get_current_platform",
            "get_available_backends",
            "is_platform_supported",
            "create_backend",
            "create_lut_streamer",
            "list_supported_formats",
            "get_platform_info",
            "register_backend",
        ]

        for method_name in expected_methods:
            assert hasattr(StreamingFactory, method_name)
            assert callable(getattr(StreamingFactory, method_name))

    def test_factory_constants_exist(self) -> None:
        """Test that factory has expected constants."""
        # Should have a _backends registry
        assert hasattr(StreamingFactory, "_backends")
        assert isinstance(StreamingFactory._backends, dict)
