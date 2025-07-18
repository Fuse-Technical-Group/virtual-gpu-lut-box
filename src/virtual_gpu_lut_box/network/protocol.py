"""Protocol handler for OpenGradeIO BSON messages."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np
else:
    import numpy as np

logger = logging.getLogger(__name__)


class ProtocolHandler:
    """Handle OpenGradeIO BSON protocol messages."""

    def __init__(self) -> None:
        """Initialize protocol handler."""
        self.supported_commands = {"setLUT", "setCDL"}

    def parse_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Parse incoming BSON message from OpenGradeIO.

        Args:
            message: BSON decoded message dictionary

        Returns:
            Parsed command data or None if invalid
        """
        if not isinstance(message, dict):
            logger.warning(f"Received non-dict message: {type(message)}")
            return None

        command = message.get("command")
        if not command:
            logger.warning(f"Message missing command field: {message}")
            return None

        if command not in self.supported_commands:
            logger.warning(f"Unsupported command: {command}")
            return None

        arguments = message.get("arguments", {})

        # Extract top-level metadata (service, instance, type, etc.)
        top_level_metadata = {
            k: v for k, v in message.items() if k not in ["command", "arguments"]
        }

        return {
            "command": command,
            "arguments": arguments,
            "metadata": top_level_metadata,
        }

    def process_set_lut_command(
        self, arguments: dict[str, Any]
    ) -> tuple[np.ndarray[Any, Any], dict[str, Any]] | None:
        """Process setLUT command and convert LUT data.

        Args:
            arguments: Command arguments containing lutData

        Returns:
            Tuple of (converted LUT array, metadata dict) or None if invalid
        """
        lut_data = arguments.get("lutData")
        if lut_data is None:
            logger.error("setLUT command missing lutData")
            return None

        try:
            # Get explicit LUT size if provided for validation
            explicit_lut_size = arguments.get("lutSize")

            lut_array = self._convert_lut_data(lut_data, explicit_lut_size)

            # Extract metadata (everything except lutData)
            metadata = {k: v for k, v in arguments.items() if k != "lutData"}

            return lut_array, metadata
        except Exception as e:
            logger.error(f"Failed to convert LUT data: {e}")
            return None

    def _convert_lut_data(
        self, lut_data: bytes, explicit_size: int | None = None
    ) -> np.ndarray:
        """Convert raw LUT data to our internal format.

        OpenGradeIO sends float RGBA data as bytes. For a 32x32x32 LUT:
        - Size: 32*32*32*4*4 = 524,288 bytes
        - Format: float32 RGBA values

        Args:
            lut_data: Raw bytes from OpenGradeIO

        Returns:
            LUT array with shape (size, size, size, 3)
        """
        # Convert bytes to float32 array
        float_array = np.frombuffer(lut_data, dtype=np.float32)

        # Determine LUT size from data length
        # Expected format: size^3 * 4 channels * 4 bytes per float
        total_values = len(float_array)
        values_per_channel = total_values // 4  # RGBA = 4 channels

        # Calculate cube size (should be perfect cube root)
        lut_size = round(values_per_channel ** (1 / 3))

        if lut_size**3 != values_per_channel:
            raise ValueError(
                f"Invalid LUT data size: {total_values} values, expected cube"
            )

        # Validate against explicit size if provided
        if explicit_size is not None and lut_size != explicit_size:
            raise ValueError(
                f"LUT size mismatch: calculated {lut_size} from data, but lutSize field says {explicit_size}"
            )

        logger.debug(
            f"Processing {lut_size}x{lut_size}x{lut_size} LUT ({len(lut_data)} bytes)"
        )

        # Reshape to (size^3, 4) for RGBA
        rgba_data = float_array.reshape(-1, 4)

        # Preserve original channel count - check if alpha channel contains meaningful data
        # If all alpha values are 1.0, we can treat this as RGB data
        alpha_channel = rgba_data[:, 3]
        has_meaningful_alpha = not np.allclose(alpha_channel, 1.0, rtol=1e-6)

        if has_meaningful_alpha:
            # Keep all 4 channels (RGBA)
            lut_3d = rgba_data.reshape(lut_size, lut_size, lut_size, 4)
            logger.debug("Preserving RGBA channels (alpha contains data)")
        else:
            # Use only RGB channels for efficiency
            rgb_data = rgba_data[:, :3]
            lut_3d = rgb_data.reshape(lut_size, lut_size, lut_size, 3)
            logger.debug("Using RGB channels only (alpha is uniform 1.0)")

        # Preserve exact float32 precision - do NOT clip or convert
        # HDR and creative LUTs may have values outside [0,1] range
        lut_3d = lut_3d.astype(np.float32)

        return lut_3d

    def create_response(
        self, success: bool = True, error: str | None = None
    ) -> dict[str, Any]:
        """Create response message for OpenGradeIO.

        Args:
            success: Whether operation was successful
            error: Error message if failed

        Returns:
            Response dictionary for BSON encoding
        """
        if success:
            return {"result": 1}
        return {"result": 0, "error": error or "Unknown error"}
