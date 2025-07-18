"""Tests for network protocol module."""

import numpy as np
import pytest

from virtual_gpu_lut_box.network.protocol import ProtocolHandler


class TestProtocolHandler:
    """Test cases for ProtocolHandler class."""

    def test_init(self) -> None:
        """Test protocol handler initialization."""
        handler = ProtocolHandler()

        assert handler.supported_commands == {"setLUT", "setCDL"}

    def test_parse_message_valid_setLUT(self) -> None:
        """Test parsing valid setLUT message."""
        handler = ProtocolHandler()

        message = {
            "command": "setLUT",
            "service": "OpenGradeIO",
            "instance": "test_instance",
            "type": "3dlut",
            "arguments": {"lutData": b"some_lut_data", "channel": "main"},
        }

        result = handler.parse_message(message)

        assert result is not None
        assert result["command"] == "setLUT"
        assert result["arguments"]["channel"] == "main"
        assert "lutData" in result["arguments"]
        assert result["metadata"]["service"] == "OpenGradeIO"
        assert result["metadata"]["instance"] == "test_instance"

    def test_parse_message_valid_setCDL(self) -> None:
        """Test parsing valid setCDL message."""
        handler = ProtocolHandler()

        message = {
            "command": "setCDL",
            "service": "OpenGradeIO",
            "arguments": {
                "slope": [1.0, 1.0, 1.0],
                "offset": [0.0, 0.0, 0.0],
                "power": [1.0, 1.0, 1.0],
            },
        }

        result = handler.parse_message(message)

        assert result is not None
        assert result["command"] == "setCDL"
        assert result["arguments"]["slope"] == [1.0, 1.0, 1.0]

    def test_parse_message_non_dict(self) -> None:
        """Test parsing non-dict message."""
        handler = ProtocolHandler()

        result = handler.parse_message("not a dict")

        assert result is None

    def test_parse_message_missing_command(self) -> None:
        """Test parsing message missing command field."""
        handler = ProtocolHandler()

        message = {"service": "OpenGradeIO", "arguments": {}}

        result = handler.parse_message(message)

        assert result is None

    def test_parse_message_unsupported_command(self) -> None:
        """Test parsing message with unsupported command."""
        handler = ProtocolHandler()

        message = {"command": "unsupported_command", "arguments": {}}

        result = handler.parse_message(message)

        assert result is None

    def test_parse_message_empty_arguments(self) -> None:
        """Test parsing message with empty arguments."""
        handler = ProtocolHandler()

        message = {"command": "setLUT", "service": "OpenGradeIO"}

        result = handler.parse_message(message)

        assert result is not None
        assert result["arguments"] == {}

    def test_parse_message_with_metadata(self) -> None:
        """Test parsing message with various metadata fields."""
        handler = ProtocolHandler()

        message = {
            "command": "setLUT",
            "service": "OpenGradeIO",
            "instance": "instance1",
            "type": "3dlut",
            "version": "1.0",
            "timestamp": 1234567890,
            "arguments": {"lutData": b"test_data"},
        }

        result = handler.parse_message(message)

        assert result is not None
        metadata = result["metadata"]
        assert metadata["service"] == "OpenGradeIO"
        assert metadata["instance"] == "instance1"
        assert metadata["type"] == "3dlut"
        assert metadata["version"] == "1.0"
        assert metadata["timestamp"] == 1234567890
        # Should not include command and arguments in metadata
        assert "command" not in metadata
        assert "arguments" not in metadata

    def test_process_set_lut_command_valid(self) -> None:
        """Test processing valid setLUT command."""
        handler = ProtocolHandler()

        # Create valid LUT data for 4x4x4 LUT with RGBA
        lut_size = 4
        rgba_data = np.random.rand(lut_size**3, 4).astype(np.float32)
        lut_bytes = rgba_data.tobytes()

        arguments = {"lutData": lut_bytes, "channel": "main", "lutSize": lut_size}

        result = handler.process_set_lut_command(arguments)

        assert result is not None
        lut_array, metadata = result
        assert lut_array.shape == (
            lut_size,
            lut_size,
            lut_size,
            4,
        )  # RGBA (alpha is not uniform)
        assert metadata["channel"] == "main"
        assert metadata["lutSize"] == lut_size

    def test_process_set_lut_command_missing_lutData(self) -> None:
        """Test processing setLUT command missing lutData."""
        handler = ProtocolHandler()

        arguments = {"channel": "main"}

        result = handler.process_set_lut_command(arguments)

        assert result is None

    def test_process_set_lut_command_invalid_data(self) -> None:
        """Test processing setLUT command with invalid data."""
        handler = ProtocolHandler()

        arguments = {"lutData": b"invalid_data", "channel": "main"}

        result = handler.process_set_lut_command(arguments)

        assert result is None

    def test_convert_lut_data_valid_rgb(self) -> None:
        """Test converting valid LUT data (RGB)."""
        handler = ProtocolHandler()

        # Create 4x4x4 LUT with uniform alpha (should become RGB)
        lut_size = 4
        rgba_data = np.random.rand(lut_size**3, 4).astype(np.float32)
        rgba_data[:, 3] = 1.0  # Set alpha to 1.0
        lut_bytes = rgba_data.tobytes()

        result = handler._convert_lut_data(lut_bytes)

        assert result.shape == (lut_size, lut_size, lut_size, 3)
        assert result.dtype == np.float32

    def test_convert_lut_data_valid_rgba(self) -> None:
        """Test converting valid LUT data (RGBA)."""
        handler = ProtocolHandler()

        # Create 4x4x4 LUT with meaningful alpha
        lut_size = 4
        rgba_data = np.random.rand(lut_size**3, 4).astype(np.float32)
        rgba_data[:, 3] = np.random.rand(lut_size**3)  # Random alpha values
        lut_bytes = rgba_data.tobytes()

        result = handler._convert_lut_data(lut_bytes)

        assert result.shape == (lut_size, lut_size, lut_size, 4)
        assert result.dtype == np.float32

    def test_convert_lut_data_invalid_size(self) -> None:
        """Test converting LUT data with invalid size."""
        handler = ProtocolHandler()

        # Create data that's not a perfect cube
        invalid_data = np.random.rand(100, 4).astype(np.float32)
        lut_bytes = invalid_data.tobytes()

        with pytest.raises(ValueError, match="Invalid LUT data size"):
            handler._convert_lut_data(lut_bytes)

    def test_convert_lut_data_size_mismatch(self) -> None:
        """Test converting LUT data with size mismatch."""
        handler = ProtocolHandler()

        # Create 4x4x4 LUT but claim it's 8x8x8
        lut_size = 4
        rgba_data = np.random.rand(lut_size**3, 4).astype(np.float32)
        lut_bytes = rgba_data.tobytes()

        with pytest.raises(ValueError, match="LUT size mismatch"):
            handler._convert_lut_data(lut_bytes, explicit_size=8)

    def test_convert_lut_data_preserves_precision(self) -> None:
        """Test that LUT conversion preserves precision."""
        handler = ProtocolHandler()

        # Create LUT with values outside [0,1] range
        lut_size = 4
        rgba_data = np.random.rand(lut_size**3, 4).astype(np.float32)
        rgba_data[:, 3] = 1.0  # Uniform alpha
        rgba_data[0, 0] = -0.5  # Negative value
        rgba_data[1, 1] = 2.0  # Value > 1
        lut_bytes = rgba_data.tobytes()

        result = handler._convert_lut_data(lut_bytes)

        # Should preserve out-of-range values
        assert np.any(result < 0)
        assert np.any(result > 1)

    def test_create_response_success(self) -> None:
        """Test creating successful response."""
        handler = ProtocolHandler()

        response = handler.create_response(success=True)

        assert response == {"result": 1}

    def test_create_response_failure(self) -> None:
        """Test creating failure response."""
        handler = ProtocolHandler()

        response = handler.create_response(success=False, error="Test error")

        assert response == {"result": 0, "error": "Test error"}

    def test_create_response_failure_no_error(self) -> None:
        """Test creating failure response without error message."""
        handler = ProtocolHandler()

        response = handler.create_response(success=False)

        assert response == {"result": 0, "error": "Unknown error"}

    def test_supported_commands_property(self) -> None:
        """Test supported_commands property."""
        handler = ProtocolHandler()

        assert "setLUT" in handler.supported_commands
        assert "setCDL" in handler.supported_commands
        assert len(handler.supported_commands) >= 2

    def test_parse_message_none_input(self) -> None:
        """Test parsing None input."""
        handler = ProtocolHandler()

        result = handler.parse_message(None)

        assert result is None

    def test_parse_message_empty_dict(self) -> None:
        """Test parsing empty dict."""
        handler = ProtocolHandler()

        result = handler.parse_message({})

        assert result is None

    def test_convert_lut_data_various_sizes(self) -> None:
        """Test converting LUT data with various valid sizes."""
        handler = ProtocolHandler()

        for lut_size in [8, 16, 32, 64]:
            rgba_data = np.random.rand(lut_size**3, 4).astype(np.float32)
            rgba_data[:, 3] = 1.0  # Uniform alpha
            lut_bytes = rgba_data.tobytes()

            result = handler._convert_lut_data(lut_bytes)

            assert result.shape == (lut_size, lut_size, lut_size, 3)
            assert result.dtype == np.float32

    def test_metadata_extraction(self) -> None:
        """Test metadata extraction from arguments."""
        handler = ProtocolHandler()

        # Create valid LUT data
        lut_size = 4
        rgba_data = np.random.rand(lut_size**3, 4).astype(np.float32)
        rgba_data[:, 3] = 1.0
        lut_bytes = rgba_data.tobytes()

        arguments = {
            "lutData": lut_bytes,
            "channel": "main",
            "lutSize": lut_size,
            "customField": "customValue",
        }

        result = handler.process_set_lut_command(arguments)

        assert result is not None
        lut_array, metadata = result
        assert "lutData" not in metadata  # Should be excluded
        assert metadata["channel"] == "main"
        assert metadata["lutSize"] == lut_size
        assert metadata["customField"] == "customValue"
