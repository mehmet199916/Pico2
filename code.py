import time
import board
import digitalio
import usb_hid
import usb_cdc
import json

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
    
    def right_click(self):
        """Perform a right mouse click at current position."""
        if self._mouse_device is None:
            return
        
        print("Performing right click...")
        
        # Press right button
        self.report[0] = self.RIGHT_BUTTON
        self._send_report()
        
        # Small delay to ensure click is registered
        time.sleep(0.05)
        
        # Release right button
        self.report[0] = 0
        self._send_report()
    
    def click_at_pixel(self, pixel_x, pixel_y, button="left"):
        """Move to pixel coordinates and perform click."""
        self.move_to_pixel(pixel_x, pixel_y)
        time.sleep(0.1)  # Small delay after movement
        
        if button == "left":
            self.left_click()
        elif button == "right":
            self.right_click()
        
    def _send_report(self):
        """Send the current report to the host."""
        if self._mouse_device:
            self._mouse_device.send_report(self.report)

class MacroPlayer:
    """Handles macro storage and playback."""
    
    def __init__(self, mouse):
        self.mouse = mouse
        self.macros = {}
        self.current_macro = None
        self.playing = False
        self.loop_mode = False
        
    def add_macro(self, name, actions):
        """Add a macro with the given name and actions."""
        self.macros[name] = actions
        print(f"Added macro '{name}' with {len(actions)} actions")
    
    def play_macro(self, name, loop=False):
        """Play a macro by name."""
        if name not in self.macros:
            print(f"Macro '{name}' not found!")
            return False
        
        self.current_macro = name
        self.playing = True
        self.loop_mode = loop
        
        print(f"Playing macro '{name}' (loop={loop})")
        
        actions = self.macros[name]
        
        while self.playing:
            for action in actions:
                if not self.playing:
                    break
                    
                action_type = action.get("type")
                x = action.get("x", 0)
                y = action.get("y", 0)
                button = action.get("button", "left")
                delay = action.get("delay", 0.05)
                
                if action_type == "click":
                    self.mouse.click_at_pixel(x, y, button)
                elif action_type == "move":
                    self.mouse.move_to_pixel(x, y)
                
                # Apply delay between actions
                time.sleep(delay)
                
                # Check for serial commands during playback
                if usb_cdc.data.in_waiting:
                    command = usb_cdc.data.readline().decode('utf-8').strip()
                    if command == "STOP":
                        self.stop_macro()
                        break
            
            if not self.loop_mode:
                break
        
        self.playing = False
        print(f"Finished playing macro '{name}'")
        return True
    
    def stop_macro(self):
        """Stop the currently playing macro."""
        self.playing = False
        print("Macro playback stopped")
    
    def list_macros(self):
        """List all available macros."""
        return list(self.macros.keys())

# Initialize mouse and macro player
print(f"Screen resolution set to: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
print("Initializing absolute mouse...")
mouse = AbsoluteMouse()
macro_player = MacroPlayer(mouse)

# Blink LED to show we're starting
led.value = True
time.sleep(0.2)
led.value = False

print("Pico2 Macro Mouse ready!")
print("Listening for serial commands...")

# Main command loop
while True:
    if usb_cdc.data.in_waiting:
        try:
            command_line = usb_cdc.data.readline().decode('utf-8').strip()
            print(f"Received command: {command_line}")
            
            if command_line.startswith("MACRO_DATA:"):
                # Parse macro data: MACRO_DATA:macro_name:json_data
                parts = command_line.split(":", 2)
                if len(parts) >= 3:
                    macro_name = parts[1]
                    json_data = parts[2]
                    
                    try:
                        actions = json.loads(json_data)
                        macro_player.add_macro(macro_name, actions)
                        usb_cdc.data.write(b"OK\n")
                        led.value = True
                        time.sleep(0.1)
                        led.value = False
                    except Exception as e:
                        print(f"Error parsing macro data: {e}")
                        usb_cdc.data.write(b"ERROR\n")
            
            elif command_line.startswith("PLAY:"):
                # Parse play command: PLAY:macro_name or PLAY:macro_name:LOOP
                parts = command_line.split(":")
                if len(parts) >= 2:
                    macro_name = parts[1]
                    loop = len(parts) > 2 and parts[2] == "LOOP"
                    
                    if macro_player.play_macro(macro_name, loop):
                        usb_cdc.data.write(b"OK\n")
                    else:
                        usb_cdc.data.write(b"ERROR\n")
            
            elif command_line == "STOP":
                macro_player.stop_macro()
                usb_cdc.data.write(b"OK\n")
            
            elif command_line == "LIST":
                macros = macro_player.list_macros()
                response = "MACROS:" + ",".join(macros) + "\n"
                usb_cdc.data.write(response.encode())
            
            elif command_line.startswith("CLICK:"):
                # Parse click command: CLICK:x:y:button
                parts = command_line.split(":")
                if len(parts) >= 4:
                    x = int(parts[1])
                    y = int(parts[2])
                    button = parts[3]
                    mouse.click_at_pixel(x, y, button)
                    usb_cdc.data.write(b"OK\n")
            
            elif command_line.startswith("MOVE:"):
                # Parse move command: MOVE:x:y
                parts = command_line.split(":")
                if len(parts) >= 3:
                    x = int(parts[1])
                    y = int(parts[2])
                    mouse.move_to_pixel(x, y)
                    usb_cdc.data.write(b"OK\n")
            
            elif command_line == "PING":
                usb_cdc.data.write(b"PONG\n")
            
            else:
                print(f"Unknown command: {command_line}")
                usb_cdc.data.write(b"UNKNOWN\n")
        
        except Exception as e:
            print(f"Error processing command: {e}")
            usb_cdc.data.write(b"ERROR\n")
    
    # Short delay to prevent overwhelming the loop
    time.sleep(0.01)
