# Pico2 Macro Recording and Playback System

A complete system for recording and playing back mouse macros using a Raspberry Pi Pico2 with CircuitPython and a Windows GUI application.

## Features

- **Record mouse clicks** at absolute positions while holding Alt key
- **Support for both left and right clicks** with configurable delays (20-40ms)
- **Multiple macro management** with save/load functionality
- **Loop playback** option for repetitive tasks
- **Serial communication** via USB (COM12, 115200 baud)
- **Real-time logging** and status feedback
- **GUI interface** for easy operation

## Hardware Requirements

- Raspberry Pi Pico2 with CircuitPython installed
- USB cable for connection to Windows PC
- Windows PC with COM12 available (or modify the code for different port)

## Software Requirements

### For Pico2 (CircuitPython)
- CircuitPython 8.x or later
- `usb_hid` library (built-in)
- `usb_cdc` library (built-in)

### For Windows Application
- Python 3.7 or later
- Required packages (install via `pip install -r requirements.txt`):
  - `pyserial==3.5`
  - `pynput==1.7.6`

## Installation

### 1. Setup Pico2

1. Install CircuitPython on your Pico2
2. Copy `boot.py` and `code.py` to the CIRCUITPY drive
3. Update the screen resolution in `code.py` if needed:
   ```python
   SCREEN_WIDTH = 2560   # Change to your screen width
   SCREEN_HEIGHT = 1440  # Change to your screen height
   ```

### 2. Setup Windows Application

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python macro_recorder.py
   ```

## Usage

### Recording Macros

1. **Start the GUI application** and ensure connection to Pico2
2. **Enter a macro name** in the "Macro Name" field
3. **Click "Start Recording"**
4. **Hold Alt key and click** at the positions you want to record
5. **Click "Stop Recording"** when finished
6. The macro will appear in the macro list

### Playing Macros

1. **Select a macro** from the list
2. **Click "Send to Pico"** to transfer the macro to the Pico2
3. **Click "Play Once"** for single execution or **"Play Loop"** for continuous playback
4. **Click "Stop"** to halt playback

### Saving/Loading Macros

- **Save Macros**: Export all macros to a JSON file
- **Load Macros**: Import macros from a JSON file
- **Delete**: Remove selected macro from the list

## Communication Protocol

The system uses a simple text-based protocol over serial:

- `PING` - Test connection (responds with `PONG`)
- `MACRO_DATA:name:json_data` - Send macro to Pico2
- `PLAY:name` - Play macro once
- `PLAY:name:LOOP` - Play macro in loop
- `STOP` - Stop current playback
- `LIST` - List available macros

## File Structure

```
├── code.py              # Pico2 CircuitPython code
├── boot.py              # Pico2 USB HID configuration
├── macro_recorder.py    # Windows GUI application
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Troubleshooting

### Connection Issues
- Ensure Pico2 is connected to COM12 (or modify the port in code)
- Check that CircuitPython is properly installed
- Verify the Pico2 is not in bootloader mode

### Recording Issues
- Make sure to hold Alt key while clicking
- Check that the application has focus
- Verify mouse coordinates are within screen bounds

### Playback Issues
- Ensure macro is sent to Pico2 before playing
- Check serial connection status
- Verify screen resolution settings match your display

## Customization

### Changing COM Port
Edit `macro_recorder.py` line 128:
```python
self.serial_port = serial.Serial('COM12', 115200, timeout=1)
```

### Adjusting Delays
The GUI records natural timing between clicks, but you can modify the delay range by editing the recording logic in `on_mouse_click()`.

### Screen Resolution
Update `SCREEN_WIDTH` and `SCREEN_HEIGHT` in `code.py` to match your display.

## Technical Details

### Mouse Positioning
The system uses absolute mouse positioning with coordinates from 0-32767 for both X and Y axes, automatically scaled to your screen resolution.

### HID Report Format
The Pico2 sends 6-byte HID reports: `[buttons, x_low, x_high, y_low, y_high, wheel]`

### Macro Format
Macros are stored as JSON arrays with action objects:
```json
[
  {
    "type": "click",
    "x": 100,
    "y": 200,
    "button": "left",
    "delay": 0.05
  }
]
```

## License

This project is open source and available under the MIT License.