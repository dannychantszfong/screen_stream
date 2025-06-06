import socket
import threading
import time
import struct
import queue
from PIL import ImageGrab
import cv2
import numpy as np
import mss
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor

class AdvancedScreenShareClient:
    def __init__(self):
        self.client_socket = None
        self.connected = False
        self.streaming = False
        self.sct = None
        
        # Advanced features
        self.frame_queue = queue.Queue(maxsize=5)  # Frame buffer
        self.use_threading = True
        self.use_hardware_encoding = False
        self.adaptive_quality = True
        self.target_fps = 30
        self.current_quality = 75
        
        # Performance monitoring
        self.frame_times = []
        self.network_times = []
        
    def init_hardware_encoding(self):
        """Try to initialize hardware encoding (if available)"""
        try:
            # Check for NVIDIA GPU encoding
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            # This is a simplified check - real implementation would use
            # specialized libraries like nvidia-ml-py or Intel Media SDK
            self.use_hardware_encoding = True
            print("Hardware encoding available (simulated)")
        except:
            print("Hardware encoding not available, using software")
            self.use_hardware_encoding = False
    
    def adaptive_quality_control(self, frame_time, network_time):
        """Adjust quality based on performance metrics"""
        if not self.adaptive_quality:
            return
            
        total_time = frame_time + network_time
        target_time = 1.0 / self.target_fps
        
        if total_time > target_time * 1.2:  # 20% over target
            # Reduce quality
            self.current_quality = max(30, self.current_quality - 5)
        elif total_time < target_time * 0.8:  # 20% under target
            # Increase quality
            self.current_quality = min(90, self.current_quality + 2)
    
    def capture_worker(self):
        """Dedicated thread for screen capture"""
        while self.streaming:
            try:
                start_time = time.time()
                
                # Capture screen
                if self.sct:
                    monitor = self.sct.monitors[1]
                    screenshot = self.sct.grab(monitor)
                    frame = np.array(screenshot)
                    if frame.shape[2] == 4:
                        frame = frame[:, :, :3]
                else:
                    screenshot = ImageGrab.grab()
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                capture_time = time.time() - start_time
                
                # Add to queue (non-blocking)
                try:
                    self.frame_queue.put((frame, capture_time), block=False)
                except queue.Full:
                    # Drop frame if queue is full (prevents lag buildup)
                    pass
                    
                # Control capture rate
                time.sleep(max(0, (1.0 / self.target_fps) - capture_time))
                
            except Exception as e:
                print(f"Capture error: {e}")
                break
    
    def encode_frame_advanced(self, frame):
        """Advanced frame encoding with multiple options"""
        try:
            # Resize with different algorithms based on performance needs
            height, width = frame.shape[:2]
            new_width = min(1280, width)
            new_height = int(height * (new_width / width))
            
            if new_width != width:
                # Use different interpolation based on quality needs
                if self.current_quality > 70:
                    interpolation = cv2.INTER_CUBIC  # Higher quality
                else:
                    interpolation = cv2.INTER_LINEAR  # Faster
                    
                frame = cv2.resize(frame, (new_width, new_height), 
                                 interpolation=interpolation)
            
            # Advanced encoding options
            if self.use_hardware_encoding:
                # Simulate hardware encoding (would use actual GPU encoding)
                encode_param = [
                    int(cv2.IMWRITE_JPEG_QUALITY), self.current_quality,
                    int(cv2.IMWRITE_JPEG_OPTIMIZE), 1,
                    int(cv2.IMWRITE_JPEG_PROGRESSIVE), 1  # Progressive JPEG
                ]
            else:
                # Optimized software encoding
                encode_param = [
                    int(cv2.IMWRITE_JPEG_QUALITY), self.current_quality,
                    int(cv2.IMWRITE_JPEG_OPTIMIZE), 1
                ]
            
            result, encoded_img = cv2.imencode('.jpg', frame, encode_param)
            
            if result:
                return encoded_img.tobytes()
            return None
            
        except Exception as e:
            print(f"Encoding error: {e}")
            return None
    
    def network_worker(self):
        """Dedicated thread for network transmission"""
        while self.streaming:
            try:
                # Get frame from queue
                frame_data = self.frame_queue.get(timeout=1.0)
                if frame_data is None:
                    continue
                    
                frame, capture_time = frame_data
                
                # Encode frame
                encode_start = time.time()
                encoded_data = self.encode_frame_advanced(frame)
                encode_time = time.time() - encode_start
                
                if encoded_data:
                    # Send frame
                    network_start = time.time()
                    success = self.send_frame_data(encoded_data)
                    network_time = time.time() - network_start
                    
                    if success:
                        # Update adaptive quality
                        total_frame_time = capture_time + encode_time
                        self.adaptive_quality_control(total_frame_time, network_time)
                        
                        # Performance monitoring
                        self.frame_times.append(total_frame_time)
                        self.network_times.append(network_time)
                        
                        # Keep only recent measurements
                        if len(self.frame_times) > 100:
                            self.frame_times = self.frame_times[-50:]
                            self.network_times = self.network_times[-50:]
                    else:
                        print("Network send failed")
                        break
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Network worker error: {e}")
                break
    
    def connect_to_server(self, host, port):
        """Connect with optimized socket settings"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Professional socket optimizations
            self.client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024)  # 1MB buffer
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024)
            
            # Set socket timeout
            self.client_socket.settimeout(10.0)
            
            self.client_socket.connect((host, port))
            self.connected = True
            print(f"Connected to server at {host}:{port}")
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
    
    def send_frame_data(self, data):
        """Optimized frame transmission"""
        try:
            size = len(data)
            size_data = struct.pack("!I", size)
            
            # Send in one operation when possible
            full_data = size_data + data
            self.client_socket.sendall(full_data)
            return True
        except Exception as e:
            print(f"Error sending frame: {e}")
            return False
    
    def print_performance_stats(self):
        """Print performance statistics"""
        if self.frame_times and self.network_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            avg_network_time = sum(self.network_times) / len(self.network_times)
            actual_fps = 1.0 / (avg_frame_time + avg_network_time) if (avg_frame_time + avg_network_time) > 0 else 0
            
            print(f"Performance Stats:")
            print(f"  Average Frame Time: {avg_frame_time*1000:.1f}ms")
            print(f"  Average Network Time: {avg_network_time*1000:.1f}ms")
            print(f"  Actual FPS: {actual_fps:.1f}")
            print(f"  Current Quality: {self.current_quality}%")
    
    def start_streaming(self):
        """Start advanced streaming with threading"""
        if not self.connected:
            print("Not connected to server!")
            return
        
        # Initialize components
        try:
            import mss
            self.sct = mss.mss()
            print("Using MSS for screen capture")
        except ImportError:
            print("MSS not available, using PIL")
        
        self.init_hardware_encoding()
        
        self.streaming = True
        print("Starting advanced screen streaming...")
        print(f"Target FPS: {self.target_fps}")
        print(f"Adaptive Quality: {'Enabled' if self.adaptive_quality else 'Disabled'}")
        print("Press Ctrl+C to stop")
        
        try:
            if self.use_threading:
                # Start worker threads
                capture_thread = threading.Thread(target=self.capture_worker, daemon=True)
                network_thread = threading.Thread(target=self.network_worker, daemon=True)
                
                capture_thread.start()
                network_thread.start()
                
                # Performance monitoring loop
                last_stats_time = time.time()
                while self.streaming:
                    time.sleep(1.0)
                    
                    # Print stats every 10 seconds
                    if time.time() - last_stats_time > 10:
                        self.print_performance_stats()
                        last_stats_time = time.time()
                        
            else:
                # Fallback to single-threaded mode
                print("Using single-threaded mode")
                # ... single threaded implementation
                
        except KeyboardInterrupt:
            print("\nStopping stream...")
        except Exception as e:
            print(f"Streaming error: {e}")
        finally:
            self.stop_streaming()
    
    def stop_streaming(self):
        """Stop streaming and cleanup"""
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
    client = AdvancedScreenShareClient()
    
    print("=== Advanced Screen Share Client ===")
    print("Features: Threading, Adaptive Quality, Performance Monitoring")
    
    # Configuration options
    print("\nConfiguration:")
    try:
        fps_input = input("Target FPS (default 30): ").strip()
        if fps_input:
            client.target_fps = int(fps_input)
    except:
        pass
    
    adaptive = input("Enable adaptive quality? (y/n, default y): ").strip().lower()
    client.adaptive_quality = adaptive != 'n'
    
    # Get server connection
    while True:
        try:
            connection_input = input("Enter server address (IP:PORT): ").strip()
            
            if ':' in connection_input:
                host, port_str = connection_input.rsplit(':', 1)
                host = host.strip() or "localhost"
                port = int(port_str.strip())
                
                if 1024 <= port <= 65535:
                    break
                else:
                    print("Port must be between 1024 and 65535")
            else:
                print("Use format: IP:PORT")
        except ValueError:
            print("Invalid format")
    
    # Connect and stream
    if client.connect_to_server(host, port):
        client.start_streaming()
    else:
        print("Failed to connect to server")

if __name__ == "__main__":
    main() 