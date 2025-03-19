import asyncio
import time
import threading
import random
import math

import time
import threading
import serial  # Requires pySerial

class EMGHandler:
    def __init__(self):
        self.connected = False
        self.data = {
            'time': 0, 'bicep': 0, 'shoulder': 0, 'tricep': 0
        }
        self.data_callbacks = []
        self.data_thread = None
        self.thread_running = False
        self.serial_port = None

    def connect(self, port, baudrate):
        """
        Connect to the EMG device via the specified serial port and baudrate.
        """
        if self.connected:
            return "Already connected to the EMG device."
        
        try:
            # Attempt to open the serial port
            self.serial_port = serial.Serial(port, baudrate, timeout=1)
            # Give the device time to initialize (if needed)
            time.sleep(2)
        except Exception as e:
            return f"Error connecting to port {port}: {str(e)}"
        
        self.connected = True
        self.thread_running = True
        
        # Start the data reading thread
        self.data_thread = threading.Thread(target=self.read_serial)
        self.data_thread.daemon = True
        self.data_thread.start()
        
        print(f"[DEBUG] Connected to serial port {port} at {baudrate} baud.")
        return "Connected to EMG device via serial port successfully."

    def read_serial(self):
        """
        Read data from the serial port continuously. This function expects
        each line of data to contain four comma-separated values:
        time (ms), bicep, shoulder, and tricep.
        """
        while self.thread_running:
            try:
                # Read a line from the serial port
                line = self.serial_port.readline().decode(errors='ignore').strip()
                if line:
                    # Expecting a comma-separated line like: "12345,512,600,490"
                    parts = line.split(",")
                    if len(parts) == 4:
                        try:
                            self.data = {
                                'time': int(parts[0]),
                                'bicep': int(parts[1]),
                                'shoulder': int(parts[2]),
                                'tricep': int(parts[3])
                            }
                        except ValueError:
                            print(f"[DEBUG] Data conversion error for line: {line}")
                            continue
                        
                        # Notify registered callbacks
                        for callback in self.data_callbacks:
                            callback(self.data)
                    else:
                        print(f"[DEBUG] Unexpected data format: {line}")
            except Exception as e:
                print(f"[DEBUG] Error reading from serial port: {e}")
                time.sleep(0.1)

    def register_callback(self, callback):
        """Register a callback function to be called when new data arrives."""
        if callback not in self.data_callbacks:
            self.data_callbacks.append(callback)

    def disconnect(self):
        """
        Disconnect from the EMG device by stopping the read thread and closing the serial port.
        """
        if not self.connected:
            return "Not connected to any EMG device."
        
        self.thread_running = False
        if self.data_thread:
            self.data_thread.join(timeout=1.0)
        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception as e:
                print(f"[DEBUG] Error closing serial port: {e}")
        self.connected = False
        print("[DEBUG] Disconnected from EMG device via serial port.")
        return "Disconnected from EMG device."

    def get_data(self):
        """Return the most recent set of EMG data."""
        return self.data


import asyncio
import threading
import time
import struct
from bleak import BleakClient, BleakScanner

# Define the UUIDs for the IMU characteristics
ACCEL_X_UUID = "19b10011-e8f2-537e-4f6c-d104768a1214"
ACCEL_Y_UUID = "19b10012-e8f2-537e-4f6c-d104768a1214"
ACCEL_Z_UUID = "19b10013-e8f2-537e-4f6c-d104768a1214"
GYRO_X_UUID  = "19b10014-e8f2-537e-4f6c-d104768a1214"
GYRO_Y_UUID  = "19b10015-e8f2-537e-4f6c-d104768a1214"
GYRO_Z_UUID  = "19b10016-e8f2-537e-4f6c-d104768a1214"

