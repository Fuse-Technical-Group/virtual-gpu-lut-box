#!/usr/bin/env python3
"""LiveGrade integration example for virtual-gpu-lut-box."""

import time
from typing import Optional

import numpy as np

from virtual_gpu_lut_box import HaldConverter, LUTGenerator, StreamingFactory


class LiveGradingLUTBox:
    """A LiveGrade-compatible LUT box for real-time color correction streaming."""

    def __init__(self, stream_name: str = "virtual-gpu-lut-box", lut_size: int = 33):
        """Initialize the LUT box.

        Args:
            stream_name: Name for the Spout/Syphon stream
            lut_size: Size of the LUT cube (default: 33)
        """
        self.stream_name = stream_name
        self.lut_size = lut_size

        # Create components
        self.generator = LUTGenerator(lut_size)
        self.converter = HaldConverter(lut_size)
        self.backend: Optional[StreamingFactory] = None

        # LUT parameters
        self.gamma = 1.0
        self.brightness = 0.0
        self.contrast = 1.0
        self.hue_shift = 0.0
        self.saturation = 1.0

        # State
        self.streaming = False
        self.frame_count = 0

    def initialize(self) -> bool:
        """Initialize the streaming backend.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.backend = StreamingFactory.create_lut_streamer(
                self.stream_name, self.lut_size
            )
            return self.backend.initialize()
        except Exception as e:
            print(f"Failed to initialize streaming: {e}")
            return False

    def start_streaming(self, fps: int = 30) -> None:
        """Start streaming LUT updates.

        Args:
            fps: Target frame rate
        """
        if not self.backend or not self.backend.initialized:
            print("Backend not initialized")
            return

        self.streaming = True
        frame_delay = 1.0 / fps

        print(f"Starting LiveGrade LUT streaming at {fps} FPS")
        print(f"Stream name: {self.stream_name}")
        print(f"LUT size: {self.lut_size}x{self.lut_size}x{self.lut_size}")
        print("Press Ctrl+C to stop")

        try:
            while self.streaming:
                start_time = time.time()

                # Generate current LUT
                lut = self.generator.create_custom_lut(
                    gamma=self.gamma,
                    brightness=self.brightness,
                    contrast=self.contrast,
                    hue_shift=self.hue_shift,
                    saturation=self.saturation,
                )

                # Convert to Hald image
                hald_image = self.converter.lut_to_hald(lut)

                # Stream to GPU shader
                if not self.backend.send_lut_texture(hald_image):
                    print("Failed to send frame")
                    break

                self.frame_count += 1

                # Frame timing
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_delay - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

                # Progress indicator
                if self.frame_count % (fps * 10) == 0:  # Every 10 seconds
                    print(f"Streamed {self.frame_count} frames")

        except KeyboardInterrupt:
            print("\\nStopping stream...")
        finally:
            self.streaming = False

    def stop_streaming(self) -> None:
        """Stop streaming."""
        self.streaming = False

    def update_gamma(self, gamma: float) -> None:
        """Update gamma correction.

        Args:
            gamma: Gamma value (> 0)
        """
        if gamma > 0:
            self.gamma = gamma
            print(f"Updated gamma: {gamma}")

    def update_brightness(self, brightness: float) -> None:
        """Update brightness.

        Args:
            brightness: Brightness adjustment (-1 to 1)
        """
        self.brightness = max(-1.0, min(1.0, brightness))
        print(f"Updated brightness: {self.brightness}")

    def update_contrast(self, contrast: float) -> None:
        """Update contrast.

        Args:
            contrast: Contrast multiplier (> 0)
        """
        if contrast > 0:
            self.contrast = contrast
            print(f"Updated contrast: {contrast}")

    def update_hue_shift(self, hue_shift_degrees: float) -> None:
        """Update hue shift.

        Args:
            hue_shift_degrees: Hue shift in degrees
        """
        self.hue_shift = np.radians(hue_shift_degrees)
        print(f"Updated hue shift: {hue_shift_degrees}°")

    def update_saturation(self, saturation: float) -> None:
        """Update saturation.

        Args:
            saturation: Saturation multiplier (>= 0)
        """
        if saturation >= 0:
            self.saturation = saturation
            print(f"Updated saturation: {saturation}")

    def reset_to_identity(self) -> None:
        """Reset all parameters to identity (no correction)."""
        self.gamma = 1.0
        self.brightness = 0.0
        self.contrast = 1.0
        self.hue_shift = 0.0
        self.saturation = 1.0
        print("Reset to identity LUT")

    def apply_preset(self, preset_name: str) -> None:
        """Apply a color correction preset.

        Args:
            preset_name: Name of the preset to apply
        """
        presets = {
            "film_look": {
                "gamma": 2.2,
                "brightness": 0.05,
                "contrast": 1.15,
                "hue_shift": 0.0,
                "saturation": 1.1,
            },
            "vibrant": {
                "gamma": 1.8,
                "brightness": 0.1,
                "contrast": 1.25,
                "hue_shift": 0.0,
                "saturation": 1.3,
            },
            "warm": {
                "gamma": 2.0,
                "brightness": 0.05,
                "contrast": 1.1,
                "hue_shift": np.pi / 12,  # 15 degrees
                "saturation": 1.05,
            },
            "cool": {
                "gamma": 2.0,
                "brightness": 0.0,
                "contrast": 1.05,
                "hue_shift": -np.pi / 12,  # -15 degrees
                "saturation": 1.0,
            },
        }

        if preset_name in presets:
            preset = presets[preset_name]
            self.gamma = preset["gamma"]
            self.brightness = preset["brightness"]
            self.contrast = preset["contrast"]
            self.hue_shift = preset["hue_shift"]
            self.saturation = preset["saturation"]
            print(f"Applied preset: {preset_name}")
        else:
            print(f"Unknown preset: {preset_name}")
            print(f"Available presets: {list(presets.keys())}")

    def get_status(self) -> dict:
        """Get current status and parameters.

        Returns:
            Dictionary with current status
        """
        return {
            "stream_name": self.stream_name,
            "lut_size": self.lut_size,
            "streaming": self.streaming,
            "frame_count": self.frame_count,
            "gamma": self.gamma,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "hue_shift_degrees": np.degrees(self.hue_shift),
            "saturation": self.saturation,
            "backend_initialized": self.backend is not None
            and self.backend.initialized,
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_streaming()
        if self.backend:
            self.backend.cleanup()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


def demo_livegrading_workflow():
    """Demonstrate a typical LiveGrade workflow."""
    print("=== LiveGrade Integration Demo ===")

    # Check platform support
    if not StreamingFactory.is_platform_supported():
        print("Streaming not supported on this platform")
        return

    # Create LUT box (uses default name "virtual-gpu-lut-box")
    lut_box = LiveGradingLUTBox(lut_size=33)

    # Initialize
    if not lut_box.initialize():
        print("Failed to initialize LUT box")
        return

    try:
        # Show initial status
        print("Initial status:")
        for key, value in lut_box.get_status().items():
            print(f"  {key}: {value}")

        # Simulate LiveGrade workflow
        print("\\nSimulating LiveGrade workflow...")

        # 1. Start with identity
        lut_box.reset_to_identity()

        # 2. Apply film look preset
        lut_box.apply_preset("film_look")

        # 3. Fine-tune parameters
        lut_box.update_brightness(0.08)
        lut_box.update_saturation(1.2)

        # 4. Generate and stream a few frames
        print("\\nGenerating sample frames...")
        for i in range(5):
            # Generate LUT
            lut = lut_box.generator.create_custom_lut(
                gamma=lut_box.gamma,
                brightness=lut_box.brightness,
                contrast=lut_box.contrast,
                hue_shift=lut_box.hue_shift,
                saturation=lut_box.saturation,
            )

            # Convert to Hald
            hald_image = lut_box.converter.lut_to_hald(lut)

            # Stream (simulate)
            if lut_box.backend and lut_box.backend.send_lut_texture(hald_image):
                print(f"  Frame {i + 1}: Sent successfully")
            else:
                print(f"  Frame {i + 1}: Failed to send")

            time.sleep(0.1)  # Small delay

        print("\\nFinal status:")
        for key, value in lut_box.get_status().items():
            print(f"  {key}: {value}")

    finally:
        lut_box.cleanup()


def interactive_lut_control():
    """Interactive LUT control example."""
    print("=== Interactive LUT Control ===")

    if not StreamingFactory.is_platform_supported():
        print("Streaming not supported on this platform")
        return

    lut_box = LiveGradingLUTBox("Interactive LUT", lut_size=33)

    if not lut_box.initialize():
        print("Failed to initialize LUT box")
        return

    print("Interactive LUT Control")
    print("Commands:")
    print("  gamma <value>     - Set gamma correction")
    print("  brightness <value> - Set brightness (-1 to 1)")
    print("  contrast <value>   - Set contrast (> 0)")
    print("  hue <degrees>      - Set hue shift in degrees")
    print("  saturation <value> - Set saturation (>= 0)")
    print("  preset <name>      - Apply preset (film_look, vibrant, warm, cool)")
    print("  reset             - Reset to identity")
    print("  status            - Show current status")
    print("  stream <fps>      - Start streaming at FPS")
    print("  stop              - Stop streaming")
    print("  quit              - Exit")

    try:
        while True:
            command = input("\\n> ").strip().lower()

            if command.startswith("gamma "):
                try:
                    value = float(command.split()[1])
                    lut_box.update_gamma(value)
                except (ValueError, IndexError):
                    print("Usage: gamma <value>")

            elif command.startswith("brightness "):
                try:
                    value = float(command.split()[1])
                    lut_box.update_brightness(value)
                except (ValueError, IndexError):
                    print("Usage: brightness <value>")

            elif command.startswith("contrast "):
                try:
                    value = float(command.split()[1])
                    lut_box.update_contrast(value)
                except (ValueError, IndexError):
                    print("Usage: contrast <value>")

            elif command.startswith("hue "):
                try:
                    value = float(command.split()[1])
                    lut_box.update_hue_shift(value)
                except (ValueError, IndexError):
                    print("Usage: hue <degrees>")

            elif command.startswith("saturation "):
                try:
                    value = float(command.split()[1])
                    lut_box.update_saturation(value)
                except (ValueError, IndexError):
                    print("Usage: saturation <value>")

            elif command.startswith("preset "):
                try:
                    preset_name = command.split()[1]
                    lut_box.apply_preset(preset_name)
                except IndexError:
                    print("Usage: preset <name>")

            elif command == "reset":
                lut_box.reset_to_identity()

            elif command == "status":
                for key, value in lut_box.get_status().items():
                    print(f"  {key}: {value}")

            elif command.startswith("stream "):
                try:
                    fps = int(command.split()[1])
                    print(f"Starting stream at {fps} FPS (press Ctrl+C to stop)...")
                    lut_box.start_streaming(fps)
                except (ValueError, IndexError):
                    print("Usage: stream <fps>")
                except KeyboardInterrupt:
                    print("\\nStopped streaming")

            elif command == "stop":
                lut_box.stop_streaming()

            elif command == "quit":
                break

            else:
                print("Unknown command")

    except KeyboardInterrupt:
        print("\\nExiting...")
    finally:
        lut_box.cleanup()


def main():
    """Main function."""
    print("Virtual GPU LUT Box - LiveGrade Integration Examples")
    print("=" * 60)

    # Run demo
    demo_livegrading_workflow()

    # Ask if user wants interactive mode
    try:
        response = input("\\nRun interactive mode? (y/n): ").strip().lower()
        if response == "y":
            interactive_lut_control()
    except KeyboardInterrupt:
        print("\\nExiting...")


if __name__ == "__main__":
    main()
