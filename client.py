import socket
import threading
import time
import pickle
import struct
from PIL import ImageGrab
import cv2
import numpy as np

class ScreenShareClient:
    def __init__(self):
        self.client_socket = None
        self.connected = False
        self.streaming = False
        
    def connect_to_server(self, host, port):
        """Connect to the server"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            self.connected = True
            print(f"Connected to server at {host}:{port}")
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
    
    def capture_screen(self):
        """Capture the screen and return as compressed image data"""
        try:
            # Capture the screen
            screenshot = ImageGrab.grab()
            
            # Convert PIL image to numpy array
            frame = np.array(screenshot)
            
            # Convert RGB to BGR for OpenCV
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Resize frame to reduce bandwidth (optional)
            height, width = frame.shape[:2]
            new_width = min(1280, width)
            new_height = int(height * (new_width / width))
            frame = cv2.resize(frame, (new_width, new_height))
            
            # Compress the frame
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
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
    
    def start_streaming(self):
        """Start streaming screen to server"""
        if not self.connected:
            print("Not connected to server!")
            return
            
        self.streaming = True
        print("Starting screen streaming... Press Ctrl+C to stop")
        
        try:
            while self.streaming:
                # Capture screen
                frame_data = self.capture_screen()
                
                if frame_data:
                    # Send frame to server
                    if not self.send_frame_data(frame_data):
                        print("Failed to send frame, stopping stream")
                        break
                
                # Control frame rate (adjust as needed)
                time.sleep(0.033)  # ~30 FPS
                
        except KeyboardInterrupt:
            print("\nStopping stream...")
        except Exception as e:
            print(f"Streaming error: {e}")
        finally:
            self.stop_streaming()
    
    def stop_streaming(self):
        """Stop streaming and disconnect"""
        self.streaming = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.connected = False
        print("Disconnected from server")

def main():
    client = ScreenShareClient()
    
    print("=== Screen Share Client ===")
    
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