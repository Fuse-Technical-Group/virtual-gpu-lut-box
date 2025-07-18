"""Tests for network server module."""

import socket
import threading
import time
from unittest.mock import Mock, patch

from virtual_gpu_lut_box.network.server import OpenGradeIOServer


class TestOpenGradeIOServer:
    """Test cases for OpenGradeIOServer class."""

    def test_init_default_values(self) -> None:
        """Test server initialization with default values."""
        server = OpenGradeIOServer()

        assert server.host == "127.0.0.1"
        assert server.port == 8089
        assert server.lut_callback is None
        assert server.protocol is not None
        assert server._server_socket is None
        assert server._running is False

    def test_init_custom_values(self) -> None:
        """Test server initialization with custom values."""
        mock_callback = Mock()
        server = OpenGradeIOServer(
            host="192.168.1.100", port=9999, lut_callback=mock_callback
        )

        assert server.host == "192.168.1.100"
        assert server.port == 9999
        assert server.lut_callback is mock_callback
        assert server.protocol is not None

    def test_default_port_constant(self) -> None:
        """Test DEFAULT_PORT constant."""
        assert OpenGradeIOServer.DEFAULT_PORT == 8089

    @patch("virtual_gpu_lut_box.network.server.socket.socket")
    def test_start_server_success(self, mock_socket_class: Mock) -> None:
        """Test successful server start."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        server = OpenGradeIOServer()

        # Mock socket operations
        mock_socket.bind.return_value = None
        mock_socket.listen.return_value = None

        # Start server in thread to avoid blocking
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()

        # Give it a moment to start
        time.sleep(0.1)

        # Verify socket configuration
        mock_socket.setsockopt.assert_called_with(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )
        mock_socket.bind.assert_called_with(("127.0.0.1", 8089))
        mock_socket.listen.assert_called_with(5)

        # Stop server
        server.stop()
        server_thread.join(timeout=1)

    @patch("virtual_gpu_lut_box.network.server.socket.socket")
    def test_start_server_bind_error(self, mock_socket_class: Mock) -> None:
        """Test server start with bind error."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        # Mock bind to raise OSError
        mock_socket.bind.side_effect = OSError("Address already in use")

        server = OpenGradeIOServer()

        # Start server in thread since it runs in background
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()

        # Give it time to hit the bind error
        time.sleep(0.1)

        server.stop()
        server_thread.join(timeout=1)

    @patch("virtual_gpu_lut_box.network.server.socket.socket")
    def test_start_server_listen_error(self, mock_socket_class: Mock) -> None:
        """Test server start with listen error."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        # Mock listen to raise OSError
        mock_socket.listen.side_effect = OSError("Listen failed")

        server = OpenGradeIOServer()

        # Start server in thread since it runs in background
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()

        # Give it time to hit the listen error
        time.sleep(0.1)

        server.stop()
        server_thread.join(timeout=1)

    def test_stop_server_not_running(self) -> None:
        """Test stopping server when not running."""
        server = OpenGradeIOServer()

        # Should not raise exception
        server.stop()

        assert server._running is False

    @patch("virtual_gpu_lut_box.network.server.socket.socket")
    def test_stop_server_running(self, mock_socket_class: Mock) -> None:
        """Test stopping running server."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        server = OpenGradeIOServer()
        server._server_socket = mock_socket
        server._running = True

        server.stop()

        assert server._running is False
        mock_socket.close.assert_called_once()

    def test_is_running_property(self) -> None:
        """Test is_running property."""
        server = OpenGradeIOServer()

        assert server.is_running is False

        server._running = True
        assert server.is_running is True

        server._running = False
        assert server.is_running is False

    @patch("virtual_gpu_lut_box.network.server.socket.socket")
    def test_handle_client_connection_success(self, mock_socket_class: Mock) -> None:
        """Test handling client connection successfully."""
        mock_server_socket = Mock()
        mock_client_socket = Mock()
        mock_socket_class.return_value = mock_server_socket

        # Mock accept to return client socket
        mock_server_socket.accept.return_value = (
            mock_client_socket,
            ("127.0.0.1", 12345),
        )

        # Mock BSON socket methods - first call returns message, second returns None to exit
        mock_client_socket.recvobj.side_effect = [
            {"command": "setLUT", "arguments": {}},
            None,
        ]
        mock_client_socket.sendobj.return_value = None

        server = OpenGradeIOServer()
        server._server_socket = mock_server_socket
        server._running = True  # Set to True initially

        # Mock the protocol handler and socket methods
        with patch.object(server, "_process_message") as mock_process_message:
            mock_process_message.return_value = True

            # This would be called internally by the accept loop
            server._handle_client(mock_client_socket, ("127.0.0.1", 12345))

            # Should have called process_message for each received message
            mock_process_message.assert_called_once_with(
                {"command": "setLUT", "arguments": {}}
            )

    @patch("virtual_gpu_lut_box.network.server.socket.socket")
    def test_handle_client_connection_error(self, mock_socket_class: Mock) -> None:
        """Test handling client connection with error."""
        mock_server_socket = Mock()
        mock_client_socket = Mock()
        mock_socket_class.return_value = mock_server_socket

        # Mock BSON socket methods to raise exception
        mock_client_socket.recvobj.side_effect = Exception("Client handling error")

        server = OpenGradeIOServer()
        server._server_socket = mock_server_socket
        server._running = False  # Set to False to exit the loop quickly

        # Should not raise exception, just log error
        server._handle_client(mock_client_socket, ("127.0.0.1", 12345))

        # Should close the client socket
        mock_client_socket.close.assert_called_once()

    @patch("virtual_gpu_lut_box.network.server.socket.socket")
    def test_server_context_manager(self, mock_socket_class: Mock) -> None:
        """Test server as context manager."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        server = OpenGradeIOServer()

        with server as ctx_server:
            assert ctx_server is server
            # Server should be started
            mock_socket.bind.assert_called_once()
            mock_socket.listen.assert_called_once()

        # Server should be stopped
        assert server._running is False

    def test_repr(self) -> None:
        """Test string representation of server."""
        server = OpenGradeIOServer(host="localhost", port=8080)

        repr_str = repr(server)
        assert "OpenGradeIOServer" in repr_str
        assert "localhost" in repr_str
        assert "8080" in repr_str

    def test_callback_parameter_handling(self) -> None:
        """Test different callback parameter configurations."""
        # Test with no callback
        server1 = OpenGradeIOServer()
        assert server1.lut_callback is None

        # Test with callback
        callback = Mock()
        server2 = OpenGradeIOServer(lut_callback=callback)
        assert server2.lut_callback is callback

    @patch("virtual_gpu_lut_box.network.server.socket.socket")
    def test_socket_reuse_configuration(self, mock_socket_class: Mock) -> None:
        """Test socket reuse configuration."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        server = OpenGradeIOServer()

        # Start server to trigger socket configuration
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()

        time.sleep(0.1)

        # Check that SO_REUSEADDR was set
        mock_socket.setsockopt.assert_called_with(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )

        server.stop()
        server_thread.join(timeout=1)

    def test_server_properties(self) -> None:
        """Test server properties."""
        server = OpenGradeIOServer(host="example.com", port=9090)

        assert server.host == "example.com"
        assert server.port == 9090
        assert hasattr(server, "protocol")
        assert hasattr(server, "lut_callback")
        assert hasattr(server, "_server_socket")
        assert hasattr(server, "_running")

    @patch("virtual_gpu_lut_box.network.server.socket.socket")
    def test_accept_loop_keyboard_interrupt(self, mock_socket_class: Mock) -> None:
        """Test accept loop with keyboard interrupt."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        # Mock accept to raise KeyboardInterrupt
        mock_socket.accept.side_effect = KeyboardInterrupt()

        server = OpenGradeIOServer()

        # Should handle KeyboardInterrupt gracefully
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()

        time.sleep(0.1)

        # Should not raise exception
        server.stop()
        server_thread.join(timeout=1)

    @patch("virtual_gpu_lut_box.network.server.socket.socket")
    def test_accept_loop_socket_error(self, mock_socket_class: Mock) -> None:
        """Test accept loop with socket error."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        # Mock accept to raise socket error
        mock_socket.accept.side_effect = OSError("Accept failed")

        server = OpenGradeIOServer()

        # Should handle socket error gracefully
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()

        time.sleep(0.1)

        # Should not raise exception
        server.stop()
        server_thread.join(timeout=1)
