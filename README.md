# Screen Share Application

A Python-based screen sharing application using sockets that allows you to stream your screen over WiFi to another device on the same network.

## Features

- Real-time screen capture and streaming
- Compressed video transmission for better performance
- Simple client-server architecture
- Cross-platform compatibility
- Configurable host and port settings
- Automatic frame rate optimization
- Built-in error handling and connection management

## Requirements

- Python 3.7+ (tested with Python 3.12)
- Same WiFi network for both devices
- Windows, macOS, or Linux

## Project Structure

```
screen_stream/
├── client.py          # Screen capture and streaming client
├── server.py          # Stream receiver and display server
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Installation

1. Clone or download this repository
2. Navigate to the project directory:
```bash
cd screen_stream
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

### Dependency Troubleshooting

If you encounter installation issues with numpy on Python 3.12+, try:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Or install packages individually:
```bash
pip install pillow opencv-python numpy
```

## Quick Start

### Same Machine Test

1. **Terminal 1** (Start Server):
```bash
python server.py
# Host: [Press Enter for 0.0.0.0]
# Port: 8888
```

2. **Terminal 2** (Start Client):
```bash
python client.py
# Server IP: localhost
# Port: 8888
```

### Different Machines

1. **Server Machine** (Receiver):
```bash
python server.py
# Host: 0.0.0.0
# Port: 8888
```

2. **Client Machine** (Streamer):
```bash
python client.py
# Server IP: [Server's IP address]
# Port: 8888
```

## Usage

### Server Side (Receiver)

1. Run the server script:
```bash
python server.py
```

2. Enter the configuration:
   - **Host IP**: Press Enter for '0.0.0.0' (accepts connections from any IP) or enter a specific IP
   - **Port**: Enter a port number (e.g., 8888)

3. The server will start and wait for a client connection

4. Once connected, the screen stream will be displayed in a window

5. Press 'q' to quit or Ctrl+C to stop the server

### Client Side (Sender/Streamer)

1. Run the client script:
```bash
python client.py
```

2. Enter the server details:
   - **Server IP**: Enter the IP address of the server machine (or 'localhost' if same machine)
   - **Port**: Enter the same port number used by the server

3. The client will connect and start streaming the screen

4. Press Ctrl+C to stop streaming

## Network Setup

### Finding Your IP Address

**Windows:**
```cmd
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter

**macOS/Linux:**
```bash
ifconfig
```
Look for "inet" address under your WiFi interface (usually wlan0 or en0)

**Alternative (All platforms):**
```python
import socket
hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)
print(f"Your IP: {ip_address}")
```

### Example Usage Scenarios

#### Scenario 1: Laptop to Desktop (Same WiFi)
1. **Desktop** (IP: 192.168.1.100):
   ```bash
   python server.py
   # Host: 0.0.0.0
   # Port: 8888
   ```

2. **Laptop**:
   ```bash
   python client.py
   # Server IP: 192.168.1.100
   # Port: 8888
   ```

#### Scenario 2: Phone Hotspot Network
1. Connect both devices to the same hotspot
2. Find the server device's IP address
3. Use the same process as above

## Troubleshooting

### Connection Issues
- **"Connection refused"**: Ensure server is running first
- **"No route to host"**: Check if both devices are on the same network
- **Firewall blocking**: Allow Python or the specific port through firewall
- **Wrong IP**: Verify the IP address using `ipconfig` or `ifconfig`
- **Port in use**: Try a different port number (1024-65535)

### Performance Issues
- **Laggy stream**: Check WiFi signal strength on both devices
- **High CPU usage**: The application automatically optimizes, but you can:
  - Modify frame rate in `client.py` (line ~85): `time.sleep(0.05)` for 20 FPS
  - Reduce resolution by changing `new_width = min(1024, width)` in `client.py`
- **Network congestion**: Use 5GHz WiFi if available

### Display Issues
- **Black screen**: Check if screen capture permissions are granted (macOS)
- **Window not showing**: Ensure OpenCV GUI support is installed
- **Codec errors**: Try reinstalling opencv-python

### Firewall Settings

**Windows:**
1. Windows Defender Firewall → Allow an app through firewall
2. Add Python.exe or allow the specific port
3. Or temporarily disable firewall for testing

**macOS:**
1. System Preferences → Security & Privacy → Firewall
2. Add Python to allowed applications
3. Or use: `sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3`

**Linux:**
```bash
sudo ufw allow 8888  # Replace 8888 with your port
```

## Technical Details

- **Protocol**: TCP sockets for reliable transmission
- **Compression**: JPEG compression with 80% quality
- **Frame Rate**: ~30 FPS (adjustable via `time.sleep()` in client.py)
- **Resolution**: Automatically scaled to max 1280px width for bandwidth optimization
- **Data Format**: Size-prefixed binary frames for proper reconstruction
- **Error Handling**: Comprehensive exception handling for network issues

## Customization

### Adjusting Quality vs Performance

In `client.py`, you can modify:

```python
# Frame rate (line ~85)
time.sleep(0.033)  # 30 FPS
time.sleep(0.05)   # 20 FPS (better for slow networks)

# Compression quality (line ~45)
encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]  # 80% quality
encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]  # Lower quality, smaller size

# Resolution limit (line ~40)
new_width = min(1280, width)  # Max 1280px width
new_width = min(1024, width)  # Max 1024px width (faster)
```

## Security Considerations

- This application transmits unencrypted data over the network
- Only use on trusted networks
- Consider implementing authentication for production use
- The server accepts connections from any IP when using 0.0.0.0

## Limitations

- Works only on the same WiFi network (no internet streaming)
- Performance depends on network speed and quality
- No audio transmission (video only)
- Single client connection at a time
- No built-in authentication or encryption
- Requires Python and dependencies on both machines

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Contact

**Author:** Danny Chan (Tsz Fong Chan)  
**Email:** dannychantszfong@gmail.com  
**LinkedIn:** Tsz Fong Chan  
**GitHub:** @dannychantszfong

## License

This project is open source and available under the MIT License. 