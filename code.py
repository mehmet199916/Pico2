import time
import board
import digitalio
import usb_hid

# LED for visual feedback
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Wait for USB host to recognize the device
time.sleep(1)


SCREEN_WIDTH = 2560   # Change to your screen width
SCREEN_HEIGHT = 1440  # Change to your screen height

# Popular options:
# 1920x1080 (Full HD)
# 2560x1440 (1440p) 
# 3840x2160 (4K)
# 1366x768 (Common laptop)

def pixel_to_absolute(pixel_x, pixel_y, screen_width=SCREEN_WIDTH, screen_height=SCREEN_HEIGHT):
    """Convert pixel coordinates to absolute mouse coordinates (0-32767)."""
    # Calculate the proportion and scale to 0-32767
    abs_x = int((pixel_x / screen_width) * 32767)
    abs_y = int((pixel_y / screen_height) * 32767)
    
    # Clamp to valid range
    abs_x = max(0, min(32767, abs_x))
    abs_y = max(0, min(32767, abs_y))
    
    return abs_x, abs_y

def find_device(devices, *, usage_page, usage):
    """Find a device with the specified usage page and usage."""
    for device in devices:
        if device.usage_page == usage_page and device.usage == usage:
            return device
    return None

class AbsoluteMouse:
    """Simple absolute mouse control with click functionality."""
    
    # Mouse button constants
    LEFT_BUTTON = 1
    RIGHT_BUTTON = 2
    MIDDLE_BUTTON = 4
    
    def __init__(self):
        # Find the absolute mouse device we set up in boot.py
        self._mouse_device = find_device(usb_hid.devices, usage_page=0x1, usage=0x02)
        if self._mouse_device is None:
            print("Mouse device not found!")
            return
        
        # HID report: [buttons, x_low, x_high, y_low, y_high, wheel]
        self.report = bytearray(6)
        
        # Test if device is ready
        try:
            self._send_report()
        except OSError:
            time.sleep(0.5)
            self._send_report()
    
    def move_to(self, x, y):
        """Move mouse to absolute coordinates (0-32767 for both x and y)."""
        if self._mouse_device is None:
            return
            
        # Clamp coordinates
        x = max(0, min(32767, x))
        y = max(0, min(32767, y))
        
        # Convert to little-endian bytes
        x_bytes = x.to_bytes(2, 'little')
        y_bytes = y.to_bytes(2, 'little')
        
        # Build report: [buttons, x_low, x_high, y_low, y_high, wheel]
        self.report[0] = 0  # No buttons pressed
        self.report[1] = x_bytes[0]  # X low byte
        self.report[2] = x_bytes[1]  # X high byte
        self.report[3] = y_bytes[0]  # Y low byte
        self.report[4] = y_bytes[1]  # Y high byte
        self.report[5] = 0  # No wheel movement
        
        self._send_report()
        
    def move_to_pixel(self, pixel_x, pixel_y):
        """Move mouse to specific pixel coordinates."""
        abs_x, abs_y = pixel_to_absolute(pixel_x, pixel_y)
        print(f"Moving to pixel ({pixel_x}, {pixel_y}) = absolute ({abs_x}, {abs_y})")
        self.move_to(abs_x, abs_y)
    
    def left_click(self):
        """Perform a left mouse click at current position."""
        if self._mouse_device is None:
            return
        
        print("Performing left click...")
        
        # Press left button
        self.report[0] = self.LEFT_BUTTON
        self._send_report()
        
        # Small delay to ensure click is registered
        time.sleep(0.05)
        
        # Release left button
        self.report[0] = 0
        self._send_report()
    
    def click_at_pixel(self, pixel_x, pixel_y):
        """Move to pixel coordinates and perform left click."""
        self.move_to_pixel(pixel_x, pixel_y)
        time.sleep(0.1)  # Small delay after movement
        self.left_click()
        
    def _send_report(self):
        """Send the current report to the host."""
        if self._mouse_device:
            self._mouse_device.send_report(self.report)

# Initialize mouse
print(f"Screen resolution set to: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
print("Initializing absolute mouse...")
mouse = AbsoluteMouse()

# Blink LED to show we're starting
led.value = True
time.sleep(0.2)
led.value = False

print("Moving mouse to your requested position and clicking...")
# Move to your specific pixel coordinates and left click: 2500, 1400
mouse.click_at_pixel(500, 1400)

# Wait and blink to show click completed
time.sleep(1)
led.value = True
time.sleep(0.1)
led.value = False

# Final blink sequence to show completion
time.sleep(0.5)
for i in range(3):
    led.value = True
    time.sleep(0.1)
    led.value = False
    time.sleep(0.1)

    led.value = True

print("Mouse movement and click sequence complete!")
print(f"Clicked at pixel coordinates (2500, 1400) on {SCREEN_WIDTH}x{SCREEN_HEIGHT} screen")
print("If the position is wrong, update SCREEN_WIDTH and SCREEN_HEIGHT at the top of the code")
