import socket
import threading
import time
import pickle
import struct
from PIL import ImageGrab
import cv2
import numpy as np
import mss  # More efficient screen capture

class ScreenShareClient:
    def __init__(self):
        self.client_socket = None
        self.connected = False
        self.streaming = False
        self.use_mss = True  # Use MSS for faster screen capture
        self.sct = None
        self.frame_count = 0
        self.start_time = None
        
    def connect_to_server(self, host, port):
        """Connect to the server"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Optimize socket settings
            self.client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            self.client_socket.connect((host, port))
            self.connected = True
            print(f"Connected to server at {host}:{port}")
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
    
    def init_screen_capture(self):
        """Initialize screen capture method"""
        try:
            import mss
            self.sct = mss.mss()
            self.use_mss = True
            print("Using MSS for screen capture (faster)")
        except ImportError:
            print("MSS not available, using PIL (slower). Install with: pip install mss")
            self.use_mss = False
    
    def capture_screen_mss(self):
        """Capture screen using MSS (faster method)"""
        try:
            # Capture the primary monitor
            monitor = self.sct.monitors[1]  # Primary monitor
            screenshot = self.sct.grab(monitor)
            
            # Convert to numpy array directly
            frame = np.array(screenshot)
            
            # Remove alpha channel if present and convert BGRA to BGR
            if frame.shape[2] == 4:
                frame = frame[:, :, :3]
            
            return frame
        except Exception as e:
            print(f"Error with MSS capture: {e}")
            return None
    
    def capture_screen_pil(self):
        """Capture screen using PIL (fallback method)"""
        try:
            screenshot = ImageGrab.grab()
            frame = np.array(screenshot)
            # Convert RGB to BGR for OpenCV
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame
        except Exception as e:
            print(f"Error with PIL capture: {e}")
            return None
    
    def capture_screen(self):
        """Capture the screen and return as compressed image data"""
        try:
            # Use appropriate capture method
            if self.use_mss and self.sct:
                frame = self.capture_screen_mss()
            else:
                frame = self.capture_screen_pil()
            
            if frame is None:
                return None
            
            # Resize frame to reduce bandwidth
            height, width = frame.shape[:2]
            new_width = min(1280, width)
            new_height = int(height * (new_width / width))
            
            # Use faster interpolation for resizing
            if new_width != width:
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
            # Compress the frame with optimized settings
            encode_param = [
                int(cv2.IMWRITE_JPEG_QUALITY), 75,  # Slightly lower quality for speed
                int(cv2.IMWRITE_JPEG_OPTIMIZE), 1   # Optimize for size
            ]
            result, encoded_img = cv2.imencode('.jpg', frame, encode_param)
            
            if result:
                return encoded_img.tobytes()
            else:
                return None
                
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None
    
    def send_frame_data(self, data):
        """Send frame data to server with size header"""
        try:
            # Pack the size of the data
            size = len(data)
            size_data = struct.pack("!I", size)
            
            # Send size first, then data
            self.client_socket.sendall(size_data)
            self.client_socket.sendall(data)
            return True
        except Exception as e:
            print(f"Error sending frame: {e}")
            return False
    
    def calculate_fps(self):
        """Calculate and display current FPS"""
        self.frame_count += 1
        if self.frame_count % 30 == 0:  # Display FPS every 30 frames
            current_time = time.time()
            if self.start_time:
                elapsed = current_time - self.start_time
                fps = 30 / elapsed
                print(f"Current FPS: {fps:.1f}")
            self.start_time = current_time
    
    def start_streaming(self):
        """Start streaming screen to server"""
        if not self.connected:
            print("Not connected to server!")
            return
        
        # Initialize screen capture
        self.init_screen_capture()
        
        self.streaming = True
        self.start_time = time.time()
        print("Starting screen streaming... Press Ctrl+C to stop")
        print("Optimizations enabled for better performance")
        
        try:
            while self.streaming:
                frame_start = time.time()
                
                # Capture screen
                frame_data = self.capture_screen()
                
                if frame_data:
                    # Send frame to server
                    if not self.send_frame_data(frame_data):
                        print("Failed to send frame, stopping stream")
                        break
                    
                    # Calculate FPS
                    self.calculate_fps()
                
                # Dynamic frame rate control
                frame_time = time.time() - frame_start
                target_frame_time = 1.0 / 30.0  # Target 30 FPS
                
                if frame_time < target_frame_time:
                    time.sleep(target_frame_time - frame_time)
                
        except KeyboardInterrupt:
            print("\nStopping stream...")
        except Exception as e:
            print(f"Streaming error: {e}")
        finally:
            self.stop_streaming()
    
    def stop_streaming(self):
        """Stop streaming and disconnect"""
        self.streaming = False
        if self.sct:
            self.sct.close()
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.connected = False
        print("Disconnected from server")

def main():
    client = ScreenShareClient()
    
    print("=== Screen Share Client (Optimized) ===")
    
    # Get server details from user
    while True:
        try:
            host = input("Enter server IP address (or 'localhost' for same machine): ").strip()
            if not host:
                host = "localhost"
            
            port = input("Enter server port: ").strip()
            if not port:
                print("Port is required!")
                continue
            
            port = int(port)
            if port < 1024 or port > 65535:
                print("Port must be between 1024 and 65535")
                continue
                
            break
        except ValueError:
            print("Invalid port number!")
    
    # Connect to server
    if client.connect_to_server(host, port):
        # Start streaming
        client.start_streaming()
    else:
        print("Failed to connect to server")

if __name__ == "__main__":
    main() 