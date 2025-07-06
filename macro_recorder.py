import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import json
import serial
import serial.tools.list_ports
import pynput
from pynput import mouse, keyboard
import os
from datetime import datetime

class MacroRecorder:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pico2 Macro Recorder")
        self.root.geometry("700x600")
        
        # Serial connection
        self.serial_port = None
        self.serial_connected = False
        
        # Recording state
        self.recording = False
        self.current_macro = []
        self.alt_pressed = False
        self.macro_start_time = None
        
        # Macro storage
        self.macros = {}
        self.current_macro_name = ""
        
        # Mouse listener
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # GUI setup
        self.setup_gui()
        
        # Start listeners
        self.start_listeners()
        
        # Refresh ports and try to connect to Pico2
        self.refresh_ports()
        self.auto_connect()
    
    def setup_gui(self):
        """Setup the GUI interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="wens")
        
        # Connection frame
        conn_frame = ttk.LabelFrame(main_frame, text="Connection", padding="5")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 10))
        
        self.status_label = ttk.Label(conn_frame, text="Status: Disconnected")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(conn_frame, text="Port:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.port_combo = ttk.Combobox(conn_frame, width=10)
        self.port_combo.grid(row=1, column=1, padx=(5, 0), pady=(5, 0))
        
        ttk.Button(conn_frame, text="Refresh", command=self.refresh_ports).grid(row=1, column=2, padx=(5, 0), pady=(5, 0))
        ttk.Button(conn_frame, text="Connect", command=self.connect_to_pico).grid(row=1, column=3, padx=(5, 0), pady=(5, 0))
        ttk.Button(conn_frame, text="Disconnect", command=self.disconnect_from_pico).grid(row=1, column=4, padx=(5, 0), pady=(5, 0))
        
        # Recording frame
        rec_frame = ttk.LabelFrame(main_frame, text="Recording", padding="5")
        rec_frame.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))
        
        ttk.Label(rec_frame, text="Macro Name:").grid(row=0, column=0, sticky=tk.W)
        self.macro_name_entry = ttk.Entry(rec_frame, width=30)
        self.macro_name_entry.grid(row=0, column=1, padx=(5, 0))
        
        self.record_button = ttk.Button(rec_frame, text="Start Recording", command=self.toggle_recording)
        self.record_button.grid(row=0, column=2, padx=(10, 0))
        
        self.record_status = ttk.Label(rec_frame, text="Hold Alt and click to record")
        self.record_status.grid(row=1, column=0, columnspan=3, pady=(5, 0))
        
        # Recording feedback
        self.last_click_label = ttk.Label(rec_frame, text="Last click: None", foreground="blue")
        self.last_click_label.grid(row=2, column=0, columnspan=3, pady=(5, 0))
        
        self.click_counter_label = ttk.Label(rec_frame, text="Clicks recorded: 0", foreground="green")
        self.click_counter_label.grid(row=3, column=0, columnspan=3, pady=(5, 0))
        
        # Macro management frame
        macro_frame = ttk.LabelFrame(main_frame, text="Macro Management", padding="5")
        macro_frame.grid(row=2, column=0, columnspan=2, sticky="we", pady=(0, 10))
        
        # Macro list
        self.macro_listbox = tk.Listbox(macro_frame, height=8)
        self.macro_listbox.grid(row=0, column=0, columnspan=3, sticky="we", pady=(0, 5))
        
        # Control buttons
        button_frame = ttk.Frame(macro_frame)
        button_frame.grid(row=1, column=0, columnspan=3, pady=(5, 0))
        
        ttk.Button(button_frame, text="Play Once", command=self.play_macro).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="Play Loop", command=self.play_macro_loop).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(button_frame, text="Stop", command=self.stop_macro).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(button_frame, text="Delete", command=self.delete_macro).grid(row=0, column=3, padx=(0, 5))
        
        # File operations
        file_frame = ttk.Frame(macro_frame)
        file_frame.grid(row=2, column=0, columnspan=3, pady=(5, 0))
        
        ttk.Button(file_frame, text="Save Macros", command=self.save_macros).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(file_frame, text="Load Macros", command=self.load_macros).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(file_frame, text="Send to Pico", command=self.send_macro_to_pico).grid(row=0, column=2, padx=(0, 5))
        
        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=3, column=0, columnspan=2, sticky="wens", pady=(0, 10))
        
        self.log_text = tk.Text(log_frame, height=6, width=70)
        self.log_text.grid(row=0, column=0, sticky="wens")
        
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        macro_frame.columnconfigure(0, weight=1)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    
    def log_message(self, message):
        """Add a message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def refresh_ports(self):
        """Refresh the list of available COM ports."""
        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]
        
        self.port_combo['values'] = port_names
        if port_names:
            # Try to default to COM12 if available, otherwise first port
            if 'COM12' in port_names:
                self.port_combo.set('COM12')
            else:
                self.port_combo.set(port_names[0])
        
        self.log_message(f"Found {len(port_names)} COM ports: {', '.join(port_names) if port_names else 'None'}")
    
    def auto_connect(self):
        """Try to auto-connect to Pico2."""
        if self.port_combo.get():
            self.connect_to_pico()
    
    def connect_to_pico(self):
        """Connect to Pico2 via serial."""
        selected_port = self.port_combo.get()
        if not selected_port:
            messagebox.showerror("Error", "Please select a COM port")
            return
        
        try:
            if self.serial_port:
                self.serial_port.close()
            
            self.log_message(f"Attempting to connect to {selected_port}...")
            self.serial_port = serial.Serial(selected_port, 115200, timeout=2)
            time.sleep(2)  # Give time for connection
            
            # Send ping to test connection
            self.serial_port.write(b'PING\n')
            response = self.serial_port.readline().decode('utf-8').strip()
            
            if response == 'PONG':
                self.serial_connected = True
                self.status_label.config(text=f"Status: Connected to {selected_port}")
                self.log_message(f"Connected to Pico2 on {selected_port} successfully")
            else:
                raise Exception(f"Unexpected response: '{response}' (expected 'PONG')")
                
        except Exception as e:
            self.serial_connected = False
            self.status_label.config(text="Status: Connection Failed")
            self.log_message(f"Connection failed: {str(e)}")
            messagebox.showerror("Connection Error", f"Failed to connect to Pico2 on {selected_port}:\n{str(e)}")
    
    def disconnect_from_pico(self):
        """Disconnect from Pico2."""
        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None
        self.serial_connected = False
        self.status_label.config(text="Status: Disconnected")
        self.log_message("Disconnected from Pico2")
    
    def start_listeners(self):
        """Start mouse and keyboard listeners."""
        self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        
        self.mouse_listener.start()
        self.keyboard_listener.start()
    
    def on_key_press(self, key):
        """Handle key press events."""
        if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            self.alt_pressed = True
            if self.recording:
                self.record_status.config(text="Recording... (Alt held, click to record)")
    
    def on_key_release(self, key):
        """Handle key release events."""
        if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            self.alt_pressed = False
            if self.recording:
                self.record_status.config(text="Recording... (Hold Alt and click to record)")
    
    def on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click events."""
        if self.recording and self.alt_pressed and pressed:
            # Record the click
            current_time = time.time()
            if self.macro_start_time is None:
                self.macro_start_time = current_time
                delay = 0.05  # Default delay for first click
            else:
                delay = max(0.02, current_time - self.macro_start_time)
            
            button_name = "left" if button == mouse.Button.left else "right"
            
            action = {
                "type": "click",
                "x": x,
                "y": y,
                "button": button_name,
                "delay": delay
            }
            
            self.current_macro.append(action)
            
            # Update GUI feedback
            click_info = f"Last click: {button_name.upper()} at ({x}, {y}) - {delay:.3f}s delay"
            self.last_click_label.config(text=click_info)
            self.click_counter_label.config(text=f"Clicks recorded: {len(self.current_macro)}")
            self.log_message(f"Recorded {button_name} click at ({x}, {y}) with {delay:.3f}s delay")
            
            # Visual feedback - briefly flash the record button
            original_text = self.record_button.cget('text')
            self.record_button.config(text="● RECORDED")
            self.root.after(300, lambda: self.record_button.config(text=original_text))
            
            self.macro_start_time = current_time
    
    def toggle_recording(self):
        """Toggle recording state."""
        if not self.recording:
            macro_name = self.macro_name_entry.get().strip()
            if not macro_name:
                messagebox.showerror("Error", "Please enter a macro name")
                return
            
            self.current_macro_name = macro_name
            self.current_macro = []
            self.macro_start_time = None
            self.recording = True
            
            self.record_button.config(text="Stop Recording")
            self.record_status.config(text="Recording... (Hold Alt and click to record)")
            self.last_click_label.config(text="Last click: None")
            self.click_counter_label.config(text="Clicks recorded: 0")
            self.log_message(f"Started recording macro: {macro_name}")
        else:
            self.recording = False
            self.record_button.config(text="Start Recording")
            self.record_status.config(text="Hold Alt and click to record")
            
            if self.current_macro:
                self.macros[self.current_macro_name] = self.current_macro.copy()
                self.update_macro_list()
                self.log_message(f"Finished recording macro: {self.current_macro_name} ({len(self.current_macro)} actions)")
                self.last_click_label.config(text=f"Macro '{self.current_macro_name}' saved with {len(self.current_macro)} clicks")
            else:
                self.log_message("No actions recorded")
                self.last_click_label.config(text="No clicks recorded")
                self.click_counter_label.config(text="Clicks recorded: 0")
    
    def update_macro_list(self):
        """Update the macro list display."""
        self.macro_listbox.delete(0, tk.END)
        for name, actions in self.macros.items():
            self.macro_listbox.insert(tk.END, f"{name} ({len(actions)} actions)")
    
    def get_selected_macro_name(self):
        """Get the selected macro name."""
        selection = self.macro_listbox.curselection()
        if not selection:
            return None
        
        selected_text = self.macro_listbox.get(selection[0])
        return selected_text.split(' (')[0]  # Extract name before the action count
    
    def send_macro_to_pico(self):
        """Send selected macro to Pico2."""
        if not self.serial_connected:
            messagebox.showerror("Error", "Not connected to Pico2")
            return
        
        macro_name = self.get_selected_macro_name()
        if not macro_name:
            messagebox.showerror("Error", "Please select a macro")
            return
        
        try:
            macro_data = json.dumps(self.macros[macro_name])
            command = f"MACRO_DATA:{macro_name}:{macro_data}\n"
            
            if self.serial_port:
                self.serial_port.write(command.encode('utf-8'))
                response = self.serial_port.readline().decode('utf-8').strip()
                
                if response == 'OK':
                    self.log_message(f"Sent macro '{macro_name}' to Pico2")
                else:
                    self.log_message(f"Failed to send macro: {response}")
            else:
                self.log_message("Serial port not available")
                
        except Exception as e:
            self.log_message(f"Error sending macro: {str(e)}")
    
    def play_macro(self):
        """Play selected macro once."""
        self._play_macro(loop=False)
    
    def play_macro_loop(self):
        """Play selected macro in loop."""
        self._play_macro(loop=True)
    
    def _play_macro(self, loop=False):
        """Play selected macro."""
        if not self.serial_connected:
            messagebox.showerror("Error", "Not connected to Pico2")
            return
        
        macro_name = self.get_selected_macro_name()
        if not macro_name:
            messagebox.showerror("Error", "Please select a macro")
            return
        
        try:
            command = f"PLAY:{macro_name}"
            if loop:
                command += ":LOOP"
            command += "\n"
            
            if self.serial_port:
                self.serial_port.write(command.encode('utf-8'))
                response = self.serial_port.readline().decode('utf-8').strip()
                
                if response == 'OK':
                    loop_text = " (looping)" if loop else ""
                    self.log_message(f"Started playing macro '{macro_name}'{loop_text}")
                else:
                    self.log_message(f"Failed to play macro: {response}")
            else:
                self.log_message("Serial port not available")
                
        except Exception as e:
            self.log_message(f"Error playing macro: {str(e)}")
    
    def stop_macro(self):
        """Stop currently playing macro."""
        if not self.serial_connected:
            messagebox.showerror("Error", "Not connected to Pico2")
            return
        
        try:
            if self.serial_port:
                self.serial_port.write(b'STOP\n')
                response = self.serial_port.readline().decode('utf-8').strip()
                
                if response == 'OK':
                    self.log_message("Stopped macro playback")
                else:
                    self.log_message(f"Failed to stop macro: {response}")
            else:
                self.log_message("Serial port not available")
                
        except Exception as e:
            self.log_message(f"Error stopping macro: {str(e)}")
    
    def delete_macro(self):
        """Delete selected macro."""
        macro_name = self.get_selected_macro_name()
        if not macro_name:
            messagebox.showerror("Error", "Please select a macro")
            return
        
        if messagebox.askyesno("Confirm Delete", f"Delete macro '{macro_name}'?"):
            del self.macros[macro_name]
            self.update_macro_list()
            self.log_message(f"Deleted macro '{macro_name}'")
    
    def save_macros(self):
        """Save macros to file."""
        if not self.macros:
            messagebox.showwarning("Warning", "No macros to save")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.macros, f, indent=2)
                self.log_message(f"Saved macros to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save macros:\n{str(e)}")
    
    def load_macros(self):
        """Load macros from file."""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    loaded_macros = json.load(f)
                
                # Merge with existing macros
                self.macros.update(loaded_macros)
                self.update_macro_list()
                self.log_message(f"Loaded {len(loaded_macros)} macros from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load macros:\n{str(e)}")
    
    def run(self):
        """Run the application."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """Handle application closing."""
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.serial_port:
            self.serial_port.close()
        self.root.destroy()

if __name__ == "__main__":
    app = MacroRecorder()
    app.run()