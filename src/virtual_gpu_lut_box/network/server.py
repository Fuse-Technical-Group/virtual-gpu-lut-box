"""OpenGradeIO virtual LUT box server implementation."""

from __future__ import annotations

import logging
import socket
import threading
from typing import TYPE_CHECKING, Any, Callable

import bson

if TYPE_CHECKING:
    import numpy as np
else:
    pass

from .protocol import ProtocolHandler

logger = logging.getLogger(__name__)


class OpenGradeIOServer:
    """TCP server for OpenGradeIO virtual LUT box protocol."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8089,
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
        logger.info("OpenGradeIO server started on %s:%d", self.host, self.port)

    def stop(self) -> None:
        """Stop the server and all client connections."""
        if not self._running:
            return

        logger.info("Stopping OpenGradeIO server")
        self._running = False

        # Close server socket
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception as e:
                logger.error("Error closing server socket: %s", e)

        # Wait for server thread to finish
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)

        # Clean up client threads
        for thread in self._client_threads[:]:
            if thread.is_alive():
                thread.join(timeout=1.0)
        self._client_threads.clear()

        logger.info("OpenGradeIO server stopped")

    def _run_server(self) -> None:
        """Main server loop."""
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(5)

            logger.info(
                "Listening for OpenGradeIO connections on %s:%d", self.host, self.port
            )

            while self._running:
                try:
                    # Set timeout so we can check _running periodically
                    self._server_socket.settimeout(1.0)
                    conn, addr = self._server_socket.accept()

                    if not self._running:
                        conn.close()
                        break

                    logger.info(
                        "OpenGradeIO client connected from %s:%d", addr[0], addr[1]
                    )

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

                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        logger.error("Error accepting connection: %s", e)

        except Exception as e:
            logger.error("Server error: %s", e)
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

                    logger.debug("Received message from %s:%d", address[0], address[1])

                    # Process message
                    success = self._process_message(message)

                    # Send response
                    response = self.protocol.create_response(success)
                    connection.sendobj(response)  # type: ignore[attr-defined]

                except Exception as e:
                    logger.error("Error handling client message: %s", e)
                    break

        except Exception as e:
            logger.error("Client handler error: %s", e)
        finally:
            try:
                connection.close()
                logger.info("Client %s:%d disconnected", address[0], address[1])
            except Exception as e:
                logger.debug("Error during client disconnect cleanup: %s", e)

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
            logger.warning("Unhandled command: %s", command)
            return False

        except Exception as e:
            logger.error("Error processing message: %s", e)
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
            # Log top-level metadata
            if top_level_metadata:
                logger.info("setLUT top-level metadata: %s", top_level_metadata)

            # Log all arguments to see what OpenGradeIO sends
            logger.info("setLUT arguments received:")
            for key, value in arguments.items():
                if key == "lutData":
                    logger.info(
                        "  %s: <binary data, %d bytes>",
                        key,
                        len(value)
                        if isinstance(value, (bytes, bytearray))
                        else "unknown",
                    )
                else:
                    logger.info("  %s: %s", key, value)

            result = self.protocol.process_set_lut_command(arguments)
            if result is None:
                return False

            lut_array, metadata = result
            logger.info(
                "Processed LUT: shape=%s, dtype=%s", lut_array.shape, lut_array.dtype
            )

            if metadata:
                logger.info("LUT metadata: %s", metadata)

            # Call user callback if provided
            if self.lut_callback:
                try:
                    # Extract channel/instance name from top-level metadata
                    channel_name = top_level_metadata.get("instance")

                    logger.info("Forwarding LUT to streaming callback")
                    # Try new signature first (with channel_name), fall back to old if it fails
                    try:
                        self.lut_callback(lut_array, channel_name)  # type: ignore[misc]
                    except TypeError:
                        # Callback doesn't accept channel_name parameter, use old signature
                        self.lut_callback(lut_array)  # type: ignore[misc]
                    logger.info("LUT callback completed successfully")
                except Exception as e:
                    logger.error("Error in LUT callback: %s", e)
                    return False
            else:
                logger.warning("No LUT callback configured - LUT will not be streamed")

            return True

        except Exception as e:
            logger.error("Error handling setLUT: %s", e)
            return False

    def _handle_set_cdl(self, arguments: dict) -> bool:
        """Handle setCDL command.

        Args:
            arguments: Command arguments

        Returns:
            True if handled successfully
        """
        try:
            logger.info("Received setCDL message with arguments: %s", arguments)

            # For now, just log the reception - actual CDL processing can be added later
            logger.info("setCDL command processed successfully")
            return True

        except Exception as e:
            logger.error("Error handling setCDL: %s", e)
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
