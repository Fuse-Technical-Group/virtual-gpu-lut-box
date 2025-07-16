#!/usr/bin/env python3

import signal
import sys
import time
import Metal
import numpy as np
from syphon import SyphonMetalServer

def create_static_texture(device, width=512, height=512):
    """Create a static test Metal texture."""
    # Create texture descriptor
    texture_desc = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
        Metal.MTLPixelFormatRGBA8Unorm, width, height, False
    )
    texture_desc.setUsage_(Metal.MTLTextureUsageShaderWrite | Metal.MTLTextureUsageShaderRead)
    
    # Create the texture
    texture = device.newTextureWithDescriptor_(texture_desc)
    
    # Generate static test pattern
    data = np.zeros((height, width, 4), dtype=np.uint8)
    
    for y in range(height):
        for x in range(width):
            # Create static pattern
            r = int(255 * (x / width))
            g = int(255 * (y / height))
            b = int(255 * ((x + y) / (width + height)))
            a = 255
            
            data[y, x] = [r, g, b, a]
    
    # Upload data to texture
    region = Metal.MTLRegion(Metal.MTLOrigin(0, 0, 0), Metal.MTLSize(width, height, 1))
    texture.replaceRegion_mipmapLevel_withBytes_bytesPerRow_(
        region, 0, data.tobytes(), width * 4
    )
    
    return texture

def run_continuous_syphon_server():
    """Run Syphon Metal server continuously until interrupted."""
    
    server = None
    
    def signal_handler(sig, frame):
        print("\n🛑 Interrupt received, stopping server...")
        if server:
            server.stop()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create Metal device
        device = Metal.MTLCreateSystemDefaultDevice()
        if device is None:
            print("❌ No Metal device available")
            return False
        
        print(f"✅ Metal device: {device.name()}")
        
        # Create command queue
        command_queue = device.newCommandQueue()
        if command_queue is None:
            print("❌ Failed to create Metal command queue")
            return False
        
        print("✅ Metal command queue created")
        
        # Create Syphon Metal server
        server = SyphonMetalServer("VirtualGPU-LUT-Box", device=device, command_queue=command_queue)
        print("✅ Syphon Metal server created successfully")
        
        # Create static texture once
        texture = create_static_texture(device)
        print("✅ Static test texture created")
        print("📡 Publishing frames at ~60fps... Press Ctrl+C to stop")
        
        frame_count = 0
        last_client_check = time.time()
        start_time = time.time()
        
        while True:
            frame_start = time.time()
            
            # Publish the same frame
            server.publish_frame_texture(texture)
            
            # Check for clients and show FPS periodically
            current_time = time.time()
            if current_time - last_client_check > 2.0:  # Check every 2 seconds
                elapsed = current_time - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                has_clients = server.has_clients
                print(f"📊 Frame {frame_count}, FPS: {fps:.1f}, Clients: {has_clients}")
                last_client_check = current_time
            
            frame_count += 1
            
            # Target 60 FPS with precise timing
            target_frame_time = 1.0 / 60.0
            frame_time = time.time() - frame_start
            sleep_time = max(0, target_frame_time - frame_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
    except Exception as e:
        print(f"❌ Error running Syphon Metal server: {e}")
        return False
    finally:
        if server:
            server.stop()
            print("✅ Syphon Metal server stopped")
    
    return True

if __name__ == "__main__":
    print("🎥 Starting continuous Syphon Metal server...")
    run_continuous_syphon_server()