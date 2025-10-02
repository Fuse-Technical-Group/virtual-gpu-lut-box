# SPDX-FileCopyrightText: 2025 Fuse Technical Group
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for CLI module."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from virtual_gpu_lut_box.cli import main, show_system_info, start_server_cli
from virtual_gpu_lut_box.gpu_texture_stream.factory import PlatformNotSupportedError


class TestCLI:
    """Test cases for CLI functionality."""

    def test_main_help(self) -> None:
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Virtual GPU LUT Box" in result.output
        assert "--host" in result.output
        assert "--port" in result.output
        assert "--stream-name" in result.output
        assert "--verbose" in result.output
        assert "--info-logging" in result.output
        assert "--info" in result.output

    def test_main_version(self) -> None:
        """Test CLI version output."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        # Should contain version info
        assert len(result.output.strip()) > 0

    @patch("virtual_gpu_lut_box.cli.show_system_info")
    def test_main_info_flag(self, mock_show_info: Mock) -> None:
        """Test CLI --info flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["--info"])

        assert result.exit_code == 0
        mock_show_info.assert_called_once()

    @patch("virtual_gpu_lut_box.cli.start_server_cli")
    def test_main_default_behavior(self, mock_start_server: Mock) -> None:
        """Test CLI default behavior starts server."""
        runner = CliRunner()
        result = runner.invoke(main)

        assert result.exit_code == 0
        mock_start_server.assert_called_once_with(
            "0.0.0.0",  # noqa: S104
            8089,
            "OpenGradeIO-LUT",
            False,
            False,
        )

    @patch("virtual_gpu_lut_box.cli.start_server_cli")
    def test_main_custom_options(self, mock_start_server: Mock) -> None:
        """Test CLI with custom options."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--host",
                "192.168.1.100",
                "--port",
                "9999",
                "--stream-name",
                "CustomLUT",
                "--verbose",
                "--info-logging",
            ],
        )

        assert result.exit_code == 0
        mock_start_server.assert_called_once_with(
            "192.168.1.100", 9999, "CustomLUT", True, True
        )

    @patch("virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer")
    def test_show_system_info_success(self, mock_server_class: Mock) -> None:
        """Test successful system info display."""
        # Mock platform info
        mock_platform_info = {
            "system": "Darwin",
            "release": "24.0.0",
            "version": "Darwin Kernel Version 24.0.0",
            "machine": "arm64",
            "processor": "arm",
            "python_version": "3.11.5",
            "current_platform": "Darwin",
            "available_backends": ["Darwin"],
            "platform_supported": True,
            "supported_formats": ["rgb", "rgba", "bgr", "bgra"],
        }
        mock_server_class.get_platform_info.return_value = mock_platform_info

        runner = CliRunner()
        result = runner.invoke(main, ["--info"])

        assert result.exit_code == 0
        assert "System Information:" in result.output
        assert "system: Darwin" in result.output
        assert "Current platform: Darwin" in result.output
        assert "Available backends: Darwin" in result.output
        assert "Platform supported: True" in result.output
        assert "Supported formats: rgb, rgba, bgr, bgra" in result.output

    @patch("virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer")
    def test_show_system_info_unsupported_platform(
        self, mock_server_class: Mock
    ) -> None:
        """Test system info display for unsupported platform."""
        mock_platform_info = {
            "system": "Linux",
            "release": "5.15.0",
            "version": "Linux version 5.15.0",
            "machine": "x86_64",
            "processor": "x86_64",
            "python_version": "3.11.5",
            "current_platform": "Linux",
            "available_backends": [],
            "platform_supported": False,
        }
        mock_server_class.get_platform_info.return_value = mock_platform_info

        runner = CliRunner()
        result = runner.invoke(main, ["--info"])

        assert result.exit_code == 0
        assert "System Information:" in result.output
        assert "system: Linux" in result.output
        assert "Current platform: Linux" in result.output
        assert "Platform supported: False" in result.output
        # Should not show supported formats for unsupported platform
        assert "Supported formats:" not in result.output

    @patch("virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer")
    def test_show_system_info_error(self, mock_server_class: Mock) -> None:
        """Test system info display with error."""
        mock_server_class.get_platform_info.side_effect = RuntimeError("Platform error")

        runner = CliRunner()
        result = runner.invoke(main, ["--info"])

        assert result.exit_code == 1
        assert "Error: Platform error" in result.output

    @patch("virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer")
    @patch("virtual_gpu_lut_box.cli.time.sleep")
    def test_start_server_cli_success(
        self, mock_sleep: Mock, mock_server_class: Mock
    ) -> None:
        """Test successful server start."""
        mock_server = Mock()
        mock_server.is_running = True
        mock_server_class.return_value = mock_server

        # Mock sleep to avoid infinite loop, then trigger KeyboardInterrupt
        mock_sleep.side_effect = KeyboardInterrupt()

        runner = CliRunner()
        result = runner.invoke(main, ["--host", "localhost", "--port", "8888"])

        assert result.exit_code == 0
        mock_server_class.assert_called_once_with(
            host="localhost",
            port=8888,
            stream_name="OpenGradeIO-LUT",
            verbose=False,
            info_logging=False,
        )
        mock_server.start.assert_called_once()
        mock_server.stop.assert_called_once()
        assert "Server running. Press Ctrl+C to stop." in result.output
        assert "Stopping server..." in result.output
        assert "Server stopped" in result.output

    @patch("virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer")
    def test_start_server_cli_platform_not_supported(
        self, mock_server_class: Mock
    ) -> None:
        """Test server start with platform not supported error."""
        mock_server_class.side_effect = PlatformNotSupportedError("Linux not supported")

        runner = CliRunner()
        result = runner.invoke(main)

        assert result.exit_code == 1
        assert "Platform error: Linux not supported" in result.output
        assert "GPU texture streaming not supported on this platform" in result.output

    @patch("virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer")
    def test_start_server_cli_server_creation_error(
        self, mock_server_class: Mock
    ) -> None:
        """Test server start with server creation error."""
        mock_server_class.side_effect = RuntimeError("Server creation failed")

        runner = CliRunner()
        result = runner.invoke(main)

        assert result.exit_code == 1
        assert "Error: Server creation failed" in result.output

    @patch("virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer")
    def test_start_server_cli_server_start_error(self, mock_server_class: Mock) -> None:
        """Test server start with server.start() error."""
        mock_server = Mock()
        mock_server.start.side_effect = RuntimeError("Server start failed")
        mock_server_class.return_value = mock_server

        runner = CliRunner()
        result = runner.invoke(main)

        assert result.exit_code == 1
        assert "Error: Server start failed" in result.output
        mock_server.stop.assert_called_once()  # Should still call stop in finally

    @patch("virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer")
    @patch("virtual_gpu_lut_box.cli.time.sleep")
    def test_start_server_cli_server_stops_running(
        self, mock_sleep: Mock, mock_server_class: Mock
    ) -> None:
        """Test server CLI when server stops running naturally."""
        mock_server = Mock()
        # First check returns True, second returns False to exit loop
        mock_server.is_running = True
        mock_server_class.return_value = mock_server

        # Mock sleep to return immediately and change is_running
        def sleep_side_effect(duration):
            mock_server.is_running = False

        mock_sleep.side_effect = sleep_side_effect

        runner = CliRunner()
        result = runner.invoke(main)

        assert result.exit_code == 0
        assert "Server running. Press Ctrl+C to stop." in result.output
        assert "Server stopped" in result.output
        mock_server.stop.assert_called_once()

    def test_start_server_cli_direct_call(self) -> None:
        """Test direct call to start_server_cli function."""
        with patch(
            "virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer"
        ) as mock_server_class:
            mock_server = Mock()
            mock_server.is_running = False  # Exit immediately
            mock_server_class.return_value = mock_server

            # This should not raise an exception
            start_server_cli("localhost", 8765, "TestLUT", False, False)

            mock_server_class.assert_called_once_with(
                host="localhost",
                port=8765,
                stream_name="TestLUT",
                verbose=False,
                info_logging=False,
            )

    def test_show_system_info_direct_call(self) -> None:
        """Test direct call to show_system_info function."""
        with patch(
            "virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer"
        ) as mock_server_class:
            mock_platform_info = {
                "system": "Darwin",
                "current_platform": "Darwin",
                "available_backends": ["Darwin"],
                "platform_supported": True,
                "supported_formats": ["rgb", "rgba"],
            }
            mock_server_class.get_platform_info.return_value = mock_platform_info

            # This should not raise an exception
            show_system_info()

            mock_server_class.get_platform_info.assert_called_once()

    def test_show_system_info_direct_call_error(self) -> None:
        """Test direct call to show_system_info function with error."""
        with patch(
            "virtual_gpu_lut_box.cli.VirtualGPULUTBoxServer"
        ) as mock_server_class:
            mock_server_class.get_platform_info.side_effect = RuntimeError("Test error")

            with pytest.raises(SystemExit) as exc_info:
                show_system_info()

            assert exc_info.value.code == 1