class BluetoothManager:
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BluetoothManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if BluetoothManager._initialized:
            return
            
        self.loop = None
        self.loop_thread = None
        self.running = False
        self.scanner = None
        BluetoothManager._initialized = True
    
    def start(self):
        """Start the Bluetooth manager with a dedicated event loop"""
        if self.running:
            print("[DEBUG] BluetoothManager already running")
            return
            
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()
        self.running = True
        time.sleep(0.5)  # Give the loop time to start
        print("[DEBUG] BluetoothManager started")
    
    def _run_loop(self):
        """Run the asyncio event loop"""
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        except Exception as e:
            print(f"[ERROR] BluetoothManager loop error: {e}")
        finally:
            # Cancel all pending tasks
            try:
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                
                # Run loop until all tasks are cancelled
                if pending:
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as e:
                print(f"[ERROR] Error cleaning up tasks: {e}")
                
            self.loop.close()
            print("[DEBUG] BluetoothManager loop closed")
    
    def stop(self):
        """Stop the Bluetooth manager and clean up resources"""
        if not self.running:
            return
            
        print("[DEBUG] Stopping BluetoothManager")
        
        # Stop any ongoing scanning
        if self.scanner:
            try:
                async def stop_scanner():
                    await self.scanner.stop()
                    self.scanner = None
                
                if not self.loop.is_closed():
                    future = asyncio.run_coroutine_threadsafe(stop_scanner(), self.loop)
                    future.result(timeout=2.0)
            except Exception as e:
                print(f"[ERROR] Error stopping scanner: {e}")
        
        # Stop the event loop
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)
            
        # Wait for the thread to end
        if self.loop_thread and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=3.0)
            
        self.running = False
        print("[DEBUG] BluetoothManager stopped")
    
    def run_coroutine(self, coro, timeout=10.0):
        """Run a coroutine in the Bluetooth manager's event loop"""
        if not self.running or (self.loop and self.loop.is_closed()):
            self.start()
        
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future.result(timeout=timeout)
        except Exception as e:
            print(f"[ERROR] Error running coroutine: {e}")
            return f"Error: {str(e)}"


# Create a singleton instance of IMUHandler
_IMU_INSTANCE = None

