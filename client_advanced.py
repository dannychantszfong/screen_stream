import socket
import threading
import time
import struct
import queue
import platform
import sys
import os
from PIL import ImageGrab
import cv2
import numpy as np
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor

# Platform detection
IS_MACOS = platform.system() == "Darwin"
IS_APPLE_SILICON = IS_MACOS and platform.machine() == "arm64"
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

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
        self.current_quality = 90  # Start with higher quality
        
        # Quality settings
        self.use_png_compression = False  # Option for lossless compression
        self.min_quality = 60  # Higher minimum quality
        self.max_quality = 98  # Higher maximum quality
        self.preserve_original_resolution = False  # Option to keep original size
        
        # Performance monitoring
        self.frame_times = []
        self.network_times = []
        
        # Platform-specific settings
        self.screen_capture_method = self.detect_best_capture_method()
        
    def detect_best_capture_method(self):
        """Detect the best screen capture method for the current platform"""
        if IS_MACOS:
            # Check for screen recording permissions on macOS
            if self.check_macos_permissions():
                try:
                    import mss
                    print("macOS: Using MSS for screen capture")
                    return "mss"
                except ImportError:
                    print("macOS: MSS not available, using PIL")
                    return "pil"
            else:
                print("macOS: Screen recording permission required")
                return "pil"  # Fallback to PIL
        else:
            # Windows/Linux
            try:
                import mss
                print(f"{platform.system()}: Using MSS for screen capture")
                return "mss"
            except ImportError:
                print(f"{platform.system()}: MSS not available, using PIL")
                return "pil"
    
    def check_macos_permissions(self):
        """Check if screen recording permissions are granted on macOS"""
        if not IS_MACOS:
            return True
            
        try:
            # Try to capture a small area to test permissions
            test_screenshot = ImageGrab.grab(bbox=(0, 0, 100, 100))
            # If we get a black image, permissions might be denied
            test_array = np.array(test_screenshot)
            if np.all(test_array == 0):
                print("⚠️  macOS Screen Recording Permission Required!")
                print("   Go to: System Preferences → Security & Privacy → Privacy → Screen Recording")
                print("   Add and enable your terminal application or Python")
                print("   You may need to restart the application after granting permission")
                return False
            return True
        except Exception as e:
            print(f"Permission check failed: {e}")
            return False
    
    def init_screen_capture(self):
        """Initialize screen capture based on detected method"""
        if self.screen_capture_method == "mss":
            try:
                import mss
                self.sct = mss.mss()
                
                if IS_MACOS:
                    # macOS-specific MSS optimizations
                    print("Initialized MSS for macOS")
                    # On macOS, we might need to handle multiple displays differently
                    monitors = self.sct.monitors
                    print(f"Detected {len(monitors)-1} monitor(s)")
                    
                elif IS_APPLE_SILICON:
                    # Apple Silicon specific optimizations
                    print("Optimizing for Apple Silicon")
                    
                return True
            except ImportError:
                print("MSS not available, falling back to PIL")
                self.screen_capture_method = "pil"
                return True
            except Exception as e:
                print(f"MSS initialization failed: {e}")
                self.screen_capture_method = "pil"
                return True
        
        # PIL fallback
        print("Using PIL for screen capture")
        return True
    
    def init_hardware_encoding(self):
        """Try to initialize hardware encoding with platform-specific optimizations"""
        try:
            if IS_APPLE_SILICON:
                # Apple Silicon has hardware video encoders
                print("Apple Silicon detected - hardware encoding capabilities available")
                # Note: Real implementation would use VideoToolbox framework
                # For now, we'll simulate this
                self.use_hardware_encoding = True
                print("Hardware encoding enabled (VideoToolbox simulation)")
                
            elif IS_MACOS:
                # Intel Mac
                print("Intel Mac detected - checking for hardware encoding")
                # Intel Macs may have Intel Quick Sync
                fourcc = cv2.VideoWriter_fourcc(*'H264')
                self.use_hardware_encoding = True
                print("Hardware encoding enabled (Intel Quick Sync simulation)")
                
            elif IS_WINDOWS:
                # Windows hardware encoding (NVENC, Intel Quick Sync, etc.)
                fourcc = cv2.VideoWriter_fourcc(*'H264')
                self.use_hardware_encoding = True
                print("Hardware encoding available (Windows)")
                
            else:
                # Linux
                print("Linux detected - using software encoding")
                self.use_hardware_encoding = False
                
        except Exception as e:
            print(f"Hardware encoding initialization failed: {e}")
            self.use_hardware_encoding = False
    
    def adaptive_quality_control(self, frame_time, network_time):
        """Adjust quality based on performance metrics with platform considerations"""
        if not self.adaptive_quality:
            return
            
        total_time = frame_time + network_time
        target_time = 1.0 / self.target_fps
        
        # Platform-specific quality adjustments - less aggressive quality reduction
        if IS_APPLE_SILICON:
            # Apple Silicon is generally faster, can handle higher quality
            quality_step = 2  # Smaller steps for smoother quality changes
            min_quality = 70  # Higher minimum for Apple Silicon
            max_quality = 98
        elif IS_MACOS:
            # Intel Mac
            quality_step = 3
            min_quality = 65  # Higher minimum for Intel Mac
            max_quality = 95
        else:
            # Windows/Linux
            quality_step = 4
            min_quality = self.min_quality
            max_quality = self.max_quality
        
        # Be less aggressive with quality reduction
        if total_time > target_time * 1.5:  # Only reduce if significantly over target
            # Reduce quality
            self.current_quality = max(min_quality, self.current_quality - quality_step)
        elif total_time < target_time * 0.7:  # Increase quality when well under target
            # Increase quality
            self.current_quality = min(max_quality, self.current_quality + (quality_step // 2))
    
    def capture_screen_mss(self):
        """Capture screen using MSS with platform-specific optimizations"""
        try:
            if IS_MACOS:
                # macOS-specific capture
                # Primary monitor on macOS
                monitor = self.sct.monitors[1]
                
                # On macOS, we might need to handle Retina displays
                screenshot = self.sct.grab(monitor)
                frame = np.array(screenshot)
                
                # Handle RGBA to RGB conversion
                if frame.shape[2] == 4:
                    frame = frame[:, :, :3]
                    
            else:
                # Windows/Linux capture
                monitor = self.sct.monitors[1]
                screenshot = self.sct.grab(monitor)
                frame = np.array(screenshot)
                
                if frame.shape[2] == 4:
                    frame = frame[:, :, :3]
            
            return frame
            
        except Exception as e:
            print(f"MSS capture error: {e}")
            return None
    
    def capture_screen_pil(self):
        """Capture screen using PIL with platform-specific handling"""
        try:
            if IS_MACOS:
                # macOS PIL capture
                screenshot = ImageGrab.grab()
                frame = np.array(screenshot)
                
                # macOS returns RGB, convert to BGR for OpenCV
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
            else:
                # Windows/Linux PIL capture
                screenshot = ImageGrab.grab()
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            return frame
            
        except Exception as e:
            print(f"PIL capture error: {e}")
            return None
    
    def capture_worker(self):
        """Dedicated thread for screen capture with platform optimizations"""
        while self.streaming:
            try:
                start_time = time.time()
                
                # Use appropriate capture method
                if self.screen_capture_method == "mss" and self.sct:
                    frame = self.capture_screen_mss()
                else:
                    frame = self.capture_screen_pil()
                
                if frame is None:
                    continue
                
                capture_time = time.time() - start_time
                
                # Add to queue (non-blocking)
                try:
                    self.frame_queue.put((frame, capture_time), block=False)
                except queue.Full:
                    # Drop frame if queue is full (prevents lag buildup)
                    pass
                    
                # Platform-specific timing adjustments
                if IS_APPLE_SILICON:
                    # Apple Silicon can handle higher frame rates
                    min_sleep = 0.001
                else:
                    min_sleep = 0.005
                
                sleep_time = max(min_sleep, (1.0 / self.target_fps) - capture_time)
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"Capture error: {e}")
                break
    
    def encode_frame_advanced(self, frame):
        """Advanced frame encoding with high-quality settings to reduce blur"""
        try:
            original_height, original_width = frame.shape[:2]
            
            # Smart resolution handling - avoid unnecessary resizing
            if self.preserve_original_resolution:
                # Keep original resolution for maximum quality
                new_width = original_width
                new_height = original_height
            else:
                # Platform-specific resolution limits - but be more conservative
                if IS_APPLE_SILICON:
                    max_width = 2560  # Higher res for Apple Silicon
                elif IS_MACOS:
                    max_width = 1920  # Higher res for Intel Mac
                else:
                    max_width = 1600  # Higher res for Windows/Linux
                
                # Only resize if significantly larger than max
                if original_width > max_width * 1.2:
                    new_width = max_width
                    new_height = int(original_height * (new_width / original_width))
                else:
                    # Keep original size if not too large
                    new_width = original_width
                    new_height = original_height
            
            # High-quality resizing if needed
            if new_width != original_width or new_height != original_height:
                # Always use highest quality interpolation for resizing
                if IS_APPLE_SILICON:
                    interpolation = cv2.INTER_LANCZOS4  # Best quality
                else:
                    interpolation = cv2.INTER_CUBIC  # High quality
                    
                frame = cv2.resize(frame, (new_width, new_height), 
                                 interpolation=interpolation)
            
            # High-quality encoding options
            if self.use_png_compression:
                # PNG for lossless compression (larger files but perfect quality)
                encode_param = [
                    int(cv2.IMWRITE_PNG_COMPRESSION), 3  # Balanced compression/speed
                ]
                result, encoded_img = cv2.imencode('.png', frame, encode_param)
            else:
                # High-quality JPEG encoding
                if self.use_hardware_encoding:
                    if IS_APPLE_SILICON:
                        # Apple Silicon optimized encoding - highest quality
                        encode_param = [
                            int(cv2.IMWRITE_JPEG_QUALITY), self.current_quality,
                            int(cv2.IMWRITE_JPEG_OPTIMIZE), 1,
                            int(cv2.IMWRITE_JPEG_PROGRESSIVE), 1,
                            int(cv2.IMWRITE_JPEG_LUMA_QUALITY), self.current_quality,
                            int(cv2.IMWRITE_JPEG_CHROMA_QUALITY), self.current_quality
                        ]
                    elif IS_MACOS:
                        # Intel Mac encoding - high quality
                        encode_param = [
                            int(cv2.IMWRITE_JPEG_QUALITY), self.current_quality,
                            int(cv2.IMWRITE_JPEG_OPTIMIZE), 1,
                            int(cv2.IMWRITE_JPEG_LUMA_QUALITY), self.current_quality,
                            int(cv2.IMWRITE_JPEG_CHROMA_QUALITY), min(95, self.current_quality + 5)
                        ]
                    else:
                        # Windows/Linux hardware encoding
                        encode_param = [
                            int(cv2.IMWRITE_JPEG_QUALITY), self.current_quality,
                            int(cv2.IMWRITE_JPEG_OPTIMIZE), 1,
                            int(cv2.IMWRITE_JPEG_LUMA_QUALITY), self.current_quality
                        ]
                else:
                    # High-quality software encoding
                    encode_param = [
                        int(cv2.IMWRITE_JPEG_QUALITY), self.current_quality,
                        int(cv2.IMWRITE_JPEG_OPTIMIZE), 1,
                        int(cv2.IMWRITE_JPEG_LUMA_QUALITY), self.current_quality,
                        int(cv2.IMWRITE_JPEG_CHROMA_QUALITY), min(98, self.current_quality + 3)
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
        """Connect with platform-optimized socket settings"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Platform-specific socket optimizations
            self.client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            if IS_MACOS:
                # macOS-specific socket settings
                buffer_size = 2 * 1024 * 1024  # 2MB buffer for macOS
                self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, buffer_size)
                self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buffer_size)
            else:
                # Windows/Linux
                buffer_size = 1024 * 1024  # 1MB buffer
                self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, buffer_size)
                self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buffer_size)
            
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
        """Print performance statistics with platform info"""
        if self.frame_times and self.network_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            avg_network_time = sum(self.network_times) / len(self.network_times)
            actual_fps = 1.0 / (avg_frame_time + avg_network_time) if (avg_frame_time + avg_network_time) > 0 else 0
            
            platform_info = f"{platform.system()} {platform.machine()}"
            if IS_APPLE_SILICON:
                platform_info += " (Apple Silicon)"
            
            print(f"Performance Stats ({platform_info}):")
            print(f"  Average Frame Time: {avg_frame_time*1000:.1f}ms")
            print(f"  Average Network Time: {avg_network_time*1000:.1f}ms")
            print(f"  Actual FPS: {actual_fps:.1f}")
            print(f"  Current Quality: {self.current_quality}%")
            print(f"  Capture Method: {self.screen_capture_method.upper()}")
    
    def start_streaming(self):
        """Start advanced streaming with platform-specific initialization"""
        if not self.connected:
            print("Not connected to server!")
            return
        
        # Platform-specific initialization
        print(f"Initializing for {platform.system()} {platform.machine()}")
        if IS_APPLE_SILICON:
            print("🍎 Apple Silicon optimizations enabled")
        elif IS_MACOS:
            print("🍎 macOS Intel detected")
        
        # Initialize screen capture
        if not self.init_screen_capture():
            print("Failed to initialize screen capture")
            return
        
        # Initialize hardware encoding
        self.init_hardware_encoding()
        
        self.streaming = True
        print("Starting advanced screen streaming...")
        print(f"Target FPS: {self.target_fps}")
        print(f"Adaptive Quality: {'Enabled' if self.adaptive_quality else 'Disabled'}")
        print(f"Hardware Encoding: {'Enabled' if self.use_hardware_encoding else 'Disabled'}")
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
    
    print("=== Advanced Screen Share Client (Cross-Platform) ===")
    print(f"Platform: {platform.system()} {platform.machine()}")
    if IS_APPLE_SILICON:
        print("🍎 Apple Silicon detected - Enhanced performance available")
    elif IS_MACOS:
        print("🍎 macOS Intel detected")
    
    print("Features: Threading, Adaptive Quality, Performance Monitoring, Platform Optimization")
    
    # macOS permission check
    if IS_MACOS:
        print("\n📋 macOS Setup:")
        print("   Ensure Screen Recording permission is granted in System Preferences")
        print("   Security & Privacy → Privacy → Screen Recording")
    
    # Configuration options
    print("\nConfiguration:")
    
    # Quality settings
    print("\n🎨 Quality Settings:")
    quality_mode = input("Quality mode (1=Balanced, 2=High Quality, 3=Maximum Quality): ").strip()
    
    if quality_mode == "2":
        print("🔧 High Quality mode selected")
        client.current_quality = 95
        client.min_quality = 75
        client.max_quality = 98
        client.preserve_original_resolution = False
    elif quality_mode == "3":
        print("🔧 Maximum Quality mode selected (larger bandwidth usage)")
        client.current_quality = 98
        client.min_quality = 85
        client.max_quality = 98
        client.preserve_original_resolution = True
        
        # Option for PNG compression
        use_png = input("Use PNG compression for lossless quality? (y/n, slower): ").strip().lower()
        if use_png == 'y':
            client.use_png_compression = True
            print("🖼️  PNG compression enabled (lossless)")
    else:
        print("🔧 Balanced mode selected")
    
    # FPS settings
    try:
        fps_input = input("Target FPS (default 30): ").strip()
        if fps_input:
            client.target_fps = int(fps_input)
    except:
        pass
    
    # Adaptive quality
    adaptive = input("Enable adaptive quality? (y/n, default y): ").strip().lower()
    client.adaptive_quality = adaptive != 'n'
    
    # Display current settings
    print(f"\n📊 Current Settings:")
    print(f"   Quality: {client.current_quality}% (range: {client.min_quality}-{client.max_quality}%)")
    print(f"   Compression: {'PNG (lossless)' if client.use_png_compression else 'JPEG (lossy)'}")
    print(f"   Resolution: {'Original' if client.preserve_original_resolution else 'Adaptive'}")
    print(f"   Target FPS: {client.target_fps}")
    print(f"   Adaptive Quality: {'Enabled' if client.adaptive_quality else 'Disabled'}")
    
    # Get server connection
    print("\n🌐 Connection:")
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