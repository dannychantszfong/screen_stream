import socket
import threading
import struct
import cv2
import numpy as np

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
        """Receive and display the video stream"""
        if not self.client_socket:
            print("No client connected!")
            return
        
        self.receiving = True
        print("Receiving stream... Press 'q' to quit")
        
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
                    # Display the frame
                    cv2.imshow('Screen Share - Server', frame)
                    
                    # Check for quit key
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("Quit key pressed")
                        break
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