class IMUHandler:
    def __new__(cls):
        global _IMU_INSTANCE
        if _IMU_INSTANCE is None:
            _IMU_INSTANCE = super(IMUHandler, cls).__new__(cls)
            _IMU_INSTANCE._initialized = False
        return _IMU_INSTANCE
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.connected = False
        self.data = {
            "accel_x": 0.0, "accel_y": 0.0, "accel_z": 0.0,
            "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0
        }
        self.notification_callbacks = []
        self.client = None
        self.device_address = None
        self.bt_manager = BluetoothManager()
        self.detection_stopped = False
        self._initialized = True
        print("[DEBUG] IMUHandler initialized")
    
    async def scan_for_device(self, timeout=5.0):
        """Scan for Arduino IMU device"""
        print("[DEBUG] Scanning for BLE devices...")
        
        # Create scanner only if needed
        scanner = BleakScanner()
        self.bt_manager.scanner = scanner
        
        try:
            devices = await scanner.discover(timeout=timeout)
            
            target_device = None
            for d in devices:
                print(f"[DEBUG] Found device: {d.name} at {d.address}")
                if d.name and "Arduino" in d.name:
                    target_device = d
                    break
            
            if target_device:
                self.device_address = target_device.address
                print(f"[DEBUG] Found device: {target_device.name} at {self.device_address}")
                return target_device
            else:
                print("[DEBUG] Arduino device not found")
                return None
        except Exception as e:
            print(f"[ERROR] Error scanning for devices: {e}")
            return None
        finally:
            # Don't stop the scanner here - let it be handled by the manager
            pass
    
    async def connect(self):
        """Connect to the Arduino IMU via Bluetooth and start notifications."""
        if self.connected and self.client and self.client.is_connected:
            print("[DEBUG] Already connected to IMU device")
            return "Already connected to IMU device."
        
        # Start the Bluetooth manager if not already running
        if not self.bt_manager.running:
            self.bt_manager.start()
        
        # First scan for the device
        device = await self.scan_for_device()
        if not device:
            return "Arduino IMU not found!"
        
        try:
            # Connect to the device
            print(f"[DEBUG] Connecting to device at {self.device_address}")
            self.client = BleakClient(self.device_address)
            await self.client.connect(timeout=10.0)
            
            if not self.client.is_connected:
                return "Failed to connect to IMU device."
            
            print("[DEBUG] Connected to IMU device")
            self.connected = True
            
            # Start notifications for all characteristics
            uuids = [ACCEL_X_UUID, ACCEL_Y_UUID, ACCEL_Z_UUID,
                     GYRO_X_UUID, GYRO_Y_UUID, GYRO_Z_UUID]
            for uuid in uuids:
                await self.client.start_notify(uuid, self.notification_handler)
            
            print("[DEBUG] Notifications started for all characteristics")
            return "Connected to IMU device successfully."
        except Exception as e:
            print(f"[ERROR] Error connecting to IMU: {e}")
            self.connected = False
            return f"Error connecting to IMU: {str(e)}"
    
    async def notification_handler(self, characteristic, data):
        """Handle BLE notifications"""
        if len(data) != 4:
            return
        
        value = struct.unpack("<f", data)[0]
        uuid = characteristic.uuid.lower()
        
        # Update data dictionary based on which characteristic sent the notification
        if uuid == ACCEL_X_UUID:
            self.data["accel_x"] = value
        elif uuid == ACCEL_Y_UUID:
            self.data["accel_y"] = value
        elif uuid == ACCEL_Z_UUID:
            self.data["accel_z"] = value
        elif uuid == GYRO_X_UUID:
            self.data["gyro_x"] = value
        elif uuid == GYRO_Y_UUID:
            self.data["gyro_y"] = value
        elif uuid == GYRO_Z_UUID:
            self.data["gyro_z"] = value
        
        # Call any registered callbacks with the updated data
        callbacks = self.notification_callbacks.copy()  # Make a copy to avoid modification during iteration
        for callback in callbacks:
            try:
                callback(self.data.copy())  # Pass a copy to avoid reference issues
            except Exception as e:
                print(f"[ERROR] Error in callback: {e}")
    
    async def disconnect(self):
        """Disconnect from the IMU device and clean up resources"""
        if not self.connected:
            return "Not connected to IMU device."
        
        print("[DEBUG] Disconnecting from IMU device...")
        
        try:
            # Stop notifications first
            if self.client and self.client.is_connected:
                uuids = [ACCEL_X_UUID, ACCEL_Y_UUID, ACCEL_Z_UUID,
                        GYRO_X_UUID, GYRO_Y_UUID, GYRO_Z_UUID]
                for uuid in uuids:
                    try:
                        await self.client.stop_notify(uuid)
                    except Exception as e:
                        print(f"[DEBUG] Error stopping notify for {uuid}: {str(e)}")
                
                # Then disconnect
                await self.client.disconnect()
        except Exception as e:
            print(f"[ERROR] Error during disconnect: {e}")
        finally:
            self.connected = False
            self.client = None
            print("[DEBUG] Disconnected from IMU device")
        
        return "Disconnected from IMU device."
    
    def register_callback(self, callback):
        """Register a callback for data updates"""
        if callback not in self.notification_callbacks:
            self.notification_callbacks.append(callback)
    
    def get_data(self):
        """Get the current IMU data"""
        return self.data.copy()  # Return a copy to avoid reference issues
    
    def process_imu_data(self, data):
        """Process IMU data for use in ML algorithms"""
        # This method can be extended for any additional processing needed
        pass


# Functions to connect and disconnect from IMU

def connect_to_imu():
    """Connect to the IMU device"""
    try:
        imu_handler = IMUHandler()
        bt_manager = BluetoothManager()
        
        # Start the Bluetooth manager
        bt_manager.start()
        
        # Connect to the IMU
        result = bt_manager.run_coroutine(imu_handler.connect())
        
        if imu_handler.connected:
            return {"status": "connected", "message": "Connected to IMU device and streaming data"}
        else:
            return {"status": "error", "message": f"Failed to connect: {result}"}
    except Exception as e:
        return {"status": "error", "message": f"Error connecting to IMU: {str(e)}"}

def disconnect_from_imu():
    """Disconnect from the IMU device"""
    try:
        imu_handler = IMUHandler()
        bt_manager = BluetoothManager()
        
        if not imu_handler.connected:
            return {"status": "not_connected", "message": "IMU not connected"}
        
        # Disconnect from the IMU
        result = bt_manager.run_coroutine(imu_handler.disconnect())
        
        # Stop the Bluetooth manager
        bt_manager.stop()
        
        return {"status": "disconnected", "message": "IMU disconnected successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Error disconnecting from IMU: {str(e)}"}