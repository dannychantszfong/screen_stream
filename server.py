import socket
import threading
import struct
import cv2
import numpy as np

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Connect to a remote address to determine local IP
        # This doesn't actually send data, just determines routing
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        try:
            # Fallback method
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except Exception:
            return "Unable to determine"

class ScreenShareServer:
    def __init__(self):
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.receiving = False
        
    def start_server(self, host, port):
        """Start the server and listen for connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((host, port))
            self.server_socket.listen(1)
            
            self.running = True
            print(f"Server started on {host}:{port}")
            
            # Display local IP address for easy connection
            local_ip = get_local_ip()
            print(f"Local IP address: {local_ip}")
            if host == "0.0.0.0":
                print(f"Clients can connect using: {local_ip}:{port}")
            
            print("Waiting for client connection...")
            
            return True
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False
    
    def wait_for_connection(self):
        """Wait for client connection"""
        try:
            self.client_socket, client_address = self.server_socket.accept()
            print(f"Client connected from {client_address}")
            return True
        except Exception as e:
            print(f"Error accepting connection: {e}")
            return False
    
    def receive_frame_data(self):
        """Receive frame data from client"""
        try:
            # First, receive the size of the incoming data
            size_data = b''
            while len(size_data) < 4:
                chunk = self.client_socket.recv(4 - len(size_data))
                if not chunk:
                    return None
                size_data += chunk
            
            # Unpack the size
            size = struct.unpack("!I", size_data)[0]
            
            # Receive the actual frame data
            frame_data = b''
            while len(frame_data) < size:
                chunk = self.client_socket.recv(min(size - len(frame_data), 4096))
                if not chunk:
                    return None
                frame_data += chunk
            
            return frame_data
            
        except Exception as e:
            print(f"Error receiving frame: {e}")
            return None
    
    def display_stream(self):
        """Receive and display the video stream with proper aspect ratio handling"""
        if not self.client_socket:
            print("No client connected!")
            return
        
        self.receiving = True
        print("Receiving stream... Press 'q' to quit, 'f' for fullscreen, 's' to fit screen")
        
        # Display mode settings
        fit_to_screen = False
        window_created = False
        
        try:
            while self.receiving:
                # Receive frame data
                frame_data = self.receive_frame_data()
                
                if frame_data is None:
                    print("Connection lost or no data received")
                    break
                
                # Decode the frame
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    original_height, original_width = frame.shape[:2]
                    
                    # Create window with proper sizing on first frame
                    if not window_created:
                        cv2.namedWindow('Screen Share - Server', cv2.WINDOW_NORMAL)
                        
                        # Get screen dimensions for smart initial sizing
                        try:
                            import tkinter as tk
                            root = tk.Tk()
                            screen_width = root.winfo_screenwidth()
                            screen_height = root.winfo_screenheight()
                            root.destroy()
                            
                            # Calculate initial window size (80% of screen size max)
                            max_display_width = int(screen_width * 0.8)
                            max_display_height = int(screen_height * 0.8)
                            
                            # Scale frame to fit screen while maintaining aspect ratio
                            scale_w = max_display_width / original_width
                            scale_h = max_display_height / original_height
                            scale = min(scale_w, scale_h, 1.0)  # Don't upscale
                            
                            display_width = int(original_width * scale)
                            display_height = int(original_height * scale)
                            
                            cv2.resizeWindow('Screen Share - Server', display_width, display_height)
                            print(f"Window sized to {display_width}x{display_height} (scale: {scale:.2f})")
                            print(f"Original stream: {original_width}x{original_height}")
                            
                        except ImportError:
                            # Fallback if tkinter not available
                            cv2.resizeWindow('Screen Share - Server', min(1200, original_width), min(800, original_height))
                            print(f"Stream resolution: {original_width}x{original_height}")
                        
                        window_created = True
                    
                    # Handle different display modes
                    display_frame = frame
                    if fit_to_screen:
                        # Get current window size
                        try:
                            # This is a workaround since OpenCV doesn't provide direct window size access
                            window_rect = cv2.getWindowImageRect('Screen Share - Server')
                            if window_rect[2] > 0 and window_rect[3] > 0:
                                display_frame = cv2.resize(frame, (window_rect[2], window_rect[3]), 
                                                         interpolation=cv2.INTER_LINEAR)
                        except:
                            pass  # Use original frame if resize fails
                    
                    # Display the frame
                    cv2.imshow('Screen Share - Server', display_frame)
                    
                    # Handle key presses
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        print("Quit key pressed")
                        break
                    elif key == ord('f'):
                        # Toggle fullscreen
                        cv2.setWindowProperty('Screen Share - Server', cv2.WND_PROP_FULLSCREEN, 
                                            cv2.WINDOW_FULLSCREEN)
                        print("Switched to fullscreen mode")
                    elif key == ord('s'):
                        # Toggle fit to screen
                        fit_to_screen = not fit_to_screen
                        if fit_to_screen:
                            print("Fit to screen mode enabled")
                        else:
                            print("Original size mode enabled")
                    elif key == ord('r'):
                        # Reset window size
                        cv2.setWindowProperty('Screen Share - Server', cv2.WND_PROP_FULLSCREEN, 
                                            cv2.WINDOW_NORMAL)
                        cv2.resizeWindow('Screen Share - Server', original_width, original_height)
                        fit_to_screen = False
                        print(f"Reset to original size: {original_width}x{original_height}")
                else:
                    print("Failed to decode frame")
                    
        except KeyboardInterrupt:
            print("\nStopping server...")
        except Exception as e:
            print(f"Display error: {e}")
        finally:
            self.stop_receiving()
    
    def stop_receiving(self):
        """Stop receiving and clean up"""
        self.receiving = False
        cv2.destroyAllWindows()
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
            print("Client disconnected")
    
    def stop_server(self):
        """Stop the server"""
        self.running = False
        self.receiving = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        cv2.destroyAllWindows()
        print("Server stopped")

def main():
    server = ScreenShareServer()
    
    print("=== Screen Share Server ===")
    
    # Get server configuration from user
    while True:
        try:
            host = input("Enter host IP (press Enter for '0.0.0.0' to accept from any IP): ").strip()
            if not host:
                host = "0.0.0.0"
            
            port = input("Enter port to listen on: ").strip()
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
    
    # Start server
    if server.start_server(host, port):
        try:
            # Wait for client connection
            if server.wait_for_connection():
                # Start displaying the stream
                server.display_stream()
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            server.stop_server()
    else:
        print("Failed to start server")

if __name__ == "__main__":
    main() 