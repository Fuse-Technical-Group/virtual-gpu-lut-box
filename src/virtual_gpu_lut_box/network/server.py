# SPDX-FileCopyrightText: 2025 Fuse Technical Group
#
# SPDX-License-Identifier: BSD-3-Clause

"""OpenGradeIO virtual LUT box server implementation."""

from __future__ import annotations

import logging
import socket
import threading
from typing import TYPE_CHECKING, Any

import bson

if TYPE_CHECKING:
    from collections.abc import Callable

    import numpy as np
else:
    pass

from .protocol import ProtocolHandler

logger = logging.getLogger(__name__)


class OpenGradeIOServer:
    """TCP server for OpenGradeIO virtual LUT box protocol."""

    DEFAULT_HOST = "0.0.0.0"  # noqa: S104 # nosec B104 - intentionally bind to all interfaces for network access
    DEFAULT_PORT = 8089

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        lut_callback: Callable[[np.ndarray[Any, Any]], None]
        | Callable[[np.ndarray[Any, Any], str | None], None]
        | None = None,
    ) -> None:
        """Initialize OpenGradeIO server.

        Args:
            host: Server host address
            port: Server port number
            lut_callback: Callback function for processed LUT data
        """
        self.host = host
        self.port = port
        self.lut_callback = lut_callback
        self.protocol = ProtocolHandler()

        self._server_socket: socket.socket | None = None
        self._running = False
        self._server_thread: threading.Thread | None = None
        self._client_threads: list[threading.Thread] = []

        # Apply BSON socket patching for easy serialization
        bson.patch_socket()

    def start(self) -> None:
        """Start the server in a background thread."""
        if self._running:
            logger.warning("Server already running")
            return

        self._running = True
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        logger.debug(f"OpenGradeIO server started on {self.host}:{self.port}")

    def stop(self) -> None:
        """Stop the server and all client connections."""
        if not self._running:
            return

        logger.debug("Stopping OpenGradeIO server")
        self._running = False

        # Close server socket
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")

        # Wait for server thread to finish
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)

        # Clean up client threads
        for thread in self._client_threads[:]:
            if thread.is_alive():
                thread.join(timeout=1.0)
        self._client_threads.clear()

        logger.debug("OpenGradeIO server stopped")

    def _run_server(self) -> None:
        """Main server loop."""
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(5)

            logger.debug(
                f"Listening for OpenGradeIO connections on {self.host}:{self.port}"
            )

            while self._running:
                try:
                    # Set timeout so we can check _running periodically
                    self._server_socket.settimeout(1.0)
                    conn, addr = self._server_socket.accept()

                    if not self._running:
                        conn.close()
                        break

                    # Client connection - show in quiet mode
                    print(f"🔌 Client connected from {addr[0]}:{addr[1]}")

                    # Start client handler thread
                    client_thread = threading.Thread(
                        target=self._handle_client, args=(conn, addr), daemon=True
                    )
                    client_thread.start()
                    self._client_threads.append(client_thread)

                    # Clean up finished threads
                    self._client_threads = [
                        t for t in self._client_threads if t.is_alive()
                    ]

                except TimeoutError:
                    continue
                except KeyboardInterrupt:
                    # Gracefully handle keyboard interrupt in accept loop
                    logger.debug("Keyboard interrupt in accept loop")
                    break
                except Exception as e:
                    if self._running:
                        logger.error(f"Error accepting connection: {e}")

        except KeyboardInterrupt:
            # Gracefully handle keyboard interrupt
            logger.debug("Server interrupted by keyboard interrupt")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            if self._server_socket:
                self._server_socket.close()

    def _handle_client(
        self, connection: socket.socket, address: tuple[str, int]
    ) -> None:
        """Handle individual client connection.

        Args:
            connection: Client socket connection
            address: Client address tuple (host, port)
        """
        try:
            while self._running:
                try:
                    # Receive BSON message
                    message = connection.recvobj()  # type: ignore[attr-defined]

                    if not message:
                        break

                    logger.debug(f"Received message from {address[0]}:{address[1]}")

                    # Process message
                    success = self._process_message(message)

                    # Send response
                    response = self.protocol.create_response(success)
                    connection.sendobj(response)  # type: ignore[attr-defined]

                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
                    break

        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            try:
                connection.close()
                # Client disconnection - show in quiet mode
                print(f"🔌 Client {address[0]}:{address[1]} disconnected")
            except Exception as e:
                logger.debug(f"Error during client disconnect cleanup: {e}")

    def _process_message(self, message: dict) -> bool:
        """Process incoming message from OpenGradeIO.

        Args:
            message: Decoded BSON message

        Returns:
            True if processed successfully
        """
        try:
            parsed = self.protocol.parse_message(message)
            if not parsed:
                return False

            command = parsed["command"]
            arguments = parsed["arguments"]
            top_level_metadata = parsed.get("metadata", {})

            if command == "setLUT":
                return self._handle_set_lut(arguments, top_level_metadata)
            if command == "setCDL":
                return self._handle_set_cdl(arguments)
            logger.warning(f"Unhandled command: {command}")
            return False

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return False

    def _handle_set_lut(self, arguments: dict, top_level_metadata: dict) -> bool:
        """Handle setLUT command.

        Args:
            arguments: Command arguments
            top_level_metadata: Top-level message metadata (service, instance, type)

        Returns:
            True if handled successfully
        """
        try:
            # Log detailed protocol info only in verbose mode
            if top_level_metadata:
                logger.debug(f"setLUT top-level metadata: {top_level_metadata}")

            # Log all arguments to see what OpenGradeIO sends (debug only)
            logger.debug("setLUT arguments received:")
            for key, value in arguments.items():
                if key == "lutData":
                    logger.debug(
                        f"  {key}: <binary data, {len(value) if isinstance(value, bytes | bytearray) else 'unknown'} bytes>"
                    )
                else:
                    logger.debug(f"  {key}: {value}")

            result = self.protocol.process_set_lut_command(arguments)
            if result is None:
                return False

            lut_array, metadata = result
            logger.debug(
                f"Processed LUT: shape={lut_array.shape}, dtype={lut_array.dtype}"
            )

            if metadata:
                logger.debug(f"LUT metadata: {metadata}")

            # Call user callback if provided
            if self.lut_callback:
                try:
                    # Extract channel/instance name from top-level metadata
                    channel_name = top_level_metadata.get("instance")

                    logger.debug("Forwarding LUT to streaming callback")
                    # Try new signature first (with channel_name), fall back to old if it fails
                    try:
                        self.lut_callback(lut_array, channel_name)  # type: ignore[misc]
                    except TypeError:
                        # Callback doesn't accept channel_name parameter, use old signature
                        self.lut_callback(lut_array)  # type: ignore[misc]
                    logger.debug("LUT callback completed successfully")
                except Exception as e:
                    logger.error(f"Error in LUT callback: {e}")
                    return False
            else:
                logger.warning("No LUT callback configured - LUT will not be streamed")

            return True

        except Exception as e:
            logger.error(f"Error handling setLUT: {e}")
            return False

    def _handle_set_cdl(self, arguments: dict) -> bool:
        """Handle setCDL command.

        Args:
            arguments: Command arguments

        Returns:
            True if handled successfully
        """
        try:
            logger.debug(f"Received setCDL message with arguments: {arguments}")

            # For now, just log the reception - actual CDL processing can be added later
            logger.debug("setCDL command processed successfully")
            return True

        except Exception as e:
            logger.error(f"Error handling setCDL: {e}")
            return False

    def set_lut_callback(
        self, callback: Callable[[np.ndarray[Any, Any]], None]
    ) -> None:
        """Set callback function for LUT updates.

        Args:
            callback: Function to call with LUT data
        """
        self.lut_callback = callback

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    def __enter__(self) -> OpenGradeIOServer:
        """Enter context manager."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.stop()

    def __repr__(self) -> str:
        """String representation of server."""
        return f"OpenGradeIOServer(host={self.host}, port={self.port})"
