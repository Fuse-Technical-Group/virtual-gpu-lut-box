# SPDX-FileCopyrightText: 2025 Fuse Technical Group
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for main server module."""

from unittest.mock import Mock, patch

import pytest

from virtual_gpu_lut_box.server import VirtualGPULUTBoxServer, _server_process_worker


class TestVirtualGPULUTBoxServer:
    """Test cases for VirtualGPULUTBoxServer class."""

    def test_init_default_values(self) -> None:
        """Test server initialization with default values."""
        with (
            patch("virtual_gpu_lut_box.server.multiprocessing.Process") as mock_process,
            patch("virtual_gpu_lut_box.server.multiprocessing.Event") as mock_event,
        ):
            mock_process_instance = Mock()
            mock_process.return_value = mock_process_instance
            mock_event_instance = Mock()
            mock_event.return_value = mock_event_instance

            server = VirtualGPULUTBoxServer()

            assert server.host == "0.0.0.0"  # noqa: S104
            assert server.port == 8089  # DEFAULT_PORT
            assert server.stream_name == "OpenGradeIO-LUT"
            assert server.verbose is False
            assert server.info_logging is False
            assert server.lut_callback is None
            assert server._process is mock_process_instance
            assert server._shutdown_event is mock_event_instance

            # Process should be started
            mock_process_instance.start.assert_called_once()

    def test_init_custom_values(self) -> None:
        """Test server initialization with custom values."""
        mock_callback = Mock()

        with (
            patch("virtual_gpu_lut_box.server.multiprocessing.Process") as mock_process,
            patch("virtual_gpu_lut_box.server.multiprocessing.Event"),
        ):
            mock_process_instance = Mock()
            mock_process.return_value = mock_process_instance

            server = VirtualGPULUTBoxServer(
                host="192.168.1.100",
                port=9999,
                stream_name="CustomLUT",
                verbose=True,
                info_logging=True,
                lut_callback=mock_callback,
            )

            assert server.host == "192.168.1.100"
            assert server.port == 9999
            assert server.stream_name == "CustomLUT"
            assert server.verbose is True
            assert server.info_logging is True
            assert server.lut_callback is mock_callback

    def test_default_port_constant(self) -> None:
        """Test DEFAULT_PORT constant."""
        assert VirtualGPULUTBoxServer.DEFAULT_PORT == 8089

    def test_start_server_already_running(self) -> None:
        """Test starting server when process is already running."""
        with (
            patch("virtual_gpu_lut_box.server.multiprocessing.Process") as mock_process,
            patch("virtual_gpu_lut_box.server.multiprocessing.Event"),
        ):
            mock_process_instance = Mock()
            mock_process_instance.is_alive.return_value = True
            mock_process.return_value = mock_process_instance

            server = VirtualGPULUTBoxServer()

            # Should not raise exception
            server.start()

            # Process should already be alive
            mock_process_instance.is_alive.assert_called()

    def test_start_server_process_failed(self) -> None:
        """Test starting server when process failed to start."""
        with (
            patch("virtual_gpu_lut_box.server.multiprocessing.Process") as mock_process,
            patch("virtual_gpu_lut_box.server.multiprocessing.Event"),
        ):
            mock_process_instance = Mock()
            mock_process_instance.is_alive.return_value = False
            mock_process.return_value = mock_process_instance

            server = VirtualGPULUTBoxServer()

            with pytest.raises(RuntimeError, match="Failed to start server process"):
                server.start()

    def test_stop_server_running(self) -> None:
        """Test stopping running server."""
        with (
            patch("virtual_gpu_lut_box.server.multiprocessing.Process") as mock_process,
            patch("virtual_gpu_lut_box.server.multiprocessing.Event") as mock_event,
        ):
            mock_process_instance = Mock()
            mock_process_instance.is_alive.return_value = True
            mock_process.return_value = mock_process_instance

            mock_event_instance = Mock()
            mock_event.return_value = mock_event_instance

            server = VirtualGPULUTBoxServer()
            server.stop()

            # Should signal shutdown and wait for process
            mock_event_instance.set.assert_called_once()
            mock_process_instance.join.assert_called_with(timeout=2.0)

    def test_stop_server_not_running(self) -> None:
        """Test stopping server when not running."""
        with (
            patch("virtual_gpu_lut_box.server.multiprocessing.Process") as mock_process,
            patch("virtual_gpu_lut_box.server.multiprocessing.Event"),
        ):
            mock_process_instance = Mock()
            mock_process_instance.is_alive.return_value = False
            mock_process.return_value = mock_process_instance

            server = VirtualGPULUTBoxServer()

            # Should not raise exception
            server.stop()

    def test_stop_server_force_terminate(self) -> None:
        """Test stopping server with force terminate."""
        with (
            patch("virtual_gpu_lut_box.server.multiprocessing.Process") as mock_process,
            patch("virtual_gpu_lut_box.server.multiprocessing.Event") as mock_event,
        ):
            mock_process_instance = Mock()
            # First is_alive returns True, second (after join) returns True (didn't stop)
            mock_process_instance.is_alive.side_effect = [True, True, False]
            mock_process.return_value = mock_process_instance

            mock_event_instance = Mock()
            mock_event.return_value = mock_event_instance

            server = VirtualGPULUTBoxServer()
            server.stop()

            # Should terminate process
            mock_process_instance.terminate.assert_called_once()
            # Should call join twice (once for graceful, once after terminate)
            assert mock_process_instance.join.call_count == 2

    def test_is_running_property(self) -> None:
        """Test is_running property."""
        with (
            patch("virtual_gpu_lut_box.server.multiprocessing.Process") as mock_process,
            patch("virtual_gpu_lut_box.server.multiprocessing.Event"),
        ):
            mock_process_instance = Mock()
            mock_process.return_value = mock_process_instance

            server = VirtualGPULUTBoxServer()

            # Test when process is alive
            mock_process_instance.is_alive.return_value = True
            assert server.is_running is True

            # Test when process is not alive
            mock_process_instance.is_alive.return_value = False
            assert server.is_running is False

    def test_is_running_no_process(self) -> None:
        """Test is_running property when no process."""
        with (
            patch("virtual_gpu_lut_box.server.multiprocessing.Process"),
            patch("virtual_gpu_lut_box.server.multiprocessing.Event"),
        ):
            # Don't call the constructor, just test the property directly
            server = VirtualGPULUTBoxServer.__new__(VirtualGPULUTBoxServer)
            server._process = None

            assert server.is_running is False

    @patch("virtual_gpu_lut_box.gpu_texture_stream.factory.StreamingFactory")
    def test_get_platform_info(self, mock_factory: Mock) -> None:
        """Test get_platform_info static method."""
        mock_base_info = {
            "system": "Darwin",
            "release": "24.0.0",
            "version": "Darwin Kernel Version 24.0.0",
            "machine": "arm64",
            "processor": "arm",
            "python_version": "3.11.5",
        }
        mock_factory.get_platform_info.return_value = mock_base_info
        mock_factory.get_current_platform.return_value = "Darwin"
        mock_factory.get_available_backends.return_value = ["Darwin"]
        mock_factory.is_platform_supported.return_value = True
        mock_factory.list_supported_formats.return_value = ["rgb", "rgba"]

        result = VirtualGPULUTBoxServer.get_platform_info()

        assert result["system"] == "Darwin"
        assert result["current_platform"] == "Darwin"
        assert result["available_backends"] == ["Darwin"]
        assert result["platform_supported"] is True
        assert result["supported_formats"] == ["rgb", "rgba"]

    @patch("virtual_gpu_lut_box.gpu_texture_stream.factory.StreamingFactory")
    def test_get_platform_info_unsupported(self, mock_factory: Mock) -> None:
        """Test get_platform_info for unsupported platform."""
        mock_base_info = {
            "system": "Linux",
            "release": "5.15.0",
            "version": "Linux version 5.15.0",
            "machine": "x86_64",
            "processor": "x86_64",
            "python_version": "3.11.5",
        }
        mock_factory.get_platform_info.return_value = mock_base_info
        mock_factory.get_current_platform.return_value = "Linux"
        mock_factory.get_available_backends.return_value = []
        mock_factory.is_platform_supported.return_value = False

        result = VirtualGPULUTBoxServer.get_platform_info()

        assert result["system"] == "Linux"
        assert result["current_platform"] == "Linux"
        assert result["available_backends"] == []
        assert result["platform_supported"] is False
        # Should not have supported_formats for unsupported platform
        assert "supported_formats" not in result

    def test_logging_configuration(self) -> None:
        """Test logging configuration for different modes."""
        with (
            patch("virtual_gpu_lut_box.server.multiprocessing.Process"),
            patch("virtual_gpu_lut_box.server.multiprocessing.Event"),
            patch("virtual_gpu_lut_box.server.logging.basicConfig") as mock_config,
        ):
            # Test verbose mode
            VirtualGPULUTBoxServer(verbose=True)
            mock_config.assert_called_with(
                level=10,  # DEBUG level
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

            mock_config.reset_mock()

            # Test info logging mode
            VirtualGPULUTBoxServer(info_logging=True)
            mock_config.assert_called_with(
                level=20,  # INFO level
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

            mock_config.reset_mock()

            # Test quiet mode (default)
            VirtualGPULUTBoxServer()
            mock_config.assert_called_with(
                level=30,  # WARNING level
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )


class TestServerProcessWorker:
    """Test cases for _server_process_worker function."""

    @patch("virtual_gpu_lut_box.server.OpenGradeIOServer")
    @patch("virtual_gpu_lut_box.server.OpenGradeIOLUTStreamer")
    @patch("virtual_gpu_lut_box.server.logging.basicConfig")
    def test_worker_verbose_mode(
        self, mock_logging: Mock, mock_streamer: Mock, mock_server: Mock
    ) -> None:
        """Test server process worker in verbose mode."""
        mock_shutdown_event = Mock()
        mock_shutdown_event.wait.return_value = None

        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        mock_streamer_instance = Mock()
        mock_streamer.return_value = mock_streamer_instance

        _server_process_worker(
            host="localhost",
            port=8089,
            stream_name="TestLUT",
            verbose=True,
            info_logging=False,
            lut_callback=None,
            shutdown_event=mock_shutdown_event,
        )

        # Should configure debug logging
        mock_logging.assert_called_once()
        args = mock_logging.call_args[1]
        assert args["level"] == 10  # DEBUG level

        # Should create streamer and server
        mock_streamer.assert_called_once_with(stream_name="TestLUT", quiet_mode=False)
        mock_server.assert_called_once()

        # Should start and stop server
        mock_server_instance.start.assert_called_once()
        mock_server_instance.stop.assert_called_once()

    @patch("virtual_gpu_lut_box.server.OpenGradeIOServer")
    @patch("virtual_gpu_lut_box.server.OpenGradeIOLUTStreamer")
    @patch("virtual_gpu_lut_box.server.logging.basicConfig")
    def test_worker_info_logging_mode(
        self, mock_logging: Mock, mock_streamer: Mock, mock_server: Mock
    ) -> None:
        """Test server process worker in info logging mode."""
        mock_shutdown_event = Mock()
        mock_shutdown_event.wait.return_value = None

        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        mock_streamer_instance = Mock()
        mock_streamer.return_value = mock_streamer_instance

        _server_process_worker(
            host="localhost",
            port=8089,
            stream_name="TestLUT",
            verbose=False,
            info_logging=True,
            lut_callback=None,
            shutdown_event=mock_shutdown_event,
        )

        # Should configure info logging
        mock_logging.assert_called_once()
        args = mock_logging.call_args[1]
        assert args["level"] == 20  # INFO level

        # Should create streamer in non-quiet mode
        mock_streamer.assert_called_once_with(stream_name="TestLUT", quiet_mode=False)

    @patch("virtual_gpu_lut_box.server.OpenGradeIOServer")
    @patch("virtual_gpu_lut_box.server.OpenGradeIOLUTStreamer")
    @patch("virtual_gpu_lut_box.server.logging.basicConfig")
    def test_worker_quiet_mode(
        self, mock_logging: Mock, mock_streamer: Mock, mock_server: Mock
    ) -> None:
        """Test server process worker in quiet mode."""
        mock_shutdown_event = Mock()
        mock_shutdown_event.wait.return_value = None

        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        mock_streamer_instance = Mock()
        mock_streamer.return_value = mock_streamer_instance

        _server_process_worker(
            host="localhost",
            port=8089,
            stream_name="TestLUT",
            verbose=False,
            info_logging=False,
            lut_callback=None,
            shutdown_event=mock_shutdown_event,
        )

        # Should configure warning logging
        mock_logging.assert_called_once()
        args = mock_logging.call_args[1]
        assert args["level"] == 30  # WARNING level

        # Should create streamer in quiet mode
        mock_streamer.assert_called_once_with(stream_name="TestLUT", quiet_mode=True)

    @patch("virtual_gpu_lut_box.server.OpenGradeIOServer")
    @patch("virtual_gpu_lut_box.server.logging.basicConfig")
    def test_worker_with_custom_callback(
        self, mock_logging: Mock, mock_server: Mock
    ) -> None:
        """Test server process worker with custom callback."""
        mock_shutdown_event = Mock()
        mock_shutdown_event.wait.return_value = None

        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        custom_callback = Mock()

        _server_process_worker(
            host="localhost",
            port=8089,
            stream_name="TestLUT",
            verbose=False,
            info_logging=False,
            lut_callback=custom_callback,
            shutdown_event=mock_shutdown_event,
        )

        # Should use custom callback directly
        mock_server.assert_called_once()
        server_args = mock_server.call_args[1]
        assert server_args["lut_callback"] is custom_callback

    @patch("virtual_gpu_lut_box.server.OpenGradeIOServer")
    @patch("virtual_gpu_lut_box.server.OpenGradeIOLUTStreamer")
    @patch("virtual_gpu_lut_box.server.logging.basicConfig")
    def test_worker_keyboard_interrupt(
        self, mock_logging: Mock, mock_streamer: Mock, mock_server: Mock
    ) -> None:
        """Test server process worker with keyboard interrupt."""
        mock_shutdown_event = Mock()
        mock_shutdown_event.wait.side_effect = KeyboardInterrupt()

        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        mock_streamer_instance = Mock()
        mock_streamer.return_value = mock_streamer_instance

        # Should handle KeyboardInterrupt gracefully
        _server_process_worker(
            host="localhost",
            port=8089,
            stream_name="TestLUT",
            verbose=False,
            info_logging=False,
            lut_callback=None,
            shutdown_event=mock_shutdown_event,
        )

        # Should still clean up
        mock_server_instance.stop.assert_called_once()
        mock_streamer_instance.stop_streaming.assert_called_once()

    @patch("virtual_gpu_lut_box.server.OpenGradeIOServer")
    @patch("virtual_gpu_lut_box.server.OpenGradeIOLUTStreamer")
    @patch("virtual_gpu_lut_box.server.logging.basicConfig")
    def test_worker_server_error(
        self, mock_logging: Mock, mock_streamer: Mock, mock_server: Mock
    ) -> None:
        """Test server process worker with server error."""
        mock_shutdown_event = Mock()
        mock_shutdown_event.wait.return_value = None

        mock_server_instance = Mock()
        mock_server_instance.start.side_effect = Exception("Server start error")
        mock_server.return_value = mock_server_instance

        mock_streamer_instance = Mock()
        mock_streamer.return_value = mock_streamer_instance

        # Should handle server error gracefully
        _server_process_worker(
            host="localhost",
            port=8089,
            stream_name="TestLUT",
            verbose=False,
            info_logging=False,
            lut_callback=None,
            shutdown_event=mock_shutdown_event,
        )

        # Should still clean up
        mock_server_instance.stop.assert_called_once()
        mock_streamer_instance.stop_streaming.assert_called_once()
