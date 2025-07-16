"""Tests for platform detection and cross-platform functionality."""

from unittest.mock import Mock, patch

from virtual_gpu_lut_box.streaming.factory import StreamingFactory


class TestPlatformDetection:
    """Test cases for platform detection functionality."""

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_windows_platform_detection(self, mock_platform: Mock) -> None:
        """Test Windows platform detection."""
        mock_platform.return_value = "Windows"

        platform_name = StreamingFactory.get_current_platform()
        assert platform_name == "Windows"

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_macos_platform_detection(self, mock_platform: Mock) -> None:
        """Test macOS platform detection."""
        mock_platform.return_value = "Darwin"

        platform_name = StreamingFactory.get_current_platform()
        assert platform_name == "Darwin"

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_linux_platform_detection(self, mock_platform: Mock) -> None:
        """Test Linux platform detection."""
        mock_platform.return_value = "Linux"

        platform_name = StreamingFactory.get_current_platform()
        assert platform_name == "Linux"

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_unsupported_platform_detection(self, mock_platform: Mock) -> None:
        """Test detection of unsupported platform."""
        mock_platform.return_value = "FreeBSD"

        platform_name = StreamingFactory.get_current_platform()
        assert platform_name == "FreeBSD"

        # Should not be supported
        is_supported = StreamingFactory.is_platform_supported()
        assert is_supported is False

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    @patch("virtual_gpu_lut_box.streaming.spout.platform.system")
    def test_spout_availability_windows(
        self, mock_spout_platform: Mock, mock_factory_platform: Mock
    ) -> None:
        """Test SpoutGL availability on Windows."""
        mock_factory_platform.return_value = "Windows"
        mock_spout_platform.return_value = "Windows"

        # Mock SpoutGL import
        with patch.dict("sys.modules", {"SpoutGL": Mock()}):
            from virtual_gpu_lut_box.streaming.spout import SpoutBackend

            backend = SpoutBackend("test", 100, 200)
            assert backend.is_available() is True

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    @patch("virtual_gpu_lut_box.streaming.spout.platform.system")
    def test_spout_unavailable_non_windows(
        self, mock_spout_platform: Mock, mock_factory_platform: Mock
    ) -> None:
        """Test SpoutGL unavailability on non-Windows platforms."""
        mock_factory_platform.return_value = "Darwin"
        mock_spout_platform.return_value = "Darwin"

        from virtual_gpu_lut_box.streaming.spout import SpoutBackend

        backend = SpoutBackend("test", 100, 200)
        assert backend.is_available() is False

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    @patch("virtual_gpu_lut_box.streaming.syphon.platform.system")
    def test_syphon_availability_macos(
        self, mock_syphon_platform: Mock, mock_factory_platform: Mock
    ) -> None:
        """Test Syphon availability on macOS."""
        mock_factory_platform.return_value = "Darwin"
        mock_syphon_platform.return_value = "Darwin"

        # Mock syphon-python import
        with patch.dict("sys.modules", {"syphon": Mock()}):
            from virtual_gpu_lut_box.streaming.syphon import SyphonBackend

            backend = SyphonBackend("test", 100, 200)
            assert backend.is_available() is True

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    @patch("virtual_gpu_lut_box.streaming.syphon.platform.system")
    def test_syphon_unavailable_non_macos(
        self, mock_syphon_platform: Mock, mock_factory_platform: Mock
    ) -> None:
        """Test Syphon unavailability on non-macOS platforms."""
        mock_factory_platform.return_value = "Windows"
        mock_syphon_platform.return_value = "Windows"

        from virtual_gpu_lut_box.streaming.syphon import SyphonBackend

        backend = SyphonBackend("test", 100, 200)
        assert backend.is_available() is False

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_backend_registration_windows(self, mock_platform: Mock) -> None:
        """Test backend registration on Windows."""
        mock_platform.return_value = "Windows"

        # Mock SpoutGL import
        with patch.dict("sys.modules", {"SpoutGL": Mock()}):
            # Re-import factory to trigger registration
            from importlib import reload

            from virtual_gpu_lut_box.streaming import factory

            reload(factory)

            available_backends = factory.StreamingFactory.get_available_backends()
            assert "Windows" in available_backends

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_backend_registration_macos(self, mock_platform: Mock) -> None:
        """Test backend registration on macOS."""
        mock_platform.return_value = "Darwin"

        # Mock syphon-python import
        with patch.dict("sys.modules", {"syphon": Mock()}):
            # Re-import factory to trigger registration
            from importlib import reload

            from virtual_gpu_lut_box.streaming import factory

            reload(factory)

            available_backends = factory.StreamingFactory.get_available_backends()
            assert "Darwin" in available_backends

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_cross_platform_lut_streamer_creation(self, mock_platform: Mock) -> None:
        """Test cross-platform LUT streamer creation."""
        # Test with different platform names
        platforms = ["Windows", "Darwin"]

        for platform_name in platforms:
            mock_platform.return_value = platform_name

            # Mock the appropriate module
            if platform_name == "Windows":
                mock_module = {"SpoutGL": Mock()}
            else:
                mock_module = {"syphon": Mock()}

            with patch.dict("sys.modules", mock_module):
                # Re-import factory to trigger registration
                from importlib import reload

                from virtual_gpu_lut_box.streaming import factory

                reload(factory)

                # Should be able to create LUT streamer
                backend = factory.StreamingFactory.create_lut_streamer(
                    "test", lut_size=33, platform_name=platform_name
                )

                assert backend.width == 33 * 33
                assert backend.height == 33

    def test_platform_info_completeness(self) -> None:
        """Test that platform info contains all expected fields."""
        info = StreamingFactory.get_platform_info()

        expected_fields = [
            "system",
            "release",
            "version",
            "machine",
            "processor",
            "python_version",
        ]

        for field in expected_fields:
            assert field in info
            assert isinstance(info[field], str)

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_platform_override_functionality(self, mock_platform: Mock) -> None:
        """Test platform override functionality."""
        # Current platform is Windows
        mock_platform.return_value = "Windows"

        # But we override to Darwin
        with patch.dict("sys.modules", {"syphonpy": Mock()}):
            from importlib import reload

            from virtual_gpu_lut_box.streaming import factory

            reload(factory)

            # Should create Darwin backend despite Windows platform
            backend = factory.StreamingFactory.create_lut_streamer(
                "test", lut_size=17, platform_name="Darwin"
            )

            # Check that it's the right type
            from virtual_gpu_lut_box.streaming.syphon import SyphonBackend

            assert isinstance(backend, SyphonBackend)

    @patch("virtual_gpu_lut_box.streaming.factory.platform.system")
    def test_format_listing_cross_platform(self, mock_platform: Mock) -> None:
        """Test format listing across platforms."""
        platforms = ["Windows", "Darwin"]

        for platform_name in platforms:
            mock_platform.return_value = platform_name

            # Mock the appropriate module
            if platform_name == "Windows":
                mock_module = {"SpoutGL": Mock()}
            else:
                mock_module = {"syphon": Mock()}

            with patch.dict("sys.modules", mock_module):
                # Re-import factory to trigger registration
                from importlib import reload

                from virtual_gpu_lut_box.streaming import factory

                reload(factory)

                # Should return format list
                formats = factory.StreamingFactory.list_supported_formats(platform_name)

                expected_formats = ["rgb", "rgba", "bgr", "bgra"]
                assert formats == expected_formats

    def test_error_handling_import_failures(self) -> None:
        """Test error handling when imports fail."""
        # Clear any existing modules
        import sys

        modules_to_remove = [
            "virtual_gpu_lut_box.streaming.spout",
            "virtual_gpu_lut_box.streaming.syphon",
        ]

        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

        # Mock import errors
        with patch.dict("sys.modules", {"SpoutGL": None, "syphon": None}):
            from importlib import reload

            from virtual_gpu_lut_box.streaming import factory

            # Should not raise errors, just skip registration
            reload(factory)

            # Should have empty backends
            available_backends = factory.StreamingFactory.get_available_backends()
            assert len(available_backends) == 0
